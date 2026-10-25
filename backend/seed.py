"""Fill the database with realistic *fictional* demo data.

    python seed.py            # add demo data (only if the database is empty)
    python seed.py --reset    # drop every table, recreate, then seed

Dates are generated relative to today, so the demo always has upcoming
events, a weekly feed and recent history for the Attendance Predictor.

Demo logins (all fictional):
    admin@campus.test        Admin@123
    priya@campus.test        Coord@123   (coordinator: Tech, Robotics, E-Cell)
    rahul@campus.test        Coord@123   (coordinator: Music, Drama, Photography)
    meera@campus.test        Coord@123   (coordinator: Sports, Literary)
    student@campus.test      Student@123 (student)
"""
import random
import sys
from datetime import datetime, time, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (Club, ClubActivity, Event, Membership, Notification, Registration, User, Venue,
                        VenueBlackout)

FIRST = ["Aarav", "Diya", "Kabir", "Isha", "Neel", "Anika", "Rohan", "Tara", "Veer", "Meher",
         "Arjun", "Sana", "Dev", "Riya", "Kian", "Zoya", "Aditya", "Nisha", "Yash", "Leela"]
LAST = ["Nair", "Menon", "Iyer", "Pillai", "Varma", "Kurup", "Thomas", "George", "Mathew", "Joseph",
        "Warrier", "Panicker", "Namboodiri", "Kaimal", "Das", "Rao", "Shetty", "Bhat", "Kamath", "Pai"]
DEPTS = ["Computer Science", "Electronics", "Mechanical", "Civil", "Business Studies", "Design"]


def _dt(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute))


def seed():
    rnd = random.Random(2026)
    today = datetime.now().date()
    pw = {k: generate_password_hash(v) for k, v in
          {"admin": "Admin@123", "coord": "Coord@123", "student": "Student@123"}.items()}

    def user(name, email, role, key, dept=None):
        u = User(name=name, email=email, role=role, password_hash=pw[key], department=dept)
        db.session.add(u)
        return u

    admin = user("Campus Admin", "admin@campus.test", "admin", "admin")
    priya = user("Priya Raman", "priya@campus.test", "coordinator", "coord", "Computer Science")
    rahul = user("Rahul Verma", "rahul@campus.test", "coordinator", "coord", "Design")
    meera = user("Meera Joseph", "meera@campus.test", "coordinator", "coord", "Business Studies")
    demo = user("Demo Student", "student@campus.test", "student", "student", "Computer Science")
    students = [demo]
    combos = [(f, l) for f in FIRST for l in LAST]
    rnd.shuffle(combos)
    for i, (f, l) in enumerate(combos[:219]):
        students.append(user(f"{f} {l}", f"{f.lower()}.{l.lower()}{i}@campus.test", "student", "student",
                             rnd.choice(DEPTS)))
    db.session.flush()

    V = {}
    for name, loc, cap, fac, o, c in [
        ("Seminar hall", "Academic Block, Level 2", 180, "Projector,Sound system,Air conditioning,Wi-Fi", 8, 21),
        ("Main lawn", "Central Quadrangle", 400, "Open air,Stage,Power outlets", 8, 21),
        ("Amphitheatre", "Behind Library", 250, "Stage,Sound system,Stepped seating", 9, 21),
        ("Robotics lab", "Engineering Block", 40, "Workbenches,Power outlets,Wi-Fi", 9, 20),
        ("Auditorium", "Arts Centre", 500, "Stage,Projector,Sound system,Green room,Air conditioning", 8, 21),
        ("Seminar room B", "Academic Block, Level 1", 60, "Projector,Whiteboard,Wi-Fi", 8, 20),
        ("Sports ground", "East Campus", 300, "Floodlights,Changing rooms", 7, 20),
        ("Library hall", "Library, Level 3", 80, "Projector,Wi-Fi,Quiet zone", 9, 19),
    ]:
        V[name] = Venue(name=name, location=loc, capacity=cap, facilities=fac, open_time=time(o), close_time=time(c))
        db.session.add(V[name])
    db.session.flush()
    db.session.add(VenueBlackout(venue_id=V["Main lawn"].id, start=_dt(today + timedelta(days=9), 8),
                                 end=_dt(today + timedelta(days=9), 21), reason="Lawn maintenance"))

    C = {}
    for name, cat, desc, coord in [
        ("Tech Club", "Tech", "Hackathons, talks and build nights for curious coders.", priya),
        ("Music Club", "Culture", "Bands, jams and campus concerts.", rahul),
        ("Drama Club", "Culture", "Stage plays, improv and open mic nights.", rahul),
        ("Robotics Club", "Tech", "Build, program and battle robots.", priya),
        ("Sports Club", "Sports", "Friendly matches and inter-department leagues.", meera),
        ("Literary Society", "Academic", "Debates, poetry slams and book talks.", meera),
        ("Photography Club", "Culture", "Photo walks, editing workshops and exhibitions.", rahul),
        ("Entrepreneurship Cell", "Academic", "Pitch nights and founder talks.", priya),
    ]:
        C[name] = Club(name=name, category=cat, description=desc, coordinator_id=coord.id)
        db.session.add(C[name])
    db.session.flush()

    # memberships: everyone joins 1-3 clubs; the demo student joins Tech + Drama
    club_list = list(C.values())
    for s in students:
        picks = [C["Tech Club"], C["Drama Club"]] if s is demo else rnd.sample(club_list, rnd.randint(1, 3))
        for c in picks:
            db.session.add(Membership(user_id=s.id, club_id=c.id))

    # ---------- past events (history for the Attendance Predictor) ----------
    booked = set()
    for club in club_list:
        for _ in range(rnd.randint(3, 6)):
            for _try in range(20):
                day = today - timedelta(days=rnd.randint(3, 60))
                venue = rnd.choice(list(V.values()))
                if (venue.id, day) not in booked:
                    booked.add((venue.id, day))
                    break
            else:
                continue
            hour = rnd.choice([10, 14, 16, 17, 18, 19])
            e = Event(club_id=club.id, venue_id=venue.id, category=club.category, status="published",
                      title=rnd.choice(["Monthly meetup", "Skills workshop", "Open session", "Showcase", "Guest talk",
                                        "Friendly tournament", "Social evening"]) + f" #{rnd.randint(1, 40)}",
                      description="Past event kept for attendance history.", created_by=club.coordinator_id,
                      start=_dt(day, hour), end=_dt(day, hour + 2), capacity=min(venue.capacity, 120))
            db.session.add(e)
            db.session.flush()
            rate = {10: .62, 14: .72, 16: .84, 17: .86, 18: .88, 19: .82}[hour] + rnd.uniform(-.06, .06)
            for s in rnd.sample(students, min(e.capacity, rnd.randint(20, 70))):
                db.session.add(Registration(event_id=e.id, user_id=s.id, attended=rnd.random() < rate,
                                            marked_at=e.end))

    # ---------- upcoming events (match the PPT mockups) ----------
    fri = today + timedelta(days=1)
    while fri.weekday() != 4:
        fri += timedelta(days=1)
    sat, sun = fri + timedelta(days=1), fri + timedelta(days=2)

    def event(club, venue, title, day, sh, sm, eh, em, cat, desc, status="published", cap=None):
        e = Event(club_id=C[club].id, venue_id=V[venue].id, title=title, description=desc, category=cat,
                  start=_dt(day, sh, sm), end=_dt(day, eh, em), status=status, capacity=cap,
                  created_by=C[club].coordinator_id)
        db.session.add(e)
        db.session.flush()
        return e

    def register(e, people):
        for s in people:
            db.session.add(Registration(event_id=e.id, user_id=s.id))

    pool = students[1:]
    hack = event("Tech Club", "Seminar hall", "Hackathon kickoff night", fri, 18, 0, 21, 0, "Tech",
                 "Teams form, themes drop and the 24-hour build begins. Pizza, mentors and a very loud playlist.", cap=180)
    hack_people = [demo] + rnd.sample(pool, 141)
    register(hack, hack_people)
    mic = event("Drama Club", "Amphitheatre", "Open mic and improv jam", fri, 18, 30, 21, 0, "Culture",
                "Poetry, stand-up, improv games. Sign up on the night or just come to cheer.", cap=120)
    shared = rnd.sample(hack_people[1:], 11)
    rest = [s for s in pool if s not in hack_people]
    register(mic, [demo] + shared + rnd.sample(rest, 46))
    bands = event("Music Club", "Main lawn", "Battle of the bands", sat, 17, 0, 20, 0, "Culture",
                  "Six campus bands, one trophy. Food stalls open from 4 pm.", cap=350)
    bands_people = rnd.sample(pool, 104)
    register(bands, bands_people)
    bots = event("Robotics Club", "Robotics lab", "Bot battle arena", sat, 14, 0, 16, 30, "Tech",
                 "Bring your bot. Weight class 1 kg and 3 kg. Safety goggles provided.", cap=40)
    register(bots, rnd.sample(pool, 21))
    walk = event("Photography Club", "Library hall", "Sunrise photo walk", sun, 10, 0, 12, 0, "Culture",
                 "A guided walk around campus in the soft morning light. Phones welcome.", cap=60)
    register(walk, rnd.sample(pool, 31))
    foot = event("Sports Club", "Sports ground", "Inter-department football friendly", sun, 16, 0, 18, 0, "Sports",
                 "Seven-a-side. Teams of 10 per department; spectators very welcome.", cap=200)
    register(foot, rnd.sample(pool, 83))
    ml = event("Tech Club", "Seminar room B", "Intro to machine learning workshop", fri + timedelta(days=4), 15, 0, 17, 0,
               "Tech", "Hands-on notebook session. Bring a laptop. No prior experience needed.", cap=60)
    register(ml, rnd.sample(pool, 44))
    slam = event("Literary Society", "Library hall", "Poetry slam", fri + timedelta(days=5), 17, 0, 19, 0, "Academic",
                 "Three rounds, five minutes each, one winner.", cap=80)
    register(slam, rnd.sample(pool, 37))
    pitch = event("Entrepreneurship Cell", "Seminar hall", "Startup pitch night", fri + timedelta(days=6), 17, 0, 19, 0,
                  "Academic", "Eight student teams pitch to alumni founders.", cap=180)
    register(pitch, rnd.sample(pool, 96))
    # draft that deliberately clashes with the pitch night so coordinators can see the Conflict Detector
    event("Tech Club", "Seminar hall", "Alumni career talk", fri + timedelta(days=6), 18, 0, 19, 30, "Tech",
          "Draft: three alumni on breaking into industry. (Venue clashes with Startup pitch night.)", status="draft", cap=150)
    event("Sports Club", "Sports ground", "Chess in the park", today + timedelta(days=2), 15, 0, 17, 0, "Sports",
          "Cancelled because of the forecast.", status="cancelled", cap=40)

    for c, title, body in [
        ("Tech Club", "Hackathon team-matching is open", "Solo? Drop your skills in the form and we'll pair you up."),
        ("Drama Club", "Auditions for the spring play", "Auditions next month. Prepare a one-minute monologue."),
        ("Music Club", "Sound check schedule", "Bands: your slots go out after registration closes."),
    ]:
        db.session.add(ClubActivity(club_id=C[c].id, title=title, body=body))
    db.session.add(Notification(user_id=demo.id, kind="club", message="Welcome to Campus Pulse! Join clubs to see more events."))
    db.session.commit()
    return {"users": User.query.count(), "events": Event.query.count()}


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        if "--reset" in sys.argv:
            db.drop_all()
            db.create_all()
        if User.query.count():
            print("Database already has data. Run `python seed.py --reset` to start over.")
        else:
            print("Seeded:", seed())
