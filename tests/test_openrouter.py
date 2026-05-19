import os

import pytest
from dotenv import load_dotenv


pytestmark = pytest.mark.integration


def test_openrouter_basic_completion():
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")

    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    response = client.chat.completions.create(
        model="qwen/qwen3.6-35b-a3b",
        messages=[{"role": "user", "content": "Respond with exactly: ok"}],
        temperature=0,
    )

    content = response.choices[0].message.content or ""
    assert content.strip()
