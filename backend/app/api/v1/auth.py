from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserPublic
from app.services.user_service import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, session: SessionDep) -> UserPublic:
    try:
        user = await create_user(session, payload)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    return UserPublic.model_validate(user)


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, session: SessionDep) -> Token:
    user = await authenticate_user(session, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )
    return Token(access_token=create_access_token(str(user.id)))
