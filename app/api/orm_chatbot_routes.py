"""
FastAPI Routes para Chatbot con SQLAlchemy ORM + LangGraph + Groq
Endpoints integrados con IA real y datos hospitalarios
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field

from app.services.orm_enhanced_langchain_service import (
    get_orm_enhanced_chatbot_service,
    init_orm_enhanced_chatbot_service,
    force_reinit_orm_enhanced_chatbot_service,
    quick_test_orm_service,
    quick_test_full_workflow
)
from app.services.orm_hospital_service import ORMHospitalService
from app.config.settings import settings

logger = logging.getLogger(__name__)

# ===============================================
# MODELOS PYDANTIC
# ===============================================

class ChatMessage(BaseModel):
    """Mensaje de chat del usuario"""
    message: str = Field(..., min_length=1, max_length=2000, description="Mensaje del usuario")
    conversation_id: str = Field(default="default", description="ID de la conversación")
    user_id: str = Field(default="anonymous", description="ID del usuario")
    hospital_id: str = Field(default="3", description="ID del hospital")

class ChatResponse(BaseModel):
    """Respuesta del chatbot"""
    success: bool
    response: str
    timestamp: str
    conversation_id: str
    metadata: Optional[Dict[str, Any]] = None

class DirectQueryRequest(BaseModel):
    """Request para consultas directas ORM"""
    query_type: str = Field(..., description="Tipo de consulta: patient_dni, specialties, stats, etc.")
    parameters: Dict[str, Any] = Field(default={}, description="Parámetros de la consulta")
    hospital_id: int = Field(default=3, description="ID del hospital")

class DirectQueryResponse(BaseModel):
    """Respuesta para consultas directas ORM"""
    success: bool
    data: Any
    message: str
    query_type: str
    execution_time_ms: Optional[float] = None

class HealthCheckResponse(BaseModel):
    """Respuesta del health check"""
    status: str
    timestamp: str
    services: Dict[str, Any]
    version: str = "1.0.0"

# ===============================================
# ROUTER
# ===============================================

router = APIRouter(prefix="/api/v1/orm-chatbot", tags=["ORM Chatbot"])

# ===============================================
# DEPENDENCY: INICIALIZAR SERVICIO
# ===============================================

async def get_chatbot_service():
    """Dependency para obtener servicio de chatbot"""
    try:
        service = await get_orm_enhanced_chatbot_service()
        return service
    except ValueError:
        # Inicializar si no existe
        await init_orm_enhanced_chatbot_service(
            groq_api_key=settings.GROQ_API_KEY,
            model="llama-3.1-8b-instant"
        )
        return await get_orm_enhanced_chatbot_service()

# ===============================================
# ENDPOINTS PRINCIPALES
# ===============================================


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    message: ChatMessage,
    background_tasks: BackgroundTasks,
    chatbot_service = Depends(get_chatbot_service)
):
    """
    Endpoint principal para chat con IA usando ORM + LangGraph
    """
    try:
        logger.info(f"💬 Nueva consulta: {message.message[:50]}... (Usuario: {message.user_id})")

        start_time = datetime.now()

        # Procesar mensaje con el servicio enhanced
        response = await chatbot_service.process_message(
            user_message=message.message,
            conversation_id=message.conversation_id,
            user_id=message.user_id,
            hospital_id=message.hospital_id
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds() * 1000

        # Metadata de respuesta
        metadata = {
            "processing_time_ms": processing_time,
            "hospital_id": message.hospital_id,
            "service_type": "orm_enhanced_langchain",
            "model": "llama-3.1-8b-instant"
        }

        logger.info(f"✅ Respuesta generada en {processing_time:.2f}ms")

        return ChatResponse(
            success=True,
            response=response,
            timestamp=datetime.now().isoformat(),
            conversation_id=message.conversation_id,
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"❌ Error en chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando mensaje: {str(e)}"
        )

@router.post("/direct-query", response_model=DirectQueryResponse)
async def direct_orm_query(
    request: DirectQueryRequest,
    chatbot_service = Depends(get_chatbot_service)
):
    """
    Endpoint para consultas directas al ORM (sin IA)
    Útil para integraciones específicas y debugging
    """
    try:
        start_time = datetime.now()

        query_type = request.query_type.lower()
        params = request.parameters
        hospital_id = request.hospital_id

        logger.info(f"🔍 Consulta directa: {query_type} - Hospital: {hospital_id}")

        # Router de consultas directas
        if query_type == "patient_dni":
            dni = params.get("dni")
            if not dni:
                raise HTTPException(status_code=400, detail="DNI requerido para búsqueda")
            result = await chatbot_service.get_patient_by_dni_direct(dni, hospital_id)

        elif query_type == "patient_name":
            name = params.get("name")
            if not name:
                raise HTTPException(status_code=400, detail="Nombre requerido para búsqueda")
            result = await chatbot_service.search_patients_by_name_direct(name, hospital_id)

        elif query_type == "specialties":
            result = await chatbot_service.get_specialties_direct(hospital_id)

        elif query_type == "services":
            result = await chatbot_service.get_services_direct(hospital_id)

        elif query_type == "providers":
            result = await chatbot_service.get_providers_direct(hospital_id)

        elif query_type == "stats":
            result = await chatbot_service.get_hospital_stats_direct(hospital_id)

        elif query_type == "beds_status":
            result = await orm_hospital_service.obtener_estado_camas(hospital_id)

        elif query_type == "emergency_status":
            result = await orm_hospital_service.obtener_estado_emergencias(hospital_id)

        elif query_type == "providers_availability":
            result = await orm_hospital_service.obtener_disponibilidad_prestadores(hospital_id)

        elif query_type == "appointments_summary":
            result = await orm_hospital_service.obtener_resumen_turnos(hospital_id)

        elif query_type == "hospital_metrics":
            result = await orm_hospital_service.obtener_metricas_completas(hospital_id)

        elif query_type == "test_connection":
            result = await chatbot_service.test_orm_connection()

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de consulta no soportado: {query_type}. Disponibles: patient_dni, patient_name, specialties, services, providers, stats, beds_status, emergency_status, providers_availability, appointments_summary, hospital_metrics, test_connection"
            )

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds() * 1000

        return DirectQueryResponse(
            success=result["success"],
            data=result.get("data"),
            message=result.get("message", "Consulta ejecutada"),
            query_type=query_type,
            execution_time_ms=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en consulta directa: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando consulta: {str(e)}"
        )

# ===============================================
# ENDPOINTS DE TESTING Y DIAGNÓSTICO
# ===============================================

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check completo del sistema ORM + IA
    """
    try:
        logger.info("🏥 Ejecutando health check...")

        # Test servicios principales
        services_status = {}

        # Test ORM
        try:
            orm_result = await orm_hospital_service.test_connection()
            services_status["orm"] = {
                "status": "ok" if orm_result.success else "error",
                "details": orm_result.data if orm_result.success else orm_result.error
            }
        except Exception as e:
            services_status["orm"] = {"status": "error", "details": str(e)}

        # Test LangGraph Workflow
        try:
            service = await get_chatbot_service()
            if hasattr(service, 'get_workflow_info'):
                workflow_info = service.get_workflow_info()
                services_status["langraph"] = {
                    "status": "ok" if workflow_info.get("status") == "functional" else "degraded",
                    "details": workflow_info
                }
            else:
                services_status["langraph"] = {
                    "status": "degraded",
                    "details": "Workflow info method not available - service functional but limited"
                }
        except Exception as e:
            services_status["langraph"] = {"status": "error", "details": str(e)}

        # Test Groq LLM
        try:
            service = await get_chatbot_service()
            if hasattr(service, 'test_workflow'):
                test_result = await service.test_workflow("test")
                services_status["groq_llm"] = {
                    "status": "ok" if test_result.get("success") else "degraded",
                    "details": test_result.get("llm_response", test_result.get("error", "Test completed"))
                }
            else:
                services_status["groq_llm"] = {
                    "status": "degraded",
                    "details": "LLM test method not available - service functional but limited"
                }
        except Exception as e:
            services_status["groq_llm"] = {"status": "error", "details": str(e)}

        # Estado general - más permisivo
        critical_services = ["orm"]  # Solo ORM es crítico
        errors = [name for name, status in services_status.items() if status["status"] == "error"]
        critical_errors = [name for name in errors if name in critical_services]

        if critical_errors:
            overall_status = "unhealthy"
        elif errors:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            services=services_status
        )

    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en health check: {str(e)}"
        )

@router.get("/test/quick-orm")
async def quick_test_orm():
    """Test rápido del ORM"""
    try:
        logger.info("🧪 Ejecutando test rápido ORM...")

        results = {}

        # Test conexión
        connection_result = await orm_hospital_service.test_connection()
        results["connection"] = {
            "success": connection_result.success,
            "message": connection_result.message
        }

        # Test especialidades
        specialties_result = await orm_hospital_service.obtener_especialidades_con_prestadores(3)
        results["specialties"] = {
            "success": specialties_result.success,
            "count": len(specialties_result.data) if specialties_result.success else 0
        }

        # Test estadísticas
        stats_result = await orm_hospital_service.obtener_estadisticas_hospital(3)
        results["stats"] = {
            "success": stats_result.success,
            "data": stats_result.data if stats_result.success else None
        }

        return {
            "success": True,
            "message": "Test ORM completado",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error en test ORM: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test ORM: {str(e)}"
        )

@router.get("/test/workflow")
async def test_full_workflow(
    query: str = "¿Qué especialidades tienen disponibles?",
    chatbot_service = Depends(get_chatbot_service)
):
    """Test completo del workflow LangGraph"""
    try:
        logger.info(f"🧪 Testing workflow con query: {query}")

        # Test workflow
        result = await chatbot_service.test_workflow(query)

        return {
            "success": result["success"],
            "query": query,
            "response": result.get("response", "No response"),
            "confidence": result.get("confidence", 0.0),
            "intent": result.get("intent"),
            "processing_steps": result.get("processing_steps", []),
            "errors": result.get("errors", []),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error en test workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test workflow: {str(e)}"
        )

# ===============================================
# ENDPOINTS DE INFORMACIÓN
# ===============================================

@router.get("/info/capabilities")
async def get_capabilities():
    """Obtener capacidades del sistema"""
    return {
        "service_name": "ORM Enhanced Medical Chatbot",
        "version": "1.0.0",
        "capabilities": {
            "orm_direct_access": True,
            "langraph_workflow": True,
            "groq_llm": True,
            "real_time_data": True,
            "conversation_memory": True,
            "emergency_detection": True
        },
        "supported_queries": [
            "Búsqueda de pacientes por DNI",
            "Búsqueda de pacientes por nombre",
            "Información de especialidades",
            "Información de servicios hospitalarios",
            "Información de prestadores",
            "Estadísticas hospitalarias",
            "Consultas generales",
            "Detección de emergencias"
        ],
        "supported_intents": [
            "PATIENT_SEARCH_DNI", "PATIENT_SEARCH_NAME",
            "SPECIALTIES_INFO", "SERVICES_INFO", "PROVIDERS_INFO",
            "HOSPITAL_STATS", "EMERGENCY", "GENERAL_INFO"
        ],
        "models": {
            "llm": "llama-3.1-8b-instant",
            "orm": "SQLAlchemy",
            "workflow": "LangGraph"
        }
    }

@router.get("/info/workflow")
async def get_workflow_info(chatbot_service = Depends(get_chatbot_service)):
    """Obtener información del workflow"""
    try:
        workflow_info = chatbot_service.get_workflow_info()
        return {
            "success": True,
            "workflow_info": workflow_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo info workflow: {str(e)}"
        )

# ===============================================
# ENDPOINTS DE DATOS ESPECÍFICOS
# ===============================================

@router.get("/data/specialties/{hospital_id}")
async def get_specialties_data(hospital_id: int = 3):
    """Obtener especialidades en formato JSON"""
    try:
        result = await orm_hospital_service.obtener_especialidades_con_prestadores(hospital_id)
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "count": len(result.data),
                "hospital_id": hospital_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=result.error)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/services/{hospital_id}")
async def get_services_data(hospital_id: int = 3):
    """Obtener servicios hospitalarios en formato JSON"""
    try:
        result = await orm_hospital_service.obtener_servicios_hospital(hospital_id)
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "count": len(result.data),
                "hospital_id": hospital_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=result.error)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/force-reinit")
async def force_reinitialize_service():
    """🔄 FORZAR re-inicialización del servicio (para desarrollo)"""
    try:
        logger.info("🔄 FORZANDO re-inicialización del ORM Enhanced Service...")

        await force_reinit_orm_enhanced_chatbot_service(
            groq_api_key=settings.GROQ_API_KEY,
            model="llama-3.1-8b-instant"
        )

        # Test rápido para verificar que funciona
        service = await get_orm_enhanced_chatbot_service()
        test_response = await service.process_message(
            "¿Cuántas especialidades hay?",
            "test_conversation",
            "test_user",
            "3"
        )

        return {
            "success": True,
            "message": "✅ Servicio re-inicializado exitosamente",
            "test_response": test_response,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error re-inicializando servicio: {e}")
        raise HTTPException(status_code=500, detail=f"Error re-inicializando: {str(e)}")

@router.get("/data/stats/{hospital_id}")
async def get_hospital_stats_data(hospital_id: int = 3):
    """Obtener estadísticas en formato JSON"""
    try:
        result = await orm_hospital_service.obtener_estadisticas_hospital(hospital_id)
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "hospital_id": hospital_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=result.error)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================
# ENDPOINTS DE CAMAS Y TURNOS - NUEVAS FUNCIONALIDADES
# ===============================================

@router.get("/data/beds/{hospital_id}", summary="Disponibilidad de camas")
async def get_beds_availability(hospital_id: int = 3):
    """
    Obtener disponibilidad de camas por sector y habitación

    Args:
        hospital_id: ID del hospital (por defecto 3)

    Returns:
        JSONResponse con disponibilidad detallada de camas
    """
    try:
        logger.info(f"🛏️ Obteniendo disponibilidad de camas del hospital {hospital_id}")

        result = await orm_hospital_service.obtener_disponibilidad_camas(hospital_id)

        if result.success:
            return {
                "success": True,
                "data": result.data,
                "hospital_id": hospital_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo disponibilidad de camas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/appointments/today/{hospital_id}", summary="Turnos de hoy")
async def get_today_appointments(hospital_id: int = 3):
    """
    Obtener turnos de hoy para un hospital específico

    Args:
        hospital_id: ID del hospital (por defecto 3)

    Returns:
        JSONResponse con turnos del día actual
    """
    try:
        logger.info(f"📅 Obteniendo turnos de hoy del hospital {hospital_id}")

        result = await orm_hospital_service.obtener_turnos_hoy(hospital_id)

        if result.success:
            return {
                "success": True,
                "data": result.data,
                "hospital_id": hospital_id,
                "fecha": date.today().strftime('%Y-%m-%d'),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": result.message,
                "hospital_id": hospital_id,
                "fecha": date.today().strftime('%Y-%m-%d'),
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Error obteniendo turnos de hoy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/appointments/date/{hospital_id}", summary="Turnos por fecha específica")
async def get_appointments_by_date(
    hospital_id: int = 3,
    fecha: str = Query(..., description="Fecha en formato YYYY-MM-DD")
):
    """
    Obtener turnos para una fecha específica

    Args:
        hospital_id: ID del hospital (por defecto 3)
        fecha: Fecha en formato YYYY-MM-DD

    Returns:
        JSONResponse con turnos de la fecha especificada
    """
    try:
        # Validar y convertir fecha
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )

        logger.info(f"📅 Obteniendo turnos del {fecha} del hospital {hospital_id}")

        result = await orm_hospital_service.obtener_turnos_por_fecha(fecha_obj, hospital_id)

        if result.success:
            return {
                "success": True,
                "data": result.data,
                "hospital_id": hospital_id,
                "fecha": fecha,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": result.message,
                "hospital_id": hospital_id,
                "fecha": fecha,
                "timestamp": datetime.now().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo turnos por fecha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/appointments/range/{hospital_id}", summary="Turnos por rango de fechas")
async def get_appointments_by_range(
    hospital_id: int = 3,
    fecha_inicio: str = Query(..., description="Fecha inicio en formato YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="Fecha fin en formato YYYY-MM-DD"),
    limit: int = Query(500, description="Límite de turnos a retornar")
):
    """
    Obtener turnos en un rango de fechas

    Args:
        hospital_id: ID del hospital (por defecto 3)
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD
        limit: Número máximo de turnos a retornar

    Returns:
        JSONResponse con turnos del rango de fechas
    """
    try:
        # Validar y convertir fechas
        try:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )

        # Validar que fecha_inicio <= fecha_fin
        if fecha_inicio_obj > fecha_fin_obj:
            raise HTTPException(
                status_code=400,
                detail="La fecha de inicio debe ser anterior o igual a la fecha de fin"
            )

        logger.info(f"📅 Obteniendo turnos desde {fecha_inicio} hasta {fecha_fin} del hospital {hospital_id}")

        result = await orm_hospital_service.obtener_turnos_rango_fechas(
            fecha_inicio_obj, fecha_fin_obj, hospital_id, limit
        )

        if result.success:
            return {
                "success": True,
                "data": result.data,
                "hospital_id": hospital_id,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "limit": limit,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": result.message,
                "hospital_id": hospital_id,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "timestamp": datetime.now().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo turnos por rango: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================
# ENDPOINTS DE BÚSQUEDA DE PACIENTES - RELOAD TEST
# ===============================================

@router.get("/patients/search-dni/{dni}", summary="Buscar paciente por DNI")
async def search_patient_by_dni(dni: str, hospital_id: int = 3):
    """
    Buscar paciente específico por DNI

    Args:
        dni: Documento Nacional de Identidad del paciente
        hospital_id: ID del hospital (por defecto 3 - Hospital Regional)

    Returns:
        JSONResponse con datos completos del paciente
    """
    try:
        logger.info(f"🔍 Buscando paciente con DNI: {dni} en hospital {hospital_id}")

        result = await orm_hospital_service.buscar_paciente_por_dni(dni, hospital_id)

        if result.success:
            return {
                "success": True,
                "patient": result.data,
                "hospital_id": hospital_id,
                "search_type": "dni",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": f"No se encontró paciente con DNI {dni}",
                "hospital_id": hospital_id,
                "search_type": "dni",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Error buscando paciente por DNI: {e}")
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")

@router.get("/patients/search-name", summary="Buscar pacientes por nombre")
async def search_patients_by_name(
    name: str,
    hospital_id: int = 3,
    limit: int = 10
):
    """
    Buscar pacientes por nombre o apellido (búsqueda parcial)

    Args:
        name: Nombre o apellido a buscar
        hospital_id: ID del hospital (por defecto 3 - Hospital Regional)
        limit: Número máximo de resultados (por defecto 10)

    Returns:
        JSONResponse con lista de pacientes encontrados
    """
    try:
        logger.info(f"🔍 Buscando pacientes con nombre: {name} en hospital {hospital_id}")

        result = await orm_hospital_service.buscar_pacientes_por_nombre(name, hospital_id)

        if result.success:
            # Limitar resultados
            patients = result.data[:limit] if result.data else []

            return {
                "success": True,
                "patients": patients,
                "total_found": len(result.data) if result.data else 0,
                "showing": len(patients),
                "hospital_id": hospital_id,
                "search_type": "name",
                "search_term": name,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": f"No se encontraron pacientes con nombre '{name}'",
                "patients": [],
                "total_found": 0,
                "hospital_id": hospital_id,
                "search_type": "name",
                "search_term": name,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Error buscando pacientes por nombre: {e}")
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")

@router.get("/patients/search", summary="Búsqueda avanzada de pacientes")
async def advanced_patient_search(
    dni: str = None,
    name: str = None,
    apellido: str = None,
    hospital_id: int = 3,
    limit: int = 10
):
    """
    Búsqueda avanzada de pacientes con múltiples criterios

    Args:
        dni: DNI específico (búsqueda exacta)
        name: Nombre del paciente (búsqueda parcial)
        apellido: Apellido del paciente (búsqueda parcial)
        hospital_id: ID del hospital
        limit: Número máximo de resultados

    Returns:
        JSONResponse con resultados de búsqueda
    """
    try:
        # Validar que al menos un criterio esté presente
        if not any([dni, name, apellido]):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar al menos un criterio de búsqueda (dni, name, o apellido)"
            )

        search_criteria = {}
        if dni:
            search_criteria["dni"] = dni
        if name:
            search_criteria["nombre"] = name
        if apellido:
            search_criteria["apellido"] = apellido

        logger.info(f"🔍 Búsqueda avanzada: {search_criteria} en hospital {hospital_id}")

        # Si hay DNI, buscar específicamente
        if dni:
            result = await orm_hospital_service.buscar_paciente_por_dni(dni, hospital_id)
            if result.success and result.data:
                return {
                    "success": True,
                    "patients": [result.data],
                    "total_found": 1,
                    "showing": 1,
                    "hospital_id": hospital_id,
                    "search_type": "advanced",
                    "search_criteria": search_criteria,
                    "timestamp": datetime.now().isoformat()
                }

        # Búsqueda por nombre/apellido
        search_term = f"{name or ''} {apellido or ''}".strip()
        if search_term:
            result = await orm_hospital_service.buscar_pacientes_por_nombre(search_term, hospital_id)

            if result.success:
                patients = result.data[:limit] if result.data else []

                return {
                    "success": True,
                    "patients": patients,
                    "total_found": len(result.data) if result.data else 0,
                    "showing": len(patients),
                    "hospital_id": hospital_id,
                    "search_type": "advanced",
                    "search_criteria": search_criteria,
                    "timestamp": datetime.now().isoformat()
                }

        # No se encontraron resultados
        return {
            "success": False,
            "message": "No se encontraron pacientes con los criterios especificados",
            "patients": [],
            "total_found": 0,
            "hospital_id": hospital_id,
            "search_type": "advanced",
            "search_criteria": search_criteria,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en búsqueda avanzada: {e}")
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")

@router.get("/patients/stats/{hospital_id}", summary="Estadísticas de pacientes")
async def get_patient_stats(hospital_id: int = 3):
    """
    Obtener estadísticas de pacientes del hospital

    Args:
        hospital_id: ID del hospital

    Returns:
        JSONResponse con estadísticas de pacientes
    """
    try:
        logger.info(f"📊 Obteniendo estadísticas de pacientes del hospital {hospital_id}")

        result = await orm_hospital_service.obtener_estadisticas_hospital(hospital_id)

        if result.success:
            return {
                "success": True,
                "stats": result.data,
                "hospital_id": hospital_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

# ===============================================
# INSTANCIA DEL SERVICIO
# ===============================================

# Crear instancia del servicio ORM
orm_hospital_service = ORMHospitalService()