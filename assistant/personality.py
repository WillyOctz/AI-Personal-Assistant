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