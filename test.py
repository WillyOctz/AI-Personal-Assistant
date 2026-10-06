from assistant import database
from assistant.semantic_memory import cache_note_embedding


notes = database.get_sqlite_notes()

if not notes:
    raise RuntimeError("No SQLite notes exist to test.")

result = cache_note_embedding(notes[0]["id"])

print({
    "ok": result["ok"],
    "status": result["status"],
    "note_id": result["note_id"],
    "dimensions": (
        result["embedding"]["dimensions"]
        if result["embedding"]
        else None
    ),
    "error": result["error"],
})