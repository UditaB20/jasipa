import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database.session import get_db
from app.database.models import Candidate

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# Predefined HR accounts
HR_USERS = {
    "hr@jasipa.ai": {
        "user_id": "USR_HR_01",
        "email": "hr@jasipa.ai",
        "name": "Sarah Connor",
        "role": "HR",
        "hashed_password": hash_password("admin123")
    },
    "recruiter@jasipa.ai": {
        "user_id": "USR_REC_01",
        "email": "recruiter@jasipa.ai",
        "name": "Sarah Recruiter",
        "role": "HR",
        "hashed_password": hash_password("admin123")
    },
    "reviewer@jasipa.ai": {
        "user_id": "USR_REV_01",
        "email": "reviewer@jasipa.ai",
        "name": "Dr. Alex HumanReviewer",
        "role": "HR",
        "hashed_password": hash_password("reviewer123")
    }
}

# Predefined Candidate demo accounts
CANDIDATE_USERS = {
    "candidate@jasipa.ai": {
        "user_id": "USR_CAND_01",
        "candidate_id": "CAND-001-ELENA",
        "email": "candidate@jasipa.ai",
        "name": "Elena Rostova",
        "role": "CANDIDATE",
        "hashed_password": hash_password("candidate123")
    },
    "student@jasipa.ai": {
        "user_id": "USR_CAND_01",
        "candidate_id": "CAND-001-ELENA",
        "email": "student@jasipa.ai",
        "name": "Elena Rostova",
        "role": "CANDIDATE",
        "hashed_password": hash_password("student123")
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Dict:
    """
    Decodes JWT token and extracts user identity and role.
    If no authorization header is provided, raises 401 Unauthorized.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        name: str = payload.get("name")
        candidate_id: Optional[str] = payload.get("candidate_id")

        if email is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "email": email,
            "role": role,
            "name": name,
            "candidate_id": candidate_id
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(allowed_roles: list[str]):
    """
    Role-based authorization guard.
    """
    def role_checker(current_user: Dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {allowed_roles}, your role: {current_user['role']}"
            )
        return current_user
    return role_checker

def require_hr(current_user: Dict = Depends(get_current_user)):
    """Enforces that the authenticated user is an HR member."""
    if current_user["role"] != "HR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to HR personnel only."
        )
    return current_user

def require_candidate(current_user: Dict = Depends(get_current_user)):
    """Enforces that the authenticated user is a Candidate with a valid candidate_id."""
    if current_user["role"] != "CANDIDATE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to candidate portal."
        )
    if not current_user.get("candidate_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate profile associated with this account."
        )
    return current_user
