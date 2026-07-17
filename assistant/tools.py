from datetime import datetime
from assistant.memory import add_reminder
import ast
import operator

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_calculate(expression):
    try:
        tree = ast.parse(expression, mode="eval")
        result = evaluate_math_mode(tree.body)
        return f"The answer is {result}"
    except ZeroDivisionError:
        return "I cannot divide by zero."
    except:
        return "I could not calculate that."
    
def evaluate_math_mode(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        
        raise ValueError("Only numbers are allowed")
    
    if isinstance(node, ast.BinOp):
        left = evaluate_math_mode(node.left)
        right = evaluate_math_mode(node.right)
        operator_type = type(node.op)
        
        if operator_type not in ALLOWED_OPERATORS:
            raise ValueError("Operator not allowed")
        
        return ALLOWED_OPERATORS[operator_type](left, right)
    
    if isinstance(node, ast.UnaryOp):
        operand = evaluate_math_mode(node.operand)
        operator_type = type(node.op)
        
        if operator_type not in ALLOWED_OPERATORS:
            raise ValueError("Operator not allowed")
        
        return ALLOWED_OPERATORS[operator_type](operand)
    
    raise ValueError("Invalid expression")

def get_time():
    now = datetime.now()
    return now.strftime("The current time is %H:%M.")

def create_reminder(reminder_text, due=None):
    result = add_reminder(reminder_text, due)
    
    if not result["saved"]:
        return f"You already have this reminder: {result['reminder']}"
    
    if result["due"]:
        return f"Reminder saved: {result['reminder']} at {result['due']}"
    
    return f"Reminder saved: {result['reminder']}"

def open_app(app_name):
    return f"I understand you want to open {app_name}, but real app launching is not connected yet."

def play_game(game_name):
    if game_name:
        return f"I understand you want to play {game_name}, but game launching is not connected yet."

    return "I understand you want to play a game, but I do not know which game yet."

def open_registered_app(app_name, app_entry, real_launching=False):
    command = app_entry["command"]
    
    if not real_launching:
        return f"Real app launching is disabled. I would open {app_name} using command: {command}"
    
    return f"Real launching is not implemented yet. Command would be: {command}"