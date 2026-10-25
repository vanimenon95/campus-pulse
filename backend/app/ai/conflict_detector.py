"""AI component 1 - Conflict Detector.

Finds every problem a proposed event slot would cause:

* ``venue_double_booking``  - another active event uses the same venue at the same time (high)
* ``venue_blackout``        - the venue is blocked (maintenance, exam...) during the slot (high)
* ``outside_venue_hours``   - the slot is outside the venue's opening hours (high)
* ``capacity_exceeded``     - expected attendees do not fit in the venue (medium)
* ``time_overlap``          - another event elsewhere on campus runs at the same time (medium)

Events are plain dicts: ``{id, title, venue_id, start, end, club_id}`` where
``start``/``end`` are ``datetime`` objects.
"""
from datetime import datetime, time


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Two time ranges overlap when each starts before the other ends.
    Back-to-back events (one ends exactly when the next starts) do NOT overlap."""
    return a_start < b_end and b_start < a_end


def overlap_minutes(a_start, a_end, b_start, b_end) -> int:
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    return max(0, int((earliest_end - latest_start).total_seconds() // 60))


def _hours_ok(venue, start: datetime, end: datetime) -> bool:
    open_t = venue.get("open_time") or time(0, 0)
    close_t = venue.get("close_time") or time(23, 59)
    if start.date() != end.date():
        return False
    return open_t <= start.time() and end.time() <= close_t


def detect_conflicts(target, others, venue=None, blackouts=(), expected_attendees=None):
    """Return a list of conflict dicts for ``target`` against ``others``.

    ``others`` should only contain *active* (published) events; the target
    itself is skipped by id.  ``blackouts`` is a list of
    ``{venue_id, start, end, reason}``.
    """
    found = []
    for other in others:
        if other["id"] == target.get("id"):
            continue
        if not overlaps(target["start"], target["end"], other["start"], other["end"]):
            continue
        mins = overlap_minutes(target["start"], target["end"], other["start"], other["end"])
        if other["venue_id"] == target["venue_id"]:
            found.append({
                "type": "venue_double_booking", "severity": "high",
                "other_event_id": other["id"], "other_event_title": other["title"],
                "overlap_minutes": mins,
                "message": f"Venue already booked for \"{other['title']}\" ({mins} min overlap).",
            })
        else:
            found.append({
                "type": "time_overlap", "severity": "medium",
                "other_event_id": other["id"], "other_event_title": other["title"],
                "overlap_minutes": mins,
                "message": f"Runs at the same time as \"{other['title']}\" ({mins} min overlap).",
            })

    for block in blackouts:
        if block["venue_id"] == target["venue_id"] and overlaps(
                target["start"], target["end"], block["start"], block["end"]):
            found.append({
                "type": "venue_blackout", "severity": "high", "other_event_id": None,
                "overlap_minutes": overlap_minutes(target["start"], target["end"], block["start"], block["end"]),
                "message": f"Venue unavailable: {block.get('reason') or 'blocked'}.",
            })

    if venue:
        if not _hours_ok(venue, target["start"], target["end"]):
            found.append({
                "type": "outside_venue_hours", "severity": "high", "other_event_id": None,
                "overlap_minutes": 0,
                "message": f"Outside venue hours ({venue['open_time']:%H:%M}-{venue['close_time']:%H:%M}).",
            })
        if expected_attendees is not None and expected_attendees > venue["capacity"]:
            found.append({
                "type": "capacity_exceeded", "severity": "medium", "other_event_id": None,
                "overlap_minutes": 0,
                "message": f"Expected {expected_attendees} attendees but venue holds {venue['capacity']}.",
            })
    return found


def has_blocking_conflict(conflicts) -> bool:
    """High severity conflicts make a slot unusable."""
    return any(c["severity"] == "high" for c in conflicts)
