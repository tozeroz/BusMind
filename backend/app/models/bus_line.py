from sqlalchemy import BIGINT, DECIMAL, DateTime, ForeignKey, Integer, String, Time, Column
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class BusLine(Base):
    __tablename__ = "bus_line"

    line_id = Column(BIGINT, primary_key=True, autoincrement=True)
    line_code = Column("service_no", String(30), nullable=False, index=True)
    line_name = Column(String(100), nullable=False)
    operator = Column(String(100))
    raw_direction = Column("direction", Integer)
    category = Column(String(50))
    origin_station_id = Column(BIGINT)
    start_station = Column("origin_stop_code", String(30))
    destination_station_id = Column(BIGINT)
    end_station = Column("destination_stop_code", String(30))
    am_peak_freq = Column(String(20))
    am_offpeak_freq = Column(String(20))
    pm_peak_freq = Column(String(20))
    pm_offpeak_freq = Column(String(20))
    avg_service_frequency = Column(DECIMAL(6, 2))
    loop_desc = Column(String(255))
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line_stations = relationship("LineStation", back_populates="line", viewonly=True)

    @property
    def total_stations(self) -> int:
        return len(self.line_stations)

    @total_stations.setter
    def total_stations(self, _: int) -> None:
        # Kept for compatibility with existing create/update request models.
        return None

    @property
    def distance_km(self) -> float:
        distances = [float(ls.route_distance_km or 0) for ls in self.line_stations]
        return max(distances, default=0.0)

    @distance_km.setter
    def distance_km(self, _: float) -> None:
        return None

    @property
    def first_departure_time(self) -> str | None:
        times = [ls.wd_first_bus for ls in self.line_stations if ls.wd_first_bus]
        return min(times).strftime("%H:%M:%S") if times else None

    @first_departure_time.setter
    def first_departure_time(self, _: str | None) -> None:
        return None

    @property
    def last_departure_time(self) -> str | None:
        times = [ls.wd_last_bus for ls in self.line_stations if ls.wd_last_bus]
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

    station_id = Column(BIGINT, primary_key=True, autoincrement=True)
    station_code = Column("bus_stop_code", String(30), unique=True, nullable=False, index=True)
    station_name = Column(String(100), nullable=False)
    address = Column("road_name", String(100))
    latitude = Column(DECIMAL(10, 7), nullable=False)
    longitude = Column(DECIMAL(10, 7), nullable=False)
    status = Column(String(20))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def zone(self) -> None:
        return None

    @zone.setter
    def zone(self, _: str | None) -> None:
        return None


class LineStation(Base):
    __tablename__ = "line_station"

    id = Column("line_station_id", String(50), primary_key=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    service_no = Column(String(30))
    line_name = Column(String(100))
    operator = Column(String(100))
    _direction_code = Column("direction", Integer)
    order_index = Column("stop_sequence", Integer, nullable=False)
    station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), nullable=False, index=True)
    station_code = Column("bus_stop_code", String(30))
    route_distance_km = Column(DECIMAL(8, 3))
    wd_first_bus = Column(Time)
    wd_last_bus = Column(Time)
    sat_first_bus = Column(Time)
    sat_last_bus = Column(Time)
    sun_first_bus = Column(Time)
    sun_last_bus = Column(Time)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine", back_populates="line_stations", viewonly=True)
    station = relationship("BusStation", viewonly=True)

    @property
    def direction(self) -> str:
        return "forward" if self._direction_code == 1 else "backward"

    @direction.setter
    def direction(self, value: str | None) -> None:
        self._direction_code = 1 if value in (None, "forward") else 2
