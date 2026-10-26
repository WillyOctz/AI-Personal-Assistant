import logging
import threading
from datetime import datetime

from assistant import events, memory, toasts
from assistant.runtime import BRAIN_LOCK, hooks, ui_state

log = logging.getLogger("nebula.notifier")
CHECK_EVERY = 30
_stop = threading.Event()

def _quiet_now():
    if not memory.get_setting("quiet_hours", False):
        return False
    start = memory.get_setting("quiet_start", "22:00")
    end = memory.get_setting("quiet_end", "07:00")
    now = datetime.now().strftime("%H:%M")
    if start == end:
        return False
    return (start <= now < end) if start < end else (now >= start or now < end)

def _format(result):
    lines = [f"Reminder notification: {result['today']}"]
    for label, key in (("Overdue", "overdue"), ("Due today", "due")):
        if result[key]:
            lines += ["", f"{label}:"]
            lines += [f"- {i['text']} | due: {i['due']}" for i in result[key]]
    return "\n".join(lines)

def check_once():
    with BRAIN_LOCK:
        result = memory.collect_due_reminder_notifications()
        
    items = [("overdue", i) for i in result["overdue"]] + [("due", i) for i in result["due"]]
    if not items:
        return
    
    events.publish("notify", {"text": _format(result)})
    
    if ui_state["visible"]:
        return
    
    verbosity = memory.get_setting("verbosity", "normal")
    if len(items) <= 3:
        for kind, item in items:
            toasts.reminder_toast(kind, item, verbosity)
    else:
        toasts.summary_toast(len(items))
        
def _loop():
    while not _stop.is_set():
        try:
            paused = memory.get_setting("notifications_paused", False)
            if not paused and not _quiet_now():
                check_once()
            if hooks.get("tick"):
                hooks["tick"]()
        except Exception:
            log.exception("notifier loop error")
        _stop.wait(CHECK_EVERY)
        
def start():
    threading.Thread(target=_loop, daemon=True, name="notifier").start()
    
def stop():
    _stop.set()