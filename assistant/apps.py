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