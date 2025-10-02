"""
Hospital Data Service - Consultas reales a la base de datos DBH_TEST
Servicio para las 6 consultas principales usando SQLAlchemy ORM
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text, Date
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DataError
from app.database.connection import db_connection
from app.database.models import (
    Cama, Habitacion, Sector, Internacion, Paciente,
    Turno, Especialidad, Consultorio, Prestador, Servicio
)
from app.services.orm_hospital_service import orm_hospital_service
from app.utils.validators import validate_dni, validate_date

logger = logging.getLogger(__name__)

def handle_sql_error(error: Exception, operation: str) -> Dict[str, Any]:
    """
    Manejo centralizado de errores SQL con mensajes amigables

    Args:
        error: Excepción capturada
        operation: Nombre de la operación (para logs)

    Returns:
        Dict con error amigable y detalles técnicos
    """
    logger.error(f"❌ Error en {operation}: {type(error).__name__} - {str(error)}")

    # Errores de conexión
    if isinstance(error, OperationalError):
        return {
            'error': '🔌 Error de conexión con la base de datos. Intente nuevamente en unos momentos.',
            'error_type': 'connection_error',
            'technical_detail': str(error)
        }

    # Errores de datos/formato
    if isinstance(error, DataError):
        return {
            'error': '❌ Los datos proporcionados son inválidos. Verifique el formato e intente nuevamente.',
            'error_type': 'data_error',
            'technical_detail': str(error)
        }

    # Error genérico de SQLAlchemy
    if isinstance(error, SQLAlchemyError):
        return {
            'error': '⚠️ Error procesando la consulta. Para asistencia: Mesa de Ayuda 4212121',
            'error_type': 'database_error',
            'technical_detail': str(error)
        }

    # Otros errores
    return {
        'error': f'❌ Error inesperado: {str(error)}. Para asistencia: Mesa de Ayuda 4212121',
        'error_type': 'unknown_error',
        'technical_detail': str(error)
    }

class HospitalDataService:
    def __init__(self):
        self.db_connection = db_connection

    def get_session(self) -> Session:
        """Obtener sesión de base de datos"""
        return self.db_connection.get_session()

    # 1. CONSULTA DE CAMAS DISPONIBLES
    async def get_camas_disponibles(self, servicio_nombre: str = None, fecha: str = None) -> Dict[str, Any]:
        """
        Obtener estadísticas completas de camas por servicio/sector/fecha
        Devuelve: total, ocupadas, disponibles, porcentaje de ocupación
        """
        try:
            session = self.get_session()

            # Query base para todas las camas habilitadas
            query_total = session.query(
                Cama.CamaId,
                Cama.Nombre.label('nombre_cama'),
                Habitacion.Nombre.label('habitacion'),
                Sector.Nombre.label('sector')
            ).join(
                Habitacion, Cama.HabitacionID == Habitacion.HabitacionID
            ).join(
                Sector, Habitacion.SectorID == Sector.SectorId
            ).filter(
                and_(
                    Cama.InstitucionID == 3,
                    Cama.Anulado == False,
                    Habitacion.Anulado == False,
                    Sector.Anulado == False
                    # Filtrar solo por InstitucionID de cama para mostrar capacidad completa
                    # Las inconsistencias en habitaciones/sectores no limitan la capacidad
                )
            )

            # Filtrar por servicio si se especifica
            if servicio_nombre:
                query_total = query_total.filter(
                    Sector.Nombre.ilike(f'%{servicio_nombre}%')
                )

            # Obtener total de camas habilitadas
            todas_camas = query_total.all()
            total_camas = len(todas_camas)

            # Query para camas ocupadas (considerar filtro de fecha si se especifica)
            query_ocupadas = session.query(Internacion.CamaID).filter(
                and_(
                    Internacion.Anulado == False,
                    Internacion.Fecha_Alta.is_(None)  # No tienen alta (internaciones vigentes)
                )
            )

            # Si hay filtro por fecha, considerar internaciones en esa fecha específica
            if fecha:
                from datetime import datetime
                try:
                    fecha_consulta = datetime.strptime(fecha, '%Y-%m-%d').date()
                    query_ocupadas = query_ocupadas.filter(
                        Internacion.Fecha_ingreso <= fecha_consulta
                    )
                except ValueError:
                    # Si la fecha no es válida, usar fecha actual
                    pass

            camas_ocupadas_ids = [r[0] for r in query_ocupadas.all()]

            # Calcular estadísticas
            camas_ocupadas_en_servicio = 0
            camas_disponibles = []

            for cama in todas_camas:
                if cama.CamaId in camas_ocupadas_ids:
                    camas_ocupadas_en_servicio += 1
                else:
                    camas_disponibles.append({
                        'cama_id': cama.CamaId,
                        'nombre': cama.nombre_cama,
                        'habitacion': cama.habitacion,
                        'sector': cama.sector
                    })

            total_disponibles = len(camas_disponibles)
            porcentaje_ocupacion = round((camas_ocupadas_en_servicio / total_camas * 100), 2) if total_camas > 0 else 0
            porcentaje_disponibilidad = round((total_disponibles / total_camas * 100), 2) if total_camas > 0 else 0

            result = {
                'total_camas': total_camas,
                'total_ocupadas': camas_ocupadas_en_servicio,
                'total_disponibles': total_disponibles,
                'porcentaje_ocupacion': porcentaje_ocupacion,
                'porcentaje_disponibilidad': porcentaje_disponibilidad,
                'servicio_consultado': servicio_nombre or 'General',
                'fecha_consultada': fecha,
                'camas_disponibles': camas_disponibles,
                'estadisticas_por_sector': {}
            }

            # Agregar estadísticas por sector si no se filtró por uno específico
            if not servicio_nombre:
                sectores_stats = {}
                for cama in todas_camas:
                    sector = cama.sector
                    if sector not in sectores_stats:
                        sectores_stats[sector] = {'total': 0, 'ocupadas': 0, 'disponibles': 0}

                    sectores_stats[sector]['total'] += 1
                    if cama.CamaId in camas_ocupadas_ids:
                        sectores_stats[sector]['ocupadas'] += 1
                    else:
                        sectores_stats[sector]['disponibles'] += 1

                # Calcular porcentajes por sector
                for sector, stats in sectores_stats.items():
                    if stats['total'] > 0:
                        stats['porcentaje_ocupacion'] = round((stats['ocupadas'] / stats['total'] * 100), 2)
                        stats['porcentaje_disponibilidad'] = round((stats['disponibles'] / stats['total'] * 100), 2)

                result['estadisticas_por_sector'] = sectores_stats

            session.close()
            return result

        except Exception as e:
            error_info = handle_sql_error(e, "get_camas_disponibles")
            return {
                **error_info,
                'total_camas': 0,
                'total_ocupadas': 0,
                'total_disponibles': 0
            }

    # 2. HISTORIA CLÍNICA DE PACIENTE
    async def get_historia_clinica(self, documento: str = None, nombre: str = None) -> Dict[str, Any]:
        """
        Obtener historia clínica completa de un paciente
        """
        try:
            session = self.get_session()

            # Buscar paciente por documento o nombre
            query = session.query(Paciente)
            if documento:
                query = query.filter(Paciente.Documento == documento)
            elif nombre:
                nombres = nombre.split()
                if len(nombres) >= 2:
                    query = query.filter(
                        and_(
                            Paciente.Nombre.ilike(f'%{nombres[0]}%'),
                            Paciente.Apellido.ilike(f'%{nombres[-1]}%')
                        )
                    )
                else:
                    query = query.filter(
                        or_(
                            Paciente.Nombre.ilike(f'%{nombre}%'),
                            Paciente.Apellido.ilike(f'%{nombre}%')
                        )
                    )

            paciente = query.filter(Paciente.Anulado == False).first()

            if not paciente:
                return {'error': 'Paciente no encontrado', 'encontrado': False}

            # Obtener internaciones del paciente
            internaciones = session.query(
                Internacion,
                Cama.Nombre.label('nombre_cama'),
                Habitacion.Nombre.label('habitacion'),
                Sector.Nombre.label('sector'),
                Prestador.Nombre.label('medico_ingreso')
            ).join(
                Cama, Internacion.CamaID == Cama.CamaId
            ).join(
                Habitacion, Internacion.HabitacionID == Habitacion.HabitacionID
            ).join(
                Sector, Habitacion.SectorID == Sector.SectorId
            ).outerjoin(
                Prestador, Internacion.PrestadorIngresoID == Prestador.PrestadorID
            ).filter(
                and_(
                    Internacion.PacienteID == paciente.PacienteID,
                    Internacion.Anulado == False
                )
            ).order_by(Internacion.Fecha_ingreso.desc()).all()

            # Obtener turnos recientes
            turnos_recientes = session.query(
                Turno,
                Especialidad.Nombre.label('especialidad'),
                Prestador.Nombre.label('medico')
            ).outerjoin(
                Consultorio, Turno.ConsultorioID == Consultorio.ConsultorioID
            ).outerjoin(
                Especialidad, Consultorio.EspecialidadID == Especialidad.EspecialidadID
            ).outerjoin(
                Prestador, Turno.PrestadorID == Prestador.PrestadorID
            ).filter(
                and_(
                    Turno.PacienteID == paciente.PacienteID,
                    Turno.Anulado == False,
                    Turno.Fecha_Hora >= datetime(2024, 1, 1)  # Últimos años
                )
            ).order_by(Turno.Fecha_Hora.desc()).limit(10).all()

            # TODO: Implementar consulta de laboratorios cuando el modelo esté disponible
            estudios_laboratorio = []

            result = {
                'encontrado': True,
                'paciente': {
                    'id': paciente.PacienteID,
                    'nombre_completo': f"{paciente.Nombre} {paciente.Apellido}".strip(),
                    'documento': paciente.Documento,
                    'cuil': paciente.Cuil,
                    'fecha_nacimiento': paciente.FechadeNacimiento.strftime('%d/%m/%Y') if paciente.FechadeNacimiento else None,
                    'telefono': paciente.Telefono,
                    'correo': paciente.Correo
                },
                'internaciones': [],
                'turnos_recientes': []
            }

            # Procesar internaciones
            for internacion_data in internaciones:
                internacion = internacion_data.Internacion
                result['internaciones'].append({
                    'fecha_ingreso': internacion.Fecha_ingreso.strftime('%d/%m/%Y') if internacion.Fecha_ingreso else None,
                    'hora_ingreso': internacion.Hora_Ingreso,
                    'fecha_alta': internacion.Fecha_Alta.strftime('%d/%m/%Y') if internacion.Fecha_Alta else 'Internado actualmente',
                    'cama': internacion_data.nombre_cama,
                    'habitacion': internacion_data.habitacion,
                    'sector': internacion_data.sector,
                    'medico_ingreso': internacion_data.medico_ingreso,
                    'observaciones': getattr(internacion, 'Observaciones', 'Sin observaciones')
                })

            # Procesar turnos
            for turno_data in turnos_recientes:
                turno = turno_data.Turno
                result['turnos_recientes'].append({
                    'fecha': turno.Fecha_Hora.strftime('%d/%m/%Y %H:%M') if turno.Fecha_Hora else None,
                    'especialidad': turno_data.especialidad,
                    'medico': turno_data.medico,
                    'atendido': 'Sí' if turno.Atendido else 'No' if turno.NoAtendido else 'Pendiente'
                })

            session.close()
            return result

        except Exception as e:
            error_info = handle_sql_error(e, "get_historia_clinica")
            return {**error_info, 'encontrado': False}

    # 3. DATOS DE PACIENTE POR CAMA
    async def get_paciente_en_cama(self, numero_cama: str, sector: str = None) -> Dict[str, Any]:
        """
        Obtener datos del paciente internado en una cama específica
        """
        try:
            session = self.get_session()

            # Buscar cama - priorizar búsqueda por nombre, solo buscar por ID si es específicamente solicitado
            query = session.query(Cama)
            if numero_cama.isdigit() and len(numero_cama) >= 3:  # IDs típicamente son números largos
                # Buscar por ID solo si parece un ID real (3+ dígitos)
                query = query.filter(Cama.CamaId == int(numero_cama))
            else:
                # Para casos como "04", "101", buscar por nombre que contenga el número
                query = query.filter(Cama.Nombre.ilike(f'%{numero_cama}%'))

            if sector:
                # Buscar tanto en sector como en habitación para mayor flexibilidad
                query = query.join(Habitacion).outerjoin(Sector).filter(
                    or_(
                        Sector.Nombre.ilike(f'%{sector}%'),
                        Habitacion.Nombre.ilike(f'%{sector}%')
                    )
                )

            cama = query.filter(Cama.Anulado == False).first()

            if not cama:
                return {'error': 'Cama no encontrada', 'ocupada': False}

            # Buscar internación activa
            internacion = session.query(
                Internacion,
                Paciente,
                Prestador.Nombre.label('medico_ingreso')
            ).join(
                Paciente, Internacion.PacienteID == Paciente.PacienteID
            ).outerjoin(
                Prestador, Internacion.PrestadorIngresoID == Prestador.PrestadorID
            ).filter(
                and_(
                    Internacion.CamaID == cama.CamaId,
                    Internacion.Anulado == False,
                    Internacion.Fecha_Alta.is_(None)  # Sin alta
                )
            ).first()

            if not internacion:
                return {
                    'ocupada': False,
                    'cama_info': {
                        'id': cama.CamaId,
                        'nombre': cama.Nombre,
                        'estado': 'Disponible'
                    }
                }

            result = {
                'ocupada': True,
                'paciente': {
                    'nombre_completo': f"{internacion.Paciente.Nombre} {internacion.Paciente.Apellido}".strip(),
                    'documento': internacion.Paciente.Documento,
                    'fecha_ingreso': internacion.Internacion.Fecha_ingreso.strftime('%d/%m/%Y') if internacion.Internacion.Fecha_ingreso else None,
                    'dias_internado': (datetime.now().date() - internacion.Internacion.Fecha_ingreso).days if internacion.Internacion.Fecha_ingreso else 0,
                    'medico_ingreso': internacion.medico_ingreso,
                    'observaciones': getattr(internacion.Internacion, 'Observaciones', 'Sin observaciones') if hasattr(internacion, 'Internacion') else 'Sin observaciones'
                },
                'cama_info': {
                    'id': cama.CamaId,
                    'nombre': cama.Nombre
                }
            }

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error obteniendo paciente en cama: {e}")
            return {'error': str(e), 'ocupada': False}

    # 4. HORARIOS DE ATENCIÓN POR SERVICIO
    async def get_horarios_atencion(self, servicio_nombre: str) -> Dict[str, Any]:
        """
        Obtener horarios de atención directamente desde ServiciosDias y PrestadorDias
        """
        try:
            from app.models.entities import ZisServicio, ZisServicioDias, ZisDia, ZisPrestadorDias, ZisPrestador
            from sqlalchemy import and_

            session = self.get_session()

            # Buscar servicio por nombre
            servicio = session.query(ZisServicio).filter(
                and_(
                    ZisServicio.Nombre.ilike(f'%{servicio_nombre}%'),
                    ZisServicio.Anulado == False
                )
            ).first()

            if not servicio:
                return {'error': f'Servicio "{servicio_nombre}" no encontrado', 'encontrado': False}

            # Obtener horarios desde ServiciosDias
            horarios_servicio = session.query(ZisServicioDias, ZisDia).join(
                ZisDia, ZisServicioDias.DiaID == ZisDia.DiaID
            ).filter(
                and_(
                    ZisServicioDias.ServicioID == servicio.ServicioID,
                    ZisServicioDias.Anulado == False
                )
            ).all()

            # Obtener horarios desde PrestadorDias para este servicio
            horarios_prestador = session.query(ZisPrestadorDias, ZisDia, ZisPrestador).join(
                ZisDia, ZisPrestadorDias.DiaID == ZisDia.DiaID
            ).join(
                ZisPrestador, ZisPrestadorDias.PrestadorID == ZisPrestador.PrestadorID
            ).filter(
                and_(
                    ZisPrestadorDias.ServicioID == servicio.ServicioID,
                    ZisPrestadorDias.Anulado == False,
                    ZisPrestador.Anulado == False
                )
            ).all()

            # Formatear horarios
            horarios_formateados = []
            dias_procesados = set()

            # Procesar ServiciosDias
            for horario, dia in horarios_servicio:
                if dia.Nombre.strip() not in dias_procesados:
                    # Calcular turnos totales (Mañana + Tarde, usando campo Turnos o Frecuencia)
                    turnos_total = horario.Turnos if horario.Turnos else 0

                    # Determinar hora inicio: primer horario disponible
                    hora_inicio = None
                    if horario.M_Desde and horario.M_Desde.strip():
                        hora_inicio = self._format_hora(horario.M_Desde)
                    elif horario.T_Desde and horario.T_Desde.strip():
                        hora_inicio = self._format_hora(horario.T_Desde)
                    elif horario.N_Desde and horario.N_Desde.strip():
                        hora_inicio = self._format_hora(horario.N_Desde)

                    # Determinar hora fin: último horario disponible
                    hora_fin = None
                    if horario.N_Hasta and horario.N_Hasta.strip():
                        hora_fin = self._format_hora(horario.N_Hasta)
                    elif horario.T_Hasta and horario.T_Hasta.strip():
                        hora_fin = self._format_hora(horario.T_Hasta)
                    elif horario.M_Hasta and horario.M_Hasta.strip():
                        hora_fin = self._format_hora(horario.M_Hasta)

                    horario_info = {
                        'dia': dia.Nombre.strip(),
                        'hora_inicio': hora_inicio,
                        'hora_fin': hora_fin,
                        'cantidad_turnos': turnos_total,
                        'manana': f"{self._format_hora(horario.M_Desde)} - {self._format_hora(horario.M_Hasta)}" if horario.M_Desde and horario.M_Desde.strip() and horario.M_Hasta and horario.M_Hasta.strip() else None,
                        'tarde': f"{self._format_hora(horario.T_Desde)} - {self._format_hora(horario.T_Hasta)}" if horario.T_Desde and horario.T_Desde.strip() and horario.T_Hasta and horario.T_Hasta.strip() else None
                    }
                    horarios_formateados.append(horario_info)
                    dias_procesados.add(dia.Nombre.strip())

            # Procesar PrestadorDias
            prestadores_count = set()
            for horario, dia, prestador in horarios_prestador:
                prestadores_count.add(prestador.PrestadorID)
                if dia.Nombre.strip() not in dias_procesados:
                    # Calcular turnos totales (Mañana + Tarde + Noche)
                    turnos_total = (horario.CantPacienteM or 0) + (horario.CantPacienteT or 0) + (horario.CantPacienteN or 0)

                    # Determinar hora inicio: primer horario disponible
                    hora_inicio = None
                    if horario.M_Desde and horario.M_Desde.strip():
                        hora_inicio = self._format_hora(horario.M_Desde)
                    elif horario.T_Desde and horario.T_Desde.strip():
                        hora_inicio = self._format_hora(horario.T_Desde)
                    elif horario.N_Desde and horario.N_Desde.strip():
                        hora_inicio = self._format_hora(horario.N_Desde)

                    # Determinar hora fin: último horario disponible
                    hora_fin = None
                    if horario.N_Hasta and horario.N_Hasta.strip():
                        hora_fin = self._format_hora(horario.N_Hasta)
                    elif horario.T_Hasta and horario.T_Hasta.strip():
                        hora_fin = self._format_hora(horario.T_Hasta)
                    elif horario.M_Hasta and horario.M_Hasta.strip():
                        hora_fin = self._format_hora(horario.M_Hasta)

                    horario_info = {
                        'dia': dia.Nombre.strip(),
                        'hora_inicio': hora_inicio,
                        'hora_fin': hora_fin,
                        'cantidad_turnos': turnos_total,
                        'prestador': prestador.Nombre.strip(),
                        'manana': f"{self._format_hora(horario.M_Desde)} - {self._format_hora(horario.M_Hasta)}" if horario.M_Desde and horario.M_Desde.strip() and horario.M_Hasta and horario.M_Hasta.strip() else None,
                        'tarde': f"{self._format_hora(horario.T_Desde)} - {self._format_hora(horario.T_Hasta)}" if horario.T_Desde and horario.T_Desde.strip() and horario.T_Hasta and horario.T_Hasta.strip() else None
                    }
                    horarios_formateados.append(horario_info)
                    dias_procesados.add(dia.Nombre.strip())

            session.close()

            if not horarios_formateados:
                return {
                    'encontrado': True,
                    'servicio': servicio.Nombre.strip(),
                    'horarios': [],
                    'consultorios': 0,
                    'mensaje': 'Servicio encontrado pero sin horarios programados'
                }

            return {
                'encontrado': True,
                'servicio': servicio.Nombre.strip(),
                'horarios': sorted(horarios_formateados, key=lambda x: self._dia_orden(x['dia'])),
                'consultorios': len(prestadores_count),
                'estadisticas': {
                    'total_turnos': sum(h['cantidad_turnos'] for h in horarios_formateados),
                    'dias_con_atencion': len(horarios_formateados)
                }
            }

        except Exception as e:
            error_info = handle_sql_error(e, "get_horarios_atencion")
            return {**error_info, 'encontrado': False}

    def _format_hora(self, hora_str: str) -> str:
        """Formatear hora de formato HHMM a HH:MM"""
        if not hora_str or len(hora_str) < 4:
            return "00:00"
        return f"{hora_str[:2]}:{hora_str[2:]}"

    def _dia_orden(self, dia: str) -> int:
        """Obtener orden del día para sorting"""
        dias = {
            'Lunes': 1, 'Martes': 2, 'Miércoles': 3, 'Miercoles': 3,
            'Jueves': 4, 'Viernes': 5, 'Sábado': 6, 'Sabado': 6, 'Domingo': 7
        }
        return dias.get(dia.strip(), 99)

    # 5. VOLUMEN DE PACIENTES ATENDIDOS
    async def get_volumen_pacientes(self, servicio_nombre: str = None, fecha_desde: date = None,
                                  fecha_hasta: date = None) -> Dict[str, Any]:
        """
        Obtener cantidad de pacientes atendidos por servicio en un rango de fechas
        Usando el nuevo ORM service
        """
        try:
            # Si no se especifica servicio, obtener todos los servicios
            servicio_id = None
            servicio_encontrado = None

            if servicio_nombre:
                # Obtener servicios con horarios para buscar por nombre
                servicios_result = await orm_hospital_service.obtener_servicios_con_horarios()
                if not servicios_result.success:
                    return {'error': servicios_result.message, 'encontrado': False}

                # Buscar servicio por nombre
                for servicio in servicios_result.data['servicios']:
                    if servicio_nombre.lower() in servicio['nombre'].lower():
                        servicio_id = servicio['servicio_id']
                        servicio_encontrado = servicio
                        break

                if not servicio_id:
                    return {'error': 'Servicio no encontrado', 'encontrado': False}

            # Obtener volumen usando ORM service
            volumen_result = await orm_hospital_service.obtener_volumen_atencion(
                servicio_id=servicio_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )

            if not volumen_result.success:
                return {'error': volumen_result.message, 'encontrado': False}

            # Convertir formato del ORM a formato esperado por chatbot
            volumen_data = volumen_result.data

            # Preparar desglose por días en formato esperado
            desglose_dias = []
            if 'desglose_por_dia' in volumen_data:
                for fecha, info in sorted(volumen_data['desglose_por_dia'].items()):
                    desglose_dias.append({
                        'fecha': fecha,
                        'pacientes_atendidos': info['pacientes_atendidos'],
                        'total_turnos': info['total_turnos'],
                        'servicios_activos': info['servicios_activos']
                    })

            result = {
                'encontrado': True,
                'servicio': servicio_encontrado['nombre'] if servicio_encontrado else 'Todos los servicios',
                'periodo': f"{volumen_data['fecha_desde']} a {volumen_data['fecha_hasta']}",
                'total_pacientes_atendidos': volumen_data.get('total_pacientes_atendidos', 0),
                'total_turnos': volumen_data.get('total_turnos', 0),
                'servicios': volumen_data.get('servicios', []),
                'desglose_por_dia': desglose_dias,
                'estadisticas': {
                    'promedio_diario': volumen_data.get('estadisticas', {}).get('promedio_diario', 0),
                    'dias_con_atencion': volumen_data.get('estadisticas', {}).get('dias_con_atencion', 0),
                    'servicios_activos': volumen_data.get('estadisticas', {}).get('servicios_activos', 0)
                }
            }

            return result

        except Exception as e:
            error_info = handle_sql_error(e, "get_volumen_atencion")
            return {**error_info, 'encontrado': False}

    # 6. TURNOS PROGRAMADOS
    async def get_turnos_programados(self, servicio_nombre: str, fecha_desde: date = None) -> Dict[str, Any]:
        """
        Obtener turnos programados para un servicio o todos los turnos si no se especifica
        """
        try:
            session = self.get_session()

            if not fecha_desde:
                fecha_desde = datetime.now().date()

            fecha_hasta = fecha_desde + timedelta(days=7)  # Próxima semana

            # Si no se especifica servicio o es genérico, obtener todos los turnos de hoy
            if not servicio_nombre or servicio_nombre in ['medicina_general', 'general', 'todos']:
                # Query para todos los turnos de hoy
                turnos_count = session.query(Turno).filter(
                    and_(
                        func.cast(Turno.Fecha_Hora, Date) == fecha_desde,
                        Turno.Anulado == False
                    )
                ).count()

                result = {
                    'encontrado': True,
                    'servicio': 'Todos los servicios',
                    'fecha': fecha_desde.strftime('%d/%m/%Y'),
                    'total_turnos': turnos_count,
                    'turnos': [],
                    'message': f"Se encontraron {turnos_count} turnos programados para hoy"
                }

                session.close()
                return result

            # Buscar especialidad específica
            especialidad = session.query(Especialidad).filter(
                and_(
                    Especialidad.Nombre.ilike(f'%{servicio_nombre}%'),
                    Especialidad.Anulado == False
                )
            ).first()

            if not especialidad:
                # Si no encuentra la especialidad específica, devolver turnos generales
                turnos_count = session.query(Turno).filter(
                    and_(
                        func.cast(Turno.Fecha_Hora, Date) == fecha_desde,
                        Turno.Anulado == False
                    )
                ).count()

                result = {
                    'encontrado': True,
                    'servicio': f'Todos los servicios (no se encontró {servicio_nombre})',
                    'fecha': fecha_desde.strftime('%d/%m/%Y'),
                    'total_turnos': turnos_count,
                    'turnos': [],
                    'message': f"Se encontraron {turnos_count} turnos programados para hoy (especialidad {servicio_nombre} no encontrada)"
                }

                session.close()
                return result

            # Contar turnos para la especialidad específica
            turnos_count = session.query(Turno).join(
                Consultorio, Turno.ConsultorioID == Consultorio.ConsultorioID
            ).filter(
                and_(
                    Consultorio.EspecialidadID == especialidad.EspecialidadID,
                    func.cast(Turno.Fecha_Hora, Date) == fecha_desde,
                    Turno.Anulado == False
                )
            ).count()

            result = {
                'encontrado': True,
                'servicio': especialidad.Nombre,
                'fecha': fecha_desde.strftime('%d/%m/%Y'),
                'total_turnos': turnos_count,
                'turnos': [],
                'message': f"Se encontraron {turnos_count} turnos programados para {especialidad.Nombre} el {fecha_desde.strftime('%d/%m/%Y')}"
            }

            session.close()
            return result

        except Exception as e:
            error_info = handle_sql_error(e, "get_turnos_programados")
            return {**error_info, 'encontrado': False}

    # 7. CONSULTA DE ESPECIALIDADES DISPONIBLES
    async def get_especialidades_disponibles(self, filtro: str = None) -> Dict[str, Any]:
        """
        Obtener lista de especialidades disponibles en el hospital
        """
        try:
            session = self.get_session()

            # Query base para especialidades activas
            query = session.query(
                Especialidad.EspecialidadID,
                Especialidad.Nombre,
                func.count(Prestador.PrestadorID).label('prestadores_activos')
            ).outerjoin(
                Prestador, and_(
                    Prestador.EspecialidadID == Especialidad.EspecialidadID,
                    Prestador.Anulado == False
                )
            ).filter(
                Especialidad.Anulado == False
            ).group_by(
                Especialidad.EspecialidadID,
                Especialidad.Nombre
            )

            # Filtrar si se proporciona un criterio
            if filtro:
                query = query.filter(
                    Especialidad.Nombre.ilike(f'%{filtro}%')
                )

            especialidades = query.order_by(Especialidad.Nombre).all()

            result = {
                'encontrado': True,
                'total_especialidades': len(especialidades),
                'hospital': 'Hospital Regional Santiago del Estero',
                'especialidades': []
            }

            for esp in especialidades:
                result['especialidades'].append({
                    'id': esp.EspecialidadID,
                    'nombre': esp.Nombre.strip(),
                    'descripcion': f"Especialidad {esp.Nombre.strip()}",
                    'prestadores_activos': esp.prestadores_activos,
                    'disponible': esp.prestadores_activos > 0
                })

            session.close()
            return result

        except Exception as e:
            error_info = handle_sql_error(e, "get_especialidades_disponibles")
            return {**error_info, 'encontrado': False}

    # 8. BÚSQUEDA DE PACIENTE POR NOMBRE
    async def buscar_paciente_por_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        """
        Buscar datos básicos de paciente por nombre
        """
        try:
            session = self.get_session()

            # Buscar paciente por nombre - MEJORADO para casos con apellido en campo Nombre
            nombres = nombre.split()
            query = session.query(Paciente)

            if len(nombres) >= 2:
                # Si tiene nombre y apellido
                primer_nombre = nombres[0]
                ultimo_apellido = nombres[-1]

                query = query.filter(
                    or_(
                        # Búsqueda tradicional (nombre en Nombre, apellido en Apellido)
                        and_(
                            Paciente.Nombre.ilike(f'%{primer_nombre}%'),
                            Paciente.Apellido.ilike(f'%{ultimo_apellido}%')
                        ),
                        # Búsqueda inversa para casos "APELLIDO NOMBRE" en campo Nombre
                        and_(
                            Paciente.Nombre.ilike(f'%{ultimo_apellido}%'),
                            Paciente.Nombre.ilike(f'%{primer_nombre}%')
                        ),
                        # Búsqueda completa en campo Nombre
                        Paciente.Nombre.ilike(f'%{nombre}%')
                    )
                )
            else:
                # Solo un término de búsqueda - BUSCAR EN AMBOS CAMPOS Y CASOS MIXTOS
                query = query.filter(
                    or_(
                        # Búsqueda en campo Nombre
                        Paciente.Nombre.ilike(f'%{nombre}%'),
                        # Búsqueda en campo Apellido
                        Paciente.Apellido.ilike(f'%{nombre}%'),
                        # Búsqueda al inicio del campo Nombre (casos APELLIDO NOMBRE)
                        Paciente.Nombre.ilike(f'{nombre}%')
                    )
                )

            paciente = query.filter(Paciente.Anulado == False).first()

            if not paciente:
                session.close()
                return None

            # Verificar si tiene internación vigente
            internacion_vigente = session.query(
                Internacion,
                Cama.Nombre.label('nombre_cama'),
                Habitacion.Nombre.label('habitacion'),
                Sector.Nombre.label('sector'),
                Prestador.Nombre.label('medico_responsable')
            ).join(
                Cama, Internacion.CamaID == Cama.CamaId
            ).join(
                Habitacion, Internacion.HabitacionID == Habitacion.HabitacionID
            ).join(
                Sector, Habitacion.SectorID == Sector.SectorId
            ).outerjoin(
                Prestador, Internacion.PrestadorIngresoID == Prestador.PrestadorID
            ).filter(
                and_(
                    Internacion.PacienteID == paciente.PacienteID,
                    Internacion.Anulado == False,
                    Internacion.Fecha_Alta.is_(None)  # Sin alta (internado)
                )
            ).first()

            # Calcular edad si tiene fecha de nacimiento
            edad = None
            if paciente.FechadeNacimiento:
                hoy = datetime.now().date()
                edad = hoy.year - paciente.FechadeNacimiento.year
                if hoy.month < paciente.FechadeNacimiento.month or \
                   (hoy.month == paciente.FechadeNacimiento.month and hoy.day < paciente.FechadeNacimiento.day):
                    edad -= 1

            result = {
                'nombre_completo': f"{paciente.Nombre} {paciente.Apellido}".strip(),
                'documento': paciente.Documento.strip() if paciente.Documento else 'No disponible',
                'edad': edad,
                'fecha_nacimiento': paciente.FechadeNacimiento.strftime('%d/%m/%Y') if paciente.FechadeNacimiento else None,
                'telefono': paciente.Telefono.strip() if paciente.Telefono else None,
                'email': paciente.Correo.strip() if paciente.Correo else None,
                'obra_social': 'Información no disponible',  # El modelo no tiene este campo directo
            }

            if internacion_vigente:
                internacion = internacion_vigente.Internacion
                dias_internado = (datetime.now().date() - internacion.Fecha_ingreso).days if internacion.Fecha_ingreso else 0

                result['internacion_vigente'] = {
                    'internado': True,
                    'cama': internacion_vigente.nombre_cama,
                    'habitacion': internacion_vigente.habitacion,
                    'sector': internacion_vigente.sector,
                    'medico_responsable': internacion_vigente.medico_responsable,
                    'fecha_ingreso': internacion.Fecha_ingreso.strftime('%d/%m/%Y') if internacion.Fecha_ingreso else None,
                    'dias_internado': dias_internado
                }
            else:
                result['internacion_vigente'] = {'internado': False}

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error buscando paciente por nombre: {e}")
            return None

    # 9. ESTADO DE EMERGENCIAS BASADO EN DATOS REALES
    async def get_estado_emergencias(self, hospital_id: int = 3) -> Dict[str, Any]:
        """
        Obtener estado de emergencias basado en datos reales de ocupación de camas
        """
        try:
            session = self.get_session()

            # Obtener estadísticas reales de camas
            camas_query = session.query(
                func.count(Internacion.InternacionID).label('total_camas'),
                func.sum(case((Internacion.Anulado == False, 1), else_=0)).label('camas_ocupadas')
            ).filter(
                Internacion.InstitucionID == hospital_id
            ).first()

            total_camas = camas_query.total_camas or 0
            camas_ocupadas = camas_query.camas_ocupadas or 0
            camas_disponibles = max(0, total_camas - camas_ocupadas)
            porcentaje_ocupacion = (camas_ocupadas / total_camas * 100) if total_camas > 0 else 0

            result = {
                'encontrado': True,
                'total_camas': total_camas,
                'camas_ocupadas': camas_ocupadas,
                'camas_disponibles': camas_disponibles,
                'porcentaje_ocupacion': porcentaje_ocupacion,
                'timestamp': datetime.now().isoformat()
            }

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error obteniendo estado de emergencias: {e}")
            return {'error': str(e), 'encontrado': False}

    # 10. PRESTADORES DISPONIBLES
    async def get_prestadores_disponibles(self, hospital_id: int = 3) -> Dict[str, Any]:
        """
        Obtener información de prestadores disponibles por especialidad
        """
        try:
            session = self.get_session()

            # Contar prestadores por especialidad
            prestadores_query = session.query(
                Especialidad.Nombre.label('especialidad'),
                func.count(Prestador.PrestadorID).label('cantidad_prestadores')
            ).join(
                Prestador, Especialidad.EspecialidadID == Prestador.EspecialidadID
            ).filter(
                and_(
                    Especialidad.Anulado == False,
                    Prestador.Anulado == False,
                    Prestador.InstitucionID == hospital_id
                )
            ).group_by(
                Especialidad.EspecialidadID, Especialidad.Nombre
            ).order_by(
                func.count(Prestador.PrestadorID).desc()
            ).all()

            # Procesar resultados
            por_especialidad = []
            total_prestadores = 0

            for row in prestadores_query:
                especialidad_data = {
                    'nombre': row.especialidad,
                    'cantidad': row.cantidad_prestadores
                }
                por_especialidad.append(especialidad_data)
                total_prestadores += row.cantidad_prestadores

            result = {
                'encontrado': True,
                'total_prestadores': total_prestadores,
                'especialidades_activas': len(por_especialidad),
                'por_especialidad': por_especialidad,
                'timestamp': datetime.now().isoformat()
            }

            session.close()
            return result

        except Exception as e:
            error_info = handle_sql_error(e, "get_prestadores_por_especialidad")
            return {**error_info, 'encontrado': False}

# Instancia global del servicio
hospital_data_service = HospitalDataService()