"""Resume upload: PDF/DOCX parsing, structured extraction, validation and storage safety."""
import io
import os

import docx
import fitz
import pytest

from app.config import settings
from app.services.resume_parser import ResumeFileError, detect_format, extract_structured_profile, extract_text

RESUME = """Jordan Rivera
Summary
Backend engineer with 5 years of experience building Python and FastAPI services.
Experience
Software Engineer, Acme Corp (Jan 2021 - Present)
Built REST APIs with FastAPI, PostgreSQL and Docker.
Junior Developer, Initech (2019 - 2020)
Education
B.Tech in Computer Science, National Institute of Technology, 2019
Projects
Payments reconciliation service processing 2M transactions per day.
Skills
Python, FastAPI, SQL, Docker, React, C++
"""


def make_pdf(text=RESUME):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


def make_docx(text=RESUME):
    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize("name,maker", [("resume.pdf", make_pdf), ("resume.docx", make_docx)])
def test_pdf_and_docx_are_extracted(name, maker):
    parsed = extract_text(name, maker())
    profile = extract_structured_profile(parsed["text"])
    assert parsed["status"] == "PARSED"
    assert {"Python", "FastAPI", "Docker", "React", "C++"} <= set(profile["skills"])
    assert profile["experience_years"] == 5 and profile["experience_source"] == "stated"
    assert profile["highest_education"] == "Bachelor's Degree"
    assert any("Payments reconciliation" in p for p in profile["projects"])


def test_experience_from_date_ranges_when_not_stated():
    profile = extract_structured_profile("Experience\nAnalyst, Foo (2015 - 2018)\nLead, Bar (Mar 2017 - Dec 2019)\n")
    assert profile["experience_source"] == "date_ranges" and 4.0 <= profile["experience_years"] <= 5.0


@pytest.mark.parametrize("name,data,message", [
    ("resume.exe", b"MZ...", "Unsupported file type"),
    ("resume.pdf", b"", "empty"),
    ("resume.pdf", b"PK\x03\x04 not a pdf", "not a valid PDF"),
    ("resume.docx", b"%PDF-1.4 renamed", "not a valid Word"),
    ("resume.docx", b"PK\x03\x04garbage", "not a valid Word"),
])
def test_invalid_files_are_rejected(name, data, message):
    with pytest.raises(ResumeFileError, match=message):
        detect_format(name, data)


def test_image_only_pdf_is_rejected():
    doc = fitz.open()
    doc.new_page()
    with pytest.raises(ResumeFileError, match="No readable text"):
        extract_text("scan.pdf", doc.tobytes())


def test_hr_upload_creates_candidate_and_screens(client, hr_headers):
    files = {"file": ("../../etc/passwd.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"name": "Jordan Rivera", "email": "Jordan.Rivera@Example.com", "target_jd_id": "JD-SWE-101", "cohort_tag": "Cohort_Alpha"}
    response = client.post("/api/candidates/upload-resume", files=files, data=data, headers=hr_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "jordan.rivera@example.com"
    assert body["current_stage"] == "RESUME_SCREENED"
    assert "Python" in body["skills_extracted"] and body["resume_profile"]["format"] == "docx"
    stored = os.listdir(settings.UPLOAD_DIR)
    assert all(".." not in name and "passwd" not in name for name in stored)
    download = client.get(f"/api/candidates/{body['candidate_id']}/resume", headers=hr_headers)
    assert download.status_code == 200 and download.content.startswith(b"PK")


def test_upload_errors_return_clear_messages(client, hr_headers):
    files = {"file": ("resume.pdf", b"not really a pdf", "application/pdf")}
    response = client.post("/api/candidates/upload-resume", files=files,
                           data={"name": "Bad File", "email": "bad.file@example.com"}, headers=hr_headers)
    assert response.status_code == 422 and "not a valid PDF" in response.json()["detail"]
    big = {"file": ("big.pdf", b"%PDF" + b"0" * (settings.MAX_RESUME_BYTES + 10), "application/pdf")}
    response = client.post("/api/candidates/upload-resume", files=big,
                           data={"name": "Big File", "email": "big.file@example.com"}, headers=hr_headers)
    assert response.status_code == 422 and "larger than" in response.json()["detail"]


def test_candidate_uploads_resume_then_applies(client, register_candidate):
    headers, _ = register_candidate("Robin Candidate")
    blocked = client.post("/api/candidate/apply", json={"jd_id": "JD-SWE-101"}, headers=headers)
    assert blocked.status_code == 422 and "Upload your resume" in blocked.json()["detail"]
    upload = client.post("/api/candidate/upload-resume", files={"file": ("cv.pdf", make_pdf(), "application/pdf")}, headers=headers)
    assert upload.status_code == 200, upload.text
    assert upload.json()["profile"]["resume_profile"]["experience_years"] == 5
    applied = client.post("/api/candidate/apply", json={"jd_id": "JD-SWE-101"}, headers=headers)
    assert applied.status_code == 200 and applied.json()["current_stage"] == "RESUME_SCREENED"
    again = client.post("/api/candidate/apply", json={"jd_id": "JD-MLE-202"}, headers=headers)
    assert again.status_code == 409
