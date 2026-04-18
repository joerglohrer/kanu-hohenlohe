# backtest/run.py
import json
from pathlib import Path
from datetime import date, timedelta
from src.config import load_config
from src.engine.ampel import compute_ampel, DayInput, DayResult, Stufe


def compute_metrics(results: list[DayResult]) -> dict:
    """Compute simple stability metrics over a backtest run."""
    transitions = sum(1 for a, b in zip(results, results[1:]) if a.stufe != b.stufe)
    green = sum(1 for r in results if r.stufe == Stufe.GRUEN)
    yellow = sum(1 for r in results if r.stufe == Stufe.GELB)
    hw = sum(1 for r in results if r.stufe == Stufe.ROT_HOCHWASSER)
    wenig = sum(1 for r in results if r.stufe == Stufe.ROT_WENIG)
    return {
        "n_days": len(results),
        "transitions": transitions,
        "green_days": green,
        "yellow_days": yellow,
        "rot_hochwasser_days": hw,
        "rot_wenig_days": wenig,
        "flapping_rate_per_week": round(transitions / max(1, len(results)) * 7, 2),
    }


def run_backtest(data_dir: Path, config_path: Path, start: date, end: date,
                 out_html: Path) -> None:
    """Run the ampel engine over historical archive and write an HTML report.

    Loads daily pegel means from the HVZ archive. Rain is currently not loaded
    in this first cut (the weather archive covers too short a horizon for the
    initial 5-year backtest; the metric focuses on flapping/stability of the
    pegel-only ampel).
    """
    cfg = load_config(config_path)
    results: list[DayResult] = []
    day = start
    while day <= end:
        level, rain = _load_day(data_dir, day)
        if level is None:
            day += timedelta(days=1)
            continue
        results.append(compute_ampel(DayInput(
            day=day, level_cm=level, regen_24h_mm=rain,
            anstieg_cm_per_h=0.0, confidence=1.0), cfg.thresholds))
        day += timedelta(days=1)

    m = compute_metrics(results)
    tpl = (Path(__file__).parent / "report_template.html").read_text()
    out_html.write_text(
        tpl.replace("{{METRICS}}", json.dumps(m, indent=2))
            .replace("{{START}}", str(start))
            .replace("{{END}}", str(end))
            .replace("{{N}}", str(len(results)))
    )


def _load_day(data_dir: Path, day: date) -> tuple[float | None, float]:
    """Load daily-mean pegel for a given date from the archive. Rain is 0.0 for now."""
    f = data_dir / "hvz" / "doerzbach" / f"{day.year:04d}" / f"{day.month:02d}.json"
    if not f.exists():
        return None, 0.0
    rows = json.loads(f.read_text())
    todays = [r["w_cm"] for r in rows if r["ts"].startswith(day.isoformat())]
    if not todays:
        return None, 0.0
    return sum(todays) / len(todays), 0.0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data")
    p.add_argument("--config", default="config/config.yaml")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--out", default="backtest/report.html")
    a = p.parse_args()
    run_backtest(Path(a.data), Path(a.config),
                 date.fromisoformat(a.start), date.fromisoformat(a.end),
                 Path(a.out))
