import re

from assistant import memory, statements
from assistant.registry import command, confirmable
from assistant.reply import Reply
from assistant.shared import voice

@command("self_statement", "chat",
         matcher=lambda t: (statements.classify(t) or {}).get("kind") in ("mood", "maybe_name"),
         help="Tell me how you feel: i am tired")
def self_statement(ctx):
    info = statements.classify(ctx.text)
    
    if info["kind"] == "mood":
        statements.save_mood(info["mood"])
        say = voice("mood.positive" if info["polarity"] == "positive" else "mood.negative", mood=info["mood"])
        if info["asked_back"]:
            say += " " + voice("mood.asked_back")
        return Reply(say=say, styled=True)
    
    last = (re.findall(r"[A-Za-z]+", ctx.input) or [""])[-1]
    if last[:1].isupper() and last[1:].islower():
        memory.set_state_value("pending_name", {"name": info["name"]})
        return Reply(
            say=f"Shall I call you {info['name']}, dear?",
            detail="Reply yes to save it or no to skip.", kind="confirm",
            data={"title": f"Call you {info['name']}?", "subtitle": "Saved to your profile"},
            needs_confirmation=True, styled=True
        )
        
    from assistant import brain
    return brain.get_llm_fallback_response(ctx.input, ctx.analysis)

confirmable(
    "pending_name",
    lambda p: (memory.set_profile_value("name", p["name"]) or f"Lovely to meet you, {p['name']}."),
    lambda p: "Alright, I won't save that."
)