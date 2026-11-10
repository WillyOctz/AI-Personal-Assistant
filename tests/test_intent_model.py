import numpy as np

from assistant import intent_model, persona_rag, retrieval

LABELS = ["set_reminder", "set_reminder", "play_music", "unknown", "unknown"]


def test_majority_vote_with_confidence():
    intent, conf, _ = intent_model.decide(np.array([0.9, 0.8, 0.6, 0.55, 0.3]), LABELS)
    assert intent == "set_reminder" and conf > 0.75


def test_far_from_everything_abstains():
    assert intent_model.decide(np.array([0.2, 0.1, 0.1, 0.0, 0.0]), LABELS)[0] is None


def test_unknown_majority_goes_to_llm():
    assert intent_model.decide(np.array([0.5, 0.5, 0.5, 0.9, 0.85]), LABELS)[0] is None


def test_conflicts_are_dropped(tmp_path, monkeypatch):
    f = tmp_path / "a.jsonl"
    f.write_text('{"input":"play music","intent":"play_music"}\n'
                 '{"input":"Play Music","intent":"unknown"}\n'
                 '{"input":"open chrome","intent":"open_app"}\n'
                 '{"input":"dataset stats","intent":"dataset_stats"}\n', encoding="utf-8")
    monkeypatch.setattr(intent_model, "_source_paths", lambda: [f])
    pairs, conflicts = intent_model.load_pairs()
    assert pairs == [("open chrome", "open_app")]          # prefix-style intents are ignored
    assert conflicts[0][0] == "play music"


def test_bm25_scores_even_a_single_document():
    corpus = [retrieval.tokens("i love learning python")]
    assert retrieval.bm25_scores(retrieval.tokens("python"), corpus)[0] > 0


def test_rrf_prefers_ids_in_both_lists():
    assert retrieval.rrf([["a", "b", "c"], ["c", "a"]])[0] == "a"


def test_hybrid_rank_works_offline():
    docs = [{"id": "1", "text": "i like black coffee"}, {"id": "2", "text": "my cat is named luna"}]
    hits = retrieval.hybrid_rank("what coffee do i like", docs, {}, limit=2)
    assert [h["id"] for h in hits] == ["1"]


def test_persona_loader_skips_bad_lines(tmp_path, monkeypatch):
    f = tmp_path / "p.jsonl"
    f.write_text('{"context":"thanks","user":"thx","nebula":"Of course, dear."}\n'
                 'not json\n{"user":"","nebula":"x"}\n', encoding="utf-8")
    monkeypatch.setattr(persona_rag, "PERSONA_FILE", f)
    assert len(persona_rag.load_pairs()) == 1