import json

from assistant import database, memory


def test_kv_migration_roundtrip(tmp_path, monkeypatch):
    mem_file = tmp_path / "memory.json"
    mem_file.write_text(json.dumps({
        "state": {"focus_mode": True}, "settings": {"verbosity": "chatty"}, "notes": ["a"],
    }), encoding="utf-8")

    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "t.db")
    monkeypatch.setattr(database, "_kv_ready", False)
    monkeypatch.setattr(memory, "MEMORY_FILE", mem_file)
    monkeypatch.setattr(memory, "_KV", None)
    monkeypatch.setitem(memory._CACHE, "text", None)

    assert memory.get_setting("verbosity") == "chatty"        # migrated from the JSON
    assert memory.get_state_value("focus_mode") is True
    assert (tmp_path / "backups").exists()                    # backup was made

    memory.set_state_value("x", [1, 2])
    got = memory.get_state_value("x")
    got.append(3)
    assert memory.get_state_value("x") == [1, 2]              # callers can't mutate the cache

    monkeypatch.setattr(memory, "_KV", None)                  # simulate a restart
    assert memory.get_state_value("x") == [1, 2]
    assert memory.get_setting("missing", "dflt") == "dflt"

    memory.save_memory(memory.load_memory())
    raw = json.loads(mem_file.read_text(encoding="utf-8"))
    assert "state" not in raw and "settings" not in raw       # no longer written to the file
    assert raw["notes"] == ["a"]