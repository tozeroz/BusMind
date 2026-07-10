from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.intelligence_router import router as intelligence_router
from app.api.v1.user.user_api import router as user_router
from app.core.api_response import ApiResponse, success_response
from app.api.v1.line import line_router, station_router, bus_lines_router, bus_stations_router
from app.api.v1.vehicle import vehicle_router
from app.api.v1.map import map_router
from app.api.v1.history import history_router
from app.api.v1.locations import locations_router

router = APIRouter(prefix="/v1")


@router.get("/", response_model=ApiResponse, tags=["Health"])
async def api_v1_health() -> ApiResponse:
    return success_response({"status": "ok", "version": "v1"}, "req_health")


router.include_router(user_router)
router.include_router(admin_router)
router.include_router(intelligence_router)
router.include_router(line_router)
router.include_router(station_router)
router.include_router(bus_lines_router)
router.include_router(bus_stations_router)
router.include_router(vehicle_router)
router.include_router(map_router)
router.include_router(history_router)
router.include_router(locations_router)
