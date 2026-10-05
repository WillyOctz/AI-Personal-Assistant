from assistant.semantic_memory import cache_note_embeddings

summary = cache_note_embeddings(limit=3)

print({
    "total": summary["total"],
    "created": summary["created"],
    "cached": summary["cached"],
    "refreshed": summary["refreshed"],
    "failed": summary["failed"],
})

for result in summary["results"]:
    print(
        f"{result['note_id']} | "
        f"{result['status']} | "
        f"{result['error']}"
    )