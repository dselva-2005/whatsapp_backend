import requests
import logging
from flask import Blueprint, request, jsonify, current_app
from app.db import get_quota, increment_sent

webhook_bp = Blueprint("webhook", __name__)

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_webhook")

# -------------------------------------------------
# Option → Image mapping
# -------------------------------------------------
IMAGE_MAP = {
    "opt_1": "https://allspray.in/static/images/final_network.png",
    "opt_2": "https://allspray.in/static/images/sample2.png",
    "opt_3": "https://allspray.in/static/images/sample3.png",
    "opt_4": "https://allspray.in/static/images/sample4.png",
}

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _headers():
    return {
        "Content-Type": "application/json",
        "apikey": current_app.config["WHATSAPP_TOKEN"],
    }


def send_text(to: str, text: str):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    requests.post(
        current_app.config["WHATSAPP_API_URL"],
        headers=_headers(),
        json=payload,
        timeout=10,
    )


def send_image(to: str, image_url: str, caption: str = ""):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption,
        },
    }
    requests.post(
        current_app.config["WHATSAPP_API_URL"],
        headers=_headers(),
        json=payload,
        timeout=10,
    )


def send_options(to: str):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Welcome 👋"},
            "body": {"text": "Please choose one option below:"},
            "footer": {"text": "Allspray"},
            "action": {
                "button": "View Options",
                "sections": [
                    {
                        "title": "Options",
                        "rows": [
                            {"id": "opt_1", "title": "Option 1"},
                            {"id": "opt_2", "title": "Option 2"},
                            {"id": "opt_3", "title": "Option 3"},
                            {"id": "opt_4", "title": "Option 4"},
                        ],
                    }
                ],
            },
        },
    }
    requests.post(
        current_app.config["WHATSAPP_API_URL"],
        headers=_headers(),
        json=payload,
        timeout=10,
    )

# -------------------------------------------------
# Webhook entrypoint
# -------------------------------------------------
@webhook_bp.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "ignored"}), 200

    handle_event(data)
    return jsonify({"status": "ok"}), 200


# -------------------------------------------------
# Core logic
# -------------------------------------------------
def handle_event(payload: dict):
    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})

        if "messages" not in value:
            return

        message = value["messages"][0]
        from_number = message.get("from")
        msg_type = message.get("type")

        # Text → options
        if msg_type == "text":
            send_options(from_number)
            return

        # Interactive → image (quota guarded)
        if msg_type == "interactive":
            option_id = (
                message.get("interactive", {})
                .get("list_reply", {})
                .get("id")
            )

            max_images, sent_images = get_quota()

            if sent_images >= max_images:
                send_text(
                    from_number,
                    "🚫 Image limit reached. Please try again later.",
                )
                return

            image_url = IMAGE_MAP.get(option_id)
            if not image_url:
                send_text(from_number, "Invalid option ❌")
                return

            send_image(from_number, image_url, "Here you go 📷")
            increment_sent()

    except Exception:
        logger.exception("Webhook parse error")
