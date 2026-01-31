import json
import time
import redis
import requests

from app.config import Config
from app.handlers.webhook import PRODUCTS

QUEUE = "whatsapp_tasks"


def headers():
    return {
        "Content-Type": "application/json",
        "apikey": Config.WHATSAPP_TOKEN,
    }


def run():
    r = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        decode_responses=True,
    )

    session = requests.Session()
    session.headers.update(headers())

    print("🚀 WhatsApp worker started")

    while True:
        _, raw = r.blpop(QUEUE)
        task = json.loads(raw)

        t = task["type"]
        to = task["to"]

        if t == "send_text":
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": task["text"]},
            }
            session.post(Config.WHATSAPP_API_URL, json=payload)

        elif t == "send_image":
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "image",
                "image": {
                    "link": task["image_url"],
                    "caption": task["caption"],
                },
            }
            session.post(Config.WHATSAPP_API_URL, json=payload)

        elif t == "send_product_previews":
            for product in PRODUCTS.values():
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "image",
                    "image": {
                        "link": product["preview_image"],
                        "caption": product["name"],
                    },
                }
                session.post(Config.WHATSAPP_API_URL, json=payload)
                time.sleep(0.3)  # keep WhatsApp happy

        elif t == "send_options":
            # reuse existing logic
            pass
