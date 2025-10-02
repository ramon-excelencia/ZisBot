<template>
  <div class="login-container">
    <div class="login-card slide-up">
      <!-- Header del login -->
      <div class="login-header">
        <div class="login-logo">
          <svg
            class="w-12 h-12 mx-auto text-blue-600"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M12 2L2 7v10c0 5.55 3.84 9.74 8.9 11.82.5.2 1.1.2 1.6 0C17.16 26.74 21 22.55 21 17V7l-10-5zM12 4.14L19 7.7v9.3c0 4.54-3.07 7.82-7 9.53-3.93-1.71-7-4.99-7-9.53V7.7l7-3.56z"
            />
            <path d="M15.5 11.5L14 10l-2 2-2-2-1.5 1.5L10.5 13.5 15.5 11.5z" />
          </svg>
        </div>
        <h1 class="login-title">ZisMed Chatbot</h1>
        <p class="login-subtitle">Chatbot Conversacional y de Gestion</p>
        <div
          class="text-xs text-gray-500 mt-2 flex items-center justify-center"
        >
          <span class="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
          Powered by Groq AI
        </div>
      </div>

      <!-- Formulario de login -->
      <form @submit.prevent="handleLogin" class="login-form">
        <!-- Campo CUIL -->
        <div class="form-group">
          <label for="cuil" class="form-label"> CUIL / DNI </label>
          <input
            id="cuil"
            v-model="formData.cuil"
            type="text"
            class="form-input"
            placeholder="Ej: 20123456789"
            required
            :disabled="isLoading"
            @input="formatCuil"
          />
          <p v-if="errors.cuil" class="form-error">{{ errors.cuil }}</p>
        </div>

        <!-- Campo Contraseña -->
        <div class="form-group">
          <label for="password" class="form-label"> Contraseña </label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            class="form-input"
            placeholder="Ingrese su contraseña"
            required
            :disabled="isLoading"
          />
          <p v-if="errors.password" class="form-error">{{ errors.password }}</p>
        </div>

        <!-- Selector de Institución (mostrar después de validar credenciales) -->
        <div v-if="showInstitutionSelector" class="form-group">
          <label for="institution" class="form-label"> Institución </label>
          <select
            id="institution"
            v-model="selectedInstitutionId"
            class="form-input"
            required
            :disabled="isLoading"
          >
            <option value="">Seleccione una institución...</option>
            <option
              v-for="institution in availableInstitutions"
              :key="institution.id"
              :value="institution.id"
            >
              {{ institution.name }}
            </option>
          </select>
          <p v-if="errors.institution" class="form-error">
            {{ errors.institution }}
          </p>
        </div>

        <!-- Checkbox para términos y condiciones -->
        <div v-if="showTermsCheckbox" class="form-group">
          <label class="flex items-start">
            <input
              v-model="formData.acceptsTerms"
              type="checkbox"
              class="mt-1 mr-2"
              :disabled="isLoading"
            />
            <span class="text-sm text-gray-700">
              Acepto los términos y condiciones de la institución seleccionada
            </span>
          </label>
          <p v-if="errors.terms" class="form-error">{{ errors.terms }}</p>
        </div>

        <!-- Error general -->
        <div
          v-if="generalError"
          class="form-error bg-red-50 border border-red-200 rounded-lg p-3"
        >
          <div class="flex items-start">
            <ExclamationCircleIcon
              class="icon-sm text-red-400 mr-2 mt-0.5 flex-shrink-0"
            />
            <div>
              <p class="font-medium text-red-800">Error de autenticación</p>
              <p class="text-red-700 text-sm mt-1">{{ generalError }}</p>
            </div>
          </div>
        </div>

        <!-- Botón de login -->
        <button
          type="submit"
          class="login-button"
          :disabled="isLoading || !isFormValid"
        >
          <span v-if="isLoading" class="flex items-center justify-center">
            <div class="loading-spinner mr-2"></div>
            Autenticando...
          </span>
          <span v-else> Iniciar Sesión </span>
        </button>
      </form>

      <!-- Información de acceso -->
      <div class="mt-8 pt-6 border-t border-gray-200">
        <div class="text-center text-sm text-gray-500">
          <p class="font-medium mb-2">Información de Acceso:</p>
          <div class="bg-gray-50 rounded-lg p-3 text-left">
            <p>Utilice sus credenciales de ZisMed para acceder al sistema.</p>
            <p class="mt-2 text-xs">Para soporte técnico: Mesa de Ayuda 4212121</p>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-6 text-center text-xs text-gray-400">
        <p>Sistema de Gestión Hospitalaria ZisMed</p>
        <p>© 2025 Hospital Regional - Santiago del Estero</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { ExclamationCircleIcon } from "@heroicons/vue/24/outline";
import { authAPI, apiUtils } from "../services/api";

export default {
  name: "LoginView",
  components: {
    ExclamationCircleIcon,
  },
  setup() {
    const router = useRouter();

    // Estado reactivo
    const isLoading = ref(false);
    const generalError = ref("");

    const formData = ref({
      cuil: "",
      password: "",
      acceptsTerms: false,
    });

    // Estados para el selector de instituciones
    const showInstitutionSelector = ref(false);
    const availableInstitutions = ref([]);
    const selectedInstitutionId = ref("");
    const showTermsCheckbox = ref(false);

    const errors = ref({
      cuil: "",
      password: "",
      institution: "",
      terms: "",
    });

    // Computed properties
    const isFormValid = computed(() => {
      const basicValid =
        formData.value.cuil.length >= 7 && formData.value.password.length > 0;

      if (!showInstitutionSelector.value) {
        return basicValid;
      }

      const institutionValid = selectedInstitutionId.value !== "";
      const termsValid =
        !showTermsCheckbox.value || formData.value.acceptsTerms;

      return basicValid && institutionValid && termsValid;
    });

    // Métodos
    const formatCuil = () => {
      // Limpiar solo números
      let value = formData.value.cuil.replace(/\D/g, "");

      // Limitar a 11 dígitos
      if (value.length > 11) {
        value = value.slice(0, 11);
      }

      formData.value.cuil = value;
      errors.value.cuil = "";
    };

    const validateForm = () => {
      errors.value = { cuil: "", password: "", institution: "", terms: "" };
      let isValid = true;

      // Validar CUIL
      const cuil = formData.value.cuil.replace(/\D/g, "");
      if (cuil.length < 7) {
        errors.value.cuil = "CUIL/DNI debe tener al menos 7 dígitos";
        isValid = false;
      } else if (cuil.length > 11) {
        errors.value.cuil = "CUIL no puede tener más de 11 dígitos";
        isValid = false;
      }

      // Validar contraseña
      if (!formData.value.password.trim()) {
        errors.value.password = "La contraseña es requerida";
        isValid = false;
      }

      // Validar institución si se está mostrando el selector
      if (showInstitutionSelector.value && !selectedInstitutionId.value) {
        errors.value.institution = "Debe seleccionar una institución";
        isValid = false;
      }

      // Validar términos y condiciones si es necesario
      if (showTermsCheckbox.value && !formData.value.acceptsTerms) {
        errors.value.terms = "Debe aceptar los términos y condiciones";
        isValid = false;
      }

      return isValid;
    };

    const handleLogin = async () => {
      generalError.value = "";

      if (!validateForm()) {
        return;
      }

      isLoading.value = true;

      try {
        if (!showInstitutionSelector.value) {
          // Paso 1: Validar credenciales y obtener instituciones
          const result = await authAPI.validateCredentials(
            formData.value.cuil,
            formData.value.password
          );

          if (
            result.success &&
            result.institutions &&
            result.institutions.length > 0
          ) {
            // Credenciales válidas, mostrar selector de instituciones
            availableInstitutions.value = result.institutions;
            showInstitutionSelector.value = true;

            // Si solo hay una institución, seleccionarla automáticamente
            if (result.institutions.length === 1) {
              selectedInstitutionId.value = result.institutions[0].id;
              // Verificar si requiere términos
              if (result.institutions[0].requires_terms) {
                showTermsCheckbox.value = true;
              } else {
                // Login automático si no requiere términos
                await proceedWithInstitutionLogin();
              }
            }

            isLoading.value = false;
          } else {
            // Error de autenticación
            generalError.value = result.message || "Credenciales incorrectas";
            isLoading.value = false;
          }
        } else {
          // Paso 2: Login con institución seleccionada
          await proceedWithInstitutionLogin();
        }
      } catch (error) {
        console.error("❌ Error en login:", error);
        generalError.value =
          error.message || "Error de conexión con el servidor";
        isLoading.value = false;
      }
    };

    // Función auxiliar para el login con institución
    const proceedWithInstitutionLogin = async () => {
      try {
        const result = await authAPI.loginWithInstitution(
          formData.value.cuil,
          formData.value.password,
          selectedInstitutionId.value,
          formData.value.acceptsTerms
        );

        if (result.success) {
          // Login exitoso
          console.log(
            "✅ Login exitoso:",
            result.user.name,
            "-",
            result.selected_institution?.name
          );

          // Mostrar notificación de éxito
          if (window.showNotification) {
            window.showNotification(
              "success",
              "¡Bienvenido!",
              `Sesión iniciada como ${result.user.name} en ${
                result.selected_institution?.name ||
                "la institución seleccionada"
              }`
            );
          }

          // Redirigir al chat
          await router.push("/chat");
        } else {
          // Error de autenticación
          generalError.value = result.message || "Error en el login";
        }
      } catch (error) {
        console.error("❌ Error en login con institución:", error);
        generalError.value =
          error.message || "Error de conexión con el servidor";
      } finally {
        isLoading.value = false;
      }
    };

    // Función para manejar cambio de institución
    const onInstitutionChange = () => {
      const selectedInstitution = availableInstitutions.value.find(
        (inst) => inst.id === selectedInstitutionId.value
      );

      if (selectedInstitution && selectedInstitution.requires_terms) {
        showTermsCheckbox.value = true;
        formData.value.acceptsTerms = false;
      } else {
        showTermsCheckbox.value = false;
        formData.value.acceptsTerms = false;
      }
    };

    // Watch para cambios en la institución seleccionada
    watch(selectedInstitutionId, onInstitutionChange);

    // Inicialización
    onMounted(() => {
      // Verificar si ya está logueado
      if (apiUtils.isAuthenticated()) {
        router.push("/chat");
      }
    });

    return {
      formData,
      errors,
      generalError,
      isLoading,
      isFormValid,
      showInstitutionSelector,
      availableInstitutions,
      selectedInstitutionId,
      showTermsCheckbox,
      formatCuil,
      handleLogin,
    };
  },
};
</script>

<style scoped>
/* Estilos específicos del login están en app.css */
</style>
