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
        "image": "https://allspray.in/static/images/product1.png",
        "original": 499,
        "discount": 20,
    },
    "opt_2": {
        "image": "https://allspray.in/static/images/product2.png",
        "original": 699,
        "discount": 20,
    },
    "opt_3": {
        "image": "https://allspray.in/static/images/product3.png",
        "original": 599,
        "discount": 49,
    },
    "opt_4": {
        "image": "https://allspray.in/static/images/product4.png",
        "original": 899,
        "discount": 99,
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


def send_image(to: str, image_url: str, caption: str):
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


# 🔥 NEW: Send product previews (image + price)
def send_product_previews(to: str):
    for opt_id, product in PRODUCTS.items():
        discounted_price = product["original"] - product["discount"]

        caption = (
            f"🛍️ *{opt_id.replace('opt_', 'Product ')}*\n"
            f"MRP: ₹{product['original']}\n"
            f"🔥 Offer Price: ₹{discounted_price}\n"
            f"💸 You Save: ₹{product['discount']}"
        )

        send_image(to, product["image"], caption)


def send_options(to: str):
    rows = []

    for opt_id, product in PRODUCTS.items():
        discounted_price = product["original"] - product["discount"]

        rows.append({
            "id": opt_id,
            "title": f"{opt_id.replace('opt_', 'Product ')}",
            "description": (
                f"MRP ₹{product['original']} → "
                f"Now ₹{discounted_price} "
                f"(Save ₹{product['discount']})"
            ),
        })

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "🔥 Exclusive Discounts"},
            "body": {"text": "Select ONE product to get your discount 👇"},
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

        user = get_user(from_number)
        state = user[1] if user else "START"

        # ----------------------------
        # START → Ask name
        # ----------------------------
        if state == "START" and msg_type == "text":
            upsert_user(from_number, state="ASKED_NAME")
            send_text(
                from_number,
                "👋 Welcome to *Khalifa Hitech Mobile!*\n\nPlease tell us your *name*."
            )
            return

        # ----------------------------
        # ASKED_NAME → Save name & show products
        # ----------------------------
        if state == "ASKED_NAME" and msg_type == "text":
            name = message["text"]["body"].strip()
            upsert_user(from_number, state="SHOWED_PRODUCTS", name=name)

            send_text(
                from_number,
                f"Thanks, *{name}* 😊\n\nHere are today’s exclusive offers 👇"
            )

            # 🔥 NEW FLOW
            send_product_previews(from_number)
            send_text(from_number, "👇 Now select ONE product to receive your discount")
            send_options(from_number)
            return

        # ----------------------------
        # SHOWED_PRODUCTS → Handle selection
        # ----------------------------
        if state == "SHOWED_PRODUCTS" and msg_type == "interactive":
            if has_user_received(from_number):
                send_text(
                    from_number,
                    "ℹ️ You have already received your discount barcode."
                )
                return

            if not can_send_image():
                send_text(
                    from_number,
                    "🚫 Discount quota exhausted. Please try again later."
                )
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

            caption = (
                f"Worth ₹{product['original']}\n"
                f"Only ₹{product['original'] - product['discount']}"
            )

            send_text(
                from_number,
                "✅ Thanks for choosing *Khalifa Hitech Mobile*!"
            )

            send_image(from_number, product["image"], caption)

            mark_user_received(from_number)
            increment_sent()
            upsert_user(from_number, state="COMPLETED")
            return

        # ----------------------------
        # COMPLETED
        # ----------------------------
        if state == "COMPLETED":
            send_text(
                from_number,
                "✅ You have already completed this offer."
            )
            return

    except Exception:
        logger.exception("Webhook parse error")
