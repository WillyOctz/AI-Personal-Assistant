def parse_feeling_statement(user_input):
    text = user_input.lower().strip()

    for prefix in ["i feel ", "i am feeling ", "i am "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()

    return ""


def parse_chat_remember_that(user_input):
    text = user_input.lower().strip()

    if text.startswith("remember that "):
        return text.replace("remember that ", "", 1).strip()

    return ""


def parse_topic_statement(user_input):
    text = user_input.lower().strip()

    for prefix in ["i am learning ", "i'm learning ", "we are learning ", "we are working on "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()

    return ""


def parse_feedback_intent_query(user_input):
    text = user_input.lower().strip()

    if text.startswith("feedback for "):
        return text.replace("feedback for ", "", 1).strip()

    return ""


def parse_response_feedback_search(user_input):
    text = user_input.lower().strip()

    for prefix in ["search feedback ", "search response feedback "]:
        if text.startswith(prefix):
            return text.replace(prefix, "", 1).strip()

    return ""


def parse_feedback_value_filter(user_input):
    text = user_input.lower().strip()

    if text.startswith("feedback value "):
        return text.replace("feedback value ", "", 1).strip()

    return ""


def parse_feedback_group_filter(user_input):
    text = user_input.lower().strip()

    if text.startswith("feedback group "):
        return text.replace("feedback group ", "", 1).strip()

    return ""


def parse_feedback_note(user_input):
    text = user_input.strip()

    if text.lower().startswith("feedback note "):
        return text[14:].strip()

    return ""


def parse_delete_feedback_note(user_input):
    text = user_input.lower().strip()

    for prefix in ["delete feedback note ", "remove feedback note "]:
        if text.startswith(prefix):
            value = text.replace(prefix, "", 1).strip()

            if value.isdigit():
                return int(value)

    return None

def format_response_feedback_stats(stats):
    return (
        f"Response feedback stats:\n"
        f"Total: {stats['total']}\n"
        f"Helpful: {stats['helpful']}\n"
        f"Not helpful: {stats['not_helpful']}"
    )


def format_recent_response_feedback(feedback_items):
    if not feedback_items:
        return "I do not have any response feedback yet."

    lines = ["Recent response feedback:"]

    for item in feedback_items:
        lines.append(
            f"- {item['timestamp']} | {item['feedback']} | "
            f"{item['last_intent']} | {item['last_group']}"
        )

    return "\n".join(lines)


def format_chat_feedback_dashboard(stats, recent):
    lines = [
        "Chat feedback dashboard:",
        f"Total: {stats['total']}",
        f"Helpful: {stats['helpful']}",
        f"Not helpful: {stats['not_helpful']}",
    ]

    if not recent:
        lines.append("Recent feedback: None")
        return "\n".join(lines)

    lines.append("Recent feedback:")

    for item in recent:
        lines.append(
            f"- {item['timestamp']} | {item['feedback']} | "
            f"{item['last_intent']} | {item['last_group']}"
        )

    return "\n".join(lines)

def format_feedback_for_intent(intent_name, feedback_items):
    if not feedback_items:
        return f"I do not have response feedback for {intent_name}."

    helpful = 0
    not_helpful = 0

    for item in feedback_items:
        if item.get("feedback") == "helpful":
            helpful += 1

        if item.get("feedback") == "not_helpful":
            not_helpful += 1

    return (
        f"Feedback for {intent_name}:\n"
        f"Total: {len(feedback_items)}\n"
        f"Helpful: {helpful}\n"
        f"Not helpful: {not_helpful}"
    )


def format_feedback_search_results(query, results):
    if not results:
        return f"I could not find response feedback matching: {query}"

    lines = [f"Response feedback matching {query}:"]

    for item in results[-5:]:
        lines.append(
            f"- {item['timestamp']} | {item['feedback']} | "
            f"{item['last_intent']} | {item['last_group']}"
        )

    return "\n".join(lines)


def format_feedback_by_value(value, results):
    if not results:
        return f"I do not have {value} response feedback."

    lines = [f"{value} response feedback:"]

    for item in results[-5:]:
        lines.append(
            f"- {item['timestamp']} | {item['last_intent']} | {item['last_group']}"
        )

    return "\n".join(lines)


def format_feedback_by_group(group, results):
    if not results:
        return f"I do not have response feedback for group: {group}"

    lines = [f"Response feedback for group {group}:"]

    for item in results[-5:]:
        lines.append(
            f"- {item['timestamp']} | {item['feedback']} | {item['last_intent']}"
        )

    return "\n".join(lines)

def format_feedback_notes(notes):
    if not notes:
        return "I do not have any feedback notes yet."

    lines = ["Feedback notes:"]

    for note in notes:
        lines.append(f"- {note['timestamp']} | {note['note']}")

    return "\n".join(lines)


def format_delete_feedback_note_result(result):
    if result["deleted"]:
        return f"Deleted feedback note: {result['note']['note']}"

    if result["reason"] == "empty":
        return "I do not have any feedback notes to delete."

    return "That feedback note number does not exist."

def format_response_feedback_health(health):
    return (
        f"Response feedback health:\n"
        f"Total: {health['total']}\n"
        f"Broken: {health['broken']}\n"
        f"Missing timestamp: {health['missing_timestamp']}\n"
        f"Invalid feedback: {health['invalid_feedback']}\n"
        f"Missing last intent: {health['missing_last_intent']}\n"
        f"Missing last group: {health['missing_last_group']}"
    )


def format_problem_feedback_intents(results):
    if not results:
        return "I do not have any not helpful feedback by intent yet."

    lines = ["Problem feedback intents:"]

    for intent_name, count in results:
        lines.append(f"- {intent_name}: {count}")

    return "\n".join(lines)


def format_helpful_feedback_intents(results):
    if not results:
        return "I do not have any helpful feedback by intent yet."

    lines = ["Helpful feedback intents:"]

    for intent_name, count in results:
        lines.append(f"- {intent_name}: {count}")

    return "\n".join(lines)

def format_response_feedback_cleanup(removed_count):
    return f"Response feedback cleanup finished. Removed {removed_count} broken item(s)."


def format_clear_response_feedback_preview(preview):
    return (
        f"Response feedback clear preview:\n"
        f"Total feedback items: {preview['total']}\n"
        f"Would remove: {preview['would_remove']}"
    )


def format_clear_response_feedback_prompt(total):
    return (
        f"This will clear {total} response feedback item(s).\n"
        f"Reply yes to confirm or no to cancel."
    )


def format_clear_response_feedback_result(removed_count):
    return f"Cleared {removed_count} response feedback item(s)."


def format_feedback_note_saved(note):
    return f"Saved feedback note: {note}"

def build_response_feedback(feedback_value, last_intent, last_group, last_text, timestamp):
    return {
        "timestamp": timestamp,
        "feedback": feedback_value,
        "last_intent": last_intent,
        "last_group": last_group,
        "last_text": last_text
    }


def format_response_feedback_saved(feedback_value):
    if feedback_value == "helpful":
        return "Good. I will remember that response helped."

    return "Got it. I will remember that response did not help."

def format_current_topic(topic):
    if not topic:
        return "I do not have a current topic saved yet."

    return f"We are currently working on {topic}."


def format_topic_saved(topic):
    return f"Got it. We are working on {topic}."


def format_topic_cleared(topic):
    if not topic:
        return "There is no current topic to clear."

    return f"Cleared current topic: {topic}"


def format_mood_saved(mood):
    return f"I will remember that you are {mood}."


def format_note_saved_from_chat(fact):
    return f"I will remember that {fact}."


def format_general_remembered_fact(fact):
    return f"I will remember that: {fact}"

def handle_chat_intent(user_input, analysis, memory, personality, current_timestamp):
    intent = analysis["intent"]

    if intent == "chat_how_are_you":
        mood = memory.get_profile_value("mood")
        goal = memory.get_profile_value("goal")

        lines = ["I am doing alright."]

        if mood:
            lines.append(f"I remember your current mood is {mood}.")

        if goal:
            lines.append(f"We are still working toward your goal: {goal}.")

        return " ".join(lines)

    if intent == "chat_need_help":
        goal = memory.get_profile_value("goal")
        topic = memory.get_state_value("current_topic")
        return personality.respond_to_help_request(goal, topic)

    if intent == "chat_stuck":
        goal = memory.get_profile_value("goal")
        topic = memory.get_state_value("current_topic")
        return personality.respond_to_stuck(goal, topic)

    if intent == "chat_thanks":
        return personality.respond_to_thanks()

    if intent == "chat_goodbye":
        return personality.respond_to_goodbye()

    if intent == "chat_day_greeting":
        mood = memory.get_profile_value("mood")
        goal = memory.get_profile_value("goal")
        return personality.respond_to_day_greeting(user_input, mood, goal)

    if intent == "chat_capabilities":
        return personality.respond_to_capabilities()

    if intent == "chat_identity":
        return personality.respond_to_identity()

    if intent == "chat_about_user":
        profile = memory.get_profile()
        return personality.respond_about_user(profile)
    
    if intent == "chat_feeling_statement":
        feeling = parse_feeling_statement(user_input)

        if not feeling:
            return "I hear you. Tell me a little more."

        memory.set_profile_value("mood", feeling)
        return personality.respond_to_feeling(feeling)

    if intent == "chat_remember_that":
        fact = parse_chat_remember_that(user_input)

        if not fact:
            return "What should I remember?"

        if fact.startswith("i am "):
            mood = fact.replace("i am ", "", 1).strip()
            memory.set_profile_value("mood", mood)
            return format_mood_saved(mood)

        if fact.startswith("i like "):
            memory.add_note(fact)
            return format_note_saved_from_chat(fact)

        memory.add_note(fact)
        return format_general_remembered_fact(fact)

    if intent == "chat_topic_statement":
        topic = parse_topic_statement(user_input)

        if not topic:
            return "What topic are we working on?"

        memory.set_state_value("current_topic", topic)
        return format_topic_saved(topic)

    if intent == "chat_current_topic":
        topic = memory.get_state_value("current_topic")
        return format_current_topic(topic)

    if intent == "chat_clear_topic":
        topic = memory.get_state_value("current_topic")

        if topic:
            memory.clear_state_value("current_topic")

        return format_topic_cleared(topic)
    
    if intent == "show_response_feedback_stats":
        stats = memory.get_response_feedback_stats()
        return format_response_feedback_stats(stats)

    if intent == "show_recent_response_feedback":
        feedback_items = memory.get_recent_response_feedback()
        return format_recent_response_feedback(feedback_items)

    if intent == "chat_feedback_dashboard":
        stats = memory.get_response_feedback_stats()
        recent = memory.get_recent_response_feedback()
        return format_chat_feedback_dashboard(stats, recent)

    if intent == "chat_feedback_for_intent":
        intent_name = parse_feedback_intent_query(user_input)

        if not intent_name:
            return "Use this format: feedback for intent_name"

        feedback_items = memory.get_response_feedback_for_intent(intent_name)
        return format_feedback_for_intent(intent_name, feedback_items)

    if intent == "search_response_feedback":
        query = parse_response_feedback_search(user_input)

        if not query:
            return "What feedback should I search for?"

        results = memory.search_response_feedback(query)
        return format_feedback_search_results(query, results)

    if intent == "filter_response_feedback_by_value":
        value = parse_feedback_value_filter(user_input)

        if value == "not helpful":
            value = "not_helpful"

        if value not in ["helpful", "not_helpful"]:
            return "Use this format: feedback value helpful or feedback value not_helpful"

        results = memory.get_response_feedback_by_value(value)
        return format_feedback_by_value(value, results)

    if intent == "filter_response_feedback_by_group":
        group = parse_feedback_group_filter(user_input)

        if group not in ["chat", "memory", "action", "control", "basic", "unknown"]:
            return "Use this format: feedback group chat/memory/action/control/basic/unknown"

        results = memory.get_response_feedback_by_group(group)
        return format_feedback_by_group(group, results)

    if intent == "response_feedback_health":
        health = memory.get_response_feedback_health()
        return format_response_feedback_health(health)

    if intent == "response_feedback_summary":
        stats = memory.get_response_feedback_stats()
        return personality.summarize_response_feedback(stats)

    if intent == "problem_feedback_intents":
        results = memory.get_problem_feedback_intents()
        return format_problem_feedback_intents(results)

    if intent == "helpful_feedback_intents":
        results = memory.get_helpful_feedback_intents()
        return format_helpful_feedback_intents(results)

    if intent == "chat_improvement_target":
        target = memory.get_response_improvement_target()
        return personality.respond_to_improvement_target(target)

    if intent == "show_feedback_notes":
        notes = memory.get_response_feedback_notes()
        return format_feedback_notes(notes)
    
    if intent in ["chat_response_helpful", "chat_response_not_helpful"]:
        last_intent = memory.get_state_value("last_response_intent")
        last_group = memory.get_state_value("last_response_group")
        last_text = memory.get_state_value("last_response_text")

        feedback_value = "helpful" if intent == "chat_response_helpful" else "not_helpful"

        feedback = build_response_feedback(
            feedback_value,
            last_intent,
            last_group,
            last_text,
            current_timestamp()
        )

        memory.add_response_feedback(feedback)
        return format_response_feedback_saved(feedback_value)

    if intent == "cleanup_response_feedback":
        removed_count = memory.cleanup_response_feedback()
        return format_response_feedback_cleanup(removed_count)

    if intent == "preview_clear_response_feedback":
        preview = memory.preview_clear_response_feedback()
        return format_clear_response_feedback_preview(preview)

    if intent == "clear_response_feedback":
        preview = memory.preview_clear_response_feedback()

        if preview["total"] == 0:
            return "There is no response feedback to clear."

        memory.set_state_value("pending_response_feedback_clear", True)
        return format_clear_response_feedback_prompt(preview["total"])

    if intent == "chat_feedback_note":
        note = parse_feedback_note(user_input)

        if not note:
            return "What feedback note should I save?"

        memory.add_response_feedback_note(note)
        return format_feedback_note_saved(note)

    if intent == "delete_feedback_note":
        recent_index = parse_delete_feedback_note(user_input)

        if recent_index is None:
            return "Use this format: delete feedback note number"

        result = memory.delete_response_feedback_note(recent_index)
        return format_delete_feedback_note_result(result)

    return None