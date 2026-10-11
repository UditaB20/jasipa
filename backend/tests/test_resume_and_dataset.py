"""Resume upload, extraction, section display data, original-file download and Kaggle dataset import."""
import os

import fitz
import pytest

from app.config import settings
from app.services.resume_parser import (
    ResumeFileError, detect_format, extract_structured_profile, extract_text, html_resume_to_text, ordered_sections,
)
from helpers import STRONG_RESUME, make_docx, make_pdf


@pytest.mark.parametrize("name,maker", [("resume.pdf", make_pdf), ("resume.docx", make_docx)])
def test_pdf_and_docx_are_extracted(name, maker):
    """Feature: Resume extraction – PDF and DOCX
    Input: the same resume rendered as PDF and as DOCX
    Expected: parsed; skills, 6 years stated experience, bachelor's degree and project extracted"""
    parsed = extract_text(name, maker(STRONG_RESUME))
    profile = extract_structured_profile(parsed["text"])
    assert parsed["status"] == "PARSED"
    assert {"Python", "SQL", "Algorithms", "Docker"} <= set(profile["skills"])
    assert profile["experience_years"] == 6 and profile["experience_source"] == "stated"
    assert profile["highest_education"] == "Bachelor's Degree"
    assert any("Payments reconciliation" in p for p in profile["projects"])


def test_sections_follow_document_order():
    """Feature: Resume display – section structure
    Input: resume text with Summary, Experience, Education, Projects, Skills headings
    Expected: ordered sections with those titles and their own lines"""
    titles = [s["title"] for s in ordered_sections(STRONG_RESUME)]
    assert titles == [None, "Summary", "Experience", "Education", "Projects", "Skills"]
    assert ordered_sections(STRONG_RESUME)[2]["lines"][0].startswith("Senior Software Engineer")


def test_experience_from_date_ranges_when_not_stated():
    """Feature: Resume extraction – experience from dated roles (MM/YYYY and month names)
    Input: two dated roles without a stated total
    Expected: experience computed from merged date ranges"""
    profile = extract_structured_profile("Experience\nAnalyst, Foo (07/2015 - 06/2018)\nLead, Bar (Mar 2017 - Dec 2019)\n")
    assert profile["experience_source"] == "date_ranges" and 4.0 <= profile["experience_years"] <= 5.0


@pytest.mark.parametrize("name,data,message", [
    ("resume.exe", b"MZ...", "Unsupported file type"),
    ("resume.pdf", b"", "empty"),
    ("resume.pdf", b"PK\x03\x04 not a pdf", "not a valid PDF"),
    ("resume.docx", b"%PDF-1.4 renamed", "not a valid Word"),
    ("resume.docx", b"PK\x03\x04garbage", "not a valid Word"),
])
def test_invalid_files_are_rejected(name, data, message):
    """Feature: Resume upload – file validation (negative)
    Input: wrong extension, empty file, renamed ZIP/PDF, corrupt DOCX
    Expected: ResumeFileError with a user-readable message"""
    with pytest.raises(ResumeFileError, match=message):
        detect_format(name, data)


def test_image_only_pdf_is_rejected():
    """Feature: Resume upload – scanned PDF (negative)
    Input: PDF page without a text layer
    Expected: 'No readable text' error"""
    doc = fitz.open()
    doc.new_page()
    with pytest.raises(ResumeFileError, match="No readable text"):
        extract_text("scan.pdf", doc.tobytes())


def test_hr_upload_creates_candidate_screens_and_downloads_original(client, hr_headers, software_job, db):
    """Feature: Resume upload (HR) and original-file download
    Input: DOCX with a path-traversal filename, uploaded for a new candidate on the software job
    Expected: candidate created (source hr_upload), screened, stored under a random name, original bytes downloadable, sections returned"""
    files = {"file": ("../../etc/passwd.docx", make_docx(STRONG_RESUME),
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"name": "Jordan Rivera", "email": "Jordan.Rivera@Example.com", "target_jd_id": software_job["jd_id"], "cohort_tag": "Cohort_Alpha"}
    response = client.post("/api/candidates/upload-resume", files=files, data=data, headers=hr_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "jordan.rivera@example.com" and body["source"] == "hr_upload"
    assert body["current_stage"] == "RESUME_SCREENED" and "Python" in body["skills_extracted"]
    assert all(".." not in name and "passwd" not in name for name in os.listdir(settings.UPLOAD_DIR))
    detail = client.get(f"/api/candidates/{body['candidate_id']}", headers=hr_headers).json()
    assert detail["has_original_file"] is True and [s["title"] for s in detail["resume_sections"]][1] == "Summary"
    download = client.get(f"/api/candidates/{body['candidate_id']}/resume", headers=hr_headers)
    assert download.status_code == 200 and download.content == files["file"][1]


def test_upload_errors_return_clear_messages(client, hr_headers):
    """Feature: Resume upload – error handling (negative, boundary)
    Input: fake PDF; PDF larger than MAX_RESUME_BYTES
    Expected: 422 with 'not a valid PDF' and 'larger than' messages"""
    response = client.post("/api/candidates/upload-resume", files={"file": ("resume.pdf", b"not really a pdf", "application/pdf")},
                           data={"name": "Bad File", "email": "bad.file@example.com"}, headers=hr_headers)
    assert response.status_code == 422 and "not a valid PDF" in response.json()["detail"]
    big = {"file": ("big.pdf", b"%PDF" + b"0" * (settings.MAX_RESUME_BYTES + 10), "application/pdf")}
    response = client.post("/api/candidates/upload-resume", files=big, data={"name": "Big File", "email": "big.file@example.com"}, headers=hr_headers)
    assert response.status_code == 422 and "larger than" in response.json()["detail"]


def test_candidate_uploads_downloads_and_applies(client, new_candidate, software_job):
    """Feature: Candidate portal – resume upload, original download, apply
    Input: new portal account; apply without resume; upload PDF; download it; apply; apply again to another job
    Expected: 422 before upload; download returns identical bytes; application screened; second application 409"""
    headers, _ = new_candidate("Robin Candidate")
    assert client.get("/api/candidate/resume", headers=headers).status_code == 404
    blocked = client.post("/api/candidate/apply", json={"jd_id": software_job["jd_id"]}, headers=headers)
    assert blocked.status_code == 422 and "Upload your resume" in blocked.json()["detail"]
    pdf = make_pdf(STRONG_RESUME)
    upload = client.post("/api/candidate/upload-resume", files={"file": ("cv.pdf", pdf, "application/pdf")}, headers=headers)
    assert upload.status_code == 200 and upload.json()["profile"]["has_original_file"] is True
    download = client.get("/api/candidate/resume", headers=headers)
    assert download.status_code == 200 and download.content == pdf
    applied = client.post("/api/candidate/apply", json={"jd_id": software_job["jd_id"]}, headers=headers)
    assert applied.status_code == 200 and applied.json()["current_stage"] == "RESUME_SCREENED"
    assert client.post("/api/candidate/apply", json={"jd_id": "JD-KAG-HR"}, headers=headers).status_code == 409


def test_kaggle_html_is_converted_with_sections():
    """Feature: Dataset import – HTML to structured text
    Input: Resume_html fragment with sectiontitle divs and list items
    Expected: headings on their own lines, bullets preserved, sections detected"""
    html = ('<div class="section"><div class="heading"><div class="sectiontitle"> Summary</div></div>'
            '<div class="paragraph"><span>Ten years in payroll.</span></div></div>'
            '<div class="section"><div class="heading"><div class="sectiontitle"> Skills</div></div><ul><li>Payroll</li><li>Excel</li></ul></div>')
    text = html_resume_to_text(html)
    assert "Summary\nTen years in payroll." in text and "• Payroll" in text
    assert [s["title"] for s in ordered_sections(text)] == ["Summary", "Skills"]


def test_seed_imports_only_kaggle_records(seeded_database, db):
    """Feature: Dataset replacement – seed contents
    Input: python scripts/seed_data.py (per_category=4, demo accounts on)
    Expected: 24 dataset_import records across 6 categories; no synthetic candidates with scores/assessments; only 2 empty portal logins"""
    from app.database.models import Assessment, Candidate, HumanReview
    imported = db.query(Candidate).filter(Candidate.source == "dataset_import").all()
    assert seeded_database["imported"] == 24 and len(imported) == 24
    assert {c.dataset_category for c in imported} == set(seeded_database["per_category"])
    assert all(c.external_id and c.email.endswith("@dataset.invalid") and c.name == f"Kaggle resume #{c.external_id}" for c in imported)
    demo = db.query(Candidate).filter(Candidate.email.in_(["student@jasipa.ai", "candidate@jasipa.ai"])).all()
    assert all(c.resume_text is None and c.current_stage == "REGISTERED" for c in demo)
    assert db.query(Assessment).filter(Assessment.candidate_id.in_([c.candidate_id for c in imported])).count() == 0
    assert db.query(HumanReview).filter(HumanReview.candidate_id.in_([c.candidate_id for c in imported])).count() == 0


def test_imported_text_matches_dataset_row_and_is_screened(db):
    """Feature: Dataset replacement – consistency with the source data
    Input: one imported record and its row in Resume.csv
    Expected: stored text equals the HTML-derived text for that row ID; a screening result exists for its category job"""
    from app.database.models import Candidate, ScreeningResult
    from app.services.dataset_import import read_rows
    cand = db.query(Candidate).filter(Candidate.source == "dataset_import", Candidate.dataset_category == "ENGINEERING").first()
    row = next(r for r in read_rows(os.path.join(os.path.dirname(__file__), "..", "..", "Resume.csv")) if r["ID"] == cand.external_id)
    assert cand.resume_text == html_resume_to_text(row["Resume_html"]) and row["Category"] == cand.dataset_category
    screening = db.query(ScreeningResult).filter(ScreeningResult.candidate_id == cand.candidate_id).one()
    assert screening.jd_id == cand.target_jd_id and cand.current_stage == "RESUME_SCREENED"


def test_import_is_idempotent_and_rejects_wrong_files(db, tmp_path):
    """Feature: Dataset import – re-runs and invalid input (negative)
    Input: importing the same categories again; a CSV without the dataset columns; an unknown category
    Expected: no duplicates; clear DatasetError messages"""
    from app.database.models import Candidate
    from app.services.dataset_import import DatasetError, import_resumes
    csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "Resume.csv")
    before = db.query(Candidate).filter(Candidate.source == "dataset_import").count()
    stats = import_resumes(db, csv_path, ["HR"], 4, screen=False)
    assert stats["imported"] == 0 and stats["skipped_existing"] == 4
    assert db.query(Candidate).filter(Candidate.source == "dataset_import").count() == before
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(DatasetError, match="not the Kaggle Resume Dataset"):
        list(import_resumes(db, str(bad), ["HR"], 1).items())
    with pytest.raises(DatasetError, match="No job is defined"):
        import_resumes(db, csv_path, ["CHEF"], 1)


def test_dataset_records_cannot_be_overwritten_by_uploads(client, hr_headers, db):
    """Feature: Dataset vs real candidates – provenance protection (negative)
    Input: HR upload using the placeholder email of an imported record
    Expected: 409; the dataset record is unchanged"""
    from app.database.models import Candidate
    cand = db.query(Candidate).filter(Candidate.source == "dataset_import").first()
    response = client.post("/api/candidates/upload-resume", headers=hr_headers, data={"name": "X Y", "email": cand.email},
                           files={"file": ("cv.pdf", make_pdf(STRONG_RESUME), "application/pdf")})
    assert response.status_code == 409 and "dataset" in response.json()["detail"]
