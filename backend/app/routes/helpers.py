from datetime import datetime

from flask import jsonify


def bad(msg, code=400):
    return jsonify(error=msg), code


def parse_dt(value, field="date"):
    """Parse ISO strings like 2026-11-14T18:00 (also accepts a trailing Z)."""
    if not value:
        raise ValueError(f"{field} is required.")
    try:
        return datetime.fromisoformat(str(value).replace("Z", "")).replace(tzinfo=None)
    except ValueError:
        raise ValueError(f"{field} is not a valid date/time.")


def clean(value, max_len=None):
    value = (value or "").strip()
    return value[:max_len] if max_len else value
