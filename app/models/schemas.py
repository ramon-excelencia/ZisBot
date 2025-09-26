"""
Modelos y esquemas de datos usando Pydantic
Define la estructura de datos para requests, responses y entidades del dominio
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

# Modelos de autenticación
class LoginRequest(BaseModel):
    """Request para login de usuario"""
    cuil: str = Field(..., description="CUIL del usuario")
    password: str = Field(..., description="Contraseña del usuario")

class ValidateCredentialsRequest(BaseModel):
    """Request para validar credenciales (Paso 1)"""
    cuil: str = Field(..., description="CUIL del usuario")
    password: str = Field(..., description="Contraseña del usuario")

class LoginWithInstitutionRequest(BaseModel):
    """Request para login completo con institución (Paso 2)"""
    cuil: str = Field(..., description="CUIL del usuario")
    password: str = Field(..., description="Contraseña del usuario")
    institution_id: int = Field(..., description="ID de la institución seleccionada")
    accepts_terms: bool = Field(default=False, description="Acepta términos y condiciones")

class Institution(BaseModel):
    """Modelo de institución"""
    id: int = Field(..., description="ID de la institución")
    name: str = Field(..., description="Nombre de la institución")
    requires_terms: bool = Field(default=False, description="Requiere aceptar términos")
    address: Optional[str] = Field(None, description="Dirección")
    phone: Optional[str] = Field(None, description="Teléfono")

class ValidateCredentialsResponse(BaseModel):
    """Response de validación de credenciales"""
    success: bool
    message: str
    institutions: List[Institution] = Field(default_factory=list, description="Instituciones disponibles")

class LoginResponse(BaseModel):
    """Response exitosa de login"""
    success: bool
    message: str
    access_token: str
    user: Dict[str, Any]

class UserContext(BaseModel):
    """Contexto del usuario para las consultas"""
    user_id: str
    user_name: str
    role: str
    institution: str
    hospital_id: str
    session_id: Optional[str] = None

# Modelos del chatbot
class ChatMessage(BaseModel):
    """Mensaje de chat del usuario"""
    message: str = Field(..., description="Mensaje del usuario")

class ChatResponse(BaseModel):
    """Respuesta del chatbot"""
    response: str = Field(..., description="Respuesta del bot")
    type: str = Field(default="api_response", description="Tipo de respuesta")
    confidence: float = Field(default=0.9, description="Nivel de confianza")
    processing_time: float = Field(default=0.0, description="Tiempo de procesamiento")
    function_used: str = Field(default="ninguna", description="Función utilizada")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")

# Modelos de entidades del hospital
class Paciente(BaseModel):
    """Información de un paciente"""
    id: int
    documento: str
    nombre: str
    apellido: str
    fecha_nacimiento: Optional[datetime] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    obra_social: Optional[str] = None
    obra_social_numero: Optional[str] = None

class Especialidad(BaseModel):
    """Especialidad médica"""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activa: bool = True

class Medico(BaseModel):
    """Información de un médico"""
    id: int
    nombre: str
    apellido: str
    especialidades: List[str] = []
    matricula: Optional[str] = None

class Turno(BaseModel):
    """Turno médico"""
    id: int
    paciente_id: int
    medico_id: int
    especialidad_id: int
    fecha_hora: datetime
    estado: str
    observaciones: Optional[str] = None

# Modelos de respuesta de API
class ApiResponse(BaseModel):
    """Respuesta estándar de API"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None

class PacienteSearchResponse(ApiResponse):
    """Respuesta de búsqueda de pacientes"""
    data: Optional[List[Paciente]] = None

class EspecialidadListResponse(ApiResponse):
    """Respuesta de lista de especialidades"""
    data: Optional[List[Especialidad]] = None

class VulnerabilidadSocialResponse(ApiResponse):
    """Respuesta de análisis de vulnerabilidad social"""
    data: Optional[Dict[str, Any]] = None

# Modelos de configuración
class SystemStatus(BaseModel):
    """Estado del sistema"""
    system: str
    version: str
    status: str
    ai_system: Dict[str, Any]
    authentication: str
    database: str
    ports: Dict[str, int]
    timestamp: datetime

# Validadores
class MessageValidator:
    """Validadores para mensajes"""

    @staticmethod
    def validate_dni(dni: str) -> bool:
        """Valida formato de DNI argentino"""
        if not dni:
            return False
        # Remover espacios y guiones
        dni_clean = dni.replace(" ", "").replace("-", "")
        return dni_clean.isdigit() and 7 <= len(dni_clean) <= 8

    @staticmethod
    def validate_cuil(cuil: str) -> bool:
        """Valida formato de CUIL argentino"""
        if not cuil:
            return False
        # Remover espacios y guiones
        cuil_clean = cuil.replace(" ", "").replace("-", "")
        return cuil_clean.isdigit() and len(cuil_clean) == 11