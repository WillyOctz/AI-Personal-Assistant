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