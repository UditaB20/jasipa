from datetime import datetime, timedelta
from typing import Optional, Dict
import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# Demo HR accounts. Each has a distinct user_id so four-eyes sign-off can tell reviewers apart.
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
        "name": "Sam Recruiter",
        "role": "HR",
        "hashed_password": hash_password("admin123")
    },
    "reviewer@jasipa.ai": {
        "user_id": "USR_REV_01",
        "email": "reviewer@jasipa.ai",
        "name": "Alex Reviewer",
        "role": "HR",
        "hashed_password": hash_password("reviewer123")
    }
}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Dict:
    """Decodes the bearer token and returns the caller's identity and role."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload.get("sub")
    role = payload.get("role")
    if email is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "email": email,
        "role": str(role).upper(),
        "name": payload.get("name"),
        "user_id": payload.get("uid") or email,
        "candidate_id": payload.get("candidate_id"),
    }


def require_hr(current_user: Dict = Depends(get_current_user)):
    """Enforces that the authenticated user is an HR member."""
    if current_user.get("role") != "HR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to HR personnel only.")
    return current_user


def require_candidate(current_user: Dict = Depends(get_current_user)):
    """Enforces that the authenticated user is a candidate linked to a candidate record."""
    if current_user.get("role") != "CANDIDATE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to candidate portal.")
    if not current_user.get("candidate_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No candidate profile associated with this account.")
    return current_user
