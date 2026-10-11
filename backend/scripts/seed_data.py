"""Resets the database and loads candidates from the Kaggle Resume Dataset (Resume.csv).

No synthetic candidates, assessments, decisions or outcomes are created. Imported records are screened
against the job for their dataset category by the real Resume-Screener; everything after screening
(assessments, panel, bias check, decision) happens through the application.

    python scripts/seed_data.py                      # 8 resumes for each of the 6 mapped categories
    python scripts/seed_data.py --per-category 20
    python scripts/seed_data.py --demo-accounts      # also create two empty candidate portal logins

HR accounts are defined in app/auth/security.py (hr@jasipa.ai / admin123, reviewer@jasipa.ai / reviewer123).
"""
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402

DEFAULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Resume.csv")
DEMO_ACCOUNTS = [("Demo Candidate", "student@jasipa.ai", "student123"), ("Second Demo Candidate", "candidate@jasipa.ai", "candidate123")]


def seed_database(csv_path: str = DEFAULT_CSV, per_category: int = 8, demo_accounts: bool = False, use_llm: bool = False,
                  categories=None):
    if not use_llm:
        settings.LLM_PROVIDER = "mock"
    from app.auth.security import hash_password
    from app.database.migrations import run_additive_migrations
    from app.database.models import Candidate
    from app.database.session import Base, SessionLocal, engine
    from app.services.dataset_import import CATEGORY_JOBS, import_resumes
    from app.services.assessment_service import get_question_set_for_jd
    from app.database.models import JobDescription

    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    run_additive_migrations(engine)
    with SessionLocal() as db:
        stats = import_resumes(db, csv_path, categories or sorted(CATEGORY_JOBS), per_category, actor="seed")
        print(f"Imported {stats['imported']} dataset resumes: {stats['per_category']}")
        for jd in db.query(JobDescription).all():
            get_question_set_for_jd(db, jd)  # warm the assessment cache so the portal opens instantly
        if demo_accounts:
            for name, email, password in DEMO_ACCOUNTS:
                db.add(Candidate(name=name, email=email, password_hash=hash_password(password), source="candidate_portal",
                                 current_stage="REGISTERED", skills_extracted=[], resume_profile={}))
            db.commit()
            print("Created empty portal accounts: " + ", ".join(e for _, e, _ in DEMO_ACCOUNTS))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset the database and import the Kaggle Resume Dataset.")
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--per-category", type=int, default=8)
    parser.add_argument("--demo-accounts", action="store_true", help="Create two empty candidate portal accounts")
    parser.add_argument("--use-llm", action="store_true", help="Use the configured LLM provider while screening")
    args = parser.parse_args()
    seed_database(args.csv, args.per_category, args.demo_accounts, args.use_llm)
