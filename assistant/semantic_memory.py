from assistant import database
from assistant.embeddings import create_content_hash
from assistant.llm import (
    GEMINI_EMBEDDING_MODEL,
    get_gemini_embedding,
)

NOTE_SOURCE_TYPE = "note"

def cache_note_embedding(note_id):
    note = database.get_sqlite_note(note_id)
    
    if note is None:
        return {
            "ok": False,
            "status": "not_found",
            "note_id": note_id,
            "embedding": None,
            "error": "Note was not found.",
        }
        
    content_hash = create_content_hash(note["text"])
    
    cached_embedding = database.get_memory_embedding(
        source_type=NOTE_SOURCE_TYPE,
        source_id=note["id"],
        model=GEMINI_EMBEDDING_MODEL,
    )
    
    if (
        cached_embedding is not None
        and cached_embedding["content_hash"] == content_hash
    ):
        return {
            "ok": True,
            "status": "cached",
            "note_id": note["id"],
            "embedding": cached_embedding,
            "error": None,
        }
        
    embedding_result = get_gemini_embedding(note["text"])
    
    if not embedding_result["ok"]:
        return {
            "ok": False,
            "status": "embedding_failed",
            "note_id": note["id"],
            "embedding": None,
            "error": embedding_result["error"],
        }
        
    saved_embedding = database.upsert_memory_embedding(
        source_type=NOTE_SOURCE_TYPE,
        source_id=note["id"],
        content_hash=content_hash,
        model=GEMINI_EMBEDDING_MODEL,
        vector=embedding_result["vector"],
    )
    
    status = "created"
    
    if cached_embedding is not None:
        status = "refreshed"
        
    return {
        "ok": True,
        "status": status,
        "note_id": note["id"],
        "embedding": saved_embedding,
        "error": None,
    }