from datetime import datetime
from assistant import memory

def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_app_launch(app_name, command, result):
    event = {
        "app_name": app_name,
        "command": command,
        "result": result,
        "timestamp": current_timestamp()
    }
    
    memory.add_app_launch(event)
    
def parse_register_app(user_input):
    text = user_input.strip()
    
    if not text.lower().startswith("register app "):
        return "", ""
    
    text = text[13:].strip()
    
    if " as " not in text:
        return "", ""
    
    name, command = text.split(" as ", 1)
    
    return name.strip(), command.strip()

def parse_unregister_app(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["unregister app ", "remove app "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_update_app(user_input):
    text = user_input.strip()
    
    for prefix in ["update app ", "change app "]:
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
            break
        
    if " as " not in text:
        return "", ""
    
    name, command = text.split(" as ", 1)
    
    return name.strip(), command.strip()

def parse_app_search(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["search apps ", "find app "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_app_alias(user_input):
    text = user_input.strip()
    
    if not text.lower().startswith("alias app "):
        return "", ""
    
    text = text[10:].strip()
    
    if " as " not in text:
        return "", ""
    
    alias, app_name = text.split(" as ", 1)
    
    return alias.strip(), app_name.strip()

def parse_remove_app_alias(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["remove app alias ", "delete app alias "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_default_app(user_input):
    text = user_input.strip()
    
    if not text.lower().startswith("set default app "):
        return "", ""
    
    text = text[16:].strip()
    
    if " as " not in text:
        return "", ""
    
    category, app_name = text.split(" as ", 1)
    
    return category.strip(), app_name.strip()

def parse_remove_default_app(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["remove default app ", "delete default app "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def parse_debug_app(user_input):
    text = user_input.lower().strip()
    
    if not text.startswith("debug app "):
        return ""
    
    return text.replace("debug app ", "", 1).strip()

def parse_delete_app_registry_index(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["delete app registry ", "remove app registry "]:
        if text.startswith(prefix):
            value = text.replace(prefix, "", 1).strip()
            
            if value.isdigit():
                return int(value)
            
    return None

def parse_rename_app_registry_index(user_input):
    text = user_input.lower().strip()
    
    if not text.startswith("rename app registry "):
        return None, ""
    
    text = text.replace("rename app registry ", "", 1).strip()
    
    if " as " not in text:
        return None, ""
    
    index_text, new_name = text.split(" as ", 1)
    
    if not index_text.strip().isdigit():
        return None, ""
    
    return int(index_text.strip()), new_name.strip()

def parse_backup_index(user_input, prefix):
    text = user_input.lower().strip()
    
    if not text.startswith(prefix):
        return None
    
    value = text.replace(prefix, "", 1).strip()
    
    if not value.isdigit():
        return None
    
    return int(value)

def parse_allow_app(user_input):
    text = user_input.lower().strip()
    
    if text.startswith("allow app "):
        return text.replace("allow app ", "", 1).strip()
    
    return ""

def parse_disallow_app(user_input):
    text = user_input.lower().strip()
    
    for prefix in ["disallow app ", "block app "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()
        
    return ""

def resolve_app_name_for_open(app_name):
    alias_result = memory.resolve_app_alias(app_name)
    
    default_result = memory.get_default_app(alias_result)
    
    if default_result:
        final_name = default_result
    else:
        final_name = alias_result
        
    app_entry = memory.get_app_registry_entry(final_name)
    
    return {
       "input": app_name,
        "after_alias": alias_result,
        "after_default": final_name,
        "registered": app_entry is not None,
        "app_entry": app_entry 
    }
    
def set_pending_app_launch(app_name, command):
    pending = {
        "app_name": app_name,
        "command": command
    }
    
    memory.set_state_value("pending_app_launch", pending)
    
def get_pending_app_launch():
    return memory.get_state_value("pending_app_launch")

def clear_pending_app_launch():
    memory.clear_state_value("pending_app_launch")
    
def log_app_launch(app_name, command, result):
    event = {
        "app_name": app_name,
        "command": command,
        "result": result,
        "timestamp": current_timestamp()
    }
    
    memory.add_app_launch(event)
    
## =========================================================================
## -------------------Format Debug/Preview Handlers for apps----------------
## =========================================================================
    
def format_app_registry():
    registry = memory.get_app_registry()
    
    if not registry:
        return "No apps registered yet."
    
    lines = ["Registered apps:"]
    
    for index, (name, app) in enumerate(registry.items(), start=1):
        allowed = app.get("allowed", False)
        lines.append(f"{index}. {name}: {app['command']} | allowed: {allowed}")
        
    return "\n".join(lines)

def format_app_aliases():
    aliases = memory.get_app_aliases()
    
    if not aliases:
        return "No app aliases saved yet."
    
    lines = ["App aliases:"]
    
    for alias, app_name in aliases.items():
        lines.append(f"- {alias} -> {app_name}")
        
    return "\n".join(lines)

def format_default_apps():
    defaults = memory.get_default_apps()
    
    if not defaults:
        return "No default apps saved yet."
    
    lines = ["Default apps:"]
    
    for category, app_name in defaults.items():
        lines.append(f"- {category} -> {app_name}")
        
    return "\n".join(lines)

def format_app_dashboard():
    registry = memory.get_app_registry()
    aliases = memory.get_app_aliases()
    defaults = memory.get_default_apps()
    real_launching = memory.get_setting("real_app_launching", False)
    launch_stats = memory.get_app_launch_stats()
    
    lines = [
        "App dashboard:",
        f"Registered apps: {len(registry)}",
        f"Aliases: {len(aliases)}",
        f"Default apps: {len(defaults)}",
        f"Real launching: {real_launching}",
        f"Total launches: {launch_stats['total']}",
    ]
    
    if launch_stats["total"] > 0:
        lines.append(
            f"Most launched: {launch_stats['most_launched']} ({launch_stats['most_count']} time(s))"
        )
        lines.append(f"Last launched: {launch_stats['last_launched']}")
        
    return "\n".join(lines)

def format_app_safety_dashboard():
    registry = memory.get_app_registry()
    real_launching = memory.get_setting("real_app_launching", False)
    confirm_launching = memory.get_setting("confirm_app_launching", True)
    pending_app = get_pending_app_launch()
    
    allowed_count = 0
    
    for app in registry.values():
        if app.get("allowed", False):
            allowed_count += 1
            
    blocked_count = len(registry) - allowed_count
    
    lines = [
       "App safety dashboard:",
        f"Real launching: {real_launching}",
        f"Launch confirmation: {confirm_launching}",
        f"Registered apps: {len(registry)}",
        f"Allowed apps: {allowed_count}",
        f"Blocked apps: {blocked_count}", 
    ]
    
    if pending_app:
        lines.append(f"Pending launch: {pending_app['app_name']}")
    else:
        lines.append("Pending launch: None")
        
    return "\n".join(lines)

def format_debug_app_resolution(user_input):
    app_name = parse_debug_app(user_input)
    
    if not app_name:
        return "What app should I debug?"
    
    resolution = resolve_app_name_for_open(app_name)
    app_entry = resolution["app_entry"]
    
    lines = [
        f"Input: {resolution['input']}",
        f"After alias: {resolution['after_alias']}",
        f"After default: {resolution['after_default']}",
        f"Registered: {resolution['registered']}", 
    ]
    
    if app_entry:
        lines.append(f"Command: {app_entry['command']}")
        
    return "\n".join(lines)

def format_app_cleanup_preview():
    preview = memory.preview_app_cleanup()
    
    return (
       f"App cleanup preview:\n"
        f"Missing command: {len(preview['missing_command'])}\n"
        f"Missing allowed field: {len(preview['missing_allowed'])}\n"
        f"Broken aliases: {len(preview['broken_aliases'])}\n"
        f"Broken defaults: {len(preview['broken_defaults'])}" 
    )
    
def format_debug_app_cleanup():
    preview = memory.preview_app_cleanup()
    
    lines = ["App cleanup details:"]
    
    lines.append("Missing command:")
    if preview["missing_command"]:
        for name in preview["missing_command"]:
            lines.append(f"- {name}")
    else:
        lines.append("- None")
        
    lines.append("Missing allowed field:")
    if preview["missing_allowed"]:
        for name in preview["missing_allowed"]:
            lines.append(f"- {name}")
    else:
        lines.append("- None")
        
    lines.append("Broken aliases:")
    if preview["broken_aliases"]:
        for item in preview["broken_aliases"]:
            lines.append(f"- {item['alias']} -> {item['app_name']}")
    else:
        lines.append("- None")

    lines.append("Broken defaults:")
    if preview["broken_defaults"]:
        for item in preview["broken_defaults"]:
            lines.append(f"- {item['category']} -> {item['app_name']}")
    else:
        lines.append("- None")
        
    return "\n".join(lines)

def format_app_registry_backups():
    backups = memory.get_app_registry_backups()
    
    if not backups:
        return "No app registry backups saved yet."
    
    lines = ["App registry backups:"]
    
    for index, backup in enumerate(backups, start=1):
        lines.append(
            f"{index}. {backup['timestamp']} | "
            f"apps: {len(backup['app_registry'])}, "
            f"aliases: {len(backup['app_aliases'])}, "
            f"defaults: {len(backup['default_apps'])}"
        )
        
    return "\n".join(lines)

def format_restore_app_registry_preview(user_input):
    index = parse_backup_index(user_input, "preview app registry restore ")
    
    if index is None:
        return "Use this format: preview app registry restore number"
    
    preview = memory.preview_restore_app_registry_backup(index)
    
    if not preview["found"]:
        if preview["reason"] == "empty":
            return "No app registry backups found."
        
        return "That app registry backup number does not exist."
    
    return (
        f"Restore preview for backup: {preview['backup_timestamp']}\n"
        f"Apps: current {preview['current_apps']} -> backup {preview['backup_apps']}\n"
        f"Aliases: current {preview['current_aliases']} -> backup {preview['backup_aliases']}\n"
        f"Defaults: current {preview['current_defaults']} -> backup {preview['backup_defaults']}"
    )
    
def format_app_backup_cleanup_preview():
    preview = memory.preview_app_registry_backup_cleanup()
    
    return (
        f"App backup cleanup preview:\n"
        f"Total backups: {preview['total']}\n"
        f"Keep latest: {preview['keep_latest']}\n"
        f"Would remove: {preview['remove_count']}"
    )
    
## ===============================================================
## -------------------App Action Handlers for apps----------------
## ===============================================================

def handle_register_app(user_input):
    name, command = parse_register_app(user_input)

    if not name or not command:
        return "Use this format: register app app_name as command"

    app = memory.add_app_registry_entry(name, command)

    return f"Registered app: {app['name']} -> {app['command']}"

def handle_update_registered_app(user_input):
    name, command = parse_update_app(user_input)

    if not name or not command:
        return "Use this format: update app app_name as command"

    result = memory.update_app_registry_entry(name, command)

    if not result["updated"]:
        return f"I could not find registered app: {result['app']}"

    app = result["app"]
    return f"Updated app: {app['name']} -> {app['command']}"

def handle_unregister_app(user_input):
    app_name = parse_unregister_app(user_input)

    if not app_name:
        return "Use this format: unregister app app_name"

    result = memory.remove_app_registry_entry(app_name)

    if not result["removed"]:
        return f"I could not find registered app: {result['app']}"

    app = result["app"]
    return f"Unregistered app: {app['name']} -> {app['command']}"

def handle_set_default_app(user_input):
    category, app_name = parse_default_app(user_input)

    if not category or not app_name:
        return "Use this format: set default app category as registered_app"

    resolved_app_name = memory.resolve_app_alias(app_name)
    app_entry = memory.get_app_registry_entry(resolved_app_name)

    if not app_entry:
        return f"I could not find registered app: {app_name}"

    result = memory.set_default_app(category, app_entry["name"])

    return f"Default app saved: {result['category']} -> {result['app_name']}"

def handle_remove_default_app(user_input):
    category = parse_remove_default_app(user_input)

    if not category:
        return "Use this format: remove default app category"

    result = memory.remove_default_app(category)

    if not result["removed"]:
        return f"I could not find default app category: {result['category']}"

    return f"Removed default app: {result['category']} -> {result['app_name']}"

def handle_add_app_alias(user_input):
    alias, app_name = parse_app_alias(user_input)

    if not alias or not app_name:
        return "Use this format: alias app alias_name as registered_app_name"

    app_name = memory.resolve_app_alias(app_name)
    app_entry = memory.get_app_registry_entry(app_name)

    if not app_entry:
        return f"I could not find registered app: {app_name}"

    result = memory.add_app_alias(alias, app_entry["name"])

    return f"App alias saved: {result['alias']} -> {result['app_name']}"

def handle_remove_app_alias(user_input):
    alias = parse_remove_app_alias(user_input)

    if not alias:
        return "Use this format: remove app alias alias_name"

    result = memory.remove_app_alias(alias)

    if not result["removed"]:
        return f"I could not find app alias: {result['alias']}"

    return f"Removed app alias: {result['alias']} -> {result['app_name']}"

## =========================================================================
## -------------------App Operation Handlers for apps----------------
## =========================================================================

def handle_rename_app_registry_by_index(user_input):
    index, new_name = parse_rename_app_registry_index(user_input)

    if index is None or not new_name:
        return "Use this format: rename app registry number as new_name"

    result = memory.rename_app_registry_entry_by_index(index, new_name)

    if result["renamed"]:
        return f"Renamed app registry entry: {result['old_name']} -> {result['new_name']}"

    if result["reason"] == "empty":
        return "No registered apps to rename."

    if result["reason"] == "invalid_index":
        return "That app registry number does not exist."

    if result["reason"] == "name_exists":
        return f"An app named {result['new_name']} already exists."

    return "I could not rename that app."

def handle_delete_app_registry_by_index(user_input):
    index = parse_delete_app_registry_index(user_input)

    if index is None:
        return "Use this format: delete app registry number"

    result = memory.remove_app_registry_entry_by_index(index)

    if result["removed"]:
        app = result["app"]
        return f"Removed app registry entry: {app['name']} -> {app['command']}"

    if result["reason"] == "empty":
        return "No registered apps to remove."

    return "That app registry number does not exist."

def handle_search_app_registry(user_input):
    query = parse_app_search(user_input)

    if not query:
        return "What app should I search for?"

    results = memory.search_app_registry(query)

    if not results:
        return f"I could not find registered apps matching: {query}"

    lines = [f"Registered apps matching {query}:"]

    for app in results:
        lines.append(f"- {app['name']}: {app['command']}")

    return "\n".join(lines)

def handle_allow_app(user_input):
    app_name = parse_allow_app(user_input)

    if not app_name:
        return "Use this format: allow app app_name"

    resolved_name = memory.resolve_app_alias(app_name)
    result = memory.set_app_allowed(resolved_name, True)

    if not result["updated"]:
        return f"I could not find registered app: {resolved_name}"

    return f"Allowed app for launching: {result['app']['name']}"

def handle_disallow_app(user_input):
    app_name = parse_disallow_app(user_input)

    if not app_name:
        return "Use this format: disallow app app_name"

    resolved_name = memory.resolve_app_alias(app_name)
    result = memory.set_app_allowed(resolved_name, False)

    if not result["updated"]:
        return f"I could not find registered app: {resolved_name}"

    return f"Disallowed app for launching: {result['app']['name']}"

## =========================================================================
## -----------App Backup/Cleanup Operation Handlers for apps--------------
## =========================================================================

def handle_backup_app_registry(timestamp):
    backup = memory.backup_app_registry(timestamp)

    return (
        f"App registry backup saved: {backup['timestamp']}\n"
        f"Apps: {len(backup['app_registry'])}\n"
        f"Aliases: {len(backup['app_aliases'])}\n"
        f"Defaults: {len(backup['default_apps'])}"
    )

def handle_restore_app_registry_backup(user_input):
    index = parse_backup_index(user_input, "restore app registry backup ")

    if index is None:
        return "Use this format: restore app registry backup number"

    result = memory.restore_app_registry_backup(index)

    if not result["restored"]:
        if result["reason"] == "empty":
            return "No app registry backups found."

        return "That app registry backup number does not exist."

    backup = result["backup"]

    return (
        f"Restored app registry backup: {backup['timestamp']}\n"
        f"Apps: {len(backup['app_registry'])}\n"
        f"Aliases: {len(backup['app_aliases'])}\n"
        f"Defaults: {len(backup['default_apps'])}"
    )

def handle_cleanup_app_backups():
    result = memory.cleanup_app_registry_backups()

    return (
        f"App backup cleanup finished.\n"
        f"Removed backups: {result['removed']}\n"
        f"Kept backups: {result['kept']}"
    )

def handle_repair_app_cleanup():
    result = memory.repair_app_cleanup()

    return (
        f"App cleanup repair finished.\n"
        f"Added missing allowed fields: {result['repaired_allowed']}\n"
        f"Removed broken aliases: {result['removed_aliases']}\n"
        f"Removed broken defaults: {result['removed_defaults']}\n"
        f"Skipped missing command entries: {result['skipped_missing_command']}"
    )
    
## =========================================================================
## -------------------App Opening Logic for apps----------------
## =========================================================================

def handle_open_app(app_name, open_registered_app, fallback_open_app):
    resolution = resolve_app_name_for_open(app_name)
    app_entry = resolution["app_entry"]

    if not app_entry:
        return fallback_open_app(app_name)

    real_launching = memory.get_setting("real_app_launching", False)

    if real_launching and not app_entry.get("allowed", False):
        return (
            f"{resolution['after_default']} is registered but not allowed for real launching.\n"
            f"Use: allow app {resolution['after_default']}"
        )

    confirm_launching = memory.get_setting("confirm_app_launching", True)

    if real_launching and confirm_launching:
        set_pending_app_launch(resolution["after_default"], app_entry["command"])
        return (
            f"I am ready to open {resolution['after_default']} using command: {app_entry['command']}.\n"
            f"Reply yes to launch or no to cancel."
        )

    result = open_registered_app(
        resolution["after_default"],
        app_entry,
        real_launching
    )

    log_app_launch(
        resolution["after_default"],
        app_entry["command"],
        result
    )

    return result

## =========================================================================
## -------------------App Yes/No Pending Logic for apps----------------
## =========================================================================

def confirm_pending_app_launch(open_registered_app):
    pending_app = get_pending_app_launch()

    if not pending_app:
        return None

    app_entry = {
        "name": pending_app["app_name"],
        "command": pending_app["command"]
    }

    result = open_registered_app(
        pending_app["app_name"],
        app_entry,
        True
    )

    log_app_launch(
        pending_app["app_name"],
        pending_app["command"],
        result
    )

    clear_pending_app_launch()

    return result

def deny_pending_app_launch():
    pending_app = get_pending_app_launch()

    if not pending_app:
        return None

    clear_pending_app_launch()

    return f"Cancelled app launch: {pending_app['app_name']}"