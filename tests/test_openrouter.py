import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Execute the web search tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or main argument"},
                    "url": {"type": "string", "description": "URL if applicable"}
                }
            }
        }
    }
]

response = client.chat.completions.create(
    model="x-ai/grok-4.1-fast",
    messages=[
        {"role": "user", "content": "latest soccer italian match with result, search for it"}
    ],
    tools=tools,
    temperature=0.7
)

print(response)
print("Content:", response.choices[0].message.content)
print("Tool calls:", response.choices[0].message.tool_calls)