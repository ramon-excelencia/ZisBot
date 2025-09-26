from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums para validaciones
class EstadoTurno(str, Enum):
    PROGRAMADO = "programado"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    COMPLETADO = "completado"


class ConfianzaIA(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


# Base schemas
class BaseResponse(BaseModel):
    id: int
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None

    class ConfigDict:
        from_attributes = True


# Clinica schemas
class ClinicaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    configuraciones: Optional[Dict[str, Any]] = None
    did_whatsapp: Optional[str] = Field(None, max_length=50)
    activa: bool = True


class ClinicaCreate(ClinicaBase):
    pass


class ClinicaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    configuraciones: Optional[Dict[str, Any]] = None
    did_whatsapp: Optional[str] = Field(None, max_length=50)
    activa: Optional[bool] = None


class ClinicaResponse(BaseResponse, ClinicaBase):
    pass


# Paciente schemas
class PacienteBase(BaseModel):
    dni: str = Field(..., min_length=1, max_length=20)
    telefono: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)

    @field_validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Email debe contener @')
        return v


class PacienteCreate(PacienteBase):
    pass


class PacienteUpdate(BaseModel):
    dni: Optional[str] = Field(None, min_length=1, max_length=20)
    telefono: Optional[str] = Field(None, min_length=1, max_length=20)
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)

    @field_validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Email debe contener @')
        return v


class PacienteResponse(BaseResponse, PacienteBase):
    fecha_registro: Optional[datetime] = None


# Profesional schemas
class ProfesionalBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    especialidades: Optional[List[str]] = None
    horarios: Optional[Dict[str, Any]] = None
    activo: bool = True

    @field_validator('especialidades')
    def validate_especialidades(cls, v):
        if v and not isinstance(v, list):
            raise ValueError('Especialidades debe ser una lista')
        return v


class ProfesionalCreate(ProfesionalBase):
    pass


class ProfesionalUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    especialidades: Optional[List[str]] = None
    horarios: Optional[Dict[str, Any]] = None
    activo: Optional[bool] = None

    @field_validator('especialidades')
    def validate_especialidades(cls, v):
        if v and not isinstance(v, list):
            raise ValueError('Especialidades debe ser una lista')
        return v


class ProfesionalResponse(BaseResponse, ProfesionalBase):
    pass


# Especialidad schemas
class EspecialidadBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = None
    preparacion_previa: Optional[str] = None


class EspecialidadCreate(EspecialidadBase):
    pass


class EspecialidadUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = None
    preparacion_previa: Optional[str] = None


class EspecialidadResponse(BaseResponse, EspecialidadBase):
    pass


# Turno schemas
class TurnoBase(BaseModel):
    id_paciente: int
    id_profesional: int
    id_clinica: int
    fecha_hora: datetime
    estado: EstadoTurno = EstadoTurno.PROGRAMADO
    observaciones: Optional[str] = None


class TurnoCreate(TurnoBase):
    pass


class TurnoUpdate(BaseModel):
    id_paciente: Optional[int] = None
    id_profesional: Optional[int] = None
    id_clinica: Optional[int] = None
    fecha_hora: Optional[datetime] = None
    estado: Optional[EstadoTurno] = None
    observaciones: Optional[str] = None


class TurnoResponse(BaseResponse, TurnoBase):
    # Relaciones anidadas (opcional)
    paciente: Optional[PacienteResponse] = None
    profesional: Optional[ProfesionalResponse] = None
    clinica: Optional[ClinicaResponse] = None


# LogIA schemas
class LogIABase(BaseModel):
    mensaje: str
    respuesta_ia: str
    confianza: Optional[ConfianzaIA] = None
    metadatos: Optional[Dict[str, Any]] = None


class LogIACreate(LogIABase):
    pass


class LogIAResponse(BaseResponse, LogIABase):
    fecha: Optional[datetime] = None


# Schemas para respuestas con listas
class ClinicaListResponse(BaseModel):
    items: List[ClinicaResponse]
    total: int
    page: int = 1
    size: int = 50


class PacienteListResponse(BaseModel):
    items: List[PacienteResponse]
    total: int
    page: int = 1
    size: int = 50


class ProfesionalListResponse(BaseModel):
    items: List[ProfesionalResponse]
    total: int
    page: int = 1
    size: int = 50


class EspecialidadListResponse(BaseModel):
    items: List[EspecialidadResponse]
    total: int
    page: int = 1
    size: int = 50


class TurnoListResponse(BaseModel):
    items: List[TurnoResponse]
    total: int
    page: int = 1
    size: int = 50


class LogIAListResponse(BaseModel):
    items: List[LogIAResponse]
    total: int
    page: int = 1
    size: int = 50