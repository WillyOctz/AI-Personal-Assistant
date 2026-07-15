from assistant.tools import get_time, create_reminder, open_app, play_game, safe_calculate
from assistant import memory
from assistant.personality import greet, unknown_response
from assistant.intents import VALID_INTENTS, SEARCH_IGNORED_INTENTS, MEMORY_INTENTS, MEMORY_TYPE_PRIORITY, ACTION_INTENTS, CONTROL_INTENTS, INTENT_PATTERNS, INTENT_PREFIXES, PROFILE_KEY_ALIASES, KNOWN_GAMES, KNOWN_APPS
from assistant.trainer import save_feedback, find_best_match, tokenize, predict_intent_with_model, evaluate_model, summarize_confusion, get_debug_weights, similarity_score
from datetime import datetime, timedelta

HIGH_CONFIDENCE = 0.75
LOW_CONFIDENCE = 0.55

def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_timestamp(timestamp):
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except:
        return None
    
def is_timestamp_today(timestamp):
    parsed_time = parse_timestamp(timestamp)
    
    if not parsed_time:
        return False
    
    now = datetime.now()
    
    return parsed_time.date() == now.date()

def is_timestamp_within_days(timestamp, days):
    parsed_time = parse_timestamp(timestamp)
    
    if not parsed_time:
        return False
    
    now = datetime.now()
    age = now - parsed_time
    
    return age.days < days
    
def parse_complete_reminder(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["complete reminder ", "done reminder ", "finish reminder "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_reminder_search(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["search reminders ", "find reminder "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_reminder_details(user_input):
    reminder_text = extract_entity(user_input, "set_reminder")
    
    if " at " in reminder_text:
        text, due = reminder_text.split(" at ", 1)
        return text.strip(), due.strip()
    
    if " tomorrow" in reminder_text:
        text = reminder_text.replace(" tomorrow", "", 1).strip()
        return text, "tomorrow"
    
    return reminder_text, None

def parse_edit_reminder(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["edit reminder ", "change reminder ", "update reminder "]:
        if text.startswith(prefix):
            text = text.replace(prefix, "", 1).strip()
            break
        
    if " as " not in text:
        return "", ""
    
    identifier, new_text = text.split(" as ", 1)
    
    return identifier.strip(),new_text.strip()

def parse_due_search(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["show reminders due ", "search reminders due ", "find reminders due "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_focus_task_query(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["focus stats for ", "focus summary for "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_focus_search(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["search focus ", "find focus "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def should_skip_memory_item(intent):
    return intent in SEARCH_IGNORED_INTENTS

def normalize_memory_text(text):
    return " ".join(tokenize(text))

def make_analysis(intent, confidence=1.0, source="rule", scores=None):
    if scores is None:
        scores = {}
        
    return {
        "intent": intent,
        "group": get_intent_group(intent),
        "confidence": confidence,
        "source": source,
        "scores": scores
    }
    
def match_exact_pattern(text, intent):
    patterns = INTENT_PATTERNS.get(intent, [])
    return text in patterns

def match_prefix_pattern(text, intent):
    prefixes = INTENT_PREFIXES.get(intent, [])
    
    for prefix in prefixes:
        if text.startswith(prefix):
            return True
        
    return False
    
def build_simple_summary(conversation):
    if not conversation:
        return "No conversation to summarize."
    
    intents = {}
    
    for turn in conversation:
        intent = turn["intent"]
        
        if intent not in intents:
            intents[intent] = 0
            
        intents[intent] += 1
        
    intent_parts = []
    
    for intent, count in intents.items():
        intent_parts.append(f"{intent}: {count}")
        
    last_user_message = conversation[-1]["user"]
    
    return (
        f"Recent conversation had {len(conversation)} turns. "
        f"Intent counts: {', '.join(intent_parts)}. "
        f"Last user message was: {last_user_message}"
    )
    
def log_action(user_input, analysis, result):
    event = {
        "user_input": user_input,
        "intent": analysis["intent"],
        "group": analysis["group"],
        "confidence": analysis["confidence"],
        "source": analysis["source"],
        "result": result,
        "timestamp": current_timestamp(),
        "importance": calculate_importance(user_input, analysis),
    }
    
    memory.add_history_event(event)
    
def log_conversation(user_input, assistant_response, analysis):
    turn = {
        "user": user_input,
        "assistant": assistant_response,
        "intent": analysis["intent"],
        "group": analysis["group"],
        "confidence": analysis["confidence"],
        "source": analysis["source"],
        "timestamp": current_timestamp(),
        "importance": calculate_importance(user_input, analysis),
    }
    
    memory.add_conversation_turn(turn)
    
def parse_recall_source(user_input):
    text = user_input.lower()
    
    if text.startswith("recall notes about "):
        return "note", user_input.replace("recall notes about ", "", 1).strip()

    if text.startswith("recall history about "):
        return "history", user_input.replace("recall history about ", "", 1).strip()

    if text.startswith("recall archive about "):
        return "archive_summary", user_input.replace("recall archive about ", "", 1).strip()
    
    return None, ""

def normalize_profile_key(raw_key):
    key = raw_key.lower().strip()
    key = key.replace("?", "")
    
    if key in PROFILE_KEY_ALIASES:
        return PROFILE_KEY_ALIASES[key]
    
    key = key.replace(" ", "_")
    return key

def parse_profile_question(user_input):
    text = user_input.lower().strip()
    text = text.replace("?", "")
    
    if text.startswith("what is my "):
        key = text.replace("what is my ", "", 1).strip()
    elif text.startswith("what's my "):
        key = text.replace("what's my ", "", 1).strip()
    else:
        return ""
    
    return normalize_profile_key(key)

def parse_profile_fact(user_input):
    text = user_input.replace("remember profile ", "", 1).strip()
    
    parts = text.split(" ", 1)
    
    if len(parts) < 2:
        return None, None
    
    key = normalize_profile_key(parts[0])
    value = parts[1]
    
    return key, value

def parse_entity_resolution(user_input):
    text = user_input.lower().strip()
    
    if not text.startswith("resolve entity "):
        return None, None, None
    
    text = text.replace("resolve entity ", "", 1)
    
    if " as "not in text:
        return None, None, None
    
    left, new_value = text.split(" as ", 1)
    
    parts = left.split(" ", 1)
    
    if len(parts) < 2:
        return None, None, None
    
    entity_label = parts[0]
    old_value = parts[1]
    
    if entity_label == "game":
        entity_type = "games"
    elif entity_label == "app":
        entity_type = "apps"
    else:
        return None, None, None
    
    return entity_type, old_value.strip(), new_value.strip()

def parse_set_reminder_due(user_input):
    text = user_input.lower().strip()

    if not text.startswith("set reminder "):
        return "", ""

    text = text.replace("set reminder ", "", 1)

    if " due " not in text:
        return "", ""

    identifier, due = text.split(" due ", 1)

    return identifier.strip(), due.strip()

def parse_clear_reminder_due(user_input):
    text = user_input.lower().strip()

    if not text.startswith("clear reminder "):
        return ""

    text = text.replace("clear reminder ", "", 1)

    if not text.endswith(" due"):
        return ""

    return text.replace(" due", "", 1).strip()

def parse_duration_to_seconds(text):
    if not text:
        return None
    
    parts = text.lower().strip().split()
    
    if len(parts) < 2:
        return None
    
    number_text = parts[0]
    unit = parts[1]
    
    if not number_text.isdigit():
        return None
    
    number = int(number_text)
    
    if unit in ["second", "seconds"]:
        return number
    
    if unit in ["minute", "minutes"]:
        return number * 60
    
    if unit in ["hour", "hours"]:
        return number * 3600
    
    return None

def get_first_reminder_text(results):
    if not results:
        return None
    
    return results[0]["reminder"]

def get_first_general_reminder():
    reminders = memory.get_reminders()
    
    if not reminders:
        return None
    
    first = reminders[0]
    
    return {
        "reminder": memory.get_reminder_text(first),
        "due": memory.get_reminder_due(first)
    }

def count_reminders_by_due_label(label):
    results = memory.search_reminders_by_due(label)
    return len(results)

def format_reminder_results(title, results):
    if not results:
        return f"No reminders found for {title.lower()}."
    
    lines = [title]
    
    for result in results:
        lines.append(f"{result['index']}. {result['reminder']} | due: {result['due']}")
        
    return "\n".join(lines)

def format_recall_item(item):
    if item["type"] == "archive_summary":
        return "Archive summary mentions this topic."
    
    return item["display"]

def format_focus_session_summary(task, duration, notes):
    lines = [
        "Focus session summary:",
        f"Task: {task}",
        f"Duration: {duration}",
        f"Notes: {len(notes)}"
    ]
    
    for note in notes:
        lines.append(f"- {note}")
        
    return "\n".join(lines)

def set_pending_task(reminder_text):
    memory.set_state_value("pending_task", reminder_text)
    
def get_pending_task():
    return memory.get_state_value("pending_task")

def clear_pending_task():
    memory.clear_state_value("pending_task")
    
def start_focus_mode(task):
    memory.set_state_value("focus_mode", True)
    memory.set_state_value("focus_task", task)
    memory.set_state_value("focus_started_at", current_timestamp())
    
    clear_current_focus_notes()
    
def get_focus_started_at():
    return memory.get_state_value("focus_started_at")
    
def stop_focus_mode():
    started_at = get_focus_started_at()
    
    memory.set_state_value("focus_mode", False)
    memory.clear_state_value("focus_task")
    memory.clear_state_value("focus_started_at")
    
    return started_at
    
def get_focus_mode():
    return memory.get_state_value("focus_mode")

def get_focus_task():
    return memory.get_state_value("focus_task")

def get_focus_session_dates():
    sessions = memory.get_all_focus_sessions()
    dates = set()
    
    for session in sessions:
        parsed_time = parse_timestamp(session["started_at"])
        
        if parsed_time:
            dates.add(parsed_time.date())
            
    return dates

def save_focus_session(task, started_at):
    ended_at = current_timestamp()
    duration = format_duration_since(started_at)
    
    session = {
        "task": task,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration": duration,
        "notes": get_current_focus_notes()
    }
    
    memory.add_focus_session(session)
    memory.add_focus_session(session)
    clear_current_focus_notes()
    
    return {
        "duration": duration,
        "notes": session["notes"]
    }

def get_focus_goal_progress_summary():
    goal_text = memory.get_profile_value("focus_goal")
    
    if not goal_text:
        return None
    
    goal_seconds = parse_duration_to_seconds(goal_text)
    
    if not goal_seconds:
        return {
            "goal": goal_text,
            "progress": None,
            "today_focus": None
        }
        
    stats = build_today_focus_stats()
    today_seconds = stats["total_seconds"]
    
    progress = int((today_seconds / goal_seconds)* 100)
    
    if progress > 100:
        progress = 100
        
    return {
        "goal": goal_text,
        "progress": progress,
        "today_focus": format_duration_from_seconds(today_seconds)
    }

def parse_focus_goal(user_input):
    text = user_input.lower().strip()
    
    if not text.startswith("set focus goal "):
        return ""
    
    return text.replace("set focus goal ", "", 1).strip()

def parse_focus_note(user_input):
    text = user_input.strip()
    
    if not text.lower().startswith("focus note "):
        return ""
    
    return text[11:].strip()

def parse_focus_note_search(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["search focus notes ", "find focus notes "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_delete_focus_session(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["delete focus session ", "remove focus session "]:
        if text.startswith(prefix):
            value = text.replace(prefix, "", 1).strip()
            
            if value.isdigit():
                return int(value)
            
    return None

def build_focus_stats():
    sessions = memory.get_all_focus_sessions()
    
    if not sessions:
        return {
            "total_sessions": 0,
            "total_seconds": 0,
            "last_focus": None
        }
        
    total_seconds = 0
    
    for session in sessions:
        total_seconds += calculate_duration_seconds(
            session["started_at"],
            session["ended_at"]
        )
        
    return {
        "total_sessions": len(sessions),
        "total_seconds": total_seconds,
        "last_focus": sessions[-1]["task"]
    }
    
def build_focus_stats_for_task(query):
    sessions = memory.get_all_focus_sessions()
    query = query.lower().strip()
    
    matched_sessions = []
    
    for session in sessions:
        task = session["task"].lower()
        
        if query in task:
            matched_sessions.append(session)
            
    if not matched_sessions:
        return {
           "total_sessions": 0,
            "total_seconds": 0,
            "last_focus": None 
        }
        
    total_seconds = 0
    
    for session in matched_sessions:
        total_seconds += calculate_duration_seconds(
            session["started_at"],
            session["ended_at"]
        )
        
    return {
        "total_sessions": len(matched_sessions),
        "total_seconds": total_seconds,
        "last_focus": matched_sessions[-1]["task"]
    }
    
def build_today_focus_stats():
    sessions = memory.get_all_focus_sessions()
    
    today_sessions = []
    
    for session in sessions:
        if is_timestamp_today(session["started_at"]):
            today_sessions.append(session)
            
    if not today_sessions:
        return {
            "total_sessions": 0,
            "total_seconds": 0,
            "last_focus": None
        }
        
    total_seconds = 0
    
    for session in today_sessions:
        total_seconds += calculate_duration_seconds(
            session["started_at"],
            session["ended_at"]
        )
        
    return {
        "total_sessions": len(today_sessions),
        "total_seconds": total_seconds,
        "last_focus": today_sessions[-1]["task"]
    }
    
def build_recent_focus_stats(days):
    sessions = memory.get_all_focus_sessions()
    
    recent_sessions = []
    
    for session in sessions:
        if is_timestamp_within_days(session["started_at"], days):
            recent_sessions.append(session)
            
    if not recent_sessions:
        return {
            "total_sessions": 0,
            "total_seconds": 0,
            "last_focus": None
        }
        
    total_seconds = 0
    
    for session in recent_sessions:
        total_seconds += calculate_duration_seconds(
            session["started_at"],
            session["ended_at"]
        )
        
    return {
        "total_sessions": len(recent_sessions),
        "total_seconds": total_seconds,
        "last_focus": recent_sessions[-1]["task"]
    }
    
def build_simple_focus_streak():
    dates = get_focus_session_dates()
    
    return {
        "focused_days": len(dates)
    }
    
def build_true_focus_streak():
    dates = get_focus_session_dates()
    
    if not dates:
        return {
            "focused_days": 0,
            "current_streak": 0,
            "longest_streak": 0
        }
        
    today = datetime.now().date()
    current_day = today
    current_streak = 0
    
    while current_day in dates:
        current_streak += 1
        current_day = current_day - timedelta(days=1)
        
    longest_streak = calculate_longest_streak(dates)
        
    return {
        "focused_days": len(dates),
        "current_streak": current_streak,
        "longest_streak": longest_streak
    }
    
def calculate_longest_streak(dates):
    if not dates:
        return 0
    
    sorted_dates = sorted(dates)
    
    longest_streak = 1
    current_streak = 1
    
    for index in range(1, len(sorted_dates)):
        previous_day = sorted_dates[index - 1]
        current_day = sorted_dates[index]
        
        if current_day == previous_day + timedelta(days=1):
            current_streak += 1
        else:
            current_streak = 1
            
        if current_streak > longest_streak:
            longest_streak = current_streak
            
    return longest_streak

def find_known_entity(text, known_entities):
    text = text.lower()
    
    sorted_entities = sorted(
        known_entities,
        key=len,
        reverse=True
    )
    
    for entity in sorted_entities:
        if entity in text:
            return entity
        
    return None

def apply_entity_hints(text, analysis):
    tokens = tokenize(text)
    
    known_games = set(KNOWN_GAMES)
    known_games.update(memory.get_entities("games"))
    
    matched_game = find_known_entity(text, known_games)
    
    known_apps = set(KNOWN_APPS)
    known_apps.update(memory.get_entities("apps"))
    
    matched_app = find_known_entity(text, known_apps)
    
    for token in tokens:
        if matched_game and analysis["intent"] in ["minecraft", "play_music", None, "unknown"]:
            new_analysis = make_analysis(
                "play_game",
                confidence=max(analysis["confidence"], 0.8),
                source="entity_hint",
                scores=analysis["scores"]
            )
            
            new_analysis["hint_reason"] = f"'{matched_game}' is a known game"
            
            return new_analysis
            
    for token in tokens:
        if matched_app and analysis["intent"] in [None, "unknown"]:
            new_analysis = make_analysis(
                "open_app",
                confidence=max(analysis["confidence"], 0.8),
                source="entity_hint",
                scores=analysis["scores"]
            )
            
            new_analysis["hint_reason"] = f"'{matched_app}' is a known app"
            
            return new_analysis
        
    return analysis

def choose_focus_task():
    pending_task = get_pending_task()
    
    if pending_task:
        return pending_task
    
    overdue_results = memory.search_reminders_by_due("yesterday")
    
    if overdue_results:
        return overdue_results[0]["reminder"]
    
    today_results =  memory.search_reminders_by_due("today")
    
    if today_results:
        return today_results[0]["reminder"]
    
    general_reminder = get_first_general_reminder()
    
    if general_reminder:
        return general_reminder["reminder"]
    
    goal = memory.get_profile_value("goal")
    
    if goal:
        return f"work toward your goal - {goal}"
    
    return None

def add_current_focus_note(note):
    notes = memory.get_state_value("focus_notes")
    
    if notes is None:
        notes = []
        
    notes.append(note)
    memory.set_state_value("focus_notes", notes)
    
def get_current_focus_notes():
    notes = memory.get_state_value("focus_notes")
    
    if notes is None:
        return []
    
    return notes

def clear_current_focus_notes():
    memory.set_state_value("focus_notes", [])

def analyze_intent(user_input):
    text = user_input.lower()
    
    if match_exact_pattern(text, "complete_pending_task"):
        return make_analysis("complete_pending_task")
    
    if match_exact_pattern(text, "skip_pending_task"):
        return make_analysis("skip_pending_task")
    
    if match_exact_pattern(text, "show_pending_task"):
        return make_analysis("show_pending_task")
    
    if text in ["yes", "yeah", "yep", "correct"]:
        return make_analysis("confirm_intent")
    
    if text in ["no", "nope", "wrong"]:
        return make_analysis("deny_intent")
    
    if match_prefix_pattern(text, "debug_memory_search"):
        return make_analysis("debug_memory_search")
    
    if match_prefix_pattern(text, "debug_entity"):
        return make_analysis("debug_entity")
    
    if match_prefix_pattern(text, "debug_model"):
        return make_analysis("debug_model")

    if match_prefix_pattern(text, "debug_match"):
        return make_analysis("debug_match")

    if match_exact_pattern(text, "evaluate_model"):
        return make_analysis("evaluate_model")
    
    if match_exact_pattern(text, "debug_focus_goal"):
        return make_analysis("debug_focus_goal")
    
    if match_exact_pattern(text, "coding_help"):
        return make_analysis("coding_help")

    if match_prefix_pattern(text, "teach_intent"):
        return make_analysis("teach_intent")

    if match_exact_pattern(text, "greeting"):
        return make_analysis("greeting")

    if "time" in text:
        return make_analysis("get_time")
    
    if match_prefix_pattern(text, "set_profile_fact"):
        return make_analysis("set_profile_fact")
    
    if match_exact_pattern(text, "show_profile"):
        return make_analysis("show_profile")
    
    if match_exact_pattern(text, "show_reminders"):
        return make_analysis("show_reminders")
    
    if match_prefix_pattern(text, "remember_game_entity"):
        return make_analysis("remember_game_entity")
    
    if match_prefix_pattern(text, "remember_app_entity"):
        return make_analysis("remember_app_entity")
    
    if match_prefix_pattern(text, "show_entities"):
        return make_analysis("show_entities")
    
    if match_prefix_pattern(text, "resolve_entity_conflict"):
        return make_analysis("resolve_entity_conflict")

    if match_prefix_pattern(text, "remember_note"):
        return make_analysis("remember_note")

    if "show notes" in text:
        return make_analysis("show_notes")

    if text.startswith("my name is "):
        return make_analysis("set_name")

    if "what is my name" in text:
        return make_analysis("get_name")
    
    if text in ["history", "show history", "what did you do recently"]:
        return make_analysis("show_history")
    
    if text in ["show conversation", "conversation history", "what did we talk about"]:
        return make_analysis("show_conversation")
    
    if text in ["summarize conversation", "summarize our chat"]:
        return make_analysis("summarize_conversation")
    
    if text in ["show summaries", "conversation summaries"]:
        return make_analysis("show_summaries")
    
    if match_prefix_pattern(text, "search_reminders_by_due"):
        return make_analysis("search_reminders_by_due")
    
    if match_prefix_pattern(text, "search_reminders"):
        return make_analysis("search_reminders")
    
    if match_prefix_pattern(text, "search_memory"):
        return make_analysis("search_memory")
    
    if match_exact_pattern(text, "preview_entity_conflicts"):
        return make_analysis("preview_entity_conflicts")
    
    if match_prefix_pattern(text, "semantic_memory_search"):
        return make_analysis("semantic_memory_search")
    
    if text in ["memory stats", "show memory stats"]:
        return make_analysis("memory_stats")
    
    if text in ["preview memory cleanup", "memory cleanup preview"]:
        return make_analysis("preview_memory_cleanup")
    
    if text in ["archive memory cleanup", "cleanup memory archive"]:
        return make_analysis("archive_memory_cleanup")
    
    if match_exact_pattern(text, "cleanup_entities"):
        return make_analysis("cleanup_entities")
    
    if match_exact_pattern(text, "cleanup_reminders"):
        return make_analysis("cleanup_reminders")
    
    if match_prefix_pattern(text, "search_archive"):
        return make_analysis("search_archive")
    
    if text in ["archive stats", "show archive stats"]:
        return make_analysis("archive_stats")
    
    if text in ["preview archive summary", "summarize archive preview"]:
        return make_analysis("preview_archive_summary")
    
    if text in ["save archive summary", "compress archive"]:
        return make_analysis("save_archive_summary")
    
    if text in ["show archive summaries", "archive summaries"]:
        return make_analysis("show_archive_summaries")
    
    if text in ["prune archive", "clear archive conversation"]:
        return make_analysis("prune_archive")
    
    if match_prefix_pattern(text, "recall_memory"):
        return make_analysis("recall_memory")
    
    if match_prefix_pattern(text, "recall_memory_source"):
        return make_analysis("recall_memory_source")

    if text.startswith("recall history about "):
        return make_analysis("recall_memory_source")

    if text.startswith("recall archive about "):
        return make_analysis("recall_memory_source")
    
    if match_prefix_pattern(text, "get_profile_fact"):
        return make_analysis("get_profile_fact")
    
    if match_prefix_pattern(text, "calculate"):
        return make_analysis("calculate")
    
    if match_prefix_pattern(text, "complete_reminder"):
        return make_analysis("complete_reminder")
    
    if match_exact_pattern(text, "reminder_stats"):
        return make_analysis("reminder_stats")
    
    if match_prefix_pattern(text, "edit_reminder"):
        return make_analysis("edit_reminder")
    
    if match_exact_pattern(text, "migrate_reminders"):
        return make_analysis("migrate_reminders")
    
    if match_prefix_pattern(text, "clear_reminder_due") and text.endswith(" due"):
        return make_analysis("clear_reminder_due")

    if match_prefix_pattern(text, "set_reminder_due") and " due " in text:
        return make_analysis("set_reminder_due")
    
    if match_exact_pattern(text, "today_reminders"):
        return make_analysis("today_reminders")
    
    if match_exact_pattern(text, "tomorrow_reminders"):
        return make_analysis("tomorrow_reminders")
    
    if match_exact_pattern(text, "overdue_reminders"):
        return make_analysis("overdue_reminders")
    
    if match_exact_pattern(text, "reminder_dashboard"):
        return make_analysis("reminder_dashboard")
    
    if match_exact_pattern(text, "start_focus"):
        return make_analysis("start_focus")
    
    if match_exact_pattern(text, "stop_focus"):
        return make_analysis("stop_focus")
    
    if match_exact_pattern(text, "focus_status"):
        return make_analysis("focus_status")
    
    if match_exact_pattern(text, "suggest_next_task"):
        return make_analysis("suggest_next_task")
    
    if match_exact_pattern(text, "daily_briefing"):
        return make_analysis("daily_briefing")
    
    if match_exact_pattern(text, "show_focus_sessions"):
        return make_analysis("show_focus_sessions")
    
    if match_exact_pattern(text, "today_focus_stats"):
        return make_analysis("today_focus_stats")
    
    if match_prefix_pattern(text, "focus_stats_for_task"):
        return make_analysis("focus_stats_for_task")
    
    if match_exact_pattern(text, "weekly_focus_stats"):
        return make_analysis("weekly_focus_stats")
    
    if match_exact_pattern(text, "focus_stats"):
        return make_analysis("focus_stats")
    
    if match_exact_pattern(text, "focus_streak"):
        return make_analysis("focus_streak")
    
    if match_prefix_pattern(text, "set_focus_goal"):
        return make_analysis("set_focus_goal")
    
    if match_exact_pattern(text, "show_focus_goal"):
        return make_analysis("show_focus_goal")
    
    if match_exact_pattern(text, "focus_goal_progress"):
        return make_analysis("focus_goal_progress")
    
    if match_prefix_pattern(text, "add_focus_note"):
        return make_analysis("add_focus_note")
    
    if match_exact_pattern(text, "show_current_focus_notes"):
        return make_analysis("show_current_focus_notes")
    
    if match_prefix_pattern(text, "search_focus_notes"):
        return make_analysis("search_focus_notes")
    
    if match_prefix_pattern(text, "search_focus_sessions"):
        return make_analysis("search_focus_sessions")
    
    if match_prefix_pattern(text, "delete_focus_session"):
        return make_analysis("delete_focus_session")
    
    if match_exact_pattern(text, "cleanup_focus_sessions"):
        return make_analysis("cleanup_focus_sessions")
        
    model_intent, model_confidence, scores = predict_intent_with_model(user_input)
    
    if model_intent:
        analysis = make_analysis(
            model_intent,
            model_confidence,
            source= "model",
            scores=scores
        )
        
        return apply_entity_hints(text, analysis)
        
    analysis = make_analysis("unknown", confidence=0, source="None")
    return apply_entity_hints(text, analysis)

def get_memory_stats():
    memory = memory.get_all_memory()
    
    return {
        "notes": len(memory["notes"]),
        "reminders": len(memory["reminders"]),
        "history": len(memory["history"]),
        "conversation": len(memory["conversation"]),
        "summaries": len(memory["summaries"]),
        "archived_conversation": len(memory["archive"]["conversation"]),
    }
    
def get_profile_context():
    profile = memory.get_profile()
    
    name = profile.get("name")
    goal = profile.get("goal")
    favorite_language = profile.get("favorite_language")
    
    parts = []
    
    if name:
        parts.append(f"your name is {name}")
        
    if goal:
        parts.append(f"your goal is {goal}")
        
    if favorite_language:
        parts.append(f"you like {favorite_language}")
        
    if not parts:
        return ""
    
    return ", ".join(parts)

def collect_memory_search_items():
    memory = memory.get_all_memory()
    items = []
    
    for note in memory["notes"]:
        items.append({
            "type": "note",
            "text": note,
            "display": f"Note: {note}",
            "importance": 1.0,
            "priority": MEMORY_TYPE_PRIORITY["note"],
            "recency": 1.0
        })
        
    for reminder in memory["reminders"]:
        items.append({
            "type": "reminder",
            "text": reminder,
            "display": f"Reminder: {reminder}",
            "importance": 1.0,
            "priority": MEMORY_TYPE_PRIORITY["reminder"],
            "recency": 1.0
        })
        
    for event in memory["history"]:
        if should_skip_memory_item(event["intent"]):
            continue
        
        text = f"{event['user_input']} {event['intent']} {event['result']}"
        items.append({
            "type": "history",
            "text": text,
            "display": f"History: {event['timestamp']} | {event['intent']} | {event['user_input']}",
            "importance": event.get("importance", 0.8),
            "priority": MEMORY_TYPE_PRIORITY["history"],
            "recency": calculate_recency(event["timestamp"])
        })
        
    for turn in memory["conversation"]:
        if should_skip_memory_item(turn["intent"]):
            continue
        
        text = f"{turn['user']} {turn['assistant']} {turn['intent']}"
        items.append({
            "type": "conversation",
            "text": text,
            "display": f"Conversation: {turn['timestamp']} | You: {turn['user']}",
            "importance": turn.get("importance", 0.5),
            "priority": MEMORY_TYPE_PRIORITY["conversation"],
            "recency": calculate_recency(turn["timestamp"])
        })
        
    for summary in memory["summaries"]:
        items.append({
            "type": "summary",
            "text": summary["summary"],
            "display": f"Summary: {summary['timestamp']} | {summary['summary']}",
            "importance": 0.7,
            "priority": MEMORY_TYPE_PRIORITY["summary"],
            "recency": calculate_recency(summary["timestamp"])
        })
        
    for summary in memory["archive_summaries"]:
        items.append({
            "type": "archive_summary",
            "text": summary["summary"],
            "display": f"Archive summary: {summary['timestamp']} | {summary['summary']}",
            "importance": 0.6,
            "recency": calculate_recency(summary["timestamp"]),
            "priority": MEMORY_TYPE_PRIORITY["archive_summary"]
        })
        
    return items

def preview_memory_cleanup():
    memory = memory.get_all_memory()
    
    low_importance_turns = []
    control_turns = []
    
    for turn in memory["conversation"]:
        importance = turn.get("importance", 0.5)
        intent = turn.get("intent")
        
        if importance <= 0.2:
            low_importance_turns.append(turn)
            
        if intent in SEARCH_IGNORED_INTENTS:
            control_turns.append(turn)
            
    return {
       "low_importance_turns": low_importance_turns,
        "control_turns": control_turns 
    }

def semantic_search_memory(query, limit=5, min_score=0.3, source_type=None):
    items = collect_memory_search_items()
    scored_results = []
    
    for item in items:
        if source_type and item["type"] != source_type:
            continue
        
        similarity = similarity_score(query, item["text"])
        score = similarity * item["importance"] * item["recency"]
        
        if score >= min_score:
            scored_results.append({
                "score": score,
                "similarity": similarity,
                "importance": item["importance"],
                "recency": item["recency"],
                "item": item
            })
        
    scored_results.sort(key=lambda result: (
            result["score"],
            result["item"]["priority"]
        ),
    reverse=True
    )
    
    unique_results = []
    seen_texts = set()
    
    for result in scored_results:
        normalized = normalize_memory_text(result["item"]["text"])
        
        if normalized in seen_texts:
            continue
        
        seen_texts.add(normalized)
        unique_results.append(result)
        
    return unique_results[:limit]

def search_archive(query):
    archive = memory.get_archive()
    query = query.lower()
    
    results = []
    
    for turn in archive["conversation"]:
        text = f"{turn['user']} {turn['assistant']} {turn['intent']}".lower()
        
        if query in text:
            results.append(
                f"{turn['timestamp']} | You: {turn['user']}"
            )
            
    return results

def get_archive_stats():
    archive = memory.get_archive()
    conversation = archive["conversation"]
    
    if not conversation:
        return {
            "archived_conversation": 0,
            "ignored_intents": 0,
            "oldest": None,
            "newest": None
        }
        
    ignored_intents = 0
    
    for turn in conversation:
        if turn["intent"] in SEARCH_IGNORED_INTENTS:
            ignored_intents += 1
            
    timestamps = [turn["timestamp"] for turn in conversation]
    
    return {
        "archived_conversation": len(conversation),
        "ignored_intents": ignored_intents,
        "oldest": min(timestamps),
        "newest": max(timestamps)
    }

def debug_memory_search(query, limit=5):
    items = collect_memory_search_items()
    debug_results = []
    
    for item in items:
        similarity = similarity_score(query, item["text"])
        score = similarity * item["importance"] * item["recency"]
        
        debug_results.append({
            "score": score,
            "similarity": similarity,
            "importance": item["importance"],
            "recency": item["recency"],
            "item": item,
            "tokens": tokenize(item["text"]) 
        })
        
    debug_results.sort(key=lambda result: result["score"], reverse=True)
    
    return debug_results[:limit]

def calculate_importance(user_input, analysis):
    intent = analysis["intent"]
    group = analysis["group"]
    
    if intent in ["set_name", "remember_note", "set_reminder"]:
        return 1.0
    
    if group == "action":
        return 0.8
    
    if group == "memory":
        return 0.6
    
    if group == "basic":
        return 0.2
    
    if group == "control":
        return 0.1
    
    return 0.3
        
def calculate_recency(timestamp):
    parsed_time = parse_timestamp(timestamp)     
    
    if not parsed_time:
        return 0.5
    
    now = datetime.now()
    age = now - parsed_time
    age_days = age.total_seconds() / 86400
    
    if age_days <= 1:
        return 1.0
    
    if age_days <= 7:
        return 0.8
    
    if age_days <= 30:
        return 0.6
    
    return 0.4

def format_duration_since(timestamp):
    parsed_time = parse_timestamp(timestamp)
    
    if not parsed_time:
        return "unknown"
    
    now = datetime.now()
    duration = now - parsed_time
    total_seconds = int(duration.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds} seconds"
    
    minutes = total_seconds // 60
    
    if minutes < 60:
        return f"{minutes} minutes"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    return f"{hours} hours {remaining_minutes} minutes"

def format_duration_from_seconds(total_seconds):
    if total_seconds < 60:
        return f"{total_seconds} seconds"
    
    minutes = total_seconds // 60
    
    if minutes < 60:
        return f"{minutes} minutes"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    return f"{hours} hours {remaining_minutes} minutes"

def calculate_duration_seconds(started_at, ended_at):
    start = parse_timestamp(started_at)
    end = parse_timestamp(ended_at)
    
    if not start or not end:
        return 0
    
    duration = end - start
    return int(duration.total_seconds())

def get_intent_group(intent):
    if intent in CONTROL_INTENTS:
        return "control"
    
    if intent in MEMORY_INTENTS:
        return "memory"
    
    if intent in ACTION_INTENTS:
        return "action"
    
    if intent == "greeting" or intent == "get_time":
        return "basic"
    
    return "unknown"

def extract_after_keyword(user_input, keywords):
    text = user_input.lower()
    
    for keyword in keywords:
        if keyword in text:
            return text.split(keyword, 1)[1].strip()
        
    return ""

def extract_calculation_expression(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["calculate ", "what is ", "what's "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return text

def extract_entity(user_input, intent):
    if intent == "open_app":
        return extract_after_keyword(user_input, ["open", "launch", "start"])
    
    if intent == "play_game":
        return extract_after_keyword(user_input, ["play", "launch", "start"])
    
    if intent == "set_reminder":
        return extract_after_keyword(user_input, ["remind me to", "remind me", "remember to"])
    
    return ""

def debug_entity_extraction(query):
    raw_intent, raw_confidence, scores = predict_intent_with_model(query)
    
    raw_analysis = make_analysis(
        raw_intent,
        raw_confidence,
        source="model",
        scores=scores
    )
    
    final_analysis = apply_entity_hints(query, raw_analysis)
    
    final_intent = final_analysis["intent"]
    final_confidence = final_analysis["confidence"]
    entity = extract_entity(query, final_intent)
    
    hint_reason = final_analysis.get("hint_reason", "No entity hint used")
        
    return (
        f"Input: {query}\n"
        f"Tokens: {tokenize(query)}\n"
        f"Raw intent: {raw_intent}\n"
        f"Raw confidence: {raw_confidence:.2f}\n"
        f"Final intent: {final_intent}\n"
        f"Final confidence: {final_confidence:.2f}\n"
        f"Source: {final_analysis['source']}\n"
        f"Expected entity: {entity}\n"
        f"Hint reason: {hint_reason}\n"
    )

def search_memory(query):
    memory = memory.get_all_memory()
    query = query.lower()
    
    results = []
    
    for note in memory["notes"]:
        if query in note.lower():
            results.append(f"Note: {note}")
            
    for reminder in memory["reminders"]:
        if query in reminder.lower():
            results.append(f"Reminder: {reminder}")
            
    for event in memory["history"]:
        text = f"{event['user_input']} {event['intent']} {event['result']}".lower()
        
        if query in text:
            results.append(f"History: {event['timestamp']} | {event['intent']} | {event['user_input']}")
            
    for turn in memory["conversation"]:
        text = f"{turn['user']} {turn['assistant']} {turn['intent']}".lower()
        
        if query in text:
            results.append(f"Conversation: {turn['timestamp']} | You: {turn['user']}")
            
    for summary in memory["summaries"]:
        if query in summary["summary"].lower():
            results.append(f"Summary: {summary['timestamp']} | {summary['summary']}")
            
    return results

def build_archive_summay_preview():
    archive = memory.get_archive()
    conversation = archive["conversation"]
    
    if not conversation:
        return "Archive is empty."
    
    intent_counts = {}
    word_counts = {}
    
    for turn in conversation:
        intent = turn["intent"]
        
        if intent not in intent_counts:
            intent_counts[intent] = 0
            
        intent_counts[intent] += 1
        
        text = f"{turn['user']} {turn['assistant']}"
        words = tokenize(text)
        
        for word in words:
            if word not in word_counts:
                word_counts[word] = 0
                
            word_counts[word] += 1
            
    sorted_intents = sorted(
        intent_counts.items(),
        key=lambda item: item[1],
        reverse=True
    )
    
    sorted_words = sorted(
        word_counts.items(),
        key=lambda item: item[1],
        reverse=True
    )
    
    intent_lines = []
    
    for intent, count in sorted_intents[:5]:
        intent_lines.append(f"{intent}: {count}")
        
    topic_words = []
    
    for word, count in sorted_words[:8]:
        topic_words.append(word)
        
    return (
        f"Archive summary preview:\n"
        f"{len(conversation)} archived conversation turns.\n"
        f"Most common intents:\n" + "\n".join(intent_lines) + "\n"
        f"Main topics: {', '.join(topic_words)}"
    )

def set_pending_confirmation(user_input, analysis):  
    pending = {
        "user_input": user_input,
        "analysis": analysis
    }
    
    memory.set_state_value("pending_confirmation", pending)

def get_pending_confirmation():
    return memory.get_state_value("pending_confirmation")

def clear_pending_confirmation():
    memory.clear_state_value("pending_confirmation")

def handle_basic_intent(user_input, analysis):
    intent = analysis["intent"]
    
    if intent == "greeting":
        context = get_profile_context()
        
        if context:
            return f"{greet()} I remember that {context}."
        
        return greet()

    if intent == "get_time":
        return get_time()

    return unknown_response()

def stop_focus_if_task_completed(completed_task):
    focus_task = get_focus_task()
    
    if not get_focus_mode():
        return False
    
    if focus_task != completed_task:
        return False
    
    started_at = stop_focus_mode()
    return started_at

def handle_control_intent(user_input, analysis):
    intent = analysis["intent"]
    teaching_text = user_input.replace("teach ", "", 1)

    if intent == "teach_intent":
        if " as " not in teaching_text:
            return "Use this format: teach message as intent_name"

        example_input, correct_intent = teaching_text.split(" as ", 1)
        saved = save_feedback(example_input, correct_intent)
        if saved:
            return f"Got it. I learned that '{example_input}' means '{correct_intent}'"
        
        return f"I already knew that '{example_input}' means '{correct_intent}'"
    
    if intent == "confirm_intent":
        pending = get_pending_confirmation()
        
        if not pending:
            return "There is nothing waiting for confirmation."
        
        confirmed_analysis = pending["analysis"].copy()
        confirmed_analysis["confidence"] = 1.0
        confirmed_analysis["source"] = "confirmed"
        
        original_input = pending["user_input"]
        confirmed_intent = confirmed_analysis["intent"]
        
        save_feedback(original_input, confirmed_intent)
        
        clear_pending_confirmation()
    
        return handle_action_intent(original_input, confirmed_analysis)
            
    if intent == "deny_intent":
        pending = get_pending_confirmation()
        
        if not pending:
            return "There is nothing waiting for rejection."
        
        original_input = pending["user_input"]
        clear_pending_confirmation()
        
        return f"Okay. Teach me the correct intent with: teach {original_input} as intent_name"


    if intent == "debug_memory_search":
        query = user_input.replace("debug memory ", "", 1).strip()
        
        if not query:
            return "What memory search should I debug?"
        
        results = debug_memory_search(query)
        
        if not results:
            return "I do not have any memory items to debug."
        
        lines = [
            f"Query tokens: {tokenize(query)}"
        ]
        
        for result in results:
            item = result["item"]
            lines.append("")
            lines.append(f"Score: {result['score']:.2f}")
            lines.append(f"Type: {item['type']}")
            lines.append(f"Text: {item['text']}")
            lines.append(f"Tokens: {result['tokens']}")
            lines.append(f"Recency: {result['recency']:.2f}")
            
        return "\n".join(lines)

    if intent == "debug_model":
        query = user_input.replace("debug model ", "", 1).strip()
        predicted_intent, confidence, scores = predict_intent_with_model(query)
        prediction_group = get_intent_group(predicted_intent)
        
        score_lines = []
        
        weights = get_debug_weights(query)
        
        weight_lines = []
        
        for word, weight in weights.items():
            weight_lines.append(f"{word}: {weight:.2f}")
        
        for intent_name, score in scores.items():
            score_lines.append(f"{intent_name}: {score:.2f}")
            
        return (
            f"Tokens: {tokenize(query)}\n"
            f"Prediction: {predicted_intent}\n"
            f"Confidence: {confidence:.2f}\n"
            f"Group: {prediction_group}\n"
            f"Scores:\n" + "\n".join(score_lines) +
            f"\nWeights:\n" + "\n".join(weight_lines)
        )
        
    if intent == "debug_match":
        query = user_input[6:].strip()
        best_example, best_score = find_best_match(query)
        
        if not best_example:
            return "I do not have any feedback examples yet."
        
        return (
            f"Input tokens: {tokenize(query)}\n"
            f"Match tokens: {tokenize(best_example['input'])}\n"
            f"Best match: '{best_example['input']}'\n"
            f"Intent: {best_example['correct_intent']}\n"
            f"Score: {best_score:.2f}"
        )
        
    if intent == "evaluate_model":
        result = evaluate_model()
        
        if result["total"] == 0:
            return "No test examples found yet."
        
        lines = [
            f"Accuracy: {result['correct']}/{result['total']} = {result['accuracy']:.2f}"
        ]
        
        confusion_summary = summarize_confusion(result["confusion"])
        
        if confusion_summary:
            lines.append("")
            lines.append("Confusion: ")
            
            for confusion_name, count in confusion_summary.items():
                lines.append(f"{confusion_name}: {count}")
        
        if result["mistakes"]:
            lines.append("")
            lines.append("Mistakes:")
            
            for mistake in result["mistakes"]:
                lines.append(f"Input: {mistake['input']}")
                lines.append(f"Expected: {mistake['expected']}")
                lines.append(f"Predicted: {mistake['predicted']}")
                lines.append(f"Confidence: {mistake['confidence']:.2f}")
                lines.append("")
                
        return "\n".join(lines)
    
    if intent == "complete_pending_task":
        pending_task = get_pending_task()
        
        if not pending_task:
            return "I do not have a suggested task waiting."
        
        result = memory.complete_reminder(pending_task)
        clear_pending_task()
        
        if result["removed"]:
            focus_stopped = stop_focus_if_task_completed(result["reminder"])
            
            if focus_stopped:
                session_result = save_focus_session(result["reminder"], focus_stopped)
                summary = format_focus_session_summary(
                    result["reminder"],
                    session_result["duration"],
                    session_result["notes"]
                )
                
                return (
                    f"Completed suggested task: {result['reminder']}\n"
                    f"{summary}"
                )
        
        return f"I could not complete the suggested task: {pending_task}"
    
    if intent == "skip_pending_task":
        pending_task = get_pending_task()
        
        if not pending_task:
            return "I do not have a suggested task waiting."
        
        clear_pending_task()
        
        return f"Okay, I skipped this suggested task for now: {pending_task}"
    
    if intent == "debug_entity":
        query = user_input.replace("debug entity ", "", 1).strip()
        
        if not query:
            return "What entity extraction should I debug?"
        
        return debug_entity_extraction(query)
    
    if intent == "debug_focus_goal":
        goal_text = memory.get_profile_value("focus_goal")
        goal_seconds = parse_duration_to_seconds(goal_text)
        
        today_stats = build_today_focus_stats()
        all_stats = build_focus_stats()
        
        return (
            f"Focus goal text: {goal_text}\n"
            f"Goal seconds: {goal_seconds}\n"
            f"Today seconds: {today_stats['total_seconds']}\n"
            f"Today sessions: {today_stats['total_sessions']}\n"
            f"All sessions: {all_stats['total_sessions']}\n"
            f"Focus mode active: {get_focus_mode()}\n"
            f"Current focus task: {get_focus_task()}"
        )
    
    return unknown_response()       

def handle_memory_intent(user_input, analysis):
    intent = analysis["intent"]
    
    if intent == "remember_game_entity":
        game = user_input.replace("remember game ", "", 1).strip().lower()
        
        if not game:
            return "Which game should I remember?"
        
        saved_games = memory.add_entity("games", game)
        return f"Got it. I will remember {saved_games} as a game."
    
    if intent == "preview_entity_conflicts":
        conflicts = memory.preview_entity_conflicts()
        
        lines = ["Possible entity conflicts:"]
        
        found_any = False
        
        for entity_type, entity_conflicts in conflicts.items():
            lines.append(f"{entity_type}:")
            
            if not entity_conflicts:
                lines.append("None")
                continue
            
            found_any = True
            
            for conflict in entity_conflicts:
                lines.append(f"{conflict['short']} -> {conflict['long']}")
                
        if not found_any:
            return "No possible entity conflicts found."
        
        return "\n".join(lines)
    
    if intent == "resolve_entity_conflict":
        entity_type, old_value, new_value = parse_entity_resolution(user_input)
        
        if not entity_type:
            return "Use this format: resolve entity game old_name as new_name"
        
        result = memory.resolve_entity_conflict(entity_type, old_value, new_value)
        
        return f"Resolved {result['old']} as {result['new']} in {entity_type}."
    
    if intent == "remember_app_entity":
        app = user_input.replace("remember app ", "", 1).strip().lower()
        
        if not app:
            return "Which app should I remember?"
        
        saved_apps = memory.add_entity("apps", app)
        return f"Got it. I will remember {saved_apps} as an app."
    
    if intent == "reminder_stats":
        stats = memory.get_reminder_stats()
        
        if stats["total"] == 0:
            return "You have no reminders."
        
        return (
            f"Total reminders: {stats['total']}\n"
            f"First reminder: {stats['first']}\n"
            f"Last reminder: {stats['last']}"
        )
        
    if intent == "edit_reminder":
        identifier, new_text = parse_edit_reminder(user_input)
        
        if not identifier or not new_text:
            return "Use this format: edit reminder old_or_number as new_reminder"
        
        result = memory.edit_reminder(identifier, new_text)
        
        if result["edited"]:
            return f"Updated reminder: {result['old']} -> {result['new']}"
        
        if result["reason"] == "empty":
            return "You have no reminders to edit."
        
        if result["reason"] == "invalid_index":
            return "That reminder number does not exist."
        
        return f"I could not find this reminder: {result['old']}"
    
    if intent == "remember_note":
        note = user_input.replace("remember ", "", 1)
        memory.add_note(note)
        return "i remembered that."
    
    if intent == "show_entities":
        games = memory.get_entities("games")
        apps = memory.get_entities("apps")
        
        lines = []
        
        lines.append("Games:")
        lines.extend(games if games else ["None"])
        
        lines.append("Apps:")
        lines.extend(apps if apps else ["None"])
        
        return "\n".join(lines)
    
    if intent == "cleanup_entities":
        report = memory.cleanup_entities()
        
        lines = ["Entity cleanup finished"]
        
        for entity_type, removed_count in report.items():
            lines.append(f"{entity_type}: removed {removed_count} duplicate entries")
    
        return "\n".join(lines)
    
    if intent == "cleanup_reminders":
        removed_count = memory.cleanup_reminders()
        
        return f"Reminder cleanup finished. Removed {removed_count} duplicate reminders."
        
    if intent == "show_notes":
        notes = memory.get_notes()
        if not notes:
            return "You have no notes yet."
        return "\n".join(notes)
    
    if intent == "show_pending_task":
        pending_task = get_pending_task()
        
        if not pending_task:
            return "You do not have a pending task."
        
        return f"Pending task: {pending_task}"
    
    if intent == "show_history":
        history = memory.get_history()
        
        if not history:
            return "I do not have any action history yet."
        
        lines = []
        
        for event in history:
            lines.append(
                f"{event['timestamp']} | {event['intent']} | {event['user_input']}"
            )
            
        return "\n".join(lines)
    
    if intent == "show_conversation":
        conversation = memory.get_conversation()
        
        if not conversation:
            return "I do not have any conversation history yet."
        
        lines = []
        
        for turn in conversation:
            lines.append(f"{turn['timestamp']}")
            lines.append(f"You: {turn['user']}")
            lines.append(f"Assistant: {turn['assistant']}")
            lines.append("")
            
        return "\n".join(lines)
    
    if intent == "show_focus_sessions":
        sessions = memory.get_focus_sessions()
        
        if not sessions:
            return "I do not have any focus sessions yet."
        
        lines = ["Recent focus sessions:"]
        
        for index, session in enumerate(sessions, start=1):
            lines.append(
                f"{index}. {session['task']} | {session['duration']} | {session['started_at']} -> {session['ended_at']}"
            )
            
        notes = session.get("notes", [])
        
        for note in notes:
            lines.append(f" note: {note}")
            
        return "\n".join(lines)
    
    if intent == "summarize_conversation":
        conversation = memory.get_conversation(limit=10)
        summary_text = build_simple_summary(conversation)
        
        summary = {
            "summary": summary_text,
            "timestamp": current_timestamp()
        }
        
        memory.add_summary(summary)
        
        return summary_text
    
    if intent == "daily_briefing":
        name = memory.get_profile_value("name")
        goal = memory.get_profile_value("goal")
        
        today_results = memory.search_reminders_by_due("today")
        overdue_results = memory.search_reminders_by_due("yesterday")
        
        focus = get_first_reminder_text(today_results)
        
        lines = []
        
        if name:
            lines.append(f"Good day, {name}.")
        else:
            lines.append("Good day.")
            
        if goal:
            lines.append(f"Goal: {goal}")
            
        lines.append(f"Reminders today: {len(today_results)}")
        lines.append(f"Overdue reminders: {len(overdue_results)}")
        
        focus_progress = get_focus_goal_progress_summary()
        
        if focus_progress:
            lines.append(f"Focus goal: {focus_progress['goal']}")
            
            if focus_progress["progress"] is not None:
                lines.append(f"Focus progress: {focus_progress['progress']}%")
                lines.append(f"Today's focus: {focus_progress['today_focus']}")
            else:
                lines.append("Focus progress: unknown")
        
        if focus:
            lines.append(f"Suggested focus: {focus}")
        elif goal:
            lines.append(f"Suggested focus: work toward your goal - {goal}")
            
        return "\n".join(lines)
    
    if intent == "semantic_memory_search":
        query = user_input.replace("semantic memory ", "", 1).strip()
        
        if not query:
            return "What should I search memory for?"
        
        results = semantic_search_memory(query)
        
        if not results:
            return f"I could not find anything similar to '{query}'."
        
        lines = []
        
        for result in results:
            score = result["score"]
            display = result["item"]["display"]
            lines.append(
                f"{result['score']:.2f} | sim={result['similarity']:.2f} | "
                f"imp={result['importance']:.2f} | rec={result['recency']:.2f} | {display}"
            )
            
        return "\n".join(lines)
    
    if intent == "show_summaries":
        summaries = memory.get_summaries()
        
        if not summaries:
            return "I do not have any summaries yet."
        
        lines = []
        
        for summary in summaries:
            lines.append(f"{summary['timestamp']} | {summary['summary']}")
        
        return "\n".join(lines)
    
    if intent == "show_reminders":
        reminders = memory.get_reminders()
        
        if not reminders:
            return "You have no reminders."
        
        lines = ["Your reminders:"]
        
        for index, reminder in enumerate(reminders, start=1):
            text = memory.get_reminder_text(reminder)
            due = memory.get_reminder_due(reminder)
            
            if due:
                lines.append(f"{index}. {text} | due: {due}")
            else:
                lines.append(f"{index}. {text}")
            
        return "\n".join(lines)
    
    if intent == "overdue_reminders":
        results = memory.search_reminders_by_due("yesterday")
        return format_reminder_results("Overdue reminders:", results)
    
    if intent == "reminder_dashboard":
        stats = memory.get_reminder_stats()
        
        today_count = count_reminders_by_due_label("today")
        tomorrow_count = count_reminders_by_due_label("tomorrow")
        overdue_count = count_reminders_by_due_label("yesterday")
        
        return (
            f"Reminder dashboard:\n"
            f"Total: {stats['total']}\n"
            f"Today: {today_count}\n"
            f"Tomorrow: {tomorrow_count}\n"
            f"Overdue: {overdue_count}"
        )
    
    if intent == "search_memory":
        query = user_input.replace("search memory ", "", 1).strip()
        
        if not query:
            return "What should I search memory for?"
        
        results = search_memory(query)
        
        if not results:
            return f"I could not find anything about '{query}'."
        
        return "\n".join(results[:10])
    
    if intent == "migrate_reminders":
        migrated_count = memory.migrate_reminders_to_dicts()
        
        return f"Reminder migration finished. Migrated {migrated_count} old reminders."
    
    if intent == "preview_memory_cleanup":
        preview = preview_memory_cleanup()
        
        return (
            f"Low-importance conversation turns: {len(preview['low_importance_turns'])}\n"
            f"Control/debug/search turns: {len(preview['control_turns'])}"
        )
        
    if intent == "archive_memory_cleanup":
        preview = preview_memory_cleanup()
        
        turns_to_archive = []
        
        for turn in preview["low_importance_turns"]:
            if turn not in turns_to_archive:
                turns_to_archive.append(turn)
                
        for turn in preview["control_turns"]:
            if turn not in turns_to_archive:
                turns_to_archive.append(turn)
                
        archived_count = memory.archive_conversation_turns(turns_to_archive)
        
        return f"Archived {archived_count} conversation turns."
    
    if intent == "memory_stats":
        stats = get_memory_stats()
        
        return (
            f"Notes: {stats['notes']}\n"
            f"Reminders: {stats['reminders']}\n"
            f"History events: {stats['history']}\n"
            f"Conversation turns: {stats['conversation']}\n"
            f"Summaries: {stats['summaries']}\n"
            f"Archived conversation turns: {stats['archived_conversation']}"
        )
        
    if intent == "save_archive_summary":
        summary_text = build_archive_summay_preview()
        
        summary = {
            "summary": summary_text,
            "timestamp": current_timestamp()
        }
        
        memory.add_archive_summary(summary)
        
        return "Saved archive summary."
    
    if intent == "show_archive_summaries":
        summaries = memory.get_archive_summaries()
        
        if not summaries:
            return "I do not have any archive summaries yet."
        
        lines = []
        
        for summary in summaries:
            lines.append(f"{summary['timestamp']} | {summary['summary']}")
            
        return "\n".join(lines)
        
    if intent == "preview_archive_summary":
        return build_archive_summay_preview()
        
    if intent == "search_archive":
        query = user_input.replace("search archive ", "", 1).strip()
        
        if not query:
            return "What should I search the archive for?"
        
        results = search_archive(query)
        
        if not results:
            return f"I could not find '{query}' in the archive."
        
        return "\n".join(results[:10])
    
    if intent == "archive_stats":
        stats = get_archive_stats()
        
        return (
            f"Archived conversation turns: {stats['archived_conversation']}\n"
            f"Search/debug/archive-related turns: {stats['ignored_intents']}\n"
            f"Oldest archived turn: {stats['oldest']}\n"
            f"Newest archived turn: {stats['newest']}"
        )
        
    if intent == "prune_archive":
        summaries = memory.get_archive_summaries()
        
        if not summaries:
            return "I will not prune the archive until an archive summary has been saved."
        
        removed_count = memory.clear_archived_conversation()
        
        return f"Pruned {removed_count} archived conversation turns. Archive summaries were kept."
    
    if intent == "recall_memory":
        query = user_input.replace("what do you remember about ", "", 1).strip()

        if not query:
            return "What topic should I recall?"
        
        results = semantic_search_memory(query, limit=3, min_score=0.2)
        
        if not results:
            return f"I do not remember anything clear about {query}."
        
        lines = [f"I remember these things about {query}:"]
        
        for result in results:
            item = result["item"]
            lines.append(f"- {format_recall_item(item)}")
            
        return "\n".join(lines)
    
    if intent == "recall_memory_source":
        source_type, query = parse_recall_source(user_input)
        
        if not query:
            return "What topic should I recall?"
        
        results = semantic_search_memory(query, limit=5, min_score=0.2, source_type=source_type)
        
        if not results:
            return f"I do not remember anything clear about {query} in {source_type} memory."
        
        lines = [f"I found these {source_type} memories about {query}:"]
        
        for result in results:
            item = result["item"]
            lines.append(f"- {format_recall_item(item)}")
            
        return "\n".join(lines)
        
    if intent == "set_name":
        name = user_input.replace("my name is ", "", 1)
        memory.set_profile_value("name", name)
        return f"Got it. i will remember your name is {name}."
    
    if intent == "set_profile_fact":
        key, value = parse_profile_fact(user_input)
        
        if not key or not value:
            return "Use this format: remember profile key value"
        
        memory.set_profile_value(key, value)
        
        return f"Got it. I saved {key} as {value}."
    
    if intent == "set_reminder_due":
        identifier, due = parse_set_reminder_due(user_input)
        
        if not identifier or not due:
            return "Use this format: set reminder reminder_or_number due time"
        
        result = memory.set_reminder_due(identifier, due)
        
        if result["updated"]:
            return f"Updated reminder due date: {result['reminder']} | due: {result['due']}"
        
        if result["reason"] == "empty":
            return "You have no reminders"
        
        if result["reason"] == "invalid_index":
            return "That reminder number does not exist."
        
        return f"I could not find this reminder: {result['reminder']}"
    
    if intent == "today_reminders":
        results = memory.search_reminders_by_due("today")
        return format_reminder_results("Today's reminders:", results)
    
    if intent == "tomorrow_reminders":
        results = memory.search_reminders_by_due("tomorrow")
        return format_reminder_results("Tomorrow's reminders:", results)
    
    if intent == "clear_reminder_due":
        identifier = parse_clear_reminder_due(user_input)
        
        if not identifier:
            return "Use this format: clear reminder reminder_or_number due"
        
        result = memory.clear_reminder_due(identifier)
        
        if result["updated"]:
            return f"Cleared due date for reminder: {result['reminder']}"
        
        if result["reason"] == "empty":
            return "You have no reminders."
        
        if result["reason"] == "invalid_index":
            return "That reminder number does not exist."
        
        return f"I could not find this reminder: {result['reminder']}"
    
    if intent == "get_profile_fact":
        key = parse_profile_question(user_input)
        
        if not key:
            return "What profile fact should I look up?"
        
        value = memory.get_profile_value(key)
        
        if not value:
            readable_key = key.replace("_", " ")
            return f"I do not know your {readable_key} yet."
        
        readable_key = key.replace("_", " ")
        return f"Your {readable_key} is {value}."
    
    if intent == "show_profile":
        profile = memory.get_profile()
        
        if not profile:
            return "I do not know much about you yet."
        
        lines = []
        
        for key, value in profile.items():
            lines.append(f"{key}: {value}")
            
        return "\n".join(lines)
    
    if intent == "get_name":
        name = memory.get_profile_value("name")
        if name:
            return f"Your name is {name}"
        return "I do not know your name yet."
    
    if intent == "coding_help":
        favorite_language = memory.get_profile_value("favorite_language")
        goal = memory.get_profile_value("goal")
        
        if favorite_language and goal:
            return (
                f"Since you like {favorite_language}, we can use it while working toward your goal: {goal}.\n"
                f"A good next step is to build one small feature, test it, then improve it." 
            )
            
        if favorite_language:
            return (
                f"Since you like {favorite_language}, we can start with a simple {favorite_language} example.\n"
                f"The best way is to build one small feature at a time."
            )
            
        return (
            "We can start with one small coding task.\n"
            "First, choose the feature. Then write the simplest version. Then test it."
        )
        
    if intent == "search_reminders_by_due":
        due_query = parse_due_search(user_input)
        
        if not due_query:
            return "Which due date should I search for?"
        
        results = memory.search_reminders_by_due(due_query)
        
        if not results:
            return f"I could not find reminders due {due_query}."
        
        lines = [f"Reminders due {due_query}:"]
        
        for result in results:
            lines.append(f"{result['index']}. {result['reminder']} | due: {result['due']}")
            
        return "\n".join(lines)
        
    if intent == "search_reminders":
        query = parse_reminder_search(user_input)
        
        if not query:
            return "What reminder should I search for?"
        
        results = memory.search_reminders(query)
        
        if not results:
            return f"I could not find reminders matching: {query}"
        
        lines = ["Matching reminders:"]
        
        for result in results:
            if result["due"]:
                lines.append(f"{result['index']}. {result['reminder']} | due: {result['due']}")
            else:
                lines.append(f"{result['index']}. {result['reminder']}")
            
        return "\n".join(lines)
        
    if intent == "complete_reminder":
        identifier = parse_complete_reminder(user_input)
        
        if not identifier:
            return "Which reminder should I complete?"
        
        result = memory.complete_reminder(identifier)
        
        if result["removed"]:
            return f"Completed reminder: {result['reminder']}"
        
        if result["reason"] == "empty":
            return "You have no reminders to complete."
        
        if result["reason"] == "invalid_index":
            return "That reminder number does not exist."
        
        return f"I could not find this reminder: {result['reminder']}"
    
    if intent == "suggest_next_task":
        overdue_results  = memory.search_reminders_by_due("yesterday")
        
        if overdue_results:
            first = overdue_results[0]
            set_pending_task(first["reminder"])
            return f"Start with overdue reminder: {first['reminder']} | due: {first['due']}"
        
        today_results = memory.search_reminders_by_due("today")
        
        if today_results:
            first = today_results[0]
            set_pending_task(first["reminder"])
            return f"Start with today's reminder: {first['reminder']} | due: {first['due']}"
        
        general_reminder = get_first_general_reminder()
        
        if general_reminder:
            set_pending_task(general_reminder["reminder"])
            if general_reminder["due"]:
                return f"Start with this reminder: {general_reminder['reminder']} | due: {general_reminder['due']}"
            
            return f"Start with this reminder: {general_reminder['reminder']}"
        
        goal = memory.get_profile_value("goal")
        
        if goal:
            return f"You have no reminders right now. A good next step is to work on your goal: {goal}"
        
        return f"You have no reminders right now. A good next step is to choose one small task and start there."
    
    if intent == "start_focus":
        task = choose_focus_task()
        
        if not task:
            return "You do not have a task to focus on yet."
        
        start_focus_mode(task)
        set_pending_task(task)
        
        return f"Focus mode started. Current focus: {task}"
    
    if intent == "stop_focus":
        if not get_focus_mode():
            return "Focus mode is not active."
        
        task = get_focus_task()
        started_at = stop_focus_mode()
        session_result = save_focus_session(task, started_at)
        
        return format_focus_session_summary(
            task,
            session_result["duration"],
            session_result["notes"]
        )
    
    if intent == "focus_status":
        if not get_focus_mode():
            return "Focus mode is not active."
        
        task = get_focus_task()
        return f"Focus mode is active. Current focus: {task}"
    
    if intent == "focus_stats_for_task":
        query = parse_focus_task_query(user_input)
        
        if not query:
            return "Which task should I summarize focus stats for?"
        
        stats = build_focus_stats_for_task(query)
        
        if stats["total_sessions"] == 0:
            return f"I do not have focus sessions for {query}."
        
        total_duration = format_duration_from_seconds(stats["total_seconds"])
        
        return (
           f"Focus stats for {query}:\n"
            f"Sessions: {stats['total_sessions']}\n"
            f"Total time: {total_duration}\n"
            f"Last matching focus: {stats['last_focus']}" 
        )   
        
    if intent == "today_focus_stats":
        stats = build_today_focus_stats()
        
        if stats["total_sessions"] == 0:
            return "I do not have any focus sessions for today."
        
        total_duration = format_duration_from_seconds(stats["total_seconds"])
        
        return (
            f"Today's focus sessions: {stats['total_sessions']}\n"
            f"Today's focus time: {total_duration}\n"
            f"Last focus today: {stats['last_focus']}"
        )
    
    if intent == "focus_stats":
        stats = build_focus_stats()
        
        if stats["total_sessions"] == 0:
            return "I do not have any focus sessions yet."
        
        total_duration = format_duration_from_seconds(stats["total_seconds"])
        
        return (
            f"Focus sessions: {stats['total_sessions']}\n"
            f"Total focus time: {total_duration}\n"
            f"Last focus: {stats['last_focus']}"
        )
        
    if intent == "focus_goal_progress":
        goal_text = memory.get_profile_value("focus_goal")
        
        if not goal_text:
            return "You do not have a focus goal yet."
        
        goal_seconds = parse_duration_to_seconds(goal_text)
        
        if not goal_seconds:
            return f"I could not understand your focus goal: {goal_text}"
        
        stats = build_today_focus_stats()
        today_seconds = stats["total_seconds"]
        
        progress = int((today_seconds / goal_seconds) * 100)
        
        if progress > 100:
            progress = 100
            
        return (
            f"Focus goal: {goal_text}\n"
            f"Today's focus: {format_duration_from_seconds(today_seconds)}\n"
            f"Progress: {progress}%"
        )
        
    if intent == "focus_streak":
        streak = build_true_focus_streak()
        
        if streak["focused_days"] == 0:
            return "You do not have any focused days yet."
        
        return (
            f"Focused days: {streak['focused_days']}\n"
            f"Current streak: {streak['current_streak']} day(s)\n"
            f"Longest streak: {streak['longest_streak']} day(s)"
        )
        
    if intent == "set_focus_goal":
        goal = parse_focus_goal(user_input)
        
        if not goal:
            return "Use this format: set focus goal 30 minutes"
        
        memory.set_profile_value("focus_goal", goal)
        
        return f"Focus goal saved: {goal}"
    
    if intent  == "show_focus_goal":
        goal = memory.get_profile_value("focus_goal")
        
        if not goal:
            return "You do not have a focus goal yet."
        
        return f"Your focus goal is {goal}."
    
    if intent == "add_focus_note":
        if not get_focus_mode():
            return "Focus mode is not active."
        
        note = parse_focus_note(user_input)
        
        if not note:
            return "What note should I add to this focus session?"
        
        add_current_focus_note(note)
        
        return f"Focus note added: {note}"
    
    if intent == "show_current_focus_notes":
        if not get_focus_mode():
            return "Focus mode is not active."
        
        notes = get_current_focus_notes()
        
        if not notes:
            return "This focus session has no notes yet."
        
        lines = ["Current focus notes:"]
        
        for note in notes:
            lines.append(f"- {note}")
            
        return "\n".join(lines)
    
    if intent == "search_focus_notes":
        query = parse_focus_note_search(user_input)
        
        if not query:
            return "What focus notes should I search for?"
        
        results = memory.search_focus_notes(query)
        
        if not results:
            return f"I could not find focus notes matching: {query}"
        
        lines = [f"Focus notes matching {query}:"]
        
        for result in results[-5:]:
            session = result["session"]
            lines.append(f"- {session['task']} | {session['started_at']}")
            
            for note in result["notes"]:
                lines.append(f"  note: {note}")
                
        return "\n".join(lines)
    
    if intent == "search_focus_sessions":
        query = parse_focus_search(user_input)
        
        if not query:
            return "What focus sessions should I search for?"
        
        results = memory.search_focus_sessions(query)
        
        if not results:
            return f"I could not find focus sessions matching: {query}"
        
        lines = [f"Focus sessions matching {query}:"]
        
        for session in results[-5:]:
            lines.append(
                f"- {session['task']} | {session['duration']} | {session['started_at']}"
            )
            
            notes = session.get("notes", [])
            
            for note in notes:
                lines.append(f"  note: {note}")
                
        return "\n".join(lines)
    
    if intent == "weekly_focus_stats":
        stats = build_recent_focus_stats(7) # can be changed to a month too
        
        if stats["total_sessions"] == 0:
            return "I do not have any focus sessions from the last 7 days."
        
        total_duration = format_duration_from_seconds(stats["total_seconds"])
        
        return (
            f"Weekly focus sessions: {stats['total_sessions']}\n"
            f"Weekly focus time: {total_duration}\n"
            f"Last focus this week: {stats['last_focus']}" 
        )
    
    if intent == "delete_focus_session":
        recent_index = parse_delete_focus_session(user_input)
        
        if recent_index is None:
            return "Use this format: delete focus session number"
        
        result = memory.delete_focus_session(recent_index)
        
        if result["deleted"]:
            session = result["session"]
            return f"Deleted focus session: {session['task']} | {session['duration']}"
        
        if result["reason"] == "empty":
            return "I do not have any focus sessions to delete."
        
        return "That focus session number does not exist."
    
    if intent == "cleanup_focus_sessions":
        removed_count = memory.cleanup_focus_sessions()
        
        return f"Focus session cleanup finished. Removed {removed_count} broken sessions."
    
    return unknown_response()

def handle_action_intent(user_input, analysis):
    intent = analysis["intent"]
    confidence = analysis["confidence"]
    source = analysis["source"]
    
    if source == "model" and confidence < HIGH_CONFIDENCE:
        set_pending_confirmation(user_input, analysis)
        action_preview = preview_action(user_input, analysis)
        
        return (
            f"I think this means '{intent}', but I am only {confidence:.2f} confident.\n"
            f"If confirmed, I will: {action_preview}.\n"
            f"Reply yes to confirm, no to reject, or teach me with: teach {user_input} as intent_name"
        )
    
        
    if intent == "set_reminder":
        reminder_text, due = parse_reminder_details(user_input)

        if not reminder_text:
            return "What should I remind you about?"
        
        result = create_reminder(reminder_text, due)
        log_action(user_input, analysis, result)
        return result
    
    if intent == "open_app":
        app_name = extract_entity(user_input, intent)
        
        if not app_name:
            return "What should i open?"
        
        result = open_app(app_name)
        log_action(user_input, analysis, result)
        return result
    
    if intent == "play_game":
        game_name = extract_entity(user_input, intent)
        
        if not game_name:
            return "Which game should I play?"
        
        result = play_game(game_name)
        log_action(user_input, analysis, result)
        return result
    
    if intent == "calculate":
        expression = extract_calculation_expression(user_input)
        
        if not expression:
            return "What should I calculate?"
        
        result = safe_calculate(expression)
        log_action(user_input, analysis, result)
        return result
        
    return f"I recognize this as '{intent}', but I do not know how to perform that action yet."

def preview_action(user_input, analysis):
    intent = analysis["intent"]
    
    if intent == "set_reminder":
        reminder_text = extract_entity(user_input, intent)
        if reminder_text:
            return f"save a reminder: {reminder_text}"
        
        return "ask what reminder to save"
    
    if intent == "open_app":
        app_name = extract_entity(user_input, intent)
        
        if app_name:
            return f"open the app: {app_name}"
        
        return "ask which app to open"
    
    if intent == "play_game":
        game_name = extract_entity(user_input, intent)
        
        if game_name:
            return f"play the game: {game_name}"
        
        return "try to play a game"
    
    if intent == "play_music":
        return "play music"
    
    return f"handle intent: {intent}"

def get_response(user_input):
    analysis = analyze_intent(user_input)
    group = analysis["group"]
    
    if group == "basic":
        response = handle_basic_intent(user_input, analysis)
    
    elif group == "control":
        response = handle_control_intent(user_input, analysis)
    
    elif group == "memory":
        response = handle_memory_intent(user_input, analysis)
    
    elif group == "action":
        response = handle_action_intent(user_input, analysis) 
    
    else:
        response = unknown_response()
        
    log_conversation(user_input, response, analysis)
    
    return response
    