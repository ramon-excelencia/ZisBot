"""
Endpoints REST extendidos para servicios hospitalarios con LangChain
Nuevas funcionalidades para el sistema profesional
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from app.services.orm_hospital_service import orm_hospital_service as hospital_service
from app.utils.auth import verify_jwt_token

# Router para endpoints hospitalarios extendidos
extended_hospital_router = APIRouter(prefix="/api/hospital", tags=["Hospital Extended"])

# ===============================================
# ENDPOINTS EXTENDIDOS PARA LANGCHAIN
# ===============================================

@extended_hospital_router.get("/medicos")
async def obtener_medicos_por_especialidad(
    especialidad: str,
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Obtener médicos de una especialidad específica

    Args:
        especialidad: Nombre de la especialidad
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con la lista de médicos
    """
    try:
        if not especialidad or len(especialidad.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La especialidad debe tener al menos 2 caracteres"
            )

        result = hospital_service.obtener_medicos_por_especialidad(especialidad.strip())

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data or [],
                "message": result.message,
                "count": len(result.data) if result.data else 0
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@extended_hospital_router.get("/turnos")
async def buscar_turnos_por_fecha(
    fecha: str,
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Buscar turnos por fecha específica

    Args:
        fecha: Fecha en formato YYYY-MM-DD
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con la lista de turnos
    """
    try:
        # Validar formato de fecha básico
        if not fecha or len(fecha) != 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha debe estar en formato YYYY-MM-DD"
            )

        result = hospital_service.buscar_turnos_por_fecha(fecha)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data or [],
                "message": result.message,
                "count": len(result.data) if result.data else 0
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@extended_hospital_router.get("/estadisticas")
async def obtener_estadisticas_hospital(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Obtener estadísticas generales del hospital

    Args:
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con las estadísticas del hospital
    """
    try:
        result = hospital_service.obtener_estadisticas_hospital()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data,
                "message": result.message
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@extended_hospital_router.get("/pacientes/obra-social/{obra_social}")
async def buscar_pacientes_por_obra_social(
    obra_social: str,
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Buscar pacientes por obra social específica

    Args:
        obra_social: Nombre de la obra social
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con la lista de pacientes
    """
    try:
        if not obra_social or len(obra_social.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de la obra social debe tener al menos 2 caracteres"
            )

        result = hospital_service.buscar_pacientes_por_obra_social(obra_social.strip())

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data or [],
                "message": result.message,
                "count": len(result.data) if result.data else 0
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@extended_hospital_router.get("/obras-sociales")
async def obtener_obras_sociales(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Obtener todas las obras sociales disponibles

    Args:
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con la lista de obras sociales
    """
    try:
        result = hospital_service.obtener_obras_sociales()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data or [],
                "message": result.message,
                "count": len(result.data) if result.data else 0
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )