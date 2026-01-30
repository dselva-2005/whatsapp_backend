import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# =====================
# CONFIG
# =====================
ACCESS_TOKEN = "YOUR_WHATSAPP_TOKEN"
PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID"
VERIFY_TOKEN = "VERIFY_ME"

WHATSAPP_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# =====================
# IN-MEMORY DB (simple)
# =====================
USERS = {}

# =====================
# PRODUCT CATALOG
# =====================

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
        "original": 899,
        "discount": 99,
    },
}

# =====================
# HELPERS
# =====================
def send_text(to, text):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(WHATSAPP_URL, headers=HEADERS, json=payload)


def send_image(to, image_url, caption=None):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url
        }
    }
    if caption:
        payload["image"]["caption"] = caption

    requests.post(WHATSAPP_URL, headers=HEADERS, json=payload)


def send_options(to):
    rows = []
    for pid, product in PRODUCTS.items():
        rows.append({
            "id": pid,
            "title": product["name"],
            "description": f"Offer ₹{product['original'] - product['discount']}"
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": "Please select one product 👇"
            },
            "action": {
                "button": "View Products",
                "sections": [{
                    "title": "Available Offers",
                    "rows": rows
                }]
            }
        }
    }

    requests.post(WHATSAPP_URL, headers=HEADERS, json=payload)


def send_product_previews(to):
    for pid, product in PRODUCTS.items():
        offer = product["original"] - product["discount"]

        caption = (
            f"🛍️ *{product['name']}*\n"
            f"MRP: ₹{product['original']}\n"
            f"🔥 Offer: ₹{offer}\n"
            f"💸 Save: ₹{product['discount']}"
        )

        send_image(to, product["preview_image"], caption)
        time.sleep(0.8)  # pacing between images


# =====================
# WEBHOOK
# =====================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid token", 403

    data = request.get_json()

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        message = value["messages"][0]

        from_number = message["from"]
        msg_type = message["type"]

        user = USERS.get(from_number, {"state": "NEW"})

        # =====================
        # NEW USER
        # =====================
        if user["state"] == "NEW":
            send_text(from_number, "Hi 👋\nWhat’s your name?")
            USERS[from_number] = {"state": "ASKED_NAME"}
            return jsonify(success=True)

        # =====================
        # NAME RECEIVED
        # =====================
        if user["state"] == "ASKED_NAME" and msg_type == "text":
            name = message["text"]["body"].strip()
            USERS[from_number] = {
                "state": "SHOWED_PRODUCTS",
                "name": name
            }

            send_text(from_number, f"Thanks, *{name}* 😊\nHere are today’s offers 👇")

            # 1️⃣ Images first
            send_product_previews(from_number)

            # 2️⃣ HARD BARRIER
            time.sleep(2)

            # 3️⃣ Then options
            send_text(from_number, "👇 Select ONE product below")
            time.sleep(1)
            send_options(from_number)

            return jsonify(success=True)

        # =====================
        # PRODUCT SELECTED
        # =====================
        if msg_type == "interactive":
            pid = message["interactive"]["list_reply"]["id"]
            product = PRODUCTS.get(pid)

            send_text(
                from_number,
                f"✅ You selected *{product['name']}*\nOur team will contact you shortly."
            )

            USERS[from_number]["state"] = "DONE"
            return jsonify(success=True)

    except Exception as e:
        print("Error:", e)

    return jsonify(success=True)


if __name__ == "__main__":
    app.run(port=5000)
