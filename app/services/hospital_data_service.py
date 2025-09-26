"""
Hospital Data Service - Consultas reales a la base de datos DBH_TEST
Servicio para las 6 consultas principales usando SQLAlchemy ORM
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from app.database.connection import db_connection
from app.database.models import (
    Cama, Habitacion, Sector, Internacion, Paciente,
    Turno, Especialidad, Consultorio, Prestador, Servicio
)

logger = logging.getLogger(__name__)

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
            logger.error(f"Error obteniendo estadísticas de camas: {e}")
            return {'error': str(e), 'total_camas': 0, 'total_ocupadas': 0, 'total_disponibles': 0}

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
                    'observaciones': internacion.Observaciones
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
            logger.error(f"Error obteniendo historia clínica: {e}")
            return {'error': str(e), 'encontrado': False}

    # 3. DATOS DE PACIENTE POR CAMA
    async def get_paciente_en_cama(self, numero_cama: str, sector: str = None) -> Dict[str, Any]:
        """
        Obtener datos del paciente internado en una cama específica
        """
        try:
            session = self.get_session()

            # Buscar cama
            query = session.query(Cama)
            if numero_cama.isdigit():
                query = query.filter(Cama.CamaId == int(numero_cama))
            else:
                query = query.filter(Cama.Nombre.ilike(f'%{numero_cama}%'))

            if sector:
                query = query.join(Habitacion).join(Sector).filter(
                    Sector.Nombre.ilike(f'%{sector}%')
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
                    'observaciones': internacion.Internacion.Observaciones
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
        Obtener horarios de atención de un servicio basado en turnos programados
        """
        try:
            session = self.get_session()

            # Buscar especialidad por nombre
            especialidad = session.query(Especialidad).filter(
                and_(
                    Especialidad.Nombre.ilike(f'%{servicio_nombre}%'),
                    Especialidad.Anulado == False
                )
            ).first()

            if not especialidad:
                return {'error': 'Servicio no encontrado', 'encontrado': False}

            # Obtener consultorios de la especialidad
            consultorios = session.query(Consultorio).filter(
                and_(
                    Consultorio.EspecialidadID == especialidad.EspecialidadID,
                    Consultorio.Anulado == False
                )
            ).all()

            if not consultorios:
                return {'error': 'No hay consultorios para este servicio', 'encontrado': False}

            consultorio_ids = [c.ConsultorioID for c in consultorios]

            # Obtener horarios típicos basados en turnos recientes
            from datetime import datetime, timedelta

            fecha_desde = datetime.now().date() - timedelta(days=30)  # Últimos 30 días

            # Simplificar la consulta para evitar problemas con func.datepart
            turnos_query = session.query(Turno).filter(
                and_(
                    Turno.ConsultorioID.in_(consultorio_ids),
                    Turno.Anulado == False,
                    func.cast(Turno.Fecha_Hora, date) >= fecha_desde
                )
            ).limit(100).all()  # Limitar para mejorar rendimiento

            # Procesar turnos en Python para extraer horarios
            horarios_por_dia = {}

            for turno in turnos_query:
                if turno.Fecha_Hora:
                    dia_semana = turno.Fecha_Hora.weekday()  # 0=Lunes, 6=Domingo
                    hora_inicio = turno.Fecha_Hora.time()

                    if dia_semana not in horarios_por_dia:
                        horarios_por_dia[dia_semana] = {
                            'horas_inicio': [],
                            'horas_fin': [],
                            'cantidad': 0
                        }

                    horarios_por_dia[dia_semana]['horas_inicio'].append(hora_inicio)
                    if turno.Hora_Hasta:
                        horarios_por_dia[dia_semana]['horas_fin'].append(turno.Hora_Hasta)
                    horarios_por_dia[dia_semana]['cantidad'] += 1

            # Convertir a formato final
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            horarios = []

            for dia_num, data in horarios_por_dia.items():
                if data['cantidad'] > 0:
                    hora_min = min(data['horas_inicio']).strftime('%H:%M') if data['horas_inicio'] else '08:00'
                    hora_max = max(data['horas_fin']).strftime('%H:%M') if data['horas_fin'] else '17:00'

                    horarios.append({
                        'dia': dias[dia_num],
                        'hora_inicio': hora_min,
                        'hora_fin': hora_max,
                        'cantidad_turnos': data['cantidad']
                    })

            result = {
                'encontrado': True,
                'servicio': especialidad.Nombre,
                'horarios': sorted(horarios, key=lambda x: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].index(x['dia']) if x['dia'] in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'] else 7),
                'consultorios': len(consultorios)
            }

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error obteniendo horarios: {e}")
            return {'error': str(e), 'encontrado': False}

    # 5. VOLUMEN DE PACIENTES ATENDIDOS
    async def get_volumen_pacientes(self, servicio_nombre: str, mes: int, año: int) -> Dict[str, Any]:
        """
        Obtener cantidad de pacientes atendidos en un período
        """
        try:
            session = self.get_session()

            # Buscar especialidad
            especialidad = session.query(Especialidad).filter(
                and_(
                    Especialidad.Nombre.ilike(f'%{servicio_nombre}%'),
                    Especialidad.Anulado == False
                )
            ).first()

            if not especialidad:
                return {'error': 'Servicio no encontrado', 'encontrado': False}

            # Obtener consultorios
            consultorio_ids = session.query(Consultorio.ConsultorioID).filter(
                and_(
                    Consultorio.EspecialidadID == especialidad.EspecialidadID,
                    Consultorio.Anulado == False
                )
            ).subquery()

            # Contar turnos atendidos en el período
            fecha_inicio = datetime(año, mes, 1)
            if mes == 12:
                fecha_fin = datetime(año + 1, 1, 1)
            else:
                fecha_fin = datetime(año, mes + 1, 1)

            turnos_atendidos = session.query(func.count(Turno.TurnoID)).filter(
                and_(
                    Turno.ConsultorioID.in_(consultorio_ids),
                    Turno.Anulado == False,
                    Turno.Atendido.isnot(None),  # Fueron atendidos
                    Turno.Fecha_Hora >= fecha_inicio,
                    Turno.Fecha_Hora < fecha_fin
                )
            ).scalar()

            # Contar pacientes únicos
            pacientes_unicos = session.query(func.count(func.distinct(Turno.PacienteID))).filter(
                and_(
                    Turno.ConsultorioID.in_(consultorio_ids),
                    Turno.Anulado == False,
                    Turno.Atendido.isnot(None),
                    Turno.Fecha_Hora >= fecha_inicio,
                    Turno.Fecha_Hora < fecha_fin
                )
            ).scalar()

            meses = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

            result = {
                'encontrado': True,
                'servicio': especialidad.Nombre,
                'período': f"{meses[mes]} {año}",
                'total_turnos_atendidos': turnos_atendidos or 0,
                'pacientes_únicos': pacientes_unicos or 0
            }

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error obteniendo volumen: {e}")
            return {'error': str(e), 'encontrado': False}

    # 6. TURNOS PROGRAMADOS
    async def get_turnos_programados(self, servicio_nombre: str, fecha_desde: date = None) -> Dict[str, Any]:
        """
        Obtener turnos programados para un servicio
        """
        try:
            session = self.get_session()

            if not fecha_desde:
                fecha_desde = datetime.now().date()

            fecha_hasta = fecha_desde + timedelta(days=7)  # Próxima semana

            # Buscar especialidad
            especialidad = session.query(Especialidad).filter(
                and_(
                    Especialidad.Nombre.ilike(f'%{servicio_nombre}%'),
                    Especialidad.Anulado == False
                )
            ).first()

            if not especialidad:
                return {'error': 'Servicio no encontrado', 'encontrado': False}

            # Obtener turnos programados
            turnos = session.query(
                Turno,
                Paciente.Nombre.label('nombre_paciente'),
                Paciente.Apellido.label('apellido_paciente'),
                Prestador.Nombre.label('medico'),
                Consultorio.Nombre.label('consultorio')
            ).join(
                Paciente, Turno.PacienteID == Paciente.PacienteID
            ).join(
                Consultorio, Turno.ConsultorioID == Consultorio.ConsultorioID
            ).outerjoin(
                Prestador, Turno.PrestadorID == Prestador.PrestadorID
            ).filter(
                and_(
                    Consultorio.EspecialidadID == especialidad.EspecialidadID,
                    Turno.Anulado == False,
                    func.cast(Turno.Fecha_Hora, date) >= fecha_desde,
                    func.cast(Turno.Fecha_Hora, date) <= fecha_hasta,
                    Turno.Atendido.is_(None)  # No atendidos aún
                )
            ).order_by(Turno.Fecha_Hora).all()

            result = {
                'encontrado': True,
                'servicio': especialidad.Nombre,
                'período': f"Desde {fecha_desde.strftime('%d/%m/%Y')}",
                'total_turnos': len(turnos),
                'turnos': []
            }

            for turno_data in turnos:
                turno = turno_data.Turno
                result['turnos'].append({
                    'fecha': turno.Fecha_Hora.strftime('%d/%m/%Y'),
                    'hora': turno.Fecha_Hora.strftime('%H:%M'),
                    'paciente': f"{turno_data.nombre_paciente} {turno_data.apellido_paciente}".strip(),
                    'medico': turno_data.medico,
                    'consultorio': turno_data.consultorio,
                    'estado': 'Programado'
                })

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error obteniendo turnos: {e}")
            return {'error': str(e), 'encontrado': False}

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
                Especialidad.Descripcion,
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
                Especialidad.Nombre,
                Especialidad.Descripcion
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
                    'descripcion': esp.Descripcion.strip() if esp.Descripcion else None,
                    'prestadores_activos': esp.prestadores_activos,
                    'disponible': esp.prestadores_activos > 0
                })

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error obteniendo especialidades: {e}")
            return {'error': str(e), 'encontrado': False}

    # 8. BÚSQUEDA DE PACIENTE POR NOMBRE
    async def buscar_paciente_por_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        """
        Buscar datos básicos de paciente por nombre
        """
        try:
            session = self.get_session()

            # Buscar paciente por nombre
            nombres = nombre.split()
            query = session.query(Paciente)

            if len(nombres) >= 2:
                # Si tiene nombre y apellido
                query = query.filter(
                    and_(
                        Paciente.Nombre.ilike(f'%{nombres[0]}%'),
                        Paciente.Apellido.ilike(f'%{nombres[-1]}%')
                    )
                )
            else:
                # Solo un término de búsqueda
                query = query.filter(
                    or_(
                        Paciente.Nombre.ilike(f'%{nombre}%'),
                        Paciente.Apellido.ilike(f'%{nombre}%')
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

# Instancia global del servicio
hospital_data_service = HospitalDataService()