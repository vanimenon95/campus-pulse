"""Turn model objects into JSON-friendly dicts."""
from .models import Registration


def club_to_dict(c, member_count=None, joined=None):
    return {"id": c.id, "name": c.name, "category": c.category, "description": c.description,
            "coordinator_id": c.coordinator_id,
            "coordinator_name": c.coordinator.name if c.coordinator else None,
            "is_active": c.is_active,
            "member_count": len(c.memberships) if member_count is None else member_count,
            "joined": joined}


def event_to_dict(e, registered=None, flags=None, user_registered=None):
    if registered is None:
        registered = Registration.query.filter_by(event_id=e.id).count()
    d = {"id": e.id, "title": e.title, "description": e.description, "category": e.category,
         "start": e.start.isoformat(), "end": e.end.isoformat(), "status": e.status,
         "club_id": e.club_id, "club_name": e.club.name,
         "venue_id": e.venue_id, "venue_name": e.venue.name, "venue_capacity": e.venue.capacity,
         "capacity": e.cap, "registered": registered, "created_by": e.created_by,
         "user_registered": user_registered}
    if flags is not None:
        d["flags"] = flags
    return d
