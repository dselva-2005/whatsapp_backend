from flask import Blueprint, render_template, request, redirect, url_for
from app.db import get_quota, update_max_quota

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        new_limit = int(request.form["max_images"])
        update_max_quota(new_limit)
        return redirect(url_for("admin.admin"))

    max_images, sent_images = get_quota()

    return render_template(
        "admin.html",
        max_images=max_images,
        sent_images=sent_images,
    )
