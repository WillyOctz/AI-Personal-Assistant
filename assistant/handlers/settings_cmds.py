import re
from rapidfuzz import fuzz, process
from assistant import memory, settings_spec as S
from assistant.registry import command
from assistant.reply import Reply, button

TRUE = {"on", "true", "yes", "1", "enable", "enabled"}
FALSE = {"off", "false", "no", "0", "disable", "disabled"}
PY_CALL = re.compile(r"""^set_setting\(\s*["'](\w+)["']\s*,\s*(.+?)\s*\)$""", re.I)
TURN = re.compile(r"^(?:turn|switch)\s+(on|off)\s+(.+)$")


def _norm(text):
    return re.sub(r"[\s\-]+", "_", text.strip().lower()).strip("_")

def resolve_key(text, cutoff=90):
    key = _norm(text)
    if key in S.SPEC:
        return key
    hit = process.extractOne(key, list(S.SPEC), scorer=fuzz.WRatio, score_cutoff=cutoff)
    return hit[0] if hit else None

def suggest(text):
    return [h[0] for h in process.extract(_norm(text), list(S.SPEC), scorer=fuzz.WRatio, limit=3, score_cutoff=60)]

def shown(value, kind):
    return ("on" if value else "off") if kind == "bool" else str(value)

def parse_value(key, raw):
    _, kind, _, limits, _ = S.SPEC[key]
    raw = raw.strip().strip("\"'").lower()
    if kind == "bool":
        return True if raw in TRUE else False if raw in FALSE else None
    if kind == "choice":
        return raw if raw in limits else None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if limits[0] <= n <= limits[1] else None

def expects(kind, limits):
    return {"bool": "on or off", "choice": " / ".join(limits or ()) , "int": f"a number {limits[0]}-{limits[1]}" if limits else ""}[kind]

def _split(text, rest):
    m = PY_CALL.match(text)
    if m:
        return m.group(1), m.group(2)
    t = TURN.match(text)
    if t:
        return t.group(2), t.group(1)
    words = rest.replace("=", " ").split()
    if len(words) >= 2 and resolve_key(" ".join(words[:-1])):
        return " ".join(words[:-1]), words[-1]
    return " ".join(words), None            # no value -> "show this setting"

def _turn_matches(text):
    t = TURN.match(text)
    return bool(t and resolve_key(t.group(2)))   # "turn on the lights" is NOT hijacked


@command("change_setting", "memory",
         prefixes=("set setting ", "change setting "),
         matcher=lambda t: bool(PY_CALL.match(t)) or _turn_matches(t),
         help="Change a preference: set setting confirm path open on")
def change_setting(ctx):
    text = ctx.text.rstrip("?!. ")
    name, raw = _split(text, ctx.rest("set setting ", "change setting "))
    key = resolve_key(name)

    if not key:
        near = suggest(name)
        hint = "Did you mean: " + ", ".join(near) if near else "Say 'settings' to see them all."
        return Reply(say=f"I don't have a setting called '{name}'. {hint}", styled=True)

    _, kind, default, limits, desc = S.SPEC[key]
    current = S.get(key)

    if raw is None:
        return f"{key}: {shown(current, kind)} (default {shown(default, kind)})\n{desc}"

    value = parse_value(key, raw)
    if value is None:
        return f"{key} expects {expects(kind, limits)}."

    memory.set_setting(key, value)
    return Reply(
        say=f"{key}: {shown(current, kind)} -> {shown(value, kind)}",
        detail=desc,
        actions=[button("Undo", f"set setting {key} {shown(current, kind)}", style="ghost")],
        styled=True,
    )


@command("reset_setting", "memory", prefixes=("reset setting ",), help="Back to default: reset setting verbosity")
def reset_setting(ctx):
    key = resolve_key(ctx.rest("reset setting "))
    if not key:
        return "I don't know that setting. Say 'settings'."
    memory.set_setting(key, S.SPEC[key][2])
    return f"{key} is back to its default: {shown(S.SPEC[key][2], S.SPEC[key][1])}"


@command("show_settings", "memory",
         patterns=("settings", "show settings", "list settings", "all settings"),
         help="Show every preference and its current value")
def show_settings(ctx):
    lines, group = [], None
    for key, (g, kind, default, _, desc) in S.SPEC.items():
        if g != group:
            lines.append(f"\n{g}:")
            group = g
        value = S.get(key)
        mark = "*" if value != default else " "
        extra = f"   (default {shown(default, kind)})" if value != default else ""
        lines.append(f" {mark} {key}: {shown(value, kind)}{extra}")

    lines += [
        "\nSafety switches (own commands, not changeable here):",
        f"   real_app_launching: {shown(memory.get_setting('real_app_launching', False), 'bool')}   -> enable/disable app launching",
        f"   real_website_opening: {shown(memory.get_setting('real_website_opening', False), 'bool')}   -> enable/disable website opening",
        "\n* = changed from default.   Change one: set setting <name> <value>",
        "Companion tuning is separate: set companion ...",
    ]
    return Reply(say="Here are my settings, dear.", detail="\n".join(lines).strip(), styled=True)