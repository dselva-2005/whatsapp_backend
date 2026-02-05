import os
from PIL import Image, ImageDraw, ImageFont

# -----------------------------
# CONFIG (adjust freely)
# -----------------------------
BASE_COUPON_PATH = "./base_coupon.png"   # copy your base image here
FONT_PATH = "../fonts/DejaVuSans-Bold.ttf"      # copy font here
OUTPUT_PATH = "./preview_coupon.png"

NAME = "KHALIFA MELUR"
PHONE = "919321697497"

FONT_SIZE = 30

# Vertical positions
Y_NAME = 1000
Y_PHONE = 1050

# Horizontal control (USER POV → smaller = more left)
LEFT_PERCENT = 0.25   # try 0.05, 0.06, 0.1 etc

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
    x = int(img_width * LEFT_PERCENT)

    print(f"📐 Image size: {img_width}x{img_height}")
    print(f"✏️ Drawing text at x={x}, y={Y_NAME}/{Y_PHONE}")

    draw.text((x, Y_NAME), NAME, fill="white", font=font)
    draw.text((x, Y_PHONE), f"Mobile: {PHONE}", fill="white", font=font)

    img.save(OUTPUT_PATH)
    print(f"✅ Preview saved as {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
