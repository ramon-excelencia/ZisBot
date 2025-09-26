"""
Servicio API para datos hospitalarios
Este servicio hace las consultas a ZisMed y expone APIs REST limpias
"""

import httpx
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ApiResponse:
    """Respuesta estándar de API"""
    success: bool
    data: Any = None
    error: str = None
    metadata: Dict = None

class HospitalApiService:
    """Servicio que expone APIs REST para datos hospitalarios"""

    def __init__(self):
        self.base_url = os.getenv("HOSPITAL_API_BASE_URL", "http://localhost:8000")
        self.timeout = 30

    async def _make_request(self, endpoint: str, params: Dict = None) -> ApiResponse:
        """Hacer petición HTTP a endpoint interno"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/hospital{endpoint}"
                response = await client.get(url, params=params or {})

                if response.status_code == 200:
                    data = response.json()
                    return ApiResponse(success=True, data=data)
                else:
                    error_msg = f"API Error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return ApiResponse(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(error_msg)
            return ApiResponse(success=False, error=error_msg)

    # ===============================================
    # API ENDPOINTS PARA FUNCIONALIDADES
    # ===============================================

    async def search_patient_by_dni(self, dni: str, hospital_id: str) -> ApiResponse:
        """API: Buscar paciente por DNI"""
        return await self._make_request(f"/patients/search/dni/{dni}", {
            "hospital_id": hospital_id
        })

    async def search_patients_by_name(self, name: str, hospital_id: str, limit: int = 10) -> ApiResponse:
        """API: Buscar pacientes por nombre"""
        return await self._make_request("/patients/search/name", {
            "name": name,
            "hospital_id": hospital_id,
            "limit": limit
        })

    async def get_specialties_historical(self, hospital_id: str) -> ApiResponse:
        """API: Especialidades históricas"""
        return await self._make_request("/specialties/historical", {
            "hospital_id": hospital_id
        })

    async def get_specialties_summary(self, hospital_id: str) -> ApiResponse:
        """API: Resumen de especialidades"""
        return await self._make_request("/specialties/summary", {
            "hospital_id": hospital_id
        })

    async def get_bed_occupancy(self, hospital_id: str) -> ApiResponse:
        """API: Ocupación de camas"""
        return await self._make_request("/beds/occupancy", {
            "hospital_id": hospital_id
        })

    async def get_bed_occupancy_by_service(self, hospital_id: str) -> ApiResponse:
        """API: Ocupación por servicio"""
        return await self._make_request("/beds/occupancy/by-service", {
            "hospital_id": hospital_id
        })

    async def get_operational_dashboard(self, hospital_id: str) -> ApiResponse:
        """API: Dashboard operativo"""
        return await self._make_request("/dashboard/operational", {
            "hospital_id": hospital_id
        })

    async def get_specialties_activity(self, hospital_id: str, limit: int = 10) -> ApiResponse:
        """API: Actividad por especialidades"""
        return await self._make_request("/dashboard/specialties-activity", {
            "hospital_id": hospital_id,
            "limit": limit
        })

    async def get_laboratory_stats(self, hospital_id: str) -> ApiResponse:
        """API: Estadísticas de laboratorio"""
        return await self._make_request("/laboratory/stats", {
            "hospital_id": hospital_id
        })

    async def get_recent_laboratory_studies(self, hospital_id: str, limit: int = 10) -> ApiResponse:
        """API: Estudios recientes de laboratorio"""
        return await self._make_request("/laboratory/recent-studies", {
            "hospital_id": hospital_id,
            "limit": limit
        })

    async def get_pharmacy_stock(self, hospital_id: str, search: str = None) -> ApiResponse:
        """API: Stock de farmacia"""
        params = {"hospital_id": hospital_id}
        if search:
            params["search"] = search
        return await self._make_request("/pharmacy/stock", params)

    async def get_pharmacy_medications(self, hospital_id: str, search: str = None, limit: int = 20) -> ApiResponse:
        """API: Medicamentos de farmacia"""
        params = {"hospital_id": hospital_id, "limit": limit}
        if search:
            params["search"] = search
        return await self._make_request("/pharmacy/medications", params)

    async def get_professionals(self, hospital_id: str) -> ApiResponse:
        """API: Profesionales"""
        return await self._make_request("/professionals", {
            "hospital_id": hospital_id
        })

    async def get_professionals_detailed(self, hospital_id: str, limit: int = 50) -> ApiResponse:
        """API: Profesionales detallados"""
        return await self._make_request("/professionals/detailed", {
            "hospital_id": hospital_id,
            "limit": limit
        })

    async def get_patient_appointments(self, patient_id: str, hospital_id: str,
                                     date_from: date = None, date_to: date = None) -> ApiResponse:
        """API: Turnos de paciente"""
        params = {"hospital_id": hospital_id}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()

        return await self._make_request(f"/appointments/patient/{patient_id}", params)

    async def health_check(self, hospital_id: str) -> ApiResponse:
        """API: Health check"""
        return await self._make_request("/health", {
            "hospital_id": hospital_id
        })

# Instancia global del servicio
hospital_api_service = HospitalApiService()

async def get_hospital_api_service() -> HospitalApiService:
    """Obtener instancia del servicio API"""
    return hospital_api_service