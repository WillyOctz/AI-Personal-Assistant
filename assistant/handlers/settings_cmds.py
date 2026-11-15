import re
from assistant import memory
from assistant.registry import command

SETTINGS = {  
    "confirm_path_open":    ("bool", None),
    "confirm_project_open": ("bool", None),
    "confirm_app_launching":("bool", None),
    "index_enabled":        ("bool", None),
    "index_content":        ("bool", None),
    "index_vectors":        ("bool", None),
    "recap_llm":            ("bool", None),
    "verbosity":            ("choice", ("minimal", "normal", "chatty")),
}
TRUE = {"on", "true", "yes", "1", "enable", "enabled"}
FALSE = {"off", "false", "no", "0", "disable", "disabled"}
PY_CALL = re.compile(r"""^set_setting\(\s*["'](\w+)["']\s*,\s*(.+?)\s*\)$""")

@command("change_setting", "memory",
         prefixes=("set setting ", "setting "),
         matcher=lambda t: bool(PY_CALL.match(t.strip())),
         help="Change a preference: set setting confirm path open on")
def change_setting(ctx):
    m = PY_CALL.match(ctx.text)
    if m:
        key, raw = m.group(1), m.group(2).strip("\"'")
    else:
        words = ctx.rest("set setting ", "setting ").replace("=", " ").split()
        if len(words) < 2:
            return "Use: set setting <name> <on/off/value>\nKnown: " + ", ".join(SETTINGS)
        key, raw = "_".join(words[:-1]).lower(), words[-1]

    if key not in SETTINGS:
        return f"I don't know the setting '{key}'.\nKnown: " + ", ".join(SETTINGS)

    kind, choices = SETTINGS[key]
    raw = raw.lower()
    if kind == "bool":
        if raw in TRUE: value = True
        elif raw in FALSE: value = False
        else: return "Use on or off."
    else:
        if raw not in choices: return f"{key} must be one of: {', '.join(choices)}"
        value = raw

    memory.set_setting(key, value)
    return f"Setting saved: {key} = {value}"

@command("list_settings", "memory", patterns=("all settings", "list settings"),
         help="Show every preference I can change")
def list_settings(ctx):
    return "\n".join(f"{k}: {memory.get_setting(k)}" for k in SETTINGS)