import json
from datetime import date, datetime, timezone
from pathlib import Path
from src.engine.ampel import Stufe, DayResult
from src.storage.status import write_status, rotate_prev


def _r(day, stufe, level=66.0):
    return DayResult(day=day, stufe=stufe, begruendung="test",
                     level_cm=level, regen_24h_mm=0.0, confidence=1.0)


def test_write_status_produces_valid_json(tmp_path):
    days = [_r(date(2026, 4, 18), Stufe.GRUEN), _r(date(2026, 4, 19), Stufe.GELB, 55.0)]
    write_status(
        tmp_path / "status.json",
        generated_at=datetime(2026, 4, 18, 11, 15, tzinfo=timezone.utc),
        latest_level_cm=68.0, latest_q_m3s=4.8,
        tendenz_cm_per_h=0.3,
        hvz_stale=False, hvz_last_ts=datetime(2026, 4, 18, 11, 0, tzinfo=timezone.utc),
        hmo_stufe_1_cm=180,
        regen_24h_mean_mm=1.2, regen_24h_max_mm=3.1,
        days=days,
    )
    f = tmp_path / "status.json"
    data = json.loads(f.read_text())
    assert data["latest_level_cm"] == 68.0
    assert data["hvz_stale"] is False
    assert data["days"][0]["stufe"] == "gruen"
    assert data["days"][0]["emoji"] == "🛶"
    assert len(data["days"]) == 2


def test_rotate_prev_copies_previous_status(tmp_path):
    cur = tmp_path / "status.json"
    prv = tmp_path / "status.prev.json"
    cur.write_text('{"a": 1}')
    rotate_prev(cur, prv)
    assert prv.read_text() == '{"a": 1}'


def test_rotate_prev_noop_when_missing(tmp_path):
    cur = tmp_path / "status.json"
    prv = tmp_path / "status.prev.json"
    rotate_prev(cur, prv)  # must not raise
    assert not prv.exists()
