#!/usr/bin/env python3
"""
Script para explorar datos de horarios en la base de datos
"""
import sys
import os
sys.path.append('.')

from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database.connection import DatabaseConnection

def explore_schedule_data():
    """Explorar datos de horarios desde diferentes fuentes"""

    # Crear conexión a la base de datos
    db = DatabaseConnection()
    engine = db.engine
    Session = sessionmaker(bind=engine)
    session = Session()

    print("EXPLORANDO DATOS DE HORARIOS...")
    print("=" * 50)

    try:
        # 1. Buscar servicios únicos en turnos
        print("\n1. SERVICIOS EN TURNOS:")
        servicios_query = text("""
            SELECT DISTINCT s.Nombre as Servicio, COUNT(*) as Total_Turnos
            FROM Turnos t
            INNER JOIN Servicios s ON t.ServicioID = s.ServicioID
            WHERE t.Anulado = 0 AND s.Anulado = 0
            GROUP BY s.Nombre
            ORDER BY COUNT(*) DESC
        """)
        servicios = session.execute(servicios_query).fetchall()
        for servicio in servicios[:10]:
            print(f"  - {servicio[0]}: {servicio[1]} turnos")

        # 2. Horarios típicos por servicio (top 3 servicios)
        if servicios:
            print(f"\n2. HORARIOS DEL SERVICIO MÁS USADO: {servicios[0][0]}")
            horarios_query = text("""
                SELECT DISTINCT
                    CONVERT(varchar(5), t.Fecha_Hora, 108) as Hora_Inicio,
                    t.Hora_Hasta,
                    DATEPART(WEEKDAY, t.Fecha_Hora) as Dia_Semana,
                    COUNT(*) as Frecuencia
                FROM Turnos t
                INNER JOIN Servicios s ON t.ServicioID = s.ServicioID
                WHERE t.Anulado = 0 AND s.Nombre = :servicio_nombre
                  AND t.Fecha_Hora >= DATEADD(month, -6, GETDATE())
                GROUP BY CONVERT(varchar(5), t.Fecha_Hora, 108), t.Hora_Hasta, DATEPART(WEEKDAY, t.Fecha_Hora)
                ORDER BY Dia_Semana, Hora_Inicio
            """)
            horarios = session.execute(horarios_query, {"servicio_nombre": servicios[0][0]}).fetchall()

            dias = {1: "Domingo", 2: "Lunes", 3: "Martes", 4: "Miércoles", 5: "Jueves", 6: "Viernes", 7: "Sábado"}
            for horario in horarios[:15]:
                dia_nombre = dias.get(horario[2], f"Día {horario[2]}")
                print(f"  - {dia_nombre}: {horario[0]} - {horario[1]} ({horario[3]} turnos)")

        # 3. Prestadores con más turnos
        print(f"\n3. PRESTADORES MAS ACTIVOS:")
        prestadores_query = text("""
            SELECT TOP 5
                p.Nombre as Prestador,
                e.Nombre as Especialidad,
                COUNT(*) as Total_Turnos,
                MIN(CONVERT(varchar(5), t.Fecha_Hora, 108)) as Hora_Mas_Temprana,
                MAX(CONVERT(varchar(5), t.Fecha_Hora, 108)) as Hora_Mas_Tarde
            FROM Turnos t
            INNER JOIN Prestadores p ON t.PrestadorID = p.PrestadorID
            LEFT JOIN Especialidades e ON p.EspecialidadID = e.EspecialidadID
            WHERE t.Anulado = 0 AND p.Anulado = 0
              AND t.Fecha_Hora >= DATEADD(month, -3, GETDATE())
            GROUP BY p.Nombre, e.Nombre
            ORDER BY COUNT(*) DESC
        """)
        prestadores = session.execute(prestadores_query).fetchall()
        for prestador in prestadores:
            print(f"  - {prestador[0]} ({prestador[1] or 'Sin especialidad'})")
            print(f"    Turnos: {prestador[2]}, Horario: {prestador[3]} - {prestador[4]}")

        # 4. Especialidades disponibles
        print(f"\n4. ESPECIALIDADES CON TURNOS ACTIVOS:")
        especialidades_query = text("""
            SELECT DISTINCT
                e.Nombre as Especialidad,
                COUNT(*) as Total_Turnos
            FROM Turnos t
            INNER JOIN Prestadores p ON t.PrestadorID = p.PrestadorID
            INNER JOIN Especialidades e ON p.EspecialidadID = e.EspecialidadID
            WHERE t.Anulado = 0 AND p.Anulado = 0 AND e.Anulado = 0
              AND t.Fecha_Hora >= DATEADD(month, -3, GETDATE())
            GROUP BY e.Nombre
            ORDER BY COUNT(*) DESC
        """)
        especialidades = session.execute(especialidades_query).fetchall()
        for esp in especialidades[:10]:
            print(f"  - {esp[0]}: {esp[1]} turnos")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    explore_schedule_data()