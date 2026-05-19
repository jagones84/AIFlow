from fastapi.testclient import TestClient

from src.server import app


def test_save_workflow_writes_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    res = client.post("/api/workflow", json={"name": "test_save", "data": {"test": 123}})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    saved = tmp_path / "config" / "workflows" / "test_save.json"
    assert saved.exists()
    assert '"test": 123' in saved.read_text(encoding="utf-8")
