from assistant.brain import get_relevant_llm_notes


queries = [
    "What have I said about learning AI?",
    "What language do I enjoy programming in?",
    "Give me cooking advice.",
]

for query in queries:
    notes = get_relevant_llm_notes(query)

    print(f"\nQuery: {query}")

    for note in notes:
        print(
            f"{note['score']:.3f} | "
            f"{note['text']}"
        )