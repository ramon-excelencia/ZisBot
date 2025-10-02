from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, JSON, SmallInteger, Date, Numeric, CHAR
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

# Base para modelos ZisMed (SQL Server)
ZisMedBase = declarative_base()

# === MODELOS ZISMED REALES (SQL Server) ===

class ZisTurno(ZisMedBase):
    """Modelo real de tabla Turnos de ZisMed"""
    __tablename__ = "Turnos"

    TurnoID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, nullable=False, index=True)
    ServicioID = Column(Integer, nullable=False)
    ConsultorioID = Column(Integer, nullable=False)
    PrestadorID = Column(Integer, nullable=False, index=True)
    Fecha_Hora = Column(DateTime, nullable=False, index=True)
    Hora_Hasta = Column(CHAR(4), nullable=False)
    Orden = Column(CHAR(2), nullable=True)
    Llegada = Column(DateTime, nullable=True)
    Llamado = Column(DateTime, nullable=True)
    Atendido = Column(DateTime, nullable=True)
    NoAtendido = Column(DateTime, nullable=True)
    Primeravez = Column(Boolean, nullable=True)
    ObraSocialID = Column(Integer, nullable=True)
    Emergencia = Column(Boolean, nullable=True)
    Admisionado = Column(Boolean, nullable=False, default=False)
    Edad = Column(SmallInteger, nullable=True)
    OpCrea = Column(CHAR(11), nullable=True)
    OpModifica = Column(CHAR(11), nullable=True)
    FecModifica = Column(DateTime, nullable=True)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)
    FechaCrea = Column(DateTime, nullable=True, default=func.getdate())
    InstitucionID = Column(Integer, nullable=True, index=True)

class ZisPaciente(ZisMedBase):
    """Modelo real de tabla Pacientes de ZisMed"""
    __tablename__ = "Pacientes"

    PacienteID = Column(Integer, primary_key=True)
    Cuil = Column(CHAR(11), nullable=True)
    IdTipoDocumento = Column(Integer, nullable=False, default=0)
    Documento = Column(CHAR(50), nullable=False, index=True)
    Nombre = Column(CHAR(100), nullable=False, index=True)
    Apellido = Column(CHAR(50), nullable=True)
    ObraSocialID = Column(Integer, nullable=True, default=0)
    IdSexo = Column(SmallInteger, nullable=True)
    FechadeNacimiento = Column(Date, nullable=True)
    Telefono = Column(String(20), nullable=True)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)
    FechaCarga = Column(DateTime, nullable=True, default=func.getdate())
    UsuarioCarga = Column(CHAR(11), nullable=True)
    Correo = Column(String(200), nullable=True)
    InstitucionID = Column(Integer, nullable=True, index=True)

class ZisEspecialidad(ZisMedBase):
    """Modelo real de tabla Especialidades de ZisMed"""
    __tablename__ = "Especialidades"

    EspecialidadID = Column(Integer, primary_key=True)
    Nombre = Column(CHAR(50), nullable=False, index=True)
    Grilla = Column(Boolean, nullable=False)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)

class ZisConsultorio(ZisMedBase):
    """Modelo real de tabla Consultorios de ZisMed"""
    __tablename__ = "Consultorios"

    ConsultorioID = Column(Integer, primary_key=True)
    Nombre = Column(CHAR(50), nullable=False, index=True)
    EspecialidadID = Column(Integer, nullable=True)
    TvMonitorID = Column(Integer, nullable=False)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)
    InstitucionID = Column(Integer, nullable=True, index=True)

class ZisLaboratorioRegistro(ZisMedBase):
    """Modelo real de tabla LaboratorioRegistro de ZisMed"""
    __tablename__ = "LaboratorioRegistro"

    LaboratorioRegistroID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, nullable=False, index=True)
    TurnoID = Column(Integer, nullable=True)
    PracticasOrigenID = Column(Integer, nullable=False)
    PracticasEstadoID = Column(Integer, nullable=False)
    Urgente = Column(Boolean, nullable=False)
    NumeroIdentificador = Column(Integer, nullable=False)
    PrestadorSolicita = Column(Integer, nullable=True)
    PrestadorRealiza = Column(Integer, nullable=True)
    Fecha = Column(DateTime, nullable=False, index=True)
    Anulado = Column(Boolean, nullable=False, index=True)
    InstitucionID = Column(Integer, nullable=True, index=True)

class ZisCama(ZisMedBase):
    """Modelo real de tabla Camas de ZisMed"""
    __tablename__ = "Camas"

    CamaId = Column(Integer, primary_key=True)
    Nombre = Column(CHAR(100), nullable=False)
    HabitacionID = Column(Integer, nullable=False, index=True)
    En_mantenimiento = Column(Boolean, nullable=False, default=False)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)
    InstitucionID = Column(Integer, nullable=True, index=True)
    TieneOxigeno = Column(Boolean, nullable=True)
    Habilitada = Column(Boolean, nullable=True)

class ZisInternacion(ZisMedBase):
    """Modelo real de tabla Internaciones de ZisMed"""
    __tablename__ = "Internaciones"

    InternacionID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, nullable=False, index=True)
    HabitacionID = Column(Integer, nullable=False)
    CamaID = Column(Integer, nullable=False, index=True)
    ObraSocialID = Column(Integer, nullable=False)
    Fecha_ingreso = Column(Date, nullable=False, index=True)
    Fecha_Alta = Column(Date, nullable=True, index=True)
    PrestadorIngresoID = Column(Integer, nullable=False)
    PrestadorAltaID = Column(Integer, nullable=True)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)
    InstitucionID = Column(Integer, nullable=True, index=True)

class ZisFarmaciaArticulo(ZisMedBase):
    """Modelo real de tabla FarmaciaArticulo de ZisMed"""
    __tablename__ = "FarmaciaArticulo"

    FarmaciaArticuloID = Column(Integer, primary_key=True)
    CodigoArticulo = Column(CHAR(12), nullable=True)
    Nombre = Column(String(100), nullable=False, index=True)
    Presentacion = Column(String(100), nullable=True)
    CodigoBarras = Column(CHAR(13), nullable=True)
    StockMinimo = Column(Numeric, nullable=False, default=0)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)
    FechaCrea = Column(DateTime, nullable=False)

class ZisServicio(ZisMedBase):
    """Modelo real de tabla Servicios de ZisMed - Columnas esenciales"""
    __tablename__ = "Servicios"

    ServicioID = Column(Integer, primary_key=True)
    Nombre = Column(CHAR(50), nullable=False, index=True)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)

class ZisDia(ZisMedBase):
    """Modelo real de tabla Dias de ZisMed"""
    __tablename__ = "Dias"

    DiaID = Column(Integer, primary_key=True)
    Nombre = Column(CHAR(15), nullable=False, index=True)

class ZisServicioDias(ZisMedBase):
    """Modelo real de tabla ServiciosDias de ZisMed"""
    __tablename__ = "ServiciosDias"

    ServiociosDiasID = Column(Integer, primary_key=True)  # Nota: tiene error de tipeo en la BD
    ServicioID = Column(Integer, nullable=False, index=True)
    DiaID = Column(Integer, nullable=False, index=True)
    Cantidad_Consultorios = Column(Integer, nullable=False)
    M_Desde = Column(CHAR(4), nullable=True)
    M_Hasta = Column(CHAR(4), nullable=True)
    T_Desde = Column(CHAR(4), nullable=True)
    T_Hasta = Column(CHAR(4), nullable=True)
    N_Desde = Column(CHAR(4), nullable=True)
    N_Hasta = Column(CHAR(4), nullable=True)
    Frecuencia = Column(CHAR(2), nullable=True)
    Turnos = Column(Integer, nullable=True)
    Demanda = Column(Boolean, nullable=True)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)

class ZisPrestador(ZisMedBase):
    """Modelo real de tabla Prestadores de ZisMed"""
    __tablename__ = "Prestadores"

    PrestadorID = Column(Integer, primary_key=True)
    Nombre = Column(CHAR(100), nullable=False, index=True)
    Matricula = Column(CHAR(20), nullable=True)
    Documento = Column(CHAR(30), nullable=True)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)

class ZisPrestadorDias(ZisMedBase):
    """Modelo real de tabla PrestadorDias de ZisMed"""
    __tablename__ = "PrestadorDias"

    PrestadorDiasID = Column(Integer, primary_key=True)
    PrestadorID = Column(Integer, nullable=False, index=True)
    ServicioID = Column(Integer, nullable=False, index=True)
    ConsultorioID = Column(Integer, nullable=False)
    DiaID = Column(Integer, nullable=False, index=True)
    M_Desde = Column(CHAR(4), nullable=True)
    M_Hasta = Column(CHAR(4), nullable=True)
    T_Desde = Column(CHAR(4), nullable=True)
    T_Hasta = Column(CHAR(4), nullable=True)
    N_Desde = Column(CHAR(4), nullable=True)
    N_Hasta = Column(CHAR(4), nullable=True)
    Frecuencia = Column(CHAR(2), nullable=True)
    CantPacienteM = Column(Integer, nullable=True)
    CantPacienteT = Column(Integer, nullable=True)
    CantPacienteN = Column(Integer, nullable=True)
    Anulado = Column(Boolean, nullable=False, default=False, index=True)
    PrestadoresInstitucionesID = Column(Integer, nullable=True, index=True)

# === MODELOS MONGODB (para logs y cache) ===
# Comentados temporalmente - MongoDB no está en uso actualmente
# from app.config.database import Base as MongoBase
#
# class Clinica(MongoBase):
#     """Modelo para configuración de clínicas (MongoDB)"""
#     __tablename__ = "clinicas"
#
#     id = Column(Integer, primary_key=True, index=True)
#     nombre = Column(String(100), nullable=False, index=True)
#     configuraciones = Column(JSON, nullable=True)
#     did_whatsapp = Column(String(50), unique=True, index=True)
#     activa = Column(Boolean, default=True, nullable=False)
#     fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
#     fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())