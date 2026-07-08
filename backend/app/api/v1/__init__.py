from fastapi import APIRouter
from backend.app.api.v1.user.user_api import router as user_router

router = APIRouter(prefix="/v1")
router.include_router(user_router)