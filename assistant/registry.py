import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

log = logging.getLogger("nebula.registry")

NOT_HANDLED = object()

@dataclass(frozen=True)
class Command:
    intent : str
    group: str
    handler: Callable
    patterns: tuple = ()
    prefixes: tuple = ()
    matcher: Optional[Callable] = None
    routable: bool = False
    help: str = ""
    dev: bool = False
    
@dataclass
class Ctx:
    input: str
    analysis: dict
    intent: str
    
    @property
    def text(self):
        return self.input.strip().lower()
    
    def rest(self, *prefixes):
        """the user text without command words"""
        raw = self.input.strip()
        low = raw.lower()
        
        for prefix in (*prefixes, self.analysis.get("matched") or ""):
            if prefix and low.startswith(prefix):
                return raw[len(prefix):].strip()
            
        return raw
    
    
COMMANDS = {}
CONFIRMABLES = []
_index = None


def command(intent, group="memory", patterns=(), prefixes=(), matcher=None, routable=False, help="", dev=False):
    def decorator(fn):
        global _index
        
        if intent in COMMANDS:
            raise ValueError(f"Command registered twice: {intent}")
        
        COMMANDS[intent] = Command(
            intent, group, fn,
            tuple(p.lower() for p in patterns),
            tuple(p.lower() for p in prefixes),
            matcher, routable, help, dev,
        )
        _index = None
        return fn
    
    return decorator

def _reset_index():
    global _index
    _index = None
    
def _get_index():
    global _index
    
    if _index is not None:
        return _index
    
    exact, prefix_owner = {}, {}
    
    for c in COMMANDS.values():
        for p in c.patterns:
            if exact.get(p, c.intent) != c.intent:
                raise ValueError(f"Pattern {p!r} belongs to both {exact[p]} and {c.intent}")
            exact[p] = c.intent
            
        for p in c.prefixes:
            if prefix_owner.get(p, c.intent) != c.intent:
                raise ValueError(f"Prefix {p!r} belongs to both {prefix_owner[p]} and {c.intent}")
            prefix_owner[p] = c.intent
            
    prefixes = sorted(prefix_owner.items(), key=lambda item: -len(item[0]))
    matchers = [c for c in COMMANDS.values() if c.matcher]
    _index = {"exact": exact, "prefixes": prefixes, "matchers": matchers}
    
    return _index


def match(text):
    index = _get_index()
    text = text.strip()
    
    if text in index["exact"]:
        return index["exact"][text], text
    
    for prefix, intent in index["prefixes"]:
        if text.startswith(prefix):
            return intent, prefix
        
    for c in index["matchers"]:
        try:
            if c.matcher(text):
                return c.intent, ""
        except Exception:
            log.exception("matcher for %s failed", c.intent)
            
    return None

def dispatch(intent, user_input, analysis):
    c = COMMANDS.get(intent)
    
    if c is None:
        return NOT_HANDLED
    
    return c.handler(Ctx(user_input, analysis, intent))


# ---------------------------Confirmations Flows----------------------------------------

def confirmable(state_key, on_yes, on_no):
    if all(key != state_key for key, _, _ in CONFIRMABLES):
        CONFIRMABLES.append((state_key, on_yes, on_no))
        
def pending_keys():
    return [key for key, _, _ in CONFIRMABLES]

def run_confirm(yes):
    from assistant import memory
    
    for key, on_yes, on_no in CONFIRMABLES:
        pending = memory.get_state_value(key)
        
        if pending:
            memory.clear_state_value(key)
            return (on_yes if yes else on_no)(pending)
        
    return NOT_HANDLED

# ------------------------------Feed Legacy sets from registry---------------------------

def sync_into_intents():
    from assistant import intent_model, intents
    
    group_sets = {
        "memory": intents.MEMORY_INTENTS, "control": intents.CONTROL_INTENTS,
        "action": intents.ACTION_INTENTS, "chat": intents.CHAT_INTENTS,
    }
    
    for c in COMMANDS.values():
        intents.VALID_INTENTS.add(c.intent)
        group_sets.get(c.group, set()).add(c.intent)
        
        if c.routable:
            intent_model.ROUTABLE.add(c.intent)
            
    _get_index()
    
def help_lines():
    groups = {}
    
    for c in COMMANDS.values():
        if c.help and not c.dev:
            groups.setdefault(c.group, []).append(c.help)