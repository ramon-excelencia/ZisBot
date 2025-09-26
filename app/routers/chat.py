from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import uuid

from app.databases.mongodb import Conversation, ConversationMessage, get_conversation_repo
from app.services.enhanced_langchain_service import get_enhanced_chatbot_service
from app.services.auth import auth_service
from app.providers.factory import ProviderFactory
from app.providers.base import ProviderConfig


router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    user_id: str  # phone number or user identifier
    hospital_id: str
    conversation_id: Optional[str] = None
    provider: str = "zismed"


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: datetime


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send message to AI chatbot"""
    try:
        # Get or create conversation
        repo = await get_conversation_repo()
        
        if request.conversation_id:
            conversation = await repo.get_conversation(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                conversation_id=conversation_id,
                user_id=request.user_id,
                hospital_id=request.hospital_id,
                provider=request.provider,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repo.create_conversation(conversation)
        
        # Add user message to conversation
        user_message = ConversationMessage(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        )
        await repo.add_message(conversation.conversation_id, user_message)
        
        # Get AI response with enhanced memory
        chatbot = await get_enhanced_chatbot_service()
        ai_response = await chatbot.process_message(
            user_message=request.message,
            conversation_id=conversation.conversation_id,
            user_id=request.user_id,
            hospital_id=request.hospital_id
        )
        
        # Add AI response to conversation
        ai_message = ConversationMessage(
            role="assistant",
            content=ai_response,
            timestamp=datetime.utcnow()
        )
        await repo.add_message(conversation.conversation_id, ai_message)
        
        return ChatResponse(
            response=ai_response,
            conversation_id=conversation.conversation_id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error processing message")


@router.get("/appointments/{dni}")
async def get_appointments(dni: str, hospital_id: str):
    """Get patient appointments by DNI"""
    try:
        chatbot = await get_enhanced_chatbot_service()
        response = await chatbot.get_appointment_info(dni, hospital_id)
        return {"message": response}
    except Exception as e:
        print(f"Error getting appointments: {e}")
        raise HTTPException(status_code=500, detail="Error getting appointments")


@router.get("/professionals/{hospital_id}")
async def get_professionals(hospital_id: str, specialty: Optional[str] = None):
    """Get professionals in hospital"""
    try:
        chatbot = await get_enhanced_chatbot_service()
        response = await chatbot.get_professionals_info(hospital_id, specialty)
        return {"message": response}
    except Exception as e:
        print(f"Error getting professionals: {e}")
        raise HTTPException(status_code=500, detail="Error getting professionals")


@router.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str, hospital_id: str):
    """Get user's conversation history"""
    try:
        repo = await get_conversation_repo()
        conversations = await repo.get_user_conversations(user_id, hospital_id)
        return conversations
    except Exception as e:
        print(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversations")