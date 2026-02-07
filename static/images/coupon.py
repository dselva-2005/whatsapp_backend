import os
from PIL import Image, ImageDraw, ImageFont
import qrcode

# -----------------------------
# CONFIG (adjust freely)
# -----------------------------
BASE_COUPON_PATH = "./base_coupon.png"
FONT_PATH = "../fonts/DejaVuSans-Bold.ttf"
OUTPUT_PATH = "./preview_coupon.png"

NAME = "KHALIFA MELUR"
PHONE = "919321697497"

FONT_SIZE = 30

# Vertical positions
Y_NAME = 1000
Y_PHONE = 1050

# QR placement
QR_SIZE = 260
TEXT_TO_QR_GAP = 110   # ✅ EXACT gap you requested

# Horizontal control
LEFT_PERCENT = 0.25

# -----------------------------
# SCRIPT
# -----------------------------
def main():
    if not os.path.exists(BASE_COUPON_PATH):
        raise FileNotFoundError("❌ base_coupon.png not found")

    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError("❌ Font file not found")

    img = Image.open(BASE_COUPON_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    img_width, img_height = img.size
    x_text = int(img_width * LEFT_PERCENT)

    print(f"📐 Image size: {img_width}x{img_height}")

    # -----------------------------
    # Draw text
    # -----------------------------
    draw.text((x_text, Y_NAME), NAME, fill="white", font=font)
    draw.text((x_text, Y_PHONE), f"Mobile: {PHONE}", fill="white", font=font)

    # -----------------------------
    # Generate QR Code
    # -----------------------------
    qr_data = f"KHALIFA|{PHONE}"
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

    qr_img = qr_img.resize((QR_SIZE, QR_SIZE))

    # -----------------------------
    # Position QR (center aligned)
    # -----------------------------
    qr_x = (img_width - QR_SIZE) // 2
    qr_y = Y_PHONE + TEXT_TO_QR_GAP

    print(f"🔳 QR placed at x={qr_x}, y={qr_y}")

    img.paste(qr_img, (qr_x, qr_y))

    # -----------------------------
    # Save output
    # -----------------------------
    img.save(OUTPUT_PATH)
    print(f"✅ Preview saved as {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
