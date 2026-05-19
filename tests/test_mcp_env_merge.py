import subprocess

from src.logic.mcp_client import NativeMcpClient


def test_mcp_env_does_not_override_placeholder(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "REAL")

    captured = {}

    def fake_popen(args, stdin=None, stdout=None, stderr=None, env=None, cwd=None, shell=None, text=None, bufsize=None):
        captured["env"] = env
        return object()

    client = NativeMcpClient()
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(client, "_send_request", lambda server_name, payload: {"result": {"ok": True}})
    monkeypatch.setattr(client, "_send_raw", lambda server_name, payload: None)

    ok = client.start_server(
        "Brave Search",
        {"command": "node", "args": [], "env": {"BRAVE_API_KEY": "YOUR_BRAVE_API_KEY"}},
    )
    assert ok is True
    assert captured["env"]["BRAVE_API_KEY"] == "REAL"

