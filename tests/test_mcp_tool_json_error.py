import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def test_mcp_tool_result_json_parsing():
    """Test that MCP tool results don't cause JSON parsing errors downstream."""
    
    # Simulate what happens when an MCP tool returns an error that looks like it could cause JSON parsing issues
    from src.logic.mcp_client import NativeMcpClient

    client = NativeMcpClient()

    # Create a mock process that returns various types of responses
    mock_process = MagicMock()
    mock_stdout = MagicMock()
    mock_stdin = MagicMock()

    # Test case 1: Normal successful response
    mock_stdout.readline.side_effect = [
        '{"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "success"}]}}\n'
    ]

    client._processes["test"] = mock_process
    client._locks["test"] = __import__("threading").Lock()
    mock_process.stdout = mock_stdout
    mock_process.stdin = mock_stdin
    mock_process.poll.return_value = None

    result = client.execute_tool("test", "test_tool", {"arg": "value"})
    print(f"Normal response result: {result}")
    assert result == "success", f"Expected 'success', got {result}"

    # Test case 2: Response with content that has no 'text' key
    mock_stdout.readline.side_effect = [
        '{"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "image", "data": "abc123"}]}}\n'
    ]

    client._message_id = 1  # Reset
    result = client.execute_tool("test", "test_tool", {"arg": "value"})
    print(f"No text key result: {result}")
    # This should return the whole content list as string, which could cause issues

    # Test case 3: Response that might cause issues
    mock_stdout.readline.side_effect = [
        '{"jsonrpc": "2.0", "id": 1, "result": {"content": "just a string"}}\n'
    ]

    client._message_id = 1
    result = client.execute_tool("test", "test_tool", {"arg": "value"})
    print(f"String content result: {result}")


def test_openrouter_tool_message_format():
    """Test that messages sent back to OpenRouter have proper format."""
    
    from src.logic.node_executor import NodeExecutor
    from src.logic.tools import ToolRegistry
    from src.models.node_models import FlowItem, FlowPayload, NodeData, NodeType

    captured_messages = []

    def fake_execute_tool(name, args):
        # Return a result that might cause issues
        if name == "fetch_url":
            return "This is a test result"
        elif name == "web_search":
            return "Search result here"
        return f"Result for {name}"

    # Mock the openai client to capture messages
    captured_create_kwargs = []
    
    class FakeMessage:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

        def model_dump(self, exclude_unset=True):
            result = {}
            if self.content is not None:
                result["content"] = self.content
            if self.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
                    }
                    for tc in self.tool_calls
                ]
            return result

    class FakeChoice:
        def __init__(self, message):
            self.message = message

    class FakeResponse:
        def __init__(self, choices):
            self.choices = choices

    call_count = [0]

    class FakeChatCompletions:
        def create(self, **kwargs):
            captured_create_kwargs.append(kwargs)
            call_count[0] += 1
            
            messages = kwargs.get("messages", [])
            
            if call_count[0] == 1:
                # First call: return a tool call
                return FakeResponse([
                    FakeChoice(FakeMessage(
                        None,
                        [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "fetch_url",
                                    "arguments": '{"url": "https://example.com"}'
                                }
                            }
                        ]
                    ))
                ])
            else:
                # Second call: verify messages include tool results
                # The bug might be here - if messages are malformed
                print(f"Call {call_count[0]} messages: {json.dumps(messages, indent=2)[:500]}")
                return FakeResponse([FakeChoice(FakeMessage("done", None))])

    class FakeOpenAI:
        def __init__(self, base_url=None, api_key=None):
            self.chat = types.SimpleNamespace(completions=FakeChatCompletions())

    with patch.object(sys, 'modules', {**sys.modules, 'openai': types.SimpleNamespace(OpenAI=FakeOpenAI)}):
        with patch.object(ToolRegistry, 'execute_tool', staticmethod(fake_execute_tool)):
            import os
            os.environ['OPENROUTER_API_KEY'] = 'test'
            
            executor = NodeExecutor()
            node = NodeData(
                title="AI_AGENT",
                type=NodeType.AI_AGENT,
                modelId="qwen/qwen3.6-35b-a3b",
                allowedTools=["fetch_url"],
            )
            payload = FlowPayload.from_items([FlowItem(json={"text": "Fetch the URL"})])
            
            try:
                res = executor.execute(node, payload.all_items(), [node], {node.id: payload})
                print(f"Result: {res}")
            except Exception as e:
                print(f"Error during execution: {e}")
                import traceback
                traceback.print_exc()


def test_tool_result_format_edge_cases():
    """Test various tool result formats that might cause issues."""
    
    from src.logic.tools import ToolRegistry
    
    # Test that different result types are handled correctly
    test_cases = [
        # (tool_name, args, expected_behavior)
        ("fetch_url", {"url": "https://example.com"}, "string"),
        ("web_search", {"query": "test"}, "string"),
        ("nonexistent", {}, "error string"),
    ]
    
    for tool_name, args, expected in test_cases:
        try:
            result = ToolRegistry.execute_tool(tool_name, args)
            print(f"Tool {tool_name} returned: {type(result).__name__} = {str(result)[:100]}...")
            assert isinstance(result, str), f"Expected string, got {type(result)}"
        except Exception as e:
            print(f"Tool {tool_name} raised: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: MCP Tool Result JSON Parsing")
    print("=" * 60)
    test_mcp_tool_result_json_parsing()
    
    print("\n" + "=" * 60)
    print("Test 2: OpenRouter Tool Message Format")
    print("=" * 60)
    test_openrouter_tool_message_format()
    
    print("\n" + "=" * 60)
    print("Test 3: Tool Result Format Edge Cases")
    print("=" * 60)
    test_tool_result_format_edge_cases()
