import threading

BRAIN_LOCK = threading.RLock()
ui_state = {"visible": True}
hooks = {}

