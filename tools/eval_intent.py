import argparse
from pathlib import Path

import numpy as np

from assistant import intent_model, local_embed
from assistant.trainer import get_record_input, get_record_intent, read_jsonl_records

parser = argparse.ArgumentParser()
parser.add_argument("--text", help="show the nearest training lines for one message")
args = parser.parse_args()

if not intent_model._ensure_index():
    raise SystemExit("No training data found.")

X, labels, texts = intent_model._state["X"], intent_model._state["labels"], intent_model._state["texts"]

if args.text:
    sims = X @ local_embed.embed([args.text])[0]
    
    for i in np.argsort(-sims)[:8]:
        print(f"{sims[i]:.2f}  {labels[i]:<26} {texts[i]}")
        
    print("->", intent_model.decide(sims, labels))
    raise SystemExit

tests = [(get_record_input(r), get_record_intent(r))
         for r in read_jsonl_records(Path("datasets/test_intents.jsonl"))
         if get_record_input(r) and get_record_intent(r)]
negatives = [r["message"] for r in read_jsonl_records(Path("datasets/llm_eval_cases.jsonl"))
             if r.get("expected_command") is False and r.get("message")]

T = local_embed.embed([t for t, _ in tests]) @ X.T if tests else []
N = local_embed.embed(negatives) @ X.T if negatives else []

print(f"{len(tests)} test lines, {len(negatives)} should-not-be-a-command lines\n")
print("min_sim  correct  abstained(->LLM)  wrong  risky-negatives")

for min_sim in (0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70):
    correct = abstain = 0
    
    for (text, expected), sims in zip(tests, T):
        got = intent_model.decide(sims, labels, min_sim=min_sim)[0]
        correct += got == expected
        abstain += got is None and got != expected
        
    risky = sum(1 for sims in N
                if (g := intent_model.decide(sims, labels, min_sim=min_sim)[0]) and not g.startswith("chat_"))
    wrong = len(tests) - correct - abstain
    mark = "  <- current" if abs(min_sim - intent_model.MIN_SIM) < 1e-9 else ""
    print(f"{min_sim:>6.2f}  {correct:>7}  {abstain:>16}  {wrong:>5}  {risky:>15}{mark}")
    
print("\nMisses at the current threshold:")
for (text, expected), sims in zip(tests, T):
    got = intent_model.decide(sims, labels)[0]
    
    if got != expected:
        print(f"  {text!r}: expected {expected}, got {got}")
        
print("\nHow the 'should not be a command' lines route:")
for text, sims in zip(negatives, N):
    print(f"  {text!r} -> {intent_model.decide(sims, labels)[0]}")