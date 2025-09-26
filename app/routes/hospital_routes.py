"""
Endpoints REST para servicios hospitalarios
Expone las funcionalidades del hospital de manera profesional
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Optional

from app.services.orm_hospital_service import orm_hospital_service as hospital_service
from app.models.schemas import ApiResponse
from app.utils.auth import verify_jwt_token

# Router para endpoints hospitalarios
hospital_router = APIRouter(prefix="/api/hospital", tags=["Hospital"])

# ===============================================
# ENDPOINTS DE PACIENTES
# ===============================================

@hospital_router.get("/pacientes/{dni}")
async def buscar_paciente_por_dni(
    dni: str,
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Buscar un paciente por su DNI

    Args:
        dni: Documento Nacional de Identidad del paciente
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con los datos del paciente o error
    """
    try:
        # Validar DNI
        if not dni or not dni.isdigit() or len(dni) < 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DNI inválido. Debe contener entre 7 y 8 dígitos"
            )

        result = await hospital_service.buscar_paciente_por_dni(dni)

        if result.success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "data": result.data,
                    "message": result.message
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "message": result.message or "Paciente no encontrado"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@hospital_router.get("/pacientes/buscar")
async def buscar_pacientes_por_nombre(
    nombre: str,
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Buscar pacientes por nombre (búsqueda parcial)

    Args:
        nombre: Nombre o apellido a buscar
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con la lista de pacientes encontrados
    """
    try:
        if not nombre or len(nombre.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre debe tener al menos 2 caracteres"
            )

        result = await hospital_service.buscar_pacientes_por_nombre(nombre.strip())

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

# ===============================================
# ENDPOINTS DE ANALYTICS
# ===============================================

@hospital_router.get("/analytics/vulnerabilidad-social")
async def obtener_vulnerabilidad_social(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Análisis de vulnerabilidad social - pacientes sin obra social

    Args:
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con estadísticas de vulnerabilidad social
    """
    try:
        result = await hospital_service.analizar_vulnerabilidad_social()

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

# ===============================================
# ENDPOINTS DE ESPECIALIDADES
# ===============================================

@hospital_router.get("/especialidades")
async def obtener_especialidades(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Obtener todas las especialidades médicas disponibles

    Args:
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con la lista de especialidades
    """
    try:
        # 🔒 FILTRADO AUTOMÁTICO: hospital_id DEBE venir del login
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario. Reloguearse."
            )

        # Usar el método filtrado que ya funciona
        result = await hospital_service.obtener_especialidades_filtradas(hospital_id, user_cuil, user_password)

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

@hospital_router.get("/especialidades/por-institucion")
async def obtener_especialidades_por_institucion(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Obtener especialidades médicas filtradas por la institución del usuario logueado

    Args:
        user_data: Datos del usuario autenticado (incluye hospital_id)

    Returns:
        JSONResponse con las especialidades filtradas de la institución
    """
    try:
        # 🔒 FILTRADO AUTOMÁTICO: hospital_id DEBE venir del login
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        institution_name = user_data.get('institution', 'Institución')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario. Reloguearse."
            )

        # Llamar al servicio con filtrado por institución
        result = await hospital_service.obtener_especialidades_filtradas(
            hospital_id, user_cuil, user_password
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data or [],
                "message": result.message,
                "institution": institution_name,
                "hospital_id": hospital_id,
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

# ===============================================
# ENDPOINTS DE SERVICIOS HOSPITALARIOS
# ===============================================

@hospital_router.get("/servicios")
async def obtener_servicios_hospitalarios(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    Obtener todos los servicios hospitalarios disponibles

    Args:
        user_data: Datos del usuario autenticado

    Returns:
        JSONResponse con la lista de servicios
    """
    try:
        result = await hospital_service.obtener_servicios_hospitalarios()

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

# ===============================================
# NUEVOS ENDPOINTS PARA FUNCIONALIDADES REALES
# ===============================================

@hospital_router.get("/dashboard/operativo")
async def obtener_dashboard_operativo(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """Dashboard operativo en tiempo real"""
    try:
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario"
            )

        result = await hospital_service.obtener_dashboard_operativo(hospital_id, user_cuil, user_password)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data,
                "message": result.message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@hospital_router.get("/camas/ocupacion")
async def obtener_ocupacion_camas(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """Obtener ocupación actual de camas"""
    try:
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario"
            )

        result = await hospital_service.obtener_ocupacion_camas(hospital_id, user_cuil, user_password)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data,
                "message": result.message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@hospital_router.get("/laboratorio/estadisticas")
async def obtener_laboratorio_stats(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """Estadísticas de laboratorio del día"""
    try:
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario"
            )

        result = await hospital_service.obtener_laboratorio_stats(hospital_id, user_cuil, user_password)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data,
                "message": result.message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@hospital_router.get("/farmacia/stock")
async def obtener_farmacia_stock(
    medicamento: Optional[str] = None,
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """Stock de farmacia con búsqueda opcional"""
    try:
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario"
            )

        result = await hospital_service.obtener_farmacia_stock(hospital_id, medicamento, user_cuil, user_password)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data,
                "message": result.message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@hospital_router.get("/prestadores/activos")
async def obtener_prestadores_activos(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """Prestadores activos por institución"""
    try:
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario"
            )

        result = await hospital_service.obtener_prestadores_activos(hospital_id, user_cuil, user_password)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data,
                "message": result.message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )