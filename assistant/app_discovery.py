import os
from pathlib import Path
from rapidfuzz import fuzz, process

SKIP = ("uninstall", "readme", "help", "manual", "documentation", "license", "website", "release notes", "changelog")

def start_menu_programs():
    roots = [Path(os.environ.get("ProgramData", "")) / "Microsoft/Windows/Start Menu/Programs",
             Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs"]
    found = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.lnk"):
            name = path.stem.lower()
            if not any(word in name for word in SKIP):
                found.setdefault(name, str(path))
    return found

def search(query, limit=5):
    programs = start_menu_programs()
    hits = process.extract(query.lower().strip(), list(programs), scorer=fuzz.WRatio, limit=limit, score_cutoff=70)
    return [(name, programs[name]) for name, _, _ in hits]