import logging
import time

import numpy as np

from assistant import file_index, local_embed
from assistant.retrieval import rrf

log = logging.getLogger("nebula.filevec")

SNIPPET_CHARS = 500
_ready = False
_cache = {"sig": None, "ids": [], "X": np.zeros((0, 0), "float32")}

def _init():
    global _ready
    
    if _ready:
        return
    
    file_index.init_file_index()
    
    with file_index._db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS file_vec (
            file_id INTEGER PRIMARY KEY, mtime REAL NOT NULL, vec BLOB NOT NULL)"""
        )
        
    _ready = True
    
_PENDING = """FROM file_index f
    WHERE f.is_dir = 0 AND f.cloud = 0 AND f.indexed_mtime IS NOT NULL
      AND f.id IN (SELECT rowid FROM file_fts)
      AND NOT EXISTS (SELECT 1 FROM file_vec v WHERE v.file_id = f.id AND v.mtime >= f.mtime)"""
      
def index_vectors(should_stop=None, limit=400, time_budget=120):
    """Embed 'name + first 500 chars' of content-indexed files"""
    if not local_embed.available() or not file_index.FTS_OK:
        return {"indexed": 0, "remaining": 0}
    
    _init()
    deadline = time.time() + time_budget
    done = 0
    
    with file_index._db() as conn:
        conn.execute("DELETE FROM file_vec WHERE file_id NOT IN (SELECT id FROM file_index)")
        
    while done < limit and time.time() < deadline and not (should_stop and should_stop()):
        with file_index._db() as conn:
            rows = conn.execute(f"SELECT f.id, f.path, f.name, f.ext, f.mtime {_PENDING} LIMIT 32").fetchall()
            
            if not rows:
                break
            
            ids, texts, mtimes = [], [], []
            
            for row in rows:
                body = "" if file_index.SENSITIVE.search(row["name"]) else file_index._read_text(row["path"], row["ext"])
                snippet = " ".join(body.split())[:SNIPPET_CHARS]
                ids.append(row["id"])
                mtimes.append(row["mtime"])
                texts.append(f"{row['name']}. {snippet}")
                
            vectors = local_embed.embed(texts)
            
            conn.executemany(
                "INSERT OR REPLACE INTO file_vec (file_id, mtime, vec) VALUES (?, ?, ?)",
                [(i, m, v.astype("float32").tobytes()) for i, m, v in zip(ids, mtimes, vectors)],
            )
            done += len(rows)
            
    with file_index._db() as conn:
        remaining = conn.execute(f"SELECT COUNT(*) AS c {_PENDING}").fetchone()["c"]
        
    return {"indexed": done, "remaining": remaining}

def _matrix():
    _init()
    
    with file_index._db() as conn:
        sig = tuple(conn.execute("SELECT COUNT(*), COALESCE(SUM(mtime), 0) FROM file_vec").fetchone())
        
        if sig == _cache["sig"]:
            return _cache
        
        rows = conn.execute("SELECT file_id, vec FROM file_vec").fetchall()
        
    X = np.stack([np.frombuffer(r["vec"], dtype="float32") for r in rows]) if rows else np.zeros((0, 0), "float32")
    _cache.update(sig=sig, ids=[r["file_id"] for r in rows], X=X)
    return _cache

def search(query, limit=8, min_sim=0.35):
    if not local_embed.is_ready():
        return []
    
    store = _matrix()
    
    if not store["ids"]:
        return []
    
    sims = store["X"] @ local_embed.embed([query])[0]
    order = [i for i in np.argsort(-sims)[:limit] if sims[i] >= min_sim]
    
    if not order:
        return []
    
    ids = [store["ids"][i] for i in order]
    marks = ",".join("?" * len(ids))
    
    with file_index._db() as conn:
        rows = {r["id"]: dict(r) for r in conn.execute(
            f"SELECT id, root, path, name, is_dir, mtime FROM file_index WHERE id IN ({marks})", ids)}
        
    out = []
    
    for i in order:
        row = rows.get(store["ids"][i])
        
        if row:
            row["snip"] = f"similar ({sims[i]:.0%})"
            out.append(row)
            
    return out

def fuse(*row_lists, limit=8):
    """Merge name/FTS/semantic hits through path and Earlier lists win ties then FTS snippets are kept"""
    by_path, rankings = {}, []
    
    for rows in row_lists:
        rankings.append([r["path"] for r in rows])
        
        for r in rows:
            by_path.setdefault(r["path"], r)
            
    return [by_path[p] for p in rrf(rankings)[:limit]]
             
  