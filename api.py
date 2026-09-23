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
    
@app.get("/startup")
def startup_message():
    return {
        "message": get_startup_notification_message(),
    }
    
@app.get("/conversation")
def conversation_history(limit: int = 20):
    safe_limit = max(1, min(limit, 50))
    
    return {
        "turns": memory.get_conversation(safe_limit),
    }
    
@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB_DIR / "index.html")
    
@app.post("/chat")
def chat(req: MessageRequest):
    message = req.message.strip()
    
    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )
        
    res = get_response(message)
    
    return {
        "input": message,
        "response": res, 
    }