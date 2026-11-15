from assistant import database, pins


def test_query_cleaning():
    assert pins.clean_query("my Thesis Folder") == "thesis"


def test_pin_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "t.db")
    monkeypatch.setattr(pins, "_ready", False)
    folder = tmp_path / "Thesis Docs"
    folder.mkdir()

    result = pins.add_pin("", str(folder))
    assert result["ok"] and result["pin"]["name"] == "thesis docs" and result["pin"]["kind"] == "folder"
    assert pins.resolve("my thesis docs folder")["path"] == str(folder)
    assert pins.resolve("thesis doc")["name"] == "thesis docs"        # typo tolerated
    assert pins.resolve("thesis banana") is None                       # guesses are not
    assert pins.remove_pin("thesis docs")


def test_special_folder_alias(monkeypatch, tmp_path):
    monkeypatch.setattr(pins, "special_folders", lambda: {"downloads": str(tmp_path)})
    monkeypatch.setattr(pins, "get_pin", lambda name: None)
    monkeypatch.setattr(pins, "list_pins", lambda limit=100: [])
    assert pins.resolve("my download folder")["source"] == "special"


def test_programs_are_never_opened(tmp_path):
    program = tmp_path / "tool.exe"
    program.write_text("x")
    assert pins.open_path(str(program)) == {"ok": False, "reason": "blocked_type"}
    assert pins.open_path(str(tmp_path / "gone.txt"))["reason"] == "not_found"