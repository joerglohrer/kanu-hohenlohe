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

def test_parse_tolerates_explicit_nulls():
    raw = {"pegel": None, "values": None, "forecast": None, "stammdaten": None}
    r = parse_hvz_response(raw)
    assert r.gauge_id == ""
    assert r.name == ""
    assert r.measurements == []
    assert r.forecast == []
    assert r.hmo_stufe_1_cm is None


def test_fetch_hvz_live_returns_compatible_dict(monkeypatch):
    """Smoke test: fetch_hvz_live returns something parse_hvz_response can consume."""
    from src.fetcher.hvz import fetch_hvz_live

    # Minimal JS stammdaten snippet with one gauge entry
    _FAKE_STMN_JS = """
// Stammdaten
HVZ_Site.PEG_DB =
[
 ['00061','Dörzbach','Jagst',5,'66','cm','18.04.2026 09:15 MESZ','4.70','m³/s','18.04.2026 09:15 MESZ',0,'DOERZBACH',1,1,1,1,1,1,3552228,5470293,9.719182,49.368446,32552132,5468544,'2.20','1030','237.51','NHN+m','72.595','0',225,331,366,404,434,136,257,307,373,425,63,10.9,'',37,1.63,'',20,'','',0.20,'1991-2025','10.08.2022','','Regionalisierung (Stand: 12/2024)','','Regionalisierung (Stand: 01.03.2016)','','Regionalisierung (Stand: 01.03.2016)','Berechnet aus NQ und aktueller WQ-Beziehung.','Tagesmittelwerte',0,1,1,'Regierungspräsidium Stuttgart','https://rp.baden-wuerttemberg.de/','','','3.95!21.12.1993|4.40!29.12.1947',290,207,1,1],
];
"""

    class _R:
        content = _FAKE_STMN_JS.encode("utf-8")
        def raise_for_status(self):
            pass

    def _fake_get(*args, **kwargs):
        return _R()

    monkeypatch.setattr("src.fetcher.hvz.requests.get", _fake_get)
    raw = fetch_hvz_live("00061")

    # must be a dict with the four top-level keys (even if mostly empty)
    assert isinstance(raw, dict)
    for key in ("pegel", "values", "forecast", "stammdaten"):
        assert key in raw, f"missing key: {key}"

    # parse must not crash
    r = parse_hvz_response(raw)
    assert r.gauge_id == "00061"
    assert r.name == "Dörzbach"
    # values list has one entry from the current snapshot
    assert len(r.measurements) == 1
    assert r.measurements[0].level_cm == 66.0
    assert r.measurements[0].q_m3s == 4.70
    # HMO Stufe 1 = field[30] = 225 cm
    assert r.hmo_stufe_1_cm == 225
    assert r.latest_level_cm == 66.0
    assert r.latest_ts is not None
