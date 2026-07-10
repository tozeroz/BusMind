"""Configuration for service-side intelligence modules.

Secrets are read from environment variables or a dedicated ``service-b.env``
file.  The loader intentionally runs before ``IntelligenceSettings`` is
instantiated so values such as ``DEEPSEEK_API_KEY`` are available during
application import.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - direct environment variables still work
    dotenv_values = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


def _candidate_env_files() -> list[Path]:
    """Return supported service-B env locations in priority order.

    ``service-b.env`` in the project root remains the canonical location.  The
    backend directory and the common misspelling ``sevice-b.env`` are accepted
    to make local startup less fragile.  ``BUSMIND_SERVICE_B_ENV_FILE`` can be
    used to select an explicit path.
    """

    candidates: list[Path] = []
    explicit = os.getenv("BUSMIND_SERVICE_B_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    cwd = Path.cwd()
    candidates.extend(
        [
            PROJECT_ROOT / "service-b.env",
            PROJECT_ROOT / "sevice-b.env",
            BACKEND_ROOT / "service-b.env",
            BACKEND_ROOT / "sevice-b.env",
            cwd / "service-b.env",
            cwd / "sevice-b.env",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        marker = os.path.normcase(str(resolved))
        if marker not in seen:
            seen.add(marker)
            unique.append(resolved)
    return unique


def _load_service_b_env() -> Path:
    candidates = _candidate_env_files()
    selected = next((item for item in candidates if item.is_file()), candidates[0])

    if dotenv_values is not None and selected.is_file():
        # A non-empty process environment variable has priority.  Empty values
        # do not block a valid value from the dedicated env file.
        for key, value in dotenv_values(selected, encoding="utf-8").items():
            if value is not None and not os.getenv(key):
                os.environ[key] = value
    return selected


SERVICE_B_ENV_FILE = _load_service_b_env()


def _env_text(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_float(name: str, default: float) -> float:
    value = _env_text(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = _env_text(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _api_key(name: str) -> str | None:
    value = _env_text(name)
    if value is None:
        return None
    lowered = value.lower()
    placeholders = (
        "请填写",
        "your_api_key",
        "your-api-key",
        "replace_me",
        "changeme",
    )
    if any(marker in lowered for marker in placeholders):
        return None
    return value


@dataclass(frozen=True, slots=True)
class IntelligenceSettings:
    timezone: str = _env_text("BUSMIND_TIMEZONE", "Asia/Shanghai") or "Asia/Shanghai"

    eta_predictor_path: str = _env_text(
        "BUSMIND_ETA_PREDICTOR",
        "algorithm.eta_prediction.models.predict_eta:predict_eta",
    ) or "algorithm.eta_prediction.models.predict_eta:predict_eta"
    load_predictor_path: str = _env_text(
        "BUSMIND_LOAD_PREDICTOR",
        "algorithm.load_prediction.models.predict_load:predict_load",
    ) or "algorithm.load_prediction.models.predict_load:predict_load"

    default_vehicle_capacity: int = _env_int("BUSMIND_DEFAULT_CAPACITY", 60)
    default_walking_speed_mps: float = _env_float("BUSMIND_WALKING_SPEED_MPS", 1.2)
    walking_road_factor: float = _env_float("BUSMIND_WALKING_ROAD_FACTOR", 1.25)

    weight_load: float = _env_float("BUSMIND_WEIGHT_LOAD", 0.50)
    weight_walk: float = _env_float("BUSMIND_WEIGHT_WALK", 0.30)
    weight_transfer: float = _env_float("BUSMIND_WEIGHT_TRANSFER", 0.20)

    deepseek_api_key: str | None = _api_key("DEEPSEEK_API_KEY")
    deepseek_base_url: str = _env_text(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
    ) or "https://api.deepseek.com"
    deepseek_model: str = _env_text(
        "DEEPSEEK_MODEL", "deepseek-v4-flash"
    ) or "deepseek-v4-flash"
    deepseek_timeout_seconds: float = _env_float("DEEPSEEK_TIMEOUT_SECONDS", 20.0)
    deepseek_max_tokens: int = _env_int("DEEPSEEK_MAX_TOKENS", 700)
    deepseek_temperature: float = _env_float("DEEPSEEK_TEMPERATURE", 0.2)

    lta_account_key: str | None = _api_key("LTA_ACCOUNT_KEY")
    lta_base_url: str = _env_text(
        "LTA_BASE_URL",
        "https://datamall2.mytransport.sg/ltaodataservice",
    ) or "https://datamall2.mytransport.sg/ltaodataservice"
    lta_timeout_seconds: float = _env_float("LTA_TIMEOUT_SECONDS", 12.0)


settings = IntelligenceSettings()
