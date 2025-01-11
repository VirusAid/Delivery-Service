from redis import Redis
from config import get_settings
import json

settings = get_settings()
redis_client = Redis.from_url(settings.REDIS_URL)

def cache_key(prefix: str, *args):
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"

def get_cached_data(key: str):
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cached_data(key: str, data: dict, expire_seconds: int = 300):
    redis_client.setex(key, expire_seconds, json.dumps(data)) 