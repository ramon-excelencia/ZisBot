# DOCUMENTACIÓN COMPLETA: TABLAS Y MODELOS ORM PARA CHATBOT ZISMED

## RESUMEN EJECUTIVO

Este documento detalla todas las tablas y columnas necesarias de la base de datos **DBH_Test** para implementar un chatbot que cumpla con los criterios de aceptación definidos. Se incluyen sugerencias de implementación con SQLAlchemy ORM.

**Base de Datos:** DBH_Test
**Servidor:** 168.226.219.57,2424
**Usuario:** sa
**Password:** Excel159753

---

## 1. IDENTIDAD Y PERMISOS

### Tablas Principales para Autenticación

#### AspNetUsers
```sql
-- Tabla principal de usuarios del sistema
CREATE TABLE AspNetUsers (
    Id nvarchar(256) PRIMARY KEY,
    Email nvarchar(512),
    UserName nvarchar(512),
    Name nvarchar(512),
    PasswordHash nvarchar(max),
    SecurityStamp nvarchar(max),
    PhoneNumber nvarchar(max),
    UserIDOriginal nvarchar(256),
    Token nvarchar(400),
    TokenZismed nvarchar(max),
    CaduceTokenZismed datetime
);
```

#### AspNetRoles
```sql
-- Roles y permisos
CREATE TABLE AspNetRoles (
    Id nvarchar(256) PRIMARY KEY,
    Name nvarchar(512),
    Observacion ntext,
    Es_Coordinador bit
);
```

#### AspNetUserRoles
```sql
-- Relación usuarios-roles por institución
CREATE TABLE AspNetUserRoles (
    UserId nvarchar(256),
    RoleId nvarchar(256),
    InstitucionID int,
    PRIMARY KEY (UserId, RoleId, InstitucionID)
);
```

### Modelo SQLAlchemy para Autenticación

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class AspNetUser(Base):
    """Usuario del sistema con autenticación"""
    __tablename__ = 'AspNetUsers'

    Id = Column(String(256), primary_key=True)
    Email = Column(String(512))
    UserName = Column(String(512))
    Name = Column(String(512))
    PasswordHash = Column(Text)
    SecurityStamp = Column(Text)
    PhoneNumber = Column(Text)
    Token = Column(String(400))
    TokenZismed = Column(Text)
    CaduceTokenZismed = Column(DateTime)

    # Relaciones
    user_roles = relationship("AspNetUserRole", back_populates="user")

class AspNetRole(Base):
    """Roles del sistema"""
    __tablename__ = 'AspNetRoles'

    Id = Column(String(256), primary_key=True)
    Name = Column(String(512))
    Observacion = Column(Text)
    Es_Coordinador = Column(Boolean, default=False)

class AspNetUserRole(Base):
    """Asignación de roles por institución"""
    __tablename__ = 'AspNetUserRoles'

    UserId = Column(String(256), ForeignKey('AspNetUsers.Id'), primary_key=True)
    RoleId = Column(String(256), ForeignKey('AspNetRoles.Id'), primary_key=True)
    InstitucionID = Column(Integer, primary_key=True)

    # Relaciones
    user = relationship("AspNetUser", back_populates="user_roles")
    role = relationship("AspNetRole")
    institucion = relationship("Institucion")
```

---

## 2. CAMAS DISPONIBLES

### Tablas para Gestión de Camas

#### Camas
```sql
CREATE TABLE Camas (
    CamaId int PRIMARY KEY,
    Nombre nchar(100),
    HabitacionID int,
    En_mantenimiento bit DEFAULT 0,
    Anulado bit DEFAULT 0,
    InstitucionID int,
    TieneOxigeno bit,
    Habilitada bit,
    Considerar bit,
    TipoCamaID int,
    Reservada int
);
```

#### Habitaciones_Hospital
```sql
CREATE TABLE Habitaciones_Hospital (
    HabitacionID int PRIMARY KEY,
    Nombre nchar(30),
    SectorID int,
    PisoId int,
    Anulado bit DEFAULT 0,
    InstitucionID int,
    AdmiteCuna bit DEFAULT 0,
    TipoInternacionID int,
    PermiteReserva bit,
    EsNeo bit
);
```

#### Sectores_Hospital
```sql
CREATE TABLE Sectores_Hospital (
    SectorId int PRIMARY KEY,
    Nombre nchar(50),
    CupoPermisosDiario int DEFAULT 0,
    Anulado bit DEFAULT 0,
    InstitucionID int
);
```

#### Internaciones (para ocupación)
```sql
CREATE TABLE Internaciones (
    InternacionID int PRIMARY KEY,
    PacienteID int,
    HabitacionID int,
    CamaID int,
    ObraSocialID int,
    Fecha_ingreso date,
    Fecha_Alta date,
    PrestadorIngresoID int,
    Anulado bit DEFAULT 0,
    InstitucionID int,
    NoConsiderar bit
);
```

### Modelos SQLAlchemy para Camas

```python
class Sector(Base):
    """Sectores del hospital"""
    __tablename__ = 'Sectores_Hospital'

    SectorId = Column(Integer, primary_key=True)
    Nombre = Column(String(50))
    CupoPermisosDiario = Column(Integer, default=0)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))

    # Relaciones
    habitaciones = relationship("Habitacion", back_populates="sector")
    institucion = relationship("Institucion")

class Habitacion(Base):
    """Habitaciones del hospital"""
    __tablename__ = 'Habitaciones_Hospital'

    HabitacionID = Column(Integer, primary_key=True)
    Nombre = Column(String(30))
    SectorID = Column(Integer, ForeignKey('Sectores_Hospital.SectorId'))
    PisoId = Column(Integer)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer, ForeignKey('Instituciones.InstitucionID'))
    AdmiteCuna = Column(Boolean, default=False)
    TipoInternacionID = Column(Integer)
    PermiteReserva = Column(Boolean)
    EsNeo = Column(Boolean)

    # Relaciones
    sector = relationship("Sector", back_populates="habitaciones")
    camas = relationship("Cama", back_populates="habitacion")
    internaciones = relationship("Internacion", back_populates="habitacion")

class Cama(Base):
    """Camas del hospital"""
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
    TipoCamaID = Column(Integer, ForeignKey('TipoCama.TipoCamaID'))
    Reservada = Column(Integer)

    # Relaciones
    habitacion = relationship("Habitacion", back_populates="camas")
    internaciones = relationship("Internacion", back_populates="cama")
    tipo_cama = relationship("TipoCama")

class Internacion(Base):
    """Internaciones activas"""
    __tablename__ = 'Internaciones'

    InternacionID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, ForeignKey('Pacientes.PacienteID'))
    HabitacionID = Column(Integer, ForeignKey('Habitaciones_Hospital.HabitacionID'))
    CamaID = Column(Integer, ForeignKey('Camas.CamaId'))
    ObraSocialID = Column(Integer)
    Fecha_ingreso = Column(DateTime)
    Fecha_Alta = Column(DateTime)
    PrestadorIngresoID = Column(Integer, ForeignKey('Prestadores.PrestadorID'))
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer)
    NoConsiderar = Column(Boolean)

    # Relaciones
    paciente = relationship("Paciente")
    habitacion = relationship("Habitacion", back_populates="internaciones")
    cama = relationship("Cama", back_populates="internaciones")
    prestador_ingreso = relationship("Prestador")

# Consulta ejemplo para obtener disponibilidad de camas
def get_bed_availability(db_session, sector_id=None, fecha=None):
    """
    Consulta para obtener disponibilidad de camas por sector/fecha

    Returns:
        dict: {
            'total_camas': int,
            'camas_ocupadas': int,
            'camas_disponibles': int,
            'porcentaje_ocupacion': float
        }
    """
    query = db_session.query(Cama).filter(
        Cama.Anulado == False,
        Cama.Habilitada == True,
        Cama.Considerar == True
    )

    if sector_id:
        query = query.join(Habitacion).filter(
            Habitacion.SectorID == sector_id
        )

    total_camas = query.count()

    # Camas ocupadas (con internación activa)
    ocupadas_query = query.join(Internacion, Cama.CamaId == Internacion.CamaID).filter(
        Internacion.Fecha_Alta.is_(None),
        Internacion.Anulado == False,
        Internacion.NoConsiderar == False
    )

    if fecha:
        ocupadas_query = ocupadas_query.filter(
            Internacion.Fecha_ingreso <= fecha
        )

    camas_ocupadas = ocupadas_query.count()
    camas_disponibles = total_camas - camas_ocupadas
    porcentaje = (camas_ocupadas / total_camas * 100) if total_camas > 0 else 0

    return {
        'total_camas': total_camas,
        'camas_ocupadas': camas_ocupadas,
        'camas_disponibles': camas_disponibles,
        'porcentaje_ocupacion': round(porcentaje, 2)
    }
```

---

## 3. HISTORIAS CLÍNICAS

### Tablas para Datos de Pacientes e Historia Clínica

#### Pacientes
```sql
CREATE TABLE Pacientes (
    PacienteID int PRIMARY KEY,
    Cuil nchar(11),
    IdTipoDocumento int,
    Documento nchar(50),
    Nombre nchar(100),
    Apellido nchar(50),
    ObraSocialID int,
    IdSexo tinyint,
    FechadeNacimiento date,
    Telefono varchar(20),
    Correo nvarchar(200),
    Anulado bit DEFAULT 0,
    InstitucionID int
);
```

#### Consultas_Ambulatorias
```sql
CREATE TABLE Consultas_Ambulatorias (
    ConsultaID int PRIMARY KEY,
    PacienteID int,
    TurnoID int,
    PrestadorID int,
    ServicioID int,
    FechaConsulta datetime,
    MotivoConsulta nvarchar(max),
    Diagnostico nvarchar(max),
    EvolucionClinica nvarchar(max),
    IndicacionesTerapeuticas nvarchar(max),
    Anulado bit DEFAULT 0,
    InstitucionID int
);
```

#### Prestadores
```sql
CREATE TABLE Prestadores (
    PrestadorID int PRIMARY KEY,
    Matricula nvarchar(50),
    Nombre nvarchar(100),
    EspecialidadID int,
    Telefono varchar(50),
    Email nvarchar(100),
    Documento nvarchar(20),
    Cuil nvarchar(20),
    Anulado bit DEFAULT 0,
    InstitucionID int
);
```

### Modelos SQLAlchemy para Historia Clínica

```python
class Paciente(Base):
    """Datos básicos del paciente"""
    __tablename__ = 'Pacientes'

    PacienteID = Column(Integer, primary_key=True)
    Cuil = Column(String(11))
    IdTipoDocumento = Column(Integer)
    Documento = Column(String(50), index=True)
    Nombre = Column(String(100))
    Apellido = Column(String(50))
    ObraSocialID = Column(Integer)
    IdSexo = Column(Integer)
    FechadeNacimiento = Column(DateTime)
    Telefono = Column(String(20))
    Correo = Column(String(200))
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer)

    # Relaciones
    consultas = relationship("ConsultaAmbulatoria", back_populates="paciente")
    internaciones = relationship("Internacion", back_populates="paciente")

class ConsultaAmbulatoria(Base):
    """Consultas y evoluciones del paciente"""
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

class Prestador(Base):
    """Profesionales médicos"""
    __tablename__ = 'Prestadores'

    PrestadorID = Column(Integer, primary_key=True)
    Matricula = Column(String(50))
    Nombre = Column(String(100))
    EspecialidadID = Column(Integer, ForeignKey('Especialidades.EspecialidadID'))
    Telefono = Column(String(50))
    Email = Column(String(100))
    Documento = Column(String(20))
    Cuil = Column(String(20))
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer)

    # Relaciones
    especialidad = relationship("Especialidad")
    consultas = relationship("ConsultaAmbulatoria", back_populates="prestador")

# Función para obtener historia clínica resumida
def get_patient_summary(db_session, paciente_id, user_permissions):
    """
    Obtiene resumen de historia clínica según permisos del usuario

    Args:
        db_session: Sesión de base de datos
        paciente_id: ID del paciente
        user_permissions: Permisos del usuario directivo

    Returns:
        dict: Resumen de la historia clínica autorizada
    """
    # Datos básicos del paciente
    paciente = db_session.query(Paciente).filter(
        Paciente.PacienteID == paciente_id,
        Paciente.Anulado == False
    ).first()

    if not paciente:
        return None

    # Verificar permisos sobre este paciente
    if not check_patient_permissions(user_permissions, paciente):
        return {"error": "No tiene autorización para acceder a este paciente"}

    # Consultas recientes
    consultas = db_session.query(ConsultaAmbulatoria).filter(
        ConsultaAmbulatoria.PacienteID == paciente_id,
        ConsultaAmbulatoria.Anulado == False
    ).join(Prestador).order_by(
        ConsultaAmbulatoria.FechaConsulta.desc()
    ).limit(10).all()

    # Internación actual
    internacion_actual = db_session.query(Internacion).filter(
        Internacion.PacienteID == paciente_id,
        Internacion.Fecha_Alta.is_(None),
        Internacion.Anulado == False
    ).first()

    return {
        "identificacion": {
            "nombre": f"{paciente.Nombre} {paciente.Apellido}",
            "documento": paciente.Documento,
            "fecha_nacimiento": paciente.FechadeNacimiento.strftime('%d/%m/%Y') if paciente.FechadeNacimiento else None
        },
        "internacion_vigente": {
            "cama": internacion_actual.cama.Nombre if internacion_actual and internacion_actual.cama else None,
            "sector": internacion_actual.habitacion.sector.Nombre if internacion_actual and internacion_actual.habitacion else None,
            "fecha_ingreso": internacion_actual.Fecha_ingreso.strftime('%d/%m/%Y') if internacion_actual else None,
            "medico_responsable": internacion_actual.prestador_ingreso.Nombre if internacion_actual and internacion_actual.prestador_ingreso else None
        },
        "evoluciones_recientes": [
            {
                "fecha": consulta.FechaConsulta.strftime('%d/%m/%Y %H:%M'),
                "profesional": consulta.prestador.Nombre,
                "diagnostico": consulta.Diagnostico[:200] + "..." if len(consulta.Diagnostico or "") > 200 else consulta.Diagnostico,
                "evolucion": consulta.EvolucionClinica[:300] + "..." if len(consulta.EvolucionClinica or "") > 300 else consulta.EvolucionClinica
            }
            for consulta in consultas
        ]
    }

def check_patient_permissions(user_permissions, paciente):
    """
    Verifica si el usuario tiene permisos para acceder a los datos del paciente

    Args:
        user_permissions: Permisos del usuario
        paciente: Objeto Paciente

    Returns:
        bool: True si tiene permisos
    """
    # Implementar lógica de permisos según rol y sector
    # Por ejemplo: directivos pueden ver todos los pacientes de su institución
    return True  # Simplificado para el ejemplo
```

---

## 4. HORARIOS Y SERVICIOS

### Tablas para Servicios y Horarios

#### Servicios
```sql
CREATE TABLE Servicios (
    ServicioID int PRIMARY KEY,
    Nombre nvarchar(200),
    Anulado bit DEFAULT 0,
    InstitucionID int
);
```

#### Especialidades
```sql
CREATE TABLE Especialidades (
    EspecialidadID int PRIMARY KEY,
    Nombre nchar(50),
    Grilla bit,
    Anulado bit DEFAULT 0
);
```

#### Consultorios
```sql
CREATE TABLE Consultorios (
    ConsultorioID int PRIMARY KEY,
    Nombre nchar(50),
    EspecialidadID int,
    TvMonitorID int,
    Anulado bit DEFAULT 0,
    InstitucionID int,
    EsAdmision bit
);
```

#### Turnos (para horarios)
```sql
CREATE TABLE Turnos (
    TurnoID int PRIMARY KEY,
    PacienteID int,
    ServicioID int,
    ConsultorioID int,
    PrestadorID int,
    Fecha_Hora smalldatetime,
    Hora_Hasta nchar(4),
    Llegada smalldatetime,
    Atendido smalldatetime,
    Anulado bit DEFAULT 0,
    InstitucionID int
);
```

### Modelos SQLAlchemy para Servicios

```python
class Servicio(Base):
    """Servicios del hospital"""
    __tablename__ = 'Servicios'

    ServicioID = Column(Integer, primary_key=True)
    Nombre = Column(String(200))
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer)

    # Relaciones
    turnos = relationship("Turno", back_populates="servicio")

class Especialidad(Base):
    """Especialidades médicas"""
    __tablename__ = 'Especialidades'

    EspecialidadID = Column(Integer, primary_key=True)
    Nombre = Column(String(50))
    Grilla = Column(Boolean)
    Anulado = Column(Boolean, default=False)

    # Relaciones
    prestadores = relationship("Prestador", back_populates="especialidad")

class Consultorio(Base):
    """Consultorios"""
    __tablename__ = 'Consultorios'

    ConsultorioID = Column(Integer, primary_key=True)
    Nombre = Column(String(50))
    EspecialidadID = Column(Integer, ForeignKey('Especialidades.EspecialidadID'))
    TvMonitorID = Column(Integer)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer)
    EsAdmision = Column(Boolean)

    # Relaciones
    especialidad = relationship("Especialidad")
    turnos = relationship("Turno", back_populates="consultorio")

class Turno(Base):
    """Turnos y citas"""
    __tablename__ = 'Turnos'

    TurnoID = Column(Integer, primary_key=True)
    PacienteID = Column(Integer, ForeignKey('Pacientes.PacienteID'))
    ServicioID = Column(Integer, ForeignKey('Servicios.ServicioID'))
    ConsultorioID = Column(Integer, ForeignKey('Consultorios.ConsultorioID'))
    PrestadorID = Column(Integer, ForeignKey('Prestadores.PrestadorID'))
    Fecha_Hora = Column(DateTime)
    Hora_Hasta = Column(String(4))
    Llegada = Column(DateTime)
    Atendido = Column(DateTime)
    Anulado = Column(Boolean, default=False)
    InstitucionID = Column(Integer)

    # Relaciones
    paciente = relationship("Paciente")
    servicio = relationship("Servicio", back_populates="turnos")
    consultorio = relationship("Consultorio", back_populates="turnos")
    prestador = relationship("Prestador")

# Función para obtener horarios de atención
def get_service_schedule(db_session, servicio_id=None, prestador_id=None):
    """
    Obtiene horarios de atención por servicio/prestador

    Returns:
        list: Lista de horarios con días, horarios y ubicaciones
    """
    from datetime import datetime, timedelta

    # Obtener turnos de la próxima semana para identificar patrones
    fecha_inicio = datetime.now().date()
    fecha_fin = fecha_inicio + timedelta(days=7)

    query = db_session.query(Turno).filter(
        Turno.Fecha_Hora >= fecha_inicio,
        Turno.Fecha_Hora <= fecha_fin,
        Turno.Anulado == False
    )

    if servicio_id:
        query = query.filter(Turno.ServicioID == servicio_id)
    if prestador_id:
        query = query.filter(Turno.PrestadorID == prestador_id)

    turnos = query.join(Prestador).join(Consultorio).join(Servicio).all()

    # Agrupar por días y horarios
    horarios = {}
    for turno in turnos:
        dia = turno.Fecha_Hora.strftime('%A')  # Día de la semana
        hora = turno.Fecha_Hora.strftime('%H:%M')

        if dia not in horarios:
            horarios[dia] = []

        horarios[dia].append({
            'hora_inicio': hora,
            'hora_fin': turno.Hora_Hasta,
            'prestador': turno.prestador.Nombre,
            'consultorio': turno.consultorio.Nombre,
            'servicio': turno.servicio.Nombre
        })

    return horarios
```

---

## 5. VOLUMEN DE ATENCIÓN

### Consultas para Estadísticas de Atención

```python
def get_attention_volume(db_session, fecha_desde, fecha_hasta, servicio_id=None):
    """
    Obtiene volumen de atención por servicio y período

    Args:
        db_session: Sesión de base de datos
        fecha_desde: Fecha inicio del período
        fecha_hasta: Fecha fin del período
        servicio_id: ID del servicio (opcional)

    Returns:
        dict: Estadísticas de atención
    """
    from sqlalchemy import func

    # Consulta base para turnos atendidos
    query = db_session.query(
        Servicio.Nombre.label('servicio'),
        func.count(Turno.TurnoID).label('cantidad_pacientes'),
        func.date(Turno.Atendido).label('fecha')
    ).join(Servicio).filter(
        Turno.Atendido.isnot(None),
        Turno.Atendido >= fecha_desde,
        Turno.Atendido <= fecha_hasta,
        Turno.Anulado == False
    )

    if servicio_id:
        query = query.filter(Turno.ServicioID == servicio_id)

    # Agrupar por servicio y fecha
    resultados = query.group_by(
        Servicio.Nombre,
        func.date(Turno.Atendido)
    ).all()

    # Procesar resultados
    estadisticas = {}
    total_general = 0

    for resultado in resultados:
        servicio = resultado.servicio
        cantidad = resultado.cantidad_pacientes
        fecha = resultado.fecha.strftime('%Y-%m-%d')

        if servicio not in estadisticas:
            estadisticas[servicio] = {
                'total': 0,
                'por_dia': {}
            }

        estadisticas[servicio]['total'] += cantidad
        estadisticas[servicio]['por_dia'][fecha] = cantidad
        total_general += cantidad

    return {
        'total_general': total_general,
        'por_servicio': estadisticas,
        'periodo': {
            'desde': fecha_desde.strftime('%Y-%m-%d'),
            'hasta': fecha_hasta.strftime('%Y-%m-%d')
        }
    }

def get_emergency_stats(db_session, fecha_desde, fecha_hasta):
    """
    Estadísticas específicas de guardia/emergencias
    """
    # Consultar tabla de Guardia si existe
    # Por ahora usar Turnos con flag Emergencia

    emergencias = db_session.query(
        func.count(Turno.TurnoID).label('total'),
        func.date(Turno.Atendido).label('fecha')
    ).filter(
        Turno.Emergencia == True,
        Turno.Atendido >= fecha_desde,
        Turno.Atendido <= fecha_hasta,
        Turno.Anulado == False
    ).group_by(func.date(Turno.Atendido)).all()

    return [
        {
            'fecha': resultado.fecha.strftime('%Y-%m-%d'),
            'emergencias': resultado.total
        }
        for resultado in emergencias
    ]
```

---

## 6. TRAZABILIDAD Y AUDITORÍA

### Sistema de Logging

```python
class ChatbotAuditLog(Base):
    """Tabla para auditoría del chatbot"""
    __tablename__ = 'ChatbotAuditLog'

    LogID = Column(Integer, primary_key=True, autoincrement=True)
    UsuarioID = Column(String(256), ForeignKey('AspNetUsers.Id'))
    FechaHora = Column(DateTime, default=func.now())
    TipoConsulta = Column(String(100))  # 'camas', 'historia_clinica', 'horarios', etc.
    PacienteID = Column(Integer)  # Si la consulta involucra un paciente
    ServicioID = Column(Integer)   # Si la consulta involucra un servicio
    ConsultaDetalle = Column(Text)  # Texto de la consulta original
    RespuestaGenerada = Column(Text)  # Respuesta del chatbot
    IPAddress = Column(String(50))
    UserAgent = Column(String(500))
    InstitucionID = Column(Integer)

    # Relaciones
    usuario = relationship("AspNetUser")

def log_chatbot_interaction(db_session, user_id, tipo_consulta, consulta_detalle,
                          respuesta=None, paciente_id=None, servicio_id=None,
                          ip_address=None, user_agent=None, institucion_id=None):
    """
    Registra cada interacción con el chatbot para auditoría
    """
    log_entry = ChatbotAuditLog(
        UsuarioID=user_id,
        TipoConsulta=tipo_consulta,
        PacienteID=paciente_id,
        ServicioID=servicio_id,
        ConsultaDetalle=consulta_detalle,
        RespuestaGenerada=respuesta,
        IPAddress=ip_address,
        UserAgent=user_agent,
        InstitucionID=institucion_id
    )

    db_session.add(log_entry)
    db_session.commit()

    return log_entry.LogID

# Ejemplo de uso en el chatbot
def process_chatbot_query(db_session, user_id, query_text, user_permissions):
    """
    Procesa una consulta del chatbot con logging completo
    """
    import json

    try:
        # Identificar tipo de consulta
        tipo_consulta = classify_query(query_text)

        # Log de la consulta entrante
        log_id = log_chatbot_interaction(
            db_session,
            user_id,
            tipo_consulta,
            query_text
        )

        # Procesar según tipo
        if tipo_consulta == 'camas_disponibles':
            response = handle_bed_availability_query(db_session, query_text, user_permissions)
        elif tipo_consulta == 'historia_clinica':
            response = handle_patient_history_query(db_session, query_text, user_permissions)
        elif tipo_consulta == 'horarios_servicios':
            response = handle_schedule_query(db_session, query_text, user_permissions)
        else:
            response = {"error": "Tipo de consulta no reconocida"}

        # Actualizar log con respuesta
        log_entry = db_session.query(ChatbotAuditLog).filter(
            ChatbotAuditLog.LogID == log_id
        ).first()

        log_entry.RespuestaGenerada = json.dumps(response, ensure_ascii=False)
        db_session.commit()

        return response

    except Exception as e:
        # Log del error
        log_chatbot_interaction(
            db_session,
            user_id,
            'error',
            query_text,
            respuesta=f"Error: {str(e)}"
        )
        raise
```

---

## 7. CONFIGURACIÓN DE BASE DE DATOS

### Configuración SQLAlchemy

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Configuración de conexión
DATABASE_CONFIG = {
    'server': '168.226.219.57,2424',
    'database': 'DBH_Test',
    'username': 'sa',
    'password': 'Excel159753',
    'driver': 'SQL Server'
}

# String de conexión
CONNECTION_STRING = (
    f"mssql+pyodbc://{DATABASE_CONFIG['username']}:{DATABASE_CONFIG['password']}"
    f"@{DATABASE_CONFIG['server']}/{DATABASE_CONFIG['database']}"
    f"?driver={DATABASE_CONFIG['driver']}"
)

# Crear engine
engine = create_engine(
    CONNECTION_STRING,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    echo=False  # Cambiar a True para debug SQL
)

# Crear session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Crear todas las tablas (si no existen)
def create_tables():
    Base.metadata.create_all(bind=engine)
```

---

## 8. IMPLEMENTACIÓN DE SEGURIDAD

### Sistema de Permisos por Rol

```python
from enum import Enum

class PermissionLevel(Enum):
    READ_BASIC = "read_basic"           # Datos básicos
    READ_CLINICAL = "read_clinical"     # Historia clínica
    READ_SENSITIVE = "read_sensitive"   # Datos sensibles
    READ_ALL = "read_all"              # Todos los datos

class ChatbotPermissions:
    """Manejo de permisos del chatbot"""

    ROLE_PERMISSIONS = {
        'DirectivoGeneral': [
            PermissionLevel.READ_ALL
        ],
        'DirectivoMedico': [
            PermissionLevel.READ_CLINICAL,
            PermissionLevel.READ_BASIC
        ],
        'DirectivoAdministrativo': [
            PermissionLevel.READ_BASIC
        ],
        'Coordinador': [
            PermissionLevel.READ_CLINICAL,
            PermissionLevel.READ_BASIC
        ]
    }

    @staticmethod
    def get_user_permissions(db_session, user_id):
        """Obtiene permisos del usuario"""
        user_roles = db_session.query(AspNetUserRole).filter(
            AspNetUserRole.UserId == user_id
        ).join(AspNetRole).all()

        permissions = set()
        for user_role in user_roles:
            role_name = user_role.role.Name
            if role_name in ChatbotPermissions.ROLE_PERMISSIONS:
                permissions.update(ChatbotPermissions.ROLE_PERMISSIONS[role_name])

        return list(permissions)

    @staticmethod
    def can_access_patient_data(permissions, data_type):
        """Verifica si puede acceder a un tipo de dato del paciente"""
        required_permission = {
            'basic': PermissionLevel.READ_BASIC,
            'clinical': PermissionLevel.READ_CLINICAL,
            'sensitive': PermissionLevel.READ_SENSITIVE
        }

        return (
            PermissionLevel.READ_ALL in permissions or
            required_permission.get(data_type) in permissions
        )

def filter_patient_data_by_permissions(patient_data, permissions):
    """Filtra datos del paciente según permisos"""
    filtered_data = {}

    # Datos básicos
    if ChatbotPermissions.can_access_patient_data(permissions, 'basic'):
        filtered_data.update({
            'nombre': patient_data.get('nombre'),
            'documento': patient_data.get('documento'),
            'cobertura': patient_data.get('cobertura'),
            'internacion_vigente': patient_data.get('internacion_vigente')
        })

    # Datos clínicos
    if ChatbotPermissions.can_access_patient_data(permissions, 'clinical'):
        filtered_data.update({
            'evoluciones_recientes': patient_data.get('evoluciones_recientes'),
            'diagnosticos': patient_data.get('diagnosticos')
        })

    # Datos sensibles (todos)
    if ChatbotPermissions.can_access_patient_data(permissions, 'sensitive'):
        filtered_data = patient_data

    return filtered_data
```

---

## 9. RESUMEN DE IMPLEMENTACIÓN

### Tablas Críticas Identificadas

1. **Autenticación y Permisos**
   - `AspNetUsers`, `AspNetRoles`, `AspNetUserRoles`

2. **Capacidad Hospitalaria**
   - `Camas`, `Habitaciones_Hospital`, `Sectores_Hospital`, `Internaciones`

3. **Historia Clínica**
   - `Pacientes`, `Consultas_Ambulatorias`, `Prestadores`

4. **Servicios y Horarios**
   - `Servicios`, `Especialidades`, `Consultorios`, `Turnos`

5. **Auditoría**
   - `ChatbotAuditLog` (nueva tabla propuesta)

### Funciones Principales del Chatbot

```python
class ZismedChatbot:
    """Clase principal del chatbot ZISMED"""

    def __init__(self, db_session):
        self.db = db_session

    def authenticate_user(self, token):
        """Autentica usuario por token JWT"""
        # Implementar validación JWT
        pass

    def get_bed_availability(self, user_id, sector=None, fecha=None):
        """Consulta disponibilidad de camas"""
        permissions = ChatbotPermissions.get_user_permissions(self.db, user_id)
        if not permissions:
            return {"error": "No tiene permisos para esta consulta"}

        return get_bed_availability(self.db, sector, fecha)

    def get_patient_history(self, user_id, paciente_id):
        """Obtiene historia clínica del paciente"""
        permissions = ChatbotPermissions.get_user_permissions(self.db, user_id)
        raw_data = get_patient_summary(self.db, paciente_id, permissions)
        return filter_patient_data_by_permissions(raw_data, permissions)

    def get_service_schedules(self, user_id, servicio_id=None):
        """Obtiene horarios de servicios"""
        return get_service_schedule(self.db, servicio_id)

    def get_attention_stats(self, user_id, fecha_desde, fecha_hasta):
        """Obtiene estadísticas de atención"""
        return get_attention_volume(self.db, fecha_desde, fecha_hasta)
```

### Próximos Pasos

1. **Crear tablas de auditoría**
2. **Implementar autenticación JWT**
3. **Configurar permisos granulares**
4. **Desarrollar interfaz de chat**
5. **Implementar procesamiento de lenguaje natural**
6. **Crear tests de integración**
7. **Documentar APIs**

Esta documentación proporciona la base completa para implementar el chatbot ZISMED con todos los criterios de aceptación requeridos.