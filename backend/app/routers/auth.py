from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user_schema import UserCreate, UserLogin, UserResponse, UserUpdate, TokenResponse
from ..services.auth_service import register_user, authenticate_user, create_token
from ..middleware.auth import get_current_user
from ..models.user_model import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: UserCreate, db: Session = Depends(get_db)):
    try:
        user = register_user(db, body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    token = create_token(user.id)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    token = create_token(user.id)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.username is not None:
        username = body.username.strip()
        if len(username) < 2:
            raise HTTPException(status_code=400, detail="用户名至少需要 2 个字符")
        exists = db.query(User).filter(User.username == username, User.id != current_user.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="这个用户名已被使用")
        current_user.username = username

    if body.avatar_url is not None:
        avatar_url = body.avatar_url.strip()
        if avatar_url and not (
            avatar_url.startswith("data:image/")
            or avatar_url.startswith("http://")
            or avatar_url.startswith("https://")
        ):
            raise HTTPException(status_code=400, detail="头像需要是图片链接，或通过页面上传图片")
        current_user.avatar_url = avatar_url

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
