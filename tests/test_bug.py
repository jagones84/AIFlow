import os

import pytest
from dotenv import load_dotenv


pytestmark = pytest.mark.integration


def test_openrouter_tool_call_message_formatting():
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")

    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    ai_tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Execute the web search tool",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
    ]

    messages = [{"role": "user", "content": "Use the web_search tool with query 'example.com'."}]
    res1 = client.chat.completions.create(model="x-ai/grok-4.1-fast", messages=messages, tools=ai_tools, temperature=0.2)
    message = res1.choices[0].message
    if not message.tool_calls:
        pytest.skip("Model did not call tools; cannot validate tool-call formatting regression")

    msg_dict = message.model_dump(exclude_unset=True)
    messages.append({"role": "assistant", "content": msg_dict.get("content") or "", "tool_calls": msg_dict.get("tool_calls")})

    for tc in message.tool_calls:
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": "ok", "name": tc.function.name})

    res2 = client.chat.completions.create(model="x-ai/grok-4.1-fast", messages=messages, tools=ai_tools, temperature=0.2)
    assert (res2.choices[0].message.content or "").strip()
