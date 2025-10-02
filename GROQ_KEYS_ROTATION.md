# Sistema de Rotación de API Keys de Groq

## ¿Qué es?

Sistema automático que rota entre múltiples API keys de Groq cuando se alcanza el rate limit (429 error).

## ¿Cómo funciona?

1. **Carga múltiples keys** desde `.env`:
   - `GROQ_API_KEY` (principal)
   - `GROQ_API_KEY_2` (backup 1)
   - `GROQ_API_KEY_3` (backup 2)
   - etc.

2. **Detecta rate limits** automáticamente (error 429)

3. **Rota a la siguiente key** disponible

4. **Continúa operando** sin interrupciones

## Configuración

### 1. Editar `.env`:

```env
GROQ_API_KEY=gsk_tu_primera_key_aqui
GROQ_API_KEY_2=gsk_tu_segunda_key_aqui
GROQ_API_KEY_3=gsk_tu_tercera_key_aqui
```

### 2. Obtener múltiples keys de Groq:

- Ve a: https://console.groq.com/keys
- Crea varias API keys
- Copia cada una en tu `.env`

## Ventajas

✅ **Sin interrupciones**: Rota automáticamente cuando hay rate limit
✅ **Fácil configuración**: Solo agrega keys en `.env`
✅ **Multiplica tu límite**: 3 keys = 300K tokens/día gratis
✅ **Sin código extra**: Funciona automáticamente

## Logs

Verás en el servidor:

```
🔑 Usando Groq con 3 keys disponibles
🔄 Detectado rate limit, rotando API key...
✅ Rotado a nueva key (total: 3)
```

## Límites de Groq Free Tier

- **100,000 tokens/día** por key
- **30 requests/minuto** por key
- Con 3 keys = **300,000 tokens/día**

## Ejemplo de uso

Si tienes 3 keys:
1. Empieza usando `GROQ_API_KEY`
2. Cuando llega a 100K tokens → rota a `GROQ_API_KEY_2`
3. Cuando llega a 100K tokens → rota a `GROQ_API_KEY_3`
4. Total disponible: **300K tokens/día**

## Estructura del código

```
app/utils/groq_key_rotator.py     # Lógica de rotación
app/services/chatbot_service.py    # Integración automática
```

## Resetear keys

Las keys se resetean automáticamente al reiniciar el servidor (vuelve a índice 0).
