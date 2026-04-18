# src/engine/ampel.py
from dataclasses import dataclass
from datetime import date
from enum import Enum
from src.config import Thresholds


class Stufe(str, Enum):
    GRUEN = "gruen"
    GELB = "gelb"
    ROT_WENIG = "rot_wenig"
    ROT_HOCHWASSER = "rot_hochwasser"
    UNGEWISS = "ungewiss"


EMOJI = {
    Stufe.GRUEN: "🛶",
    Stufe.GELB: "😐",
    Stufe.ROT_WENIG: "🚫",
    Stufe.ROT_HOCHWASSER: "⚠️",
    Stufe.UNGEWISS: "·",
}


@dataclass(frozen=True)
class DayInput:
    day: date
    level_cm: float
    regen_24h_mm: float
    anstieg_cm_per_h: float
    confidence: float  # 0..1


@dataclass(frozen=True)
class DayResult:
    day: date
    stufe: Stufe
    begruendung: str
    level_cm: float
    regen_24h_mm: float
    confidence: float


CONFIDENCE_UNGEWISS = 0.5
EXTREME_RISE_FACTOR = 3  # "extreme" = 3x max_anstieg threshold


def compute_ampel(day: DayInput, t: Thresholds) -> DayResult:
    if day.confidence < CONFIDENCE_UNGEWISS:
        return DayResult(day.day, Stufe.UNGEWISS, "Prognose zu unsicher",
                         day.level_cm, day.regen_24h_mm, day.confidence)

    if day.anstieg_cm_per_h >= t.max_anstieg_cm_per_h * EXTREME_RISE_FACTOR:
        return DayResult(day.day, Stufe.ROT_HOCHWASSER,
                         f"Extremer Pegelanstieg ({day.anstieg_cm_per_h:.1f} cm/h)",
                         day.level_cm, day.regen_24h_mm, day.confidence)

    if t.hochwasser_cm is not None and day.level_cm >= t.hochwasser_cm:
        return DayResult(day.day, Stufe.ROT_HOCHWASSER,
                         f"Pegel ≥ Hochwasser-Meldestufe ({t.hochwasser_cm} cm)",
                         day.level_cm, day.regen_24h_mm, day.confidence)

    if day.level_cm < t.min_cm:
        return DayResult(day.day, Stufe.ROT_WENIG,
                         f"Pegel {day.level_cm:.0f} cm unter Minimum {t.min_cm} cm",
                         day.level_cm, day.regen_24h_mm, day.confidence)

    if day.level_cm < t.komfort_cm:
        return DayResult(day.day, Stufe.GELB,
                         f"Pegel {day.level_cm:.0f} cm — Ausleitungen umtragen",
                         day.level_cm, day.regen_24h_mm, day.confidence)

    if day.regen_24h_mm > t.max_regen_24h_mm:
        return DayResult(day.day, Stufe.GELB,
                         f"Regen im Einzugsgebiet {day.regen_24h_mm:.1f} mm/24h",
                         day.level_cm, day.regen_24h_mm, day.confidence)

    if day.anstieg_cm_per_h >= t.max_anstieg_cm_per_h:
        return DayResult(day.day, Stufe.GELB,
                         f"Pegelanstieg {day.anstieg_cm_per_h:.1f} cm/h",
                         day.level_cm, day.regen_24h_mm, day.confidence)

    return DayResult(day.day, Stufe.GRUEN,
                     f"Pegel {day.level_cm:.0f} cm, trocken, stabil",
                     day.level_cm, day.regen_24h_mm, day.confidence)
