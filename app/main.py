from flask import Flask
from app.config import Config
from app.handlers.webhook import webhook_bp
from app.handlers.admin import admin_bp
from app.db import init_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db()  # ✅ ensure DB exists

    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
