import os
from dotenv import load_dotenv

load_dotenv(override=True)

API_URL = os.getenv("API_URL")
APP_ENV = os.getenv("APP_ENV", "production")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "50"))
#en este config, declaro las variables que tomo desde el .env y uso de manera global en el proyecto, por ejemplo en Redis y Services
class Config:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    API_BASE_MERCEDARIO = os.getenv("API_BASE_MERCEDARIO")
    API_BASE_HCWEB = os.getenv("API_BASE_HCWEB")
    
    # ZisMed/Hospital Regional Configuration
    DEFAULT_HOSPITAL_ID = os.getenv("DEFAULT_HOSPITAL_ID", "3")  # Hospital Regional ID
    DEFAULT_HOSPITAL_NAME = os.getenv("DEFAULT_HOSPITAL_NAME", "Hospital Regional")
    PROVIDER_TYPE = os.getenv("PROVIDER_TYPE", "zismed")