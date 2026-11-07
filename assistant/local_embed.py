import logging
import os
import threading
from pathlib import Path

import numpy as np

log = logging.getLogger("nebula.embed")

MODEL_NAME = os.getenv("NEBULA_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CACHE_DIR = Path("db/models")

_model = None
_failed = False
_lock = threading.RLock()

def _load():
    global _model, _failed
    
    with _lock:
        if _model is not None or _failed:
            return
        
        try:
            from fastembed import TextEmbedding
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _model = TextEmbedding(MODEL_NAME, cache_dir=str(CACHE_DIR))
            log.info("Embedding model ready: %s", MODEL_NAME)
        except Exception:
            log.exception("Local embedding model unavailable; falling back to old behaviour")
            _failed = True
            
def warm():
    _load()
    
def is_ready():
    return _model is not None

def available():
    return not _failed

def embed(texts):
    """float32 matrix, one L2-normalised row per text."""
    texts = [str(t) for t in texts]
    
    if not texts:
        return np.zeros((0, 0), dtype="float32")
    
    with _lock:
        _load()
        
        if _model is None:
            raise RuntimeError("local embedding model unavailable")
        
        vectors = np.array(list(_model.embed(texts)), dtype="float32")
        
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms

def embed_cached(texts, cache_file):
    """Embed cache using re-vectors. new ones will takes time"""
    cache_file = Path(cache_file)
    cached = {}
    
    if cache_file.exists():
        try:
            data = np.load(cache_file, allow_pickle=False)
            
            if str(data["model"]) == MODEL_NAME:
                cached = dict(zip(data["texts"].tolist(), data["X"]))
        except Exception:
            log.exception("embedding cache unreadable; rebuilding %s", cache_file)
            
    missing = [t for t in dict.fromkeys(texts) if t not in cached]
    
    if missing:
        cached.update(zip(missing, embed(missing)))
        
    X = np.stack([cached[t] for t in texts]) if texts else np.zeros((0, 0), dtype="float32")
    
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache_file, X=X, texts=np.array(texts), model=np.array(MODEL_NAME))
    
    return X
    
    