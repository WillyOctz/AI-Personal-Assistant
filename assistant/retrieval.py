import logging
import math
import re
import threading

import numpy as np

from assistant import database
from assistant.embeddings import create_content_hash
from assistant.llm import GEMINI_EMBEDDING_MODEL, get_gemini_embedding

log = logging.getLogger("nebula.retrieval")

_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was", "were",
         "it", "this", "that", "my", "me", "i", "you", "your", "about", "with", "do", "did", "what"}

def tokens(text):
    return [t for t in re.findall(r"\w+", (text or "").lower()) if t not in _STOP and len(t) > 1]

def bm25_scores(query_tokens, corpus, k1=1.4, b=0.75):
    """Okapi BM25 with the always-positive idf variant"""
    n_docs = len(corpus)
    
    if not n_docs:
        return []
     
    avg_len = sum(len(d) for d in corpus) / n_docs or 1.0
    df = {}
    
    for doc in corpus:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1
            
    scores = []
    
    for doc in corpus:
        tf = {}
        
        for term in doc:
            tf[term] = tf.get(term, 0) + 1
            
        score = 0.0
        
        for term in set(query_tokens):
            if term not in tf:
                continue
            
            idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            f = tf[term]
            score += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(doc) / avg_len))
            
        scores.append(score)
        
    return scores

def rrf(rankings, k=60):
    """Reciprocal rank fusion: ids that rank well in several lists win."""
    fused = {}
    
    for ranking in rankings:
        for pos, doc_id in enumerate(ranking):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + pos + 1)
            
    return sorted(fused, key=fused.get, reverse=True)

def hybrid_rank(query, docs, dense_scores, limit=3, min_dense=0.55):
    q = tokens(query)
    
    lexical = []
    
    if q and docs:
        corpus = [tokens(d["text"]) for d in docs]
        raw = bm25_scores(q, corpus)
        lexical = [docs[i]["id"] for i in np.argsort(-np.array(raw)) if raw[i] > 0]
        
    dense = [i for i, s in sorted(dense_scores.items(), key=lambda kv: -kv[1]) if s >= min_dense]
    by_id = {d["id"]: d for d in docs}
    out = []
    
    for doc_id in rrf([lexical[:10], dense[:10]])[:limit]:
        item = dict(by_id[doc_id])
        item["score"] = dense_scores.get(doc_id)
        out.append(item)
        
    return out


# ---------------Dense side : Gemini existing cache vectors as matrix--------------
_dense = {}
_dense_lock = threading.Lock()

def _matrix(source_type):
    sig = database.get_memory_embedding(source_type, GEMINI_EMBEDDING_MODEL)
    
    with _dense_lock:
        cached = _dense.get(source_type)
        
        if cached and cached["sig"] == sig:
            return cached
        
        rows = database.get_memory_embeddings(source_type, GEMINI_EMBEDDING_MODEL)
        M = np.array([r["vector"] for r in rows], dtype="float32") if rows else np.zeros((0, 0), "float32")
        
        if len(M):
            norms = np.linalg.norm(M, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            M = M / norms
            
        _dense[source_type] = {"sig": sig, "ids": [r["source_id"] for r in rows],
                               "hashes": [r["content_hash"] for r in rows], "M": M}
        
        return _dense[source_type]
    
def _dense_scores(source_type, docs, qvec):
    if qvec is None:
        return {}
    
    store = _matrix(source_type)
    
    if not store["ids"] or store["M"].shape[1] != qvec.shape[0]:
        return {}
    
    row_of = {sid: n for n, sid in enumerate(store["ids"])}
    scores = {}
    
    for doc in docs:
        n = row_of.get(doc["id"])
        
        if n is None or store["hashes"][n] != create_content_hash(doc["text"]):
            continue 
        
        scores[doc["id"]] = float(store["M"][n] @ qvec)
        
    return scores

def hybrid_context(query, note_limit=3, summary_limit=2, note_min=0.55, summary_min=0.55):
    clean = str(query or "").strip()
    
    if not clean:
        return {"ok": False, "notes": [], "summaries": [], "dense": False}
    
    qvec = None
    
    try:
        result = get_gemini_embedding(clean)
        
        if result["ok"]:
            qvec = np.array(result["vector"], dtype="float32")
            qvec = qvec / (np.linalg.norm(qvec) or 1.0)
    except Exception:
        log.exception("query embedding failed; lexical retrieval only")
        
    notes = [{"id": str(n["id"]), "text": n["text"]} for n in database.get_sqlite_notes()]
    summaries = [{"id": str(s["id"]), "text": s["summary"], "summary": s["summary"],
                  "timestamp": s["timestamp"]} for s in database.get_sqlite_conversation_summaries()]
    
    return {
        "ok": True,
        "dense": qvec is not None,
        "notes": hybrid_rank(clean, notes, _dense_scores("note", notes, qvec), note_limit, note_min),
        "summaries": hybrid_rank(clean, summaries, _dense_scores("conversation_summary", summaries, qvec),
                                 summary_limit, summary_min),
    }