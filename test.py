from assistant.llm import get_gemini_embedding
from assistant.embeddings import rank_embedding_matches


query_text = "Help me understand Python data structures."

candidate_texts = [
    "How do Python dictionaries store key value pairs?",
    "Explain Python lists and how to append items.",
    "I need to buy groceries this afternoon.",
    "My favorite game is Stardew Valley.",
]

query_result = get_gemini_embedding(query_text)

if not query_result["ok"]:
    raise RuntimeError(query_result["error"])

candidates = []

for text in candidate_texts:
    embedding_result = get_gemini_embedding(text)

    if not embedding_result["ok"]:
        raise RuntimeError(embedding_result["error"])

    candidates.append({
        "text": text,
        "vector": embedding_result["vector"],
    })

matches = rank_embedding_matches(
    query_result["vector"],
    candidates,
    limit=4,
    min_score=0.0,
)

for match in matches:
    print(
        f"{match['score']:.3f} | "
        f"{match['text']}"
    )