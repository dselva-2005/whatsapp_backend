import os

class Config:
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "dev_token")
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID","")
    WHATSAPP_API_URL = f"https://partnersv1.pinbot.ai/v3/{PHONE_NUMBER_ID}/messages"
    PORT = int(os.getenv("PORT", 8000))
    REDIS_HOST = "redis"
    REDIS_PORT = 6379
