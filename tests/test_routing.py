import json
from pathlib import Path
import pytest
from assistant import brain

CASES = [json.loads(l) for l in Path("datasets/routing_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

@pytest.mark.parametrize("case", CASES, ids=lambda c: c["text"])
def test_route(case, tmp_db, monkeypatch):
    monkeypatch.setattr(brain.intent_model, "predict", lambda text: None)
    got = brain.analyze_intent(case["text"])["intent"]
    if "intent" in case:
        assert got == case["intent"]
    else:
        assert got != case["not_intent"]