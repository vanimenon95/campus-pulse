import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from .extensions import db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    CORS(app, origins=app.config["CORS_ORIGINS"])
    db.init_app(app)

    from .routes import auth, events, clubs, venues, me, admin, reports, ai
    for module in (auth, events, clubs, venues, me, admin, reports, ai):
        app.register_blueprint(module.bp, url_prefix="/api")

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="Not found."), 404

    @app.errorhandler(405)
    def bad_method(_):
        return jsonify(error="Method not allowed."), 405

    @app.errorhandler(Exception)
    def server_error(err):
        from werkzeug.exceptions import HTTPException
        if isinstance(err, HTTPException):
            return jsonify(error=err.description), err.code
        app.logger.exception(err)
        db.session.rollback()
        return jsonify(error="Something went wrong on the server."), 500

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # Single-service hosting: if the React app has been built (frontend/dist), Flask serves it,
    # so the site and the API share one URL and no CORS / API-URL setup is needed.
    dist = os.path.abspath(os.getenv("FRONTEND_DIST") or os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
    if os.path.isfile(os.path.join(dist, "index.html")):
        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def spa(path):
            if path.startswith("api/"):
                return jsonify(error="Not found."), 404
            target = os.path.join(dist, path)
            if path and os.path.isfile(target):
                return send_from_directory(dist, path)
            return send_from_directory(dist, "index.html")

    with app.app_context():
        db.create_all()  # creates missing tables; database/schema.sql is the same layout
        if os.getenv("AUTO_SEED") == "1":  # load demo data automatically on first start
            from .models import User
            if User.query.count() == 0:
                import seed
                seed.seed()
    return app
