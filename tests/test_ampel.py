# tests/test_ampel.py
from datetime import date
from src.config import Thresholds
from src.engine.ampel import compute_ampel, Stufe, DayInput, DayResult

TH = Thresholds(
    min_cm=40, komfort_cm=60, hochwasser_cm=180,
    max_regen_24h_mm=5.0, max_anstieg_cm_per_h=3.0,
)

def _d(level, regen_24h=0.0, anstieg=0.0, confidence=1.0):
    return DayInput(
        day=date(2026, 4, 18),
        level_cm=level,
        regen_24h_mm=regen_24h,
        anstieg_cm_per_h=anstieg,
        confidence=confidence,
    )

def test_green_when_comfortable_and_dry():
    r = compute_ampel(_d(level=70, regen_24h=1.0, anstieg=0.5), TH)
    assert r.stufe == Stufe.GRUEN

def test_yellow_when_between_min_and_komfort():
    r = compute_ampel(_d(level=55), TH)
    assert r.stufe == Stufe.GELB

def test_yellow_when_comfortable_but_raining():
    r = compute_ampel(_d(level=70, regen_24h=8.0), TH)
    assert r.stufe == Stufe.GELB
    assert "regen" in r.begruendung.lower()

def test_yellow_when_comfortable_but_rising_fast():
    r = compute_ampel(_d(level=70, anstieg=5.0), TH)
    assert r.stufe == Stufe.GELB
    assert "anstieg" in r.begruendung.lower()

def test_red_too_little_water():
    r = compute_ampel(_d(level=30), TH)
    assert r.stufe == Stufe.ROT_WENIG

def test_red_hochwasser_by_level():
    r = compute_ampel(_d(level=200), TH)
    assert r.stufe == Stufe.ROT_HOCHWASSER

def test_red_hochwasser_by_extreme_rise():
    r = compute_ampel(_d(level=70, anstieg=10.0), TH)
    assert r.stufe == Stufe.ROT_HOCHWASSER

def test_missing_hochwasser_threshold_skips_hochwasser_check():
    th = Thresholds(40, 60, None, 5.0, 3.0)
    r = compute_ampel(_d(level=200), th)
    # still Grün because hochwasser_cm is unknown; only extreme rise could flag it
    assert r.stufe == Stufe.GRUEN

def test_low_confidence_marks_ungewiss():
    r = compute_ampel(_d(level=70, confidence=0.3), TH)
    assert r.stufe == Stufe.UNGEWISS

def test_each_result_has_nonempty_reason():
    for level in (30, 55, 70, 200):
        r = compute_ampel(_d(level=level), TH)
        assert r.begruendung.strip()
