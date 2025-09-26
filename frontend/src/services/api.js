/**
 * Servicio API para ZisMed Chatbot
 * Maneja todas las comunicaciones con el backend
 */
import axios from 'axios'

// Configuración base de Axios
const api = axios.create({
  baseURL: 'http://localhost:8009/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Interceptor para agregar token de autorización
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('zismed_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor para manejar respuestas y errores
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Manejar errores de autorización
    if (error.response?.status === 401) {
      localStorage.removeItem('zismed_token')
      localStorage.removeItem('zismed_user')
      window.location.href = '/login'
    }

    // Log de errores para debugging
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      message: error.response?.data?.detail || error.message
    })

    return Promise.reject(error)
  }
)

// Servicios de autenticación
export const authAPI = {
  /**
   * Paso 1: Validar credenciales y obtener instituciones
   */
  async validateCredentials(cuil, password) {
    try {
      const response = await api.post('/auth/validate-credentials', {
        cuil: cuil.replace(/[-\s]/g, ''),
        password
      })

      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.message ||
        error.response?.data?.detail ||
        'Error validando credenciales'
      )
    }
  },

  /**
   * Paso 2: Login completo con institución seleccionada
   */
  async loginWithInstitution(cuil, password, institutionId, acceptsTerms = false) {
    try {
      const response = await api.post('/auth/login-with-institution', {
        cuil: cuil.replace(/[-\s]/g, ''),
        password,
        institution_id: institutionId,
        accepts_terms: acceptsTerms
      })

      if (response.data.success && response.data.access_token) {
        // Guardar token y datos de usuario
        localStorage.setItem('zismed_token', response.data.access_token)
        localStorage.setItem('zismed_user', JSON.stringify(response.data.user))

        if (response.data.selected_institution) {
          localStorage.setItem('zismed_institution', JSON.stringify(response.data.selected_institution))
        }
      }

      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Error en login con institución'
      )
    }
  },

  /**
   * Login simple (retrocompatibilidad)
   */
  async login(cuil, password) {
    try {
      const response = await api.post('/auth/login', {
        cuil: cuil.replace(/[-\s]/g, ''), // Limpiar CUIL
        password
      })

      if (response.data.success && response.data.access_token) {
        // Guardar token y datos de usuario
        localStorage.setItem('zismed_token', response.data.access_token)
        localStorage.setItem('zismed_user', JSON.stringify(response.data.user))

        if (response.data.default_institution) {
          localStorage.setItem('zismed_institution', JSON.stringify(response.data.default_institution))
        }
      }

      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.error ||
        error.response?.data?.detail ||
        'Error de conexión con el servidor'
      )
    }
  },

  /**
   * Logout del sistema
   */
  async logout() {
    try {
      // El backend no tiene endpoint de logout, solo limpiamos datos locales
      console.log('Cerrando sesión...')
    } catch (error) {
      console.warn('Error en logout:', error)
    } finally {
      // Limpiar datos locales
      localStorage.removeItem('zismed_token')
      localStorage.removeItem('zismed_user')
      localStorage.removeItem('zismed_institution')
    }
  },

  /**
   * Obtener información del usuario actual
   */
  async getCurrentUser() {
    const response = await api.get('/auth/me')
    return response.data
  },

  /**
   * Renovar token de acceso
   */
  async refreshToken() {
    const response = await api.post('/auth/refresh')
    if (response.data.access_token) {
      localStorage.setItem('zismed_token', response.data.access_token)
    }
    return response.data
  }
}

// Servicios de chat
export const chatAPI = {
  /**
   * Enviar mensaje al chatbot ZisBot con memoria por sesión
   */
  async sendMessage(message, conversationId = null) {
    // Generar ID único de sesión si no existe
    if (!conversationId) {
      conversationId = apiUtils.generateSessionId()
    }

    const payload = {
      message: message,
      conversation_id: conversationId
    }

    const response = await api.post('/chat', payload)
    return response.data
  },

  /**
   * Obtener conversaciones del usuario
   */
  async getConversations(limit = 20) {
    const response = await api.get(`/chat/conversations?limit=${limit}`)
    return response.data
  },

  /**
   * Obtener historial de una conversación
   */
  async getConversationHistory(conversationId, limit = 50) {
    const response = await api.get(`/chat/conversation/${conversationId}?limit=${limit}`)
    return response.data
  },

  /**
   * Eliminar conversación
   */
  async deleteConversation(conversationId) {
    const response = await api.delete(`/chat/conversation/${conversationId}`)
    return response.data
  },

  /**
   * Obtener acciones rápidas
   */
  async getQuickActions() {
    const response = await api.get('/chat/quick-actions')
    return response.data
  },

  /**
   * Buscar paciente por DNI
   */
  async searchPatientByDNI(dni) {
    const response = await api.get(`/v1/orm-chatbot/patients/search-dni/${dni}`)
    return response.data
  },

  /**
   * Buscar pacientes por nombre
   */
  async searchPatientsByName(name, limit = 10) {
    const response = await api.get(`/v1/orm-chatbot/patients/search-name?name=${encodeURIComponent(name)}&limit=${limit}`)
    return response.data
  },

  /**
   * Obtener especialidades disponibles
   */
  async getSpecialties(hospitalId = "3") {
    const response = await api.get(`/v1/orm-chatbot/data/specialties/${hospitalId}`)
    return response.data
  },

  /**
   * Obtener disponibilidad de camas
   */
  async getBedsAvailability(hospitalId = "3") {
    const response = await api.get(`/v1/orm-chatbot/data/beds/${hospitalId}`)
    return response.data
  },

  /**
   * Obtener turnos de hoy
   */
  async getTodayAppointments(hospitalId = "3") {
    const response = await api.get(`/v1/orm-chatbot/data/appointments/today/${hospitalId}`)
    return response.data
  },

  /**
   * Obtener turnos por fecha
   */
  async getAppointmentsByDate(date, hospitalId = "3") {
    const response = await api.get(`/v1/orm-chatbot/data/appointments/date/${hospitalId}?fecha=${date}`)
    return response.data
  },

  /**
   * Health check del sistema ORM
   */
  async getHealthCheck() {
    const response = await api.get('/v1/orm-chatbot/health')
    return response.data
  }
}

// Servicios del sistema
export const systemAPI = {
  /**
   * Verificar estado del sistema
   */
  async getSystemStatus() {
    const response = await api.get('/system/status')
    return response.data
  },

  /**
   * Health check
   */
  async healthCheck() {
    const response = await api.get('/v1/orm-chatbot/health')
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
    if (error.response?.data?.detail) {
      return error.response.data.detail
    }
    if (error.message) {
      return error.message
    }
    return 'Error desconocido'
  },

  /**
   * Generar ID único de sesión para cada chat
   */
  generateSessionId() {
    const timestamp = Date.now()
    const random = Math.random().toString(36).substring(2, 8)
    const sessionId = `session_${timestamp}_${random}`

    // Guardar en localStorage para mantener consistencia durante la sesión
    localStorage.setItem('current_session_id', sessionId)

    return sessionId
  },

  /**
   * Obtener o generar ID de sesión actual
   */
  getCurrentSessionId() {
    let sessionId = localStorage.getItem('current_session_id')

    if (!sessionId) {
      sessionId = this.generateSessionId()
    }

    return sessionId
  },

  /**
   * Crear nueva sesión (limpiar sesión actual)
   */
  createNewSession() {
    localStorage.removeItem('current_session_id')
    return this.generateSessionId()
  }
}

export default api