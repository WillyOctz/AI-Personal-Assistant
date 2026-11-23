import json
from pathlib import Path
import pytest
from assistant import brain

CASES = [json.loads(l) for l in Path("datasets/routing_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    from assistant import convo_store, database, memory, pins
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "t.db")
    monkeypatch.setattr(database, "MEMORY_FILE", tmp_path / "memory.json")
    monkeypatch.setattr(memory, "MEMORY_FILE", tmp_path / "memory.json")
    monkeypatch.setitem(memory._CACHE, "text", None)
    monkeypatch.setattr(memory, "_KV", None)
    monkeypatch.setattr(database, "_db_ready", None, raising=False)
    monkeypatch.setattr(database, "_kv_ready", None, raising=False)
    monkeypatch.setattr(convo_store, "_ready", False)
    monkeypatch.setattr(pins, "_ready", False)

@pytest.mark.parametrize("case", CASES, ids=lambda c: c["text"])
def test_route(case, tmp_db, monkeypatch):
    monkeypatch.setattr(brain.intent_model, "predict", lambda text: None)
    got = brain.analyze_intent(case["text"])["intent"]
    if "intent" in case:
        assert got == case["intent"]
    else:
        assert got != case["not_intent"]