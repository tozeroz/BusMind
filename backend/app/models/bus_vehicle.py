from sqlalchemy import BIGINT, DECIMAL, DateTime, ForeignKey, Integer, String, Column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.bus_line import Base


class BusVehicle(Base):
    __tablename__ = "bus_vehicle"

    vehicle_id = Column(BIGINT, primary_key=True, autoincrement=True)
    vehicle_code = Column(String(30), unique=True, nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    service_no = Column(String(30))
    line_name = Column(String(100))
    current_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), index=True)
    next_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), index=True)
    next_station_name = Column(String(100))
    current_position_text = Column(String(150))
    current_longitude = Column("longitude", DECIMAL(10, 7))
    current_latitude = Column("latitude", DECIMAL(10, 7))
    speed_kmh = Column("speed_kph", DECIMAL(6, 2))
    onboard_count = Column(Integer, default=0)
    capacity = Column(Integer, default=60)
    load_level = Column(String(30))
    load_code = Column(String(10))
    load_score = Column(DECIMAL(6, 2))
    status = Column("operation_status", String(20), nullable=False, default="running")
    delay_minutes = Column(Integer)
    data_status = Column(String(20))
    last_updated_at = Column("last_reported_at", DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine", viewonly=True)
    current_station = relationship("BusStation", foreign_keys=[current_station_id], viewonly=True)
    next_station = relationship("BusStation", foreign_keys=[next_station_id], viewonly=True)

    @property
    def progress(self) -> float:
        return 0.0

    @progress.setter
    def progress(self, _: float | None) -> None:
        return None

    @property
    def direction_deg(self) -> float:
        return 0.0

    @direction_deg.setter
    def direction_deg(self, _: float | None) -> None:
        return None
