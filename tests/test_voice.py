import pytest
from assistant import personality
from assistant.reply import Reply, as_reply

SAMPLE = dict(
    text="stretch", due="2026-11-01", app="Chrome", n=2, folder="docs",
    query="notes", name="a.txt", task="essay", duration="5 minutes",
    greeting="Good morning", name_part=", Ann", summary="1 overdue.",
    project="nebula", target="VS Code", age="2 hours ago", file_part=", working on brain.py",
    files=120,
    minutes=50, apps="Chrome", note_part=' You left yourself a note: "fix login"',
    when="Today", label="Today", total="2h 10m", top_part=" Most of it in nebula."
)


@pytest.mark.parametrize("key", list(personality.TEMPLATES))
@pytest.mark.parametrize("verbosity", ["minimal", "normal", "chatty"])
def test_every_template_renders(key, verbosity):
    out = personality.line(key, verbosity=verbosity, **SAMPLE)
    assert out and "{" not in out and "}" not in out


def test_reply_full_joins_say_and_detail():
    assert Reply(say="Hi", detail="there").full() == "Hi\nthere"
    assert str(Reply(say="Hi")) == "Hi"


def test_as_reply_accepts_everything():
    assert as_reply("x").say == "x"
    assert as_reply(None, fallback="y").say == "y"
    r = Reply(say="z")
    assert as_reply(r) is r