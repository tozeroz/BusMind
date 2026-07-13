from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Computed, DateTime, DECIMAL, ForeignKey, Integer, String, text
from sqlalchemy.orm import synonym
from sqlalchemy.sql import func

from app.db.base import BIGINT_COMPAT, Base


class PassengerFlowTrend(Base):
    __tablename__ = "passenger_flow_trend"

    flow_record_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False, index=True)
    target_id = Column(BIGINT_COMPAT, nullable=False, index=True)
    bus_stop_code = Column(String(30), nullable=True)
    record_time = Column(DateTime, nullable=False, index=True)
    record_hour = Column(Integer, Computed("HOUR(record_time)", persisted=True))
    day_type = Column(String(20), nullable=True)
    tap_in_volume = Column(Integer, nullable=False, default=0, server_default=text("0"))
    tap_out_volume = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_flow = Column(Integer, nullable=False, default=0, server_default=text("0"))
    flow_level = Column(String(20), nullable=True, index=True)
    data_source = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    def __init__(self, **kwargs):
        # Backward-compatible handling for old test/demo inputs. These values are
        # converted to the physical record_time column rather than stored as columns.
        year_month = kwargs.pop("year_month", None)
        hour = kwargs.pop("hour", None)
        if "record_time" not in kwargs:
            if year_month:
                try:
                    year, month = (int(part) for part in str(year_month).split("-", 1))
                    kwargs["record_time"] = datetime(year, month, 1, int(hour or 0))
                except (TypeError, ValueError):
                    kwargs["record_time"] = datetime.now()
            else:
                kwargs["record_time"] = datetime.now()
        super().__init__(**kwargs)

    @property
    def year_month(self) -> str:
        return self.record_time.strftime("%Y-%m") if self.record_time else ""

    @property
    def hour(self) -> int | None:
        return self.record_time.hour if self.record_time else None


class PassengerFlowPrediction(Base):
    __tablename__ = "passenger_flow_prediction"

    prediction_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False, index=True)
    target_id = Column(String(50), nullable=False, index=True)
    prediction_time = Column(DateTime, nullable=False, index=True)
    predict_time = Column(DateTime, nullable=False, index=True)
    predicted_flow = Column(Integer, nullable=False)
    crowd_level = Column(String(20), nullable=False)
    confidence = Column(DECIMAL(5, 4), nullable=True)
    model_version = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class EtaPrediction(Base):
    """Compatibility class mapped to ``bus_eta_status``."""

    __tablename__ = "bus_eta_status"

    eta_prediction_id = Column("eta_status_id", BIGINT_COMPAT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT_COMPAT, nullable=False, index=True)
    line_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_line.line_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    target_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    bus_stop_code = Column(String(30), nullable=True)
    prediction_time = Column("query_time", DateTime, nullable=False, index=True)
    predicted_eta_minutes = Column("eta_minutes", DECIMAL(8, 2), nullable=False)
    arrival_time = Column(DateTime, nullable=True, index=True)
    vehicle_to_stop_distance_m = Column(DECIMAL(10, 2), nullable=True)
    speed_kph = Column(DECIMAL(6, 2), nullable=True)
    confidence = Column(DECIMAL(5, 4), nullable=True)
    data_source = Column(
        String(100), nullable=False, default="lta_bus_arrival", server_default=text("'lta_bus_arrival'")
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    eta_status_id = synonym("eta_prediction_id")
    query_time = synonym("prediction_time")
    eta_minutes = synonym("predicted_eta_minutes")

    @property
    def model_version(self) -> None:
        return None


class LoadPrediction(Base):
    """Compatibility class mapped to ``bus_load_status``."""

    __tablename__ = "bus_load_status"

    load_prediction_id = Column("load_status_id", BIGINT_COMPAT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT_COMPAT, nullable=False, index=True)
    line_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_line.line_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    bus_stop_code = Column(String(30), nullable=True)
    prediction_time = Column("query_time", DateTime, nullable=False, index=True)
    load_code = Column(String(10), nullable=True)
    predicted_load_level = Column("load_level", String(30), nullable=False)
    load_score = Column(DECIMAL(6, 2), nullable=True)
    predicted_load_rate = Column("load_rate", DECIMAL(6, 4), nullable=True)
    onboard_count = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    confidence = Column(DECIMAL(5, 4), nullable=True)
    data_source = Column(
        String(100), nullable=False, default="lta_bus_arrival", server_default=text("'lta_bus_arrival'")
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    load_status_id = synonym("load_prediction_id")
    query_time = synonym("prediction_time")
    load_level = synonym("predicted_load_level")
    load_rate = synonym("predicted_load_rate")

    @property
    def model_version(self) -> None:
        return None


__all__ = [
    "Base",
    "PassengerFlowTrend",
    "PassengerFlowPrediction",
    "EtaPrediction",
    "LoadPrediction",
]
