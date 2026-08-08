"""
Flask backend entrypoint. Serves job data from the same Supabase DB the
scraper writes to — reuses scraper.common.db.get_client() rather than
opening a second, separately-configured connection.

Run: python -m backend.app
"""
from flask import Flask
from flask_cors import CORS

from backend.routes.jobs import jobs_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)  # tighten to specific origins before production deploy
    app.register_blueprint(jobs_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)