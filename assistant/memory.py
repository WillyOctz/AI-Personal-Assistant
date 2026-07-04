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

def add_reminder(reminder):
    memory = load_memory()
    clean_reminder = normalize_reminder_text(reminder)
    
    if clean_reminder in memory["reminders"]:
        return {
            "saved": False,
            "reminder": clean_reminder
        }
        
    memory["reminders"].append(clean_reminder)
    save_memory(memory)
    
    return {
        "saved": True,
        "reminder": clean_reminder
    }
    
def get_reminders():
    memory = load_memory()
    return memory["reminders"]

def cleanup_reminders():
    memory = load_memory()
    
    cleaned_reminders = []
    
    for reminder in memory["reminders"]:
        clean_reminder = normalize_reminder_text(reminder)
        
        if clean_reminder not in cleaned_reminders:
            cleaned_reminders.append(clean_reminder)
            
    removed_count = len(memory["reminders"]) - len(cleaned_reminders)
    
    memory["reminders"] = cleaned_reminders
    save_memory(memory)
    
    return removed_count

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



