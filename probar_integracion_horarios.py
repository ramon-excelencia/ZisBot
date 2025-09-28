"""
Script para probar la integración completa de horarios de atención desde el chatbot
"""
import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.chatbot_service import ChatbotService
from app.services.hospital_data_service import HospitalDataService
from app.services.orm_hospital_service import orm_hospital_service

async def probar_integracion_horarios():
    """Probar la integración completa de horarios de atención"""
    print("="*60)
    print("PRUEBA DE INTEGRACION HORARIOS DE ATENCION")
    print("="*60)

    # 1. Probar directamente el ORM service
    print("\n1. PROBANDO ORM SERVICE DIRECTAMENTE...")
    try:
        servicios_result = await orm_hospital_service.obtener_servicios_con_horarios()
        if servicios_result.success:
            print(f"OK Servicios encontrados: {len(servicios_result.data['servicios'])}")
            for servicio in servicios_result.data['servicios'][:3]:  # Solo mostrar primeros 3
                print(f"   - {servicio['nombre']} (ID: {servicio['servicio_id']})")
        else:
            print(f"ERROR obteniendo servicios: {servicios_result.message}")
            return
    except Exception as e:
        print(f"ERROR en ORM service: {e}")
        return

    # 2. Probar hospital_data_service con el nuevo método
    print("\n2. PROBANDO HOSPITAL DATA SERVICE...")
    hospital_service = HospitalDataService()
    try:
        # Usar el primer servicio encontrado para la prueba
        primer_servicio = servicios_result.data['servicios'][0]['nombre']
        print(f"Probando con servicio: {primer_servicio}")

        horarios_result = await hospital_service.get_horarios_atencion(primer_servicio)
        if horarios_result['encontrado']:
            print("OK Hospital Data Service funcionando correctamente")
            print(f"   Servicio: {horarios_result['servicio']}")
            print(f"   Horarios encontrados: {len(horarios_result['horarios'])}")
            for horario in horarios_result['horarios'][:2]:  # Mostrar primeros 2
                print(f"   - {horario['dia']}: {horario['hora_inicio']}-{horario['hora_fin']} ({horario['cantidad_turnos']} turnos)")
        else:
            print(f"ERROR en Hospital Data Service: {horarios_result.get('error')}")
            return
    except Exception as e:
        print(f"ERROR en Hospital Data Service: {e}")
        return

    # 3. Probar chatbot service con mensaje natural
    print("\n3. PROBANDO CHATBOT SERVICE...")
    chatbot = ChatbotService()
    try:
        # Probar con diferentes variaciones de consulta
        consultas_prueba = [
            f"¿Cuáles son los horarios de atención de {primer_servicio}?",
            f"horarios {primer_servicio}",
            "horarios de laboratorio"
        ]

        for i, consulta in enumerate(consultas_prueba, 1):
            print(f"\n3.{i}. Probando consulta: '{consulta}'")
            response = await chatbot.process_message(consulta, "user_test_123", "directivo")

            if "horarios" in response.lower() and ("no encontrado" not in response.lower()):
                print("OK Chatbot respondio correctamente")
                print(f"   Respuesta (primeros 200 chars): {response[:200]}...")
            else:
                print("ERROR Chatbot no detecto o no pudo procesar la consulta")
                print(f"   Respuesta: {response[:300]}...")

    except Exception as e:
        print(f"ERROR en Chatbot Service: {e}")
        return

    print("\n" + "="*60)
    print("PRUEBA DE INTEGRACION COMPLETADA")
    print("="*60)

async def main():
    await probar_integracion_horarios()

if __name__ == "__main__":
    asyncio.run(main())