"""
Configuración centralizada para ZisBot
Maneja variables de entorno, configuración de base de datos, APIs externas, etc.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar variables de entorno del archivo .env
load_dotenv(BASE_DIR / ".env")

class Settings:
    """Configuración principal del sistema"""

    # Configuración de la aplicación
    APP_NAME: str = "ZisBot - Hospital Regional Santiago del Estero"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Configuración del servidor
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8008))

    # Configuración JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET_KEY", "zismed_hospital_regional_secret_key_2024")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 8

    # Configuración de CORS
    CORS_ORIGINS: list = ["*"]

    # APIs externas
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Configuración de base de datos
    DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_SERVER: str = os.getenv("DB_SERVER", "SRVZISMED\\SQLEXPRESS")
    DB_NAME: str = os.getenv("DB_NAME", "BdHospital")
    DB_TRUSTED_CONNECTION: bool = True

    # MongoDB (para memoria de conversaciones)
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
    MONGO_DB: str = os.getenv("MONGO_DB", "zisbot_conversations")

    # Configuración del chatbot
    DEFAULT_HOSPITAL_ID: str = "3"  # Hospital Regional Santiago del Estero
    MAX_CONVERSATION_HISTORY: int = 50
    AI_RESPONSE_TIMEOUT: int = 30

    # Configuración de logs
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "zisbot.log")

    # Endpoints del backend ZisMed (si existen)
    ZISMED_BASE_URL: Optional[str] = os.getenv("ZISMED_BASE_URL", None)
    ZISMED_API_TOKEN: Optional[str] = os.getenv("ZISMED_API_TOKEN", None)

    # Sistema ZisMed C# WebHospital URLs
    ZISMED_SYSTEM_URL: str = os.getenv("ZISMED_SYSTEM_URL", "http://localhost:5955")

    # Credenciales del chatbot para autenticación automática
    CHATBOT_USER_CUIL: str = os.getenv("CHATBOT_USER_CUIL", "27357388827")
    CHATBOT_USER_PASSWORD: str = os.getenv("CHATBOT_USER_PASSWORD", "simon0")

    @classmethod
    def get_database_connection_string(cls) -> str:
        """Genera la cadena de conexión a SQL Server"""
        # Usar cadena de conexión del .env si está disponible
        connection_string = os.getenv("SQLSERVER_CONNECTION_STRING")
        if connection_string:
            return connection_string

        # Fallback a configuración tradicional
        if cls.DB_TRUSTED_CONNECTION:
            return f"DRIVER={{{cls.DB_DRIVER}}};SERVER={cls.DB_SERVER};DATABASE={cls.DB_NAME};Trusted_Connection=yes;"
        else:
            username = os.getenv("DB_USERNAME", "")
            password = os.getenv("DB_PASSWORD", "")
            return f"DRIVER={{{cls.DB_DRIVER}}};SERVER={cls.DB_SERVER};DATABASE={cls.DB_NAME};UID={username};PWD={password};"

# Instancia global de configuración
settings = Settings()