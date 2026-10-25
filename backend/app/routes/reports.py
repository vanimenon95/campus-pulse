from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify

from ..auth import login_required, optional_auth
from ..extensions import db
from ..models import Club, Event, Membership, Registration, Venue
from ..services.insights import InsightEngine

bp = Blueprint("reports", __name__)


@bp.get("/stats")
def public_stats():
    """Numbers for the home page. 'conflict_free' is computed by the Overlap Analyzer, not hardcoded."""
    now = datetime.now()
    engine = InsightEngine()
    upcoming = [e for e in engine.published if e.end >= now]
    flagged = sum(1 for e in upcoming if engine.feed_flags(e)["affected_students"] > 0
                  or engine.feed_flags(e)["venue_conflict"])
    term_start = now - timedelta(days=90)
    return jsonify(
        active_clubs=Club.query.filter_by(is_active=True).count(),
        events_this_term=Event.query.filter(Event.status == "published", Event.start >= term_start).count(),
        upcoming_events=len(upcoming),
        conflict_free_pct=round(100 * (1 - flagged / len(upcoming))) if upcoming else 100)


def _scope_clubs(user):
    q = Club.query
    if user.role != "admin":
        q = q.filter_by(coordinator_id=user.id)
    return [c.id for c in q.all()]


@bp.get("/reports/participation")
@login_required("coordinator", "admin")
def participation():
    ids = _scope_clubs(g.user)
    events = Event.query.filter(Event.club_id.in_(ids or [0]), Event.status == "published").order_by(Event.start).all()
    rows = []
    for e in events:
        regs = Registration.query.filter_by(event_id=e.id).all()
        marked = [r for r in regs if r.attended is not None]
        present = sum(1 for r in marked if r.attended)
        rows.append({"event_id": e.id, "title": e.title, "club_name": e.club.name, "start": e.start.isoformat(),
                     "registered": len(regs), "capacity": e.cap, "fill_rate": round(len(regs) / e.cap, 3) if e.cap else 0,
                     "recorded": len(marked), "present": present,
                     "attendance_rate": round(present / len(marked), 3) if marked else None})
    done = [r for r in rows if r["attendance_rate"] is not None]
    return jsonify(events=rows, summary={
        "events": len(rows), "registrations": sum(r["registered"] for r in rows),
        "avg_attendance_rate": round(sum(r["present"] for r in done) / max(1, sum(r["recorded"] for r in done)), 3) if done else None})


@bp.get("/reports/clubs")
@login_required("coordinator", "admin")
def clubs_report():
    out = []
    for c in Club.query.filter(Club.id.in_(_scope_clubs(g.user) or [0])).all():
        evs = Event.query.filter_by(club_id=c.id, status="published").all()
        regs = Registration.query.filter(Registration.event_id.in_([e.id for e in evs] or [0])).all()
        marked = [r for r in regs if r.attended is not None]
        out.append({"club_id": c.id, "name": c.name, "category": c.category,
                    "members": Membership.query.filter_by(club_id=c.id).count(),
                    "events": len(evs), "registrations": len(regs),
                    "attendance_rate": round(sum(1 for r in marked if r.attended) / len(marked), 3) if marked else None})
    out.sort(key=lambda r: -r["registrations"])
    return jsonify(clubs=out)


@bp.get("/reports/venues")
@login_required("coordinator", "admin")
def venues_report():
    """Utilisation = booked hours / open hours over the last and next 30 days (published events)."""
    now = datetime.now()
    win_start, win_end = now - timedelta(days=30), now + timedelta(days=30)
    out = []
    for v in Venue.query.order_by(Venue.name):
        evs = Event.query.filter(Event.venue_id == v.id, Event.status == "published",
                                 Event.start >= win_start, Event.start < win_end).all()
        booked = sum((e.end - e.start).total_seconds() for e in evs) / 3600
        open_hours = ((v.close_time.hour * 60 + v.close_time.minute) - (v.open_time.hour * 60 + v.open_time.minute)) / 60
        available = open_hours * 60
        regs = sum(Registration.query.filter_by(event_id=e.id).count() for e in evs)
        out.append({"venue_id": v.id, "name": v.name, "capacity": v.capacity, "events": len(evs),
                    "booked_hours": round(booked, 1), "utilization": round(min(1.0, booked / available), 3) if available else 0,
                    "avg_fill": round(regs / (len(evs) * v.capacity), 3) if evs else 0})
    return jsonify(venues=out, window_days=60)


@bp.get("/reports/timeline")
@login_required("coordinator", "admin")
def timeline():
    """Registrations per week for the last 8 weeks and next 4 weeks."""
    ids = _scope_clubs(g.user)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    monday = today - timedelta(days=today.weekday())
    buckets = defaultdict(lambda: {"events": 0, "registrations": 0})
    for e in Event.query.filter(Event.club_id.in_(ids or [0]), Event.status == "published").all():
        wk = (e.start.replace(hour=0, minute=0) - timedelta(days=e.start.weekday())).date()
        buckets[wk]["events"] += 1
        buckets[wk]["registrations"] += Registration.query.filter_by(event_id=e.id).count()
    weeks = [(monday + timedelta(weeks=i)).date() for i in range(-8, 5)]
    return jsonify(weeks=[{"week": w.isoformat(), **buckets[w]} for w in weeks])
