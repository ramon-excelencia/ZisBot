"""
Herramientas LangChain personalizadas para servicios hospitalarios
Estas tools consumen los endpoints REST que creamos (no SQL directo)
"""
from typing import Type, Optional, Dict, Any
import asyncio
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

from app.services.orm_hospital_service import orm_hospital_service as hospital_service


class BuscarPacientePorDNIInput(BaseModel):
    """Input para buscar paciente por DNI"""
    dni: str = Field(description="DNI del paciente (7-8 dígitos)")


class BuscarPacientePorDNITool(BaseTool):
    """Herramienta para buscar paciente por DNI usando endpoint REST"""

    name: str = "buscar_paciente_dni"
    description: str = """
    Busca información de un paciente específico por su DNI.
    Devuelve datos completos del paciente incluyendo nombre, obra social, teléfono.
    Usar cuando el usuario pregunta por un DNI específico.
    """
    args_schema: Type[BaseModel] = BuscarPacientePorDNIInput

    def _run(
        self,
        dni: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar búsqueda de paciente por DNI"""
        try:
            # ✅ Usa endpoint REST (no SQL directo) - ejecuta async en sync
            result = asyncio.run(hospital_service.buscar_paciente_por_dni(dni))

            if result.success and result.data:
                patient = result.data
                return f"""
Paciente encontrado:
- Nombre: {patient.get('nombre', '')} {patient.get('apellido', '')}
- DNI: {patient.get('documento', '')}
- Teléfono: {patient.get('telefono', 'No registrado')}
- Obra Social: {patient.get('obra_social', 'Sin obra social')}
- Número OS: {patient.get('obra_social_numero', 'N/A')}
"""
            else:
                return f"No se encontró ningún paciente con DNI {dni}"

        except Exception as e:
            return f"Error buscando paciente: {str(e)}"


class BuscarPacientesPorNombreInput(BaseModel):
    """Input para buscar pacientes por nombre"""
    nombre: str = Field(description="Nombre o apellido a buscar")


class BuscarPacientesPorNombreTool(BaseTool):
    """Herramienta para buscar pacientes por nombre usando endpoint REST"""

    name: str = "buscar_pacientes_nombre"
    description: str = """
    Busca pacientes por nombre o apellido (búsqueda parcial).
    Devuelve lista de pacientes que coinciden con el nombre.
    Usar cuando el usuario busca por nombre sin DNI específico.
    """
    args_schema: Type[BaseModel] = BuscarPacientesPorNombreInput

    def _run(
        self,
        nombre: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar búsqueda de pacientes por nombre"""
        try:
            # ✅ Usa endpoint REST (no SQL directo) - ejecuta async en sync
            result = asyncio.run(hospital_service.buscar_pacientes_por_nombre(nombre))

            if result.success and result.data:
                pacientes = result.data
                output = f"Encontrados {len(pacientes)} pacientes con nombre '{nombre}':\n\n"

                for i, patient in enumerate(pacientes[:5], 1):  # Máximo 5
                    output += f"{i}. {patient.get('apellido', '')}, {patient.get('nombre', '')} "
                    output += f"(DNI: {patient.get('documento', '')}) "
                    output += f"- {patient.get('obra_social', 'Sin OS')}\n"

                if len(pacientes) > 5:
                    output += f"\n... y {len(pacientes) - 5} más"

                return output
            else:
                return f"No se encontraron pacientes con nombre '{nombre}'"

        except Exception as e:
            return f"Error buscando pacientes: {str(e)}"


class ObtenerEspecialidadesInput(BaseModel):
    """Input para obtener especialidades (no requiere parámetros)"""
    pass


class ObtenerEspecialidadesTool(BaseTool):
    """Herramienta para obtener especialidades médicas usando endpoint REST"""

    name: str = "obtener_especialidades"
    description: str = """
    Obtiene todas las especialidades médicas disponibles en el hospital.
    Devuelve lista completa de especialidades con cantidad de médicos.
    Usar cuando pregunten qué especialidades hay disponibles.
    """
    args_schema: Type[BaseModel] = ObtenerEspecialidadesInput

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar obtención de especialidades"""
        try:
            # ✅ Usa endpoint REST (no SQL directo) - ejecuta async en sync
            result = asyncio.run(hospital_service.obtener_especialidades())

            if result.success and result.data:
                especialidades = result.data
                output = f"Especialidades disponibles ({len(especialidades)} total):\n\n"

                for esp in especialidades[:15]:  # Máximo 15
                    nombre = esp.get('nombre', '')
                    cantidad = esp.get('cantidad_medicos', 0)
                    output += f"• {nombre} ({cantidad} médicos)\n"

                if len(especialidades) > 15:
                    output += f"\n... y {len(especialidades) - 15} especialidades más"

                return output
            else:
                return "No se pudieron obtener las especialidades"

        except Exception as e:
            return f"Error obteniendo especialidades: {str(e)}"


class AnalisisVulnerabilidadSocialInput(BaseModel):
    """Input para análisis de vulnerabilidad social (no requiere parámetros)"""
    pass


class AnalisisVulnerabilidadSocialTool(BaseTool):
    """Herramienta para análisis de vulnerabilidad social usando endpoint REST"""

    name: str = "analisis_vulnerabilidad_social"
    description: str = """
    Realiza análisis de vulnerabilidad social de pacientes sin obra social.
    Devuelve estadísticas de pacientes sin cobertura médica.
    Usar cuando pregunten sobre pacientes sin obra social o vulnerabilidad.
    """
    args_schema: Type[BaseModel] = AnalisisVulnerabilidadSocialInput

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar análisis de vulnerabilidad social"""
        try:
            # ✅ Usa endpoint REST (no SQL directo) - ejecuta async en sync
            result = asyncio.run(hospital_service.analizar_vulnerabilidad_social())

            if result.success and result.data:
                stats = result.data

                sin_obra_social = next((item for item in stats if "Sin Obra Social" in item.get("categoria", "")), {})
                total_pacientes = next((item for item in stats if "Total Pacientes" in item.get("categoria", "")), {})

                if sin_obra_social and total_pacientes:
                    cantidad = sin_obra_social.get("total", 0)
                    porcentaje = sin_obra_social.get("porcentaje", 0)
                    total = total_pacientes.get("total", 0)

                    return f"""
Análisis de Vulnerabilidad Social:

📊 Pacientes sin obra social: {cantidad:,} ({porcentaje}%)
📈 Total pacientes activos: {total:,}
🚨 Nivel de vulnerabilidad: {porcentaje}%

Este grupo requiere atención prioritaria para programas de asistencia social.
"""
                else:
                    return "No se pudieron procesar las estadísticas de vulnerabilidad"
            else:
                return "No se pudo realizar el análisis de vulnerabilidad social"

        except Exception as e:
            return f"Error en análisis de vulnerabilidad: {str(e)}"


class ObtenerServiciosHospitalariosInput(BaseModel):
    """Input para obtener servicios hospitalarios (no requiere parámetros)"""
    pass


class ObtenerServiciosHospitalariosTool(BaseTool):
    """Herramienta para obtener servicios hospitalarios usando endpoint REST"""

    name: str = "obtener_servicios_hospitalarios"
    description: str = """
    Obtiene todos los servicios hospitalarios disponibles.
    Devuelve lista completa de servicios con ubicaciones.
    Usar cuando pregunten qué servicios ofrece el hospital.
    """
    args_schema: Type[BaseModel] = ObtenerServiciosHospitalariosInput

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Ejecutar obtención de servicios hospitalarios"""
        try:
            # ✅ Usa endpoint REST (no SQL directo) - ejecuta async en sync
            result = asyncio.run(hospital_service.obtener_servicios_hospitalarios())

            if result.success and result.data:
                servicios = result.data
                output = f"Servicios Hospitalarios ({len(servicios)} total):\n\n"

                for servicio in servicios[:20]:  # Máximo 20
                    nombre = servicio.get('nombre', '')
                    ubicacion = servicio.get('ubicacion', '')
                    ubicacion_text = f" - {ubicacion}" if ubicacion else ""
                    output += f"• {nombre}{ubicacion_text}\n"

                if len(servicios) > 20:
                    output += f"\n... y {len(servicios) - 20} servicios más"

                return output
            else:
                return "No se pudieron obtener los servicios hospitalarios"

        except Exception as e:
            return f"Error obteniendo servicios: {str(e)}"


# Lista de todas las herramientas disponibles
HOSPITAL_TOOLS = [
    BuscarPacientePorDNITool(),
    BuscarPacientesPorNombreTool(),
    ObtenerEspecialidadesTool(),
    AnalisisVulnerabilidadSocialTool(),
    ObtenerServiciosHospitalariosTool()
]