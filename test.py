from assistant import database
from assistant.llm import GEMINI_EMBEDDING_MODEL


summaries = database.get_sqlite_conversation_summaries()

if not summaries:
    raise RuntimeError("No conversation summaries exist.")

latest_summary = summaries[-1]

cached_embedding = database.get_memory_embedding(
    source_type="conversation_summary",
    source_id=latest_summary["id"],
    model=GEMINI_EMBEDDING_MODEL,
)

print({
    "summary_id": latest_summary["id"],
    "summary_saved": bool(latest_summary["summary"]),
    "embedding_cached": cached_embedding is not None,
    "dimensions": (
        cached_embedding["dimensions"]
        if cached_embedding
        else None
    ),
})