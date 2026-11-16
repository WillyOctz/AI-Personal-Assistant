from assistant import database, retrieval

def test_matrix_uses_signature_function(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "t.db")
    monkeypatch.setattr(retrieval, "_dense", {})
    assert retrieval._matrix("note")["ids"] == []  