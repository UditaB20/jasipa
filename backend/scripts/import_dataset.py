"""Import rows from the Kaggle Resume Dataset (Resume.csv) without resetting the database.

    python scripts/import_dataset.py ../Resume.csv --categories INFORMATION-TECHNOLOGY HR --per-category 10
"""
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.migrations import run_additive_migrations  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.services.dataset_import import CATEGORY_JOBS, import_resumes  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Kaggle Resume.csv rows into JASIPA")
    parser.add_argument("path", nargs="?", default=os.path.join(os.path.dirname(__file__), "..", "..", "Resume.csv"))
    parser.add_argument("--categories", nargs="*", default=sorted(CATEGORY_JOBS), help="Dataset categories to import")
    parser.add_argument("--per-category", type=int, default=10)
    parser.add_argument("--no-screen", action="store_true", help="Import without running the Resume-Screener")
    args = parser.parse_args()
    run_additive_migrations(engine)
    with SessionLocal() as db:
        print(import_resumes(db, args.path, args.categories, args.per_category, screen=not args.no_screen))
