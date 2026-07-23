import json
from pathlib import Path

MEMORY_FILE = Path("datasets/memory.json")

def normalize_entity_name(value):
    return value.lower().strip()

def normalize_reminder_text(value):
    return value.lower().strip()

def load_memory():
    if not MEMORY_FILE.exists():
        return ensure_memory_shape({})
        
    with open(MEMORY_FILE, "r") as file:
        memory = json.load(file)
    
    return ensure_memory_shape(memory)
    
def set_state_value(key, value):
    memory = load_memory()
    memory["state"][key] = value
    save_memory(memory)
    
def get_state_value(key):
    memory = load_memory()
    return memory["state"].get(key)

def clear_state_value(key):
    memory = load_memory()
    memory["state"][key] = None
    save_memory(memory)

def ensure_memory_shape(memory):
    if "notes" not in memory:
        memory["notes"] = []
        
    if "profile" not in memory:
        memory["profile"] = {}
        
    if "reminders" not in memory:
        memory["reminders"] = []
        
    if "state" not in memory:
        memory["state"] = {}
        
    if "history" not in memory:
        memory["history"] = []
        
    if "conversation" not in memory:
        memory["conversation"] = []
        
    if "summaries" not in memory:
        memory["summaries"] = []
        
    if "pending_confirmation" not in memory["state"]:
        memory["state"]["pending_confirmation"] = None
        
    if "archive" not in memory:
        memory["archive"] = {}
        
    if "conversation" not in memory["archive"]:
        memory["archive"]["conversation"] = []
         
    if "archive_summaries" not in memory:
        memory["archive_summaries"] = []
        
    if "entities" not in memory:
        memory["entities"] = {}
        
    if "games" not in memory["entities"]:
        memory["entities"]["games"] = []
        
    if "apps" not in memory["entities"]:
        memory["entities"]["apps"] = []
        
    if "pending_task" not in memory["state"]:
        memory["state"]["pending_task"] = None
        
    if "focus_mode" not in memory["state"]:
        memory["state"]["focus_mode"] = False
        
    if "focus_task" not in memory["state"]:
        memory["state"]["focus_task"] = None
        
    if "focus_started_at" not in memory["state"]:
        memory["state"]["focus_started_at"] = None
        
    if "focus_sessions" not in memory:
        memory["focus_sessions"] = []
        
    if "focus_notes" not in memory["state"]:
        memory["state"]["focus_notes"] = []
        
    if "app_registry" not in memory:
        memory["app_registry"] = {}
        
    if "settings" not in memory:
        memory["settings"] = {}
        
    if "real_app_launching" not in memory["settings"]:
        memory["settings"]["real_app_launching"] = False
        
    if "app_launches" not in memory:
        memory["app_launches"] = []
        
    if "app_aliases" not in memory:
        memory["app_aliases"] = {}
        
    if "default_apps" not in memory:
        memory["default_apps"] = {}
        
    if "confirm_app_launching" not in memory["settings"]:
        memory["settings"]["confirm_app_launching"] = True
        
    if "pending_app_launch" not in memory["state"]:
        memory["state"]["pending_app_launch"] = None
        
    return memory

def archive_conversation_turns(turns_to_archive):
    memory = load_memory()
    
    remaining_turns = []
    archived_turns = []
    
    for turn in memory["conversation"]:
        if turn in turns_to_archive:
            archived_turns.append(turn)
        else:
            remaining_turns.append(turn)
            
    memory["conversation"] = remaining_turns
    memory["archive"]["conversation"].extend(archived_turns)
    
    save_memory(memory)
    
    return len(archived_turns)

def save_memory(memory):
    MEMORY_FILE.parent.mkdir(exist_ok=True)
    
    with open(MEMORY_FILE, "w") as file:
        json.dump(memory, file, indent=4)
        
def add_note(note):
    memory = load_memory()
    memory["notes"].append(note)
    save_memory(memory)
    
def get_notes():
    memory = load_memory()
    return memory["notes"]

def set_profile_value(key, value):
    memory = load_memory()
    memory["profile"][key] = value
    save_memory(memory)
    
def get_profile_value(key):
    memory = load_memory()
    return memory["profile"].get(key)

def get_profile():
    memory = load_memory()
    return memory["profile"]

def add_reminder(reminder, due=None):
    memory = load_memory()
    clean_reminder = normalize_reminder_text(reminder)
    
    for existing in memory["reminders"]:
        if get_reminder_text(existing) == clean_reminder:
            return {
                "saved": False,
                "reminder": clean_reminder,
                "due": get_reminder_due(existing)
            }
        
    memory["reminders"].append(make_reminder(clean_reminder, due))
    save_memory(memory)
    
    return {
        "saved": True,
        "reminder": clean_reminder,
        "due": due
    }
    
def edit_reminder(identifier, new_text):
    memory = load_memory()
    reminders = memory["reminders"]
    
    if not reminders:
        return {
            "edited": False,
            "reason": "empty",
            "old": None,
            "new": None
        }
        
    identifier = normalize_reminder_text(identifier)
    new_clean = normalize_reminder_text(new_text)
    
    if identifier.isdigit():
        index = int(identifier) - 1
        
        if index < 0 or index >= len(reminders):
            return {
                "edited": False,
                "reason": "invalid_index",
                "old": None,
                "new": None
            }
            
        old_reminder = reminders[index]
        old_text = get_reminder_text(old_reminder)
        old_due = get_reminder_due(old_reminder)
        
        reminders[index] = make_reminder(new_clean, old_due)
        save_memory(memory)
        
        return {
            "edited": True,
            "reason": "edited",
            "old": old_text,
            "new": new_clean
        }
        
    for index, reminder in enumerate(reminders):
        if get_reminder_text(reminder) == identifier:
            old_text = get_reminder_text(reminder)
            old_due = get_reminder_due(reminder)
            
            reminders[index] = make_reminder(new_clean, old_due)
            save_memory(memory)
            
            return {
                "edited": True,
                "reason": "edited",
                "old": old_text,
                "new": new_clean
            }
        
    return {
        "edited": False,
        "reason": "not_found",
        "old": identifier,
        "new": new_clean
    }
    
def get_reminders():
    memory = load_memory()
    return memory["reminders"]

def set_reminder_due(identifier, due):
    memory = load_memory()
    reminders = memory["reminders"]
    
    if not reminders:
        return {
            "updated": False,
            "reason": "empty",
            "reminder": None,
            "due": None
        }
        
    identifier = normalize_reminder_text(identifier)
    due = due.lower().strip()
    
    if identifier.isdigit():
        index = int(identifier) - 1
        
        if index < 0 or index >= len(reminders):
            return {
                "updated": False,
                "reason": "invalid_index",
                "reminder": None,
                "due": None
            }
            
        text = get_reminder_text(reminders[index])
        reminders[index] = make_reminder(text, due)
        save_memory(memory)
        
        return {
           "updated": True,
            "reason": "updated",
            "reminder": text,
            "due": due 
        }
        
    for index, reminder in enumerate(reminders):
        if get_reminder_text(reminder) == identifier:
            reminders[index] = make_reminder(identifier, due)
            save_memory(memory)
            
            return {
                "updated": True,
                "reason": "updated",
                "reminder": identifier,
                "due": due
            }
            
    return {
        "updated": False,
        "reason": "not_found",
        "reminder": identifier,
        "due": due
    }

def make_reminder(text, due=None):
    return {
        "text": normalize_reminder_text(text),
        "due": due
    }
    
def migrate_reminders_to_dicts():
    memory = load_memory()
    
    migrated_count = 0
    new_reminders = []
    
    for reminder in memory["reminders"]:
        if isinstance(reminder, dict):
            new_reminders.append({
                "text": get_reminder_text(reminder),
                "due": get_reminder_due(reminder)
            })
            continue
        
        new_reminders.append(make_reminder(reminder))
        migrated_count += 1
        
    memory["reminders"] = new_reminders
    save_memory(memory)
    
    return migrated_count
    
def get_reminder_text(reminder):
    if isinstance(reminder, dict):
        return reminder.get("text", "")
    
    return reminder

def get_reminder_due(reminder):
    if isinstance(reminder, dict):
        return reminder.get("due")
    
    return None

def get_reminder_stats():
    memory = load_memory()
    reminders = memory["reminders"]
    
    if not reminders:
        return {
            "total": 0,
            "first": None,
            "last": None
        }
        
    return {
        "total": len(reminders),
        "first": get_reminder_text(reminders[0]),
        "last": get_reminder_text(reminders[-1])
    }

def complete_reminder(identifier):
    memory = load_memory()
    reminders = memory["reminders"]
    
    if not reminders:
        return {
            "removed": False,
            "reason": "empty",
            "reminder": None
        }
        
    identifier = identifier.strip().lower()
    
    if identifier.isdigit():
        index = int(identifier) - 1
        
        if index < 0 or index >= len(reminders):
            return {
                "removed": False,
                "reason": "invalid_index",
                "reminder": None
            }
            
        removed_reminder = reminders.pop(index)
        save_memory(memory)
        
        return {
            "removed": True,
            "reason": "completed",
            "reminder": get_reminder_text(removed_reminder)
        }
        
    clean_identifier = normalize_reminder_text(identifier)
    
    for reminder in reminders:
        if get_reminder_text(reminder) == clean_identifier:
            reminders.remove(reminder)
            save_memory(memory)
            
            return {
                "removed": True,
                "reason": "completed",
                "reminder": clean_identifier
            }
        
    return {
        "removed": False,
        "reason": "not_found",
        "reminder": clean_identifier
    }
    
def clear_reminder_due(identifier):
    memory = load_memory()
    reminders = memory["reminders"]
    
    if not reminders:
        return {
           "updated": False,
            "reason": "empty",
            "reminder": None 
        }
        
    identifier = normalize_reminder_text(identifier)
    
    if identifier.isdigit():
        index = int(identifier) - 1
        
        if index < 0 or index >= len(reminders):
            return {
                "updated": False,
                "reason": "invalid_index",
                "reminder": None
            }
            
        text = get_reminder_text(reminders[index])
        reminders[index] = make_reminder(text, None)
        save_memory(memory)
        
        return {
            "updated": True,
            "reason": "updated",
            "reminder": text
        }
        
    for index, reminder in enumerate(reminders):
        if get_reminder_text(reminder) == identifier:
            reminders[index] = make_reminder(identifier, None)
            save_memory(memory)
            
            return {
               "updated": True,
                "reason": "updated",
                "reminder": identifier 
            }
            
    return {
        "updated": False,
        "reason": "not_found",
        "reminder": identifier
    }

def cleanup_reminders():
    memory = load_memory()
    
    cleaned_reminders = []
    seen_texts = set()
    
    for reminder in memory["reminders"]:
        text = get_reminder_text(reminder)
        clean_text = normalize_reminder_text(text)
        
        if clean_text in seen_texts:
            continue
        
        seen_texts.add(clean_text)
        
        if isinstance(reminder, dict):
            cleaned_reminders.append({
                "text": clean_text,
                "due": get_reminder_due(reminder)
            })
            
        else:
            cleaned_reminders.append(clean_text)
            
    removed_count = len(memory["reminders"]) - len(cleaned_reminders)
    
    memory["reminders"] = cleaned_reminders
    save_memory(memory)
    
    return removed_count

def search_reminders(query):
    memory = load_memory()
    query = normalize_reminder_text(query)
    
    results = []
    
    for index, reminder in enumerate(memory["reminders"], start=1):
        text = get_reminder_text(reminder)
        due = get_reminder_due(reminder)
        
        if query in text:
            results.append({
                "index": index,
                "reminder": get_reminder_text(reminder),
                "due": due,
            })
            
    return results

def search_reminders_by_due(due_query):
    memory = load_memory()
    due_query = due_query.lower().strip()
    
    results = []
    
    for index, reminder in enumerate(memory["reminders"], start=1):
        due = get_reminder_due(reminder)
        
        if not due:
            continue
        
        if due_query in due.lower():
            results.append({
                "index": index,
                "reminder": get_reminder_text(reminder),
                "due": due
            })
            
    return results

def add_history_event(event):
    memory = load_memory()
    memory["history"].append(event)
    save_memory(memory)
    
def get_history(limit=5):
    memory = load_memory()
    return memory["history"][-limit:]

def add_conversation_turn(turn):
    memory = load_memory()
    memory["conversation"].append(turn)
    save_memory(memory)
    
def get_conversation(limit=5):
    memory = load_memory()
    return memory["conversation"][-limit:]

def add_summary(summary):
    memory = load_memory()
    memory["summaries"].append(summary)
    save_memory(memory)
    
def get_summaries(limit=5):
    memory = load_memory()
    return memory["summaries"][-limit:]

def get_all_memory():
    return load_memory()

def get_archive():
    memory = load_memory()
    return memory["archive"]

def add_archive_summary(summary):
    memory = load_memory()
    memory["archive_summaries"].append(summary)
    save_memory(memory)
    
def get_archive_summaries(limit=5):
    memory = load_memory()
    return memory["archive_summaries"][-limit:]

def clear_archived_conversation():
    memory = load_memory()
    count = len(memory["archive"]["conversation"])
    memory["archive"]["conversation"] = []
    save_memory(memory)
    return count

def resolve_entity_conflict(entity_type, old_value, new_value):
    memory = load_memory()
    
    old_clean = normalize_entity_name(old_value)
    new_clean = normalize_entity_name(new_value)
    
    values = memory["entities"][entity_type]
    
    if old_clean in values:
        values.remove(old_clean)
        
    if new_clean not in values:
        values.append(new_clean)
        
    save_memory(memory)
    
    return {
        "old": old_clean,
        "new": new_clean
    }

def preview_entity_conflicts():
    memory = load_memory()
    
    conflicts = {}
    
    for entity_type, values in memory["entities"].items():
        entity_conflicts = []
        
        for short_value in values:
            for long_value in values:
                if short_value == long_value:
                    continue
                
                if short_value in long_value:
                    entity_conflicts.append({
                        "short": short_value,
                        "long": long_value
                    })
                
        conflicts[entity_type] = entity_conflicts
        
    return conflicts

def cleanup_entities():
    memory = load_memory()
    
    cleanup_report = {}
    
    for entity_type, values in memory["entities"].items():
        cleaned_values = []
        
        for value in values:
            clean_value = normalize_entity_name(value)
            
            if clean_value not in cleaned_values:
                cleaned_values.append(clean_value)
                
        removed_count = len(values) - len(cleaned_values)
        memory["entities"][entity_type] = cleaned_values
        cleanup_report[entity_type] = removed_count
        
    save_memory(memory)
    
    return cleanup_report

def add_entity(entity_type, value):
    memory = load_memory()
    clean_value = normalize_entity_name(value)
    
    if clean_value not in memory["entities"][entity_type]:
        memory["entities"][entity_type].append(clean_value)
        
    save_memory(memory)
    
def get_entities(entity_type):
    memory = load_memory()
    return memory["entities"].get(entity_type, [])

def add_focus_session(session):
    memory = load_memory()
    memory["focus_sessions"].append(session)
    save_memory(memory)
    
def get_focus_sessions(limit=5):
    memory = load_memory()
    return memory["focus_sessions"][-limit:]

def get_all_focus_sessions():
    memory = load_memory()
    return memory["focus_sessions"]

def search_focus_sessions(query):
    memory = load_memory()
    query = query.lower().strip()
    
    results = []
    
    for session in memory["focus_sessions"]:
        task = session.get("task", "")
        notes = session.get("notes", [])
        
        combined_text = task.lower() + " " + " ".join(notes).lower()
        
        if query in combined_text:
            results.append(session)
            
    return results

def delete_focus_session(recent_index, limit=5):
    memory = load_memory()
    sessions = memory["focus_sessions"]
    
    if not sessions:
        return {
            "deleted": False,
            "reason": "empty",
            "session": None
        }
        
    if recent_index < 1 or recent_index > min(limit, len(sessions)):
        return {
            "deleted": False,
            "reason": "invalid_index",
            "session": None
        }
        
    start_index = max(0, len(sessions) - limit)
    actual_index = start_index + recent_index - 1
    
    removed_session = sessions.pop(actual_index)
    save_memory(memory)
    
    return {
        "deleted": True,
        "reason": "deleted",
        "session": removed_session
    }
    
def cleanup_focus_sessions():
    memory = load_memory()
    sessions = memory["focus_sessions"]
    
    cleaned_sessions = []
    
    for session in sessions:
        has_task = bool(session.get("task"))
        has_started_at = bool(session.get("started_at"))
        has_ended_at = bool(session.get("ended_at"))
        has_duration = bool(session.get("duration"))
        
        if has_task and has_started_at and has_ended_at and has_duration:
            cleaned_sessions.append(session)
            
    removed_count = len(sessions) - len(cleaned_sessions)
    
    memory["focus_sessions"] = cleaned_sessions
    save_memory(memory)
    
    return removed_count

def search_focus_notes(query):
    memory = load_memory()
    query = query.lower().strip()
    
    results = []
    
    for session in memory["focus_sessions"]:
        notes = session.get("notes", [])
        
        matched_notes = []
        
        for note in notes:
            if query in note.lower():
                matched_notes.append(note)
                
        if matched_notes:
            results.append({
                "session": session,
                "notes": matched_notes
            })
            
    return results

def add_app_registry_entry(name, command):
    memory = load_memory()
    
    clean_name = normalize_entity_name(name)
    clean_command = command.strip()
    
    memory["app_registry"][clean_name] = {
        "name": clean_name,
        "command": clean_command,
        "allowed": False
    }
    
    save_memory(memory)
    
    return memory["app_registry"][clean_name]

def add_app_alias(alias, app_name):
    memory = load_memory()
    
    clean_alias = normalize_entity_name(alias)
    clean_app_name = normalize_entity_name(app_name)
    
    memory["app_aliases"][clean_alias] = clean_app_name
    save_memory(memory)
    
    return {
        "alias": clean_alias,
        "app_name": clean_app_name
    }
    
def resolve_app_alias(name):
    memory = load_memory()
    clean_name = normalize_entity_name(name)
    
    return memory["app_aliases"].get(clean_name, clean_name)

def get_app_aliases():
    memory = load_memory()
    return memory["app_aliases"]

def remove_app_alias(alias):
    memory = load_memory()
    clean_alias = normalize_entity_name(alias)
    
    if clean_alias not in memory["app_aliases"]:
        return {
            "removed": False,
            "alias": clean_alias,
            "app_name": None
        }
        
    app_name = memory["app_aliases"].pop(clean_alias)
    save_memory(memory)
    
    return {
        "removed": True,
        "alias": clean_alias,
        "app_name": app_name
    }

def get_app_registry_entry(name):
    memory = load_memory()
    clean_name = normalize_entity_name(name)
    
    return memory["app_registry"].get(clean_name)

def get_app_registry():
    memory = load_memory()
    return memory["app_registry"]

def remove_app_registry_entry(name):
    memory = load_memory()
    clean_name = normalize_entity_name(name)
    
    if clean_name not in memory["app_registry"]:
        return {
           "removed": False,
            "app": clean_name 
        }
        
    removed_app = memory["app_registry"].pop(clean_name)
    save_memory(memory)
    
    return {
        "removed": True,
        "app": removed_app
    }
    
def update_app_registry_entry(name, command):
    memory = load_memory()
    clean_name = normalize_entity_name(name)
    clean_command = command.strip()
    
    if clean_name not in memory["app_registry"]:
        return {
            "updated": False,
            "app": clean_name
        }
        
    memory["app_registry"][clean_name]["command"] = clean_command
    save_memory(memory)
    
    return {
        "updated": True,
        "app": memory["app_registry"][clean_name]
    }
    
def search_app_registry(query):
    memory = load_memory()
    query = normalize_entity_name(query)
    
    results = []
    
    for name, app in memory["app_registry"].items():
        command = app["command"].lower()
        
        if query in name or query in command:
            results.append(app)
            
    return results

def get_setting(key, default=None):
    memory = load_memory()
    return memory["settings"].get(key, default)

def set_setting(key, value):
    memory = load_memory()
    memory["settings"][key] = value
    save_memory(memory)
    
def set_app_allowed(name, allowed):
    memory = load_memory()
    clean_name = normalize_entity_name(name)
    
    if clean_name not in memory["app_registry"]:
        return {
            "updated": False,
            "app": clean_name
        }
        
    memory["app_registry"][clean_name]["allowed"] = allowed
    save_memory(memory)
    
    return {
        "updated": True,
        "app": memory["app_registry"][clean_name]
    }
    
def is_app_allowed(name):
    app = get_app_registry_entry(name)
    
    if not app:
        return False
    
    return app.get("allowed", False)
    
def add_app_launch(event):
    memory = load_memory()
    memory["app_launches"].append(event)
    save_memory(memory)
    
def get_app_launches(limit=10):
    memory = load_memory()
    return memory["app_launches"][-limit:]

def get_app_launch_stats():
    memory = load_memory()
    launches = memory["app_launches"]
    
    if not launches:
        return {
           "total": 0,
            "most_launched": None,
            "last_launched": None 
        }
        
    counts = {}
    
    for launch in launches:
        app_name = launch["app_name"]
        
        if app_name not in counts:
            counts[app_name] = 0
            
        counts[app_name] += 1
        
    most_launched = None
    most_count = 0
    
    for app_name, count in counts.items():
        if count > most_count:
            most_launched = app_name
            most_count = count
            
    return {
        "total": len(launches),
        "most_launched": most_launched,
        "most_count": most_count,
        "last_launched": launches[-1]["app_name"] 
    }
    
def set_default_app(category, app_name):
    memory = load_memory()
    
    clean_category = normalize_entity_name(category)
    clean_app_name = normalize_entity_name(app_name)
    
    memory["default_apps"][clean_category] = clean_app_name
    save_memory(memory)
    
    return {
        "category": clean_category,
        "app_name": clean_app_name
    }
    
def remove_default_app(category):
    memory = load_memory()
    clean_category = normalize_entity_name(category)
    
    if clean_category not in memory["default_apps"]:
        return {
            "removed": False,
            "category": clean_category,
            "app_name": None
        }
        
    app_name = memory["default_apps"].pop(clean_category)
    save_memory(memory)
    
    return {
        "removed": True,
        "category": clean_category,
        "app_name": app_name
    }
    
def get_default_app(category):
    memory = load_memory()
    clean_category = normalize_entity_name(category)
    
    return memory["default_apps"].get(clean_category)

def get_default_apps():
    memory = load_memory()
    return memory["default_apps"]

def preview_app_cleanup():
    memory = load_memory()
    
    registry = memory["app_registry"]
    aliases = memory["app_aliases"]
    defaults = memory["default_apps"]
    
    missing_command = []
    missing_allowed = []
    broken_aliases = []
    broken_defaults = []
    
    for name, app in registry.items():
        if not app.get("command"):
            missing_command.append(name)
            
        if "allowed" not in app:
            missing_allowed.append(name)
            
    for alias, app_name in aliases.items():
        if app_name not in registry:
            broken_aliases.append({
                "alias": alias,
                "app_name": app_name
            })
            
    for category, app_name in defaults.items():
        if app_name not in registry:
            broken_defaults.append({
                "category": category,
                "app_name": app_name
            })
            
    return {
        "missing_command": missing_command,
        "missing_allowed": missing_allowed,
        "broken_aliases": broken_aliases,
        "broken_defaults": broken_defaults
    }





