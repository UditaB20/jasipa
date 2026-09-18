from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.auth.security import USERS_DB, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(req: LoginRequest):
    user = USERS_DB.get(req.email)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token = create_access_token(data={"sub": user["email"], "role": user["role"], "name": user["name"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }
    }

@router.get("/me")
def get_me():
    # Return available demo accounts for easy switching
    return {
        "users": [
            {"email": u["email"], "name": u["name"], "role": u["role"]} 
            for u in USERS_DB.values()
        ]
    }
