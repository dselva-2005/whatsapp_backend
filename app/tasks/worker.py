import json
import redis
import requests
import logging

from app.config import Config

QUEUE = "whatsapp_tasks"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_worker")


# -------------------------------------------------
# WhatsApp headers
# -------------------------------------------------
def headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
    }


# -------------------------------------------------
# Worker loop
# -------------------------------------------------
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
                response = session.post(
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

                logger.info(f"✅ Text sent → {response.status_code}")

            # -------------------------
            # SEND IMAGE (PUBLIC URL)
            # -------------------------
            elif task_type == "send_image":
                image_url = task.get("image_url")

                if not image_url:
                    logger.warning("⚠️ send_image task missing image_url")
                    continue

                response = session.post(
                    Config.WHATSAPP_API_URL,
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "image",
                        "image": {
                            "link": image_url,
                            "caption": task.get("caption", ""),
                        },
                    },
                    timeout=10,
                )

                logger.info(f"🖼️ Image sent → {response.status_code}")

            else:
                logger.warning(f"⚠️ Unknown task type: {task_type}")

        except Exception:
            logger.exception("🔥 Worker crashed while processing task")


# -------------------------------------------------
# Entry
# -------------------------------------------------
if __name__ == "__main__":
    run()
