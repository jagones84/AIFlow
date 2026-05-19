import os

from src.logic.node_executor import NodeExecutor
from src.models.node_models import FlowItem, FlowPayload, NodeData, NodeType


def test_ai_agent_fallback_without_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    executor = NodeExecutor()
    node = NodeData(title="AI_AGENT", type=NodeType.AI_AGENT, modelId="x-ai/grok-4.1-fast", systemPrompt="You are a helpful AI.")

    payload = FlowPayload.from_items([FlowItem(json={"text": "hello"})])
    res = executor.execute(node, payload.all_items(), [node], {node.id: payload})

    assert res.success is True
    assert res.outputItems
    assert "Simulated AI Response" in (res.outputItems[0].json_data.get("text") or "")
