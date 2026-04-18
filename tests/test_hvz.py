# tests/test_hvz.py
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from src.fetcher.hvz import parse_hvz_response, HVZResult

FIX = Path(__file__).parent / "fixtures"

def test_parse_ok():
    raw = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())
    r = parse_hvz_response(raw)
    assert r.gauge_id == "00061"
    assert r.name == "Dörzbach"
    assert len(r.measurements) >= 1
    assert r.latest_level_cm > 0
    assert r.latest_ts is not None
    assert r.hmo_stufe_1_cm == 180

def test_parse_wartung_returns_empty_measurements():
    raw = json.loads((FIX / "hvz_doerzbach_wartung.json").read_text())
    r = parse_hvz_response(raw)
    assert r.measurements == []
    assert r.latest_level_cm is None

def test_compute_tendenz_cm_per_hour():
    from src.fetcher.hvz import compute_tendenz_cm_per_h
    base = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    series = [
        (base, 60.0),
        (base + timedelta(minutes=15), 61.0),
        (base + timedelta(minutes=30), 62.0),
        (base + timedelta(minutes=45), 63.0),
        (base + timedelta(minutes=60), 64.0),
    ]
    # 4 cm rise over 60 minutes → 4 cm/h
    assert abs(compute_tendenz_cm_per_h(series) - 4.0) < 0.01

def test_compute_tendenz_returns_zero_for_insufficient_data():
    from src.fetcher.hvz import compute_tendenz_cm_per_h
    assert compute_tendenz_cm_per_h([]) == 0.0
