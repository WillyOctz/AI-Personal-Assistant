import pytest

from assistant import registry


@pytest.fixture
def fresh(monkeypatch):
    monkeypatch.setattr(registry, "COMMANDS", {})
    monkeypatch.setattr(registry, "CONFIRMABLES", [])
    registry._reset_index()
    yield registry
    registry._reset_index()


def test_exact_prefix_and_longest_wins(fresh):
    fresh.command("a", patterns=("hello there",), prefixes=("pin ",))(lambda c: "a")
    fresh.command("b", prefixes=("pin folder ",))(lambda c: "b")
    assert fresh.match("hello there") == ("a", "hello there")
    assert fresh.match("pin x") == ("a", "pin ")
    assert fresh.match("pin folder x") == ("b", "pin folder ")
    assert fresh.match("nothing") is None


def test_collisions_fail_fast(fresh):
    fresh.command("a", patterns=("same",))(lambda c: 1)
    fresh.command("b", patterns=("same",))(lambda c: 2)
    with pytest.raises(ValueError):
        fresh.match("x")


def test_duplicate_intent_rejected(fresh):
    fresh.command("a")(lambda c: 1)
    with pytest.raises(ValueError):
        fresh.command("a")(lambda c: 2)


def test_matcher_and_dispatch_and_rest(fresh):
    fresh.command("go", prefixes=("go to ",), matcher=lambda t: t == "open x")(lambda c: c.rest("go to "))
    assert fresh.match("open x")[0] == "go"
    assert fresh.dispatch("go", "Go To My Docs", {"matched": "go to "}) == "My Docs"
    assert fresh.dispatch("missing", "x", {}) is registry.NOT_HANDLED