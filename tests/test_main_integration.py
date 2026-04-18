# tests/test_main_integration.py
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from src import main as orchestrator
from src.fetcher.wetter import parse_openmeteo_response

FIX = Path(__file__).parent / "fixtures"


def _make_grids(n=1):
    """Return n GridForecast objects from the fixture."""
    raw = json.loads((FIX / "openmeteo_forecast.json").read_text())
    fc = parse_openmeteo_response(raw)
    return [fc] * n


def test_full_run_writes_status_and_archives(tmp_path):
    cfg_yaml = tmp_path / "config.yaml"
    cfg_yaml.write_text((Path("config") / "config.yaml").read_text())
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    hvz_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())
    unter_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())  # reuse fixture

    with patch("src.main.fetch_hvz_raw", side_effect=[hvz_ok, unter_ok]), \
         patch("src.main.fetch_openmeteo_batch", return_value=_make_grids()), \
         patch("src.main.send_push_if_needed") as push:
        orchestrator.run(
            config_path=cfg_yaml,
            data_dir=data_dir,
            catchment_path=Path("config/catchment.geojson"),
            now=datetime(2026, 4, 18, 11, 0, tzinfo=timezone.utc),
        )

    status = json.loads((data_dir / "status.json").read_text())
    assert status["latest_level_cm"] is not None
    assert len(status["days"]) == 8  # today + 7
    assert status["weather_stale"] is False
    assert (data_dir / "hvz" / "doerzbach" / "2026" / "04.json").exists()


def test_run_degrades_gracefully_when_weather_fails(tmp_path):
    cfg_yaml = tmp_path / "config.yaml"
    cfg_yaml.write_text((Path("config") / "config.yaml").read_text())
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    hvz_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())
    unter_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())

    with patch("src.main.fetch_hvz_raw", side_effect=[hvz_ok, unter_ok]), \
         patch("src.main.fetch_openmeteo_batch", side_effect=RuntimeError("timeout")), \
         patch("src.main.send_push_if_needed"):
        orchestrator.run(
            config_path=cfg_yaml,
            data_dir=data_dir,
            catchment_path=Path("config/catchment.geojson"),
            now=datetime(2026, 4, 18, 11, 0, tzinfo=timezone.utc),
        )

    status = json.loads((data_dir / "status.json").read_text())
    assert status["weather_stale"] is True
    assert len(status["days"]) == 8
    # day 0 has confidence=1.0, should not be UNGEWISS
    from src.engine.ampel import Stufe
    assert status["days"][0]["stufe"] != Stufe.UNGEWISS.value
