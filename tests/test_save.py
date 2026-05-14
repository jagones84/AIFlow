import requests
res = requests.post("http://localhost:8000/api/workflow", json={"name": "test_save", "data": {"test": 123}})
print(res.status_code, res.text)
