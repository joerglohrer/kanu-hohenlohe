# src/fetcher/hvz.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HVZMeasurement:
    ts: datetime
    level_cm: float
    q_m3s: float | None


@dataclass(frozen=True)
class HVZForecastPoint:
    ts: datetime
    level_cm: float


@dataclass(frozen=True)
class HVZResult:
    gauge_id: str
    name: str
    measurements: list[HVZMeasurement]
    forecast: list[HVZForecastPoint]
    hmo_stufe_1_cm: int | None
    latest_ts: datetime | None
    latest_level_cm: float | None


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def parse_hvz_response(raw: dict) -> HVZResult:
    pegel = raw.get("pegel", {})
    vals = raw.get("values", []) or []
    fc = raw.get("forecast", []) or []
    stamm = raw.get("stammdaten", {}) or {}

    measurements = [
        HVZMeasurement(
            ts=_parse_ts(v["ts"]),
            level_cm=float(v["w_cm"]),
            q_m3s=float(v["q_m3s"]) if v.get("q_m3s") is not None else None,
        )
        for v in vals
    ]
    forecast = [
        HVZForecastPoint(ts=_parse_ts(v["ts"]), level_cm=float(v["w_cm"]))
        for v in fc
    ]
    latest = measurements[-1] if measurements else None

    return HVZResult(
        gauge_id=str(pegel.get("id", "")),
        name=str(pegel.get("name", "")),
        measurements=measurements,
        forecast=forecast,
        hmo_stufe_1_cm=int(stamm["hmo_stufe_1_cm"]) if stamm.get("hmo_stufe_1_cm") is not None else None,
        latest_ts=latest.ts if latest else None,
        latest_level_cm=latest.level_cm if latest else None,
    )


def compute_tendenz_cm_per_h(series: list[tuple[datetime, float]]) -> float:
    """Linear slope (cm/h) over the given series. Returns 0.0 if < 2 points."""
    if len(series) < 2:
        return 0.0
    t0, l0 = series[0]
    tn, ln = series[-1]
    hours = (tn - t0).total_seconds() / 3600.0
    if hours <= 0:
        return 0.0
    return (ln - l0) / hours
