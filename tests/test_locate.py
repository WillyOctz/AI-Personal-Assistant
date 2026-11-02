from assistant.locate_parser import parse_locate_query, parse_name_query


def test_where_is_my():
    assert parse_locate_query("Where is my thesis pdf?") == {
        "kind": "name", "query": "thesis pdf", "personal": True}


def test_persona_prefix_and_verb():
    r = parse_locate_query("mommy, where did i put the budget sheet")
    assert r["kind"] == "name" and r["query"] == "budget sheet"


def test_content_search():
    r = parse_locate_query("where did i write about the login bug")
    assert r["kind"] == "content" and r["query"] == "login bug"
    assert parse_locate_query("find text login bug")["kind"] == "content"


def test_non_personal():
    assert parse_locate_query("where is paris")["personal"] is False


def test_does_not_hijack_other_commands():
    for text in ["where was i", "find files proj main", "find reminder milk",
                 "search text proj hello", "what is 2+2", "where are we", "hello"]:
        assert parse_locate_query(text) is None, text


def test_query_parsing():
    q = parse_name_query("my latest budget pdf")
    assert q["tokens"] == ["budget"] and q["exts"] == (".pdf",) and q["recent"]
    assert parse_name_query("thesis folder")["kind"] == "folder"
    assert parse_name_query("report.docx")["exts"] == (".docx",)
    assert parse_name_query("report.docx")["tokens"] == ["report"]
    assert parse_name_query("pdfs")["exts"] == (".pdf",)