"""Import all ORM models so the shared Base metadata is complete."""

from app.db.base import Base
from app.models.user import QueryHistory, User
from app.models.bus_line import BusLine, BusStation, LineStation
from app.models.bus_vehicle import BusVehicle
from app.models.history import EtaPrediction, LoadPrediction, PassengerFlowPrediction, PassengerFlowTrend
from app.models.transit_extra import LocationPoi, LtaBusArrival, MapRoadSegment, TrafficSpeedBand

__all__ = [
    "Base",
    "User",
    "QueryHistory",
    "BusStation",
    "BusLine",
    "LineStation",
    "BusVehicle",
    "EtaPrediction",
    "LoadPrediction",
    "PassengerFlowTrend",
    "PassengerFlowPrediction",
    "LocationPoi",
    "MapRoadSegment",
    "LtaBusArrival",
    "TrafficSpeedBand",
]
