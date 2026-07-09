"""Configuration used only by service-side engineer B modules.

All values are read from environment variables so no secret is committed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - environment variables still work
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVICE_B_ENV_FILE = PROJECT_ROOT / "service-b.env"

if load_dotenv is not None:
    # 服务端 B 使用独立配置文件，避免其变量被服务端 A 的 Pydantic Settings
    # 当作未声明字段并触发 extra_forbidden。
    load_dotenv(dotenv_path=SERVICE_B_ENV_FILE, override=False)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class IntelligenceSettings:
    timezone: str = os.getenv("BUSMIND_TIMEZONE", "Asia/Shanghai")

    # Optional prediction adapters supplied later by the data-processing engineer.
    eta_predictor_path: str = os.getenv(
        "BUSMIND_ETA_PREDICTOR",
        "algorithm.eta_prediction.models.predict_eta:predict_eta",
    )
    load_predictor_path: str = os.getenv(
        "BUSMIND_LOAD_PREDICTOR",
        "algorithm.load_prediction.models.predict_load:predict_load",
    )

    default_vehicle_capacity: int = _env_int("BUSMIND_DEFAULT_CAPACITY", 60)
    default_walking_speed_mps: float = _env_float("BUSMIND_WALKING_SPEED_MPS", 1.2)
    walking_road_factor: float = _env_float("BUSMIND_WALKING_ROAD_FACTOR", 1.25)

    # Latest interface-document scoring rule: load/walk/transfer only.
    weight_load: float = _env_float("BUSMIND_WEIGHT_LOAD", 0.50)
    weight_walk: float = _env_float("BUSMIND_WEIGHT_WALK", 0.30)
    weight_transfer: float = _env_float("BUSMIND_WEIGHT_TRANSFER", 0.20)

    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    deepseek_timeout_seconds: float = _env_float("DEEPSEEK_TIMEOUT_SECONDS", 20.0)
    deepseek_max_tokens: int = _env_int("DEEPSEEK_MAX_TOKENS", 700)
    deepseek_temperature: float = _env_float("DEEPSEEK_TEMPERATURE", 0.2)

    # Optional LTA DataMall Bus Arrival integration for real-time ETA/load.
    lta_account_key: str | None = os.getenv("LTA_ACCOUNT_KEY")
    lta_base_url: str = os.getenv(
        "LTA_BASE_URL",
        "https://datamall2.mytransport.sg/ltaodataservice",
    )
    lta_timeout_seconds: float = _env_float("LTA_TIMEOUT_SECONDS", 12.0)


settings = IntelligenceSettings()
