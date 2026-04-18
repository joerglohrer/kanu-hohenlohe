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


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must be a mapping")
    missing = REQUIRED - raw.keys()
    if missing:
        raise ConfigError(f"missing keys: {sorted(missing)}")

    gauges = raw["gauges"]
    if not {"doerzbach", "unterregenbach"} <= gauges.keys():
        raise ConfigError("gauges must include doerzbach and unterregenbach")

    t = raw["thresholds"]
    thresholds = Thresholds(
        min_cm=int(t["min_cm"]),
        komfort_cm=int(t["komfort_cm"]),
        hochwasser_cm=int(t["hochwasser_cm"]) if t.get("hochwasser_cm") is not None else None,
        max_regen_24h_mm=float(t["max_regen_24h_mm"]),
        max_anstieg_cm_per_h=float(t["max_anstieg_cm_per_h"]),
    )
    if thresholds.komfort_cm < thresholds.min_cm:
        raise ConfigError("komfort_cm must be >= min_cm")

    return Config(
        gauges=dict(gauges),
        thresholds=thresholds,
        catchment_geojson=str(raw["catchment_geojson"]),
        timezone=str(raw["cron"]["timezone"]),
    )
