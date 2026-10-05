from assistant.semantic_memory import (
    cache_note_embeddings,
    semantic_search_cached_notes,
)

cache_note_embeddings(limit=3)

result = semantic_search_cached_notes(
    "I want to study artificial intelligence.",
    limit=3,
    min_score=0.0,
)

print({
    "ok": result["ok"],
    "cached_notes": result["cached_notes"],
    "skipped_stale": result["skipped_stale"],
    "error": result["error"],
})

for match in result["matches"]:
    print(
        f"{match['score']:.3f} | "
        f"{match['note_id']} | "
        f"{match['text']}"
    )