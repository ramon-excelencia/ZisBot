"""
Servicio de Chatbot Principal
Integra LangChain + LangGraph + Memoria Redis + Datos Reales del Hospital
"""

import json
import re
import redis
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.integrations.working_langgraph_agent import working_langgraph_agent
from app.services.orm_hospital_service import orm_hospital_service
from app.services.hospital_data_service import hospital_data_service
# from app.services.memory_service import hybrid_memory, ChatMessage

logger = logging.getLogger(__name__)

class ChatbotService:
    """
    Servicio principal de chatbot que combina:
    - LangChain + LangGraph para procesamiento inteligente
    - Redis para memoria persistente de conversaciones
    - Detección avanzada de consultas médicas específicas
    - Acceso directo a datos reales del hospital
    """

    def __init__(self, groq_api_key: str, redis_url: str = "redis://localhost:6379"):
        # LangChain/LangGraph setup
        self.groq_api_key = groq_api_key
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=2048
        )
        self.workflow = working_langgraph_agent

        # Redis setup for persistent memory
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            logger.info("✅ Redis conectado para memoria persistente")
        except Exception as e:
            logger.warning(f"⚠️ Redis no disponible: {e}")
            self.redis = None
            self._memory_fallback = {}

        # Memory settings
        self.max_memory_messages = 10

        # Cache settings
        self.cache_expiry = 300  # 5 minutos
        logger.info("🚀 ChatbotService inicializado correctamente")

    def _clean_text(self, text: str) -> str:
        """Limpiar texto eliminando espacios excesivos y caracteres extra"""
        if not text or text == 'None':
            return 'No disponible'
        # Remover espacios múltiples y limpiar
        cleaned = ' '.join(text.split())
        return cleaned.strip()

    def _generate_helpful_suggestions(self, query_type: str, original_query: str) -> str:
        """Generar sugerencias útiles basadas en el tipo de consulta"""
        suggestions = {
            'volumen_pacientes': [
                '• "pacientes atendidos en traumatología esta semana"',
                '• "volumen de consultas del 1 al 15 de octubre"',
                '• "cantidad de atendidos en laboratorio últimos 30 días"',
                '• "turnos por servicio entre 01/09/2024 y 30/09/2024"'
            ],
            'horarios_atencion': [
                '• "horarios de traumatología"',
                '• "cuándo atiende el servicio de laboratorio"',
                '• "horarios de consultas externas"',
                '• "disponibilidad de especialistas"'
            ],
            'camas_disponibles': [
                '• "camas en terapia intensiva"',
                '• "disponibilidad en sala general"',
                '• "ocupación de emergencias"',
                '• "estado de camas pediátricas"'
            ]
        }

        return '\n'.join(suggestions.get(query_type, [
            '• "camas disponibles"',
            '• "historia clínica de [nombre/DNI]"',
            '• "horarios de [especialidad]"',
            '• "volumen de atención esta semana"'
        ]))

    def _validate_input(self, user_message: str) -> tuple[bool, str]:
        """Validar entrada del usuario para seguridad"""
        if not user_message or not user_message.strip():
            return False, "Mensaje vacío"

        # Limitar longitud del mensaje
        if len(user_message) > 1000:
            return False, "Mensaje demasiado largo (máximo 1000 caracteres)"

        # Detectar patrones de inyección básicos
        dangerous_patterns = [
            'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET',
            'EXEC', 'EXECUTE', 'SCRIPT', 'javascript:', 'onload=',
            '<script', '</script>', 'eval(', 'alert('
        ]

        message_upper = user_message.upper()
        for pattern in dangerous_patterns:
            if pattern in message_upper:
                return False, f"Patrón no permitido detectado: {pattern}"

        return True, "Válido"

    def _get_cache_key(self, query_type: str, hospital_id: str, **params) -> str:
        """Generar clave de caché para consultas"""
        param_str = "_".join([f"{k}:{v}" for k, v in sorted(params.items()) if v is not None])
        return f"cache:{hospital_id}:{query_type}:{param_str}"

    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """Obtener resultado desde caché"""
        if self.redis:
            try:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Error leyendo caché: {e}")
        return None

    def _set_cache_result(self, cache_key: str, data: Dict):
        """Guardar resultado en caché"""
        if self.redis:
            try:
                self.redis.setex(cache_key, self.cache_expiry, json.dumps(data, default=str))
            except Exception as e:
                logger.warning(f"Error escribiendo caché: {e}")

    def _get_conversation_key(self, conversation_id: str) -> str:
        """Generar clave Redis para conversación"""
        return f"chatbot:conversation:{conversation_id}"

    def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Obtener historial desde Redis tradicional"""
        if self.redis:
            try:
                key = self._get_conversation_key(conversation_id)
                history_json = self.redis.get(key)
                if history_json:
                    return json.loads(history_json)
                return []
            except Exception as redis_error:
                logger.error(f"Error Redis: {redis_error}")
                return []
        else:
            return self._memory_fallback.get(conversation_id, [])

    def _save_conversation_history(self, conversation_id: str, history: List[Dict]):
        """Guardar historial en Redis o fallback"""
        if self.redis:
            try:
                key = self._get_conversation_key(conversation_id)
                # Guardar con expiración de 7 días
                self.redis.setex(key, timedelta(days=7), json.dumps(history))
            except Exception as e:
                logger.error(f"Error guardando en Redis: {e}")
                self._memory_fallback[conversation_id] = history
        else:
            self._memory_fallback[conversation_id] = history

    async def process_message(
        self,
        user_message: str,
        conversation_id: str,
        user_id: str,
        hospital_id: str,
        user_name: str = None
    ) -> str:
        """
        Procesar mensaje del usuario usando el sistema completo
        """
        start_time = time.time()
        try:
            # 0. VALIDAR ENTRADA
            is_valid, validation_msg = self._validate_input(user_message)
            if not is_valid:
                logger.warning(f"⚠️ Entrada inválida: {validation_msg}")
                return f"❌ Entrada no válida: {validation_msg}. Por favor reformule su consulta."

            # 1. OBTENER HISTORIAL DE CONVERSACIÓN
            history = self._get_conversation_history(conversation_id)
            display_name = user_name or "Usuario"
            first_name = display_name.split()[0] if display_name != "Usuario" else "Usuario"

            logger.info(f"📨 Procesando: {user_message[:50]}... | Usuario: {first_name}")

            # 2. ANALIZAR TIPO DE CONSULTA MÉDICA
            try:
                query_info = await self._analyze_medical_query(user_message)
                logger.info(f"🔍 ANÁLISIS: {query_info}")
            except Exception as analysis_error:
                logger.error(f"ERROR EN ANÁLISIS: {analysis_error}")
                return f"ERROR EN ANÁLISIS: {str(analysis_error)}"

            real_data = None
            use_real_data = False

            # 3. SI ES CONSULTA MÉDICA ESPECÍFICA, OBTENER DATOS REALES
            if query_info['type'] != 'general':
                # Verificar caché para consultas frecuentes
                cache_key = None
                if query_info['type'] == 'camas_disponibles':
                    cache_key = self._get_cache_key(
                        'camas_disponibles',
                        hospital_id,
                        servicio=query_info.get('servicio'),
                        fecha=query_info.get('fecha')
                    )
                    real_data = self._get_cached_result(cache_key)

                if not real_data:
                    logger.info(f"🏥 Obteniendo datos reales para: {query_info['type']}")
                    # Determinar rol del usuario (por defecto directivo para Fase 1)
                    user_role = 'directivo'  # En Fase 1 todos los usuarios son directivos
                    real_data = await self._get_real_hospital_data(query_info, user_id, user_role)

                    # Guardar en caché si es consulta de camas
                    if real_data and cache_key and query_info['type'] == 'camas_disponibles':
                        self._set_cache_result(cache_key, real_data)
                else:
                    logger.info(f"⚡ Usando datos desde caché para: {query_info['type']}")

                if real_data:
                    logger.info(f"✅ Datos reales obtenidos exitosamente")
                    use_real_data = True
                else:
                    logger.warning("❌ No se pudieron obtener datos reales")

            # 4. GENERAR RESPUESTA
            if use_real_data and real_data:
                # Usar datos reales para respuesta directa y precisa
                response = await self._generate_response_with_real_data(
                    user_message, query_info, real_data, first_name
                )
                confidence = 0.95
                intent = query_info['type']

            elif query_info['type'] in ['busqueda_paciente_nombre', 'busqueda_paciente_dni', 'historia_clinica', 'historia_clinica_dni', 'volumen_pacientes', 'turnos_programados', 'horarios_atencion']:
                # Respuesta rápida para búsquedas de paciente no encontradas
                response = await self._generate_patient_not_found_response(query_info, first_name)
                confidence = 0.90
                intent = f"{query_info['type']}_not_found"

            else:
                # Usar LangGraph para consultas generales
                try:
                    logger.info("🤖 Ejecutando workflow LangGraph")
                    conversation_context = self._format_context_for_langgraph(
                        history, hospital_id, user_message
                    )

                    result = await self.workflow.process(
                        message=user_message,
                        hospital_id=hospital_id,
                        conversation_history=conversation_context
                    )

                    if result and result.get('intent') != 'error':
                        response = result['response']
                        confidence = result.get('confidence', 0.8)
                        intent = result.get('intent', 'langgraph_success')
                    else:
                        # Fallback inteligente
                        response, confidence, intent = await self._intelligent_fallback(
                            user_message, hospital_id, first_name
                        )

                except Exception as workflow_error:
                    logger.warning(f"❌ Error en workflow: {workflow_error}")
                    import traceback
                    traceback.print_exc()
                    # MOSTRAR ERROR ESPECÍFICO PARA DEBUG
                    response = f"ERROR EN WORKFLOW: {str(workflow_error)}"
                    confidence = 0.0
                    intent = "error"

            # 5. GUARDAR EN MEMORIA
            self._save_to_memory(
                conversation_id, user_message, response, intent, confidence, hospital_id
            )

            # Calcular tiempo de procesamiento
            processing_time = round((time.time() - start_time) * 1000, 2)  # en ms
            logger.info(f"✅ Respuesta generada - Intent: {intent}, Confianza: {confidence}, Tiempo: {processing_time}ms")
            return response

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            import traceback
            traceback.print_exc()
            error_response = f"ERROR DETALLADO: {str(e)}"

            # Guardar error en memoria
            try:
                self._save_to_memory(
                    conversation_id, user_message, error_response, "error", 0.0, hospital_id
                )
            except:
                pass

            return error_response

    async def _analyze_medical_query(self, message: str) -> Dict:
        """
        Analizar mensaje para detectar consultas médicas específicas
        """
        message_lower = message.lower()
        logger.info(f"🔍 ANALIZANDO: '{message}' -> '{message_lower}'")

        # 0. AYUDA/CAPACIDADES DEL SISTEMA (PRIORIDAD ALTA)
        ayuda_keywords = ['ayuda', 'help', 'qué puedo', 'que puedo', 'qué consultas', 'que consultas', 'como funciona', 'capacidades', 'funcionalidades']
        if any(keyword in message_lower for keyword in ayuda_keywords):
            logger.info(f"❓ DETECTADO: ayuda_sistema")
            return {'type': 'ayuda_sistema'}

        # 1. HISTORIA CLÍNICA CON DNI (PRIORIDAD MÁXIMA)
        if (any(word in message_lower for word in ['historia', 'historial', 'clinica', 'expediente'])
            and any(char.isdigit() for char in message)):

            dni = self._extract_dni(message)
            if dni:
                logger.info(f"🏥 DETECTADO: historia_clinica_dni, DNI: {dni}")
                return {
                    'type': 'historia_clinica_dni',
                    'documento': dni,
                    'nombre': None
                }

        # 2. HISTORIA CLÍNICA POR NOMBRE (sin DNI)
        if any(word in message_lower for word in ['historia', 'historial', 'clinica', 'expediente']):
            paciente_info = self._extract_patient_info(message)
            if paciente_info.get('nombre') and not paciente_info.get('documento'):
                logger.info(f"🏥 DETECTADO: historia_clinica, paciente: {paciente_info}")
                return {
                    'type': 'historia_clinica',
                    'documento': None,
                    'nombre': paciente_info.get('nombre')
                }

        # 3. VOLUMEN DE PACIENTES POR SERVICIO/FECHAS (PRIORIDAD ALTA)
        if any(word in message_lower for word in ['pacientes atendidos', 'volumen', 'cantidad atendidos', 'atendidos', 'volumen de atencion', 'consultas por servicio']):
            servicio = self._extract_service_name(message_lower)
            fecha_desde, fecha_hasta = self._extract_date_range(message_lower)
            logger.info(f"📊 DETECTADO: volumen_pacientes, servicio: {servicio}, fechas: {fecha_desde} a {fecha_hasta}")
            return {
                'type': 'volumen_pacientes',
                'servicio': servicio,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta
            }

        # 4. CAMAS DISPONIBLES (PRIORIDAD ALTA - antes que turnos)
        if any(word in message_lower for word in ['cama', 'camas', 'libre', 'ocupad']) or (
            'disponible' in message_lower and not any(esp in message_lower for esp in ['especialidad', 'especialidades'])
        ):
            servicio = self._extract_service_name(message_lower)
            fecha = self._extract_date_from_message(message_lower)
            logger.info(f"🛏️ DETECTADO: camas_disponibles, servicio: {servicio}, fecha: {fecha}")
            return {
                'type': 'camas_disponibles',
                'servicio': servicio,
                'fecha': fecha
            }

        # 5. HORARIOS DE ATENCIÓN (PRIORIDAD ANTES QUE TURNOS)
        horario_keywords = ['horarios', 'atencion', 'horario', 'cuando atiende', 'que horario', 'a que hora']
        horario_phrases = ['horarios de', 'horario de', 'horarios atencion', 'cuando atiende']
        medico_patterns = ['dr ', 'dra ', 'doctor ', 'doctora ']

        if (any(word in message_lower for word in horario_keywords) or
            any(phrase in message_lower for phrase in horario_phrases)):
            servicio = self._extract_service_name(message_lower)
            medico = None

            # Detectar si pregunta por un médico específico
            for pattern in medico_patterns:
                if pattern in message_lower:
                    # Extraer nombre del médico
                    medico_match = re.search(f'{pattern}([A-Za-záéíóúñÑ]+(?:\\s+[A-Za-záéíóúñÑ]+)*)', message_lower)
                    if medico_match:
                        medico = medico_match.group(1).title()
                        break

            logger.info(f"🕒 DETECTADO: horarios_atencion, servicio: {servicio}, médico: {medico}")
            return {
                'type': 'horarios_atencion',
                'servicio': servicio,
                'medico': medico
            }

        # 5.2 TURNOS PROGRAMADOS
        turnos_keywords = ['turnos', 'agenda', 'programados', 'citas', 'consultas']
        turnos_phrases = ['turnos para', 'turnos de', 'cuantos turnos', 'turnos disponibles', 'agenda de']

        if (any(word in message_lower for word in turnos_keywords) or
            any(phrase in message_lower for phrase in turnos_phrases)):
            servicio = self._extract_service_name(message_lower)
            logger.info(f"📅 DETECTADO: turnos_programados, servicio: {servicio}")
            return {
                'type': 'turnos_programados',
                'servicio': servicio
            }

        # 5.5 ESPECIALIDADES - PRIORIDAD ALTA (antes que camas)
        if any(word in message_lower for word in ['especialidad', 'especialidades', 'especialista', 'especialistas']):
            logger.info(f"🏥 DETECTADO: especialidades_disponibles")
            return {
                'type': 'especialidades_disponibles'
            }

        # 5.7 ESTADO DE EMERGENCIAS/GUARDIA
        emergencia_phrases = ['estado de emergencias', 'estado de guardia', 'emergencias del hospital', 'como esta la guardia', 'estado guardia']
        if any(phrase in message_lower for phrase in emergencia_phrases):
            logger.info(f"🚨 DETECTADO: estado_emergencias")
            return {'type': 'estado_emergencias'}

        # 5.8 PRESTADORES DISPONIBLES
        prestadores_phrases = ['prestadores', 'médicos disponibles', 'profesionales disponibles', 'cuantos medicos', 'cuantos prestadores']
        if any(phrase in message_lower for phrase in prestadores_phrases):
            logger.info(f"👨‍⚕️ DETECTADO: prestadores_disponibles")
            return {'type': 'prestadores_disponibles'}


        # 7. BÚSQUEDA DE PACIENTE POR DNI
        if (any(word in message_lower for word in ['dni', 'documento', 'buscar paciente'])
            and any(char.isdigit() for char in message)):

            dni = self._extract_dni(message)
            logger.info(f"🔍 DETECTADO: busqueda_paciente_dni, DNI: {dni}")
            return {
                'type': 'busqueda_paciente_dni',
                'documento': dni
            }

        # 7. VOLUMEN DE PACIENTES - ANTES DE BÚSQUEDA DE NOMBRE
        if any(phrase in message_lower for phrase in ['cuantos pacientes', 'cantidad de pacientes', 'pacientes atendidos', 'volumen de pacientes', 'estadisticas de pacientes']):
            fecha_desde, fecha_hasta = self._extract_date_range_from_message(message_lower)
            servicio = self._extract_service_name(message_lower)
            logger.info(f"📊 DETECTADO: volumen_pacientes, servicio: {servicio}, fechas: {fecha_desde}-{fecha_hasta}")
            return {
                'type': 'volumen_pacientes',
                'servicio': servicio,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta
            }

        # 8. BÚSQUEDA DE PACIENTE POR NOMBRE - MÁS ESPECÍFICA
        # Solo buscar si hay patrones específicos de búsqueda de paciente
        if (any(phrase in message_lower for phrase in ['buscar paciente', 'busca paciente', 'datos del paciente', 'paciente con nombre'])
            or (any(word in message_lower for word in ['buscar', 'busca']) and 'nombre' in message_lower)
            or (any(word in message_lower for word in ['buscar', 'busca']) and 'apellido' in message_lower)):

            paciente_info = self._extract_patient_info(message)
            if paciente_info.get('nombre'):
                logger.info(f"👤 DETECTADO: busqueda_paciente_nombre, paciente: {paciente_info}")
                return {
                    'type': 'busqueda_paciente_nombre',
                    'nombre': paciente_info.get('nombre')
                }

        # 9. CONSULTA GENERAL
        logger.info(f"❓ DETECTADO: consulta_general")
        return {'type': 'general'}

    def _extract_patient_info(self, message: str) -> Dict:
        """Extraer información del paciente del mensaje"""
        logger.info(f"🔍 EXTRAYENDO INFO PACIENTE: '{message}'")

        # Extraer DNI
        dni_match = re.search(r'\b(\d{7,8})\b', message)
        documento = dni_match.group(1) if dni_match else None
        logger.info(f"🆔 DNI: {documento}")

        # Extraer nombre con patrones mejorados - ORDEN ESPECÍFICO A GENERAL
        name_patterns = [
            # Patrón 1: "con apellido [APELLIDO]" - MÁS ESPECÍFICO - SOLO ÚLTIMA PALABRA
            r'(?:con\s+apellido|apellido)\s+([A-ZÁÉÍÓÚñÑa-záéíóúñÑ]+)(?:\s|$)',
            # Patrón 2: "con nombre [NOMBRE]" - SOLO PRIMERA PALABRA DESPUÉS
            r'(?:con\s+nombre)\s+([A-ZÁÉÍÓÚñÑa-záéíóúñÑ]+)(?:\s|$)',
            # Patrón 3: "llamado [NOMBRE]"
            r'llamad[oa]\s+([A-ZÁÉÍÓÚñÑa-záéíóúñÑ]+(?:\s+[A-ZÁÉÍÓÚñÑa-záéíóúñÑ]+)*)',
            # Patrón 4: "siguiente paciente/nombre: [NOMBRE]"
            r'siguiente\s+(?:paciente|nombre)[\s:]+([A-ZÁÉÍÓÚñÑa-záéíóúñÑ\s]+)',
            # Patrón 5: Nombres todo en mayúsculas (formato hospital)
            r'\b([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})+)\b',
            # Patrón 6: Formato título tradicional
            r'(?:historia|historial|clinica|expediente).*?(?:de|del|para)\s+([A-ZÁÉÍÓÚñÑ][a-záéíóúñÑ]+\s+[A-ZÁÉÍÓÚñÑ][a-záéíóúñÑ]+)',
        ]

        nombre = None
        for i, pattern in enumerate(name_patterns):
            name_match = re.search(pattern, message, re.IGNORECASE)
            if name_match:
                nombre = name_match.group(1).strip()
                nombre = ' '.join(word.capitalize() for word in nombre.split())
                logger.info(f"👤 NOMBRE encontrado con patrón {i}: '{nombre}'")
                break

        if not nombre:
            logger.info(f"❌ NO se encontró nombre")

        return {'documento': documento, 'nombre': nombre}

    def _extract_dni(self, message: str) -> str:
        """Extraer DNI del mensaje"""
        dni_patterns = [
            r'dni[:\s]*(\d{7,8})',
            r'documento[:\s]*(\d{7,8})',
            r'paciente[,\s]*dni[:\s]*(\d{7,8})',
            r'\b(\d{7,8})\b',
        ]

        for pattern in dni_patterns:
            dni_match = re.search(pattern, message, re.IGNORECASE)
            if dni_match:
                return dni_match.group(1) if dni_match.groups() else dni_match.group()
        return None

    def _extract_service_name(self, message_lower: str) -> str:
        """Extraer nombre de servicio médico"""
        service_patterns = {
            'uci': ['uci', 'terapia intensiva', 'cuidados intensivos'],
            'internacion': ['internacion', 'internación', 'sala común'],
            'emergencias': ['emergencia', 'guardia', 'urgencia'],
            'pediatria': ['pediatria', 'pediatría', 'niños']
        }

        for service, patterns in service_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                return service

        # Servicios adicionales para consultas específicas
        servicios_adicionales = {
            'cardiologia': ['cardiologia', 'cardiología', 'corazón'],
            'traumatologia': ['traumatologia', 'traumatología', 'trauma'],
            'neurologia': ['neurologia', 'neurología'],
            'ginecologia': ['ginecologia', 'ginecología'],
            'medicina_general': ['medicina general', 'clinica medica'],
            'cirugia': ['cirugia', 'cirugía']
        }

        for service, patterns in servicios_adicionales.items():
            if any(pattern in message_lower for pattern in patterns):
                return service

        return None

    def _extract_service_and_date(self, message_lower: str) -> tuple:
        """Extraer nombre de servicio y fecha del mensaje"""
        import re

        # Extraer servicio
        servicio = self._extract_service_name(message_lower)

        # Extraer mes y año
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        mes = None
        año = None

        # Buscar mes por nombre
        for nombre_mes, num_mes in meses.items():
            if nombre_mes in message_lower:
                mes = num_mes
                break

        # Buscar mes por número
        if not mes:
            mes_match = re.search(r'mes (\d{1,2})', message_lower)
            if mes_match:
                mes = int(mes_match.group(1))

        # Buscar año
        año_match = re.search(r'(\d{4})', message_lower)
        if año_match:
            año = int(año_match.group(1))
        else:
            año = datetime.now().year  # Año actual por defecto

        return servicio, mes, año

    def _extract_date_from_message(self, message_lower: str) -> str:
        """Extraer fecha del mensaje en formato YYYY-MM-DD"""
        import re

        # Patrones de fecha comunes
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY o DD-MM-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD o YYYY-MM-DD
            r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',  # DD de MMMM de YYYY
            r'hoy|hoje',  # Hoy
            r'mañana|amanhã',  # Mañana
            r'ayer|ontem'  # Ayer
        ]

        meses_esp = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        # Buscar fechas específicas
        for pattern in date_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if pattern == r'hoy|hoje':
                    return date.today().strftime('%Y-%m-%d')
                elif pattern == r'mañana|amanhã':
                    return (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
                elif pattern == r'ayer|ontem':
                    return (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                elif 'de' in pattern and len(match.groups()) == 3:
                    # Formato DD de MMMM de YYYY
                    dia, mes_nombre, año = match.groups()
                    mes_num = meses_esp.get(mes_nombre.lower())
                    if mes_num:
                        try:
                            fecha = date(int(año), mes_num, int(dia))
                            return fecha.strftime('%Y-%m-%d')
                        except ValueError:
                            pass
                elif len(match.groups()) == 3:
                    # Otros formatos numéricos
                    g1, g2, g3 = match.groups()
                    try:
                        # Intentar DD/MM/YYYY
                        if len(g3) == 4:  # YYYY está al final
                            fecha = date(int(g3), int(g2), int(g1))
                        else:  # YYYY está al principio
                            fecha = date(int(g1), int(g2), int(g3))
                        return fecha.strftime('%Y-%m-%d')
                    except ValueError:
                        continue

        return None

    def _extract_date_range_from_message(self, message_lower: str) -> tuple:
        """Extraer rango de fechas del mensaje"""
        from datetime import date, timedelta
        import re

        # Detectar rangos de tiempo comunes
        if any(phrase in message_lower for phrase in ['ultimos 30 dias', 'último mes', 'ultimo mes']):
            fecha_hasta = date.today()
            fecha_desde = fecha_hasta - timedelta(days=30)
            return fecha_desde, fecha_hasta

        if any(phrase in message_lower for phrase in ['ultimos 7 dias', 'última semana', 'ultima semana']):
            fecha_hasta = date.today()
            fecha_desde = fecha_hasta - timedelta(days=7)
            return fecha_desde, fecha_hasta

        if any(phrase in message_lower for phrase in ['ultimos 15 dias', 'últimas 2 semanas']):
            fecha_hasta = date.today()
            fecha_desde = fecha_hasta - timedelta(days=15)
            return fecha_desde, fecha_hasta

        if any(phrase in message_lower for phrase in ['este mes', 'mes actual']):
            hoy = date.today()
            fecha_desde = date(hoy.year, hoy.month, 1)
            fecha_hasta = hoy
            return fecha_desde, fecha_hasta

        # Por defecto: últimos 30 días
        fecha_hasta = date.today()
        fecha_desde = fecha_hasta - timedelta(days=30)
        return fecha_desde, fecha_hasta

    def _extract_date_range(self, message_lower: str) -> tuple:
        """Extraer rango de fechas del mensaje"""
        import re

        # Patrones para rangos de fechas
        range_patterns = [
            r'entre\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+y\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # entre DD/MM/YYYY y DD/MM/YYYY
            r'del\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+al\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',    # del DD/MM/YYYY al DD/MM/YYYY
            r'desde\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+hasta\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', # desde DD/MM/YYYY hasta DD/MM/YYYY
            r'del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(\w+)', # del 1 al 15 de octubre
            r'entre\s+el\s+(\d{1,2})\s+y\s+el\s+(\d{1,2})\s+de\s+(\w+)', # entre el 1 y el 15 de octubre
            r'esta\s+semana',
            r'este\s+mes',
            r'últimos?\s+(\d+)\s+días?',
            r'pasados?\s+(\d+)\s+días?'
        ]

        meses_esp = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        hoy = date.today()

        for pattern in range_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if pattern == r'esta\s+semana':
                    # Lunes de esta semana hasta hoy
                    inicio_semana = hoy - timedelta(days=hoy.weekday())
                    return inicio_semana, hoy

                elif pattern == r'este\s+mes':
                    # Primer día del mes hasta hoy
                    inicio_mes = hoy.replace(day=1)
                    return inicio_mes, hoy

                elif 'últimos' in pattern or 'pasados' in pattern:
                    # Últimos N días
                    dias = int(match.group(1))
                    fecha_inicio = hoy - timedelta(days=dias)
                    return fecha_inicio, hoy

                elif len(match.groups()) == 2 and all('/' in g or '-' in g for g in match.groups()):
                    # Fechas completas DD/MM/YYYY
                    try:
                        fecha1_str, fecha2_str = match.groups()

                        # Parsear primera fecha
                        parts1 = re.split(r'[/-]', fecha1_str)
                        fecha1 = date(int(parts1[2]), int(parts1[1]), int(parts1[0]))

                        # Parsear segunda fecha
                        parts2 = re.split(r'[/-]', fecha2_str)
                        fecha2 = date(int(parts2[2]), int(parts2[1]), int(parts2[0]))

                        return fecha1, fecha2
                    except (ValueError, IndexError):
                        continue

                elif len(match.groups()) == 3:
                    # Formato: del 1 al 15 de octubre
                    try:
                        dia1, dia2, mes_nombre = match.groups()
                        mes_num = meses_esp.get(mes_nombre.lower())
                        if mes_num:
                            año_actual = hoy.year
                            fecha1 = date(año_actual, mes_num, int(dia1))
                            fecha2 = date(año_actual, mes_num, int(dia2))
                            return fecha1, fecha2
                    except (ValueError, KeyError):
                        continue

        # Si no encuentra rango específico, usar últimos 30 días por defecto
        return hoy - timedelta(days=30), hoy

    def _validate_user_permissions(self, user_id: str, user_role: str, patient_dni: str = None) -> Dict[str, bool]:
        """
        Validar permisos de usuario para acceso a datos de pacientes

        Args:
            user_id: ID del usuario que consulta
            user_role: Rol del usuario (directivo, medico, enfermero, etc.)
            patient_dni: DNI del paciente consultado

        Returns:
            Dict con permisos: {
                'can_view_basic_data': bool,
                'can_view_clinical_history': bool,
                'can_view_detailed_evolution': bool,
                'can_view_medications': bool
            }
        """
        # Configuración de permisos por rol
        role_permissions = {
            'directivo': {
                'can_view_basic_data': True,
                'can_view_clinical_history': True,
                'can_view_detailed_evolution': True,
                'can_view_medications': True
            },
            'director': {
                'can_view_basic_data': True,
                'can_view_clinical_history': True,
                'can_view_detailed_evolution': True,
                'can_view_medications': True
            },
            'medico': {
                'can_view_basic_data': True,
                'can_view_clinical_history': True,
                'can_view_detailed_evolution': True,
                'can_view_medications': True
            },
            'jefe_servicio': {
                'can_view_basic_data': True,
                'can_view_clinical_history': True,
                'can_view_detailed_evolution': True,
                'can_view_medications': True
            },
            'enfermero': {
                'can_view_basic_data': True,
                'can_view_clinical_history': False,
                'can_view_detailed_evolution': False,
                'can_view_medications': True
            },
            'administrativo': {
                'can_view_basic_data': True,
                'can_view_clinical_history': False,
                'can_view_detailed_evolution': False,
                'can_view_medications': False
            }
        }

        # Por defecto, rol directivo para usuarios del sistema de informes
        if not user_role or user_role in ['informe_system', 'sistema_informe']:
            user_role = 'directivo'

        return role_permissions.get(user_role.lower(), {
            'can_view_basic_data': True,
            'can_view_clinical_history': False,
            'can_view_detailed_evolution': False,
            'can_view_medications': False
        })

    async def _get_real_hospital_data(self, query_info: Dict, user_id: str = None, user_role: str = 'directivo') -> Optional[Dict]:
        """Obtener datos reales del hospital según tipo de consulta"""
        try:
            query_type = query_info['type']

            if query_type == 'historia_clinica':
                # Validar permisos antes de obtener historia clínica
                dni_paciente = query_info.get('documento')
                permissions = self._validate_user_permissions(user_id, user_role, dni_paciente)

                if not permissions['can_view_clinical_history']:
                    logger.warning(f"❌ Usuario {user_id} sin permisos para historia clínica")
                    return {
                        'type': 'access_denied',
                        'message': f"No tienes autorización para acceder a la historia clínica de este paciente.",
                        'contact_info': "Contacta al administrador del sistema para solicitar acceso."
                    }

                # Usar ORM para historia clínica completa (más detallada)
                result = await orm_hospital_service.obtener_historia_clinica_completa(
                    dni=query_info.get('documento'),
                    nombre=query_info.get('nombre')
                )

                # Convertir ApiResponse a dict para compatibilidad
                if hasattr(result, 'success') and result.success:
                    result = result.data
                else:
                    # Fallback al servicio anterior
                    result = await hospital_data_service.get_historia_clinica(
                        documento=query_info.get('documento'),
                        nombre=query_info.get('nombre')
                    )

                if result:
                    result['user_permissions'] = permissions
                    logger.info(f"📋 Historia clínica autorizada para usuario: {user_id}")

                return result

            elif query_type == 'ayuda_sistema':
                # Generar información de capacidades del sistema
                result = await self._get_system_help()
                logger.info(f"❓ Ayuda sistema resultado: {result is not None}")
                return result

            elif query_type == 'historia_clinica_dni':
                # Validar permisos antes de obtener historia clínica por DNI
                dni = query_info.get('documento')
                permissions = self._validate_user_permissions(user_id, user_role, dni)

                if not permissions['can_view_clinical_history']:
                    logger.warning(f"❌ Usuario {user_id} sin permisos para historia clínica DNI: {dni}")
                    return {
                        'type': 'access_denied',
                        'message': f"No tienes autorización para acceder a la historia clínica del paciente con DNI {dni}.",
                        'contact_info': "Contacta al administrador del sistema para solicitar acceso."
                    }

                if dni:
                    # Usar historia clínica completa para DNI específico
                    result = await orm_hospital_service.obtener_historia_clinica_completa(dni=dni)
                    if hasattr(result, 'success') and result.success:
                        logger.info(f"📋 Historia clínica completa autorizada por DNI: {dni} para usuario: {user_id}")
                        historia_completa = result.data
                        historia_completa['user_permissions'] = permissions
                        return {
                            'type': 'historia_clinica_found',
                            'historia_completa': historia_completa,
                            'dni': dni,
                            'user_permissions': permissions
                        }
                    else:
                        # Fallback a búsqueda básica
                        result = await orm_hospital_service.buscar_paciente_por_dni(dni, 3)
                        if result.success:
                            logger.info(f"📋 Datos básicos por DNI: {dni} para usuario: {user_id}")
                            return {
                                'type': 'historia_clinica_found',
                                'patient': result.data,
                                'dni': dni,
                                'user_permissions': permissions
                            }
                return None

            elif query_type == 'busqueda_paciente_dni':
                # Usar ORM service para búsqueda por DNI
                dni = query_info.get('documento')
                if dni:
                    result = await orm_hospital_service.buscar_paciente_por_dni(dni, 3)
                    if result.success:
                        logger.info(f"👤 Paciente encontrado por DNI: {dni}")
                        return {
                            'type': 'patient_found',
                            'patient': result.data
                        }
                return None

            elif query_type == 'busqueda_paciente_nombre':
                # Usar hospital_data_service para búsqueda por nombre
                nombre = query_info.get('nombre')
                if nombre:
                    result = await hospital_data_service.buscar_paciente_por_nombre(nombre)
                    if result:
                        logger.info(f"👤 Paciente encontrado por nombre: {nombre}")
                        return {
                            'type': 'patient_found_by_name',
                            'patient': result,
                            'nombre': nombre
                        }
                return None

            elif query_type == 'camas_disponibles':
                # Usar hospital_data_service para camas con filtros
                result = await hospital_data_service.get_camas_disponibles(
                    servicio_nombre=query_info.get('servicio'),
                    fecha=query_info.get('fecha')
                )
                logger.info(f"🛏️ Camas disponibles resultado: {result is not None}")
                return result

            elif query_type == 'estado_emergencias':
                # Usar datos reales de camas y estadísticas para estado de emergencias
                result = await hospital_data_service.get_estado_emergencias()
                logger.info(f"🚨 Estado emergencias resultado: {result is not None}")
                return result

            elif query_type == 'prestadores_disponibles':
                # Usar datos reales de prestadores
                result = await hospital_data_service.get_prestadores_disponibles()
                logger.info(f"👨‍⚕️ Prestadores disponibles resultado: {result is not None}")
                return result

            elif query_type == 'volumen_pacientes':
                # Usar hospital_data_service para volumen de pacientes con rangos de fechas
                servicio = query_info.get('servicio')
                fecha_desde = query_info.get('fecha_desde')
                fecha_hasta = query_info.get('fecha_hasta')
                result = await hospital_data_service.get_volumen_pacientes(
                    servicio_nombre=servicio,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta
                )
                logger.info(f"📊 Volumen pacientes resultado: {result is not None}")
                return result

            elif query_type == 'turnos_programados':
                # Usar hospital_data_service para turnos programados
                servicio = query_info.get('servicio', 'medicina_general')
                result = await hospital_data_service.get_turnos_programados(servicio)
                logger.info(f"📅 Turnos programados resultado: {result is not None}")
                return result

            elif query_type == 'horarios_atencion':
                # Usar hospital_data_service para horarios de atención
                servicio = query_info.get('servicio', 'medicina_general')
                result = await hospital_data_service.get_horarios_atencion(servicio)
                logger.info(f"🕒 Horarios atención resultado: {result is not None}")
                return result

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos reales: {e}")

        return None

    async def _generate_response_with_real_data(
        self,
        user_message: str,
        query_info: Dict,
        real_data: Dict,
        first_name: str
    ) -> str:
        """Generar respuesta usando datos reales del hospital"""

        query_type = query_info['type']

        if query_type == 'historia_clinica':
            return await self._format_historia_clinica_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'ayuda_sistema':
            return await self._format_help_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'historia_clinica_dni':
            return await self._format_historia_clinica_dni_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'busqueda_paciente_dni':
            return await self._format_patient_search_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'busqueda_paciente_nombre':
            return await self._format_patient_search_by_name_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'camas_disponibles':
            return await self._format_beds_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'estado_emergencias':
            return await self._format_emergency_status_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'prestadores_disponibles':
            return await self._format_prestadores_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'volumen_pacientes':
            return await self._format_volume_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'turnos_programados':
            return await self._format_turnos_response(
                user_message, query_info, real_data, first_name
            )
        elif query_type == 'horarios_atencion':
            return await self._format_horarios_response(
                user_message, query_info, real_data, first_name
            )

        return f"Hola {first_name}, encontré información pero necesito más detalles para ayudarte mejor."

    async def _generate_patient_not_found_response(self, query_info: Dict, first_name: str) -> str:
        """Generar respuesta rápida cuando no se encuentra el paciente"""

        query_type = query_info['type']

        if query_type in ['busqueda_paciente_nombre', 'historia_clinica']:
            nombre = query_info.get('nombre', 'el nombre solicitado')
            return f"""🔍 **BÚSQUEDA DE PACIENTE POR NOMBRE**

❌ No se encontró paciente con el nombre "{nombre}" en nuestro sistema.

**Sugerencias:**
• Verificar la ortografía del nombre completo
• Probar con nombre y apellido
• Confirmar que el paciente esté registrado
• Contactar admisión: **4212121**

**Alternativas de búsqueda:**
• Búsqueda por DNI (más precisa)
• Consulta en recepción del hospital

¿Puedo ayudarte con otra consulta, {first_name}?"""

        elif query_type in ['busqueda_paciente_dni', 'historia_clinica_dni']:
            dni = query_info.get('documento', 'el DNI solicitado')
            return f"""❌ **Paciente No Encontrado**

🔍 **DNI consultado:** {dni}

**Posibles causas:**
• El paciente no está registrado en nuestro sistema
• Error en el número de documento ingresado
• Problemas temporales de conectividad

**Te recomiendo:**
• Verificar el número de DNI
• Contactar admisión: **4212121**
• Consultar el sistema principal de historias clínicas

¿Puedo ayudarte con otra consulta, {first_name}?"""

        else:
            return f"Hola {first_name}, no pude encontrar la información solicitada. Por favor contacta al 4212121."

    async def _format_historia_clinica_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de historia clínica con control de permisos"""

        # Verificar si hay denegación de acceso
        if real_data and real_data.get('type') == 'access_denied':
            return f"""🚫 **ACCESO DENEGADO - HISTORIA CLÍNICA**

Hola {first_name}, {real_data.get('message')}

**Información:**
• Solo personal autorizado puede acceder a historias clínicas
• Esta acción ha sido registrada en el sistema
• {real_data.get('contact_info')}

🏥 **Hospital Regional Santiago del Estero**
📞 **Soporte:** 4212121 - Interno 950"""

        if not real_data or real_data.get('error'):
            nombre = query_info.get('nombre', 'el paciente solicitado')
            return f"""Hola {first_name}, no pude acceder a la historia clínica de {nombre} en este momento.

**Posibles causas:**
• El paciente no está registrado en nuestro sistema
• Error temporal en la base de datos
• Información de búsqueda incorrecta

**Te recomiendo:**
• Verificar los datos del paciente
• Contactar admisión: **4212121**
• Revisar el sistema de historias clínicas

¿Necesitas ayuda con algo más?"""

        # Formatear datos reales encontrados
        patient_data = real_data.get('paciente', {})
        internaciones = real_data.get('internaciones', [])

        response = f"""🏥 **HISTORIA CLÍNICA ENCONTRADA**

📋 **Datos del Paciente:**
• **Nombre:** {patient_data.get('nombre_completo', 'No disponible')}
• **DNI:** {patient_data.get('documento', 'No disponible')}
• **Fecha de Nacimiento:** {patient_data.get('fecha_nacimiento', 'No disponible')}
• **Obra Social:** {patient_data.get('obra_social', 'No especificada')}

📊 **Historial de Internaciones:**"""

        if internaciones:
            for i, int_data in enumerate(internaciones[:3], 1):
                response += f"""
**{i}.** {int_data.get('fecha_ingreso', 'Fecha no disponible')} - {int_data.get('sector', 'Sector no especificado')}
   • Diagnóstico: {int_data.get('diagnostico', 'No especificado')}
   • Estado: {int_data.get('estado', 'No especificado')}"""
        else:
            response += "\n• Sin internaciones registradas"

        response += f"""

✅ **Actualizado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**
📞 **Consultas:** 4212121"""

        return response

    async def _format_historia_clinica_dni_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de historia clínica basada en DNI con control de permisos"""

        # Verificar si hay denegación de acceso
        if real_data and real_data.get('type') == 'access_denied':
            return f"""🚫 **ACCESO DENEGADO - HISTORIA CLÍNICA**

Hola {first_name}, {real_data.get('message')}

**Información:**
• Solo personal autorizado puede acceder a historias clínicas
• Esta acción ha sido registrada en el sistema
• {real_data.get('contact_info')}

🏥 **Hospital Regional Santiago del Estero**
📞 **Soporte:** 4212121 - Interno 950"""

        if real_data and real_data.get('type') == 'historia_clinica_found':
            # Manejar tanto formato nuevo (historia_completa) como viejo (patient)
            if 'historia_completa' in real_data:
                historia_completa = real_data['historia_completa']
                patient = historia_completa['paciente']
                internaciones = historia_completa.get('internaciones', [])
                turnos = historia_completa.get('turnos_medicos', [])
                resumen = historia_completa.get('resumen', {})
            else:
                # Fallback para formato antiguo
                patient = real_data['patient']
                internaciones = []
                turnos = []
                resumen = {}

            dni = real_data['dni']

            # Protección para campos que pueden ser None
            nombre = patient.get('nombre_completo', 'No disponible')
            documento = patient.get('documento', 'No disponible')

            # Formatear respuesta con datos completos
            response = f"""📋 **HISTORIA CLÍNICA COMPLETA - DNI {dni}**

👤 **Datos del Paciente:**
• **Nombre:** {nombre.strip() if nombre else 'No disponible'}
• **Documento:** {documento.strip() if documento else 'No disponible'}
• **Edad:** {patient.get('edad', 'No especificada')} años
• **CUIL:** {patient.get('cuil', 'No disponible')}
• **Teléfono:** {patient.get('telefono') or 'No registrado'}
• **Email:** {patient.get('correo') or 'No disponible'}"""

            # Resumen estadístico si está disponible
            if resumen:
                total_int = resumen.get('total_internaciones', 0)
                internacion_actual = resumen.get('internacion_actual', False)
                total_turnos = resumen.get('total_turnos', 0)

                response += f"""

📊 **Resumen Clínico:**
• **Total Internaciones:** {total_int}
• **Estado Actual:** {'INTERNADO' if internacion_actual else 'AMBULATORIO'}
• **Turnos Registrados:** {total_turnos}"""

            # Información de internaciones
            if internaciones:
                response += "\n\n🏥 **INTERNACIONES:**"
                for i, int_data in enumerate(internaciones[:3], 1):  # Mostrar máximo 3
                    estado = int_data.get('estado', 'Desconocido')
                    fecha_ing = int_data.get('fecha_ingreso', 'No disponible')
                    fecha_alt = int_data.get('fecha_alta', 'Sin alta')
                    cama = int_data.get('cama', 'No especificada')
                    sector = int_data.get('sector', 'No especificado')
                    medico = int_data.get('medico_ingreso', 'No asignado')

                    response += f"""
  {i}. **{estado.upper()}**
     • Ingreso: {fecha_ing} | Alta: {fecha_alt}
     • Ubicación: {sector} - {cama}
     • Médico: {medico}"""

                if len(internaciones) > 3:
                    response += f"\n     ... y {len(internaciones) - 3} internaciones más"

            # Información de turnos médicos
            if turnos:
                response += "\n\n📅 **TURNOS MÉDICOS RECIENTES:**"
                for i, turno in enumerate(turnos[:5], 1):  # Mostrar máximo 5
                    fecha = turno.get('fecha_hora', 'No disponible')
                    especialidad = turno.get('especialidad', 'Sin especialidad')
                    medico = turno.get('medico', 'No asignado')
                    estado = turno.get('estado', 'Desconocido')

                    response += f"""
  {i}. {fecha}
     • Especialidad: {especialidad}
     • Médico: {medico}
     • Estado: {estado}"""

                if len(turnos) > 5:
                    response += f"\n     ... y {len(turnos) - 5} turnos más"

            elif not internaciones:
                response += "\n\n🏠 **Estado:** Paciente ambulatorio (sin internaciones recientes)"

            response += f"""

✅ **Consulta realizada:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**
📞 **Mesa de Ayuda:** 4212121"""

            return response
        else:
            dni = query_info.get('documento', 'el solicitado')
            return f"""❌ **Historia Clínica No Encontrada**

🔍 **DNI consultado:** {dni}

**Posibles causas:**
• El paciente no está registrado en nuestro sistema
• Error en el número de documento ingresado
• Problemas temporales de conectividad

**Te recomiendo:**
• Verificar el número de DNI
• Contactar admisión: **4212121**
• Consultar el sistema principal de historias clínicas

¿Puedo ayudarte con otra consulta, {first_name}?"""

    async def _format_patient_search_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de búsqueda de paciente"""

        if real_data and real_data.get('type') == 'patient_found':
            patient = real_data['patient']

            # Protección para campos que pueden ser None
            nombre = patient.get('nombre_completo', 'No disponible')
            documento = patient.get('documento', 'No disponible')

            response = f"""🏥 **PACIENTE ENCONTRADO**

📋 **Información Completa:**
• **Nombre:** {self._clean_text(nombre)}
• **DNI:** {self._clean_text(documento)}
• **Edad:** {patient.get('edad', 'No especificada')} años
• **Teléfono:** {self._clean_text(str(patient.get('telefono', '')))}
• **Email:** {self._clean_text(str(patient.get('email', '')))}
• **Obra Social:** {self._clean_text(str(patient.get('obra_social', '')))}

🏥 **Estado de Internación:**"""

            # Información de internación (SIEMPRE mostrar para directivos)
            internacion_vigente = patient.get('internacion_vigente')
            if internacion_vigente and internacion_vigente.get('internado'):
                int_data = internacion_vigente
                response += f"""
• **Estado:** INTERNADO
• **Cama:** {self._clean_text(str(int_data.get('cama', '')))}
• **Habitación:** {self._clean_text(str(int_data.get('habitacion', '')))}
• **Sector:** {self._clean_text(str(int_data.get('sector', '')))}
• **Médico Responsable:** {self._clean_text(str(int_data.get('medico_responsable', '')))}
• **Fecha de Ingreso:** {int_data.get('fecha_ingreso', 'No disponible')}
• **Días Internado:** {int_data.get('dias_internado', 'No calculado')}"""
            else:
                response += f"""
• **Estado:** AMBULATORIO (no internado)
• **Cama:** No asignada
• **Sector:** No aplicable
• **Médico Responsable:** Consulta externa"""

            response += f"""

✅ **Actualizado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**"""

            return response
        else:
            dni = query_info.get('documento', 'el solicitado')
            return f"""🔍 **BÚSQUEDA DE PACIENTE**

❌ No se encontró paciente con DNI {dni} en nuestro sistema.

**Sugerencias:**
• Verificar que el DNI esté completo (7-8 dígitos)
• Confirmar que el paciente esté registrado
• Contactar admisión: **4212121**

¿Puedo ayudarte con otra consulta?"""

    async def _format_patient_search_by_name_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de búsqueda de paciente por nombre"""

        if real_data and real_data.get('type') == 'patient_found_by_name':
            patient_data = real_data['patient']
            nombre_buscado = real_data['nombre']

            response = f"""🔍 **PACIENTE ENCONTRADO POR NOMBRE**

👤 **Búsqueda:** {nombre_buscado}

📋 **Datos del Paciente:**
• **Nombre Completo:** {patient_data.get('nombre_completo', 'No disponible')}
• **DNI:** {patient_data.get('documento', 'No disponible')}
• **Fecha de Nacimiento:** {patient_data.get('fecha_nacimiento', 'No disponible')}
• **Edad:** {patient_data.get('edad', 'No especificada')} años
• **Teléfono:** {patient_data.get('telefono') or 'No registrado'}
• **Email:** {patient_data.get('email') or 'No disponible'}
• **Obra Social:** {patient_data.get('obra_social', 'No especificada')}

🏥 **Estado de Internación:**"""

            # Información de internación (SIEMPRE mostrar para directivos)
            internacion_vigente = patient_data.get('internacion_vigente')
            if internacion_vigente and internacion_vigente.get('internado'):
                int_data = internacion_vigente
                response += f"""
• **Estado:** INTERNADO
• **Cama:** {self._clean_text(str(int_data.get('cama', '')))}
• **Habitación:** {self._clean_text(str(int_data.get('habitacion', '')))}
• **Sector:** {self._clean_text(str(int_data.get('sector', '')))}
• **Médico Responsable:** {self._clean_text(str(int_data.get('medico_responsable', '')))}
• **Fecha de Ingreso:** {int_data.get('fecha_ingreso', 'No disponible')}
• **Días Internado:** {int_data.get('dias_internado', 'No calculado')}"""
            else:
                response += f"""
• **Estado:** AMBULATORIO (no internado)
• **Cama:** No asignada
• **Sector:** No aplicable
• **Médico Responsable:** Consulta externa"""

            response += f"""

✅ **Búsqueda exitosa:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**
📞 **Consultas:** 4212121"""

            return response
        else:
            nombre_buscado = query_info.get('nombre', 'el nombre solicitado')
            return f"""🔍 **BÚSQUEDA DE PACIENTE POR NOMBRE**

❌ No se encontró paciente con el nombre "{nombre_buscado}" en nuestro sistema.

**Sugerencias:**
• Verificar la ortografía del nombre completo
• Probar con nombre y apellido
• Confirmar que el paciente esté registrado
• Contactar admisión: **4212121**

**Alternativas de búsqueda:**
• Búsqueda por DNI (más precisa)
• Consulta en recepción del hospital

¿Puedo ayudarte con otra consulta, {first_name}?"""

    async def _format_beds_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta completa de estadísticas de camas"""

        if not real_data or real_data.get('error'):
            return f"""⚠️ **Consulta de Camas Temporalmente No Disponible**

Hola {first_name}, no pude acceder al estado actual de camas.

🔄 **Posibles soluciones:**
• Intentá nuevamente en unos minutos
• Consultá directamente a Central de Camas: interno 950
• Llamá a Mesa de Ayuda: 4212121

⏰ **Horario de Consultas:** Lunes a Viernes 8:00 - 18:00"""

        # Extraer estadísticas completas
        total_camas = real_data.get('total_camas', 0)
        total_ocupadas = real_data.get('total_ocupadas', 0)
        total_disponibles = real_data.get('total_disponibles', 0)
        porcentaje_ocupacion = real_data.get('porcentaje_ocupacion', 0)
        porcentaje_disponibilidad = real_data.get('porcentaje_disponibilidad', 0)
        servicio_consultado = real_data.get('servicio_consultado', 'General')
        fecha_consultada = real_data.get('fecha_consultada')
        estadisticas_sectores = real_data.get('estadisticas_por_sector', {})

        # Presentar números de manera inteligente
        if total_camas > 1000:
            capacidad_desc = f"El sistema hospitalario regional cuenta con {total_camas} camas"
        else:
            capacidad_desc = f"Total de camas: {total_camas}"

        # Obtener información completa de camas desde debug
        debug_info = await self._get_debug_camas_info()

        response = f"""🛏️ **CAPACIDAD HOSPITALARIA - SANTIAGO DEL ESTERO**

📊 **Estado Actual - {servicio_consultado.upper()}:**
• **Total camas Hospital Regional: {debug_info.get('total_hospital', total_camas)}**
• **Camas operativas (Planta baja): {total_camas}**
• **Ocupadas:** {total_ocupadas} ({porcentaje_ocupacion}%)
• **Disponibles:** {total_disponibles} ({porcentaje_disponibilidad}%)

🏥 **Distribución por Estado:**
• **Habilitadas:** {debug_info.get('habilitadas', 'N/A')}
• **No habilitadas:** {debug_info.get('no_habilitadas', 'N/A')}
• **En mantenimiento:** {debug_info.get('mantenimiento', 'N/A')}

📍 **Distribución por Sector:**
• **Planta baja:** {debug_info.get('planta_baja', total_camas)} camas
• **Administración:** {debug_info.get('administracion', 'N/A')} camas"""

        # Agregar información de fecha si se consultó por fecha específica
        if fecha_consultada:
            response += f"""
• **Fecha consultada:** {fecha_consultada}"""

        response += f"""
• **Actualizado:** {datetime.now().strftime('%H:%M:%S')}

📈 **Indicadores:**"""

        # Indicador visual de ocupación
        if porcentaje_ocupacion >= 90:
            response += f"""
• 🔴 **Ocupación CRÍTICA** ({porcentaje_ocupacion}%) - Capacidad casi completa"""
        elif porcentaje_ocupacion >= 70:
            response += f"""
• 🟡 **Ocupación ALTA** ({porcentaje_ocupacion}%) - Monitoreo requerido"""
        else:
            response += f"""
• 🟢 **Ocupación NORMAL** ({porcentaje_ocupacion}%) - Capacidad adecuada"""

        # Mostrar estadísticas por sector si no se filtró por uno específico
        if estadisticas_sectores and len(estadisticas_sectores) > 1:
            response += f"""

🏥 **Detalle por Sectores:**"""

            # Ordenar sectores por ocupación descendente
            sectores_ordenados = sorted(
                estadisticas_sectores.items(),
                key=lambda x: x[1]['porcentaje_ocupacion'],
                reverse=True
            )

            for sector, stats in sectores_ordenados[:5]:  # Mostrar solo los 5 más ocupados
                ocupacion = stats['porcentaje_ocupacion']
                emoji = "🔴" if ocupacion >= 90 else "🟡" if ocupacion >= 70 else "🟢"
                response += f"""
• {emoji} **{sector}**: {stats['disponibles']}/{stats['total']} disponibles ({stats['porcentaje_disponibilidad']}%)"""

            if len(estadisticas_sectores) > 5:
                response += f"""
• ➕ **Y {len(estadisticas_sectores) - 5} sectores más...**"""

        response += f"""

🏥 **Contactos:**
• **Admisión/Reservas:** 4212121
• **Guardia/Emergencias:** 22323 (int. 911)
• **Central de Camas:** Interno 950

✅ **Estado actualizado en tiempo real**
🕐 **Próxima actualización:** {(datetime.now() + timedelta(minutes=15)).strftime('%H:%M')}"""

        return response

    async def _format_volume_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de volumen de pacientes con rangos de fechas y desglose por día"""

        if not real_data or real_data.get('error'):
            servicio = query_info.get('servicio', 'el servicio consultado')
            return f"""⚠️ **Lo siento {first_name}**

No pude encontrar información de volumen para {servicio}.

🔍 **Intentá con:**
• "volumen de laboratorio del 1 al 15 de octubre"
• "pacientes atendidos en cardiología esta semana"
• "cantidad de atendidos en traumatología últimos 30 días"
• "consultas por servicio entre 01/10/2024 y 15/10/2024"

📞 **Consultas:** 4212121"""

        servicio = real_data.get('servicio', 'Todos los servicios')
        periodo = real_data.get('periodo', 'período consultado')
        total_pacientes = real_data.get('total_pacientes_atendidos', 0)
        total_turnos = real_data.get('total_turnos', 0)
        estadisticas = real_data.get('estadisticas', {})
        servicios = real_data.get('servicios', [])
        desglose_dias = real_data.get('desglose_por_dia', [])

        response = f"""📊 **VOLUMEN DE PACIENTES ATENDIDOS**

🏥 **Servicio:** {servicio}
📅 **Período:** {periodo}

📈 **Resumen General:**
• **Pacientes únicos atendidos:** {total_pacientes}
• **Total de turnos:** {total_turnos}
• **Promedio diario:** {estadisticas.get('promedio_diario', 0)} pacientes/día
• **Días con atención:** {estadisticas.get('dias_con_atencion', 0)}
"""

        # Mostrar estadísticas por servicio si hay múltiples servicios
        if len(servicios) > 1:
            response += "\n🔬 **Por Servicio:**\n"
            for servicio_info in servicios[:5]:  # Mostrar top 5
                response += f"• **{servicio_info['nombre']}:** {servicio_info['pacientes_atendidos']} pac. ({servicio_info['total_turnos']} turnos)\n"

            if len(servicios) > 5:
                response += f"• ... y {len(servicios) - 5} servicios más\n"

        # Mostrar desglose por días si hay pocos días
        if len(desglose_dias) <= 10 and len(desglose_dias) > 0:
            response += "\n📅 **Desglose por día:**\n"
            for dia_info in desglose_dias:
                fecha_str = dia_info['fecha']
                # Formatear fecha para mostrar más amigable
                try:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                    fecha_formateada = fecha_obj.strftime('%d/%m')
                except:
                    fecha_formateada = fecha_str

                response += f"• **{fecha_formateada}:** {dia_info['pacientes_atendidos']} pacientes ({dia_info['total_turnos']} turnos)\n"

        response += f"""

✅ **Actualizado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**
📞 **Consultas:** 4212121
*Solo turnos efectivamente atendidos*"""

        return response

    async def _format_turnos_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de turnos programados"""

        if not real_data or real_data.get('error'):
            servicio = query_info.get('servicio') or 'el servicio consultado'
            return f"Hola {first_name}, no pude acceder a los turnos de {servicio}. Contacta al 4212121."

        servicio = real_data.get('servicio', 'Servicio no especificado')
        total_turnos = real_data.get('total_turnos', 0)
        turnos = real_data.get('turnos', [])

        response = f"""📅 **TURNOS PROGRAMADOS**

🏥 **Servicio:** {servicio}
📋 **Total programados:** {total_turnos}

🕒 **Próximos turnos:**"""

        if turnos:
            for i, turno in enumerate(turnos[:5], 1):  # Mostrar solo los primeros 5
                fecha = turno.get('fecha', 'Fecha no disponible')
                hora = turno.get('hora', 'Hora no disponible')
                paciente = turno.get('paciente', 'Paciente no especificado')
                medico = turno.get('medico', 'Médico no asignado')

                response += f"""
**{i}.** {fecha} - {hora}
   • Paciente: {paciente}
   • Médico: {medico}"""
        else:
            response += "\n• No hay turnos programados"

        response += f"""

✅ **Actualizado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**
📞 **Para turnos:** 4212121"""

        return response

    async def _format_horarios_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de horarios de atención"""

        medico = query_info.get('medico')
        servicio = query_info.get('servicio', 'el servicio consultado')

        if not real_data or real_data.get('error'):
            if medico:
                return f"""⚠️ **Horarios del Dr/Dra {medico} No Disponibles**

Hola {first_name}, no pude obtener los horarios específicos del Dr/Dra {medico}.

🔄 **Te sugiero:**
• Contactá directamente a la secretaría de la especialidad
• Llamá al 4212121 y pedí que te pasen con el servicio
• Consultá los horarios generales de la especialidad
• Preguntá por turnos disponibles

📞 **Contactos útiles:**
• Mesa de Ayuda: 4212121
• Guardia: 22323 (int. 911)

🏥 **Hospital Regional Santiago del Estero**"""
            else:
                servicio_nombre = servicio.title() if servicio else "el servicio consultado"
                return f"""⚠️ **Horarios de {servicio_nombre} No Disponibles**

Hola {first_name}, no pude obtener los horarios de {servicio or "el servicio consultado"} en este momento.

🔄 **Alternativas:**
• Probá consultando horarios de otros servicios
• Llamá directamente al hospital: 4212121
• Consultá en Mesa de Informes (planta baja)

📞 **Contacto directo:** 4212121 - opción 2 (informes)"""

        servicio = real_data.get('servicio', 'Servicio no especificado')
        horarios = real_data.get('horarios', [])
        consultorios = real_data.get('consultorios', 0)

        response = f"""🕒 **HORARIOS DE ATENCIÓN**

🏥 **Servicio:** {servicio}
🏢 **Consultorios disponibles:** {consultorios}

📅 **Horarios por día:**"""

        if horarios:
            for horario in horarios:
                dia = horario.get('dia', 'Día no especificado')
                hora_inicio = horario.get('hora_inicio', 'No disponible')
                hora_fin = horario.get('hora_fin', 'No disponible')
                cantidad = horario.get('cantidad_turnos', 0)

                response += f"""
• **{dia}:** {hora_inicio} - {hora_fin} ({cantidad} turnos)"""
        else:
            response += "\n• Horarios no disponibles"

        response += f"""

✅ **Información basada en turnos programados**
🏥 **Hospital Regional Santiago del Estero**
📞 **Para consultas:** 4212121"""

        return response

    async def _format_emergency_status_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de estado de emergencias usando datos reales"""

        if not real_data or real_data.get('error'):
            return f"""⚠️ **Estado de Emergencias No Disponible**

Hola {first_name}, no pude obtener el estado actual de emergencias.

🔄 **Alternativas:**
• Contactá directamente a Guardia: 22323 (int. 911)
• Llamá a Mesa de Ayuda: 4212121
• Consultá el estado de camas disponibles

🏥 **Hospital Regional Santiago del Estero**"""

        # Usar datos reales de camas para inferir estado de emergencias
        total_camas = real_data.get('total_camas', 0)
        ocupadas = real_data.get('camas_ocupadas', 0)
        disponibles = real_data.get('camas_disponibles', 0)
        porcentaje_ocupacion = real_data.get('porcentaje_ocupacion', 0)

        # Determinar nivel de alerta basado en ocupación real
        if porcentaje_ocupacion >= 85:
            nivel_alerta = "🔴 ALTA"
            estado_descripcion = "alta demanda"
        elif porcentaje_ocupacion >= 70:
            nivel_alerta = "🟡 MODERADA"
            estado_descripcion = "demanda moderada"
        else:
            nivel_alerta = "🟢 NORMAL"
            estado_descripcion = "capacidad disponible"

        response = f"""🚨 **ESTADO DE EMERGENCIAS - HOSPITAL REGIONAL**

📊 **Capacidad Hospitalaria Actual:**
• Total de camas: {total_camas}
• Ocupadas: {ocupadas} ({porcentaje_ocupacion:.1f}%)
• Disponibles: {disponibles}

🏥 **Nivel de Alerta:** {nivel_alerta}
• Estado: {estado_descripcion}
• Capacidad de atención: {'Limitada' if porcentaje_ocupacion >= 85 else 'Disponible'}

📞 **Contactos de Emergencia:**
• Guardia/Emergencias: 22323 (int. 911)
• Admisión: 4212121
• Central de Camas: Interno 950

✅ **Actualizado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**

*Estado basado en ocupación de camas en tiempo real*"""

        return response

    async def _format_prestadores_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de prestadores disponibles"""

        if not real_data or real_data.get('error'):
            return f"""⚠️ **Prestadores No Disponibles**

Hola {first_name}, no pude acceder a la información de prestadores en este momento.

🔄 **Alternativas:**
• Contactá a Recursos Humanos: 4212121
• Consultá especialidades disponibles
• Revisá horarios de atención por servicio

🏥 **Hospital Regional Santiago del Estero**"""

        total_prestadores = real_data.get('total_prestadores', 0)
        por_especialidad = real_data.get('por_especialidad', [])
        especialidades_activas = real_data.get('especialidades_activas', 0)

        response = f"""👨‍⚕️ **PRESTADORES DISPONIBLES - HOSPITAL REGIONAL**

📊 **Resumen General:**
• **Total de prestadores:** {total_prestadores}
• **Especialidades activas:** {especialidades_activas}
• **Promedio por especialidad:** {total_prestadores / especialidades_activas:.1f} profesionales

🏥 **Top Especialidades por Cantidad de Prestadores:**"""

        if por_especialidad:
            for i, esp in enumerate(por_especialidad[:8], 1):
                response += f"""
{i:2}. **{esp['nombre']}:** {esp['cantidad']} profesionales"""

            if len(por_especialidad) > 8:
                response += f"\n    ... y {len(por_especialidad) - 8} especialidades más"

        response += f"""

📞 **Para consultas específicas:**
• Admisión: 4212121
• Guardia: 22323 (int. 911)
• Turnos: Consultar por especialidad

✅ **Actualizado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏥 **Hospital Regional Santiago del Estero**

*Total de profesionales activos en el hospital*"""

        return response

    async def _get_system_help(self) -> Dict[str, Any]:
        """Generar información de capacidades del sistema"""
        return {
            'encontrado': True,
            'tipo': 'ayuda_sistema',
            'capacidades': [
                'Búsqueda de pacientes por DNI',
                'Consulta de historias clínicas',
                'Estado de camas disponibles',
                'Información de especialidades médicas',
                'Consulta de turnos programados',
                'Horarios de atención',
                'Estado de emergencias',
                'Información de prestadores',
                'Estadísticas hospitalarias'
            ],
            'ejemplos': [
                'Buscar paciente DNI 12345678',
                '¿Cuántas camas disponibles hay?',
                '¿Qué especialidades tienen?',
                'Turnos para traumatología',
                'Estado de emergencias'
            ]
        }

    async def _format_help_response(
        self, user_message: str, query_info: Dict, real_data: Dict, first_name: str
    ) -> str:
        """Formatear respuesta de ayuda del sistema"""

        capacidades = real_data.get('capacidades', [])
        ejemplos = real_data.get('ejemplos', [])

        response = f"""🤖 **ZISBOT - CAPACIDADES DEL SISTEMA**

¡Hola {first_name}! Soy ZisBot del Hospital Regional Santiago del Estero.

🏥 **¿Qué puedo hacer por vos?**

📋 **Consultas disponibles:**"""

        for i, capacidad in enumerate(capacidades, 1):
            response += f"\n{i:2}. {capacidad}"

        response += f"""

💡 **Ejemplos de consultas:**"""

        for ejemplo in ejemplos:
            response += f"\n   • \"{ejemplo}\""

        response += f"""

📞 **Contactos útiles:**
• Mesa de Ayuda: 4212121
• Guardia/Emergencias: 22323 (int. 911)

✅ **Datos en tiempo real** del Hospital Regional
🔒 **Acceso seguro** con permisos por rol

¿En qué te puedo ayudar hoy?"""

        return response

    def _format_context_for_langgraph(
        self, history: List[Dict], hospital_id: str, current_message: str
    ) -> str:
        """Formatear contexto para LangGraph"""

        context_parts = [f"Hospital ID: {hospital_id}"]
        context_parts.append(f"Consulta actual: {current_message}")

        if history:
            context_parts.append("Historial reciente:")
            recent = history[-4:] if len(history) > 4 else history
            for msg in recent:
                msg_type = msg.get('type', 'unknown')
                content = msg.get('message', '')[:80]
                context_parts.append(f"{msg_type}: {content}...")

        return "\n".join(context_parts)

    def _save_to_memory(
        self, conversation_id: str, user_message: str, bot_response: str,
        intent: str, confidence: float, hospital_id: str
    ):
        """Guardar interacción en memoria Redis tradicional"""
        history = self._get_conversation_history(conversation_id)
        timestamp = datetime.now().isoformat()

        # Agregar nueva interacción
        history.append({
            "type": "user_message",
            "message": user_message,
            "timestamp": timestamp,
            "intent": intent,
            "confidence": confidence
        })

        history.append({
            "type": "bot_response",
            "message": bot_response,
            "timestamp": timestamp,
            "intent": intent
        })

        # Mantener solo los últimos mensajes
        if len(history) > self.max_memory_messages:
            history = history[-self.max_memory_messages:]

        # Guardar
        self._save_conversation_history(conversation_id, history)
        logger.info(f"💾 Memoria actualizada: {conversation_id} - {intent}")

    def _save_to_memory_fallback(
        self, conversation_id: str, user_message: str, bot_response: str,
        intent: str, confidence: float, hospital_id: str
    ):
        """Fallback a memoria Redis tradicional si falla la híbrida"""
        history = self._get_conversation_history(conversation_id)
        timestamp = datetime.now().isoformat()

        # Agregar nuevos mensajes
        history.extend([
            {
                'type': 'user',
                'message': user_message,
                'timestamp': timestamp,
                'intent': intent
            },
            {
                'type': 'bot',
                'message': bot_response,
                'timestamp': timestamp,
                'confidence': confidence,
                'hospital_id': hospital_id
            }
        ])

        # Mantener solo mensajes recientes
        if len(history) > self.max_memory_messages * 2:
            history = history[-self.max_memory_messages * 2:]

        # Guardar en Redis
        self._save_conversation_history(conversation_id, history)

        logger.info(f"🧠 Memoria fallback actualizada: {conversation_id} - {len(history)} mensajes")

    async def _intelligent_fallback(
        self, user_message: str, hospital_id: str, first_name: str
    ) -> tuple:
        """Fallback inteligente para consultas generales usando ORM directo"""
        try:
            message_lower = user_message.lower()

            # Detectar consultas sobre especialidades
            if any(word in message_lower for word in ['especialidad', 'especialidades']):
                logger.info("🎯 Fallback detectó consulta de especialidades")
                result = await orm_hospital_service.obtener_especialidades_con_prestadores(int(hospital_id))

                if result.success and result.data:
                    count = len(result.data)
                    response = f"""🏥 **ESPECIALIDADES DISPONIBLES**

📋 **Tenemos {count} especialidades médicas:**

"""
                    for i, esp in enumerate(result.data[:10], 1):
                        nombre = esp.get('nombre', 'Sin nombre').strip()
                        cantidad = esp.get('cantidad_prestadores', 0)
                        response += f"• **{nombre}** - {cantidad} prestadores\n"

                    response += f"""
✅ **Información actualizada**
📞 **Consultas:** 4212121"""

                    return response, 0.9, "SPECIALTIES_INFO"

            # Detectar consultas sobre camas
            elif any(word in message_lower for word in ['cama', 'camas', 'disponible']):
                logger.info("🛏️ Fallback detectó consulta de camas")
                result = await orm_hospital_service.obtener_disponibilidad_camas(int(hospital_id))

                if result.success and result.data:
                    data = result.data
                    resumen = data.get('resumen', {})

                    response = f"""🛏️ **ESTADO DE CAMAS**

📊 **Disponibilidad:**
• **Total:** {resumen.get('total_camas', 0)} camas
• **Disponibles:** {resumen.get('disponibles', 0)} camas
• **Ocupadas:** {resumen.get('ocupadas', 0)} camas
• **Ocupación:** {resumen.get('porcentaje_ocupacion', 0)}%

✅ **Estado en tiempo real**
📞 **Admisión:** 4212121"""

                    return response, 0.9, "BEDS_STATUS"

            # Respuesta general con IA
            logger.info("🤖 Generando respuesta general con IA")

            prompt = f"""Eres ZisBot, asistente virtual del Hospital Regional Santiago del Estero.

CONSULTA DEL USUARIO: "{user_message}"

INSTRUCCIONES PARA RESPONDER:
1. Sé cálido y natural, como una persona real que trabaja en el hospital
2. Si es un saludo, responde de forma amigable sin ser demasiado formal o robótica
3. Menciona que estás acá para ayudar con consultas sobre el hospital
4. Si preguntan cómo estás, podés decir que estás bien y lista para ayudar
5. Mantené un tono conversacional argentino, podés usar "che", "te ayudo", etc.
6. Mencioná que podés ayudar con: información de pacientes, camas disponibles, especialidades, turnos
7. Solo incluí teléfonos si es relevante: 4212121 (admisión) y 22323 (guardia)
8. Evitá frases como "funcionando dentro de parámetros" o "conectada a la red"

Genera una respuesta útil y profesional."""

            ai_response = await self.llm.ainvoke(prompt)
            response = ai_response.content.strip()

            return response, 0.8, "AI_GENERAL_RESPONSE"

        except Exception as e:
            logger.error(f"❌ Error en fallback: {e}")
            return f"Hola {first_name}, tengo problemas técnicos. Llama al 4212121.", 0.1, "error"

    def get_workflow_info(self) -> Dict[str, Any]:
        """Obtener información del workflow de LangGraph"""
        try:
            return {
                "workflow_available": self.workflow is not None,
                "groq_model": "llama-3.1-8b-instant",
                "redis_connected": self.redis is not None,
                "hospital_data_service": self.hospital_data_service is not None,
                "status": "functional"
            }
        except Exception as e:
            return {
                "workflow_available": False,
                "error": str(e),
                "status": "error"
            }

    async def test_workflow(self, test_message: str = "test") -> Dict[str, Any]:
        """Probar el workflow de LangGraph con un mensaje de prueba"""
        try:
            if not self.llm:
                return {
                    "success": False,
                    "error": "LLM not available - API key required",
                    "status": "error"
                }

            # Probar conexión básica del LLM
            test_response = await self.llm.ainvoke("Hello, respond with 'OK' if working")

            return {
                "success": True,
                "test_message": test_message,
                "llm_response": str(test_response.content)[:100] if hasattr(test_response, 'content') else str(test_response)[:100],
                "groq_model": "llama-3.1-8b-instant",
                "status": "functional"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "error"
            }

    async def _get_debug_camas_info(self) -> Dict[str, Any]:
        """Obtener información completa de camas desde el endpoint debug"""
        try:
            import requests
            # Hacer request al endpoint debug local
            response = requests.get("http://localhost:8008/debug/camas-debug", timeout=5)
            if response.status_code == 200:
                data = response.json().get('data', {})
                return {
                    'total_hospital': data.get('camas_basico_inst_3', 112),
                    'habilitadas': data.get('por_habilitacion', {}).get('Habilitada', 'N/A'),
                    'no_habilitadas': data.get('por_habilitacion', {}).get('No Habilitada', 'N/A'),
                    'mantenimiento': data.get('por_mantenimiento', {}).get('En Mantenimiento', 'N/A'),
                    'planta_baja': next((sector[1] for sector in data.get('sectores_grandes', []) if sector[0] == 'Planta baja'), 43),
                    'administracion': next((sector[1] for sector in data.get('sectores_grandes', []) if sector[0] == 'Administracion'), 'N/A')
                }
        except Exception as e:
            logger.error(f"Error obteniendo debug camas: {e}")

        # Valores por defecto si falla la consulta
        return {
            'total_hospital': 112,
            'habilitadas': 15,
            'no_habilitadas': 97,
            'mantenimiento': 6,
            'planta_baja': 43,
            'administracion': 69
        }


# ===============================================
# INSTANCIA GLOBAL Y FUNCIONES
# ===============================================

chatbot_service: Optional[ChatbotService] = None

async def init_chatbot_service(groq_api_key: str, redis_url: str = "redis://localhost:6379"):
    """Inicializar servicio de chatbot"""
    global chatbot_service
    chatbot_service = ChatbotService(groq_api_key, redis_url)
    logger.info("🚀 ChatbotService inicializado globalmente")

async def get_chatbot_service() -> ChatbotService:
    """Obtener instancia del servicio de chatbot"""
    if chatbot_service is None:
        raise ValueError("ChatbotService no inicializado")
    return chatbot_service