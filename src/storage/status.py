import json
import shutil
from datetime import datetime
from pathlib import Path
from src.engine.ampel import DayResult, EMOJI


def write_status(
    path: Path,
    *,
    generated_at: datetime,
    latest_level_cm: float | None,
    latest_q_m3s: float | None,
    tendenz_cm_per_h: float,
    hvz_stale: bool,
    hvz_last_ts: datetime | None,
    hmo_stufe_1_cm: int | None,
    regen_24h_mean_mm: float,
    regen_24h_max_mm: float,
    days: list[DayResult],
    weather_stale: bool = False,
) -> None:
    """Write the single-source-of-truth status JSON for the frontend.

    Emoji is denormalized into each day for zero-logic rendering in the browser.
    """
    payload = {
        "generated_at": generated_at.isoformat(),
        "latest_level_cm": latest_level_cm,
        "latest_q_m3s": latest_q_m3s,
        "tendenz_cm_per_h": tendenz_cm_per_h,
        "hvz_stale": hvz_stale,
        "hvz_last_ts": hvz_last_ts.isoformat() if hvz_last_ts else None,
        "hmo_stufe_1_cm": hmo_stufe_1_cm,
        "regen_24h_mean_mm": regen_24h_mean_mm,
        "regen_24h_max_mm": regen_24h_max_mm,
        "weather_stale": weather_stale,
        "days": [
            {
                "day": d.day.isoformat(),
                "stufe": d.stufe.value,
                "emoji": EMOJI[d.stufe],
                "begruendung": d.begruendung,
                "level_cm": d.level_cm,
                "regen_24h_mm": d.regen_24h_mm,
                "confidence": d.confidence,
            }
            for d in days
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def rotate_prev(current: Path, previous: Path) -> None:
    """Copy current status to previous-status path. No-op if current is missing."""
    if current.exists():
        shutil.copy2(current, previous)
