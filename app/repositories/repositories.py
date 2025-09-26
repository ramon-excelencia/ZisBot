from app.models.entities import Clinica, Paciente, Profesional, Especialidad, Turno, LogIA
from app.schemas.responses import (
    ClinicaCreate, ClinicaUpdate,
    PacienteCreate, PacienteUpdate,
    ProfesionalCreate, ProfesionalUpdate,
    EspecialidadCreate, EspecialidadUpdate,
    TurnoCreate, TurnoUpdate,
    LogIACreate
)
from .base import BaseRepository, ClinicaRepository, PacienteRepository, TurnoRepository

# Instancias de repositorios
clinica_repo = ClinicaRepository(Clinica)
paciente_repo = PacienteRepository(Paciente)
profesional_repo = BaseRepository[Profesional, ProfesionalCreate, ProfesionalUpdate](Profesional)
especialidad_repo = BaseRepository[Especialidad, EspecialidadCreate, EspecialidadUpdate](Especialidad)
turno_repo = TurnoRepository(Turno)
log_ia_repo = BaseRepository[LogIA, LogIACreate, dict](LogIA)