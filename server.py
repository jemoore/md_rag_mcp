"""
MCP Server for RAG over markdown API documentation.

Exposes tools that GitHub Copilot (or any MCP client) can call to
search and retrieve information from a directory of markdown files.

Usage:
    python server.py [--docs-dir PATH]
    
    Or set the DOCS_DIR environment variable.
"""

import argparse
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from indexer import MarkdownIndex

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DOCS_DIR = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(__file__), "docs"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,  # MCP uses stdout for protocol; logs go to stderr
)
logger = logging.getLogger("rag-server")

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="MCP RAG Server for API docs")
parser.add_argument(
    "--docs-dir",
    default=DEFAULT_DOCS_DIR,
    help="Path to directory containing markdown API docs",
)
args, _ = parser.parse_known_args()

docs_dir = args.docs_dir
logger.info(f"Docs directory: {docs_dir}")

# ---------------------------------------------------------------------------
# Build index
# ---------------------------------------------------------------------------

index = MarkdownIndex(docs_dir)
num_chunks = index.build()
logger.info(f"Index ready: {num_chunks} chunks")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "API Docs RAG",
    instructions=(
        "This server provides search over API documentation. "
        "Use the search_api_docs tool to find relevant documentation "
        "for any API-related question. Use lookup_api_file to read "
        "a specific doc file. Use list_api_docs to see all available files."
    ),
)


@mcp.tool()
def search_api_docs(query: str, top_k: int = 5) -> str:
    """
    Search the API documentation for information relevant to the query.

    Use this tool when you need to find documentation about API endpoints,
    parameters, request/response formats, error codes, authentication,
    or any other API-related topic.

    Args:
        query: Natural language search query describing what you're looking for.
               Examples: "authentication", "create user endpoint", "error codes",
               "rate limiting", "pagination parameters"
        top_k: Maximum number of results to return (default: 5, max: 20)
    
    Returns:
        Relevant documentation chunks with source file and section info.
    """
    top_k = min(max(1, top_k), 20)
    results = index.search(query, top_k=top_k)

    if not results:
        return f"No results found for: '{query}'. Try different keywords."

    parts = [f"Found {len(results)} relevant section(s) for '{query}':\n"]
    for i, chunk in enumerate(results, 1):
        parts.append(f"--- Result {i} ---")
        parts.append(chunk.context_string)
        parts.append("")

    return "\n".join(parts)


@mcp.tool()
def list_api_docs() -> str:
    """
    List all available API documentation files.

    Use this tool to discover what documentation is available,
    or to find the right file to look up.

    Returns:
        A list of all markdown files in the documentation directory.
    """
    files = index.list_files()
    if not files:
        return "No documentation files found."

    stats = index.get_stats()
    lines = [
        f"API Documentation ({stats['total_files']} files, {stats['total_chunks']} sections):",
        "",
    ]
    for f in files:
        lines.append(f"  - {f}")
    return "\n".join(lines)


@mcp.tool()
def lookup_api_file(file_path: str) -> str:
    """
    Read the full content of a specific API documentation file.

    Use this tool when you know exactly which file contains the
    information you need (e.g., after seeing it in search results).

    Args:
        file_path: Relative path to the markdown file within the docs directory.
                   Example: "endpoints/users.md"

    Returns:
        The full content of the documentation file.
    """
    from pathlib import Path

    full_path = Path(docs_dir) / file_path
    
    # Security: ensure the resolved path is within docs_dir
    try:
        full_path = full_path.resolve()
        docs_resolved = Path(docs_dir).resolve()
        if not str(full_path).startswith(str(docs_resolved)):
            return "Error: Path is outside the documentation directory."
    except (OSError, ValueError):
        return "Error: Invalid file path."

    if not full_path.exists():
        # Try to find close matches
        available = index.list_files()
        suggestions = [f for f in available if file_path.lower() in f.lower()]
        if suggestions:
            return f"File not found: '{file_path}'. Did you mean: {', '.join(suggestions)}"
        return f"File not found: '{file_path}'. Use list_api_docs to see available files."

    if not full_path.suffix.lower() == ".md":
        return "Error: Only markdown (.md) files can be read."

    try:
        content = full_path.read_text(encoding="utf-8")
        return f"[File: {file_path}]\n\n{content}"
    except (UnicodeDecodeError, OSError) as e:
        return f"Error reading file: {e}"


@mcp.tool()
def rebuild_index() -> str:
    """
    Rebuild the search index.

    Use this tool if the documentation files have been updated
    and you need to refresh the search index.

    Returns:
        Status message with the number of chunks indexed.
    """
    num = index.build()
    return f"Index rebuilt successfully: {num} chunks from {len(index.list_files())} files."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting MCP RAG server (stdio transport)...")
    mcp.run(transport="stdio")
