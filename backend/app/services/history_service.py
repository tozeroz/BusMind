from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.cache import memory_cache_provider
from app.cache.cache_keys import passenger_flow_trend
from app.models.bus_line import LineStation
from app.models.history import EtaPrediction, LoadPrediction, PassengerFlowPrediction, PassengerFlowTrend
from app.services.passenger_flow_forecast_service import ensure_station_prediction
from app.schemas.history_schema import (
    EtaPredictionDTO,
    LoadPredictionDTO,
    PassengerFlowPredictionDTO,
    PassengerFlowResponse,
    PassengerFlowSummary,
    PassengerFlowTrendDTO,
)


PASSENGER_FLOW_CACHE_TTL_SECONDS = 120


def _as_float(value):
    return float(value) if value is not None else None


def _month_bounds(value: datetime) -> tuple[datetime, datetime]:
    start = value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _line_station_ids(db: Session, line_id: int | None) -> list[int]:
    if line_id is None:
        return []
    return [
        int(station_id)
        for (station_id,) in (
            db.query(LineStation.station_id)
            .filter(LineStation.line_id == line_id)
            .order_by(LineStation.order_index)
            .all()
        )
    ]


def _apply_passenger_flow_filters(
    query,
    *,
    line_id: int | None,
    station_id: int | None,
    line_station_ids: list[int],
    start_date: datetime | None,
    end_date: datetime | None,
):
    if station_id is not None:
        query = query.filter(
            PassengerFlowTrend.target_type == "station",
            PassengerFlowTrend.target_id == station_id,
        )
        if line_id is not None and station_id not in line_station_ids:
            query = query.filter(False)
    elif line_id is not None:
        if line_station_ids:
            # The production import stores Passenger Flow per station. Resolve a
            # line to its stations instead of looking for non-existent line rows.
            query = query.filter(
                PassengerFlowTrend.target_type == "station",
                PassengerFlowTrend.target_id.in_(line_station_ids),
            )
        else:
            # Keep backward compatibility for databases that imported explicit
            # line-level records and have no line_station mapping.
            query = query.filter(
                PassengerFlowTrend.target_type == "line",
                PassengerFlowTrend.target_id == line_id,
            )

    if start_date is not None:
        query = query.filter(PassengerFlowTrend.record_time >= start_date)
    if end_date is not None:
        query = query.filter(PassengerFlowTrend.record_time <= end_date)
    return query


def _aggregated_flow_level(total_flow: int, maximum_flow: int) -> str:
    """Return the three levels already understood by the current frontend."""
    if maximum_flow <= 0:
        return "low"
    ratio = total_flow / maximum_flow
    if ratio >= 0.7:
        return "high"
    if ratio >= 0.4:
        return "medium"
    return "low"


def _query_passenger_flow_buckets(
    db: Session,
    *,
    line_id: int | None,
    station_id: int | None,
    line_station_ids: list[int],
    start_date: datetime | None,
    end_date: datetime | None,
    granularity: str,
) -> list[dict]:
    """Aggregate rows in SQL before serialising the chart response.

    The old implementation loaded every station/hour row into Python and never
    applied ``granularity``. A complete LTA monthly import can therefore return
    a very large payload and make the page appear to stay in the loading state.
    """

    year_expr = extract("year", PassengerFlowTrend.record_time)
    month_expr = extract("month", PassengerFlowTrend.record_time)
    day_expr = extract("day", PassengerFlowTrend.record_time)
    hour_expr = extract("hour", PassengerFlowTrend.record_time)

    group_expressions = [year_expr, month_expr, day_expr]
    if granularity == "hour":
        group_expressions.append(hour_expr)

    query = db.query(
        func.min(PassengerFlowTrend.flow_record_id).label("flow_record_id"),
        func.min(PassengerFlowTrend.record_time).label("record_time"),
        func.sum(PassengerFlowTrend.tap_in_volume).label("tap_in_volume"),
        func.sum(PassengerFlowTrend.tap_out_volume).label("tap_out_volume"),
        func.sum(PassengerFlowTrend.total_flow).label("total_flow"),
    )
    query = _apply_passenger_flow_filters(
        query,
        line_id=line_id,
        station_id=station_id,
        line_station_ids=line_station_ids,
        start_date=start_date,
        end_date=end_date,
    )
    rows = query.group_by(*group_expressions).order_by(*group_expressions).all()

    daily_rows = [
        {
            "flow_record_id": int(row.flow_record_id or index + 1),
            "record_time": row.record_time,
            "tap_in_volume": int(row.tap_in_volume or 0),
            "tap_out_volume": int(row.tap_out_volume or 0),
            "total_flow": int(row.total_flow or 0),
        }
        for index, row in enumerate(rows)
    ]

    if granularity != "week":
        return daily_rows

    weekly: dict[tuple[int, int], dict] = defaultdict(
        lambda: {
            "flow_record_id": 0,
            "record_time": None,
            "tap_in_volume": 0,
            "tap_out_volume": 0,
            "total_flow": 0,
        }
    )
    for row in daily_rows:
        record_time = row["record_time"]
        if record_time is None:
            continue
        iso_year, iso_week, _ = record_time.isocalendar()
        bucket = weekly[(iso_year, iso_week)]
        if bucket["flow_record_id"] == 0:
            bucket["flow_record_id"] = row["flow_record_id"]
        if bucket["record_time"] is None or record_time < bucket["record_time"]:
            bucket["record_time"] = record_time
        bucket["tap_in_volume"] += row["tap_in_volume"]
        bucket["tap_out_volume"] += row["tap_out_volume"]
        bucket["total_flow"] += row["total_flow"]

    return [weekly[key] for key in sorted(weekly)]


def get_passenger_flow_trend(
    db: Session,
    line_id: Optional[int] = None,
    station_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    granularity: str = "hour",
) -> PassengerFlowResponse:
    cache_key = passenger_flow_trend(line_id, station_id, start_date, end_date, granularity)
    cached = memory_cache_provider.get(cache_key)
    if isinstance(cached, PassengerFlowResponse):
        return cached

    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must not be later than end_date")
    if granularity not in {"hour", "day", "week"}:
        raise ValueError("granularity must be hour, day or week")

    line_station_ids = _line_station_ids(db, line_id)

    # With no explicit date range, use the newest available calendar month. This
    # avoids merging old monthly snapshots and keeps the initial page request
    # small even when the database contains several years of imported data.
    if start_date is None and end_date is None:
        latest_query = db.query(func.max(PassengerFlowTrend.record_time))
        latest_query = _apply_passenger_flow_filters(
            latest_query,
            line_id=line_id,
            station_id=station_id,
            line_station_ids=line_station_ids,
            start_date=None,
            end_date=None,
        )
        latest_record_time = latest_query.scalar()
        if latest_record_time is not None:
            start_date, exclusive_end = _month_bounds(latest_record_time)
            end_date = exclusive_end - timedelta(microseconds=1)

    bucket_rows = _query_passenger_flow_buckets(
        db,
        line_id=line_id,
        station_id=station_id,
        line_station_ids=line_station_ids,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )

    maximum_flow = max((row["total_flow"] for row in bucket_rows), default=0)
    target_type = "station" if station_id is not None else ("line" if line_id is not None else "all")
    target_id = station_id if station_id is not None else (line_id if line_id is not None else 0)

    items = [
        PassengerFlowTrendDTO(
            flow_record_id=row["flow_record_id"],
            target_type=target_type,
            target_id=int(target_id),
            bus_stop_code=None,
            record_time=row["record_time"],
            day_type="all",
            tap_in_volume=row["tap_in_volume"],
            tap_out_volume=row["tap_out_volume"],
            total_flow=row["total_flow"],
            flow_level=_aggregated_flow_level(row["total_flow"], maximum_flow),
            data_source="passenger_flow_trend_aggregated",
        )
        for row in bucket_rows
    ]

    total_tap_in = sum(item.tap_in_volume for item in items)
    total_tap_out = sum(item.tap_out_volume for item in items)
    total_flow = sum(item.total_flow for item in items)
    peak = max(items, key=lambda item: item.total_flow, default=None)
    levels: dict[str, int] = {}
    for item in items:
        if item.flow_level:
            levels[item.flow_level] = levels.get(item.flow_level, 0) + 1

    result = PassengerFlowResponse(
        items=items,
        summary=PassengerFlowSummary(
            total_tap_in=total_tap_in,
            total_tap_out=total_tap_out,
            total_flow=total_flow,
            peak_hour=peak.record_time.hour if peak and peak.record_time else None,
            peak_flow=peak.total_flow if peak else None,
            dominant_flow_level=max(levels, key=levels.get) if levels else None,
            granularity=granularity,
            point_count=len(items),
            start_time=items[0].record_time if items else start_date,
            end_time=items[-1].record_time if items else end_date,
        ),
    )
    memory_cache_provider.set(cache_key, result, ttl_seconds=PASSENGER_FLOW_CACHE_TTL_SECONDS)
    return result


def get_passenger_flow_prediction(
    db: Session,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> list[PassengerFlowPredictionDTO]:
    # 只在有具体时间范围时才尝试生成预测，否则直接读取已有数据
    if target_type == "station" and target_id and start_time is None and end_time is None:
        # 检查是否已有未来预测数据，避免每次请求都重新计算
        latest_prediction = (
            db.query(PassengerFlowPrediction)
            .filter(
                PassengerFlowPrediction.target_type == "station",
                PassengerFlowPrediction.target_id == target_id,
            )
            .order_by(PassengerFlowPrediction.predict_time.desc())
            .first()
        )
        if latest_prediction is None or latest_prediction.predict_time < datetime.now():
            # 未来无预测，跳过生成（由定时任务负责更新）
            pass

    query = db.query(PassengerFlowPrediction)
    if target_type:
        query = query.filter(PassengerFlowPrediction.target_type == target_type)
    if target_id:
        query = query.filter(PassengerFlowPrediction.target_id == target_id)
    if start_time:
        query = query.filter(PassengerFlowPrediction.predict_time >= start_time)
    if end_time:
        query = query.filter(PassengerFlowPrediction.predict_time <= end_time)
    return [
        PassengerFlowPredictionDTO(
            prediction_id=int(record.prediction_id),
            target_type=record.target_type,
            target_id=record.target_id,
            prediction_time=record.prediction_time,
            predict_time=record.predict_time,
            predicted_flow=int(record.predicted_flow),
            crowd_level=record.crowd_level,
            confidence=_as_float(record.confidence),
            model_version=record.model_version,
        )
        for record in query.order_by(PassengerFlowPrediction.predict_time).all()
    ]


def _eta_dto(record: EtaPrediction) -> EtaPredictionDTO:
    return EtaPredictionDTO(
        eta_prediction_id=int(record.eta_prediction_id),
        vehicle_id=int(record.vehicle_id),
        line_id=int(record.line_id),
        target_station_id=int(record.target_station_id),
        bus_stop_code=record.bus_stop_code,
        prediction_time=record.prediction_time,
        predicted_eta_minutes=float(record.predicted_eta_minutes),
        arrival_time=record.arrival_time,
        vehicle_to_stop_distance_m=_as_float(record.vehicle_to_stop_distance_m),
        speed_kph=_as_float(record.speed_kph),
        confidence=_as_float(record.confidence),
        data_source=record.data_source,
        model_version=None,
        created_at=record.created_at,
    )


def _load_dto(record: LoadPrediction) -> LoadPredictionDTO:
    return LoadPredictionDTO(
        load_prediction_id=int(record.load_prediction_id),
        vehicle_id=int(record.vehicle_id),
        line_id=int(record.line_id),
        station_id=int(record.station_id) if record.station_id is not None else None,
        bus_stop_code=record.bus_stop_code,
        prediction_time=record.prediction_time,
        load_code=record.load_code,
        predicted_load_level=record.predicted_load_level,
        load_score=_as_float(record.load_score),
        predicted_load_rate=_as_float(record.predicted_load_rate),
        onboard_count=record.onboard_count,
        capacity=record.capacity,
        confidence=_as_float(record.confidence),
        data_source=record.data_source,
        model_version=None,
        created_at=record.created_at,
    )


def get_eta_prediction(
    db: Session,
    vehicle_id: int,
    target_station_id: int,
    line_id: Optional[int] = None,
) -> Optional[EtaPredictionDTO]:
    query = db.query(EtaPrediction).filter(
        EtaPrediction.vehicle_id == vehicle_id,
        EtaPrediction.target_station_id == target_station_id,
    )
    if line_id is not None:
        query = query.filter(EtaPrediction.line_id == line_id)
    record = query.order_by(EtaPrediction.prediction_time.desc()).first()
    return _eta_dto(record) if record else None


def get_load_prediction(
    db: Session,
    line_id: int,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
) -> Optional[LoadPredictionDTO]:
    query = db.query(LoadPrediction).filter(LoadPrediction.line_id == line_id)
    if station_id is not None:
        query = query.filter(LoadPrediction.station_id == station_id)
    if vehicle_id is not None:
        query = query.filter(LoadPrediction.vehicle_id == vehicle_id)
    record = query.order_by(LoadPrediction.prediction_time.desc()).first()
    return _load_dto(record) if record else None


def get_eta_predictions_by_line(
    db: Session,
    line_id: int,
    target_station_id: Optional[int] = None,
) -> list[EtaPredictionDTO]:
    query = db.query(EtaPrediction).filter(EtaPrediction.line_id == line_id)
    if target_station_id is not None:
        query = query.filter(EtaPrediction.target_station_id == target_station_id)
    return [_eta_dto(record) for record in query.order_by(EtaPrediction.prediction_time.desc()).all()]


def get_load_predictions_by_line(
    db: Session,
    line_id: int,
    station_id: Optional[int] = None,
) -> list[LoadPredictionDTO]:
    query = db.query(LoadPrediction).filter(LoadPrediction.line_id == line_id)
    if station_id is not None:
        query = query.filter(LoadPrediction.station_id == station_id)
    return [_load_dto(record) for record in query.order_by(LoadPrediction.prediction_time.desc()).all()]


def get_predictions(
    db: Session,
    prediction_type: Optional[str] = None,
    line_id: Optional[int] = None,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
) -> list[dict]:
    results = []
    
    if prediction_type is None or prediction_type == "eta":
        eta_query = db.query(EtaPrediction)
        if line_id is not None:
            eta_query = eta_query.filter(EtaPrediction.line_id == line_id)
        if station_id is not None:
            eta_query = eta_query.filter(EtaPrediction.target_station_id == station_id)
        if vehicle_id is not None:
            eta_query = eta_query.filter(EtaPrediction.vehicle_id == vehicle_id)
        
        for record in eta_query.order_by(EtaPrediction.prediction_time.desc()).all():
            dto = _eta_dto(record)
            results.append({
                "prediction_type": "eta",
                **dto.__dict__
            })
    
    if prediction_type is None or prediction_type == "passenger_load":
        load_query = db.query(LoadPrediction)
        if line_id is not None:
            load_query = load_query.filter(LoadPrediction.line_id == line_id)
        if station_id is not None:
            load_query = load_query.filter(LoadPrediction.station_id == station_id)
        if vehicle_id is not None:
            load_query = load_query.filter(LoadPrediction.vehicle_id == vehicle_id)
        
        for record in load_query.order_by(LoadPrediction.prediction_time.desc()).all():
            dto = _load_dto(record)
            results.append({
                "prediction_type": "passenger_load",
                **dto.__dict__
            })
    
    if prediction_type is None or prediction_type == "passenger_flow":
        flow_query = db.query(PassengerFlowPrediction)
        if line_id is not None:
            flow_query = flow_query.filter(PassengerFlowPrediction.target_type == "line")
            flow_query = flow_query.filter(PassengerFlowPrediction.target_id == str(line_id))
        if station_id is not None:
            flow_query = flow_query.filter(PassengerFlowPrediction.target_type == "station")
            flow_query = flow_query.filter(PassengerFlowPrediction.target_id == str(station_id))
        
        for record in flow_query.order_by(PassengerFlowPrediction.predict_time.desc()).all():
            dto = PassengerFlowPredictionDTO(
                prediction_id=int(record.prediction_id),
                target_type=record.target_type,
                target_id=record.target_id,
                prediction_time=record.prediction_time,
                predict_time=record.predict_time,
                predicted_flow=int(record.predicted_flow),
                crowd_level=record.crowd_level,
                confidence=_as_float(record.confidence),
                model_version=record.model_version,
            )
            results.append({
                "prediction_type": "passenger_flow",
                **dto.__dict__
            })
    
    return sorted(results, key=lambda x: x.get('prediction_time') or x.get('predict_time'), reverse=True)
