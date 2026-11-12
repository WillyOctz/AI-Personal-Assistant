import ctypes
import os
import re
import threading
import time
from contextlib import contextmanager

from rapidfuzz import fuzz, process

from assistant.database import get_connection
from assistant.tools import open_folder_in_explorer

BLOCKED_EXT = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".msix", ".appx", ".ps1", ".psm1", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".hta", ".scr", ".lnk", ".reg", ".dll", ".cpl", ".msc", ".jar",
}

ALIASES = {
    "download": "downloads", "docs": "documents", "doc": "documents", "document": "documents",
    "pics": "pictures", "pic": "pictures", "photos": "pictures", "picture": "pictures",
    "video": "videos", "song": "music", "songs": "music", "home folder": "home",
}

_ready = False
_lock = threading.Lock()


@contextmanager
def _db():
    global _ready
    conn = get_connection()
    
    try:
        if not _ready:
            with _lock:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS pins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    path TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    uses INTEGER NOT NULL DEFAULT 0,
                    last_used REAL,
                    created REAL NOT NULL)"""
                )
                conn.commit()
                _ready = True
                
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
        
def clean_name(text):
    return re.sub(r"\s+", " ", str(text or "").lower().strip().strip("\"'"))[:40]

def clean_query(text):
    q = clean_name(text)
    q = re.sub(r"^(?:my|the|our)\s+", "", q)
    q = re.sub(r"\s+(?:folder|directory|dir)$", "", q)
    return q.strip()


# -------------------------------Windows common folders--------------------------------
def _csidl(code):
    try:
        buffer = ctypes.create_unicode_buffer(260)
        
        if ctypes.windll.shell32.SHGetFolderPathW(None, code, None, 0, buffer) == 0:
            return buffer.value
        
    except Exception:
        pass
    
    return ""

def special_folders():
    home = os.path.expanduser("-")
    candidates = {
        "desktop": _csidl(0x10), "documents": _csidl(0x05), "pictures": _csidl(0x27),
        "music": _csidl(0x0D), "videos": _csidl(0x0E),
        "downloads": os.path.join(home, "Downloads"), "home": home,
    }
    return {name: path for name, path in candidates.items() if path and os.path.isdir(path)}


# -----------------------------------CRUD-----------------------------------------------
def get_pin(name):
    with _db() as conn:
        row = conn.execute("SELECT * FROM pins WHERE name = ?", (clean_name(name),)).fetchone()
        
    return dict(row) if row else None

def list_pins(limit=100):
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM pins ORDER BY uses DESC, COALESCE(last_used, 0) DESC, name LIMIT ?", (limit,)
        ).fetchall()
        
    return [dict(row) for row in rows]

def add_pin(name, path):
    raw = str(path or "").strip().strip('"')
    
    if not raw:
        return {"ok": False, "reason": "invalid"}
    
    full = os.path.abspath(os.path.expandvars(os.path.expanduser(raw)))
    
    if not os.path.exists(full):
        return {"ok": False, "reason": "not_found"}
    
    kind = "folder" if os.path.isdir(full) else "file"
    pin_name = clean_name(name) or clean_name(os.path.basename(full.rstrip("\\/")) or full)
    
    if not pin_name:
        return {"ok": False, "reason": "invalid"}
    
    existed = get_pin(pin_name) is not None
    
    with _db() as conn:
        conn.execute(
            """INSERT INTO pins (name, path, kind, uses, last_used, created) VALUES (?, ?, ?, 0, NULL, ?)
               ON CONFLICT(name) DO UPDATE SET path = excluded.path, kind = excluded.kind""",
            (pin_name, full, kind, time.time()),
        )
        
    return {"ok": True, "created": not existed, "pin": get_pin(pin_name)}

def remove_pin(name):
    with _db() as conn:
        return conn.execute("DELETE FROM pins WHERE name = ?", (clean_name(name),)).rowcount > 0
    
def touch(name):
    with _db() as conn:
        conn.execute("UPDATE pins SET uses = uses + 1, last_used = ? WHERE name = ?",
                     (time.time(), clean_name(name)))
        
        
# -------------------------------------Resolving for download folder or thesis---------------------------------------
def resolve(query):
    for candidate in (clean_name(query), clean_query(query)):
        if candidate:
            pin = get_pin(candidate)
            
            if pin:
                return {**pin, "source": "pin"}
            
    q = clean_query(query)
    
    if not q:
        return None
    
    key = ALIASES.get(q, q)
    special = special_folders()
    
    if key in special:
        return {"name": key, "path": special[key], "kind": "folder", "source": "special"}
    
    pins = list_pins()
    
    if pins:
        hit = process.extractOne(q, [p["name"] for p in pins], scorer=fuzz.ratio, score_cutoff=82)
        
        if hit:
            return {**pins[hit[2]], "source": "pin"}
        
    return None

def quick(limit=6):
    out = [{"name": p["name"], "kind": p["kind"]} for p in list_pins(limit)]
    special = special_folders()
    
    for name in ("downloads", "documents", "desktop"):
        if name in special and len(out) < limit and all(o["name"] != name for o in out):
            out.append({"name": name, "kind": "folder"})
            
    return out[:limit]

def open_path(path):
    """re-validate at the moment of opening"""
    if not os.path.exists(path):
        return {"ok": False, "reason": "not_found"}
    
    if os.path.isdir(path):
        return open_folder_in_explorer(path)
    
    if os.path.splitext(path)[1].lower() in BLOCKED_EXT:
        return {"ok": False, "reason": "blocked_type"}
    
    try:
        os.startfile(path)
        return {"ok": True, "reason": "opened"}
    except OSError:
        return {"ok": False, "reason": "open_error"}