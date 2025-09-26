"""
Endpoints REST para gestión de turnos médicos
Incluye consultas y operaciones CRUD completas
"""
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from app.models.schemas import ApiResponse, Turno
from app.services.orm_hospital_service import orm_hospital_service as hospital_service
from app.utils.auth import verify_jwt_token

router = APIRouter(prefix="/api/turnos-management", tags=["Turnos Management"])

# Modelos para requests
class CrearTurnoRequest(BaseModel):
    """Request para crear turno"""
    paciente_dni: str = Field(..., description="DNI del paciente")
    medico_id: int = Field(..., description="ID del médico")
    fecha_hora: str = Field(..., description="Fecha y hora del turno (YYYY-MM-DD HH:MM)")
    especialidad_id: int = Field(..., description="ID de la especialidad")

class CancelarTurnoRequest(BaseModel):
    """Request para cancelar turno"""
    turno_id: int = Field(..., description="ID del turno a cancelar")
    motivo: Optional[str] = Field(None, description="Motivo de cancelación")

class ReprogramarTurnoRequest(BaseModel):
    """Request para reprogramar turno"""
    turno_id: int = Field(..., description="ID del turno a reprogramar")
    nueva_fecha_hora: str = Field(..., description="Nueva fecha y hora (YYYY-MM-DD HH:MM)")
    motivo: Optional[str] = Field(None, description="Motivo de reprogramación")

# CONSULTAS DE TURNOS
@router.get("/fecha/{fecha}")
async def buscar_turnos_por_fecha(
    fecha: str,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Busca turnos por fecha específica"""
    try:
        hospital_id = user_data.get("hospital_id", "3")
        result = await hospital_service.buscar_turnos_por_fecha(fecha, hospital_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error buscando turnos: {str(e)}"
        )

@router.get("/paciente/{dni}")
async def obtener_turnos_paciente(
    dni: str,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Obtiene todos los turnos de un paciente por DNI"""
    try:
        result = await hospital_service.obtener_turnos_paciente(dni)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo turnos del paciente: {str(e)}"
        )

@router.get("/proximos/{dni}")
async def obtener_proximos_turnos_paciente(
    dni: str,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Obtiene próximos turnos de un paciente"""
    try:
        hospital_id = user_data.get("hospital_id", "3")
        result = await hospital_service.obtener_proximos_turnos_paciente(dni, hospital_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo próximos turnos: {str(e)}"
        )

@router.get("/disponibles")
async def obtener_turnos_disponibles(
    fecha: str,
    especialidad_id: Optional[int] = None,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Obtiene turnos disponibles para una fecha y especialidad"""
    try:
        hospital_id = user_data.get("hospital_id", "3")
        result = await hospital_service.obtener_turnos_disponibles(fecha, especialidad_id, hospital_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo turnos disponibles: {str(e)}"
        )

@router.get("/dias-disponibles/{servicio_id}")
async def obtener_dias_disponibles_servicio(
    servicio_id: int,
    prestador_id: Optional[int] = None,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Obtiene días disponibles para turnos de un servicio"""
    try:
        result = await hospital_service.obtener_dias_disponibles_servicio(servicio_id, prestador_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo días disponibles: {str(e)}"
        )

# CRUD DE TURNOS
@router.post("/crear")
async def crear_turno(
    request: CrearTurnoRequest,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Crea un nuevo turno médico"""
    try:
        hospital_id = user_data.get("hospital_id", "3")
        result = await hospital_service.crear_turno(
            request.paciente_dni,
            request.medico_id,
            request.fecha_hora,
            request.especialidad_id,
            hospital_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando turno: {str(e)}"
        )

@router.post("/cancelar")
async def cancelar_turno(
    request: CancelarTurnoRequest,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Cancela un turno médico"""
    try:
        result = await hospital_service.cancelar_turno(request.turno_id, request.motivo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelando turno: {str(e)}"
        )

@router.post("/reprogramar")
async def reprogramar_turno(
    request: ReprogramarTurnoRequest,
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Reprograma un turno médico"""
    try:
        result = await hospital_service.reprogramar_turno(
            request.turno_id,
            request.nueva_fecha_hora,
            request.motivo
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprogramando turno: {str(e)}"
        )

# ENDPOINTS ADICIONALES ÚTILES
@router.get("/hoy")
async def obtener_turnos_hoy(
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Obtiene turnos del día de hoy"""
    try:
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        hospital_id = user_data.get("hospital_id", "3")
        result = await hospital_service.buscar_turnos_por_fecha(fecha_hoy, hospital_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo turnos de hoy: {str(e)}"
        )

@router.get("/consultorios")
async def obtener_consultorios(
    user_data: dict = Depends(verify_jwt_token)
) -> ApiResponse:
    """Obtiene consultorios disponibles de la institución"""
    try:
        institucion_id = int(user_data.get("hospital_id", "3"))
        result = await hospital_service.obtener_consultorios_institucion(institucion_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo consultorios: {str(e)}"
        )