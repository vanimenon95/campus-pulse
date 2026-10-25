from datetime import datetime

from flask import Blueprint, g, jsonify

from ..auth import login_required
from ..extensions import db
from ..models import Club, Event, Membership, Notification, Registration
from ..serializers import club_to_dict, event_to_dict
from ..services.insights import InsightEngine
from .helpers import bad

bp = Blueprint("me", __name__)


@bp.get("/me/dashboard")
@login_required()
def dashboard():
    """Student dashboard: joined clubs, registered events (with AI clash flags), notifications."""
    uid = g.user.id
    clubs = [m.club for m in Membership.query.filter_by(user_id=uid)]
    regs = (Registration.query.filter_by(user_id=uid).join(Event)
            .filter(Event.status != "cancelled").order_by(Event.start).all())
    engine = InsightEngine()
    now = datetime.now()
    upcoming, past = [], []
    for r in regs:
        e = r.event
        d = event_to_dict(e, len(engine.regs.get(e.id, ())), None, True)
        d["attended"] = r.attended
        if e.end >= now:
            d["flags"] = engine.feed_flags(e)
            upcoming.append(d)
        else:
            past.append(d)
    # personal clashes: two of MY events overlapping
    my_clashes = []
    for i, a in enumerate(upcoming):
        for b in upcoming[i + 1:]:
            if a["start"] < b["end"] and b["start"] < a["end"]:
                my_clashes.append({"a": a["title"], "b": b["title"], "a_id": a["id"], "b_id": b["id"]})
    notes = Notification.query.filter_by(user_id=uid).order_by(Notification.created_at.desc()).limit(30).all()
    suggestions = (Event.query.filter(Event.status == "published", Event.end >= now,
                                      Event.club_id.in_([c.id for c in clubs] or [0]))
                   .order_by(Event.start).limit(6).all())
    mine = {r.event_id for r in regs}
    return jsonify(
        clubs=[club_to_dict(c, joined=True) for c in clubs],
        upcoming=upcoming, past=past[-10:], my_clashes=my_clashes,
        notifications=[n.to_dict() for n in notes], unread=sum(1 for n in notes if not n.is_read),
        from_my_clubs=[event_to_dict(e, len(engine.regs.get(e.id, ())), None, e.id in mine)
                       for e in suggestions if e.id not in mine])


@bp.post("/me/notifications/read")
@login_required()
def read_all():
    Notification.query.filter_by(user_id=g.user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify(message="All caught up.")


@bp.post("/me/notifications/<int:nid>/read")
@login_required()
def read_one(nid):
    n = db.session.get(Notification, nid)
    if not n or n.user_id != g.user.id:
        return bad("Notification not found.", 404)
    n.is_read = True
    db.session.commit()
    return jsonify(message="Marked as read.")


@bp.get("/coordinator/dashboard")
@login_required("coordinator", "admin")
def coordinator_dashboard():
    """Events of the clubs this person coordinates (all clubs for admins), with AI insight + optimizer hints."""
    clubs = Club.query.filter_by(is_active=True)
    if g.user.role != "admin":
        clubs = clubs.filter_by(coordinator_id=g.user.id)
    clubs = clubs.all()
    ids = [c.id for c in clubs] or [0]
    events = Event.query.filter(Event.club_id.in_(ids), Event.status != "cancelled").order_by(Event.start).all()
    engine = InsightEngine()
    now = datetime.now()
    rows, recs = [], []
    for e in events:
        a = engine.analyze(e)
        d = event_to_dict(e, a["registered"])
        upcoming_ev = e.end >= now
        d["conflict_count"] = len(a["conflicts"]) if upcoming_ev else 0
        d["affected_students"] = a["overlap"]["affected_count"] if upcoming_ev else 0
        d["predicted_attendance"] = a["prediction"]["predicted_attendees"]
        d["predicted_rate"] = a["prediction"]["predicted_rate"]
        d["prediction_method"] = a["prediction"]["method"]
        rows.append(d)
        if e.end >= now and e.status == "published" and a["conflicts"]:
            opt = engine.optimize(e)
            if opt["recommendations"]:
                best = opt["recommendations"][0]
                recs.append({"event_id": e.id, "title": e.title, "current_affected": opt["current"]["affected_students"],
                             "best_start": best["start"].isoformat(), "best_end": best["end"].isoformat(),
                             "best_venue": best["venue_name"], "improvement": best["improvement"],
                             "students_saved": best["students_saved"]})
    return jsonify(
        clubs=[club_to_dict(c) for c in clubs], events=rows, recommendations=recs,
        totals={"events": len(rows), "published": sum(1 for r in rows if r["status"] == "published"),
                "drafts": sum(1 for r in rows if r["status"] == "draft"),
                "registrations": sum(r["registered"] for r in rows),
                "with_conflicts": sum(1 for r in rows if r["conflict_count"])})
