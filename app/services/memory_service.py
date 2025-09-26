"""
Servicio híbrido de memoria para chatbot
Combina Redis (velocidad) con MongoDB (persistencia)
"""

import logging
import redis
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Estructura de mensaje de chat"""
    timestamp: datetime
    user_id: str
    user_name: str
    message: str
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    session_id: Optional[str] = None

@dataclass
class ChatSession:
    """Estructura de sesión de chat"""
    session_id: str
    user_id: str
    user_name: str
    start_time: datetime
    last_activity: datetime
    messages: List[Dict] = None
    total_messages: int = 0

class HybridMemoryService:
    """Servicio híbrido de memoria Redis + MongoDB"""

    def __init__(self):
        # Redis para memoria rápida
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Redis conectado para memoria rápida")
        except Exception as e:
            logger.error(f"❌ Error conectando Redis: {e}")
            self.redis_client = None

        # MongoDB para persistencia
        try:
            self.mongo_client = MongoClient('mongodb://localhost:27017/')
            self.db = self.mongo_client['zisbot']
            self.sessions_collection = self.db['chat_sessions']
            self.messages_collection = self.db['chat_messages']
            logger.info("✅ MongoDB conectado para persistencia")
        except Exception as e:
            logger.error(f"❌ Error conectando MongoDB: {e}")
            self.mongo_client = None

        self.redis_session_ttl = 3600  # 1 hora
        self.context_window = 10  # Últimos 10 mensajes en Redis

    async def get_conversation_context(self, session_id: str) -> List[Dict]:
        """Obtener contexto de conversación (híbrido Redis+MongoDB)"""
        context = []

        try:
            # 1. Intentar obtener de Redis (rápido)
            if self.redis_client:
                redis_key = f"context:{session_id}"
                redis_context = self.redis_client.get(redis_key)
                if redis_context:
                    context = json.loads(redis_context)
                    logger.info(f"📚 Contexto obtenido de Redis: {len(context)} mensajes")
                    return context

            # 2. Si no está en Redis, obtener de MongoDB
            if self.mongo_client:
                messages = list(self.messages_collection
                    .find({"session_id": session_id})
                    .sort("timestamp", -1)
                    .limit(self.context_window))

                context = [{
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": msg.get("message", "") if i % 2 == 0 else msg.get("response", ""),
                    "timestamp": msg.get("timestamp"),
                    "intent": msg.get("intent")
                } for i, msg in enumerate(reversed(messages))]

                # Guardar en Redis para próximas consultas
                if self.redis_client and context:
                    self.redis_client.setex(
                        f"context:{session_id}",
                        self.redis_session_ttl,
                        json.dumps(context, default=str)
                    )

                logger.info(f"📚 Contexto obtenido de MongoDB: {len(context)} mensajes")

        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto: {e}")

        return context

    async def save_message(self, message: ChatMessage) -> bool:
        """Guardar mensaje en ambas memorias"""
        try:
            # 1. Guardar en MongoDB (persistencia)
            if self.mongo_client:
                message_doc = {
                    "session_id": message.session_id,
                    "user_id": message.user_id,
                    "user_name": message.user_name,
                    "message": message.message,
                    "response": message.response,
                    "intent": message.intent,
                    "confidence": message.confidence,
                    "timestamp": message.timestamp
                }
                self.messages_collection.insert_one(message_doc)
                logger.info(f"💾 Mensaje guardado en MongoDB")

            # 2. Actualizar contexto en Redis
            if self.redis_client:
                redis_key = f"context:{message.session_id}"

                # Obtener contexto actual
                current_context = []
                redis_context = self.redis_client.get(redis_key)
                if redis_context:
                    current_context = json.loads(redis_context)

                # Agregar nuevo intercambio
                current_context.extend([
                    {
                        "role": "user",
                        "content": message.message,
                        "timestamp": message.timestamp.isoformat(),
                        "intent": message.intent
                    },
                    {
                        "role": "assistant",
                        "content": message.response,
                        "timestamp": message.timestamp.isoformat(),
                        "intent": message.intent
                    }
                ])

                # Mantener solo últimos mensajes
                if len(current_context) > self.context_window * 2:
                    current_context = current_context[-self.context_window * 2:]

                # Guardar contexto actualizado
                self.redis_client.setex(
                    redis_key,
                    self.redis_session_ttl,
                    json.dumps(current_context, default=str)
                )
                logger.info(f"⚡ Contexto actualizado en Redis: {len(current_context)} mensajes")

            return True

        except Exception as e:
            logger.error(f"❌ Error guardando mensaje: {e}")
            return False

    async def create_or_update_session(self, session_id: str, user_id: str, user_name: str) -> bool:
        """Crear o actualizar sesión"""
        try:
            if self.mongo_client:
                session_doc = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }

                self.sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": session_doc, "$setOnInsert": {"start_time": datetime.now()}},
                    upsert=True
                )
                logger.info(f"📝 Sesión actualizada: {session_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Error actualizando sesión: {e}")
            return False

    async def get_user_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Obtener historial del usuario"""
        try:
            if self.mongo_client:
                messages = list(self.messages_collection
                    .find({"user_id": user_id})
                    .sort("timestamp", -1)
                    .limit(limit))
                return messages
        except Exception as e:
            logger.error(f"❌ Error obteniendo historial: {e}")
        return []

# Instancia global del servicio
hybrid_memory = HybridMemoryService()