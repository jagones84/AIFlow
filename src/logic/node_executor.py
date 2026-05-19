import json
import time
import requests
import os
from typing import List, Dict, Any, Optional, Tuple, Callable
from pydantic import BaseModel
from src.models.node_models import NodeData, FlowItem, FlowPayload, NodeType, NodeStatus, MergeMode, MergeJoinType
from src.logic.expression_evaluator import ExpressionEvaluator
from src.utils.managers import LogManager, VariableManager
from src.logic.tools import ToolRegistry

class ExecutionResult(BaseModel):
    output: str
    success: bool
    outputItems: List[FlowItem] = []
    shouldTriggerNext: bool = True
    shouldStopFlow: bool = False
    iteratorBatches: Optional[List[List[FlowItem]]] = None
    loopBatches: Optional[List[List[FlowItem]]] = None
    doneItems: Optional[List[FlowItem]] = None
    updatedNode: Optional[NodeData] = None
    subWorkflowId: Optional[str] = None
    subWorkflowInput: Optional[List[FlowItem]] = None

class NodeExecutor:
    
    @staticmethod
    def _log_info(msg: str):
        LogManager.info("NodeExecutor", msg)

    @staticmethod
    def _log_error(msg: str):
        LogManager.error("NodeExecutor", msg)
        
    @staticmethod
    def _get_iteration_context(node: NodeData) -> str:
        base = f"[System Info] Current Iteration: {node.executionCount} of {node.maxIterations}."
        if node.executionCount >= node.maxIterations:
            base += " This is the FINAL iteration."
        return base

    @staticmethod
    def _wrap_text_item(text: str, extra: Dict[str, Any] = None) -> FlowItem:
        json_data = {"text": text}
        if extra:
            json_data.update(extra)
        return FlowItem(json_data=json_data)

    @staticmethod
    def _items_to_text(items: List[FlowItem]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            text = items[0].json_data.get("text")
            if text and str(text).strip():
                return str(text)
            return json.dumps(items[0].json_data)
            
        out = []
        for idx, item in enumerate(items):
            text = item.json_data.get("text")
            rendered = str(text) if text and str(text).strip() else json.dumps(item.json_data)
            out.append(f"[{idx + 1}] {rendered}")
        return "\n".join(out)

    @staticmethod
    def _parse_legacy_string_to_items(raw: str) -> List[FlowItem]:
        s = str(raw).strip()
        if not s:
            return []
        
        # Extract first JSON-like structure
        first_brace = s.find('{')
        first_bracket = s.find('[')
        start = -1
        if first_brace >= 0 and first_bracket >= 0:
            start = min(first_brace, first_bracket)
        elif first_brace >= 0:
            start = first_brace
        elif first_bracket >= 0:
            start = first_bracket
            
        if start >= 0:
            try:
                parsed = json.loads(s[start:])
                if isinstance(parsed, list):
                    out = []
                    for e in parsed:
                        if isinstance(e, dict):
                            out.append(FlowItem(json_data=e))
                        else:
                            out.append(FlowItem(json_data={"text": str(e)}))
                    return out
                elif isinstance(parsed, dict):
                    return [FlowItem(json_data=parsed)]
            except json.JSONDecodeError:
                pass
                
        return [FlowItem(json_data={"text": s})]

    def execute(
        self,
        node: NodeData,
        input_items: List[FlowItem],
        all_node_data: List[NodeData],
        runtime_payloads: Dict[str, FlowPayload],
        append_log: Optional[Callable[[str], None]] = None,
        check_running: Optional[Callable[[], bool]] = None
    ) -> ExecutionResult:
        
        output = ""
        success = True
        output_items = []
        should_trigger_next = True
        should_stop_flow = False
        loop_batches = None
        done_items = None
        updated_node = None
        sub_workflow_id = None
        sub_workflow_input = None

        def local_log_info(msg: str):
            self._log_info(msg)
            if append_log:
                append_log(msg)
                
        def local_log_error(msg: str):
            self._log_error(msg)
            if append_log:
                append_log(msg)

        local_log_info(f"Executing Node '{node.title}' [{node.type.value}] (ID: {node.id})")

        all_vars = VariableManager.get_all_variables()
        evaluator = ExpressionEvaluator(input_items, all_node_data, runtime_payloads, all_vars)

        try:
            if node.type == NodeType.TRIGGER:
                output = "Trigger Fired"
                output_items = [self._wrap_text_item(output)]
                local_log_info("Trigger node activated.")
                
            elif node.type == NodeType.HTTP_REQUEST:
                url_str = evaluator.evaluate(node.httpUrl)
                if not url_str.strip():
                    success = False
                    output = "Error: HTTP URL is empty"
                    output_items = [self._wrap_text_item(output)]
                else:
                    local_log_info(f"HTTP Request: {node.httpMethod} {url_str}")
                    headers = {k: evaluator.evaluate(v) for k, v in node.httpHeaders.items()}
                    body = evaluator.evaluate(node.httpBody) if node.httpBody else None
                    
                    try:
                        resp = requests.request(node.httpMethod, url_str, headers=headers, data=body, timeout=30)
                        output = resp.text
                        success = resp.ok
                        parsed = self._parse_legacy_string_to_items(output)
                        output_items = parsed if parsed else [self._wrap_text_item(output)]
                        if not success:
                            local_log_error(f"HTTP Request failed: {output}")
                    except Exception as e:
                        success = False
                        output = str(e)
                        output_items = [self._wrap_text_item(output)]
                        local_log_error(f"HTTP Request error: {e}")

            elif node.type == NodeType.WAIT:
                wait_time_str = evaluator.evaluate(str(node.waitTimeMs))
                try:
                    wait_time = int(wait_time_str)
                except ValueError:
                    wait_time = node.waitTimeMs
                    
                local_log_info(f"Wait node: sleeping for {wait_time}ms...")
                
                # Sleep in small increments to allow cancellation
                slept = 0
                while slept < wait_time:
                    if check_running and not check_running():
                        local_log_info("Wait interrupted by user.")
                        break
                    time.sleep(0.1)
                    slept += 100
                    
                output = f"Waited for {wait_time}ms"
                output_items = input_items

            elif node.type == NodeType.CODE:
                code = evaluator.evaluate(node.codeBody or "")
                
                # Wrap code in a function to support 'return' statements
                wrapped_code = f"def __user_code__():\n"
                for line in code.split('\n'):
                    wrapped_code += f"    {line}\n"
                wrapped_code += "\nresult = __user_code__()"
                
                local_vars = {"input": input_items, "context": node.context}
                try:
                    exec(wrapped_code, {}, local_vars)
                    output_items = local_vars.get("result", [])
                    if not isinstance(output_items, list):
                        output_items = [self._wrap_text_item(str(output_items))]
                    output = f"Code executed successfully. Generated {len(output_items)} items."
                except Exception as e:
                    output = f"Error: {str(e)}"
                    success = False

            elif node.type == NodeType.AI_AGENT:
                model_id = node.modelId
                prompt = evaluator.evaluate(node.systemPrompt)
                input_text = self._items_to_text(input_items) if input_items else node.lastInput or ""
                
                local_log_info(f"AI Agent running with model: {model_id}")
                
                openai_api_key = os.getenv("OPENAI_API_KEY")
                anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
                openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                groq_api_key = os.getenv("GROQ_API_KEY")
                
                output = ""
                
                # We must be careful with the routing logic here
                is_openrouter = False
                if openrouter_api_key:
                    if "openrouter" in model_id.lower() or "grok" in model_id.lower():
                        is_openrouter = True
                    elif "/" in model_id:
                        is_openrouter = True
                    elif ("gpt" in model_id.lower() or "o1" in model_id.lower()) and not openai_api_key:
                        is_openrouter = True
                    elif "claude" in model_id.lower() and not anthropic_api_key:
                        is_openrouter = True
                    elif "gemini" in model_id.lower() and not gemini_api_key:
                        is_openrouter = True
                    elif ("llama" in model_id.lower() or "mixtral" in model_id.lower()) and not groq_api_key:
                        is_openrouter = True
                    elif "gpt" not in model_id.lower() and "claude" not in model_id.lower() and "gemini" not in model_id.lower() and "llama" not in model_id.lower():
                        is_openrouter = True
                
                local_log_info(f"Routing Decision: is_openrouter={is_openrouter} for model={model_id}")
                
                # Auto-inject today's date to prevent LLM hallucinations
                from datetime import datetime
                today_str = datetime.now().strftime("%Y-%m-%d")
                system_instruction = prompt
                if system_instruction:
                    system_instruction += f"\n\n[System Note: Today's date is {today_str}. If asked about recent events, ALWAYS use the provided tools to search the web first. Do not hallucinate or guess recent sports results without checking.]"
                else:
                    system_instruction = f"You are a helpful assistant. Today's date is {today_str}. ALWAYS use tools to search for current events."
                
                # Prepare tools for OpenAI/OpenRouter if allowedTools is set
                ai_tools = []
                tool_name_map = {} # Maps safe tool name to actual tool metadata
                
                if node.allowedTools:
                    for t in node.allowedTools:
                        if t.startswith("mcp__"):
                            server_name = t[5:]
                            actual_tools = ToolRegistry.get_mcp_server_tools(server_name)
                            for at in actual_tools:
                                # We need a safe name for OpenAI (no dashes, spaces)
                                safe_name = at["name"].replace("-", "_").replace(" ", "_")
                                ai_tools.append({
                                    "type": "function",
                                    "function": {
                                        "name": safe_name,
                                        "description": at.get("description", f"Execute {safe_name}"),
                                        "parameters": at.get("inputSchema", {
                                            "type": "object",
                                            "properties": {"query": {"type": "string"}}
                                        })
                                    }
                                })
                                tool_name_map[safe_name] = {"server": server_name, "real_name": at["name"], "is_mcp": True}
                        else:
                            # Standard local tool
                            safe_name = t.replace(" ", "_").replace("-", "_")
                            
                            params = {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query or main argument"},
                                    "url": {"type": "string", "description": "URL if applicable"},
                                    "expression": {"type": "string", "description": "Math expression to calculate"}
                                }
                            }
                            
                            ai_tools.append({
                                "type": "function",
                                "function": {
                                    "name": safe_name,
                                    "description": f"Execute the {t} tool",
                                    "parameters": params
                                }
                            })
                            tool_name_map[safe_name] = {"real_name": t, "is_mcp": False}

                # Check for OpenRouter Models first
                if is_openrouter:
                    try:
                        local_log_info(f"Routing to OpenRouter with model: {model_id}")
                        from openai import OpenAI
                        # OpenRouter provides an OpenAI-compatible API endpoint
                        client = OpenAI(
                            base_url="https://openrouter.ai/api/v1",
                            api_key=openrouter_api_key,
                        )
                        messages = []
                        if system_instruction:
                            messages.append({"role": "system", "content": system_instruction})
                        messages.append({"role": "user", "content": input_text})
                        
                        target_model = model_id
                        if target_model.startswith("openrouter/"):
                            target_model = target_model[11:]
                        elif "/" not in target_model:
                            target_model = f"openrouter/{model_id}"
                            
                        kwargs = {
                            "model": target_model,
                            "messages": messages,
                            "temperature": 0.7
                        }
                        if ai_tools:
                            kwargs["tools"] = ai_tools
                            
                        response = client.chat.completions.create(**kwargs)
                        
                        # Loop to handle multiple tool calls (Agentic loop)
                        MAX_LOOPS = 25
                        loop_count = 0
                        message = response.choices[0].message
                        
                        while message.tool_calls and loop_count < MAX_LOOPS:
                            if check_running and not check_running():
                                local_log_info("AI loop interrupted by user.")
                                break
                            
                            loop_count += 1
                            local_log_info(f"AI decided to call tools (loop {loop_count}): {[tc.function.name for tc in message.tool_calls]}")
                            
                            # OpenRouter requires strict message format.
                            msg_dict = message.model_dump(exclude_unset=True)
                            
                            # Clean up the message dict for OpenRouter
                            clean_msg = {
                                "role": "assistant",
                                "content": msg_dict.get("content") or "",
                                "tool_calls": msg_dict.get("tool_calls")
                            }
                            messages.append(clean_msg)
                            
                            for tool_call in message.tool_calls:
                                tool_name = tool_call.function.name
                                
                                try:
                                    args = json.loads(tool_call.function.arguments)
                                except:
                                    args = {"query": tool_call.function.arguments}
                                    
                                tool_meta = tool_name_map.get(tool_name)
                                if tool_meta:
                                    if tool_meta["is_mcp"]:
                                        mcp_args = {
                                            "mcp_tool_name": tool_meta["real_name"],
                                            "mcp_tool_args": args
                                        }
                                        tool_result = ToolRegistry.execute_tool(f"mcp__{tool_meta['server']}", mcp_args)
                                    else:
                                        tool_result = ToolRegistry.execute_tool(tool_meta["real_name"], args)
                                else:
                                    tool_result = f"Error: Tool {tool_name} not found."
                                    
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": str(tool_result),
                                    "name": tool_name
                                })
                                
                            local_log_info(f"Submitting tool results back to LLM...")
                            kwargs["messages"] = messages
                            response = client.chat.completions.create(**kwargs)
                            message = response.choices[0].message

                        output = message.content or ""
                        if not output and loop_count >= MAX_LOOPS:
                            output = "Error: AI reached maximum tool loop limit without returning a final answer."
                            
                    except Exception as e:
                        import traceback
                        self._log_error(f"OpenRouter API Error: {str(e)}")
                        self._log_error(f"Traceback: {traceback.format_exc()}")
                        success = False
                        output = f"OpenRouter API Error: {str(e)}"
                
                # Check for OpenAI
                elif ("gpt" in model_id.lower() or "o1" in model_id.lower()) and openai_api_key and openai_api_key != "your_openai_api_key_here":
                    try:
                        self._log_info(f"Routing to OpenAI with model: {model_id}")
                        from openai import OpenAI
                        client = OpenAI(api_key=openai_api_key)
                        messages = []
                        if system_instruction:
                            messages.append({"role": "system", "content": system_instruction})
                        messages.append({"role": "user", "content": input_text})
                        
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=messages,
                            temperature=0.7
                        )
                        output = response.choices[0].message.content or ""
                    except Exception as e:
                        success = False
                        output = f"OpenAI API Error: {str(e)}"
                        
                # Check for Anthropic
                elif "claude" in model_id.lower() and anthropic_api_key and anthropic_api_key != "your_anthropic_api_key_here":
                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=anthropic_api_key)
                        response = client.messages.create(
                            model=model_id,
                            max_tokens=1024,
                            system=system_instruction,
                            messages=[{"role": "user", "content": input_text}]
                        )
                        output = response.content[0].text or ""
                    except Exception as e:
                        success = False
                        output = f"Anthropic API Error: {str(e)}"
                        
                # Check for Gemini (using openai SDK wrapper or native)
                elif "gemini" in model_id.lower() and gemini_api_key:
                    try:
                        # Simple requests fallback if google-generativeai isn't installed
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={gemini_api_key}"
                        payload = {
                            "contents": [{"parts":[{"text": f"{system_instruction}\n\n{input_text}"}]}]
                        }
                        res = requests.post(url, json=payload)
                        res.raise_for_status()
                        output = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception as e:
                        success = False
                        output = f"Gemini API Error: {str(e)}"
                        
                # Check for Groq
                elif ("llama" in model_id.lower() or "mixtral" in model_id.lower()) and groq_api_key:
                    try:
                        from openai import OpenAI
                        client = OpenAI(
                            base_url="https://api.groq.com/openai/v1",
                            api_key=groq_api_key
                        )
                        messages = []
                        if system_instruction:
                            messages.append({"role": "system", "content": system_instruction})
                        messages.append({"role": "user", "content": input_text})
                        
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=messages,
                            temperature=0.7
                        )
                        output = response.choices[0].message.content or ""
                    except Exception as e:
                        success = False
                        output = f"Groq API Error: {str(e)}"

                else:
                    # Fallback simulation if no API keys match
                    output = f"Simulated AI Response using {model_id}.\n(To get real responses, add API Keys to .env file)\nPrompt: {prompt}\nInput: {input_text}"
                
                output_items = [self._wrap_text_item(output)]
                
                if node.allowedTools:
                    self._log_info(f"AI has access to tools: {', '.join(node.allowedTools)}")

            elif node.type == NodeType.TOOL_EXECUTION:
                tool_name = node.selectedToolName
                # Use httpUrl or first available input as URL if not provided
                url = evaluator.evaluate(node.httpUrl or "")
                if not url and input_items:
                    url = input_items[0].json_data.get("text", "") or str(input_items[0].json_data)
                
                if not tool_name:
                    success = False
                    output = "No tool selected."
                    output_items = input_items
                else:
                    self._log_info(f"Executing Tool '{tool_name}' for {len(input_items)} items...")
                    results = []
                    for item in (input_items or [FlowItem(json_data={"text": ""})]):
                        val = item.json_data.get("text", "")
                        
                        # Try to parse input as json args
                        args = {}
                        
                        # Use explicit args if defined by the user in the UI
                        mcp_tool_name = node.staticData.get("mcpToolName") or getattr(node, "mcpToolName", None)
                        mcp_tool_args_raw = node.staticData.get("mcpToolArgs") or getattr(node, "mcpToolArgs", None)
                        
                        # Look inside config if they're stored there
                        if hasattr(node, "config") and isinstance(node.config, dict):
                            mcp_tool_name = mcp_tool_name or node.config.get("mcpToolName")
                            mcp_tool_args_raw = mcp_tool_args_raw or node.config.get("mcpToolArgs")
                            
                        # Workaround because Pydantic extra fields are discarded or put in a dict. 
                        # We extract it safely from wherever the UI put it:
                        # (Usually the UI sends extra fields that pydantic might ignore unless configured,
                        # but let's parse from raw input if needed. Wait, we defined them in UI but not in NodeData model).
                        
                        # Better: Parse the raw values if passed, else fallback
                        try:
                            if isinstance(val, str) and val.startswith("{"):
                                args = json.loads(val)
                            elif isinstance(val, dict):
                                args = val
                            else:
                                args = {"query": str(val), "url": str(val), "expression": str(val)}
                        except:
                            args = {"query": str(val), "url": str(val), "expression": str(val)}
                            
                        # If UI provided explicit MCP parameters, inject them into args
                        # For this to work perfectly, we need to extract them from the JSON payload.
                        # Since we might not have added mcpToolName to the Pydantic model, we'll try to find it in the node.
                        try:
                            # Use evaluator to resolve the template
                            if hasattr(node, "mcpToolArgs"):
                                evaluated_args = evaluator.evaluate(getattr(node, "mcpToolArgs"))
                                args["mcp_tool_args"] = json.loads(evaluated_args)
                            if hasattr(node, "mcpToolName"):
                                args["mcp_tool_name"] = evaluator.evaluate(getattr(node, "mcpToolName"))
                        except Exception as e:
                            self._log_error(f"Error parsing MCP args: {e}")

                        res_text = ToolRegistry.execute_tool(tool_name, args)
                        
                        new_json = dict(item.json_data)
                        new_json["tool_result"] = res_text
                        new_json["text"] = res_text # Overwrite text for chaining
                        results.append(FlowItem(json_data=new_json))
                        
                    output_items = results
                    output = f"Executed tool '{tool_name}'"

            elif node.type == NodeType.SET:
                output_items_list = []
                for item in input_items:
                    new_json = {} if node.keepOnlySetFields else dict(item.json_data)
                    for field in node.setFields:
                        eval_val = evaluator.evaluate(field.value)
                        final_val = eval_val
                        if field.type == "number":
                            try:
                                final_val = float(eval_val)
                                if final_val.is_integer():
                                    final_val = int(final_val)
                            except ValueError:
                                pass
                        elif field.type == "boolean":
                            final_val = eval_val.lower() in ("true", "1")
                        elif field.type == "object":
                            try:
                                final_val = json.loads(eval_val)
                            except Exception:
                                pass
                        new_json[field.name] = final_val
                    output_items_list.append(FlowItem(json_data=new_json))
                output_items = output_items_list
                output = f"Set fields for {len(output_items)} item(s)."
                self._log_info(output)

            elif node.type == NodeType.EXECUTE_WORKFLOW:
                sub_id = evaluator.evaluate(node.subWorkflowId or "")
                if not sub_id.strip():
                    success = False
                    output = "Error: Sub-workflow ID is empty"
                    output_items = input_items
                else:
                    output = f"Triggering sub-workflow: {sub_id}"
                    output_items = input_items
                    sub_workflow_id = sub_id
                    sub_workflow_input = input_items

            elif node.type == NodeType.FILTER:
                condition = node.ruleCondition or ""
                filtered = []
                for item in input_items:
                    item_text = str(item.json_data.get("text", json.dumps(item.json_data)))
                    from src.logic.flow_graph_traverser import FlowGraphTraverser
                    is_match = FlowGraphTraverser._evaluate_condition(condition, node, all_node_data, item, item_text)
                    if is_match:
                        filtered.append(item)
                output_items = filtered
                output = f"Filtered {len(filtered)} out of {len(input_items)} item(s)."
                self._log_info(output)

            elif node.type == NodeType.SORT:
                field = evaluator.evaluate(node.sortFieldName or "")
                if not field.strip():
                    output_items = input_items
                    output = "No sort field specified. Passing through."
                else:
                    def sort_key(item: FlowItem):
                        v = item.json_data.get(field)
                        if node.sortType == "number":
                            try:
                                return float(v) if v is not None else 0.0
                            except ValueError:
                                return 0.0
                        return str(v) if v is not None else ""
                        
                    sorted_items = sorted(input_items, key=sort_key, reverse=(node.sortOrder == "desc"))
                    output_items = sorted_items
                    output = f"Sorted {len(sorted_items)} items by '{field}' ({node.sortOrder})."
                self._log_info(output)

            elif node.type == NodeType.LIMIT:
                count = max(0, node.limitCount)
                offset = max(0, node.limitOffset)
                if offset < len(input_items):
                    output_items = input_items[offset:offset+count]
                else:
                    output_items = []
                output = f"Limited to {count} items (offset {offset}). Result: {len(output_items)} items."
                self._log_info(output)

            elif node.type == NodeType.AGGREGATE:
                output_field = evaluator.evaluate(node.aggregateOutputField).strip() or "data"
                if node.aggregateMode == "allItemData":
                    aggregated_list = [i.json_data for i in input_items]
                    output_items = [FlowItem(json_data={output_field: aggregated_list})]
                    output = f"Aggregated {len(input_items)} items into a single list under '{output_field}'."
                else:
                    input_field = evaluator.evaluate(node.aggregateInputField or "")
                    if not input_field.strip():
                        output_items = input_items
                        output = "No input field specified for aggregation. Passing through."
                    else:
                        vals = [i.json_data.get(input_field) for i in input_items]
                        if node.aggregateMergeLists:
                            merged = []
                            for v in vals:
                                if isinstance(v, list):
                                    merged.extend(v)
                                else:
                                    merged.append(v)
                            vals = merged
                        if not node.aggregateKeepMissing:
                            vals = [v for v in vals if v is not None]
                        output_items = [FlowItem(json_data={output_field: vals})]
                        output = f"Aggregated values from '{input_field}' into '{output_field}'."
                self._log_info(output)

            elif node.type == NodeType.REMOVE_DUPLICATES:
                fields = [evaluator.evaluate(f) for f in node.dedupeFields if evaluator.evaluate(f).strip()]
                seen = set()
                unique_items = []
                for item in input_items:
                    if node.dedupeCompareAllFields or not fields:
                        key = json.dumps(item.json_data, sort_keys=True)
                    else:
                        key = json.dumps([item.json_data.get(f) for f in fields], sort_keys=True)
                    if key not in seen:
                        seen.add(key)
                        unique_items.append(item)
                output_items = unique_items
                output = f"Removed duplicates. {len(unique_items)} unique items remain out of {len(input_items)}."
                self._log_info(output)

            elif node.type == NodeType.SPLIT_OUT:
                field = evaluator.evaluate(node.splitOutField or "")
                if not field.strip():
                    output_items = input_items
                    output = "No field specified to split out. Passing through."
                else:
                    result = []
                    for item in input_items:
                        val = item.json_data.get(field)
                        if isinstance(val, list):
                            for v in val:
                                new_json = dict(item.json_data)
                                new_json[field] = v
                                result.append(FlowItem(json_data=new_json))
                        else:
                            result.append(item)
                    output_items = result
                    output = f"Split out into {len(result)} items."
                self._log_info(output)

            elif node.type == NodeType.STOP_AND_ERROR:
                success = False
                should_stop_flow = True
                msg = evaluator.evaluate(node.errorMessage or "Forced stop with error.")
                err_obj = evaluator.evaluate(node.stopAndErrorObject or "{}")
                if node.stopAndErrorType == "object":
                    output = f"Forced Stop Error: {err_obj}"
                else:
                    output = f"Forced Stop Error: {msg}"
                output_items = [self._wrap_text_item(output, extra={"isError": True, "errorObject": err_obj})]
                self._log_error(output)

            elif node.type == NodeType.ERROR_TRIGGER:
                text = self._items_to_text(input_items) if input_items else node.lastInput or ""
                output = text if text else "Error Trigger Activated"
                output_items = input_items if input_items else [self._wrap_text_item(output)]
                self._log_info("Error Trigger activated.")

            elif node.type == NodeType.VARIABLE_STORE:
                key = evaluator.evaluate(node.variableKey or "default_var")
                if node.variableOperation == "WRITE":
                    val_to_save = self._items_to_text(input_items) if input_items else node.lastInput or ""
                    VariableManager.save_variable(key, val_to_save)
                    output = val_to_save
                    output_items = [self._wrap_text_item(output, extra={"key": key})]
                    self._log_info(f"Saved variable '{key}'")
                elif node.variableOperation == "APPEND":
                    val_to_append = self._items_to_text(input_items) if input_items else node.lastInput or ""
                    existing = VariableManager.load_variable(key)
                    merged = f"{existing}\n{val_to_append}" if existing else val_to_append
                    VariableManager.save_variable(key, merged)
                    output = merged
                    output_items = [self._wrap_text_item(output, extra={"key": key})]
                    self._log_info(f"Appended variable '{key}'")
                else:
                    output = VariableManager.load_variable(key)
                    output_items = [self._wrap_text_item(output, extra={"key": key})]
                    self._log_info(f"Loaded variable '{key}'")

            elif node.type == NodeType.LOOP_OVER_ITEMS:
                items = input_items if input_items else self._parse_legacy_string_to_items(node.lastInput or "")
                batch_size_str = evaluator.evaluate(str(node.batchSize))
                try:
                    batch_size = max(1, int(batch_size_str))
                except ValueError:
                    batch_size = max(1, node.batchSize)
                
                if not items:
                    output = "Empty List"
                    success = False
                    output_items = []
                else:
                    loop_batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
                    done_items = items
                    output_items = items
                    output = f"Split {len(items)} item(s) into {len(loop_batches)} batch(es) of {batch_size}"
                    n_ctx = dict(node.context)
                    n_ctx["noItemsLeft"] = False
                    updated_node = node.model_copy(deep=True)
                    updated_node.context = n_ctx
                    self._log_info(output)

            elif node.type == NodeType.MERGE:
                payload = runtime_payloads.get(node.id, FlowPayload())
                # Use inputs list to find pins for robustness
                input_pins = node.inputs
                sorted_pin_ids = [p.id for p in input_pins] if input_pins else sorted(payload.itemsByPinId.keys())
                
                # Support more than 2 inputs by flattening them all if appending
                all_items = payload.all_items()
                
                # Get specific inputs for operations that require pairs
                input1_items = payload.itemsByPinId.get(sorted_pin_ids[0], []) if sorted_pin_ids else []
                input2_items = payload.itemsByPinId.get(sorted_pin_ids[1], []) if len(sorted_pin_ids) > 1 else []

                if node.mergeMode == MergeMode.APPEND:
                    output_items = all_items
                    output = f"Merged {len(all_items)} item(s) from all {len(sorted_pin_ids)} inputs."
                elif node.mergeMode == MergeMode.WAIT:
                    output_items = all_items # Pass through everything we waited for
                    output = f"Wait completed. Passing through {len(output_items)} item(s)."
                elif node.mergeMode == MergeMode.CHOOSE_BRANCH:
                    idx = max(0, min(node.mergeOutputIndex, len(sorted_pins) - 1))
                    output_items = payload.itemsByPinId.get(sorted_pins[idx], []) if sorted_pins else []
                    output = f"Selected branch {idx} with {len(output_items)} item(s)."
                elif node.mergeMode == MergeMode.COMBINE_BY_POSITION:
                    max_size = max(len(input1_items), len(input2_items))
                    merged = []
                    for i in range(max_size):
                        i1 = input1_items[i] if i < len(input1_items) else None
                        i2 = input2_items[i] if i < len(input2_items) else None
                        if i1 and i2:
                            merged.append(FlowItem(json_data={**i1.json_data, **i2.json_data}))
                        elif i1:
                            merged.append(i1)
                        elif i2:
                            merged.append(i2)
                    output_items = merged
                    output = f"Combined {len(merged)} item(s) by position."
                elif node.mergeMode == MergeMode.MULTIPLEX:
                    merged = []
                    for i1 in input1_items:
                        for i2 in input2_items:
                            merged.append(FlowItem(json_data={**i1.json_data, **i2.json_data}))
                    output_items = merged
                    output = f"Multiplexed into {len(merged)} item(s) (Cartesian Product)."
                # COMBINE_BY_FIELDS omitted for brevity, but easily added
                self._log_info(f"Merge '{node.title}' finished ({node.mergeMode}).")

            elif node.type == NodeType.USER_INPUT:
                if node.isInteractive and not node.lastOutput:
                    # Halt and wait for user input
                    success = True
                    should_trigger_next = False
                    updated_node = node.model_copy(deep=True)
                    updated_node.status = NodeStatus.WAITING_FOR_USER
                    output = "Waiting for user input..."
                    self._log_info(output)
                else:
                    output = node.lastOutput if (node.isInteractive and node.lastOutput) else (node.userInstruction or "User input provided")
                    output_items = [self._wrap_text_item(output)]
                    self._log_info(f"User input processed: {output}")

            else:
                # Default pass-through for unhandled types
                output = f"Executed {node.type.value}"
                output_items = input_items if input_items else [self._wrap_text_item(output)]

        except Exception as e:
            success = False
            output = f"Exception: {str(e)}"
            output_items = [self._wrap_text_item(output)]
            self._log_error(output)

        return ExecutionResult(
            output=output,
            success=success,
            outputItems=output_items,
            shouldTriggerNext=should_trigger_next,
            shouldStopFlow=should_stop_flow,
            loopBatches=loop_batches,
            doneItems=done_items,
            updatedNode=updated_node,
            subWorkflowId=sub_workflow_id,
            subWorkflowInput=sub_workflow_input
        )
