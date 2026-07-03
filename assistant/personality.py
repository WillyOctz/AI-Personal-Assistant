ASSISTANT_NAME = "Nebula"

def greet():
    return f"Hello, I am {ASSISTANT_NAME}. What can I help you with?ehe~"

def add_personality(text):
    return f"{text}"

def unknown_response():
    return "I do not understand what you say, but you can teach me"

def memory_saved_response():
    return "Got it"

def unknown_response():
    return "I do not understand that yet. You can teach me with: teach message as intent_name"