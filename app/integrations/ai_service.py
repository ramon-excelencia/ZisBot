"""
Servicio de IA profesional que consume endpoints REST
Ya NO hace consultas SQL directas, sino que consume APIs
"""
import asyncio
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from app.config.settings import settings
from app.services.orm_hospital_service import orm_hospital_service
from app.models.schemas import ChatResponse, UserContext

logger = logging.getLogger(__name__)

class AIService:
    """
    Servicio de IA que usa endpoints REST en lugar de consultas SQL directas
    Esto es mucho más seguro y mantenible
    """

    def __init__(self):
        self.intent_patterns = {
            "buscar_paciente_dni": {
                "patterns": [
                    r"buscar.*paciente.*dni.*(\d{7,8})",
                    r"paciente.*dni.*(\d{7,8})",
                    r"buscar.*(\d{7,8})",
                    r"dni.*(\d{7,8})"
                ],
                "entities": {"dni": r"(\d{7,8})"},
                "model": "api_call",
                "complexity": "medium"
            },
            "buscar_paciente_nombre": {
                "patterns": [
                    r"buscar.*paciente.*nombre.*([\w\s]+)",
                    r"paciente.*llamado.*([\w\s]+)",
                    r"buscar.*([\w\s]+)",
                ],
                "entities": {"nombre": r"nombre\s+([\w\s]+)"},
                "model": "api_call",
                "complexity": "medium"
            },
            "vulnerabilidad_social": {
                "patterns": [
                    r"cuántos.*sin.*obra.*social",
                    r"cantidad.*sin.*obra.*social",
                    r"pacientes.*sin.*obra.*social",
                    r"análisis.*vulnerabilidad",
                    r"vulnerabilidad.*social",
                    r"estadística.*sin.*obra",
                    r"sin.*cobertura.*social",
                    r"pacientes.*vulnerables"
                ],
                "entities": {},
                "model": "api_call",
                "complexity": "high"
            },
            "especialidades_disponibles": {
                "patterns": [
                    r"especialidades.*disponibles",
                    r"qué.*especialidades",
                    r"especialidades.*médicas",
                    r"mostrar.*especialidades",
                    r"listar.*especialidades"
                ],
                "entities": {},
                "model": "api_call",
                "complexity": "low"
            },
            "servicios_hospitalarios": {
                "patterns": [
                    r"servicios.*hospitalarios",
                    r"qué.*servicios",
                    r"servicios.*disponibles",
                    r"mostrar.*servicios",
                    r"todos.*servicios"
                ],
                "entities": {},
                "model": "api_call",
                "complexity": "low"
            }
        }

        self.groq_client = None
        self._initialize_groq()

    def _initialize_groq(self):
        """Inicializar cliente Groq"""
        try:
            if settings.GROQ_API_KEY:
                import groq
                self.groq_client = groq.Groq(api_key=settings.GROQ_API_KEY)
                logger.info("✅ Cliente Groq inicializado")
            else:
                logger.warning("⚠️ No se encontró API key de Groq")
        except Exception as e:
            logger.error(f"❌ Error inicializando Groq: {e}")

    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Extrae entidades del mensaje según el intent"""
        import re

        entities = {}
        intent_config = self.intent_patterns.get(intent, {})

        for entity_name, pattern in intent_config.get("entities", {}).items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                entities[entity_name] = match.group(1).strip()

        # Extracción específica por intent
        if intent == "buscar_paciente_dni":
            dni_match = re.search(r"\b(\d{7,8})\b", message)
            if dni_match:
                entities["dni"] = dni_match.group(1)

        elif intent == "buscar_paciente_nombre":
            # Buscar nombre después de palabras clave
            patterns = [
                r"buscar.*paciente.*nombre\s+([a-záéíóúñü\s]+)",
                r"paciente.*llamado\s+([a-záéíóúñü\s]+)",
                r"buscar\s+([a-záéíóúñü\s]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    entities["nombre"] = match.group(1).strip()
                    break

        return entities

    def _classify_intent(self, message: str) -> Optional[str]:
        """Clasifica la intención del mensaje"""
        import re

        message_lower = message.lower()

        for intent, config in self.intent_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, message_lower):
                    return intent

        return None

    # ===============================================
    # FUNCIONES QUE CONSUMEN ENDPOINTS (NO SQL)
    # ===============================================

    async def _buscar_paciente_por_dni_api(self, entities: Dict, user_context: UserContext) -> Dict[str, Any]:
        """
        🔹 NUEVO: Usa endpoint API en lugar de SQL directo
        """
        dni = entities.get("dni")
        if not dni:
            return {
                "success": False,
                "response": "❌ No se pudo extraer el DNI del mensaje. Por favor, especifica un DNI válido (7-8 dígitos).",
                "type": "error"
            }

        try:
            # ✅ Usa el servicio hospitalario (que actúa como API)
            result = await orm_hospital_service.buscar_paciente_por_dni(dni, 3)

            if result.success and result.data:
                patient = result.data
                obra_social = patient.get("obra_social", "Sin obra social")

                response = f"""
🏥 **Paciente Encontrado**

👤 **Nombre**: {patient.get('nombre', '')} {patient.get('apellido', '')}
📄 **DNI**: {patient.get('documento', '')}
📞 **Teléfono**: {patient.get('telefono', 'No registrado')}
🏥 **Obra Social**: {obra_social}

✅ Información obtenida de la base de datos del Hospital Regional.
                """.strip()

                return {
                    "success": True,
                    "response": response,
                    "type": "patient_search",
                    "data": patient,
                    "function_used": "buscar_paciente_por_dni_api"
                }
            else:
                return {
                    "success": False,
                    "response": f"❌ No se encontró ningún paciente con DNI {dni} en el sistema del Hospital Regional.",
                    "type": "not_found",
                    "function_used": "buscar_paciente_por_dni_api"
                }

        except Exception as e:
            logger.error(f"Error buscando paciente por DNI {dni}: {e}")
            return {
                "success": False,
                "response": "🏥 Disculpas, ocurrió un error técnico. Para asistencia inmediata llama al 4212121.",
                "type": "error"
            }

    async def _analizar_vulnerabilidad_social_api(self, entities: Dict, user_context: UserContext) -> Dict[str, Any]:
        """
        🔹 NUEVO: Usa endpoint API en lugar de SQL directo
        """
        try:
            # ✅ Usa el servicio hospitalario
            result = await orm_hospital_service.obtener_estadisticas_hospital(3)

            if result.success and result.data:
                stats = result.data

                sin_obra_social = next((item for item in stats if "Sin Obra Social" in item.get("categoria", "")), {})
                total_pacientes = next((item for item in stats if "Total Pacientes" in item.get("categoria", "")), {})

                if sin_obra_social and total_pacientes:
                    cantidad = sin_obra_social.get("total", 0)
                    porcentaje = sin_obra_social.get("porcentaje", 0)

                    response = f"""
📊 **Análisis de Vulnerabilidad Social - Hospital Regional**

🚨 **Pacientes sin Obra Social**: {cantidad:,} pacientes ({porcentaje}% del total)

📈 **Estadísticas**:
• Total de pacientes activos: {total_pacientes.get('total', 0):,}
• Pacientes sin cobertura social: {cantidad:,}
• Nivel de vulnerabilidad: {porcentaje}%

💡 **Recomendación**: Este grupo requiere atención prioritaria para programas de asistencia social y acceso a servicios de salud gratuitos.

✅ Datos actualizados del sistema hospitalario.
                    """.strip()

                    return {
                        "success": True,
                        "response": response,
                        "type": "social_analysis",
                        "data": stats,
                        "function_used": "analizar_vulnerabilidad_social_api"
                    }

            return {
                "success": False,
                "response": "❌ No se pudieron obtener los datos de vulnerabilidad social.",
                "type": "error"
            }

        except Exception as e:
            logger.error(f"Error en análisis de vulnerabilidad social: {e}")
            return {
                "success": False,
                "response": "🏥 Disculpas, ocurrió un error técnico. Para asistencia inmediata llama al 4212121.",
                "type": "error"
            }

    async def _obtener_especialidades_api(self, entities: Dict, user_context: UserContext) -> Dict[str, Any]:
        """
        🔹 NUEVO: Usa endpoint API en lugar de SQL directo
        """
        try:
            # ✅ Usa el servicio hospitalario
            result = await orm_hospital_service.obtener_especialidades_con_prestadores(3)

            if result.success and result.data:
                especialidades = result.data

                response = f"🏥 **Especialidades Médicas Disponibles - Hospital Regional**\n\n"

                for esp in especialidades[:15]:  # Mostrar máximo 15
                    nombre = esp.get("nombre", "")
                    cantidad = esp.get("cantidad_medicos", 0)
                    medicos_text = f"({cantidad} médicos)" if cantidad > 0 else "(Sin médicos asignados)"
                    response += f"👨‍⚕️ **{nombre}** {medicos_text}\n"

                response += f"\n✅ Total: {len(especialidades)} especialidades disponibles"
                if len(especialidades) > 15:
                    response += f" (mostrando primeras 15)"

                return {
                    "success": True,
                    "response": response,
                    "type": "specialties_list",
                    "data": especialidades,
                    "function_used": "obtener_especialidades_api"
                }
            else:
                return {
                    "success": False,
                    "response": "❌ No se pudieron obtener las especialidades disponibles.",
                    "type": "error"
                }

        except Exception as e:
            logger.error(f"Error obteniendo especialidades: {e}")
            return {
                "success": False,
                "response": "🏥 Disculpas, ocurrió un error técnico. Para asistencia inmediata llama al 4212121.",
                "type": "error"
            }

    async def _obtener_servicios_api(self, entities: Dict, user_context: UserContext) -> Dict[str, Any]:
        """
        🔹 NUEVO: Usa endpoint API en lugar de SQL directo
        """
        try:
            # ✅ Usa el servicio hospitalario
            result = await orm_hospital_service.obtener_servicios_hospital(3)

            if result.success and result.data:
                servicios = result.data

                response = f"🏥 **Servicios Hospitalarios - Hospital Regional**\n\n"

                for servicio in servicios[:20]:  # Mostrar máximo 20
                    nombre = servicio.get("nombre", "")
                    ubicacion = servicio.get("ubicacion", "")
                    ubicacion_text = f" - {ubicacion}" if ubicacion else ""
                    response += f"🏢 **{nombre}**{ubicacion_text}\n"

                response += f"\n✅ Total: {len(servicios)} servicios hospitalarios disponibles"

                return {
                    "success": True,
                    "response": response,
                    "type": "services_list",
                    "data": servicios,
                    "function_used": "obtener_servicios_api"
                }
            else:
                return {
                    "success": False,
                    "response": "❌ No se pudieron obtener los servicios hospitalarios.",
                    "type": "error"
                }

        except Exception as e:
            logger.error(f"Error obteniendo servicios: {e}")
            return {
                "success": False,
                "response": "🏥 Disculpas, ocurrió un error técnico. Para asistencia inmediata llama al 4212121.",
                "type": "error"
            }

    # ===============================================
    # MÉTODO PRINCIPAL DE PROCESAMIENTO
    # ===============================================

    async def process_message(self, message: str, user_context: Dict) -> Dict[str, Any]:
        """
        Procesa el mensaje del usuario usando endpoints API
        """
        start_time = datetime.now()

        try:
            # Clasificar intención
            intent = self._classify_intent(message)

            if not intent:
                # Usar Groq para respuesta genérica
                return await self._generate_generic_response(message, user_context)

            # Extraer entidades
            entities = self._extract_entities(message, intent)

            # Mapeo de intenciones a funciones API
            function_mapping = {
                "buscar_paciente_dni": self._buscar_paciente_por_dni_api,
                "vulnerabilidad_social": self._analizar_vulnerabilidad_social_api,
                "especialidades_disponibles": self._obtener_especialidades_api,
                "servicios_hospitalarios": self._obtener_servicios_api,
            }

            # Ejecutar función correspondiente
            func = function_mapping.get(intent)
            if func:
                result = await func(entities, UserContext(**user_context))

                # Calcular tiempo de procesamiento
                processing_time = (datetime.now() - start_time).total_seconds()
                result["processing_time"] = processing_time

                return result
            else:
                return await self._generate_generic_response(message, user_context)

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            return {
                "success": False,
                "response": "🏥 Disculpas, ocurrió un error técnico. Para asistencia inmediata llama al 4212121.",
                "type": "error",
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

    async def _generate_generic_response(self, message: str, user_context: Dict) -> Dict[str, Any]:
        """Genera respuesta genérica usando Groq"""
        try:
            if not self.groq_client:
                return {
                    "success": False,
                    "response": "🤖 Sistema de IA no disponible. Puedo ayudarte con: búsqueda de pacientes, especialidades, servicios hospitalarios y estadísticas.",
                    "type": "fallback"
                }

            # Prompt para Groq
            system_prompt = f"""
Eres ZisBot, asistente del Hospital Regional Santiago del Estero.

Usuario: {user_context.get('user_name', 'Usuario')}
Rol: {user_context.get('role', 'general')}

Puedes ayudar con:
- Búsqueda de pacientes por DNI
- Información de especialidades médicas
- Servicios hospitalarios
- Estadísticas de vulnerabilidad social

Responde de manera amigable y profesional en español.
            """

            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=500
            )

            ai_response = response.choices[0].message.content

            return {
                "success": True,
                "response": ai_response,
                "type": "ai_response",
                "function_used": "groq_llm"
            }

        except Exception as e:
            logger.error(f"Error con Groq: {e}")
            return {
                "success": False,
                "response": "🏥 Puedo ayudarte con: búsqueda de pacientes por DNI, especialidades médicas, servicios hospitalarios y análisis de vulnerabilidad social.",
                "type": "fallback"
            }

# Instancia global del servicio de IA
ai_service = AIService()