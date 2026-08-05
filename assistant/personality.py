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

def respond_to_feeling(feeling):
    feeling = feeling.lower().strip()
    
    if "tired" in feeling:
        return "I hear you. Take it slow for a moment. We can choose one small thing and keep it manageable."

    if "confused" in feeling:
        return "I hear you. Let us slow it down and untangle one piece at a time."

    if "excited" in feeling:
        return "That is good energy. Let us aim it at one useful step."

    if "focused" in feeling:
        return "Good. Let us protect that focus and keep the next step clear."

    return f"I hear you. I will remember that you are feeling {feeling}."

def respond_to_help_request(goal=None):
    if goal:
        return f"Tell me what part is stuck. We can connect it back to your goal: {goal}."
    
    return "Tell me what part is stuck. We can break it into one small step."

def respond_to_stuck(goal=None):
    if goal:
        return f"Okay. Let us reduce the problem. What is the smallest part of {goal} that feels stuck?"
    
    return "Okay. Let us reduce the problem. What is the smallest part that feels stuck?"

def respond_to_thanks():
    return "You are welcome. I am here with you."

def respond_to_goodbye():
    return "Alright. I will be here when you come back."

def respond_to_day_greeting(user_input, mood=None, goal=None):
    text = user_input.lower()
    
    if "morning" in text:
        greeting = "Good morning."
    elif "afternoon" in text:
        greeting = "Good afternoon."
    elif "evening" in text:
        greeting = "Good evening."
    else:
        greeting = "Hello."
        
    details = []
    
    if mood:
        details.append(f"I remember you were feeling {mood}.")
        
    if goal:
        details.append(f"We are still working toward your goal: {goal}.")
        
    if details:
        return greeting + " " + " ".join(details)
    
    return greeting

def respond_to_capabilities():
    return (
        "I can help with reminders, memory notes, profile facts, focus sessions, "
        "planning, app launching, file search, simple calculations, and learning new intents."
    )
    
def respond_to_identity():
    return (
        "I am Nebula, your personal assistant. "
        "I help you remember things, plan tasks, focus, search files, open apps, and keep learning with you."
    )