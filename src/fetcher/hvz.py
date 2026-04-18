# src/fetcher/hvz.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HVZMeasurement:
    ts: datetime
    level_cm: float
    q_m3s: float | None


@dataclass(frozen=True)
class HVZForecastPoint:
    ts: datetime
    level_cm: float


@dataclass(frozen=True)
class HVZResult:
    gauge_id: str
    name: str
    measurements: list[HVZMeasurement]
    forecast: list[HVZForecastPoint]
    hmo_stufe_1_cm: int | None
    latest_ts: datetime | None
    latest_level_cm: float | None


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def parse_hvz_response(raw: dict) -> HVZResult:
    """Parse an HVZ API response dict (fixture or live) into a typed HVZResult.

    Tolerates missing keys and explicit nulls (returns sensible defaults).
    """
    pegel = raw.get("pegel") or {}
    vals = raw.get("values") or []
    fc = raw.get("forecast") or []
    stamm = raw.get("stammdaten") or {}

    measurements = [
        HVZMeasurement(
            ts=_parse_ts(v["ts"]),
            level_cm=float(v["w_cm"]),
            q_m3s=float(v["q_m3s"]) if v.get("q_m3s") is not None else None,
        )
        for v in vals
    ]
    forecast = [
        HVZForecastPoint(ts=_parse_ts(v["ts"]), level_cm=float(v["w_cm"]))
        for v in fc
    ]
    latest = measurements[-1] if measurements else None

    return HVZResult(
        gauge_id=str(pegel.get("id", "")),
        name=str(pegel.get("name", "")),
        measurements=measurements,
        forecast=forecast,
        hmo_stufe_1_cm=int(stamm["hmo_stufe_1_cm"]) if stamm.get("hmo_stufe_1_cm") is not None else None,
        latest_ts=latest.ts if latest else None,
        latest_level_cm=latest.level_cm if latest else None,
    )


import csv
import io
import logging
import re
from datetime import timedelta, timezone

import requests
from bs4 import BeautifulSoup  # noqa: F401 – kept for optional HTML inspection

_log = logging.getLogger(__name__)

HVZ_STMN_URL = "https://www.hvz.baden-wuerttemberg.de/js/hvz_peg_stmn.js"
USER_AGENT = "kanu-hohenlohe/0.1 (+https://github.com/)"

# Column indices from hvz_peg_var.js (stable since at least 2024-04-25)
_POS_DASA = 0   # gauge ID string e.g. '00061'
_POS_NAME = 1   # gauge name
_POS_GEW = 2    # watercourse name
_POS_W = 4      # current water level value (str or '--')
_POS_WD = 5     # water level unit ('cm' / 'm')
_POS_WZ = 6     # water level timestamp ('DD.MM.YYYY HH:MM MESZ')
_POS_Q = 7      # current discharge value
_POS_QD = 8     # discharge unit
_POS_QZ = 9     # discharge timestamp
_POS_HMO = 24   # Hochwassermeldeordnung Stufe 1 in m (string, e.g. '2.20') — convert ×100 → cm
_POS_HWB = 30   # Statistischer Hochwasserrichtwert 1 in cm (MHW / HHW-Stufe 1), NOT the Meldestufe


def _parse_stmn_ts(s: str) -> datetime | None:
    """Parse an HVZ stammdaten timestamp like '18.04.2026 16:15 MESZ'."""
    if not s or s.strip() in ('--', ''):
        return None
    m = re.match(r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})\s+(MESZ|MEZ)', s.strip())
    if not m:
        return None
    day, mon, yr, hr, mi, tz_str = m.groups()
    offset = timedelta(hours=2 if tz_str == 'MESZ' else 1)
    return datetime(int(yr), int(mon), int(day), int(hr), int(mi),
                    tzinfo=timezone(offset))


def _parse_float(s: str) -> float | None:
    """Return float or None if the value is missing/invalid."""
    try:
        return float(s.replace(',', '.'))
    except (ValueError, AttributeError):
        return None


def _parse_stmn_record(row: list[str]) -> tuple[str, str, str, str | None, float | None, float | None, float | None]:
    """Return (id, name, gewaesser, ts_iso, w_cm, q_m3s, hmo_stufe1_cm)."""
    gauge_id = row[_POS_DASA]
    name = row[_POS_NAME]
    gew = row[_POS_GEW]
    ts = _parse_stmn_ts(row[_POS_WZ]) if len(row) > _POS_WZ else None
    ts_iso = ts.isoformat() if ts else None

    w_raw = row[_POS_W] if len(row) > _POS_W else '--'
    wd = row[_POS_WD] if len(row) > _POS_WD else 'cm'
    w_cm: float | None = None
    if w_raw and w_raw != '--':
        val = _parse_float(w_raw)
        if val is not None:
            # Convert to cm if unit is m
            w_cm = val * 100 if wd.strip() == 'm' else val

    q_raw = row[_POS_Q] if len(row) > _POS_Q else '--'
    q_m3s = _parse_float(q_raw) if q_raw and q_raw != '--' else None

    # POS_HMO (index 24) holds the Hochwassermeldeordnung Stufe 1 in metres (e.g. '2.20').
    # Multiply by 100 to convert to cm. Fall back to None if the field is absent or empty.
    hmo_cm: float | None = None
    if len(row) > _POS_HMO:
        raw_hmo = _parse_float(row[_POS_HMO])
        if raw_hmo is not None and raw_hmo > 0:
            hmo_cm = raw_hmo * 100  # m → cm

    return gauge_id, name, gew, ts_iso, w_cm, q_m3s, hmo_cm


def _parse_stmn_js(js: str, gauge_id: str) -> dict:
    """Parse hvz_peg_stmn.js and return a fetch-result dict for *gauge_id*.

    The JS file contains one JavaScript array assignment; each element is a
    JS array literal with single-quoted string fields.  We extract the line
    that starts with the target gauge ID and parse it as CSV (quotechar=').
    """
    # Each gauge is on its own line: " ['00061','Dörzbach',...],"
    pattern = re.compile(r"\[\s*'" + re.escape(gauge_id) + r"'")
    for line in js.splitlines():
        if pattern.search(line):
            # Strip surrounding array brackets and trailing comma
            inner = line.strip().lstrip('[').rstrip(',').rstrip(']')
            # Wrap back in brackets to parse as a single CSV record
            reader = csv.reader(io.StringIO(inner), quotechar="'")
            try:
                row = next(reader)
            except StopIteration:
                continue
            row = [f.strip() for f in row]
            gid, name, gew, ts_iso, w_cm, q_m3s, hmo_cm = _parse_stmn_record(row)
            values = []
            if ts_iso and w_cm is not None:
                values = [{"ts": ts_iso, "w_cm": w_cm, "q_m3s": q_m3s}]
            stammdaten: dict = {}
            if hmo_cm is not None:
                stammdaten["hmo_stufe_1_cm"] = int(hmo_cm)
            return {
                "pegel": {"id": gid, "name": name, "gewaesser": gew},
                "values": values,
                "forecast": [],
                "stammdaten": stammdaten,
            }

    _log.warning("HVZ: gauge %s not found in hvz_peg_stmn.js — returning empty dict", gauge_id)
    return {
        "pegel": {"id": gauge_id, "name": "", "gewaesser": ""},
        "values": [],
        "forecast": [],
        "stammdaten": {},
    }


def fetch_hvz_live(gauge_id: str) -> dict:
    """Fetch live HVZ data for *gauge_id* by scraping the hvz_peg_stmn.js file.

    The HVZ website renders all time-series data as GIF images; the only
    machine-readable data exposed is the current snapshot (latest W/Q with
    timestamp) plus HW thresholds in the JavaScript stammdaten file.

    Returns a dict compatible with :func:`parse_hvz_response`:
    - ``values``: one entry (the current snapshot) or empty list if unavailable
    - ``forecast``: always empty (forecasts are image-only)
    - ``stammdaten``: contains ``hmo_stufe_1_cm`` if available

    If the gauge cannot be found or the request fails, returns a degraded dict
    with empty ``values``/``forecast`` so that downstream code produces an
    *ungewiss* (low-confidence) Ampel status rather than crashing.
    """
    try:
        r = requests.get(
            HVZ_STMN_URL,
            timeout=30,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        # The server returns UTF-8 but omits the charset in Content-Type, so
        # requests defaults to ISO-8859-1 for text/* responses. Decode manually.
        js_text = r.content.decode("utf-8", errors="replace")
    except requests.RequestException as exc:
        _log.error("HVZ: failed to fetch %s: %s", HVZ_STMN_URL, exc)
        return {
            "pegel": {"id": gauge_id, "name": "", "gewaesser": ""},
            "values": [],
            "forecast": [],
            "stammdaten": {},
        }
    return _parse_stmn_js(js_text, gauge_id)


def compute_tendenz_cm_per_h(series: list[tuple[datetime, float]]) -> float:
    """Linear slope (cm/h) over the given series. Returns 0.0 if < 2 points."""
    if len(series) < 2:
        return 0.0
    t0, l0 = series[0]
    tn, ln = series[-1]
    hours = (tn - t0).total_seconds() / 3600.0
    if hours <= 0:
        return 0.0
    return (ln - l0) / hours
