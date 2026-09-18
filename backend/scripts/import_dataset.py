import sys
import os
import csv
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.database.models import Candidate, JobDescription
from app.services.resume_parser import extract_preliminary_metadata
from app.services.rubric_service import get_or_create_rubric

def import_kaggle_resumes(csv_or_json_path: str, target_jd_id: str = "JD-SWE-101"):
    """
    Imports resume records from a Kaggle CSV or JSON export into the JASIPA database.
    Format supported: CSV with columns (e.g. 'Resume_str', 'Resume_title', 'Category', 'ID')
    or JSON array of candidate objects.
    """
    db = SessionLocal()
    imported_count = 0

    if not os.path.exists(csv_or_json_path):
        print(f"File not found: {csv_or_json_path}")
        return

    if csv_or_json_path.endswith(".csv"):
        with open(csv_or_json_path, mode="r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 50: # Cap bulk import at 50 records per run
                    break
                
                resume_text = row.get("Resume_str") or row.get("resume") or row.get("text") or ""
                name = row.get("name") or f"Imported Candidate {i+1}"
                email = row.get("email") or f"imported.candidate.{i+1}@kaggle-dataset.org"
                category = row.get("Category") or "Engineering"

                meta = extract_preliminary_metadata(resume_text)
                
                # Check for existing
                existing = db.query(Candidate).filter(Candidate.email == email).first()
                if not existing:
                    cand = Candidate(
                        name=name,
                        email=email,
                        cohort_tag="Kaggle_Import_Cohort",
                        resume_text=resume_text,
                        skills_extracted=meta["skills"],
                        experience_years=meta["experience_years"],
                        education=meta["education"],
                        target_jd_id=target_jd_id,
                        current_stage="APPLIED"
                    )
                    db.add(cand)
                    imported_count += 1

    db.commit()
    db.close()
    print(f"Successfully imported {imported_count} candidate records from {csv_or_json_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        import_kaggle_resumes(sys.argv[1])
    else:
        print("Usage: python import_dataset.py <path_to_kaggle_csv_or_json>")
