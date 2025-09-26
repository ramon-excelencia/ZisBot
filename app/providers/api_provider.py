"""
Provider que usa APIs REST en lugar de conexión directa a BD
Arquitectura limpia y escalable
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging

from .base import BaseProvider, ProviderConfig, Patient, Professional, Hospital, Appointment
from app.services.hospital_api_service import get_hospital_api_service

logger = logging.getLogger(__name__)

class ApiProvider(BaseProvider):
    """Provider que consume APIs REST para datos hospitalarios"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_service = None

    async def connect(self) -> bool:
        """Verificar conectividad con APIs"""
        try:
            self.api_service = await get_hospital_api_service()
            # Test básico de conectividad
            response = await self.api_service.health_check("3")  # Hospital test
            return response.success
        except Exception as e:
            logger.error(f"Error conectando con APIs: {e}")
            return False

    # ===============================================
    # FUNCIONALIDAD 1: BÚSQUEDA DE PACIENTES
    # ===============================================

    async def get_patient_by_dni(self, dni: str, hospital_id: str) -> Optional[Patient]:
        """Buscar paciente por DNI vía API"""
        try:
            response = await self.api_service.search_patient_by_dni(dni, hospital_id)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return None

            if not response.data:
                return None

            # Convertir respuesta API a objeto Patient
            data = response.data
            return Patient(
                id=str(data.get("patient_id", "")),
                dni=data.get("dni", ""),
                name=data.get("name", ""),
                phone=data.get("phone", ""),
                email=data.get("email", ""),
                metadata={
                    "age": data.get("age"),
                    "total_appointments": data.get("total_appointments", 0)
                }
            )

        except Exception as e:
            logger.error(f"Error buscando paciente por DNI {dni}: {e}")
            return None

    async def search_patients_by_name(self, name: str, hospital_id: str, limit: int = 10) -> List[Patient]:
        """Buscar pacientes por nombre vía API"""
        try:
            response = await self.api_service.search_patients_by_name(name, hospital_id, limit)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return []

            patients = []
            for data in response.data or []:
                patients.append(Patient(
                    id=str(data.get("patient_id", "")),
                    dni=data.get("dni", ""),
                    name=data.get("name", ""),
                    phone=data.get("phone", ""),
                    email=data.get("email", ""),
                    metadata={
                        "age": data.get("age"),
                        "total_appointments": data.get("total_appointments", 0)
                    }
                ))

            return patients

        except Exception as e:
            logger.error(f"Error buscando pacientes por nombre {name}: {e}")
            return []

    async def search_patients_advanced(self, criteria: Dict[str, Any], hospital_id: str, limit: int = 10) -> List[Patient]:
        """Búsqueda avanzada vía API"""
        # TODO: Implementar endpoint de búsqueda avanzada
        logger.warning("Búsqueda avanzada no implementada en API")
        return []

    # ===============================================
    # FUNCIONALIDAD 2: ESPECIALIDADES HISTÓRICAS
    # ===============================================

    async def get_complete_specialties_historical(self, hospital_id: str) -> Dict[str, Any]:
        """Obtener especialidades históricas vía API"""
        try:
            response = await self.api_service.get_specialties_historical(hospital_id)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return {"error": response.error, "especialidades": []}

            # Transformar respuesta para mantener compatibilidad
            specialties_data = response.data or []

            return {
                "especialidades": [
                    {
                        "id": esp.get("id"),
                        "nombre": esp.get("name", ""),
                        "total_turnos_año": esp.get("total_appointments_year", 0),
                        "prestadores_unicos": esp.get("unique_professionals", 0),
                        "ultimo_turno": esp.get("last_appointment"),
                        "nivel_actividad": esp.get("activity_level", "BAJA")
                    } for esp in specialties_data
                ],
                "total_especialidades": len(specialties_data),
                "total_turnos_historicos": sum(esp.get("total_appointments_year", 0) for esp in specialties_data),
                "periodo_analizado": "Últimos 365 días desde API",
                "hospital_id": hospital_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error obteniendo especialidades históricas: {e}")
            return {"error": str(e), "especialidades": []}

    # ===============================================
    # FUNCIONALIDAD 3: TURNOS Y AGENDA
    # ===============================================

    async def get_appointments(
        self,
        hospital_id: str,
        patient_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Appointment]:
        """Obtener turnos vía API"""
        try:
            if not patient_id:
                logger.warning("get_appointments requiere patient_id para API")
                return []

            date_from_date = date_from.date() if date_from else None
            date_to_date = date_to.date() if date_to else None

            response = await self.api_service.get_patient_appointments(
                patient_id, hospital_id, date_from_date, date_to_date
            )

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return []

            appointments = []
            appointments_data = response.data.get("appointments", []) if response.data else []

            for apt_data in appointments_data:
                appointments.append(Appointment(
                    id=str(apt_data.get("id", "")),
                    patient_id=patient_id,
                    professional_id=str(apt_data.get("professional_id", "")),
                    hospital_id=hospital_id,
                    datetime=datetime.fromisoformat(apt_data.get("datetime", "")),
                    status=apt_data.get("status", ""),
                    notes=apt_data.get("notes", "")
                ))

            return appointments

        except Exception as e:
            logger.error(f"Error obteniendo turnos: {e}")
            return []

    # ===============================================
    # FUNCIONALIDAD 4: ESTADO DE CAMAS
    # ===============================================

    async def get_complete_bed_occupancy_data(self, hospital_id: str) -> Dict[str, Any]:
        """Obtener datos de camas vía API"""
        try:
            response = await self.api_service.get_bed_occupancy(hospital_id)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return {"error": response.error}

            # Transformar respuesta API
            data = response.data
            return {
                "resumen_camas": {
                    "camas_totales_estimadas": data.get("total_beds", 0),
                    "camas_ocupadas_estimadas": data.get("occupied_beds", 0),
                    "camas_disponibles_estimadas": data.get("available_beds", 0),
                    "porcentaje_ocupacion": data.get("occupancy_percentage", 0.0),
                    "en_mantenimiento": data.get("in_maintenance", 0),
                    "habilitadas": data.get("enabled", 0)
                },
                "hospital_id": hospital_id,
                "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M')
            }

        except Exception as e:
            logger.error(f"Error obteniendo datos de camas: {e}")
            return {"error": str(e)}

    # ===============================================
    # FUNCIONALIDAD 5: DASHBOARD OPERATIVO
    # ===============================================

    async def get_real_bed_data(self, hospital_id: str) -> Dict[str, Any]:
        """Dashboard operativo vía API"""
        try:
            response = await self.api_service.get_operational_dashboard(hospital_id)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return {"error": response.error}

            # Transformar respuesta API
            data = response.data
            return {
                "resumen_operativo": {
                    "turnos_programados_hoy": data.get("appointments_today", 0),
                    "pacientes_en_atencion_ahora": data.get("patients_in_care_now", 0),
                    "prestadores_activos_hoy": data.get("active_professionals_today", 0),
                    "especialidades_operativas": data.get("operational_specialties", 0),
                    "turnos_ultimas_24h": data.get("appointments_last_24h", 0)
                },
                "hospital_id": hospital_id,
                "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }

        except Exception as e:
            logger.error(f"Error obteniendo dashboard operativo: {e}")
            return {"error": str(e)}

    # ===============================================
    # FUNCIONALIDAD 6: LABORATORIO
    # ===============================================

    async def get_laboratory_data(self, hospital_id: str, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """Datos de laboratorio vía API"""
        try:
            response = await self.api_service.get_laboratory_stats(hospital_id)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return {"error": response.error}

            # Transformar respuesta API
            data = response.data
            return {
                "estadisticas": {
                    "estudios_hoy": data.get("studies_today", 0),
                    "estudios_pendientes": data.get("pending_studies", 0),
                    "estudios_urgentes": data.get("urgent_studies", 0)
                },
                "hospital_id": hospital_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error obteniendo datos laboratorio: {e}")
            return {"error": str(e)}

    # ===============================================
    # FUNCIONALIDAD 7: FARMACIA
    # ===============================================

    async def get_pharmacy_stock(self, hospital_id: str, search_term: Optional[str] = None) -> Dict[str, Any]:
        """Stock de farmacia vía API"""
        try:
            response = await self.api_service.get_pharmacy_stock(hospital_id, search_term)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return {"error": response.error}

            # Transformar respuesta API
            data = response.data
            return {
                "total_articulos": data.get("total_items", 0),
                "busqueda": search_term or "Todos",
                "medicamentos_encontrados": data.get("medications_found", 0),
                "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M')
            }

        except Exception as e:
            logger.error(f"Error obteniendo stock farmacia: {e}")
            return {"error": str(e)}

    # ===============================================
    # FUNCIONALIDAD 8: PRESTADORES
    # ===============================================

    async def get_professionals(self, hospital_id: str) -> List[Professional]:
        """Prestadores vía API"""
        try:
            response = await self.api_service.get_professionals(hospital_id)

            if not response.success:
                logger.error(f"API Error: {response.error}")
                return []

            # Simular estructura de Professional basada en respuesta API
            data = response.data
            professionals = []

            # Crear objetos Professional simulados basados en la respuesta
            total_professionals = data.get("total_active_professionals", 0)
            main_specialties = data.get("main_specialties", [])

            for i in range(min(total_professionals, 10)):  # Limitar a 10 para demo
                specialties = main_specialties[:3] if main_specialties else ["General"]
                professionals.append(Professional(
                    id=str(i + 1),
                    name=f"Prestador {i + 1}",
                    specialties=specialties,
                    hospital_id=hospital_id,
                    metadata={
                        "total_turnos_mes": 0,
                        "ultimo_turno": None
                    }
                ))

            return professionals

        except Exception as e:
            logger.error(f"Error obteniendo profesionales: {e}")
            return []

    # ===============================================
    # FUNCIONES BASE OBLIGATORIAS
    # ===============================================

    async def get_hospitals(self) -> List[Hospital]:
        """Obtener hospitales (configuración estática por ahora)"""
        return [
            Hospital(
                id="3",
                name="Hospital Regional Santiago del Estero",
                address="Av. Belgrano, Santiago del Estero",
                phone="22323",
                active=True
            )
        ]

    async def create_appointment(self, appointment: Appointment) -> str:
        """Crear turno (no implementado por seguridad)"""
        raise NotImplementedError("Creación de turnos no habilitada desde chatbot")

    async def cancel_appointment(self, appointment_id: str, reason: str) -> bool:
        """Cancelar turno (no implementado por seguridad)"""
        raise NotImplementedError("Cancelación de turnos no habilitada desde chatbot")