"""AI component 3 - Attendance Predictor.

Method (transparent, no black box)
----------------------------------
1. Pick the best *history scope* that has at least ``MIN_HISTORY`` past events
   with recorded attendance: the same club, else the same category, else all
   campus events.
2. Show-rate = Bayesian-smoothed historical turnout:
   ``(sum attended + PRIOR_RATE*K) / (sum registered + K)``.
   The prior keeps a single odd event from swinging the estimate.
3. If no scope has enough history, **fallback**: use ``DEFAULT_SHOW_RATE`` and
   label the result ``method = "fallback_default"``.
4. Students signed up for a clashing event only attend ours about half the
   time, so we remove ``CLASH_LOSS * affected`` expected attendees.
"""
MIN_HISTORY = 3
PRIOR_RATE = 0.65
PRIOR_WEIGHT = 10        # "K": how many imaginary registrations the prior is worth
DEFAULT_SHOW_RATE = 0.65
CLASH_LOSS = 0.5


def _pick_history(history, club_id, category):
    usable = [h for h in history if h.get("registered", 0) > 0 and h.get("attended") is not None]
    tiers = (
        ("club", [h for h in usable if club_id is not None and h.get("club_id") == club_id]),
        ("category", [h for h in usable if category and h.get("category") == category]),
        ("campus", usable),
    )
    for scope, rows in tiers:
        if len(rows) >= MIN_HISTORY:
            return scope, rows
    return None, []


def _venue_fit(attendees, capacity):
    if capacity <= 0:
        return 0.0
    if attendees > capacity:
        return round(capacity / attendees, 3)
    util = attendees / capacity
    return round(0.4 + 0.6 * min(util / 0.7, 1.0), 3)


def predict_attendance(registered, capacity, history=(), club_id=None, category=None,
                       affected_students=0, hard_conflicts=0):
    scope, rows = _pick_history(list(history), club_id, category)
    if rows:
        att = sum(r["attended"] for r in rows)
        reg = sum(r["registered"] for r in rows)
        show_rate = (att + PRIOR_RATE * PRIOR_WEIGHT) / (reg + PRIOR_WEIGHT)
        method = "historical"
        confidence = "high" if len(rows) >= 8 else "medium"
        note = f"Based on {len(rows)} past {scope} events (smoothed show-rate {show_rate:.0%})."
    else:
        show_rate = DEFAULT_SHOW_RATE
        method = "fallback_default"
        confidence = "low"
        note = (f"Fallback estimate: fewer than {MIN_HISTORY} past events with attendance data, "
                f"so a default {DEFAULT_SHOW_RATE:.0%} show-rate is used.")

    expected = max(0.0, registered * show_rate - CLASH_LOSS * affected_students)
    expected = min(expected, registered)
    attendees = int(round(expected))
    predicted_rate = (expected / registered) if registered else show_rate

    conflict_free = 1.0 if registered == 0 else max(0.0, 1 - affected_students / registered)
    if hard_conflicts:
        conflict_free = min(conflict_free, 0.5)

    return {
        "method": method, "confidence": confidence, "history_scope": scope,
        "history_events": len(rows), "base_show_rate": round(show_rate, 3),
        "predicted_attendees": attendees,
        "predicted_rate": round(predicted_rate, 3),
        "venue_fit": _venue_fit(expected, capacity),
        "conflict_free": round(conflict_free, 3),
        "explanation": note,
    }
