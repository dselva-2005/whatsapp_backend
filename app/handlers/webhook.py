import logging
import os
from flask import Blueprint, request, jsonify
from PIL import Image, ImageDraw, ImageFont

from app.tasks.queue import enqueue
from app.config import Config
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
# Project paths (🔥 FIXED)
# -------------------------------------------------
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..","..")
)

STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGE_DIR = os.path.join(STATIC_DIR, "images")
GENERATED_DIR = os.path.join(IMAGE_DIR, "generated")

BASE_COUPON_PATH = os.path.join(IMAGE_DIR, "base_coupon.png")

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# -------------------------------------------------
# Image generation
# -------------------------------------------------
def generate_coupon(name: str, phone: str) -> str:
    """
    Generates personalized coupon
    Returns PUBLIC HTTPS URL
    """
    os.makedirs(GENERATED_DIR, exist_ok=True)

    img = Image.open(BASE_COUPON_PATH)
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(FONT_PATH, 40)

    draw.text((200, 1000), name, fill="white", font=font)
    draw.text((200, 1050), f"Mobile: {phone}", fill="white", font=font)

    filename = f"coupon_{phone}.png"
    output_path = os.path.join(GENERATED_DIR, filename)
    img.save(output_path)

    # Public URL WhatsApp can access
    return f"{Config.BASE_URL}/static/images/generated/{filename}"


# -------------------------------------------------
# Queue helpers
# -------------------------------------------------
def send_text(to, text):
    enqueue({
        "type": "send_text",
        "to": to,
        "text": text,
    })


def send_image(to, image_url, caption=""):
    enqueue({
        "type": "send_image",
        "to": to,
        "image_url": image_url,
        "caption": caption,
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

        text_body = ""
        if msg_type == "text":
            text_body = message["text"]["body"].strip().lower()

        # -------------------------------------------------
        # START GATE
        # -------------------------------------------------
        if state == "START":
            if msg_type != "text":
                return

            if "khalifa melur" not in text_body:
                return

            upsert_user(from_number, state="ASKED_NAME")

            send_text(
                from_number,
                "வணக்கம் கலிபா ஹைடெக் மொபைல்ஸ் திறப்பு விழா ஆஃபர் பெற உங்களது பெயரை உள்ளிடவும்"
            )
            return

        # -------------------------------------------------
        # NAME RECEIVED → GENERATE & SEND COUPON
        # -------------------------------------------------
        if state == "ASKED_NAME" and msg_type == "text":
            name = message["text"]["body"].strip()

            if has_user_received(from_number):
                send_text(from_number, "ℹ️ நீங்கள் ஏற்கனவே கூப்பனை பெற்றுவிட்டீர்கள்.")
                upsert_user(from_number, state="COMPLETED")
                return

            if not can_send_image():
                send_text(from_number, "🚫 இன்று கூப்பன் அளவு முடிந்துவிட்டது.")
                return

            upsert_user(from_number, state="COMPLETED", name=name)

            send_text(
                from_number,
                "🎉 கலிபா ஹைடெக் மொபைல்ஸ் திறப்பு விழா ஆஃபர் உறுதி செய்யப்பட்டது!"
            )

            image_url = generate_coupon(name, from_number)

            send_image(
                from_number,
                image_url,
                "🎟️ இந்த கூப்பனை கடையில் காட்டவும்"
            )

            mark_user_received(from_number)
            increment_sent()
            return

        # -------------------------------------------------
        # COMPLETED
        # -------------------------------------------------
        if state == "COMPLETED":
            send_text(from_number, "நீங்கள் ஏற்கனவே கூப்பனுக்கு பதிவு செய்துவிட்டீர்கள்!")
            return

    except Exception:
        logger.exception("🔥 Webhook error")
