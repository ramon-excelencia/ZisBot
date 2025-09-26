/**
 * ZisMed Chatbot - Aplicación Principal Vue.js
 * Sistema de chatbot médico con Gemini AI
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// Estilos globales
import './assets/css/tailwind.css'
import './assets/css/app.css'

// Crear aplicación Vue
const app = createApp(App)

// Configurar store (Pinia)
const pinia = createPinia()
app.use(pinia)

// Configurar router
app.use(router)

// Configuración global
app.config.globalProperties.$appName = 'ZisMed Chatbot'
app.config.globalProperties.$version = '1.0.0'
app.config.globalProperties.$hospital = 'Hospital Regional de Santiago del Estero'

// Montar aplicación
app.mount('#app')

console.log('🏥 ZisMed Chatbot iniciado correctamente')
console.log('🤖 Powered by Gemini AI')
console.log('📍 Hospital Regional de Santiago del Estero')