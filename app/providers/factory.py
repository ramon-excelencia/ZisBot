from typing import Dict, Type
from .base import BaseProvider, ProviderConfig
from .api_provider import ApiProvider
from .hcweb import HCWebProvider


class ProviderFactory:
    """Factory to create provider instances"""

    _providers: Dict[str, Type[BaseProvider]] = {
        "zismed": ApiProvider,  # Usar provider API (arquitectura limpia)
        "zismed_real": ApiProvider,
        "api": ApiProvider,
        "hcweb": HCWebProvider
    }
    
    @classmethod
    def create_provider(cls, config: ProviderConfig) -> BaseProvider:
        """Create provider instance based on configuration"""
        provider_class = cls._providers.get(config.provider_name.lower())
        
        if not provider_class:
            raise ValueError(f"Unknown provider: {config.provider_name}")
        
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names"""
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseProvider]):
        """Register new provider type"""
        cls._providers[name] = provider_class