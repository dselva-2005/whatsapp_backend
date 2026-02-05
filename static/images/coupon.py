from PIL import Image, ImageDraw, ImageFont

img = Image.open("base_coupon.png")
draw = ImageDraw.Draw(img)

font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    40
)

# Coordinates depend on your image
draw.text((200, 1000), "Ramesh Kumar", fill="white", font=font)
draw.text((200, 1050), "Mobile: 9876543210", fill="white", font=font)

img.save("poster_ramesh.png")