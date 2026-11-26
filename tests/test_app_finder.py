import os
import pytest
from assistant import app_finder as F, memory, tools

@pytest.fixture
def tree(tmp_path, tmp_db, monkeypatch):
    monkeypatch.setattr(F, "_ready", False)
    F._cache["dirty"] = True
    monkeypatch.setenv("SystemRoot", str(tmp_path / "Windows"))
    monkeypatch.setattr(F, "_start_menu", lambda: {})
    monkeypatch.setattr(tools, "app_paths_lookup", lambda n: None)
    monkeypatch.setattr(F.shutil, "which", lambda q: None)
    for rel in ["Opera/opera.exe", "Opera/unins000.exe", "Opera/crashpad_handler.exe",
                "Downloads/shady.exe", "Windows/notepad.exe", "Windows/System32/cmd.exe"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    F.scan(roots=[str(tmp_path)])
    return tmp_path

def test_scan_filters_junk_and_blocked(tree):
    names = {r["name"] for r in F._rows()}
    assert "opera" in names and "notepad" in names and "shady" in names
    assert not names & {"unins000", "crashpad_handler", "cmd"}

def test_find_ranks_and_classifies(tree):
    found = F.find("opera")
    assert found["status"] == "ok" and found["candidates"][0]["path"].endswith("opera.exe")
    assert F.find("shady")["candidates"][0]["tier"] == "risky"
    assert F.find("notepad")["candidates"][0]["tier"] == "protected"

def test_shells_are_refused(tree):
    assert F.find("cmd")["status"] == "blocked"
    assert F.find("powershell.exe")["status"] == "blocked"

def test_protected_can_be_switched_off(tree, monkeypatch):
    memory.set_setting("app_search_protected", False)
    assert F.find("notepad")["status"] != "ok"

def test_launch_rechecks_file(tree, monkeypatch):
    memory.set_setting("real_app_launching", True)
    monkeypatch.setattr(F.tools, "open_registered_app", lambda *a: "Opening opera.")
    monkeypatch.setattr("assistant.apps.log_app_launch", lambda *a: None)
    c = F.find("opera")["candidates"][0]
    F._ask(c)
    pending = memory.get_state_value("pending_found_app")
    assert str(F._launch(pending)).startswith("Opening")
    with open(c["path"], "a") as f:
        f.write("changed")                                    # size changes -> must refuse
    assert "changed" in str(F._launch(pending))

def test_strict_yes_is_not_enough(tree):
    F._ask(F.find("shady")["candidates"][0])
    pending = memory.get_state_value("pending_found_app")
    assert pending["strict"] is True
    assert "stronger yes" in F._confirmed(pending).say