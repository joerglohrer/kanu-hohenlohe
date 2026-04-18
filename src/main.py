# src/main.py
import json
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import load_config
from src.engine.ampel import compute_ampel, DayInput
from src.fetcher.hvz import fetch_hvz_live, parse_hvz_response, compute_tendenz_cm_per_h
from src.fetcher.wetter import (
    build_grid_points, aggregate_area_mean, GridForecast, fetch_openmeteo_batch,
)
from src.storage.archive import append_measurements
from src.storage.status import write_status, rotate_prev
from src.notify.telegram import should_push, compose_message, send_push, PushDecision


def fetch_hvz_raw(gauge_id: str) -> dict:
    """Live HVZ fetch via JS stammdaten scraping (see src.fetcher.hvz.fetch_hvz_live)."""
    return fetch_hvz_live(gauge_id)


def send_push_if_needed(status_path: Path, prev_path: Path, last_push_path: Path,
                        now: datetime) -> None:
    """Read .last_push ts and send a Telegram push if should_push decides GREEN_WINDOW."""
    last_ts = None
    if last_push_path.exists():
        last_ts = datetime.fromisoformat(last_push_path.read_text().strip())
    d = should_push(status_path, prev_path, last_ts, now)
    if d.kind == PushDecision.GREEN_WINDOW:
        status = json.loads(status_path.read_text())
        send_push(compose_message(status))
        last_push_path.write_text(now.isoformat())


def run(*, config_path: Path, data_dir: Path, catchment_path: Path,
        now: datetime | None = None) -> None:
    """One cron iteration: fetch, compute, persist, notify."""
    cfg = load_config(config_path)
    now = now or datetime.now(tz=timezone.utc)

    # Fetch HVZ for both gauges
    hvz_raw_d = fetch_hvz_raw(cfg.gauges["doerzbach"])
    hvz_raw_u = fetch_hvz_raw(cfg.gauges["jagstzell"])
    hvz_d = parse_hvz_response(hvz_raw_d)
    hvz_u = parse_hvz_response(hvz_raw_u)

    # Archive pegel
    append_measurements(
        data_dir / "hvz", "doerzbach",
        [{"ts": m.ts.isoformat(), "w_cm": m.level_cm, "q_m3s": m.q_m3s} for m in hvz_d.measurements],
    )
    append_measurements(
        data_dir / "hvz", "jagstzell",
        [{"ts": m.ts.isoformat(), "w_cm": m.level_cm, "q_m3s": m.q_m3s} for m in hvz_u.measurements],
    )

    # Weather — single batch request for all catchment points, retried, graceful degradation
    polygon = json.loads(catchment_path.read_text())
    points = build_grid_points(polygon, step_deg=0.1)
    weather_stale = False
    try:
        grids = fetch_openmeteo_batch(points)
        area = aggregate_area_mean(grids)
    except Exception as e:
        print(f"[warn] Weather fetch failed: {e}. Continuing pegel-only.")
        area = GridForecast(hours=[])
        weather_stale = True

    # Archive weather (area mean only)
    append_measurements(
        data_dir / "weather", "area_mean",
        [{"ts": h.ts.isoformat(), "precip_mm": h.precip_mm,
          "max_precip_mm": h.max_precip_mm, "cloud_cover": h.cloud_cover}
         for h in area.hours],
    )

    # Compute ampel for today + next 7 days
    today = now.astimezone(ZoneInfo("Europe/Berlin")).date()
    days_out = []
    level = hvz_d.latest_level_cm or 0.0
    tend = compute_tendenz_cm_per_h([(m.ts, m.level_cm) for m in hvz_d.measurements])

    for offset in range(8):
        d = today + timedelta(days=offset)
        regen_24h = sum(h.precip_mm for h in area.hours if h.ts.date() == d) if area.hours else 0.0  # h.ts is naive Berlin-local
        fc_for_day = [p for p in hvz_d.forecast if p.ts.date() == d]
        level_day = fc_for_day[-1].level_cm if fc_for_day else level
        confidence = 1.0 if offset < 2 else max(0.0, 1.0 - (offset - 1) * 0.2)
        day_in = DayInput(day=d, level_cm=level_day,
                          regen_24h_mm=regen_24h,
                          anstieg_cm_per_h=tend if offset == 0 else 0.0,
                          confidence=confidence)
        days_out.append(compute_ampel(day_in, cfg.thresholds))

    # Rotate prev and write status
    status_path = data_dir / "status.json"
    prev_path = data_dir / "status.prev.json"
    rotate_prev(status_path, prev_path)

    # Use learned HMO value if config had null
    hmo_cm = cfg.thresholds.hochwasser_cm or hvz_d.hmo_stufe_1_cm

    # Staleness: HVZ data is stale if no measurement in the last 6 hours
    hvz_stale = hvz_d.latest_ts is None or (now - hvz_d.latest_ts).total_seconds() > 6 * 3600

    write_status(
        status_path,
        generated_at=now,
        latest_level_cm=hvz_d.latest_level_cm,
        latest_q_m3s=hvz_d.measurements[-1].q_m3s if hvz_d.measurements else None,
        tendenz_cm_per_h=tend,
        hvz_stale=hvz_stale,
        hvz_last_ts=hvz_d.latest_ts,
        hmo_stufe_1_cm=hmo_cm,
        regen_24h_mean_mm=round(
            sum(h.precip_mm for h in area.hours[:24]) / max(1, min(24, len(area.hours))), 2
        ),
        regen_24h_max_mm=max((h.max_precip_mm for h in area.hours[:24]), default=0.0),
        days=days_out,
        weather_stale=weather_stale,
    )

    send_push_if_needed(status_path, prev_path, data_dir / ".last_push", now)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config/config.yaml")
    p.add_argument("--data", default="data")
    p.add_argument("--catchment", default="config/catchment.geojson")
    args = p.parse_args()
    run(config_path=Path(args.config), data_dir=Path(args.data),
        catchment_path=Path(args.catchment))
