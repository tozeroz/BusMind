from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, Integer, String, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import BIGINT_COMPAT, Base, runtime_bigint_id, runtime_string_id


class BusVehicle(Base):
    __tablename__ = "bus_vehicle"

    vehicle_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=False, default=runtime_bigint_id)
    vehicle_code = Column(String(30), unique=True, nullable=True, index=True)
    line_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_line.line_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    service_no = Column(String(30), nullable=True)
    line_name = Column(String(100), nullable=True)
    current_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    next_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    next_station_name = Column(String(100), nullable=True)
    current_position_text = Column(String(150), nullable=True)
    current_longitude = Column("longitude", DECIMAL(10, 7), nullable=True)
    current_latitude = Column("latitude", DECIMAL(10, 7), nullable=True)
    speed_kmh = Column("speed_kph", DECIMAL(6, 2), nullable=True)
    onboard_count = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    load_level = Column(String(30), nullable=True)
    load_code = Column(String(10), nullable=True)
    load_score = Column(DECIMAL(6, 2), nullable=True)
    status = Column(
        "operation_status",
        String(20),
        nullable=False,
        default="normal",
        server_default=text("'normal'"),
        index=True,
    )
    delay_minutes = Column(Integer, nullable=False, default=0, server_default=text("0"))
    data_status = Column(
        String(20), nullable=False, default="estimated", server_default=text("'estimated'")
    )
    last_updated_at = Column("last_reported_at", DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), index=True)

    line = relationship("BusLine")
    current_station = relationship("BusStation", foreign_keys=[current_station_id])
    next_station = relationship("BusStation", foreign_keys=[next_station_id])

    @property
    def longitude(self):
        return self.current_longitude

    @longitude.setter
    def longitude(self, value):
        self.current_longitude = value

    @property
    def latitude(self):
        return self.current_latitude

    @latitude.setter
    def latitude(self, value):
        self.current_latitude = value

    @property
    def speed_kph(self):
        return self.speed_kmh

    @speed_kph.setter
    def speed_kph(self, value):
        self.speed_kmh = value

    @property
    def operation_status(self) -> str:
        return self.status

    @operation_status.setter
    def operation_status(self, value: str) -> None:
        self.status = value

    @property
    def progress(self) -> float:
        # No progress column exists in the final database schema.
        return 0.0

    @progress.setter
    def progress(self, _: float | None) -> None:
        return None

    @property
    def direction_deg(self) -> float:
        # No direction_deg column exists in the final database schema.
        return 0.0

    @direction_deg.setter
    def direction_deg(self, _: float | None) -> None:
        return None


__all__ = ["Base", "BusVehicle"]
