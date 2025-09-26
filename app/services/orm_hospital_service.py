"""
Servicio ORM completo para reemplazar endpoints C#
Integración directa con base de datos usando SQLAlchemy
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy.orm import sessionmaker, joinedload, selectinload
from sqlalchemy import func, and_, or_, desc, text
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import db_connection
from app.models.schemas import ApiResponse
from app.database.models import (
    Paciente, Especialidad, Prestador, Institucion, Servicio,
    Sector, Habitacion, Cama, Internacion, Consultorio, Turno
)

logger = logging.getLogger(__name__)

class ORMHospitalService:
    """Servicio ORM completo para manejo hospitalario con IA"""

    def __init__(self):
        self.db = db_connection
        self.Session = sessionmaker(bind=self.db.engine)

    def get_session(self):
        """Obtener nueva sesión ORM"""
        return self.Session()

    async def test_connection(self) -> ApiResponse:
        """Probar conexión usando ORM"""
        try:
            session = self.get_session()
            try:
                count = session.query(Paciente).count()
                return ApiResponse(
                    success=True,
                    message="Conexión ORM exitosa",
                    data={"status": "connected", "total_pacientes": count}
                )
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error probando conexión ORM: {e}")
            return ApiResponse(success=False, error=str(e))

    # ===============================================
    # BÚSQUEDA DE PACIENTES - IA READY
    # ===============================================

    async def buscar_paciente_por_dni(self, dni: str, hospital_id: int = 3) -> ApiResponse:
        """Buscar paciente por DNI con datos completos para IA incluyendo internación vigente"""
        try:
            logger.info(f"🔍 Buscando paciente DNI {dni} (ORM)")

            session = self.get_session()
            try:
                # Query con joins para obtener datos completos
                paciente = session.query(Paciente)\
                    .filter(
                        and_(
                            Paciente.Documento == dni,
                            Paciente.Anulado == False
                        )
                    )\
                    .order_by(Paciente.PacienteID.desc())\
                    .first()

                if paciente:
                    # Construir datos estructurados para IA
                    obra_social_info = None
                    numero_obra_social = None

                    # Simplificado: usar solo ID de obra social
                    obra_social_info = paciente.ObraSocialID
                    numero_obra_social = None

                    # Buscar internación vigente (sin alta)
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
                            Internacion.Fecha_Alta.is_(None)  # Sin alta = internado
                        )
                    ).first()

                    # Datos de internación si existe
                    internacion_data = None
                    if internacion_vigente:
                        internacion_data = {
                            "internado": True,
                            "fecha_ingreso": internacion_vigente.Internacion.Fecha_ingreso.strftime('%d/%m/%Y') if internacion_vigente.Internacion.Fecha_ingreso else None,
                            "cama": internacion_vigente.nombre_cama,
                            "habitacion": internacion_vigente.habitacion,
                            "sector": internacion_vigente.sector,
                            "medico_responsable": internacion_vigente.medico_responsable,
                            "hora_ingreso": internacion_vigente.Internacion.Hora_Ingreso,
                            "dias_internado": (datetime.now().date() - internacion_vigente.Internacion.Fecha_ingreso).days if internacion_vigente.Internacion.Fecha_ingreso else 0
                        }

                    paciente_data = {
                        "paciente_id": paciente.PacienteID,
                        "nombre": paciente.Nombre,
                        "apellido": paciente.Apellido,
                        "nombre_completo": f"{paciente.Nombre} {paciente.Apellido}",
                        "documento": paciente.Documento,
                        "fecha_nacimiento": paciente.FechadeNacimiento.strftime('%Y-%m-%d') if paciente.FechadeNacimiento else None,
                        "edad": self._calcular_edad(paciente.FechadeNacimiento) if paciente.FechadeNacimiento else None,
                        "telefono": paciente.Telefono,
                        "email": "No disponible",  # Los pacientes no tienen email en el modelo
                        "direccion": None,  # Campo no disponible en el modelo
                        "obra_social": obra_social_info,
                        "numero_obra_social": numero_obra_social,
                        "sexo_id": paciente.IdSexo,
                        "anulado": paciente.Anulado,
                        "institucion_id": hospital_id,
                        "internacion_vigente": internacion_data
                    }

                    logger.info(f"✅ Paciente encontrado: {paciente_data['nombre_completo']}")

                    return ApiResponse(
                        success=True,
                        data=paciente_data,
                        message=f"Paciente encontrado: {paciente_data['nombre_completo']}"
                    )
                else:
                    logger.info(f"❌ No se encontró paciente con DNI {dni}")
                    return ApiResponse(
                        success=False,
                        message=f"No se encontró paciente con DNI {dni}",
                        error="Paciente no encontrado"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error buscando paciente por DNI {dni}: {e}")
            return ApiResponse(
                success=False,
                error=f"Error interno: {str(e)}"
            )

    async def buscar_pacientes_por_nombre(self, nombre: str, hospital_id: int = 3, limit: int = 5) -> ApiResponse:
        """Buscar pacientes por nombre para IA"""
        try:
            logger.info(f"🔍 Buscando pacientes por nombre: {nombre}")

            session = self.get_session()
            try:
                # Buscar por nombre o apellido
                pacientes = session.query(Paciente)\
\
                    .filter(
                        and_(
                            or_(
                                Paciente.Nombre.ilike(f'%{nombre}%'),
                                Paciente.Apellido.ilike(f'%{nombre}%')
                            ),
                            Paciente.Anulado == False
                        )
                    )\
                    .order_by(Paciente.Apellido, Paciente.Nombre)\
                    .limit(limit)\
                    .all()

                if pacientes:
                    pacientes_data = []
                    for p in pacientes:
                        pacientes_data.append({
                            "paciente_id": p.PacienteID,
                            "nombre_completo": f"{p.Nombre} {p.Apellido}",
                            "documento": p.Documento,
                            "telefono": p.Telefono,
                            "edad": self._calcular_edad(p.FechadeNacimiento) if p.FechadeNacimiento else None,
                            "sexo_id": p.IdSexo
                        })

                    return ApiResponse(
                        success=True,
                        data=pacientes_data,
                        message=f"Encontrados {len(pacientes_data)} pacientes con nombre '{nombre}'"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        message=f"No se encontraron pacientes con nombre '{nombre}'"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error buscando pacientes por nombre {nombre}: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    # ===============================================
    # ESPECIALIDADES - IA READY
    # ===============================================

    async def obtener_especialidades_con_prestadores(self, hospital_id: int = 3) -> ApiResponse:
        """Obtener especialidades con prestadores activos - Datos para IA"""
        try:
            logger.info(f"🏥 Obteniendo especialidades con prestadores para institución {hospital_id}")

            session = self.get_session()
            try:
                # Query optimizada con joins usando estructura real de BD
                especialidades_query = session.query(
                    Especialidad.EspecialidadID,
                    Especialidad.Nombre,
                    func.count(Prestador.PrestadorID).label('cantidad_prestadores')
                )\
                .join(Prestador, Especialidad.EspecialidadID == Prestador.EspecialidadID)\
                .filter(
                    and_(
                        Especialidad.Anulado == False,
                        Prestador.Anulado == False,
                        Prestador.InstitucionID == hospital_id  # Filtrado directo por institución
                    )
                )\
                .group_by(Especialidad.EspecialidadID, Especialidad.Nombre)\
                .having(func.count(Prestador.PrestadorID) > 0)\
                .order_by(Especialidad.Nombre)\
                .all()

                if especialidades_query:
                    especialidades = []

                    for esp_id, esp_nombre, cantidad in especialidades_query:
                        # Obtener prestadores de esta especialidad usando estructura real
                        prestadores = session.query(Prestador)\
                            .filter(
                                and_(
                                    Prestador.EspecialidadID == esp_id,
                                    Prestador.Anulado == False,
                                    Prestador.InstitucionID == hospital_id  # Filtrado directo
                                )
                            ).all()

                        prestadores_lista = []
                        for p in prestadores:
                            prestadores_lista.append({
                                "prestador_id": p.PrestadorID,
                                "nombre_completo": p.Nombre.strip() if p.Nombre else "Sin nombre",
                                "matricula": p.Matricula.strip() if p.Matricula else "Sin matrícula",
                                "telefono": p.Telefono.strip() if p.Telefono else "Sin teléfono",
                                "email": p.Email.strip() if p.Email else "Sin email"
                            })

                        especialidades.append({
                            "especialidad_id": esp_id,
                            "nombre": esp_nombre,
                            "cantidad_prestadores": cantidad,
                            "prestadores": prestadores_lista,
                            "institucion_id": hospital_id
                        })

                    logger.info(f"✅ Encontradas {len(especialidades)} especialidades con prestadores")

                    return ApiResponse(
                        success=True,
                        data=especialidades,
                        message=f"Encontradas {len(especialidades)} especialidades con prestadores activos"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        error="No se encontraron especialidades con prestadores activos"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo especialidades: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    # ===============================================
    # SERVICIOS HOSPITALARIOS - IA READY
    # ===============================================

    async def obtener_servicios_hospital(self, hospital_id: int = 3, limit: int = None) -> ApiResponse:
        """Obtener servicios del hospital filtrados por institución"""
        try:
            logger.info(f"🏥 Obteniendo servicios del hospital {hospital_id}")

            session = self.get_session()
            try:
                servicios_query = session.query(Servicio)\
                .filter(
                    and_(
                        Servicio.Anulado == False,
                        Servicio.InstitucionID == hospital_id
                    )
                )\
                .order_by(Servicio.Nombre)

                # Aplicar limit solo si se especifica
                if limit:
                    servicios_query = servicios_query.limit(limit)

                servicios_query = servicios_query.all()

                if servicios_query:
                    servicios = []

                    for servicio in servicios_query:
                        servicios.append({
                            "servicio_id": servicio.ServicioID,
                            "nombre": servicio.Nombre.strip() if servicio.Nombre else "",
                            "activo": not servicio.Anulado,
                            "institucion_id": servicio.InstitucionID
                        })

                    return ApiResponse(
                        success=True,
                        data=servicios,
                        message=f"Encontrados {len(servicios)} servicios del hospital"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        error="No se encontraron servicios en el hospital"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo servicios: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    # ===============================================
    # PRESTADORES - IA READY
    # ===============================================

    async def obtener_prestadores_por_institucion(self, hospital_id: int = 3, limit: int = 50) -> ApiResponse:
        """Obtener prestadores activos de una institución"""
        try:
            logger.info(f"👨‍⚕️ Obteniendo prestadores de institución {hospital_id}")

            session = self.get_session()
            try:
                prestadores = session.query(Prestador)\
                    .options(
                        joinedload(Prestador.especialidad),
                        joinedload(Prestador.institucion)
                    )\
                    .filter(
                        and_(
                            Prestador.Anulado == False,
                            Prestador.InstitucionID == hospital_id
                        )
                    )\
                    .order_by(Prestador.Apellido, Prestador.Nombre)\
                    .limit(limit)\
                    .all()

                if prestadores:
                    prestadores_data = []

                    for prestador in prestadores:
                        # Buscar relación con la institución específica
                        institucion_rel = None
                        for inst_rel in prestador.instituciones:
                            if inst_rel.InstitucionID == hospital_id:
                                institucion_rel = inst_rel
                                break

                        prestadores_data.append({
                            "prestador_id": prestador.PrestadorID,
                            "nombre_completo": f"{prestador.Nombre} {prestador.Apellido}",
                            "documento": prestador.Documento,
                            "especialidad": prestador.especialidad.Nombre if prestador.especialidad else None,
                            "servicio": prestador.servicio.Nombre if prestador.servicio else None,
                            "matricula": prestador.Matricula,
                            "telefono": prestador.Telefono,
                            "email": prestador.Email,
                            "fecha_inicio": institucion_rel.FechaInicio.strftime('%Y-%m-%d') if institucion_rel and institucion_rel.FechaInicio else None,
                            "activo": institucion_rel.Activo if institucion_rel else False,
                            "institucion_id": hospital_id
                        })

                    return ApiResponse(
                        success=True,
                        data=prestadores_data,
                        message=f"Encontrados {len(prestadores_data)} prestadores activos"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        error="No se encontraron prestadores activos"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo prestadores: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    # ===============================================
    # ESTADÍSTICAS Y MÉTRICAS - IA READY
    # ===============================================

    async def obtener_estadisticas_hospital(self, hospital_id: int = 3) -> ApiResponse:
        """Obtener estadísticas completas del hospital para IA"""
        try:
            logger.info(f"📊 Obteniendo estadísticas del hospital {hospital_id}")

            session = self.get_session()
            try:
                # Contar entidades principales
                total_pacientes = session.query(Paciente).filter(Paciente.Anulado == False).count()

                total_prestadores = session.query(Prestador)\
                    .filter(
                        and_(
                            Prestador.Anulado == False,
                            Prestador.InstitucionID == hospital_id
                        )
                    ).count()

                total_especialidades = session.query(Especialidad)\
                    .join(Prestador)\
                    .filter(
                        and_(
                            Especialidad.Anulado == False,
                            Prestador.Anulado == False,
                            Prestador.InstitucionID == hospital_id
                        )
                    ).distinct().count()

                total_servicios = session.query(Servicio)\
                    .join(ServicioHospital)\
                    .filter(
                        and_(
                            Servicio.Anulado == False,
                            ServicioHospital.HospitalID == hospital_id,
                            ServicioHospital.Activo == True
                        )
                    ).count()

                # Especialidades más demandadas (simulado por cantidad de prestadores)
                especialidades_top = session.query(
                    Especialidad.Nombre,
                    func.count(Prestador.PrestadorID).label('cantidad_prestadores')
                )\
                .join(Prestador)\
                .filter(
                    and_(
                        Especialidad.Anulado == False,
                        Prestador.Anulado == False,
                        Prestador.InstitucionID == hospital_id,
                        Prestador.Activo == True
                    )
                )\
                .group_by(Especialidad.EspecialidadID, Especialidad.Nombre)\
                .order_by(desc('cantidad_prestadores'))\
                .limit(5)\
                .all()

                estadisticas = {
                    "hospital_id": hospital_id,
                    "fecha_reporte": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "totales": {
                        "pacientes": total_pacientes,
                        "prestadores": total_prestadores,
                        "especialidades": total_especialidades,
                        "servicios": total_servicios
                    },
                    "especialidades_top": [
                        {
                            "nombre": esp_nombre,
                            "cantidad_prestadores": cantidad
                        }
                        for esp_nombre, cantidad in especialidades_top
                    ]
                }

                return ApiResponse(
                    success=True,
                    data=estadisticas,
                    message="Estadísticas del hospital obtenidas exitosamente"
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    # ===============================================
    # MÉTODOS AUXILIARES
    # ===============================================

    def _calcular_edad(self, fecha_nacimiento: date) -> int:
        """Calcular edad a partir de fecha de nacimiento"""
        if not fecha_nacimiento:
            return None

        today = date.today()
        return today.year - fecha_nacimiento.year - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

    async def buscar_por_dni_multiple(self, dnis: List[str], hospital_id: int = 3) -> ApiResponse:
        """Buscar múltiples pacientes por DNI - Útil para IA batch processing"""
        try:
            session = self.get_session()
            try:
                pacientes = session.query(Paciente)\
\
                    .filter(
                        and_(
                            Paciente.Documento.in_(dnis),
                            Paciente.Anulado == False
                        )
                    ).all()

                pacientes_data = []
                for p in pacientes:
                    pacientes_data.append({
                        "paciente_id": p.PacienteID,
                        "nombre_completo": f"{p.Nombre} {p.Apellido}",
                        "documento": p.Documento,
                        "edad": self._calcular_edad(p.FechadeNacimiento) if p.FechadeNacimiento else None,
                        "sexo_id": p.IdSexo
                    })

                return ApiResponse(
                    success=True,
                    data=pacientes_data,
                    message=f"Encontrados {len(pacientes_data)} pacientes de {len(dnis)} solicitados"
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error en búsqueda múltiple: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    # ===============================================
    # DISPONIBILIDAD DE CAMAS - IA READY
    # ===============================================

    async def obtener_disponibilidad_camas(self, hospital_id: int = 3) -> ApiResponse:
        """Obtener disponibilidad de camas por sector y habitación"""
        try:
            logger.info(f"🛏️ Obteniendo disponibilidad de camas para institución {hospital_id}")

            session = self.get_session()
            try:
                # Query completa con joins para obtener disponibilidad
                camas_query = session.query(
                    Cama.CamaId,
                    Cama.Nombre.label('cama_nombre'),
                    Habitacion.Nombre.label('habitacion_nombre'),
                    Sector.Nombre.label('sector_nombre'),
                    Cama.En_mantenimiento,
                    Cama.Habilitada,
                    Cama.TieneOxigeno,
                    Cama.TipoCamaID,
                    # Verificar ocupación actual
                    func.count(Internacion.InternacionID).label('ocupada')
                )\
                .join(Habitacion, Cama.HabitacionID == Habitacion.HabitacionID)\
                .join(Sector, Habitacion.SectorID == Sector.SectorId)\
                .outerjoin(
                    Internacion,
                    and_(
                        Cama.CamaId == Internacion.CamaID,
                        Internacion.Fecha_Alta == None,  # Sin fecha de alta = ocupada
                        Internacion.Anulado == False
                    )
                )\
                .filter(
                    and_(
                        Cama.InstitucionID == hospital_id,
                        Cama.Anulado == False,
                        Habitacion.Anulado == False,
                        Sector.Anulado == False
                        # Solo filtrar por InstitucionID de cama para incluir toda la capacidad
                        # Las inconsistencias de InstitucionID en habitaciones/sectores
                        # no deben limitar la capacidad reportada del hospital
                    )
                )\
                .group_by(
                    Cama.CamaId, Cama.Nombre, Habitacion.Nombre,
                    Sector.Nombre, Cama.En_mantenimiento, Cama.Habilitada,
                    Cama.TieneOxigeno, Cama.TipoCamaID
                )\
                .order_by(Sector.Nombre, Habitacion.Nombre, Cama.Nombre)\
                .all()

                if camas_query:
                    # Organizar por sector
                    sectores = {}

                    for row in camas_query:
                        sector_nombre = row.sector_nombre

                        if sector_nombre not in sectores:
                            sectores[sector_nombre] = {
                                "sector_nombre": sector_nombre,
                                "total_camas": 0,
                                "camas_disponibles": 0,
                                "camas_ocupadas": 0,
                                "camas_mantenimiento": 0,
                                "habitaciones": {}
                            }

                        habitacion_nombre = row.habitacion_nombre
                        if habitacion_nombre not in sectores[sector_nombre]["habitaciones"]:
                            sectores[sector_nombre]["habitaciones"][habitacion_nombre] = {
                                "habitacion_nombre": habitacion_nombre,
                                "camas": []
                            }

                        # Determinar estado de la cama
                        ocupada = row.ocupada > 0
                        en_mantenimiento = row.En_mantenimiento
                        habilitada = row.Habilitada

                        estado = "ocupada" if ocupada else ("mantenimiento" if en_mantenimiento else ("disponible" if habilitada else "no_habilitada"))

                        cama_info = {
                            "cama_id": row.CamaId,
                            "nombre": row.cama_nombre,
                            "estado": estado,
                            "ocupada": ocupada,
                            "en_mantenimiento": en_mantenimiento,
                            "habilitada": habilitada,
                            "tiene_oxigeno": row.TieneOxigeno,
                            "tipo_cama_id": row.TipoCamaID
                        }

                        sectores[sector_nombre]["habitaciones"][habitacion_nombre]["camas"].append(cama_info)

                        # Actualizar contadores del sector
                        sectores[sector_nombre]["total_camas"] += 1
                        if estado == "disponible":
                            sectores[sector_nombre]["camas_disponibles"] += 1
                        elif estado == "ocupada":
                            sectores[sector_nombre]["camas_ocupadas"] += 1
                        elif estado == "mantenimiento":
                            sectores[sector_nombre]["camas_mantenimiento"] += 1

                    # Convertir a lista y calcular resumen
                    sectores_lista = list(sectores.values())

                    total_camas = sum(s["total_camas"] for s in sectores_lista)
                    total_disponibles = sum(s["camas_disponibles"] for s in sectores_lista)
                    total_ocupadas = sum(s["camas_ocupadas"] for s in sectores_lista)

                    # DEBUG: Log para ver los números reales
                    logger.info(f"🔍 DEBUG CAMAS - Hospital {hospital_id}:")
                    logger.info(f"   Total camas encontradas: {total_camas}")
                    logger.info(f"   Disponibles: {total_disponibles}")
                    logger.info(f"   Ocupadas: {total_ocupadas}")
                    logger.info(f"   Sectores: {len(sectores_lista)}")
                    if total_camas > 1000:
                        logger.warning(f"⚠️ NÚMERO ALTO: {total_camas} camas para hospital {hospital_id}")
                        logger.info(f"   Sectores más grandes: {[(s['sector_nombre'][:30], s['total_camas']) for s in sorted(sectores_lista, key=lambda x: x['total_camas'], reverse=True)[:5]]}")

                    # Si es muy alto, aplicar un filtro adicional temporal
                    if total_camas > 800:
                        logger.info("🔧 Aplicando filtro adicional por número alto...")
                        # Filtrar solo sectores principales del hospital (expandido)
                        sectores_principales = [
                            "UTI", "MEDICINA", "CIRUGIA", "PEDIATRIA", "GINECOLOGIA",
                            "EMERGENCIAS", "TRAUMATOLOGIA", "CARDIOLOGIA", "INTERNACION",
                            "GUARDIA", "PISO", "SALA", "CUIDADOS", "MATERNIDAD",
                            "NEONATOLOGIA", "RESPIRATORIO", "ONCOLOGIA",
                            "ADMINISTRACION", "PLANTA", "PISO"
                        ]
                        sectores_filtrados = [
                            s for s in sectores_lista
                            if any(principal.lower() in s["sector_nombre"].lower()
                                   for principal in sectores_principales)
                        ]

                        if sectores_filtrados and len(sectores_filtrados) > 3:
                            logger.info(f"🎯 Usando solo sectores principales: {len(sectores_filtrados)} sectores")
                            sectores_lista = sectores_filtrados
                            total_camas = sum(s["total_camas"] for s in sectores_lista)
                            total_disponibles = sum(s["camas_disponibles"] for s in sectores_lista)
                            total_ocupadas = sum(s["camas_ocupadas"] for s in sectores_lista)
                            logger.info(f"   Total filtrado: {total_camas} camas")
                    total_mantenimiento = sum(s["camas_mantenimiento"] for s in sectores_lista)

                    resultado = {
                        "institucion_id": hospital_id,
                        "fecha_consulta": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "resumen": {
                            "total_camas": total_camas,
                            "camas_disponibles": total_disponibles,
                            "camas_ocupadas": total_ocupadas,
                            "camas_mantenimiento": total_mantenimiento,
                            "porcentaje_ocupacion": round((total_ocupadas / total_camas * 100), 2) if total_camas > 0 else 0
                        },
                        "sectores": sectores_lista
                    }

                    return ApiResponse(
                        success=True,
                        data=resultado,
                        message=f"Disponibilidad de camas obtenida: {total_disponibles}/{total_camas} disponibles"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        error="No se encontraron camas en la institución"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo disponibilidad de camas: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    # ===============================================
    # GESTIÓN DE TURNOS - IA READY
    # ===============================================

    async def obtener_turnos_por_fecha(self, fecha: date, hospital_id: int = 3, limit: int = 100) -> ApiResponse:
        """Obtener turnos para una fecha específica"""
        try:
            logger.info(f"📅 Obteniendo turnos para fecha {fecha} en institución {hospital_id}")

            session = self.get_session()
            try:
                # Query con joins para datos completos
                turnos_query = session.query(Turno)\
                .options(
                    joinedload(Turno.paciente),
                    joinedload(Turno.prestador),
                    joinedload(Turno.consultorio).joinedload(Consultorio.especialidad),
                    joinedload(Turno.servicio)
                )\
                .filter(
                    and_(
                        func.date(Turno.Fecha_Hora) == fecha,
                        Turno.InstitucionID == hospital_id,
                        Turno.Anulado == False
                    )
                )\
                .order_by(Turno.Fecha_Hora, Turno.Orden)\
                .limit(limit)\
                .all()

                if turnos_query:
                    turnos_data = []

                    for turno in turnos_query:
                        # Determinar estado del turno
                        estado = "programado"
                        if turno.NoAtendido:
                            estado = "no_atendido"
                        elif turno.Atendido:
                            estado = "atendido"
                        elif turno.Llamado:
                            estado = "llamado"
                        elif turno.Llegada:
                            estado = "presente"

                        turno_info = {
                            "turno_id": turno.TurnoID,
                            "fecha_hora": turno.Fecha_Hora.strftime('%Y-%m-%d %H:%M') if turno.Fecha_Hora else None,
                            "hora_hasta": turno.Hora_Hasta,
                            "orden": turno.Orden,
                            "estado": estado,
                            "emergencia": turno.Emergencia,
                            "primera_vez": turno.Primeravez,
                            "telesalud": turno.TeleSalud,
                            "admisionado": turno.Admisionado,
                            "paciente": {
                                "paciente_id": turno.paciente.PacienteID if turno.paciente else None,
                                "nombre_completo": f"{turno.paciente.Nombre} {turno.paciente.Apellido}" if turno.paciente else "Sin paciente",
                                "documento": turno.paciente.Documento if turno.paciente else None,
                                "edad": turno.Edad if turno.Edad else (self._calcular_edad(turno.paciente.FechadeNacimiento) if turno.paciente and turno.paciente.FechadeNacimiento else None)
                            },
                            "prestador": {
                                "prestador_id": turno.prestador.PrestadorID if turno.prestador else None,
                                "nombre": turno.prestador.Nombre if turno.prestador else "Sin prestador",
                                "matricula": turno.prestador.Matricula if turno.prestador else None
                            },
                            "consultorio": {
                                "consultorio_id": turno.consultorio.ConsultorioID if turno.consultorio else None,
                                "nombre": turno.consultorio.Nombre if turno.consultorio else "Sin consultorio",
                                "especialidad": turno.consultorio.especialidad.Nombre if turno.consultorio and turno.consultorio.especialidad else "Sin especialidad"
                            },
                            "servicio": {
                                "servicio_id": turno.servicio.ServicioID if turno.servicio else None,
                                "nombre": turno.servicio.Nombre if turno.servicio else "Sin servicio"
                            },
                            "horarios": {
                                "llegada": turno.Llegada.strftime('%H:%M') if turno.Llegada else None,
                                "llamado": turno.Llamado.strftime('%H:%M') if turno.Llamado else None,
                                "atendido": turno.Atendido.strftime('%H:%M') if turno.Atendido else None,
                                "no_atendido": turno.NoAtendido.strftime('%H:%M') if turno.NoAtendido else None
                            }
                        }

                        turnos_data.append(turno_info)

                    # Estadísticas del día
                    total_turnos = len(turnos_data)
                    turnos_atendidos = len([t for t in turnos_data if t["estado"] == "atendido"])
                    turnos_pendientes = len([t for t in turnos_data if t["estado"] in ["programado", "presente", "llamado"]])
                    turnos_no_atendidos = len([t for t in turnos_data if t["estado"] == "no_atendido"])
                    emergencias = len([t for t in turnos_data if t["emergencia"]])

                    resultado = {
                        "fecha": fecha.strftime('%Y-%m-%d'),
                        "institucion_id": hospital_id,
                        "estadisticas": {
                            "total_turnos": total_turnos,
                            "atendidos": turnos_atendidos,
                            "pendientes": turnos_pendientes,
                            "no_atendidos": turnos_no_atendidos,
                            "emergencias": emergencias
                        },
                        "turnos": turnos_data
                    }

                    return ApiResponse(
                        success=True,
                        data=resultado,
                        message=f"Encontrados {total_turnos} turnos para {fecha.strftime('%Y-%m-%d')}"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        message=f"No se encontraron turnos para la fecha {fecha.strftime('%Y-%m-%d')}"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo turnos por fecha: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    async def obtener_turnos_rango_fechas(self, fecha_inicio: date, fecha_fin: date, hospital_id: int = 3, limit: int = 500) -> ApiResponse:
        """Obtener turnos en un rango de fechas"""
        try:
            logger.info(f"📅 Obteniendo turnos desde {fecha_inicio} hasta {fecha_fin} en institución {hospital_id}")

            session = self.get_session()
            try:
                turnos_query = session.query(Turno)\
                .options(
                    joinedload(Turno.paciente),
                    joinedload(Turno.prestador),
                    joinedload(Turno.consultorio).joinedload(Consultorio.especialidad)
                )\
                .filter(
                    and_(
                        func.date(Turno.Fecha_Hora) >= fecha_inicio,
                        func.date(Turno.Fecha_Hora) <= fecha_fin,
                        Turno.InstitucionID == hospital_id,
                        Turno.Anulado == False
                    )
                )\
                .order_by(Turno.Fecha_Hora)\
                .limit(limit)\
                .all()

                if turnos_query:
                    # Agrupar por fecha
                    turnos_por_fecha = {}

                    for turno in turnos_query:
                        fecha_str = turno.Fecha_Hora.strftime('%Y-%m-%d')

                        if fecha_str not in turnos_por_fecha:
                            turnos_por_fecha[fecha_str] = {
                                "fecha": fecha_str,
                                "total_turnos": 0,
                                "turnos": []
                            }

                        # Determinar estado
                        estado = "programado"
                        if turno.NoAtendido:
                            estado = "no_atendido"
                        elif turno.Atendido:
                            estado = "atendido"
                        elif turno.Llamado:
                            estado = "llamado"
                        elif turno.Llegada:
                            estado = "presente"

                        turno_info = {
                            "turno_id": turno.TurnoID,
                            "hora": turno.Fecha_Hora.strftime('%H:%M'),
                            "estado": estado,
                            "paciente": f"{turno.paciente.Nombre} {turno.paciente.Apellido}" if turno.paciente else "Sin paciente",
                            "prestador": turno.prestador.Nombre if turno.prestador else "Sin prestador",
                            "consultorio": turno.consultorio.Nombre if turno.consultorio else "Sin consultorio",
                            "especialidad": turno.consultorio.especialidad.Nombre if turno.consultorio and turno.consultorio.especialidad else "Sin especialidad",
                            "emergencia": turno.Emergencia
                        }

                        turnos_por_fecha[fecha_str]["turnos"].append(turno_info)
                        turnos_por_fecha[fecha_str]["total_turnos"] += 1

                    # Convertir a lista ordenada
                    fechas_lista = sorted(turnos_por_fecha.values(), key=lambda x: x["fecha"])

                    # Estadísticas generales
                    total_turnos = sum(f["total_turnos"] for f in fechas_lista)

                    resultado = {
                        "fecha_inicio": fecha_inicio.strftime('%Y-%m-%d'),
                        "fecha_fin": fecha_fin.strftime('%Y-%m-%d'),
                        "institucion_id": hospital_id,
                        "total_turnos": total_turnos,
                        "fechas_con_turnos": len(fechas_lista),
                        "fechas": fechas_lista
                    }

                    return ApiResponse(
                        success=True,
                        data=resultado,
                        message=f"Encontrados {total_turnos} turnos en el rango de fechas"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        message=f"No se encontraron turnos en el rango {fecha_inicio} - {fecha_fin}"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo turnos por rango: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    async def obtener_turnos_hoy(self, hospital_id: int = 3) -> ApiResponse:
        """Obtener turnos de hoy"""
        hoy = date.today()
        return await self.obtener_turnos_por_fecha(hoy, hospital_id)

    async def obtener_disponibilidad_prestadores(self, especialidad: str = None, hospital_id: int = 3) -> ApiResponse:
        """Obtener prestadores disponibles por especialidad"""
        try:
            logger.info(f"👨‍⚕️ Obteniendo prestadores disponibles para especialidad: {especialidad}")

            session = self.get_session()
            try:
                query = session.query(Prestador)\
                    .join(Especialidad)\
                    .filter(
                        and_(
                            Prestador.Anulado == False,
                            Prestador.InstitucionID == hospital_id
                        )
                    )

                if especialidad:
                    query = query.filter(Especialidad.Nombre.ilike(f'%{especialidad}%'))

                prestadores = query.order_by(Prestador.Nombre).limit(20).all()

                if prestadores:
                    prestadores_data = []
                    for p in prestadores:
                        prestadores_data.append({
                            "prestador_id": p.PrestadorID,
                            "nombre": p.Nombre,
                            "matricula": p.Matricula,
                            "telefono": p.Telefono,
                            "especialidad": especialidad if especialidad else "Múltiples"
                        })

                    return ApiResponse(
                        success=True,
                        data=prestadores_data,
                        message=f"Encontrados {len(prestadores_data)} prestadores para {especialidad if especialidad else 'todas las especialidades'}"
                    )
                else:
                    return ApiResponse(
                        success=False,
                        message=f"No se encontraron prestadores para {especialidad if especialidad else 'las especialidades solicitadas'}"
                    )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo prestadores disponibles: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    async def obtener_metricas_completas(self, hospital_id: int = 3) -> ApiResponse:
        """Obtener métricas completas del hospital para estadísticas"""
        try:
            logger.info(f"📊 Obteniendo métricas completas para institución {hospital_id}")

            session = self.get_session()
            try:
                # Métricas básicas
                total_pacientes = session.query(Paciente).filter(Paciente.Anulado == False).count()

                total_prestadores = session.query(Prestador)\
                    .filter(
                        and_(
                            Prestador.Anulado == False,
                            Prestador.InstitucionID == hospital_id
                        )
                    ).count()

                total_especialidades = session.query(Especialidad)\
                    .join(Prestador)\
                    .filter(
                        and_(
                            Especialidad.Anulado == False,
                            Prestador.Anulado == False,
                            Prestador.InstitucionID == hospital_id
                        )
                    ).distinct().count()

                # Turnos de hoy
                hoy = date.today()
                turnos_hoy = session.query(Turno)\
                    .filter(
                        and_(
                            func.date(Turno.Fecha_Hora) == hoy,
                            Turno.InstitucionID == hospital_id,
                            Turno.Anulado == False
                        )
                    ).count()

                turnos_atendidos_hoy = session.query(Turno)\
                    .filter(
                        and_(
                            func.date(Turno.Fecha_Hora) == hoy,
                            Turno.InstitucionID == hospital_id,
                            Turno.Anulado == False,
                            Turno.Atendido.isnot(None)
                        )
                    ).count()

                # Camas
                total_camas = session.query(Cama)\
                    .join(Habitacion)\
                    .join(Sector)\
                    .filter(
                        and_(
                            Sector.InstitucionID == hospital_id,
                            Cama.Anulado == False
                        )
                    ).count()

                camas_ocupadas = session.query(Cama)\
                    .join(Habitacion)\
                    .join(Sector)\
                    .filter(
                        and_(
                            Sector.InstitucionID == hospital_id,
                            Cama.Anulado == False,
                            Cama.Disponible == False
                        )
                    ).count()

                metricas = {
                    "hospital_id": hospital_id,
                    "fecha_reporte": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "resumen_general": {
                        "total_pacientes": total_pacientes,
                        "total_prestadores": total_prestadores,
                        "total_especialidades": total_especialidades
                    },
                    "actividad_hoy": {
                        "fecha": hoy.strftime('%Y-%m-%d'),
                        "turnos_programados": turnos_hoy,
                        "turnos_atendidos": turnos_atendidos_hoy,
                        "turnos_pendientes": turnos_hoy - turnos_atendidos_hoy
                    },
                    "ocupacion_camas": {
                        "total_camas": total_camas,
                        "camas_ocupadas": camas_ocupadas,
                        "camas_disponibles": total_camas - camas_ocupadas,
                        "porcentaje_ocupacion": round((camas_ocupadas / total_camas * 100) if total_camas > 0 else 0, 2)
                    }
                }

                return ApiResponse(
                    success=True,
                    data=metricas,
                    message="Métricas completas del hospital obtenidas exitosamente"
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas completas: {e}")
            return ApiResponse(success=False, error=f"Error interno: {str(e)}")

    async def validate_credentials_and_get_institutions(self, cuil: str, password: str) -> dict:
        """
        Validate credentials and return available institutions
        For now, returns hardcoded data - should be replaced with real validation
        """
        try:
            # Hardcoded validation for testing - replace with real implementation
            if cuil == "27357388827" and password == "simon0":
                return {
                    "success": True,
                    "message": "Credenciales válidas",
                    "institutions": [
                        {
                            "id": 3,
                            "name": "Hospital Regional Santiago del Estero",
                            "requires_terms": False,
                            "address": "Santiago del Estero",
                            "phone": "4212121"
                        }
                    ]
                }
            else:
                return {
                    "success": False,
                    "error": "Credenciales incorrectas"
                }
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            return {
                "success": False,
                "error": "Error interno del servidor"
            }


# Instancia global del servicio ORM
orm_hospital_service = ORMHospitalService()