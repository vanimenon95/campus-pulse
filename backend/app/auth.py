"""JWT authentication helpers and role decorators."""
import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from .extensions import db
from .models import RevokedToken, User, utcnow


def make_token(user: User) -> str:
    payload = {"sub": str(user.id), "role": user.role, "jti": uuid.uuid4().hex,
               "exp": utcnow() + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"])}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _load_user(required: bool):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None if not required else "Please sign in."
    try:
        data = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return "Session expired. Please sign in again."
    except jwt.InvalidTokenError:
        return "Invalid session. Please sign in again."
    if RevokedToken.query.filter_by(jti=data["jti"]).first():
        return "You have been signed out."
    user = db.session.get(User, int(data["sub"]))
    if not user or not user.is_active:
        return "Account not available."
    g.token = data
    return user


def optional_auth(fn):
    """Attach g.user when a valid token is sent; anonymous requests still pass."""
    @wraps(fn)
    def wrapper(*a, **kw):
        user = _load_user(required=False)
        g.user = user if isinstance(user, User) else None
        return fn(*a, **kw)
    return wrapper


def login_required(*roles):
    """Require a signed-in user, optionally restricted to the given roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            user = _load_user(required=True)
            if not isinstance(user, User):
                return jsonify(error=user), 401
            if roles and user.role not in roles:
                return jsonify(error="You do not have permission to do that."), 403
            g.user = user
            return fn(*a, **kw)
        return wrapper
    return decorator
