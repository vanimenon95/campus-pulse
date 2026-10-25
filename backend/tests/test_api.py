"""API tests against an in-memory SQLite database seeded with demo data."""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Event, Venue


def test_public_feed_and_stats(client):
    r = client.get("/api/events?upcoming=1")
    assert r.status_code == 200
    titles = {e["title"]: e for e in r.json["events"]}
    hack = titles["Hackathon kickoff night"]
    assert hack["registered"] == 142 and hack["flags"]["affected_students"] == 12
    assert client.get("/api/events?upcoming=1&category=Sports").json["events"][0]["title"].startswith("Inter-department")
    assert client.get("/api/events?upcoming=1&q=bands").json["events"][0]["title"] == "Battle of the bands"
    stats = client.get("/api/stats").json
    assert stats["active_clubs"] == 8 and 0 <= stats["conflict_free_pct"] <= 100


def test_auth_flow_and_roles(client, login):
    assert client.post("/api/auth/register", json={"name": "A", "email": "bad", "password": "x"}).status_code == 400
    r = client.post("/api/auth/register", json={"name": "Test User", "email": "t@campus.test", "password": "password1"})
    assert r.status_code == 201 and r.json["user"]["role"] == "student"
    assert client.post("/api/auth/register", json={"name": "Test User", "email": "t@campus.test", "password": "password1"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "t@campus.test", "password": "nope"}).status_code == 401
    student = {"Authorization": "Bearer " + r.json["token"]}
    assert client.get("/api/admin/users", headers=student).status_code == 403
    assert client.get("/api/coordinator/dashboard", headers=student).status_code == 403
    assert client.get("/api/admin/users").status_code == 401
    assert client.post("/api/auth/logout", headers=student).status_code == 200
    assert client.get("/api/auth/me", headers=student).status_code == 401  # token revoked


def test_register_cancel_and_full_event(client, login, app):
    h = login("student@campus.test", "Student@123")
    ev = client.get("/api/events?upcoming=1&q=football").json["events"][0]
    assert client.post(f"/api/events/{ev['id']}/register", headers=h).status_code == 201
    assert client.post(f"/api/events/{ev['id']}/register", headers=h).status_code == 409
    assert client.delete(f"/api/events/{ev['id']}/register", headers=h).status_code == 200
    e = db.session.get(Event, ev["id"])
    e.capacity = ev["registered"]
    db.session.commit()
    assert client.post(f"/api/events/{ev['id']}/register", headers=h).status_code == 409  # full


def test_event_detail_insights(client, login):
    ev = next(e for e in client.get("/api/events?upcoming=1").json["events"] if e["title"].startswith("Open mic"))
    detail = client.get(f"/api/events/{ev['id']}").json["event"]
    ins = detail["insights"]
    assert ins["overlap"]["affected_count"] == 12
    assert ins["prediction"]["method"] in ("historical", "fallback_default")
    assert ins["conflicts"][0]["type"] == "time_overlap"
    assert "students" not in ins["overlap"]["by_event"][0]  # names hidden from the public
    h = login("rahul@campus.test", "Coord@123")
    managed = client.get(f"/api/events/{ev['id']}", headers=h).json["event"]
    assert len(managed["insights"]["overlap"]["by_event"][0]["students"]) == 12


def test_optimizer_endpoint_and_permissions(client, login):
    ev = next(e for e in client.get("/api/events?upcoming=1").json["events"] if e["title"].startswith("Open mic"))
    assert client.get(f"/api/events/{ev['id']}/optimize", headers=login("student@campus.test", "Student@123")).status_code == 403
    assert client.get(f"/api/events/{ev['id']}/optimize", headers=login("meera@campus.test", "Coord@123")).status_code == 404  # not her club
    res = client.get(f"/api/events/{ev['id']}/optimize", headers=login("rahul@campus.test", "Coord@123")).json
    assert res["recommendations"] and res["recommendations"][0]["affected_students"] == 0


def test_event_lifecycle_and_publish_guard(client, login):
    h = login("priya@campus.test", "Coord@123")
    clubs = client.get("/api/clubs").json["clubs"]
    tech = next(c for c in clubs if c["name"] == "Tech Club")["id"]
    hall = next(v for v in client.get("/api/venues").json["venues"] if v["name"] == "Seminar hall")["id"]
    day = (datetime.now() + timedelta(days=40)).replace(hour=0, minute=0, second=0, microsecond=0)
    payload = {"title": "Test night", "club_id": tech, "venue_id": hall, "category": "Tech",
               "start": day.replace(hour=15).isoformat(), "end": day.replace(hour=17).isoformat()}
    assert client.post("/api/events", json={**payload, "title": "x"}, headers=h).status_code == 400
    assert client.post("/api/events", json={**payload, "end": payload["start"]}, headers=h).status_code == 400
    created = client.post("/api/events", json=payload, headers=h)
    assert created.status_code == 201
    eid = created.json["event"]["id"]
    assert client.get(f"/api/events/{eid}").status_code == 404  # drafts are private
    assert client.put(f"/api/events/{eid}", json={**payload, "title": "Renamed night"}, headers=h).status_code == 200
    # a second event in the same venue/time can be drafted but never published
    dup = client.post("/api/events", json={**payload, "title": "Duplicate slot"}, headers=h).json["event"]["id"]
    assert client.post(f"/api/events/{eid}/publish", headers=h).status_code == 200
    blocked = client.post(f"/api/events/{dup}/publish", json={"force": True}, headers=h)
    assert blocked.status_code == 409 and "Venue already booked" in blocked.json["error"]
    assert client.post(f"/api/events/{eid}/cancel", headers=h).status_code == 200
    assert client.put(f"/api/events/{eid}", json=payload, headers=h).status_code == 400  # cancelled


def test_attendance_and_reports(client, login):
    h = login("priya@campus.test", "Coord@123")
    dash = client.get("/api/coordinator/dashboard", headers=h).json
    past = next(e for e in dash["events"] if e["end"] < datetime.now().isoformat() and e["registered"])
    regs = client.get(f"/api/events/{past['id']}/registrations", headers=h).json
    first = regs["registrations"][0]["user_id"]
    r = client.put(f"/api/events/{past['id']}/attendance", json={"records": [{"user_id": first, "attended": True}]}, headers=h)
    assert r.status_code == 200 and r.json["updated"] == 1
    summary = client.get(f"/api/events/{past['id']}/registrations", headers=h).json["summary"]
    assert summary["attendance_rate"] is not None and 0 <= summary["attendance_rate"] <= 1
    # attendance for future events is refused
    upcoming = next(e for e in dash["events"] if e["start"] > datetime.now().isoformat() and e["status"] == "published")
    assert client.put(f"/api/events/{upcoming['id']}/attendance", json={"records": []}, headers=h).status_code == 400
    assert client.get("/api/reports/participation", headers=h).json["summary"]["events"] > 0
    adm = login("admin@campus.test", "Admin@123")
    venues = client.get("/api/reports/venues", headers=adm).json["venues"]
    assert all(0 <= v["utilization"] <= 1 for v in venues)
    assert client.get("/api/ai/conflicts", headers=adm).json["conflicts"]


def test_club_membership_and_admin(client, login):
    h = login("student@campus.test", "Student@123")
    sports = next(c for c in client.get("/api/clubs", headers=h).json["clubs"] if c["name"] == "Sports Club")
    assert client.post(f"/api/clubs/{sports['id']}/join", headers=h).status_code in (201, 409)
    assert client.post("/api/clubs", json={"name": "Chess Club"}, headers=h).status_code == 403
    coord = login("meera@campus.test", "Coord@123")
    assert client.post("/api/clubs", json={"name": "Chess Club", "category": "Social" if False else "Academic"}, headers=coord).status_code == 201
    assert client.post(f"/api/clubs/{sports['id']}/activities", json={"title": "Kit day", "body": "Bring boots"}, headers=coord).status_code == 201
    adm = login("admin@campus.test", "Admin@123")
    users = client.get("/api/admin/users?q=priya", headers=adm).json["users"]
    assert client.put(f"/api/admin/users/{users[0]['id']}", json={"role": "student"}, headers=adm).status_code == 200
    me_id = client.get("/api/auth/me", headers=adm).json["user"]["id"]
    assert client.put(f"/api/admin/users/{me_id}", json={"role": "student"}, headers=adm).status_code == 400
    assert client.post("/api/venues", json={"name": "Tiny room", "capacity": 0}, headers=adm).status_code == 400
    assert client.post("/api/venues", json={"name": "Tiny room", "capacity": 12, "open_time": "09:00", "close_time": "17:00",
                                            "facilities": ["Whiteboard"]}, headers=adm).status_code == 201


def test_student_dashboard_flags_personal_clash(client, login):
    d = client.get("/api/me/dashboard", headers=login("student@campus.test", "Student@123")).json
    assert any("Hackathon" in c["a"] + c["b"] for c in d["my_clashes"])
    assert len(d["clubs"]) == 2
