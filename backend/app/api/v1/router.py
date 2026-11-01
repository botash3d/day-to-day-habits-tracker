from fastapi import APIRouter

from app.api.v1 import auth, build, dsa, learn, tasks, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dsa.router)
api_router.include_router(tasks.router)
api_router.include_router(learn.router)
api_router.include_router(build.router)