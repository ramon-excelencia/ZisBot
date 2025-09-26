#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iniciar servidor ZisBot sin autoreload para debugging
"""
import uvicorn
from app.main import app
import sys
import os

# Configurar UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    print("=" * 60)
    print("ZISBOT - SERVIDOR SIN AUTORELOAD PARA DEBUGGING")
    print("=" * 60)
    print("Puerto: 8008")
    print("Docs: http://localhost:8008/api/docs")
    print("Frontend: http://localhost:3003")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8009,
        reload=False,  # Sin autoreload
        log_level="info"
    )