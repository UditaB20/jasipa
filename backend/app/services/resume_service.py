"""Stores an uploaded resume privately and updates the candidate record from its extracted content."""
import os
import uuid
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import Candidate, JobDescription
from app.services.resume_parser import ResumeFileError, extract_text, extract_preliminary_metadata, text_hash


def _storage_path(storage_key: str) -> str:
    return os.path.join(settings.UPLOAD_DIR, storage_key)


def ingest_resume(db: Session, candidate: Candidate, filename: str, data: bytes) -> Dict[str, Any]:
    """Validates, parses and stores a resume. Raises ResumeFileError with a user-safe message."""
    if len(data) > settings.MAX_RESUME_BYTES:
        raise ResumeFileError(f"The file is larger than {settings.MAX_RESUME_BYTES // (1024 * 1024)} MB.")
    parsed = extract_text(filename, data)

    jd_skills = []
    if candidate.target_jd_id:
        jd = db.query(JobDescription).filter(JobDescription.jd_id == candidate.target_jd_id).first()
        if jd:
            jd_skills = list(jd.required_skills or []) + list(jd.preferred_skills or [])
    meta = extract_preliminary_metadata(parsed["text"], jd_skills)

    # Random storage key: the client-supplied name never becomes part of a filesystem path.
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    storage_key = f"{uuid.uuid4().hex}.{parsed['format']}"
    with open(_storage_path(storage_key), "wb") as handle:
        handle.write(data)
    previous = candidate.resume_file_path
    if previous and os.path.basename(previous) == previous and os.path.exists(_storage_path(previous)):
        try:
            os.remove(_storage_path(previous))
        except OSError:
            pass

    candidate.resume_text = parsed["text"]
    candidate.resume_hash = text_hash(parsed["text"])
    candidate.resume_file_path = storage_key
    candidate.resume_original_filename = os.path.basename(filename or "resume")[:200]
    candidate.skills_extracted = meta["skills"]
    candidate.experience_years = meta["experience_years"]
    candidate.education = meta["education"]
    candidate.resume_profile = {**meta["profile"], "format": parsed["format"],
                                "extraction_confidence": parsed["confidence"], "parse_status": parsed["status"]}
    if parsed["status"] == "MANUAL_REVIEW_REQUIRED" and candidate.current_stage in (None, "REGISTERED", "APPLIED"):
        candidate.current_stage = "MANUAL_REVIEW_REQUIRED"
    return {"format": parsed["format"], "confidence": parsed["confidence"], "status": parsed["status"],
            "profile": candidate.resume_profile}


def resume_file_path(candidate: Candidate) -> str | None:
    key = candidate.resume_file_path
    if not key or os.path.basename(key) != key:
        return None
    path = _storage_path(key)
    return path if os.path.exists(path) else None
