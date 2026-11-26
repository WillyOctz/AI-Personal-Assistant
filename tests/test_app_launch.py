import os
from assistant import tools

def test_split_command(tmp_path):
    exe = tmp_path / "My App" / "app.exe"
    exe.parent.mkdir()
    exe.write_text("x")
    assert tools.split_command(f'"{exe}" --flag') == (str(exe), "--flag")
    assert tools.split_command(f"{exe} --flag") == (str(exe), "--flag")          # unquoted, spaces, args
    assert tools.split_command("chrome") == ("chrome", "")
    assert tools.split_command("shell:AppsFolder\\Foo_8wekyb3d8bbwe!App") == ("shell:AppsFolder\\Foo_8wekyb3d8bbwe!App", "")

def test_open_uses_startfile(tmp_path, monkeypatch):
    exe = tmp_path / "a.exe"
    exe.write_text("x")
    calls = []
    monkeypatch.setattr(os, "startfile", lambda p, **kw: calls.append((p, kw)), raising=False)
    assert tools.open_registered_app("a", {"command": f'"{exe}" -x'}, True) == "Opening a"
    assert calls[0][0] == str(exe) and calls[0][1]["arguments"] == "-x"

def test_disabled_launching_does_not_start(monkeypatch):
    monkeypatch.setattr(os, "startfile", lambda *a, **k: (_ for _ in ()).throw(AssertionError("launched")), raising=False)
    assert tools.open_registered_app("a", {"command": "x"}, False).startswith("Real app launching is disabled")