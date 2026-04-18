import json
from datetime import datetime
from pathlib import Path


def _month_file(base: Path, series: str, year: int, month: int) -> Path:
    return base / series / f"{year:04d}" / f"{month:02d}.json"


def load_month(base: Path, series: str, year: int, month: int) -> list[dict]:
    """Load an archived month as a list of records. Returns [] if the file doesn't exist."""
    f = _month_file(base, series, year, month)
    if not f.exists():
        return []
    return json.loads(f.read_text())


def _save_month(base: Path, series: str, year: int, month: int, data: list[dict]) -> None:
    f = _month_file(base, series, year, month)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def append_measurements(base: Path, series: str, new_records: list[dict]) -> int:
    """Append records (each with 'ts' isoformat) to the appropriate monthly file.

    Idempotent on 'ts' collision — records with a timestamp already present are skipped.
    Returns the number of records actually added.
    """
    by_month: dict[tuple[int, int], list[dict]] = {}
    for r in new_records:
        dt = datetime.fromisoformat(r["ts"])
        by_month.setdefault((dt.year, dt.month), []).append(r)

    added_total = 0
    for (y, m), recs in by_month.items():
        existing = load_month(base, series, y, m)
        seen = {e["ts"] for e in existing}
        fresh = [r for r in recs if r["ts"] not in seen]
        if not fresh:
            continue
        merged = existing + fresh
        merged.sort(key=lambda r: r["ts"])
        _save_month(base, series, y, m, merged)
        added_total += len(fresh)
    return added_total
