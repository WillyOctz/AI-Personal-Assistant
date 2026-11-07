import ctypes
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from ctypes import wintypes
from datetime import datetime

import psutil

from assistant import file_index, focus, memory
from assistant.database import get_connection

log = logging.getLogger("nebula.monitor")

POLL = 5              # seconds between samples
CONFIG_EVERY = 30     # reload settings + run companion rules
RUN_RESET = 300       
MATCHER_EVERY = 300   # refresh the project-name matchers

# Only these apps are allowed to be attributed to a project
WORK_APPS = {
    "code.exe", "code - insiders.exe", "cursor.exe", "zed.exe", "pycharm64.exe", "idea64.exe",
    "webstorm64.exe", "rider64.exe", "clion64.exe", "androidstudio64.exe", "devenv.exe",
    "sublime_text.exe", "notepad++.exe", "notepad.exe", "atom.exe", "explorer.exe",
    "windowsterminal.exe", "wt.exe", "cmd.exe", "powershell.exe", "pwsh.exe", "conhost.exe",
}

# Folder names too common to attribute safely 
GENERIC_NAMES = {
    "src", "app", "apps", "test", "tests", "docs", "main", "code", "project", "projects",
    "website", "web", "api", "lib", "backend", "frontend", "client", "server", "build", "demo",
}
DEFAULT_EXCLUDE = ["keepass.exe", "keepassxc.exe", "bitwarden.exe", "1password.exe", "lastpass.exe"]

FRIENDLY = {
    "code": "VS Code", "chrome": "Chrome", "msedge": "Edge", "firefox": "Firefox",
    "explorer": "Explorer", "windowsterminal": "Terminal", "powershell": "PowerShell",
    "pwsh": "PowerShell", "cmd": "Command Prompt", "notepad": "Notepad", "spotify": "Spotify",
    "discord": "Discord", "winword": "Word", "excel": "Excel", "powerpnt": "PowerPoint",
}

def friendly(app):
    base = (app or "unknown").lower()
    base = base[:-4] if base.endswith(".exe") else base
    return FRIENDLY.get(base, base.replace("_", " ").title())

def fmt_duration(seconds):
    s = int(max(0, seconds))
    
    if s < 60:
        return f"{s} sec"
    
    m = s // 60
    
    if m < 60:
        return f"{m} min"
    
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m" if m else f"{h}h"


# -------------------------------Windows API---------------------------------
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_kernel32.GetTickCount.restype = wintypes.DWORD

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]
    
def idle_seconds():
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    
    return ((_kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0 # 32-bit only

def active_window():
    hwnd = _user32.GetForegroundWindow()
    
    if not hwnd:
        return None
    
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    length = _user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buffer, length + 1)
    
    try:
        app = psutil.Process(pid.value).name().lower()
    except (psutil.Error, OSError):
        app = "unknown"
        
    return {"pid": pid.value, "app": app, "title": buffer.value}


# --------------------------------------Database----------------------------------
_init_done = False
_init_lock = threading.Lock()

def _init():
    global _init_done

    if _init_done:
        return

    with _init_lock:
        if _init_done:
            return

        conn = get_connection()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started REAL NOT NULL,
                ended REAL NOT NULL,
                app TEXT NOT NULL,
                project_id INTEGER,
                project TEXT
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_started ON activity_log (started)")
            conn.commit()
        finally:
            conn.close()

        _init_done = True

@contextmanager
def _db():
    _init()
    conn = get_connection()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
        
        
# -----------------------------------Project Attribution--------------------------------
def build_matchers(projects):
    out = []
    
    for p in projects:
        name = (p.get("name") or "").lower()
        
        if len(name) < 4 or name in GENERIC_NAMES:
            continue
        
        out.append((len(name), re.compile(rf"(?<![\w]){re.escape(name)}(?![\w])"), p["id"], p["name"]))
        
    out.sort(key=lambda item: -item[0])
    return out

def match_project(app, title, matchers):
    if app not in WORK_APPS or not title:
        return None
    
    low = title.lower()
    
    for _, rx, pid, name in matchers:
        if rx.search(low):
            return pid, name
        
    return None

_matchers = []
_matchers_at = 0.0


def _get_matchers(now):
    global _matchers, _matchers_at
    
    if not _matchers_at or now - _matchers_at > MATCHER_EVERY:
        try:
            _matchers = build_matchers(file_index.list_projects(500))
        except Exception:
            log.exception("could not refresh project matchers")
            
        _matchers_at = now
        
    return _matchers


# --------------------Config-----------------------------
def load_config():
    s, st = memory.get_all_settings(), memory.get_all_state()
    
    started = None
    
    if st.get("focus_started_at"):
        parsed = focus.parse_timestamp(st["focus_started_at"])
        started = parsed.timestamp() if parsed else None
        
    return {
        "enabled": bool(s.get("monitor_enabled", False)),
        "nudges": bool(s.get("nudges_enabled", True)),
        "paused": bool(s.get("notifications_paused", False)),
        "suggest": bool(s.get("suggest_focus", True)),
        "recap_ai": bool(s.get("recap_llm", True)),
        "verbosity": s.get("verbosity", "normal"),
        "idle_limit": int(s.get("idle_limit_seconds", 120)),
        "resume_gap": int(s.get("resume_gap_minutes", 30)) * 60,
        "break_min": int(s.get("break_minutes", 50)),
        "distraction_min": int(s.get("distraction_minutes", 10)),
        "min_gap": int(s.get("nudge_min_gap_minutes", 20)) * 60,
        "max_per_day": 8,
        "retention_days": int(s.get("activity_retention_days", 30)),
        "recap_time": s.get("recap_time", "") or "",
        "distraction_apps": [a.lower() for a in s.get("distraction_apps", [])],
        "exclude": {a.lower() for a in s.get("monitor_exclude", DEFAULT_EXCLUDE)},
        "focus_on": bool(st.get("focus_mode")),
        "focus_task": st.get("focus_task") or "",
        "focus_started": started,
    }
    
    
# ----------------------------Sampling--------------------------------
_UNSET = object()
_seg = None
_run_start = None
_last_active = _UNSET
_last_tick = 0.0
_state = {"active": False, "app": None, "project_id": None, "project": None, "run_start": None}


def _companion():
    from assistant import companion
    return companion

def _db_last_end():
    with _db() as c:
        row = c.execute("SELECT MAX(ended) AS e FROM activity_log").fetchone()

    return row["e"] if row else None

def _close(at):
    global _seg

    seg, _seg = _seg, None

    if not seg:
        return

    try:
        with _db() as c:
            c.execute("UPDATE activity_log SET ended = ? WHERE id = ?", (max(seg["started"], at), seg["id"]))
    except Exception:
        log.exception("could not close activity segment")
        
def _step(cfg):
    global _seg, _run_start, _last_active, _last_tick
    
    now = time.time()
    
    if _last_active is _UNSET:
        _last_active = _db_last_end()
        
    if _last_tick and now - _last_tick > POLL * 6 and _seg:
        _close(_last_tick)
        
    _last_trick = now
    
    idle = idle_seconds()
    window = active_window() if idle < cfg["idle_limit"] else None
    
    if window is None:
        if _seg:
            _close(now - idle)
            
        _state.update(active=False)
        return
    
    prev = _last_active
    _last_active = now
    
    if prev is None or now - prev >= RUN_RESET:
        _run_start = now
        
    if prev is not None and now - prev >= cfg["resume_gap"]:
        try:
            _companion().on_return(cfg, now - prev)
        except Exception:
            log.exception("on_return failed")
            
    app = window["app"]
    ignored = (
        window["pid"] == os.getpid()
        or window["title"] == "Nebula"
        or app in cfg["exclude"]
    )
    
    if ignored:
        if _seg:
            _close(now)
            
        _state.update(active=True, app=None, project_id=None, project=None, run_start=_run_start)
        return
    
    match = match_project(app, window["title"], _get_matchers(now))
    pid, pname = match if match else (None, None)
    
    if _seg and _seg["app"] == app and _seg["project_id"] == pid:
        with _db() as c:
            c.execute("UPDATE activity_log SET ended = ? WHERE id = ?", (now, _seg["id"]))
            
    else:
        if _seg:
            _close(now)
            
        with _db() as c:
            cur = c.execute(
                "INSERT INTO activity_log (started, ended, app, project_id, project) VALUES (?, ?, ?, ?, ?)",
                (now, now, app, pid, pname),
            )
            _seg = {"id": cur.lastrowid, "app": app, "project_id": pid, "started": now}
            
    _state.update(active=True, app=app, project_id=pid, project=pname, run_start=_run_start)
    
def _pause():
    global _last_active, _run_start
    
    if _seg:
        _close(time.time())
        
    _last_active = None
    _run_start = None
    _state.update(active=False, app=None, project_id=None, project=None, run_start=None)
    
    
# -------------------------------Thread------------------------------------
_stop = threading.Event()
_wake = threading.Event()
_thread = None

def _loop():
    cfg, cfg_at, last_prune = None, 0.0, 0.0
    
    while not _stop.is_set():
        try:
            now = time.time()
            refreshed = False
            
            if cfg is None or _wake.is_set() or now - cfg_at >= CONFIG_EVERY:
                _wake.clear()
                cfg, cfg_at, refreshed = load_config(), now, True
                
            if cfg["enabled"]:
                _step(cfg)
                
                if refreshed:
                    _companion().evaluate(cfg, snapshot())
                    
                if now - last_prune > 6 * 3600:
                    prune(cfg["retention_days"])
                    last_prune = now
                    
            else:
                _pause()
                
        except Exception:
            log.exception("monitor loop error")    
    
    try:
        _close(time.time())
    except Exception:
        pass
    

def start():
    global _thread
    
    if _thread and _thread.is_alive():
        return
    
    _thread = threading.Thread(target=_loop, daemon=True, name="monitor")
    _thread.start()
    
def stop():
    _stop.set()
    _wake.set()
    
def refresh():
    _wake.set()
    
def snapshot():
    return dict(_state)


current = snapshot

# ----------------------------Queries----------------------------
def day_start(ts=None):
    return datetime.fromtimestamp(ts or time.time()).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

def last_project_info():
    with _db() as c:
        row = c.execute(
            "SELECT project_id, project, ended FROM activity_log "
            "WHERE project_id IS NOT NULL ORDER BY ended DESC LIMIT 1"
        ).fetchone()
        
    return {"id": row["project_id"], "name": row["project"], "ended": row["ended"]} if row else None

def project_seconds(window_s, now=None):
    now = now or time.time()
    since = now - window_s
    
    with _db() as c:
        rows = c.execute(
            """SELECT project_id, project, SUM(MIN(ended, ?) - MAX(started, ?)) AS secs
               FROM activity_log
               WHERE project_id IS NOT NULL AND ended > ? AND started < ?
               GROUP BY project_id ORDER BY secs DESC""",
            (now, since, since, now),
        ).fetchall()
        
    return [{"id": r["project_id"], "name": r["project"], "seconds": r["secs"] or 0} for r in rows]

def app_seconds(apps, window_s, now=None):
    if not apps:
        return 0.0
    
    now = now or time.time()
    since = now - window_s
    marks = ",".join("?" * len(apps))
    
    with _db() as c:
        row = c.execute(
            f"""SELECT SUM(MIN(ended, ?) - MAX(started, ?)) AS secs
                FROM activity_log WHERE app IN ({marks}) AND ended > ? AND started < ?""",
            (now, since, *apps, since, now),
        ).fetchone()
        
    return float(row["secs"] or 0)

def top_project_between(start, end, minimum=60):
    with _db() as c:
        row = c.execute(
            """SELECT project_id, project, SUM(MIN(ended, ?) - MAX(started, ?)) AS secs
               FROM activity_log
               WHERE project_id IS NOT NULL AND ended > ? AND started < ?
               GROUP BY project_id ORDER BY secs DESC LIMIT 1""",
            (end, start, start, end),
        ).fetchone()
        
    if not row or (row["secs"] or 0) < minimum:
        return None
    
    return {"id": row["project_id"], "name": row["project"], "seconds": row["secs"]}

def summary(start, end, top=5):
    with _db() as c:
        rows = c.execute(
            """SELECT app, project_id, project, MIN(ended, ?) - MAX(started, ?) AS secs
               FROM activity_log WHERE ended > ? AND started < ?""",
            (end, start, start, end),
        ).fetchall()
        
    apps, projects, total = {}, {}, 0.0
    
    for r in rows:
        secs = max(0.0, r["secs"] or 0)
        total += secs
        apps[r["app"]] = apps.get(r["app"], 0) + secs
        
        if r["project_id"] is not None:
            key = (r["project_id"], r["project"])
            projects[key] = projects.get(key, 0) + secs
            
    def best(items):
        return sorted(items, key=lambda x: -x["seconds"])[:top]
    
    return {
        "total": total,
        "apps": best([{"name": friendly(a), "raw": a, "seconds": s} for a, s in apps.items()]),
        "projects": best([{"id": k[0], "name": k[1], "seconds": s} for k, s in projects.items()]),
    }

def today_summary(top=3):
    try:
        s = summary(day_start(), time.time(), top=top)
    except Exception:
        log.exception("today_summary failed")
        return None
    
    return {
        "total_seconds": int(s["total"]),
        "total_text": fmt_duration(s["total"]),
        "projects": [{"name": p["name"], "text": fmt_duration(p["seconds"])} for p in s["projects"]],
        "apps": [{"name": a["name"], "text": fmt_duration(a["seconds"])} for a in s["apps"]],
    }
    
def stats():
    with _db() as c:
        row = c.execute("SELECT COUNT(*) AS n, MIN(started) AS oldest FROM activity_log").fetchone()
        
    seen = [a["raw"] for a in summary(day_start(), time.time(), top=8)["apps"]]
    return {"rows": row["n"], "oldest": row["oldest"], "apps_today": seen}

def prune(days):
    with _db() as c:
        c.execute("DELETE FROM activity_log WHERE ended < ?", (time.time() - days * 86400,))
        
def forget(everything=False):
    global _seg
    
    with _db() as c:
        if everything:
            cur = c.execute("DELETE FROM activity_log")
        else:
            cur = c.execute("DELETE FROM activity_log WHERE started >= ?", (day_start(),))
            
        deleted = cur.rowcount
 
    _seg = None
    return deleted