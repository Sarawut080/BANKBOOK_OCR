from dotenv import load_dotenv
from flask import Flask

from .config import Config


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    from .routes.ocr import bp as ocr_bp
    from .routes.web import bp as web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(ocr_bp)

    return app
