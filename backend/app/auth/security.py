import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# Predefined demo accounts
USERS_DB = {
    "recruiter@jasipa.ai": {
        "user_id": "USR_REC_01",
        "email": "recruiter@jasipa.ai",
        "name": "Sarah Recruiter",
        "role": "HR_ADMIN",
        "hashed_password": hash_password("admin123")
    },
    "reviewer@jasipa.ai": {
        "user_id": "USR_REV_01",
        "email": "reviewer@jasipa.ai",
        "name": "Dr. Alex HumanReviewer",
        "role": "REVIEWER",
        "hashed_password": hash_password("reviewer123")
    },
    "student@jasipa.ai": {
        "user_id": "USR_STU_01",
        "email": "student@jasipa.ai",
        "name": "Elena Rostova (Student/Candidate)",
        "role": "STUDENT",
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
    if not credentials:
        # Default to demo HR Admin if no header provided in development
        return USERS_DB["recruiter@jasipa.ai"]
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None or email not in USERS_DB:
            return USERS_DB["recruiter@jasipa.ai"]
        return USERS_DB[email]
    except JWTError:
        return USERS_DB["recruiter@jasipa.ai"]

def require_role(allowed_roles: list[str]):
    def role_checker(current_user: Dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role {current_user['role']}"
            )
        return current_user
    return role_checker
