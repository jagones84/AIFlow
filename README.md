# AI Flow Engine

A Python-based visual node workflow execution engine, inspired by n8n. It allows you to create drag-and-drop workflows directly from your browser, leveraging AI Agents, OpenRouter LLMs, and native local MCP (Model Context Protocol) Tools.

## Key Features
- **Visual Drag & Drop Interface:** Powered by Drawflow. Create, connect, and edit nodes in real time.
- **AI Agent Node:** Full LLM integration with dynamic "Tool Calling" loop to autonomously solve problems using multiple tools.
- **Native MCP Support:** Executes standard MCP JSON-RPC servers (e.g., Brave Search, FileSystem, Fetch) locally without needing an external bridge.
- **Topological Execution:** Nodes execute asynchronously following visual arrows/connections, with real-time UI status updates (green rings for running nodes).
- **Save & Load:** Workflows can be saved locally to your `config/workflows` folder as JSON.

## Project Structure

- `src/`: Core logic and models.
  - `web/`: Frontend static files (HTML, JS, CSS) for the Visual UI.
  - `models/`: Pydantic models for strict validation.
  - `logic/`: Orchestrator, node executor logic, and native MCP client.
- `config/`: Configuration files (`mcp_default.json`) and saved `workflows/`.
- `tests/`: Automated tests and agent simulation scripts.
- `outputs/`: Automatically generated run logs.

## Installation

### Requirements
- Python 3.10+ recommended

### Setup
1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   - Option A: copy `.env.template` to `.env` and fill keys (recommended for local dev)
   - Option B: start the app and set keys from the UI (Settings modal)

Minimum for Architect/LLM features:
- `OPENROUTER_API_KEY`

Optional (depending on which tools you enable/use):
- `BRAVE_API_KEY`, `TAVILY_API_KEY`, `GITHUB_TOKEN`, etc.

## Usage

Start the FastAPI server (serves UI + API):

```bash
python -m src.server
```

Open the UI:
- http://localhost:8000/

Set API keys from the UI (alternative to `.env`):
- Open Settings (⚙️) and save keys to the backend `.env`

### MCP configuration
- MCP configuration JSON files live in [config](file:///f:/REPOSITORIES/AI_flow/config) (e.g. `mcp_default.json`).
- The Tool list in the UI is populated from `/api/tools`. MCP servers/tools must be enabled/available for them to appear.

## Testing

Run unit tests:

```bash
pytest
```

Run integration tests (requires API keys / external services):

```bash
pytest -m integration
```

### Troubleshooting
- If port 8000 is busy, stop the existing process or change the port in [server.py](file:///f:/REPOSITORIES/AI_flow/src/server.py).
- If the UI loads but tools are missing, check `.env` keys and MCP config in `config/`.
