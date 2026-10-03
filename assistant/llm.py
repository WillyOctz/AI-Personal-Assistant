import os
import json

from google import genai
from google.genai import types
from pydantic import BaseModel

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

GEMINI_EMBEDDING_DIMENSIONS = 768

class CommandProposal(BaseModel):
    reply: str
    suggested_command: str | None = None
    
GROQ_COMMAND_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {
            "type": "string",
        },
        "suggested_command": {
            "type": ["string", "null"],
        },
    },
    "required": [
        "reply",
        "suggested_command",
    ],
    "additionalProperties": False,
}

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
            response_schema=CommandProposal,
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
            
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=config,
        )
        
        proposal = CommandProposal.model_validate_json(
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
        
def get_groq_command_proposal(user_message, system_instruction=None):
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return {
            "ok": False,
            "provider": "groq",
            "reply": "",
            "suggested_command": None,
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
            temperature=0.4,
            max_completion_tokens=300,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "nebula_command_proposal",
                    "strict": True,
                    "schema": GROQ_COMMAND_PROPOSAL_SCHEMA,
                },
            },
        )
        
        content = (
            completion.choices[0].message.content or ""
        ).strip()
        
        proposal = CommandProposal.model_validate(
            json.loads(content)
        )
        
        return {
            "ok": True,
            "provider": "groq",
            "reply": proposal.reply.strip(),
            "suggested_command": proposal.suggested_command,
            "error": None,
        }
        
    except Exception as error:
        return {
            "ok": False,
            "provider": "groq",
            "reply": "",
            "suggested_command": None,
            "error": str(error),
        }
        
def get_llm_command_proposal(user_message, system_instruction=None):
    gemini_result = get_gemini_command_proposal(
        user_message,
        system_instruction,
    )
    
    if gemini_result["ok"]:
        return gemini_result
    
    groq_result = get_groq_command_proposal(
        user_message,
        system_instruction,
    )
    
    if groq_result["ok"]:
        return groq_result
    
    return {
        "ok": False,
        "provider": "none",
        "reply": "",
        "suggested_command": None,
        "error": (
            "Gemini failed: "
            + gemini_result["error"]
            + " | Groq failed: "
            + groq_result["error"]
        ),
    }
    
def get_gemini_embedding(text):
    api_key = os.getenv("GEMINI_API_KEY")
    clean_text = str(text or "").strip()
    
    if not api_key:
        return {
            "ok": False,
            "provider": "gemini",
            "vector": [],
            "dimensions": 0,
            "error": "GEMINI_API_KEY is not configured.",
        }
        
    if not clean_text:
        return {
            "ok": False,
            "provider": "gemini",
            "vector": [],
            "dimensions": 0,
            "error": "Text cannot be empty.",
        }
        
    try:
        client = genai.Client(api_key=api_key)
        
        response = client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=clean_text,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
                output_dimensionality=GEMINI_EMBEDDING_DIMENSIONS,
            ),
        )
        
        if not response.embeddings:
            return {
                "ok": False,
                "provider": "gemini",
                "vector": [],
                "dimensions": 0,
                "error": "Gemini returned no embedding.",
            }
            
        vector = list(response.embeddings[0].values)
        
        return {
            "ok": True,
            "provider": "gemini",
            "vector": vector,
            "dimensions": len(vector),
            "error": None,
        }
    
    except Exception as error:
        return {
            "ok": False,
            "provider": "gemini",
            "vector": [],
            "dimensions": 0,
            "error": str(error),
        }