"""
Validadores de entrada para el sistema ZisBot
Valida datos antes de procesarlos para evitar errores
"""
from datetime import datetime
from typing import Dict, Any, Optional
import re


def validate_dni(dni: str) -> Dict[str, Any]:
    """
    Valida formato de DNI argentino

    Args:
        dni: String con el DNI a validar

    Returns:
        Dict con 'valid' (bool), 'dni' (cleaned) y 'error' (str)
    """
    # Limpiar DNI
    dni_clean = re.sub(r'\D', '', dni)

    # Validar longitud (7-8 dígitos para DNI argentino)
    if len(dni_clean) < 7:
        return {
            'valid': False,
            'dni': dni_clean,
            'error': '❌ El DNI debe tener al menos 7 dígitos'
        }

    if len(dni_clean) > 8:
        return {
            'valid': False,
            'dni': dni_clean,
            'error': '❌ El DNI no puede tener más de 8 dígitos'
        }

    return {
        'valid': True,
        'dni': dni_clean,
        'error': None
    }


def validate_date(date_str: str) -> Dict[str, Any]:
    """
    Valida formato de fecha y que sea válida

    Args:
        date_str: String con fecha en varios formatos posibles

    Returns:
        Dict con 'valid' (bool), 'date' (datetime) y 'error' (str)
    """
    if not date_str:
        return {
            'valid': False,
            'date': None,
            'error': '❌ Debe proporcionar una fecha'
        }

    # Formatos soportados
    date_formats = [
        '%Y-%m-%d',      # 2025-01-15
        '%d/%m/%Y',      # 15/01/2025
        '%d-%m-%Y',      # 15-01-2025
        '%Y/%m/%d',      # 2025/01/15
    ]

    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)

            # Validar que no sea fecha futura muy lejana (más de 1 año)
            if parsed_date.year > datetime.now().year + 1:
                return {
                    'valid': False,
                    'date': None,
                    'error': f'❌ La fecha {date_str} es demasiado futura'
                }

            # Validar que no sea fecha muy antigua (antes de 1900)
            if parsed_date.year < 1900:
                return {
                    'valid': False,
                    'date': None,
                    'error': f'❌ La fecha {date_str} es inválida'
                }

            return {
                'valid': True,
                'date': parsed_date,
                'error': None
            }

        except ValueError:
            continue

    # Ningún formato funcionó
    return {
        'valid': False,
        'date': None,
        'error': f'❌ Formato de fecha inválido: {date_str}. Use YYYY-MM-DD o DD/MM/YYYY'
    }


def validate_date_range(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Valida rango de fechas

    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin

    Returns:
        Dict con 'valid' (bool), 'start', 'end' y 'error'
    """
    # Validar fecha inicio
    start_validation = validate_date(start_date)
    if not start_validation['valid']:
        return start_validation

    # Validar fecha fin
    end_validation = validate_date(end_date)
    if not end_validation['valid']:
        return end_validation

    # Validar que inicio sea antes que fin
    if start_validation['date'] > end_validation['date']:
        return {
            'valid': False,
            'start': None,
            'end': None,
            'error': '❌ La fecha de inicio debe ser anterior a la fecha de fin'
        }

    # Validar que el rango no sea mayor a 1 año
    days_diff = (end_validation['date'] - start_validation['date']).days
    if days_diff > 365:
        return {
            'valid': False,
            'start': None,
            'end': None,
            'error': '❌ El rango de fechas no puede ser mayor a 1 año'
        }

    return {
        'valid': True,
        'start': start_validation['date'],
        'end': end_validation['date'],
        'error': None
    }


def validate_query_length(query: str, max_length: int = 500) -> Dict[str, Any]:
    """
    Valida longitud de consulta del usuario

    Args:
        query: Texto de la consulta
        max_length: Longitud máxima permitida

    Returns:
        Dict con 'valid' (bool), 'query' y 'error'
    """
    if not query or not query.strip():
        return {
            'valid': False,
            'query': '',
            'error': '❌ La consulta no puede estar vacía'
        }

    query_clean = query.strip()

    if len(query_clean) > max_length:
        return {
            'valid': False,
            'query': query_clean[:max_length],
            'error': f'❌ La consulta es demasiado larga (máximo {max_length} caracteres)'
        }

    return {
        'valid': True,
        'query': query_clean,
        'error': None
    }


def validate_service_name(service_name: str) -> Dict[str, Any]:
    """
    Valida nombre de servicio/especialidad

    Args:
        service_name: Nombre del servicio

    Returns:
        Dict con 'valid' (bool), 'service_name' y 'error'
    """
    if not service_name or not service_name.strip():
        return {
            'valid': False,
            'service_name': '',
            'error': '❌ Debe especificar un servicio o especialidad'
        }

    service_clean = service_name.strip()

    # Validar longitud razonable
    if len(service_clean) < 3:
        return {
            'valid': False,
            'service_name': service_clean,
            'error': '❌ El nombre del servicio es demasiado corto'
        }

    if len(service_clean) > 100:
        return {
            'valid': False,
            'service_name': service_clean,
            'error': '❌ El nombre del servicio es demasiado largo'
        }

    return {
        'valid': True,
        'service_name': service_clean,
        'error': None
    }
