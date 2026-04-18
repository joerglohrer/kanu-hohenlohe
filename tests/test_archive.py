from datetime import datetime, timezone
from pathlib import Path
from src.storage.archive import append_measurements, load_month

def _m(ts, w):
    return {"ts": ts.isoformat(), "w_cm": w}

def test_append_creates_monthly_file(tmp_path):
    ts = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    n = append_measurements(tmp_path, "doerzbach", [_m(ts, 66.0)])
    assert n == 1
    f = tmp_path / "doerzbach" / "2026" / "04.json"
    assert f.exists()

def test_append_is_idempotent(tmp_path):
    ts = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    append_measurements(tmp_path, "doerzbach", [_m(ts, 66.0)])
    n = append_measurements(tmp_path, "doerzbach", [_m(ts, 66.0)])
    assert n == 0  # duplicate not added
    loaded = load_month(tmp_path, "doerzbach", 2026, 4)
    assert len(loaded) == 1

def test_append_across_months_writes_separate_files(tmp_path):
    ts_apr = datetime(2026, 4, 30, 23, 45, tzinfo=timezone.utc)
    ts_may = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    append_measurements(tmp_path, "doerzbach", [_m(ts_apr, 66), _m(ts_may, 67)])
    assert (tmp_path / "doerzbach" / "2026" / "04.json").exists()
    assert (tmp_path / "doerzbach" / "2026" / "05.json").exists()

def test_append_preserves_order(tmp_path):
    t1 = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 4, 18, 9, 15, tzinfo=timezone.utc)
    append_measurements(tmp_path, "doerzbach", [_m(t2, 67), _m(t1, 66)])
    loaded = load_month(tmp_path, "doerzbach", 2026, 4)
    assert loaded[0]["ts"] == t1.isoformat()
    assert loaded[1]["ts"] == t2.isoformat()
