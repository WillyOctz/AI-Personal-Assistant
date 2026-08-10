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