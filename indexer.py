"""
Markdown document indexer with BM25 search.

Parses markdown files, chunks them by headings, and builds a BM25 index
for fast keyword-based retrieval.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class DocChunk:
    """A chunk of documentation extracted from a markdown file."""
    file_path: str
    heading: str
    heading_level: int
    content: str
    parent_headings: list[str] = field(default_factory=list)

    @property
    def full_heading_path(self) -> str:
        """Returns the full heading hierarchy, e.g. 'API > Users > Create User'."""
        parts = self.parent_headings + [self.heading]
        return " > ".join(parts)

    @property
    def context_string(self) -> str:
        """Returns a formatted string for inclusion in LLM context."""
        rel_path = self.file_path
        header = f"[Source: {rel_path} | Section: {self.full_heading_path}]"
        return f"{header}\n\n{self.content.strip()}"


def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer for BM25."""
    text = text.lower()
    # Keep alphanumeric, hyphens, underscores (common in API names)
    tokens = re.findall(r'[a-z0-9_\-]+', text)
    return tokens


def parse_markdown_file(file_path: Path, docs_root: Path) -> list[DocChunk]:
    """
    Parse a markdown file into chunks split by headings.
    
    Each chunk contains the content under a heading, along with
    the heading hierarchy for context.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        logger.warning(f"Could not read {file_path}: {e}")
        return []

    rel_path = str(file_path.relative_to(docs_root)).replace("\\", "/")
    lines = content.split("\n")

    chunks: list[DocChunk] = []
    heading_stack: list[tuple[int, str]] = []  # (level, heading_text)
    current_heading = file_path.stem  # Default heading = filename
    current_level = 0
    current_lines: list[str] = []

    def flush_chunk():
        text = "\n".join(current_lines).strip()
        if text:
            parent_headings = [h for _, h in heading_stack]
            chunks.append(DocChunk(
                file_path=rel_path,
                heading=current_heading,
                heading_level=current_level,
                content=text,
                parent_headings=parent_headings,
            ))

    for line in lines:
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            # Flush previous chunk
            flush_chunk()
            current_lines = []

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # Update heading stack - pop headings at same or deeper level
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            # The current heading's parents are what's in the stack
            current_heading = heading_text
            current_level = level
            current_lines.append(line)  # Include the heading itself
        else:
            current_lines.append(line)

    # Don't forget the last chunk
    flush_chunk()

    # If no headings found, treat entire file as one chunk
    if not chunks and content.strip():
        chunks.append(DocChunk(
            file_path=rel_path,
            heading=file_path.stem,
            heading_level=0,
            content=content.strip(),
            parent_headings=[],
        ))

    return chunks


class MarkdownIndex:
    """
    BM25 search index over a directory of markdown files.
    
    Usage:
        index = MarkdownIndex("./docs")
        index.build()
        results = index.search("create user endpoint", top_k=5)
    """

    def __init__(self, docs_dir: str):
        self.docs_dir = Path(docs_dir)
        self.chunks: list[DocChunk] = []
        self.bm25: Optional[BM25Okapi] = None
        self._tokenized_corpus: list[list[str]] = []

    def build(self) -> int:
        """
        Scan the docs directory, parse all markdown files, and build the index.
        Returns the number of chunks indexed.
        """
        if not self.docs_dir.exists():
            logger.warning(f"Docs directory does not exist: {self.docs_dir}")
            return 0

        self.chunks = []
        md_files = sorted(self.docs_dir.rglob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files in {self.docs_dir}")

        for md_file in md_files:
            file_chunks = parse_markdown_file(md_file, self.docs_dir)
            self.chunks.extend(file_chunks)

        if not self.chunks:
            logger.warning("No chunks found in markdown files")
            return 0

        # Build BM25 index
        # Tokenize both heading path and content for better matching
        self._tokenized_corpus = [
            tokenize(f"{chunk.full_heading_path} {chunk.content}")
            for chunk in self.chunks
        ]
        self.bm25 = BM25Okapi(self._tokenized_corpus)

        logger.info(f"Built index with {len(self.chunks)} chunks from {len(md_files)} files")
        return len(self.chunks)

    def search(self, query: str, top_k: int = 5) -> list[DocChunk]:
        """
        Search the index and return the top-k most relevant chunks.
        """
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Get top-k indices sorted by score (descending)
        scored_indices = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        # Filter out zero-score results
        results = [
            self.chunks[idx]
            for idx, score in scored_indices
            if score > 0
        ]

        return results

    def list_files(self) -> list[str]:
        """Return a list of all indexed file paths."""
        return sorted(set(chunk.file_path for chunk in self.chunks))

    def get_stats(self) -> dict:
        """Return index statistics."""
        return {
            "docs_dir": str(self.docs_dir),
            "total_files": len(self.list_files()),
            "total_chunks": len(self.chunks),
        }
