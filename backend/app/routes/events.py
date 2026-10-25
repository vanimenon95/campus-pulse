from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, request

from ..auth import login_required, optional_auth
from ..extensions import db
from ..models import utcnow, EVENT_CATEGORIES, Club, Event, Notification, Registration, Venue
from ..serializers import event_to_dict
from ..services.insights import InsightEngine
from .helpers import bad, clean, parse_dt

bp = Blueprint("events", __name__)


def can_manage_event(user, event):
    """Admins manage everything; coordinators only their own clubs' events."""
    return user.role == "admin" or (user.role == "coordinator" and event.club.coordinator_id == user.id)


def week_bounds(offset):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return monday, monday + timedelta(days=7)


@bp.get("/events")
@optional_auth
def list_events():
    """Public feed. Query: q, category, week (offset, 0=this week), upcoming=1, club_id, mine=1."""
    q = Event.query.filter(Event.status == "published")
    if request.args.get("upcoming") == "1":
        q = q.filter(Event.end >= datetime.now())
    elif request.args.get("week") not in (None, "", "all"):
        try:
            start, end = week_bounds(int(request.args["week"]))
        except ValueError:
            return bad("week must be a number.")
        q = q.filter(Event.start >= start, Event.start < end)
    if cat := request.args.get("category"):
        q = q.filter(Event.category == cat)
    if club_id := request.args.get("club_id", type=int):
        q = q.filter(Event.club_id == club_id)
    if term := clean(request.args.get("q"), 80):
        like = f"%{term}%"
        q = q.join(Club).filter(db.or_(Event.title.ilike(like), Club.name.ilike(like), Event.description.ilike(like)))
    events = q.order_by(Event.start).all()

    engine = InsightEngine()
    counts = {eid: len(s) for eid, s in engine.regs.items()}
    mine = set()
    if g.user:
        mine = {r.event_id for r in Registration.query.filter_by(user_id=g.user.id)}
    out = []
    for e in events:
        flags = engine.feed_flags(e) if e.end >= datetime.now() else None
        out.append(event_to_dict(e, counts.get(e.id, 0), flags, (e.id in mine) if g.user else None))
    return jsonify(events=out, categories=list(EVENT_CATEGORIES))


@bp.get("/events/<int:event_id>")
@optional_auth
def event_detail(event_id):
    e = db.session.get(Event, event_id)
    if not e:
        return bad("Event not found.", 404)
    if e.status != "published" and not (g.user and can_manage_event(g.user, e)):
        return bad("Event not found.", 404)
    engine = InsightEngine()
    a = engine.analyze(e)
    mine = bool(g.user and Registration.query.filter_by(event_id=e.id, user_id=g.user.id).first())

    # names of overlapping students are only shown to people who manage the event
    overlap = a["overlap"]
    can_see_names = bool(g.user and can_manage_event(g.user, e))
    from ..models import User
    for row in overlap["by_event"]:
        if can_see_names and row["student_ids"]:
            users = User.query.filter(User.id.in_(row["student_ids"])).all()
            row["students"] = [{"id": u.id, "name": u.name} for u in users]
        row.pop("student_ids", None)
    overlap.pop("affected_students", None)

    d = event_to_dict(e, a["registered"], None, mine if g.user else None)
    attendance = None
    if e.end < datetime.now():
        regs = Registration.query.filter_by(event_id=e.id).all()
        marked = [r for r in regs if r.attended is not None]
        attendance = {"recorded": len(marked), "present": sum(1 for r in marked if r.attended),
                      "rate": round(sum(1 for r in marked if r.attended) / len(marked), 3) if marked else None}
    d.update(insights={"conflicts": a["conflicts"], "overlap": overlap, "prediction": a["prediction"]},
             attendance=attendance, can_manage=bool(g.user and can_manage_event(g.user, e)))
    return jsonify(event=d)


@bp.get("/events/<int:event_id>/optimize")
@login_required("coordinator", "admin")
def optimize(event_id):
    e = db.session.get(Event, event_id)
    if not e or not can_manage_event(g.user, e):
        return bad("Event not found.", 404)
    result = InsightEngine().optimize(e)
    venues = {v.id: v.name for v in Venue.query.all()}
    for key in ("recommendations",):
        for r in result[key]:
            r["start"], r["end"] = r["start"].isoformat(), r["end"].isoformat()
    cur = result["current"]
    cur["start"], cur["end"] = cur["start"].isoformat(), cur["end"].isoformat()
    cur["venue_name"] = venues.get(cur["venue_id"])
    return jsonify(result)


@bp.post("/events/<int:event_id>/register")
@login_required()
def register_for_event(event_id):
    e = db.session.get(Event, event_id)
    if not e or e.status != "published":
        return bad("Event not found.", 404)
    if e.end < datetime.now():
        return bad("This event has already finished.")
    if Registration.query.filter_by(event_id=e.id, user_id=g.user.id).first():
        return bad("You are already registered.", 409)
    if Registration.query.filter_by(event_id=e.id).count() >= e.cap:
        return bad("Sorry, this event is full.", 409)
    db.session.add(Registration(event_id=e.id, user_id=g.user.id))
    # warn the student if they are already signed up for something at the same time
    clash = (db.session.query(Event).join(Registration, Registration.event_id == Event.id)
             .filter(Registration.user_id == g.user.id, Event.id != e.id, Event.status == "published",
                     Event.start < e.end, Event.end > e.start).first())
    warning = None
    if clash:
        warning = f"Heads up: this overlaps with \"{clash.title}\", which you also registered for."
        db.session.add(Notification(user_id=g.user.id, kind="conflict", event_id=e.id, message=warning))
    db.session.add(Notification(user_id=g.user.id, kind="event", event_id=e.id,
                                message=f"You're registered for \"{e.title}\"."))
    db.session.commit()
    return jsonify(message="You're in!", warning=warning), 201


@bp.delete("/events/<int:event_id>/register")
@login_required()
def unregister(event_id):
    reg = Registration.query.filter_by(event_id=event_id, user_id=g.user.id).first()
    if not reg:
        return bad("You are not registered for this event.", 404)
    db.session.delete(reg)
    db.session.commit()
    return jsonify(message="Registration cancelled.")


# ---------- event management (coordinator / admin) ----------

def _read_event_payload(data, existing=None):
    """Validate and return a dict of event fields, or raise ValueError."""
    title = clean(data.get("title"), 160)
    if len(title) < 3:
        raise ValueError("Title must be at least 3 characters.")
    category = data.get("category") or "Tech"
    if category not in EVENT_CATEGORIES:
        raise ValueError("Unknown category.")
    start, end = parse_dt(data.get("start"), "Start"), parse_dt(data.get("end"), "End")
    if end <= start:
        raise ValueError("End time must be after the start time.")
    if start.date() != end.date():
        raise ValueError("Events must start and end on the same day.")
    club = db.session.get(Club, int(data.get("club_id") or 0))
    venue = db.session.get(Venue, int(data.get("venue_id") or 0))
    if not club:
        raise ValueError("Please choose a club.")
    if not venue:
        raise ValueError("Please choose a venue.")
    cap = data.get("capacity")
    cap = int(cap) if cap not in (None, "") else None
    if cap is not None and cap < 1:
        raise ValueError("Capacity must be at least 1.")
    return dict(title=title, description=clean(data.get("description"), 4000), category=category,
                start=start, end=end, club_id=club.id, venue_id=venue.id, capacity=cap), club


def _club_allowed(user, club):
    return user.role == "admin" or club.coordinator_id == user.id


@bp.post("/events")
@login_required("coordinator", "admin")
def create_event():
    try:
        fields, club = _read_event_payload(request.get_json(silent=True) or {})
    except (ValueError, TypeError) as err:
        return bad(str(err))
    if not _club_allowed(g.user, club):
        return bad("You can only create events for clubs you coordinate.", 403)
    e = Event(**fields, status="draft", created_by=g.user.id)
    db.session.add(e)
    db.session.commit()
    return jsonify(event=event_to_dict(e), message="Draft saved."), 201


@bp.put("/events/<int:event_id>")
@login_required("coordinator", "admin")
def update_event(event_id):
    e = db.session.get(Event, event_id)
    if not e or not can_manage_event(g.user, e):
        return bad("Event not found.", 404)
    if e.status == "cancelled":
        return bad("Cancelled events cannot be edited.")
    try:
        fields, club = _read_event_payload(request.get_json(silent=True) or {})
    except (ValueError, TypeError) as err:
        return bad(str(err))
    if not _club_allowed(g.user, club):
        return bad("You can only use clubs you coordinate.", 403)
    for k, v in fields.items():
        setattr(e, k, v)
    db.session.commit()
    return jsonify(event=event_to_dict(e), message="Event updated.")


@bp.post("/events/<int:event_id>/publish")
@login_required("coordinator", "admin")
def publish(event_id):
    e = db.session.get(Event, event_id)
    if not e or not can_manage_event(g.user, e):
        return bad("Event not found.", 404)
    if e.status == "cancelled":
        return bad("Cancelled events cannot be published.")
    conflicts = InsightEngine().check_slot(e.start, e.end, e.venue_id, e.id)
    blocking = [c for c in conflicts if c["severity"] == "high"]
    force = bool((request.get_json(silent=True) or {}).get("force"))
    if blocking:  # venue clashes can never be published, even with force
        return jsonify(error="Cannot publish: " + blocking[0]["message"], conflicts=conflicts), 409
    if conflicts and not force:
        return jsonify(error="This event overlaps other events. Review the warnings or publish anyway.",
                       conflicts=conflicts, needs_confirmation=True), 409
    e.status = "published"
    db.session.commit()
    return jsonify(event=event_to_dict(e), message="Event published.", conflicts=conflicts)


@bp.post("/events/<int:event_id>/cancel")
@login_required("coordinator", "admin")
def cancel(event_id):
    e = db.session.get(Event, event_id)
    if not e or not can_manage_event(g.user, e):
        return bad("Event not found.", 404)
    if e.status == "cancelled":
        return bad("Already cancelled.")
    e.status = "cancelled"
    for reg in e.registrations:
        db.session.add(Notification(user_id=reg.user_id, kind="event", event_id=e.id,
                                    message=f"\"{e.title}\" has been cancelled."))
    db.session.commit()
    return jsonify(event=event_to_dict(e), message="Event cancelled and registrants notified.")


@bp.delete("/events/<int:event_id>")
@login_required("coordinator", "admin")
def delete_event(event_id):
    e = db.session.get(Event, event_id)
    if not e or not can_manage_event(g.user, e):
        return bad("Event not found.", 404)
    if e.status == "published" and e.registrations:
        return bad("Cancel the event instead - students are registered.")
    db.session.delete(e)
    db.session.commit()
    return jsonify(message="Event deleted.")


@bp.get("/events/<int:event_id>/registrations")
@login_required("coordinator", "admin")
def registrations(event_id):
    e = db.session.get(Event, event_id)
    if not e or not can_manage_event(g.user, e):
        return bad("Event not found.", 404)
    rows = Registration.query.filter_by(event_id=e.id).order_by(Registration.created_at).all()
    present = sum(1 for r in rows if r.attended)
    marked = sum(1 for r in rows if r.attended is not None)
    return jsonify(
        event=event_to_dict(e, len(rows)),
        registrations=[{"user_id": r.user_id, "name": r.user.name, "email": r.user.email,
                        "registered_at": r.created_at.isoformat(), "attended": r.attended} for r in rows],
        summary={"registered": len(rows), "marked": marked, "present": present,
                 "attendance_rate": round(present / marked, 3) if marked else None})


@bp.put("/events/<int:event_id>/attendance")
@login_required("coordinator", "admin")
def mark_attendance(event_id):
    """Body: {"records": [{"user_id": 3, "attended": true}, ...]}"""
    e = db.session.get(Event, event_id)
    if not e or not can_manage_event(g.user, e):
        return bad("Event not found.", 404)
    if e.status != "published":
        return bad("Attendance can only be recorded for published events.")
    if e.start > datetime.now():
        return bad("Attendance can be recorded once the event has started.")
    records = (request.get_json(silent=True) or {}).get("records")
    if not isinstance(records, list):
        return bad("records must be a list.")
    by_user = {r.user_id: r for r in e.registrations}
    changed = 0
    for rec in records:
        reg = by_user.get(rec.get("user_id"))
        if reg is None or not isinstance(rec.get("attended"), bool):
            continue
        reg.attended, reg.marked_at = rec["attended"], utcnow()
        changed += 1
    db.session.commit()
    return jsonify(message=f"Attendance saved for {changed} student(s).", updated=changed)
