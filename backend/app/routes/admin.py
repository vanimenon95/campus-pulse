from flask import Blueprint, g, jsonify, request

from ..auth import login_required
from ..extensions import db
from ..models import ROLES, Club, Event, Registration, User, Venue
from .helpers import bad, clean

bp = Blueprint("admin", __name__)


@bp.get("/admin/overview")
@login_required("admin")
def overview():
    return jsonify(users=User.query.count(), clubs=Club.query.filter_by(is_active=True).count(),
                   venues=Venue.query.count(), events=Event.query.count(),
                   published=Event.query.filter_by(status="published").count(),
                   registrations=Registration.query.count())


@bp.get("/admin/users")
@login_required("admin")
def users():
    q = User.query
    if term := clean(request.args.get("q"), 80):
        q = q.filter(db.or_(User.name.ilike(f"%{term}%"), User.email.ilike(f"%{term}%")))
    if role := request.args.get("role"):
        q = q.filter_by(role=role)
    return jsonify(users=[u.to_dict() for u in q.order_by(User.name).limit(200)])


@bp.put("/admin/users/<int:user_id>")
@login_required("admin")
def update_user(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return bad("User not found.", 404)
    d = request.get_json(silent=True) or {}
    if u.id == g.user.id and (d.get("role", u.role) != "admin" or d.get("is_active") is False):
        return bad("You cannot demote or deactivate your own account.")
    if "role" in d:
        if d["role"] not in ROLES:
            return bad("Unknown role.")
        u.role = d["role"]
    if "is_active" in d:
        u.is_active = bool(d["is_active"])
    db.session.commit()
    return jsonify(user=u.to_dict(), message="User updated.")


@bp.delete("/admin/users/<int:user_id>")
@login_required("admin")
def delete_user(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return bad("User not found.", 404)
    if u.id == g.user.id:
        return bad("You cannot delete your own account.")
    if Club.query.filter_by(coordinator_id=u.id).first() or Event.query.filter_by(created_by=u.id).first():
        u.is_active = False  # keep history intact: deactivate instead of deleting
        db.session.commit()
        return jsonify(message="User owns clubs/events, so the account was deactivated instead.")
    from ..models import Membership, Notification
    Registration.query.filter_by(user_id=u.id).delete()
    Membership.query.filter_by(user_id=u.id).delete()
    Notification.query.filter_by(user_id=u.id).delete()
    db.session.delete(u)
    db.session.commit()
    return jsonify(message="User deleted.")


@bp.get("/admin/clubs")
@login_required("admin")
def all_clubs():
    from ..serializers import club_to_dict
    return jsonify(clubs=[club_to_dict(c) for c in Club.query.order_by(Club.name)])


@bp.get("/admin/events")
@login_required("admin")
def all_events():
    from ..serializers import event_to_dict
    return jsonify(events=[event_to_dict(e) for e in Event.query.order_by(Event.start.desc()).limit(200)])
