#!/usr/bin/env python3
import sys
import os
sys.path.append('.')

from app.utils.auth import create_jwt_token

def generate_test_token():
    """Generar token de prueba para Yanet Villalba"""
    user_data = {
        "user_id": "yanet_villalba",
        "user_name": "Yanet Villalba",
        "username": "yanet.villalba",
        "first_name": "Yanet",
        "last_name": "Villalba",
        "role": "medico",
        "sector": "emergencias"
    }

    token = create_jwt_token(user_data)
    print(f"Token generado para pruebas:")
    print(token)
    return token

if __name__ == "__main__":
    generate_test_token()