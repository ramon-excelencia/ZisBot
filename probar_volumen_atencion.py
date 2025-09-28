"""
Script para probar la funcionalidad completa de volumen de atención
"""
import asyncio
import sys
import os
from datetime import date, timedelta

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.orm_hospital_service import orm_hospital_service
from app.services.hospital_data_service import HospitalDataService

async def probar_volumen_atencion():
    """Probar la funcionalidad completa de volumen de atención"""
    print("="*60)
    print("PRUEBA DE VOLUMEN DE ATENCION")
    print("="*60)

    # 1. Probar método ORM directamente
    print("\n1. PROBANDO ORM SERVICE DIRECTAMENTE...")
    try:
        # Probar con últimos 30 días
        hoy = date.today()
        fecha_desde = hoy - timedelta(days=30)

        print(f"Probando volumen general últimos 30 días ({fecha_desde} a {hoy})")

        volumen_result = await orm_hospital_service.obtener_volumen_atencion(
            fecha_desde=fecha_desde,
            fecha_hasta=hoy
        )

        if volumen_result.success:
            data = volumen_result.data
            print("OK ORM Service funcionando correctamente")
            print(f"   Total pacientes atendidos: {data.get('total_pacientes_atendidos', 0)}")
            print(f"   Total turnos: {data.get('total_turnos', 0)}")
            print(f"   Servicios activos: {len(data.get('servicios', []))}")
            print(f"   Días con atención: {data.get('estadisticas', {}).get('dias_con_atencion', 0)}")

            # Mostrar servicios
            servicios = data.get('servicios', [])
            if servicios:
                print("   Servicios encontrados:")
                for servicio in servicios[:3]:  # Top 3
                    print(f"     - {servicio['nombre']}: {servicio['pacientes_atendidos']} pacientes")
            else:
                print("   No se encontraron servicios con atención")

        else:
            print(f"ERROR en ORM Service: {volumen_result.message}")
            return

    except Exception as e:
        print(f"ERROR en ORM Service: {e}")
        return

    # 2. Probar hospital_data_service
    print("\n2. PROBANDO HOSPITAL DATA SERVICE...")
    hospital_service = HospitalDataService()
    try:
        # Probar sin servicio específico (todos los servicios)
        print("Probando volumen general...")

        volumen_result = await hospital_service.get_volumen_pacientes(
            fecha_desde=fecha_desde,
            fecha_hasta=hoy
        )

        if volumen_result['encontrado']:
            print("OK Hospital Data Service funcionando correctamente")
            print(f"   Servicio: {volumen_result['servicio']}")
            print(f"   Período: {volumen_result['periodo']}")
            print(f"   Pacientes atendidos: {volumen_result['total_pacientes_atendidos']}")
            print(f"   Total turnos: {volumen_result['total_turnos']}")

            # Mostrar desglose por días (primeros 3)
            desglose = volumen_result.get('desglose_por_dia', [])
            if desglose:
                print("   Desglose por día (últimos 3):")
                for dia_info in desglose[-3:]:
                    print(f"     - {dia_info['fecha']}: {dia_info['pacientes_atendidos']} pacientes")

        else:
            print(f"ERROR en Hospital Data Service: {volumen_result.get('error')}")
            return

    except Exception as e:
        print(f"ERROR en Hospital Data Service: {e}")
        return

    # 3. Probar con servicio específico
    print("\n3. PROBANDO CON SERVICIO ESPECÍFICO...")
    try:
        # Usar laboratorio si está disponible
        volumen_servicio = await hospital_service.get_volumen_pacientes(
            servicio_nombre="laboratorio",
            fecha_desde=fecha_desde,
            fecha_hasta=hoy
        )

        if volumen_servicio['encontrado']:
            print("OK Consulta por servicio específico funcionando")
            print(f"   Servicio: {volumen_servicio['servicio']}")
            print(f"   Pacientes atendidos: {volumen_servicio['total_pacientes_atendidos']}")
        else:
            print(f"INFO: No se encontró servicio 'laboratorio' o no tiene datos: {volumen_servicio.get('error')}")

    except Exception as e:
        print(f"ERROR consultando servicio específico: {e}")

    # 4. Probar detección de rangos de fechas
    print("\n4. PROBANDO DETECCIÓN DE RANGOS DE FECHAS...")
    from app.services.chatbot_service import ChatbotService

    chatbot = ChatbotService.__new__(ChatbotService)  # Crear instancia sin init
    chatbot.groq_client = None  # Mock para evitar error de API key

    # Probar diferentes patrones de fecha
    patrones_prueba = [
        "volumen de laboratorio esta semana",
        "pacientes atendidos últimos 7 días",
        "cantidad atendidos del 01/10/2024 al 15/10/2024",
        "consultas por servicio entre el 1 y el 15 de octubre"
    ]

    for patron in patrones_prueba:
        try:
            print(f"   Probando: '{patron}'")
            fecha_desde, fecha_hasta = chatbot._extract_date_range(patron.lower())
            print(f"     -> Detectado: {fecha_desde} a {fecha_hasta}")
        except Exception as e:
            print(f"     -> ERROR: {e}")

    print("\n" + "="*60)
    print("PRUEBA DE VOLUMEN DE ATENCION COMPLETADA")
    print("="*60)

async def main():
    await probar_volumen_atencion()

if __name__ == "__main__":
    asyncio.run(main())