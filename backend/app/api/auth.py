from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Candidate
from app.auth.security import (
    HR_USERS, CANDIDATE_USERS, verify_password, create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()

    # 1. Check HR accounts
    for hr_email, hr_data in HR_USERS.items():
        if hr_email.lower() == email_clean:
            if verify_password(req.password, hr_data["hashed_password"]):
                token = create_access_token(data={
                    "sub": hr_data["email"],
                    "role": "HR",
                    "name": hr_data["name"]
                })
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "role": "HR",
                    "user": {
                        "email": hr_data["email"],
                        "name": hr_data["name"],
                        "role": "HR"
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

    # 2. Check predefined Candidate demo accounts
    for cand_email, cand_data in CANDIDATE_USERS.items():
        if cand_email.lower() == email_clean:
            if verify_password(req.password, cand_data["hashed_password"]):
                token = create_access_token(data={
                    "sub": cand_data["email"],
                    "role": "CANDIDATE",
                    "name": cand_data["name"],
                    "candidate_id": cand_data["candidate_id"]
                })
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "role": "CANDIDATE",
                    "user": {
                        "email": cand_data["email"],
                        "name": cand_data["name"],
                        "role": "CANDIDATE",
                        "candidate_id": cand_data["candidate_id"]
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

    # 3. Check Candidates table in SQLite database
    db_cand = db.query(Candidate).filter(Candidate.email.ilike(email_clean)).first()
    if db_cand:
        # Default password for all seeded candidates is 'candidate123'
        if req.password == "candidate123":
            token = create_access_token(data={
                "sub": db_cand.email,
                "role": "CANDIDATE",
                "name": db_cand.name,
                "candidate_id": db_cand.candidate_id
            })
            return {
                "access_token": token,
                "token_type": "bearer",
                "role": "CANDIDATE",
                "user": {
                    "email": db_cand.email,
                    "name": db_cand.name,
                    "role": "CANDIDATE",
                    "candidate_id": db_cand.candidate_id
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Account not found. Please check your email or contact HR."
    )

@router.get("/me")
def get_current_user_profile(user: dict = Depends(get_current_user)):
    return user

class HRProfileUpdateRequest(BaseModel):
    name: Optional[str] = None

@router.put("/profile")
def update_hr_profile(payload: HRProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    """
    Updates the HR user's profile display name.
    """
    email = current_user["email"]
    if current_user.get("role") != "HR":
        raise HTTPException(status_code=403, detail="Only HR users can update their profile here.")
    
    updated_name = current_user.get("name")
    if email in HR_USERS and payload.name and payload.name.strip():
        HR_USERS[email]["name"] = payload.name.strip()
        updated_name = payload.name.strip()
    elif payload.name and payload.name.strip():
        updated_name = payload.name.strip()

    return {
        "status": "success",
        "message": "HR profile updated successfully",
        "user": {
            "email": email,
            "name": updated_name,
            "role": "HR"
        }
    }

