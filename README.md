# ZisBot - Sistema de Chatbot Hospitalario

## 🏥 Chatbot Inteligente para Hospital Regional Santiago del Estero

Sistema de chatbot avanzado integrado con ZISMED, usando LangGraph + Groq para brindar información hospitalaria en tiempo real.

## 🎯 Estado del Proyecto
- ✅ **COMPLETAMENTE FUNCIONAL** (Fase 1 completada)
- ✅ **100% Operativo** - Todas las pruebas exitosas
- ✅ **Proyecto limpio** y listo para producción

## 🚀 Configuración Rápida

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
- Copiar `.env.example` a `.env`
- Configurar credenciales de ZISMED y Groq

### 3. Iniciar el sistema
```bash
# Servidor principal (recomendado para producción)
python iniciar_servidor_sin_reload.py

# Servidor con autoreload (desarrollo)
python iniciar_servidor.py
```

### 4. Frontend (opcional)
```bash
cd frontend
npm install
npm start
```

## 🔐 Credenciales de Prueba
- **CUIL:** 27357388827
- **Contraseña:** simon0
- **Usuario:** Yanet Villalba (Coordinadora de Gestión)

## 🌐 Endpoints Principales
- **API Principal:** http://localhost:8009/api/chat
- **Documentación:** http://localhost:8009/api/docs
- **Login:** http://localhost:8009/api/auth/login
- **Frontend:** http://localhost:3003

## ✅ Funcionalidades Verificadas

### 🏥 Datos Hospitalarios
- **Búsqueda por DNI:** Acceso a 3 pacientes verificados
- **Especialidades:** 52 especialidades médicas disponibles
- **Servicios:** 80 servicios hospitalarios activos
- **Camas:** Estado en tiempo real (43 camas totales)
- **Historia clínica:** Acceso autorizado por DNI

### 🤖 Inteligencia Artificial
- **LangGraph:** Workflow inteligente de procesamiento
- **Groq API:** Respuestas rápidas y precisas
- **Detección de intenciones:** Reconoce tipos de consulta
- **Memoria persistente:** Redis para sesiones

### 🔐 Seguridad
- **Autenticación JWT:** Tokens seguros
- **Autorización por roles:** Control de acceso
- **Integración ZISMED:** Conexión segura a base de datos

## 🛠️ Arquitectura Técnica

### Backend (FastAPI)
- **Framework:** FastAPI con arquitectura limpia
- **Base de datos:** SQL Server (ZISMED)
- **Cache:** Redis para memoria
- **IA:** Groq + LangGraph
- **Autenticación:** JWT

### Estructura del Proyecto
```
ZisBot-Regional/
├── app/
│   ├── main.py              # Servidor principal
│   ├── services/            # Servicios del negocio
│   │   ├── chatbot_service.py
│   │   ├── orm_hospital_service.py
│   │   └── hospital_data_service.py
│   ├── integrations/        # Integraciones IA
│   ├── routes/             # Rutas API
│   ├── config/             # Configuración
│   └── models/             # Modelos de datos
├── frontend/               # Interfaz web
├── requirements.txt        # Dependencias
└── .env                   # Variables de entorno
```

## 📋 Casos de Uso Verificados

1. **"Hola, ¿cómo estás?"** → Saludo personalizado
2. **"¿Cuántas camas disponibles hay?"** → Estado de camas (14/43 disponibles)
3. **"Buscar paciente DNI 4131847"** → Datos del paciente encontrado
4. **"¿Qué especialidades están disponibles?"** → Lista de 52 especialidades
5. **"Historia clínica DNI 4131847"** → Acceso autorizado a historia
6. **"¿Qué servicios tiene el hospital?"** → Lista de 80 servicios

## 🎯 Criterios de Fase 1 Cumplidos

- ✅ **Identidad y permisos:** Autenticación ZISMED completa
- ✅ **Consultas de camas:** Estado en tiempo real
- ✅ **Registros médicos:** Acceso a historias clínicas
- ✅ **Datos de pacientes:** Búsqueda por DNI funcionando
- ✅ **Horarios y servicios:** 80 servicios listados
- ✅ **Volumen de atención:** Métricas hospitalarias
- ✅ **Trazabilidad:** Logs y seguimiento completo
- ✅ **Experiencia de usuario:** Interfaz intuitiva

## 🔧 Troubleshooting

### Problemas Comunes
1. **Puerto ocupado:** Cambiar puerto en `iniciar_servidor.py`
2. **Error de conexión:** Verificar credenciales en `.env`
3. **Timeout:** Reiniciar Redis si está configurado

### Logs
```bash
# Ver logs en tiempo real
tail -f server_logs.txt
```

## 📞 Soporte
- **Mesa de Ayuda Hospital:** 4212121
- **Emergencias:** 22323 (int. 911)
- **Documentación:** Ver archivos `*.md` en la raíz del proyecto