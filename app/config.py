import os

class Config:
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "dev_token")
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    PORT = int(os.getenv("PORT", 8000))
