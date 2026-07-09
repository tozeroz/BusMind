from fastapi import APIRouter
from app.api.v1.user.user_api import router as user_router
from app.api.v1.line import line_router, station_router
from app.api.v1.vehicle import vehicle_router
from app.api.v1.map import map_router
from app.api.v1.history import history_router

router = APIRouter(prefix="/v1")
router.include_router(user_router)
router.include_router(line_router)
router.include_router(station_router)
router.include_router(vehicle_router)
router.include_router(map_router)
router.include_router(history_router)