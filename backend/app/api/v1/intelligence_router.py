"""Single router exported for integration into team A's shared application."""

from fastapi import APIRouter

from backend.app.api.v1.ai import router as ai_router
from backend.app.api.v1.eta import router as eta_router
from backend.app.api.v1.load import router as load_router
from backend.app.api.v1.recommend import router as recommend_router

router = APIRouter()
router.include_router(eta_router)
router.include_router(load_router)
router.include_router(recommend_router)
router.include_router(ai_router)
