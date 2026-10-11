"""Resume file validation, text extraction (PDF/DOCX) and structured, non-inferential field extraction.

Extraction only records what the document states: skills that appear verbatim, degree lines,
explicit experience statements or dated roles, and lines under a "Projects" heading. Nothing is
guessed, and demographic details are never extracted.
"""
import hashlib
import io
import re
import zipfile
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import fitz  # PyMuPDF

SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx"}

SKILL_TAXONOMY = [
    # Languages & runtimes
    "Python", "Java", "C++", "C#", "C", "Go", "Rust", "Kotlin", "Swift", "Scala", "R", "MATLAB", "PHP", "Ruby",
    "JavaScript", "TypeScript", "Node.js", "SQL", "Bash", "HTML5", "CSS3",
    # Frameworks & libraries
    "React", "Angular", "Vue", "Next.js", "Django", "Flask", "FastAPI", "Spring Boot", ".NET", "Express",
    "TensorFlow", "PyTorch", "Scikit-Learn", "Pandas", "NumPy", "Spark", "Hadoop", "Airflow", "Tailwind",
    # Data & infrastructure
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Kafka", "Docker", "Kubernetes", "Terraform",
    "AWS", "Azure", "GCP", "Linux", "Git", "CI/CD", "REST API", "GraphQL", "Microservices", "System Design",
    # Disciplines
    "Data Structures", "Algorithms", "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Data Analysis", "Statistics", "Power BI", "Tableau", "Excel", "Agile", "Scrum", "Project Management",
    "Networking", "Cybersecurity", "Troubleshooting", "Accounting", "Financial Modeling", "Auditing",
    "Taxation", "Recruitment", "Employee Relations", "Talent Acquisition", "Payroll", "Compliance",
    "Digital Marketing", "SEO", "Sales", "Customer Service", "Communication", "Leadership",
]

_SECTION_HEADINGS = {
    "education": ("education", "academic background", "qualifications", "academics"),
    "experience": ("experience", "work experience", "professional experience", "employment history", "work history"),
    "projects": ("projects", "personal projects", "academic projects", "key projects", "selected projects"),
    "skills": ("skills", "technical skills", "core competencies", "competencies"),
}
_DEGREE_PATTERN = re.compile(
    r"\b(ph\.?\s?d|doctorate|master'?s?|m\.?\s?sc|m\.?\s?tech|m\.?\s?s\.|mba|m\.?\s?e\.|bachelor'?s?|b\.?\s?sc|"
    r"b\.?\s?tech|b\.?\s?e\.|b\.?\s?s\.|b\.?\s?a\.|associate'?s?|diploma)\b", re.IGNORECASE)
_MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
_DATE_RANGE = re.compile(
    rf"(?:(?P<m1>{_MONTHS})[a-z]*\.?\s+|(?P<n1>0?[1-9]|1[0-2])/)?(?P<y1>(?:19|20)\d{{2}})\s*(?:-|–|—|to)\s*"
    rf"(?:(?:(?P<m2>{_MONTHS})[a-z]*\.?\s+|(?P<n2>0?[1-9]|1[0-2])/)?(?P<y2>(?:19|20)\d{{2}})|(?P<present>present|current|now|date))",
    re.IGNORECASE)


class ResumeFileError(ValueError):
    """Raised for files that are not acceptable resumes; the message is safe to show users."""


def detect_format(filename: str, data: bytes) -> str:
    """Validates extension and file signature together so a renamed file is rejected."""
    name = (filename or "").lower().strip()
    extension = next((ext for ext in SUPPORTED_EXTENSIONS if name.endswith(ext)), None)
    if extension is None:
        raise ResumeFileError("Unsupported file type. Upload a PDF or Word (.docx) resume.")
    if not data:
        raise ResumeFileError("The uploaded file is empty.")
    kind = SUPPORTED_EXTENSIONS[extension]
    if kind == "pdf" and not data.lstrip()[:5].startswith(b"%PDF"):
        raise ResumeFileError("This file is not a valid PDF document.")
    if kind == "docx":
        if not data.startswith(b"PK"):
            raise ResumeFileError("This file is not a valid Word (.docx) document.")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise ResumeFileError("This file is not a valid Word (.docx) document.")
        except zipfile.BadZipFile:
            raise ResumeFileError("This file is not a valid Word (.docx) document.")
    return kind


def _extract_pdf(data: bytes) -> str:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        raise ResumeFileError("The PDF could not be opened. It may be corrupted.")
    try:
        if doc.needs_pass:
            raise ResumeFileError("The PDF is password-protected. Upload an unlocked copy.")
        if doc.page_count > 20:
            raise ResumeFileError("The PDF has more than 20 pages. Upload a resume of 20 pages or fewer.")
        return "\n".join(page.get_text() for page in doc).strip()
    finally:
        doc.close()


def _extract_docx(data: bytes) -> str:
    try:
        import docx  # python-docx
        document = docx.Document(io.BytesIO(data))
    except Exception:
        raise ResumeFileError("The Word document could not be opened. It may be corrupted.")
    lines = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells if cell.text.strip()))
    return "\n".join(line for line in lines if line is not None).strip()


def extract_text(filename: str, data: bytes) -> Dict[str, Any]:
    kind = detect_format(filename, data)
    text = _extract_pdf(data) if kind == "pdf" else _extract_docx(data)
    text = re.sub(r"[ \t]+", " ", text.replace("\x00", ""))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 50:
        raise ResumeFileError("No readable text was found. If this is a scanned image, upload a text-based PDF or DOCX.")
    printable = sum(1 for ch in text if ch.isalnum() or ch.isspace() or ch in ".,;:-()/+#&@'%")
    confidence = round(printable / len(text), 2)
    return {"format": kind, "text": text, "confidence": confidence,
            "status": "PARSED" if confidence >= 0.65 else "MANUAL_REVIEW_REQUIRED"}


def extract_text_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Backwards-compatible wrapper used by older call sites and scripts."""
    try:
        result = extract_text("resume.pdf", pdf_bytes)
        return {"success": True, **result, "message": "Text extracted successfully."}
    except ResumeFileError as exc:
        return {"success": False, "text": "", "confidence": 0.0, "status": "MANUAL_REVIEW_REQUIRED", "message": str(exc)}


def _split_sections(text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {"_preamble": []}
    current = "_preamble"
    for raw in text.splitlines():
        line = raw.strip(" •·-*\t")
        if not line:
            continue
        heading = line.lower().rstrip(":").strip()
        matched = next((key for key, names in _SECTION_HEADINGS.items() if heading in names), None)
        if matched and len(line) <= 40:
            current = matched
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def find_skills(text: str, extra_skills: Iterable[str] = ()) -> List[str]:
    """Skills that appear verbatim (word-bounded) in the text, including any job-specific skills."""
    lowered = text.lower()
    found: List[str] = []
    seen = set()
    for skill in list(SKILL_TAXONOMY) + [s for s in extra_skills if s]:
        key = skill.lower().strip()
        if not key or key in seen:
            continue
        # Single letters (C, R) are too ambiguous to match outside an explicit skills list.
        if len(key) == 1:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", lowered):
            found.append(skill)
            seen.add(key)
    return found


def _experience_from_ranges(lines: List[str]) -> tuple[float, List[Dict[str, Any]]]:
    now = datetime.utcnow()
    months_index = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
    intervals = []
    entries = []
    for line in lines:
        for match in _DATE_RANGE.finditer(line):
            start_month = int(match.group("n1")) if match.group("n1") else months_index.get((match.group("m1") or "jan")[:3].lower(), 1)
            start = datetime(int(match.group("y1")), start_month, 1)
            if match.group("present"):
                end = now
            else:
                end_month = int(match.group("n2")) if match.group("n2") else months_index.get((match.group("m2") or "dec")[:3].lower(), 12)
                end = datetime(int(match.group("y2")), end_month, 1)
            if end < start or start > now:
                continue
            intervals.append((start, min(end, now)))
            entries.append({"summary": line[:160], "start": start.strftime("%Y-%m"),
                            "end": "present" if match.group("present") else end.strftime("%Y-%m")})
    # Merge overlapping roles so concurrent jobs are not double counted.
    intervals.sort()
    merged: List[List[datetime]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    months = sum((end.year - start.year) * 12 + (end.month - start.month) for start, end in merged)
    return round(months / 12, 1), entries


def extract_structured_profile(text: str, extra_skills: Iterable[str] = ()) -> Dict[str, Any]:
    sections = _split_sections(text)
    all_lines = [line for lines in sections.values() for line in lines]

    education_lines = sections.get("education") or [l for l in all_lines if _DEGREE_PATTERN.search(l)]
    education = [line[:200] for line in education_lines if _DEGREE_PATTERN.search(line) or re.search(r"university|college|institute", line, re.I)][:6]

    stated_years = [float(x) for x in re.findall(
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:\w+\s+){0,3}?experience", text.lower())]
    stated_years = [y for y in stated_years if 0 < y <= 50]
    range_years, roles = _experience_from_ranges(sections.get("experience") or all_lines)
    if stated_years:
        experience_years, experience_source = max(stated_years), "stated"
    elif range_years:
        experience_years, experience_source = range_years, "date_ranges"
    else:
        experience_years, experience_source = 0.0, "not_found"

    projects = [line[:200] for line in sections.get("projects", []) if len(line) > 12][:8]

    return {
        "skills": find_skills(text, extra_skills),
        "education": education,
        "highest_education": _highest_degree(" ".join(education) or text),
        "experience_years": experience_years,
        "experience_source": experience_source,
        "experience_entries": roles[:10],
        "projects": projects,
    }


def _highest_degree(text: str) -> str:
    lowered = text.lower()
    if re.search(r"ph\.?\s?d|doctorate", lowered):
        return "Doctorate"
    if re.search(r"master|m\.?\s?sc\b|m\.?\s?tech|\bmba\b|m\.s\.", lowered):
        return "Master's Degree"
    if re.search(r"bachelor|b\.?\s?sc\b|b\.?\s?tech|b\.e\.|b\.s\.|b\.a\.", lowered):
        return "Bachelor's Degree"
    if re.search(r"associate|diploma", lowered):
        return "Associate/Diploma"
    return "Not specified"


def extract_preliminary_metadata(text: str, extra_skills: Iterable[str] = ()) -> Dict[str, Any]:
    """Compact metadata used to populate candidate columns."""
    profile = extract_structured_profile(text or "", extra_skills)
    return {"skills": profile["skills"], "experience_years": profile["experience_years"],
            "education": profile["highest_education"], "profile": profile}


def text_hash(text: Optional[str]) -> Optional[str]:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None
