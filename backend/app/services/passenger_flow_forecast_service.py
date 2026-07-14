from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math

from sqlalchemy.orm import Session

from app.models.history import PassengerFlowPrediction, PassengerFlowTrend


MODEL_VERSION_RIDGE = "ridge_linear_v1"
MODEL_VERSION_BASELINE = "historical_average_v1"
DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_HORIZON_DAYS = 7
DEFAULT_MIN_HISTORY_POINTS = 24
RIDGE_ALPHA = 1.0
_FEATURE_DIMENSIONS = 8


@dataclass(frozen=True, slots=True)
class PassengerFlowForecastResult:
    station_id: int
    created: int
    deleted: int
    reused: int
    skipped: bool
    reason: str | None
    model_version: str | None


def _feature_vector(value: datetime) -> list[float]:
    hour = float(value.hour)
    weekday = float(value.weekday())
    return [
        1.0,
        hour,
        weekday,
        hour * hour,
        math.sin(2.0 * math.pi * hour / 24.0),
        math.cos(2.0 * math.pi * hour / 24.0),
        math.sin(2.0 * math.pi * weekday / 7.0),
        math.cos(2.0 * math.pi * weekday / 7.0),
    ]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(l * r for l, r in zip(left, right))


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    size = len(values)
    augmented = [row[:] + [values[index]] for index, row in enumerate(matrix)]

    for column in range(size):
        pivot = max(range(column, size), key=lambda row_index: abs(augmented[row_index][column]))
        pivot_value = augmented[pivot][column]
        if abs(pivot_value) < 1e-9:
            raise ValueError("ridge system is singular")

        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]

        pivot_value = augmented[column][column]
        for cursor in range(column, size + 1):
            augmented[column][cursor] /= pivot_value

        for row_index in range(size):
            if row_index == column:
                continue
            factor = augmented[row_index][column]
            if abs(factor) < 1e-12:
                continue
            for cursor in range(column, size + 1):
                augmented[row_index][cursor] -= factor * augmented[column][cursor]

    return [augmented[index][size] for index in range(size)]


class _RidgeRegressionModel:
    def __init__(self, weights: list[float]):
        self._weights = weights

    @property
    def model_version(self) -> str:
        return MODEL_VERSION_RIDGE

    @property
    def confidence(self) -> float:
        return 0.6

    def predict(self, value: datetime) -> int:
        prediction = max(0.0, _dot(self._weights, _feature_vector(value)))
        return int(round(prediction))


class _HistoricalAverageModel:
    def __init__(self, rows: list):
        self._weekday_hour_average: dict[tuple[int, int], float] = {}
        self._hour_average: dict[int, float] = {}
        self._overall_average = 0.0

        weekday_hour_totals: dict[tuple[int, int], tuple[int, int]] = {}
        hour_totals: dict[int, tuple[int, int]] = {}
        overall_total = 0

        for row in rows:
            hour = row.record_time.hour
            weekday = row.record_time.weekday()
            flow = int(row.total_flow or 0)

            weekday_hour_total, weekday_hour_count = weekday_hour_totals.get((weekday, hour), (0, 0))
            weekday_hour_totals[(weekday, hour)] = (weekday_hour_total + flow, weekday_hour_count + 1)

            hour_total, hour_count = hour_totals.get(hour, (0, 0))
            hour_totals[hour] = (hour_total + flow, hour_count + 1)

            overall_total += flow

        for key, (total, count) in weekday_hour_totals.items():
            self._weekday_hour_average[key] = total / count
        for hour, (total, count) in hour_totals.items():
            self._hour_average[hour] = total / count
        self._overall_average = overall_total / max(1, len(rows))

    @property
    def model_version(self) -> str:
        return MODEL_VERSION_BASELINE

    @property
    def confidence(self) -> float:
        return 0.45

    def predict(self, value: datetime) -> int:
        estimate = self._weekday_hour_average.get((value.weekday(), value.hour))
        if estimate is None:
            estimate = self._hour_average.get(value.hour, self._overall_average)
        return int(round(max(0.0, estimate)))


def _train_ridge_model(rows: list) -> _RidgeRegressionModel:
    matrix = [[0.0] * _FEATURE_DIMENSIONS for _ in range(_FEATURE_DIMENSIONS)]
    values = [0.0] * _FEATURE_DIMENSIONS

    for row in rows:
        features = _feature_vector(row.record_time)
        target = float(row.total_flow or 0)
        for left_index in range(_FEATURE_DIMENSIONS):
            values[left_index] += features[left_index] * target
            for right_index in range(_FEATURE_DIMENSIONS):
                matrix[left_index][right_index] += features[left_index] * features[right_index]

    for index in range(1, _FEATURE_DIMENSIONS):
        matrix[index][index] += RIDGE_ALPHA

    return _RidgeRegressionModel(_solve_linear_system(matrix, values))


def _crowd_level(predicted_flow: int) -> str:
    if predicted_flow >= 100:
        return "high"
    if predicted_flow >= 50:
        return "medium"
    return "low"


def _base_time(now: datetime | None) -> datetime:
    reference = now or datetime.now()
    return reference.replace(minute=0, second=0, microsecond=0)


def list_station_ids_with_history(db: Session) -> list[int]:
    rows = (
        db.query(PassengerFlowTrend.target_id)
        .filter(PassengerFlowTrend.target_type == "station")
        .distinct()
        .order_by(PassengerFlowTrend.target_id.asc())
        .all()
    )
    return [int(station_id) for (station_id,) in rows]


def ensure_station_prediction(
    db: Session,
    station_id: int,
    *,
    now: datetime | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    min_history_points: int = DEFAULT_MIN_HISTORY_POINTS,
    commit: bool = True,
) -> PassengerFlowForecastResult:
    base_time = _base_time(now)
    horizon_hours = max(1, horizon_days * 24)
    horizon_end = base_time + timedelta(hours=horizon_hours)
    target_id = str(station_id)

    existing_query = db.query(PassengerFlowPrediction).filter(
        PassengerFlowPrediction.target_type == "station",
        PassengerFlowPrediction.target_id == target_id,
        PassengerFlowPrediction.predict_time >= base_time,
        PassengerFlowPrediction.predict_time < horizon_end,
    )
    existing_rows = existing_query.order_by(PassengerFlowPrediction.predict_time.asc()).all()
    if len(existing_rows) >= horizon_hours:
        last_predict_time = existing_rows[-1].predict_time
        if last_predict_time >= horizon_end - timedelta(hours=1):
            return PassengerFlowForecastResult(
                station_id=station_id,
                created=0,
                deleted=0,
                reused=len(existing_rows),
                skipped=False,
                reason="up_to_date",
                model_version=existing_rows[-1].model_version,
            )

    history_rows = (
        db.query(
            PassengerFlowTrend.record_time,
            PassengerFlowTrend.total_flow,
        )
        .filter(
            PassengerFlowTrend.target_type == "station",
            PassengerFlowTrend.target_id == station_id,
            PassengerFlowTrend.record_time >= base_time - timedelta(days=max(1, lookback_days)),
            PassengerFlowTrend.record_time < base_time,
        )
        .order_by(PassengerFlowTrend.record_time.asc())
        .all()
    )
    if not history_rows:
        return PassengerFlowForecastResult(
            station_id=station_id,
            created=0,
            deleted=0,
            reused=0,
            skipped=True,
            reason="no_history",
            model_version=None,
        )

    try:
        model = (
            _train_ridge_model(history_rows)
            if len(history_rows) >= max(_FEATURE_DIMENSIONS, min_history_points)
            else _HistoricalAverageModel(history_rows)
        )
    except ValueError:
        model = _HistoricalAverageModel(history_rows)

    deleted = existing_query.delete(synchronize_session=False)
    created = 0
    for offset in range(horizon_hours):
        predict_time = base_time + timedelta(hours=offset)
        predicted_flow = model.predict(predict_time)
        db.add(
            PassengerFlowPrediction(
                target_type="station",
                target_id=target_id,
                prediction_time=base_time,
                predict_time=predict_time,
                predicted_flow=predicted_flow,
                crowd_level=_crowd_level(predicted_flow),
                confidence=model.confidence,
                model_version=model.model_version,
            )
        )
        created += 1

    if commit:
        db.commit()
    else:
        db.flush()

    return PassengerFlowForecastResult(
        station_id=station_id,
        created=created,
        deleted=int(deleted or 0),
        reused=0,
        skipped=False,
        reason="generated",
        model_version=model.model_version,
    )


def generate_station_predictions(
    db: Session,
    *,
    station_ids: list[int] | None = None,
    now: datetime | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    min_history_points: int = DEFAULT_MIN_HISTORY_POINTS,
) -> list[PassengerFlowForecastResult]:
    base_time = _base_time(now)
    results: list[PassengerFlowForecastResult] = []
    for station_id in station_ids or list_station_ids_with_history(db):
        results.append(
            ensure_station_prediction(
                db,
                station_id,
                now=base_time,
                lookback_days=lookback_days,
                horizon_days=horizon_days,
                min_history_points=min_history_points,
                commit=False,
            )
        )
    db.commit()
    return results


__all__ = [
    "DEFAULT_HORIZON_DAYS",
    "DEFAULT_LOOKBACK_DAYS",
    "DEFAULT_MIN_HISTORY_POINTS",
    "MODEL_VERSION_BASELINE",
    "MODEL_VERSION_RIDGE",
    "PassengerFlowForecastResult",
    "ensure_station_prediction",
    "generate_station_predictions",
    "list_station_ids_with_history",
]
