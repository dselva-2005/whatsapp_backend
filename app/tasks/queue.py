import json
import redis
from app.config import Config

def get_redis():
    return redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        decode_responses=True
    )

def enqueue(task: dict):
    r = get_redis()
    r.rpush("whatsapp_tasks", json.dumps(task))
