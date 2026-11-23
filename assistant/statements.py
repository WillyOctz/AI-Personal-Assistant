import re
import time

from assistant import memory

POSITIVE = {"fine", "good", "great", "well", "okay", "ok", "alright", "happy", "excited", "fantastic", "awesome",
            "amazing", "better", "calm", "relaxed", "motivated", "focused", "productive", "energetic",
            "proud", "grateful", "hopeful", "content"}
NEGATIVE = {"tired", "exhausted", "sleepy", "stressed", "anxious", "sad", "bored", "angry", "frustrated",
            "upset", "worried", "nervous", "lonely", "overwhelmed", "confused", "unmotivated", "drained",
            "sick", "annoyed", "depressed"}
MOODS = POSITIVE | NEGATIVE
SAFE = {"so", "very", "really", "quite", "pretty", "a", "bit", "little", "kinda", "kind", "of", "sort",
        "somewhat", "extremely", "just", "still", "today", "now", "right",          # intensifiers / time
        "thank", "thanks", "thx", "ty", "you", "u", "how", "are", "about", "what", "hbu", "wbu",  # politeness
        "and", "but", "too"}
NOT_NAMES = {"sorry", "back", "here", "home", "ready", "done", "busy", "late", "new", "online", "free",
             "hungry", "thirsty", "there", "sure", "also", "single", "student", "developer", "engineer"}

_ASKED_BACK = re.compile(r"\b(and you|and u|how about you|what about you|how are you|hbu|wbu)\b")
_START = re.compile(r"^i\s+(am(?:\s+feeling)?|feel)\s+(.+)$")

def _normalise(text):
    t = text.lower().replace("'", "'").strip()
    return re.sub(r"\bi'?m\b", "i am", t)

def classify(text):
    """classify subjective statements for ex.: kind -> mood or personality or maybe name or species"""
    t = _normalise(text)
    m = _START.match(t)
    
    if not m:
        return None
    
    verb, rest = m.group(1), m.group(2)
    tokens = re.findall(r"[a-z]+", rest)
    if not tokens:
        return None
    
    moods = [w for w in tokens if w in MOODS]
    if moods and all(w in MOODS or w in SAFE for w in tokens):
        unique = list(dict.fromkeys(moods))[:2]
        return {"kind": "mood", "mood": " and ".join(unique),
                "polarity": "negative" if any(w in NEGATIVE for w in unique) else "positive",
                "asked_back": bool(_ASKED_BACK.search(rest))}
        
    word = tokens[0]
    if (verb == "am" and len(tokens) == 1 and len(word) >= 2 and word not in NOT_NAMES and not word.endswith("ing") and re.fullmatch(r"[a-z]+", rest.strip(" ,.!"))):
        return {"kind": "maybe_name", "name": word.title()}
    return None

def save_mood(mood):
    memory.set_profile_value("mood", mood)
    memory.set_state_value("mood_at", time.time())
    
def current_mood(max_hours=8):
    mood, at = memory.get_profile_value("mood"), memory.get_state_value("mood_at")
    if not mood or not at or time.time() - at > max_hours * 3600:
        return None
    return mood

