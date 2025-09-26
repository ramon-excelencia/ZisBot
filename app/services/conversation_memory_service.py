"""
Servicio de memoria conversacional avanzado para ZisBot
Mantiene contexto e historial de conversaciones para respuestas inteligentes
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

class ConversationMessage(BaseModel):
    """Mensaje de conversación"""
    timestamp: datetime
    user_message: str
    bot_response: str
    intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    hospital_id: str = "3"

class ConversationContext(BaseModel):
    """Contexto de conversación"""
    conversation_id: str
    user_id: str
    hospital_id: str
    last_activity: datetime
    messages: List[ConversationMessage] = []
    user_preferences: Dict[str, Any] = {}
    current_topic: Optional[str] = None
    patient_context: Optional[Dict[str, Any]] = None

class ConversationMemoryService:
    """Servicio de memoria conversacional avanzado"""

    def __init__(self):
        # Memoria en RAM para acceso rápido
        self.active_conversations: Dict[str, ConversationContext] = {}
        # Configuración
        self.max_messages_per_conversation = 50
        self.conversation_timeout_hours = 24
        logger.info("🧠 Servicio de memoria conversacional inicializado")

    def get_conversation_context(self, conversation_id: str, user_id: str, hospital_id: str = "3") -> ConversationContext:
        """Obtener o crear contexto de conversación"""
        try:
            # Buscar conversación existente
            if conversation_id in self.active_conversations:
                context = self.active_conversations[conversation_id]

                # Verificar si no ha expirado
                if datetime.now() - context.last_activity < timedelta(hours=self.conversation_timeout_hours):
                    context.last_activity = datetime.now()
                    logger.info(f"🔄 Contexto existente recuperado para {conversation_id}")
                    return context
                else:
                    # Conversación expirada, crear nueva
                    logger.info(f"⏰ Conversación {conversation_id} expirada, creando nueva")
                    del self.active_conversations[conversation_id]

            # Crear nueva conversación
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                hospital_id=hospital_id,
                last_activity=datetime.now(),
                messages=[],
                user_preferences={},
                current_topic=None,
                patient_context=None
            )

            self.active_conversations[conversation_id] = context
            logger.info(f"✨ Nueva conversación creada: {conversation_id}")
            return context

        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto de conversación: {e}")
            # Fallback: crear contexto básico
            return ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                hospital_id=hospital_id,
                last_activity=datetime.now()
            )

    def add_message(self, conversation_id: str, user_message: str, bot_response: str,
                   intent: str = None, metadata: Dict[str, Any] = None) -> None:
        """Agregar mensaje a la conversación"""
        try:
            if conversation_id in self.active_conversations:
                context = self.active_conversations[conversation_id]

                # Crear mensaje
                message = ConversationMessage(
                    timestamp=datetime.now(),
                    user_message=user_message,
                    bot_response=bot_response,
                    intent=intent,
                    metadata=metadata or {},
                    hospital_id=context.hospital_id
                )

                # Agregar mensaje
                context.messages.append(message)
                context.last_activity = datetime.now()

                # Mantener solo los últimos N mensajes
                if len(context.messages) > self.max_messages_per_conversation:
                    context.messages = context.messages[-self.max_messages_per_conversation:]

                # Actualizar tópico actual basado en intent
                if intent:
                    context.current_topic = intent

                logger.info(f"💬 Mensaje agregado a conversación {conversation_id} (total: {len(context.messages)})")

        except Exception as e:
            logger.error(f"❌ Error agregando mensaje: {e}")

    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Obtener historial de conversación"""
        try:
            if conversation_id in self.active_conversations:
                context = self.active_conversations[conversation_id]
                return context.messages[-limit:] if limit > 0 else context.messages
            return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo historial: {e}")
            return []

    def get_context_summary(self, conversation_id: str) -> str:
        """Generar resumen de contexto para IA"""
        try:
            if conversation_id not in self.active_conversations:
                return "Nueva conversación sin historial previo."

            context = self.active_conversations[conversation_id]

            if not context.messages:
                return "Nueva conversación sin mensajes previos."

            # Obtener últimos 5 mensajes
            recent_messages = context.messages[-5:]

            summary_parts = []

            # Información del contexto
            summary_parts.append(f"Hospital ID: {context.hospital_id}")
            summary_parts.append(f"Usuario: {context.user_id}")

            if context.current_topic:
                summary_parts.append(f"Tópico actual: {context.current_topic}")

            if context.patient_context:
                summary_parts.append(f"Paciente en contexto: {context.patient_context.get('nombre', 'N/A')}")

            # Historial reciente
            summary_parts.append("\nHistorial reciente:")
            for msg in recent_messages:
                timestamp = msg.timestamp.strftime("%H:%M")
                summary_parts.append(f"[{timestamp}] Usuario: {msg.user_message[:100]}...")
                summary_parts.append(f"[{timestamp}] Bot: {msg.bot_response[:100]}...")

            return "\n".join(summary_parts)

        except Exception as e:
            logger.error(f"❌ Error generando resumen de contexto: {e}")
            return "Error obteniendo contexto de conversación."

    def set_patient_context(self, conversation_id: str, patient_data: Dict[str, Any]) -> None:
        """Establecer contexto de paciente actual"""
        try:
            if conversation_id in self.active_conversations:
                context = self.active_conversations[conversation_id]
                context.patient_context = patient_data
                logger.info(f"👤 Contexto de paciente establecido para {conversation_id}")
        except Exception as e:
            logger.error(f"❌ Error estableciendo contexto de paciente: {e}")

    def get_smart_suggestions(self, conversation_id: str, current_message: str) -> List[str]:
        """Generar sugerencias inteligentes basadas en contexto"""
        try:
            suggestions = []

            if conversation_id in self.active_conversations:
                context = self.active_conversations[conversation_id]

                # Sugerencias basadas en tópico actual
                if context.current_topic == "PATIENT_SEARCH_DNI":
                    suggestions.extend([
                        "¿Quieres buscar más información de este paciente?",
                        "¿Necesitas ver los turnos de este paciente?",
                        "¿Quieres buscar otro paciente?"
                    ])
                elif context.current_topic == "SPECIALTIES_INFO":
                    suggestions.extend([
                        "¿Quieres ver prestadores de alguna especialidad específica?",
                        "¿Necesitas agendar un turno?",
                        "¿Quieres ver disponibilidad de especialistas?"
                    ])
                elif context.current_topic == "BEDS_STATUS":
                    suggestions.extend([
                        "¿Quieres ver el estado por sectores?",
                        "¿Necesitas información de internación?",
                        "¿Quieres consultar disponibilidad de UCI?"
                    ])

                # Sugerencias basadas en paciente en contexto
                if context.patient_context:
                    patient_name = context.patient_context.get('nombre', 'paciente')
                    suggestions.extend([
                        f"¿Quieres ver los turnos de {patient_name}?",
                        f"¿Necesitas información médica de {patient_name}?",
                        f"¿Quieres buscar el historial de {patient_name}?"
                    ])

            # Sugerencias generales si no hay contexto específico
            if not suggestions:
                suggestions = [
                    "¿En qué puedo ayudarte con el hospital?",
                    "¿Quieres buscar un paciente?",
                    "¿Necesitas información sobre especialidades?",
                    "¿Quieres consultar disponibilidad de camas?"
                ]

            return suggestions[:3]  # Máximo 3 sugerencias

        except Exception as e:
            logger.error(f"❌ Error generando sugerencias: {e}")
            return ["¿En qué puedo ayudarte?"]

    def cleanup_expired_conversations(self) -> int:
        """Limpiar conversaciones expiradas"""
        try:
            expired_count = 0
            expired_conversations = []

            cutoff_time = datetime.now() - timedelta(hours=self.conversation_timeout_hours)

            for conv_id, context in self.active_conversations.items():
                if context.last_activity < cutoff_time:
                    expired_conversations.append(conv_id)

            for conv_id in expired_conversations:
                del self.active_conversations[conv_id]
                expired_count += 1

            if expired_count > 0:
                logger.info(f"🧹 {expired_count} conversaciones expiradas limpiadas")

            return expired_count

        except Exception as e:
            logger.error(f"❌ Error limpiando conversaciones: {e}")
            return 0

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de conversaciones"""
        try:
            total_conversations = len(self.active_conversations)
            total_messages = sum(len(ctx.messages) for ctx in self.active_conversations.values())

            # Conversaciones por tópico
            topics = {}
            for ctx in self.active_conversations.values():
                topic = ctx.current_topic or "GENERAL"
                topics[topic] = topics.get(topic, 0) + 1

            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "conversations_by_topic": topics,
                "active_conversations": list(self.active_conversations.keys())
            }

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}

# Instancia global del servicio de memoria
conversation_memory_service = ConversationMemoryService()