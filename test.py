from assistant.semantic_memory import cache_note_embedding


NOTE_ID = 20

result = cache_note_embedding(NOTE_ID)

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