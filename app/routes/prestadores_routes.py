"""
🎯 Endpoints REST para prestadores y especialidades con filtrado avanzado
Implementa la nueva estrategia de filtrado por prestadores activos
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from app.services.orm_hospital_service import orm_hospital_service as hospital_service
from app.utils.auth import verify_jwt_token

# Router para endpoints de prestadores
prestadores_router = APIRouter(prefix="/api/prestadores", tags=["Prestadores"])

@prestadores_router.get("/especialidades-disponibles")
async def obtener_especialidades_con_prestadores(
    user_data: dict = Depends(verify_jwt_token)
) -> JSONResponse:
    """
    🎯 NUEVA ESTRATEGIA: Obtener especialidades reales basadas en prestadores activos

    Flujo:
    1. Filtra automáticamente por institución del usuario logueado
    2. Para cada especialidad, verifica si tiene prestadores activos
    3. Retorna solo especialidades que tienen prestadores disponibles

    Args:
        user_data: Datos del usuario autenticado (incluye hospital_id, cuil, password)

    Returns:
        JSONResponse con especialidades que tienen prestadores activos + info de prestadores
    """
    try:
        # 🔒 FILTRADO AUTOMÁTICO: hospital_id del login
        hospital_id = user_data.get('hospital_id') or user_data.get('institution_id')
        institution_name = user_data.get('institution', 'Institución')
        user_cuil = user_data.get('cuil')
        user_password = user_data.get('password')

        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede determinar la institución del usuario. Reloguearse."
            )

        if not user_cuil or not user_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Faltan credenciales de usuario en el token. Reloguearse."
            )

        # Usar el nuevo método de filtrado por prestadores
        result = await hospital_service.obtener_especialidades_desde_prestadores(
            hospital_id, user_cuil, user_password
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result.success,
                "data": result.data or [],
                "message": result.message,
                "strategy": "prestadores_activos",
                "institution": institution_name,
                "hospital_id": hospital_id,
                "count": len(result.data) if result.data else 0,
                "metadata": {
                    "filtrado_por": "prestadores_activos",
                    "datos_reales": True,
                    "filtrado_automatico": True
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )