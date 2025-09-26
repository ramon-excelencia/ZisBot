/**
 * Servicio API simplificado para ZisMed Chatbot
 * Conecta con el servidor de prueba
 */
import axios from 'axios'

// Configuración base de Axios
const api = axios.create({
  baseURL: 'http://localhost:8002',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Servicios de autenticación
export const authAPI = {
  /**
   * Login con CUIL y contraseña
   */
  async login(cuil, password) {
    try {
      const response = await api.post('/api/test/login', {
        cuil: cuil.replace(/[-\s]/g, ''),
        password
      })

      if (response.data.success && response.data.access_token) {
        // Guardar token y datos de usuario
        localStorage.setItem('zismed_token', response.data.access_token)
        localStorage.setItem('zismed_user', JSON.stringify(response.data.user))

        // Crear institución por defecto
        const institution = {
          id: "3",
          name: response.data.user.institution
        }
        localStorage.setItem('zismed_institution', JSON.stringify(institution))
      }

      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.error ||
        'Error de conexión con el servidor'
      )
    }
  },

  /**
   * Logout del sistema
   */
  async logout() {
    localStorage.removeItem('zismed_token')
    localStorage.removeItem('zismed_user')
    localStorage.removeItem('zismed_institution')
  }
}

// Servicios de chat
export const chatAPI = {
  /**
   * Enviar mensaje al chatbot con Function Calling
   */
  async sendMessage(message, conversationId = null) {
    try {
      // Intentar primero con el endpoint Gemini Function Calling
      const userData = apiUtils.getCurrentUserData()
      const userContext = {
        hospital_id: "3",
        user_id: userData?.id,
        user_role: userData?.role,
        institution: userData?.institution
      }

      const response = await api.post('/api/gemini/chat', {
        message,
        conversation_id: conversationId,
        user_context: userContext
      })

      return response.data
    } catch (error) {
      console.warn('Function Calling falló, usando endpoint simple:', error.message)

      // Fallback al endpoint simple
      try {
        const response = await api.post('/api/test/chat', {
          message,
          conversation_id: conversationId
        })
        return response.data
      } catch (fallbackError) {
        console.error('Todos los endpoints fallaron:', fallbackError)
        throw fallbackError
      }
    }
  },

  /**
   * Obtener acciones rápidas
   */
  async getQuickActions() {
    return {
      success: true,
      actions: [
        {
          id: "specialties",
          title: "Ver Especialidades",
          description: "Consultar especialidades disponibles",
          icon: "👨‍⚕️",
          template: "especialidades"
        },
        {
          id: "turnos",
          title: "Gestionar Turnos",
          description: "Administrar agenda médica",
          icon: "📅",
          template: "turnos"
        },
        {
          id: "pacientes",
          title: "Consultar Pacientes",
          description: "Búsqueda y gestión de pacientes",
          icon: "👤",
          template: "pacientes"
        },
        {
          id: "reportes",
          title: "Reportes",
          description: "Estadísticas hospitalarias",
          icon: "📊",
          template: "reportes"
        }
      ]
    }
  }
}

// Servicios del sistema
export const systemAPI = {
  /**
   * Verificar estado del sistema
   */
  async getSystemStatus() {
    const response = await api.get('/health')
    return response.data
  },

  /**
   * Obtener especialidades
   */
  async getSpecialties() {
    const response = await api.get('/api/test/specialties')
    return response.data
  }
}

// Utilidades
export const apiUtils = {
  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated() {
    const token = localStorage.getItem('zismed_token')
    const user = localStorage.getItem('zismed_user')
    return !!(token && user)
  },

  /**
   * Obtener datos del usuario desde localStorage
   */
  getCurrentUserData() {
    const userData = localStorage.getItem('zismed_user')
    return userData ? JSON.parse(userData) : null
  },

  /**
   * Obtener datos de la institución actual
   */
  getCurrentInstitution() {
    const institutionData = localStorage.getItem('zismed_institution')
    return institutionData ? JSON.parse(institutionData) : null
  },

  /**
   * Formatear errores de API para mostrar al usuario
   */
  formatError(error) {
    if (error.response?.data?.error) {
      return error.response.data.error
    }
    if (error.message) {
      return error.message
    }
    return 'Error desconocido'
  }
}

export default api