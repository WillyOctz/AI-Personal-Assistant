from urllib.parse import urlparse
from assistant import memory

def handle_register_website(user_input):
    name, url = parse_register_website(user_input)
    
    if not name or not url:
        return "Use this format: register website website_name as https://example.com"
    
    if not is_safe_website_url(url):
        return "Website URLs must start with http:// or https://"
    
    result = memory.save_website(name, url)
    website = result["website"]
    
    if result["created"]:
        return f"Registered website: {website['name']} -> {website['url']}"
    
    return f"Updated website: {website['name']} -> {website['url']}"

def format_website_registry():
    registry = memory.get_website_registry()
    
    if not registry:
        return "No websites registered yet."
    
    lines = ["Registered websites:"]
    
    for index, website in enumerate(registry.values(), start=1):
        lines.append(
            f"{index}. {website['name']}: {website['url']} | "
            f"allowed: {website.get('allowed', False)}"
        )
        
    return "\n".join(lines)

def parse_register_website(user_input):
    prefix = "register website "
    text = user_input.strip()
    
    if not text.lower().startswith(prefix):
        return "", ""
    
    details = text[len(prefix):].strip()
    
    if " as " not in details.lower():
        return "", ""
    
    name, url = details.split(" as ", 1)
    return name.strip(), url.strip()

def is_safe_website_url(url):
    parsed = urlparse(url.strip())
    
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
    )
    
def parse_allow_website(user_input):
    prefix = "allow website "
    text = user_input.lower().strip()
    
    if not text.startswith(prefix):
        return ""
    
    return text[len(prefix):].strip()

def parse_open_website(user_input):
    prefix = "open website "
    text = user_input.lower().strip()
    
    if not text.startswith(prefix):
        return ""
    
    return text[len(prefix):].strip()

def parse_disallow_website(user_input):
    prefix = "disallow website "
    text = user_input.lower().strip()
    
    if not text.startswith(prefix):
        return ""
    
    return text[len(prefix):].strip()

def set_pending_website_open(website):
    pending = {
        "name": website["name"],
        "url": website["url"],
    }
    
    memory.set_state_value("pending_website_open", pending)
    
def get_pending_website_open():
    return memory.get_state_value("pending_website_open")

def clear_pending_website_open():
    memory.clear_state_value("pending_website_open")
    
def handle_open_website(user_input):
    name = parse_open_website(user_input)
    
    if not name:
        return "Use this format: open website website_name"
    
    website = memory.get_website_registry_entry(name)
    
    if not website:
        return f"I could not find registered website: {name}"
    
    if not memory.get_setting("real_website_opening", False):
        return (
            "Real website opening is disabled.\n"
            "Use: enable website opening"
        )
        
    if not website.get("allowed", False):
        return (
            f"{website['name']} is registered but not allowed for opening.\n"
            f"Use: allow website {website['name']}"
        )
        
    set_pending_website_open(website)
    
    return (
        f"I am ready to open {website['name']}: {website['url']}\n"
        "Reply yes to open it or no to cancel."
    )
    
def confirm_pending_website_open(open_website_url):
    pending = get_pending_website_open()
    
    if not pending:
        return None
    
    result = open_website_url(pending["name"], pending["url"])
    log_website_open(
        pending["name"],
        pending["url"],
        result
    )
    
    clear_pending_website_open()
    
    return result

def deny_pending_website_open():
    pending = get_pending_website_open()
    
    if not pending:
        return None
    
    clear_pending_website_open()
    
    return f"Cancelled website opening: {pending['name']}"

def handle_allow_website(user_input):
    name = parse_allow_website(user_input)
    
    if not name:
        return "Use this format: allow website website_name"
    
    result = memory.set_website_allowed(name, True)
    
    if not result["updated"]:
        return f"I could not find registered website: {result['website']}"
    
    return f"Allowed website: {result['website']['name']}"

def handle_disallow_website(user_input):
    name = parse_disallow_website(user_input)
    
    if not name:
        return "Use this format: disallow website website_name"
    
    result = memory.set_website_allowed(name, False)
    
    if not result["updated"]:
        return f"I could not find registered website: {result['website']}"
    
    return f"Disallowed website: {result['website']['name']}"

def log_website_open(website_name, url, result):
    event = {
        "website_name": website_name,
        "url": url,
        "result": result,
        "timestamp": memory.current_timestamp(),
    }
    
    memory.add_website_open(event)
    
def format_website_open_history():
    opens = memory.get_website_open()
    
    if not opens:
        return "I do not have any website opening history yet."
    
    lines = ["Website opening history:"]
    
    for event in opens:
        lines.append(
            f"- {event['timestamp']} | "
            f"{event['website_name']} | "
            f"{event['result']}"
        )
        
    return "\n".join(lines)