from assistant import convo_store, retrieval

def _items(summaries, limit):
    out = []
    for s in summaries:
        for i, line in enumerate(s["decisions"]):
            out.append({"id": f"{s['id']}:{i}", "text": line, "summary_id": s["id"], "when": s["timestamp"],
                        "origin": s["origin"], "topics": s["topics"], "kind": "decision"})
    return out[:limit] if limit else out

def find(topic, limit=4):
    topic = (topic or "").strip()
    sums = convo_store.summaries(kinds=("session", "manual", "decision"))
    
    if not topic:
        return {"items": _items(sums, limit), "live": [], "mode": "latest"}
    
    docs = _items(sums, None)
    ranked = retrieval.search("decision", topic, docs, limit=limit * 2) if docs else []
    mode = "decision"
    
    if not ranked:
        sdocs = [{"id": str(s["id"]), "text": s["summary"], "summary_id": s["id"], "when": s["timestamp"],
                  "origin": s["origin"], "topics": s["topics"], "kind": "mention"} for s in sums]
        ranked, mode = retrieval.search("conversation_summary", topic, sdocs, limit=limit), "mention"
        
    ranked = sorted(ranked[:limit], key=lambda r: r["when"], reverse=True)
    
    live_docs = [{"id": str(t["id"]), "text": f"{t['user']} {t['assistant'] or ''}", "when": t["timestamp"],
                  "user": t["user"]} for t in convo_store.recent_unsummarised(60)]
    
    live = retrieval.search("none", topic, live_docs, limit=2, use_dense=False) if live_docs else []
    return {"items": ranked, "live": live, "mode": mode}