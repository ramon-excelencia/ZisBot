"""
🧠 LangGraph Agent Funcional - Sin dependencias problemáticas
Usa SQLAlchemy ORM + Groq LLM + workflow simple
"""
import re
import json
import logging
from typing import Dict, Any, TypedDict, List
from datetime import datetime

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from app.services.orm_hospital_service import orm_hospital_service
from app.config.settings import settings

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """Estado del workflow"""
    user_query: str
    hospital_id: str
    conversation_history: List[Dict[str, Any]]
    intent: str
    extracted_data: Dict[str, Any]
    hospital_data: Dict[str, Any]
    ai_response: str
    confidence: float
    processing_steps: List[str]
    errors: List[str]

class WorkingLangGraphAgent:
    """LangGraph Agent que funciona sin problemas de import"""

    def __init__(self):
        self.llm = None
        self.cache = {}  # Cache simple en memoria para respuestas rápidas
        try:
            if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "gsk_placeholder_key_for_testing_purposes_only":
                self.llm = ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model_name="llama-3.1-8b-instant",
                    temperature=0.1,
                    max_tokens=800,  # Reducido para respuestas más rápidas
                    timeout=10       # Timeout más corto
                )
                logger.info("✅ LLM Groq inicializado con optimizaciones")
            else:
                logger.warning("⚠️ No hay API key de Groq disponible")
        except Exception as e:
            logger.error(f"❌ Error inicializando LLM: {e}")

        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Construir workflow optimizado - 2 pasos en lugar de 4"""
        try:
            workflow = StateGraph(WorkflowState)

            # OPTIMIZACIÓN: Solo 2 nodos en lugar de 4
            workflow.add_node("smart_analysis", self._smart_analysis_and_extraction)
            workflow.add_node("fetch_and_respond", self._fetch_data_and_respond)

            # Definir flujo optimizado
            workflow.set_entry_point("smart_analysis")
            workflow.add_edge("smart_analysis", "fetch_and_respond")
            workflow.add_edge("fetch_and_respond", END)

            return workflow.compile()

        except Exception as e:
            logger.error(f"❌ Error construyendo workflow: {e}")
            return None

    async def process_message(self, message: str, user_context: Dict[str, Any]) -> str:
        """Procesar mensaje con workflow"""
        try:
            if not self.workflow:
                return await self._simple_fallback(message, user_context)

            # Estado inicial con contexto de conversación
            initial_state = {
                "user_query": message,
                "hospital_id": str(user_context.get("hospital_id", "3")),
                "conversation_history": user_context.get("conversation_history", []),
                "intent": "",
                "extracted_data": {},
                "hospital_data": {},
                "ai_response": "",
                "confidence": 0.0,
                "processing_steps": [],
                "errors": []
            }

            # Ejecutar workflow
            final_state = await self.workflow.ainvoke(initial_state)

            return final_state["ai_response"]

        except Exception as e:
            logger.error(f"❌ Error en workflow: {e}")
            return await self._simple_fallback(message, user_context)

    async def _smart_analysis_and_extraction(self, state: WorkflowState) -> WorkflowState:
        """ULTRA OPTIMIZADO: Análisis rápido con cache"""
        try:
            state["processing_steps"].append("smart_analysis")
            query = state["user_query"]

            # CACHE CHECK - respuestas inmediatas para consultas repetitivas
            cache_key = hash(query.lower())
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                state.update(cached)
                logger.info(f"⚡ CACHE HIT: {state['intent']}")
                return state

            # OPTIMIZACIÓN 1: Análisis rápido con regex (sin IA)
            quick_analysis = self._quick_pattern_analysis(query)
            if quick_analysis["confidence"] > 0.85:  # Subido el umbral
                state.update(quick_analysis)
                # Guardar en cache
                self.cache[cache_key] = quick_analysis
                logger.info(f"⚡ Análisis regex: {state['intent']} (sin IA)")
                return state

            # OPTIMIZACIÓN 2: IA con prompt MÍNIMO
            if self.llm:
                try:
                    # Prompt ultra conciso para velocidad máxima
                    quick_prompt = f"Clasifica esta consulta hospitalaria en una palabra: '{query[:100]}'\nOpciones: ESPECIALIDADES, PACIENTE_DNI, PACIENTE_NOMBRE, CAMAS, TURNOS, ESTADISTICAS, GENERAL\nRespuesta:"

                    response = await self.llm.ainvoke([("human", quick_prompt)])
                    intent_word = response.content.strip().upper()

                    # Mapeo rápido
                    intent_map = {
                        'ESPECIALIDADES': 'SPECIALTIES_INFO',
                        'PACIENTE_DNI': 'PATIENT_SEARCH_DNI',
                        'PACIENTE_NOMBRE': 'PATIENT_SEARCH_NAME',
                        'CAMAS': 'BEDS_STATUS',
                        'TURNOS': 'APPOINTMENTS_INFO',
                        'ESTADISTICAS': 'HOSPITAL_METRICS'
                    }

                    state["intent"] = intent_map.get(intent_word, "GENERAL_INFO")
                    state["confidence"] = 0.8

                    # Extracción simple de DNI
                    dni_match = re.search(r'\b\d{7,8}\b', query)
                    if dni_match:
                        state["extracted_data"] = {"dni": dni_match.group()}
                    else:
                        state["extracted_data"] = {}

                    logger.info(f"🤖 IA rápida: {state['intent']}")

                except Exception as e:
                    logger.warning(f"IA fallback: {e}")
                    state["intent"] = "GENERAL_INFO"
                    state["confidence"] = 0.6
                    state["extracted_data"] = {}
            else:
                state["intent"] = "GENERAL_INFO"
                state["confidence"] = 0.5
                state["extracted_data"] = {}

            return state

        except Exception as e:
            logger.error(f"❌ Error análisis: {e}")
            state["intent"] = "GENERAL_INFO"
            state["confidence"] = 0.3
            state["extracted_data"] = {}
            return state

    def _quick_pattern_analysis(self, query: str) -> Dict[str, Any]:
        """OPTIMIZACIÓN: Análisis rápido con regex para consultas comunes"""
        query_lower = query.lower()
        result = {"confidence": 0.0, "intent": "GENERAL_INFO", "extracted_data": {}}

        # Patrones de DNI
        dni_pattern = r'\b\d{7,8}\b'
        dni_match = re.search(dni_pattern, query)
        if dni_match:
            result["extracted_data"]["dni"] = dni_match.group()
            if any(word in query_lower for word in ["buscar", "paciente", "dni", "documento"]):
                result["intent"] = "PATIENT_SEARCH_DNI"
                result["confidence"] = 0.9
                return result

        # Especialidades
        if any(word in query_lower for word in ["especialidad", "especialista", "especialidades", "médico", "doctor"]):
            if any(word in query_lower for word in ["todas", "lista", "completa", "disponibles"]):
                result["intent"] = "SPECIALTIES_FULL_LIST"
                result["confidence"] = 0.95
            else:
                result["intent"] = "SPECIALTIES_INFO"
                result["confidence"] = 0.9
            return result

        # Camas
        if any(word in query_lower for word in ["cama", "ocupación", "disponibilidad", "internación"]):
            result["intent"] = "BEDS_STATUS"
            result["confidence"] = 0.9
            return result

        # Servicios
        if any(word in query_lower for word in ["servicio", "servicios", "ofrece", "brinda"]):
            result["intent"] = "SERVICES_INFO"
            result["confidence"] = 0.9
            return result

        # Turnos
        if any(word in query_lower for word in ["turno", "cita", "agenda", "consulta"]):
            result["intent"] = "APPOINTMENTS_INFO"
            result["confidence"] = 0.9
            return result

        return result

    async def _fetch_data_and_respond(self, state: WorkflowState) -> WorkflowState:
        """OPTIMIZADO: Fetch datos + generar respuesta en un solo paso"""
        try:
            state["processing_steps"].append("fetch_and_respond")

            # PASO 1: Obtener datos hospitalarios (optimizado)
            intent = state["intent"]
            hospital_id = state["hospital_id"]
            hospital_data = {}

            # OPTIMIZACIÓN: Cache en memoria para consultas frecuentes
            cache_key = f"{intent}_{hospital_id}"

            if intent == "SPECIALTIES_INFO" or intent == "SPECIALTIES_FULL_LIST":
                result = await orm_hospital_service.obtener_especialidades_con_prestadores(hospital_id)
                if result.success:
                    hospital_data = {"specialties": result.data, "result": result}
                else:
                    hospital_data = {"specialties": [], "result": result}

            elif intent == "SERVICES_INFO":
                result = await orm_hospital_service.obtener_servicios_hospital(hospital_id)
                if result.success:
                    hospital_data = {"services": result.data, "result": result}
                else:
                    hospital_data = {"services": [], "result": result}

            elif intent == "PATIENT_SEARCH_DNI" and state["extracted_data"].get("dni"):
                dni = state["extracted_data"]["dni"]
                result = await orm_hospital_service.buscar_paciente_por_dni(dni, hospital_id)
                if result.success:
                    hospital_data = {"patient": result.data, "result": result}
                else:
                    hospital_data = {"patient": None, "result": result}

            elif intent == "BEDS_STATUS":
                result = await orm_hospital_service.obtener_disponibilidad_camas(hospital_id)
                if result.success:
                    hospital_data = {"beds": result.data, "result": result}
                else:
                    hospital_data = {"beds": {}, "result": result}

            elif intent == "APPOINTMENTS_INFO":
                result = await orm_hospital_service.obtener_turnos_hoy(hospital_id)
                if result.success:
                    hospital_data = {"appointments": result.data, "result": result}
                else:
                    hospital_data = {"appointments": {}, "result": result}
            else:
                # Para otros intents, datos básicos
                hospital_data = {"result": {"success": True, "message": "Consulta general"}}

            state["hospital_data"] = hospital_data

            # PASO 2: Generar respuesta inmediata basada en datos
            try:
                result_success = hospital_data.get("result", {})
                if hasattr(result_success, 'success'):
                    success = result_success.success
                else:
                    success = result_success.get("success", True)

                if success:
                    ai_response = await self._generate_smart_response(state)
                else:
                    ai_response = f"Lo siento, no pude obtener información para tu consulta sobre {intent.lower().replace('_', ' ')}."

                state["ai_response"] = ai_response
                state["confidence"] = 0.9

                logger.info(f"✅ Respuesta generada para {intent}: {len(ai_response)} caracteres")
                return state

            except Exception as e:
                logger.error(f"❌ Error generando respuesta: {e}")
                state["ai_response"] = await self._generate_emergency_fallback(state)
                return state

        except Exception as e:
            logger.error(f"❌ Error crítico en fetch_and_respond: {e}")
            state["errors"].append(f"Error crítico: {e}")
            state["ai_response"] = "Lo siento, hay un problema temporal con el sistema."
            return state

    async def _generate_smart_response(self, state: WorkflowState) -> str:
        """ULTRA OPTIMIZADO: Respuestas directas sin IA cuando sea posible"""
        try:
            intent = state["intent"]
            hospital_data = state["hospital_data"]
            query = state["user_query"]

            # RESPUESTAS DIRECTAS (sin IA) para casos simples
            if intent == "PATIENT_SEARCH_DNI":
                patient = hospital_data.get("patient")
                if patient:
                    nombre = patient.get('nombre_completo', 'N/A').strip()
                    dni = patient.get('documento', 'N/A').strip()
                    telefono = patient.get('telefono', 'No registrado').strip()
                    edad = patient.get('edad', 'No especificada')
                    obra_social = patient.get('obra_social', 'No registrada')

                    response = f"INFORMACIÓN DEL PACIENTE - HOSPITAL REGIONAL\n\n"
                    response += f"DATOS PERSONALES:\n"
                    response += f"Nombre completo: {nombre}\n"
                    response += f"DNI: {dni}\n"
                    response += f"Edad: {edad} años\n"
                    response += f"Teléfono: {telefono}\n"
                    response += f"Obra Social: {obra_social}\n\n"
                    response += f"ESTADO: Paciente registrado en el sistema hospitalario\n"
                    response += f"ÚLTIMA ACTUALIZACIÓN: Datos verificados en tiempo real"

                    return response
                else:
                    dni = state.get("extracted_data", {}).get("dni", "")
                    return f"BÚSQUEDA DE PACIENTE - RESULTADO\n\nNo se encontró registro de paciente con DNI: {dni}\n\nPOSIBLES CAUSAS:\n• El número de documento puede tener un error de tipeo\n• El paciente aún no está registrado en el sistema\n• Puede estar registrado en otra institución del grupo hospitalario\n\nVERIFICACIONES SUGERIDAS:\n• Confirmar que el DNI esté completo y correcto\n• Revisar si hay registros con variaciones del nombre\n• Consultar con el área de admisión para registro manual"

            if intent == "BEDS_STATUS":
                beds = hospital_data.get("beds", {})
                if isinstance(beds, dict) and "resumen" in beds:
                    resumen = beds["resumen"]
                    total = resumen.get("total_camas", 0)
                    ocupadas = resumen.get("camas_ocupadas", 0)
                    disponibles = resumen.get("camas_disponibles", 0)
                    mantenimiento = resumen.get("camas_mantenimiento", 0)
                    ocupacion_pct = resumen.get("porcentaje_ocupacion", 0)

                    response = f"ESTADO ACTUAL DE CAMAS - HOSPITAL REGIONAL\n\n"
                    response += f"RESUMEN OPERATIVO:\n"
                    response += f"• Total de camas: {total} unidades\n"
                    response += f"• Camas ocupadas: {ocupadas} ({ocupacion_pct}% de ocupación)\n"
                    response += f"• Camas disponibles: {disponibles} para nuevas admisiones\n"
                    response += f"• Camas en mantenimiento: {mantenimiento} temporalmente fuera de servicio\n\n"

                    if ocupacion_pct > 85:
                        response += f"⚠️  ALERTA: Ocupación alta ({ocupacion_pct}%). Considerar coordinar con otros sectores.\n"
                    elif ocupacion_pct < 50:
                        response += f"✅ CAPACIDAD DISPONIBLE: Buena disponibilidad para admisiones.\n"
                    else:
                        response += f"📊 OCUPACIÓN NORMAL: Niveles de ocupación dentro de parámetros esperados.\n"

                    # Información por sectores si está disponible
                    sectores = beds.get("sectores", [])
                    if sectores:
                        response += f"\nDETALLE POR SECTORES:\n"
                        for sector in sectores[:3]:  # Primeros 3 sectores
                            nombre = sector.get("sector_nombre", "").strip()
                            sector_total = sector.get("total_camas", 0)
                            sector_ocupadas = sector.get("camas_ocupadas", 0)
                            response += f"• {nombre}: {sector_ocupadas}/{sector_total} ocupadas\n"

                    return response
                else:
                    return "ESTADO DE CAMAS\n\nLos datos de ocupación no están disponibles en este momento. Verifique la conexión con el sistema de gestión hospitalaria o contacte al área de sistemas."

            if intent == "SPECIALTIES_INFO" or intent == "SPECIALTIES_FULL_LIST":
                specs = hospital_data.get("specialties", [])
                if specs and isinstance(specs, list):
                    # Calcular totales reales
                    total_prestadores = sum(spec.get('cantidad_prestadores', 0) for spec in specs if isinstance(spec, dict))

                    # Ordenar por cantidad de prestadores
                    specs_sorted = sorted(specs, key=lambda x: x.get('cantidad_prestadores', 0), reverse=True)

                    response = f"ESPECIALIDADES MÉDICAS DISPONIBLES - HOSPITAL REGIONAL\n\n"
                    response += f"El hospital cuenta actualmente con {len(specs)} especialidades médicas diferentes, "
                    response += f"atendidas por un total de {total_prestadores} profesionales de la salud. Esta amplia "
                    response += f"cobertura nos permite brindar atención integral a la comunidad en prácticamente "
                    response += f"todas las áreas médicas.\n\n"

                    response += f"DISTRIBUCIÓN POR ESPECIALIDAD (ordenadas por cantidad de profesionales):\n\n"

                    for i, spec in enumerate(specs_sorted[:12], 1):
                        if isinstance(spec, dict):
                            nombre = spec.get('nombre', '').strip()
                            cantidad = spec.get('cantidad_prestadores', 0)
                            response += f"{i:2d}. {nombre}: {cantidad} profesionales\n"

                    if len(specs) > 12:
                        response += f"\n[Se muestran las primeras 12 especialidades. Total disponible: {len(specs)} especialidades]\n"

                    # Análisis de cobertura
                    especialidades_grandes = len([s for s in specs if s.get('cantidad_prestadores', 0) >= 20])
                    response += f"\nANÁLISIS DE COBERTURA:\n"
                    response += f"• Especialidades con alta cobertura (≥20 profesionales): {especialidades_grandes}\n"
                    response += f"• Promedio de profesionales por especialidad: {total_prestadores // len(specs)}\n"
                    response += f"• Cobertura total asegurada para atención especializada integral"

                    return response
                else:
                    return "ESPECIALIDADES MÉDICAS\n\nNo se pudieron obtener los datos de especialidades en este momento. Esto puede deberse a un problema temporal de conectividad con el sistema de gestión hospitalaria."

            if intent == "SERVICES_INFO":
                services = hospital_data.get("services", [])
                if services and isinstance(services, list):
                    response = f"SERVICIOS MÉDICOS DISPONIBLES - HOSPITAL REGIONAL\n\n"
                    response += f"Nuestro hospital ofrece un portafolio completo de {len(services)} servicios médicos "
                    response += f"especializados, organizados para brindar atención integral desde servicios ambulatorios "
                    response += f"hasta procedimientos de alta complejidad. Esta diversidad nos permite cubrir "
                    response += f"prácticamente todas las necesidades de salud de nuestra región.\n\n"

                    # Categorizar algunos servicios principales
                    servicios_criticos = [s for s in services if any(palabra in s.get('nombre', '').upper() for palabra in ['UCI', 'EMERGENCIA', 'GUARDIA', 'QUIROFANO'])]
                    laboratorios = [s for s in services if 'LABORATORIO' in s.get('nombre', '').upper()]
                    especialidades_clinicas = [s for s in services if any(palabra in s.get('nombre', '').upper() for palabra in ['CARDIOLOGIA', 'NEUROLOGIA', 'GASTRO', 'TRAUMA'])]

                    response += f"CLASIFICACIÓN DE SERVICIOS:\n"
                    response += f"• Servicios críticos y de emergencia: {len(servicios_criticos)}\n"
                    response += f"• Servicios de laboratorio y diagnóstico: {len(laboratorios)}\n"
                    response += f"• Especialidades clínicas: {len(especialidades_clinicas)}\n"
                    response += f"• Otros servicios especializados: {len(services) - len(servicios_criticos) - len(laboratorios) - len(especialidades_clinicas)}\n\n"

                    response += f"LISTADO DETALLADO DE SERVICIOS:\n\n"

                    # Mostrar servicios organizados
                    for i, serv in enumerate(services[:35], 1):  # Mostrar hasta 35 servicios
                        if isinstance(serv, dict):
                            nombre = serv.get('nombre', '').strip()
                            if nombre:
                                response += f"{i:2d}. {nombre}\n"

                    if len(services) > 35:
                        response += f"\n[Se muestran los primeros 35 servicios. Total disponible: {len(services)} servicios]\n"

                    response += f"\nEsta amplia gama de servicios garantiza que el Hospital Regional pueda "
                    response += f"atender desde consultas de rutina hasta casos de alta complejidad, "
                    response += f"manteniéndose como centro de referencia para la región."

                    return response
                else:
                    return "SERVICIOS MÉDICOS\n\nNo se pudieron obtener los datos de servicios en este momento. Esto puede deberse a un problema temporal de conectividad con el sistema de gestión hospitalaria."

            # Solo usar IA para casos complejos
            if not self.llm:
                return f"Datos obtenidos para {intent}. Para más detalles, llama al 4212121"

            # IA con prompt MÍNIMO
            context = f"Consulta: {query}\nDatos: {self._build_data_summary(hospital_data, intent)}"

            prompt = f"Como ZisBot del Hospital Regional, responde esta consulta de forma profesional y concisa (máximo 2 párrafos):\n{context}"

            response = await self.llm.ainvoke([("human", prompt)])
            return response.content.strip()

        except Exception as e:
            logger.error(f"❌ Error respuesta: {e}")
            return f"Información disponible para {intent}. Para detalles, contacta al 4212121"

    def _build_data_summary(self, hospital_data: Dict, intent: str) -> str:
        """Construir resumen de datos optimizado"""
        try:
            if intent == "SPECIALTIES_INFO" or intent == "SPECIALTIES_FULL_LIST":
                specialties = hospital_data.get("specialties", [])
                return f"{len(specialties)} especialidades disponibles"

            elif "PATIENT_SEARCH" in intent:
                patient = hospital_data.get("patient")
                if patient:
                    return f"Paciente: {patient.get('nombre', 'N/A')} - DNI: {patient.get('documento', 'N/A')}"
                return "Paciente no encontrado"

            return "Datos hospitalarios disponibles"

        except Exception:
            return "Resumen no disponible"

    async def _generate_emergency_fallback(self, state: WorkflowState) -> str:
        """Respuesta de emergencia cuando falla la IA"""
        intent = state["intent"]
        extracted_data = state["extracted_data"]

        if intent == "PATIENT_SEARCH_DNI":
            dni = extracted_data.get("dni", "N/A")
            return f"Estoy procesando la búsqueda del paciente con DNI {dni}. Por favor, espera un momento."

        elif intent == "SPECIALTIES_INFO" or intent == "SPECIALTIES_FULL_LIST":
            return "Estoy consultando las especialidades disponibles en el hospital. La información estará disponible en breve."

        elif intent == "BEDS_STATUS":
            return "Estoy verificando el estado actual de camas en el hospital. Un momento por favor."

        return "Estoy procesando tu consulta. Gracias por tu paciencia."

    async def process(self, message: str, hospital_id: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """MÉTODO PRINCIPAL OPTIMIZADO - Punto de entrada único"""
        try:
            if not self.workflow:
                return await self._create_error_response("Workflow no disponible")

            # Estado inicial optimizado
            initial_state = {
                "user_query": message,
                "hospital_id": str(hospital_id),
                "conversation_history": conversation_history or [],
                "intent": "",
                "extracted_data": {},
                "hospital_data": {},
                "ai_response": "",
                "confidence": 0.0,
                "processing_steps": [],
                "errors": []
            }

            # Ejecutar workflow optimizado (solo 2 nodos)
            final_state = await self.workflow.ainvoke(initial_state)

            return {
                "response": final_state["ai_response"],
                "intent": final_state["intent"],
                "confidence": final_state["confidence"],
                "processing_steps": final_state["processing_steps"],
                "success": True
            }

        except Exception as e:
            logger.error(f"❌ Error crítico en proceso principal: {e}")
            return await self._create_error_response(f"Error: {str(e)}")

    async def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Crear respuesta de error"""
        return {
            "response": "Lo siento, hay un problema temporal con el sistema. Intenta de nuevo en un momento.",
            "intent": "error",
            "confidence": 0.0,
            "processing_steps": ["error"],
            "success": False,
            "error": error_msg
        }

    async def _fetch_hospital_data(self, state: WorkflowState) -> WorkflowState:
        """Obtener datos hospitalarios usando ORM"""
        try:
            state["processing_steps"].append("fetch_data")

            intent = state["intent"]
            hospital_id = state["hospital_id"]
            hospital_data = {}

            if intent == "SPECIALTIES_INFO" or intent == "SPECIALTIES_FULL_LIST":
                result = await orm_hospital_service.obtener_especialidades_con_prestadores(hospital_id)
                hospital_data["specialties"] = result.data if result.success else []
                hospital_data["specialties_result"] = result

            elif intent == "PATIENT_SEARCH_DNI" and state["extracted_data"].get("dni"):
                dni = state["extracted_data"]["dni"]
                result = await orm_hospital_service.buscar_paciente_por_dni(dni, hospital_id)
                hospital_data["patient"] = result.data if result.success else None
                hospital_data["patient_result"] = result

            elif intent == "PATIENT_SEARCH_NAME" and state["extracted_data"].get("name"):
                name = state["extracted_data"]["name"]
                result = await orm_hospital_service.buscar_pacientes_por_nombre(name, hospital_id)
                hospital_data["patients"] = result.data if result.success else []
                hospital_data["patients_result"] = result

            elif intent == "PROVIDERS_INFO":
                result = await orm_hospital_service.obtener_disponibilidad_prestadores(hospital_id)
                hospital_data["providers"] = result.data if result.success else []
                hospital_data["providers_result"] = result

            elif intent == "BEDS_STATUS":
                result = await orm_hospital_service.obtener_estado_camas(hospital_id)
                hospital_data["beds"] = result.data if result.success else {}
                hospital_data["beds_result"] = result

            elif intent == "EMERGENCY_STATUS":
                result = await orm_hospital_service.obtener_estado_emergencias(hospital_id)
                hospital_data["emergency"] = result.data if result.success else {}
                hospital_data["emergency_result"] = result

            elif intent == "APPOINTMENTS_INFO":
                result = await orm_hospital_service.obtener_resumen_turnos(hospital_id)
                hospital_data["appointments"] = result.data if result.success else {}
                hospital_data["appointments_result"] = result

            elif intent == "HOSPITAL_METRICS":
                result = await orm_hospital_service.obtener_metricas_completas(hospital_id)
                hospital_data["metrics"] = result.data if result.success else {}
                hospital_data["metrics_result"] = result

            state["hospital_data"] = hospital_data
            logger.info(f"📊 Datos obtenidos para intent: {intent}")

            return state

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos: {e}")
            state["errors"].append(f"Error datos: {e}")
            state["hospital_data"] = {}
            return state

    async def _generate_response(self, state: WorkflowState) -> WorkflowState:
        """Generar respuesta usando IA real SIEMPRE"""
        try:
            state["processing_steps"].append("generate_response")

            # SIEMPRE intentar usar IA real primero
            if not self.llm:
                logger.error("❌ LLM no disponible - inicializando...")
                try:
                    self.llm = ChatGroq(
                        api_key=settings.GROQ_API_KEY,
                        model_name="llama-3.1-8b-instant",
                        temperature=0.1,
                        max_tokens=800
                    )
                    logger.info("✅ LLM Groq reinicializado")
                except Exception as init_error:
                    logger.error(f"❌ Error reinicializando LLM: {init_error}")
                    state["ai_response"] = await self._generate_emergency_fallback(state)
                    return state

            # Construir contexto enriquecido
            context = self._build_enhanced_context(state)

            # Prompt mejorado para IA real
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Eres ZisBot, asistente de gestión hospitalaria del Hospital Regional de Santiago del Estero.

CONTEXTO LABORAL:
- Usuarios: Personal médico, administrativo y de gestión del hospital (NO pacientes)
- Función: Proveer información operativa y estadísticas en tiempo real
- Estilo: Profesional, preciso y eficiente

IMPORTANTE - LIMITACIONES DE SCOPE:
- SOLO responde consultas relacionadas al hospital y su gestión
- NO respondas preguntas generales, personales, o fuera del ámbito hospitalario
- Si te preguntan algo no relacionado al hospital, indica: "Solo puedo ayudarte con consultas sobre el Hospital Regional"
- Los usuarios son TRABAJADORES del hospital, nunca los trates como pacientes

REGLAS CRÍTICAS:
1. USA ÚNICAMENTE los datos hospitalarios reales proporcionados
2. NUNCA generes información ficticia o aproximada
3. Si no tienes datos específicos, indícalo claramente
4. Mantén respuestas concisas pero completas
5. Incluye siempre timestamps y referencias de datos
6. NO gastes tokens en consultas irrelevantes (clima, noticias, recetas, etc.)

FORMATO DE RESPUESTA:
- Información clara y estructurada
- Datos numéricos exactos del sistema
- Referencias temporales (cuándo se actualizaron los datos)
- Sin información de contacto a menos que sea relevante

NUNCA repitas respuestas idénticas. Cada consulta debe generar una respuesta única basada en los datos actuales."""),
                ("human", context)
            ])

            # Llamada a IA real
            response = await self.llm.ainvoke(prompt.format_messages(context=context))
            state["ai_response"] = response.content.strip()
            state["confidence"] = 0.9  # Alta confianza en IA real

            logger.info(f"🤖 IA REAL - Respuesta generada: {len(response.content)} caracteres")

            return state

        except Exception as e:
            logger.error(f"❌ Error generando respuesta IA real: {e}")
            state["errors"].append(f"Error IA: {e}")
            # Solo si falla completamente la IA
            state["ai_response"] = await self._generate_emergency_fallback(state)
            return state

    def _build_context(self, state: WorkflowState) -> str:
        """Construir contexto para IA"""
        query = state["user_query"]
        intent = state["intent"]
        hospital_data = state["hospital_data"]
        extracted = state["extracted_data"]

        context = f"""CONSULTA: "{query}"
INTENCIÓN: {intent}
HOSPITAL ID: {state["hospital_id"]}
FECHA: {datetime.now().strftime('%d/%m/%Y %H:%M')}

DATOS HOSPITALARIOS EN TIEMPO REAL:
"""

        if intent == "SPECIALTIES_INFO" and "specialties" in hospital_data:
            specialties = hospital_data["specialties"]
            if specialties:
                context += f"\n🏥 ESPECIALIDADES DISPONIBLES ({len(specialties)}):\n"
                for spec in specialties[:10]:
                    try:
                        if isinstance(spec, dict):
                            nombre = spec.get('nombre', 'Sin nombre')
                            cantidad = spec.get('cantidad_prestadores', 0)
                            context += f"• {nombre} - {cantidad} prestadores\n"
                    except Exception:
                        continue
            else:
                context += "\n❌ No se encontraron especialidades\n"

        elif intent == "PATIENT_SEARCH_DNI" and "patient" in hospital_data:
            patient = hospital_data["patient"]
            if patient:
                context += f"\n👤 PACIENTE ENCONTRADO:\n"
                context += f"- Nombre: {patient.get('nombre_completo', 'N/A')}\n"
                context += f"- DNI: {patient.get('documento', 'N/A')}\n"
                context += f"- Edad: {patient.get('edad', 'N/A')}\n"
            else:
                context += f"\n❌ NO SE ENCONTRÓ PACIENTE\n"

        elif intent == "PATIENT_SEARCH_NAME" and "patients" in hospital_data:
            patients = hospital_data["patients"]
            if patients:
                context += f"\n👥 PACIENTES ENCONTRADOS ({len(patients)}):\n"
                for i, p in enumerate(patients[:5], 1):
                    context += f"{i}. {p.get('nombre_completo', 'N/A')} - DNI: {p.get('documento', 'N/A')}\n"
            else:
                context += f"\n❌ NO SE ENCONTRARON PACIENTES\n"

        return context

    def _build_enhanced_context(self, state: WorkflowState) -> str:
        """Construir contexto enriquecido para IA real"""
        query = state["user_query"]
        intent = state["intent"]
        hospital_data = state["hospital_data"]
        extracted = state["extracted_data"]

        # Timestamp actual
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        context = f"""=== CONSULTA DE GESTIÓN HOSPITALARIA ===

CONSULTA ORIGINAL: "{query}"
INTENCIÓN DETECTADA: {intent}
HOSPITAL ID: {state["hospital_id"]} (Hospital Regional Santiago del Estero)
TIMESTAMP: {timestamp}

DATOS EXTRAÍDOS DE LA CONSULTA:
{str(extracted) if extracted else "Ningún dato específico extraído"}

DATOS HOSPITALARIOS EN TIEMPO REAL:
"""

        if (intent == "SPECIALTIES_INFO" or intent == "SPECIALTIES_FULL_LIST") and "specialties" in hospital_data:
            specialties = hospital_data["specialties"]
            if specialties:
                context += f"\n🏥 ESPECIALIDADES MÉDICAS DISPONIBLES (Total: {len(specialties)}):\n"
                context += "Formato: Nombre de Especialidad - Cantidad de Prestadores Activos\n\n"

                # Si es FULL_LIST, mostrar todas; si es INFO, mostrar solo primeras 15
                limit = len(specialties) if intent == "SPECIALTIES_FULL_LIST" else 15

                for i, spec in enumerate(specialties, 1):
                    try:
                        if isinstance(spec, dict):
                            nombre = spec.get('nombre', 'Sin nombre')
                            cantidad = spec.get('cantidad_prestadores', 0)
                            context += f"{i:2d}. {nombre} - {cantidad} prestadores\n"
                    except Exception:
                        continue

                    if i >= limit and intent == "SPECIALTIES_INFO":
                        context += f"\n... y {len(specialties) - limit} especialidades más disponibles\n"
                        break

                context += f"\nDATOS ACTUALIZADOS: {timestamp}\n"
                context += f"FUENTE: Base de datos ZisMed - Consulta ORM directa\n"

                if intent == "SPECIALTIES_INFO" and len(specialties) > 15:
                    context += f"\nNOTA: Esta es una vista resumida. Si el usuario quiere ver TODAS las especialidades, puede pedirlo.\n"
            else:
                context += "\n❌ ERROR: No se encontraron especialidades en la base de datos\n"

        elif intent == "PATIENT_SEARCH_DNI" and "patient" in hospital_data:
            patient = hospital_data["patient"]
            if patient:
                context += f"\n👤 INFORMACIÓN DEL PACIENTE ENCONTRADO:\n"
                context += f"- Nombre Completo: {patient.get('nombre_completo', 'N/A')}\n"
                context += f"- DNI: {patient.get('documento', 'N/A')}\n"
                context += f"- Edad: {patient.get('edad', 'N/A')} años\n"
                context += f"- Teléfono: {patient.get('telefono', 'No registrado')}\n"
                context += f"- Obra Social: {patient.get('obra_social', 'No especificada')}\n"
                context += f"DATOS ACTUALIZADOS: {timestamp}\n"
            else:
                context += f"\n❌ NO SE ENCONTRÓ PACIENTE CON DNI: {extracted.get('dni', 'No especificado')}\n"

        elif intent == "PATIENT_SEARCH_NAME" and "patients" in hospital_data:
            patients = hospital_data["patients"]
            if patients:
                context += f"\n👥 PACIENTES ENCONTRADOS (Total: {len(patients)}):\n"
                for i, p in enumerate(patients[:10], 1):
                    context += f"{i}. {p.get('nombre_completo', 'N/A')} - DNI: {p.get('documento', 'N/A')}\n"
                if len(patients) > 10:
                    context += f"... y {len(patients) - 10} pacientes adicionales\n"
                context += f"DATOS ACTUALIZADOS: {timestamp}\n"
            else:
                context += f"\n❌ NO SE ENCONTRARON PACIENTES CON EL CRITERIO: {extracted.get('name', 'No especificado')}\n"

        context += f"\n=== INSTRUCCIONES PARA LA RESPUESTA ===\n"
        context += f"1. Usa ÚNICAMENTE la información hospitalaria proporcionada arriba\n"
        context += f"2. Genera una respuesta ÚNICA y no repetitiva\n"
        context += f"3. Mantén tono profesional para personal hospitalario\n"
        context += f"4. Incluye el timestamp de actualización de datos\n"
        context += f"5. Si no hay datos, explícalo claramente\n"

        return context

    async def _generate_emergency_fallback(self, state: WorkflowState) -> str:
        """Fallback solo para emergencias cuando IA falla completamente"""
        intent = state["intent"]

        if intent == "SPECIALTIES_INFO":
            return "Error del sistema: No se pudo procesar la consulta de especialidades. Contacte al administrador del sistema."
        elif "PATIENT_SEARCH" in intent:
            return "Error del sistema: No se pudo procesar la búsqueda de pacientes. Contacte al administrador del sistema."
        else:
            return "Error del sistema: Servicio temporalmente no disponible. Contacte al administrador del sistema."

    async def _generate_fallback_response(self, state: WorkflowState) -> str:
        """Generar respuesta fallback sin IA"""
        intent = state["intent"]
        hospital_data = state["hospital_data"]

        if (intent == "SPECIALTIES_INFO" or intent == "SPECIALTIES_FULL_LIST") and "specialties" in hospital_data:
            specialties = hospital_data["specialties"]
            if specialties:
                # Respuesta más conversacional y natural
                total = len(specialties)

                # Saludos variados más naturales
                greetings = [
                    "¡Hola! Me da mucho gusto ayudarte 😊",
                    "¡Qué bueno que consultes conmigo! 👋",
                    "¡Encantada de poder asistirte! 🏥"
                ]
                import random
                greeting = random.choice(greetings)

                if intent == "SPECIALTIES_FULL_LIST":
                    # Lista completa de especialidades
                    response = f"{greeting} Te comparto la **lista completa** de todas nuestras {total} especialidades médicas disponibles:\n\n"
                    response += "📋 **LISTADO COMPLETO DE ESPECIALIDADES:**\n\n"

                    # Mostrar TODAS las especialidades
                    for i, spec in enumerate(specialties, 1):
                        try:
                            if isinstance(spec, dict):
                                nombre = spec.get('nombre', 'Sin nombre').strip()
                                cantidad = spec.get('cantidad_prestadores', 0)
                                emoji = self._get_specialty_emoji(nombre)
                                response += f"{i:2d}. {emoji} **{nombre}** - {cantidad} especialista{'s' if cantidad != 1 else ''}\n"
                        except Exception:
                            continue

                    response += f"\n✅ **Total: {total} especialidades médicas disponibles**\n"
                else:
                    # Vista resumida (SPECIALTIES_INFO)
                    response = f"{greeting} Te cuento que nuestro Hospital Regional cuenta con **{total} especialidades médicas** completamente disponibles para atenderte.\n\n"
                    response += "✨ **Algunas de nuestras especialidades principales:**\n\n"

                    # Mostrar especialidades con emojis y formato amigable
                    for i, spec in enumerate(specialties[:12], 1):
                        try:
                            if isinstance(spec, dict):
                                nombre = spec.get('nombre', 'Sin nombre').strip()
                                cantidad = spec.get('cantidad_prestadores', 0)
                                emoji = self._get_specialty_emoji(nombre)

                                if cantidad == 1:
                                    response += f"{emoji} **{nombre}** - Contamos con {cantidad} especialista altamente calificado\n"
                                else:
                                    response += f"{emoji} **{nombre}** - Disponemos de {cantidad} especialistas en esta área\n"
                        except Exception:
                            continue

                    if total > 12:
                        response += f"\n🔍 ¡Y tenemos {total - 12} especialidades adicionales para ofrecerte!\n"
                        response += "💡 **Tip:** Puedes pedirme **'mostrar todas las especialidades'** para ver la lista completa\n"

                response += "\n💫 **¿Necesitas algo más específico?**\n"
                response += "📞 Para turnos y consultas: **4212121**\n"
                response += "🚨 Emergencias 24hs: **22323** (interno 911)\n"
                response += "\n¡Estoy aquí para ayudarte en lo que necesites! 😊"
                return response

        return "¡Hola! Disculpa, estoy teniendo algunas dificultades técnicas en este momento 😔 Por favor, no dudes en llamarnos directamente al **4212121** donde nuestro equipo estará encantado de ayudarte. ¡Gracias por tu paciencia! 🙏"

    def _get_specialty_emoji(self, specialty_name: str) -> str:
        """Obtener emoji apropiado para cada especialidad"""
        name_lower = specialty_name.lower()

        emoji_map = {
            'cardiolog': '❤️',
            'pediatr': '👶',
            'ginecolog': '🤱',
            'traumatolog': '🦴',
            'neurolog': '🧠',
            'dermatolog': '🧴',
            'oftalmolog': '👁️',
            'otorrinolar': '👂',
            'urolog': '🫧',
            'gastroenter': '🫃',
            'neumolog': '🫁',
            'psiquiatr': '🧠',
            'oncolog': '🎗️',
            'endocrinolog': '⚕️',
            'reumatolog': '🦴',
            'anestesi': '💤',
            'cirug': '🔪',
            'medicina': '👩‍⚕️',
            'radiolog': '🩻',
            'laborator': '🔬',
            'farmac': '💊',
            'nutricion': '🥗',
            'fisioter': '💪',
            'psicolog': '🧠',
            'odontolog': '🦷',
            'emergenc': '🚨'
        }

        for key, emoji in emoji_map.items():
            if key in name_lower:
                return emoji

        return '👩‍⚕️'  # emoji por defecto

    async def _simple_fallback(self, message: str, user_context: Dict[str, Any]) -> str:
        """Fallback simple cuando workflow no está disponible"""
        try:
            hospital_id = str(user_context.get("hospital_id", "3"))

            if any(word in message.lower() for word in ['especialidad', 'especialidades']):
                result = await orm_hospital_service.obtener_especialidades_con_prestadores(hospital_id)
                if result.success and result.data:
                    total = len(result.data)
                    response = f"¡Te ayudo con gusto! En nuestro hospital contamos con {total} especialidades médicas. Te dejo algunas de las más consultadas:\n\n"

                    for i, spec in enumerate(result.data[:15], 1):
                        try:
                            if isinstance(spec, dict):
                                nombre = spec.get('nombre', 'Sin nombre').strip()
                                cantidad = spec.get('cantidad_prestadores', 0)

                                if cantidad == 1:
                                    response += f"{i}. **{nombre}** - Disponemos de {cantidad} especialista\n"
                                else:
                                    response += f"{i}. **{nombre}** - Tenemos {cantidad} especialistas\n"
                        except Exception:
                            continue

                    if total > 15:
                        response += f"\n...además de {total - 15} especialidades más que puedes consultar.\n"

                    response += "\n📞 Para sacar turnos o más detalles, comunicate al **4212121**"
                    return response

            return "Para consultas específicas, llama al 4212121"

        except Exception as e:
            logger.error(f"❌ Error en fallback: {e}")
            return "Disculpa, tengo problemas para procesar tu consulta. Por favor llama al 4212121."


# Instancia global
working_langgraph_agent = WorkingLangGraphAgent()