from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.rate_limit import (
    check_login_failures,
    clear_login_failures,
    limit_login_by_ip,
    limit_signup_by_ip,
    record_login_failure,
)
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserPublic
from app.services.user_service import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_signup_by_ip)],
)
async def signup(payload: UserCreate, session: SessionDep) -> UserPublic:
    try:
        user = await create_user(session, payload)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    return UserPublic.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(limit_login_by_ip)],
)
async def login(payload: LoginRequest, session: SessionDep) -> Token:
    # Blocked even with the right password: otherwise guessing could continue.
    check_login_failures(payload.email)

    user = await authenticate_user(session, payload.email, payload.password)
    if user is None:
        record_login_failure(payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    clear_login_failures(payload.email)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )
    return Token(access_token=create_access_token(str(user.id)))