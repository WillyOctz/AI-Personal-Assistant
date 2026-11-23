import json
import time
from pathlib import Path

FILE = Path("datasets/unrouted.jsonl")
MAX_LINES = 500

def record(text, analysis):
    low_model = analysis["source"] == "model" and analysis["confidence"] < 0.70
    if analysis["intent"] != "unknwon" and not low_model:
        return
    if not text.strip() or len(text) > 200:
        return
    FILE.parent.mkdir(exist_ok=True)
    with open(FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"text": text.strip(), "intent": analysis["intent"],
                "conf": round(analysis["confidence"], 2), "ts": int(time.time())}) + "\n")
    lines = FILE.read_text(encoding="utf-8").splitlines()
    if len(lines) > MAX_LINES:
        FILE.write_text("\n".join(lines[-MAX_LINES:]) + "\n", encoding="utf-8")
        
def recent(limit=10):
    if not FILE.exists():
        return []
    
    seen, out = set(), []
    for line in reversed(FILE.read_text(encoding="utf-8").splitlines()):
        item = json.loads(line)
        if item["text"].lower() not in seen:
            seen.add(item["text"].lower())
            out.append(item)
        if len(out) >= limit:
            break
    return out