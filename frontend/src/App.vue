<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <!-- Loader global -->
    <div v-if="isLoading" class="fixed inset-0 bg-white bg-opacity-90 flex items-center justify-center z-50">
      <div class="text-center">
        <div class="loading-spinner w-12 h-12 border-4 border-hospital-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-gray-600 font-medium">Cargando ZisMed Chatbot...</p>
      </div>
    </div>

    <!-- Aplicación principal -->
    <div v-else>
      <router-view />
    </div>

    <!-- Toast de notificaciones -->
    <div v-if="notification" class="fixed top-4 right-4 z-40 max-w-sm">
      <div
        :class="[
          'p-4 rounded-lg shadow-lg border-l-4 bg-white',
          notification.type === 'success' ? 'border-green-500' :
          notification.type === 'error' ? 'border-red-500' :
          notification.type === 'warning' ? 'border-yellow-500' :
          'border-blue-500'
        ]"
        class="fade-in"
      >
        <div class="flex items-start">
          <div class="flex-shrink-0">
            <component
              :is="getNotificationIcon(notification.type)"
              class="w-5 h-5"
              :class="[
                notification.type === 'success' ? 'text-green-500' :
                notification.type === 'error' ? 'text-red-500' :
                notification.type === 'warning' ? 'text-yellow-500' :
                'text-blue-500'
              ]"
            />
          </div>
          <div class="ml-3 flex-1">
            <p class="text-sm font-medium text-gray-900">{{ notification.title }}</p>
            <p class="text-sm text-gray-600 mt-1">{{ notification.message }}</p>
          </div>
          <button
            @click="clearNotification"
            class="ml-4 text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'
import { apiUtils } from './services/api'

export default {
  name: 'App',
  components: {
    CheckCircleIcon,
    ExclamationCircleIcon,
    ExclamationTriangleIcon,
    InformationCircleIcon,
    XMarkIcon
  },
  setup() {
    const router = useRouter()
    const isLoading = ref(true)
    const notification = ref(null)

    // Inicialización de la aplicación
    onMounted(async () => {
      try {
        // LIMPIAR SESIÓN SIEMPRE AL CARGAR LA PÁGINA
        localStorage.removeItem('zismed_token')
        localStorage.removeItem('zismed_user')
        localStorage.removeItem('zismed_institution')

        // Siempre ir al login en cada carga
        await router.push('/login')
      } catch (error) {
        console.error('Error en inicialización:', error)
        showNotification('error', 'Error', 'Error inicializando la aplicación')
      } finally {
        isLoading.value = false
      }
    })

    // Sistema de notificaciones
    const showNotification = (type, title, message, duration = 5000) => {
      notification.value = { type, title, message }

      if (duration > 0) {
        setTimeout(() => {
          clearNotification()
        }, duration)
      }
    }

    const clearNotification = () => {
      notification.value = null
    }

    const getNotificationIcon = (type) => {
      switch (type) {
        case 'success': return CheckCircleIcon
        case 'error': return ExclamationCircleIcon
        case 'warning': return ExclamationTriangleIcon
        default: return InformationCircleIcon
      }
    }

    // Exponer métodos globalmente
    window.showNotification = showNotification

    return {
      isLoading,
      notification,
      clearNotification,
      getNotificationIcon
    }
  }
}
</script>

<style scoped>
/* Estilos específicos del componente App */
</style>