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
            "experience_threshold_years": jd.min_experience or 2.0,
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
    """
    Fetches the existing active rubric for a JD or generates a new one.
    """
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
