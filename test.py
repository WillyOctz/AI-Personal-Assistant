from uuid import uuid4

from assistant import memory


note_text = f"embedding reuse test {uuid4().hex}"

first = memory.add_note(note_text)
second = memory.add_note(note_text)

print({
    "first_note_id": first["note_id"],
    "first_status": first["embedding"]["status"],
    "second_note_id": second["note_id"],
    "second_status": second["embedding"]["status"],
})

memory.delete_note(note_text)
memory.delete_note(note_text)