"""AI component 2 - Student Overlap Analyzer.

Given who registered for which event, counts the students who would be torn
between events that run at the same time.
"""


def analyze_overlap(target_id, registrations, competing_event_ids, titles=None):
    """``registrations`` maps event_id -> set of student ids.

    Returns::

        {"affected_students": [ids], "affected_count": n, "affected_pct": 0-1,
         "by_event": [{"event_id", "title", "shared_count", "student_ids",
                       "pct_of_target", "pct_of_other"}]}

    ``affected_count`` is the number of *unique* students registered for the
    target and at least one competing event (a student in two competitors is
    counted once).
    """
    titles = titles or {}
    mine = set(registrations.get(target_id, ()))
    affected = set()
    by_event = []
    for eid in competing_event_ids:
        if eid == target_id:
            continue
        theirs = set(registrations.get(eid, ()))
        shared = mine & theirs
        affected |= shared
        by_event.append({
            "event_id": eid,
            "title": titles.get(eid, f"Event {eid}"),
            "shared_count": len(shared),
            "student_ids": sorted(shared),
            "pct_of_target": round(len(shared) / len(mine), 3) if mine else 0.0,
            "pct_of_other": round(len(shared) / len(theirs), 3) if theirs else 0.0,
        })
    by_event.sort(key=lambda r: -r["shared_count"])
    return {
        "affected_students": sorted(affected),
        "affected_count": len(affected),
        "affected_pct": round(len(affected) / len(mine), 3) if mine else 0.0,
        "by_event": by_event,
    }
