from assistant import database
from assistant.llm import GEMINI_EMBEDDING_MODEL
from assistant.semantic_memory import repair_semantic_cache


notes = database.get_sqlite_notes()

if not notes:
    raise RuntimeError("No SQLite notes exist.")

note = notes[0]

database.delete_memory_embeddings(
    source_type="note",
    source_id=note["id"],
)

before = database.get_memory_embedding(
    source_type="note",
    source_id=note["id"],
    model=GEMINI_EMBEDDING_MODEL,
)

repair = repair_semantic_cache()

after = database.get_memory_embedding(
    source_type="note",
    source_id=note["id"],
    model=GEMINI_EMBEDDING_MODEL,
)

print({
    "note_id": note["id"],
    "cache_before_repair": before is not None,
    "notes_repaired": repair["sources"]["notes"]["repaired"],
    "notes_failed": repair["sources"]["notes"]["failed"],
    "cache_after_repair": after is not None,
})