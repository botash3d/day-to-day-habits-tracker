from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)
