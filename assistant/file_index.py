import html
import json
import os
import re
import sqlite3
import threading
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

from rapidfuzz import fuzz, process

from assistant.database import get_connection
from assistant.locate_parser import parse_name_query
from assistant.tools import IGNORED_FILE_FOLDERS, TEXT_EXTENSIONS

#------------Initial---------------------
MAX_ITEMS_PER_ROOT = 300_000
MAX_DEPTH = 14
MAX_CONTENT_BYTES = 2_000_000
MAX_CONTENT_CHARS = 200_000
MIN_MATCH = 62                      # rapidfuzz score floor (0-100)
SYNONYMS_FILE = Path("datasets/locate_synonyms.json")

INDEX_IGNORED = {n.lower() for n in IGNORED_FILE_FOLDERS} | {
    "dist", "build", "target", "bin", "obj", "site-packages", "$recycle.bin",
    "system volume information", "appdata", "windows", "program files",
    "program files (x86)", "programdata", "__macosx", ".gradle",
}

PROJECT_MARKERS = (
    ".git", "pyproject.toml", "package.json", "cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "requirements.txt", "setup.py", "cmakelists.txt",
    "composer.json", "gemfile", "pubspec.yaml", "project.godot",
)
PROJECT_SUFFIXES = (".sln", ".csproj", ".uproject")

CONTENT_EXTS = set(TEXT_EXTENSIONS) | {
    ".docx", ".rst", ".tex", ".yaml", ".yml", ".toml", ".ini", ".xml",
}
try:
    import pypdf                  
    CONTENT_EXTS.add(".pdf")
except ImportError:
    pypdf = None

SENSITIVE = re.compile(
    r"(secret|password|passwd|credential|token|id_rsa|\.env|private[_-]?key|\.pem|\.key|wallet|seed)",
    re.I,
)

_REPARSE = 0x400                    # junction / symlink / OneDrive placeholder
_CLOUD = 0x400000 | 0x40000 | 0x1000   # recall-on-access / recall-on-open

FTS_OK = False
_init_done = False
_init_lock = threading.Lock()

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS file_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        root TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        ext TEXT NOT NULL DEFAULT '',
        is_dir INTEGER NOT NULL,
        size INTEGER NOT NULL DEFAULT 0,
        mtime REAL NOT NULL DEFAULT 0,
        seen REAL NOT NULL DEFAULT 0,
        cloud INTEGER NOT NULL DEFAULT 0,
        indexed_mtime REAL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_file_index_root ON file_index (root, seen)",
    "CREATE INDEX IF NOT EXISTS idx_file_index_mtime ON file_index (mtime)",
    """CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        root TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        marker TEXT NOT NULL DEFAULT '',
        last_activity REAL NOT NULL DEFAULT 0,
        last_opened REAL,
        note TEXT NOT NULL DEFAULT '',
        seen REAL NOT NULL DEFAULT 0
    )""",
]

UPSERT_FILE = """
INSERT INTO file_index (root, path, name, ext, is_dir, size, mtime, seen, cloud)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(path) DO UPDATE SET
    root = excluded.root, name = excluded.name, ext = excluded.ext,
    is_dir = excluded.is_dir, size = excluded.size, mtime = excluded.mtime,
    seen = excluded.seen, cloud = excluded.cloud
"""

UPSERT_PROJECT = """
INSERT INTO projects (root, path, name, marker, last_activity, seen)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(path) DO UPDATE SET
    root = excluded.root, name = excluded.name, marker = excluded.marker,
    last_activity = excluded.last_activity, seen = excluded.seen
"""

@contextmanager
def _db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
        
def init_file_index():
    global _init_done, FTS_OK
    
    if _init_done:
        return
    
    with _init_lock:
        if _init_done:
            return
        
        with _db() as conn:
            for statement in SCHEMA:
                conn.execute(statement)
                
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5("
                    "content, tokenize='unicode61 remove_diacritics 2')"
                )
                FTS_OK = True
            except sqlite3.OperationalError:
                FTS_OK = False
                
        _init_done = True
        

#--------------------Scanning--------------------------
def _ignored_dir(low):
    return low in INDEX_IGNORED or low.startswith(".") or low.endswith(".egg-info")

def _find_marker(names):
    for marker in PROJECT_MARKERS:
        if marker in names:
            return marker
        
    for name in names:
        if name.endswith(PROJECT_SUFFIXES):
            return name
        
    return None

def _is_real_dir(path):
    try:
        return os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.abspath(path))
    except OSError:
        return False
    
def scan_root(root_name, root_path, should_stop=None):
    init_file_index()
    root = os.path.abspath(str(root_path))
    
    if not os.path.isdir(root):
        return {"ok": False, "reason": "not_a_folder", "items": 0, "projects": 0}
    
    started = time.time()
    batch, projects = [], {}
    items = 0
    stopped = truncated = False
    stack = [(root, None, 0)]
    
    conn = get_connection()
    try:
        def flush():
            if batch:
                conn.executemany(UPSERT_FILE, batch)
                conn.commit()
                batch.clear()
                
        while stack:
            if should_stop and should_stop():
                stopped = True
                break
            
            current, project, depth = stack.pop()
            
            try:
                with os.scandir(current) as iterator:
                    entries = list(iterator)
            except OSError:
                continue
            
            marker = _find_marker({entry.name.lower} for entry in entries)
            
            if marker:
                project = current
                projects[current] = {"marker": marker, "newest": 0.0}
                
            for entry in entries:
                name = entry.name
                low = name.lower()
                
                if low.startswith("~$"):
                    continue
                
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                
                attrs = getattr(stat, "st_file_attributes", 0)
                
                if is_dir:
                    if _ignored_dir(low):
                        continue
                    
                    if attrs & _REPARSE and not _is_real_dir(entry.path):
                        continue
                    
                    if depth < MAX_DEPTH:
                        stack.append((entry.path, project, depth + 1))
                        
                    size, cloud, ext = 0, 0, ""
                    
                else:
                    size = stat.st_size
                    cloud = 1 if attrs & _CLOUD else 0
                    ext = os.path.splitext(name)[1].lower()
                    
                    if project:
                        info = projects[project]
                        info["newest"] = max(info["newest"], stat.st_mtime)
                        
                batch.append((root_name, entry.path, name, ext, int(is_dir), size, stat.st_mtime, started, cloud))
                items += 1
                
            if len(batch) >= 200:
                flush()
                
            if items >= MAX_ITEMS_PER_ROOT:
                truncated = True
                break
        
        flush()
        
        if not stopped:
            for path, info in projects.items():
                last_activity = info["newest"]
                
                if not last_activity:
                    try:
                        last_activity = os.stat(path).st_mtime
                    except OSError:
                        last_activity = 0
                        
                conn.execute(UPSERT_PROJECT, (
                    root_name, path, os.path.basename(path) or path, info["marker"], last_activity, started,
                ))
                
                if FTS_OK:
                    conn.execute(
                        "DELETE FROM file_fts WHERE rowid IN "
                        "(SELECT id FROM file_index WHERE root = ? AND seen < ?)",
                        (root_name, started),
                    )
                    
                conn.execute("DELETE FROM file_index WHERE root = ? AND seen < ?", (root_name, started))
                conn.execute("DELETE FROM projects WHERE root = ? AND seen < ?", (root_name, started))
                conn.commit()
                
    finally:
        conn.close()
        
    invalidate_cache()
    
    return {
        "ok": True, "items": items, "projects": len(projects),
        "stopped": stopped, "truncated": truncated,
    }
    
def prune_roots(valid_roots):
    init_file_index()
    valid = set(valid_roots)
    
    with _db() as conn:
        known = {r["root"] for r in conn.execute("SELECT DISTINCT root FROM file_index")}
        known |= {r["root"] for r in conn.execute("SELECT DISTINCT root FROM projects")}
        
        for root in known - valid:
            if FTS_OK:
                conn.execute(
                    "DELETE FROM file_fts WHERE rowid IN (SELECT id FROM file_index WHERE root = ?)",
                    (root,),
                )
            conn.execute("DELETE FROM file_index WHERE root = ?", (root,))
            conn.execute("DELETE FROM projects WHERE root = ?", (root,))
            
    invalidate_cache()
    
    
#---------------------------------Content Indexing--------------------------------
def _read_docx(path):
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", "ignore")
        
    xml = re.sub(r"</w:p>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", " ", xml))

def _read_pdf(path):
    reader = pypdf.PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages[:20])

def _read_text(path, ext):
    try:
        if ext == ".docx":
            text = _read_docx(path)
        elif ext == ".pdf" and pypdf:
            text = _read_pdf(path)
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                text = file.read(MAX_CONTENT_CHARS)
                
    except Exception:
        return ""
    
    return text[:MAX_CONTENT_CHARS]

def index_contents(should_stop=None, time_budget=300):
    """Read new/changed files into FTS. Returns how many were done and how many remain."""
    init_file_index()
    
    if not FTS_OK:
        return {"indexed": 0, "remaining": 0}
    
    placeholders = ",".join("?" * len(CONTENT_EXTS))
    where = (
        f"is_dir = 0 AND cloud = 0 AND size <= ? AND ext IN ({placeholders}) "
        "AND (indexed_mtime IS NULL OR indexed_mtime < mtime)"
    )
    params = (MAX_CONTENT_BYTES, *sorted(CONTENT_EXTS))
    deadline = time.time() + time_budget
    done = 0
    
    while time.time() < deadline and not (should_stop and should_stop()):
        with _db() as conn:
            rows = conn.execute(
                f"SELECT id, path, name, ext, mtime FROM file_index WHERE {where} LIMIT 300",
                params,
            ).fetchall()
            
            if not rows:
                break
            
            for row in rows:
                text = "" if SENSITIVE.search(row["name"]) else _read_text(row["path"])
                
                conn.execute("DELETE FROM file_fts WHERE rowid = ?", (row["id"],))
                
                if text.strip():
                    conn.execute(
                        "INSERT INTO file_fts (rowid, content) VALUES (?, ?)",
                        (row["id"], text),
                    )
                    
                # mark as processed even when empty/unreadable
                conn.execute(
                    "UPDATE file_index SET indexed_mtime = ? WHERE id = ?",
                    (row["mtime"], row["id"]),
                )
                done += 1
                
    with _db() as conn:
        remaining = conn.execute(
            f"SELECT COUNT(*) AS c FROM file_index WHERE {where}", params
        ).fetchone()["c"]
        
    return {"indexed": done, "remaining": remaining}


_STOP_FTS = {"the", "a", "an", "about", "of", "in", "on", "my", "and", "or", "to", "for", "is"}

def search_content(query, limit=8):
    init_file_index()
    
    if not FTS_OK:
        return []
    
    tokens = [t for t in re.findall(r"\w+", (query or "").lower()) if t not in _STOP_FTS]
    
    if not tokens:
        return []
    
    match = " ".join(f'"{t}"' for t in tokens[:-1])
    last = f'"{tokens[-1]}"*'
    match = f"{match} {last}".strip()
    
    try:
        with _db() as conn:
            rows = conn.execute(
                """SELECT f.root, f.path, f.name, f.is_dir, f.mtime,
                          snippet(file_fts, 0, '[', ']', '…', 14) AS snip
                   FROM file_fts JOIN file_index f ON f.id = file_fts.rowid
                   WHERE file_fts MATCH ? ORDER BY rank LIMIT ?""",
                   (match, limit),
            ).fetchall()
            
    except sqlite3.OperationalError:
        return []
    
    return [dict(row) for row in rows]

# ----------------------------------Name Search (RAM cache + rapidfuzz)-------------------------
_cache = {"items": [], "keys": [], "projects": {}, "dirty": True}
_cache_lock = threading.Lock()

def invalidate_cache():
    _cache["dirty"] = True
    
def _ensure_cache():
    if not _cache["dirty"]:
        return
    
    init_file_index()
    
    with _db() as conn:
        rows = conn.execute(
            "SELECT root, path, name, ext, is_dir, mtime FROM file_index"
        ).fetchall()
        project_ids = {r["path"]: r["id"] for r in conn.execute("SELECT id, path FROM projects")}
        
    items, keys = [], []
    
    for row in rows:
        parent = os.path.dirname(row["path"])
        near = os.path.basename(parent)
        far = os.path.basename(os.path.dirname(parent))
        
        keys.append(f"{row['name']} {near} {far}".lower())
        items.append((row["root"], row["path"], row["name"], row["ext"], row["is_dir"], row["mtime"]))
        
    with _cache_lock:
        _cache.update(items=items, keys=keys, projects=project_ids, dirty=False)
        

_syn_cache = {"mtime": None, "map": {}}

def _synonyms():
    """This will be using the datasets: datasets/locate_synonym.json"""
    try:
        mtime = SYNONYMS_FILE.stat().st_mtime
    except OSError:
        return {}
    
    if _syn_cache["mtime"] == mtime:
        return _syn_cache["map"]
    
    try:
        raw = json.loads(SYNONYMS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    
    mapping = {}
    
    for key, alts in raw.items():
        for alt in alts:
            mapping.setdefault(key.lower(), []).append(alt.lower())
            
            if " " not in alt:
                mapping.setdefault(alt.lower(), []).append(key.lower())
                
    _syn_cache.update(mtime=mtime, map=mapping)
    return mapping

def _variants(tokens):
    syn, variants = _synonyms(), [tokens]
    
    for i, token in enumerate(tokens):
        for alt in syn.get(token, []):
            variants.append(tokens[:i] + alt.split() + tokens[i + 1:])
            
    return variants[:5]

def find(query, limit=8):
    """fuzzy search by names, recent files, project root and word-hits"""
    spec = parse_name_query(query)
    _ensure_cache()
    
    with _cache_lock:
        items, keys, projects = _cache["items"], _cache["keys"], _cache["projects"]
        
    def passes(item):
        _, path, _, ext, is_dir = item
        
        if spec["kind"] == "folder" and not is_dir:
            return False
        if spec["kind"] == "file" and is_dir:
            return False
        if spec["kind"] == "project" and path not in projects:
            return False
        if spec["exts"] and ext not in spec["exts"]:
            return False
        return True
    
    idx = [i for i, item in enumerate(items) if passes(item)]
    
    if not spec["tokens"]:
        if not (spec["exts"] or spec["kind"]):
            return []
        
        idx.sort(key=lambda i: items[i][5], reverse=True)
        picked = {i: 60.0 for i in idx[:limit]}
    else:
        choices = [keys[i] for i in idx]
        picked = {}
        
        for tokens in _variants(spec["tokens"]):
            text = " ".join(tokens)
            
            for _, score, pos in process.extract(
                text, choices, scorer=fuzz.WRatio, limit=limit * 5, score_cutoff=MIN_MATCH
            ):
                i = idx[pos]
                picked[i] = max(picked.get(i, 0), score)
                
    now = time.time()
    recency_weight = 30 if spec["recent"] else 10
    text = " ".join(spec["tokens"])
    ranked = []
    
    for i, match in picked.items():
        root, path, name, ext, is_dir, mtime = items[i]
        bonus = 0.0
        
        if spec["tokens"] and all(t in keys[i] for t in spec["tokens"]):
            bonus += 12
            
        if os.path.splitext(name)[0].lower() == text:
            bonus += 15
            
        age_days = max(0.0, (now - mtime) / 86400)
        bonus += recency_weight * 0.5 ** (age_days / 45)
        
        if path in projects:
            bonus += 4
            
        ranked.append(
            {
                "root": root, "path": path, "name": name, "is_dir": is_dir, "mtime": mtime,
                "match": match, "score": match + bonus, "project_id": projects.get(path),
            }
        )
        
    ranked.sort(key=lambda row: row["score"], reverse=True)
    return ranked[:limit]


#------------------------------Projects-----------------------------
_RECENT_SQL = "ORDER BY MAX(last_activity, COALESCE(last_opened, 0)) DESC"

def list_projects(limit=8):
    init_file_index()
    
    with _db() as conn:
        rows = conn.execute(f"SELECT * FROM projects {_RECENT_SQL} LIMIT ?", (limit,)).fetchall()
        
    return [dict(row) for row in rows]

def recent_projects(limit=5):
    return [{"id": p["id"], "name": p["name"]} for p in list_projects]

def get_project(project_id):
    init_file_index()

    with _db() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (int(project_id),)).fetchone()

    return dict(row) if row else None


def last_project():
    projects = list_projects(1)
    return projects[0] if projects else None


def find_project(name):
    projects = list_projects(500)
    low = (name or "").lower().strip()

    if not low or not projects:
        return None

    for project in projects:
        if project["name"].lower() == low:
            return project

    hit = process.extractOne(low, [p["name"].lower() for p in projects],
                             scorer=fuzz.WRatio, score_cutoff=65)

    return projects[hit[2]] if hit else None


def is_known_project(path):
    init_file_index()

    with _db() as conn:
        return conn.execute("SELECT 1 FROM projects WHERE path = ?", (path,)).fetchone() is not None


def mark_project_opened(path):
    with _db() as conn:
        conn.execute("UPDATE projects SET last_opened = ? WHERE path = ?", (time.time(), path))


def set_project_note(path, note):
    """Used by the 'handoff note' feature in the next phase."""
    with _db() as conn:
        conn.execute("UPDATE projects SET note = ? WHERE path = ?", (note, path))


def project_recent_files(path, limit=5):
    init_file_index()
    prefix = path.rstrip("\\/") + os.sep

    with _db() as conn:
        rows = conn.execute(
            """SELECT root, path, name, mtime FROM file_index
               WHERE is_dir = 0 AND substr(path, 1, ?) = ?
               ORDER BY mtime DESC LIMIT ?""",
            (len(prefix), prefix, limit),
        ).fetchall()

    return [dict(row) for row in rows]

# ---------------------Status/Helpers---------------------------
def stats():
    init_file_index()
    
    with _db() as conn:
        def count(sql):
            return conn.execute(sql).fetchone()["c"]
        
        return {
            "files": count("SELECT COUNT(*) AS c FROM file_index WHERE is_dir = 0"),
            "folders": count("SELECT COUNT(*) AS c FROM file_index WHERE is_dir = 1"),
            "projects": count("SELECT COUNT(*) AS c FROM projects"),
            "content_done": count(
                "SELECT COUNT(*) AS c FROM file_index WHERE is_dir = 0 AND indexed_mtime IS NOT NULL"
            ),
            "roots": [r["root"] for r in conn.execute("SELECT DISTINCT root FROM file_index")],
            "fts": FTS_OK,
        }
        
def humanize_age(ts):
    if not ts:
        return "never"
    
    seconds = max(0, time.time() - ts)

    if seconds < 90:
        return "just now"

    minutes = seconds / 60

    if minutes < 60:
        return f"{int(minutes)} min ago"

    hours = minutes / 60

    if hours < 24:
        n = int(hours)
        return f"{n} hour{'s' if n != 1 else ''} ago"

    days = hours / 24

    if days < 14:
        n = int(days)
        return f"{n} day{'s' if n != 1 else ''} ago"

    if days < 60:
        return f"{int(days / 7)} weeks ago"

    return f"{int(days / 30)} months ago"
    
    