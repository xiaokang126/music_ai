from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.user import UserCreate, UserLogin, TokenResponse
from ..services.auth_service import register_user, authenticate_user, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    user = register_user(db, data.username, data.password)
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "user": {"id": user.id, "username": user.username, "avatar": user.avatar, "created_at": user.created_at}
    }


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.username, data.password)
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "user": {"id": user.id, "username": user.username, "avatar": user.avatar, "created_at": user.created_at}
    }
