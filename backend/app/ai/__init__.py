"""The four AI components of Campus Pulse.

Every module here is plain Python with no Flask/database imports, so the
algorithms can be read, tested and reused on their own.  The
``app.services.insights`` module is the glue that loads data from the
database and feeds it into these functions.
"""
from .conflict_detector import detect_conflicts, overlaps
from .overlap_analyzer import analyze_overlap
from .attendance_predictor import predict_attendance
from .schedule_optimizer import optimize_schedule

__all__ = ["detect_conflicts", "overlaps", "analyze_overlap",
           "predict_attendance", "optimize_schedule"]
