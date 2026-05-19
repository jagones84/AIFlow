import json
import sys
import types

from src.logic.node_executor import NodeExecutor
from src.logic.tools import ToolRegistry
from src.models.node_models import FlowItem, FlowPayload, NodeData, NodeType


def test_openrouter_tool_loop_includes_tool_results(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    def fake_execute_tool(name, args):
        assert name == "fetch_url"
        assert "url" in args
        return "toolresult"

    monkeypatch.setattr(ToolRegistry, "execute_tool", staticmethod(fake_execute_tool))

    class FakeFunction:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class FakeToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.function = FakeFunction(name, arguments)

    class FakeMessage:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls

        def model_dump(self, exclude_unset=True):
            tool_calls = []
            for tc in self.tool_calls or []:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                )
            return {"content": self.content, "tool_calls": tool_calls or None}

    class FakeResponse:
        def __init__(self, message):
            self.choices = [types.SimpleNamespace(message=message)]

    class FakeChatCompletions:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            messages = kwargs.get("messages", [])
            if self.calls == 1:
                assert not any(m.get("role") == "tool" for m in messages)
                return FakeResponse(
                    FakeMessage(
                        "",
                        [
                            FakeToolCall(
                                "call_1",
                                "fetch_url",
                                json.dumps({"url": "https://example.com"}),
                            )
                        ],
                    )
                )
            assert any(m.get("role") == "tool" and "toolresult" in (m.get("content") or "") for m in messages)
            return FakeResponse(FakeMessage("done", None))

    class FakeOpenAI:
        def __init__(self, base_url=None, api_key=None):
            self.chat = types.SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    executor = NodeExecutor()
    node = NodeData(
        title="AI_AGENT",
        type=NodeType.AI_AGENT,
        modelId="qwen/qwen3.6-35b-a3b",
        allowedTools=["fetch_url"],
    )
    payload = FlowPayload.from_items([FlowItem(json={"text": "hi"})])
    res = executor.execute(node, payload.all_items(), [node], {node.id: payload})
    assert res.success is True
    assert res.outputItems
    assert "done" in (res.outputItems[0].json_data.get("text") or "")

