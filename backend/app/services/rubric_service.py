from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.database.models import JobDescription, Rubric

DEFAULT_BEHAVIORAL_COMPETENCIES = [
    {
        "competency": "Communication",
        "description": "Ability to articulate technical and non-technical ideas clearly, actively listen, and adjust communication style.",
        "max_points": 25
    },
    {
        "competency": "Team Collaboration",
        "description": "Demonstrated ability to resolve disagreements constructively, support peers, and foster a healthy team environment.",
        "max_points": 25
    },
    {
        "competency": "Problem Solving",
        "description": "Structured approach to tackling ambiguity, breaking down complex engineering challenges, and continuous learning.",
        "max_points": 25
    },
    {
        "competency": "Adaptability",
        "description": "Resilience in fast-changing environments, receptiveness to feedback, and agility when learning new tools.",
        "max_points": 25
    }
]

def generate_rubric_for_jd(jd: JobDescription, version: str = "1.0") -> Dict[str, Any]:
    """
    Generates a structured, anchored scoring rubric customized for a specific Job Description.
    """
    required_skills = jd.required_skills or []
    preferred_skills = jd.preferred_skills or []
    
    # Distribute 100 resume points across required skills, experience, projects, and education
    req_count = len(required_skills) if required_skills else 1
    pref_count = len(preferred_skills) if preferred_skills else 1
    
    # 50 points for required skills, 15 points for preferred, 20 for experience, 15 for education/projects
    skill_points = {}
    for skill in required_skills:
        skill_points[skill] = round(50.0 / req_count, 1)
    
    preferred_points = {}
    for skill in preferred_skills:
        preferred_points[skill] = round(15.0 / pref_count, 1)

    rubric_criteria = {
        "jd_title": jd.title,
        "department": jd.department,
        "weights": {
            "resume_fit": 0.40,
            "technical_skill": 0.40,
            "behavioral_fit": 0.20
        },
        "resume_scoring": {
            "required_skills_weight": 50,
            "required_skills_breakdown": skill_points,
            "preferred_skills_weight": 15,
            "preferred_skills_breakdown": preferred_points,
            "experience_threshold_years": int(jd.min_experience if jd.min_experience is not None else 2),
            "experience_weight": 20,

            "education_and_projects_weight": 15
        },
        "technical_scoring": {
            "skills_evaluated": required_skills,
            "mcq_weight": 30,
            "coding_weight": 40,
            "short_answer_weight": 30,
            "passing_threshold": 70.0
        },
        "behavioral_scoring": {
            "competencies": DEFAULT_BEHAVIORAL_COMPETENCIES,
            "total_points": 100,
            "insufficient_evidence_threshold": 0.50
        }
    }

    return rubric_criteria

def get_or_create_rubric(db: Session, jd: JobDescription) -> Rubric:
    """Returns the rubric for the JD's active version, generating version 1.0 on first use."""
    existing_rubric = db.query(Rubric).filter(Rubric.jd_id == jd.jd_id, Rubric.version == jd.rubric_version).first()
    if existing_rubric:
        return existing_rubric

    criteria = generate_rubric_for_jd(jd, version=jd.rubric_version)
    rubric = Rubric(
        jd_id=jd.jd_id,
        version=jd.rubric_version,
        resume_weight=0.40,
        skill_weight=0.40,
        culture_weight=0.20,
        criteria=criteria
    )
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return rubric


def next_version(db: Session, jd_id: str, current: str) -> str:
    """Next free minor version (1.0 -> 1.1 -> ... -> 1.10), never reusing an existing version label."""
    used = {row.version for row in db.query(Rubric.version).filter(Rubric.jd_id == jd_id).all()}
    try:
        major, minor = (current or "1.0").split(".", 1)
        major, minor = int(major), int(minor)
    except ValueError:
        major, minor = 1, 0
    candidate = f"{major}.{minor + 1}"
    while candidate in used:
        minor += 1
        candidate = f"{major}.{minor + 1}"
    return candidate


def rubric_to_dict(rubric: Rubric) -> Dict[str, Any]:
    """Uniform rubric payload for agents: weights, version and criteria together."""
    return {"rubric_id": rubric.rubric_id, "jd_id": rubric.jd_id, "version": rubric.version,
            "resume_weight": rubric.resume_weight, "skill_weight": rubric.skill_weight,
            "culture_weight": rubric.culture_weight, "criteria": rubric.criteria or {}}


def jd_to_dict(jd: JobDescription) -> Dict[str, Any]:
    return {"jd_id": jd.jd_id, "title": jd.title, "department": jd.department, "description": jd.description,
            "required_skills": jd.required_skills or [], "preferred_skills": jd.preferred_skills or [],
            "min_experience": jd.min_experience, "education_requirement": jd.education_requirement,
            "rubric_version": jd.rubric_version}
