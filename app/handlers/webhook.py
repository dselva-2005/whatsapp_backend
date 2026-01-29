from flask import Blueprint, request, jsonify

webhook_bp = Blueprint("webhook", __name__)

@webhook_bp.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data:
        return jsonify({"status": "ignored"}), 200

    print(data)  # log raw payload

    # 🔹 handle everything internally
    handle_event(data)

    return jsonify({"status": "ok"}), 200


def handle_event(payload: dict):
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" in value:
            message = value["messages"][0]
            print("Incoming message:", message)

    except Exception as e:
        print("Parse error:", e)
