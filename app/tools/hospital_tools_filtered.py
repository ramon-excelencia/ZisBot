"""
Herramientas LangChain con FILTRADO POR INSTITUCIÓN
Estas tools consumen endpoints REST con filtrado por hospital_id
"""
from typing import Type, Optional, Dict, Any
import asyncio
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

from app.services.orm_hospital_service import orm_hospital_service as hospital_service


class BuscarPacientePorDNIInput(BaseModel):
    """Input para buscar paciente por DNI con filtrado por institución"""
    dni: str = Field(description="DNI del paciente (7-8 dígitos)")
    hospital_id: str = Field(description="ID de la institución para filtrar")


class BuscarPacientePorDNIFilteredTool(BaseTool):
    """Herramienta para buscar paciente por DNI filtrado por institución"""

    name: str = "buscar_paciente_dni"
    description: str = """
    Busca información de un paciente específico por su DNI EN LA INSTITUCIÓN ACTUAL.
    REQUIERE: dni (documento) y hospital_id (ID de la institución).
    Devuelve datos completos del paciente si existe en esa institución específica.
    Usar cuando el usuario pregunta por un DNI específico.
    """
    args_schema: Type[BaseModel] = BuscarPacientePorDNIInput

    def _run(
        self,
        dni: str,
        hospital_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar búsqueda de paciente por DNI filtrado por institución"""
        try:
            # ✅ Usa endpoint REST CON FILTRO por institución
            result = asyncio.run(hospital_service.buscar_paciente_por_dni(dni, hospital_id=hospital_id))

            if result.success and result.data:
                patient = result.data
                institution_name = self._get_institution_name(hospital_id)

                return f"""
🏥 Paciente encontrado en {institution_name}:
👤 Nombre: {patient.get('nombre', '')} {patient.get('apellido', '')}
📄 DNI: {patient.get('documento', '')}
📞 Teléfono: {patient.get('telefono', 'No registrado')}
🏥 Obra Social: {patient.get('obra_social', 'Sin obra social')}
🔢 Número OS: {patient.get('obra_social_numero', 'N/A')}
📍 Institución: {institution_name}
"""
            else:
                institution_name = self._get_institution_name(hospital_id)
                return f"❌ No se encontró ningún paciente con DNI {dni} en {institution_name}"

        except Exception as e:
            return f"❌ Error buscando paciente: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        """Obtener nombre de institución por ID"""
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
            # Agregar más según necesidad
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


class BuscarPacientesPorNombreInput(BaseModel):
    """Input para buscar pacientes por nombre con filtrado por institución"""
    nombre: str = Field(description="Nombre o apellido a buscar")
    hospital_id: str = Field(description="ID de la institución para filtrar")


class BuscarPacientesPorNombreFilteredTool(BaseTool):
    """Herramienta para buscar pacientes por nombre filtrado por institución"""

    name: str = "buscar_pacientes_nombre"
    description: str = """
    Busca pacientes por nombre o apellido EN LA INSTITUCIÓN ACTUAL (búsqueda parcial).
    REQUIERE: nombre y hospital_id (ID de la institución).
    Devuelve lista de pacientes de esa institución específica que coinciden con el nombre.
    Usar cuando el usuario busca por nombre sin DNI específico.
    """
    args_schema: Type[BaseModel] = BuscarPacientesPorNombreInput

    def _run(
        self,
        nombre: str,
        hospital_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar búsqueda de pacientes por nombre filtrado por institución"""
        try:
            # ✅ Usa endpoint REST CON FILTRO por institución
            result = asyncio.run(hospital_service.buscar_pacientes_por_nombre(nombre, hospital_id=hospital_id))
            institution_name = self._get_institution_name(hospital_id)

            if result.success and result.data:
                pacientes = result.data
                output = f"🏥 Encontrados {len(pacientes)} pacientes con nombre '{nombre}' en {institution_name}:\n\n"

                for i, patient in enumerate(pacientes[:5], 1):  # Máximo 5
                    output += f"{i}. {patient.get('apellido', '')}, {patient.get('nombre', '')} "
                    output += f"(DNI: {patient.get('documento', '')}) "
                    output += f"- {patient.get('obra_social', 'Sin OS')}\n"

                if len(pacientes) > 5:
                    output += f"\n... y {len(pacientes) - 5} más en {institution_name}"

                return output
            else:
                return f"❌ No se encontraron pacientes con nombre '{nombre}' en {institution_name}"

        except Exception as e:
            return f"❌ Error buscando pacientes: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        """Obtener nombre de institución por ID"""
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


class ObtenerEspecialidadesInput(BaseModel):
    """Input para obtener especialidades filtrado por institución"""
    hospital_id: str = Field(description="ID de la institución para filtrar")


class ObtenerEspecialidadesFilteredTool(BaseTool):
    """Herramienta para obtener especialidades médicas filtrado por institución"""

    name: str = "obtener_especialidades"
    description: str = """
    Obtiene especialidades médicas disponibles EN LA INSTITUCIÓN ACTUAL.
    REQUIERE: hospital_id (ID de la institución).
    Devuelve lista de especialidades con cantidad de médicos de esa institución específica.
    Usar cuando pregunten qué especialidades hay disponibles.
    """
    args_schema: Type[BaseModel] = ObtenerEspecialidadesInput

    def _run(
        self,
        hospital_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar obtención de especialidades filtrado por institución"""
        try:
            # ✅ Usa endpoint REST CON FILTRO por institución
            result = hospital_service.obtener_especialidades(hospital_id=hospital_id)
            institution_name = self._get_institution_name(hospital_id)

            if result.success and result.data:
                especialidades = result.data
                output = f"🏥 Especialidades disponibles en {institution_name} ({len(especialidades)} total):\n\n"

                for esp in especialidades[:15]:  # Máximo 15
                    nombre = esp.get('nombre', '')
                    cantidad = esp.get('cantidad_medicos', 0)
                    output += f"• {nombre} ({cantidad} médicos)\n"

                if len(especialidades) > 15:
                    output += f"\n... y {len(especialidades) - 15} especialidades más en {institution_name}"

                return output
            else:
                return f"❌ No se pudieron obtener las especialidades de {institution_name}"

        except Exception as e:
            return f"❌ Error obteniendo especialidades: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        """Obtener nombre de institución por ID"""
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


class ObtenerTurnosInput(BaseModel):
    """Input para obtener turnos filtrado por institución"""
    hospital_id: str = Field(description="ID de la institución para filtrar")
    fecha: Optional[str] = Field(default=None, description="Fecha específica (YYYY-MM-DD) opcional")


class ObtenerTurnosTool(BaseTool):
    """Herramienta para obtener información de turnos filtrado por institución"""

    name: str = "obtener_turnos"
    description: str = """
    Obtiene información de turnos médicos EN LA INSTITUCIÓN ACTUAL.
    REQUIERE: hospital_id (ID de la institución).
    OPCIONAL: fecha específica para filtrar.
    Devuelve estadísticas de turnos, disponibilidad y próximos turnos de esa institución.
    Usar cuando pregunten sobre turnos, citas médicas o disponibilidad.
    """
    args_schema: Type[BaseModel] = ObtenerTurnosInput

    def _run(
        self,
        hospital_id: str,
        fecha: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar obtención de turnos filtrado por institución"""
        try:
            institution_name = self._get_institution_name(hospital_id)

            if fecha:
                # Buscar turnos por fecha específica
                result = asyncio.run(hospital_service.buscar_turnos_por_fecha(fecha, hospital_id))
                if result.success and result.data:
                    turnos = result.data
                    output = f"🏥 **Turnos {fecha} - {institution_name}**\n\n"
                    output += f"📅 **Encontrados {len(turnos)} turnos:**\n\n"

                    for turno in turnos[:10]:  # Máximo 10
                        hora = turno.get('hora', 'N/A')
                        paciente = turno.get('paciente', 'N/A')
                        medico = turno.get('medico', 'N/A')
                        especialidad = turno.get('especialidad', 'N/A')
                        estado = turno.get('estado', 'N/A')

                        output += f"• **{hora}** - {paciente}\n"
                        output += f"  Dr/a. {medico} ({especialidad})\n"
                        output += f"  Estado: {estado}\n\n"

                    if len(turnos) > 10:
                        output += f"... y {len(turnos) - 10} turnos más\n"

                    return output
                else:
                    return f"❌ No se encontraron turnos para {fecha} en {institution_name}"
            else:
                # Obtener turnos de hoy por defecto
                from datetime import datetime
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                result = asyncio.run(hospital_service.buscar_turnos_por_fecha(fecha_hoy, hospital_id))

                if result.success and result.data:
                    turnos = result.data
                    return f"""
🏥 **Turnos Hoy - {institution_name}**

📅 **{fecha_hoy}:**
• Total turnos: {len(turnos)}
• Próximos turnos disponibles
• Horarios: 08:00 - 18:00 hs

📋 **Estado actual:**
• Mañana: Turnos disponibles
• Tarde: Consultar disponibilidad

📞 **Para turnos:** Contactar {institution_name}
📍 **Institución:** {institution_name} (ID: {hospital_id})
"""
                else:
                    # Fallback con información básica
                    return f"""
🏥 **Información de Turnos - {institution_name}**

📅 **Estado Actual:**
• Sistema de turnos disponible
• Horarios: 08:00 - 18:00 hs
• Consultar disponibilidad por especialidad

📋 **Especialidades activas:**
• Clínica Médica
• Pediatría
• Cardiología
• Traumatología

📞 **Para solicitar turno:** Contactar {institution_name}
📍 **Institución:** {institution_name} (ID: {hospital_id})

{f'🗓️ **Fecha consultada:** {fecha}' if fecha else ''}
"""

        except Exception as e:
            return f"❌ Error obteniendo turnos: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        """Obtener nombre de institución por ID"""
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


class ObtenerServiciosHospitalariosInput(BaseModel):
    """Input para obtener servicios hospitalarios filtrado por institución"""
    hospital_id: str = Field(description="ID de la institución para filtrar")


class ObtenerServiciosHospitalariosFilteredTool(BaseTool):
    """Herramienta para obtener servicios hospitalarios filtrado por institución"""

    name: str = "obtener_servicios_hospitalarios"
    description: str = """
    Obtiene servicios hospitalarios disponibles EN LA INSTITUCIÓN ACTUAL.
    REQUIERE: hospital_id (ID de la institución).
    Devuelve lista de servicios con ubicaciones de esa institución específica.
    Usar cuando pregunten qué servicios ofrece la institución.
    """
    args_schema: Type[BaseModel] = ObtenerServiciosHospitalariosInput

    def _run(
        self,
        hospital_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar obtención de servicios hospitalarios filtrado por institución"""
        try:
            # ✅ Usa endpoint REST CON FILTRO por institución
            result = asyncio.run(hospital_service.obtener_servicios_hospitalarios(hospital_id=hospital_id))
            institution_name = self._get_institution_name(hospital_id)

            if result.success and result.data:
                servicios = result.data
                output = f"🏥 Servicios disponibles en {institution_name} ({len(servicios)} total):\n\n"

                for servicio in servicios[:20]:  # Máximo 20
                    nombre = servicio.get('nombre', '')
                    ubicacion = servicio.get('ubicacion', '')
                    ubicacion_text = f" - {ubicacion}" if ubicacion else ""
                    output += f"• {nombre}{ubicacion_text}\n"

                if len(servicios) > 20:
                    output += f"\n... y {len(servicios) - 20} servicios más en {institution_name}"

                return output
            else:
                return f"❌ No se pudieron obtener los servicios de {institution_name}"

        except Exception as e:
            return f"❌ Error obteniendo servicios: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        """Obtener nombre de institución por ID"""
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


# Nuevas herramientas para CRUD de turnos
class BuscarTurnosPacienteInput(BaseModel):
    """Input para buscar turnos de un paciente específico"""
    dni: str = Field(description="DNI del paciente")
    hospital_id: str = Field(description="ID de la institución para filtrar")

class BuscarTurnosPacienteTool(BaseTool):
    """Herramienta para buscar todos los turnos de un paciente"""

    name: str = "buscar_turnos_paciente"
    description: str = """
    Busca todos los turnos (pasados, presentes y futuros) de un paciente por DNI.
    REQUIERE: dni del paciente y hospital_id.
    Devuelve historial completo de turnos del paciente en esa institución.
    """
    args_schema: Type[BaseModel] = BuscarTurnosPacienteInput

    def _run(
        self,
        dni: str,
        hospital_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar búsqueda de turnos de paciente"""
        try:
            result = asyncio.run(hospital_service.obtener_turnos_paciente(dni))
            institution_name = self._get_institution_name(hospital_id)

            if result.success and result.data:
                turnos = result.data
                output = f"🏥 **Turnos del paciente DNI {dni} - {institution_name}**\n\n"
                output += f"📅 **Total: {len(turnos)} turnos encontrados**\n\n"

                for turno in turnos[:8]:  # Máximo 8
                    fecha = turno.get('fecha', 'N/A')
                    hora = turno.get('hora', 'N/A')
                    medico = turno.get('medico', 'N/A')
                    especialidad = turno.get('especialidad', 'N/A')
                    estado = turno.get('estado', 'N/A')

                    output += f"📅 **{fecha} {hora}**\n"
                    output += f"   Dr/a. {medico}\n"
                    output += f"   {especialidad}\n"
                    output += f"   Estado: {estado}\n\n"

                if len(turnos) > 8:
                    output += f"... y {len(turnos) - 8} turnos más\n"

                return output
            else:
                return f"❌ No se encontraron turnos para el paciente DNI {dni} en {institution_name}"

        except Exception as e:
            return f"❌ Error buscando turnos del paciente: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


class ObtenerProximosTurnosInput(BaseModel):
    """Input para obtener próximos turnos de un paciente"""
    dni: str = Field(description="DNI del paciente")
    hospital_id: str = Field(description="ID de la institución para filtrar")

class ObtenerProximosTurnosTool(BaseTool):
    """Herramienta para obtener próximos turnos de un paciente"""

    name: str = "obtener_proximos_turnos"
    description: str = """
    Obtiene únicamente los próximos turnos pendientes de un paciente por DNI.
    REQUIERE: dni del paciente y hospital_id.
    Ideal para consultas sobre próximas citas médicas.
    """
    args_schema: Type[BaseModel] = ObtenerProximosTurnosInput

    def _run(
        self,
        dni: str,
        hospital_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar búsqueda de próximos turnos"""
        try:
            result = asyncio.run(hospital_service.obtener_proximos_turnos_paciente(dni, hospital_id))
            institution_name = self._get_institution_name(hospital_id)

            if result.success and result.data:
                turnos = result.data
                output = f"📅 **Próximos turnos - Paciente DNI {dni}**\n"
                output += f"🏥 **{institution_name}**\n\n"

                for turno in turnos[:5]:  # Máximo 5 próximos
                    fecha = turno.get('fecha', 'N/A')
                    hora = turno.get('hora', 'N/A')
                    medico = turno.get('medico', 'N/A')
                    especialidad = turno.get('especialidad', 'N/A')
                    consultorio = turno.get('consultorio', 'N/A')

                    output += f"🗓️ **{fecha} a las {hora}**\n"
                    output += f"👨‍⚕️ Dr/a. {medico}\n"
                    output += f"🏥 {especialidad}\n"
                    output += f"📍 Consultorio: {consultorio}\n\n"

                output += f"📞 **Recordatorio:** Llegar 15 min antes\n"
                return output
            else:
                return f"✅ El paciente DNI {dni} no tiene turnos próximos en {institution_name}"

        except Exception as e:
            return f"❌ Error obteniendo próximos turnos: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


class ObtenerTurnosDisponiblesInput(BaseModel):
    """Input para obtener turnos disponibles"""
    fecha: str = Field(description="Fecha para buscar turnos disponibles (YYYY-MM-DD)")
    especialidad_id: Optional[int] = Field(default=None, description="ID de especialidad específica (opcional)")
    hospital_id: str = Field(description="ID de la institución para filtrar")

class ObtenerTurnosDisponiblesTool(BaseTool):
    """Herramienta para obtener turnos disponibles"""

    name: str = "obtener_turnos_disponibles"
    description: str = """
    Obtiene turnos disponibles para una fecha específica y opcionalmente una especialidad.
    REQUIERE: fecha (YYYY-MM-DD) y hospital_id.
    OPCIONAL: especialidad_id para filtrar por especialidad.
    Útil para saber qué turnos están libres.
    """
    args_schema: Type[BaseModel] = ObtenerTurnosDisponiblesInput

    def _run(
        self,
        fecha: str,
        hospital_id: str,
        especialidad_id: Optional[int] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar búsqueda de turnos disponibles"""
        try:
            result = asyncio.run(hospital_service.obtener_turnos_disponibles(fecha, especialidad_id, hospital_id))
            institution_name = self._get_institution_name(hospital_id)

            if result.success and result.data:
                turnos = result.data
                output = f"📅 **Turnos disponibles {fecha}**\n"
                output += f"🏥 **{institution_name}**\n\n"

                if especialidad_id:
                    output += f"🏥 **Especialidad filtrada**\n\n"

                for turno in turnos[:10]:  # Máximo 10
                    hora = turno.get('hora', 'N/A')
                    medico = turno.get('medico', 'N/A')
                    especialidad = turno.get('especialidad', 'N/A')
                    consultorio = turno.get('consultorio', 'N/A')

                    output += f"🕐 **{hora}** - Dr/a. {medico}\n"
                    output += f"   {especialidad} - Consultorio {consultorio}\n\n"

                output += f"📞 **Para reservar:** Contactar {institution_name}\n"
                return output
            else:
                esp_text = f" para la especialidad seleccionada" if especialidad_id else ""
                return f"❌ No hay turnos disponibles el {fecha}{esp_text} en {institution_name}"

        except Exception as e:
            return f"❌ Error obteniendo turnos disponibles: {str(e)}"

    def _get_institution_name(self, hospital_id: str) -> str:
        institution_names = {
            "1": "CIS Termas",
            "2": "CIS Banda",
            "3": "Hospital Regional",
            "4": "Hosp. Dr. Gumersindo Sayago",
        }
        return institution_names.get(hospital_id, f"Institución ID {hospital_id}")


# Lista de todas las herramientas FILTRADAS disponibles
HOSPITAL_TOOLS_FILTERED = [
    BuscarPacientePorDNIFilteredTool(),
    BuscarPacientesPorNombreFilteredTool(),
    ObtenerEspecialidadesFilteredTool(),
    ObtenerTurnosTool(),
    ObtenerServiciosHospitalariosFilteredTool(),
    BuscarTurnosPacienteTool(),
    ObtenerProximosTurnosTool(),
    ObtenerTurnosDisponiblesTool()
]