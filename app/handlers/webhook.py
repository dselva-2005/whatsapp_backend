import requests
import logging
import time
from flask import Blueprint, request, jsonify, current_app
from app.tasks.queue import enqueue


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
        "name": "Product 1",
        "preview_image": "https://allspray.in/static/images/product1.png",
        "code_image": "https://allspray.in/static/images/final_network.png",
        "original": 499,
        "discount": 479,
    },
    "opt_2": {
        "name": "Product 2",
        "preview_image": "https://allspray.in/static/images/product2.png",
        "code_image": "https://allspray.in/static/images/code2.png",
        "original": 699,
        "discount": 679,
    },
    "opt_3": {
        "name": "Product 3",
        "preview_image": "https://allspray.in/static/images/product3.png",
        "code_image": "https://allspray.in/static/images/code3.png",
        "original": 599,
        "discount": 550,
    },
    "opt_4": {
        "name": "Product 4",
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


def send_text(to, text):
    enqueue({
        "type": "send_text",
        "to": to,
        "text": text
    })


def send_image(to, image_url, caption=""):
    enqueue({
        "type": "send_image",
        "to": to,
        "image_url": image_url,
        "caption": caption
    })


# -------------------------------------------------
# Product preview images (send in sequence)
# -------------------------------------------------
def send_product_previews(to):
    enqueue({
        "type": "send_product_previews",
        "to": to
    })


# -------------------------------------------------
# Interactive options (after all previews)
# -------------------------------------------------
def send_options(to):
    enqueue({
        "type": "send_options",
        "to": to
    })


# -------------------------------------------------
# Webhook endpoint
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
def handle_event(payload):
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        if "messages" not in value:
            return

        message = value["messages"][0]
        from_number = message["from"]
        msg_type = message["type"]

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
        # NAME RECEIVED
        # ---------------------
        if state == "ASKED_NAME" and msg_type == "text":
            name = message["text"]["body"].strip()
            upsert_user(from_number, state="SHOWED_PRODUCTS", name=name)

            send_text(
                from_number,
                f"Thanks, *{name}* 😊\n\nHere are today’s offers 👇"
            )
            # Send interactive options after all images
            send_options(from_number)

            # Send all product images in sequence
            send_product_previews(from_number)

            return

        # ---------------------
        # PRODUCT SELECTED
        # ---------------------
        if state == "SHOWED_PRODUCTS" and msg_type == "interactive":
            if has_user_received(from_number):
                send_text(from_number, "ℹ️ You have already received your discount code.")
                return

            if not can_send_image():
                send_text(from_number, "🚫 Discount quota exhausted.")
                return

            opt_id = message["interactive"]["list_reply"]["id"]
            product = PRODUCTS.get(opt_id)

            send_text(from_number, "🎁 Here is your exclusive discount code 👇")
            send_image(from_number, product["code_image"], "Show this at the store")

            mark_user_received(from_number)
            increment_sent()
            upsert_user(from_number, state="COMPLETED")
            return

        # ---------------------
        # COMPLETED
        # ---------------------
        if state == "COMPLETED":
            send_text(from_number, "✅ Offer already used.")
            return

    except Exception:
        logger.exception("Webhook error")
