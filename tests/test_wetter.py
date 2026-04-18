# tests/test_wetter.py
import json
from pathlib import Path
from src.fetcher.wetter import (
    build_grid_points, parse_openmeteo_response, aggregate_area_mean, GridForecast,
)

FIX = Path(__file__).parent / "fixtures"

def test_build_grid_points_returns_inside_polygon_only():
    polygon = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[
            [10.0, 49.0], [10.2, 49.0], [10.2, 49.2], [10.0, 49.2], [10.0, 49.0]
        ]]},
    }
    pts = build_grid_points(polygon, step_deg=0.1)
    assert len(pts) >= 1
    for lat, lon in pts:
        assert 49.0 <= lat <= 49.2
        assert 10.0 <= lon <= 10.2

def test_parse_openmeteo_returns_hourly_series():
    raw = json.loads((FIX / "openmeteo_forecast.json").read_text())
    fc = parse_openmeteo_response(raw)
    assert len(fc.hours) > 0
    h0 = fc.hours[0]
    assert h0.ts is not None
    assert h0.precip_mm >= 0.0
    assert 0 <= h0.cloud_cover <= 100

def test_aggregate_area_mean():
    from datetime import datetime, timezone
    from src.fetcher.wetter import HourFc, GridForecast
    ts = datetime(2026, 4, 18, 12, tzinfo=timezone.utc)
    g1 = GridForecast(hours=[HourFc(ts=ts, precip_mm=2.0, cloud_cover=50)])
    g2 = GridForecast(hours=[HourFc(ts=ts, precip_mm=4.0, cloud_cover=70)])
    agg = aggregate_area_mean([g1, g2])
    assert agg.hours[0].precip_mm == 3.0
    assert agg.hours[0].max_precip_mm == 4.0
