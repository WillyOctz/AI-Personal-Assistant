import argparse
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from assistant import intent_model, local_embed, trainer
from assistant.intents import VALID_INTENTS

MIN_EXAMPLES = 5
TEST_FILE = Path("datasets/test_intents.jsonl")
QUARANTINE = Path("datasets/quarantine.jsonl")

def load_rows():
    rows = []
    
    for path in intent_model._source_paths():
        for index, record in enumerate(trainer.read_jsonl_records(path)):
            text = trainer.get_record_input(record)
            intent = trainer.get_record_intent(record)
            rows.append({"path": path, "index": index, "record": record, "text": text,
                         "intent": intent, "key": intent_model._norm(text) if text else ""})
            
    return rows

def analyse(rows):
    by_text = defaultdict(list)
    
    for r in rows:
        if r["key"] and r["intent"]:
            by_text[r["key"]].append(r)
            
    dups, conflicts, drop, conflict_keys = [], [], set(), set()
    
    for key, items in by_text.items():
        intents = {i["intent"] for i in items}
        
        if len(intents) > 1:
            conflicts.append((key, sorted(intents)))
            conflict_keys.add(key)
            drop.update((i["path"], i["index"]) for i in items)
        elif len(items) > 1:
            dups.append((key, len(items)))
            drop.update((i["path"], i["index"]) for i in items[1:])
            
    return dups, conflicts, drop, conflict_keys

def near_conflicts(rows, threshold=0.90):
    ok = intent_model.ROUTABLE | {"unknown"}
    uniq = list(dict.fromkeys((r["text"], r["intent"]) for r in rows
                              if r["key"] and r["intent"] in ok))
    
    if len(uniq) < 2:
        return []
    
    X = local_embed.embed_cached([t for t, _ in uniq], Path("db/audit_cache.npz"))
    S = np.triu(X @ X.T, 1)
    out = []
    
    for i, j in np.argwhere(S >= threshold):
        if uniq[i][1] != uniq[j][1]:
            out.append((float(S[i, j]), uniq[i], uniq[j]))
            
    return sorted(out, reverse=True)[:30]

def backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path("datasets/backups")
    folder.mkdir(parents=True, exist_ok=True)
    
    for path in intent_model._source_paths() + [TEST_FILE]:
        if path.exists():
            shutil.copy2(path, folder / f"{path.stem}_audit_{stamp}{path.suffix}")
            
            
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true",
                        help="back up, drop exact duplicates, move conflicting lines to quarantine.jsonl")
    args = parser.parse_args()
    
    rows = load_rows()
    dups, conflicts, drop, conflict_keys = analyse(rows)
    valid = set(VALID_INTENTS) | {"unknown"}
    
    print(f"Training lines: {len(rows)} from {len(intent_model._source_paths())} file(s)\n")
    
    print(f"Exact duplicates: {len(dups)}")
    for key, n in dups[:15]:
        print(f"  x{n}  {key}")
        
    print(f"\nConflicts (same text, different labels): {len(conflicts)}")
    for key, intents in conflicts:
        print(f"  {key!r} -> {intents}")
        
    bad = [r for r in rows if r["intent"] and r["intent"] not in valid]
    print(f"\nLabels that are not real intents: {len(bad)}")
    for r in bad:
        print(f"  {r['intent']!r}  <-  {r['text']!r}  ({r['path'].name})")
        
    ignored = sorted({r["intent"] for r in rows if r["intent"] in VALID_INTENTS
                      and r["intent"] not in intent_model.ROUTABLE and r["intent"] != "unknown"})
    print(f"\nValid but handled by rules/prefixes (the model ignores them): {len(ignored)}")
    print("  " + ", ".join(ignored[:25]) + (" ..." if len(ignored) > 25 else ""))

    short = [r for r in rows if r["key"] and len(r["key"]) < 3]
    print(f"\nVery short inputs: {len(short)}")
    
    for r in short:
        print(f"  {r['text']!r} -> {r['intent']}")
        
    counts = defaultdict(set)
    for r in rows:
        if r["key"] and r["intent"]:
            counts[r["intent"]].add(r["key"])
            
    thin = [(i, len(counts[i])) for i in sorted(intent_model.ROUTABLE | {"unknown"})
            if len(counts[i]) < MIN_EXAMPLES]
    print(f"\nIntents with fewer than {MIN_EXAMPLES} examples: {len(thin)}")
    for intent, n in thin:
        print(f"  {intent}: {n}")
        
    test_keys = {intent_model._norm(trainer.get_record_input(r) or "")
                 for r in trainer.read_jsonl_records(TEST_FILE)}
    
    leaked = [k for k in test_keys if k in {r["key"] for r in rows}]
    print(f"\nTest inputs also in training (leakage): {len(leaked)}")
    for key in leaked:
        print(f"  {key}")
        
    try:
        near = near_conflicts(rows)
        print(f"\nNear-identical sentences with different labels: {len(near)}")
        for sim, a, b in near:
            print(f"  {sim:.2f}  {a[0]!r} [{a[1]}]  vs  {b[0]!r} [{b[1]}]")
            
    except Exception as err:
        print(f"\n(Near-conflict check skipped: {err})")
        
    if not args.fix:
        print("\nNothing was changed. Re-run with --fix to clean duplicates and conflicts.")
        return
    
    backup()
    quarantined = []
    by_file = defaultdict(list)
    
    for r in rows:
        by_file[r["path"]].append(r)
        
    for path, items in by_file.items():
        keep = []
        
        for r in items:
            if (r["path"], r["index"]) in drop:
                if r["key"] in conflict_keys:
                    quarantined.append({**r["record"], "source": path.name})
                continue
            
            keep.append(r["record"])
            
        trainer.write_jsonl_records(path, keep)
        
    if quarantined:
        with open(QUARANTINE, "a", encoding="utf-8") as file:
            import json
            for record in quarantined:
                file.write(json.dumps(record) + "\n")
                
    print(f"\nFixed. Backups in datasets/backups/. Quarantined {len(quarantined)} conflicting line(s) "
          f"to {QUARANTINE}. Re-add the correct version of each by hand.")
    
    
if __name__ == "__main__":
    main()
            
        