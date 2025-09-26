"""
Agente LangChain con IA real (Groq + Llama) integrado con métodos contextuales
Combina inteligencia artificial avanzada con datos reales de ZisMed
ACTUALIZADO: Ahora usa LangGraph para flujos complejos
"""
import logging
import os
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ✅ LangChain activado - dependencias instaladas (con fallback)
try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ LangChain no disponible: {e}")
    ChatGroq = None
    ChatPromptTemplate = None
    HumanMessage = None
    SystemMessage = None
    LANGCHAIN_AVAILABLE = False

from app.integrations.simple_agent import simple_agent
from app.integrations.working_langgraph_agent import working_langgraph_agent
from app.config.settings import settings

logger = logging.getLogger(__name__)


class HospitalLangChainAgent:
    """Agente LangChain con IA real que usa métodos contextuales de ZisMed"""

    def __init__(self):
        # Intentar múltiples fuentes para la API key
        self.groq_api_key = (
            os.getenv("GROQ_API_KEY") or
            os.getenv("GROQ_API") or
            self._load_from_env_file()
        )

        # ✅ LangChain activado con LangGraph
        if LANGCHAIN_AVAILABLE and self.groq_api_key and self.groq_api_key != "gsk_placeholder_key_for_testing_purposes_only":
            try:
                self.llm = ChatGroq(
                    api_key=self.groq_api_key,
                    model_name="llama-3.1-8b-instant",
                    temperature=0.1,
                    max_tokens=1000
                )
                logger.info("✅ LangChain + Groq ACTIVADO con IA real")
                self.ai_enabled = True
            except Exception as e:
                logger.error(f"❌ Error inicializando Groq: {e}")
                self.llm = None
                self.ai_enabled = False
        else:
            self.llm = None
            self.ai_enabled = False
            if not LANGCHAIN_AVAILABLE:
                logger.warning("⚠️ LangChain no disponible, usando SimpleAgent como fallback")
            else:
                logger.warning("⚠️ GROQ_API_KEY no encontrada o es placeholder, usando SimpleAgent como fallback")

    def _load_from_env_file(self):
        """Cargar API key desde archivo .env"""
        try:
            env_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('GROQ_API_KEY='):
                            return line.split('=', 1)[1].strip()
        except Exception as e:
            logger.debug(f"Error leyendo .env: {e}")
        return None

    def _build_system_prompt(self, user_context: Dict[str, Any]) -> str:
        """Construir prompt del sistema adaptado al contexto del usuario"""
        institution = user_context.get('institution', 'Hospital')
        hospital_id = user_context.get('hospital_id', '3')
        user_name = user_context.get('user_name', 'Usuario')

        return f"""Eres ZisBot, el asistente médico virtual inteligente de {institution}.

🏥 CONTEXTO ACTUAL:
- Institución: {institution} (ID: {hospital_id})
- Usuario: {user_name}
- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🎯 CAPACIDADES CONTEXTUALES:
Tienes acceso directo a datos REALES de ZisMed para:
• Buscar pacientes por DNI (datos reales filtrados por {institution})
• Consultar especialidades médicas (filtradas por {institution})
• Obtener información de servicios hospitalarios

📋 INSTRUCCIONES INTELIGENTES:
1. Si detectas un DNI (7-8 dígitos), automaticamente busca el paciente
2. Si preguntan por especialidades, muestra las de {institution}
3. Usa lenguaje médico profesional pero comprensible
4. Siempre menciona que los datos son reales de ZisMed
5. Adapta las respuestas al contexto específico de {institution}

🚨 EMERGENCIAS: Si detectas síntomas urgentes, prioriza la derivación inmediata

Responde siempre en español argentino, siendo empático pero profesional."""

    async def process_message(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar mensaje con IA real y métodos contextuales"""
        start_time = datetime.now()

        try:
            institution = user_context.get('institution', 'Hospital')
            logger.info(f"🤖 IA REAL procesando: '{message[:50]}...' para {institution}")

            # 🚀 NUEVO: Usar Working LangGraph para consultas complejas o LLM simple para conversación
            if self.llm and any(keyword in message.lower() for keyword in ['dni', 'paciente', 'buscar', 'especialidad', 'medico']):
                logger.info("🧠 Usando Working LangGraph para consulta compleja")
                return await working_langgraph_agent.process_message(message, user_context)

            elif self.llm and LANGCHAIN_AVAILABLE:
                logger.info("🤖 Usando IA simple para conversación general")
                # Usar IA directa para conversación general
                system_prompt = self._build_system_prompt(user_context)

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message)
                ]

                response = await self.llm.ainvoke(messages)
                ai_response = response.content

                # Añadir signature de IA real
                ai_response += f"\n\n🤖 *Respuesta generada por IA (Groq + Llama) para {institution}*"

                return {
                    "response": ai_response,
                    "type": "ai_conversational",
                    "confidence": 0.95,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "function_used": "langchain_conversational",
                    "metadata": {
                        "ai_model": "groq_llama_3.1",
                        "institution": institution,
                        "context_data_used": False
                    }
                }
            else:
                logger.info("🔄 Fallback a SimpleAgent (sin API key)")
                return await simple_agent.process_message(message, user_context)


        except Exception as e:
            logger.error(f"❌ Error en IA real: {e}")
            # Fallback automático al simple_agent
            logger.info("🔄 Fallback automático a SimpleAgent")
            result = await simple_agent.process_message(message, user_context)
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["fallback_reason"] = str(e)
            return result


# Instancia global
langchain_agent = HospitalLangChainAgent()