from datetime import datetime
from assistant.memory import add_reminder

def get_time():
    now = datetime.now()
    return now.strftime("The current time is %H:%M.")

def create_reminder(reminder_text):
    add_reminder(reminder_text)
    return f"Reminder saved: {reminder_text}"

def open_app(app_name):
    return f"I understand you want to open {app_name}, but real app launching is not connected yet."

def play_game(game_name):
    if game_name:
        return f"I understand you want to play {game_name}, but game launching is not connected yet."

    return "I understand you want to play a game, but I do not know which game yet."