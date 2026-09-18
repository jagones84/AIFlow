import runpy


def test_main_server_start_disables_reload(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", fake_run)

    runpy.run_module("src.server", run_name="__main__")

    assert captured["args"] == ("src.server:app",)
    assert captured["kwargs"]["host"] == "0.0.0.0"
    assert captured["kwargs"]["port"] == 8000
    assert captured["kwargs"].get("reload") is False
