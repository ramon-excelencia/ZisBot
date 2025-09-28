"""
Modelos ORM limpios según estructura real de la BD DBH_Test
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Paciente(Base):
    """Modelo ORM para tabla Pacientes según estructura real"""
    __tablename__ = 'Pacientes'

    PacienteID = Column(Integer, primary_key=True)
    Cuil = Column(String(20))
    IdTipoDocumento = Column(Integer)
    Documento = Column(String(50), index=True)
    Nombre = Column(String(100))
    Apellido = Column(String(100))
    ObraSocialID = Column(Integer)
    IdNacionalidad = Column(Integer)
    IdSexo = Column(Integer)
    IdSexoGenero = Column(Integer)
    IdEstadoCivil = Column(Integer)
    FechadeNacimiento = Column(DateTime)
    Telefono = Column(String(50))
    Correo = Column(String(100))
    Anulado = Column(Boolean, default=False)

    # Relaciones
    consultas = relationship("ConsultaAmbulatoria", back_populates="paciente")

class Especialidad(Base):
    """Modelo ORM para tabla Especialidades"""
    __tablename__ = 'Especialidades'

    EspecialidadID = Column(Integer, primary_key=True)
    Nombre = Column(String(200))
    Anulado = Column(Boolean, default=False)

    prestadores = relationship("Prestador", back_populates="especialidad")

class Prestador(Base):
    """Modelo ORM para tabla Prestadores"""
    __tablename__ = 'Prestadores'

    PrestadorID = Column(Integer, primary_key=True)
    Matricula = Column(String(50))
    Nombre = Column(String(100))
    EspecialidadID = Column(Integer, ForeignKey('Especialidades.EspecialidadID'))
    Telefono = Column(String(50))
    Email = Column(String(100))
    Anulado = Column(Boolean, default=False)
    Documento = Column(String(20))
    Cuil = Column(String(20))
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))

    especialidad = relationship("Especialidad", back_populates="prestadores")
    institucion = relationship("Institucion", back_populates="prestadores")

class Institucion(Base):
    """Modelo ORM para tabla Instituciones"""
    __tablename__ = 'Instituciones'

    InstitucionID = Column(Integer, primary_key=True)
    Nombre = Column(String(200))
    Anulado = Column(Boolean, default=False)

    prestadores = relationship("Prestador", back_populates="institucion")

class Servicio(Base):
    """Modelo ORM para tabla Servicios"""
    __tablename__ = 'Servicios'

    ServicioID = Column(Integer, primary_key=True)
    Nombre = Column(String(200))
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))

    institucion = relationship("Institucion")

class Sector(Base):
    """Modelo ORM para tabla Sectores_Hospital"""
    __tablename__ = 'Sectores_Hospital'

    SectorId = Column(Integer, primary_key=True)
    Nombre = Column(String(50))
    CupoPermisosDiario = Column(Integer, default=0)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))

    institucion = relationship("Institucion")
    habitaciones = relationship("Habitacion", back_populates="sector")

class Habitacion(Base):
    """Modelo ORM para tabla Habitaciones_Hospital"""
    __tablename__ = 'Habitaciones_Hospital'

    HabitacionID = Column(Integer, primary_key=True)
    Nombre = Column(String(30))
    SectorID = Column(Integer, ForeignKey('Sectores_Hospital.SectorId'))
    PisoId = Column(Integer)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))
    AdmiteCuna = Column(Boolean, default=False)
    TipoInternacionID = Column(Integer)

    sector = relationship("Sector", back_populates="habitaciones")
    institucion = relationship("Institucion")
    camas = relationship("Cama", back_populates="habitacion")

class Cama(Base):
    """Modelo ORM para tabla Camas"""
    __tablename__ = 'Camas'

    CamaId = Column(Integer, primary_key=True)
    Nombre = Column(String(100))
    HabitacionID = Column(Integer, ForeignKey('Habitaciones_Hospital.HabitacionID'))
    En_mantenimiento = Column(Boolean, default=False)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))
    TieneOxigeno = Column(Boolean)
    Habilitada = Column(Boolean)
    Considerar = Column(Boolean)
    TipoCamaID = Column(Integer)
    Reservada = Column(Integer)

    habitacion = relationship("Habitacion", back_populates="camas")
    institucion = relationship("Institucion")
    internaciones = relationship("Internacion", back_populates="cama")

class Internacion(Base):
    """Modelo ORM para tabla Internaciones"""
    __tablename__ = 'Internaciones'

    InternacionID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, ForeignKey('Pacientes.PacienteID'))
    CamaID = Column(Integer, ForeignKey('Camas.CamaId'))
    HabitacionID = Column(Integer, ForeignKey('Habitaciones_Hospital.HabitacionID'))
    ObraSocialID = Column(Integer)
    Fecha_ingreso = Column(DateTime)
    Hora_Ingreso = Column(String(4))
    PrestadorIngresoID = Column(Integer, ForeignKey('Prestadores.PrestadorID'))
    Fecha_Alta = Column(DateTime)
    Hora_alta = Column(String(4))
    PrestadorAltaID = Column(Integer, ForeignKey('Prestadores.PrestadorID'))
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))
    FechaCrea = Column(DateTime)
    UsuarioCrea = Column(String(11))

    paciente = relationship("Paciente")
    cama = relationship("Cama", back_populates="internaciones")
    habitacion = relationship("Habitacion")
    prestador_ingreso = relationship("Prestador", foreign_keys=[PrestadorIngresoID])
    prestador_alta = relationship("Prestador", foreign_keys=[PrestadorAltaID])
    institucion = relationship("Institucion")

class Consultorio(Base):
    """Modelo ORM para tabla Consultorios"""
    __tablename__ = 'Consultorios'

    ConsultorioID = Column(Integer, primary_key=True)
    Nombre = Column(String(50))
    EspecialidadID = Column(Integer, ForeignKey('Especialidades.EspecialidadID'))
    TvMonitorID = Column(Integer)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))
    EsAdmision = Column(Boolean)

    especialidad = relationship("Especialidad")
    institucion = relationship("Institucion")
    turnos = relationship("Turno", back_populates="consultorio")

class Turno(Base):
    """Modelo ORM para tabla Turnos"""
    __tablename__ = 'Turnos'

    TurnoID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, ForeignKey('Pacientes.PacienteID'))
    ServicioID = Column(Integer, ForeignKey('Servicios.ServicioID'))
    ConsultorioID = Column(Integer, ForeignKey('Consultorios.ConsultorioID'))
    PrestadorID = Column(Integer, ForeignKey('Prestadores.PrestadorID'))
    Fecha_Hora = Column(DateTime)
    Hora_Hasta = Column(String(4))
    Orden = Column(String(2))
    Llegada = Column(DateTime)
    Llamado = Column(DateTime)
    Atendido = Column(DateTime)
    NoAtendido = Column(DateTime)
    Primeravez = Column(Boolean)
    ObraSocialID = Column(Integer)
    Emergencia = Column(Boolean)
    Admisionado = Column(Boolean, default=False)
    Edad = Column(Integer)
    Anulado = Column(Boolean, default=False)
    FechaCrea = Column(DateTime)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))
    TeleSalud = Column(Boolean)

    paciente = relationship("Paciente")
    servicio = relationship("Servicio")
    consultorio = relationship("Consultorio", back_populates="turnos")
    prestador = relationship("Prestador")
    institucion = relationship("Institucion")

class ConsultaAmbulatoria(Base):
    """Modelo ORM para tabla Consultas_Ambulatorias"""
    __tablename__ = 'Consultas_Ambulatorias'

    ConsultaID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, ForeignKey('Pacientes.PacienteID'))
    TurnoID = Column(Integer, ForeignKey('Turnos.TurnoID'))
    PrestadorID = Column(Integer, ForeignKey('Prestadores.PrestadorID'))
    ServicioID = Column(Integer, ForeignKey('Servicios.ServicioID'))
    FechaConsulta = Column(DateTime)
    MotivoConsulta = Column(Text)
    Diagnostico = Column(Text)
    EvolucionClinica = Column(Text)
    IndicacionesTerapeuticas = Column(Text)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer)

    # Relaciones
    paciente = relationship("Paciente", back_populates="consultas")
    turno = relationship("Turno")
    prestador = relationship("Prestador")
    servicio = relationship("Servicio")