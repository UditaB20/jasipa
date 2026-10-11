"""Resets the database and seeds demo data by driving the real services end to end.

Every score, panel decision, bias check and audit entry is produced by the same code paths the API
uses (resume parsing, question generation, sandboxed code scoring, the LangGraph pipeline and the
human decision endpoint), so the demo data is internally consistent.

By default the seed runs deterministically without LLM calls. Pass --use-llm to use the configured provider.

Demo accounts
  HR:         hr@jasipa.ai / admin123, reviewer@jasipa.ai / reviewer123, recruiter@jasipa.ai / admin123
  Candidates: candidate@jasipa.ai / candidate123 (decided application)
              student@jasipa.ai / student123 (applied; assessments open)
"""
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402

DEMO_PASSWORDS = {"candidate@jasipa.ai": "candidate123", "student@jasipa.ai": "student123"}

JOBS = [
    {"jd_id": "JD-SWE-101", "title": "Senior Full Stack Engineer", "department": "Engineering",
     "description": "Design and build cloud-native microservices in Python and FastAPI.\n"
                    "Develop responsive React user interfaces used by internal recruiters.\n"
                    "Model and optimise PostgreSQL schemas and SQL queries for reporting workloads.\n"
                    "Review code, mentor engineers and improve CI/CD reliability.",
     "required_skills": ["Python", "React", "SQL", "FastAPI", "Data Structures"],
     "preferred_skills": ["Docker", "Kubernetes", "AWS", "CI/CD"], "min_experience": 4,
     "education_requirement": "Bachelor's in Computer Science or equivalent experience"},
    {"jd_id": "JD-MLE-202", "title": "Machine Learning Engineer", "department": "AI Research",
     "description": "Build and evaluate machine learning models for document classification.\n"
                    "Own feature pipelines in Python and Pandas with reproducible experiments.\n"
                    "Train and fine-tune PyTorch models and monitor their quality in production.\n"
                    "Write SQL to assemble labelled training datasets.",
     "required_skills": ["Python", "Machine Learning", "PyTorch", "SQL", "Pandas"],
     "preferred_skills": ["Docker", "Deep Learning", "GCP"], "min_experience": 3,
     "education_requirement": "Bachelor's or Master's in CS, Statistics or a related field"},
    {"jd_id": "JD-SCA-303", "title": "Supply Chain Planning Analyst", "department": "Operations",
     "description": "Forecast demand and plan inventory for 40 regional warehouses.\n"
                    "Build Excel and Power BI reports that track stock-outs and supplier lead times.\n"
                    "Coordinate replenishment plans with procurement and logistics partners.\n"
                    "Investigate forecast errors and recommend process improvements.",
     "required_skills": ["Excel", "Data Analysis", "Demand Forecasting", "Inventory Planning", "Communication"],
     "preferred_skills": ["Power BI", "SAP", "SQL"], "min_experience": 2,
     "education_requirement": "Bachelor's in Supply Chain, Operations, Business or Engineering"},
]

# name, email, cohort, job, years, skills, quality (strong|medium|weak|mixed), target state
CANDIDATES = [
    ("Elena Rostova", "candidate@jasipa.ai", "Cohort_Alpha", "JD-SWE-101", 6, ["Python", "FastAPI", "React", "SQL", "Data Structures", "Docker", "AWS"], "strong", "approve"),
    ("Marcus Vance", "marcus.vance@example.com", "Cohort_Alpha", "JD-SWE-101", 2, ["Python", "React", "SQL", "FastAPI"], "medium", "awaiting"),
    ("Tariq Al-Mansoor", "tariq.mansoor@example.com", "Cohort_Beta", "JD-SWE-101", 5, ["Python", "SQL", "FastAPI", "Data Structures"], "strong", "awaiting"),
    ("Chloe Bennett", "chloe.bennett@example.com", "Cohort_Alpha", "JD-SWE-101", 4, ["Python", "React", "SQL"], "brief", "awaiting"),
    ("Rohan Iyer", "rohan.iyer@example.com", "Cohort_Gamma", "JD-SWE-101", 7, ["Python", "React", "SQL", "FastAPI", "Data Structures", "Kubernetes"], "mixed", "awaiting"),
    ("Samuel O'Connor", "samuel.oconnor@example.com", "Cohort_Alpha", "JD-SWE-101", 3, ["Python", "React", "SQL"], "medium", "assessed"),
    ("Priya Sharma", "student@jasipa.ai", "Cohort_Beta", "JD-SWE-101", 5, ["Python", "SQL", "FastAPI", "Docker"], "medium", "applied"),
    ("Fatima Zahra", "fatima.zahra@example.com", "Cohort_Beta", "JD-SWE-101", 6, ["Python", "React", "SQL", "Data Structures"], "strong", "approve"),
    ("Jonas Weber", "jonas.weber@example.com", "Cohort_Alpha", "JD-SWE-101", 5, ["Python", "React", "SQL", "FastAPI", "Data Structures"], "strong", "approve"),
    ("Mei Lin", "mei.lin@example.com", "Cohort_Gamma", "JD-SWE-101", 4, ["Python", "React", "SQL", "FastAPI"], "medium", "reject"),
    ("Daniel Okafor", "daniel.okafor@example.com", "Cohort_Beta", "JD-SWE-101", 3, ["Python", "SQL"], "weak", "reject"),
    ("Sofia Rossi", "sofia.rossi@example.com", None, "JD-SWE-101", 4, ["Python", "React", "SQL", "FastAPI"], "medium", "screened"),
    ("David Chen", "david.chen@example.com", "Cohort_Beta", "JD-MLE-202", 4, ["Python", "Machine Learning", "PyTorch", "SQL", "Pandas"], "strong", "approve"),
    ("Aisha Khan", "aisha.khan@example.com", "Cohort_Gamma", "JD-MLE-202", 4, ["Python", "Machine Learning", "Pandas", "SQL"], "medium", "awaiting"),
    ("Lucas Silva", "lucas.silva@example.com", "Cohort_Gamma", "JD-MLE-202", 3, ["Python", "Machine Learning", "PyTorch"], "weak", "reject"),
    ("Hannah Schmidt", "hannah.schmidt@example.com", "Cohort_Alpha", "JD-MLE-202", 5, ["Python", "Machine Learning", "PyTorch", "SQL", "Pandas", "Docker"], "strong", "approve"),
    ("Kwame Mensah", "kwame.mensah@example.com", "Cohort_Beta", "JD-MLE-202", 2, ["Python", "Pandas", "SQL"], "medium", "reject"),
    ("Ana Lima", "ana.lima@example.com", "Cohort_Gamma", "JD-MLE-202", 6, ["Python", "Machine Learning", "PyTorch", "SQL", "Pandas"], "strong", "approve"),
    ("Grace Muller", "grace.muller@example.com", "Cohort_Alpha", "JD-SCA-303", 3, ["Excel", "Data Analysis", "Demand Forecasting", "Inventory Planning", "Power BI"], "strong", "approve"),
    ("Arjun Patel", "arjun.patel@example.com", "Cohort_Gamma", "JD-SCA-303", 2, ["Excel", "Inventory Planning", "SAP"], "medium", "awaiting"),
    ("Noah Johnson", "noah.johnson@example.com", "Cohort_Beta", "JD-SCA-303", 1, ["Excel", "Communication"], "weak", "reject"),
    ("Leila Haddad", "leila.haddad@example.com", "Cohort_Alpha", "JD-SCA-303", 4, ["Excel", "Data Analysis", "Demand Forecasting", "SQL"], "medium", "approve"),
]

PROJECTS = {
    "JD-SWE-101": ["Recruiting dashboard: React front end over a FastAPI service with PostgreSQL, used by 120 recruiters.",
                   "Migrated a monolith to containerised microservices, cutting p95 latency by 40%."],
    "JD-MLE-202": ["Document classifier in PyTorch reaching 0.91 macro-F1 on 60k labelled contracts.",
                   "Feature store in Pandas and SQL with versioned, reproducible training datasets."],
    "JD-SCA-303": ["Weekly demand forecast model in Excel that reduced stock-outs by 18% across 12 warehouses.",
                   "Power BI supplier lead-time report adopted by the procurement team."],
}


def resume_for(name, years, skills, job_id, rng):
    start = datetime.utcnow().year - years
    mid = start + max(1, years // 2)
    degree = rng.choice(["B.Tech in Computer Science", "Bachelor of Science in Information Systems",
                         "Master of Science in Data Science", "Bachelor of Engineering"])
    if job_id == "JD-SCA-303":
        degree = rng.choice(["Bachelor of Business Administration, Operations", "Bachelor of Engineering, Industrial"])
    return "\n".join([
        name, "Summary", f"Professional with {years} years of experience using {', '.join(skills[:4])}.",
        "Experience", f"Senior role, Northwind Ltd ({mid} - Present)", f"Delivered work using {', '.join(skills)}.",
        f"Associate role, Contoso ({start} - {mid})", "Collaborated with cross-functional teams on delivery.",
        "Education", f"{degree}, State University, {start - 1}",
        "Projects", *PROJECTS[job_id],
        "Skills", ", ".join(skills),
    ])


def technical_answers(questions, quality, rng):
    answers = []
    for q in questions:
        kind = q.get("type")
        strong = quality == "strong" or (quality == "mixed" and kind == "mcq") or (quality == "medium" and rng.random() < 0.6)
        if kind == "mcq":
            letter = q["correct_option"] if strong else rng.choice([o for o in "ABCD" if o != q["correct_option"]])
            text = letter
        elif kind == "coding":
            fn = q["coding"]["function_name"]
            reference = q["coding"]["reference_solution"]
            if quality == "strong":
                text = reference
            elif quality in ("medium", "brief"):
                # Plausible solution that mishandles empty inputs, so some hidden tests fail.
                text = reference.replace(f"def {fn}(", f"def _draft_{fn}(", 1) + (
                    f"\n\ndef {fn}(*args):\n    if any(a in ([], '', {{}}) for a in args):\n        return None\n    return _draft_{fn}(*args)\n")
            else:
                text = f"def {fn}(*args):\n    return None\n"
        else:
            guide = q.get("rubric_guideline", "")
            if strong:
                text = (f"My approach: {guide} I would start by clarifying requirements, then implement it incrementally, "
                        "compare two options and explain the trade-off, and validate the result with tests and a review "
                        "of edge cases before rollout, monitoring it afterwards.")
            else:
                text = "I would look into it and use the usual tools to get it done."
        answers.append({"question_id": q["question_id"], "answer_text": text})
    return answers


def behavioral_answers(questions, quality):
    answers = []
    for q in questions:
        if quality == "brief":
            text = "I am a good team player."
        elif quality in ("strong", "mixed"):
            text = (f"Situation: during a release at my previous role, our team hit a problem related to {q['competency_or_skill'].lower()}. "
                    "Task: I was responsible for getting the work back on track within two weeks. "
                    "Action: I analyzed the root cause, I proposed a plan, I communicated trade-offs to stakeholders and I organized daily check-ins. "
                    "Result: we delivered on time, reduced defects by 30% and the process was adopted by two other teams.")
        elif quality == "medium":
            text = (f"In my last project I worked on {q['competency_or_skill'].lower()} with my team. I needed to fix a delay, "
                    "so we talked it through and agreed a plan, and it improved afterwards.")
        else:
            text = "We usually discuss things as a team and it works out."
        answers.append({"question_id": q["question_id"], "answer_text": text})
    return answers


def seed_database(use_llm: bool = False):
    if not use_llm:
        settings.LLM_PROVIDER = "mock"

    from app.api.reviews import submit_human_decision
    from app.auth.security import HR_USERS, hash_password
    from app.database.migrations import run_additive_migrations
    from app.database.models import Candidate, JobDescription
    from app.database.session import Base, SessionLocal, engine
    from app.schemas.outcome import HiringOutcomeCreate
    from app.schemas.review import HumanReviewCreate
    from app.services.assessment_service import get_question_set_for_jd, submit_assessment
    from app.services.audit_service import log_event
    from app.services.outcome_service import OutcomeRecordingService
    from app.services.pipeline_service import run_candidate_pipeline, screen_candidate
    from app.services.resume_parser import extract_preliminary_metadata, text_hash
    from app.services.rubric_service import get_or_create_rubric

    rng = random.Random(2027)
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    run_additive_migrations(engine)
    db = SessionLocal()

    hr = {"email": "hr@jasipa.ai", "name": HR_USERS["hr@jasipa.ai"]["name"], "user_id": HR_USERS["hr@jasipa.ai"]["user_id"], "role": "HR"}
    reviewer = {"email": "reviewer@jasipa.ai", "name": HR_USERS["reviewer@jasipa.ai"]["name"],
                "user_id": HR_USERS["reviewer@jasipa.ai"]["user_id"], "role": "HR"}

    print("Creating jobs, rubrics and question sets...")
    jobs = {}
    for spec in JOBS:
        jd = JobDescription(**spec, rubric_version="1.0")
        db.add(jd)
        db.commit()
        rubric = get_or_create_rubric(db, jd)
        log_event(db, stage="JD_CREATED", event=f"Job created: {jd.title}", agent=f"HR ({hr['name']})",
                  input_reference={"jd_id": jd.jd_id}, output={"rubric_version": rubric.version}, rubric_version=rubric.version)
        question_set = get_question_set_for_jd(db, jd)
        print(f"  {jd.title}: {len(question_set.technical_questions)} technical / {len(question_set.behavioral_questions)} behavioral ({question_set.generator})")
        jobs[jd.jd_id] = (jd, question_set)

    print("Creating candidates and running the pipeline...")
    approved = []
    for index, (name, email, cohort, job_id, years, skills, quality, target) in enumerate(CANDIDATES, start=1):
        jd, question_set = jobs[job_id]
        resume = resume_for(name, years, skills, job_id, rng)
        meta = extract_preliminary_metadata(resume, jd.required_skills + jd.preferred_skills)
        cand = Candidate(
            candidate_id=f"CAND-{index:03d}-{name.split()[0].upper().replace(chr(39), '')}", name=name, email=email,
            phone=f"+1 555 01{index:02d}", cohort_tag=cohort, resume_text=resume, resume_hash=text_hash(resume),
            skills_extracted=meta["skills"], experience_years=meta["experience_years"], education=meta["education"],
            resume_profile={**meta["profile"], "format": "text"}, target_jd_id=jd.jd_id, current_stage="APPLIED",
            password_hash=hash_password(DEMO_PASSWORDS[email]) if email in DEMO_PASSWORDS else None,
            created_at=datetime.utcnow() - timedelta(days=30 - index))
        db.add(cand)
        db.commit()
        log_event(db, stage="APPLIED", event=f"Candidate applied for {jd.title}", agent="CandidatePortal",
                  candidate_id=cand.candidate_id, input_reference={"jd_id": jd.jd_id})
        if target == "applied":
            continue
        screen_candidate(db, cand, jd, actor="seed")
        if target == "screened":
            continue
        submit_assessment(db, cand, jd, "TECHNICAL", technical_answers(question_set.technical_questions, quality, rng))
        submit_assessment(db, cand, jd, "BEHAVIORAL", behavioral_answers(question_set.behavioral_questions, quality))
        if target == "assessed":
            continue
        result = run_candidate_pipeline(db, cand, actor="seed")
        if target == "awaiting":
            continue
        decision = "APPROVE" if target == "approve" else "REJECT"
        status = result["panel_result"]
        notes = ("Strong, consistent evidence across resume, technical and behavioral stages; bias check reviewed."
                 if decision == "APPROVE" else "Technical and behavioral evidence below the role's bar; bias check reviewed, no concerns.")
        submit_human_decision(HumanReviewCreate(candidate_id=cand.candidate_id, decision=decision, notes=notes,
                                                decision_id=status["decision_id"]), current_user=hr, db=db)
        if status.get("requires_four_eyes_review"):
            submit_human_decision(HumanReviewCreate(candidate_id=cand.candidate_id, decision=decision,
                                                    notes="Second reviewer: agree with the first reviewer after reading the evidence.",
                                                    decision_id=status["decision_id"]), current_user=reviewer, db=db)
        if decision == "APPROVE":
            approved.append(cand)

    print("Recording post-hire outcomes...")
    outcomes = OutcomeRecordingService(db)
    for i, cand in enumerate(approved[:5]):
        outcomes.record_outcome(HiringOutcomeCreate(
            candidate_id=cand.candidate_id, hired_date=datetime.utcnow() - timedelta(days=200 + 30 * i),
            performance_rating=[4.5, 4.0, 3.5, 4.2, 3.0][i], still_employed=i != 4, months_employed=6 + i,
            manager_name="Morgan Lee", manager_email=hr["email"], role=cand.job_description.title,
            manager_feedback="Ramped up quickly and delivers reliably."), hr)

    total = db.query(Candidate).count()
    db.close()
    print(f"Seed complete: {len(JOBS)} jobs, {total} candidates.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset and seed the JASIPA database with demo data.")
    parser.add_argument("--use-llm", action="store_true", help="Use the configured LLM provider instead of deterministic strategies")
    seed_database(use_llm=parser.parse_args().use_llm)
