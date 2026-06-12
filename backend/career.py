"""
Career Mode Router
Covers both tracks:
  A) Interview Prep  – JD analysis, mock interview, resume gap, skills roadmap
  B) Upskill / Grow  – current role, skill map, deepen vs branch-out, learning plan
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import openai
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/career", tags=["career"])


# ── Shared helper ─────────────────────────────────────────────────────────────

def get_client() -> openai.OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=401, detail="OPENAI_API_KEY not set")
    return openai.OpenAI(api_key=key)


def chat(client: openai.OpenAI, messages: list[dict], temperature: float = 0.4) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=1500,
    )
    return resp.choices[0].message.content


# ══════════════════════════════════════════════════════════════════════════════
# TRACK A — Interview Prep
# ══════════════════════════════════════════════════════════════════════════════

class JDAnalysisRequest(BaseModel):
    """User pastes a job description, or gives title + target companies."""
    job_title: str
    company: Optional[str] = None
    job_description: Optional[str] = None   # full JD text if available


class ResumeGapRequest(BaseModel):
    job_title: str
    job_description: str
    resume_text: str                         # plain text paste of resume


class MockInterviewMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class MockInterviewRequest(BaseModel):
    job_title: str
    company: Optional[str] = None
    job_description: Optional[str] = None
    history: list[MockInterviewMessage]
    user_answer: str
    question_number: int = 1


class InterviewFeedbackRequest(BaseModel):
    job_title: str
    history: list[MockInterviewMessage]     # full interview transcript


# ── A1: Analyse JD → extract requirements, skills, culture signals ────────────

@router.post("/interview/analyse-jd")
def analyse_jd(req: JDAnalysisRequest):
    """
    Parse a job description (or infer from title/company) into:
    - required_skills, nice_to_have_skills
    - key_responsibilities
    - likely_interview_topics
    - culture_signals
    - suggested_learning_plan (skills to build before applying)
    """
    client = get_client()

    jd_block = req.job_description or f"[No JD provided — infer from: {req.job_title} at {req.company or 'a typical company'}]"

    prompt = f"""You are a senior career coach. Analyse this job description for a "{req.job_title}" role{f' at {req.company}' if req.company else ''}.

Job Description:
\"\"\"
{jd_block}
\"\"\"

Return ONLY valid JSON:
{{
  "role_summary": "2-sentence plain-English summary of the role",
  "required_skills": ["skill 1", "skill 2", ...],
  "nice_to_have_skills": ["skill 1", ...],
  "key_responsibilities": ["responsibility 1", ...],
  "likely_interview_topics": [
    {{"topic": "System design", "why": "Senior backend role needs architecture thinking", "difficulty": "hard"}},
    ...
  ],
  "culture_signals": ["Fast-paced startup environment", ...],
  "suggested_learning_plan": [
    {{"skill": "Kubernetes", "priority": "high", "reason": "Listed as required, not just nice-to-have"}},
    ...
  ],
  "red_flags": ["Optional — anything in the JD that seems concerning or vague"]
}}"""

    result = chat(client, [{"role": "user", "content": prompt}])
    return json.loads(result)


# ── A2: Resume gap analysis ───────────────────────────────────────────────────

@router.post("/interview/resume-gap")
def resume_gap(req: ResumeGapRequest):
    """
    Compare resume against JD.
    Returns match score, missing skills, weak areas, and rewrite suggestions.
    """
    client = get_client()

    prompt = f"""You are a senior technical recruiter. Score this resume against the job description.

Job Title: {req.job_title}
Job Description:
\"\"\"
{req.job_description}
\"\"\"

Resume:
\"\"\"
{req.resume_text}
\"\"\"

Return ONLY valid JSON:
{{
  "match_score": 72,
  "match_label": "Strong match / Moderate match / Weak match",
  "matched_skills": ["skill 1", ...],
  "missing_skills": [
    {{"skill": "Kubernetes", "importance": "required", "suggestion": "Add a side project or get CKA cert"}},
    ...
  ],
  "weak_sections": [
    {{"section": "Work experience", "issue": "Responsibilities listed, but no measurable outcomes", "fix": "Add metrics: 'Reduced API latency by 40%' not 'Improved API performance'"}},
    ...
  ],
  "strong_sections": ["Education well-matched", "Side projects relevant"],
  "rewrite_bullets": [
    {{"original": "Built a REST API", "rewritten": "Designed and shipped a REST API serving 50k daily requests, reducing p99 latency from 800ms to 120ms"}},
    ...
  ],
  "overall_advice": "2-3 sentences of honest coaching advice"
}}"""

    result = chat(client, [{"role": "user", "content": prompt}])
    return json.loads(result)


# ── A3: Mock interview — streaming, with real-time feedback ──────────────────

INTERVIEWER_SYSTEM = """\
You are a senior interviewer at {company} conducting a {job_title} interview.

Your job is to run a rigorous but fair mock interview. Rules:
1. Ask ONE question at a time. Never ask multiple questions in one message.
2. After the candidate answers, give brief inline feedback (1-2 sentences: what was strong, what was missing).
3. Then ask the next question. Mix question types: behavioural (STAR), technical, and situational.
4. After {total_questions} questions, say INTERVIEW_COMPLETE and nothing else.
5. Be professional but realistic — don't be artificially encouraging.
6. For technical questions, probe follow-ups if the answer is shallow.

JD context: {jd_snippet}
"""

@router.post("/interview/mock/chat")
def mock_interview_chat(req: MockInterviewRequest):
    """
    Streaming mock interview turn.
    The interviewer gives feedback on the last answer and asks the next question.
    Returns SSE stream.
    """
    client = get_client()

    jd_snippet = (req.job_description or "")[:600] if req.job_description else "Not provided"
    total_questions = 6

    system = INTERVIEWER_SYSTEM.format(
        company=req.company or "the company",
        job_title=req.job_title,
        total_questions=total_questions,
        jd_snippet=jd_snippet,
    )

    messages = [{"role": "system", "content": system}]
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.user_answer})

    def stream():
        buffer = ""
        with client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
            temperature=0.6,
            max_tokens=600,
        ) as stream_resp:
            for chunk in stream_resp:
                delta = chunk.choices[0].delta.content or ""
                buffer += delta
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"

        is_done = "INTERVIEW_COMPLETE" in buffer
        yield f"data: {json.dumps({'done': True, 'interview_complete': is_done})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── A4: End-of-interview scoring ──────────────────────────────────────────────

@router.post("/interview/mock/feedback")
def interview_feedback(req: InterviewFeedbackRequest):
    """
    After interview completes, return a structured performance report.
    """
    client = get_client()

    transcript = "\n".join(
        f"{'INTERVIEWER' if m.role == 'assistant' else 'CANDIDATE'}: {m.content}"
        for m in req.history
    )

    prompt = f"""You are a senior hiring manager. Review this mock interview transcript for a {req.job_title} role and provide a structured performance assessment.

Transcript:
\"\"\"
{transcript}
\"\"\"

Return ONLY valid JSON:
{{
  "overall_score": 74,
  "hire_signal": "Strong yes / Lean yes / Lean no / Strong no",
  "dimension_scores": {{
    "communication": 80,
    "technical_depth": 65,
    "problem_solving": 70,
    "behavioural_examples": 75,
    "role_fit": 78
  }},
  "strengths": ["Clear communication throughout", "Strong STAR format on behavioural questions"],
  "areas_to_improve": [
    {{"area": "System design depth", "specific_gap": "Couldn't articulate trade-offs between SQL and NoSQL", "how_to_fix": "Practice 10 system design questions. Study CAP theorem."}},
    ...
  ],
  "best_answer": "Question 3 — the candidate gave a well-structured STAR answer with clear metrics.",
  "weakest_answer": "Question 5 — technical answer lacked depth on time complexity.",
  "next_steps": ["Study distributed systems basics", "Practice 3 more mock interviews", "Polish resume metrics"]
}}"""

    result = chat(client, [{"role": "user", "content": prompt}])
    return json.loads(result)


# ══════════════════════════════════════════════════════════════════════════════
# TRACK B — Upskill / Grow
# ══════════════════════════════════════════════════════════════════════════════

class SkillMapRequest(BaseModel):
    current_role: str
    years_experience: int = 0
    goal: str                       # e.g. "become a senior engineer" or "move into ML"
    track: str = "deepen"           # "deepen" | "branch"
    current_skills: Optional[list[str]] = None


class LearningGoalRequest(BaseModel):
    current_role: str
    target_skill: str
    timeline_weeks: int = 8
    hours_per_week: int = 5
    skill_map: Optional[dict] = None   # from /career/upskill/skill-map


# ── B1: Skill map ─────────────────────────────────────────────────────────────

@router.post("/upskill/skill-map")
def skill_map(req: SkillMapRequest):
    """
    Generate a skill map: what they know, what gaps exist, what to prioritise.
    """
    client = get_client()

    skills_block = f"Current skills they listed: {', '.join(req.current_skills)}" if req.current_skills else "No skills listed — infer from role."

    prompt = f"""You are a senior engineering career coach. Map out this person's skill landscape.

Current role: {req.current_role}
Experience: {req.years_experience} years
Goal: {req.goal}
Track: {req.track} ({'deepen expertise in current area' if req.track == 'deepen' else 'branch out into a new adjacent area'})
{skills_block}

Return ONLY valid JSON:
{{
  "current_level": "Mid-level / Senior / Lead / etc.",
  "target_role": "What role this goal maps to (e.g. Senior ML Engineer)",
  "skill_clusters": [
    {{
      "cluster": "Core backend",
      "skills": [
        {{"name": "Python", "current_level": "proficient", "target_level": "expert", "gap": "low"}},
        {{"name": "System design", "current_level": "beginner", "target_level": "proficient", "gap": "high"}}
      ]
    }}
  ],
  "priority_skills": [
    {{"skill": "System design", "reason": "Biggest gap, highest leverage for target role", "estimated_hours": 40}}
  ],
  "learning_sequence": ["Start with X because Y", "Then move to Z once X is solid"],
  "timeline_estimate": "Realistic timeline to reach goal with 5hrs/week"
}}"""

    result = chat(client, [{"role": "user", "content": prompt}])
    return json.loads(result)


# ── B2: Generate a structured learning plan ───────────────────────────────────

@router.post("/upskill/learning-plan")
def learning_plan(req: LearningGoalRequest):
    """
    Turn a target skill + timeline into a week-by-week learning plan.
    Each week maps to MetaLearn session topics.
    """
    client = get_client()

    prompt = f"""You are a senior learning designer. Create a structured learning plan.

Current role: {req.current_role}
Target skill: {req.target_skill}
Timeline: {req.timeline_weeks} weeks
Available time: {req.hours_per_week} hours/week
Total hours: {req.timeline_weeks * req.hours_per_week}

Return ONLY valid JSON:
{{
  "plan_title": "e.g. 'ML Engineering Foundations — 8-Week Plan'",
  "goal_statement": "By the end of this plan, you will be able to...",
  "phases": [
    {{
      "phase": 1,
      "name": "Foundations",
      "weeks": "1-2",
      "focus": "Core concepts before anything else",
      "sessions": [
        {{
          "week": 1,
          "topic": "Linear algebra for ML",
          "session_type": "concept",
          "hours": 5,
          "metalearn_prompt": "Teach me the linear algebra operations used in neural networks",
          "milestone": "Understand matrix multiplication and why it matters for ML"
        }}
      ]
    }}
  ],
  "weekly_structure": "Suggested split of the {req.hours_per_week}hrs/week",
  "checkpoints": [
    {{"week": 4, "checkpoint": "Build a simple linear regression from scratch"}},
    ...
  ],
  "success_metrics": ["Can explain concept X without notes", "Built project Y", ...]
}}"""

    result = chat(client, [{"role": "user", "content": prompt}])
    return json.loads(result)


# ── B3: Goal check-in — assess progress, adjust plan ─────────────────────────

class GoalCheckinRequest(BaseModel):
    original_goal: str
    current_week: int
    total_weeks: int
    sessions_completed: int
    sessions_planned: int
    self_rating: int        # 1-10, how well they feel they're progressing
    blockers: Optional[str] = None


@router.post("/upskill/goal-checkin")
def goal_checkin(req: GoalCheckinRequest):
    """
    Weekly check-in: assess progress against plan, surface blockers, adjust.
    """
    client = get_client()

    completion_rate = req.sessions_completed / max(req.sessions_planned, 1)
    weeks_remaining = req.total_weeks - req.current_week

    prompt = f"""A learner is checking in on their learning goal: "{req.original_goal}"

Progress:
- Week {req.current_week} of {req.total_weeks}
- Sessions completed: {req.sessions_completed} / {req.sessions_planned} planned ({completion_rate:.0%} completion)
- Self-rating: {req.self_rating}/10
- Blockers: {req.blockers or "None mentioned"}
- Weeks remaining: {weeks_remaining}

Return ONLY valid JSON:
{{
  "progress_assessment": "honest 2-sentence assessment of where they are",
  "on_track": true,
  "risk_level": "low / medium / high",
  "recommended_adjustments": [
    {{"adjustment": "Reduce scope: skip advanced topic X, focus on core Y", "reason": "Only 3 weeks left and foundational gaps remain"}}
  ],
  "encouragement": "One genuine, specific observation about what they've done well",
  "next_week_focus": "One specific thing to focus on next week",
  "suggested_session_topic": "Exact topic to plug into MetaLearn next session"
}}"""

    result = chat(client, [{"role": "user", "content": prompt}])
    return json.loads(result)