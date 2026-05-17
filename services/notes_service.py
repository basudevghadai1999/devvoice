import json
import os
from datetime import datetime

NOTES_FILE = os.path.join(os.path.dirname(__file__), '..', 'notes.json')


def _load() -> list:
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, 'r') as f:
            return json.load(f)
    return []


def _save(notes: list):
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def add_note(content: str) -> str:
    notes = _load()
    notes.append({
        "id":         len(notes) + 1,
        "content":    content,
        "created_at": datetime.now().isoformat(),
    })
    _save(notes)
    return f"Note saved: {content}"


def search_notes(query: str) -> str:
    notes = _load()
    if not notes:
        return "You have no saved notes."

    if query:
        q = query.lower()
        matches = [n for n in notes if q in n['content'].lower()]
    else:
        matches = notes

    if not matches:
        return f"No notes found matching '{query}'."

    recent = matches[-5:]
    items  = [f"({n['id']}) {n['content']}" for n in recent]
    prefix = f"Found {len(matches)} note(s). " if query else f"Your last {len(recent)} note(s): "
    return prefix + " | ".join(items)


def delete_note(note_id: int) -> str:
    notes = _load()
    before = len(notes)
    notes  = [n for n in notes if n['id'] != note_id]
    if len(notes) == before:
        return f"No note with id {note_id}."
    _save(notes)
    return f"Note {note_id} deleted."
