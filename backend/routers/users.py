"""
backend/routers/users.py
User auth is handled by Clerk/Supabase Auth on the frontend —
this router handles MetaLearn-specific user profile data only.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def get_profile():
    """Returns the authenticated user's metacognitive profile.
    Stub until Supabase integration is wired in V1."""
    return {
        "knowledge_awareness_score": 0.62,
        "calibration_score": 0.44,
        "reflection_quality_score": 0.71,
        "concept_transfer_score": 0.38,
        "total_sessions": 12,
        "streak_days": 4,
    }
