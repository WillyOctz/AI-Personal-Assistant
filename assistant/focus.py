from assistant import memory
from datetime import datetime, timedelta

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
    
def get_pending_task():
    return memory.get_state_value("pending_task")

def get_first_general_reminder():
    reminders = memory.get_reminders()
    
    if not reminders:
        return None
    
    first = reminders[0]
    
    return {
        "reminder": memory.get_reminder_text(first),
        "due": memory.get_reminder_due(first)
    }
    
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
    clear_current_focus_notes()
    
    return {
        "duration": duration,
        "notes": session["notes"]
    }
    
def stop_focus_if_task_completed(completed_task):
    focus_task = get_focus_task()
    
    if not get_focus_mode():
        return False
    
    if focus_task != completed_task:
        return False
    
    started_at = stop_focus_mode()
    return started_at

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

def get_focus_session_dates():
    sessions = memory.get_all_focus_sessions()
    dates = set()
    
    for session in sessions:
        parsed_time = parse_timestamp(session["started_at"])
        
        if parsed_time:
            dates.add(parsed_time.date())
            
    return dates

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
    
def build_best_focus_day():
    sessions = memory.get_all_focus_sessions()
    
    if not sessions:
        return None
    
    daily_totals = {}
    
    for session in sessions:
        parsed_time = parse_timestamp(session["started_at"])
        
        if not parsed_time:
            continue
        
        date_key = parsed_time.strftime("%Y-%m-%d")
        seconds = calculate_duration_seconds(
            session["started_at"],
            session["ended_at"]
        )
        
        if date_key not in daily_totals:
            daily_totals[date_key] = {
                "seconds": 0,
                "sessions": 0
            }
            
        daily_totals[date_key]["seconds"] += seconds
        daily_totals[date_key]["sessions"] += 1
        
    if not daily_totals:
        return None
    
    best_date = None
    best_data = None
    
    for date_key, data in daily_totals.items():
        if best_data is None or data["seconds"] > best_data["seconds"]:
            best_date = date_key
            best_data = data
            
    return {
        "date": best_date,
        "seconds": best_data["seconds"],
        "sessions": best_data["sessions"]
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