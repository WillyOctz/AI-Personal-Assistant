from pathlib import Path
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any
from datetime import date
from assistant import memory, focus, apps, websites, llm, events
from assistant.runtime import BRAIN_LOCK, hooks

import logging

from assistant.reply import Reply
from assistant.brain import (
    get_reply,
    get_startup_notification_message,
    is_safe_llm_command,
)

from assistant.database import (
    get_database_status,
    get_sqlite_migration_status,
    initialize_database,
)

from assistant.llm_evaluation import (
    append_llm_evaluation_case,
    evaluate_llm_command_proposals,
    format_llm_evaluation_report,
)

log = logging.getLogger("nebula.api")
app = FastAPI(title="Nebula API")
initialize_database()

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "website"

app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static",
)

class MessageRequest(BaseModel):
    message: str
    
class ReplyAction(BaseModel):
    label: str
    style: str = "default"
    type: str = "command"
    command: str | None = None
    value: str | None = None
    
class ChatResponse(BaseModel):
    input: str
    response: str                    # full plain text (old clients, history, CLI)
    say: str
    detail: str = ""
    kind: str = "text"
    data: dict[str, Any] = Field(default_factory=dict)
    actions: list[ReplyAction] = Field(default_factory=list)
    needs_confirmation: bool = False
    intent: str | None = None
    
class ConversationTurnResponse(BaseModel):
    user: str
    assistant: str | None = None
    intent: str | None = None
    group: str | None = None
    confidence: float | None = None
    source: str | None = None
    timestamp: str | None = None
    importance: float | None = None
    
class ConversationResponse(BaseModel):
    turns: list[ConversationTurnResponse]
    
class StartupResponse(BaseModel):
    message: str | None = None
    
class ReminderResponse(BaseModel):
    position: int
    text: str
    due: str | None = None
    
class ReminderListResponse(BaseModel):
    reminders: list[ReminderResponse]
    
class CompleteReminderResponse(BaseModel):
    completed: bool
    reminder: str | None = None
    
class CreateReminderRequest(BaseModel):
    text: str
    due: str | None = None
    
class CreateReminderResponse(BaseModel):
    created: bool
    reminder: str
    due: str | None = None
    
class FocusSessionResponse(BaseModel):
    task: str
    started_at: str
    ended_at: str
    duration: str
    duration_seconds: int | None = None
    notes: list[str]
    
class FocusSessionListResponse(BaseModel):
    sessions: list[FocusSessionResponse]
    
class FocusStatusResponse(BaseModel):
    active: bool
    task: str | None = None
    started_at: str | None = None
    notes: list[str]
    
class FocusGoalProgressResponse(BaseModel):
    goal: str | None = None
    progress: int | None = None
    today_focus: str | None = None
    
class RegisteredAppResponse(BaseModel):
    name: str
    allowed: bool

class RegisteredAppListResponse(BaseModel):
    apps: list[RegisteredAppResponse]
    
class RegisteredWebsiteResponse(BaseModel):
    name: str
    url: str
    allowed: bool

class RegisteredWebsiteListResponse(BaseModel):
    websites: list[RegisteredWebsiteResponse]
    
class ProfileResponse(BaseModel):
    facts: dict[str, str]
    
class AppAutomationStatusResponse(BaseModel):
    launching_enabled: bool
    confirmation_enabled: bool
    registered_apps: int
    aliases: int
    allowed_apps: int
    
class WebsiteAutomationStatusResponse(BaseModel):
    opening_enabled: bool
    registered_websites: int
    allowed_websites: int
    pending_website: str | None = None
    
class AutomationStatusResponse(BaseModel):
    apps: AppAutomationStatusResponse
    websites: WebsiteAutomationStatusResponse
    
class LLMEvaluationCaseResponse(BaseModel):
    message: str
    passed: bool
    reason: str
    provider: str | None = None
    suggested_command: str | None = None
    command_is_safe: bool | None = None
    
class LLMEvaluationResponse(BaseModel):
    total: int
    passed: int
    failed: int
    report: str
    results: list[LLMEvaluationCaseResponse]
    
class LLMProviderStatusItemResponse(BaseModel):
    configured: bool
    model: str
    
class LLMProviderStatusResponse(BaseModel):
    gemini: LLMProviderStatusItemResponse
    groq: LLMProviderStatusItemResponse
    chat_available: bool
    embeddings_available: bool
    
class ResponseFeedbackSourceResponse(BaseModel):
    source: str
    total: int
    helpful: int
    not_helpful: int
    helpful_rate: float
    
class ResponseFeedbackSourceListResponse(BaseModel):
    sources: list[ResponseFeedbackSourceResponse]
    
class LLMFeedbackReviewCandidateResponse(BaseModel):
    timestamp: str | None = None
    source: str
    intent: str
    user_input: str
    response_text: str
    
class LLMFeedbackReviewCandidateListResponse(BaseModel):
    candidates: list[LLMFeedbackReviewCandidateResponse]
    
class SaveLLMFeedbackCandidateRequest(BaseModel):
    expected_command: bool
    command_prefix: str = ""


class SaveLLMFeedbackCandidateResponse(BaseModel):
    saved: bool
    message: str
    
class ReminderNotificationItemResponse(BaseModel):
    index: int
    text: str
    due: str


class ReminderNotificationCheckResponse(BaseModel):
    today: str
    due: list[ReminderNotificationItemResponse]
    overdue: list[ReminderNotificationItemResponse]
    marked_count: int
    
@app.get("/health")
def health_check():
    try:
        database_status = get_database_status()
        migration_status = get_sqlite_migration_status()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "ok": False,
                "service": "nebula-api",
                "database": {
                    "ok": False,
                },
            },
        )
        
    return {
        "ok": True,
        "service": "nebula-api",
        "assistant": "Nebula",
        "database": {
            "ok": True,
            "schema_version": database_status["schema_version"],
            "tables": migration_status["row_counts"],
        },
    }
    
@app.get(
    "/llm/status",
    response_model=LLMProviderStatusResponse,
)
def llm_provider_status():
    return llm.get_llm_provider_status()

@app.get(
    "/feedback/response-sources",
    response_model=ResponseFeedbackSourceListResponse,
)
def response_feedback_sources():
    return {
        "sources": memory.get_response_feedback_by_source(),
    }
    
@app.get(
    "/feedback/llm-review-candidates",
    response_model=LLMFeedbackReviewCandidateListResponse,
)
def llm_feedback_review_candidates(limit: int = 5):
    safe_limit = max(1, min(limit, 10))
    
    return {
        "candidates": memory.get_llm_feedback_review_candidates(
            safe_limit,
        )
    }
    
@app.post(
    "/feedback/llm-review-candidates/{candidate_number}/save",
    response_model=SaveLLMFeedbackCandidateResponse,
    responses={
        400: {"description": "Invalid review decision"},
        404: {"description": "Review candidate not found"},
        409: {"description": "Evaluation case already exists"},
    }
)
def save_llm_feedback_candidate(
    candidate_number: int,
    req: SaveLLMFeedbackCandidateRequest,
):
    candidates = memory.get_llm_feedback_review_candidates(limit=10)
    
    if candidate_number < 1 or candidate_number > len(candidates):
        raise HTTPException(
            status_code=404,
            detail="That review candidate does not exist."
        )
        
    command_prefix = req.command_prefix.strip()
    
    if req.expected_command and not command_prefix:
        raise HTTPException(
            status_code=400,
            detail="A command case needs a command prefix.",
        )
        
    candidate = candidates[candidate_number - 1]
    
    with BRAIN_LOCK:
        result = append_llm_evaluation_case(
            candidate["user_input"],
            req.expected_command,
            command_prefix,
        )
    
    if result["reason"] == "duplicate":
        raise HTTPException(
            status_code=409,
            detail="That message is already in the evaluation dataset.",
        )

    if not result["saved"]:
        raise HTTPException(
            status_code=400,
            detail="Nebula could not save that evaluation case.",
        )
    
    if req.expected_command:
        message = (
            f"Saved candidate {candidate_number} as a command case "
            f"with prefix: {command_prefix}"
        )
        
    else:
        message = (
            f"Saved candidate {candidate_number} as a no-command case."
        )
        
    return {
        "saved": True,
        "message": message,
    }
    
@app.get("/startup", response_model=StartupResponse)
def startup_message():
    return {
        "message": get_startup_notification_message(),
    }
    
@app.get("/conversation", response_model=ConversationResponse)
def conversation_history(limit: int = 5):
    safe_limit = max(1, min(limit, 20))
    
    return {
        "turns": memory.get_conversation(safe_limit),
    }
    
@app.get("/reminders", response_model=ReminderListResponse)
def reminder_list():
    return {
        "reminders": memory.get_reminders(),
    }
    
@app.post("/reminders", response_model=CreateReminderResponse,
    responses={
        400: {"description": "Invalid reminder"},
        409: {"description": "Reminder already exists"},
    },
)
def create_reminder(req: CreateReminderRequest):
    text = req.text.strip()
    due = req.due.strip() if req.due else None
    
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Reminder text cannot be empty.",
        )
        
    with BRAIN_LOCK: 
        result = memory.add_reminder(text, due)
    
    if not result["saved"]:
        raise HTTPException(
            status_code=409,
            detail="That reminder already exists.",
        )
        
    return {
        "created": True,
        "reminder": result["reminder"],
        "due": result["due"],
    }
    
@app.post(
    "/reminders/{position}/complete",
    response_model=CompleteReminderResponse,
    responses={
        404: {"description": "Reminder not found"}
    },
)
def complete_reminder(position: int):
    with BRAIN_LOCK:
        result = memory.complete_reminder(str(position))
    
    if not result["removed"]:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found.",
        )
        
    return {
        "completed": True,
        "reminder": result["reminder"],
    }
    
@app.post(
    "/notifications/pending",
    response_model=ReminderNotificationCheckResponse,
)
def collect_pending_reminder_notifications():
    with BRAIN_LOCK:
        result = memory.collect_due_reminder_notifications()
    
    return {
        "today": result["today"],
        "due": result["due"],
        "overdue": result["overdue"],
        "marked_count": result["marked_count"],
    }
    
@app.get(
    "/focus/sessions",
    response_model=FocusSessionListResponse
)
def focus_session_list(limit: int = 5):
    safe_limit = max(1, min(limit, 10))
    
    return {
        "sessions": memory.get_focus_sessions(safe_limit),
    }
    
@app.get(
    "/focus/status",
    response_model=FocusStatusResponse
)
def focus_status():
    active = bool(focus.get_focus_mode())
    
    if not active:
        return {
            "active": False,
            "task": None,
            "started_at": None,
            "notes": [],
        }
        
    return {
        "active": True,
        "task": focus.get_focus_task(),
        "started_at": focus.get_focus_started_at(),
        "notes": focus.get_current_focus_notes(),
    }
    
@app.get(
    "/focus/goal-progress",
    response_model=FocusGoalProgressResponse,
)
def focus_goal_progress():
    summary = focus.get_focus_goal_progress_summary()
    
    if summary is None:
        return {
            "goal": None,
            "progress": None,
            "today_focus": None,
        }
        
    return summary

@app.get(
    "/apps",
    response_model=RegisteredAppListResponse,
)
def registered_app_list():
    registry = memory.get_app_registry()
    
    apps = [
        {
            "name": app["name"],
            "allowed": app["allowed"],
        }
        for app in registry.values()
    ]
    
    return {
        "apps": apps,
    }
    
@app.get(
    "/websites",
    response_model=RegisteredWebsiteListResponse,
)
def registered_website_list():
    registry = memory.get_website_registry()
    
    websites = [
        {
            "name": website["name"],
            "url": website["url"],
            "allowed": website["allowed"],
        }
        for website in registry.values()
    ]
    
    return {
        "websites": websites,
    }
    
@app.get(
    "/profile",
    response_model=ProfileResponse,
)
def profile():
    return {
      "facts": memory.get_profile(),
    }  
    
@app.get(
    "/automation/status",
    response_model=AutomationStatusResponse,
)
def automation_status():
    app_status = apps.get_automation_status()
    website_status = websites.get_website_automation_status()
    
    pending_website = website_status["pending_website"]
    
    return {
        "apps": app_status,
        "websites": {
            "opening_enabled": website_status["opening_enabled"],
            "registered_websites": website_status["registered_websites"],
            "allowed_websites": website_status["allowed_websites"],
            "pending_website": (
                pending_website["name"]
                if pending_website
                else None
            ),
        },
    }
    
@app.post(
    "/evaluations/llm-command-proposals",
    response_model=LLMEvaluationResponse,
    responses={
        500: {"description": "LLM evaluation could not run"},
    },
)
def run_llm_command_proposal_evaluation(
    limit: int | None = None
):
    safe_limit = None
    
    if limit is not None:
        safe_limit = max(1, min(limit, 20))
        
    try:
        evaluation = evaluate_llm_command_proposals(
            limit=safe_limit,
            command_validator=is_safe_llm_command,
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="LLM command-proposal evaluation could not run.",
        ) from error
        
    return {
        "total": evaluation["total"],
        "passed": evaluation["passed"],
        "failed": evaluation["failed"],
        "report": format_llm_evaluation_report(evaluation),
        "results": evaluation["results"],
    }
    
@app.get("/__control/show", include_in_schema=False)
def control_show():
    show = hooks.get("show")
    
    if show:
        show()
        
    return {"ok": bool(show)}

@app.get("/events")
def sse():
    return StreamingResponse(
        events.stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    
@app.get("/today")
def today():
    today_iso = date.today().isoformat()
    reminders = []
    
    for item in memory.get_reminders():
        due_day = memory.get_due_day(item["due"])
        reminders.append({
            **item,
            "overdue": bool(due_day and due_day < today_iso),
            "today": due_day == today_iso,
        })
        
    return {
        "reminders": reminders,
        "focus": focus_status(),
        "goal": focus_goal_progress(),
        "apps": [a for a in registered_app_list()["apps"] if a["allowed"]],
        "websites": [w for w in registered_website_list()["websites"] if w["allowed"]],
    }
    
@app.get("/dev", include_in_schema=False)
def dev_console():
    return FileResponse(WEB_DIR / "dev.html")
       
@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB_DIR / "index.html")
    
@app.post("/chat", response_model=ChatResponse, responses={
    400: {"description": "Invalid message"},
    500: {"description": "Nebula could not process the message"},
})
def chat(req: MessageRequest):
    message = req.message.strip()
    
    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )
        
    try:
        with BRAIN_LOCK:
            reply = get_reply(message)
    except Exception as error:
        log.exception("chat failed for message: %r", message)
        raise HTTPException(
            status_code=500,
            detail="Nebula could not process that message.",
        ) from error
        
    if not isinstance(reply, Reply):
        raise HTTPException(
            status_code=500,
            detail="Nebula returned an invalid response.",
        )
        
    return {
        "input": message,
        "response": reply.full(),
        "say": reply.say,
        "detail": reply.detail,
        "kind": reply.kind,
        "data": reply.data,
        "actions": reply.actions,
        "needs_confirmation": reply.needs_confirmation,
        "intent": reply.intent,
    }
