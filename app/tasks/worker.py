import json
import redis
import requests
import logging

from app.config import Config
from app.constants import PRODUCT

QUEUE = "whatsapp_tasks"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_worker")


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

    logger.info("🚀 WhatsApp worker started and waiting for tasks...")

    while True:
        try:
            _, raw = r.blpop(QUEUE)
            task = json.loads(raw)

            task_type = task.get("type")
            to = task.get("to")

            if not task_type or not to:
                logger.warning(f"⚠️ Invalid task skipped: {task}")
                continue

            logger.info(f"➡️ Processing task: {task_type} → {to}")

            # -------------------------
            # SEND TEXT
            # -------------------------
            if task_type == "send_text":
                session.post(
                    Config.WHATSAPP_API_URL,
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {
                            "body": task["text"]
                        },
                    },
                    timeout=10,
                )

            # -------------------------
            # SEND IMAGE (GENERIC)
            # -------------------------
            elif task_type == "send_image":
                session.post(
                    Config.WHATSAPP_API_URL,
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "image",
                        "image": {
                            "link": task["image_url"],
                            "caption": task.get("caption", ""),
                        },
                    },
                    timeout=10,
                )

            # -------------------------------------------------
            # SEND OFFER BUNDLE (PRODUCT → CODE)
            # -------------------------------------------------
            elif task_type == "send_offer_bundle":

                # # 1️⃣ Send product preview image
                # session.post(
                #     Config.WHATSAPP_API_URL,
                #     json={
                #         "messaging_product": "whatsapp",
                #         "to": to,
                #         "type": "image",
                #         "image": {
                #             "link": PRODUCT["preview_image"],
                #             "caption": f"*{PRODUCT['name']}*",
                #         },
                #     },
                #     timeout=10,
                # )

                # 2️⃣ Send discount code image
                session.post(
                    Config.WHATSAPP_API_URL,
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "image",
                        "image": {
                            "link": PRODUCT["code_image"],
                            "caption": "🎟️ Show this code at the store",
                        },
                    },
                    timeout=10,
                )

            else:
                logger.warning(f"⚠️ Unknown task type: {task_type}")

        except Exception:
            logger.exception("🔥 Worker error")


if __name__ == "__main__":
    run()
