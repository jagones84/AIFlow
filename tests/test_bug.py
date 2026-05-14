import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

ai_tools = [{
    "type": "function",
    "function": {
        "name": "brave_web_search",
        "description": "Search web",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
    }
}]

messages = [{"role": "user", "content": "latest soccer italian match with result, search for it"}]

res1 = client.chat.completions.create(
    model="x-ai/grok-4.1-fast",
    messages=messages,
    tools=ai_tools,
    temperature=0.7
)

message = res1.choices[0].message
msg_dict = message.model_dump(exclude_unset=True)
clean_msg = {
    "role": "assistant",
    "content": msg_dict.get("content") or "",
    "tool_calls": msg_dict.get("tool_calls")
}
messages.append(clean_msg)

for tc in message.tool_calls:
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "content": "Inter Milan won 3-0 against Lazio",
        "name": tc.function.name
    })

print("Sending second request...")
try:
    res2 = client.chat.completions.create(
        model="x-ai/grok-4.1-fast",
        messages=messages,
        tools=ai_tools,
        temperature=0.7
    )
    print("Second finish_reason:", res2.choices[0].finish_reason)
    print("Second content:", res2.choices[0].message.content)
    print("Second tool_calls:", res2.choices[0].message.tool_calls)
except Exception as e:
    print("Error:", e)
