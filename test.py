from uuid import uuid4

from assistant import database
from assistant import memory
from assistant.llm import GEMINI_EMBEDDING_MODEL


note_text = f"embedding lifecycle test {uuid4().hex}"

saved = memory.add_note(note_text)
note_id = saved["note_id"]

cached_before_delete = database.get_memory_embedding(
    source_type="note",
    source_id=note_id,
    model=GEMINI_EMBEDDING_MODEL,
)

deleted = memory.delete_note(note_text)

cached_after_delete = database.get_memory_embedding(
    source_type="note",
    source_id=note_id,
    model=GEMINI_EMBEDDING_MODEL,
)

print({
    "note_id": note_id,
    "embedding": saved["embedding"],
    "cache_before_delete": cached_before_delete is not None,
    "deleted": deleted["deleted"],
    "deleted_embeddings": deleted["deleted_embeddings"],
    "cache_after_delete": cached_after_delete is not None,
})