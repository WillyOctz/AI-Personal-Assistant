def test_file_confirmation_opens_and_deny_cancels(tmp_path, monkeypatch):
    from assistant.handlers import paths
    f = tmp_path / "n.txt"; f.write_text("x")
    opened = []
    monkeypatch.setattr(paths.pins, "resolve", lambda n: {"name": "n", "path": str(f), "kind": "file", "source": "pin"})
    monkeypatch.setattr(paths, "_perform", lambda t: opened.append(t["path"]) or "ok")
    assert paths._confirmed({"name": "n", "path": str(f)}) == "ok"
    assert paths._confirmed({"name": "n", "path": str(tmp_path / "other.txt")}).startswith("That shortcut changed")