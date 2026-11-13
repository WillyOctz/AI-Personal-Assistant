from assistant import registry
from assistant.registry import command
from assistant.reply import Reply
from assistant.shared import voice

TITLES = {"memory": "Things I keep", "action": "Things I do", "basic": "Basics",
          "chat": "Talking", "control": "Under the hood"}

@command("show_help", "basic",
         patterns=("help", "commands", "list commands", "show commands", "what commands do you have"),
         help="List what I can do")
def show_help(ctx):
    lines = []
    
    for group, helps in registry.help_lines().items():
        lines.append(TITLES.get(group, group.title()) + ":")
        lines += [f"  - {h}" for h in sorted(helps)]
        
    return Reply(say=voice("help.intro"), detail="\n".join(lines), styled=True)