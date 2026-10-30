from fastapi import APIRouter

from app.api.v1 import auth, dsa, tasks, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dsa.router)
api_router.include_router(tasks.router)