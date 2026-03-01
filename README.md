# API Docs Search — MCP Server for Copilot

An MCP (Model Context Protocol) server that indexes a directory of markdown files and exposes search tools to GitHub Copilot. This lets Copilot automatically retrieve relevant API documentation when answering your questions.

## How It Works

1. **Indexing** — Parses all `.md` files in your docs directory, splitting them into chunks by heading hierarchy
2. **Search** — Uses [BM25 (Okapi)](https://en.wikipedia.org/wiki/Okapi_BM25) term-frequency ranking to find the most relevant chunks for a query (no embeddings or vector database required)
3. **Retrieval-Augmented Generation** — Copilot calls the search tools via MCP, receives the matching document chunks, and uses them as context when generating its response

This is a lightweight RAG approach: the retrieval is keyword-based (BM25) rather than semantic/vector-based, but the overall pattern — retrieve relevant docs, augment the prompt, generate a grounded answer — is the same.

## Setup

### 1. Create a virtual environment and install dependencies

```bash
cd rag
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Add your markdown docs

Place your API documentation markdown files in the `docs/` subdirectory (or configure a different path):

```
rag/
├── .venv/
├── docs/
│   ├── authentication.md
│   ├── endpoints/
│   │   ├── current-weather.md
│   │   └── forecast.md
│   └── errors.md
├── server.py
├── indexer.py
└── ...
```

### 3. VS Code MCP Configuration

The `.vscode/mcp.json` file is already configured. VS Code will automatically detect and offer to start the MCP server. The configuration uses absolute paths to the virtual environment's Python interpreter and the server script, so it can work from any workspace.

#### Using from another project

You can copy `.vscode/mcp.json` into any other project's `.vscode/` directory to give that project access to the same API docs search tools in Copilot — no need to open the `rag` folder itself. Just make sure the paths in the JSON point to this project's virtual environment and server script:

```json
{
  "servers": {
    "api-docs-rag": {
      "type": "stdio",
      "command": "D:/dev2/cpp/clanker/rag/.venv/Scripts/python.exe",
      "args": [
        "D:/dev2/cpp/clanker/rag/server.py",
        "--docs-dir",
        "D:/dev2/cpp/clanker/rag/docs"
      ]
    }
  }
}
```

Adjust the paths to match where you cloned this repository. You can also change `--docs-dir` to point to a different documentation directory.

### 4. Start using it

1. Open any project that has the `mcp.json` configured in its `.vscode/` directory
2. VS Code should detect the MCP server config — click **Start** when prompted
3. Open Copilot Chat and ask questions about your API
4. Copilot will automatically call `search_api_docs` to find relevant documentation

## Available Tools

| Tool | Description |
|------|-------------|
| `search_api_docs(query, top_k)` | Search docs with a natural language query |
| `list_api_docs()` | List all indexed documentation files |
| `lookup_api_file(file_path)` | Read the full content of a specific doc file |
| `rebuild_index()` | Re-index docs after files change |

## Example Queries

Once running, try asking Copilot:

- "How do I authenticate with the API?"
- "What parameters does the create user endpoint accept?"
- "What error codes can the API return?"
- "Show me the rate limiting documentation"

## Testing Manually

You can test the server directly:

```bash
# Run via MCP CLI inspector
mcp dev server.py -- --docs-dir ./docs

# Or specify a custom docs path
python server.py --docs-dir D:/my/api/docs
```

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `--docs-dir` | `./docs` or `$DOCS_DIR` | Path to markdown documentation directory |
