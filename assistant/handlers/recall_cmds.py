import re
from assistant import convo_store, convo_worker, decisions, memory, semantic_memory, settings_spec as S
from assistant.registry import command, confirmable
from assistant.reply import Reply, button
from assistant.shared import voice

_ASK = [re.compile(p, re.I) for p in (
    r"^(?:what|which)\s+(?:did|do|have)\s+(?:we|i)\s+(?:decide|decided|agree|agreed|settle|settled|choose|chose)\s*(?:on|about|for|regarding|with|to)?\s*(?P<q>.*)$",
    r"^(?:what(?:'s|\s+is|\s+was|\s+were)\s+)?(?:the\s+)?(?:decision|decisions|conclusion)s?\s+(?:on|about|for|regarding)\s+(?P<q>.+)$",
    r"^(?:did|have)\s+(?:we|i)\s+(?:decide|decided|agree|agreed|settle|settled)\s*(?:on|about|to)?\s*(?P<q>.+)$",
    r"^remind me what\s+(?:we|i)\s+(?:decided|agreed)\s*(?:on|about)?\s*(?P<q>.*)$",
)]

def topic_of(text):
    for rx in _ASK:
        m = rx.match(text.strip())
        if m:
            return m.group("q").strip(" ?!.,")
    return None

def _llm_phrase(topic, items):
    from assistant import llm, personality
    facts = "\n".join(f"- {i['when'][:10]}: {i['text']}" for i in items)
    system = (personality.get_llm_system_instruction() + 
             "\n\nAnswer the question in 1-3 short sentences using ONLY the dated notes given. "
              "If they do not answer it, say you do not know. Never add facts.")
    for fn in (llm.get_gemini_response, llm.get_groq_response):
        r = fn(f"Question: what did we decide about {topic}?\nNotes:\n{facts}", system)
        if r["ok"]:
            return r["text"].strip()[:400]
    return ""

@command("recall_decision", "memory", matcher=lambda t: topic_of(t) is not None,
         help="Ask what we settled: what did we decide about sqlite?")
def recall_decision(ctx):
    topic = topic_of(ctx.text.rstrip("?!. ")) or ""
    found = decisions.find(topic)
    items, live = found["items"], found["live"]
    
    if not items and not live:
        return Reply(say=voice("decision.none", query=topic or "that"),
                     detail="If we did settle it and I missed it, tell me: decision: <what we decided>", styled=True)
        
    lines = []
    for i in items:
        tag = "" if i["origin"].startswith(("llm", "user")) else "  (auto-extracted)"
        lines.append(f"- {i['when'][:10]}: {i['text']}{tag}")
    if found["mode"] == "mention":
        lines.insert(0, "No explicit decision, but these conversations mention it:")
    if len(items) > 1 and found["mode"] == "decision":
        lines.append("(newest first; if the newest one changed an older one, the newest wins)")
    for t in live:
        lines.append(f"- just now (not summarised yet): {t['user'][:160]}")
        
    say = voice("decision.found" if topic else "decision.latest", n=len(items), query=topic)
    if topic and items and S.get("recall_llm_answer"):
        say = _llm_phrase(topic, items) or say
        
    actions = [button(f"Open #{i['summary_id']}", f"show summary {i['summary_id']}", style="ghost") for i in items[:2]]
    return Reply(say=say, detail="\n".join(lines), actions=actions, styled=True)

@command("log_decision", "memory", prefixes=("decision: ", "log decision "),
         help="Write a decision down yourself: decision: use sqlite for pruning")
def log_decision(ctx):
    text = ctx.rest("decision: ", "log decision ").strip()
    if not text:
        return "Use this format: decision: what we decided"
    sid = convo_store.save_summary({"summary": f"Decision: {text}", "decisions": [text]},
                                   kind="decision", origin="user")
    convo_worker.embed_summary(sid, [text])
    return Reply(say=voice("decision.logged", text=text), styled=True)

@command("show_summaries", "memory", patterns=("show summaries", "conversation summaries", "summaries"),
         help="List remembered conversations with their numbers")
def show_summaries(ctx):
    items = convo_store.summaries(limit=10)
    if not items:
        return "I haven't written any conversations down yet."
    lines = [f"#{s['id']}  {s['timestamp'][:16]}  [{s['kind']}]  "
             f"{', '.join(s['topics']) or s['summary'][:60]}" for s in items]
    return Reply(say="Here is what I remember, newest first.", detail="\n".join(lines), styled=True)

@command("show_summary", "memory", prefixes=("show summary ",), help="Open one remembered conversation: show summary 14")
def show_summary(ctx):
    arg = ctx.rest("show summary ").lstrip("#")
    s = convo_store.get_summary(int(arg)) if arg.isdigit() else None
    if not s:
        return "I couldn't find that summary. Say 'show summaries' for the numbers."
    lines = [f"#{s['id']}  {s['timestamp']}  ({s['turn_count']} turns, {s['origin']})"]
    if s["decisions"]: lines += ["Decisions:"] + [f"  - {d}" for d in s["decisions"]]
    lines.append("Summary: " + s["summary"].split("Summary: ", 1)[-1].split("\n")[0]) 
    if s["topics"]: lines.append("Topics: " + ", ".join(s["topics"]))
    if s["open_items"]: lines += ["Open:"] + [f"  - {o}" for o in s["open_items"]]
    actions = []
    if s["session_id"]:
        actions = [button("Re-summarise", f"summarize conversation {s['session_id']}", style="ghost"),
                   button("Forget it", f"forget conversation {s['session_id']}", style="danger")]
    return Reply(say="Here it is, dear.", detail="\n".join(lines), actions=actions, styled=True)

@command("summarize_conversation", "memory",
         patterns=("summarize conversation", "summarize our chat", "summarize session"),
         prefixes=("summarize conversation ",),
         help="Write the conversation down now: summarize conversation [number]")
def summarize_conversation(ctx):
    arg = ctx.rest("summarize conversation ").lstrip("#")
    if arg.isdigit():
        sid, final = int(arg), True
    else:
        sid, final = convo_store.current_session_id(), False
    if not sid:
        return "There is no conversation to summarise yet."
    new_id = convo_worker.process(sid, force=True, final=final)
    s = convo_store.get_summary(new_id) if new_id else None
    if not s:
        return "That conversation is too short to be worth writing down."
    text = s["summary"].split("Summary: ", 1)[-1].split("\n")[0]
    lines = (["Decisions:"] + [f"  - {d}" for d in s["decisions"]] if s["decisions"] else []) + [f"Summary: {text}"]
    return show_summary.__wrapped__(ctx) if False else Reply(
        say="Written down, dear.", detail="\n".join(lines),
        actions=[button("Open", f"show summary {s['id']}", style="ghost")], styled=True
    )
    
def _forget(pending):
    n = convo_store.delete_session(pending["id"])
    return "That one is already gone." if n is None else f"Forgot conversation #{pending['id']}: {n} turn(s) and its summary."

confirmable("pending_forget_session", _forget, lambda p: "Okay, i kept it.")

@command("forget_session", "memory", prefixes=("forget conversation ",),
         help="Erase one remembered conversation: forget conversation 14")
def forget_session(ctx):
    arg = ctx.rest("forget conversation ").lstrip("#")
    if not arg.isdigit() or not convo_store.get_session(int(arg)):
        return "Use this format: forget conversation <number>   (numbers are in 'show summaries')"
    memory.set_state_value("pending_forget_session", {"id": int(arg)})
    return Reply(
        say="This erases that conversation and its summary for good.",
        detail="Reply yes to forget it or no to cancel.", kind="confirm",
        data={"title": f"Forget conversation #{arg}", "subtitle": "turns, summary and embeddings"},
        needs_confirmation=True, styled=True
    )
    
@command("convo_status", "memory", patterns=("conversation status", "session status", "conversation memory status"),
         help="How much I remember, and what is waiting to be summarised")
def convo_status(ctx):
    c = convo_store.counts()
    cache = semantic_memory.get_semantic_cache_status()["sources"]["conversation_summaries"]
    return "\n".join([
        "Conversation memory:",
        f"Turns kept: {c['turns']}   archived: {c['archived']}   action history: {c['history']}",
        f"Sessions: {c['sessions'] or 'none'}",
        f"Summaries: {c['summaries'] or 'none'}",
        f"Embeddings: {cache['cached']}/{cache['records']} cached, {cache['missing']} missing, {cache['stale']} stale",
        f"Session gap: {S.get('session_gap_minutes')} min",
    ])
    
def _prune_args():
    return (S.get("convo_keep_turns"), S.get("convo_archive_days"), S.get("convo_delete_days"), S.get("history_keep_days"))

@command("preview_convo_prune", "memory", patterns=("preview conversation prune",), help="See what pruning would remove")
def preview_convo_prune(ctx):
    r = convo_store.prune(*_prune_args(), dry_run=True)
    return (f"Conversation prune preview:\nWould archive: {r['archive']} turn(s)\n"
            f"Would delete: {r['delete']} archived turn(s)\nWould trim history: {r['history']} event(s)\n"
            "Only turns from conversations that are already summarised are touched.")
    
@command("convo_prune", "memory", patterns=("prune conversation",), help="Apply the retention rules now")
def convo_prune(ctx):
    r = convo_store.prune(*_prune_args())
    return f"Pruned. Archived {r['archive']}, deleted {r['delete']}, trimmed {r['history']} history event(s)."