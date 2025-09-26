import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class Conversation(BaseModel):
    conversation_id: str
    user_id: str  # phone number or user identifier
    hospital_id: str
    provider: str  # "zismed" | "hcweb"
    messages: List[ConversationMessage] = []
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    context: Optional[Dict[str, Any]] = None  # Patient info, current topic, etc.


class ConversationRepository:
    def __init__(self, mongo_url: str, database_name: str = "multiclinica"):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[database_name]
        self.conversations = self.db.conversations
        self.ai_logs = self.db.ai_logs
    
    async def create_conversation(self, conversation: Conversation) -> str:
        """Create new conversation"""
        conversation_dict = conversation.model_dump()
        result = await self.conversations.insert_one(conversation_dict)
        return str(result.inserted_id)
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        doc = await self.conversations.find_one({"conversation_id": conversation_id})
        if doc:
            return Conversation(**doc)
        return None
    
    async def get_user_conversations(self, user_id: str, hospital_id: str, limit: int = 10) -> List[Conversation]:
        """Get recent conversations for user in specific hospital"""
        cursor = self.conversations.find(
            {"user_id": user_id, "hospital_id": hospital_id}
        ).sort("updated_at", -1).limit(limit)
        
        conversations = []
        async for doc in cursor:
            conversations.append(Conversation(**doc))
        return conversations
    
    async def add_message(self, conversation_id: str, message: ConversationMessage) -> bool:
        """Add message to conversation"""
        result = await self.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$push": {"messages": message.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def update_context(self, conversation_id: str, context: Dict[str, Any]) -> bool:
        """Update conversation context"""
        result = await self.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "context": context,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def close_conversation(self, conversation_id: str) -> bool:
        """Mark conversation as inactive"""
        result = await self.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def get_conversation_history(self, conversation_id: str, last_n_messages: int = 10) -> List[ConversationMessage]:
        """Get recent messages from conversation for memory context"""
        conversation = await self.get_conversation(conversation_id)
        if conversation and conversation.messages:
            # Return last N messages ordered by timestamp
            messages = sorted(conversation.messages, key=lambda x: x.timestamp)
            return messages[-last_n_messages:] if len(messages) > last_n_messages else messages
        return []

    async def get_user_conversation_summary(self, user_id: str, hospital_id: str, days_back: int = 7) -> Dict[str, Any]:
        """Get summary of user's recent conversation activity"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        cursor = self.conversations.find({
            "user_id": user_id,
            "hospital_id": hospital_id,
            "updated_at": {"$gte": cutoff_date}
        })

        total_conversations = 0
        total_messages = 0
        recent_topics = []

        async for doc in cursor:
            conversation = Conversation(**doc)
            total_conversations += 1
            total_messages += len(conversation.messages)

            # Extract topics from last few messages
            if conversation.messages:
                recent_messages = conversation.messages[-3:]  # Last 3 messages
                for msg in recent_messages:
                    if msg.role == "user" and len(msg.content) > 10:
                        recent_topics.append({
                            "content": msg.content[:100],  # First 100 chars
                            "timestamp": msg.timestamp
                        })

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "recent_topics": recent_topics[-5:],  # Last 5 topics
            "period_days": days_back
        }

    async def find_similar_conversations(self, user_id: str, hospital_id: str, keywords: List[str], limit: int = 5) -> List[Dict]:
        """Find conversations with similar keywords for context"""
        # Simple keyword matching - could be improved with embeddings later
        keyword_regex = "|".join(keywords)

        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "hospital_id": hospital_id,
                    "messages.content": {"$regex": keyword_regex, "$options": "i"}
                }
            },
            {
                "$project": {
                    "conversation_id": 1,
                    "updated_at": 1,
                    "relevant_messages": {
                        "$filter": {
                            "input": "$messages",
                            "cond": {
                                "$regexMatch": {
                                    "input": "$$this.content",
                                    "regex": keyword_regex,
                                    "options": "i"
                                }
                            }
                        }
                    }
                }
            },
            {"$sort": {"updated_at": -1}},
            {"$limit": limit}
        ]

        results = []
        async for doc in self.conversations.aggregate(pipeline):
            results.append(doc)
        return results

    async def log_ai_interaction(self, conversation_id: str, prompt: str, response: str,
                                confidence: str, metadata: Optional[Dict] = None):
        """Log AI interaction for analysis"""
        log_entry = {
            "conversation_id": conversation_id,
            "prompt": prompt,
            "response": response,
            "confidence": confidence,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow()
        }
        await self.ai_logs.insert_one(log_entry)


# Global instance
conversation_repo: Optional[ConversationRepository] = None


async def init_mongodb():
    """Initialize MongoDB connection"""
    global conversation_repo
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    conversation_repo = ConversationRepository(mongo_url)


async def get_conversation_repo() -> ConversationRepository:
    """Get conversation repository instance"""
    if conversation_repo is None:
        await init_mongodb()
    return conversation_repo