from flask import Blueprint, jsonify
from app.db import get_user, redeem_user

qr_bp = Blueprint("qr", __name__)

# -------------------------------
# READ-ONLY: QR STATUS
# -------------------------------
@qr_bp.route("/api/qr/status/<phone>", methods=["GET"])
def qr_status(phone):
    user = get_user(phone)

    if not user:
        return jsonify({
            "status": "not_found",
            "can_redeem": False
        }), 404

    name, state = user

    return jsonify({
        "phone": phone,
        "name": name,
        "state": state,
        "can_redeem": state == "COMPLETED"
    })


# -------------------------------
# MUTATION: REDEEM
# -------------------------------
@qr_bp.route("/api/qr/redeem/<phone>", methods=["POST"])
def qr_redeem(phone):
    result = redeem_user(phone)

    if result == "NOT_FOUND":
        return jsonify({"status": "not_found"}), 404

    if result == "NOT_ELIGIBLE":
        return jsonify({"status": "not_eligible"}), 400

    if result == "ALREADY_REDEEMED":
        return jsonify({"status": "already_redeemed"}), 200

    return jsonify({"status": "redeemed"}), 200
