#!/usr/bin/env python3
"""Script para probar historia clínica completa directamente"""
import asyncio
import sys
import os
from datetime import datetime

# Agregar el path del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.orm_hospital_service import orm_hospital_service

async def test_historia_clinica():
    print("PROBANDO HISTORIA CLINICA COMPLETA")
    print("=" * 50)

    dni = "38112227"
    print(f"DNI a buscar: {dni}")

    try:
        # Probar método completo
        print("\n1. Probando obtener_historia_clinica_completa...")
        result = await orm_hospital_service.obtener_historia_clinica_completa(dni=dni)

        print(f"Tipo de resultado: {type(result)}")
        print(f"Tiene success? {hasattr(result, 'success')}")
        if hasattr(result, 'success'):
            print(f"Success: {result.success}")
            if result.success:
                print(f"Data disponible: {result.data is not None}")
                if result.data:
                    print(f"Datos del paciente: {result.data.get('paciente', {}).get('nombre_completo', 'NO DISPONIBLE')}")
                    print(f"Internaciones: {len(result.data.get('internaciones', []))}")
                    print(f"Turnos: {len(result.data.get('turnos_medicos', []))}")
            else:
                print(f"Error: {getattr(result, 'message', 'No disponible')}")
                print(f"Error detallado: {getattr(result, 'error', 'No disponible')}")
        else:
            print(f"Resultado no tiene formato ApiResponse: {result}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    try:
        # Probar método básico para comparar
        print("\n2. Probando buscar_paciente_por_dni (para comparar)...")
        result_basic = await orm_hospital_service.buscar_paciente_por_dni(dni, 3)

        print(f"Resultado básico - Success: {result_basic.success}")
        if result_basic.success:
            print(f"Paciente básico: {result_basic.data.get('nombre_completo', 'NO DISPONIBLE')}")
        else:
            print(f"Error básico: {result_basic.message}")

    except Exception as e:
        print(f"ERROR en metodo basico: {e}")

if __name__ == "__main__":
    asyncio.run(test_historia_clinica())