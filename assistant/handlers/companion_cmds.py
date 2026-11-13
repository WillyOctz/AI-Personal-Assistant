from assistant import companion, memory, monitor
from assistant.registry import command
from assistant.reply import Reply
from assistant.shared import voice


@command("companion_status", "memory", routable=True,
         patterns=("companion status", "activity status", "what are you tracking", "what do you track"),
         help="See what I keep track of")
def companion_status(ctx):
    return companion.status_text()


@command("companion_snooze", "memory", patterns=("companion snooze", "snooze nudges"),
         help="Silence nudges for a while")
def companion_snooze(ctx):
    return companion.snooze_nudges()


@command("companion_setting", "memory", prefixes=("set companion ",),
         help="Tune me: set companion break 50")
def companion_setting(ctx):
    parts = ctx.rest("set companion ").split(None, 1)

    if len(parts) < 2:
        return "Use this format: set companion setting value\n" + companion.settings_help()

    return companion.apply_setting(parts[0], parts[1])[1]


@command("activity_recap", "memory", routable=True,
         patterns=("recap", "daily recap", "starlight recap", "recap my day", "where did my time go",
                   "weekly recap", "recap my week"),
         help="Recap of where your time went")
def activity_recap(ctx):
    days = 7 if "week" in ctx.text else 1
    data = companion.build_recap(days)

    if not data["total"] and not data["focus"]["sessions"]:
        return companion.no_data_message()

    verbosity = memory.get_setting("verbosity", "normal")
    say = companion.recap_line(data, verbosity, memory.get_setting("recap_llm", True))
    return Reply(say=say, detail=companion.recap_text(data), kind="recap", data=data, styled=True)


@command("forget_activity", "memory", patterns=("forget activity",), prefixes=("forget activity ",),
         help="Erase what I noticed: forget activity today | all")
def forget_activity(ctx):
    arg = ctx.rest("forget activity ").lower()

    if arg not in ("today", "all"):
        return ("This deletes what I've noticed about your activity.\n"
                "Use: forget activity today     or     forget activity all")

    return f"Forgot {monitor.forget(everything=(arg == 'all'))} activity record(s)."


@command("handoff_note", "memory", prefixes=("handoff note ",),
         help="Leave a note for future you: handoff note nebula: fix login")
def handoff_note(ctx):
    text = ctx.rest("handoff note ")

    if not text:
        return "Use this format: handoff note what future-you should know"

    result = companion.set_handoff(text)

    if result is None:
        return Reply(say=voice("handoff.none"), styled=True)

    return Reply(say=voice("handoff.cleared" if result["cleared"] else "handoff.saved",
                           project=result["project"]), styled=True)