import os

from google import genai
from google.genai import types
from pydantic import BaseModel

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

class GeminiCommandProposal(BaseModel):
    reply: str
    suggested_command: str | None = None

def get_gemini_response(user_message, system_instruction=None):
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {
            "ok": False,
            "provider": "gemini",
            "text": "",
            "error": "GEMINI_API_KEY is not configured.",
        }
        
    try:
        client = genai.Client(api_key=api_key)
        
        config = types.GenerateContentConfig(
            max_output_tokens=300,
            temperature=0.7
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
            
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=config
        )
        
        text = (response.text or "").strip()
        
        if not text:
            return {
                "ok": False,
                "provider": "gemini",
                "text": "",
                "error": "Gemini returned an empty response.",
            }
            
        return {
            "ok": True,
            "provider": "gemini",
            "text": text,
            "error": None,
        }
        
    except Exception as error:
        return {
            "ok": False,
            "provider": "gemini",
            "text": "",
            "error": str(error),
        }
        
def get_gemini_command_proposal(user_message, system_instruction=None):
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {
            "ok": False,
            "provider": "gemini",
            "reply": "",
            "suggested_command": None,
            "error": "GEMINI_API_KEY is not configured.",
        }
        
    try:
        client = genai.Client(api_key=api_key)
        
        config = types.GenerateContentConfig(
            max_output_tokens=300,
            temperature=0.4,
            response_mime_type="application/json",
            response_schema=GeminiCommandProposal,
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
            
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=config,
        )
        
        proposal = GeminiCommandProposal.model_validate_json(
            response.text
        )
        
        return {
            "ok": True,
            "provider": "gemini",
            "reply": proposal.reply.strip(),
            "suggested_command": proposal.suggested_command,
            "error": None,
        }
    
    except Exception as error:
        return {
            "ok": False,
            "provider": "gemini",
            "reply": "",
            "suggested_command": None,
            "error": str(error),
        }
        
def get_groq_response(user_message, system_instruction=None):
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return {
            "ok": False,
            "provider": "groq",
            "text": "",
            "error": "GROQ_API_KEY is not configured.",
        }
        
    try:
        from groq import Groq
        
        messages = []
        
        if system_instruction:
            messages.append({
                "role": "system", 
                "content": system_instruction,
            })
            
        messages.append({
            "role": "user", 
            "content": user_message,
        })
        
        client = Groq(api_key=api_key)
        
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_completion_tokens=300,
        )
        
        text = (
            completion.choices[0].message.content or ""
        ).strip()
        
        if not text:
            return {
               "ok": False,
                "provider": "groq",
                "text": "",
                "error": "Groq returned an empty response.", 
            }
            
        return {
            "ok": True,
            "provider": "groq",
            "text": text,
            "error": None,
        }
        
    except Exception as err:
        return {
            "ok": False,
            "provider": "groq",
            "text": "",
            "error": str(err),
        }