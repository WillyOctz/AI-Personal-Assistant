import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime

from assistant import database

_ready = False
_lock = threading.Lock()

TABLES = ["""CREATE TABLE IF NOT EXISTS conversation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started REAL NOT NULL,
    last_turn REAL NOT NULL,
    turn_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','pending','summarised','skipped')),
    attempts INTEGER NOT NULL DEFAULT 0,
    summary_id INTEGER)"""]

TURN_COLS = {"session_id": "INTEGER", "archived": "INTEGER NOT NULL DEFAULT 0"}

SUMMARY_COLS = {
    "session_id": "INTEGER",
    "kind": "TEXT NOT NULL DEFAULT 'manual'",          # session | manual | decision
    "decisions_json": "TEXT NOT NULL DEFAULT '[]'",
    "topics_json": "TEXT NOT NULL DEFAULT '[]'",
    "open_json": "TEXT NOT NULL DEFAULT '[]'",
    "origin": "TEXT NOT NULL DEFAULT 'manual'",        # llm:gemini | llm:groq | extractive | user | manual
    "turn_count": "INTEGER NOT NULL DEFAULT 0",
}
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_turns_session ON conversation_turns (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_turns_archived ON conversation_turns (archived, position)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_status ON conversation_sessions (status)",
    "CREATE INDEX IF NOT EXISTS idx_summaries_kind ON conversation_summaries (kind, timestamp)",
]

def _now():                     
    return time.time()

def _stamp(ts=None):
    ts = ts if ts is not None else _now()
    return datetime.fromtimestamp(max(ts, 86400)).strftime("%Y-%m-%d %H:%M:%S")

def _parse(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").timestamp()
    except (TypeError, ValueError):
        return None
    
def _add_columns(conn, table, columns):
    have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
            
def _init():
    global _ready
    if _ready:
        return
    
    with _lock:
        if _ready:
            return
        
        database.initialize_database()
        conn = database.get_connection()
        try:
            for stmt in TABLES:
                conn.execute(stmt)
                
            _add_columns(conn, "conversation_turns", TURN_COLS)
            _add_columns(conn, "conversation_summaries", SUMMARY_COLS)
            for stmt in INDEXES:
                conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()
        _ready = True
        
@contextmanager
def _db():
    _init()
    conn = database.get_connection()
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
        
# ------------------------------------Write-------------------------------------
def add_turn(turn, gap_seconds):
    """One transaction: close a stale session, open/extend one, insert the turn."""
    now = _now()
    closed = False
    with _db() as c:
        c.execute("BEGIN IMMEDIATE")
        last = c.execute("SELECT id, last_turn FROM conversation_sessions "
                         "WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
        if last and now - last["last_turn"] > gap_seconds:
            c.execute("UPDATE conversation_sessions SET status = 'pending' WHERE id = ?", (last["id"],))
            closed, last = True, None
        if last is None:
            session_id = c.execute("INSERT INTO conversation_sessions (started, last_turn) VALUES (?, ?)", (now, now)).lastrowid
            
        else:
            session_id = last["id"]
        turn_id = c.execute(
            """INSERT INTO conversation_turns (position, user_text, assistant_text, intent, intent_group,
                   confidence, source, timestamp, importance, migrated_at, session_id)
               VALUES ((SELECT COALESCE(MAX(position), 0) + 1 FROM conversation_turns), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn.get("user") or "", turn.get("assistant"), turn.get("intent"), turn.get("group"),
             turn.get("confidence"), turn.get("source"), turn.get("timestamp") or _stamp(now),
             turn.get("importance"), _stamp(now), session_id),
        ).lastrowid
        c.execute("UPDATE conversation_sessions SET last_turn = ?, turn_count = turn_count + 1 WHERE id = ?",
                  (now, session_id))
    return {"id": turn_id, "session_id": session_id, "closed_session": closed}

def add_history(event):
    def text(key):
        return str(event.get(key) or "").strip() or "-"
    with _db() as c:
        c.execute(
            """INSERT INTO history_events (position, user_input, intent, intent_group, confidence, source,
                   result, timestamp, importance, migrated_at)
               VALUES ((SELECT COALESCE(MAX(position), 0) + 1 FROM history_events), ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (text("user_input"), text("intent"), text("group"), float(event.get("confidence") or 0),
             text("source"), text("result"), event.get("timestamp") or _stamp(), event.get("importance"), _stamp()),
        )
        
# --------------------------------Reads--------------------------------------
def _turn(r):
    return {
        "id": r["id"], "session_id": r["session_id"], "user": r["user_text"], "assistant": r["assistant_text"],
        "intent": r["intent"], "group": r["intent_group"], "confidence": r["confidence"],
        "source": r["source"], "timestamp": r["timestamp"], "importance": r["importance"]
    }
    
def turns(limit=None, archived=False):
    order = "timestamp DESC, id DESC" if archived else "position DESC"
    sql, args = f"SELECT * FROM conversation_turns WHERE archived = ? ORDER BY {order}", [int(archived)]
    if limit:
        sql += " LIMIT ?"; args.append(limit)
    with _db() as c:
        rows = c.execute(sql, args).fetchall()
    return [_turn(r) for r in reversed(rows)]

def session_turns(session_id):
    with _db() as c:
        rows = c.execute("SELECT * FROM conversation_turns WHERE session_id = ? ORDER BY position",
                         (session_id,)).fetchall()
    return [_turn(r) for r in rows]

def recent_unsummarised(limit=60):
    with _db() as c:
        rows = c.execute(
            """SELECT t.* FROM conversation_turns t JOIN conversation_sessions s ON s.id = t.session_id
               WHERE s.status IN ('open', 'pending') AND t.archived = 0
               ORDER BY t.position DESC LIMIT ?""", (limit,)
        ).fetchall()
    return [_turn(r) for r in rows]

def get_session(session_id):
    with _db() as c:
        r = c.execute("SELECT * FROM conversation_sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(r) if r else None

def current_session_id():
    with _db() as c:
        r = c.execute("SELECT id FROM conversation_sessions WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
    return r["id"] if r else None

def pending(limit=3):
    with _db() as c:
        rows = c.execute("SELECT id FROM conversation_sessions WHERE status = 'pending' "
                         "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [r["id"] for r in rows]

def close_idle(gap_seconds):
    with _db() as c:
        return c.execute("UPDATE conversation_sessions SET status = 'pending' "
                         "WHERE status = 'open' AND last_turn < ?", (_now() - gap_seconds,)).rowcount
        
def set_status(session_id, status=None, summary_id=None):
    with _db() as c:
        if status:
            c.execute("UPDATE conversation_sessions SET status = ? WHERE id = ?", (status, session_id))
        if summary_id is not None:
            c.execute("UPDATE conversation_sessions SET summary_id = ? WHERE id = ?", (summary_id, session_id))
            
def bump_attempts(session_id):
    with _db() as c:
        c.execute("UPDATE conversation_sessions SET attempts = attempts + 1 WHERE id = ?", (session_id,))
        

# -------------------------------------------------Summaries------------------------------------------------
def render_text(d):
    """The retrieval text. Decisions come first so even truncated prompt context still keeps them."""
    parts = []
    if d.get("decisions"):
        parts.append("Decisions: " + " | ".join(d["decisions"]))
    parts.append("Summary: " + d["summary"].strip())
    if d.get("topics"):
        parts.append("Topics: " + ", ".join(d["topics"]))
    if d.get("open_items"):
        parts.append("Open: " + " | ".join(d["open_items"]))
    return "\n".join(parts)

def save_summary(data, *, kind, origin, session_id=None, timestamp=None, turn_count=0):
    data = {"decisions": [], "topics": [], "open_items": [], **data}
    with _db() as c:
        return c.execute(
            """INSERT INTO conversation_summaries (position, summary, timestamp, migrated_at, session_id, kind,
                   decisions_json, topics_json, open_json, origin, turn_count)
               VALUES ((SELECT COALESCE(MAX(position), 0) + 1 FROM conversation_summaries), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (render_text(data), timestamp or _stamp(), _stamp(), session_id, kind, json.dumps(data["decisions"]),
             json.dumps(data["topics"]), json.dumps(data["open_items"]), origin, turn_count),
        ).lastrowid
        
def _summary(r):
    return {"id": r["id"], "summary": r["summary"], "timestamp": r["timestamp"], "kind": r["kind"],
            "origin": r["origin"], "session_id": r["session_id"], "turn_count": r["turn_count"],
            "decisions": json.loads(r["decisions_json"]), "topics": json.loads(r["topics_json"]),
            "open_items": json.loads(r["open_json"])}
    
def summaries(kinds=None, limit=None):
    sql, args = "SELECT * FROM conversation_summaries", []
    if kinds:
        sql += f" WHERE kind IN ({','.join('?' * len(kinds))})"; args += list(kinds)
    sql += " ORDER BY timestamp DESC, id DESC"
    if limit:
        sql += " LIMIT ?"; args.append(limit)
    with _db() as c:
        return [_summary(r) for r in c.execute(sql, args).fetchall()]
    
def get_summary(summary_id):
    with _db() as c:
        r = c.execute("SELECT * FROM conversation_summaries WHERE id = ?", (summary_id,)).fetchone()
    return _summary(r) if r else None

def delete_summary(summary_id):
    with _db() as c:
        c.execute("DELETE FROM conversation_summaries WHERE id = ?", (summary_id,))
        c.execute("DELETE FROM memory_embeddings WHERE source_type = 'conversation_summary' AND source_id = ?",
                  (str(summary_id),))
        c.execute("DELETE FROM memory_embeddings WHERE source_type = 'decision' AND source_id LIKE ?",
                  (f"{summary_id}:%",))
        
def delete_session(session_id):
    s = get_session(session_id)
    
    if not s:
        return None
    
    if s["summary_id"]:
        delete_summary(s["summary_id"])
        
    with _db() as c:
        n = c.execute("DELETE FROM conversation_turns WHERE session_id = ?", (session_id,)).rowcount
        c.execute("DELETE FROM conversation_sessions WHERE id = ?", (session_id,))
    return n

# ----------------------------------Backfill, Prune and Stats-------------------------------------
def backfill_sessions(gap_seconds):
    """Group old session-less turns by idle gaps."""
    made, current, last_ts = 0, None, None
    with _db() as c:
        rows = c.execute("SELECT id, timestamp FROM conversation_turns "
                         "WHERE session_id IS NULL AND archived = 0 ORDER BY position").fetchall()
        
        for r in rows:
            ts = _parse(r["timestamp"]) or last_ts or _now()
            if current is None or ts - last_ts > gap_seconds:
                current = c.execute("INSERT INTO conversation_sessions (started, last_turn, status) "
                                    "VALUES (?, ?, 'pending')", (ts, ts)).lastrowid
                made += 1
                
            c.execute("UPDATE conversation_turns SET session_id = ? WHERE id = ?", (current, r["id"]))
            c.execute("UPDATE conversation_sessions SET last_turn = ?, turn_count = turn_count + 1 WHERE id = ?",
                      (ts, current))
            last_ts = ts
        if current is not None and last_ts > _now() - gap_seconds:
            c.execute("UPDATE conversation_sessions SET status = 'open' WHERE id = ?", (current,))
    return made

_SAFE = "session_id IN (SELECT id FROM conversation_sessions WHERE status IN ('summarised', 'skipped'))"

def prune(keep_turns, archive_days, delete_days, history_days, dry_run=False):
    """Archive/delete by retention, only touched whose session is already skipped or summarised"""
    now = _now()
    cut = lambda d: _stamp(now - d * 86400)
    with _db() as c:
        top = c.execute("SELECT COALESCE(MAX(position), 0) AS m FROM conversation_turns").fetchone()["m"]
        a_where = f"archived = 0 AND timestamp < ? AND position <= ? AND {_SAFE}"
        d_where = f"archived = 1 AND timestamp < ? AND ({_SAFE} OR session_id IS NULL)"
        a_args, d_args, h_args = (cut(archive_days), top - keep_turns), (cut(delete_days),), (cut(history_days),)
        
        if dry_run:
            count = lambda table, where, args: c.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", args).fetchone()["n"]
            
            return {"archive": count("conversation_turns", a_where, a_args),
                    "delete": count("conversation_turns", d_where, d_args),
                    "history": count("history_events", "timestamp < ?", h_args)}
            
        archived = c.execute(f"UPDATE conversation_turns SET archived = 1 WHERE {a_where}", a_args).rowcount
        deleted = c.execute(f"DELETE FROM conversation_turns WHERE {d_where}", d_args).rowcount
        history = c.execute("DELETE FROM history_events WHERE timestamp < ?", h_args).rowcount
        
    return {"archive": archived, "delete": deleted, "history": history}

def counts():
    with _db() as c:
        q = lambda sql: c.execute(sql).fetchone()[0]
        return {
            "turns": q("SELECT COUNT(*) FROM conversation_turns WHERE archived = 0"),
            "archived": q("SELECT COUNT(*) FROM conversation_turns WHERE archived = 1"),
            "history": q("SELECT COUNT(*) FROM history_events"),
            "sessions": {r["status"]: r["n"] for r in c.execute(
                "SELECT status, COUNT(*) AS n FROM conversation_sessions GROUP BY status")},
            "summaries": {r["kind"]: r["n"] for r in c.execute(
                "SELECT kind, COUNT(*) AS n FROM conversation_summaries GROUP BY kind")},
        }
