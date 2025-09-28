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
from app.services.orm_hospital_service import orm_hospital_service

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
            logger.error(f"Error obteniendo historia clínica: {e}")
            return {'error': str(e), 'encontrado': False}

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
        Obtener horarios de atención de un servicio usando el nuevo ORM service
        """
        try:
            # Primero obtener servicios con horarios para buscar por nombre
            servicios_result = await orm_hospital_service.obtener_servicios_con_horarios()
            if not servicios_result.success:
                return {'error': servicios_result.message, 'encontrado': False}

            # Buscar servicio por nombre
            servicio_id = None
            servicio_encontrado = None
            for servicio in servicios_result.data['servicios']:
                if servicio_nombre.lower() in servicio['nombre'].lower():
                    servicio_id = servicio['servicio_id']
                    servicio_encontrado = servicio
                    break

            # Si no se encuentra en servicios, buscar en especialidades para dar mensaje más específico
            if not servicio_id:
                especialidades_result = await orm_hospital_service.obtener_especialidades_con_prestadores()
                if especialidades_result.success:
                    for especialidad in especialidades_result.data:
                        if servicio_nombre.lower() in especialidad['nombre'].lower().strip():
                            return {
                                'error': f'La especialidad {especialidad["nombre"].strip()} existe pero no tiene horarios de atención programados',
                                'encontrado': False,
                                'especialidad_existe': True,
                                'prestadores_disponibles': especialidad['cantidad_prestadores']
                            }

                return {'error': 'Servicio no encontrado', 'encontrado': False}

            # Obtener horarios usando ORM service
            horarios_result = await orm_hospital_service.obtener_horarios_atencion(servicio_id=servicio_id)
            if not horarios_result.success:
                return {'error': horarios_result.message, 'encontrado': False}

            # Convertir formato del ORM a formato esperado por chatbot
            horarios_data = horarios_result.data
            horarios_formateados = []

            if 'horarios_por_dia' in horarios_data:
                for dia_info in horarios_data['horarios_por_dia']:
                    if dia_info['cantidad'] > 0:
                        horarios_formateados.append({
                            'dia': dia_info['dia'],
                            'hora_inicio': dia_info['hora_inicio'],
                            'hora_fin': dia_info['hora_fin'],
                            'cantidad_turnos': dia_info['cantidad']
                        })

            result = {
                'encontrado': True,
                'servicio': servicio_encontrado['nombre'],
                'horarios': horarios_formateados,
                'consultorios': len(horarios_data.get('prestadores', [])),
                'estadisticas': {
                    'total_turnos': horarios_data.get('estadisticas', {}).get('total_turnos', 0),
                    'dias_con_atencion': len(horarios_formateados)
                }
            }

            return result

        except Exception as e:
            logger.error(f"Error obteniendo horarios: {e}")
            return {'error': str(e), 'encontrado': False}

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
                session.close()
                return {'error': 'Servicio no encontrado', 'encontrado': False}

            # Simplificar query - solo contar turnos por ahora
            turnos_count = session.query(Turno).join(
                Consultorio, Turno.ConsultorioID == Consultorio.ConsultorioID
            ).filter(
                and_(
                    Consultorio.EspecialidadID == especialidad.EspecialidadID,
                    Turno.Anulado == False
                )
            ).count()

            result = {
                'encontrado': True,
                'servicio': especialidad.Nombre,
                'período': f"Desde {fecha_desde:%d/%m/%Y}",
                'turnos_encontrados': turnos_count,
                'turnos': []
            }

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
            logger.error(f"Error obteniendo especialidades: {e}")
            return {'error': str(e), 'encontrado': False}

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

# Instancia global del servicio
hospital_data_service = HospitalDataService()