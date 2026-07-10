from __future__ import annotations

from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, Integer, String, Time, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import BIGINT_COMPAT, Base, runtime_bigint_id, runtime_string_id


class BusLine(Base):
    __tablename__ = "bus_line"
    __table_args__ = (UniqueConstraint("service_no", "direction", name="uk_line_service_direction"),)

    line_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=False, default=runtime_bigint_id)
    line_code = Column("service_no", String(30), nullable=False, index=True)
    line_name = Column(String(100), nullable=False, index=True)
    operator = Column(String(100), nullable=True)
    raw_direction = Column("direction", Integer, nullable=False, default=1, server_default=text("1"))
    category = Column(String(50), nullable=True)
    origin_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    start_station = Column("origin_stop_code", String(30), nullable=True)
    destination_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    end_station = Column("destination_stop_code", String(30), nullable=True)
    am_peak_freq = Column(String(20), nullable=True)
    am_offpeak_freq = Column(String(20), nullable=True)
    pm_peak_freq = Column(String(20), nullable=True)
    pm_offpeak_freq = Column(String(20), nullable=True)
    avg_service_frequency = Column(DECIMAL(6, 2), nullable=True)
    loop_desc = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="running", server_default=text("'running'"), index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line_stations = relationship(
        "LineStation",
        back_populates="line",
        order_by="LineStation.order_index",
        passive_deletes=True,
    )

    @property
    def service_no(self) -> str:
        return self.line_code

    @service_no.setter
    def service_no(self, value: str) -> None:
        self.line_code = value

    @property
    def direction(self) -> int:
        return int(self.raw_direction or 1)

    @direction.setter
    def direction(self, value: int | str | None) -> None:
        if isinstance(value, str):
            self.raw_direction = 1 if value.lower() in {"forward", "1"} else 2
        else:
            self.raw_direction = int(value or 1)

    @property
    def total_stations(self) -> int:
        return len(self.line_stations)

    @total_stations.setter
    def total_stations(self, _: int | None) -> None:
        # Compatibility-only input; the physical value is derived from line_station.
        return None

    @property
    def distance_km(self) -> float:
        distances = [float(item.route_distance_km or 0) for item in self.line_stations]
        return max(distances, default=0.0)

    @distance_km.setter
    def distance_km(self, _: float | None) -> None:
        return None

    @property
    def first_departure_time(self) -> str | None:
        times = [item.wd_first_bus for item in self.line_stations if item.wd_first_bus]
        return min(times).strftime("%H:%M:%S") if times else None

    @first_departure_time.setter
    def first_departure_time(self, _: str | None) -> None:
        return None

    @property
    def last_departure_time(self) -> str | None:
        times = [item.wd_last_bus for item in self.line_stations if item.wd_last_bus]
        return max(times).strftime("%H:%M:%S") if times else None

    @last_departure_time.setter
    def last_departure_time(self, _: str | None) -> None:
        return None

    @property
    def interval_minutes(self) -> int:
        return int(float(self.avg_service_frequency or 0))

    @interval_minutes.setter
    def interval_minutes(self, value: int | None) -> None:
        self.avg_service_frequency = value


class BusStation(Base):
    __tablename__ = "bus_station"

    station_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=False, default=runtime_bigint_id)
    station_code = Column("bus_stop_code", String(30), unique=True, nullable=True, index=True)
    station_name = Column(String(100), nullable=False, index=True)
    address = Column("road_name", String(100), nullable=True)
    latitude = Column(DECIMAL(10, 7), nullable=False)
    longitude = Column(DECIMAL(10, 7), nullable=False)
    status = Column(String(20), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def bus_stop_code(self) -> str | None:
        return self.station_code

    @bus_stop_code.setter
    def bus_stop_code(self, value: str | None) -> None:
        self.station_code = value

    @property
    def road_name(self) -> str | None:
        return self.address

    @road_name.setter
    def road_name(self, value: str | None) -> None:
        self.address = value

    @property
    def zone(self) -> None:
        # No zone column exists in the final schema. Kept only for API compatibility.
        return None

    @zone.setter
    def zone(self, _: str | None) -> None:
        return None


class LineStation(Base):
    __tablename__ = "line_station"
    __table_args__ = (UniqueConstraint("line_id", "stop_sequence", name="uk_line_station_sequence"),)

    id = Column("line_station_id", String(50), primary_key=True, default=runtime_string_id)
    line_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_line.line_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    service_no = Column(String(30), nullable=True)
    line_name = Column(String(100), nullable=True)
    operator = Column(String(100), nullable=True)
    _direction_code = Column("direction", Integer, nullable=True)
    order_index = Column("stop_sequence", Integer, nullable=False)
    station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    station_code = Column("bus_stop_code", String(30), nullable=True)
    route_distance_km = Column(DECIMAL(8, 3), nullable=True)
    wd_first_bus = Column(Time, nullable=True)
    wd_last_bus = Column(Time, nullable=True)
    sat_first_bus = Column(Time, nullable=True)
    sat_last_bus = Column(Time, nullable=True)
    sun_first_bus = Column(Time, nullable=True)
    sun_last_bus = Column(Time, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine", back_populates="line_stations")
    station = relationship("BusStation")

    def __init__(self, **kwargs):
        # Legacy tests and callers may pass an integer id; the final schema uses VARCHAR(50).
        if "id" in kwargs and kwargs["id"] is not None:
            kwargs["id"] = str(kwargs["id"])
        super().__init__(**kwargs)

    @property
    def line_station_id(self) -> str:
        return self.id

    @line_station_id.setter
    def line_station_id(self, value: str) -> None:
        self.id = value

    @property
    def direction(self) -> str:
        return "forward" if int(self._direction_code or 1) == 1 else "backward"

    @direction.setter
    def direction(self, value: str | int | None) -> None:
        if isinstance(value, int):
            self._direction_code = value
        else:
            self._direction_code = 1 if value in (None, "forward", "1") else 2


__all__ = ["Base", "BusLine", "BusStation", "LineStation"]
