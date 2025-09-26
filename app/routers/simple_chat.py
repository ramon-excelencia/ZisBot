from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Also register under /chat for frontend compatibility
router = APIRouter(prefix="/simple-chat", tags=["Simple Chat"])
chat_compat_router = APIRouter(prefix="/chat", tags=["Chat Compatibility"])

class ChatRequest(BaseModel):
    message: str
    user_id: str
    hospital_id: str = "3"

class FrontendChatRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: Optional[str] = None
    hospital_id: str = "3"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: datetime

@router.post("/message", response_model=ChatResponse)
async def send_simple_message(request: ChatRequest):
    """Simple chatbot endpoint using direct Groq API"""
    
    try:
        # Get Groq API key
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise HTTPException(status_code=500, detail="Groq API not configured")
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        # System prompt for Hospital Regional
        system_prompt = """Eres ZisBot, asistente virtual del Hospital Regional de Santiago del Estero.

INFORMACIÓN DEL HOSPITAL:
- Ubicación: Santiago del Estero, Argentina
- Teléfonos: 22323 (Principal) / 4212121 (Consultorios)
- Especialidades: 52 disponibles
- Profesionales: 565 médicos activos
- Horarios: 07:00-22:00

INSTRUCCIONES:
- Responde siempre en español argentino natural
- Sé profesional pero cálido
- Para emergencias: recomienda llamar al 107 o ir a Guardia (22323)
- Para turnos: mencionar teléfono 4212121
- NO des consejos médicos específicos - derivar a profesionales"""

        # Prepare request payload
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            "max_tokens": 800,
            "temperature": 0.4
        }
        
        # Make request to Groq
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            # Generate conversation ID
            conversation_id = str(uuid.uuid4())
            
            return ChatResponse(
                response=ai_response,
                conversation_id=conversation_id,
                timestamp=datetime.utcnow()
            )
        else:
            print(f"Groq API error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail="AI service error")
            
    except requests.RequestException as e:
        print(f"Network error: {e}")
        raise HTTPException(status_code=500, detail="Network error")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Service error")

@router.get("/health")
async def health_check():
    """Health check for simple chat"""
    groq_configured = bool(os.getenv("GROQ_API_KEY"))
    
    return {
        "status": "healthy",
        "service": "Simple Chat",
        "groq_api_configured": groq_configured,
        "message": "Simple chatbot ready"
    }

# Compatibility endpoints for frontend
@chat_compat_router.post("/message", response_model=ChatResponse)
async def send_message_compat(request: FrontendChatRequest):
    """Frontend compatibility endpoint"""
    # Convert to simple request
    simple_request = ChatRequest(
        message=request.message,
        user_id=request.user_id,
        hospital_id=request.hospital_id
    )
    return await send_simple_message(simple_request)

@chat_compat_router.get("/health")
async def health_check_compat():
    """Frontend compatibility health check"""
    return await health_check()