from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from assistant.brain import (
    get_response,
    get_startup_notification_message,
)

app = FastAPI(title="Nebula API")

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
    return {
        "ok": True,
        "assistant": "Nebula",
    }
    
@app.get("/startup")
def startup_message():
    return {
        "message": get_startup_notification_message(),
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