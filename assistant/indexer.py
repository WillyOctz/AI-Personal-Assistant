import logging
import threading
import time

from assistant import events, file_index, memory, personality

log = logging.getLogger("nebula.indexer")

FIRST_DELAY = 5
CONTENT_RETRY = 60

_wake = threading.Event()
_stop = threading.Event()
_announce = False

status = {"running": False, "phase": "", "last_start": None, "last_end": None, "last": None}


def request_scan(announce=False):
    global _announce
    _announce = _announce or announce
    _wake.set()
    
def _interval():
    return max(1, float(memory.get_setting("index_interval_hours", 3))) * 3600

def run_scan_once(announce=False):
    status.update(running=True, phase="folders", last_start=time.time())
    remaining = 0
    
    try:
        folders = memory.get_search_folders()
        file_index.prune_roots(folders.keys())
        
        files = projects = 0
        
        for name, path in folders.items():
            if _stop.is_set():
                break
            
            result = file_index.scan_root(name, path, should_stop=_stop.is_set)
            
            if not result["ok"]:
                log.warning("Skipped root %s (%s)", name, result["reason"])
                continue
            
            files += result["items"]
            projects += result["projects"]
            
        if memory.get_setting("index_content", True) and not _stop.is_set():
            status["phase"] = "contents"
            remaining = file_index.index_contents(should_stop=_stop.is_set)["remaining"]
            
        file_index.invalidate_cache()
        events.publish("today_changed")
        
        status["last"] = {"files": files, "projects": projects}
        
        if announce and not _stop.is_set():
            text = personality.line(
                "index.done",
                verbosity=memory.get_setting("verbosity", "normal"),
                files=files, n=projects,
            )
            events.publish("notify", {"text": text})
            
    except Exception:
        log.exception("index scan failed")
    finally:
        status.update(running=False, phase="", last_end=time.time())
        
    return remaining

def _loop():
    global _announce
    
    _stop.wait(FIRST_DELAY)
    
    while not _stop.is_set():
        announce, _announce = _announce, False
        wait = _interval()
        
        if memory.get_setting("index_enabled", True) or announce:
            remaining = run_scan_once(announce)
            wait = CONTENT_RETRY if remaining else _interval()
            
        _wake.wait(wait)
        _wake.clear()
        

def start():
    threading.Thread(target=_loop, daemon=True, name="indexer").start()
    
def stop():
    _stop.set()
    _wake.set()