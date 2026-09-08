from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from assistant.brain import get_response

app = FastAPI(title="Nebula API")

class MessageRequest(BaseModel):
    message: str
    
@app.get("/health")
def health_check():
    return {
        "ok": True,
        "assistant": "Nebula",
    }
    
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