#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para iniciar el servidor ZisBot
"""
import sys
import os
import uvicorn

# Asegurar que el path está correcto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("INICIANDO ZISBOT - HOSPITAL REGIONAL")
    print("=" * 50)
    print("Backend: http://localhost:8008")
    print("Frontend: http://localhost:3006")
    print("Documentacion: http://localhost:8008/api/docs")
    print("=" * 50)

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8008,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("Instalando dependencias faltantes...")
        os.system("venv\\Scripts\\pip install -r requirements.txt")
        print("Reintentando...")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8008)