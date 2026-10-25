"""Unit tests for the four AI components (no database needed)."""
from datetime import datetime, time, timedelta

from app.ai import analyze_overlap, detect_conflicts, optimize_schedule, overlaps, predict_attendance
from app.ai.attendance_predictor import DEFAULT_SHOW_RATE, MIN_HISTORY

D = datetime(2030, 5, 3)  # far future so "now" never filters candidates
VENUE = {"id": 1, "name": "Hall", "capacity": 100, "open_time": time(8), "close_time": time(21)}
VENUE2 = {"id": 2, "name": "Lawn", "capacity": 100, "open_time": time(8), "close_time": time(21)}


def ev(i, venue, sh, eh, title=None):
    return {"id": i, "title": title or f"E{i}", "venue_id": venue, "club_id": 1, "category": "Tech",
            "start": D.replace(hour=sh), "end": D.replace(hour=eh)}


def test_overlap_edges():
    a, b = ev(1, 1, 10, 12), ev(2, 1, 12, 14)
    assert not overlaps(a["start"], a["end"], b["start"], b["end"])  # back-to-back is fine
    assert overlaps(a["start"], a["end"], ev(3, 1, 11, 13)["start"], ev(3, 1, 11, 13)["end"])


def test_conflict_types():
    target = ev(1, 1, 10, 12)
    same_venue = detect_conflicts(target, [ev(2, 1, 11, 13)], VENUE)
    assert [c["type"] for c in same_venue] == ["venue_double_booking"]
    other_venue = detect_conflicts(target, [ev(2, 2, 11, 13)], VENUE)
    assert [c["type"] for c in other_venue] == ["time_overlap"]
    assert detect_conflicts(target, [ev(2, 1, 12, 14)], VENUE) == []
    blackout = [{"venue_id": 1, "start": D.replace(hour=9), "end": D.replace(hour=11), "reason": "Maintenance"}]
    assert detect_conflicts(target, [], VENUE, blackout)[0]["type"] == "venue_blackout"
    assert detect_conflicts(ev(1, 1, 6, 8), [], VENUE)[0]["type"] == "outside_venue_hours"
    assert detect_conflicts(target, [], VENUE, expected_attendees=150)[0]["type"] == "capacity_exceeded"


def test_overlap_analyzer_counts_unique_students():
    regs = {1: {1, 2, 3, 4}, 2: {3, 4, 9}, 3: {4, 5}}
    r = analyze_overlap(1, regs, [2, 3])
    assert r["affected_count"] == 2 and r["affected_students"] == [3, 4]  # student 4 counted once
    assert r["by_event"][0]["shared_count"] == 2 and r["affected_pct"] == 0.5


def test_predictor_fallback_when_history_is_thin():
    hist = [{"registered": 10, "attended": 9, "club_id": 1, "category": "Tech"}] * (MIN_HISTORY - 1)
    p = predict_attendance(100, 200, hist, club_id=1, category="Tech")
    assert p["method"] == "fallback_default" and p["base_show_rate"] == DEFAULT_SHOW_RATE
    assert p["confidence"] == "low" and "Fallback" in p["explanation"]


def test_predictor_uses_history_and_clash_penalty():
    hist = [{"registered": 100, "attended": 90, "club_id": 1, "category": "Tech"}] * 4
    clean = predict_attendance(100, 200, hist, club_id=1, category="Tech")
    assert clean["method"] == "historical" and clean["history_scope"] == "club"
    assert clean["base_show_rate"] > DEFAULT_SHOW_RATE
    clash = predict_attendance(100, 200, hist, club_id=1, category="Tech", affected_students=20)
    assert clash["predicted_attendees"] == clean["predicted_attendees"] - 10  # 20 students * 0.5
    assert clash["conflict_free"] == 0.8


def test_predictor_scope_falls_back_to_category_then_campus():
    hist = [{"registered": 50, "attended": 40, "club_id": 9, "category": "Tech"}] * 3
    assert predict_attendance(50, 100, hist, club_id=1, category="Tech")["history_scope"] == "category"
    assert predict_attendance(50, 100, hist, club_id=1, category="Sports")["history_scope"] == "campus"


def test_optimizer_moves_clash_and_respects_availability():
    mine, rival = ev(1, 1, 18, 20, "Mine"), ev(2, 2, 18, 20, "Rival")
    regs = {1: set(range(1, 21)), 2: set(range(1, 11))}  # 10 shared students
    blackouts = [{"venue_id": 1, "start": D.replace(hour=0), "end": D.replace(hour=23), "reason": "x"}]  # not on D+1
    res = optimize_schedule(mine, [rival], regs, [VENUE, VENUE2], blackouts=[], now=D - timedelta(days=5))
    assert res["current"]["affected_students"] == 10
    assert res["recommendations"], "should find a better slot"
    best = res["recommendations"][0]
    assert best["affected_students"] == 0 and best["improvement"] > 0 and best["students_saved"] == 10
    # every recommendation avoids venue double-booking with the rival
    for r in res["recommendations"]:
        assert not (r["venue_id"] == 2 and r["start"] < rival["end"] and rival["start"] < r["end"])

    # block venue 1 entirely on the original day and shift search to that day only
    blk = [{"venue_id": 1, "start": D.replace(hour=0), "end": D.replace(hour=23, minute=59), "reason": "Exam"}]
    res = optimize_schedule(mine, [rival], regs, [VENUE], blackouts=blk, now=D - timedelta(days=5), search_days=0)
    assert res["recommendations"] == []


def test_optimizer_never_exceeds_capacity():
    small = dict(VENUE2, capacity=5)
    res = optimize_schedule(ev(1, 1, 18, 20), [], {1: set(range(1, 21))}, [VENUE, small], now=D - timedelta(days=5))
    assert all(r["venue_id"] != 2 for r in res["recommendations"])
