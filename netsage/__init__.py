from flask import Flask
from dotenv import load_dotenv

from config import Config


def create_app() -> Flask:
    load_dotenv()

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        static_url_path="/static",
    )
    app.config.from_object(Config)

    from netsage.routes.dashboard import dashboard_bp
    from netsage.routes.main import main_bp
    from netsage.routes.review import review_bp
    from netsage.routes.troubleshooting import troubleshooting_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(troubleshooting_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(dashboard_bp)

    @app.route("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "NetSage AI",
            "phase": "architecture-foundation",
        }

    return app
