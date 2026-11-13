import os
import re

from assistant import events, memory, pins
from assistant.registry import command, confirmable
from assistant.reply import Reply, api_button, button, copy_button
from assistant.shared import log_file_search, voice
from assistant.tools import reveal_in_explorer

_LEGACY_OPEN = ("file ", "folder ", "website ", "project ", "app ")


# -----------------------open path/folders through lookup (can be update with confidence score)--------------------
def _wants_path(text):
    if not text.startswith("open "):
        return False
    
    rest = text[5:].strip()
    
    if not rest or rest.startswith(_LEGACY_OPEN):
        return False
    
    if memory.get_app_registry_entry(memory.resolve_app_alias(rest)):
        return False
     
    return pins.resolve(rest) is not None

def _perform(target):
    result = pins.open_path(target["path"])
    
    if not result["ok"]:
        reasons = {
            "not_found": f"that place is gone. Say 'unpin {target['name']}' to forget it.",
            "blocked_type": "I never launch programs or scripts.",
        }
        return f"I could not open {target['name']}: {reasons.get(result['reason'], result['reason'])}"
    
    if target.get("source") == "pin":
        pins.touch(target["name"])
        
    log_file_search("open_path", target["name"], "", target["path"])
    return Reply(say=voice("path.opened", name=target["name"]), styled=True)

@command("open_path", "action", prefixes=("open pin ", "go to ", "jump to "), matcher=_wants_path,
         help="Open a pinned or Windows folder: open downloads")
def open_path(ctx):
    name = ctx.rest("open pin ", "go to ", "jump to ", "open ")
    target = pins.resolve(name)
    
    if not target:
        return Reply(
            say=voice("path.notfound", query=name),
            actions=[button("Show pins", "show pins", style="ghost"),
                     api_button("Pin a folder…", "pin_folder", style="primary")],
            styled=True,
        )
        
    if target["kind"] == "file" or memory.get_setting("confirm_path_open", False):
        memory.set_state_value("pending_path_open", {"name": target["name"], "path": target["path"]})
        
        return Reply(
            say=voice("path.confirm", name=target["name"]),
            detail=f"{target['path']}\nReply yes to open it or no to cancel.",
            kind="confirm",
            data={"title": f"Open {target['name']}", "subtitle": target["path"]},
            needs_confirmation=True,
            styled=True,
        )
        
    return _perform(target)

def _confirmed(pending):
    current = pins.resolve(pending["name"])
    
    if not current or os.path.normcase(current["path"]):
        return "That shortcut changed, so I cancelled."

    return _perform(current)

confirmable("pending_path_open", _confirmed, lambda pending: f"Cancelled opening: {pending['name']}")


# --------------------------pin, unpin, list-------------------------------
def _split_as(rest):
    rest = rest.strip().strip('"')
    match = re.match(r'^(?P<p>.+?)\s+as\s+(?P<n>[^\\/:*?"<>|]+)$', rest, re.I)
    
    if match:
        return match.group("p").strip().strip('"'), match.group("n").strip()
    
    return rest, ""


@command("pin_path", "memory", prefixes=("pin folder ", "pin file ", "pin path ", "pin "),
         help="Pin a place for one-word access: pin C:\\Work\\thesis as thesis")
def pin_patch(ctx):
    path, name = _split_as(ctx.rest("pin folder ", "pin file ", "pin path ", "pin "))
    result = pins.add_pin(name, path)
    
    if not result["ok"]:
        if result["reason"] == "not_found":
            return "I couldn't find that path. Check it, or use the Pin folder… button."
        
        return "Use this format: pin C:\\full\\path as name"
    
    pin = result["pin"]
    key = "pin.saved" if result["created"] else "pin.updated"
    events.publish("today_changed")
    
    return Reply(
        say=voice(key, name=pin["name"]),
        actions=[button("Open it", f"open pin {pin['name']}", style="primary"),
                 button("Show pins", "show pins", style="ghost")],
        styled=True,
    )
    
@command("unpin_path", "memory", prefixes=("unpin ",), help="Forget a pinned place: unpin thesis")
def unpin_path(ctx):
    name = ctx.rest("unpin ")
    
    if not name:
        return "Use this format: unpin name"
    
    if not pins.remove_pin(name):
        return f"I could not find a pin called {name}."
    
    events.publish("today_changed")
    return Reply(say=voice("pin.removed", name=pins.clean_name(name)), styled=True)

def _item(entry, meta, removeable):
    name, path = entry["name"], entry["path"]
    actions = [button("Open", f"open pin {name}", style="primary"),
               button("Reveal", f"reveal path {path}"),
               copy_button("Copy path", path)]
    
    if removeable:
        actions.append(button("Unpin", f"unpin {name}", style="ghost"))
        
    return {"name": name, "type": entry["kind"], "path": path, "rel": path, "meta": meta, "actions": actions}


@command("show_pins", "memory",
         patterns=("pins", "show pins", "my pins", "quick paths", "shortcuts", "show shortcuts"),
         help="Show my pinned places and Windows folders")
def show_pins(ctx):
    items = [_item(p, f"used {p['uses']}×" if p["uses"] else "pinned", True) for p in pins.list_pins()]
    pinned = {item["name"] for item in items}
    
    for name, path in pins.special_folders().items():
        if name not in pinned:
            items.append(_item({"name": name, "path": path, "kind": "folder"}, "Windows folder", False))
    
    if not items:
        return Reply(say=voice("pin.none"), actions=[api_button("Pin a folder…", "pin_folder", style="primary")],
                     styled=True)
        
    return Reply(
        say=voice("pin.listed", n=len(items)),
        detail="\n".join(f"- {i['name']}: {i['path']}" for i in items),
        kind="file_list",
        data={"folder": "pins", "query": "", "items": items},
        actions=[api_button("Pin a folder…", "pin_folder", style="ghost")],
        styled=True,
    )
    
@command("reveal_path", "action", prefixes=("reveal path ",))
def reveal_path(ctx):
    path = ctx.rest("reveal path ").strip('"')
    result = reveal_in_explorer(path)
    
    if not result["ok"]:
        return f"I could not reveal that: {result['reason']}"
    
    return Reply(say=voice("file.revealed", name=os.path.basename(path.rstrip("\\/")) or path), styled=True)