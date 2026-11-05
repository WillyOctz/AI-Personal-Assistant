import logging
import re
import threading
import time
from datetime import date, datetime

from assistant import events, file_index, focus, llm, memory, monitor, personality, toasts
from assistant.notifier import _quiet_now
from assistant.reply import button
from assistant.runtime import BRAIN_LOCK, ui_state

log = logging.getLogger("nebula.companion")

PRIVACY_TEXT = (
    "I'll keep watch quietly, dear. I note which app and which project you're in, and when. "
    "Window titles are never stored, nothing leaves this PC, and password managers are skipped. "
    "Pause any time from the tray, or say 'forget activity all'."
)

SETTINGS = {
    "monitor": ("monitor_enabled", "bool"),
    "nudges": ("nudges_enabled", "bool"),
    "suggest": ("suggest_focus", "bool"),
    "recapai": ("recap_llm", "bool"),
    "break": ("break_minutes", "int", 1, 240),
    "distraction": ("distraction_minutes", "int", 1, 120),
    "resume": ("resume_gap_minutes", "int", 1, 1440),
    "gap": ("nudge_min_gap_minutes", "int", 0, 240),
    "idle": ("idle_limit_seconds", "int", 30, 1800),
    "retention": ("activity_retention_days", "int", 1, 365),
    "recap": ("recap_time", "time"),
    "distractapps": ("distraction_apps", "list"),
    "exclude": ("monitor_exclude", "list"),
}

_n = {"last_any": 0.0, "day": None, "count": 0, "snooze_until": 0.0, "last_break": 0.0, "kind_last": {}}
_suggest_day = {"day": None, "count": 0}
_suggested = {}

def _say(cfg, key, **kw):
    return personality.line(key, verbosity=cfg["verbosity"], **kw)


# ------------------------Gatekeeping-----------------------------
def can_nudge(cfg, now, bypass_gap=False):
    today = date.fromtimestamp(now).isoformat()
    
    if _n["day"] != today:
        _n.update(day=today, count=0)
        _suggest_day.update(day=today, count=0)
        
    if not cfg["nudges"] or cfg["paused"]:
        return False

    if now < _n["snooze_until"] or _quiet_now():
        return False

    if _n["count"] >= cfg["max_per_day"]:
        return False

    if not bypass_gap and now - _n["last_any"] < cfg["min_gap"]:
        return False

    return True

def snooze_nudges(minutes=120):
    _n["snooze_until"] = time.time() + minutes * 60
    return f"Alright, I'll stay quiet for {minutes // 60 if minutes >= 60 else minutes} " \
           f"{'hour(s)' if minutes >= 60 else 'minute(s)'}."
           
def _deliver(kind, say, actions, counted=True):
    now = time.time()
    
    if counted:
        _n["last_any"] = now
        _n["count"] += 1
        
    _n["kind_last"][kind] = now
    
    chat_actions = list(actions) + [button("Not now", "companion snooze", style="ghost")]
    events.publish("notify", {"text": say, "actions": chat_actions})
    
    if not ui_state["visible"]: # hidden window
        commands = [(a["label"], a["command"]) for a in actions if a.get("type", "command") == "command"]
        toasts.nudge_toast("Nebula", say, commands)
        

# ----------------------------Rules----------------------------------
def on_return(cfg, gap_seconds):
    now = time.time()
    
    if now - _n["kind_last"].get("resume", 0) < 3600:
        return
    
    if not can_nudge(cfg, now, bypass_gap=True):
        return
    
    info = monitor.last_project_info()
    project = file_index.get_project(info["id"]) if info else None
    
    if not project:
        return
    
    recent = file_index.project_recent_files(project["path"], limit=1)
    file_part = f", working on {recent[0]['name']}" if recent else ""
    note = (project.get("note") or "").strip()
    note_part = f' You left yourself a note: "{note}"' if note else ""

    say = _say(cfg, "resume.nudge", project=project["name"], file_part=file_part, note_part=note_part)
    _deliver("resume", say, [button("Resume", f"resume project #{project['id']}", style="primary")])

    
def evaluate(cfg, snap):
    now = time.time()
    
    try:
        _maybe_recap(cfg, now)
    except Exception:
        log.exception("recap check failed")

    if not cfg["nudges"] or not snap.get("active"):
        return
    
    minimal = cfg["verbosity"] == "minimal"
    
    if cfg["focus_on"]:
        base = max(snap.get("run_start") or now, cfg["focus_started"] or 0, _n["last_break"])
        run = now - base
        
        if run >= cfg["break_min"] * 60 and can_nudge(cfg, now):
            _n["last_break"] = now
            _deliver("break", _say(cfg, "nudge.break", minutes=int(run // 60)),
                     [button("Stop focus", "stop focus", style="ghost")])
            return
        
        if not minimal and cfg["distraction_apps"] and snap.get("app") in cfg["distraction_apps"]:
            secs = monitor.app_seconds(cfg["distraction_apps"], 15 * 60)
            
            if (
                secs >= cfg["distraction_min"] * 60
                and now - _n["kind_last"].get("distraction", 0) >= 1800
                and can_nudge(cfg, now)
            ):
                say = _say(cfg, "nudge.distraction", apps=monitor.friendly(snap["app"]),
                           minutes=int(secs // 60), task=cfg["focus_task"] or "your task")
                _deliver("distraction", say, [])
                
                
        return
    
    if minimal or not cfg["suggest"]:
        return
    
    top = monitor.project_seconds(20 * 60, now)
    
    if not top:
        return
    
    best = top[0]
    
    if (
        best["seconds"] >= 12 * 60
        and now - _suggested.get(best["id"], 0) >= 7200
        and can_nudge(cfg, now)
        and _suggest_day["count"] < 3
    ):
        _suggested[best["id"]] = now
        _suggest_day["count"] += 1
        say = _say(cfg, "nudge.suggest", project=best["name"], minutes=int(best["seconds"] // 60))
        _deliver("suggest", say, [button("Start focus", f"start focus on {best['name']}", style="primary")])
        
        
# -------------------------------Recap--------------------------------
def build_recap(days=1):
    end = time.time()
    start = monitor.day_start() - (days - 1) * 86400
    s = monitor.summary(start, end, top=5)
    total = s["total"] or 0.0
    
    def rows(items):
        return [{"name": i["name"], "seconds": int(i["seconds"]), "text": monitor.fmt_duration(i["seconds"]),
                 "pct": round(100 * i["seconds"] / total) if total else 0} for i in items]
        
    sessions = []
    
    for session in memory.get_all_focus_sessions():
        began = focus.parse_timestamp(session.get("started_at"))
        
        if began and began.timestamp() >= start:
            sessions.append(session)
            
    focus_seconds = sum(memory.get_focus_session_seconds(x) for x in sessions)
    notes = [n for x in sessions for n in x.get("notes", [])][:3]
    
    return {
        "label": "Today" if days == 1 else f"Last {days} days",
        "when": "Today" if days == 1 else f"In the last {days} days",
        "total": total,
        "total_text": monitor.fmt_duration(total),
        "projects": rows(s["projects"]),
        "apps": rows(s["apps"]),
        "focus": {"sessions": len(sessions), "seconds": focus_seconds,
                  "text": monitor.fmt_duration(focus_seconds)},
        "notes": notes,
    }
    
def recap_text(data):
    lines = [f"{data['label']}: {data['total_text']} active"]
    
    for p in data["projects"]:
        lines.append(f"- {p['name']}: {p['text']}")
        
    for a in data["apps"]:
        lines.append(f"  {a['name']}: {a['text']}")

    if data["focus"]["sessions"]:
        lines.append(f"Focus: {data['focus']['sessions']} session(s), {data['focus']['text']}")
        
    return "\n".join(lines)

def _llm_line(data):
    
    projects = ", ".join("{} {}".format(p["name"], p["text"]) for p in data["projects"]) or "none"
    apps = ", ".join("{} {}".format(a["name"], a["text"]) for a in data["apps"]) or "none"
    
    facts = (
        f"Period: {data['label']}. Total active time: {data['total_text']}. "
        f"Projects: {projects}. Apps: {apps}. "
        f"Focus sessions: {data['focus']['sessions']} ({data['focus']['text']}). "
        f"Focus notes: {'; '.join(data['notes']) or 'none'}."
    )
    
    system = (
        personality.get_llm_system_instruction()
        + "\n\nWrite ONE or TWO short sentences recapping the user's day. Use only the facts given. "
          "Never invent numbers, names or health advice. No lists, no markdown."
    )
    
    for fn in (llm.get_gemini_response, llm.get_groq_response):
        result = fn(facts, system)
        
        if result["ok"]:
            return result["text"].strip()[:400]
        
    return ""

def recap_line(data, verbosity="normal", use_ai=True):
    if use_ai and verbosity != "minimal":
        line = _llm_line(data)
        
        if line:
            return line
        
    top = data["projects"][0]["name"] if data["projects"] else ""
    return personality.line("recap.intro", verbosity=verbosity, label=data["label"], when=data["when"],
                            total=data["total_text"], top_part=f" Most of it in {top}." if top else "")
    
def _send_recap(cfg):
    try:
        data = build_recap(1)
        
        if data["total"] < 300:
            return
        
        say = recap_line(data, cfg["verbosity"], cfg["recap_ai"])
        _deliver("recap", say, [button("Show recap", "daily recap", style="primary")], counted=False)
    except Exception:
        log.exception("scheduled recap failed")
        
def _maybe_recap(cfg, now):
    hhmm = cfg["recap_time"]
    
    if not hhmm:
        return
    
    stamp = datetime.fromtimestamp(now)
    
    if stamp.strftime("%H:%M") < hhmm:
        return
    
    today = stamp.date().isoformat()
    
    if memory.get_state_value("last_recap_date") == today or cfg["paused"] or _quiet_now():
        return
    
    with BRAIN_LOCK:
        memory.set_state_value("last_recap_date", today)
        
    threading.Thread(target=_send_recap, args=(cfg,), daemon=True, name="recap").start()
    
def no_data_message():
    if not memory.get_setting("monitor_enabled", False):
        return "I'm not watching yet, dear. Turn it on with: set companion monitor on"
    
    return "I haven't noticed enough activity yet. Give me a little while."


# ------------------------------Notes---------------------------------
def offer_handoff(task, started_at):
    begin = focus.parse_timestamp(started_at) if started_at else None
    start_ts = begin.timestamp() if begin else time.time() - 3600
    project = None
    
    try:
        top = monitor.top_project_between(start_ts, time.time())
        
        if top:
            project = {"id": top["id"], "name": top["name"]}
    except Exception:
        log.exception("could not read activity for handoff")
        
    if not project:
        low = (task or "").lower()
        
        for p in file_index.list_projects(500):
            if len(p["name"]) >= 4 and p["name"].lower() in low:
                project = {"id": p["id"], "name": p["name"]}
                break
            
    if project:
        memory.set_state_value("pending_handoff", {"project_id": project["id"], "name": project["name"],
                                                   "at": time.time()})
        
    return project

def set_handoff(text):
    pending = memory.get_state_value("pending_handoff")
    project = None
    
    if pending and time.time() - pending.get("at", 0) < 12 * 3600:
        project = file_index.get_project(pending["project_id"])
        
    if not project:
        info = monitor.last_project_info()
        project = file_index.get_project(info["id"]) if info else None
        
    if not project:
        return None
    
    cleared = text.strip().lower() == "clear"
    file_index.set_project_note(project["path"], "" if cleared else text.strip()[:500])
    memory.clear_state_value("pending_handoff")
    
    return {"project": project["name"], "cleared": cleared}


# -------------------------------Setting & Status----------------------------------
def settings_help():
    return (
        "Companion settings:\n"
        "- set companion monitor on/off\n"
        "- set companion nudges on/off\n"
        "- set companion suggest on/off\n"
        "- set companion break 50        (minutes of focus before a break nudge)\n"
        "- set companion resume 30       (minutes away before 'welcome back')\n"
        "- set companion gap 20          (minutes between any two nudges)\n"
        "- set companion recap 18:00     (or: off)\n"
        "- set companion distractapps chrome.exe, discord.exe\n"
        "- set companion distraction 10  (minutes in those apps)\n"
        "- set companion exclude keepass.exe\n"
        "- set companion idle 120 / retention 30 / recapai on"
    )
    
def apply_setting(key, value):
    key = (key or "").lower().strip()
    value = (value or "").strip()
    spec = SETTINGS.get(key)
    
    if not spec:
        return False, "I don't know that setting.\n" + settings_help()
    
    name, kind = spec[0], spec[1]
    
    if kind == "bool":
        low = value.lower()
        
        if low in ("on", "true", "yes", "enable", "enabled", "1"):
            parsed = True
        elif low in ("off", "false", "no", "disable", "disabled", "0"):
            parsed = False
        else:
            return False, f"Use on or off: set companion {key} on"

        shown = "on" if parsed else "off"
        
    elif kind == "int":
        lo, hi = spec[2], spec[3]

        try:
            parsed = int(value)
        except ValueError:
            return False, f"{key} needs a number between {lo} and {hi}."

        if not lo <= parsed <= hi:
            return False, f"{key} must be between {lo} and {hi}."

        shown = str(parsed)

    elif kind == "time":
        if value.lower() in ("", "off", "none", "clear"):
            parsed, shown = "", "off"
        else:
            match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)

            if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
                return False, "Use a 24-hour time like 18:00, or off."

            parsed = f"{int(match.group(1)):02d}:{match.group(2)}"
            shown = parsed

    else:  # list of process names
        items = []

        if value.lower() not in ("none", "clear", "off", ""):
            for part in re.split(r"[,\s]+", value.lower()):
                if not part:
                    continue

                part = part if "." in part else part + ".exe"

                if part not in items:
                    items.append(part)

        parsed, shown = items, (", ".join(items) or "none")

    with BRAIN_LOCK:
        memory.set_setting(name, parsed)

    monitor.refresh()
    message = f"Companion setting saved: {key} = {shown}"

    if name == "monitor_enabled" and parsed:
        message += "\n" + PRIVACY_TEXT

    return True, message

def status_text():
    get = memory.get_setting
    
    lines = [
        "Companion status:",
        f"Activity tracking: {'on' if get('monitor_enabled', False) else 'off'}",
        f"Nudges: {'on' if get('nudges_enabled', True) else 'off'}"
        f" (break after {get('break_minutes', 50)} min of focus, min gap {get('nudge_min_gap_minutes', 20)} min)",
        f"Welcome-back after: {get('resume_gap_minutes', 30)} min away",
        f"Daily recap: {get('recap_time', '') or 'off'}",
        f"Distraction apps: {', '.join(get('distraction_apps', [])) or 'none'}",
    ]
    
    try:
        stats = monitor.stats()
        lines.append(
            f"Stored: {stats['rows']} record(s), local only, kept "
            f"{get('activity_retention_days', 30)} days, no window titles."
        )
        
        if stats["apps_today"]:
            lines.append("Apps seen today: " + ", ".join(stats["apps_today"]))
    except Exception:
        log.exception("status stats failed")
        
    snap = monitor.snapshot()
    
    if snap.get("project"):
        lines.append(f"Right now: {snap['project']}")

    if time.time() < _n["snooze_until"]:
        lines.append("Nudges are snoozed for now.")

    return "\n".join(lines)
