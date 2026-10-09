from assistant import semantic_memory
from assistant.brain import get_relevant_llm_context


original_function = (
    semantic_memory.get_semantic_context_matches
)


def raise_semantic_error(*args, **kwargs):
    raise RuntimeError("Temporary semantic test failure")


semantic_memory.get_semantic_context_matches = (
    raise_semantic_error
)

try:
    result = get_relevant_llm_context(
        "What have I said about artificial intelligence?"
    )

    print({
        "notes": result["notes"],
        "summaries": result["summaries"],
    })

finally:
    semantic_memory.get_semantic_context_matches = (
        original_function
    )