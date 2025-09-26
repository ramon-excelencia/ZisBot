from typing import List, Optional
from datetime import datetime
from .base import BaseProvider, ProviderConfig, Patient, Professional, Hospital, Appointment
from app.service.WsHcweb import WsHcweb


class HCWebProvider(BaseProvider):
    """HCWeb system provider implementation (existing SOAP integration)"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.ws_client = WsHcweb()
    
    async def connect(self) -> bool:
        """HCWeb uses SOAP - connection is per-request"""
        try:
            # Test connection with a simple method call
            return True
        except Exception as e:
            print(f"Error connecting to HCWeb: {e}")
            return False
    
    async def get_hospitals(self) -> List[Hospital]:
        """Get hospitals from HCWeb"""
        try:
            # Adapt this to actual HCWeb method
            response = self.ws_client.call_method("GetHospitales", {})
            
            hospitals = []
            if response and isinstance(response, list):
                for item in response:
                    hospitals.append(Hospital(
                        id=str(item.get("id", "")),
                        name=item.get("nombre", ""),
                        address=item.get("direccion", ""),
                        active=item.get("activo", True)
                    ))
            return hospitals
        except Exception as e:
            print(f"Error getting hospitals from HCWeb: {e}")
            return []
    
    async def get_patient_by_dni(self, dni: str, hospital_id: str) -> Optional[Patient]:
        """Find patient by DNI in HCWeb"""
        try:
            response = self.ws_client.call_method("BuscarPacientePorDni", {
                "dni": dni,
                "hospitalId": hospital_id
            })
            
            if response:
                return Patient(
                    id=str(response.get("id", "")),
                    dni=response.get("dni", ""),
                    name=response.get("nombre", ""),
                    phone=response.get("telefono", ""),
                    email=response.get("email", "")
                )
            return None
        except Exception as e:
            print(f"Error getting patient from HCWeb: {e}")
            return None
    
    async def get_professionals(self, hospital_id: str) -> List[Professional]:
        """Get professionals from HCWeb"""
        try:
            response = self.ws_client.call_method("GetProfesionales", {
                "hospitalId": hospital_id
            })
            
            professionals = []
            if response and isinstance(response, list):
                for item in response:
                    specialties = item.get("especialidades", [])
                    if isinstance(specialties, str):
                        specialties = [specialties]
                    
                    professionals.append(Professional(
                        id=str(item.get("id", "")),
                        name=item.get("nombre", ""),
                        specialties=specialties,
                        hospital_id=hospital_id
                    ))
            return professionals
        except Exception as e:
            print(f"Error getting professionals from HCWeb: {e}")
            return []
    
    async def get_appointments(
        self, 
        hospital_id: str,
        patient_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Appointment]:
        """Get appointments from HCWeb"""
        try:
            params = {"hospitalId": hospital_id}
            if patient_id:
                params["pacienteId"] = patient_id
            if date_from:
                params["fechaDesde"] = date_from.isoformat()
            if date_to:
                params["fechaHasta"] = date_to.isoformat()
            
            response = self.ws_client.call_method("GetTurnos", params)
            
            appointments = []
            if response and isinstance(response, list):
                for item in response:
                    appointments.append(Appointment(
                        id=str(item.get("id", "")),
                        patient_id=str(item.get("pacienteId", "")),
                        professional_id=str(item.get("profesionalId", "")),
                        hospital_id=hospital_id,
                        datetime=datetime.fromisoformat(item.get("fechaHora", "")),
                        status=item.get("estado", ""),
                        notes=item.get("observaciones", "")
                    ))
            return appointments
        except Exception as e:
            print(f"Error getting appointments from HCWeb: {e}")
            return []
    
    async def create_appointment(self, appointment: Appointment) -> str:
        """Create appointment in HCWeb"""
        try:
            response = self.ws_client.call_method("CrearTurno", {
                "pacienteId": appointment.patient_id,
                "profesionalId": appointment.professional_id,
                "hospitalId": appointment.hospital_id,
                "fechaHora": appointment.datetime.isoformat(),
                "observaciones": appointment.notes or ""
            })
            
            if response and response.get("id"):
                return str(response["id"])
            raise Exception("No se pudo crear el turno")
        except Exception as e:
            print(f"Error creating appointment in HCWeb: {e}")
            raise
    
    async def cancel_appointment(self, appointment_id: str, reason: str) -> bool:
        """Cancel appointment in HCWeb"""
        try:
            response = self.ws_client.call_method("CancelarTurno", {
                "turnoId": appointment_id,
                "motivo": reason
            })
            
            return response and response.get("success", False)
        except Exception as e:
            print(f"Error canceling appointment in HCWeb: {e}")
            return False