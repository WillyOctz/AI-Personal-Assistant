import logging
import threading
from pathlib import Path

import numpy as np

from assistant import local_embed
from assistant.trainer import get_record_input, get_record_intent, read_jsonl_records

log = logging.getLogger("nebula.intent")

TRAIN_FILES = [
    Path("datasets/examples.jsonl"),
    Path("datasets/feedback.jsonl"),
    Path("datasets/intent_seed.jsonl"),
]
TRAIN_GLOB = "train_*.jsonl"
INDEX_FILE = Path("db/intent_index.npz")

K = 5
MIN_SIM = 0.50  # tune with python -m tools.eval_intent
MAX_WORDS = 14  # the longer, for messages. shorter mean for commands

ROUTABLE = {
    "greeting", "get_time", "play_music", "play_game", "open_app", "set_reminder",
    "show_reminders", "today_reminders", "tomorrow_reminders", "overdue_reminders",
    "daily_briefing", "suggest_next_task", "start_focus", "stop_focus", "focus_status",
    "today_focus_stats", "focus_dashboard", "show_projects", "resume_project",
    "activity_recap", "show_notes", "reindex_files", "companion_status",
    "chat_how_are_you", "chat_need_help", "chat_stuck", "chat_thanks", "chat_goodbye",
    "chat_day_greeting", "chat_capabilities", "chat_identity", "chat_about_user",
    "chat_response_helpful", "chat_response_not_helpful", "chat_explain_last",
    "chat_repeat_last",
}

_state = {"sig": None, "X": None, "labels": [], "texts": []}
_lock = threading.RLock()

def _norm(text):
    return " ".join(str(text or "").lower().split()).strip(" ?!.,")

def _source_paths():
    paths = list(TRAIN_FILES) + sorted(Path("datasets").glob(TRAIN_GLOB))
    return [p for p in paths if p.exists()]

def _signature():
    sig = []
    
    for path in _source_paths():
        stat = path.stat()
        sig.append((str(path), stat.st_mtime_ns, stat.st_size))
        
    return (local_embed.MODEL_NAME, tuple(sig))

def load_pairs():
    """A text with two different labels is dropped, never guessed."""
    
    seen = {}
    
    for path in _source_paths():
        for record in read_jsonl_records(path):
            text, intent = get_record_input(record), get_record_intent(record)
            
            if not text or not intent:
                continue
            
            key = _norm(text)
            
            if not key:
                continue
            
            entry = seen.setdefault(key, {"text": str(text).strip(), "intents": set()})
            entry["intents"].add(str(intent).strip())
            
    pairs, conflicts = [], []
    
    for key, entry in seen.items():
        if len(entry["intents"]) > 1:
            conflicts.append((key, sorted(entry["intents"])))
            continue
        
        intent = next(iter(entry["intents"]))
        
        if intent == "unknown" or intent in ROUTABLE:
            pairs.append((entry["text"], intent))
            
        # any other label is handled by rules or prefixes
        
    return pairs, conflicts

def _ensure_index():
    sig = _signature()
    
    with _lock:
        if _state["sig"] == sig and _state["X"] is not None:
            return True
        
        pairs, conflicts = load_pairs()
        
        for key, intents in conflicts:
            log.warning("Intent dataset conflict dropped: %r -> %s", key, intents)
            
        if not pairs:
            _state.update(sig=sig, X=None, labels=[], texts=[])
            return False
        
        texts = [t for t, _ in pairs]
        X = local_embed.embed_cached(texts, INDEX_FILE)
        _state.update(sig=sig, X=X, labels=[i for _, i in pairs], texts=texts)
        return True
    
def decide(sims, labels, k=K, min_sim=MIN_SIM):
    """Just pure voting logic without model interfering"""
    if len(labels) == 0:
        return None, 0.0, {}
    
    order = np.argsort(-sims)[:k]
    
    if float(sims[order[0]]) < min_sim:
        return None, 0.0, {}
    
    scores = {}
    
    for i in order:
        if sims[i] >= min_sim:
            scores[labels[i]] = scores.get(labels[i], 0.0) + float(sims[i])
            
    top = max(scores, key=scores.get)
    
    if top == "unknown":
        return None, 0.0, scores
    
    share = scores[top] / sum(scores.values())
    best = max(float(sims[i]) for i in order if labels[i] == top and sims[i] >= min_sim)
    return top, 0.5 * best + 0.5 * share, scores

def predict(user_input):
    if not local_embed.is_ready() or _state["X"] is None:
        return None
    
    if len(str(user_input).split()) > MAX_WORDS:
        return None, 0.0, {}
    
    try:
        _ensure_index()
        query = local_embed.embed([user_input])[0]
        
        with _lock:
            X, labels = _state["X"], list(_state["labels"])
            
        return decide(X @ query, labels)
    except Exception:
        log.exception("intent model failed")
        return None
    
def warm_up():
    """Load up model and build index off from main thread"""
    def work():
        try:
            local_embed.warm()
            
            if local_embed.is_ready():
                _ensure_index()
        except Exception:
            log.exception("intent warm-up failed")
            
    threading.Thread(target=work, daemon=True, name="intent-warmup").start()
