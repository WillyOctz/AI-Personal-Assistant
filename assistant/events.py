import json
import queue
import threading

_subscribers = set()
_lock = threading.Lock()

def publish(kind, data=None):
    payload = f"event: {kind}\ndata: {json.dumps(data or {})}\n\n"
    with _lock:
        for q in list(_subscribers):
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass
            
def stream():
    q = queue.Queue(maxsize=100)
    with _lock:
        _subscribers.add(q)
        
    try:
        yield ": connected\n\n"
        while True:
            try:
                yield q.get(timeout=15)
            except queue.Empty:
                yield ": ping\n\n"
                
    finally:
        with _lock:
            _subscribers.discard(q)