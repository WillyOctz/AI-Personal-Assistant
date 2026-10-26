import logging
import random
from datetime import date, timedelta
from urllib.parse import parse_qs, urlencode

from assistant import events, memory
from assistant.runtime import BRAIN_LOCK, hooks

log = logging.getLogger("nebula.toasts")

try:
    from windows_toasts import InteractableWindowsToaster, Toast, ToastButton
    _toaster = InteractableWindowsToaster("Nebula")
except Exception:
    log.exception("windows-toasts unavailable; toasts disabled")
    _toaster = None
    
TITLES = {
    "due": ["It's time, dear.", "A small reminder from me."],
    "overdue": ["This one slipped by, dear.", "Still waiting on this one."],
}

def _on_activated(args):
    params = parse_qs(getattr(args, "arguments", "")or "")
    action = params.get("a", [""])[0]
    text = params.get("t", [""])[0]
    
    try:
        if action == "done":
            with BRAIN_LOCK:
                memory.complete_reminder(text) # by text so list won't shift to the wrong one
            events.publish("reminders_changed")
        elif action == "tomorrow":
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            with BRAIN_LOCK:
                memory.set_reminder_due(text, tomorrow)
            events.publish("reminders_changed")
        elif hooks.get("show"):
            hooks["show"]()
    except Exception:
        log.exception("Toast action failed")
        
def _show(title, body, buttons=()):
    if _toaster is None:
        return
    
    toast = Toast([title, body])
    for label, params in buttons:
        toast.AddAction(ToastButton(label, urlencode(params)))
    toast.on_activated = _on_activated
    _toaster.show_toast(toast)
    
def reminder_toast(kind, item, verbosity="normal"):
    title = "Nebula" if verbosity == "minimal" else random.choice(TITLES[kind])
    text = item["text"][:200]
    _show(title, text, [
        ("Done", {"a": "done", "t": text}),
        ("Tomorrow", {"a": "tomorrow", "t": text}),
    ])
    
def summary_toast(count):
    _show("Nebula", f"{count} reminders need you.", [("Open Nebula", {"a": "open"})])