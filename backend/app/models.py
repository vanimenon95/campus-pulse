"""Database models (the OOP business layer's entities).

Inheritance: every account is a ``User``; the ``role`` column decides whether
it behaves as a student, coordinator or admin (see ``User.can``).
"""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

ROLES = ("student", "coordinator", "admin")
EVENT_CATEGORIES = ("Tech", "Culture", "Sports", "Academic", "Social")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    department = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def can(self, *roles):
        return self.role in roles

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role,
                "department": self.department, "is_active": self.is_active,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class Club(db.Model):
    __tablename__ = "clubs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(40), nullable=False, default="Tech")
    description = db.Column(db.Text)
    coordinator_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    coordinator = db.relationship("User", foreign_keys=[coordinator_id])
    memberships = db.relationship("Membership", cascade="all, delete-orphan", back_populates="club")
    activities = db.relationship("ClubActivity", cascade="all, delete-orphan", back_populates="club")


class Membership(db.Model):
    __tablename__ = "memberships"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User")
    club = db.relationship("Club", back_populates="memberships")
    __table_args__ = (db.UniqueConstraint("user_id", "club_id", name="uq_member"),)


class ClubActivity(db.Model):
    """A news/announcement post a club publishes on its page."""
    __tablename__ = "club_activities"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    club = db.relationship("Club", back_populates="activities")


class Venue(db.Model):
    __tablename__ = "venues"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    location = db.Column(db.String(160))
    capacity = db.Column(db.Integer, nullable=False)
    facilities = db.Column(db.String(255))  # comma separated: "Projector,Wi-Fi,Stage"
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)
    blackouts = db.relationship("VenueBlackout", cascade="all, delete-orphan", back_populates="venue")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "location": self.location, "capacity": self.capacity,
                "facilities": [f.strip() for f in (self.facilities or "").split(",") if f.strip()],
                "open_time": self.open_time.strftime("%H:%M"), "close_time": self.close_time.strftime("%H:%M")}


class VenueBlackout(db.Model):
    """A period when a venue cannot be booked (maintenance, exams...)."""
    __tablename__ = "venue_blackouts"
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey("venues.id"), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(160))
    venue = db.relationship("Venue", back_populates="blackouts")

    def to_dict(self):
        return {"id": self.id, "venue_id": self.venue_id, "start": self.start.isoformat(),
                "end": self.end.isoformat(), "reason": self.reason}


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey("venues.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(40), nullable=False, default="Tech")
    start = db.Column(db.DateTime, nullable=False, index=True)
    end = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer)  # registration cap; defaults to venue capacity
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft|published|cancelled
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)
    club = db.relationship("Club")
    venue = db.relationship("Venue")
    registrations = db.relationship("Registration", cascade="all, delete-orphan", back_populates="event")

    @property
    def cap(self):
        return min(self.capacity or self.venue.capacity, self.venue.capacity)


class Registration(db.Model):
    __tablename__ = "registrations"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    attended = db.Column(db.Boolean)  # NULL = not recorded yet, True/False once marked
    marked_at = db.Column(db.DateTime)
    event = db.relationship("Event", back_populates="registrations")
    user = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("event_id", "user_id", name="uq_registration"),)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(30), default="info")  # info|conflict|event|club
    message = db.Column(db.String(255), nullable=False)
    event_id = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {"id": self.id, "kind": self.kind, "message": self.message, "event_id": self.event_id,
                "is_read": self.is_read, "created_at": self.created_at.isoformat()}


class RevokedToken(db.Model):
    """Logout support: a token's id is stored here so it can no longer be used."""
    __tablename__ = "revoked_tokens"
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), unique=True, nullable=False)
    revoked_at = db.Column(db.DateTime, default=utcnow)
