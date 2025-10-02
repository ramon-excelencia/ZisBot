"""
Rotador de API Keys de Groq
Gestiona múltiples API keys para evitar rate limits
"""
import os
import logging
from typing import List, Optional
from threading import Lock

logger = logging.getLogger(__name__)

class GroqKeyRotator:
    """
    Gestiona rotación automática de API keys cuando se alcanzan rate limits
    """

    def __init__(self):
        self.api_keys: List[str] = []
        self.current_index = 0
        self.lock = Lock()
        self._load_keys()

    def _load_keys(self):
        """Cargar todas las API keys desde variables de entorno"""
        # Key principal
        primary_key = os.getenv("GROQ_API_KEY")
        if primary_key:
            self.api_keys.append(primary_key)

        # Keys adicionales (GROQ_API_KEY_2, GROQ_API_KEY_3, etc.)
        i = 2
        while True:
            additional_key = os.getenv(f"GROQ_API_KEY_{i}")
            if additional_key:
                self.api_keys.append(additional_key)
                i += 1
            else:
                break

        if not self.api_keys:
            logger.error("❌ No se encontraron API keys de Groq")
        else:
            logger.info(f"✅ Cargadas {len(self.api_keys)} API keys de Groq")

    def get_current_key(self) -> Optional[str]:
        """Obtener la key actual"""
        if not self.api_keys:
            return None
        return self.api_keys[self.current_index]

    def rotate_key(self) -> Optional[str]:
        """
        Rotar a la siguiente key disponible
        Returns: La nueva key activa, o None si no hay más keys
        """
        with self.lock:
            if len(self.api_keys) <= 1:
                logger.warning("⚠️ No hay keys adicionales para rotar")
                return self.get_current_key()

            old_index = self.current_index
            self.current_index = (self.current_index + 1) % len(self.api_keys)

            logger.info(f"🔄 Rotando key: índice {old_index} → {self.current_index}")
            return self.api_keys[self.current_index]

    def get_total_keys(self) -> int:
        """Obtener cantidad total de keys disponibles"""
        return len(self.api_keys)

    def reset(self):
        """Resetear al índice 0"""
        with self.lock:
            self.current_index = 0
            logger.info("🔄 Keys reseteadas al índice 0")

# Singleton instance
_rotator_instance = None

def get_groq_key_rotator() -> GroqKeyRotator:
    """Obtener instancia singleton del rotador"""
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = GroqKeyRotator()
    return _rotator_instance
