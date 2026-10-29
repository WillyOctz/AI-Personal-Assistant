import pytest
from assistant import personality
from assistant.reply import Reply, as_reply

SAMPLE = dict(
    text="stretch", due="2026-11-01", app="Chrome", n=2, folder="docs",
    query="notes", name="a.txt", task="essay", duration="5 minutes",
    greeting="Good morning", name_part=", Ann", summary="1 overdue.",
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