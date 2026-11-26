import pytest

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    from assistant import convo_store, database, memory, pins, app_finder
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "t.db")
    monkeypatch.setattr(database, "MEMORY_FILE", tmp_path / "memory.json")
    monkeypatch.setattr(memory, "MEMORY_FILE", tmp_path / "memory.json")
    monkeypatch.setitem(memory._CACHE, "text", None)
    monkeypatch.setattr(memory, "_KV", None)
    monkeypatch.setattr(database, "_db_ready", None, raising=False)
    monkeypatch.setattr(database, "_kv_ready", None, raising=False)
    monkeypatch.setattr(convo_store, "_ready", False)
    monkeypatch.setattr(pins, "_ready", False)
    monkeypatch.setattr(app_finder, "_ready", False)