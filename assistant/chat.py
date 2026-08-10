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