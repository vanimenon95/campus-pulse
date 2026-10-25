from datetime import datetime, time, timedelta

from flask import Blueprint, g, jsonify, request

from ..auth import login_required
from ..extensions import db
from ..models import Venue, VenueBlackout
from ..services.insights import InsightEngine, venue_availability
from .helpers import bad, clean, parse_dt

bp = Blueprint("venues", __name__)


def _parse_time(v, field):
    try:
        h, m = str(v).split(":")[:2]
        return time(int(h), int(m))
    except Exception:
        raise ValueError(f"{field} must look like 09:00.")


def _read(data):
    name = clean(data.get("name"), 120)
    if len(name) < 2:
        raise ValueError("Venue name is required.")
    try:
        cap = int(data.get("capacity"))
    except (TypeError, ValueError):
        raise ValueError("Capacity must be a number.")
    if cap < 1:
        raise ValueError("Capacity must be at least 1.")
    o, c = _parse_time(data.get("open_time", "08:00"), "Opening time"), _parse_time(data.get("close_time", "21:00"), "Closing time")
    if c <= o:
        raise ValueError("Closing time must be after opening time.")
    fac = data.get("facilities") or []
    if isinstance(fac, list):
        fac = ",".join(clean(f, 40) for f in fac if clean(f))
    return dict(name=name, location=clean(data.get("location"), 160), capacity=cap,
                facilities=clean(fac, 255), open_time=o, close_time=c)


@bp.get("/venues")
def list_venues():
    return jsonify(venues=[v.to_dict() for v in Venue.query.order_by(Venue.name)])


@bp.get("/venues/<int:venue_id>/availability")
def availability(venue_id):
    """Bookings + blackouts for a day (?date=YYYY-MM-DD, default today)."""
    v = db.session.get(Venue, venue_id)
    if not v:
        return bad("Venue not found.", 404)
    try:
        day = datetime.fromisoformat(request.args.get("date") or datetime.now().date().isoformat())
    except ValueError:
        return bad("date must be YYYY-MM-DD.")
    start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    events, blocks = venue_availability(v, start, start + timedelta(days=1))
    return jsonify(venue=v.to_dict(), date=start.date().isoformat(),
                   bookings=[{"id": e.id, "title": e.title, "start": e.start.isoformat(), "end": e.end.isoformat(),
                              "status": e.status, "club_name": e.club.name} for e in events],
                   blackouts=[b.to_dict() for b in blocks])


@bp.post("/venues/check")
@login_required("coordinator", "admin")
def check_slot():
    """Dry-run booking check used by the event form: {venue_id, start, end, event_id?, expected?}"""
    d = request.get_json(silent=True) or {}
    try:
        start, end = parse_dt(d.get("start"), "Start"), parse_dt(d.get("end"), "End")
        vid = int(d.get("venue_id"))
    except (ValueError, TypeError) as err:
        return bad(str(err))
    if end <= start:
        return bad("End time must be after the start time.")
    conflicts = InsightEngine().check_slot(start, end, vid, d.get("event_id"), expected=d.get("expected"))
    return jsonify(conflicts=conflicts, ok=not any(c["severity"] == "high" for c in conflicts))


@bp.post("/venues")
@login_required("admin")
def create_venue():
    try:
        fields = _read(request.get_json(silent=True) or {})
    except ValueError as err:
        return bad(str(err))
    if Venue.query.filter(db.func.lower(Venue.name) == fields["name"].lower()).first():
        return bad("A venue with that name already exists.", 409)
    v = Venue(**fields)
    db.session.add(v)
    db.session.commit()
    return jsonify(venue=v.to_dict(), message="Venue created."), 201


@bp.put("/venues/<int:venue_id>")
@login_required("admin")
def update_venue(venue_id):
    v = db.session.get(Venue, venue_id)
    if not v:
        return bad("Venue not found.", 404)
    try:
        fields = _read(request.get_json(silent=True) or {})
    except ValueError as err:
        return bad(str(err))
    for k, val in fields.items():
        setattr(v, k, val)
    db.session.commit()
    return jsonify(venue=v.to_dict(), message="Venue updated.")


@bp.delete("/venues/<int:venue_id>")
@login_required("admin")
def delete_venue(venue_id):
    v = db.session.get(Venue, venue_id)
    if not v:
        return bad("Venue not found.", 404)
    from ..models import Event
    if Event.query.filter_by(venue_id=v.id).first():
        return bad("This venue still has events booked. Move or delete them first.", 409)
    db.session.delete(v)
    db.session.commit()
    return jsonify(message="Venue deleted.")


@bp.post("/venues/<int:venue_id>/blackouts")
@login_required("admin")
def add_blackout(venue_id):
    v = db.session.get(Venue, venue_id)
    if not v:
        return bad("Venue not found.", 404)
    d = request.get_json(silent=True) or {}
    try:
        start, end = parse_dt(d.get("start"), "Start"), parse_dt(d.get("end"), "End")
    except ValueError as err:
        return bad(str(err))
    if end <= start:
        return bad("End must be after start.")
    b = VenueBlackout(venue_id=v.id, start=start, end=end, reason=clean(d.get("reason"), 160) or "Unavailable")
    db.session.add(b)
    db.session.commit()
    return jsonify(blackout=b.to_dict(), message="Venue blocked for that period."), 201


@bp.delete("/venues/<int:venue_id>/blackouts/<int:blackout_id>")
@login_required("admin")
def delete_blackout(venue_id, blackout_id):
    b = db.session.get(VenueBlackout, blackout_id)
    if not b or b.venue_id != venue_id:
        return bad("Blackout not found.", 404)
    db.session.delete(b)
    db.session.commit()
    return jsonify(message="Blackout removed.")
