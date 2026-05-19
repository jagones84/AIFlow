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
4. Copy `.env.template` to `.env` and fill in any required environment variables (e.g. `OPENROUTER_API_KEY`, `BRAVE_API_KEY`).

## Usage

Start the FastAPI server:

```bash
python -m src.server
```

Then open your browser and navigate to: [http://localhost:8000/](http://localhost:8000/)

## Testing

Run unit tests:

```bash
pytest
```

Run integration tests (requires API keys / external services):

```bash
pytest -m integration
```
