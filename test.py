from assistant.brain import get_relevant_llm_context


result = get_relevant_llm_context(
    "What have we discussed about building my AI assistant?"
)

print("Notes:")
for note in result["notes"]:
    print(f"{note['score']:.3f} | {note['text']}")

print("\nSummaries:")
for summary in result["summaries"]:
    print(
        f"{summary['score']:.3f} | "
        f"{summary['timestamp']} | "
        f"{summary['summary']}"
    )