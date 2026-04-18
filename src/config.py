# src/config.py
from dataclasses import dataclass
from pathlib import Path
import yaml


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Thresholds:
    min_cm: int
    komfort_cm: int
    hochwasser_cm: int | None
    max_regen_24h_mm: float
    max_anstieg_cm_per_h: float


@dataclass(frozen=True)
class Config:
    gauges: dict[str, str]
    thresholds: Thresholds
    catchment_geojson: str
    timezone: str


REQUIRED = {"gauges", "thresholds", "catchment_geojson", "cron"}
REQUIRED_THRESHOLDS = {"min_cm", "komfort_cm", "hochwasser_cm",
                       "max_regen_24h_mm", "max_anstieg_cm_per_h"}


def _as_int(name: str, v):
    try:
        return int(v)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"{name} must be an integer, got {v!r}") from e


def _as_float(name: str, v):
    try:
        return float(v)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"{name} must be a number, got {v!r}") from e


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must be a mapping")
    missing = REQUIRED - raw.keys()
    if missing:
        raise ConfigError(f"missing keys: {sorted(missing)}")

    gauges = raw["gauges"]
    if not isinstance(gauges, dict):
        raise ConfigError("gauges must be a mapping")
    if not {"doerzbach", "jagstzell"} <= gauges.keys():
        raise ConfigError("gauges must include doerzbach and jagstzell")

    t = raw["thresholds"]
    if not isinstance(t, dict):
        raise ConfigError("thresholds must be a mapping")
    missing_t = REQUIRED_THRESHOLDS - t.keys()
    if missing_t:
        raise ConfigError(f"missing threshold keys: {sorted(missing_t)}")

    hw = t["hochwasser_cm"]
    thresholds = Thresholds(
        min_cm=_as_int("min_cm", t["min_cm"]),
        komfort_cm=_as_int("komfort_cm", t["komfort_cm"]),
        hochwasser_cm=_as_int("hochwasser_cm", hw) if hw is not None else None,
        max_regen_24h_mm=_as_float("max_regen_24h_mm", t["max_regen_24h_mm"]),
        max_anstieg_cm_per_h=_as_float("max_anstieg_cm_per_h", t["max_anstieg_cm_per_h"]),
    )
    if thresholds.komfort_cm < thresholds.min_cm:
        raise ConfigError("komfort_cm must be >= min_cm")

    cron = raw["cron"]
    if not isinstance(cron, dict) or "timezone" not in cron:
        raise ConfigError("cron.timezone is required")

    return Config(
        gauges=dict(gauges),
        thresholds=thresholds,
        catchment_geojson=str(raw["catchment_geojson"]),
        timezone=str(cron["timezone"]),
    )
