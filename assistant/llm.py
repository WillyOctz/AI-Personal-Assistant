import os

from google import genai

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

def get_gemini_response(prompt):
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
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
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