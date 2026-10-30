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

