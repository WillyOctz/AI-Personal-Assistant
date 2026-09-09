import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_FILE = PROJECT_ROOT / "db" / "nebula.db"
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