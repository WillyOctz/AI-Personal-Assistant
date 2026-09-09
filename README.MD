# AI Personal Assistant - Nebula

Nebula is a learning-focused personal assistant built in Python. The project starts with explicit rule-based logic and small supervised-learning experiments, then gradually adds persistent memory, safe local automation, and an API layer.

(I'm still learning more about engineering an AI while making this, if any Senior or AI Developers or Engineers spot some mistakes or giving me advice on what to upgrade or to develop, feel free to tag or chat with me. Thank you 😀)

## Current Version

### V16.0 - Local API Foundation

Nebula still runs as a console assistant through `main.py`. It can now also be used through a local FastAPI server in `api.py`.

Start the console assistant:

```powershell
python main.py
```

Start the local API:

```powershell
python -m uvicorn api:app --reload
```

Open the local API documentation at `http://127.0.0.1:8000/docs`.

Nebula currently supports:

- Rule-based intent detection
- Simple supervised learning with JSONL feedback examples
- Intent debugging and model evaluation
- Personality-based greetings
- Profile memory
- Notes and reminders
- Reminder CRUD
- Reminder due dates
- Daily briefing
- Next task suggestion
- Pending task flow
- Focus mode
- Focus stats, notes, goals, streaks, and dashboard
- App registry and real app launching
- App aliases, defaults, allowlist, backups, and cleanup
- File search folders
- File listing, search, preview, range preview, around-line preview, and file info
- File search history, stats, cleanup, and safety checks
- Chat intents such as feelings, help, stuck, thanks, goodbye, identity, and capabilities
- Current conversation topic memory
- Repeat last response
- Explain last response with source, confidence, and scores
- Response feedback system
- Feedback stats, search, filters, health, dashboard, notes, and cleanup
- Refactored modules for focus, apps, and chat helpers
- Website registry with URL validation, allow/block policy, safe browser opening, confirmation, history, removal, and search
- Unified automation status for apps and websites
- Local HTTP API with `GET /health` and `POST /chat`

## Project Structure

```text
main.py
api.py
requirements.txt
assistant/
  brain.py
  chat.py
  focus.py
  apps.py
  websites.py
  tools.py
  memory.py
  personality.py
  intents.py
  trainer.py
datasets/
  memory.json
  examples.jsonl
  feedback.jsonl
  test_intents.jsonl
```

## Current Architecture

- brain.py routes user input to the correct handler.
- intents.py stores valid intents, intent groups, patterns, and prefixes.
- memory.py stores and retrieves persistent data.
- personality.py controls tone and personality responses.
- chat.py contains chat parsers, formatters, and chat-specific handlers.
- focus.py handles focus mode.
- apps.py handles registered app logic.
- websites.py handles registered website and browser-opening safety logic.
- tools.py handles calculator, app launching, and file tools.
- trainer.py handles simple learning, token scoring, debugging, and evaluation.

## Milestone History

### V1-V4 - Assistant Foundations

- Console conversation loop, rule-based intent detection, and token normalization
- JSONL examples and feedback data
- Basic supervised-learning-style scoring, debugging, confidence, and evaluation
- Personality responses and early conversation memory

### V5-V7 - Memory and Productivity

- Notes, profile facts, reminders, due dates, and reminder CRUD
- Semantic memory search with similarity, importance, and recency scores
- Conversation archiving, summaries, archive search, and pruning
- Focus sessions, goals, notes, stats, streaks, work-session reviews, and exports
- Reminder notifications, snoozing, dismissal, and daily briefing

### V8-V10 - Local Tools, Chat, and Data Quality

- Safe file search, listing, preview, content search, history, and cleanup
- App registry, aliases, defaults, allowlist, backups, cleanup, and real local launching
- Chat intent handling, response repeat/explain, topics, and response feedback
- Dataset inspection, duplicate/conflict checks, backups, restore, and example suggestions

### V15 - Safe Local Automation

- App launch confirmation and launch history
- Website registry, permission policy, safe opening, confirmation, history, removal, and search
- Unified local automation status

## Next: V16

### V16.1 - Local Web Interface

- Browser interface that sends messages to the local `/chat` API
- Conversation display and input controls
- Clear handling for pending yes/no confirmations

### V16.2 - Storage Upgrade

- Plan and migrate persistent data from JSON to SQLite
- Preserve the existing `memory.py` public functions during migration
- Add migration and backup checks before changing saved data

### V17 - LLM-Assisted Conversation

- Add an optional LLM provider or local model behind a dedicated adapter
- Keep deterministic routing and confirmation for external actions
- Retrieve relevant memory as context instead of placing all memory in prompts

### V18 - Optional Deployment

- Authentication, encrypted configuration, scheduled background reminders, and remote access
- Cloud deployment only after the local assistant is stable
