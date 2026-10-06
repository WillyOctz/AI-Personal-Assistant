from assistant import database
from assistant.semantic_memory import (
    cache_conversation_summary_embedding,
)


summaries = database.get_sqlite_conversation_summaries()

if not summaries:
    raise RuntimeError(
        "No conversation summaries exist. "
        "Run 'summarize conversation' first."
    )

latest_summary = summaries[-1]

result = cache_conversation_summary_embedding(
    latest_summary["id"]
)

print({
    "summary_id": result["summary_id"],
    "status": result["status"],
    "dimensions": (
        result["embedding"]["dimensions"]
        if result["embedding"]
        else None
    ),
    "error": result["error"],
})