from assistant import database
from assistant.embeddings import create_content_hash
from assistant.llm import (
    GEMINI_EMBEDDING_MODEL,
    get_gemini_embedding,
)

text = "Python dictionaries map keys to values."

embedding_result = get_gemini_embedding(text)

if not embedding_result["ok"]:
    raise RuntimeError(embedding_result["error"])

saved_embedding = database.upsert_memory_embedding(
    source_type="test",
    source_id="python-dictionaries",
    content_hash=create_content_hash(text),
    model=GEMINI_EMBEDDING_MODEL,
    vector=embedding_result["vector"],
)

cached_embedding = database.get_memory_embedding(
    source_type="test",
    source_id="python-dictionaries",
    model=GEMINI_EMBEDDING_MODEL,
)

print({
    "saved": saved_embedding is not None,
    "cached": cached_embedding is not None,
    "source_type": cached_embedding["source_type"],
    "source_id": cached_embedding["source_id"],
    "model": cached_embedding["model"],
    "dimensions": cached_embedding["dimensions"],
    "same_vector": (
        cached_embedding["vector"]
        == embedding_result["vector"]
    ),
})