from fastapi import HTTPException, Request
from redis import Redis
from config import get_settings
import time

settings = get_settings()
redis_client = Redis.from_url(settings.REDIS_URL)

async def rate_limit(request: Request):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    # Получаем текущее количество запросов
    requests = redis_client.get(key)
    
    if requests is None:
        # Первый запрос
        redis_client.setex(key, 60, 1)
    else:
        requests = int(requests)
        if requests >= settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
        redis_client.incr(key) 