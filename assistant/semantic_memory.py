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
CONVERSATION_SUMMARY_SOURCE_TYPE = "conversation_summary"

def cache_text_embedding(source_type, source_id, text):
    clean_source_type = str(source_type).strip()
    clean_source_id = str(source_id).strip()
    clean_text = str(text or "").strip()
    
    if not clean_source_type or not clean_source_id:
        return {
            "ok": False,
            "status": "invalid_source",
            "source_type": clean_source_type,
            "source_id": clean_source_id,
            "embedding": None,
            "error": "Embedding source type and source ID are required.",
        }
        
    if not clean_text:
        return {
            "ok": False,
            "status": "invalid_text",
            "source_type": clean_source_type,
            "source_id": clean_source_id,
            "embedding": None,
            "error": "Embedding text cannot be empty.",
        }
        
    content_hash = create_content_hash(clean_text)
    
    cached_embedding = database.get_memory_embedding(
        source_type=clean_source_type,
        source_id=clean_source_id,
        model=GEMINI_EMBEDDING_MODEL,
    )
    
    if (
        cached_embedding is not None
        and cached_embedding["content_hash"] == content_hash
    ):
        return {
            "ok": True,
            "status": "cached",
            "source_type": clean_source_type,
            "source_id": clean_source_id,
            "embedding": cached_embedding,
            "error": None,
        }
        
    shared_embedding = (
        database.get_memory_embedding_by_content_hash(
            source_type=clean_source_type,
            content_hash=content_hash,
            model=GEMINI_EMBEDDING_MODEL,
        )
    )
    
    if shared_embedding is not None:
        saved_embedding = database.upsert_memory_embedding(
            source_type=clean_source_type,
            source_id=clean_source_id,
            content_hash=content_hash,
            model=GEMINI_EMBEDDING_MODEL,
            vector=shared_embedding["vector"],
        )
        
        return {
            "ok": True,
            "status": "reused",
            "source_type": clean_source_type,
            "source_id": clean_source_id,
            "embedding": saved_embedding,
            "error": None,
        }
        
    embedding_result = get_gemini_embedding(clean_text)
    
    if not embedding_result["ok"]:
        return {
            "ok": False,
            "status": "embedding_failed",
            "source_type": clean_source_type,
            "source_id": clean_source_id,
            "embedding": None,
            "error": embedding_result["error"],
        }
        
    saved_embedding = database.upsert_memory_embedding(
        source_type=clean_source_type,
        source_id=clean_source_id,
        content_hash=content_hash,
        model=GEMINI_EMBEDDING_MODEL,
        vector=embedding_result["vector"],
    )
    
    return {
        "ok": True,
        "status": (
            "refreshed"
            if cached_embedding is not None
            else "created"
        ),
        "source_type": clean_source_type,
        "source_id": clean_source_id,
        "embedding": saved_embedding,
        "error": None,
    }

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
        
    result = cache_text_embedding(
        source_type=NOTE_SOURCE_TYPE,
        source_id=note["id"],
        text=note["text"],
    )
    
    return {
        "ok": result["ok"],
        "status": result["status"],
        "note_id": note["id"],
        "embedding": result["embedding"],
        "error": result["error"],
    }
    
def cache_conversation_summary_embedding(summary_id):
    summary = database.get_sqlite_conversation_summary(
        summary_id
    )
    
    if summary is None:
        return {
            "ok": False,
            "status": "not_found",
            "summary_id": summary_id,
            "embedding": None,
            "error": "Conversation summary was not found.",
        }
        
    result = cache_text_embedding(
        source_type=CONVERSATION_SUMMARY_SOURCE_TYPE,
        source_id=summary["id"],
        text=summary["summary"],
    )
    
    return {
        "ok": result["ok"],
        "status": result["status"],
        "summary_id": summary["id"],
        "embedding": result["embedding"],
        "error": result["error"],
    }
    
def cache_conversation_summary_embeddings(limit=None):
    summaries = database.get_sqlite_conversation_summaries()
    
    if limit is not None:
        safe_limit = max(1, int(limit))
        summaries = summaries[:safe_limit]
        
    results = []
    
    for summary in summaries:
        result = cache_conversation_summary_embedding(
            summary["id"]
        )
        
        results.append({
            "ok": result["ok"],
            "summary_id": summary["id"],
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
    query_vector=None,
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
        
    if query_vector is None:
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
            
        query_vector = query_result["vector"]
        
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
        query_vector,
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
    
def semantic_search_cached_conversation_summaries(
    query,
    limit=5,
    min_score=0.0,
    query_vector=None,
):
    clean_query = str(query or "").strip()
    
    if not clean_query:
        return {
            "ok": False,
            "query": "",
            "matches": [],
            "cached_summaries": 0,
            "skipped_stale": 0,
            "error": "Search query cannot be empty.",
        }
        
    if query_vector is None:
        query_result = get_gemini_embedding(clean_query)
        
        if not query_result["ok"]:
            return {
                "ok": False,
                "query": clean_query,
                "matches": [],
                "cached_summaries": 0,
                "skipped_stale": 0,
                "error": query_result["error"],
            }
            
        query_vector = query_result["vector"]
        
    summaries_by_id = {
        str(summary["id"]): summary
        for summary in database.get_sqlite_conversation_summaries()
    }
    
    cached_embeddings = database.get_memory_embeddings(
        source_type=CONVERSATION_SUMMARY_SOURCE_TYPE,
        model=GEMINI_EMBEDDING_MODEL,
    )
    
    candidates = []
    skipped_stale = 0
    
    for cached_embedding in cached_embeddings:
        summary = summaries_by_id.get(
            cached_embedding["source_id"]
        )
        
        if summary is None:
            continue
        
        current_hash = create_content_hash(summary["summary"])
        
        if cached_embedding["content_hash"] != current_hash:
            skipped_stale += 1
            continue
        
        candidates.append({
            "summary_id": summary["id"],
            "summary": summary["summary"],
            "timestamp": summary["timestamp"],
            "vector": cached_embedding["vector"],
        })
        
    matches = rank_embedding_matches(
        query_vector,
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
        "cached_summaries": len(candidates),
        "skipped_stale": skipped_stale,
        "error": None,
    }
    
def get_semantic_context_matches(
    query,
    note_limit=3,
    summary_limit=2,
    note_min_score=0.55,
    summary_min_score=0.55,
):
    clean_query = str(query or "").strip()
    
    if not clean_query:
        return {
            "ok": False,
            "notes": [],
            "summaries": [],
            "error": "Search query cannot be empty.",
        }
        
    query_result = get_gemini_embedding(clean_query)
    
    if not query_result["ok"]:
        return {
            "ok": False,
            "notes": [],
            "summaries": [],
            "error": query_result["error"],
        }
        
    query_vector = query_result["vector"]
    
    note_result = semantic_search_cached_notes(
        query=clean_query,
        limit=note_limit,
        min_score=note_min_score,
        query_vector=query_vector
    )
    
    summary_result = (
        semantic_search_cached_conversation_summaries(
            query=clean_query,
            limit=summary_limit,
            min_score=summary_min_score,
            query_vector=query_vector,
        )
    )
    
    return {
        "ok": (
            note_result["ok"]
            and summary_result["ok"]
        ),
        "notes": note_result["matches"],
        "summaries": summary_result["matches"],
        "error": (
            note_result["error"]
            or summary_result["error"]
        ),
    }
    
def get_semantic_cache_status():
    source_configs = [
        {
            "label": "notes",
            "source_type": NOTE_SOURCE_TYPE,
            "records": database.get_sqlite_notes(),
            "text_key": "text",
        },
        {
            "label": "conversation_summaries",
            "source_type": CONVERSATION_SUMMARY_SOURCE_TYPE,
            "records": (
                database.get_sqlite_conversation_summaries()
            ),
            "text_key": "summary",
        },
    ]
    
    sources = {}
    
    for config in source_configs:
        records_by_id = {
            str(record["id"]): record for record in config["records"]
        }
        
        embeddings = database.get_memory_embeddings(
            source_type=config["source_type"],
            model=GEMINI_EMBEDDING_MODEL,
        )
        
        embeddings_by_source_id = {
            embedding["source_id"]: embedding
            for embedding in embeddings
        }
        
        cached = 0
        missing = 0
        stale = 0
        
        for source_id, record in records_by_id.items():
            embedding = embeddings_by_source_id.get(source_id)
            
            if embedding is None:
                missing += 1
                continue
            
            current_hash = create_content_hash(
                record[config["text_key"]]
            )
            
            if embedding["content_hash"] != current_hash:
                stale += 1
                continue
            
            cached += 1
        
        orphaned = sum(
            embedding["source_id"] not in records_by_id
            for embedding in embeddings
        )
        
        sources[config["label"]] = {
            "records": len(records_by_id),
            "cached": cached,
            "missing": missing,
            "stale": stale,
            "orphaned": orphaned,
        }
        
    return {
        "model": GEMINI_EMBEDDING_MODEL,
        "sources": sources,
    }