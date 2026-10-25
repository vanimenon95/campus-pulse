"""AI component 4 - Schedule Optimizer.

Searches nearby days and half-hour start times (same venue first, then other
venues that are big enough) and ranks the slots that

* have no *blocking* conflicts (venue double-booking, blackout, closed hours),
* respect capacity,
* minimise student overlap, and
* maximise **expected participation**::

      expected = show_rate * time_factor * (registered - CLASH_LOSS * affected)

``time_factor`` is learned from past events (turnout per start hour) when at
least ``MIN_HOUR_SAMPLES`` events exist for that hour, otherwise it comes from
a documented default curve - the response says which one was used.
"""
from datetime import datetime, timedelta

from .conflict_detector import detect_conflicts, has_blocking_conflict, overlaps
from .overlap_analyzer import analyze_overlap
from .attendance_predictor import CLASH_LOSS, DEFAULT_SHOW_RATE

MIN_HOUR_SAMPLES = 2
DAY_START_HOUR, DAY_END_HOUR = 8, 21
# Fallback curve: people are in class mid-morning/afternoon, free late afternoon/evening.
DEFAULT_HOUR_FACTOR = {8: .70, 9: .80, 10: .85, 11: .85, 12: .90, 13: .90, 14: .85,
                       15: .90, 16: 1.0, 17: 1.0, 18: 1.0, 19: .95, 20: .85}
WEEKDAY_FACTOR = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: .95, 5: .95, 6: .85}  # Mon..Sun


def hour_factors(history):
    """Learn relative turnout by start hour. Returns (func(hour)->factor, source_label)."""
    by_hour = {}
    for h in history:
        if h.get("registered") and h.get("attended") is not None and h.get("start_hour") is not None:
            by_hour.setdefault(h["start_hour"], []).append(h["attended"] / h["registered"])
    overall = [r for rows in by_hour.values() for r in rows]
    learned = {}
    if overall:
        mean_all = sum(overall) / len(overall)
        for hr, rows in by_hour.items():
            if len(rows) >= MIN_HOUR_SAMPLES and mean_all > 0:
                learned[hr] = max(0.5, min(1.2, (sum(rows) / len(rows)) / mean_all))
    source = "learned from past turnout" if learned else "default time-of-day curve (fallback)"

    def factor(hour, weekday):
        base = learned.get(hour, DEFAULT_HOUR_FACTOR.get(hour, 0.8))
        return base * WEEKDAY_FACTOR.get(weekday, 1.0)
    return factor, source


def _score(registered, affected, show_rate, tfactor):
    return max(0.0, show_rate * tfactor * (registered - CLASH_LOSS * affected))


def optimize_schedule(event, active_events, registrations, venues, blackouts=(),
                      history=(), show_rate=DEFAULT_SHOW_RATE, now=None,
                      search_days=3, step_minutes=30, max_results=3, allow_other_venues=True):
    """Recommend alternative slots for ``event``.

    ``event``: dict(id, title, venue_id, start, end).  ``active_events``: other
    published events (the target is filtered out).  ``registrations``:
    event_id -> set(student ids).  ``venues``: list of venue dicts with
    ``id, name, capacity, open_time, close_time``.
    """
    now = now or datetime.now()
    others = [e for e in active_events if e["id"] != event["id"]]
    titles = {e["id"]: e["title"] for e in others}
    mine = set(registrations.get(event["id"], ()))
    registered = len(mine)
    duration = event["end"] - event["start"]
    factor, source = hour_factors(list(history))
    venue_by_id = {v["id"]: v for v in venues}

    def evaluate(start, venue):
        cand = {"id": event["id"], "title": event["title"], "venue_id": venue["id"],
                "start": start, "end": start + duration}
        conflicts = detect_conflicts(cand, others, venue, blackouts, expected_attendees=registered)
        clash_ids = [o["id"] for o in others if overlaps(start, cand["end"], o["start"], o["end"])]
        ov = analyze_overlap(event["id"], registrations, clash_ids, titles)
        score = _score(registered, ov["affected_count"], show_rate, factor(start.hour, start.weekday()))
        return cand, conflicts, ov, score

    current_venue = venue_by_id.get(event["venue_id"])
    _, cur_conflicts, cur_ov, cur_score = evaluate(event["start"], current_venue) if current_venue \
        else (None, [], {"affected_count": 0}, 0)
    current = {"start": event["start"], "end": event["end"], "venue_id": event["venue_id"],
               "affected_students": cur_ov["affected_count"], "conflict_count": len(cur_conflicts),
               "expected_attendance": round(cur_score, 1)}

    candidates = []
    base_day = event["start"].replace(hour=0, minute=0, second=0, microsecond=0)
    venue_order = ([current_venue] if current_venue else []) + (
        [v for v in venues if v["id"] != event["venue_id"]] if allow_other_venues else [])
    for d in range(-search_days, search_days + 1):
        day = base_day + timedelta(days=d)
        minute = DAY_START_HOUR * 60
        while minute + duration.total_seconds() / 60 <= DAY_END_HOUR * 60:
            start = day + timedelta(minutes=minute)
            minute += step_minutes
            if start <= now:
                continue
            for venue in venue_order:
                if venue["capacity"] < registered:
                    continue
                if start == event["start"] and venue["id"] == event["venue_id"]:
                    continue
                cand, conflicts, ov, score = evaluate(start, venue)
                if has_blocking_conflict(conflicts):
                    continue
                shift_h = abs((start - event["start"]).total_seconds()) / 3600
                candidates.append({
                    "start": start, "end": cand["end"],
                    "venue_id": venue["id"], "venue_name": venue["name"],
                    "affected_students": ov["affected_count"],
                    "conflict_count": len(conflicts),
                    "expected_attendance": round(score, 1),
                    "improvement": round(score - cur_score, 1),
                    "students_saved": cur_ov["affected_count"] - ov["affected_count"],
                    "same_venue": venue["id"] == event["venue_id"],
                    "time_factor": round(factor(start.hour, start.weekday()), 2),
                    "_rank": (-score, len(conflicts), shift_h, 0 if venue["id"] == event["venue_id"] else 1),
                })

    candidates.sort(key=lambda c: c["_rank"])
    top, seen = [], set()
    for c in candidates:
        key = c["start"].date()  # offer variety: best slot per day
        if key in seen or c["improvement"] <= 0:
            continue
        seen.add(key)
        c.pop("_rank")
        top.append(c)
        if len(top) >= max_results:
            break
    return {
        "current": current, "recommendations": top, "time_model": source,
        "searched_candidates": len(candidates),
        "message": ("Current slot is already the best option found." if not top else
                    f"Found {len(top)} better slot(s)."),
    }
