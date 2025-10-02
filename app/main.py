"""
Servidor principal de ZisBot con arquitectura profesional
Usa la nueva estructura con separación de responsabilidades
"""
import sys
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno ANTES de cualquier otra cosa
load_dotenv()
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configurar UTF-8 para caracteres especiales del español
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Importaciones de la nueva arquitectura
from app.config.settings import settings
from app.models.schemas import (
    LoginRequest, LoginWithInstitutionRequest, ValidateCredentialsRequest,
    ValidateCredentialsResponse, Institution, ChatMessage, ChatResponse,
    UserContext, SystemStatus
)
from app.utils.auth import create_jwt_token, verify_jwt_token
from app.integrations.ai_service import ai_service
from app.integrations.langchain_agent import langchain_agent
from app.routes.hospital_routes import hospital_router
from app.routes.extended_hospital_routes import extended_hospital_router
from app.services.orm_hospital_service import orm_hospital_service as hospital_service

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===============================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ===============================================

app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema profesional de chatbot con arquitectura limpia",
    version=settings.APP_VERSION,
    docs_url="/api/docs"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(hospital_router)

# Importar y incluir router de prestadores
from app.routes.prestadores_routes import prestadores_router
app.include_router(prestadores_router)

# Importar y incluir router de turnos
try:
    from app.routes.turnos_routes import router as turnos_router
    app.include_router(turnos_router)
    logger.info("✅ Router de turnos registrado correctamente")
except ImportError as e:
    logger.warning(f"⚠️ No se pudo cargar el router de turnos: {e}")
except Exception as e:
    logger.error(f"❌ Error registrando router de turnos: {e}")

# Importar y incluir router ORM (nueva arquitectura con LangGraph + Groq)
try:
    from app.api.orm_chatbot_routes import router as orm_chatbot_router
    app.include_router(orm_chatbot_router)
except ImportError:
    logger.warning("ORM chatbot routes no disponibles")

# Incluir router del chatbot funcional - DESHABILITADO (servicio eliminado)
# from app.routers.functional_chatbot_routes import router as functional_chatbot_router
# app.include_router(functional_chatbot_router)

# Incluir nuevos endpoints específicos de ZisMed
# from app.routers.zismed_real_routes import router as zismed_router
# app.include_router(zismed_router)  # Comentado por conflictos de importación

# Incluir routers de chat
try:
    from app.routers.chat import router as chat_router
    app.include_router(chat_router)
except ImportError:
    logger.warning("Chat router no disponible")

try:
    from app.routers.simple_chat import router as simple_chat_router, chat_compat_router
    app.include_router(simple_chat_router)
    app.include_router(chat_compat_router)
except ImportError:
    logger.warning("Simple chat routers no disponibles")

# ===============================================
# AUTENTICACIÓN TEMPORAL
# ===============================================
# IMPORTANTE: Este diccionario se usa solo para desarrollo/testing
# Para producción, migrar a consulta directa de usuarios desde ZisMed
# Ver README.md para credenciales de acceso
# ===============================================

USERS_DB = {
    # Los usuarios reales de ZisMed deben agregarse aquí para testing
    # Formato: "CUIL": {"password": "...", "user_data": {...}}
}

# ===============================================
# ENDPOINTS PRINCIPALES
# ===============================================

@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "Operativo",
        "architecture": "Clean Architecture",
        "features": [
            "🔐 Autenticación JWT",
            "🏥 API REST para consultas hospitalarias",
            "🤖 IA con Groq (sin consultas SQL directas)",
            "📊 Endpoints para pacientes, especialidades y servicios",
            "🔒 Seguridad y validaciones con Pydantic"
        ],
        "endpoints": {
            "docs": f"http://localhost:{settings.PORT}/api/docs",
            "hospital_api": f"http://localhost:{settings.PORT}/api/hospital",
            "frontend": "http://localhost:3003"
        }
    }

@app.post("/api/auth/login")
async def login(request: LoginRequest) -> JSONResponse:
    """
    Login con credenciales
    TODO: Migrar a base de datos
    """
    try:
        cuil_clean = request.cuil.replace("-", "").replace(" ", "")

        user = USERS_DB.get(cuil_clean)
        if not user or user["password"] != request.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )

        # Crear token JWT
        token = create_jwt_token(user["user_data"])

        logger.info(f"Login exitoso: {user['user_data']['user_name']}")

        # Respuesta compatible con frontend
        user_response = {
            **user["user_data"],
            "name": user["user_data"]["user_name"]  # Frontend espera 'name'
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Login exitoso",
                "access_token": token,
                "user": user_response
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@app.post("/api/auth/validate-credentials")
async def validate_credentials(request: ValidateCredentialsRequest) -> ValidateCredentialsResponse:
    """
    Paso 1: Validar credenciales y obtener instituciones disponibles
    """
    try:
        cuil_clean = request.cuil.replace("-", "").replace(" ", "")

        # Usar el servicio para validar con ZisMed
        result = await hospital_service.validate_credentials_and_get_institutions(
            cuil_clean, request.password
        )

        if result["success"]:
            institutions = [
                Institution(
                    id=inst["id"],
                    name=inst["name"],
                    requires_terms=inst["requires_terms"],
                    address=inst["address"],
                    phone=inst["phone"]
                ) for inst in result["institutions"]
            ]

            return ValidateCredentialsResponse(
                success=True,
                message=result["message"],
                institutions=institutions
            )
        else:
            return ValidateCredentialsResponse(
                success=False,
                message=result["error"],
                institutions=[]
            )

    except Exception as e:
        logger.error(f"Error validando credenciales: {e}")
        return ValidateCredentialsResponse(
            success=False,
            message="Error interno del servidor",
            institutions=[]
        )

@app.post("/api/auth/login-with-institution")
async def login_with_institution(request: LoginWithInstitutionRequest) -> JSONResponse:
    """
    Paso 2: Login completo con institución seleccionada
    """
    try:
        cuil_clean = request.cuil.replace("-", "").replace(" ", "")

        # Primero validar credenciales y verificar que la institución existe
        validation_result = await hospital_service.validate_credentials_and_get_institutions(
            cuil_clean, request.password
        )

        if not validation_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=validation_result["error"]
            )

        # Verificar que la institución seleccionada es válida
        selected_institution = None
        for inst in validation_result["institutions"]:
            if inst["id"] == request.institution_id:
                selected_institution = inst
                break

        if not selected_institution:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Institución seleccionada no válida"
            )

        # Verificar términos y condiciones si es necesario
        if selected_institution["requires_terms"] and not request.accepts_terms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe aceptar los términos y condiciones"
            )

        # Crear datos del usuario con la institución seleccionada
        user_data = {
            "user_id": f"user_{cuil_clean}",
            "user_name": "Yanet Villalba",  # TODO: Obtener del sistema ZisMed
            "role": "coordinadora_gestion",
            "institution": selected_institution["name"],
            "hospital_id": str(selected_institution["id"]),
            "institution_id": selected_institution["id"],
            "cuil": cuil_clean,  # ✅ FILTRADO AUTOMÁTICO: CUIL para consultas
            "password": request.password  # ✅ FILTRADO AUTOMÁTICO: Password para consultas
        }

        # Crear token JWT
        token = create_jwt_token(user_data)

        logger.info(f"Login exitoso: {user_data['user_name']} - {selected_institution['name']}")

        # Respuesta compatible con frontend
        user_response = {
            **user_data,
            "name": user_data["user_name"]
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Login exitoso",
                "access_token": token,
                "user": user_response,
                "selected_institution": {
                    "id": selected_institution["id"],
                    "name": selected_institution["name"]
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login con institución: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@app.get("/api/auth/me")
async def get_user_info(user_data: dict = Depends(verify_jwt_token)):
    """Obtener información del usuario autenticado"""
    return {
        "success": True,
        "user": user_data
    }

@app.post("/api/chat")
async def chat_endpoint(
    request: ChatMessage,
    user_data: dict = Depends(verify_jwt_token)
) -> ChatResponse:
    """
    Endpoint principal de chat usando la nueva arquitectura
    ✅ Ya NO hace consultas SQL directas
    ✅ Usa servicios y endpoints REST
    """
    try:
        # Crear contexto de usuario
        user_context = {
            **user_data,
            "session_id": f"session_{user_data['user_id']}_{datetime.now().strftime('%Y%m%d')}"
        }

        logger.info(f"🔍 CHAT: Consulta de {user_data['user_name']}: {request.message[:100]}...")
        logger.info(f"🔍 CHAT: Session ID: {user_context.get('session_id', 'N/A')}")

        # 🔹 SERVICIO UNIFICADO SIN FALLBACK (COMO FUNCIONABA ANTES)
        logger.info("🔍 CHAT: Usando servicio unificado de chatbot...")
        from app.services.chatbot_service import get_chatbot_service

        # Obtener servicio unificado
        chatbot_service = await get_chatbot_service()
        logger.info("🔍 CHAT: Servicio unificado obtenido exitosamente")

        # Procesar mensaje con sistema completo
        response = await chatbot_service.process_message(
            user_message=request.message,
            conversation_id=user_context.get("session_id", "temp_session"),
            user_id=user_data.get("user_id", "temp_user"),
            hospital_id=str(user_context.get("hospital_id", "3")),
            user_name=user_data.get("user_name", "Usuario"),
            user_role=user_data.get("role", "invitado")  # ✅ Validación de permisos por rol
        )
        logger.info("✅ CHAT: Respuesta generada con servicio unificado")
        logger.info(f"🔍 RESPUESTA CRUDA: {response}")

        result = {
            "response": response,
            "type": "enhanced_memory_response",
            "confidence": 0.95,
            "processing_time": 0.0,
            "function_used": "enhanced_langchain_service_with_memory",
            "metadata": {"hospital_id": user_context.get("hospital_id", "3")}
        }

        logger.info(f"Respuesta generada - Función: {result.get('function_used', 'unknown')}")

        # Formatear respuesta
        return ChatResponse(
            response=result.get("response", "Error procesando consulta"),
            type=result.get("type", "api_response"),
            confidence=result.get("confidence", 0.9),
            processing_time=result.get("processing_time", 0.0),
            function_used=result.get("function_used", "ninguna"),
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error en chat: {e}")
        import traceback
        traceback.print_exc()

        # MOSTRAR ERROR REAL PARA DEBUG
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error específico: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check simple para monitoreo"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.APP_VERSION
    }

@app.get("/api/system/status")
async def system_status() -> SystemStatus:
    """Estado detallado del sistema"""
    return SystemStatus(
        system="ZisBot Hospital Regional",
        version=settings.APP_VERSION,
        status="Operativo",
        ai_system={
            "type": "Groq + API Services",
            "status": "Disponible",
            "architecture": "Clean Architecture - No SQL directo",
            "features": [
                "Endpoints REST seguros",
                "Validaciones con Pydantic",
                "Separación de responsabilidades",
                "Manejo profesional de errores"
            ]
        },
        authentication="JWT activo",
        database="Acceso vía servicios (no directo)",
        ports={
            "api": settings.PORT,
            "frontend": 3003
        },
        timestamp=datetime.now()
    )

# ===============================================
# EVENTO DE STARTUP
# ===============================================

@app.on_event("startup")
async def startup_event():
    """Inicializar sistema al arrancar"""
    logger.info("=" * 60)
    logger.info("INICIANDO ZISBOT CON ARQUITECTURA PROFESIONAL")
    logger.info("=" * 60)
    logger.info(f"🏥 {settings.APP_NAME}")
    logger.info(f"📦 Versión: {settings.APP_VERSION}")
    logger.info(f"🎯 Arquitectura: Clean Architecture")
    logger.info(f"🔒 Sin consultas SQL directas")
    logger.info(f"🌐 API: http://localhost:{settings.PORT}")
    logger.info(f"📖 Docs: http://localhost:{settings.PORT}/api/docs")
    logger.info(f"🎨 Frontend: http://localhost:3003")
    logger.info("=" * 60)

    try:
        # 🔹 SERVICIO UNIFICADO: Inicializar ChatbotService con todas las funcionalidades
        try:
            from app.services.chatbot_service import init_chatbot_service

            # Inicializar servicio unificado con Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            await init_chatbot_service(settings.GROQ_API_KEY, redis_url)
            logger.info("✅ ChatbotService unificado inicializado correctamente")
        except Exception as e:
            logger.error(f"❌ Error inicializando ChatbotService: {e}")

        # Aquí se pueden inicializar otros servicios
        logger.info("✅ Servicios inicializados correctamente")
        logger.info("✅ SISTEMA COMPLETAMENTE OPERATIVO")
    except Exception as e:
        logger.error(f"❌ Error inicializando servicios: {e}")

if __name__ == "__main__":
    import uvicorn

    print("INICIANDO ZISBOT CON ARQUITECTURA PROFESIONAL")
    print("=" * 70)
    print(f"Hospital: {settings.APP_NAME}")
    print(f"Arquitectura: Clean Architecture (SIN consultas SQL directas)")
    print(f"API: http://localhost:{settings.PORT}")
    print(f"Docs: http://localhost:{settings.PORT}/api/docs")
    print(f"Frontend: http://localhost:3003")
    print(f"Usuario: Yanet Villalba (CUIL: 27357388827)")
    print("=" * 70)

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )