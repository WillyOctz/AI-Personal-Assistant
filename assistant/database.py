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
    
def create_memory_backup():
    if not MEMORY_FILE.exists():
        raise FileNotFoundError(
            f"Memory file does not exist: {MEMORY_FILE}"
        )
        
    BACKUP_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / (
        f"memory_before_sqlite_{timestamp}.json"
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