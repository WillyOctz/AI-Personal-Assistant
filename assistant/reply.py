from dataclasses import dataclass, field

def button(label, command, style="default"):
    return {"label": label, "type": "command", "command": command, "style": style}

def copy_button(label, value, style="ghost"):
    return {"label": label, "type": "copy", "value": value, "style": style}


@dataclass
class Reply:
    say: str    # short nebula voiced line
    detail: str = ""    # ClI, logs and fallback
    kind: str = "text"  # types of responses 
    data: dict = field(default_factory=dict)   # payload 
    actions: list = field(default_factory=list)
    needs_confirmation: bool = False
    styled: bool = False          # if True = skip dress()
    intent: str | None = None
    
    def full(self):
        if self.detail:
            return f"{self.say}\n{self.detail}" if self.say else self.detail
        return self.say
    
    def __str__(self):
        return self.full()
    
    
def as_reply(value, fallback=""):
    if isinstance(value, Reply):
        return value
    if value is None:
        return Reply(say=fallback)
    return Reply(say=str(value))