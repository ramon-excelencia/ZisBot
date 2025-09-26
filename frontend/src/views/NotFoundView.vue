<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
    <div class="text-center">
      <div class="w-24 h-24 bg-hospital-primary bg-opacity-10 rounded-full flex items-center justify-center mx-auto mb-6">
        <svg class="w-12 h-12 text-hospital-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 0a4 4 0 014-4h.01M9 12a4 4 0 000 8h6a4 4 0 000-8z"></path>
        </svg>
      </div>

      <h1 class="text-6xl font-bold text-gray-900 mb-4">404</h1>
      <h2 class="text-2xl font-semibold text-gray-700 mb-4">Página no encontrada</h2>
      <p class="text-gray-600 mb-8 max-w-md mx-auto">
        La página que buscas no existe en el sistema ZisMed Chatbot.
        Verifica la URL o regresa al inicio.
      </p>

      <div class="space-x-4">
        <router-link
          to="/chat"
          class="medical-button"
        >
          🏠 Ir al Chat
        </router-link>

        <router-link
          to="/login"
          class="medical-button-secondary"
        >
          🔐 Iniciar Sesión
        </router-link>
      </div>

      <div class="mt-12 text-sm text-gray-500">
        <p>ZisMed Chatbot - Hospital Regional de Santiago del Estero</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NotFoundView'
}
</script>