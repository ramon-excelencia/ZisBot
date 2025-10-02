"""
Servicio de Auditoría y Trazabilidad con MongoDB
Registra todas las consultas del chatbot para cumplir criterios de aceptación
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import os

logger = logging.getLogger(__name__)

class AuditService:
    """
    Servicio de auditoría que registra todas las consultas en MongoDB
    Cumple con el requisito: "Cada consulta quedará registrada con fecha,
    usuario, motivo/tipo de consulta y paciente/servicio involucrado"
    """

    def __init__(self):
        mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        mongo_db = os.getenv("MONGODB_DATABASE", "zismed_chatbot")

        try:
            self.client = AsyncIOMotorClient(mongo_url)
            self.db = self.client[mongo_db]
            self.audit_collection = self.db["audit_logs"]
            self.conversations_collection = self.db["conversations"]
            logger.info(f"✅ MongoDB conectado: {mongo_url}/{mongo_db}")
        except Exception as e:
            logger.error(f"❌ Error conectando MongoDB: {e}")
            self.client = None
            self.db = None

    async def log_query(
        self,
        user_id: str,
        user_name: str,
        conversation_id: str,
        query_type: str,
        user_message: str,
        bot_response: str,
        hospital_id: str = "3",
        data_accessed: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Registrar una consulta en el log de auditoría

        Args:
            user_id: ID del usuario
            user_name: Nombre del usuario
            conversation_id: ID de la conversación
            query_type: Tipo de consulta (horarios_atencion, camas_disponibles, etc.)
            user_message: Mensaje original del usuario
            bot_response: Respuesta generada
            hospital_id: ID del hospital (default: 3)
            data_accessed: Datos específicos accedidos (paciente, servicio, etc.)
            metadata: Metadata adicional
        """
        if not self.client:
            logger.warning("⚠️ MongoDB no disponible, no se registra auditoría")
            return False

        try:
            audit_record = {
                "timestamp": datetime.utcnow(),
                "user_id": user_id,
                "user_name": user_name,
                "conversation_id": conversation_id,
                "hospital_id": hospital_id,

                # Tipo de consulta y contenido
                "query_type": query_type,
                "user_message": user_message,
                "bot_response": bot_response,

                # Trazabilidad de datos accedidos
                "data_accessed": data_accessed or {},

                # Metadata adicional
                "metadata": metadata or {},

                # Info técnica
                "created_at": datetime.utcnow()
            }

            result = await self.audit_collection.insert_one(audit_record)
            logger.info(f"📝 Auditoría registrada: {result.inserted_id} | Tipo: {query_type}")
            return True

        except Exception as e:
            logger.error(f"❌ Error registrando auditoría: {e}")
            return False

    async def log_data_access(
        self,
        user_id: str,
        access_type: str,
        resource_type: str,
        resource_id: str,
        action: str,
        success: bool,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Registrar acceso a datos sensibles (pacientes, historias clínicas)

        Args:
            user_id: ID del usuario
            access_type: Tipo de acceso (read, search, etc.)
            resource_type: Tipo de recurso (paciente, historia_clinica, etc.)
            resource_id: ID del recurso
            action: Acción realizada
            success: Si el acceso fue exitoso
            metadata: Información adicional
        """
        if not self.client:
            return False

        try:
            access_record = {
                "timestamp": datetime.utcnow(),
                "user_id": user_id,
                "access_type": access_type,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "success": success,
                "metadata": metadata or {},
                "created_at": datetime.utcnow()
            }

            result = await self.audit_collection.insert_one(access_record)
            logger.info(f"🔐 Acceso registrado: {access_type} | Recurso: {resource_type}/{resource_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error registrando acceso: {e}")
            return False

    async def get_user_query_history(
        self,
        user_id: str,
        limit: int = 50,
        query_type: Optional[str] = None
    ) -> list:
        """
        Obtener historial de consultas de un usuario
        Útil para análisis y reportes
        """
        if not self.client:
            return []

        try:
            query = {"user_id": user_id}
            if query_type:
                query["query_type"] = query_type

            cursor = self.audit_collection.find(query).sort("timestamp", -1).limit(limit)
            records = await cursor.to_list(length=limit)

            # Convertir ObjectId a string para JSON
            for record in records:
                record["_id"] = str(record["_id"])

            return records

        except Exception as e:
            logger.error(f"❌ Error obteniendo historial: {e}")
            return []

    async def get_query_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Obtener estadísticas de consultas
        Útil para dashboards y reportes administrativos
        """
        if not self.client:
            return {}

        try:
            match_stage = {}
            if start_date or end_date:
                match_stage["timestamp"] = {}
                if start_date:
                    match_stage["timestamp"]["$gte"] = start_date
                if end_date:
                    match_stage["timestamp"]["$lte"] = end_date

            pipeline = [
                {"$match": match_stage} if match_stage else {"$match": {}},
                {
                    "$group": {
                        "_id": "$query_type",
                        "count": {"$sum": 1},
                        "users": {"$addToSet": "$user_id"}
                    }
                },
                {"$sort": {"count": -1}}
            ]

            cursor = self.audit_collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)

            # Formatear resultados
            stats = {
                "total_queries": sum(r["count"] for r in results),
                "unique_users": len(set(u for r in results for u in r["users"])),
                "by_type": {r["_id"]: r["count"] for r in results}
            }

            return stats

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}

    async def save_conversation(
        self,
        conversation_id: str,
        user_id: str,
        messages: list,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Guardar conversación completa en MongoDB
        Backup persistente de Redis
        """
        if not self.client:
            return False

        try:
            conversation_record = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "messages": messages,
                "metadata": metadata or {},
                "last_updated": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }

            await self.conversations_collection.update_one(
                {"conversation_id": conversation_id},
                {"$set": conversation_record},
                upsert=True
            )

            return True

        except Exception as e:
            logger.error(f"❌ Error guardando conversación: {e}")
            return False

# Singleton instance
audit_service = AuditService()
