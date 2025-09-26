from typing import Optional
from app.providers.base import BaseProvider

class MedicalChatbotService:
    def __init__(self, provider: BaseProvider, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.provider = provider
        self.api_key = api_key
        self.model = model
    
    async def process_message(self, user_message: str, conversation_id: str, user_id: str, hospital_id: str) -> str:
        """Simple message processing for testing"""
        
        # Basic DNI detection
        import re
        dni_pattern = re.search(r'\b\d{7,8}\b', user_message)
        if dni_pattern:
            dni = dni_pattern.group()
            try:
                patient = await self.provider.get_patient_by_dni(dni, hospital_id)
                if patient:
                    return f"Hola {patient.name}, encontré su información en nuestro sistema. Para consultar turnos, contáctenos al 4212121."
                else:
                    return f"No encontré un paciente con DNI {dni} en nuestro sistema del Hospital Regional."
            except Exception as e:
                return f"Error consultando DNI {dni}. Intente nuevamente."
        
        # Basic responses
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['hola', 'buenas', 'saludos']):
            return "¡Hola! Soy el asistente virtual del Hospital Regional. ¿En qué puedo ayudarte hoy? Puedes consultarme sobre turnos, especialidades, horarios o información general del hospital."
        
        if any(word in message_lower for word in ['especialidad', 'especialidades', 'doctor']):
            return """ESPECIALIDADES DISPONIBLES - HOSPITAL REGIONAL:

Las más demandadas:
• Ginecología: 13 profesionales (95.7% éxito)
• Traumatología: 26 profesionales (91.4% éxito) 
• Cardiología: 12 profesionales (96.2% éxito)
• Kinesiología: 20 profesionales (87.7% éxito)
• Pediatría: 15 profesionales (97.1% éxito)

Tenemos 52 especialidades disponibles en total.
Para turnos: 4212121"""
        
        if any(word in message_lower for word in ['turno', 'turnos', 'cita']):
            return """TURNOS - HOSPITAL REGIONAL:

Para sacar turnos:
[PHONE] Teléfono: 4212121
[TIME] Horario: 8:00-14:00 (Lun a Vie)
[LOCATION] Presencial: 7:00-12:00 (Mesa de entradas)

Necesitas:
• DNI
• Obra social/prepaga

Para consultar tus turnos, comparte tu DNI (7 u 8 dígitos)."""
        
        if any(word in message_lower for word in ['telefono', 'contacto', 'horario']):
            return """CONTACTO HOSPITAL REGIONAL:

[PHONE] Teléfonos:
• Principal: 22323
• Consultorios: 4212121
• Urgencias: 22323 (int. 911)

[LOCATION] Ubicación:
• Santiago del Estero, Belgrano

[TIME] Horarios:
• General: 7:00-15:00
• Urgencias: 24 horas"""
        
        if any(word in message_lower for word in ['emergencia', 'urgente', 'grave']):
            return """[EMERGENCY] EMERGENCIAS - HOSPITAL REGIONAL:

Para emergencias:
[PHONE] Guardia: 22323 (int. 911)  
[AMBULANCE] Ambulancias: 107
[SCHEDULE] Atención: 24 horas

Concurra inmediatamente a Guardia si tiene:
• Dolor de pecho
• Dificultad respiratoria
• Accidente grave
• Síntomas críticos

[LOCATION] Ubicación: Santiago del Estero, Belgrano"""
        
        # Default response
        return """Soy el asistente del Hospital Regional de Santiago del Estero.

Puedo ayudarte con:
• Consulta de turnos (comparte tu DNI)
• Información de especialidades
• Horarios y contacto
• Emergencias
• Información general

¿En qué te puedo ayudar? Para turnos llama al 4212121."""

# Global service instance
chatbot_service: Optional[MedicalChatbotService] = None

async def init_chatbot_service(provider: BaseProvider, api_key: str, model: str = "llama-3.1-8b-instant"):
    """Initialize chatbot service"""
    global chatbot_service
    chatbot_service = MedicalChatbotService(provider, api_key, model)

async def get_chatbot_service() -> MedicalChatbotService:
    """Get chatbot service instance"""
    if chatbot_service is None:
        raise ValueError("Chatbot service not initialized")
    return chatbot_service