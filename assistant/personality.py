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

def respond_to_help_request(goal=None, topic=None):
    if topic and goal:
        return f"Tell me what part is stuck in {topic}. We can connect it back to your goal: {goal}."
    
    if topic:
        return f"Tell me what part is stuck in {topic}. We can break it into one small step."
    
    if goal:
        return f"Tell me what part is stuck. We can connect it back to your goal: {goal}."
    
    return "Tell me what part is stuck. We can break it into one small step."

def respond_to_stuck(goal=None, topic=None):
    if topic and goal:
        return f"Okay. Let us reduce the problem. What is the smallest part of {topic} that feels stuck, and how does it connect to {goal}?"
    
    if topic:
        return f"Okay. Let us reduce the problem. What is the smallest part of {topic} that feels stuck?"

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
    
def respond_about_user(profile):
    if not profile:
        return "I do not know much about you yet."
    
    details = []
    
    for key, value in profile.items():
        details.append(f"{key}: {value}")
        
    return "Here is what I remember about you:\n" + "\n".join(details)

def explain_response(intent, group, source=None, confidence=None, scores=None):
    if not intent:
        return "I do not have a previous response to explain yet."
    
    if group == "chat":
        explanation = f"I answered conversationally because I recognized this as {intent}."

    elif group == "memory":
        explanation = f"I used memory-related logic because I recognized this as {intent}."

    elif group == "action":
        explanation = f"I used action logic because I recognized this as {intent}."

    elif group == "control":
        explanation = f"I used control/debug logic because I recognized this as {intent}."

    elif group == "basic":
        explanation = f"I used basic assistant logic because I recognized this as {intent}."
    
    else:
        explanation = f"I recognized the intent as {intent}, but I do not have a detailed explanation yet."
        
    details = []
    
    if source:
        details.append(f"Source: {source}")
        
    if confidence is not None:
        details.append(f"Confidence: {confidence:.2f}")
        
    if scores:
        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_scores = sorted_scores[:5]
            
        details.append("Scores:")
            
        for intent_name, score in top_scores:
            details.append(f"- {intent_name}: {score:.2f}")
        
    if details:
        return explanation + "\n" + "\n".join(details)

    return explanation

def unknown_chat_response(user_input=None, topic=None):
    lines = ["I am not sure if that was a command or conversation yet."]
    
    if topic:
        lines.append(f"Current topic: {topic}")
        
    if user_input:
        lines.append(f"You said: {user_input}")
        
    lines.append("You can rephrase it, or teach me with: teach message as intent_name")
    
    return "\n".join(lines)