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

    # Disable HTTP caching globally so Chrome and other browsers 
    # always fetch real-time total job counts from the database
    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    app.register_blueprint(jobs_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)