import re

from flask import Blueprint, g, jsonify, request

from ..auth import login_required, make_token
from ..extensions import db
from ..models import RevokedToken, User
from .helpers import bad, clean

bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name, email, pw = clean(data.get("name"), 120), clean(data.get("email"), 160).lower(), data.get("password") or ""
    if len(name) < 2:
        return bad("Please enter your full name.")
    if not EMAIL_RE.match(email):
        return bad("Please enter a valid email address.")
    if len(pw) < 8:
        return bad("Password must be at least 8 characters.")
    if User.query.filter_by(email=email).first():
        return bad("That email is already registered.", 409)
    # Self-service sign-up always creates a student; admins promote users later.
    user = User(name=name, email=email, role="student", department=clean(data.get("department"), 120) or None)
    user.set_password(pw)
    db.session.add(user)
    db.session.commit()
    return jsonify(token=make_token(user), user=user.to_dict()), 201


@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(email=clean(data.get("email")).lower()).first()
    if not user or not user.check_password(data.get("password") or ""):
        return bad("Incorrect email or password.", 401)
    if not user.is_active:
        return bad("This account has been deactivated.", 403)
    return jsonify(token=make_token(user), user=user.to_dict())


@bp.get("/auth/me")
@login_required()
def me():
    return jsonify(user=g.user.to_dict())


@bp.post("/auth/logout")
@login_required()
def logout():
    db.session.add(RevokedToken(jti=g.token["jti"]))
    db.session.commit()
    return jsonify(message="Signed out.")
