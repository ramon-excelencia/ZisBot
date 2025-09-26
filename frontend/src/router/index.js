/**
 * Vue Router Configuration
 * Rutas de la aplicación ZisMed Chatbot
 */
import { createRouter, createWebHistory } from 'vue-router'
import { apiUtils } from '../services/api'

// Importar vistas
import LoginView from '../views/LoginView.vue'
import ChatView from '../views/ChatView.vue'
import NotFoundView from '../views/NotFoundView.vue'

// Definir rutas
const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: {
      requiresAuth: false,
      title: 'Iniciar Sesión - ZisMed'
    }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatView,
    meta: {
      requiresAuth: true,
      title: 'Chatbot - ZisMed'
    }
  },
  {
    path: '/chat/:conversationId',
    name: 'ChatConversation',
    component: ChatView,
    props: true,
    meta: {
      requiresAuth: true,
      title: 'Conversación - ZisMed'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFoundView,
    meta: {
      title: 'Página no encontrada - ZisMed'
    }
  }
]

// Crear router
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// Guards de navegación
router.beforeEach((to, from, next) => {
  // Actualizar título de página
  if (to.meta.title) {
    document.title = to.meta.title
  }

  // Verificar autenticación
  const isAuthenticated = apiUtils.isAuthenticated()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)

  if (requiresAuth && !isAuthenticated) {
    // Ruta requiere autenticación pero usuario no está logueado
    next('/login')
  } else if (to.path === '/login' && isAuthenticated) {
    // Usuario ya está logueado, redirigir al chat
    next('/chat')
  } else {
    // Permitir navegación
    next()
  }
})

// Log de navegación en desarrollo
if (import.meta.env.DEV) {
  router.afterEach((to, from) => {
    console.log('🧭 Navegación:', from.path, '->', to.path)
  })
}

export default router