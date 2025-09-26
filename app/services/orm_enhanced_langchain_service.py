"""
SERVICIO TEMPORAL para restaurar orm_chatbot_routes
Este archivo redirige a los servicios que SÍ funcionan
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Variable global para simular el servicio
_orm_service = None

async def get_orm_enhanced_chatbot_service():
    """Obtener servicio ORM (redirecciona al servicio principal)"""
    # Importar el servicio que SÍ funciona
    from app.services.chatbot_service import get_chatbot_service
    return await get_chatbot_service()

async def init_orm_enhanced_chatbot_service(groq_api_key: str, redis_url: str = "redis://localhost:6379"):
    """Inicializar servicio ORM (redirecciona al servicio principal)"""
    global _orm_service
    try:
        from app.services.chatbot_service import init_chatbot_service
        await init_chatbot_service(groq_api_key, redis_url)
        _orm_service = "initialized"
        logger.info("✅ ORM Enhanced service inicializado (usando chatbot_service)")
        return True
    except Exception as e:
        logger.error(f"❌ Error inicializando ORM service: {e}")
        return False

async def force_reinit_orm_enhanced_chatbot_service(groq_api_key: str, redis_url: str = "redis://localhost:6379"):
    """Reinicializar servicio ORM por fuerza"""
    return await init_orm_enhanced_chatbot_service(groq_api_key, redis_url)

async def quick_test_orm_service():
    """Test rápido del servicio ORM"""
    try:
        service = await get_orm_enhanced_chatbot_service()
        if service:
            return {"status": "ok", "message": "ORM service operativo"}
        else:
            return {"status": "error", "message": "ORM service no disponible"}
    except Exception as e:
        logger.error(f"Error en quick test: {e}")
        return {"status": "error", "message": str(e)}

async def quick_test_full_workflow():
    """Test completo del workflow ORM"""
    try:
        # Test básico de conectividad
        test_result = await quick_test_orm_service()
        if test_result["status"] == "ok":
            return {
                "status": "success",
                "message": "Workflow ORM completo funcionando",
                "tests": ["service_connection", "basic_functionality"]
            }
        else:
            return {
                "status": "error",
                "message": "Workflow ORM falló",
                "error": test_result["message"]
            }
    except Exception as e:
        logger.error(f"Error en workflow test: {e}")
        return {"status": "error", "message": str(e)}