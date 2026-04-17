"""API v1 router."""

from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.cv import router as cv_router
from src.api.v1.interviews import router as interviews_router
from src.api.v1.jd import router as jd_router
from src.api.v1.jobs import router as jobs_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(jd_router)
api_router.include_router(cv_router)
api_router.include_router(jobs_router)
api_router.include_router(interviews_router)
