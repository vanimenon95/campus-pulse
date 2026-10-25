from datetime import datetime

from flask import Blueprint, g, jsonify, request

from ..ai import predict_attendance
from ..auth import login_required
from ..extensions import db
from ..models import Club, Event, Venue
from ..services.insights import InsightEngine
from .helpers import bad

bp = Blueprint("ai", __name__)


@bp.get("/ai/conflicts")
@login_required("coordinator", "admin")
def campus_conflicts():
    """Every upcoming published event that currently has a conflict (campus-wide for admins,
    own clubs for coordinators)."""
    engine = InsightEngine()
    own = {c.id for c in Club.query.filter_by(coordinator_id=g.user.id)}
    rows = []
    for e in engine.published:
        if e.end < datetime.now() or (g.user.role != "admin" and e.club_id not in own):
            continue
        a = engine.analyze(e)
        if a["conflicts"]:
            rows.append({"event_id": e.id, "title": e.title, "start": e.start.isoformat(),
                         "venue": e.venue.name, "conflicts": a["conflicts"],
                         "affected_students": a["overlap"]["affected_count"]})
    rows.sort(key=lambda r: (-r["affected_students"], r["start"]))
    return jsonify(conflicts=rows)


@bp.post("/ai/predict")
@login_required("coordinator", "admin")
def what_if_prediction():
    """What-if forecast for a draft: {club_id, venue_id, category?, registered}"""
    d = request.get_json(silent=True) or {}
    try:
        registered, venue_id = int(d.get("registered", 0)), int(d.get("venue_id"))
    except (TypeError, ValueError):
        return bad("registered and venue_id must be numbers.")
    venue = db.session.get(Venue, venue_id)
    if not venue:
        return bad("Venue not found.", 404)
    club = db.session.get(Club, int(d["club_id"])) if d.get("club_id") else None
    engine = InsightEngine()
    return jsonify(prediction=predict_attendance(registered, venue.capacity, engine.history(),
                                                 club.id if club else None, d.get("category")))
