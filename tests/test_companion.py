import time

from assistant import companion, monitor


def test_fmt_duration():
    assert monitor.fmt_duration(45) == "45 sec"
    assert monitor.fmt_duration(600) == "10 min"
    assert monitor.fmt_duration(3900) == "1h 05m"
    assert monitor.fmt_duration(7200) == "2h"


def test_project_matching():
    m = monitor.build_matchers([
        {"id": 1, "name": "nebula"}, {"id": 2, "name": "app"}, {"id": 3, "name": "nebula-web"},
    ])
    assert monitor.match_project("code.exe", "main.py - nebula - Visual Studio Code", m) == (1, "nebula")
    assert monitor.match_project("code.exe", "x - nebula-web - Visual Studio Code", m) == (3, "nebula-web")
    assert monitor.match_project("chrome.exe", "nebula docs - Chrome", m) is None      # not a work app
    assert monitor.match_project("code.exe", "my app - Visual Studio Code", m) is None  # generic name skipped


def test_can_nudge_brakes(monkeypatch):
    monkeypatch.setattr(companion, "_quiet_now", lambda: False)
    cfg = {"nudges": True, "paused": False, "min_gap": 1200, "max_per_day": 2}
    now = time.time()

    companion._n.update(last_any=0.0, day=None, count=0, snooze_until=0.0, kind_last={})
    assert companion.can_nudge(cfg, now)

    companion._n["last_any"] = now
    assert not companion.can_nudge(cfg, now + 60)               # global min gap
    assert companion.can_nudge(cfg, now + 1300)

    companion._n["count"] = 2
    assert not companion.can_nudge(cfg, now + 1300)             # daily cap

    companion._n.update(count=0, snooze_until=now + 3600)
    assert not companion.can_nudge(cfg, now + 1300)             # "Not now"


def test_apply_setting(monkeypatch):
    store = {}
    monkeypatch.setattr(companion.memory, "set_setting", lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr(companion.monitor, "refresh", lambda: None)

    assert companion.apply_setting("break", "45")[0] and store["break_minutes"] == 45
    assert not companion.apply_setting("break", "0")[0]
    assert companion.apply_setting("recap", "7:05")[0] and store["recap_time"] == "07:05"
    assert not companion.apply_setting("recap", "25:00")[0]
    assert companion.apply_setting("distractapps", "Chrome, discord.exe")[0]
    assert store["distraction_apps"] == ["chrome.exe", "discord.exe"]
    assert not companion.apply_setting("nope", "1")[0]