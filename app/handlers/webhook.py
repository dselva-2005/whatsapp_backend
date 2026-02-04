import logging
from flask import Blueprint, request, jsonify

from app.tasks.queue import enqueue
from app.constants import PRODUCT
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
# Queue helpers
# -------------------------------------------------
def send_text(to, text):
    enqueue({
        "type": "send_text",
        "to": to,
        "text": text,
    })


def send_offer_bundle(to):
    """
    Sends:
    1) Product image
    2) Discount code image
    Guaranteed order via queue
    """
    enqueue({
        "type": "send_offer_bundle",
        "to": to,
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
# Core logic (STATE SAFE + ORDER SAFE)
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

        # Normalize text
        text_body = ""
        if msg_type == "text":
            text_body = message["text"]["body"].strip().lower()

        # -------------------------------------------------
        # 🔒 START GATE (KEYWORD ONLY)
        # -------------------------------------------------
        if state == "START":
            if msg_type != "text":
                return

            if "khalifa melur" not in text_body:
                return

            upsert_user(from_number, state="ASKED_NAME")

            send_text(
                from_number,
                "வணக்கம் கலிபா  ஹைடெக் மொபைல்ஸ் திறப்பு விழா ஆஃபர் பெற உங்களது பெயரை உள்ளிடவும்"
            )
            return

        # -------------------------------------------------
        # NAME RECEIVED → SEND OFFER DIRECTLY
        # -------------------------------------------------
        if state == "ASKED_NAME" and msg_type == "text":
            name = message["text"]["body"].strip()

            # Safety: already received
            if has_user_received(from_number):
                send_text(from_number, "ℹ️ You have already received this offer.")
                upsert_user(from_number, state="COMPLETED")
                return

            # Quota check
            if not can_send_image():
                send_text(from_number, "🚫 Sorry, today’s discount quota is exhausted.")
                return

            upsert_user(from_number, state="COMPLETED", name=name)

            send_text(
                from_number,
                f"கலிபா வின்  திறப்பு விழா ஆஃபர் பெற உறுதி செய்யப்பட்டுவிட்டீர்கள் இதோ உங்களுக்கான கூப்பன்"
            )

            # 🔥 Single queued task (order guaranteed)
            send_offer_bundle(from_number)

            mark_user_received(from_number)
            increment_sent()
            return

        # -------------------------------------------------
        # COMPLETED
        # -------------------------------------------------
        if state == "COMPLETED":
            send_text(from_number, "✅ Offer already used.")
            return

    except Exception:
        logger.exception("🔥 Webhook error")
