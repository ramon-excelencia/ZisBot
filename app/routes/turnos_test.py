"""
Router simple de prueba para turnos
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/test-turnos", tags=["Test Turnos"])

@router.get("/test")
async def test_endpoint():
    """Endpoint de prueba"""
    return {"message": "Router de turnos funcionando correctamente", "status": "ok"}