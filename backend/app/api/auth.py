import re
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Candidate
from app.auth.security import HR_USERS, verify_password, hash_password, create_access_token, get_current_user
from app.services.audit_service import log_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
INVALID_CREDENTIALS = "Incorrect email or password."


def normalize_email(value: str) -> str:
    value = (value or "").strip().lower()
    if not EMAIL_PATTERN.match(value) or len(value) > 254:
        raise ValueError("Enter a valid email address.")
    return value


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        return normalize_email(value)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Name is required.")
        return value


def _candidate_session(cand: Candidate) -> dict:
    token = create_access_token(data={"sub": cand.email, "uid": cand.candidate_id, "role": "CANDIDATE",
                                      "name": cand.name, "candidate_id": cand.candidate_id})
    return {"access_token": token, "token_type": "bearer", "role": "CANDIDATE",
            "user": {"email": cand.email, "name": cand.name, "role": "CANDIDATE", "candidate_id": cand.candidate_id}}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()

    hr = HR_USERS.get(email)
    if hr:
        if not verify_password(req.password, hr["hashed_password"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
        token = create_access_token(data={"sub": hr["email"], "uid": hr["user_id"], "role": "HR", "name": hr["name"]})
        return {"access_token": token, "token_type": "bearer", "role": "HR",
                "user": {"email": hr["email"], "name": hr["name"], "role": "HR", "user_id": hr["user_id"]}}

    cand = db.query(Candidate).filter(Candidate.email == email).first()
    # Candidates created by HR (or imported) have no portal password and cannot sign in.
    if not cand or not verify_password(req.password, cand.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
    return _candidate_session(cand)


@router.post("/register", status_code=201)
def register_candidate(req: RegisterRequest, db: Session = Depends(get_db)):
    """Creates a candidate portal account. Existing records are never claimed by email alone."""
    if req.email in HR_USERS or db.query(Candidate).filter(Candidate.email == req.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")
    cand = Candidate(name=req.name, email=req.email, password_hash=hash_password(req.password),
                     current_stage="REGISTERED", skills_extracted=[], resume_profile={})
    db.add(cand)
    db.commit()
    db.refresh(cand)
    log_event(db, stage="REGISTERED", event="Candidate portal account created", agent="CandidatePortal",
              candidate_id=cand.candidate_id, model_name="n/a")
    return _candidate_session(cand)


@router.get("/me")
def get_current_user_profile(user: dict = Depends(get_current_user)):
    return user
