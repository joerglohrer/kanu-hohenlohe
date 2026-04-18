# tests/test_backtest.py
from datetime import date
from src.engine.ampel import Stufe, DayResult
from backtest.run import compute_metrics

def test_flapping_rate_counts_transitions():
    results = [
        DayResult(day=date(2026,1,i+1), stufe=s, begruendung="",
                  level_cm=50, regen_24h_mm=0, confidence=1.0)
        for i, s in enumerate([Stufe.GRUEN, Stufe.GELB, Stufe.GRUEN, Stufe.GRUEN, Stufe.GELB])
    ]
    m = compute_metrics(results)
    assert m["transitions"] == 3   # GR->GE, GE->GR, GR->GE
    assert m["green_days"] == 3
