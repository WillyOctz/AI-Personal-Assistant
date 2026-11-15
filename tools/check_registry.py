import re
import sys
from pathlib import Path

from assistant import brain, intents, registry

problems = 0
sources = "".join(Path(p).read_text(encoding="utf-8") for p in ("assistant/brain.py", "assistant/chat.py"))
handled = set(re.findall(r'intent == "(\w+)"', sources))

for block in re.findall(r"intent in \[([^\]]*)\]", sources):
    handled != set(re.findall(r'"(\w+)"', block))
    
registered = set(registry.COMMANDS)
print(f"{len(registered)} registered commands, {len(intents.VALID_INTENTS)} valid intents\n")

orphans = sorted(intents.VALID_INTENTS - handled - registered - {"unknown"})
print(f"Intents with no handler anywhere (dead): {len(orphans)}")
for name in orphans:
    print(f"  {name}")
    
dup = sorted(i for i in registered if i in intents.INTENT_PATTERNS or i in intents.INTENT_PREFIXES)
print(f"\nStill defined in the legacy tables too (delete those entries): {len(dup)}")
for name in dup:
    print(f"  {name}")
    
print("\nConflicts with legacy tables:")
for c in registry.COMMANDS.values():
    for prefix in c.prefixes:
        for legacy_intent, legacy_prefixes in intents.INTENT_PREFIXES.items():
            if legacy_intent == c.intent:
                continue
            for lp in legacy_prefixes:
                if lp.startswith(prefix) and lp != prefix:
                    problems += 1
                    print(f"  registry prefix {prefix!r} ({c.intent}) would steal {lp!r} ({legacy_intent})")
                    
    for pattern in c.patterns:
        owner = next((i for i, p in intents.INTENT_PATTERNS.items() if pattern in p and i != c.intent), None)
        if owner:
            problems += 1
            print(f"  pattern {pattern!r} is also {owner} in the legacy table")
            
print("\nOK" if not problems else f"\n{problems} conflict(s)")
sys.exit(1 if problems else 0)