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