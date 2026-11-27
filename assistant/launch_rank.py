import math
import re
import time

from rapidfuzz import fuzz

STOP = {"some", "a", "an", "any", "the", "my", "one", "that", "this", "something", "please", "of",
        "app", "apps", "program", "programs", "application"}
KIND_WORDS = {
    "game": {"game", "games", "gaming"},
    "browser": {"browser", "internet"},
    "media": {"music", "song", "songs", "player", "video"},
    "dev": {"editor", "ide", "terminal"},
    "chat": {"chat", "call", "meeting", "messenger"},
}
PATH_KINDS = (
    ("game", ("\\steamapps\\common\\", "\\epic games\\", "\\gog galaxy\\games\\", "\\riot games\\",
              "\\games\\", "\\xboxgames\\", "\\ea games\\", "\\origin games\\", "\\battle.net\\")),
)
NAME_KINDS = {
    "game": {"steam", "epicgameslauncher", "minecraft", "valorant", "roblox", "robloxplayerbeta"},
    "browser": {"chrome", "opera", "opera_gx", "firefox", "msedge", "brave", "vivaldi"},
    "dev": {"code", "cursor", "pycharm64", "idea64", "webstorm64", "sublime_text", "notepad++",
            "devenv", "windowsterminal", "wt"},
    "media": {"spotify", "vlc", "wmplayer", "itunes", "musicbee", "foobar2000"},
    "chat": {"discord", "telegram", "whatsapp", "slack", "teams", "zoom", "skype", "signal"},
}


def parse_target(text):
    kind, rest = None, []
    for tok in re.findall(r"[a-z0-9+]+", (text or "").lower()):
        if tok in STOP:
            continue
        hit = next((k for k, words in KIND_WORDS.items() if tok in words), None)
        if hit:
            kind = kind or hit
        else:
            rest.append(tok)
    return {"text": " ".join(rest), "kind": kind, "kind_only": bool(kind) and not rest}


def kind_of(path, name, known_games=()):
    n, low = name.lower(), path.lower()
    if n in known_games:
        return "game"
    for kind, parts in PATH_KINDS:
        if any(p in low for p in parts):
            return kind
    for kind, names in NAME_KINDS.items():
        if n in names:
            return kind
    return "app"


def _subsequence(q, name):
    if q[0] != name[0]:
        return False
    it = iter(name)
    return all(ch in it for ch in q)


def lexical(q, name, fuzzy=True):
    """How well the typed text matches a program name from 0-100"""
    if not q or not name:
        return 0.0
    if name == q:
        return 100.0
    words = [w for w in re.split(r"[\s_\-.]+", name) if w]
    if name.startswith(q):
        return 93.0 if len(q) >= 3 else 70.0
    if any(w.startswith(q) for w in words):
        return 88.0 if len(q) >= 3 else 60.0
    if len(q) >= 3 and q in name:
        return 80.0
    if len(q) >= 2 and len(words) >= 2 and "".join(w[0] for w in words).startswith(q):
        return 78.0
    best = 62.0 if len(q) >= 3 and _subsequence(q, name) else 0.0
    if fuzzy and len(q) >= 3:
        s = max(fuzz.WRatio(q, name), 0.9 * fuzz.partial_ratio(q, name) if len(q) >= 4 else 0.0)
        if s >= 75:
            best = max(best, min(84.0, s * 0.85))
    return best


def sem_score(sim, floor=0.30, span=0.40, cap=72.0):
    return max(0.0, min(1.0, (sim - floor) / span)) * cap


def usage_score(count, last_ts, now=None):
    if not count:
        return 0.0
    now = now or time.time()
    freq = min(1.0, math.log1p(count) / math.log1p(12))
    recency = 0.5 ** (max(0.0, now - last_ts) / 86400 / 30)
    return 100.0 * (0.7 * freq + 0.3 * recency)


def confidence(lex, sem, usage, kind_hit, kind_only=False):
    if kind_only:                                   
        return min(90.0, 30.0 + 0.6 * usage) if kind_hit else 0.0
    base = max(lex, sem)
    if base <= 0:
        return 0.0                                  
    return min(99.0, base + 0.10 * usage + (4.0 if kind_hit else 0.0))