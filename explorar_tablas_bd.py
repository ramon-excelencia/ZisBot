#!/usr/bin/env python3
"""Script para explorar tablas de la base de datos ZISMED"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de conexión directa a SQL Server
DATABASE_URL = os.getenv('DATABASE_URL_SQLSERVER',
    "mssql+pyodbc://sa:Zismed@10.0.20.35:1433/ZISMED?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes")

print(f"Conectando a: {DATABASE_URL}")

try:
    # Crear motor de base de datos
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Probar conexión
    result = session.execute(text("SELECT 1 as test"))
    print("✅ Conexión exitosa a la base de datos")

    print("\n=== BUSCANDO TABLAS RELACIONADAS CON HISTORIAS CLÍNICAS ===")

    # Buscar tablas relacionadas con historias clínicas
    tables_query = """
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    AND (TABLE_NAME LIKE '%evolu%'
         OR TABLE_NAME LIKE '%diagno%'
         OR TABLE_NAME LIKE '%histo%'
         OR TABLE_NAME LIKE '%epis%'
         OR TABLE_NAME LIKE '%consulta%'
         OR TABLE_NAME LIKE '%medic%'
         OR TABLE_NAME LIKE '%nota%'
         OR TABLE_NAME LIKE '%enferm%'
         OR TABLE_NAME LIKE '%evoluc%')
    ORDER BY TABLE_NAME
    """

    result = session.execute(text(tables_query))
    tables = result.fetchall()

    print(f"Encontradas {len(tables)} tablas relacionadas:")
    for table in tables:
        print(f"- {table[0]}")

    print("\n=== EXPLORANDO ESTRUCTURA DE TABLAS PRINCIPALES ===")

    # Explorar algunas tablas específicas
    important_tables = ['Internaciones', 'Turnos', 'Pacientes']

    for table_name in important_tables:
        print(f"\n--- Estructura de {table_name} ---")
        try:
            columns_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
            """

            result = session.execute(text(columns_query))
            columns = result.fetchall()

            if columns:
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    max_len = f"({col[3]})" if col[3] else ""
                    print(f"  {col[0]}: {col[1]}{max_len} {nullable}")
            else:
                print(f"  ⚠️ Tabla {table_name} no encontrada")

        except Exception as e:
            print(f"  ❌ Error explorando {table_name}: {e}")

    # Buscar datos de muestra de un paciente específico
    print(f"\n=== DATOS DE PACIENTE DNI 38112227 ===")

    try:
        # Datos básicos del paciente
        paciente_query = """
        SELECT TOP 1 PacienteID, Nombre, Apellido, Documento, Cuil,
               FechadeNacimiento, Telefono, Correo
        FROM Pacientes
        WHERE Documento = '38112227' AND Anulado = 0
        """

        result = session.execute(text(paciente_query))
        paciente = result.fetchone()

        if paciente:
            print(f"Paciente encontrado: {paciente[1]} {paciente[2]} (ID: {paciente[0]})")

            # Buscar internaciones
            internaciones_query = f"""
            SELECT TOP 5 i.InternacionID, i.Fecha_ingreso, i.Fecha_Alta,
                   i.Observaciones, c.Nombre as Cama, h.Nombre as Habitacion,
                   s.Nombre as Sector
            FROM Internaciones i
            LEFT JOIN Camas c ON i.CamaID = c.CamaId
            LEFT JOIN Habitaciones h ON i.HabitacionID = h.HabitacionID
            LEFT JOIN Sectores s ON h.SectorID = s.SectorId
            WHERE i.PacienteID = {paciente[0]} AND i.Anulado = 0
            ORDER BY i.Fecha_ingreso DESC
            """

            result = session.execute(text(internaciones_query))
            internaciones = result.fetchall()

            print(f"Internaciones encontradas: {len(internaciones)}")
            for int_data in internaciones:
                fecha_alta = int_data[2].strftime('%d/%m/%Y') if int_data[2] else "ACTIVA"
                print(f"  - Ingreso: {int_data[1].strftime('%d/%m/%Y')} | Alta: {fecha_alta}")
                print(f"    Sector: {int_data[6]} | Habitación: {int_data[5]} | Cama: {int_data[4]}")
                if int_data[3]:
                    print(f"    Observaciones: {int_data[3][:100]}...")

        else:
            print("❌ Paciente no encontrado")

    except Exception as e:
        print(f"❌ Error consultando paciente: {e}")

    session.close()
    print("\n✅ Exploración completada")

except Exception as e:
    print(f"❌ Error de conexión: {e}")