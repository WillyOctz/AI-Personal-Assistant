import ctypes
import logging
import os
import re
import shutil
import threading
import time

from rapidfuzz import fuzz, process

from assistant import app_discovery, memory, settings_spec as S, tools
from assistant.database import get_connection
from assistant.registry import confirmable
from assistant.reply import Reply, button

log = logging.getLogger("nebula.pathfinder")

MAX_DEPTH = 9
FIRST_DELAY = 30
PENDING_TTL = 600

SKIP_DIRS = {
    "$recycle.bin", "system volume information", "node_modules", ".git", "__pycache__", "winsxs", "installer",
    "assembly", "servicing", "softwaredistribution", "temp", "tmp", "cache", "code cache", "gpucache",
    "packages", "windowsapps", "driverstore", "crashpad", "$windows.~bt", "$windows.~ws", "windows.old",
    "recovery", "config.msi", "msocache", "site-packages", ".venv", "venv",
}
SKIP_FILE = re.compile(r"(^unins\d*|uninstall|setup|installer|updater?|^update|crash|report|helper|elevat|"
                       r"vc_?redist|redist|webview|cefsharp|chromedriver)", re.I)
GENERIC_STEMS = {"launcher", "app", "start", "main", "run", "bin", "application"}  
BLOCKED_STEMS = {
    "cmd", "powershell", "powershell_ise", "pwsh", "wscript", "cscript", "mshta", "regedit", "reg", "regedt32",
    "rundll32", "regsvr32", "msiexec", "certutil", "bitsadmin", "wmic", "schtasks", "sc", "net", "net1",
    "taskkill", "shutdown", "format", "diskpart", "bcdedit", "cipher", "takeown", "icacls", "vssadmin",
    "wevtutil", "psexec", "installutil", "msbuild", "forfiles", "runas", "at",
}
RISKY_PARTS = ("\\downloads\\", "\\temp\\", "\\tmp\\", "\\desktop\\", "\\users\\public\\")
SOURCE_BONUS = {"start menu": 15, "app paths": 15, "PATH": 10, "index": 0}
TIER_BONUS = {"trusted": 8, "standard": 0, "risky": -25, "protected": -15}
WHY = {
    "trusted": "an installed program",
    "standard": "a folder that isn't a standard install location",
    "risky": "a folder where downloads and temp files land, so I can't tell where it came from",
    "protected": "a protected place (Windows, a drive root or shared system data)",
}


status = {"running": False, "last_start": None, "last_end": None, "found": 0}
_stop, _wake, _force = threading.Event(), threading.Event(), threading.Event()
_thread = None
_ready = False
_lock = threading.Lock()
_cache = {"rows": [], "dirty": True}
_sm = {"at": 0.0, "items": {}}


# ------------------------------Storage---------------------------------
def _init():
    global _ready
    if _ready:
        return
    with _lock:
        if _ready:
            return
        conn = get_connection()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS exe_index (
                path TEXT PRIMARY KEY, name TEXT NOT NULL, stem TEXT NOT NULL, depth INTEGER NOT NULL,
                mtime REAL NOT NULL, size INTEGER NOT NULL, seen REAL NOT NULL)""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_exe_name ON exe_index (name)")
            conn.commit()
        finally:
            conn.close()
        _ready = True
        
def _rows():
    if _cache["dirty"]:
        _init()
        conn = get_connection()
        try:
            _cache["rows"] = [dict(r) for r in conn.execute("SELECT path, name, depth, mtime FROM exe_index")]
        finally:
            conn.close()
        _cache["dirty"] = False
    return _cache["rows"]

def index_ready():
    return bool(_rows())

# --------------------------------------Scan------------------------------------------
def fixed_drives():
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    out = []
    for i in range(26):
        if mask >> i & 1:
            root = f"{chr(65 + i)}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(root) == 3:
                out.append(root)
    return out

def _display_name(stem, folder):
    return folder.lower() if stem in GENERIC_STEMS and folder else stem

def scan(roots=None, should_stop=None):
    _init()
    started = time.time()
    status.update(running=True, last_start=started, found=0)
    win = os.path.normcase(os.environ.get("SystemRoot", "C:\\Windows"))
    batch, total, stopped = [], 0, False
    conn = get_connection()
    
    try:
        def flush():
            if batch:
                conn.executemany("INSERT OR REPLACE INTO exe_index (path, name, stem, depth, mtime, size, seen) "
                                 "VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                conn.commit()
                batch.clear()
                
        for root in (roots or fixed_drives()):
            stack = [(root, 0)]
            while stack and not stopped:
                if should_stop and should_stop():
                    stopped = True
                    break
                current, depth = stack.pop()
                try:
                    with os.scandir(current) as it:
                        entries = list(it)
                except OSError:
                    continue
                low = os.path.normcase(current).rstrip("\\")
                in_win = low == win or low.startswith(win + "\\")
                for e in entries:
                    name = e.name
                    lname = name.lower()
                    try:
                        is_dir = e.is_dir(follow_symlinks=False)
                        st = e.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if is_dir:
                        if lname in SKIP_DIRS or depth >= MAX_DEPTH:
                            continue
                        if getattr(st, "st_file_attributes", 0) & 0x400:  
                            continue
                        if in_win and not (low == win and lname == "system32"):
                            continue 
                        stack.append((e.path. depth + 1))
                    elif lname.endswith(".exe"):
                        stem = lname[:-4]
                        if stem in BLOCKED_STEMS or SKIP_FILE.search(stem):
                            continue
                        folder = os.path.basename(current.rstrip("\\"))
                        batch.append((e.path, _display_name(stem, folder), stem, depth, st.st_mtime, st.st_size, started))
                        total += 1
                        if len(batch) >= 2000:
                            flush()
                            status["found"] = total
                            time.sleep(0.01)
        
        flush()
        if not stopped:
            conn.execute("DELETE FROM exe_index WHERE seen < ?", (started,))
            conn.commit()
            memory.set_state_value("exe_index_at", time.time())
    
    finally:
        conn.close()
        status.update(running=False, last_end=time.time(), found=total)
        _cache["dirty"] = True
        
    return {"found": total, "stopped": stopped}