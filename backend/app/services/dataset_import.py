"""Import of the Kaggle Resume Dataset (snehaanbhawal/resume-dataset, file Resume.csv).

Columns used: ID, Resume_str, Resume_html, Category. The dataset contains no names, contact details,
demographics or assessment answers, so imported records:

* are identified as "Kaggle resume #<ID>" with a non-deliverable placeholder email
  (kaggle-<ID>@dataset.invalid, the reserved .invalid TLD) only because the schema needs a unique email;
* have no monitoring cohort (cohort analyses report them as missing data);
* carry source="dataset_import", external_id=<ID> and dataset_category=<Category> so they are never
  confused with candidates who applied through the portal or were uploaded by HR;
* get resume text rebuilt from Resume_html so the original section structure is preserved;
* are screened against the job for their category. They have no assessments: the dataset has none.

Job descriptions for categories are authored here (they are HR-side job postings, not dataset fields).
"""
import csv
import os
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.database.models import Candidate, JobDescription
from app.services.audit_service import log_event
from app.services.resume_parser import extract_preliminary_metadata, html_resume_to_text, text_hash
from app.services.rubric_service import get_or_create_rubric

DATASET_NAME = "Kaggle Resume Dataset (Resume.csv)"
REQUIRED_COLUMNS = {"ID", "Resume_str", "Resume_html", "Category"}

CATEGORY_JOBS: Dict[str, Dict] = {
    "INFORMATION-TECHNOLOGY": {
        "title": "IT Systems & Infrastructure Engineer", "department": "Information Technology",
        "description": "Administer enterprise servers, networks and user directories.\n"
                       "Troubleshoot hardware, software and connectivity incidents and restore service.\n"
                       "Maintain SQL databases, backups and security patching schedules.\n"
                       "Document systems and support users across departments.",
        "required_skills": ["Networking", "Troubleshooting", "SQL", "Linux", "Active Directory"],
        "preferred_skills": ["Cybersecurity", "Azure", "Project Management"], "min_experience": 2,
        "education_requirement": "Bachelor's in IT, Computer Science or equivalent experience"},
    "ENGINEERING": {
        "title": "Systems & Process Engineer", "department": "Engineering",
        "description": "Design and improve engineering systems and production processes.\n"
                       "Produce CAD drawings and technical specifications for new components.\n"
                       "Run quality assurance tests and analyse root causes of failures.\n"
                       "Coordinate with manufacturing and project teams on delivery.",
        "required_skills": ["CAD", "Quality Assurance", "Project Management", "Troubleshooting", "AutoCAD"],
        "preferred_skills": ["MATLAB", "Python", "Lean Manufacturing"], "min_experience": 3,
        "education_requirement": "Bachelor's in Engineering"},
    "HR": {
        "title": "Human Resources Specialist", "department": "People & Culture",
        "description": "Run recruitment from job posting through offer for business teams.\n"
                       "Handle employee relations cases and ensure policy compliance.\n"
                       "Coordinate onboarding, payroll inputs and benefits administration.\n"
                       "Maintain HR records and reporting in the HRIS.",
        "required_skills": ["Recruitment", "Employee Relations", "Payroll", "Compliance", "Onboarding"],
        "preferred_skills": ["HRIS", "Benefits Administration", "Training"], "min_experience": 2,
        "education_requirement": "Bachelor's in Human Resources, Business or Psychology"},
    "FINANCE": {
        "title": "Financial Analyst", "department": "Finance",
        "description": "Build financial models and forecasts for budgeting cycles.\n"
                       "Analyse variances against plan and explain drivers to managers.\n"
                       "Prepare monthly reporting packs in Excel.\n"
                       "Support audits with reconciliations and documentation.",
        "required_skills": ["Financial Analysis", "Excel", "Forecasting", "Budgeting", "Accounting"],
        "preferred_skills": ["Financial Modeling", "SAP", "Power BI"], "min_experience": 2,
        "education_requirement": "Bachelor's in Finance, Economics or Accounting"},
    "ACCOUNTANT": {
        "title": "Staff Accountant", "department": "Accounting",
        "description": "Maintain the general ledger and post journal entries.\n"
                       "Reconcile bank, accounts payable and accounts receivable balances.\n"
                       "Prepare month-end close schedules and tax filings.\n"
                       "Support internal and external audits.",
        "required_skills": ["Accounting", "General Ledger", "Reconciliation", "Accounts Payable", "Taxation"],
        "preferred_skills": ["QuickBooks", "GAAP", "Excel", "Payroll"], "min_experience": 2,
        "education_requirement": "Bachelor's in Accounting"},
    "BUSINESS-DEVELOPMENT": {
        "title": "Business Development Manager", "department": "Growth & Sales",
        "description": "Identify and qualify new client opportunities in target markets.\n"
                       "Negotiate partnership and sales agreements with B2B clients.\n"
                       "Maintain client relationships and pipeline in the CRM.\n"
                       "Research markets and recommend growth strategy.",
        "required_skills": ["Business Development", "Negotiation", "Sales", "Client Relationship", "Market Research"],
        "preferred_skills": ["Salesforce", "CRM", "Strategy"], "min_experience": 3,
        "education_requirement": "Bachelor's in Business, Marketing or Communications"},
}


class DatasetError(ValueError):
    pass


def category_job(db: Session, category: str) -> JobDescription:
    key = category.strip().upper()
    spec = CATEGORY_JOBS.get(key)
    if not spec:
        raise DatasetError(f"No job is defined for dataset category {key}. Available: {', '.join(sorted(CATEGORY_JOBS))}.")
    jd_id = f"JD-KAG-{key.replace('-', '_')}"
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if jd:
        return jd
    jd = JobDescription(jd_id=jd_id, rubric_version="1.0", **spec)
    db.add(jd)
    db.commit()
    db.refresh(jd)
    rubric = get_or_create_rubric(db, jd)
    log_event(db, stage="JD_CREATED", event=f"Job created for dataset category {key}: {jd.title}", agent="DatasetImport",
              input_reference={"jd_id": jd.jd_id, "dataset": DATASET_NAME, "category": key},
              output={"rubric_version": rubric.version}, rubric_version=rubric.version)
    return jd


def read_rows(csv_path: str) -> Iterable[Dict[str, str]]:
    if not os.path.exists(csv_path):
        raise DatasetError(f"Dataset file not found: {csv_path}")
    csv.field_size_limit(1 << 30)
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise DatasetError(f"{csv_path} is not the Kaggle Resume Dataset: missing columns {sorted(missing)}.")
        yield from reader


def import_resumes(db: Session, csv_path: str, categories: List[str], per_category: int,
                   screen: bool = True, actor: str = "DatasetImport") -> Dict[str, int]:
    """Imports up to per_category rows (file order) for each category. Re-running skips rows already imported."""
    from app.services.pipeline_service import screen_candidate

    wanted = [c.strip().upper() for c in categories]
    jobs = {c: category_job(db, c) for c in wanted}
    counts = {c: 0 for c in wanted}
    stats = {"imported": 0, "skipped_existing": 0, "skipped_empty": 0}
    for row in read_rows(csv_path):
        category = (row.get("Category") or "").strip().upper()
        if category not in counts or counts[category] >= per_category:
            if all(v >= per_category for v in counts.values()):
                break
            continue
        external_id = (row.get("ID") or "").strip()
        if not external_id:
            stats["skipped_empty"] += 1
            continue
        if db.query(Candidate).filter(Candidate.source == "dataset_import", Candidate.external_id == external_id).first():
            counts[category] += 1
            stats["skipped_existing"] += 1
            continue
        text = html_resume_to_text(row.get("Resume_html") or "") or (row.get("Resume_str") or "").strip()
        if len(text) < 50:
            stats["skipped_empty"] += 1
            continue
        jd = jobs[category]
        meta = extract_preliminary_metadata(text, list(jd.required_skills or []) + list(jd.preferred_skills or []))
        cand = Candidate(
            name=f"Kaggle resume #{external_id}", email=f"kaggle-{external_id}@dataset.invalid",
            source="dataset_import", external_id=external_id, dataset_category=category, cohort_tag=None,
            resume_text=text, resume_hash=text_hash(text), resume_profile={**meta["profile"], "format": "dataset_html"},
            skills_extracted=meta["skills"], experience_years=meta["experience_years"], education=meta["education"],
            target_jd_id=jd.jd_id, current_stage="APPLIED")
        db.add(cand)
        db.commit()
        log_event(db, stage="APPLIED", event=f"Imported from {DATASET_NAME}", agent=actor, candidate_id=cand.candidate_id,
                  input_reference={"dataset_id": external_id, "category": category, "jd_id": jd.jd_id},
                  output={"skills_found": len(meta["skills"]), "experience_years": meta["experience_years"]})
        if screen:
            screen_candidate(db, cand, jd, actor=actor)
        counts[category] += 1
        stats["imported"] += 1
    stats["per_category"] = counts
    return stats
