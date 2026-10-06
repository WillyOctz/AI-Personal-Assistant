from assistant import database
from assistant.embeddings import (
    create_content_hash,
    rank_embedding_matches,
)
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
        
    shared_embedding = (
        database.get_memory_embedding_by_content_hash(
            source_type=NOTE_SOURCE_TYPE,
            content_hash=content_hash,
            model=GEMINI_EMBEDDING_MODEL,
        )
    )
    
    if shared_embedding is not None:
        saved_embedding = database.upsert_memory_embedding(
            source_type=NOTE_SOURCE_TYPE,
            source_id=note["id"],
            content_hash=content_hash,
            model=GEMINI_EMBEDDING_MODEL,
            vector=shared_embedding["vector"],
        )
        
        return {
            "ok": True,
            "status": "reused",
            "note_id": note["id"],
            "embedding": saved_embedding,
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
    
def cache_note_embeddings(limit=None):
    notes = database.get_sqlite_notes()
    
    if limit is not None:
        safe_limit = max(1, int(limit))
        notes = notes[:safe_limit]
        
    results = []
    
    for note in notes:
        result = cache_note_embedding(note["id"])
        
        results.append({
            "ok": result["ok"],
            "note_id": note["id"],
            "status": result["status"],
            "error": result["error"],
        })
        
    return {
        "total": len(results),
        "created": sum(
            result["status"] == "created"
            for result in results
        ),
        "reused": sum(
            result["status"] == "reused"
            for result in results
        ),
        "cached": sum(
            result["status"] == "cached"
            for result in results
        ),
        "refreshed": sum(
            result["status"] == "refreshed"
            for result in results
        ),
        "failed": sum(
            not result["ok"]
            for result in results
        ),
        "results": results,
    }
    
def semantic_search_cached_notes(
    query,
    limit=5,
    min_score=0.0,
):
    clean_query = str(query or "").strip()
    
    if not clean_query:
        return {
            "ok": False,
            "query": "",
            "matches": [],
            "cached_notes": 0,
            "skipped_stale": 0,
            "error": "Search query cannot be empty.",
        }
        
    query_result = get_gemini_embedding(clean_query)
    
    if not query_result["ok"]:
        return {
            "ok": False,
            "query": clean_query,
            "matches": [],
            "cached_notes": 0,
            "skipped_stale": 0,
            "error": query_result["error"],
        }
        
    notes_by_id = {
        str(note["id"]): note for note in database.get_sqlite_notes()
    }
    
    cached_embeddings = database.get_memory_embeddings(
        source_type=NOTE_SOURCE_TYPE,
        model=GEMINI_EMBEDDING_MODEL,
    )
    
    candidates = []
    skipped_stale = 0
    
    for cached_embedding in cached_embeddings:
        note = notes_by_id.get(cached_embedding["source_id"])
        
        if note is None:
            continue
        
        current_hash = create_content_hash(note["text"])
        
        if cached_embedding["content_hash"] != current_hash:
            skipped_stale += 1
            continue
        
        candidates.append({
            "note_id": note["id"],
            "text": note["text"],
            "vector": cached_embedding["vector"],
        })
        
    matches = rank_embedding_matches(
        query_result["vector"],
        candidates,
        limit=max(1, int(limit)),
        min_score=float(min_score),
    )
    
    for match in matches:
        match.pop("vector", None)
        
    return {
        "ok": True,
        "query": clean_query,
        "matches": matches,
        "cached_notes": len(candidates),
        "skipped_stale": skipped_stale,
        "error": None,
    }