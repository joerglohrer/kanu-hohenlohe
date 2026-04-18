# tests/test_main_integration.py
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from src import main as orchestrator

FIX = Path(__file__).parent / "fixtures"

def test_full_run_writes_status_and_archives(tmp_path):
    cfg_yaml = tmp_path / "config.yaml"
    cfg_yaml.write_text((Path("config") / "config.yaml").read_text())
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    hvz_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())
    unter_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())  # reuse fixture
    meteo = json.loads((FIX / "openmeteo_forecast.json").read_text())

    with patch("src.main.fetch_hvz_raw", side_effect=[hvz_ok, unter_ok]), \
         patch("src.main.fetch_openmeteo_raw", return_value=meteo), \
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
    assert (data_dir / "hvz" / "doerzbach" / "2026" / "04.json").exists()
