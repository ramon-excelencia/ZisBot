import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator, Optional
import urllib.parse
from contextlib import contextmanager
import logging

from app.models.entities import ZisMedBase

logger = logging.getLogger(__name__)

class ZisMedDatabase:
    """Conexión a base de datos ZisMed (SQL Server)"""

    def __init__(self):
        self.engine: Optional[object] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._setup_connection()

    def _setup_connection(self):
        """Configurar conexión a ZisMed SQL Server"""

        # Configuración de conexión ZisMed
        DB_HOST = os.getenv("ZISMED_DB_HOST", "168.226.219.57")
        DB_PORT = os.getenv("ZISMED_DB_PORT", "2424")
        DB_NAME = os.getenv("ZISMED_DB_NAME", "DBH_Test")
        DB_USER = os.getenv("ZISMED_DB_USER", "sa")
        DB_PASSWORD = os.getenv("ZISMED_DB_PASSWORD", "Simon1")

        # Construir URL de conexión SQL Server con autenticación
        password_encoded = urllib.parse.quote_plus(DB_PASSWORD)

        # URL para SQL Server con pyodbc
        DATABASE_URL = f"mssql+pyodbc://{DB_USER}:{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server&charset=utf8&autocommit=true"

        try:
            # Crear engine con configuración optimizada
            self.engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,  # True para debug SQL
                connect_args={
                    "timeout": 30,
                    "connect_timeout": 20,
                }
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            logger.info(f"✅ Conexión ZisMed configurada: {DB_HOST}:{DB_PORT}/{DB_NAME}")

        except Exception as e:
            logger.error(f"❌ Error configurando conexión ZisMed: {e}")
            raise

    def get_session(self) -> Generator[Session, None, None]:
        """Obtener sesión de base de datos ZisMed"""
        if not self.SessionLocal:
            raise RuntimeError("Base de datos ZisMed no inicializada")

        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def get_session_context(self):
        """Context manager para sesiones"""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def test_connection(self) -> bool:
        """Probar conexión a ZisMed"""
        try:
            with self.get_session_context() as db:
                result = db.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                logger.info(f"✅ Test conexión ZisMed exitoso: {test_value}")
                return True
        except Exception as e:
            logger.error(f"❌ Error test conexión ZisMed: {e}")
            return False

    def get_database_info(self) -> dict:
        """Obtener información de la base de datos"""
        try:
            with self.get_session_context() as db:
                # Información del servidor
                server_info = db.execute(text("SELECT @@SERVERNAME as server_name, @@VERSION as version")).fetchone()

                # Contar registros principales
                turnos_count = db.execute(text("SELECT COUNT(*) FROM Turnos WHERE Anulado = 0")).scalar()
                pacientes_count = db.execute(text("SELECT COUNT(*) FROM Pacientes WHERE Anulado = 0")).scalar()
                especialidades_count = db.execute(text("SELECT COUNT(*) FROM Especialidades WHERE Anulado = 0")).scalar()

                return {
                    "servidor": server_info.server_name if server_info else "Unknown",
                    "version": server_info.version[:50] if server_info else "Unknown",
                    "turnos_total": turnos_count,
                    "pacientes_total": pacientes_count,
                    "especialidades_total": especialidades_count,
                    "conectado": True
                }
        except Exception as e:
            logger.error(f"Error obteniendo info BD: {e}")
            return {"conectado": False, "error": str(e)}

# Instancia global
zismed_db = ZisMedDatabase()

def get_zismed_session() -> Generator[Session, None, None]:
    """Dependency para FastAPI - obtener sesión ZisMed"""
    yield from zismed_db.get_session()

def get_zismed_db() -> ZisMedDatabase:
    """Obtener instancia de base ZisMed"""
    return zismed_db