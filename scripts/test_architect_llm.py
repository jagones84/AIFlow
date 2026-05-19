import requests
import json
import time

def test_llm():
    print("Testing Architect LLM endpoint...")
    url = "http://localhost:48321/api/architect"
    payload = {
        "prompt": "Create a simple workflow. Start with TRIGGER. Then add a USER_INPUT node and set its userInstruction field to 'Ciao mondo come stai?'. Then add an AI_AGENT node.",
        "model": "qwen/qwen3.6-35b-a3b" 
    }
    
    # Try to hit the API
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
        
        # Now fetch the graph to see what it built
        time.sleep(1)
        graph_resp = requests.get("http://localhost:48321/api/architect/graph")
        print("\nGenerated Graph:")
        print(json.dumps(graph_resp.json(), indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_llm()
