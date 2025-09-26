import os
from typing import Dict, Optional
from pydantic import BaseModel


class APIConfig(BaseModel):
    groq_api_key: str  # Changed from openai_api_key to groq_api_key
    model_name: str = "llama-3.1-70b-versatile"  # Default Groq model
    provider_type: str  # "zismed" | "hcweb"
    connection_string: str
    hospital_configs: Dict[str, Dict] = {}


class AuthService:
    def __init__(self):
        self.configs: Dict[str, APIConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load API configurations from environment"""
        # Default configuration
        default_config = APIConfig(
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            model_name=os.getenv("MODEL_NAME", "llama-3.1-70b-versatile"),
            provider_type=os.getenv("PROVIDER_TYPE", "zismed"),
            connection_string=os.getenv("SQLSERVER_CONNECTION_STRING", ""),
            hospital_configs={}
        )
        
        # You can add multiple configurations for different clients
        self.configs["default"] = default_config
    
    def get_config(self, client_id: str = "default") -> Optional[APIConfig]:
        """Get configuration for specific client"""
        return self.configs.get(client_id)
    
    def validate_api_key(self, api_key: str, client_id: str = "default") -> bool:
        """Validate API key for client"""
        config = self.get_config(client_id)
        if not config:
            return False
        return config.groq_api_key == api_key
    
    def add_client_config(self, client_id: str, config: APIConfig):
        """Add new client configuration"""
        self.configs[client_id] = config


# Global auth service instance
auth_service = AuthService()