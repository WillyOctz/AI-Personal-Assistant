import os

from google import genai
from google.genai import types

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

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