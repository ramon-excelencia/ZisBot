<template>
  <div class="chat-container">
    <!-- Header del chat -->
    <div class="chat-header">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm">
              <svg class="icon-sm text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
              </svg>
            </div>
            <div>
              <h1 class="text-lg font-semibold text-gray-900">ZisBot</h1>
              <p class="text-xs text-gray-500">Sistema de Gestión Hospitalaria</p>
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-3">
          <!-- Usuario actual -->
          <div class="text-right">
            <p class="text-sm font-medium text-gray-900">{{ currentUser?.name }}</p>
            <p class="text-xs text-gray-500">{{ currentInstitution?.name }}</p>
          </div>

          <!-- Botón logout -->
          <button
            @click="handleLogout"
            class="p-2 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors duration-200"
            title="Cerrar sesión"
          >
            <ArrowRightOnRectangleIcon class="icon-sm" />
          </button>
        </div>
      </div>
    </div>

    <!-- Área de mensajes -->
    <div ref="messagesContainer" class="chat-messages">
      <!-- Mensaje de bienvenida -->
      <div v-if="messages.length === 0" class="text-center py-8 px-4">
        <div class="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
          <svg class="icon-md text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900 mb-2">¡Hola {{ currentUser?.name?.split(' ')[0] }}!</h3>
        <p class="text-gray-600 text-sm mb-6 max-w-md mx-auto leading-relaxed">
          Soy ZisBot, tu asistente de gestión hospitalaria para el {{ currentInstitution?.name }}.
          Te ayudo con consultas administrativas y operativas.
        </p>

        <!-- Acciones rápidas -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
          <button
            v-for="action in quickActions"
            :key="action.id"
            @click="selectQuickAction(action)"
            class="p-4 bg-white rounded-xl shadow-lg border border-gray-100 hover:border-blue-300 hover:shadow-xl transition-all duration-300 text-left group transform hover:-translate-y-1"
          >
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-gray-50 rounded-lg flex items-center justify-center group-hover:bg-blue-50 transition-colors duration-200">
                <span class="text-base">{{ action.icon }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-medium text-gray-900 text-sm truncate">{{ action.title }}</p>
                <p class="text-gray-500 text-xs truncate">{{ action.description }}</p>
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Mensajes del chat -->
      <div v-for="(message, index) in messages" :key="index" class="mb-4">
        <div :class="message.sender === 'user' ? 'message-user' : 'message-bot'">
          <div v-if="message.sender === 'assistant'" class="flex items-center space-x-2 mb-2">
            <div class="w-5 h-5 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
              </svg>
            </div>
            <span class="text-xs text-blue-700 font-medium">ZisBot</span>
            <span class="text-xs text-gray-400">•</span>
            <span class="text-xs text-gray-400">{{ formatTime(message.timestamp) }}</span>
          </div>

          <div v-html="formatMessage(message.message)" class="whitespace-pre-wrap"></div>

          <div class="text-xs text-gray-400 mt-2">
            {{ formatTime(message.timestamp) }}
          </div>
        </div>
      </div>

      <!-- Indicador de typing -->
      <div v-if="isTyping" class="message-bot">
        <div class="flex items-center space-x-2">
          <div class="w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center">
            <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <span class="text-xs text-gray-500">ZisBot está escribiendo</span>
        </div>
        <div class="typing-indicator mt-2">
          <div class="typing-dot" style="--delay: 0"></div>
          <div class="typing-dot" style="--delay: 1"></div>
          <div class="typing-dot" style="--delay: 2"></div>
        </div>
      </div>
    </div>

    <!-- Input de chat -->
    <div class="chat-input-container">
      <form @submit.prevent="sendMessage" class="flex items-end space-x-3">
        <div class="flex-1">
          <textarea
            ref="messageInput"
            v-model="currentMessage"
            placeholder="Escribe tu consulta de gestión hospitalaria..."
            rows="1"
            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none text-base shadow-sm focus:shadow-md transition-all duration-200"
            :disabled="isLoading"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.enter.shift.exact="addNewLine"
            @input="adjustTextareaHeight"
          ></textarea>
        </div>

        <button
          type="submit"
          :disabled="isLoading || !currentMessage.trim()"
          class="px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl flex items-center justify-center min-w-[90px] transform hover:-translate-y-0.5"
        >
          <span v-if="isLoading" class="flex items-center">
            <div class="loading-spinner w-3 h-3 mr-1"></div>
            <span class="text-xs">Enviando</span>
          </span>
          <span v-else class="flex items-center">
            <svg class="icon-sm mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
            <span class="text-sm">Enviar</span>
          </span>
        </button>
      </form>

      <div class="text-xs text-gray-500 mt-2 text-center">
        <kbd class="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-medium">Enter</kbd> para enviar •
        <kbd class="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-medium">Shift+Enter</kbd> nueva línea
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRightOnRectangleIcon } from '@heroicons/vue/24/outline'
import { chatAPI, authAPI, apiUtils } from '../services/api'

export default {
  name: 'ChatView',
  components: {
    ArrowRightOnRectangleIcon
  },
  setup() {
    const router = useRouter()

    // Referencias
    const messagesContainer = ref(null)
    const messageInput = ref(null)

    // Estado
    const messages = ref([])
    const currentMessage = ref('')
    const conversationId = ref(null)
    const isLoading = ref(false)
    const isTyping = ref(false)

    // Datos del usuario
    const currentUser = computed(() => apiUtils.getCurrentUserData())
    const currentInstitution = computed(() => apiUtils.getCurrentInstitution())

    // Acciones rápidas
    const quickActions = ref([
      {
        id: 'patient_lookup',
        title: 'Buscar Paciente',
        description: 'Consultar por DNI',
        icon: '👤',
        template: 'Buscar paciente con DNI: '
      },
      {
        id: 'appointment',
        title: 'Turnos Médicos',
        description: 'Consultar o agendar',
        icon: '📅',
        template: 'Quiero consultar sobre turnos médicos'
      },
      {
        id: 'specialties',
        title: 'Especialidades',
        description: 'Ver disponibles',
        icon: '👨‍⚕️',
        template: '¿Qué especialidades están disponibles?'
      },
      {
        id: 'emergency',
        title: 'Emergencias',
        description: 'Información urgente',
        icon: '🆘',
        template: 'Necesito información sobre emergencias'
      }
    ])

    // Métodos
    const sendMessage = async () => {
      const message = currentMessage.value.trim()
      if (!message || isLoading.value) return

      // Agregar mensaje del usuario
      messages.value.push({
        sender: 'user',
        message: message,
        timestamp: new Date().toISOString()
      })

      // Limpiar input
      currentMessage.value = ''

      // Scroll al final
      await nextTick()
      scrollToBottom()

      // Mostrar indicador de typing
      isTyping.value = true
      isLoading.value = true

      try {
        // Enviar mensaje al backend
        const response = await chatAPI.sendMessage(message, conversationId.value)

        // Guardar ID de conversación
        if (response.conversation_id) {
          conversationId.value = response.conversation_id
        }

        // Agregar respuesta del bot
        messages.value.push({
          sender: 'assistant',
          message: response.response,
          timestamp: new Date().toISOString(),
          type: response.type,
          data: response.data
        })

      } catch (error) {
        console.error('Error enviando mensaje:', error)

        // Mensaje de error
        messages.value.push({
          sender: 'assistant',
          message: '🏥 Disculpas, ocurrió un error técnico. Para asistencia inmediata llama al 4212121.',
          timestamp: new Date().toISOString(),
          type: 'error'
        })

        if (window.showNotification) {
          window.showNotification('error', 'Error', 'No se pudo enviar el mensaje')
        }

      } finally {
        isTyping.value = false
        isLoading.value = false

        await nextTick()
        scrollToBottom()
      }
    }

    const selectQuickAction = (action) => {
      currentMessage.value = action.template
      messageInput.value?.focus()
    }

    const addNewLine = () => {
      currentMessage.value += '\n'
    }

    const adjustTextareaHeight = () => {
      const textarea = messageInput.value
      if (textarea) {
        textarea.style.height = 'auto'
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
      }
    }

    const scrollToBottom = () => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    }

    const formatMessage = (message) => {
      // Formatear mensaje con enlaces, emojis, etc.
      return message
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Negrita
        .replace(/\*(.*?)\*/g, '<em>$1</em>') // Cursiva
        .replace(/📞 (\d+)/g, '📞 <a href="tel:$1" class="text-hospital-primary hover:underline">$1</a>') // Teléfonos
        .replace(/🏥|👨‍⚕️|📅|📞|🆘/g, '<span class="text-lg">$&</span>') // Emojis más grandes
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString('es-AR', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const handleLogout = async () => {
      try {
        await authAPI.logout()
        await router.push('/login')

        if (window.showNotification) {
          window.showNotification('info', 'Sesión cerrada', 'Has cerrado sesión correctamente')
        }
      } catch (error) {
        console.error('Error en logout:', error)
      }
    }

    // Inicialización
    onMounted(async () => {
      // Verificar autenticación
      if (!apiUtils.isAuthenticated()) {
        router.push('/login')
        return
      }

      // Focus en el input
      await nextTick()
      messageInput.value?.focus()

      console.log('💬 Chat iniciado para:', currentUser.value?.name)
    })

    return {
      messages,
      currentMessage,
      isLoading,
      isTyping,
      currentUser,
      currentInstitution,
      quickActions,
      messagesContainer,
      messageInput,
      sendMessage,
      selectQuickAction,
      addNewLine,
      adjustTextareaHeight,
      formatMessage,
      formatTime,
      handleLogout
    }
  }
}
</script>

<style scoped>
/* Estilos específicos del chat */
kbd {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", monospace;
}
</style>