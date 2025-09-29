"""
Conexión directa a base de datos SQL Server DBH_Test
Configuración con SQLAlchemy para evitar SQL directo
"""
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import urllib.parse

logger = logging.getLogger(__name__)

# Configuración de la base de datos - PRODUCCIÓN ZISMED
DB_CONFIG = {
    'server': '172.16.30.1',
    'database': 'DBH_Test',
    'username': 'Zismed',
    'password': 'donJuane2e',
    'driver': 'ODBC Driver 17 for SQL Server'
}

# Configuración secundaria para HCWeb (integración)
DB_CONFIG_HCWEB = {
    'server': '172.16.30.1',
    'database': 'TurnosHistoriaClinicaWeb',
    'username': 'usrProduccion',
    'password': 'C@picua2018',
    'driver': 'ODBC Driver 17 for SQL Server'
}

class DatabaseConnection:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.Base = declarative_base()
        self._create_engine()

    def _create_engine(self):
        """Crear engine de SQLAlchemy para SQL Server"""
        try:
            # URL encode de la contraseña para caracteres especiales
            password_encoded = urllib.parse.quote_plus(DB_CONFIG['password'])

            # Crear connection string para SQL Server
            connection_string = (
                f"mssql+pyodbc://{DB_CONFIG['username']}:{password_encoded}@"
                f"{DB_CONFIG['server']}/{DB_CONFIG['database']}?"
                f"driver={urllib.parse.quote_plus(DB_CONFIG['driver'])}&"
                f"TrustServerCertificate=yes&Encrypt=no"
            )

            # Crear engine con pool de conexiones
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False  # Cambiar a True para debug SQL
            )

            # Crear SessionLocal
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            logger.info(f"✅ Engine SQL Server creado para {DB_CONFIG['database']}")

        except Exception as e:
            logger.error(f"❌ Error creando engine SQL Server: {e}")
            raise

    def test_connection(self):
        """Probar conexión a la base de datos"""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test"))
                test_value = result.fetchone()[0]
                logger.info(f"✅ Conexión SQL Server exitosa: test = {test_value}")
                return True
        except Exception as e:
            logger.error(f"❌ Error probando conexión: {e}")
            return False

    def get_session(self):
        """Obtener sesión de base de datos"""
        if not self.SessionLocal:
            raise RuntimeError("Base de datos no inicializada")
        return self.SessionLocal()

    def execute_query(self, query: str, params: dict = None):
        """Ejecutar query sin SQL directo usando text()"""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query), params or {})
                return result.fetchall()
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            raise

    def execute_stored_procedure(self, proc_name: str, params: dict = None):
        """Ejecutar stored procedure"""
        try:
            with self.engine.connect() as connection:
                # Construir llamada al stored procedure
                param_str = ", ".join([f":{key}" for key in (params or {}).keys()])
                query = f"EXEC {proc_name} {param_str}" if param_str else f"EXEC {proc_name}"

                result = connection.execute(text(query), params or {})
                return result.fetchall()
        except Exception as e:
            logger.error(f"❌ Error ejecutando stored procedure {proc_name}: {e}")
            raise

# Instancia global
db_connection = DatabaseConnection()