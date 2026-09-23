import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_FILE = PROJECT_ROOT / "db" / "nebula.db"
MEMORY_FILE = PROJECT_ROOT / "datasets" / "memory.json"
BACKUP_DIR = PROJECT_ROOT / "datasets" / "backups"
SCHEMA_VERSION = 1

def get_connection():
    DATABASE_FILE.parent.mkdir(exist_ok=True)
    
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    
    return connection

def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        
        row = connection.execute(
            """
            SELECT value
            FROM schema_meta
            WHERE key = ?
            """,
            ("schema_version",),
        ).fetchone()
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_facts (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                text TEXT NOT NULL,
                due TEXT,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS website_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                allowed INTEGER NOT NULL CHECK (allowed IN (0, 1)),
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE,
                command TEXT NOT NULL,
                allowed INTEGER NOT NULL CHECK (allowed IN (0, 1)),
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_launch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                app_name TEXT NOT NULL,
                command TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                alias TEXT NOT NULL UNIQUE,
                app_name TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS default_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                category TEXT NOT NULL UNIQUE,
                app_name TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_registry_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                app_registry_json TEXT NOT NULL,
                app_aliases_json TEXT NOT NULL,
                default_apps_json TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS search_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS file_search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                action TEXT NOT NULL,
                folder TEXT NOT NULL,
                query TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS website_open_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                website_name TEXT NOT NULL,
                url TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                user_text TEXT NOT NULL,
                assistant_text TEXT,
                intent TEXT,
                intent_group TEXT,
                confidence REAL,
                source TEXT,
                timestamp TEXT,
                importance REAL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS response_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                feedback TEXT NOT NULL CHECK (
                    feedback IN ('helpful', 'not_helpful')
                ),
                last_intent TEXT,
                last_group TEXT,
                last_text TEXT,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS response_feedback_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                note TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS history_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                user_input TEXT NOT NULL,
                intent TEXT NOT NULL,
                intent_group TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                importance REAL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS work_session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                total_sessions INTEGER NOT NULL,
                total_seconds INTEGER NOT NULL,
                top_task TEXT,
                notes_count INTEGER NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL CHECK (
                    entity_type IN ('games', 'apps')
                ),
                position INTEGER NOT NULL,
                value TEXT NOT NULL,
                migrated_at TEXT NOT NULL,
                UNIQUE (entity_type, position),
                UNIQUE (entity_type, value)
            )
            """
        )
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                task TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration TEXT NOT NULL,
                duration_seconds INTEGER,
                notes_json TEXT NOT NULL,
                migrated_at TEXT NOT NULL
            )
            """
        )
        
        if row is None:
            connection.execute(
                """
                INSERT INTO schema_meta (key, value)
                VALUES (?, ?)
                """,
                ("schema_version", str(SCHEMA_VERSION))
            )
            return
        
        saved_version = int(row["value"])
        
        if saved_version != SCHEMA_VERSION:
            raise RuntimeError(
                "Database schema version does not match this code."
            )
            
def get_database_status():
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT value
            FROM schema_meta
            WHERE key = ?
            """,
            ("schema_version",),
        ).fetchone()
        
    return {
        "path": str(DATABASE_FILE),
        "schema_version": int(row["value"]) if row else None,
    }
    
def create_memory_backup(label="memory_before_sqlite"):
    if not MEMORY_FILE.exists():
        raise FileNotFoundError(
            f"Memory file does not exist: {MEMORY_FILE}"
        )
        
    BACKUP_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / (
        f"{label}_{timestamp}.json"
    )
    
    shutil.copy2(MEMORY_FILE, backup_file)
    
    return backup_file

def record_migration(name, status, details):
    initialize_database()
    
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO migration_runs (
               name,
                status,
                details,
                created_at 
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                status,
                json.dumps(details),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        
def get_migration_runs(limit=10):
    initialize_database()
    
    safe_limit = max(1, min(limit, 50))
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                name,
                status,
                details,
                created_at
            FROM migration_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "details": json.loads(row["details"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    
def prepare_memory_migration():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    if not isinstance(memory_data, dict):
        raise ValueError("memory.json must contain a JSON object.")
    
    backup_file = create_memory_backup()
    
    details = {
        "backup_file": str(backup_file),
        "top_level_keys": sorted(memory_data.keys()),
        "top_level_key_count": len(memory_data),
    }
    
    record_migration(
        "prepare_memory_migration",
        "completed",
        details,
    )
    
    return details

def migrate_profile_from_json():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    profile = memory_data.get("profile", {})
    
    if not isinstance(profile, dict):
        raise ValueError("memory.json profile must be a JSON object.")
    
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as connection:
        for key, value in profile.items():
            connection.execute(
                """
                INSERT INTO profile_facts (
                    key,
                    value,
                    migrated_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    migrated_at = excluded.migrated_at
                """,
                (
                    str(key),
                    str(value),
                    migrated_at,
                ),
            )
            
        details = {
            "fact_count": len(profile),
            "keys": sorted(profile.keys()),
        }
        
    record_migration(
        "migrate_profile_from_json",
        "completed",
        details,
    )
        
    return details
    
def get_sqlite_profile():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT key, value
            FROM profile_facts
            ORDER BY key
            """
        ).fetchall()
        
    return {
        row["key"]: row["value"]
        for row in rows
    }
    
def get_sqlite_profile_fact(key):
    initialize_database()
    
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT value
            FROM profile_facts
            WHERE key = ?
            """,
            (str(key),),
        ).fetchone()
        
    if row is None:
        return None
    
    return row["value"]
    
def upsert_profile_fact(key, value):
    initialize_database()
    
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO profile_facts (
                key,
                value,
                migrated_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                migrated_at = excluded.migrated_at
            """,
            (
                str(key),
                str(value),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        
def delete_sqlite_profile_fact(key):
    initialize_database()
    
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM profile_facts
            WHERE key = ?
            """,
            (str(key),),
        )
        
    return cursor.rowcount > 0
    
def verify_profile_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_profile = memory_data.get("profile", {})
    sqlite_profile = get_sqlite_profile()
    
    json_keys = set(json_profile.keys())
    sqlite_keys = set(sqlite_profile.keys())
    
    missing_in_sqlite = sorted(json_keys - sqlite_keys)
    missing_in_json = sorted(sqlite_keys - json_keys)
    
    different_values = []
    
    for key in sorted(json_keys & sqlite_keys):
        json_value = str(json_profile[key])
        
        if json_value != sqlite_profile[key]:
            different_values.append({
                "key": key,
                "json_value": json_value,
                "sqlite_value": sqlite_profile[key],
            })
            
    matches = (
        not missing_in_sqlite
        and not missing_in_json
        and not different_values
    )
    
    result = {
        "matches": matches,
        "json_fact_count": len(json_profile),
        "sqlite_fact_count": len(sqlite_profile),
        "missing_in_sqlite": missing_in_sqlite,
        "missing_in_json": missing_in_json,
        "different_values": different_values,
    }
    
    record_migration(
        "verify_profile_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def migrate_notes_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    notes = memory_data.get("notes", [])
    
    if not isinstance(notes, list):
        raise ValueError("memory.json notes must be a JSON list.")
    
    if not all(isinstance(note, str) for note in notes):
        raise ValueError("Every note in memory.json must be text.")
    
    backup_file = create_memory_backup(
        "memory_before_notes_sqlite"
    )
    
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as connection:
        connection.execute("DELETE FROM notes")
        
        connection.executemany(
            """
            INSERT INTO notes (text, migrated_at)
            VALUES (?, ?)
            """,
            [
                (note, migrated_at)
                for note in notes
            ],
        )
        
    details = {
        "backup_file": str(backup_file),
        "note_count": len(notes),
    }
    
    record_migration(
        "migrate_notes_from_json",
        "completed",
        details,
    )
    
    return details

def get_sqlite_notes():
    initialize_database()
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, text, migrated_at
            FROM notes
            ORDER BY id
            """
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "text": row["text"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def add_sqlite_note(text):
    initialize_database()
    
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO notes (text, migrated_at)
            VALUES (?, ?)
            """,
            (
                str(text),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        
    return cursor.lastrowid

def delete_sqlite_note(text):
    initialize_database()
    
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM notes
            WHERE id = (
                SELECT id
                FROM notes
                WHERE text = ?
                ORDER BY id
                LIMIT 1
            )
            """,
            (str(text),),
        )
        
    return cursor.rowcount > 0
    
def verify_notes_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_notes = memory_data.get("notes", [])
    sqlite_rows = get_sqlite_notes()
    sqlite_notes = [
        row["text"]
        for row in sqlite_rows
    ]
    
    differences = []
    total_items = max(
        len(json_notes),
        len(sqlite_notes),
    )
    
    for index in range(total_items):
        json_note = (
            json_notes[index]
            if index < len(json_notes)
            else None
        )
        
        sqlite_note = (
            sqlite_notes[index]
            if index < len(sqlite_notes)
            else None
        )
        
        if json_note != sqlite_note:
            differences.append({
                "position": index + 1,
                "json_note": json_note,
                "sqlite_note": sqlite_note,
            })
            
    matches = not differences
    
    result = {
        "matches": matches,
        "json_note_count": len(json_notes),
        "sqlite_note_count": len(sqlite_notes),
        "differences": differences,
    }
    
    record_migration(
        "verify_notes_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def migrate_reminders_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    reminders = memory_data.get("reminders", [])
    
    if not isinstance(reminders, list):
        raise ValueError("memory.json reminders must be a JSON list.")
    
    normalized_reminders = []
    
    for index, reminder in enumerate(reminders, start=1):
        if isinstance(reminder, dict):
            text = reminder.get("text", "")
            due = reminder.get("due")
        elif isinstance(reminder, str):
            text = reminder
            due = None
        else:
            raise ValueError(
                f"Reminder {index} must be text or a JSON object."
            )
            
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Reminder {index} must contain non-empty text."
            )
            
        if due is not None and not isinstance(due, str):
            raise ValueError(
                f"Reminder {index} due value must be text or null."
            )
            
        normalized_reminders.append({
            "position": index,
            "text": text,
            "due": due,
        })
        
    backup_file = create_memory_backup(
        "memory_before_reminders_sqlite"
    )
    
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as connection:
        connection.execute("DELETE FROM reminders")
        
        connection.executemany(
            """
            INSERT INTO reminders (
                position,
                text,
                due,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    reminder["position"],
                    reminder["text"],
                    reminder["due"],
                    migrated_at,
                )
                for reminder in normalized_reminders
            ],
        )
        
    details = {
        "backup_file": str(backup_file),
        "reminder_count": len(normalized_reminders),
    }
    
    record_migration(
        "migrate_reminders_from_json",
        "completed",
        details,
    )
    
    return details

def get_sqlite_reminders():
    initialize_database()
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, position, text, due, migrated_at
            FROM reminders
            ORDER BY position
            """
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "text": row["text"],
            "due": row["due"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_reminders_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_reminders = memory_data.get("reminders", [])
    sqlite_reminders = get_sqlite_reminders()
    
    differences = []
    total_items = max(
        len(json_reminders),
        len(sqlite_reminders)
    )
    
    for index in range(total_items):
        position = index + 1
        
        json_reminder = (
            json_reminders[index]
            if index < len(json_reminders)
            else None
        )
        
        sqlite_reminder = (
            sqlite_reminders[index]
            if index < len(sqlite_reminders)
            else None
        )
        
        if json_reminder is None or sqlite_reminder is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_reminder,
                "sqlite_value": sqlite_reminder,
            })
            continue
        
        if isinstance(json_reminder, dict):
            json_text = json_reminder.get("text", "")
            json_due = json_reminder.get("due")
        else:
            json_text = json_reminder
            json_due = None
            
        if sqlite_reminder["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_reminder["position"],
            })
            
        if json_text != sqlite_reminder["text"]:
            differences.append({
                "position": position,
                "field": "text",
                "json_value": json_text,
                "sqlite_value": sqlite_reminder["text"],
            })
            
        if json_due != sqlite_reminder["due"]:
            differences.append({
                "position": position,
                "field": "due",
                "json_value": json_due,
                "sqlite_value": sqlite_reminder["due"],
            })
            
    matches = not differences
    
    result = {
        "matches": matches,
        "json_reminder_count": len(json_reminders),
        "sqlite_reminder_count": len(sqlite_reminders),
        "differences": differences,
    }
    
    record_migration(
        "verify_reminders_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def sync_sqlite_reminders_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    reminders = memory_data.get("reminders", [])
    
    if not isinstance(reminders, list):
        raise ValueError("memory.json reminders must be a JSON list.")
    
    records = []
    
    for position, reminder in enumerate(reminders, start=1):
        if isinstance(reminder, dict):
            text = reminder.get("text", "")
            due = reminder.get("due")
        elif isinstance(reminder, str):
            text = reminder
            due = None
        else:
            raise ValueError(
                f"Reminder {position} must be text or a JSON object."
            )
            
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Reminder {position} must contain non-empty text."
            )
            
        if due is not None and not isinstance(due, str):
            raise ValueError(
                f"Reminder {position} must contain non-empty text."
            )
            
        records.append((position, text, due))
        
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as connection:
        connection.execute("DELETE FROM reminders")
        
        connection.executemany(
            """
            INSERT INTO reminders (
                position,
                text,
                due,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    position,
                    text,
                    due,
                    synced_at,
                )
                for position, text, due in records
            ]
        )
    
    return len(records)

def migrate_conversation_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    conversation = memory_data.get("conversation", [])
    
    if not isinstance(conversation, list):
        raise ValueError("memory.json conversation must be a JSON list.")
    
    records = []
    
    for position, turn in enumerate(conversation, start=1):
        if not isinstance(turn, dict):
            raise ValueError(
                f"Conversation turn {position} must be a JSON object."
            )
            
        user_text = turn.get("user", "")
        assistant_text = turn.get("assistant", "")
        
        if not isinstance(user_text, str):
            raise ValueError(
                f"Conversation turn {position} user must be text."
            )
            
        if (assistant_text is not None and not isinstance(assistant_text, str)):
            raise ValueError(
                f"Conversation turn {position} assistant must be text."
            )
            
        records.append((
            position,
            user_text,
            assistant_text,
            turn.get("intent"),
            turn.get("group"),
            turn.get("confidence"),
            turn.get("source"),
            turn.get("timestamp"),
            turn.get("importance"),
        ))
        
    backup_file = create_memory_backup(
        "memory_before_conversation_sqlite"
    )
    
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as connection:
        connection.execute("DELETE FROM conversation_turns")
        
        connection.executemany(
            """
            INSERT INTO conversation_turns (
                position,
                user_text,
                assistant_text,
                intent,
                intent_group,
                confidence,
                source,
                timestamp,
                importance,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (*record, migrated_at)
                for record in records
            ],
        )
        
    details = {
        "backup_file": str(backup_file),
        "conversation_turn_count": len(records),
    }
    
    record_migration(
        "migrate_conversation_from_json",
        "completed",
        details,
    )
    
    return details

def get_sqlite_conversation(limit=None):
    initialize_database()
    
    query = """
        SELECT
            id,
            position,
            user_text,
            assistant_text,
            intent,
            intent_group,
            confidence,
            source,
            timestamp,
            importance,
            migrated_at
        FROM conversation_turns
    """
    
    parameters = ()
    
    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)
        
    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()
        
    if limit is not None:
        rows = list(reversed(rows))
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "user": row["user_text"],
            "assistant": row["assistant_text"],
            "intent": row["intent"],
            "group": row["intent_group"],
            "confidence": row["confidence"],
            "source": row["source"],
            "timestamp": row["timestamp"],
            "importance": row["importance"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def add_sqlite_conversation_turn(position, turn):
    initialize_database()
    
    user_text = turn.get("user", "")
    assistant_text = turn.get("assistant")
    
    if not isinstance(user_text, str):
        raise ValueError("Conversation user text must be text.")
    
    if (
        assistant_text is not None
        and not isinstance(assistant_text, str)
    ):
        raise ValueError(
            "Conversation assistant text must be text or null."
        )
        
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO conversation_turns (
                position,
                user_text,
                assistant_text,
                intent,
                intent_group,
                confidence,
                source,
                timestamp,
                importance,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position,
                user_text,
                assistant_text,
                turn.get("intent"),
                turn.get("group"),
                turn.get("confidence"),
                turn.get("source"),
                turn.get("timestamp"),
                turn.get("importance"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        
    return cursor.lastrowid

def sync_sqlite_conversation_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    conversation = memory_data.get("conversation", [])
    
    if not isinstance(conversation, list):
        raise ValueError("memory.json conversation must be a JSON list.")
    
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, turn in enumerate(conversation, start=1):
        if not isinstance(turn, dict):
            raise ValueError(
                f"Conversation turn {position} must be a JSON object."
            )
            
        user_text = turn.get("user", "")
        assistant_text = turn.get("assistant")
        
        if not isinstance(user_text, str):
            raise ValueError(
                f"Conversation turn {position} user must be text."
            )
            
        if (
            assistant_text is not None
            and not isinstance(assistant_text, str)
        ):
            raise ValueError(
                f"Conversation turn {position} assistant must be text or null."
            )
            
        records.append((
            position,
            user_text,
            assistant_text,
            turn.get("intent"),
            turn.get("group"),
            turn.get("confidence"),
            turn.get("source"),
            turn.get("timestamp"),
            turn.get("importance"),
            migrated_at,
        ))
        
    with get_connection() as connection:
        connection.execute("DELETE FROM conversation_turns")
        
        connection.executemany(
            """
            INSERT INTO conversation_turns (
                position,
                user_text,
                assistant_text,
                intent,
                intent_group,
                confidence,
                source,
                timestamp,
                importance,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        
    return len(records)
    
def verify_conversation_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_conversation = memory_data.get("conversation", [])
    sqlite_conversation = get_sqlite_conversation()
    
    field_map = {
        "user": "user",
        "assistant": "assistant",
        "intent": "intent",
        "group": "group",
        "confidence": "confidence",
        "source": "source",
        "timestamp": "timestamp",
        "importance": "importance",
    }
    
    differences = []
    total_items = max(
        len(json_conversation),
        len(sqlite_conversation),
    )
    
    for index in range(total_items):
        position = index + 1
        
        json_turn = (
            json_conversation[index]
            if index < len(json_conversation)
            else None
        )
        
        sqlite_turn = (
            sqlite_conversation[index]
            if index < len(sqlite_conversation)
            else None
        )
        
        if json_turn is None or sqlite_turn is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_turn,
                "sqlite_value": sqlite_turn,
            })
            continue
        
        if sqlite_turn["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_turn["position"],
            })
            
        for json_key, sqlite_key in field_map.items():
            if json_turn.get(json_key) != sqlite_turn.get(sqlite_key):
                differences.append({
                    "position": position,
                    "field": json_key,
                    "json_value": json_turn.get(json_key),
                    "sqlite_value": sqlite_turn.get(sqlite_key),
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_turn_count": len(json_conversation),
        "sqlite_turn_count": len(sqlite_conversation),
        "differences": differences,
    }
    
    record_migration(
        "verify_conversation_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def get_sqlite_migration_status():
    initialize_database()
    
    table_names = [
        "profile_facts",
        "notes",
        "reminders",
        "conversation_turns",
        "website_registry",
        "website_open_history",
        "app_registry",
        "app_launch_history",
        "app_aliases",
        "app_registry_backups",
        "search_folders",
        "file_search_history",
        "focus_sessions",
        "response_feedback",
        "response_feedback_notes",
        "history_events",
        "work_session_summaries",
        "conversation_summaries",
        "entity_registry",
        "default_apps",
        "migration_runs",
    ]
    
    row_counts = {}
    
    with get_connection() as connection:
        for table_name in table_names:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name}"
            ).fetchone()
            
            row_counts[table_name] = row["count"]
            
        rows = connection.execute(
            """
            SELECT id, name, status, details, created_at
            FROM migration_runs
            ORDER BY id DESC
            LIMIT 5
            """
        ).fetchall()
        
    return {
        "database": get_database_status(),
        "row_counts": row_counts,
        "recent_migrations": [
            {
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "details": json.loads(row["details"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ],
    }
    
def sync_sqlite_website_registry_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    registry = memory_data.get("website_registry", {})
    
    if not isinstance(registry, dict):
        raise ValueError(
            "memory.json website_registry must be a JSON object."
        )
        
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (name, website) in enumerate(
        registry.items(),
        start=1
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Website registry entry {position} needs a valid name."
            )

        if not isinstance(website, dict):
            raise ValueError(
                f"Website registry entry '{name}' must be an object."
            )

        if website.get("name") != name:
            raise ValueError(
                f"Website registry entry '{name}' has a mismatched name."
            )
            
        url = website.get("url")
        allowed = website.get("allowed", False)
        
        if not isinstance(url, str) or not url.strip():
            raise ValueError(
                f"Website registry entry '{name}' needs a URL."
            )
            
        if not isinstance(allowed, bool):
            raise ValueError(
                f"Website registry entry '{name}' allowed must be true or false."
            )
            
        records.append(
            (
                position,
                name,
                url.strip(),
                int(allowed),
                synced_at,
            )
        )
        
    with get_connection() as connection:
        connection.execute("DELETE FROM website_registry")
        
        connection.executemany(
            """
            INSERT INTO website_registry (
                position,
                name,
                url,
                allowed,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            records,
        )
        
    return len(records)
    
def verify_website_registry_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_registry = memory_data.get("website_registry", {})
    sqlite_websites = get_sqlite_website_registry()
    
    differences = []
    json_items = list(json_registry.items())
    
    total_items = max(
        len(json_items),
        len(sqlite_websites),
    )
    
    for index in range(total_items):
        position = index + 1
        
        json_item = (
            json_items[index]
            if index < len(json_items)
            else None
        )
        
        sqlite_website = (
            sqlite_websites[index]
            if index < len(sqlite_websites)
            else None
        )
        
        if json_item is None or sqlite_website is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_website,
            })
            continue
        
        json_name, json_website = json_item
        
        checks = {
            "position": (position, sqlite_website["position"]),
            "name": (json_name, sqlite_website["name"]),
            "url": (
                json_website.get("url"),
                sqlite_website["url"],
            ),
            "allowed": (
                json_website.get("allowed", False),
                sqlite_website["allowed"],
            ),
        }
        
        for field, (json_value, sqlite_value) in checks.items():
            if json_value != sqlite_value:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_value,
                    "sqlite_value": sqlite_value,
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_website_count": len(json_items),
        "sqlite_website_count": len(sqlite_websites),
        "differences": differences,
    }
    
    record_migration(
        "verify_website_registry_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result
    
def migrate_website_registry_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    registry = memory_data.get("website_registry", {})
    
    if not isinstance(registry, dict):
        raise ValueError(
            "memory.json website_registry must be a JSON object."
        )
        
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (name, website) in enumerate(
        registry.items(),
        start=1
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Website registry entry {position} needs a valid name."
            )
            
        if not isinstance(website, dict):
            raise ValueError(
                f"Website registry entry '{name}' must be an object."
            )
            
        if website.get("name") != name:
            raise ValueError(
                f"Website registry entry '{name}' has a mismatched name."
            )
            
        url = website.get("url")
        allowed = website.get("allowed", False)
        
        if not isinstance(url, str) or not url.strip():
            raise ValueError(
                f"Website registry entry '{name}' needs a URL."
            )
            
        if not isinstance(allowed, bool):
            raise ValueError(
                f"Website registry entry '{name}' allowed must be true or false."
            )
            
        records.append(
            (
                position,
                name,
                url.strip(),
                int(allowed),
                migrated_at,
            )
        )
        
    backup_file = create_memory_backup(
        "memory_before_websites_sqlite"
    )
    
    with get_connection() as connection:
        connection.execute("DELETE FROM website_registry")
        
        connection.executemany(
            """
            INSERT INTO website_registry (
                position,
                name,
                url,
                allowed,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            records,
        )
        
    details = {
        "backup_file": str(backup_file),
        "website_count": len(records),
    }
    
    record_migration(
        "migrate_website_registry_from_json",
        "completed",
        details,
    )
    
    return details

def migrate_app_registry_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    registry = memory_data.get("app_registry", {})
    
    if not isinstance(registry, dict):
        raise ValueError(
            "memory.json app_registry must be a JSON object."
        )
        
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (name, app) in enumerate(
        registry.items(),
        start=1,
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"App registry entry {position} needs a valid name."
            )

        if not isinstance(app, dict):
            raise ValueError(
                f"App registry entry '{name}' must be an object."
            )

        if app.get("name") != name:
            raise ValueError(
                f"App registry entry '{name}' has a mismatched name."
            )
            
        command = app.get("command")
        allowed = app.get("allowed", False)
        
        if not isinstance(command, str) or not command.strip():
            raise ValueError(
                f"App registry entry '{name}' needs a command."
            )

        if not isinstance(allowed, bool):
            raise ValueError(
                f"App registry entry '{name}' allowed must be true or false."
            )
            
        records.append(
            (
                position,
                name,
                command.strip(),
                int(allowed),
                migrated_at,
            )
        )
        
    backup_file = create_memory_backup(
        "memory_before_app_registry_sqlite"
    )
    
    with get_connection() as connection:
        connection.execute("DELETE FROM app_registry")
        
        connection.executemany(
            """
            INSERT INTO app_registry (
                position,
                name,
                command,
                allowed,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            records,
        )
        
    details = {
        "backup_file": str(backup_file),
        "app_count": len(records),
    }
    
    record_migration(
        "migrate_app_registry_from_json",
        "completed",
        details,
    )
    
    return details

def migrate_focus_sessions_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    sessions = memory_data.get("focus_sessions", [])

    if not isinstance(sessions, list):
        raise ValueError(
            "memory.json focus_sessions must be a JSON list."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    missing_duration_seconds = 0

    for position, session in enumerate(sessions, start=1):
        if not isinstance(session, dict):
            raise ValueError(
                f"Focus session {position} must be an object."
            )

        task = session.get("task")
        started_at = session.get("started_at")
        ended_at = session.get("ended_at")
        duration = session.get("duration")
        notes = session.get("notes", [])
        duration_seconds = session.get("duration_seconds")

        required_fields = {
            "task": task,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration": duration,
        }

        for field, value in required_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Focus session {position} {field} must be text."
                )

        if not isinstance(notes, list):
            raise ValueError(
                f"Focus session {position} notes must be a list."
            )

        if not all(isinstance(note, str) for note in notes):
            raise ValueError(
                f"Focus session {position} notes must contain text only."
            )

        if duration_seconds is None:
            missing_duration_seconds += 1
        elif (
            isinstance(duration_seconds, bool)
            or not isinstance(duration_seconds, int)
            or duration_seconds < 0
        ):
            raise ValueError(
                f"Focus session {position} duration_seconds "
                "must be a non-negative integer."
            )

        records.append(
            (
                position,
                task,
                started_at,
                ended_at,
                duration,
                duration_seconds,
                json.dumps(notes),
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_focus_sessions_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM focus_sessions")

        connection.executemany(
            """
            INSERT INTO focus_sessions (
                position,
                task,
                started_at,
                ended_at,
                duration,
                duration_seconds,
                notes_json,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "focus_session_count": len(records),
        "sessions_without_duration_seconds": (
            missing_duration_seconds
        ),
    }

    record_migration(
        "migrate_focus_sessions_from_json",
        "completed",
        details,
    )

    return details

def migrate_response_feedback_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    feedback_items = memory_data.get("response_feedback", [])

    if not isinstance(feedback_items, list):
        raise ValueError(
            "memory.json response_feedback must be a JSON list."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, item in enumerate(feedback_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Response feedback {position} must be an object."
            )

        timestamp = item.get("timestamp")
        feedback = item.get("feedback")
        last_intent = item.get("last_intent")
        last_group = item.get("last_group")
        last_text = item.get("last_text")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Response feedback {position} timestamp must be text."
            )

        if feedback not in ["helpful", "not_helpful"]:
            raise ValueError(
                f"Response feedback {position} has an invalid value."
            )

        optional_fields = {
            "last_intent": last_intent,
            "last_group": last_group,
            "last_text": last_text,
        }

        for field, value in optional_fields.items():
            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"Response feedback {position} {field} "
                    "must be text or None."
                )

        records.append(
            (
                position,
                timestamp,
                feedback,
                last_intent,
                last_group,
                last_text,
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_response_feedback_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM response_feedback")

        connection.executemany(
            """
            INSERT INTO response_feedback (
                position,
                timestamp,
                feedback,
                last_intent,
                last_group,
                last_text,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "response_feedback_count": len(records),
    }

    record_migration(
        "migrate_response_feedback_from_json",
        "completed",
        details,
    )

    return details

def migrate_response_feedback_notes_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    notes = memory_data.get("response_feedback_notes", [])

    if not isinstance(notes, list):
        raise ValueError(
            "memory.json response_feedback_notes "
            "must be a JSON list."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, item in enumerate(notes, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Response feedback note {position} must be an object."
            )

        timestamp = item.get("timestamp")
        note = item.get("note")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Response feedback note {position} timestamp "
                "must be text."
            )

        if not isinstance(note, str) or not note.strip():
            raise ValueError(
                f"Response feedback note {position} note "
                "must be text."
            )

        records.append(
            (
                position,
                timestamp,
                note,
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_response_feedback_notes_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM response_feedback_notes")

        connection.executemany(
            """
            INSERT INTO response_feedback_notes (
                position,
                timestamp,
                note,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "response_feedback_note_count": len(records),
    }

    record_migration(
        "migrate_response_feedback_notes_from_json",
        "completed",
        details,
    )

    return details

def migrate_history_events_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    history = memory_data.get("history", [])

    if not isinstance(history, list):
        raise ValueError(
            "memory.json history must be a JSON list."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    missing_importance = 0

    for position, event in enumerate(history, start=1):
        if not isinstance(event, dict):
            raise ValueError(
                f"History event {position} must be an object."
            )

        user_input = event.get("user_input")
        intent = event.get("intent")
        intent_group = event.get("group")
        confidence = event.get("confidence")
        source = event.get("source")
        result = event.get("result")
        timestamp = event.get("timestamp")
        importance = event.get("importance")

        text_fields = {
            "user_input": user_input,
            "intent": intent,
            "group": intent_group,
            "source": source,
            "result": result,
            "timestamp": timestamp,
        }

        for field, value in text_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"History event {position} {field} must be text."
                )

        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
        ):
            raise ValueError(
                f"History event {position} confidence must be numeric."
            )

        if importance is None:
            missing_importance += 1
        elif (
            isinstance(importance, bool)
            or not isinstance(importance, (int, float))
        ):
            raise ValueError(
                f"History event {position} importance must be numeric."
            )

        records.append(
            (
                position,
                user_input,
                intent,
                intent_group,
                float(confidence),
                source,
                result,
                timestamp,
                float(importance) if importance is not None else None,
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_history_events_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM history_events")

        connection.executemany(
            """
            INSERT INTO history_events (
                position,
                user_input,
                intent,
                intent_group,
                confidence,
                source,
                result,
                timestamp,
                importance,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "history_event_count": len(records),
        "events_without_importance": missing_importance,
    }

    record_migration(
        "migrate_history_events_from_json",
        "completed",
        details,
    )

    return details

def migrate_work_session_summaries_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    summaries = memory_data.get("work_session_summaries", [])

    if not isinstance(summaries, list):
        raise ValueError(
            "memory.json work_session_summaries "
            "must be a JSON list."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, item in enumerate(summaries, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Work session summary {position} must be an object."
            )

        timestamp = item.get("timestamp")
        total_sessions = item.get("total_sessions")
        total_seconds = item.get("total_seconds")
        top_task = item.get("top_task")
        notes_count = item.get("notes_count")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Work session summary {position} timestamp "
                "must be text."
            )

        integer_fields = {
            "total_sessions": total_sessions,
            "total_seconds": total_seconds,
            "notes_count": notes_count,
        }

        for field, value in integer_fields.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"Work session summary {position} {field} "
                    "must be a non-negative integer."
                )

        if top_task is not None and not isinstance(top_task, str):
            raise ValueError(
                f"Work session summary {position} top_task "
                "must be text or None."
            )

        records.append(
            (
                position,
                timestamp,
                total_sessions,
                total_seconds,
                top_task,
                notes_count,
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_work_session_summaries_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM work_session_summaries")

        connection.executemany(
            """
            INSERT INTO work_session_summaries (
                position,
                timestamp,
                total_sessions,
                total_seconds,
                top_task,
                notes_count,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "work_session_summary_count": len(records),
    }

    record_migration(
        "migrate_work_session_summaries_from_json",
        "completed",
        details,
    )

    return details

def migrate_conversation_summaries_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    summaries = memory_data.get("summaries", [])

    if not isinstance(summaries, list):
        raise ValueError(
            "memory.json summaries must be a JSON list."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, item in enumerate(summaries, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Conversation summary {position} must be an object."
            )

        summary = item.get("summary")
        timestamp = item.get("timestamp")

        if not isinstance(summary, str) or not summary.strip():
            raise ValueError(
                f"Conversation summary {position} summary "
                "must be text."
            )

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Conversation summary {position} timestamp "
                "must be text."
            )

        records.append(
            (
                position,
                summary,
                timestamp,
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_conversation_summaries_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM conversation_summaries")

        connection.executemany(
            """
            INSERT INTO conversation_summaries (
                position,
                summary,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "conversation_summary_count": len(records),
    }

    record_migration(
        "migrate_conversation_summaries_from_json",
        "completed",
        details,
    )

    return details

def migrate_entity_registry_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    entities = memory_data.get("entities", {})

    if not isinstance(entities, dict):
        raise ValueError(
            "memory.json entities must be a JSON object."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    counts = {}

    for entity_type in ["games", "apps"]:
        values = entities.get(entity_type, [])

        if not isinstance(values, list):
            raise ValueError(
                f"memory.json entities.{entity_type} "
                "must be a JSON list."
            )

        counts[entity_type] = len(values)

        for position, value in enumerate(values, start=1):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Entity {entity_type} {position} must be text."
                )

            records.append(
                (
                    entity_type,
                    position,
                    value,
                    migrated_at,
                )
            )

    backup_file = create_memory_backup(
        "memory_before_entity_registry_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM entity_registry")

        connection.executemany(
            """
            INSERT INTO entity_registry (
                entity_type,
                position,
                value,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "entity_count": len(records),
        "games_count": counts["games"],
        "apps_count": counts["apps"],
    }

    record_migration(
        "migrate_entity_registry_from_json",
        "completed",
        details,
    )

    return details

def get_sqlite_entities(entity_type):
    initialize_database()

    if entity_type not in ["games", "apps"]:
        raise ValueError(
            "Entity type must be 'games' or 'apps'."
        )

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                entity_type,
                position,
                value,
                migrated_at
            FROM entity_registry
            WHERE entity_type = ?
            ORDER BY position
            """,
            (entity_type,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "entity_type": row["entity_type"],
            "position": row["position"],
            "value": row["value"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_entity_registry_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    entities = memory_data.get("entities", {})
    differences = []

    for entity_type in ["games", "apps"]:
        json_values = entities.get(entity_type, [])
        sqlite_items = get_sqlite_entities(entity_type)

        total_items = max(
            len(json_values),
            len(sqlite_items),
        )

        for index in range(total_items):
            position = index + 1

            json_value = (
                json_values[index]
                if index < len(json_values)
                else None
            )

            sqlite_item = (
                sqlite_items[index]
                if index < len(sqlite_items)
                else None
            )

            if json_value is None or sqlite_item is None:
                differences.append({
                    "entity_type": entity_type,
                    "position": position,
                    "field": "record",
                    "json_value": json_value,
                    "sqlite_value": sqlite_item,
                })
                continue

            if sqlite_item["position"] != position:
                differences.append({
                    "entity_type": entity_type,
                    "position": position,
                    "field": "position",
                    "json_value": position,
                    "sqlite_value": sqlite_item["position"],
                })

            if json_value != sqlite_item["value"]:
                differences.append({
                    "entity_type": entity_type,
                    "position": position,
                    "field": "value",
                    "json_value": json_value,
                    "sqlite_value": sqlite_item["value"],
                })

    matches = not differences

    result = {
        "matches": matches,
        "json_games_count": len(entities.get("games", [])),
        "sqlite_games_count": len(get_sqlite_entities("games")),
        "json_apps_count": len(entities.get("apps", [])),
        "sqlite_apps_count": len(get_sqlite_entities("apps")),
        "differences": differences,
    }

    record_migration(
        "verify_entity_registry_migration",
        "completed" if matches else "mismatch",
        result,
    )

    return result

def get_sqlite_conversation_summaries(limit=None):
    initialize_database()

    query = """
        SELECT
            id,
            position,
            summary,
            timestamp,
            migrated_at
        FROM conversation_summaries
    """

    parameters = ()

    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)

    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    if limit is not None:
        rows = list(reversed(rows))

    return [
        {
            "id": row["id"],
            "position": row["position"],
            "summary": row["summary"],
            "timestamp": row["timestamp"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_conversation_summaries_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    json_summaries = memory_data.get("summaries", [])
    sqlite_summaries = get_sqlite_conversation_summaries()

    differences = []
    total_items = max(
        len(json_summaries),
        len(sqlite_summaries),
    )

    for index in range(total_items):
        position = index + 1

        json_item = (
            json_summaries[index]
            if index < len(json_summaries)
            else None
        )

        sqlite_item = (
            sqlite_summaries[index]
            if index < len(sqlite_summaries)
            else None
        )

        if json_item is None or sqlite_item is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_item,
            })
            continue

        if sqlite_item["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_item["position"],
            })

        for field in ["summary", "timestamp"]:
            if json_item.get(field) != sqlite_item[field]:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_item.get(field),
                    "sqlite_value": sqlite_item[field],
                })

    matches = not differences

    result = {
        "matches": matches,
        "json_conversation_summary_count": len(json_summaries),
        "sqlite_conversation_summary_count": len(sqlite_summaries),
        "differences": differences,
    }

    record_migration(
        "verify_conversation_summaries_migration",
        "completed" if matches else "mismatch",
        result,
    )

    return result

def add_sqlite_conversation_summary(position, item):
    initialize_database()

    if not isinstance(position, int) or position < 1:
        raise ValueError(
            "Conversation summary position must be a positive integer."
        )

    if not isinstance(item, dict):
        raise ValueError(
            "Conversation summary must be an object."
        )

    summary = item.get("summary")
    timestamp = item.get("timestamp")

    if not isinstance(summary, str) or not summary.strip():
        raise ValueError(
            "Conversation summary summary must be text."
        )

    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError(
            "Conversation summary timestamp must be text."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO conversation_summaries (
                position,
                summary,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                position,
                summary,
                timestamp,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    return cursor.lastrowid

def get_sqlite_work_session_summaries(limit=None):
    initialize_database()

    query = """
        SELECT
            id,
            position,
            timestamp,
            total_sessions,
            total_seconds,
            top_task,
            notes_count,
            migrated_at
        FROM work_session_summaries
    """

    parameters = ()

    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)

    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    if limit is not None:
        rows = list(reversed(rows))

    return [
        {
            "id": row["id"],
            "position": row["position"],
            "timestamp": row["timestamp"],
            "total_sessions": row["total_sessions"],
            "total_seconds": row["total_seconds"],
            "top_task": row["top_task"],
            "notes_count": row["notes_count"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_work_session_summaries_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    json_summaries = memory_data.get(
        "work_session_summaries",
        [],
    )
    sqlite_summaries = get_sqlite_work_session_summaries()

    differences = []
    total_items = max(
        len(json_summaries),
        len(sqlite_summaries),
    )

    fields = [
        "timestamp",
        "total_sessions",
        "total_seconds",
        "top_task",
        "notes_count",
    ]

    for index in range(total_items):
        position = index + 1

        json_item = (
            json_summaries[index]
            if index < len(json_summaries)
            else None
        )

        sqlite_item = (
            sqlite_summaries[index]
            if index < len(sqlite_summaries)
            else None
        )

        if json_item is None or sqlite_item is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_item,
            })
            continue

        if sqlite_item["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_item["position"],
            })

        for field in fields:
            if json_item.get(field) != sqlite_item[field]:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_item.get(field),
                    "sqlite_value": sqlite_item[field],
                })

    matches = not differences

    result = {
        "matches": matches,
        "json_work_session_summary_count": len(json_summaries),
        "sqlite_work_session_summary_count": len(sqlite_summaries),
        "differences": differences,
    }

    record_migration(
        "verify_work_session_summaries_migration",
        "completed" if matches else "mismatch",
        result,
    )

    return result

def add_sqlite_work_session_summary(position, item):
    initialize_database()

    if not isinstance(position, int) or position < 1:
        raise ValueError(
            "Work session summary position must be a positive integer."
        )

    if not isinstance(item, dict):
        raise ValueError(
            "Work session summary must be an object."
        )

    timestamp = item.get("timestamp")
    total_sessions = item.get("total_sessions")
    total_seconds = item.get("total_seconds")
    top_task = item.get("top_task")
    notes_count = item.get("notes_count")

    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError(
            "Work session summary timestamp must be text."
        )

    integer_fields = {
        "total_sessions": total_sessions,
        "total_seconds": total_seconds,
        "notes_count": notes_count,
    }

    for field, value in integer_fields.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"Work session summary {field} "
                "must be a non-negative integer."
            )

    if top_task is not None and not isinstance(top_task, str):
        raise ValueError(
            "Work session summary top_task must be text or None."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO work_session_summaries (
                position,
                timestamp,
                total_sessions,
                total_seconds,
                top_task,
                notes_count,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position,
                timestamp,
                total_sessions,
                total_seconds,
                top_task,
                notes_count,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    return cursor.lastrowid


def sync_sqlite_work_session_summaries_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    summaries = memory_data.get("work_session_summaries", [])

    if not isinstance(summaries, list):
        raise ValueError(
            "memory.json work_session_summaries "
            "must be a JSON list."
        )

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, item in enumerate(summaries, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Work session summary {position} must be an object."
            )

        timestamp = item.get("timestamp")
        total_sessions = item.get("total_sessions")
        total_seconds = item.get("total_seconds")
        top_task = item.get("top_task")
        notes_count = item.get("notes_count")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Work session summary {position} timestamp "
                "must be text."
            )

        integer_fields = {
            "total_sessions": total_sessions,
            "total_seconds": total_seconds,
            "notes_count": notes_count,
        }

        for field, value in integer_fields.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"Work session summary {position} {field} "
                    "must be a non-negative integer."
                )

        if top_task is not None and not isinstance(top_task, str):
            raise ValueError(
                f"Work session summary {position} top_task "
                "must be text or None."
            )

        records.append(
            (
                position,
                timestamp,
                total_sessions,
                total_seconds,
                top_task,
                notes_count,
                synced_at,
            )
        )

    with get_connection() as connection:
        connection.execute("DELETE FROM work_session_summaries")

        connection.executemany(
            """
            INSERT INTO work_session_summaries (
                position,
                timestamp,
                total_sessions,
                total_seconds,
                top_task,
                notes_count,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    return len(records)

def get_sqlite_history_events(limit=None):
    initialize_database()

    query = """
        SELECT
            id,
            position,
            user_input,
            intent,
            intent_group,
            confidence,
            source,
            result,
            timestamp,
            importance,
            migrated_at
        FROM history_events
    """

    parameters = ()

    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)

    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    if limit is not None:
        rows = list(reversed(rows))

    return [
        {
            "id": row["id"],
            "position": row["position"],
            "user_input": row["user_input"],
            "intent": row["intent"],
            "group": row["intent_group"],
            "confidence": row["confidence"],
            "source": row["source"],
            "result": row["result"],
            "timestamp": row["timestamp"],
            "importance": row["importance"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_history_events_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    json_history = memory_data.get("history", [])
    sqlite_history = get_sqlite_history_events()

    differences = []
    total_items = max(
        len(json_history),
        len(sqlite_history),
    )

    fields = [
        "user_input",
        "intent",
        "group",
        "confidence",
        "source",
        "result",
        "timestamp",
        "importance",
    ]

    for index in range(total_items):
        position = index + 1

        json_event = (
            json_history[index]
            if index < len(json_history)
            else None
        )

        sqlite_event = (
            sqlite_history[index]
            if index < len(sqlite_history)
            else None
        )

        if json_event is None or sqlite_event is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_event,
                "sqlite_value": sqlite_event,
            })
            continue

        if sqlite_event["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_event["position"],
            })

        for field in fields:
            if json_event.get(field) != sqlite_event[field]:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_event.get(field),
                    "sqlite_value": sqlite_event[field],
                })

    matches = not differences

    result = {
        "matches": matches,
        "json_history_event_count": len(json_history),
        "sqlite_history_event_count": len(sqlite_history),
        "differences": differences,
    }

    record_migration(
        "verify_history_events_migration",
        "completed" if matches else "mismatch",
        result,
    )

    return result

def add_sqlite_history_event(position, event):
    initialize_database()

    if not isinstance(position, int) or position < 1:
        raise ValueError(
            "History event position must be a positive integer."
        )

    if not isinstance(event, dict):
        raise ValueError("History event must be an object.")

    user_input = event.get("user_input")
    intent = event.get("intent")
    intent_group = event.get("group")
    confidence = event.get("confidence")
    source = event.get("source")
    result = event.get("result")
    timestamp = event.get("timestamp")
    importance = event.get("importance")

    text_fields = {
        "user_input": user_input,
        "intent": intent,
        "group": intent_group,
        "source": source,
        "result": result,
        "timestamp": timestamp,
    }

    for field, value in text_fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"History event {field} must be text."
            )

    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
    ):
        raise ValueError(
            "History event confidence must be numeric."
        )

    if importance is not None and (
        isinstance(importance, bool)
        or not isinstance(importance, (int, float))
    ):
        raise ValueError(
            "History event importance must be numeric."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO history_events (
                position,
                user_input,
                intent,
                intent_group,
                confidence,
                source,
                result,
                timestamp,
                importance,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position,
                user_input,
                intent,
                intent_group,
                float(confidence),
                source,
                result,
                timestamp,
                float(importance)
                if importance is not None
                else None,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    return cursor.lastrowid

def get_sqlite_response_feedback_notes(limit=None):
    initialize_database()

    query = """
        SELECT
            id,
            position,
            timestamp,
            note,
            migrated_at
        FROM response_feedback_notes
    """

    parameters = ()

    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)

    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    if limit is not None:
        rows = list(reversed(rows))

    return [
        {
            "id": row["id"],
            "position": row["position"],
            "timestamp": row["timestamp"],
            "note": row["note"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_response_feedback_notes_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    json_notes = memory_data.get("response_feedback_notes", [])
    sqlite_notes = get_sqlite_response_feedback_notes()

    differences = []
    total_items = max(
        len(json_notes),
        len(sqlite_notes),
    )

    for index in range(total_items):
        position = index + 1

        json_note = (
            json_notes[index]
            if index < len(json_notes)
            else None
        )

        sqlite_note = (
            sqlite_notes[index]
            if index < len(sqlite_notes)
            else None
        )

        if json_note is None or sqlite_note is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_note,
                "sqlite_value": sqlite_note,
            })
            continue

        if sqlite_note["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_note["position"],
            })

        for field in ["timestamp", "note"]:
            if json_note.get(field) != sqlite_note[field]:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_note.get(field),
                    "sqlite_value": sqlite_note[field],
                })

    matches = not differences

    result = {
        "matches": matches,
        "json_response_feedback_note_count": len(json_notes),
        "sqlite_response_feedback_note_count": len(sqlite_notes),
        "differences": differences,
    }

    record_migration(
        "verify_response_feedback_notes_migration",
        "completed" if matches else "mismatch",
        result,
    )

    return result

def add_sqlite_response_feedback_note(position, item):
    initialize_database()

    if not isinstance(position, int) or position < 1:
        raise ValueError(
            "Response feedback note position must be a positive integer."
        )

    if not isinstance(item, dict):
        raise ValueError(
            "Response feedback note must be an object."
        )

    timestamp = item.get("timestamp")
    note = item.get("note")

    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError(
            "Response feedback note timestamp must be text."
        )

    if not isinstance(note, str) or not note.strip():
        raise ValueError(
            "Response feedback note must be text."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO response_feedback_notes (
                position,
                timestamp,
                note,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                position,
                timestamp,
                note,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    return cursor.lastrowid


def sync_sqlite_response_feedback_notes_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    notes = memory_data.get("response_feedback_notes", [])

    if not isinstance(notes, list):
        raise ValueError(
            "memory.json response_feedback_notes "
            "must be a JSON list."
        )

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, item in enumerate(notes, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Response feedback note {position} must be an object."
            )

        timestamp = item.get("timestamp")
        note = item.get("note")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Response feedback note {position} timestamp "
                "must be text."
            )

        if not isinstance(note, str) or not note.strip():
            raise ValueError(
                f"Response feedback note {position} note "
                "must be text."
            )

        records.append(
            (
                position,
                timestamp,
                note,
                synced_at,
            )
        )

    with get_connection() as connection:
        connection.execute("DELETE FROM response_feedback_notes")

        connection.executemany(
            """
            INSERT INTO response_feedback_notes (
                position,
                timestamp,
                note,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )

    return len(records)

def get_sqlite_response_feedback(limit=None):
    initialize_database()
    
    query = """
        SELECT
            id,
            position,
            timestamp,
            feedback,
            last_intent,
            last_group,
            last_text,
            migrated_at
        FROM response_feedback
    """
    
    parameters = ()

    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)

    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    if limit is not None:
        rows = list(reversed(rows))

    return [
        {
            "id": row["id"],
            "position": row["position"],
            "timestamp": row["timestamp"],
            "feedback": row["feedback"],
            "last_intent": row["last_intent"],
            "last_group": row["last_group"],
            "last_text": row["last_text"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_response_feedback_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_items = memory_data.get("response_feedback", [])
    sqlite_items = get_sqlite_response_feedback()

    differences = []
    total_items = max(
        len(json_items),
        len(sqlite_items),
    )
    
    fields = [
        "timestamp",
        "feedback",
        "last_intent",
        "last_group",
        "last_text",
    ]

    for index in range(total_items):
        position = index + 1

        json_item = (
            json_items[index]
            if index < len(json_items)
            else None
        )

        sqlite_item = (
            sqlite_items[index]
            if index < len(sqlite_items)
            else None
        )

        if json_item is None or sqlite_item is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_item,
            })
            continue

        if sqlite_item["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_item["position"],
            })

        for field in fields:
            if json_item.get(field) != sqlite_item[field]:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_item.get(field),
                    "sqlite_value": sqlite_item[field],
                })

    matches = not differences

    result = {
        "matches": matches,
        "json_response_feedback_count": len(json_items),
        "sqlite_response_feedback_count": len(sqlite_items),
        "differences": differences,
    }

    record_migration(
        "verify_response_feedback_migration",
        "completed" if matches else "mismatch",
        result,
    )

    return result

def add_sqlite_response_feedback(position, item):
    initialize_database()
    
    if not isinstance(position, int) or position < 1:
        raise ValueError(
            "Response feedback position must be a positive integer."
        )
        
    if not isinstance(item, dict):
        raise ValueError("Response feedback must be an object.")
    
    timestamp = item.get("timestamp")
    feedback = item.get("feedback")
    last_intent = item.get("last_intent")
    last_group = item.get("last_group")
    last_text = item.get("last_text")
    
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError(
            "Response feedback timestamp must be text."
        )
        
    if feedback not in ["helpful", "not_helpful"]:
        raise ValueError("Response feedback has an invalid value.")
    
    optional_fields = {
        "last_intent": last_intent,
        "last_group": last_group,
        "last_text": last_text,
    }
    
    for field, value in optional_fields.items():
        if value is not None and not isinstance(value, str):
            raise ValueError(
                f"Response feedback {field} must be text or None."
            )
            
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO response_feedback (
                position,
                timestamp,
                feedback,
                last_intent,
                last_group,
                last_text,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position,
                timestamp,
                feedback,
                last_intent,
                last_group,
                last_text,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        
def sync_sqlite_response_feedback_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    feedback_items = memory_data.get("response_feedback", [])

    if not isinstance(feedback_items, list):
        raise ValueError(
            "memory.json response_feedback must be a JSON list."
        )

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, item in enumerate(feedback_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Response feedback {position} must be an object."
            )

        timestamp = item.get("timestamp")
        feedback = item.get("feedback")
        last_intent = item.get("last_intent")
        last_group = item.get("last_group")
        last_text = item.get("last_text")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Response feedback {position} timestamp must be text."
            )

        if feedback not in ["helpful", "not_helpful"]:
            raise ValueError(
                f"Response feedback {position} has an invalid value."
            )

        optional_fields = {
            "last_intent": last_intent,
            "last_group": last_group,
            "last_text": last_text,
        }

        for field, value in optional_fields.items():
            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"Response feedback {position} {field} "
                    "must be text or None."
                )

        records.append(
            (
                position,
                timestamp,
                feedback,
                last_intent,
                last_group,
                last_text,
                synced_at,
            )
        )

    with get_connection() as connection:
        connection.execute("DELETE FROM response_feedback")

        connection.executemany(
            """
            INSERT INTO response_feedback (
                position,
                timestamp,
                feedback,
                last_intent,
                last_group,
                last_text,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    return len(records)

def get_sqlite_focus_sessions(limit=None):
    initialize_database()
    
    query = """
        SELECT
            id,
            position,
            task,
            started_at,
            ended_at,
            duration,
            duration_seconds,
            notes_json,
            migrated_at
        FROM focus_sessions
    """
    
    parameters = ()
    
    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)
        
    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()
        
    if limit is not None:
        rows = list(reversed(rows))
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "task": row["task"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "duration": row["duration"],
            "duration_seconds": row["duration_seconds"],
            "notes": json.loads(row["notes_json"]),
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def verify_focus_sessions_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_sessions = memory_data.get("focus_sessions", [])
    sqlite_sessions = get_sqlite_focus_sessions()

    differences = []
    total_items = max(
        len(json_sessions),
        len(sqlite_sessions),
    )

    fields = [
        "task",
        "started_at",
        "ended_at",
        "duration",
        "duration_seconds",
        "notes",
    ]

    for index in range(total_items):
        position = index + 1

        json_session = (
            json_sessions[index]
            if index < len(json_sessions)
            else None
        )

        sqlite_session = (
            sqlite_sessions[index]
            if index < len(sqlite_sessions)
            else None
        )

        if json_session is None or sqlite_session is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_session,
                "sqlite_value": sqlite_session,
            })
            continue

        if sqlite_session["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_session["position"],
            })

        for field in fields:
            json_value = json_session.get(field)

            if field == "notes":
                json_value = json_session.get("notes", [])

            if json_value != sqlite_session[field]:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_value,
                    "sqlite_value": sqlite_session[field],
                })

    matches = not differences

    result = {
        "matches": matches,
        "json_focus_session_count": len(json_sessions),
        "sqlite_focus_session_count": len(sqlite_sessions),
        "differences": differences,
    }

    record_migration(
        "verify_focus_sessions_migration",
        "completed" if matches else "mismatch",
        result,
    )

    return result

def sync_sqlite_focus_sessions_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    sessions = memory_data.get("focus_sessions", [])

    if not isinstance(sessions, list):
        raise ValueError(
            "memory.json focus_sessions must be a JSON list."
        )

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, session in enumerate(sessions, start=1):
        if not isinstance(session, dict):
            raise ValueError(
                f"Focus session {position} must be an object."
            )

        task = session.get("task")
        started_at = session.get("started_at")
        ended_at = session.get("ended_at")
        duration = session.get("duration")
        notes = session.get("notes", [])
        duration_seconds = session.get("duration_seconds")

        required_fields = {
            "task": task,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration": duration,
        }

        for field, value in required_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Focus session {position} {field} must be text."
                )

        if not isinstance(notes, list):
            raise ValueError(
                f"Focus session {position} notes must be a list."
            )

        if not all(isinstance(note, str) for note in notes):
            raise ValueError(
                f"Focus session {position} notes must contain text only."
            )

        if duration_seconds is not None and (
            isinstance(duration_seconds, bool)
            or not isinstance(duration_seconds, int)
            or duration_seconds < 0
        ):
            raise ValueError(
                f"Focus session {position} duration_seconds "
                "must be a non-negative integer."
            )

        records.append(
            (
                position,
                task,
                started_at,
                ended_at,
                duration,
                duration_seconds,
                json.dumps(notes),
                synced_at,
            )
        )

    with get_connection() as connection:
        connection.execute("DELETE FROM focus_sessions")

        connection.executemany(
            """
            INSERT INTO focus_sessions (
                position,
                task,
                started_at,
                ended_at,
                duration,
                duration_seconds,
                notes_json,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    return len(records)
         
def get_sqlite_app_registry():
    initialize_database()
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                position,
                name,
                command,
                allowed,
                migrated_at
            FROM app_registry
            ORDER BY position
            """
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "name": row["name"],
            "command": row["command"],
            "allowed": bool(row["allowed"]),
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def sync_sqlite_app_registry_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    registry = memory_data.get("app_registry", {})
    
    if not isinstance(registry, dict):
        raise ValueError(
            "memory.json app_registry must be a JSON object."
        )
        
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (name, app) in enumerate(
        registry.items(),
        start=1,
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"App registry entry {position} needs a valid name."
            )

        if not isinstance(app, dict):
            raise ValueError(
                f"App registry entry '{name}' must be an object."
            )

        if app.get("name") != name:
            raise ValueError(
                f"App registry entry '{name}' has a mismatched name."
            )
            
        command = app.get("command")
        allowed = app.get("allowed", False)
        
        if not isinstance(command, str) or not command.strip():
            raise ValueError(
                f"App registry entry '{name}' needs a command."
            )

        if not isinstance(allowed, bool):
            raise ValueError(
                f"App registry entry '{name}' allowed must be true or false."
            )
            
        records.append(
            (
                position,
                name,
                command.strip(),
                int(allowed),
                synced_at,
            )
        )
        
    with get_connection() as connection:
        connection.execute("DELETE FROM app_registry")
        
        connection.executemany(
            """
            INSERT INTO app_registry (
                position,
                name,
                command,
                allowed,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            records,
        )
        
    return len(records)
    
def verify_app_registry_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_registry = memory_data.get("app_registry", {})
    sqlite_apps = get_sqlite_app_registry()
    
    differences = []
    json_items = list(json_registry.items())
    
    total_items = max(
        len(json_items),
        len(sqlite_apps),
    )
    
    for index in range(total_items):
        position = index + 1
        
        json_item = (
            json_items[index]
            if index < len(json_items)
            else None
        )
        
        sqlite_app = (
            sqlite_apps[index]
            if index < len(sqlite_apps)
            else None
        )
        
        if json_item is None or sqlite_app is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_app,
            })
            continue
        
        json_name, json_app = json_item
        
        checks = {
            "position": (position, sqlite_app["position"]),
            "name": (json_name, sqlite_app["name"]),
            "command": (
                json_app.get("command"),
                sqlite_app["command"],
            ),
            "allowed": (
                json_app.get("allowed", False),
                sqlite_app["allowed"],
            ),
        }
        
        for field, (json_value, sqlite_value) in checks.items():
            if json_value != sqlite_value:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_value,
                    "sqlite_value": sqlite_value,
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_app_count": len(json_items),
        "sqlite_app_count": len(sqlite_apps),
        "differences": differences,
    }
    
    record_migration(
        "verify_app_registry_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def migrate_app_registry_backups_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    backups = memory_data.get("app_registry_backups", [])
    
    if not isinstance(backups, list):
        raise ValueError(
            "memory.json app_registry_backups must be a JSON list."
        )
        
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, backup in enumerate(backups, start=1):
        if not isinstance(backup, dict):
            raise ValueError(
                f"App registry backup {position} must be an object."
            )
            
        timestamp = backup.get("timestamp")
        app_registry = backup.get("app_registry")
        app_aliases = backup.get("app_aliases")
        default_apps = backup.get("default_apps")
        
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"App registry backup {position} needs a timestamp."
            )
            
        if not isinstance(app_registry, dict):
            raise ValueError(
                f"App registry backup {position} app_registry must be an object."
            )

        if not isinstance(app_aliases, dict):
            raise ValueError(
                f"App registry backup {position} app_aliases must be an object."
            )

        if not isinstance(default_apps, dict):
            raise ValueError(
                f"App registry backup {position} default_apps must be an object."
            )
            
        records.append(
            (
                position,
                timestamp,
                json.dumps(app_registry),
                json.dumps(app_aliases),
                json.dumps(default_apps),
                migrated_at,
            )
        )
        
    backup_file = create_memory_backup(
        "memory_before_app_registry_backups_sqlite"
    )
    
    with get_connection() as connection:
        connection.execute("DELETE FROM app_registry_backups")
        
        connection.executemany(
            """
            INSERT INTO app_registry_backups (
                position,
                timestamp,
                app_registry_json,
                app_aliases_json,
                default_apps_json,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        
    details = {
        "backup_file": str(backup_file),
        "app_registry_backup_count": len(records),
    }
    
    record_migration(
        "migrate_app_registry_backups_from_json",
        "completed",
        details,
    )
    
    return details

def get_sqlite_app_registry_backups():
    initialize_database()
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT 
                id,
                position,
                timestamp,
                app_registry_json,
                app_aliases_json,
                default_apps_json,
                migrated_at
            FROM app_registry_backups
            ORDER BY position
            """
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "timestamp": row["timestamp"],
            "app_registry": json.loads(row["app_registry_json"]),
            "app_aliases": json.loads(row["app_aliases_json"]),
            "default_apps": json.loads(row["default_apps_json"]),
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def sync_sqlite_app_registry_backups_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    backups = memory_data.get("app_registry_backups", [])

    if not isinstance(backups, list):
        raise ValueError(
            "memory.json app_registry_backups must be a JSON list."
        )

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, backup in enumerate(backups, start=1):
        if not isinstance(backup, dict):
            raise ValueError(
                f"App registry backup {position} must be an object."
            )

        timestamp = backup.get("timestamp")
        app_registry = backup.get("app_registry")
        app_aliases = backup.get("app_aliases")
        default_apps = backup.get("default_apps")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"App registry backup {position} needs a timestamp."
            )

        if not isinstance(app_registry, dict):
            raise ValueError(
                f"App registry backup {position} app_registry must be an object."
            )

        if not isinstance(app_aliases, dict):
            raise ValueError(
                f"App registry backup {position} app_aliases must be an object."
            )

        if not isinstance(default_apps, dict):
            raise ValueError(
                f"App registry backup {position} default_apps must be an object."
            )

        records.append(
            (
                position,
                timestamp,
                json.dumps(app_registry),
                json.dumps(app_aliases),
                json.dumps(default_apps),
                synced_at,
            )
        )

    with get_connection() as connection:
        connection.execute("DELETE FROM app_registry_backups")

        connection.executemany(
            """
            INSERT INTO app_registry_backups (
                position,
                timestamp,
                app_registry_json,
                app_aliases_json,
                default_apps_json,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    return len(records)
    
def verify_app_registry_backups_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_backups = memory_data.get("app_registry_backups", [])
    sqlite_backups = get_sqlite_app_registry_backups()
    
    differences = []
    total_items = max(
        len(json_backups),
        len(sqlite_backups),
    )
    
    fields = [
        "timestamp",
        "app_registry",
        "app_aliases",
        "default_apps",
    ]
    
    for index in range(total_items):
        position = index + 1
        
        json_backup = (
            json_backups[index]
            if index < len(json_backups)
            else None
        )

        sqlite_backup = (
            sqlite_backups[index]
            if index < len(sqlite_backups)
            else None
        )
        
        if json_backup is None or sqlite_backup is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_backup,
                "sqlite_value": sqlite_backup,
            })
            continue
        
        if sqlite_backup["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_backup["position"],
            })
            
        for field in fields:
            if json_backup.get(field) != sqlite_backup.get(field):
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_backup.get(field),
                    "sqlite_value": sqlite_backup.get(field),
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_app_registry_backup_count": len(json_backups),
        "sqlite_app_registry_backup_count": len(sqlite_backups),
        "differences": differences,
    }
    
    record_migration(
        "verify_app_registry_backups_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def get_sqlite_website_registry():
    initialize_database()
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                position,
                name,
                url,
                allowed,
                migrated_at
            FROM website_registry
            ORDER BY position
            """
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "name": row["name"],
            "url": row["url"],
            "allowed": bool(row["allowed"]),
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def migrate_website_open_history_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    website_opens = memory_data.get("website_opens", [])
    
    if not isinstance(website_opens, list):
        raise ValueError("memory.json website_opens must be a JSON list.")
    
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, event in enumerate(website_opens, start=1):
        if not isinstance(event, dict):
            raise ValueError(
                f"Website opening event {position} must be an object."
            )
            
        website_name = event.get("website_name")
        url = event.get("url")
        result = event.get("result")
        timestamp = event.get("timestamp")
        
        fields = {
            "website_name": website_name,
            "url": url,
            "result": result,
            "timestamp": timestamp,
        }
        
        for field, value in fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Website opening event {position} {field} must be text."
                )
                
        records.append(
            (
                position,
                website_name,
                url,
                result,
                timestamp,
                migrated_at,
            )
        )
        
    backup_file = create_memory_backup(
        "memory_before_website_open_history_sqlite"
    )
    
    with get_connection() as connection:
        connection.execute("DELETE FROM website_open_history")
        
        connection.executemany(
            """
            INSERT INTO website_open_history (
                position,
                website_name,
                url,
                result,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        
    details = {
        "backup_file": str(backup_file),
        "website_open_count": len(records),
    }
    
    record_migration(
        "migrate_website_open_history_from_json",
        "completed",
        details,
    )
    
    return details

def get_sqlite_website_open_history(limit=None):
    initialize_database()
    
    query = """
        SELECT
            id,
            position,
            website_name,
            url,
            result,
            timestamp,
            migrated_at
        FROM website_open_history
    """
    
    parameters = ()
    
    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)
        
    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()
        
    if limit is not None:
        rows = list(reversed(rows))
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "website_name": row["website_name"],
            "url": row["url"],
            "result": row["result"],
            "timestamp": row["timestamp"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def add_sqlite_website_open_event(position, event):
    initialize_database()
    
    if not isinstance(position, int) or position < 1:
        raise ValueError("Website opening position must be a positive integer.")
    
    if not isinstance(event, dict):
        raise ValueError("Website opening event must be an object.")
    
    website_name = event.get("website_name")
    url = event.get("url")
    result = event.get("result")
    timestamp = event.get("timestamp")
    
    fields = {
        "website_name": website_name,
        "url": url,
        "result": result,
        "timestamp": timestamp,
    }
    
    for field, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Website opening event {field} must be text."
            )
            
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO website_open_history (
                position,
                website_name,
                url,
                result,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                position,
                website_name,
                url,
                result,
                timestamp,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        
    return cursor.lastrowid
    
def verify_website_open_history_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_events = memory_data.get("website_opens", [])
    sqlite_events = get_sqlite_website_open_history()
    
    differences = []
    total_items = max(
        len(json_events),
        len(sqlite_events),
    )
    
    fields = [
        "website_name",
        "url",
        "result",
        "timestamp"
    ]
    
    for index in range(total_items):
        position = index + 1
        
        json_event = (
            json_events[index]
            if index < len(json_events)
            else None
        )
        
        sqlite_event = (
            sqlite_events[index]
            if index < len(sqlite_events)
            else None
        )
        
        if json_event is None or sqlite_event is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_event,
                "sqlite_value": sqlite_event,
            })
            continue
        
        if sqlite_event["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_event["position"],
            })
            
        for field in fields:
            if json_event.get(field) != sqlite_event.get(field):
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_event.get(field),
                    "sqlite_value": sqlite_event.get(field),
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_website_open_count": len(json_events),
        "sqlite_website_open_count": len(sqlite_events),
        "differences": differences,
    }
    
    record_migration(
        "verify_website_open_history_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def migrate_app_launch_history_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    app_launches = memory_data.get("app_launches", [])
    
    if not isinstance(app_launches, list):
        raise ValueError("memory.json app_launches must be a JSON list.")
    
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, event in enumerate(app_launches, start=1):
        if not isinstance(event, dict):
            raise ValueError(
                f"App launch event {position} must be an object."
            )
            
        app_name = event.get("app_name")
        command = event.get("command")
        result = event.get("result")
        timestamp = event.get("timestamp")
        
        fields = {
            "app_name": app_name,
            "command": command,
            "result": result,
            "timestamp": timestamp,
        }
        
        for field, value in fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"App launch event {position} {field} must be text."
                )
                
        records.append(
            (
                position,
                app_name,
                command,
                result,
                timestamp,
                migrated_at,
            )
        )
        
    backup_file = create_memory_backup(
        "memory_before_app_launch_history_sqlite"
    )
    
    with get_connection() as connection:
        connection.execute("DELETE FROM app_launch_history")
        
        connection.executemany(
            """
            INSERT INTO app_launch_history (
                position,
                app_name,
                command,
                result,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        
    details = {
        "backup_file": str(backup_file),
        "app_launch_count": len(records),
    }
    
    record_migration(
        "migrate_app_launch_history_from_json",
        "completed",
        details,
    )
        
    return details

def get_sqlite_app_launch_history(limit=None):
    initialize_database()
    
    query = """
        SELECT
            id,
            position,
            app_name,
            command,
            result,
            timestamp,
            migrated_at
        FROM app_launch_history
    """
    
    parameters = ()
    
    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)
        
    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()
        
    if limit is not None:
        rows = list(reversed(rows))
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "app_name": row["app_name"],
            "command": row["command"],
            "result": row["result"],
            "timestamp": row["timestamp"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def add_sqlite_app_launch_event(position, event):
    initialize_database()
    
    if not isinstance(position, int) or position < 1:
        raise ValueError("App launch position must be a positive integer.")
    
    if not isinstance(event, dict):
        raise ValueError("App launch event must be an object.")
    
    app_name = event.get("app_name")
    command = event.get("command")
    result = event.get("result")
    timestamp = event.get("timestamp")
    
    fields = {
        "app_name": app_name,
        "command": command,
        "result": result,
        "timestamp": timestamp,
    }
    
    for field, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"App launch event {field} must be text."
            )
            
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO app_launch_history (
                position,
                app_name,
                command,
                result,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                position,
                app_name,
                command,
                result,
                timestamp,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        
    return cursor.lastrowid

def migrate_app_aliases_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    aliases = memory_data.get("app_aliases", {})
    
    if not isinstance(aliases, dict):
        raise ValueError(
            "memory.json app_aliases must be a JSON object."
        )
        
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (alias, app_name) in enumerate(
        aliases.items(),
        start=1,
    ):
        if not isinstance(alias, str) or not alias.strip():
            raise ValueError(
                f"App alias {position} needs a valid alias."
            )
            
        if not isinstance(app_name, str) or not app_name.strip():
            raise ValueError(
                f"App alias '{alias}' needs a target app name."
            )
            
        records.append(
            (
                position,
                alias,
                app_name,
                migrated_at,
            )
        )
        
    backup_file = create_memory_backup(
        "memory_before_app_aliases_sqlite"
    )
    
    with get_connection() as connection:
        connection.execute("DELETE FROM app_aliases")
        
        connection.executemany(
            """
            INSERT INTO app_aliases (
                position,
                alias,
                app_name,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )
        
    details = {
        "backup_file": str(backup_file),
        "alias_count": len(records),
    }
    
    record_migration(
        "migrate_app_aliases_from_json",
        "completed",
        details,
    )
    
    return details

def get_sqlite_app_aliases():
    initialize_database()
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                position,
                alias,
                app_name,
                migrated_at
            FROM app_aliases
            ORDER BY position
            """
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "alias": row["alias"],
            "app_name": row["app_name"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def sync_sqlite_app_aliases_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    aliases = memory_data.get("app_aliases", {})
    
    if not isinstance(aliases, dict):
        raise ValueError(
            "memory.json app_aliases must be a JSON object."
        )
        
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (alias, app_name) in enumerate(
        aliases.items(),
        start=1
    ):
        if not isinstance(alias, str) or not alias.strip():
            raise ValueError(
                f"App alias {position} needs a valid alias."
            )

        if not isinstance(app_name, str) or not app_name.strip():
            raise ValueError(
                f"App alias '{alias}' needs a target app name."
            )
            
        records.append(
            (
                position,
                alias,
                app_name,
                synced_at,
            )
        )
        
    with get_connection() as connection:
        connection.execute("DELETE FROM app_aliases")
        
        connection.executemany(
            """
            INSERT INTO app_aliases (
                position,
                alias,
                app_name,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )
        
    return len(records)
    
def verify_app_aliases_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_aliases = memory_data.get("app_aliases", {})
    sqlite_aliases = get_sqlite_app_aliases()
    
    differences = []
    json_items = list(json_aliases.items())
    
    total_items = max(
        len(json_items),
        len(sqlite_aliases),
    )
    
    for index in range(total_items):
        position = index + 1
        
        json_item = (
            json_items[index]
            if index < len(json_items)
            else None
        )
        
        sqlite_alias = (
            sqlite_aliases[index]
            if index < len(sqlite_aliases)
            else None
        )
        
        if json_item is None or sqlite_alias is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_alias,
            })
            continue
        
        alias, app_name = json_item
        
        checks = {
            "position": (position, sqlite_alias["position"]),
            "alias": (alias, sqlite_alias["alias"]),
            "app_name": (app_name, sqlite_alias["app_name"]),
        }
        
        for field, (json_value, sqlite_value) in checks.items():
            if json_value != sqlite_value:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_value,
                    "sqlite_value": sqlite_value,
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_alias_count": len(json_items),
        "sqlite_alias_count": len(sqlite_aliases),
        "differences": differences,
    }
    
    record_migration(
        "verify_app_aliases_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result
 
def verify_app_launch_history_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_events = memory_data.get("app_launches", [])
    sqlite_events = get_sqlite_app_launch_history()
    
    differences = []
    total_items = max(
        len(json_events),
        len(sqlite_events),
    )
    
    fields = [
        "app_name",
        "command",
        "result",
        "timestamp",
    ]
    
    for index in range(total_items):
        position = index + 1
        
        json_event = (
            json_events[index]
            if index < len(json_events)
            else None
        )
        
        sqlite_event = (
            sqlite_events[index]
            if index < len(sqlite_events)
            else None
        )
        
        if json_event is None or sqlite_event is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_event,
                "sqlite_value": sqlite_event,
            })
            continue
        
        if sqlite_event["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_event["position"],
            })
            
        for field in fields:
            if json_event.get(field) != sqlite_event.get(field):
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_event.get(field),
                    "sqlite_value": sqlite_event.get(field),
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_app_launch_count": len(json_events),
        "sqlite_app_launch_count": len(sqlite_events),
        "differences": differences,
    }
    
    record_migration(
        "verify_app_launch_history_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def migrate_default_apps_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    defaults = memory_data.get("default_apps", {})
    
    if not isinstance(defaults, dict):
        raise ValueError(
            "memory.json default_apps must be a JSON object."
        )
        
    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (category, app_name) in enumerate(
        defaults.items(),
        start=1,
    ):
        if not isinstance(category, str) or not category.strip():
            raise ValueError(
                f"Default app {position} needs a valid category."
            )

        if not isinstance(app_name, str) or not app_name.strip():
            raise ValueError(
                f"Default app '{category}' needs a target app name."
            )
            
        records.append(
            (
                position,
                category,
                app_name,
                migrated_at,
            )
        )
        
    backup_file = create_memory_backup(
        "memory_before_default_apps_sqlite"
    )
    
    with get_connection() as connection:
        connection.execute("DELETE FROM default_apps")
        
        connection.executemany(
            """
            INSERT INTO default_apps (
                position,
                category,
                app_name,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )
        
    details = {
        "backup_file": str(backup_file),
        "default_app_count": len(records),
    }
    
    record_migration(
        "migrate_default_apps_from_json",
        "completed",
        details,
    )
    
    return details

def migrate_search_folders_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    folders = memory_data.get("search_folders", {})

    if not isinstance(folders, dict):
        raise ValueError(
            "memory.json search_folders must be a JSON object."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, (name, path) in enumerate(
        folders.items(),
        start=1,
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Search folder {position} needs a valid name."
            )

        if not isinstance(path, str) or not path.strip():
            raise ValueError(
                f"Search folder '{name}' needs a valid path."
            )

        records.append(
            (
                position,
                name,
                path.strip(),
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_search_folders_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM search_folders")

        connection.executemany(
            """
            INSERT INTO search_folders (
                position,
                name,
                path,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "search_folder_count": len(records),
    }

    record_migration(
        "migrate_search_folders_from_json",
        "completed",
        details,
    )

    return details


def get_sqlite_search_folders():
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                position,
                name,
                path,
                migrated_at
            FROM search_folders
            ORDER BY position
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "position": row["position"],
            "name": row["name"],
            "path": row["path"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def sync_sqlite_search_folders_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    folders = memory_data.get("search_folders", {})

    if not isinstance(folders, dict):
        raise ValueError(
            "memory.json search_folders must be a JSON object."
        )

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, (name, path) in enumerate(
        folders.items(),
        start=1,
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Search folder {position} needs a valid name."
            )

        if not isinstance(path, str) or not path.strip():
            raise ValueError(
                f"Search folder '{name}' needs a valid path."
            )

        records.append(
            (
                position,
                name,
                path.strip(),
                synced_at,
            )
        )

    with get_connection() as connection:
        connection.execute("DELETE FROM search_folders")

        connection.executemany(
            """
            INSERT INTO search_folders (
                position,
                name,
                path,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )

    return len(records)
    
def verify_search_folders_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_folders = memory_data.get("search_folders", {})
    sqlite_folders = get_sqlite_search_folders()
    
    differences = []
    json_items = list(json_folders.items())
    
    total_items = max(
        len(json_items),
        len(sqlite_folders),
    )
    
    for index in range(total_items):
        position = index + 1
        
        json_item = (
            json_items[index]
            if index < len(json_items)
            else None
        )

        sqlite_folder = (
            sqlite_folders[index]
            if index < len(sqlite_folders)
            else None
        )
        
        if json_item is None or sqlite_folder is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_folder,
            })
            continue
        
        name, path = json_item
        
        checks = {
            "position": (position, sqlite_folder["position"]),
            "name": (name, sqlite_folder["name"]),
            "path": (path, sqlite_folder["path"]),
        }
        
        for field, (json_value, sqlite_value) in checks.items():
            if json_value != sqlite_value:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_value,
                    "sqlite_value": sqlite_value,
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_search_folder_count": len(json_items),
        "sqlite_search_folder_count": len(sqlite_folders),
        "differences": differences,
    }
    
    record_migration(
        "verify_search_folders_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result

def migrate_file_search_history_from_json():
    initialize_database()

    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)

    history = memory_data.get("file_search_history", [])

    if not isinstance(history, list):
        raise ValueError(
            "memory.json file_search_history must be a JSON list."
        )

    migrated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, event in enumerate(history, start=1):
        if not isinstance(event, dict):
            raise ValueError(
                f"File search event {position} must be an object."
            )

        action = event.get("action")
        folder = event.get("folder")
        query = event.get("query")
        result = event.get("result")
        timestamp = event.get("timestamp")

        fields = {
            "action": action,
            "folder": folder,
            "query": query,
            "result": result,
            "timestamp": timestamp,
        }

        for field, value in fields.items():
            if not isinstance(value, str):
                raise ValueError(
                    f"File search event {position} {field} must be text."
                )

        records.append(
            (
                position,
                action,
                folder,
                query,
                result,
                timestamp,
                migrated_at,
            )
        )

    backup_file = create_memory_backup(
        "memory_before_file_search_history_sqlite"
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM file_search_history")

        connection.executemany(
            """
            INSERT INTO file_search_history (
                position,
                action,
                folder,
                query,
                result,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    details = {
        "backup_file": str(backup_file),
        "file_search_event_count": len(records),
    }

    record_migration(
        "migrate_file_search_history_from_json",
        "completed",
        details,
    )

    return details

def get_sqlite_file_search_history(limit=None):
    initialize_database()
    
    query = """
        SELECT
            id,
            position,
            action,
            folder,
            query,
            result,
            timestamp,
            migrated_at
        FROM file_search_history
    """
    
    parameters = ()
    
    if limit is None:
        query += " ORDER BY position"
    else:
        safe_limit = max(1, min(limit, 100))
        query += """
            ORDER BY position DESC
            LIMIT ?
        """
        parameters = (safe_limit,)
        
    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()
        
    if limit is not None:
        rows = list(reversed(rows))
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "action": row["action"],
            "folder": row["folder"],
            "query": row["query"],
            "result": row["result"],
            "timestamp": row["timestamp"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def add_sqlite_file_search_event(position, event):
    initialize_database()

    if not isinstance(position, int) or position < 1:
        raise ValueError(
            "File search event position must be a positive integer."
        )

    if not isinstance(event, dict):
        raise ValueError("File search event must be an object.")

    fields = {
        "action": event.get("action"),
        "folder": event.get("folder"),
        "query": event.get("query"),
        "result": event.get("result"),
        "timestamp": event.get("timestamp"),
    }

    for field, value in fields.items():
        if not isinstance(value, str):
            raise ValueError(
                f"File search event {field} must be text."
            )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO file_search_history (
                position,
                action,
                folder,
                query,
                result,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position,
                fields["action"],
                fields["folder"],
                fields["query"],
                fields["result"],
                fields["timestamp"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    return cursor.lastrowid

def sync_sqlite_file_search_history_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    history = memory_data.get("file_search_history", [])
    
    if not isinstance(history, list):
        raise ValueError(
            "memory.json file_search_history must be a JSON list."
        )
        
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for position, event in enumerate(history, start=1):
        if not isinstance(event, dict):
            raise ValueError(
                f"File search event {position} must be an object."
            )

        fields = {
            "action": event.get("action"),
            "folder": event.get("folder"),
            "query": event.get("query"),
            "result": event.get("result"),
            "timestamp": event.get("timestamp"),
        }

        for field, value in fields.items():
            if not isinstance(value, str):
                raise ValueError(
                    f"File search event {position} {field} must be text."
                )

        records.append(
            (
                position,
                fields["action"],
                fields["folder"],
                fields["query"],
                fields["result"],
                fields["timestamp"],
                synced_at,
            )
        )

    with get_connection() as connection:
        connection.execute("DELETE FROM file_search_history")

        connection.executemany(
            """
            INSERT INTO file_search_history (
                position,
                action,
                folder,
                query,
                result,
                timestamp,
                migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    return len(records)
    
def verify_file_search_history_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_history = memory_data.get("file_search_history", [])
    sqlite_history = get_sqlite_file_search_history()
    
    differences = []
    total_items = max(
        len(json_history),
        len(sqlite_history),
    )
    
    fields = [
        "action",
        "folder",
        "query",
        "result",
        "timestamp",
    ]
    
    for index in range(total_items):
        position = index + 1
        
        json_event = (
            json_history[index]
            if index < len(json_history)
            else None
        )

        sqlite_event = (
            sqlite_history[index]
            if index < len(sqlite_history)
            else None
        )
        
        if json_event is None or sqlite_event is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_event,
                "sqlite_value": sqlite_event,
            })
            continue
        
        if sqlite_event["position"] != position:
            differences.append({
                "position": position,
                "field": "position",
                "json_value": position,
                "sqlite_value": sqlite_event["position"],
            })
            
        for field in fields:
            if json_event.get(field) != sqlite_event.get(field):
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_event.get(field),
                    "sqlite_value": sqlite_event.get(field),
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_file_search_event_count": len(json_history),
        "sqlite_file_search_event_count": len(sqlite_history),
        "differences": differences,
    }
    
    record_migration(
        "verify_file_search_history_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result
        
def get_sqlite_default_apps():
    initialize_database()
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                position,
                category,
                app_name,
                migrated_at
            FROM default_apps
            ORDER BY position
            """
        ).fetchall()
        
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "category": row["category"],
            "app_name": row["app_name"],
            "migrated_at": row["migrated_at"],
        }
        for row in rows
    ]
    
def sync_sqlite_default_apps_from_json():
    initialize_database()
    
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    defaults = memory_data.get("default_apps", {})
    
    if not isinstance(defaults, dict):
        raise ValueError(
            "memory.json default_apps must be a JSON object."
        )
        
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    
    for position, (category, app_name) in enumerate(
        defaults.items(),
        start=1,
    ):
        if not isinstance(category, str) or not category.strip():
            raise ValueError(
                f"Default app {position} needs a valid category."
            )

        if not isinstance(app_name, str) or not app_name.strip():
            raise ValueError(
                f"Default app '{category}' needs a target app name."
            )

        records.append(
            (
                position,
                category,
                app_name,
                synced_at,
            )
        )
        
    with get_connection() as connection:
        connection.execute("DELETE FROM default_apps")
        
        connection.executemany(
            """
            INSERT INTO default_apps (
                position,
                category,
                app_name,
                migrated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )
        
    return len(records)
    
def verify_default_apps_migration():
    with open(MEMORY_FILE, "r") as file:
        memory_data = json.load(file)
        
    json_defaults = memory_data.get("default_apps", {})
    sqlite_defaults = get_sqlite_default_apps()
    
    differences = []
    json_items = list(json_defaults.items())
    
    total_items = max(
        len(json_items),
        len(sqlite_defaults),
    )
    
    for index in range(total_items):
        position = index + 1
        
        json_item = (
            json_items[index]
            if index < len(json_items)
            else None
        )

        sqlite_default = (
            sqlite_defaults[index]
            if index < len(sqlite_defaults)
            else None
        )
        
        if json_item is None or sqlite_default is None:
            differences.append({
                "position": position,
                "field": "record",
                "json_value": json_item,
                "sqlite_value": sqlite_default,
            })
            continue
        
        category, app_name = json_item
        
        checks = {
            "position": (position, sqlite_default["position"]),
            "category": (category, sqlite_default["category"]),
            "app_name": (app_name, sqlite_default["app_name"]),
        }
        
        for field, (json_value, sqlite_value) in checks.items():
            if json_value != sqlite_value:
                differences.append({
                    "position": position,
                    "field": field,
                    "json_value": json_value,
                    "sqlite_value": sqlite_value,
                })
                
    matches = not differences
    
    result = {
        "matches": matches,
        "json_default_app_count": len(json_items),
        "sqlite_default_app_count": len(sqlite_defaults),
        "differences": differences,
    }
    
    record_migration(
        "verify_default_apps_migration",
        "completed" if matches else "mismatch",
        result,
    )
    
    return result