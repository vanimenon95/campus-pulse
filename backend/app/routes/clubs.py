from flask import Blueprint, g, jsonify, request

from ..auth import login_required, optional_auth
from ..extensions import db
from ..models import EVENT_CATEGORIES, Club, ClubActivity, Membership, Notification, User
from ..serializers import club_to_dict
from .helpers import bad, clean

bp = Blueprint("clubs", __name__)


def can_manage_club(user, club):
    return user.role == "admin" or (user.role == "coordinator" and club.coordinator_id == user.id)


@bp.get("/clubs")
@optional_auth
def list_clubs():
    joined = set()
    if g.user:
        joined = {m.club_id for m in Membership.query.filter_by(user_id=g.user.id)}
    q = Club.query.filter_by(is_active=True)
    if term := clean(request.args.get("q"), 80):
        q = q.filter(Club.name.ilike(f"%{term}%"))
    clubs = q.order_by(Club.name).all()
    return jsonify(clubs=[club_to_dict(c, joined=(c.id in joined) if g.user else None) for c in clubs])


@bp.get("/clubs/<int:club_id>")
@optional_auth
def club_detail(club_id):
    c = db.session.get(Club, club_id)
    if not c or not c.is_active:
        return bad("Club not found.", 404)
    joined = bool(g.user and Membership.query.filter_by(user_id=g.user.id, club_id=c.id).first())
    acts = ClubActivity.query.filter_by(club_id=c.id).order_by(ClubActivity.created_at.desc()).limit(20).all()
    d = club_to_dict(c, joined=joined if g.user else None)
    d["activities"] = [{"id": a.id, "title": a.title, "body": a.body, "created_at": a.created_at.isoformat()} for a in acts]
    d["can_manage"] = bool(g.user and can_manage_club(g.user, c))
    return jsonify(club=d)


@bp.post("/clubs")
@login_required("coordinator", "admin")
def create_club():
    data = request.get_json(silent=True) or {}
    name = clean(data.get("name"), 120)
    if len(name) < 3:
        return bad("Club name must be at least 3 characters.")
    if Club.query.filter(db.func.lower(Club.name) == name.lower()).first():
        return bad("A club with that name already exists.", 409)
    category = data.get("category") or "Tech"
    if category not in EVENT_CATEGORIES:
        return bad("Unknown category.")
    coord_id = g.user.id
    if g.user.role == "admin" and data.get("coordinator_id"):
        coord = db.session.get(User, int(data["coordinator_id"]))
        if not coord or coord.role not in ("coordinator", "admin"):
            return bad("Coordinator must be a coordinator or admin account.")
        coord_id = coord.id
    c = Club(name=name, category=category, description=clean(data.get("description"), 2000), coordinator_id=coord_id)
    db.session.add(c)
    db.session.commit()
    return jsonify(club=club_to_dict(c), message="Club created."), 201


@bp.put("/clubs/<int:club_id>")
@login_required("coordinator", "admin")
def update_club(club_id):
    c = db.session.get(Club, club_id)
    if not c or not can_manage_club(g.user, c):
        return bad("Club not found.", 404)
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = clean(data["name"], 120)
        if len(name) < 3:
            return bad("Club name must be at least 3 characters.")
        other = Club.query.filter(db.func.lower(Club.name) == name.lower(), Club.id != c.id).first()
        if other:
            return bad("A club with that name already exists.", 409)
        c.name = name
    if "description" in data:
        c.description = clean(data["description"], 2000)
    if data.get("category") in EVENT_CATEGORIES:
        c.category = data["category"]
    if "is_active" in data and g.user.role == "admin":
        c.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify(club=club_to_dict(c), message="Club updated.")


@bp.post("/clubs/<int:club_id>/join")
@login_required()
def join(club_id):
    c = db.session.get(Club, club_id)
    if not c or not c.is_active:
        return bad("Club not found.", 404)
    if Membership.query.filter_by(user_id=g.user.id, club_id=c.id).first():
        return bad("You are already a member.", 409)
    db.session.add(Membership(user_id=g.user.id, club_id=c.id))
    db.session.add(Notification(user_id=g.user.id, kind="club", message=f"Welcome to {c.name}!"))
    db.session.commit()
    return jsonify(message=f"You joined {c.name}."), 201


@bp.delete("/clubs/<int:club_id>/join")
@login_required()
def leave(club_id):
    m = Membership.query.filter_by(user_id=g.user.id, club_id=club_id).first()
    if not m:
        return bad("You are not a member of this club.", 404)
    db.session.delete(m)
    db.session.commit()
    return jsonify(message="You left the club.")


@bp.get("/clubs/<int:club_id>/members")
@login_required("coordinator", "admin")
def members(club_id):
    c = db.session.get(Club, club_id)
    if not c or not can_manage_club(g.user, c):
        return bad("Club not found.", 404)
    return jsonify(members=[{"user_id": m.user_id, "name": m.user.name, "email": m.user.email,
                             "joined_at": m.joined_at.isoformat()} for m in c.memberships])


@bp.post("/clubs/<int:club_id>/members")
@login_required("coordinator", "admin")
def add_member(club_id):
    c = db.session.get(Club, club_id)
    if not c or not can_manage_club(g.user, c):
        return bad("Club not found.", 404)
    email = clean((request.get_json(silent=True) or {}).get("email")).lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        return bad("No account with that email.", 404)
    if Membership.query.filter_by(user_id=user.id, club_id=c.id).first():
        return bad("Already a member.", 409)
    db.session.add(Membership(user_id=user.id, club_id=c.id))
    db.session.add(Notification(user_id=user.id, kind="club", message=f"You were added to {c.name}."))
    db.session.commit()
    return jsonify(message=f"{user.name} added."), 201


@bp.delete("/clubs/<int:club_id>/members/<int:user_id>")
@login_required("coordinator", "admin")
def remove_member(club_id, user_id):
    c = db.session.get(Club, club_id)
    if not c or not can_manage_club(g.user, c):
        return bad("Club not found.", 404)
    m = Membership.query.filter_by(user_id=user_id, club_id=club_id).first()
    if not m:
        return bad("Member not found.", 404)
    db.session.delete(m)
    db.session.commit()
    return jsonify(message="Member removed.")


@bp.post("/clubs/<int:club_id>/activities")
@login_required("coordinator", "admin")
def publish_activity(club_id):
    c = db.session.get(Club, club_id)
    if not c or not can_manage_club(g.user, c):
        return bad("Club not found.", 404)
    data = request.get_json(silent=True) or {}
    title = clean(data.get("title"), 160)
    if len(title) < 3:
        return bad("Title must be at least 3 characters.")
    a = ClubActivity(club_id=c.id, title=title, body=clean(data.get("body"), 4000))
    db.session.add(a)
    for m in c.memberships:
        db.session.add(Notification(user_id=m.user_id, kind="club", message=f"{c.name}: {title}"))
    db.session.commit()
    return jsonify(message="Activity published to members.", id=a.id), 201


@bp.delete("/clubs/<int:club_id>/activities/<int:activity_id>")
@login_required("coordinator", "admin")
def delete_activity(club_id, activity_id):
    c = db.session.get(Club, club_id)
    a = db.session.get(ClubActivity, activity_id)
    if not c or not a or a.club_id != c.id or not can_manage_club(g.user, c):
        return bad("Activity not found.", 404)
    db.session.delete(a)
    db.session.commit()
    return jsonify(message="Activity removed.")
