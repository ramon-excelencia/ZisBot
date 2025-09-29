# 🚀 GUÍA DE INSTALACIÓN EN PRODUCCIÓN - ZisBot

## 📋 PASOS COMPLETOS PARA EJECUTAR EN SERVIDOR DE PRODUCCIÓN

## 🔧 REQUISITOS PREVIOS (DESCARGAR ANTES DE EMPEZAR)

1. **Python 3.8+**: https://python.org/downloads/
   - ✅ IMPORTANTE: Marcar "Add Python to PATH" durante instalación
   - 🚨 Si hay error de permisos:
     - Opción A: Ejecutar instalador como administrador (clic derecho → "Ejecutar como administrador")
     - Opción B: Marcar "Install for current user only"
     - Opción C: Instalar desde Microsoft Store

2. **Git**: https://git-scm.com/download/win
   - Para clonar el repositorio

3. **Node.js LTS**: https://nodejs.org/
   - ✅ IMPORTANTE: Marcar "Add to PATH" durante instalación

4. **Redis para Windows**: https://github.com/microsoftarchive/redis/releases
   - Descargar Redis-x64-3.0.504.msi

---

### **PASO 1: CLONAR Y CONFIGURAR REPOSITORIO**

```bash
# 1.1 Clonar repositorio
git clone https://github.com/ramon-excelencia/ZisBot.git
cd ZisBot

# 1.2 Cambiar a rama production
git checkout production

# 1.3 Verificar que estás en la rama correcta
git branch
```

### **PASO 2: CREAR ARCHIVO .env**

```bash
# 2.1 Crear archivo .env en la raíz del proyecto
# Windows Command Prompt:
echo. > .env

# O usar PowerShell:
# New-Item .env -ItemType File

# O simplemente crear el archivo con notepad:
# notepad .env

# 2.2 Editar .env con el siguiente contenido:
```

**Contenido del archivo `.env`:**
```env
# API Keys
GROQ_API_KEY=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
OPENAI_API_KEY=sk-proj-NyWFb8H6kIYJ7lIlGW7yT3BlbkFJBHdEeqYhjA5a9GHRXpL3

# Redis Configuration
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET_KEY=tu_clave_secreta_muy_segura_para_jwt_tokens_2024
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=720

# Database URLs (no se usan en esta configuración)
DATABASE_PG_URL=postgresql://user:password@localhost/dbname
DATABASE_MONGO_URL=mongodb://localhost:27017/zisbot
```

### **PASO 3: INSTALAR PYTHON Y DEPENDENCIAS**

```cmd
REM 3.1 Verificar si Python está instalado
python --version
REM Si da error "no se reconoce", instalar Python desde https://python.org
REM IMPORTANTE: Marcar "Add Python to PATH" durante la instalación

REM Si python no funciona, probar con:
py --version

REM 3.2 Crear entorno virtual (usar py si python no funciona)
python -m venv venv
REM O:
py -m venv venv

REM 3.3 Activar entorno virtual (Windows Command Prompt)
venv\Scripts\activate.bat

REM 3.4 Actualizar pip
python -m pip install --upgrade pip

REM 3.5 Instalar dependencias
pip install -r requirements.txt
```

### **PASO 4: INSTALAR REDIS (WINDOWS)**

```cmd
REM 4.1 Descargar Redis para Windows
REM Opción 1: Instalar desde GitHub Releases
REM https://github.com/microsoftarchive/redis/releases
REM Descargar Redis-x64-3.0.504.msi

REM Opción 2: Usar Chocolatey (si está instalado)
REM choco install redis-64

REM 4.2 Iniciar Redis (después de instalar)
REM Redis se instala como servicio de Windows automáticamente
REM Para iniciarlo manualmente:
redis-server.exe

REM 4.3 Verificar Redis funciona (abrir nueva ventana de cmd)
redis-cli ping
REM Debe responder: PONG
```

### **PASO 5: CONFIGURAR FRONTEND**

```cmd
REM 5.1 Navegar a carpeta frontend
cd frontend

REM 5.2 Instalar Node.js (si no está instalado)
REM Descargar desde https://nodejs.org/ (versión LTS)
REM IMPORTANTE: Marcar "Add to PATH" durante la instalación

REM 5.3 Verificar Node.js y npm
node --version
npm --version

REM 5.4 Instalar dependencias del frontend
npm install

REM 5.5 Volver a raíz del proyecto
cd ..
```

### **PASO 6: EJECUTAR SERVIDORES**

**Ventana 1 - Backend (Command Prompt):**
```cmd
REM 6.1 Asegurarse de estar en la raíz del proyecto
cd /d C:\ruta\a\ZisBot
REM O navegar donde clonaste el proyecto

REM 6.2 Activar entorno virtual (si no está activado)
venv\Scripts\activate.bat

REM 6.3 Ejecutar backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload

REM Debe mostrar:
REM INFO:     Uvicorn running on http://0.0.0.0:8008
```

**Ventana 2 - Frontend (Command Prompt):**
```cmd
REM 6.4 Abrir nueva ventana de cmd y navegar al proyecto
cd /d C:\ruta\a\ZisBot\frontend

REM 6.5 Ejecutar frontend
npm run dev

REM Debe mostrar algo como:
REM Local:   http://localhost:3000
REM o
REM Local:   http://localhost:3004
```

### **PASO 7: VERIFICAR FUNCIONAMIENTO**

```cmd
REM 7.1 Probar backend (desde otra ventana de cmd)
REM Instalar curl para Windows si no está disponible:
REM https://curl.se/windows/

REM O usar PowerShell en su lugar:
powershell -Command "Invoke-RestMethod http://localhost:8008/"

REM 7.2 Probar login con PowerShell (más fácil en Windows)
powershell -Command "Invoke-RestMethod -Uri 'http://localhost:8008/api/auth/login' -Method POST -Body '{\"cuil\": \"27357388827\", \"password\": \"simon0\"}' -ContentType 'application/json'"

REM Debe devolver un token JWT
```

### **PASO 8: ACCEDER AL SISTEMA**

1. **Frontend**: Abrir navegador en `http://localhost:3000` (o el puerto que muestre npm)
2. **Backend API**: `http://localhost:8008`
3. **Login**: Usar CUIL `27357388827` y password `simon0`

---

## 🚨 TROUBLESHOOTING

### **Si hay errores de conexión a BD:**
```bash
# Verificar conectividad desde el servidor
ping 172.16.30.1
telnet 172.16.30.1 1433
```

### **Si Redis falla:**
```bash
# Reinstalar Redis
sudo systemctl restart redis
redis-cli ping
```

### **Si falla la instalación de dependencias:**
```bash
# Limpiar caché de pip
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

---

## 📁 ESTRUCTURA ESPERADA

```
ZisBot/
├── .env                    # Configuración
├── app/                    # Backend Python
├── frontend/               # Frontend Vue.js
├── venv/                   # Entorno virtual Python
├── requirements.txt        # Dependencias Python
└── README.md
```

---

## 🎯 CREDENCIALES DE ACCESO

- **CUIL**: `27357388827`
- **Password**: `simon0`
- **Frontend URL**: `http://localhost:3000`
- **Backend URL**: `http://localhost:8008`

---

## ✅ FUNCIONALIDADES LISTAS PARA PROBAR

1. **Login con credenciales hospitalarias**
2. **Búsqueda de pacientes por DNI**
3. **Información de camas disponibles**
4. **Horarios de atención por especialidad**
5. **Historia clínica de pacientes**
6. **Especialidades disponibles**

---

## 📞 CONTACTO

Si hay problemas durante la instalación, revisar los logs de error y verificar:
- Conectividad de red a la base de datos
- Redis funcionando correctamente
- Puertos 8008 y 3000 disponibles

**¡El sistema está configurado para funcionar con datos reales de producción!** 🎉