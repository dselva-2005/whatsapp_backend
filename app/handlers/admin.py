from flask import Blueprint, render_template, request, redirect, url_for
from app.db import get_quota, update_max_quota

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/quota", methods=["GET", "POST"])
def quota():
    if request.method == "POST":
        new_quota = request.form.get("quota")

        if new_quota and new_quota.isdigit():
            update_max_quota(int(new_quota))

        return redirect(url_for("admin.quota"))

    max_images, sent_images = get_quota()

    return render_template(
        "admin.html",
        max_images=max_images,
        sent_images=sent_images
    )
