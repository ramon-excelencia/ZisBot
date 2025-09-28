#!/usr/bin/env python3
"""Script para explorar todas las tablas disponibles en la base de datos ZISMED"""
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
    print("Conexion exitosa a la base de datos")

    print("\n=== EXPLORANDO TODAS LAS TABLAS DE LA BASE DE DATOS ===")

    # Obtener todas las tablas
    all_tables_query = """
    SELECT TABLE_NAME, TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_NAME
    """

    result = session.execute(text(all_tables_query))
    all_tables = result.fetchall()

    print(f"\nTotal de tablas encontradas: {len(all_tables)}")

    # Buscar tablas que podrían tener información médica adicional
    medical_keywords = ['diagnostico', 'evolucion', 'historia', 'consulta', 'examen', 'laboratorio',
                       'estudio', 'imagen', 'rayos', 'ecografia', 'medic', 'clinica', 'procedimiento',
                       'cirugia', 'operacion', 'tratamiento', 'medicamento', 'farmacia', 'receta',
                       'nota', 'observacion', 'seguimiento', 'control', 'visita', 'atencion']

    medical_tables = []

    print("\n=== TABLAS POTENCIALMENTE MEDICAS ===")
    for table_name, table_type in all_tables:
        table_lower = table_name.lower()
        if any(keyword in table_lower for keyword in medical_keywords):
            medical_tables.append(table_name)
            print(f"✓ {table_name}")

    # Mostrar primeras 50 tablas para referencia
    print(f"\n=== PRIMERAS 50 TABLAS DE LA BASE DE DATOS ===")
    for i, (table_name, table_type) in enumerate(all_tables[:50], 1):
        print(f"{i:2}. {table_name}")

    if len(all_tables) > 50:
        print(f"... y {len(all_tables) - 50} tablas más")

    # Explorar estructura de tablas médicas interesantes
    interesting_tables = ['Diagnosticos', 'Evoluciones', 'HistoriaClinica', 'Consultas',
                         'Examenes', 'Laboratorio', 'Estudios', 'NotasMedicas']

    print(f"\n=== EXPLORANDO ESTRUCTURA DE TABLAS MEDICAS ESPECIFICAS ===")

    for table_name in interesting_tables:
        try:
            # Verificar si la tabla existe
            exists_query = f"""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{table_name}'
            """

            result = session.execute(text(exists_query))
            exists = result.scalar() > 0

            if exists:
                print(f"\n--- Estructura de {table_name} ---")
                columns_query = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
                """

                result = session.execute(text(columns_query))
                columns = result.fetchall()

                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    max_len = f"({col[3]})" if col[3] else ""
                    print(f"  {col[0]}: {col[1]}{max_len} {nullable}")

                # Contar registros
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                result = session.execute(text(count_query))
                count = result.scalar()
                print(f"  Total registros: {count}")

            else:
                print(f"Tabla {table_name} no encontrada")

        except Exception as e:
            print(f"Error explorando {table_name}: {e}")

    # Buscar tablas relacionadas con paciente específico
    print(f"\n=== BUSCANDO DATOS ADICIONALES PARA PACIENTE DNI 38112227 ===")

    # Buscar ID del paciente
    paciente_query = """
    SELECT PacienteID, Nombre, Apellido
    FROM Pacientes
    WHERE Documento = '38112227' AND Anulado = 0
    """

    result = session.execute(text(paciente_query))
    paciente = result.fetchone()

    if paciente:
        paciente_id = paciente[0]
        print(f"PacienteID encontrado: {paciente_id} - {paciente[1]} {paciente[2]}")

        # Buscar en tablas que podrían tener referencias a PacienteID
        tables_with_patient_ref = []
        for table_name, _ in all_tables:
            try:
                # Verificar si la tabla tiene columna PacienteID
                column_query = f"""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table_name}' AND COLUMN_NAME = 'PacienteID'
                """

                result = session.execute(text(column_query))
                has_patient_id = result.scalar() > 0

                if has_patient_id:
                    tables_with_patient_ref.append(table_name)

                    # Contar registros para este paciente
                    count_query = f"SELECT COUNT(*) FROM {table_name} WHERE PacienteID = {paciente_id}"
                    result = session.execute(text(count_query))
                    count = result.scalar()

                    if count > 0:
                        print(f"  ✓ {table_name}: {count} registros")

            except Exception as e:
                # Ignorar errores de permisos o tablas inaccesibles
                pass

    session.close()
    print("\nExploracion completada")

except Exception as e:
    print(f"Error de conexion: {e}")