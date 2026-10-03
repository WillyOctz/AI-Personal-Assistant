from assistant.llm import get_gemini_embedding
from assistant.embeddings import cosine_similarity

query = get_gemini_embedding("I enjoy learning Python programming.")
similar = get_gemini_embedding("I like studying Python code.")
different = get_gemini_embedding("My reminder is to buy groceries.")

print(query["ok"], similar["ok"], different["ok"])

similarity_score = cosine_similarity(
    query["vector"],
    similar["vector"],
)

different_score = cosine_similarity(
    query["vector"],
    different["vector"],
)

print("Similar:", round(similarity_score, 3))
print("Different:", round(different_score, 3))