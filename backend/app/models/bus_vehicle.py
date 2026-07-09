from sqlalchemy import Column, BIGINT, Integer, String, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.bus_line import Base


class BusVehicle(Base):
    __tablename__ = "bus_vehicles"

    vehicle_id = Column(BIGINT, primary_key=True, autoincrement=True)
    vehicle_code = Column(String(30), unique=True, nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_lines.line_id"), nullable=False, index=True)
    current_latitude = Column(DECIMAL(10, 7))
    current_longitude = Column(DECIMAL(10, 7))
    current_station_id = Column(BIGINT, ForeignKey("bus_stations.station_id"), index=True)
    next_station_id = Column(BIGINT, ForeignKey("bus_stations.station_id"), index=True)
    progress = Column(DECIMAL(5, 2))
    status = Column(String(20), nullable=False, default='running')
    speed_kmh = Column(DECIMAL(6, 2))
    direction_deg = Column(DECIMAL(6, 2))
    onboard_count = Column(Integer, default=0)
    capacity = Column(Integer, default=60)
    last_updated_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    line = relationship("BusLine")
    current_station = relationship("BusStation", foreign_keys=[current_station_id])
    next_station = relationship("BusStation", foreign_keys=[next_station_id])