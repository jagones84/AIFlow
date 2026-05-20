import asyncio
import json
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn
import os
from dotenv import load_dotenv
from pydantic import BaseModel

from src.models.node_models import FlowProjectData
from src.main import FlowApp
from src.utils.managers import LogManager

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

app = FastAPI(title="AI Flow Engine API")

# Global reference to current running flow
current_flow_app = None

# Global state for Architect non-blocking execution
architect_state = {
    "running": False,
    "finished": False,
    "result": None,
    "error": None,
    "drawflow": None,
    "last_action": "Initializing..."
}

# Global architect chat history
architect_chat_history = []

@app.delete("/api/architect/chat")
async def clear_architect_chat():
    global architect_chat_history
    architect_chat_history = []
    return {"status": "success", "message": "Architect memory cleared."}

@app.get("/api/status")
async def get_status():
    global current_flow_app
    logs = LogManager.get_history()
    if current_flow_app:
        nodes = current_flow_app.get_nodes()
        waiting_nodes = [n.id for n in nodes if n.status.value == "WAITING_FOR_USER"]
        
        # Try to find the last AI output if there's a waiting node
        last_ai_message = ""
        if waiting_nodes:
            # Look backwards from the waiting node to find the last AI Agent's output
            waiting_node = next((n for n in nodes if n.id == waiting_nodes[0]), None)
            if waiting_node and waiting_node.lastInputItems:
                last_ai_message = waiting_node.lastInputItems[0].json_data.get("text", "")
            elif waiting_node and waiting_node.lastInput:
                last_ai_message = waiting_node.lastInput
                
        return {
            "running_nodes": [n.id for n in nodes if n.status.value == "RUNNING"],
            "waiting_nodes": waiting_nodes,
            "last_ai_message": last_ai_message,
            "logs": logs
        }
    return {"running_nodes": [], "waiting_nodes": [], "last_ai_message": "", "logs": logs}

class ResumeRequest(BaseModel):
    node_id: str
    user_text: str

@app.post("/api/resume")
async def resume_flow(req: ResumeRequest):
    global current_flow_app
    if not current_flow_app:
        return {"status": "error", "message": "No active flow"}
    
    node = current_flow_app.get_node(req.node_id)
    if node and node.status.value == "WAITING_FOR_USER":
        await current_flow_app.orchestrator.resume_node(req.node_id, req.user_text)
        return {"status": "success"}
    return {"status": "error", "message": "Node not waiting for user"}

@app.post("/api/stop")
async def stop_flow():
    global current_flow_app
    if current_flow_app:
        current_flow_app.orchestrator.stop_flow()
        return {"status": "success"}
    return {"status": "error", "message": "No active flow"}

# Serve the static HTML directly from the root path
@app.get("/")
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "web", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return HTMLResponse("<h1>UI not found. Ensure src/web/index.html exists.</h1>", status_code=404)

# Mount static files if they exist
os.makedirs("src/web", exist_ok=True)

class EnvData(BaseModel):
    openai: str = ""
    anthropic: str = ""
    openrouter: str = ""
    gemini: str = ""
    groq: str = ""
    brave: str = ""
    tavily: str = ""
    huggingface: str = ""
    mapbox: str = ""
    youtube: str = ""
    github: str = ""

@app.get("/api/env")
async def get_env():
    return {
        "openai": "",
        "anthropic": "",
        "openrouter": "",
        "gemini": "",
        "groq": "",
        "brave": "",
        "tavily": "",
        "huggingface": "",
        "mapbox": "",
        "youtube": "",
        "github": "",
        "has_openai": bool(os.getenv("OPENAI_API_KEY", "")),
        "has_anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "")),
        "has_openrouter": bool(os.getenv("OPENROUTER_API_KEY", "")),
        "has_gemini": bool(os.getenv("GEMINI_API_KEY", "")),
        "has_groq": bool(os.getenv("GROQ_API_KEY", "")),
        "has_brave": bool(os.getenv("BRAVE_API_KEY", "")),
        "has_tavily": bool(os.getenv("TAVILY_API_KEY", "")),
        "has_huggingface": bool(os.getenv("HF_TOKEN", "")),
        "has_mapbox": bool(os.getenv("MAPBOX_API_KEY", "")),
        "has_youtube": bool(os.getenv("YOUTUBE_API_KEY", "")),
        "has_github": bool(os.getenv("GITHUB_TOKEN", "")),
    }

@app.post("/api/env")
async def set_env(data: EnvData):
    # Write to .env file
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            env_lines = f.readlines()
            
    new_lines = []
    found = {
        "OPENAI_API_KEY": False,
        "ANTHROPIC_API_KEY": False,
        "OPENROUTER_API_KEY": False,
        "GEMINI_API_KEY": False,
        "GROQ_API_KEY": False,
        "BRAVE_API_KEY": False,
        "TAVILY_API_KEY": False,
        "HF_TOKEN": False,
        "MAPBOX_API_KEY": False,
        "YOUTUBE_API_KEY": False,
        "GITHUB_TOKEN": False
    }
    
    # Map the env key to the Pydantic field name
    key_to_field = {
        "OPENAI_API_KEY": "openai",
        "ANTHROPIC_API_KEY": "anthropic",
        "OPENROUTER_API_KEY": "openrouter",
        "GEMINI_API_KEY": "gemini",
        "GROQ_API_KEY": "groq",
        "BRAVE_API_KEY": "brave",
        "TAVILY_API_KEY": "tavily",
        "HF_TOKEN": "huggingface",
        "MAPBOX_API_KEY": "mapbox",
        "YOUTUBE_API_KEY": "youtube",
        "GITHUB_TOKEN": "github"
    }
    
    for line in env_lines:
        line_key = line.split("=")[0].strip() if "=" in line else ""
        if line_key in found:
            val = getattr(data, key_to_field[line_key], "")
            if val:
                new_lines.append(f"{line_key}={val}\n")
            else:
                new_lines.append(line)
            found[line_key] = True
        else:
            new_lines.append(line)
            
    for k, is_found in found.items():
        if not is_found:
            val = getattr(data, key_to_field[k], "")
            if val:
                new_lines.append(f"{k}={val}\n")
        
    with open(env_path, "w") as f:
        f.writelines(new_lines)
        
    # Update current runtime env
    for k, field in key_to_field.items():
        val = getattr(data, field, "")
        if val:
            os.environ[k] = val
    
    return {"status": "success"}

@app.get("/api/workflow")
async def load_workflow(name: str = "drawflow"):
    file_path = f"config/workflows/{name}.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return None

@app.get("/api/workflows")
async def list_workflows():
    os.makedirs("config/workflows", exist_ok=True)
    files = [f.replace(".json", "") for f in os.listdir("config/workflows") if f.endswith(".json")]
    return {"workflows": files}

class WorkflowSaveRequest(BaseModel):
    name: str
    data: dict

@app.post("/api/workflow")
async def save_workflow(req: WorkflowSaveRequest):
    try:
        os.makedirs("config/workflows", exist_ok=True)
        file_path = f"config/workflows/{req.name}.json"
        
        # Write robustly
        data_str = json.dumps(req.data, indent=2)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data_str)
            f.flush()
            os.fsync(f.fileno())
            
        print(f"Saved workflow {req.name} with {len(data_str)} bytes.")
        return {"status": "success", "bytes": len(data_str)}
    except Exception as e:
        print(f"Error saving workflow: {e}")
        return {"status": "error", "message": str(e)}

# --- ARCHITECT STATE FOR REAL-TIME GRAPH MANIPULATION ---
# When Architect runs, we store its current graph here so tools can read/modify it.
current_architect_graph = {"nodes": [], "connections": []}

@app.get("/api/architect/graph")
async def get_architect_graph():
    return current_architect_graph

@app.post("/api/architect/graph")
async def update_architect_graph(req: dict):
    global current_architect_graph
    current_architect_graph = req
    return {"status": "success"}

class ArchitectActionRequest(BaseModel):
    action: str
    params: dict

@app.post("/api/architect/action")
async def architect_action(req: ArchitectActionRequest):
    """
    Direct graph manipulation endpoints similar to the Android tools:
    AddNode, RemoveNode, ConnectNodes, ClearProject
    """
    global current_architect_graph
    
    if req.action == "ClearProject":
        current_architect_graph = {"nodes": [], "connections": []}
        return {"status": "success", "message": "Project cleared."}
        
    elif req.action == "AddNode":
        # params: id, type, title, x, y, config
        node_id = req.params.get("id")
        if not node_id:
            # Generate new max ID
            existing_ids = [int(n.get("id", 0)) for n in current_architect_graph["nodes"] if str(n.get("id")).isdigit()]
            node_id = str(max(existing_ids + [0]) + 1)
            
        new_node = {
            "id": node_id,
            "type": req.params.get("type", "CODE"),
            "title": req.params.get("title", req.params.get("type", "CODE")),
            "pos_x": req.params.get("x", 100),
            "pos_y": req.params.get("y", 100),
            "config": req.params.get("config", {})
        }
        current_architect_graph["nodes"].append(new_node)
        return {"status": "success", "message": f"Added node {node_id} ({new_node['type']})", "node_id": node_id}
        
    elif req.action == "RemoveNode":
        node_id = str(req.params.get("id"))
        current_architect_graph["nodes"] = [n for n in current_architect_graph["nodes"] if str(n.get("id")) != node_id]
        current_architect_graph["connections"] = [c for c in current_architect_graph["connections"] 
                                                if str(c.get("fromNode")) != node_id and str(c.get("toNode")) != node_id]
        return {"status": "success", "message": f"Removed node {node_id} and its connections."}
        
    elif req.action == "ConnectNodes":
        from_id = str(req.params.get("fromNode"))
        to_id = str(req.params.get("toNode"))
        current_architect_graph["connections"].append({
            "fromNode": from_id,
            "toNode": to_id
        })
        return {"status": "success", "message": f"Connected {from_id} to {to_id}."}
        
    elif req.action == "UpdateNode":
        node_id = str(req.params.get("id"))
        config = req.params.get("config", {})
        for n in current_architect_graph["nodes"]:
            if str(n.get("id")) == node_id:
                if "config" not in n:
                    n["config"] = {}
                n["config"].update(config)
                # CRITICAL: Update top-level fields
                n.update(config)
                if "title" in req.params:
                    n["title"] = req.params["title"]
                return {"status": "success", "message": f"Updated node {node_id}."}
        return {"status": "error", "message": f"Node {node_id} not found."}
        
    return {"status": "error", "message": "Unknown action"}

@app.get("/api/architect/diagnostics")
async def get_flow_diagnostics():
    global current_flow_app
    if not current_flow_app:
        return {"status": "error", "message": "No active flow running."}
        
    nodes = current_flow_app.get_nodes()
    results = []
    for n in nodes:
        results.append({
            "id": n.id,
            "title": n.title,
            "status": n.status.value,
            "lastOutput": n.lastOutput
        })
    return {"status": "success", "diagnostics": results}

class ArchitectRequest(BaseModel):
    prompt: str
    model: str = "qwen/qwen3.6-35b-a3b"
    currentGraph: dict = None

@app.post("/api/architect")
async def architect(req: ArchitectRequest):
    global architect_state, current_architect_graph
    
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {"status": "error", "message": "No API key found for Architect (requires OPENROUTER_API_KEY)."}
    
    # Initialize the graph with the current UI state if provided
    if req.currentGraph:
        current_architect_graph = req.currentGraph
    else:
        current_architect_graph = {"nodes": [], "connections": []}
    
    # Reset architect state and return immediately
    architect_state = {
        "running": True,
        "finished": False,
        "result": None,
        "error": None,
        "drawflow": None,
        "last_action": "Starting..."
    }
    
    # Start architect in background
    asyncio.create_task(run_architect_background(req.prompt, req.model))
    
    return {"status": "running", "message": "Architect started"}

async def run_architect_background(prompt: str, model: str):
    """Run architect in background to avoid proxy timeouts."""
    global architect_state, current_architect_graph
    import traceback
    import json
    from openai import OpenAI
    from src.utils.managers import LogManager
    
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = "https://openrouter.ai/api/v1"
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=45.0)
        
        tools = [
            {"type": "function", "function": {"name": "AddNode", "description": "Adds a new node to the workflow.", "parameters": {"type": "object", "properties": {"id": {"type": "string"}, "type": {"type": "string", "enum": ["TRIGGER", "AI_AGENT", "TOOL_EXECUTION", "ROUTER", "SWITCH", "USER_INPUT", "KNOWLEDGE", "JSON_PARSER", "JSON_FIELD_EXTRACT", "MERGE", "LOOP_OVER_ITEMS", "VARIABLE_STORE", "FILE_SAVE", "STOP_AND_ERROR", "HTTP_REQUEST", "WAIT", "CODE", "SET", "FILTER", "SORT", "LIMIT", "AGGREGATE", "REMOVE_DUPLICATES", "SPLIT_OUT", "SUMMARIZE", "OUTPUT_DISPLAY"]}, "title": {"type": "string"}, "x": {"type": "integer"}, "y": {"type": "integer"}, "config": {"type": "object", "properties": {"userInstruction": {"type": "string"}, "isInteractive": {"type": "boolean"}, "modelId": {"type": "string"}, "systemPrompt": {"type": "string"}, "allowedTools": {"type": "array", "items": {"type": "string"}}, "selectedToolName": {"type": "string"}, "httpUrl": {"type": "string"}, "httpMethod": {"type": "string"}, "ruleCondition": {"type": "string"}, "routerMode": {"type": "string"}, "sortFieldName": {"type": "string"}, "sortOrder": {"type": "string"}, "limitCount": {"type": "integer"}, "mergeMode": {"type": "string"}, "fileName": {"type": "string"}, "waitForAllInputs": {"type": "boolean"}}, "additionalProperties": True}, "required": ["type"]}}}},
            {"type": "function", "function": {"name": "ConnectNodes", "description": "Connects two nodes together.", "parameters": {"type": "object", "properties": {"fromNode": {"type": "string"}, "toNode": {"type": "string"}}, "required": ["fromNode", "toNode"]}}},
            {"type": "function", "function": {"name": "RemoveNode", "description": "Removes a node by its ID.", "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
            {"type": "function", "function": {"name": "RemoveConnection", "description": "Removes a connection between two nodes.", "parameters": {"type": "object", "properties": {"fromNode": {"type": "string"}, "toNode": {"type": "string"}}, "required": ["fromNode", "toNode"]}}},
            {"type": "function", "function": {"name": "UpdateNode", "description": "Updates a node's configuration.", "parameters": {"type": "object", "properties": {"id": {"type": "string"}, "config": {"type": "object", "additionalProperties": True}}, "required": ["id", "config"]}}},
            {"type": "function", "function": {"name": "GetCurrentGraph", "description": "Returns the current nodes and connections in the workflow.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "FinishDesign", "description": "Call this when the workflow is fully built and connected.", "parameters": {"type": "object", "properties": {}}}}
        ]
        
        target_model = model
        if not target_model.startswith("openrouter/") and "/" not in target_model:
            target_model = f"openrouter/{target_model}"
        
        node_descriptions = """
• TRIGGER: Starts workflow. `triggerType` (MANUAL, SCHEDULE, WEBHOOK).
• USER_INPUT: Prompts user or injects text. `userInstruction` (the prompt text), `isInteractive` (boolean).
• AI_AGENT: Uses LLM. `modelId` (qwen/qwen3.6-35b-a3b), `systemPrompt`, `allowedTools` (List of tool names).
• TOOL_EXECUTION: Runs a tool. `selectedToolName`.
• ROUTER: Splits flow. `routerMode` (AI_LLM, SIMPLE_RULE), `ruleCondition`.
• HTTP_REQUEST: Makes API calls. `httpUrl`, `httpMethod` (GET, POST).
• SET: Adds/modifies fields. `setFields`.
• MERGE: Combines branches. `mergeMode` (APPEND, WAIT, CHOOSE_BRANCH).
• CODE: Runs Python. `codeBody`.
• OUTPUT_DISPLAY: Final node to show results.
"""
        
        system_prompt = f"""You are a master workflow architect. Build or edit workflows step by step using your tools.

CRITICAL RULES:
1. NEVER connect TRIGGER directly to AI_AGENT - use USER_INPUT in between.
2. USER_INPUT: use `userInstruction` for text, `isInteractive` (true only for human pauses).
3. AI_AGENT needs `modelId` ("qwen/qwen3.6-35b-a3b"), `systemPrompt`, and `allowedTools`.
4. Always end with OUTPUT_DISPLAY. Call FinishDesign when done.

You have access to tools to AddNode, UpdateNode, ConnectNodes, and GetCurrentGraph.
If the user asks to modify the workflow, ALWAYS call GetCurrentGraph first to see the current state before making changes, unless you already know it.

NODE CONFIGURATION:
{node_descriptions}
"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history
        for msg in architect_chat_history:
            messages.append(msg)
            
        # Add new prompt
        messages.append({"role": "user", "content": prompt})
        
        loop_count = 0
        MAX_LOOPS = 15
        
        while loop_count < MAX_LOOPS:
            try:
                loop_count += 1
                architect_state["last_action"] = f"Thinking (Loop {loop_count}/{MAX_LOOPS})..."
                LogManager.info("Architect", f"Loop {loop_count} starting...")
                
                resp = client.chat.completions.create(model=target_model, messages=messages, tools=tools)
                message = resp.choices[0].message
                
                if not message.tool_calls:
                    architect_state["last_action"] = "Analyzing feedback..."
                    messages.append({"role": "assistant", "content": message.content or ""})
                    messages.append({"role": "user", "content": "Please continue building or call FinishDesign if you are done."})
                    continue
                
                clean_msg = {"role": "assistant", "content": message.content or "", "tool_calls": message.model_dump(exclude_unset=True).get("tool_calls")}
                messages.append(clean_msg)
                
                finished = False
                
                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                    except:
                        args = {}
                    
                    result_str = ""
                    
                    if name == "AddNode":
                        node_id = args.get("id")
                        if not node_id:
                            existing_ids = [int(n.get("id", 0)) for n in current_architect_graph["nodes"] if str(n.get("id")).isdigit()]
                            node_id = str(max(existing_ids + [0]) + 1)
                        
                        config = args.get("config", {})
                        for bool_field in ["isInteractive", "waitForAllInputs", "continueOnError"]:
                            if bool_field in config and isinstance(config[bool_field], str):
                                config[bool_field] = config[bool_field].lower() == "true"
                        
                        new_node = {"id": node_id, "type": args.get("type", "CODE"), "title": args.get("title", args.get("type", "CODE")), "pos_x": args.get("x", 100), "pos_y": args.get("y", 100), "config": config}
                        new_node.update(config)
                        current_architect_graph["nodes"].append(new_node)
                        result_str = f"Added node {node_id}"
                        architect_state["last_action"] = f"Added: {new_node['type']}"
                        LogManager.info("Architect", result_str)
                        
                    elif name == "ConnectNodes":
                        current_architect_graph["connections"].append({"fromNode": str(args.get("fromNode")), "toNode": str(args.get("toNode"))})
                        result_str = f"Connected {args.get('fromNode')} to {args.get('toNode')}"
                        architect_state["last_action"] = result_str
                        LogManager.info("Architect", result_str)
                        
                    elif name == "RemoveNode":
                        node_id = str(args.get("id"))
                        current_architect_graph["nodes"] = [n for n in current_architect_graph["nodes"] if str(n.get("id")) != node_id]
                        current_architect_graph["connections"] = [c for c in current_architect_graph["connections"] if str(c.get("fromNode")) != node_id and str(c.get("toNode")) != node_id]
                        result_str = f"Removed node {node_id} and its connections."
                        architect_state["last_action"] = result_str
                        LogManager.info("Architect", result_str)

                    elif name == "RemoveConnection":
                        from_id = str(args.get("fromNode"))
                        to_id = str(args.get("toNode"))
                        current_architect_graph["connections"] = [c for c in current_architect_graph["connections"] if not (str(c.get("fromNode")) == from_id and str(c.get("toNode")) == to_id)]
                        result_str = f"Removed connection from {from_id} to {to_id}."
                        architect_state["last_action"] = result_str
                        LogManager.info("Architect", result_str)
                        
                    elif name == "UpdateNode":
                        node_id = str(args.get("id"))
                        config = args.get("config", {})
                        for bool_field in ["isInteractive", "waitForAllInputs", "continueOnError"]:
                            if bool_field in config and isinstance(config[bool_field], str):
                                config[bool_field] = config[bool_field].lower() == "true"
                        
                        for n in current_architect_graph["nodes"]:
                            if str(n.get("id")) == node_id:
                                if "config" not in n:
                                    n["config"] = {}
                                n["config"].update(config)
                                n.update(config)
                                result_str = f"Updated node {node_id}"
                                architect_state["last_action"] = f"Updated: {node_id}"
                                LogManager.info("Architect", result_str)
                                break
                        else:
                            result_str = f"Node {node_id} not found"
                            
                    elif name == "GetCurrentGraph":
                        result_str = json.dumps(current_architect_graph)
                        architect_state["last_action"] = "Inspecting graph..."
                        
                    elif name == "FinishDesign":
                        finished = True
                        result_str = "Design finished."
                        architect_state["last_action"] = "Finished!"
                        LogManager.info("Architect", "FinishDesign called")
                    
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_str, "name": name})
                
                if finished:
                    break
                    
                await asyncio.sleep(1)
                
            except Exception as te:
                LogManager.error("Architect", f"Error: {str(te)}")
                architect_state["error"] = str(te)
                architect_state["running"] = False
                return
        
        # Convert to Drawflow format
        df_data = {}
        id_map = {}
        numeric_id_counter = 1
        
        for n in current_architect_graph["nodes"]:
            old_id = str(n["id"])
            if not old_id.isdigit():
                id_map[old_id] = str(numeric_id_counter)
                numeric_id_counter += 1
            else:
                id_map[old_id] = old_id
                numeric_id_counter = max(numeric_id_counter, int(old_id) + 1)
        
        for n in current_architect_graph["nodes"]:
            old_id = str(n["id"])
            nid = id_map[old_id]
            ntype = n["type"]
            html_content = f"<div class='title-box'>{ntype}</div><div class='box'>Auto-generated</div>"
            config_data = n.get("config", {})
            node_data_obj = {"type": ntype, "config": config_data}
            node_data_obj.update(config_data)
            
            df_data[nid] = {
                "id": int(nid), "name": ntype, "data": node_data_obj, "class": ntype.lower(),
                "html": html_content, "typenode": False, "inputs": {}, "outputs": {},
                "pos_x": n.get("pos_x", 100), "pos_y": n.get("pos_y", 100)
            }
            if ntype != "TRIGGER":
                df_data[nid]["inputs"]["input_1"] = {"connections": []}
            df_data[nid]["outputs"]["output_1"] = {"connections": []}
        
        for c in current_architect_graph["connections"]:
            from_id_raw = str(c.get("fromNode"))
            to_id_raw = str(c.get("toNode"))
            from_id = id_map.get(from_id_raw)
            to_id = id_map.get(to_id_raw)
            
            if from_id and to_id and from_id in df_data and to_id in df_data:
                df_data[from_id]["outputs"]["output_1"]["connections"].append({"node": to_id, "output": "input_1"})
                if "input_1" not in df_data[to_id]["inputs"]:
                    df_data[to_id]["inputs"]["input_1"] = {"connections": []}
                df_data[to_id]["inputs"]["input_1"]["connections"].append({"node": from_id, "input": "output_1"})
        
        drawflow_export = {"drawflow": {"Home": {"data": df_data}}}
        
        architect_state["finished"] = True
        architect_state["running"] = False
        architect_state["drawflow"] = drawflow_export
        architect_state["last_action"] = "Done!"
        LogManager.info("Architect", "Design complete!")
        
        # Save to history
        architect_chat_history.extend(messages[len(architect_chat_history) + 1:])
        
    except Exception as e:
        LogManager.error("Architect", f"Architect error: {str(e)}")
        architect_state["error"] = str(e)
        architect_state["running"] = False
        architect_state["finished"] = True

@app.get("/api/architect/results")
async def get_architect_results():
    """Poll for architect execution results."""
    global architect_state
    return architect_state

@app.get("/api/tools")
async def get_tools():
    from src.logic.tools import ToolRegistry
    return {"tools": ToolRegistry.get_available_tools()}

@app.get("/api/debug")
async def debug_info():
    """Debug endpoint to check environment and MCP status."""
    import traceback
    from src.logic.tools import ToolRegistry
    from src.logic.mcp_client import NativeMcpClient
    
    mcp = NativeMcpClient()
    
    # Try to get Brave Search tools
    brave_tools = []
    try:
        config = ToolRegistry._load_mcp_config()
        brave_config = config.get("Brave Search", {})
        if brave_config and not brave_config.get("disabled", False):
            success = mcp.start_server("Brave Search", brave_config)
            if success:
                brave_tools = mcp.get_tools("Brave Search")
    except Exception as e:
        brave_tools = [f"Error: {str(e)}"]
    
    return {
        "env_keys": {
            "OPENROUTER_API_KEY": bool(os.getenv("OPENROUTER_API_KEY")),
            "BRAVE_API_KEY": bool(os.getenv("BRAVE_API_KEY")),
        },
        "mcp_servers": list(ToolRegistry._load_mcp_config().keys()),
        "brave_tools": brave_tools,
        "python_version": sys.version,
        "cwd": os.getcwd(),
    }

@app.get("/api/test-tool")
async def test_tool():
    """Test Brave Search tool directly."""
    try:
        from src.logic.tools import ToolRegistry
        result = ToolRegistry.execute_tool("mcp__Brave Search", {
            "mcp_tool_name": "brave_web_search",
            "mcp_tool_args": {"query": "test"}
        })
        return {"success": True, "result": str(result)[:500]}
    except Exception as e:
        return {"success": False, "error": str(e), "trace": traceback.format_exc()}

@app.post("/api/run")
async def run_flow(project_data: FlowProjectData):
    global current_flow_app
    import time
    import traceback
    import asyncio
    
    try:
        flow_app = FlowApp(project_data)
        current_flow_app = flow_app
        
        asyncio.create_task(run_flow_background(flow_app))
        
        return {
            "status": "running", 
            "message": "Flow started"
        }
    except Exception as e:
        LogManager.error("API", f"Error executing flow: {str(e)}\n{traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e)
        }

async def run_flow_background(flow_app):
    """Run flow in background to avoid proxy timeouts."""
    import time
    try:
        await flow_app.orchestrator.start_flow()
        
        timeout = 300
        start_time = time.time()
        
        while flow_app.orchestrator.is_flow_running and time.time() - start_time < timeout:
            await asyncio.sleep(0.5)
            
        if flow_app.orchestrator.is_flow_running:
            flow_app.orchestrator.stop_flow()
            flow_app.orchestrator.execution_logs.append("Execution timed out.")
    except Exception as e:
        import traceback
        flow_app.orchestrator.execution_logs.append(f"Error: {str(e)}")
        LogManager.error("Flow", f"Flow error: {str(e)}\n{traceback.format_exc()}")

@app.get("/api/results")
async def get_results():
    global current_flow_app
    
    if not current_flow_app:
        return {"status": "error", "error": "No flow running"}
    
    nodes = current_flow_app.get_nodes()
    connections = current_flow_app.get_connections()
    
    sorted_nodes = []
    start_nodes = [n for n in nodes if not any(c.toNodeId == n.id for c in connections)]
    visited = set()
    
    def visit(node_id):
        if node_id in visited:
            return
        visited.add(node_id)
        node = next((n for n in nodes if n.id == node_id), None)
        if node:
            sorted_nodes.append(node)
            children = [c.toNodeId for c in connections if c.fromNodeId == node_id]
            for child_id in children:
                visit(child_id)
                
    for start_node in start_nodes:
        visit(start_node.id)
        
    for n in nodes:
        if n.id not in visited:
            sorted_nodes.append(n)
            
    results = [{
        "id": n.id,
        "title": n.title,
        "status": n.status.value,
        "lastOutput": n.lastOutput,
        "lastInputItems": [item.json_data for item in n.lastInputItems],
        "lastOutputItems": [item.json_data for item in n.lastOutputItems]
    } for n in sorted_nodes]
    
    return {
        "status": "success" if not current_flow_app.orchestrator.is_flow_stuck else "timeout",
        "running": current_flow_app.orchestrator.is_flow_running,
        "logs": current_flow_app.orchestrator.execution_logs,
        "results": results
    }

if __name__ == "__main__":
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)
