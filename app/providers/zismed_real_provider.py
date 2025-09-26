from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
import logging

from .base import BaseProvider, ProviderConfig, Patient, Professional, Hospital, Appointment
from app.config.zismed_database import get_zismed_session, get_zismed_db
from app.models.entities import (
    ZisTurno, ZisPaciente, ZisEspecialidad, ZisConsultorio,
    ZisLaboratorioRegistro, ZisCama, ZisInternacion, ZisFarmaciaArticulo
)

logger = logging.getLogger(__name__)

class ZisMedRealProvider(BaseProvider):
    """Provider real que usa datos de ZisMed con ORM SQLAlchemy"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.zismed_db = get_zismed_db()

    async def connect(self) -> bool:
        """Verificar conexión a ZisMed"""
        return self.zismed_db.test_connection()

    # === FUNCIONALIDAD 1: BÚSQUEDA DE PACIENTES ===
    async def get_patient_by_dni(self, dni: str, hospital_id: str) -> Optional[Patient]:
        """Buscar paciente real por DNI en ZisMed"""
        try:
            with self.zismed_db.get_session_context() as db:
                paciente = db.query(ZisPaciente).filter(
                    and_(
                        ZisPaciente.Documento == dni.strip(),
                        ZisPaciente.Anulado == False,
                        ZisPaciente.InstitucionID == int(hospital_id)
                    )
                ).first()

                if paciente:
                    # Calcular edad si tiene fecha de nacimiento
                    edad = None
                    if paciente.FechadeNacimiento:
                        today = date.today()
                        edad = today.year - paciente.FechadeNacimiento.year
                        if today.month < paciente.FechadeNacimiento.month or \
                           (today.month == paciente.FechadeNacimiento.month and today.day < paciente.FechadeNacimiento.day):
                            edad -= 1

                    return Patient(
                        id=str(paciente.PacienteID),
                        dni=paciente.Documento.strip(),
                        name=f"{paciente.Nombre.strip()} {paciente.Apellido.strip() if paciente.Apellido else ''}".strip(),
                        phone=paciente.Telefono or "No registrado",
                        email=paciente.Correo or "No registrado",
                        metadata={
                            "edad": edad,
                            "obra_social_id": paciente.ObraSocialID,
                            "fecha_nacimiento": paciente.FechadeNacimiento.isoformat() if paciente.FechadeNacimiento else None,
                            "fecha_registro": paciente.FechaCarga.isoformat() if paciente.FechaCarga else None,
                            "cuil": paciente.Cuil,
                            "sexo": paciente.IdSexo
                        }
                    )
                return None
        except Exception as e:
            logger.error(f"Error buscando paciente por DNI {dni}: {e}")
            return None

    # === FUNCIONALIDAD 2: BÚSQUEDA AVANZADA DE PACIENTES ===
    async def search_patients_by_name(self, name: str, hospital_id: str, limit: int = 10) -> List[Patient]:
        """Buscar pacientes por nombre/apellido en ZisMed"""
        try:
            with self.zismed_db.get_session_context() as db:
                search_term = f"%{name.upper()}%"

                pacientes = db.query(ZisPaciente).filter(
                    and_(
                        or_(
                            ZisPaciente.Nombre.like(search_term),
                            ZisPaciente.Apellido.like(search_term)
                        ),
                        ZisPaciente.Anulado == False,
                        ZisPaciente.InstitucionID == int(hospital_id)
                    )
                ).order_by(ZisPaciente.Nombre).limit(limit).all()

                result = []
                for p in pacientes:
                    # Contar turnos del paciente
                    turnos_count = db.query(ZisTurno).filter(
                        and_(
                            ZisTurno.PacienteID == p.PacienteID,
                            ZisTurno.Anulado == False
                        )
                    ).count()

                    result.append(Patient(
                        id=str(p.PacienteID),
                        dni=p.Documento.strip(),
                        name=f"{p.Nombre.strip()} {p.Apellido.strip() if p.Apellido else ''}".strip(),
                        phone=p.Telefono or "No registrado",
                        email=p.Correo or "No registrado",
                        metadata={"total_appointments": turnos_count}
                    ))

                return result
        except Exception as e:
            logger.error(f"Error buscando pacientes por nombre {name}: {e}")
            return []

    # === FUNCIONALIDAD 3: ESPECIALIDADES MEJORADAS ===
    async def get_complete_specialties_historical(self, hospital_id: str) -> Dict[str, Any]:
        """Obtener especialidades históricas completas con estadísticas"""
        try:
            with self.zismed_db.get_session_context() as db:
                # Obtener especialidades con estadísticas de turnos
                fecha_inicio = datetime.now() - timedelta(days=365)  # Último año

                especialidades_query = db.query(
                    ZisEspecialidad.EspecialidadID,
                    ZisEspecialidad.Nombre,
                    func.count(ZisTurno.TurnoID).label('total_turnos_año'),
                    func.count(func.distinct(ZisTurno.PrestadorID)).label('prestadores_unicos'),
                    func.max(ZisTurno.Fecha_Hora).label('ultimo_turno')
                ).outerjoin(
                    ZisConsultorio, ZisConsultorio.EspecialidadID == ZisEspecialidad.EspecialidadID
                ).outerjoin(
                    ZisTurno, and_(
                        ZisTurno.ConsultorioID == ZisConsultorio.ConsultorioID,
                        ZisTurno.Fecha_Hora >= fecha_inicio,
                        ZisTurno.Anulado == False,
                        ZisTurno.InstitucionID == int(hospital_id)
                    )
                ).filter(
                    ZisEspecialidad.Anulado == False
                ).group_by(
                    ZisEspecialidad.EspecialidadID, ZisEspecialidad.Nombre
                ).order_by(desc('total_turnos_año')).all()

                especialidades = []
                total_turnos_historicos = 0

                for esp in especialidades_query:
                    turnos_año = esp.total_turnos_año or 0
                    total_turnos_historicos += turnos_año

                    # Determinar nivel de actividad
                    if turnos_año > 500:
                        nivel_actividad = "ALTA"
                    elif turnos_año > 100:
                        nivel_actividad = "MEDIA"
                    else:
                        nivel_actividad = "BAJA"

                    especialidades.append({
                        "id": esp.EspecialidadID,
                        "nombre": esp.Nombre.strip(),
                        "total_turnos_año": turnos_año,
                        "prestadores_unicos": esp.prestadores_unicos or 0,
                        "ultimo_turno": esp.ultimo_turno.isoformat() if esp.ultimo_turno else None,
                        "nivel_actividad": nivel_actividad
                    })

                return {
                    "especialidades": especialidades,
                    "total_especialidades": len(especialidades),
                    "total_turnos_historicos": total_turnos_historicos,
                    "periodo_analizado": f"Últimos 365 días desde {fecha_inicio.strftime('%d/%m/%Y')}",
                    "hospital_id": hospital_id,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error obteniendo especialidades históricas: {e}")
            return {"error": str(e), "especialidades": []}

    # === FUNCIONALIDAD 4: TURNOS Y AGENDA ===
    async def get_appointments(
        self,
        hospital_id: str,
        patient_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Appointment]:
        """Obtener turnos reales de ZisMed"""
        try:
            with self.zismed_db.get_session_context() as db:
                query = db.query(ZisTurno).filter(
                    and_(
                        ZisTurno.Anulado == False,
                        ZisTurno.InstitucionID == int(hospital_id)
                    )
                )

                if patient_id:
                    query = query.filter(ZisTurno.PacienteID == int(patient_id))

                if date_from:
                    query = query.filter(ZisTurno.Fecha_Hora >= date_from)

                if date_to:
                    query = query.filter(ZisTurno.Fecha_Hora <= date_to)

                turnos = query.order_by(ZisTurno.Fecha_Hora).limit(100).all()

                result = []
                for turno in turnos:
                    # Determinar estado
                    if turno.Atendido:
                        status = "atendido"
                    elif turno.NoAtendido:
                        status = "no_atendido"
                    elif turno.Llamado:
                        status = "llamado"
                    elif turno.Llegada:
                        status = "llegada"
                    else:
                        status = "programado"

                    result.append(Appointment(
                        id=str(turno.TurnoID),
                        patient_id=str(turno.PacienteID),
                        professional_id=str(turno.PrestadorID),
                        hospital_id=hospital_id,
                        datetime=turno.Fecha_Hora,
                        status=status,
                        notes=f"Consultorio: {turno.ConsultorioID}, Orden: {turno.Orden or 'N/A'}"
                    ))

                return result
        except Exception as e:
            logger.error(f"Error obteniendo turnos: {e}")
            return []

    # === FUNCIONALIDAD 5: ESTADO DE CAMAS ===
    async def get_complete_bed_occupancy_data(self, hospital_id: str) -> Dict[str, Any]:
        """Obtener datos completos de ocupación de camas"""
        try:
            with self.zismed_db.get_session_context() as db:
                # Camas totales por institución
                camas_query = db.query(
                    func.count(ZisCama.CamaId).label('total_camas'),
                    func.sum(func.case([(ZisCama.En_mantenimiento == True, 1)], else_=0)).label('en_mantenimiento'),
                    func.sum(func.case([(ZisCama.Habilitada == True, 1)], else_=0)).label('habilitadas')
                ).filter(
                    and_(
                        ZisCama.Anulado == False,
                        ZisCama.InstitucionID == int(hospital_id)
                    )
                ).first()

                # Internaciones activas (sin fecha de alta)
                internaciones_activas = db.query(ZisInternacion).filter(
                    and_(
                        ZisInternacion.Fecha_Alta == None,
                        ZisInternacion.Anulado == False,
                        ZisInternacion.InstitucionID == int(hospital_id)
                    )
                ).count()

                # Ocupación por servicio (usando habitaciones)
                ocupacion_servicios = db.query(
                    func.count(ZisInternacion.InternacionID).label('ocupadas'),
                    ZisInternacion.HabitacionID
                ).filter(
                    and_(
                        ZisInternacion.Fecha_Alta == None,
                        ZisInternacion.Anulado == False,
                        ZisInternacion.InstitucionID == int(hospital_id)
                    )
                ).group_by(ZisInternacion.HabitacionID).all()

                camas_totales = camas_query.total_camas or 0
                camas_ocupadas = internaciones_activas
                camas_disponibles = max(0, camas_totales - camas_ocupadas)
                porcentaje_ocupacion = round((camas_ocupadas / max(camas_totales, 1)) * 100, 1)

                # Datos por servicio
                servicios_ocupacion = []
                for servicio in ocupacion_servicios:
                    servicios_ocupacion.append({
                        "servicio": f"Habitación {servicio.HabitacionID}",
                        "ocupacion": round((servicio.ocupadas / max(camas_totales, 1)) * 100, 1),
                        "camas_ocupadas": servicio.ocupadas
                    })

                return {
                    "resumen_camas": {
                        "camas_totales_estimadas": camas_totales,
                        "camas_ocupadas_estimadas": camas_ocupadas,
                        "camas_disponibles_estimadas": camas_disponibles,
                        "porcentaje_ocupacion": porcentaje_ocupacion,
                        "en_mantenimiento": camas_query.en_mantenimiento or 0,
                        "habilitadas": camas_query.habilitadas or 0
                    },
                    "ocupacion_por_servicio": servicios_ocupacion[:10],
                    "internaciones_activas": internaciones_activas,
                    "hospital_id": hospital_id,
                    "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M')
                }

        except Exception as e:
            logger.error(f"Error obteniendo datos de camas: {e}")
            return {"error": str(e)}

    # === FUNCIONALIDAD 6: LABORATORIO ===
    async def get_laboratory_data(self, hospital_id: str, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtener datos de laboratorio"""
        try:
            with self.zismed_db.get_session_context() as db:
                query = db.query(ZisLaboratorioRegistro).filter(
                    and_(
                        ZisLaboratorioRegistro.Anulado == False,
                        ZisLaboratorioRegistro.InstitucionID == int(hospital_id)
                    )
                )

                if patient_id:
                    query = query.filter(ZisLaboratorioRegistro.PacienteID == int(patient_id))

                # Estadísticas generales
                hoy = date.today()
                estudios_hoy = query.filter(
                    func.date(ZisLaboratorioRegistro.Fecha) == hoy
                ).count()

                estudios_pendientes = query.filter(
                    ZisLaboratorioRegistro.PracticasEstadoID != 3  # Asumiendo que 3 = completado
                ).count()

                estudios_urgentes = query.filter(
                    ZisLaboratorioRegistro.Urgente == True
                ).count()

                # Últimos estudios
                ultimos_estudios = query.order_by(
                    desc(ZisLaboratorioRegistro.Fecha)
                ).limit(10).all()

                estudios_data = []
                for estudio in ultimos_estudios:
                    estudios_data.append({
                        "id": estudio.LaboratorioRegistroID,
                        "paciente_id": estudio.PacienteID,
                        "fecha": estudio.Fecha.strftime('%d/%m/%Y %H:%M'),
                        "numero_identificador": estudio.NumeroIdentificador,
                        "urgente": estudio.Urgente,
                        "prestador_solicita": estudio.PrestadorSolicita,
                        "estado": estudio.PracticasEstadoID
                    })

                return {
                    "estadisticas": {
                        "estudios_hoy": estudios_hoy,
                        "estudios_pendientes": estudios_pendientes,
                        "estudios_urgentes": estudios_urgentes
                    },
                    "ultimos_estudios": estudios_data,
                    "hospital_id": hospital_id,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error obteniendo datos laboratorio: {e}")
            return {"error": str(e)}

    # === FUNCIONALIDAD 7: FARMACIA ===
    async def get_pharmacy_stock(self, hospital_id: str, search_term: Optional[str] = None) -> Dict[str, Any]:
        """Obtener stock de farmacia"""
        try:
            with self.zismed_db.get_session_context() as db:
                query = db.query(ZisFarmaciaArticulo).filter(
                    ZisFarmaciaArticulo.Anulado == False
                )

                if search_term:
                    search_pattern = f"%{search_term.upper()}%"
                    query = query.filter(
                        ZisFarmaciaArticulo.Nombre.like(search_pattern)
                    )

                # Medicamentos con stock bajo
                stock_bajo = query.filter(
                    ZisFarmaciaArticulo.StockMinimo > 0  # Asumiendo que hay un campo de stock actual
                ).limit(20).all()

                medicamentos = []
                for med in stock_bajo:
                    medicamentos.append({
                        "id": med.FarmaciaArticuloID,
                        "codigo": med.CodigoArticulo,
                        "nombre": med.Nombre,
                        "presentacion": med.Presentacion,
                        "codigo_barras": med.CodigoBarras,
                        "stock_minimo": float(med.StockMinimo) if med.StockMinimo else 0,
                        "fecha_creacion": med.FechaCrea.strftime('%d/%m/%Y') if med.FechaCrea else None
                    })

                return {
                    "medicamentos": medicamentos,
                    "total_articulos": len(medicamentos),
                    "busqueda": search_term or "Todos",
                    "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M')
                }

        except Exception as e:
            logger.error(f"Error obteniendo stock farmacia: {e}")
            return {"error": str(e)}

    # === FUNCIONALIDAD 8: PRESTADORES/PROFESIONALES ===
    async def get_professionals(self, hospital_id: str) -> List[Professional]:
        """Obtener prestadores/profesionales por institución"""
        try:
            with self.zismed_db.get_session_context() as db:
                # Obtener prestadores únicos con turnos activos
                prestadores_query = db.query(
                    ZisTurno.PrestadorID,
                    func.count(ZisTurno.TurnoID).label('total_turnos'),
                    func.max(ZisTurno.Fecha_Hora).label('ultimo_turno')
                ).filter(
                    and_(
                        ZisTurno.Anulado == False,
                        ZisTurno.InstitucionID == int(hospital_id),
                        ZisTurno.Fecha_Hora >= (datetime.now() - timedelta(days=30))  # Últimos 30 días
                    )
                ).group_by(
                    ZisTurno.PrestadorID
                ).order_by(
                    desc('total_turnos')
                ).limit(50).all()

                professionals = []
                for prestador in prestadores_query:
                    # Obtener especialidades del prestador
                    especialidades = db.query(
                        ZisEspecialidad.Nombre
                    ).join(
                        ZisConsultorio, ZisConsultorio.EspecialidadID == ZisEspecialidad.EspecialidadID
                    ).join(
                        ZisTurno, ZisTurno.ConsultorioID == ZisConsultorio.ConsultorioID
                    ).filter(
                        and_(
                            ZisTurno.PrestadorID == prestador.PrestadorID,
                            ZisTurno.Anulado == False,
                            ZisEspecialidad.Anulado == False
                        )
                    ).distinct().all()

                    specialties = [esp.Nombre.strip() for esp in especialidades]

                    professionals.append(Professional(
                        id=str(prestador.PrestadorID),
                        name=f"Prestador {prestador.PrestadorID}",  # En ZisMed no está el nombre en esta tabla
                        specialties=specialties,
                        hospital_id=hospital_id,
                        metadata={
                            "total_turnos_mes": prestador.total_turnos,
                            "ultimo_turno": prestador.ultimo_turno.isoformat() if prestador.ultimo_turno else None
                        }
                    ))

                return professionals

        except Exception as e:
            logger.error(f"Error obteniendo profesionales: {e}")
            return []

    # === FUNCIONALIDAD 9: DASHBOARD OPERATIVO ===
    async def get_real_bed_data(self, hospital_id: str) -> Dict[str, Any]:
        """Dashboard operativo en tiempo real"""
        try:
            with self.zismed_db.get_session_context() as db:
                hoy = date.today()
                ahora = datetime.now()

                # Turnos de hoy
                turnos_hoy = db.query(ZisTurno).filter(
                    and_(
                        func.date(ZisTurno.Fecha_Hora) == hoy,
                        ZisTurno.Anulado == False,
                        ZisTurno.InstitucionID == int(hospital_id)
                    )
                ).count()

                # Pacientes en atención ahora
                en_atencion_ahora = db.query(ZisTurno).filter(
                    and_(
                        ZisTurno.Llamado != None,
                        ZisTurno.Atendido == None,
                        ZisTurno.NoAtendido == None,
                        func.date(ZisTurno.Fecha_Hora) == hoy,
                        ZisTurno.Anulado == False,
                        ZisTurno.InstitucionID == int(hospital_id)
                    )
                ).count()

                # Prestadores activos hoy
                prestadores_hoy = db.query(
                    func.count(func.distinct(ZisTurno.PrestadorID))
                ).filter(
                    and_(
                        func.date(ZisTurno.Fecha_Hora) == hoy,
                        ZisTurno.Anulado == False,
                        ZisTurno.InstitucionID == int(hospital_id)
                    )
                ).scalar()

                # Especialidades por actividad
                especialidades_actividad = db.query(
                    ZisEspecialidad.Nombre,
                    func.count(ZisTurno.TurnoID).label('turnos_hoy'),
                    func.sum(func.case([(ZisTurno.Atendido != None, 1)], else_=0)).label('atendidos'),
                    func.sum(func.case([(and_(ZisTurno.Llamado != None, ZisTurno.Atendido == None), 1)], else_=0)).label('en_atencion'),
                    func.count(func.distinct(ZisTurno.PrestadorID)).label('prestadores')
                ).join(
                    ZisConsultorio, ZisConsultorio.EspecialidadID == ZisEspecialidad.EspecialidadID
                ).join(
                    ZisTurno, and_(
                        ZisTurno.ConsultorioID == ZisConsultorio.ConsultorioID,
                        func.date(ZisTurno.Fecha_Hora) == hoy,
                        ZisTurno.Anulado == False,
                        ZisTurno.InstitucionID == int(hospital_id)
                    )
                ).filter(
                    ZisEspecialidad.Anulado == False
                ).group_by(
                    ZisEspecialidad.Nombre
                ).order_by(
                    desc('turnos_hoy')
                ).limit(15).all()

                especialidades_detalle = []
                for esp in especialidades_actividad:
                    # Determinar estado de ocupación
                    if esp.turnos_hoy > 20:
                        estado = "ALTA"
                    elif esp.turnos_hoy > 5:
                        estado = "MEDIA"
                    else:
                        estado = "BAJA"

                    especialidades_detalle.append({
                        "especialidad": esp.Nombre.strip(),
                        "turnos_hoy": esp.turnos_hoy,
                        "atendidos_hoy": esp.atendidos,
                        "en_atencion_ahora": esp.en_atencion,
                        "prestadores_disponibles": esp.prestadores,
                        "estado_ocupacion": estado
                    })

                return {
                    "resumen_operativo": {
                        "turnos_programados_hoy": turnos_hoy,
                        "pacientes_en_atencion_ahora": en_atencion_ahora,
                        "prestadores_activos_hoy": prestadores_hoy or 0,
                        "especialidades_operativas": len(especialidades_detalle),
                        "turnos_ultimas_24h": turnos_hoy  # Simplificado
                    },
                    "especialidades_detalle": especialidades_detalle,
                    "hospital_id": hospital_id,
                    "timestamp": ahora.strftime('%d/%m/%Y %H:%M:%S')
                }

        except Exception as e:
            logger.error(f"Error obteniendo dashboard operativo: {e}")
            return {"error": str(e)}

    # === FUNCIONALIDAD 10: BÚSQUEDA AVANZADA DE PACIENTES ===
    async def search_patients_advanced(
        self,
        criteria: Dict[str, Any],
        hospital_id: str,
        limit: int = 10
    ) -> List[Patient]:
        """Búsqueda avanzada de pacientes con múltiples criterios"""
        try:
            with self.zismed_db.get_session_context() as db:
                query = db.query(ZisPaciente).filter(
                    and_(
                        ZisPaciente.Anulado == False,
                        ZisPaciente.InstitucionID == int(hospital_id)
                    )
                )

                # Filtro por DNI
                if 'dni' in criteria:
                    query = query.filter(ZisPaciente.Documento == criteria['dni'])

                # Filtro por nombre
                if 'name' in criteria:
                    name_pattern = f"%{criteria['name'].upper()}%"
                    query = query.filter(
                        or_(
                            ZisPaciente.Nombre.like(name_pattern),
                            ZisPaciente.Apellido.like(name_pattern)
                        )
                    )

                # Filtro por teléfono
                if 'phone' in criteria:
                    query = query.filter(ZisPaciente.Telefono.like(f"%{criteria['phone']}%"))

                # Filtro por rango de edad
                if 'age_min' in criteria or 'age_max' in criteria:
                    today = date.today()
                    if 'age_max' in criteria:
                        fecha_min_nacimiento = today.replace(year=today.year - int(criteria['age_max']) - 1)
                        query = query.filter(ZisPaciente.FechadeNacimiento >= fecha_min_nacimiento)
                    if 'age_min' in criteria:
                        fecha_max_nacimiento = today.replace(year=today.year - int(criteria['age_min']))
                        query = query.filter(ZisPaciente.FechadeNacimiento <= fecha_max_nacimiento)

                pacientes = query.order_by(ZisPaciente.Nombre).limit(limit).all()

                result = []
                for p in pacientes:
                    # Calcular edad
                    edad = None
                    if p.FechadeNacimiento:
                        edad = today.year - p.FechadeNacimiento.year
                        if today.month < p.FechadeNacimiento.month or \
                           (today.month == p.FechadeNacimiento.month and today.day < p.FechadeNacimiento.day):
                            edad -= 1

                    # Contar turnos
                    turnos_count = db.query(ZisTurno).filter(
                        and_(
                            ZisTurno.PacienteID == p.PacienteID,
                            ZisTurno.Anulado == False
                        )
                    ).count()

                    result.append(Patient(
                        id=str(p.PacienteID),
                        dni=p.Documento.strip(),
                        name=f"{p.Nombre.strip()} {p.Apellido.strip() if p.Apellido else ''}".strip(),
                        phone=p.Telefono or "No registrado",
                        email=p.Correo or "No registrado",
                        metadata={
                            "age": edad,
                            "total_appointments": turnos_count,
                            "fecha_nacimiento": p.FechadeNacimiento.isoformat() if p.FechadeNacimiento else None
                        }
                    ))

                return result

        except Exception as e:
            logger.error(f"Error en búsqueda avanzada: {e}")
            return []

    # === FUNCIONES BASE OBLIGATORIAS ===
    async def get_hospitals(self) -> List[Hospital]:
        """Obtener hospitales (instituciones)"""
        # Esta función retorna las instituciones configuradas
        return [
            Hospital(
                id="3",
                name="Hospital Regional Santiago del Estero",
                address="Av. Belgrano, Santiago del Estero",
                phone="22323",
                active=True
            )
        ]

    async def create_appointment(self, appointment: Appointment) -> str:
        """Crear turno (no implementado por seguridad)"""
        raise NotImplementedError("Creación de turnos no habilitada desde chatbot")

    async def cancel_appointment(self, appointment_id: str, reason: str) -> bool:
        """Cancelar turno (no implementado por seguridad)"""
        raise NotImplementedError("Cancelación de turnos no habilitada desde chatbot")