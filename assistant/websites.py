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