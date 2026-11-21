import pytest
from assistant import convo_store, convo_worker, database, memory, retrieval, semantic_memory
from assistant.handlers import recall_cmds

@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "t.db")
    monkeypatch.setattr(database, "MEMORY_FILE", tmp_path / "memory.json")
    monkeypatch.setattr(convo_store, "_ready", False)
    monkeypatch.setattr(memory, "_KV", None)
    monkeypatch.setattr(database, "_kv_ready", False)
    clock = {"t": 1_800_000_000.0}
    monkeypatch.setattr(convo_store, "_now", lambda: clock["t"])
    return clock

def turn(text, intent="chat_need_help", group="chat", source="gemini"):
    return {"user": text, "assistant": "ok", "intent": intent, "group": group, "source": source,
            "confidence": 1.0, "timestamp": "2026-11-01 10:00:00", "importance": 0.3}

def test_idle_gap_closes_session(db):
    a = convo_store.add_turn(turn("hello there"), 1800)
    db["t"] += 600
    b = convo_store.add_turn(turn("still here"), 1800)
    assert a["session_id"] == b["session_id"] and not b["closed_session"]
    db["t"] += 4000
    c = convo_store.add_turn(turn("new topic"), 1800)
    assert c["closed_session"] and c["session_id"] != a["session_id"]
    assert convo_store.pending() == [a["session_id"]]

def test_positions_survive_deletes(db):
    ids = [convo_store.add_turn(turn(f"m{i}"), 1800)["id"] for i in range(3)]
    convo_store.delete_session(1)
    assert convo_store.add_turn(turn("after"), 1800)["id"] > ids[-1]

def test_turn_write_never_touches_memory_json(db, monkeypatch):
    monkeypatch.setattr(memory, "save_memory", lambda *_: (_ for _ in ()).throw(AssertionError("JSON write")))
    memory.add_conversation_turn(turn("no json please"))
    memory.add_history_event({"user_input": "x", "intent": "i", "group": "g", "confidence": 1,
                              "source": "s", "result": "r", "timestamp": "2026-11-01 10:00:00"})

def test_prune_only_touches_summarised_sessions(db):
    for i in range(4):
        convo_store.add_turn(turn(f"old {i}"), 1800)
    sid = 1
    kwargs = dict(keep_turns=0, archive_days=0, delete_days=0, history_days=999)
    db["t"] += 90 * 86400
    assert convo_store.prune(**kwargs)["archive"] == 0            # session still open/unsummarised
    convo_store.set_status(sid, "summarised")
    assert convo_store.prune(**kwargs)["archive"] == 4

def test_summary_is_embedded_on_write(db, monkeypatch):
    for text in ("lets go with sqlite for pruning", "we will keep notes in json", "ok next thing please"):
        convo_store.add_turn(turn(text), 1800)
    convo_store.set_status(1, "pending")
    monkeypatch.setattr(convo_worker, "llm_summary", lambda turns: (
        {"summary": "Talked about storage.", "decisions": ["Use SQLite for pruning conversation turns"],
         "topics": ["storage"], "open_items": []}, "gemini"))
    seen = []
    monkeypatch.setattr(semantic_memory, "cache_conversation_summary_embedding",
                        lambda sid: seen.append(("summary", sid)) or {"ok": True, "error": None})
    monkeypatch.setattr(semantic_memory, "cache_text_embedding",
                        lambda t, i, text: seen.append((t, i)) or {"ok": True})
    sid = convo_worker.process(1)
    assert ("summary", sid) in seen and ("decision", f"{sid}:0") in seen
    assert convo_store.get_session(1)["status"] == "summarised"

def test_extractive_fallback_finds_decision_cues():
    t = [turn("lets go with sqlite"), turn("what about indexes"), turn("ok")]
    assert any("sqlite" in d for d in convo_worker.extractive_summary(t)["decisions"])

@pytest.mark.parametrize("text,topic", [
    ("what did we decide about sqlite", "sqlite"),
    ("what did we decide on the pruning plan", "the pruning plan"),
    ("did we agree on weekly recaps", "weekly recaps"),
    ("what's the decision on packaging", "packaging"),
    ("what did we decide", ""),
])
def test_decision_phrases(text, topic):
    assert recall_cmds.topic_of(text) == topic

@pytest.mark.parametrize("text", ["what is the plan for today", "what did you do yesterday", "hello"])
def test_decision_phrases_do_not_hijack(text):
    assert recall_cmds.topic_of(text) is None