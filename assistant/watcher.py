import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from assistant import file_index, indexer, memory

DEBOUNCE = 45          # seconds of quiet before a rescan
_observer = None
_timer = None
_lock = threading.Lock()


def _schedule():
    global _timer

    with _lock:
        if _timer:
            _timer.cancel()

        _timer = threading.Timer(DEBOUNCE, indexer.request_scan)
        _timer.daemon = True
        _timer.start()

class _Handler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.event_type not in ("created", "deleted", "moved"):
            return

        parts = {p.lower() for p in event.src_path.replace("\\", "/").split("/")}

        if parts & file_index.INDEX_IGNORED:
            return

        _schedule()

def start():
    global _observer

    _observer = Observer()

    for path in memory.get_search_folders().values():
        try:
            _observer.schedule(_Handler(), path, recursive=True)
        except OSError:
            pass

    _observer.daemon = True
    _observer.start()

def stop():
    if _observer:
        _observer.stop()