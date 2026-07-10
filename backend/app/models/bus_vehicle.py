from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, Integer, String, text
from sqlalchemy.orm import relationship, synonym
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
    longitude = synonym("current_longitude")
    latitude = synonym("current_latitude")
    speed_kph = synonym("speed_kmh")
    operation_status = synonym("status")
    last_reported_at = synonym("last_updated_at")

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
