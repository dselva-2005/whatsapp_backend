import json
import redis
import requests
import logging

from app.config import Config
from app.constants import PRODUCTS

QUEUE = "whatsapp_tasks"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_worker")


def headers():
    return {
        "Content-Type": "application/json",
        "apikey": Config.WHATSAPP_TOKEN,
    }


def format_price(product: dict) -> str:
    original = product["original"]
    you_save = product["discount"]
    offer = original - you_save

    return (
        f"Original: ₹{original}\n"
        f"You save: ₹{you_save}\n"
        f"Offer: ₹{offer}"
    )


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
                        "text": {"body": task["text"]},
                    },
                    timeout=10,
                )

            # -------------------------
            # SEND IMAGE (DISCOUNT CODE)
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
            # SEND PRODUCTS (FAST, NO SLEEP)
            # -------------------------------------------------
            elif task_type == "send_products_with_options":

                # 🔹 Send all product images consecutively
                for product in PRODUCTS.values():
                    session.post(
                        Config.WHATSAPP_API_URL,
                        json={
                            "messaging_product": "whatsapp",
                            "to": to,
                            "type": "image",
                            "image": {
                                "link": product["preview_image"],
                                "caption": (
                                    f"*{product['name']}*\n"
                                    f"{format_price(product)}"
                                ),
                            },
                        },
                        timeout=10,
                    )

                # 🔹 Send options (order relative to images not guaranteed)
                rows = []
                for pid, product in PRODUCTS.items():
                    original = product["original"]
                    you_save = product["discount"]
                    offer = original - you_save

                    rows.append({
                        "id": pid,
                        "title": product["name"],
                        "description": (
                            f"Original ₹{original} | "
                            f"You save ₹{you_save} | "
                            f"Offer ₹{offer}"
                        ),
                    })

                session.post(
                    Config.WHATSAPP_API_URL,
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "interactive",
                        "interactive": {
                            "type": "list",
                            "body": {
                                "text": "🛍️ Choose a product to get your discount code"
                            },
                            "action": {
                                "button": "View Products",
                                "sections": [
                                    {
                                        "title": "Available Offers",
                                        "rows": rows,
                                    }
                                ],
                            },
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
