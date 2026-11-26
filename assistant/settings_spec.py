from assistant import memory

SPEC = {
    "confirm_path_open":     ("Confirmations", "bool", False, None, "Ask before opening a pinned file/folder"),
    "confirm_project_open":  ("Confirmations", "bool", True,  None, "Ask before opening a project"),
    "confirm_app_launching": ("Confirmations", "bool", True,  None, "Ask before launching a registered app"),
    "index_enabled":  ("Indexing", "bool", True, None, "Scan registered folders in the background"),
    "index_content":  ("Indexing", "bool", True, None, "Read file contents for text search"),
    "index_vectors":  ("Indexing", "bool", True, None, "Embed files for 'similar' search"),
    "recap_llm":      ("Voice", "bool", True, None, "Let the LLM word the daily recap"),
    "verbosity":      ("Voice", "choice", "normal", ("minimal", "normal", "chatty"), "How talkative I am"),
    # conversation memory (Part 2)
    "summarize_sessions":  ("Conversation memory", "bool", True,  None, "Summarise finished conversations automatically"),
    "summary_use_llm":     ("Conversation memory", "bool", True,  None, "Let Gemini/Groq write summaries (else local extract)"),
    "recall_llm_answer":   ("Conversation memory", "bool", False, None, "Let the LLM phrase 'what did we decide' answers"),
    "session_gap_minutes": ("Conversation memory", "int", 30,  (5, 480),   "Idle minutes that end a conversation"),
    "convo_keep_turns":    ("Conversation memory", "int", 300, (50, 5000), "Newest turns that are never archived"),
    "convo_archive_days":  ("Conversation memory", "int", 14,  (1, 365),   "Archive summarised turns older than this"),
    "convo_delete_days":   ("Conversation memory", "int", 90,  (7, 3650),  "Delete archived turns older than this"),
    "history_keep_days":   ("Conversation memory", "int", 90,  (7, 3650),  "Keep the action history this long"),
    "app_search_enabled":   ("Apps", "bool", True,  None, "Search this PC for programs I don't have registered"),
    "app_search_protected": ("Apps", "bool", True,  None, "Also offer programs in Windows/system places (typed approval)"),
    "app_index_hours":      ("Apps", "int",  24, (1, 168), "Hours between background scans for programs"),
}

def get(key):
    return memory.get_setting(key, SPEC[key][2])