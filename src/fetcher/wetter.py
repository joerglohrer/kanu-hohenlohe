# src/fetcher/wetter.py
import time
from dataclasses import dataclass
from datetime import datetime
from shapely.geometry import shape, Point

import requests


@dataclass(frozen=True)
class HourFc:
    ts: datetime
    precip_mm: float
    cloud_cover: int
    max_precip_mm: float = 0.0  # set only on aggregated area mean


@dataclass(frozen=True)
class GridForecast:
    hours: list[HourFc]


def build_grid_points(polygon_geojson: dict, step_deg: float = 0.1) -> list[tuple[float, float]]:
    """Build a lat/lon grid of points inside the given polygon.

    Uses strict containment (shapely .contains) — boundary points are excluded.
    Returns (lat, lon) tuples rounded to 4 decimals (≈ 10 m precision at 49°N).
    """
    geom = shape(polygon_geojson["geometry"])
    minx, miny, maxx, maxy = geom.bounds
    lat = miny
    pts = []
    while lat <= maxy:
        lon = minx
        while lon <= maxx:
            if geom.contains(Point(lon, lat)):
                pts.append((round(lat, 4), round(lon, 4)))
            lon += step_deg
        lat += step_deg
    return pts


def parse_openmeteo_response(raw: dict) -> GridForecast:
    """Parse an Open-Meteo forecast response dict into a typed GridForecast.

    Tolerates missing 'hourly' block, missing/None arrays, and null values
    inside arrays (coerced to 0.0 mm / 0 % cloud cover).
    """
    h = raw.get("hourly", {}) or {}
    times = h.get("time", []) or []
    precs = h.get("precipitation", []) or []
    clouds = h.get("cloud_cover", []) or []
    hours = [
        HourFc(
            ts=datetime.fromisoformat(t),
            precip_mm=float(p or 0.0),
            cloud_cover=int(c or 0),
        )
        for t, p, c in zip(times, precs, clouds)
    ]
    return GridForecast(hours=hours)


def fetch_openmeteo_batch(
    points: list[tuple[float, float]],
    timezone: str = "Europe/Berlin",
    forecast_days: int = 7,
    timeout: int = 30,
    retries: int = 3,
) -> list[GridForecast]:
    """Fetch forecast for all points in ONE HTTPS request. Retries with backoff.

    Raises RuntimeError on final failure — callers should catch and degrade.
    """
    if not points:
        return []
    lats = ",".join(f"{lat:.4f}" for lat, _ in points)
    lons = ",".join(f"{lon:.4f}" for _, lon in points)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": "precipitation,cloud_cover",
        "forecast_days": forecast_days,
        "timezone": timezone,
    }
    backoff = [0, 2, 5]
    last_err = None
    for attempt in range(retries):
        if backoff[attempt]:
            time.sleep(backoff[attempt])
        try:
            r = requests.get(
                url, params=params, timeout=timeout,
                headers={"User-Agent": "kanu-hohenlohe/0.1"},
            )
            r.raise_for_status()
            return parse_openmeteo_multi_response(r.json())
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            last_err = e
    raise RuntimeError(f"Open-Meteo unreachable after {retries} attempts: {last_err}")


def parse_openmeteo_multi_response(raw) -> list[GridForecast]:
    """Parse multi-location Open-Meteo response into one GridForecast per location.

    Single-location responses are dicts; multi-location are lists.
    """
    items = raw if isinstance(raw, list) else [raw]
    return [parse_openmeteo_response(item) for item in items]


def aggregate_area_mean(grids: list[GridForecast]) -> GridForecast:
    """Combine per-point forecasts into a catchment-mean forecast.

    Uses the first grid's hour index as reference and filters to grids that
    cover each hour. Computes mean precip, max precip, and mean cloud cover
    per hour index. Returns an empty GridForecast if `grids` is empty.
    """
    if not grids:
        return GridForecast(hours=[])
    ref = grids[0].hours
    hours = []
    for i, ref_hour in enumerate(ref):
        values = [g.hours[i].precip_mm for g in grids if i < len(g.hours)]
        clouds = [g.hours[i].cloud_cover for g in grids if i < len(g.hours)]
        mean_p = sum(values) / len(values)
        max_p = max(values)
        mean_c = int(sum(clouds) / len(clouds))
        hours.append(HourFc(ts=ref_hour.ts, precip_mm=round(mean_p, 2),
                            cloud_cover=mean_c, max_precip_mm=round(max_p, 2)))
    return GridForecast(hours=hours)
