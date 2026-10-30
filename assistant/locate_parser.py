import re

_LEAD = (
    r"^(?:(?:hey|hi|hello|please)[,\s]+)?"
    r"(?:(?:nebula|mommy|mom|mama)[,\s]+)?"
    r"(?:please\s+)?"
)
_ART = r"(?:(?:my|the|a|an|that|our|some)\s+)?"

# Checked first: "where did I write about X" means content search
CONTENT_PATTERNS = [
    rf"{_LEAD}where\s+did\s+i\s+(?:write|wrote|mention|note|jot|talk|read|see)\s+"
    rf"(?:down\s+)?(?:about\s+)?{_ART}(?P<q>.+)$",
    rf"{_LEAD}(?:find\s+text|search\s+content|content\s+search|find\s+in\s+files)\s+"
    rf"(?:(?:about|for)\s+)?(?P<q>.+)$",
]

NAME_PATTERNS = [
    
    # "where is my thesis" / "where's the budget" ("where was I / are we / is you" are excluded)
    rf"{_LEAD}where(?:'s|\s+is|\s+are|\s+was|\s+were)\s+(?!i\b|you\b|we\b){_ART}(?P<q>.+)$",
    rf"{_LEAD}where\s+did\s+i\s+(?:put|save|leave|store|keep|download)\s+{_ART}(?P<q>.+)$",
    
    # "find my ..." only; plain "find files / find app / find reminder" stay separate commands
    rf"{_LEAD}(?:find|locate|look\s+for)\s+(?:me\s+)?(?:my|our)\s+(?P<q>.+)$",
    rf"{_LEAD}locate\s+{_ART}(?P<q>.+)$",
]

_FILLER = re.compile(r"\b(?:please|for me|again|right now|now|thanks)\b", re.I)
MAX_WORDS = 8

def _clean(q):
    q = _FILLER.sub(" ", q)
    return re.sub(r"\s+", " ", q).strip(" ?!.,;:'\"")

def parse_locate_query(text):
    raw = {text or ""}.strip()
    
    if not raw:
        return None
    
    for kind, patterns in (("content", CONTENT_PATTERNS), ("name", NAME_PATTERNS)):
        for pattern in patterns:
            match = re.match(pattern, raw, re.I)
            
            if not match:
                continue
            
            query = _clean(match.group("q"))
            
            if not query or len(query.split()) > MAX_WORDS:
                continue
            
            personal = bool(re.search(r"\b(my|our|did i)\b", raw, re.I))
            return {"kind": kind, "query": query, "personal": personal}
        
    return None


#---------------------query -> token filter----------------------
_IMG = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")

EXT_WORDS = {
    "pdf": (".pdf",),
    "doc": (".doc", ".docx"), "docx": (".docx",),
    "excel": (".xls", ".xlsx", ".xlsm"), "xlsx": (".xlsx",),
    "spreadsheet": (".xls", ".xlsx", ".csv"), "csv": (".csv",),
    "ppt": (".ppt", ".pptx"), "pptx": (".pptx",), "powerpoint": (".ppt", ".pptx"),
    "slides": (".ppt", ".pptx"), "presentation": (".ppt", ".pptx"),
    "txt": (".txt",), "md": (".md",), "markdown": (".md",), "json": (".json",),
    "python": (".py",), "py": (".py",), "js": (".js",),
    "image": _IMG, "picture": _IMG, "photo": _IMG, "screenshot": (".png", ".jpg", ".jpeg"),
    "png": (".png",), "jpg": (".jpg", ".jpeg"),
    "video": (".mp4", ".mkv", ".mov", ".avi"),
    "music": (".mp3", ".wav", ".flac"),
    "zip": (".zip", ".rar", ".7z"),
}
ALL_EXTS = {ext for group in EXT_WORDS.values() for ext in group}

TYPE_WORDS = {
    "folder": "folder", "folders": "folder", "directory": "folder", "dir": "folder",
    "project": "project", "projects": "project",
    "file": "file", "files": "file",
}
RECENT_WORDS = {"recent", "latest", "last", "newest"}
STOP = {
    "my", "the", "a", "an", "that", "this", "called", "named", "one", "for", "of",
    "in", "on", "at", "to", "i", "it", "from", "about", "our", "some",
}


def parse_name_query(query):
    exts, tokens, kind, recent = [], [], None, False
    
    for tok in re.findall(r"[\w.\-]+", (query or "").lower()):
        tok = tok.strip(".-")
        
        if not tok:
            continue
        
        if tok in RECENT_WORDS:
            recent = True
            continue
        
        if tok in TYPE_WORDS:
            kind = kind or TYPE_WORDS[tok]
            continue
        
        base = tok[:-1] if tok.endswith("s") and tok[:-1] in EXT_WORDS else tok
        
        if base in EXT_WORDS:
            exts.extend(EXT_WORDS[base])
            continue
        
        if "." in tok:
            stem, _, suffix = tok.rpartition(".")
            
            if stem and f".{suffix}" in ALL_EXTS:
                exts.append(f".{suffix}")
                tok = stem
                
        if tok in STOP:
            continue
        
        tokens.append(tok)
        
    return {
        "tokens": tokens,
        "exts": tuple(dict.fromkeys(exts)),
        "kind": kind,
        "recent": recent,
    }
