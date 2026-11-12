from flask import g, jsonify, request

from auth_service import AuthService
from config import FlaskConfig


def register_auth_routes(app, database):
    service = AuthService(database, FlaskConfig.AUTH_SESSION_TTL_SECONDS)

    def credentials():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ValueError("Provide an email and password.")
        return payload.get("email"), payload.get("password")

    @app.post("/api/auth/register")
    def register():
        try:
            email, password = credentials()
            return jsonify(service.register(email, password)), 201
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except FileExistsError as exc:
            return jsonify(error=str(exc)), 409

    @app.post("/api/auth/login")
    def login():
        try:
            email, password = credentials()
            return jsonify(service.login(email, password))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except PermissionError as exc:
            return jsonify(error=str(exc)), 401

    @app.get("/api/auth/me")
    def current_user():
        return jsonify({"user": {"id": g.user["id"], "email": g.user["email"]}})

    @app.post("/api/auth/logout")
    def logout():
        service.revoke(g.auth_token)
        return jsonify({"status": "signed_out"})

    return service
