from assistant.semantic_memory import (
    cache_conversation_summary_embeddings,
)


summary = cache_conversation_summary_embeddings()

print({
    "total": summary["total"],
    "created": summary["created"],
    "reused": summary["reused"],
    "cached": summary["cached"],
    "refreshed": summary["refreshed"],
    "failed": summary["failed"],
})

for result in summary["results"]:
    print(
        f"{result['summary_id']} | "
        f"{result['status']} | "
        f"{result['error']}"
    )