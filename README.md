# API Docs RAG — MCP Server for Copilot

An MCP (Model Context Protocol) server that indexes a directory of markdown files and exposes search tools to GitHub Copilot. This lets Copilot automatically retrieve relevant API documentation when answering your questions.

## How It Works

1. **Indexing**: Parses all `.md` files in your docs directory, splitting them into chunks by headings
2. **Search**: Uses BM25 (Okapi) ranking to find the most relevant chunks for a query
3. **MCP**: Exposes search as tools that Copilot calls automatically via the Model Context Protocol

## Setup

### 1. Install dependencies

```bash
cd rag
pip install -r requirements.txt
```

### 2. Add your markdown docs

Place your API documentation markdown files in the `docs/` subdirectory (or configure a different path):

```
rag/
├── docs/
│   ├── authentication.md
│   ├── endpoints/
│   │   ├── users.md
│   │   └── posts.md
│   └── errors.md
├── server.py
├── indexer.py
└── ...
```

### 3. VS Code MCP Configuration

The `.vscode/mcp.json` file is already configured. VS Code will automatically detect and offer to start the MCP server.

To change the docs directory, edit `.vscode/mcp.json`:

```json
{
  "servers": {
    "api-docs-rag": {
      "type": "stdio",
      "command": "python",
      "args": ["server.py", "--docs-dir", "D:/path/to/your/docs"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

You can also set the `DOCS_DIR` environment variable instead.

### 4. Start using it

1. Open this folder in VS Code
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
