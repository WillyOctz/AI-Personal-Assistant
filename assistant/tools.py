from datetime import datetime
from assistant.memory import add_reminder
from pathlib import Path
import ast
import operator
import subprocess
import shlex

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".jsonl",
    ".csv",
    ".html",
    ".css",
    ".js",
}

## Helper Methods
#  -------------------------------------------------

def parse_launch_command(command):
    try:
        return shlex.split(command)
    except:
        return None
    
def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

## Functions logic
#  -------------------------------------------------

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
    
    parsed_command = parse_launch_command(command)
    
    if not parsed_command:
        return f"I could not understand the app command: {command}"
    
    try:
        subprocess.Popen(command)
        return f"Opening {app_name}."
    except FileNotFoundError:
        return f"I could not find the app command: {command}"
    except:
        return f"I tried to open {app_name}, but something went wrong."
    
#======================================================================
## File Search/Path Logic Functions
#======================================================================
    
IGNORED_FILE_FOLDERS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

def is_inside_ignored_folder(path):
    for part in path.parts:
        if part in IGNORED_FILE_FOLDERS:
            return True
        
    return False

def list_folder_items(folder_path, limit=20):
    path = Path(folder_path)
    
    if not path.exists():
        return {
            "ok": False,
            "reason": "not_found",
            "items": []
        }
        
    if not path.is_dir():
        return {
            "ok": False,
            "reason": "not_directory",
            "items": []
        }
        
    items = []
    
    for item in path.iterdir():
        if item.name in IGNORED_FILE_FOLDERS:
            continue
        
        item_type = "folder" if item.is_dir() else "file"
        
        items.append({
            "name": item.name,
            "type": item_type
        })
        
        if len(items) >= limit:
            break
        
    return {
        "ok": True,
        "reason": "ok",
        "items": items
    }
    
def search_files_by_name(folder_path, query, extension=None, limit=20):
    path = Path(folder_path)
    
    if not path.exists():
        return {
            "ok": False,
            "reason": "not_found",
            "matches": []
        }
        
    if not path.is_dir():
        return {
            "ok": False,
            "reason": "not_directory",
            "matches": []
        }
        
    query = query.lower().strip()
    matches = []
    
    for item in path.rglob("*"):
        if is_inside_ignored_folder(item):
            continue
        
        if extension and item.is_file():
            if item.suffix.lower() != extension:
                continue
            
        if extension and item.is_dir():
            continue
        
        if query in item.name.lower():
            item_type = "folder" if item.is_dir() else "file"
            
            matches.append({
                "name": item.name,
                "path": str(item),
                "type": item_type
            })
            
            if len(matches) >= limit:
                break
            
    return {
        "ok": True,
        "reason": "ok",
        "matches": matches 
    }
    
def get_file_info(folder_path, filename):
    path = Path(folder_path)
    
    if not path.exists():
        return {
            "ok": False,
            "reason": "folder_not_found",
            "file": None
        }
        
    if not path.is_dir():
        return {
           "ok": False,
            "reason": "not_directory",
            "file": None 
        }
        
    filename = filename.lower().strip()
    
    for item in path.rglob("*"):
        if item.name.lower() == filename:
            stats = item.stat()
            item_type = "folder" if item.is_dir() else "file"
            
            return {
                "ok": True,
                "reason": "ok",
                "file": {
                    "name": item.name,
                    "path": str(item),
                    "type": item_type,
                    "size": stats.st_size,
                    "modified": stats.st_mtime
                }
            }
            
    return {
        "ok": False,
        "reason": "file_not_found",
        "file": None
    }
    
def preview_text_file(folder_path, filename, max_lines=20):
    path = Path(folder_path)
    
    if not path.exists():
        return {
           "ok": False,
            "reason": "folder_not_found",
            "lines": [] 
        }
        
    if not path.is_dir():
        return {
            "ok": False,
            "reason": "not_directory",
            "lines": []
        }
        
    filename = filename.lower().strip()
    
    for item in path.rglob("*"):
        if is_inside_ignored_folder(item):
            continue
        
        if item.name.lower() == filename:
            if not item.is_file():
                return {
                    "ok": False,
                    "reason": "not_file",
                    "lines": []
                }
                
            if item.suffix.lower() not in TEXT_EXTENSIONS:
                return {
                   "ok": False,
                    "reason": "not_text",
                    "lines": [] 
                }
                
            lines = []
            
            try:
                with open(item, "r", encoding="utf-8") as file:
                    for index, line in enumerate(file):
                        if index >= max_lines:
                            break
                        
                        lines.append(line.rstrip("\n"))
                        
                return {
                    "ok": True,
                    "reason": "ok",
                    "path": str(item),
                    "lines": lines 
                }
            except UnicodeDecodeError:
                return {
                   "ok": False,
                    "reason": "decode_error",
                    "lines": [] 
                }
                
    return {
        "ok": False,
        "reason": "file_not_found",
        "lines": []
    }
    
def preview_text_file_range(folder_path, filename, start_line, end_line):
    path = Path(folder_path)
    
    if not path.exists():
        return {
            "ok": False,
            "reason": "folder_not_found",
            "lines": [] 
        }
        
    if not path.is_dir():
        return {
            "ok": False,
            "reason": "not_directory",
            "lines": [] 
        }
        
    filename = filename.lower().strip()
    
    for item in path.rglob("*"):
        if is_inside_ignored_folder(item):
            continue
        
        if item.name.lower() == filename:
            if not item.is_file():
                return {
                    "ok": False,
                    "reason": "not_file",
                    "lines": [] 
                }
                
            if item.suffix.lower() not in TEXT_EXTENSIONS:
                return {
                    "ok": False,
                    "reason": "not_text",
                    "lines": []
                }
                
            lines = []
            
            try:
                with open(item, "r", encoding="utf-8") as file:
                    for line_number, line in enumerate(file, start=1):
                        if start_line <= line_number <= end_line:
                            lines.append({
                                "number": line_number,
                                "text": line.rstrip() 
                            })
                            
                        if line_number > end_line:
                            break
            except:
                return {
                    "ok": False,
                    "reason": "read_error",
                    "lines": []
                }
                
            return {
                "ok": True,
                "reason": "ok",
                "path": str(item),
                "lines": lines 
            }
    
    return {
        "ok": False,
        "reason": "file_not_found",
        "lines": []
    }
    
def preview_text_file_around(folder_path, filename, center_line, radius=5):
    start_line = center_line - radius
    end_line = center_line + radius
    
    if start_line < 1:
        start_line = 1
        
    return preview_text_file_range(folder_path, filename, start_line, end_line)
    
def search_text_in_files(folder_path, query, limit=20):
    path = Path(folder_path)
    
    if not path.exists():
        return {
           "ok": False,
            "reason": "folder_not_found",
            "matches": [] 
        }
        
    if not path.is_dir():
        return {
            "ok": False,
            "reason": "not_directory",
            "matches": []
        }
        
    query = query.lower().strip()
    matches = []
    
    for item in path.rglob("*"):
        if is_inside_ignored_folder(item):
            continue
        
        if not item.is_file():
            continue
        
        if item.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        
        try:
            with open(item, "r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    if query in line.lower():
                        matches.append({
                            "path": str(item),
                            "line": line_number,
                            "text": line.strip()
                        })
                        
                        if len(matches) >= limit:
                            return {
                               "ok": True,
                                "reason": "ok",
                                "matches": matches 
                            }
        except UnicodeDecodeError:
            continue
        
    return {
        "ok": True,
        "reason": "ok",
        "matches": matches 
    }
    
def validate_folder_path(folder_path):
    path = Path(folder_path)
    
    if not path.exists():
        return {
            "valid": False,
            "reason": "not_found" 
        }
        
    if not path.is_dir():
        return {
            "valid": False,
            "reason": "not_directory"
        }
        
    return {
        "valid": True,
        "reason": "ok" 
    }