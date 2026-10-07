from assistant.semantic_memory import (
    get_semantic_context_matches,
)


result = get_semantic_context_matches(
    "What do you remember about how I am building my AI assistant?",
)

print({
    "ok": result["ok"],
    "note_count": len(result["notes"]),
    "summary_count": len(result["summaries"]),
    "error": result["error"],
})

print("\nNotes:")
for note in result["notes"]:
    print(f"{note['score']:.3f} | {note['text']}")

print("\nConversation summaries:")
for summary in result["summaries"]:
    print(
        f"{summary['score']:.3f} | "
        f"{summary['summary']}"
    )