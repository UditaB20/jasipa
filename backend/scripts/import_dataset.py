import sys
import os
import csv
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.database.models import Candidate, JobDescription
from app.services.resume_parser import extract_preliminary_metadata

# Category to Job Description mapping with specific domain skills
KAGGLE_CATEGORY_JD_TEMPLATES = {
    "INFORMATION-TECHNOLOGY": {
        "title": "IT Systems & Infrastructure Engineer",
        "department": "Information Technology",
        "description": "Responsible for enterprise IT systems administration, infrastructure management, network configurations, database operations, and user support systems.",
        "required_skills": ["Information Technology", "Networking", "Systems Administration", "SQL", "Troubleshooting"],
        "preferred_skills": ["Linux", "Cloud", "Security", "Active Directory"],
        "min_experience": 2.0,
        "education": "Bachelor's in Information Technology, Computer Science, or related field"
    },
    "ENGINEERING": {
        "title": "Systems Software & Hardware Engineer",
        "department": "Engineering",
        "description": "Designs and develops technical engineering systems, CAD/embedded solutions, and automated testing architectures.",
        "required_skills": ["Engineering", "Python", "Problem Solving", "CAD", "Quality Assurance"],
        "preferred_skills": ["Embedded Systems", "C++", "MATLAB", "Automation"],
        "min_experience": 3.0,
        "education": "Bachelor's in Engineering or related discipline"
    },
    "HR": {
        "title": "Human Resources Specialist",
        "department": "People & Culture",
        "description": "Manages talent recruitment lifecycles, employee relations, onboarding programs, performance management, and compliance.",
        "required_skills": ["Human Resources", "Recruitment", "Employee Relations", "Communication", "Talent Acquisition"],
        "preferred_skills": ["HRIS", "Compliance", "Workday", "Performance Management"],
        "min_experience": 2.0,
        "education": "Bachelor's in Human Resources, Business Administration, or Psychology"
    },
    "FINANCE": {
        "title": "Financial Analyst & Planning Specialist",
        "department": "Finance",
        "description": "Performs financial modeling, variance analyses, forecasting, fiscal reporting, and balance sheet evaluations.",
        "required_skills": ["Finance", "Financial Modeling", "Excel", "Accounting", "Data Analysis"],
        "preferred_skills": ["SAP", "PowerBI", "Forecasting", "Audit"],
        "min_experience": 2.5,
        "education": "Bachelor's in Finance, Economics, or Accounting"
    },
    "ACCOUNTANT": {
        "title": "Staff Accountant",
        "department": "Accounting",
        "description": "Manages general ledger reconciliations, payroll processing, accounts payable/receivable, and quarterly reporting.",
        "required_skills": ["Accounting", "General Ledger", "Auditing", "Taxation", "Reconciliation"],
        "preferred_skills": ["QuickBooks", "GAAP", "Excel", "Payroll"],
        "min_experience": 2.0,
        "education": "Bachelor's in Accounting"
    },
    "BUSINESS-DEVELOPMENT": {
        "title": "Business Development Manager",
        "department": "Growth & Sales",
        "description": "Drives strategic client acquisition, partnership expansions, B2B deal negotiations, and market penetration.",
        "required_skills": ["Business Development", "Lead Generation", "Negotiation", "Client Relationship", "Strategy"],
        "preferred_skills": ["Salesforce", "CRM", "Contract Negotiation", "Market Research"],
        "min_experience": 3.0,
        "education": "Bachelor's in Business, Marketing, or Communications"
    }
}

def get_or_create_category_jd(db: SessionLocal, category: str) -> JobDescription:
    """
    Retrieves or generates a matching Job Description and Rubric for the given Kaggle resume category.
    """
    clean_cat = category.strip().upper()
    template = KAGGLE_CATEGORY_JD_TEMPLATES.get(clean_cat, {
        "title": f"{clean_cat.title()} Specialist",
        "department": clean_cat.title(),
        "description": f"Role focused on core responsibilities and industry practices in {clean_cat.title()}.",
        "required_skills": [clean_cat.title(), "Communication", "Problem Solving", "Analysis"],
        "preferred_skills": ["Project Management", "Leadership"],
        "min_experience": 2.0,
        "education": "Bachelor's degree or equivalent experience"
    })
    
    # Check if a JD for this title already exists
    existing_jd = db.query(JobDescription).filter(JobDescription.title == template["title"]).first()
    if existing_jd:
        return existing_jd
        
    jd_id = f"JD-KAG-{clean_cat.replace('-', '_')}"
    # Check if JD ID exists
    existing_by_id = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if existing_by_id:
        return existing_by_id

    from app.services.rubric_service import get_or_create_rubric

    new_jd = JobDescription(
        jd_id=jd_id,
        title=template["title"],
        department=template["department"],
        description=template["description"],
        required_skills=template["required_skills"],
        preferred_skills=template["preferred_skills"],
        min_experience=template["min_experience"],
        education_requirement=template["education"],
        rubric_version="1.0"
    )
    db.add(new_jd)
    db.commit()
    db.refresh(new_jd)
    
    # Anchor scoring rubric
    get_or_create_rubric(db, new_jd)
    print(f"  * Generated anchored JD & Rubric: [{new_jd.jd_id}] {new_jd.title}")
    return new_jd

def import_kaggle_resumes(
    csv_path: str,
    target_jd_id: str = None,
    categories: list = None,
    limit: int = 30
):
    """
    Imports resume records from Kaggle Resume.csv into the JASIPA database.
    Dynamically creates category-anchored Job Descriptions and Rubrics so
    imported candidates are properly linked to relevant requisitions.
    """
    if not os.path.exists(csv_path):
        print(f"Error: File not found at '{csv_path}'")
        return 0

    db = SessionLocal()
    imported_count = 0
    category_counts = {}

    with open(csv_path, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if imported_count >= limit:
                break

            category = (row.get("Category") or "General").strip().upper()
            
            # Apply category filter if specified
            if categories and category not in [c.upper() for c in categories]:
                continue

            raw_id = row.get("ID") or f"{imported_count+1}"
            candidate_id = f"CAND-KAG-{raw_id}"
            resume_text = row.get("Resume_str") or row.get("resume") or row.get("text") or ""
            
            if len(resume_text.strip()) < 50:
                continue

            # Determine appropriate JD: use category-anchored JD unless an override JD was given
            if target_jd_id:
                candidate_jd_id = target_jd_id
            else:
                cat_jd = get_or_create_category_jd(db, category)
                candidate_jd_id = cat_jd.jd_id

            email = f"kaggle.{raw_id.lower()}@applicant-pool.org"
            
            # Extract first line or title as name
            first_line = resume_text.strip().split("\n")[0].strip()
            title_part = first_line[:30] if first_line else category
            name = f"Candidate {raw_id} ({title_part.title()})"

            meta = extract_preliminary_metadata(resume_text)
            
            # Use category-based cohort tags for bias testing
            cohort_tag = f"Kaggle_{category.replace('-', '_')}"

            # Check if candidate already exists
            existing = db.query(Candidate).filter(
                (Candidate.candidate_id == candidate_id) | (Candidate.email == email)
            ).first()

            if not existing:
                cand = Candidate(
                    candidate_id=candidate_id,
                    name=name,
                    email=email,
                    cohort_tag=cohort_tag,
                    resume_text=resume_text,
                    skills_extracted=meta["skills"],
                    experience_years=meta["experience_years"],
                    education=meta["education"],
                    target_jd_id=candidate_jd_id,
                    current_stage="APPLIED"
                )
                db.add(cand)
                imported_count += 1
                category_counts[category] = category_counts.get(category, 0) + 1
                print(f"  + [{category}] {candidate_id} -> {candidate_jd_id} | Skills: {len(meta['skills'])} | Exp: {meta['experience_years']}y")
            else:
                # Update existing candidate's target_jd_id if assigned to default JD
                if not target_jd_id and existing.target_jd_id == "JD-SWE-101":
                    cat_jd = get_or_create_category_jd(db, category)
                    existing.target_jd_id = cat_jd.jd_id
                    print(f"  ~ Updated {existing.candidate_id} target JD to {cat_jd.jd_id}")

    db.commit()
    db.close()

    print(f"\n Successfully imported {imported_count} candidate records into database!")
    print(f"Cohort Breakdown: {category_counts}")
    return imported_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Kaggle Resume.csv into JASIPA database")
    parser.add_argument("path", nargs="?", default=None, help="Path to Resume.csv")
    parser.add_argument("--jd", default=None, help="Target Job Description ID (default: category-anchored JD)")
    parser.add_argument("--categories", nargs="*", default=["INFORMATION-TECHNOLOGY", "ENGINEERING"],
                        help="Categories to import (e.g. INFORMATION-TECHNOLOGY ENGINEERING HR)")
    parser.add_argument("--limit", type=int, default=20, help="Max number of resumes to import (default: 20)")

    args = parser.parse_args()

    # Search for Resume.csv if not provided
    csv_file = args.path
    if csv_file and os.path.isdir(csv_file):
        for candidate_name in ["Resume.csv", "resume.csv"]:
            candidate_path = os.path.join(csv_file, candidate_name)
            if os.path.exists(candidate_path):
                csv_file = candidate_path
                break
    elif not csv_file:
        for candidate_path in ["Resume.csv", "../Resume.csv", "backend/Resume.csv"]:
            if os.path.exists(candidate_path):
                csv_file = candidate_path
                break

    if not csv_file:
        print("Usage: python import_dataset.py <path_to_Resume.csv>")
        sys.exit(1)

    print(f"Reading dataset: {csv_file}")
    print(f"Target JD: {args.jd}")
    print(f"Selected Categories: {args.categories}")
    print(f"Import Limit: {args.limit}\n")
    import_kaggle_resumes(csv_file, target_jd_id=args.jd, categories=args.categories, limit=args.limit)
