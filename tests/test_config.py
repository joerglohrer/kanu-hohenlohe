# tests/test_config.py
from pathlib import Path
import pytest
from src.config import load_config, ConfigError

FIXTURE = """
gauges:
  doerzbach: "00061"
  jagstzell: "00048"
thresholds:
  min_cm: 40
  komfort_cm: 60
  hochwasser_cm: null
  max_regen_24h_mm: 5.0
  max_anstieg_cm_per_h: 3.0
catchment_geojson: "config/catchment.geojson"
cron:
  timezone: "Europe/Berlin"
"""

def test_load_config_returns_typed_object(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(FIXTURE)
    cfg = load_config(p)
    assert cfg.gauges["doerzbach"] == "00061"
    assert cfg.thresholds.min_cm == 40
    assert cfg.thresholds.komfort_cm == 60
    assert cfg.thresholds.hochwasser_cm is None
    assert cfg.thresholds.max_regen_24h_mm == 5.0

def test_load_config_rejects_missing_keys(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("gauges: {}\n")
    with pytest.raises(ConfigError):
        load_config(p)

def test_load_config_rejects_komfort_below_min(tmp_path):
    p = tmp_path / "config.yaml"
    bad = FIXTURE.replace("komfort_cm: 60", "komfort_cm: 30")
    p.write_text(bad)
    with pytest.raises(ConfigError, match="komfort_cm must be >= min_cm"):
        load_config(p)

def test_load_config_rejects_non_dict_gauges(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(FIXTURE.replace('gauges:\n  doerzbach: "00061"\n  jagstzell: "00048"', 'gauges: "oops"'))
    with pytest.raises(ConfigError, match="gauges"):
        load_config(p)

def test_load_config_rejects_missing_threshold_key(tmp_path):
    p = tmp_path / "config.yaml"
    bad = FIXTURE.replace("  max_regen_24h_mm: 5.0\n", "")
    p.write_text(bad)
    with pytest.raises(ConfigError, match="threshold"):
        load_config(p)

def test_load_config_rejects_non_numeric_threshold(tmp_path):
    p = tmp_path / "config.yaml"
    bad = FIXTURE.replace("min_cm: 40", 'min_cm: "abc"')
    p.write_text(bad)
    with pytest.raises(ConfigError, match="min_cm"):
        load_config(p)

def test_load_config_rejects_missing_timezone(tmp_path):
    p = tmp_path / "config.yaml"
    bad = FIXTURE.replace('cron:\n  timezone: "Europe/Berlin"', 'cron: {}')
    p.write_text(bad)
    with pytest.raises(ConfigError, match="timezone"):
        load_config(p)
