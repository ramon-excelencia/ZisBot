from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    provider_name: str
    connection_string: str
    api_key: Optional[str] = None
    additional_config: Optional[Dict[str, Any]] = None


class Patient(BaseModel):
    id: str
    dni: str
    name: str
    phone: str
    email: Optional[str] = None


class Professional(BaseModel):
    id: str
    name: str
    specialties: List[str]
    hospital_id: str


class Hospital(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    active: bool = True


class Appointment(BaseModel):
    id: str
    patient_id: str
    professional_id: str
    hospital_id: str
    datetime: datetime
    status: str
    notes: Optional[str] = None


class BaseProvider(ABC):
    """Base interface for medical system providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_name = config.provider_name
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the medical system"""
        pass
    
    @abstractmethod
    async def get_hospitals(self) -> List[Hospital]:
        """Get all hospitals in the system"""
        pass
    
    @abstractmethod
    async def get_patient_by_dni(self, dni: str, hospital_id: str) -> Optional[Patient]:
        """Find patient by DNI in specific hospital"""
        pass
    
    @abstractmethod
    async def get_professionals(self, hospital_id: str) -> List[Professional]:
        """Get professionals in specific hospital"""
        pass
    
    @abstractmethod
    async def get_appointments(
        self, 
        hospital_id: str,
        patient_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Appointment]:
        """Get appointments with filters"""
        pass
    
    @abstractmethod
    async def create_appointment(self, appointment: Appointment) -> str:
        """Create new appointment, returns appointment ID"""
        pass
    
    @abstractmethod
    async def cancel_appointment(self, appointment_id: str, reason: str) -> bool:
        """Cancel appointment"""
        pass