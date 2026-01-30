from flask import Blueprint, request
from app.handlers.admin import quota_page

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin/quota", methods=["GET", "POST"])
def admin_quota():
    return quota_page()
