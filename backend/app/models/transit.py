"""Legacy compatibility re-exports for the old transit model module."""

from app.models.bus_line import Base, BusLine, BusStation, LineStation
from app.models.bus_vehicle import BusVehicle
from app.models.history import (
    EtaPrediction as BusEtaStatus,
    LoadPrediction as BusLoadStatus,
    PassengerFlowPrediction,
    PassengerFlowTrend,
)
from app.models.transit_extra import LtaBusArrival, MapRoadSegment, TrafficSpeedBand

__all__ = [
    "Base",
    "BusStation",
    "BusLine",
    "LineStation",
    "BusVehicle",
    "BusEtaStatus",
    "BusLoadStatus",
    "PassengerFlowTrend",
    "PassengerFlowPrediction",
    "MapRoadSegment",
    "LtaBusArrival",
    "TrafficSpeedBand",
]
