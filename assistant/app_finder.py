import ctypes
import logging
import os
import re
import shutil
import threading
import time
import numpy as np

from datetime import datetime
from pathlib import Path
from rapidfuzz import fuzz, process

from assistant import app_discovery, memory, settings_spec as S, tools
from assistant.database import get_connection
from assistant.registry import confirmable
from assistant import app_discovery, file_index, local_embed, memory, pins, settings_spec as S, tools
from assistant import launch_rank as R
from assistant.intents import KNOWN_GAMES
from assistant.reply import Reply, button, copy_button

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
WHY = {
    "trusted": "an installed program",
    "standard": "a folder that isn't a standard install location",
    "risky": "a folder where downloads and temp files land, so I can't tell where it came from",
    "protected": "a protected place (Windows, a drive root or shared system data)",
}

VEC_FILE = Path("db/exe_vectors.npz")
SOURCE_BONUS = {"registered": 6, "start menu": 4, "app paths": 4, "PATH": 3, "index": 0}
TIER_RANK = {"trusted": 3, "standard": 0, "risky": -8, "protected": -6}


status = {"running": False, "last_start": None, "last_end": None, "found": 0}
_stop, _wake, _force = threading.Event(), threading.Event(), threading.Event()
_thread = None
_ready = False
_lock = threading.Lock()
_cache = {"rows": [], "names": set(), "names_list": [], "dirty": True}
_sm = {"at": 0.0, "items": {}}
_vec = {"X": None, "rows": []}
_usage = {"at": 0.0, "map": {}}
_memo = {"key": None, "at": 0.0, "val": None}

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
        
def _games():
    return {g.lower() for g in memory.get_entities("games")} | {g.lower() for g in KNOWN_GAMES}
        
def _rows():
    if _cache["dirty"]:
        _init()
        games = _games()
        conn = get_connection()
        try:
            rows = [dict(r) for r in conn.execute("SELECT path, name, depth, mtime FROM exe_index")]
        finally:
            conn.close()
        for r in rows:
            r["kind"] = R.kind_of(r["path"], r["name"], games)
        _cache.update(rows=rows, names={r["name"] for r in rows}, names_list=[r["name"] for r in rows], dirty=False)
    return _cache["rows"]

def index_ready():
    return bool(_rows())

# --------------------------------------Scan------------------------------------------
def _doc(r):
    return f"{r['name']}. {r['kind']}. {os.path.basename(os.path.dirname(r['path']))}"

def build_vectors(should_stop=None, cap=40000):
    if not local_embed.available():
        return
    rows = _rows()
    uniq = {}
    for r in rows:
        uniq.setdefault(_doc(r), r)
    texts = list(uniq)[:cap]
    cached = {}
    if VEC_FILE.exists():
        try:
            data = np.load(VEC_FILE, allow_pickle=False)
            if str(data["model"]) == local_embed.MODEL_NAME:
                cached = dict(zip(data["texts"].tolist(), data["X"]))
        except Exception:
            log.exception("program vector cache unreadable; rebuilding")
            
    missing = [t for t in texts if t not in cached]
    for i in range(0, len(missing), 64):
        if should_stop and should_stop():
            break
        chunk = missing[i:i + 64]
        cached.update(zip(chunk, local_embed.embed(chunk)))
        time.sleep(0.02)
    if cached:
        VEC_FILE.parent.mkdir(parents=True, exist_ok=True)
        np.savez(VEC_FILE, X=np.stack(list(cached.values())), texts=np.array(list(cached)),
                 model=np.array(local_embed.MODEL_NAME))
    ready = [t for t in texts if t in cached]
    if ready:
        _vec.update(X=np.stack([cached[t] for t in ready]), rows=[uniq[t] for t in ready])
        
def _semantic(text, limit=15, floor=0.03):
    if _vec["X"] is None or not local_embed.is_ready():
        return []
    sims = _vec["X"] @ local_embed.embed([text])[0]
    return [(_vec["rows"][i], float(sims[i])) for i in np.argsort(-sims)[:limit] if sims[i] >= floor]

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
                        if getattr(st, "st_file_attributes", 0) & 0x400 and not _is_real_dir(e.path):  
                            continue
                        if in_win and not (low == win and lname == "system32"):
                            continue 
                        stack.append((e.path, depth + 1))
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

def _loop():
    _stop.wait(FIRST_DELAY)
    while not _stop.is_set():
        try:
            scanned = False
            last = memory.get_state_value("exe_index_at") or 0
            due = time.time() - last >= S.get("app_index_hours") * 3600
            if S.get("app_search_enabled") and (_force.is_set() or due or not index_ready()):
                _force.clear()
                scan(should_stop=_stop.is_set)
                scanned = True
            if (S.get("app_search_enabled") and S.get("app_search_semantic")
                    and (scanned or _vec["X"] is None) and index_ready()):
                build_vectors(should_stop=_stop.is_set)
        except Exception:
            log.exception("app index scan failed")
        _wake.wait(1800)
        _wake.clear()
        
def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    
    _stop.clear()
    _thread = threading.Thread(target=_loop, daemon=True, name="app-index")
    _thread.start()
    
def stop():
    _stop.set()
    _wake.set()
    
def request_scan():
    _force.set()
    _wake.set()
    
# ----------------------------------Lookup---------------------------------------------
def clean_query(text):
    q = re.sub(r"\.exe$", "", (text or "").lower().strip())
    q = re.sub(r"^(?:the|my)\s+", "", q)
    return re.sub(r"\s+", " ", q).strip()

def _is_real_dir(path):
    try:
        return os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.abspath(path))
    except OSError:
        return False

def _name_score(q, name):
    if name == q:
        return 100
    if len(q) >= 3 and name.startswith(q):
        return 93
    return 0

def _ts(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").timestamp()
    except (TypeError, ValueError):
        return 0.0

def _usage_map():
    if time.time() - _usage["at"] > 60:
        counts = {}
        for ev in memory.get_app_launches(limit=None):
            target, _ = tools.split_command(ev["command"])
            key = os.path.normcase(target)
            n, last = counts.get(key, (0, 0.0))
            counts[key] = (n + 1, max(last, _ts(ev["timestamp"])))
        _usage.update(at=time.time(), map=counts)
    return _usage["map"]

def classify(path):
    p = os.path.normcase(os.path.abspath(path))
    stem = os.path.splitext(os.path.basename(p))[0]
    if stem in BLOCKED_STEMS:
        return "blocked"
    win = os.path.normcase(os.environ.get("SystemRoot", "C:\\Windows"))
    home = os.path.normcase(os.path.expanduser("~"))
    users = os.path.normcase(os.path.join(os.path.splitdrive(p)[0] + "\\" + "users"))
    programdata = os.path.normcase(os.environ.get("ProgramData", "C:\\ProgramData"))
    parent = os.path.dirname(p)
    if parent == os.path.normcase(os.path.splitdrive(p)[0] + "\\"):
        return "protected"
    if p.startswith(win + "\\") or p.startswith(programdata + "\\") or "\\$recycle.bin\\" in p:
        if "\\microsoft\\windows\\start menu\\" not in p:
            return "protected"
    if p.startswith(users + "\\") and not p.startswith(home + "\\"):
        return "protected"
    if any(part in p for part in RISKY_PARTS):
        return "risky"
    pf = [os.path.normcase(os.environ.get(k, "")) for k in ("ProgramFiles", "ProgramFiles(x86)")]
    local = os.path.normcase(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"))
    if any(x and p.startswith(x + "\\") for x in pf) or (local and p.startswith(local + "\\")):
        return "trusted"
    if "\\microsoft\\windows\\start menu\\" in p:
        return "trusted"
    return "standard"

def _start_menu():
    if time.time() - _sm["at"] > 120:
        _sm.update(at=time.time(), items=app_discovery.start_menu_programs())
    return _sm["items"]

def _add(cands, path, name, source, match, depth=0, mtime=0.0):
    if not os.path.isfile(path):
        return
    tier = classify(path)
    if tier == "blocked" or (tier == "protected" and not S.get("app_search_protected")):
        return
    age_days = max(0.0, (time.time() - mtime) / 86400) if mtime else 9999
    score = match + SOURCE_BONUS[source] + TIER_RANK[tier] - depth + 5 * 0.5 ** (age_days / 180)
    item = {"name": name, "path": path, "source": source, "tier": tier, "match": match, "score": score}
    if name not in cands or score > cands[name]["score"]:
        cands[name] = item
        
def find(query, limit=3):
    q = clean_query(query)
    if not q:
        return {"status": "none", "candidates": []}
    if q in BLOCKED_STEMS:
        return {"status": "blocked", "name": q, "candidates": []}
    
    cands = {}
    for name, path in _start_menu().items():
        score = _name_score(q, name)
        if score:
            _add(cands, path, name, "start menu", score)
    if re.fullmatch(r"[\w .\-+]+", q):
        hit = tools.app_paths_lookup(q)
        if hit:
            _add(cands, hit, q, "app paths", 100)
    which = shutil.which(q)
    if which:
        _add(cands, which, q, "PATH", 100)
        
    rows = _rows()
    exact = [(r, _name_score(q, r["name"])) for r in rows if _name_score(q, r["name"])]
    if not exact and len(q) >= 4:
        names = [r["name"] for r in rows]
        exact = [(rows[pos], score) for _, score, pos in process.extract(q, names, scorer=fuzz.WRatio, limit=8, score_cutoff=90)]
    for r, score in exact:
        _add(cands, r["path"], r["name"], "index", score, r["depth"], r["mtime"])
        
    ordered = sorted(cands.values(), key=lambda c: -c["score"])[:limit]
    if ordered:
        return {"status": "ok", "candidates": ordered}
    if not index_ready() or status["running"]:
        return {"status": "indexing", "candidates": []}
    return {"status": "none", "candidates": []}

def looks_installed(query):
    found = find(query, limit=1)
    return found["status"] == "ok" and found["candidates"][0]["match"] >= 93


# ----------------------------------------------Offer/Approve----------------------------------------------
def _fresh(pending):
    return pending and time.time() - pending.get("at", 0) < PENDING_TTL

def _ask(c):
    st = os.stat(c["path"])
    pending = {"name": c["name"], "path": c["path"], "tier": c["tier"], "source": c["source"],
               "size": st.st_size, "mtime": st.st_mtime, "at": time.time(),
               "strict": c["tier"] in ("risky", "protected")}
    memory.set_state_value("pending_found_app", pending)
    where = f"{c['path']}\nFound via: {c['source']}"
    if not pending["strict"]:
        return Reply(say=f"I found {c['name']} on your PC, dear. Shall I open it?",
                     detail=f"{where}\nReply yes to open it or no to cancel.", kind="confirm",
                     data={"title": f"Open {c['name']}", "subtitle": c["path"]},
                     needs_confirmation=True, styled=True)
    return Reply(
        say=f"I found {c['name']}, but it is in {WHY[c['tier']]}. I need a stronger approval for that.",
        detail=f"{where}\nPress the button, or type: allow opening {c['name']}",
        actions=[button(f"Allow opening {c['name']}", f"allow opening {c['name']}", style="danger"),
        button("Cancel", "no", style="ghost")], styled=True
    )
    
def offer(query):
    if not S.get("app_search_enabled"):
        return None
    found = find(query)
    if found["status"] == "blocked":
        return Reply(
            say=f"I never open '{found['name']}' from a search, dear.",
            detail="Shells and system tools must be registered by you: register app NAME as <path>",
            styled=True
        )
    if found["status"] == "indexing":
        if not index_ready():
            request_scan()
        return Reply(
            say="I'm still reading your drives to learn where programs live, dear.",
            detail="Ask again in a minute. Start Menu programs work already: add app <name>", styled=True
        )
    if found["status"] != "ok":
        return None
    if not memory.get_setting("real_app_launching", False):
        top = found["candidates"][0]
        return Reply(say=f"I found {top['name']} at {top['path']}, but app launching is off.",
                     detail="Say 'enable app launching' and ask again.", styled=True)
    cands = found["candidates"]
    if len(cands) == 1 or cands[0]["score"] - cands[1]["score"] >= 10:
        return _ask(cands[0])
    memory.set_state_value("found_app_choices", cands)
    return Reply(say="I found a few, dear. Which one?",
                 detail="\n".join(f"- {c['name']}: {c['path']}" for c in cands),
                 actions=[button(c["name"], f"use found app {i}") for i, c in enumerate(cands, start=1)],
                 styled=True)
    
def choose(arg):
    choices = memory.get_state_value("found_app_choices") or []
    if not arg.isdigit() or not 1 <= int(arg) <= len(choices):
        return "That choice is no longer available. Ask me to open it again."
    memory.clear_state_value("found_app_choices")
    return _ask(choices[int(arg) - 1])

def _launch(pending):
    path = pending["path"]
    if not _fresh(pending):
        return "That offer expired, so I cancelled. Ask me again."
    if not os.path.isfile(path) or classify(path) == "blocked":
        return "That program is gone or no longer allowed, so I cancelled."
    st = os.stat(path)
    if (st.st_size, int(st.st_mtime)) != (pending["size"], int(pending["mtime"])):
        return "That file changed since I found it, so I cancelled."
    if not memory.get_setting("real_app_launching", False):
        return "App launching is off. Say 'enable app launching' first."
    result = tools.open_registered_app(pending["name"], {"command": f'"{path}"'}, True)
    from assistant import apps
    apps.log_app_launch(pending["name"], path, result)
    _usage["at"] = 0.0
    memory.set_state_value("last_found_app", pending)
    actions = []
    if pending["tier"] in ("trusted", "standard") and result.startswith("Opening"):
        actions = [button("Remember it", "remember found app", style="primary")]
    return Reply(say=result, actions=actions, styled=True)

def _confirmed(pending):
    if pending.get("strict"):
        memory.set_state_value("pending_found_app", pending)
        return Reply(say="That location needs a stronger yes, dear.",
                    detail=f"Type: allow opening {pending['name']}",
                    actions=[button("Allow opening " + pending["name"], f"allow opening {pending['name']}",
                    style="danger")], styled=True)
    return _launch(pending)

confirmable("pending_found_app", _confirmed, lambda p: f"Okay, I won't open {p['name']}.")

def approve(name):
    pending = memory.get_state_value("pending_found_app")
    if not pending:
        return "Nothing is waiting for approval."
    if clean_query(name) != pending["name"].lower():
        return f"That doesn't match what I'm holding: {pending['name']}."
    memory.clear_state_value("pending_found_app")
    return _launch(pending)

def remember():
    last = memory.get_state_value("last_found_app")
    if not last:
        return "I don't have a recently opened program to remember."
    if last["tier"] not in ("trusted", "standard"):
        return ("I don't remember programs from protected or download-type places, dear. "
                "Register it yourself: register app NAME as <path>")
    if memory.get_app_registry_entry(last["name"]):
        return f"{last['name']} is already registered. Use: update app {last['name']} as <path>"
    memory.add_app_registry_entry(last["name"], f'"{last["path"]}"')
    memory.set_app_allowed(last["name"], True)
    memory.clear_state_value("last_found_app")
    return f"Remembered. From now on 'open {last['name']}' opens it directly."

def status_text():
    rows = _rows()
    last = memory.get_state_value("exe_index_at")
    return "\n".join([
        "Program search:",
        f"Enabled: {S.get('app_search_enabled')}   protected places offered: {S.get('app_search_protected')}",
        f"Indexed programs: {len(rows)}",
        f"Scanning now: {'yes (' + str(status['found']) + ' so far)' if status['running'] else 'no'}",
        f"Last scan: {time.strftime('%Y-%m-%d %H:%M', time.localtime(last)) if last else 'not yet'}",
        f"Drives: {', '.join(fixed_drives()) or 'none'}",
    ])