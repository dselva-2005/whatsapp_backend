import logging
import os
from flask import Blueprint, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import qrcode
import time

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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("whatsapp_webhook")

# -------------------------------------------------
# Project paths
# -------------------------------------------------
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGE_DIR = os.path.join(STATIC_DIR, "images")
GENERATED_DIR = os.path.join(IMAGE_DIR, "generated")

BASE_COUPON_PATH = os.path.join(IMAGE_DIR, "base_coupon.png")
FONT_PATH = os.path.join(STATIC_DIR, "fonts", "DejaVuSans-Bold.ttf")

logger.info(f"📁 BASE_DIR={BASE_DIR}")
logger.info(f"🖼️ BASE_COUPON_PATH={BASE_COUPON_PATH}")
logger.info(f"🔤 FONT_PATH={FONT_PATH}")

# -------------------------------------------------
# Image generation
# -------------------------------------------------

def generate_coupon(name: str, phone: str) -> str:
    logger.info(f"🧩 Generating coupon for {phone} | name='{name}'")

    os.makedirs(GENERATED_DIR, exist_ok=True)

    img = Image.open(BASE_COUPON_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    # -----------------------------
    # Text config (LOCKED)
    # -----------------------------
    FONT_SIZE = 30
    Y_NAME = 1000
    Y_PHONE = 1050
    LEFT_PERCENT = 0.25

    # -----------------------------
    # QR config (LOCKED)
    # -----------------------------
    QR_SIZE = 260
    TEXT_TO_QR_GAP = 110

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    name = name.strip()[:25]
    safe_phone = "".join(c for c in phone if c.isdigit())

    img_width, _ = img.size
    x_text = int(img_width * LEFT_PERCENT)

    # -----------------------------
    # Draw text
    # -----------------------------
    draw.text((x_text, Y_NAME), name, fill="white", font=font)
    draw.text((x_text, Y_PHONE), f"Mobile: {safe_phone}", fill="white", font=font)

    # -----------------------------
    # Generate QR (same as preview)
    # -----------------------------
    qr_data = f"KHALIFA|{safe_phone}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    qr_img = qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")

    qr_img = qr_img.resize((QR_SIZE, QR_SIZE), Image.LANCZOS)

    # -----------------------------
    # Center-align QR
    # -----------------------------
    qr_x = (img_width - QR_SIZE) // 2
    qr_y = Y_PHONE + TEXT_TO_QR_GAP

    img.paste(qr_img, (qr_x, qr_y))

    # -----------------------------
    # Save
    # -----------------------------
    filename = f"coupon_{safe_phone}.png"
    output_path = os.path.join(GENERATED_DIR, filename)
    img.save(output_path)

    image_url = f"{Config.BASE_URL}/static/images/generated/{filename}"

    logger.info(f"✅ Coupon generated → {output_path}")
    logger.info(f"🌍 Public image URL → {image_url}")

    return image_url

# -------------------------------------------------
# Queue helpers
# -------------------------------------------------
def send_text(to, text):
    logger.info(f"📤 Queue text → {to} | '{text[:40]}...'")
    enqueue({
        "type": "send_text",
        "to": to,
        "text": text,
    })


def send_image(to, image_url, caption=""):
    logger.info(f"📤 Queue image → {to} | {image_url}")
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
        logger.warning("⚠️ Empty webhook payload")
        return jsonify({"status": "ignored"}), 200

    logger.info("📥 Webhook received")
    handle_event(data)
    return jsonify({"status": "ok"}), 200


# -------------------------------------------------
# Core logic
# -------------------------------------------------
def handle_event(payload):
    try:
        value = payload["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            logger.info("ℹ️ No messages in webhook")
            return

        message = value["messages"][0]
        from_number = message["from"]
        msg_type = message["type"]

        logger.info(f"📨 Incoming message from {from_number} | type={msg_type}")

        user = get_user(from_number)
        state = user[1] if user else "START"

        logger.info(f"👤 User state → {state}")

        text_body = ""
        if msg_type == "text":
            text_body = message["text"]["body"].strip().lower()
            logger.info(f"💬 Text body → '{text_body}'")

        # -------------------------------------------------
        # START GATE
        # -------------------------------------------------
        if state == "START":
            if msg_type != "text":
                logger.info("🚫 START: non-text message ignored")
                return

            if "khalifa melur" not in text_body:
                logger.info("🚫 START: keyword mismatch")
                return

            upsert_user(from_number, state="ASKED_NAME")
            logger.info("➡️ State updated → ASKED_NAME")

            send_text(
                from_number,
                "வணக்கம் கலிபா ஹைடெக் மொபைல்ஸ் திறப்பு விழா ஆஃபர் பெற உங்களது பெயரை உள்ளிடவும்"
            )
            return

        # -------------------------------------------------
        # NAME RECEIVED
        # -------------------------------------------------
        if state == "ASKED_NAME" and msg_type == "text":
            name = message["text"]["body"].strip()
            logger.info(f"📝 Name received → '{name}'")

            if has_user_received(from_number):
                logger.info("⚠️ User already received coupon")
                send_text(from_number, "ℹ️ நீங்கள் ஏற்கனவே கூப்பனை பெற்றுவிட்டீர்கள்.")
                upsert_user(from_number, state="COMPLETED")
                return

            if not can_send_image():
                logger.warning("🚫 Daily coupon limit reached")
                send_text(from_number, "🚫 இன்று கூப்பன் அளவு முடிந்துவிட்டது.")
                return

            upsert_user(from_number, state="COMPLETED", name=name)
            logger.info("➡️ State updated → COMPLETED")

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
            logger.info("📊 Coupon marked as sent")
            return

        # -------------------------------------------------
        # COMPLETED
        # -------------------------------------------------
        if state == "COMPLETED":
            if "khalifa melur" not in text_body:
                logger.info("🚫 START: keyword mismatch")
                return
            
            logger.info("ℹ️ User already completed flow")
            send_text(from_number, "நீங்கள் ஏற்கனவே கூப்பனுக்கு பதிவு செய்துவிட்டீர்கள்!")
            return

    except Exception:
        logger.exception("🔥 Webhook error")
