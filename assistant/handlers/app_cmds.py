from assistant import app_discovery, apps, memory, tools, app_finder
from assistant.registry import command, confirmable
from assistant.reply import Reply, api_button, button

# ----------------------------------App Search Functions-----------------------------------------------

def _ask(name, path):
    memory.set_state_value("pending_add_app", {"name": name, "path": path})
    return Reply(say=f"Register {name} and allow me to launch it?", detail=f"{path}\nReply yes to add it or no to cancel.",
                 kind="confirm", data={"title": f"Add {name}", "subtitle": path}, needs_confirmation=True, styled=True)

@command("add_app", "action", prefixes=("add app ",), help="Find a program and register it: add app chrome")
def add_app(ctx):
    query = ctx.rest("add app ").strip()
    hits = app_discovery.search(query, 4)
    if not hits:
        return Reply(say=f"I couldn't find a program like '{query}' in your Start Menu.",
                     detail="Use the tray menu 'Add app…', or: register app NAME as <path>",
                     actions=[api_button("Add app…", "add_app", style="primary")], styled=True)
    exact = [h for h in hits if h[0] == query.lower()]
    if exact or len(hits) == 1:
        return _ask(*(exact or hits)[0])
    return Reply(say="Which one, dear?", detail="\n".join(f"- {n}" for n, _ in hits),
                 actions=[button(n, f"add app {n}") for n, _ in hits], styled=True)

def _added(pending):
    memory.add_app_registry_entry(pending["name"], f'"{pending["path"]}"')
    memory.set_app_allowed(pending["name"], True)
    note = "" if memory.get_setting("real_app_launching", False) else "\nApp launching is still off: say 'enable app launching'."
    return f"Added {pending['name']}. Say 'open {pending['name']}'.{note}"

confirmable("pending_add_app", _added, lambda p: "Okay, I didn't add it.")


@command("check_apps", "memory", patterns=("check apps", "validate apps", "check shortcuts"),
         help="Check that every registered app can still be found")
def check_apps(ctx):
    registry = memory.get_app_registry()
    if not registry:
        return "No apps registered yet."
    lines = []
    for name, app in registry.items():
        target, _ = tools.split_command(app["command"])
        ok = tools.resolve_executable(target) is not None
        lines.append(f"{'ok     ' if ok else 'MISSING'} {name}: {app['command']}"
                     f"{'' if app.get('allowed') else '   (not allowed)'}")
    return "App check:\n" + "\n".join(lines) + "\nFix a missing one: update app NAME as <full path>"

# ---------------------------------------App Usage Actions----------------------------------------------

@command("allow_opening", "action", prefixes=("allow opening ",),
         help="Approve opening a program I found in a protected place")
def allow_opening(ctx):
    return app_finder.approve(ctx.rest("allow opening "))

@command("use_found_app", "action", prefixes=("use found app ",))
def use_found_app(ctx):
    return app_finder.choose(ctx.rest("use found app "))

@command("remember_found_app", "action", patterns=("remember found app",),
         help="Register the program I just opened so it opens directly next time")
def remember_found_app(ctx):
    return app_finder.remember()

@command("scan_apps", "action", patterns=("scan apps", "rescan apps", "index apps"),
         help="Re-read your drives for programs")
def scan_apps(ctx):
    app_finder.request_scan()
    return Reply(say="Reading your drives for programs, dear. Check 'app search status' in a bit.", styled=True)

@command("app_search_status", "memory", patterns=("app search status", "app index status"))
def app_search_status(ctx):
    return app_finder.status_text()