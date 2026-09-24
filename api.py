from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from assistant import memory

from assistant.brain import (
    get_response,
    get_startup_notification_message,
)

from assistant.database import (
    get_database_status,
    get_sqlite_migration_status,
    initialize_database,
)

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
    
class ChatResponse(BaseModel):
    input: str
    response: str
    
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
    
@app.get("/startup", response_model=StartupResponse)
def startup_message():
    return {
        "message": get_startup_notification_message(),
    }
    
@app.get("/conversation", response_model=ConversationResponse)
def conversation_history(limit: int = 20):
    safe_limit = max(1, min(limit, 50))
    
    return {
        "turns": memory.get_conversation(safe_limit),
    }
    
@app.get("/reminders", response_model=ReminderListResponse)
def reminder_list():
    return {
        "reminders": memory.get_reminders(),
    }
    
@app.post(
    "/reminders/{position}/complete",
    response_model=CompleteReminderResponse,
    responses={
        404: {"description": "Reminder not found"}
    },
)
def complete_reminder(position: int):
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
        response = get_response(message)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Nebula could not process that message.",
        ) from error
        
    if not isinstance(response, str):
        raise HTTPException(
            status_code=500,
            detail="Nebula returned an invalid response.",
        )
        
    return {
        "input": message,
        "response": response,
    }
