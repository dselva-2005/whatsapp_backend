from flask import render_template, request, redirect
from app.db import get_db

def quota_page():
    db = get_db()

    if request.method == "POST":
        new_quota = int(request.form["quota"])
        db.execute(
            "UPDATE quota SET limit_value = ? WHERE id = 1",
            (new_quota,)
        )
        db.commit()
        return redirect("/admin/quota")

    cur = db.execute("SELECT limit_value FROM quota WHERE id = 1")
    quota = cur.fetchone()[0]

    return render_template("admin.html", quota=quota)
