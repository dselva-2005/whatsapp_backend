import requests
import logging
from flask import Blueprint, request, jsonify, current_app

from app.db import (
    get_user,
    upsert_user,
    has_user_received,
    mark_user_received,
    can_send_image,
    increment_sent,
)

webhook_bp = Blueprint("webhook", __name__)

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_webhook")

# -------------------------------------------------
# Product configuration
# -------------------------------------------------
PRODUCTS = {
    "opt_1": {
        "preview_image": "https://allspray.in/static/images/product1.png",
        "code_image": "https://allspray.in/static/images/final_network.png",
        "original": 499,
        "discount": 479,
    },
    "opt_2": {
        "preview_image": "https://allspray.in/static/images/product2.png",
        "code_image": "https://allspray.in/static/images/code2.png",
        "original": 699,
        "discount": 679,
    },
    "opt_3": {
        "preview_image": "https://allspray.in/static/images/product3.png",
        "code_image": "https://allspray.in/static/images/code3.png",
        "original": 599,
        "discount": 550,
    },
    "opt_4": {
        "preview_image": "https://allspray.in/static/images/product4.png",
        "code_image": "https://allspray.in/static/images/code4.png",
        "original": 999,
        "discount": 899,
    },
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

# -------------------------------------------------
# Product previews
# -------------------------------------------------
def send_product_previews(to: str):
    for opt_id, product in PRODUCTS.items():
        offer_price = product["original"] - product["discount"]

        caption = (
            f"🛍️ *Product {opt_id[-1]}*\n"
            f"MRP: ₹{product['original']}\n"
            f"🔥 Offer: ₹{offer_price}\n"
            f"💸 Save: ₹{product['discount']}"
        )
        send_image(to, product["preview_image"], caption)


def send_options(to: str):
    rows = []

    for opt_id, product in PRODUCTS.items():
        offer_price = product["original"] - product["discount"]
        rows.append({
            "id": opt_id,
            "title": f"Product {opt_id[-1]}",
            "description": f"₹{product['original']} → ₹{offer_price}",
        })

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "🔥 Exclusive Discounts"},
            "body": {"text": "Select ONE product to receive your discount code 👇"},
            "footer": {"text": "Khalifa Hitech Mobile"},
            "action": {
                "button": "View Products",
                "sections": [
                    {
                        "title": "Available Products",
                        "rows": rows,
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
# Core logic (SEQUENCE SAFE)
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

        user = get_user(from_number)
        state = user[1] if user else "START"

        # ---------------------
        # START
        # ---------------------
        if state == "START" and msg_type == "text":
            upsert_user(from_number, state="ASKED_NAME")
            send_text(
                from_number,
                "👋 Welcome to *Khalifa Hitech Mobile!*\n\nPlease tell us your *name*."
            )
            return

        # ---------------------
        # NAME RECEIVED → SEND IMAGES + OPTIONS
        # ---------------------
        if state == "ASKED_NAME" and msg_type == "text":
            name = message["text"]["body"].strip()

            upsert_user(
                from_number,
                state="SHOWED_PRODUCTS",
                name=name,
            )

            send_text(
                from_number,
                f"Thanks, *{name}* 😊\n\nHere are today’s offers 👇"
            )

            send_product_previews(from_number)
            send_options(from_number)
            return

        # ---------------------
        # PRODUCT SELECTED
        # ---------------------
        if state == "SHOWED_PRODUCTS" and msg_type == "interactive":
            if has_user_received(from_number):
                send_text(from_number, "ℹ️ You have already received your discount code.")
                return

            if not can_send_image():
                send_text(from_number, "🚫 Discount quota exhausted. Please try later.")
                return

            option_id = (
                message.get("interactive", {})
                .get("list_reply", {})
                .get("id")
            )

            product = PRODUCTS.get(option_id)
            if not product:
                send_text(from_number, "Invalid selection ❌")
                return

            send_text(from_number, "🎁 Here is your exclusive discount code 👇")
            send_image(from_number, product["code_image"], "Show this code at the store")

            mark_user_received(from_number)
            increment_sent()
            upsert_user(from_number, state="COMPLETED")
            return

        # ---------------------
        # COMPLETED
        # ---------------------
        if state == "COMPLETED":
            send_text(from_number, "✅ You’ve already used this offer.")
            return

    except Exception:
        logger.exception("Webhook parse error")
