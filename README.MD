# AI Personal Assistant - Nebula

Nebula is a learning-focused AI personal assistant built from basic Python logic before using advanced AI models.

## Current Version

### V10 - Conversation Intelligence + Chat Feedback

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

## Project Structure

```text
main.py
assistant/
  brain.py
  chat.py
  focus.py
  apps.py
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
- tools.py handles calculator, app launching, and file tools.
- trainer.py handles simple learning, token scoring, debugging, and evaluation.

### V11 - Data Quality / Training System

Planned next:

- Dataset stats
- Duplicate feedback detection
- Feedback cleanup
- Bad example removal
- Train/test split cleanup
- Better confusion reports
- Confidence calibration
- Tokenizer improvements

### AND MORE UPDATES SOON...😀😀😀
