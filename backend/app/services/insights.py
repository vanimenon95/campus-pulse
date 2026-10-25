"""Glue between the database and the pure-Python AI modules in ``app.ai``."""
from collections import defaultdict
from datetime import datetime

from ..ai import analyze_overlap, detect_conflicts, optimize_schedule, overlaps, predict_attendance
from ..ai.conflict_detector import has_blocking_conflict
from ..extensions import db
from ..models import Event, Registration, Venue, VenueBlackout


def venue_dict(v):
    return {"id": v.id, "name": v.name, "capacity": v.capacity,
            "open_time": v.open_time, "close_time": v.close_time}


def event_dict(e):
    return {"id": e.id, "title": e.title, "venue_id": e.venue_id, "club_id": e.club_id,
            "category": e.category, "start": e.start, "end": e.end}


class InsightEngine:
    """Loads everything the AI needs once per request, then answers questions."""

    def __init__(self, now=None):
        self.now = now or datetime.now()
        self.venues = {v.id: v for v in Venue.query.all()}
        self.blackouts = [{"venue_id": b.venue_id, "start": b.start, "end": b.end, "reason": b.reason}
                          for b in VenueBlackout.query.all()]
        self.published = Event.query.filter_by(status="published").all()
        self.events = {e.id: e for e in self.published}
        self.regs = defaultdict(set)
        ids = [e.id for e in self.published]
        if ids:
            for r in Registration.query.filter(Registration.event_id.in_(ids)).all():
                self.regs[r.event_id].add(r.user_id)
        self._history = None

    # ---- helpers -------------------------------------------------------
    def _others(self, event_id=None):
        return [event_dict(e) for e in self.published if e.id != event_id]

    def history(self):
        """Past published events that have attendance recorded."""
        if self._history is None:
            rows = []
            past = [e for e in self.published if e.end < self.now]
            for e in past:
                regs = Registration.query.filter_by(event_id=e.id).all()
                recorded = [r for r in regs if r.attended is not None]
                if not regs or not recorded:
                    continue
                rows.append({"event_id": e.id, "club_id": e.club_id, "category": e.category,
                             "registered": len(regs), "attended": sum(1 for r in regs if r.attended),
                             "start_hour": e.start.hour})
            self._history = rows
        return self._history

    # ---- per-event analysis -------------------------------------------
    def analyze(self, e):
        """Run conflict detector, overlap analyzer and attendance predictor for one event."""
        target = event_dict(e)
        venue = venue_dict(e.venue)
        regs = dict(self.regs)
        if e.id not in regs:  # draft/cancelled events are not in the cache
            regs[e.id] = {r.user_id for r in Registration.query.filter_by(event_id=e.id)}
        registered = len(regs[e.id])
        conflicts = detect_conflicts(target, self._others(e.id), venue, self.blackouts, expected_attendees=registered)
        clash_ids = [c["other_event_id"] for c in conflicts if c["other_event_id"]]
        titles = {c["other_event_id"]: c["other_event_title"] for c in conflicts if c["other_event_id"]}
        overlap = analyze_overlap(e.id, regs, clash_ids, titles)
        hard = sum(1 for c in conflicts if c["severity"] == "high")
        prediction = predict_attendance(registered, e.cap, self.history(), e.club_id, e.category,
                                        overlap["affected_count"], hard)
        return {"conflicts": conflicts, "overlap": overlap, "prediction": prediction,
                "registered": registered}

    def optimize(self, e):
        a = self.analyze(e)
        regs = dict(self.regs)
        regs[e.id] = {r.user_id for r in Registration.query.filter_by(event_id=e.id)}
        result = optimize_schedule(
            event_dict(e), self._others(e.id), regs, [venue_dict(v) for v in self.venues.values()],
            self.blackouts, self.history(), show_rate=a["prediction"]["base_show_rate"], now=self.now)
        return result

    def check_slot(self, start, end, venue_id, exclude_event_id=None, club_id=None, category=None, expected=None):
        """Dry-run conflict check for a slot that is not saved yet (used by the event form)."""
        venue = self.venues.get(venue_id)
        if not venue:
            return []
        target = {"id": exclude_event_id, "title": "(this event)", "venue_id": venue_id,
                  "start": start, "end": end}
        return detect_conflicts(target, self._others(exclude_event_id), venue_dict(venue),
                                self.blackouts, expected_attendees=expected)

    def feed_flags(self, e):
        """Cheap conflict summary for the feed card (no prediction needed)."""
        target = event_dict(e)
        conflicts = detect_conflicts(target, self._others(e.id), venue_dict(e.venue), self.blackouts)
        clash_ids = [c["other_event_id"] for c in conflicts if c["other_event_id"]]
        titles = {c["other_event_id"]: c["other_event_title"] for c in conflicts if c["other_event_id"]}
        ov = analyze_overlap(e.id, dict(self.regs), clash_ids, titles)
        return {"conflict_count": len(conflicts), "affected_students": ov["affected_count"],
                "venue_conflict": any(c["type"] in ("venue_double_booking", "venue_blackout") for c in conflicts),
                "top_clash": ov["by_event"][0]["title"] if ov["by_event"] and ov["affected_count"] else None}


def venue_availability(venue, day_start, day_end):
    """Bookings and blackouts for one venue inside a window (used by the venue page)."""
    events = Event.query.filter(Event.venue_id == venue.id, Event.status != "cancelled",
                                Event.start < day_end, Event.end > day_start).order_by(Event.start).all()
    blocks = [b for b in venue.blackouts if overlaps(b.start, b.end, day_start, day_end)]
    return events, blocks
