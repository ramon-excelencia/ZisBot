"""
Sistema de Permisos y Roles para ZisBot
Validación de acceso a datos sensibles según rol del usuario
"""
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Roles disponibles en el sistema"""
    DIRECTIVO = "directivo"
    COORDINADORA_GESTION = "coordinadora_gestion"
    MEDICO = "medico"
    ENFERMERIA = "enfermeria"
    ADMINISTRATIVO = "administrativo"
    INVITADO = "invitado"


class Permission(str, Enum):
    """Permisos granulares del sistema"""
    # Datos de pacientes
    VER_DATOS_PACIENTE = "ver_datos_paciente"
    VER_HISTORIA_CLINICA = "ver_historia_clinica"
    VER_DATOS_SENSIBLES = "ver_datos_sensibles"  # DNI completo, etc.

    # Estadísticas
    VER_CAMAS_DISPONIBLES = "ver_camas_disponibles"
    VER_ESTADISTICAS_SERVICIO = "ver_estadisticas_servicio"
    VER_VOLUMEN_ATENCION = "ver_volumen_atencion"

    # Información general
    VER_HORARIOS = "ver_horarios"
    VER_SERVICIOS = "ver_servicios"
    VER_PRESTADORES = "ver_prestadores"


# Matriz de permisos por rol
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.DIRECTIVO: [
        # Acceso total
        Permission.VER_DATOS_PACIENTE,
        Permission.VER_HISTORIA_CLINICA,
        Permission.VER_DATOS_SENSIBLES,
        Permission.VER_CAMAS_DISPONIBLES,
        Permission.VER_ESTADISTICAS_SERVICIO,
        Permission.VER_VOLUMEN_ATENCION,
        Permission.VER_HORARIOS,
        Permission.VER_SERVICIOS,
        Permission.VER_PRESTADORES,
    ],
    Role.COORDINADORA_GESTION: [
        # Mismo acceso que directivo (gestión hospitalaria)
        Permission.VER_DATOS_PACIENTE,
        Permission.VER_HISTORIA_CLINICA,
        Permission.VER_DATOS_SENSIBLES,
        Permission.VER_CAMAS_DISPONIBLES,
        Permission.VER_ESTADISTICAS_SERVICIO,
        Permission.VER_VOLUMEN_ATENCION,
        Permission.VER_HORARIOS,
        Permission.VER_SERVICIOS,
        Permission.VER_PRESTADORES,
    ],
    Role.MEDICO: [
        # Acceso clínico
        Permission.VER_DATOS_PACIENTE,
        Permission.VER_HISTORIA_CLINICA,
        Permission.VER_DATOS_SENSIBLES,
        Permission.VER_CAMAS_DISPONIBLES,
        Permission.VER_HORARIOS,
        Permission.VER_SERVICIOS,
    ],
    Role.ENFERMERIA: [
        # Acceso operativo
        Permission.VER_DATOS_PACIENTE,
        Permission.VER_CAMAS_DISPONIBLES,
        Permission.VER_HORARIOS,
    ],
    Role.ADMINISTRATIVO: [
        # Acceso administrativo
        Permission.VER_HORARIOS,
        Permission.VER_SERVICIOS,
        Permission.VER_PRESTADORES,
    ],
    Role.INVITADO: [
        # Acceso mínimo
        Permission.VER_HORARIOS,
        Permission.VER_SERVICIOS,
    ],
}


class PermissionChecker:
    """Validador de permisos"""

    @staticmethod
    def has_permission(user_role: str, permission: Permission) -> bool:
        """
        Verificar si un rol tiene un permiso específico

        Args:
            user_role: Rol del usuario (string)
            permission: Permiso a verificar

        Returns:
            True si tiene el permiso, False si no
        """
        try:
            # Convertir string a enum
            role = Role(user_role.lower())

            # Verificar si el rol tiene el permiso
            role_perms = ROLE_PERMISSIONS.get(role, [])
            has_perm = permission in role_perms

            if not has_perm:
                logger.warning(f"❌ Permiso denegado: {user_role} no tiene {permission.value}")

            return has_perm

        except ValueError:
            logger.error(f"❌ Rol inválido: {user_role}")
            return False

    @staticmethod
    def get_user_permissions(user_role: str) -> List[Permission]:
        """Obtener todos los permisos de un rol"""
        try:
            role = Role(user_role.lower())
            return ROLE_PERMISSIONS.get(role, [])
        except ValueError:
            return []

    @staticmethod
    def can_access_patient_data(user_role: str) -> bool:
        """Verificar si puede acceder a datos de pacientes"""
        return PermissionChecker.has_permission(
            user_role,
            Permission.VER_DATOS_PACIENTE
        )

    @staticmethod
    def can_access_clinical_history(user_role: str) -> bool:
        """Verificar si puede acceder a historia clínica"""
        return PermissionChecker.has_permission(
            user_role,
            Permission.VER_HISTORIA_CLINICA
        )

    @staticmethod
    def can_access_sensitive_data(user_role: str) -> bool:
        """Verificar si puede ver datos sensibles (DNI completo, etc.)"""
        return PermissionChecker.has_permission(
            user_role,
            Permission.VER_DATOS_SENSIBLES
        )

    @staticmethod
    def can_access_statistics(user_role: str) -> bool:
        """Verificar si puede ver estadísticas"""
        return PermissionChecker.has_permission(
            user_role,
            Permission.VER_ESTADISTICAS_SERVICIO
        )


def mask_sensitive_data(data: str, user_role: str) -> str:
    """
    Enmascarar datos sensibles según rol del usuario

    Ejemplo: DNI 12345678 → 1234****
    """
    if PermissionChecker.can_access_sensitive_data(user_role):
        return data  # Mostrar completo

    # Enmascarar
    if len(data) >= 6:
        return data[:4] + "*" * (len(data) - 4)
    return "****"


# Singleton
permission_checker = PermissionChecker()
