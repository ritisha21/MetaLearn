"""
backend/routers/dashboard.py
Aggregated analytics for the dashboard wireframe screen.
Stub until Supabase stores real session data.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_dashboard():
    """Returns aggregated session metrics for the dashboard.
    Stub until Supabase integration is wired in V1."""
    return {
        "understanding_score": 74,
        "calibration_score": 82,
        "concept_mastery": 68,
        "total_sessions": 12,
        "streak_days": 4,
        "recent_sessions": [
            {"topic": "CNNs", "feynman_score": 0.71, "calibration_error": -13},
            {"topic": "Linear Algebra", "feynman_score": 0.84, "calibration_error": 5},
            {"topic": "Transformers", "feynman_score": 0.62, "calibration_error": 22},
            {"topic": "System Design", "feynman_score": 0.78, "calibration_error": -8},
        ],
    }
