from assistant import database
from assistant.semantic_memory import (
    semantic_search_cached_conversation_summaries,
)


summaries = database.get_sqlite_conversation_summaries()

if not summaries:
    raise RuntimeError("No conversation summaries exist.")

expected_summary = summaries[-1]

result = semantic_search_cached_conversation_summaries(
    expected_summary["summary"],
    limit=3,
    min_score=0.0,
)

print({
    "ok": result["ok"],
    "expected_summary_id": expected_summary["id"],
    "cached_summaries": result["cached_summaries"],
    "error": result["error"],
})

for match in result["matches"]:
    print(
        f"{match['score']:.3f} | "
        f"{match['summary_id']} | "
        f"{match['summary']}"
    )