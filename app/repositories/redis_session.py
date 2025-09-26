import redis
import json
from app.config import Config

SESSION_EXPIRATION = 3600  # segundos (1 hora)

def get_redis_client():
    return redis.StrictRedis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=0,
        decode_responses=True,
    )

def set_user_session(wa_id, key, value):
    redis_client = get_redis_client()
    session_key = f"user_session:{wa_id}"
    redis_client.hset(session_key, key, json.dumps(value))
    redis_client.expire(session_key, SESSION_EXPIRATION)

def get_user_session(wa_id):
    redis_client = get_redis_client()
    session_key = f"user_session:{wa_id}"
    data = redis_client.hgetall(session_key)
    return {k: json.loads(v) for k, v in data.items()}

def update_user_session(wa_id, session_key, new_data):
    session_data = get_user_session(wa_id).get(session_key, {})
    session_data.update(new_data)
    set_user_session(wa_id, session_key, session_data)

def eliminar_sesion_usuario(wa_id):
    clave = f"user:{wa_id}"
    r= get_redis_client()
    r.delete(clave)
    print(f"Sesión completa para {wa_id} eliminada.")