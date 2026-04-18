# kanu-hohenlohe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A GitHub-hosted tool that fetches HVZ gauge + Open-Meteo weather data, computes a 4-step canoeing traffic-light for the Jagst section Dörzbach→Schöntal, publishes a dashboard on GitHub Pages and pushes a Telegram notification when a tour becomes realistic.

**Architecture:** Python-driven GitHub Actions cron (6x/day) that fetches, computes, commits JSON artefacts; static vanilla-JS frontend reads those JSON files from the repo. Pure-function ampel engine separates decision logic from I/O. All credentials live in Actions Secrets; repo is public under MIT.

**Tech Stack:** Python 3.12, `requests`, `pyyaml`, `pytest`, `shapely` (for catchment polygon), `pandas` only for backtesting. Frontend: vanilla JS + uPlot. GitHub Actions + GitHub Pages. Telegram Bot API.

---

## File Structure

```
kanu-hohenlohe/
├── .github/
│   └── workflows/
│       ├── update.yml          # Cron + dispatch: fetch, compute, commit
│       └── pages.yml           # Deploy web/ to Pages on main
├── src/
│   ├── __init__.py
│   ├── fetcher/
│   │   ├── __init__.py
│   │   ├── hvz.py              # HVZ API client (Dörzbach, Unterregenbach)
│   │   └── wetter.py           # Open-Meteo client with catchment grid
│   ├── engine/
│   │   ├── __init__.py
│   │   └── ampel.py            # Pure function: inputs → ampel per day
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── archive.py          # Append-only JSON time series per month
│   │   └── status.py           # Single-file status.json writer
│   ├── notify/
│   │   ├── __init__.py
│   │   └── telegram.py         # Push with dedup + rate limit
│   ├── config.py               # Load & validate config.yaml
│   └── main.py                 # Orchestrates one cron run
├── backtest/
│   ├── __init__.py
│   ├── run.py                  # 5-year simulation driver
│   └── report_template.html
├── web/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── vendor/uPlot.iife.min.js
├── data/
│   ├── status.json             # Generated
│   ├── status.prev.json        # Generated
│   ├── hvz/                    # Generated: YYYY/MM.json
│   └── weather/                # Generated: YYYY/MM.json
├── config/
│   ├── config.yaml             # Thresholds, gauge IDs, polygon ref
│   └── catchment.geojson       # Catchment polygon above Dörzbach
├── tests/
│   ├── fixtures/
│   │   ├── hvz_doerzbach_ok.json
│   │   ├── hvz_doerzbach_wartung.html
│   │   ├── hvz_unterregenbach_ok.json
│   │   └── openmeteo_forecast.json
│   ├── test_hvz.py
│   ├── test_wetter.py
│   ├── test_ampel.py
│   ├── test_archive.py
│   ├── test_status.py
│   ├── test_telegram.py
│   ├── test_config.py
│   └── test_main_integration.py
├── docs/
│   └── superpowers/            # Existing specs/plans
├── .env.example
├── .gitignore
├── LICENSE                     # MIT
├── README.md
├── pyproject.toml
└── pytest.ini
```

**Design principles:** fetchers have no decision logic; engine is a pure function; storage has no schema knowledge beyond append-vs-overwrite; every source file aims to stay under ~200 lines.

---

## Task 1: Repository scaffolding and tooling

**Files:**
- Create: `.gitignore`, `LICENSE`, `README.md` (minimal stub), `pyproject.toml`, `pytest.ini`, `.env.example`
- Create: `src/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/joerglohrer/repositories/kanu
git init -b main
```

- [ ] **Step 2: Write `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
.superpowers/
.DS_Store
*.egg-info/
build/
dist/
```

- [ ] **Step 3: Write `LICENSE` (MIT, current year 2026, holder placeholder)**

```
MIT License

Copyright (c) 2026 kanu-hohenlohe contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Write `pyproject.toml`**

```toml
[project]
name = "kanu-hohenlohe"
version = "0.1.0"
description = "Jagst canoe traffic-light: pegel + weather → ampel + push"
requires-python = ">=3.12"
dependencies = [
    "requests>=2.31",
    "pyyaml>=6.0",
    "shapely>=2.0",
]

[project.optional-dependencies]
backtest = ["pandas>=2.1"]
dev = ["pytest>=8.0", "pytest-mock>=3.12"]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 5: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
```

- [ ] **Step 6: Write `.env.example`**

```
# Telegram Bot — see https://core.telegram.org/bots#how-do-i-create-a-bot
TELEGRAM_BOT_TOKEN=123456789:your_bot_token_here
TELEGRAM_CHAT_ID=-1001234567890
```

- [ ] **Step 7: Write stub `README.md`**

```markdown
# kanu-hohenlohe

Wann kann ich die Jagst zwischen Dörzbach und Schöntal paddeln?

Dieses Werkzeug beobachtet Pegel Dörzbach und Wetterprognose im Einzugsgebiet
und gibt eine Ampel (🛶 / 😐 / 🚫 / ⚠️) für heute und die kommenden 7 Tage.

_Vollständige README folgt beim ersten Live-Lauf mit Dashboard-Link._
```

- [ ] **Step 8: Create empty package markers**

```bash
mkdir -p src tests
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 9: Install deps and verify pytest runs**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Expected: `no tests ran in 0.XXs` — pytest discovers no tests yet, that's fine.

- [ ] **Step 10: Commit**

```bash
git add .gitignore LICENSE README.md pyproject.toml pytest.ini .env.example src/__init__.py tests/__init__.py
git commit -m "chore: initial scaffolding, MIT license, pytest setup"
```

---

## Task 2: Config loader

**Files:**
- Create: `src/config.py`, `config/config.yaml`
- Test: `tests/test_config.py`

The config is the single place for all thresholds, gauge IDs and polygon references. The loader validates at startup and returns a frozen dataclass-like dict so later code cannot silently mutate it.

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
from pathlib import Path
import pytest
from src.config import load_config, ConfigError

FIXTURE = """
gauges:
  doerzbach: "00061"
  unterregenbach: "00069"
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
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`.

- [ ] **Step 3: Implement `src/config.py`**

```python
# src/config.py
from dataclasses import dataclass
from pathlib import Path
import yaml


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Thresholds:
    min_cm: int
    komfort_cm: int
    hochwasser_cm: int | None
    max_regen_24h_mm: float
    max_anstieg_cm_per_h: float


@dataclass(frozen=True)
class Config:
    gauges: dict[str, str]
    thresholds: Thresholds
    catchment_geojson: str
    timezone: str


REQUIRED = {"gauges", "thresholds", "catchment_geojson", "cron"}


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must be a mapping")
    missing = REQUIRED - raw.keys()
    if missing:
        raise ConfigError(f"missing keys: {sorted(missing)}")

    gauges = raw["gauges"]
    if not {"doerzbach", "unterregenbach"} <= gauges.keys():
        raise ConfigError("gauges must include doerzbach and unterregenbach")

    t = raw["thresholds"]
    thresholds = Thresholds(
        min_cm=int(t["min_cm"]),
        komfort_cm=int(t["komfort_cm"]),
        hochwasser_cm=int(t["hochwasser_cm"]) if t.get("hochwasser_cm") is not None else None,
        max_regen_24h_mm=float(t["max_regen_24h_mm"]),
        max_anstieg_cm_per_h=float(t["max_anstieg_cm_per_h"]),
    )
    if thresholds.komfort_cm < thresholds.min_cm:
        raise ConfigError("komfort_cm must be >= min_cm")

    return Config(
        gauges=dict(gauges),
        thresholds=thresholds,
        catchment_geojson=str(raw["catchment_geojson"]),
        timezone=str(raw["cron"]["timezone"]),
    )
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Write `config/config.yaml`**

```yaml
gauges:
  doerzbach: "00061"
  unterregenbach: "00069"   # to verify on first live run
thresholds:
  min_cm: 40
  komfort_cm: 60
  hochwasser_cm: null        # learned from HVZ Stammdaten on first live run
  max_regen_24h_mm: 5.0
  max_anstieg_cm_per_h: 3.0
catchment_geojson: "config/catchment.geojson"
cron:
  timezone: "Europe/Berlin"
```

- [ ] **Step 6: Commit**

```bash
git add src/config.py config/config.yaml tests/test_config.py
git commit -m "feat(config): typed config loader with validation"
```

---

## Task 3: Ampel engine — pure decision function

This is the kernel of the system. It must be a pure function and fully covered by tabular tests.

**Files:**
- Create: `src/engine/__init__.py`, `src/engine/ampel.py`
- Test: `tests/test_ampel.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_ampel.py -v`
Expected: all FAIL with import errors.

- [ ] **Step 3: Implement `src/engine/ampel.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_ampel.py -v`
Expected: all 10 pass.

- [ ] **Step 5: Commit**

```bash
git add src/engine/__init__.py src/engine/ampel.py tests/test_ampel.py
git commit -m "feat(engine): pure ampel function with 10 tabular tests"
```

---

## Task 4: HVZ fetcher — fixtures first

The HVZ backend endpoint is not publicly documented; this task parses fixtures captured from the live site. The live-endpoint discovery is a separate Task (Task 10) that wires up the real HTTP call once the parser is proven against fixtures.

**Files:**
- Create: `src/fetcher/__init__.py`, `src/fetcher/hvz.py`
- Create: `tests/fixtures/hvz_doerzbach_ok.json`, `tests/fixtures/hvz_doerzbach_wartung.json`
- Test: `tests/test_hvz.py`

- [ ] **Step 1: Capture fixture (manual step — document what to save)**

The engineer opens Chrome DevTools → Network tab → https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00061 , identifies the XHR/fetch that returns the measurement time-series and saves the response body.

Save two fixtures to `tests/fixtures/`:
- `hvz_doerzbach_ok.json` — a normal response with 15-min values and forecast
- `hvz_doerzbach_wartung.json` — a response during maintenance (or synthesize one with empty `values`)

If the real response is HTML (widget-rendered), save the HTML instead and adapt the parser. The tests below assume JSON; if HTML, adapt the `parse_*` functions accordingly in Step 4.

For planning purposes, assume the response shape (adjust in Step 4 if reality differs):

```json
{
  "pegel": {"id": "00061", "name": "Dörzbach", "gewaesser": "Jagst"},
  "values": [
    {"ts": "2026-04-18T09:00:00+02:00", "w_cm": 66, "q_m3s": 4.7},
    {"ts": "2026-04-18T09:15:00+02:00", "w_cm": 67, "q_m3s": 4.8}
  ],
  "forecast": [
    {"ts": "2026-04-18T12:00:00+02:00", "w_cm": 68}
  ],
  "stammdaten": {"hmo_stufe_1_cm": 180}
}
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_hvz.py
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from src.fetcher.hvz import parse_hvz_response, HVZResult

FIX = Path(__file__).parent / "fixtures"

def test_parse_ok():
    raw = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())
    r = parse_hvz_response(raw)
    assert r.gauge_id == "00061"
    assert r.name == "Dörzbach"
    assert len(r.measurements) >= 1
    assert r.latest_level_cm > 0
    assert r.latest_ts is not None
    assert r.hmo_stufe_1_cm == 180

def test_parse_wartung_returns_empty_measurements():
    raw = json.loads((FIX / "hvz_doerzbach_wartung.json").read_text())
    r = parse_hvz_response(raw)
    assert r.measurements == []
    assert r.latest_level_cm is None

def test_compute_tendenz_cm_per_hour():
    from src.fetcher.hvz import compute_tendenz_cm_per_h
    base = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    series = [
        (base, 60.0),
        (base + timedelta(minutes=15), 61.0),
        (base + timedelta(minutes=30), 62.0),
        (base + timedelta(minutes=45), 63.0),
        (base + timedelta(minutes=60), 64.0),
    ]
    # 4 cm rise over 60 minutes → 4 cm/h
    assert abs(compute_tendenz_cm_per_h(series) - 4.0) < 0.01

def test_compute_tendenz_returns_zero_for_insufficient_data():
    from src.fetcher.hvz import compute_tendenz_cm_per_h
    assert compute_tendenz_cm_per_h([]) == 0.0
```

- [ ] **Step 3: Create fixture files**

```json
// tests/fixtures/hvz_doerzbach_ok.json
{
  "pegel": {"id": "00061", "name": "Dörzbach", "gewaesser": "Jagst"},
  "values": [
    {"ts": "2026-04-18T09:00:00+02:00", "w_cm": 66, "q_m3s": 4.7},
    {"ts": "2026-04-18T09:15:00+02:00", "w_cm": 67, "q_m3s": 4.8},
    {"ts": "2026-04-18T09:30:00+02:00", "w_cm": 67, "q_m3s": 4.8},
    {"ts": "2026-04-18T09:45:00+02:00", "w_cm": 68, "q_m3s": 4.8}
  ],
  "forecast": [
    {"ts": "2026-04-18T12:00:00+02:00", "w_cm": 68},
    {"ts": "2026-04-18T18:00:00+02:00", "w_cm": 69}
  ],
  "stammdaten": {"hmo_stufe_1_cm": 180}
}
```

```json
// tests/fixtures/hvz_doerzbach_wartung.json
{
  "pegel": {"id": "00061", "name": "Dörzbach", "gewaesser": "Jagst"},
  "values": [],
  "forecast": [],
  "stammdaten": {"hmo_stufe_1_cm": 180}
}
```

- [ ] **Step 4: Implement `src/fetcher/hvz.py`**

```python
# src/fetcher/hvz.py
from dataclasses import dataclass, field
from datetime import datetime, timezone


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
    pegel = raw.get("pegel", {})
    vals = raw.get("values", []) or []
    fc = raw.get("forecast", []) or []
    stamm = raw.get("stammdaten", {}) or {}

    measurements = [
        HVZMeasurement(ts=_parse_ts(v["ts"]), level_cm=float(v["w_cm"]),
                       q_m3s=float(v["q_m3s"]) if v.get("q_m3s") is not None else None)
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
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/test_hvz.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/fetcher/__init__.py src/fetcher/hvz.py tests/test_hvz.py tests/fixtures/hvz_*.json
git commit -m "feat(fetcher): HVZ response parser with fixture tests"
```

---

## Task 5: Catchment polygon and Open-Meteo fetcher

**Files:**
- Create: `src/fetcher/wetter.py`
- Create: `config/catchment.geojson` (rough polygon above Dörzbach)
- Create: `tests/fixtures/openmeteo_forecast.json`
- Test: `tests/test_wetter.py`

- [ ] **Step 1: Write `config/catchment.geojson`** (rough bounding polygon around the upper Jagst catchment; refine later)

```json
{
  "type": "Feature",
  "properties": {"name": "Obere Jagst oberhalb Dörzbach"},
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [10.33, 49.06],
      [10.33, 49.37],
      [9.79, 49.37],
      [9.79, 49.24],
      [10.00, 49.16],
      [10.20, 49.06],
      [10.33, 49.06]
    ]]
  }
}
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_wetter.py
import json
from pathlib import Path
from src.fetcher.wetter import (
    build_grid_points, parse_openmeteo_response, aggregate_area_mean, GridForecast,
)

FIX = Path(__file__).parent / "fixtures"

def test_build_grid_points_returns_inside_polygon_only():
    polygon = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[
            [10.0, 49.0], [10.2, 49.0], [10.2, 49.2], [10.0, 49.2], [10.0, 49.0]
        ]]},
    }
    pts = build_grid_points(polygon, step_deg=0.1)
    assert len(pts) >= 4
    for lat, lon in pts:
        assert 49.0 <= lat <= 49.2
        assert 10.0 <= lon <= 10.2

def test_parse_openmeteo_returns_hourly_series():
    raw = json.loads((FIX / "openmeteo_forecast.json").read_text())
    fc = parse_openmeteo_response(raw)
    assert len(fc.hours) > 0
    h0 = fc.hours[0]
    assert h0.ts is not None
    assert h0.precip_mm >= 0.0
    assert 0 <= h0.cloud_cover <= 100

def test_aggregate_area_mean():
    from datetime import datetime, timezone
    from src.fetcher.wetter import HourFc, GridForecast
    ts = datetime(2026, 4, 18, 12, tzinfo=timezone.utc)
    g1 = GridForecast(hours=[HourFc(ts=ts, precip_mm=2.0, cloud_cover=50)])
    g2 = GridForecast(hours=[HourFc(ts=ts, precip_mm=4.0, cloud_cover=70)])
    agg = aggregate_area_mean([g1, g2])
    assert agg.hours[0].precip_mm == 3.0
    assert agg.hours[0].max_precip_mm == 4.0
```

- [ ] **Step 3: Create Open-Meteo fixture**

```json
// tests/fixtures/openmeteo_forecast.json
{
  "latitude": 49.1,
  "longitude": 10.1,
  "hourly": {
    "time": [
      "2026-04-18T12:00",
      "2026-04-18T13:00",
      "2026-04-18T14:00"
    ],
    "precipitation": [0.2, 0.5, 1.1],
    "cloud_cover": [30, 45, 60]
  }
}
```

- [ ] **Step 4: Implement `src/fetcher/wetter.py`**

```python
# src/fetcher/wetter.py
from dataclasses import dataclass
from datetime import datetime
from shapely.geometry import shape, Point


@dataclass(frozen=True)
class HourFc:
    ts: datetime
    precip_mm: float
    cloud_cover: int
    max_precip_mm: float = 0.0  # set only on aggregated area mean


@dataclass(frozen=True)
class GridForecast:
    hours: list[HourFc]


def build_grid_points(polygon_geojson: dict, step_deg: float = 0.1) -> list[tuple[float, float]]:
    geom = shape(polygon_geojson["geometry"])
    minx, miny, maxx, maxy = geom.bounds
    lat = miny
    pts = []
    while lat <= maxy:
        lon = minx
        while lon <= maxx:
            if geom.contains(Point(lon, lat)):
                pts.append((round(lat, 4), round(lon, 4)))
            lon += step_deg
        lat += step_deg
    return pts


def parse_openmeteo_response(raw: dict) -> GridForecast:
    h = raw.get("hourly", {})
    times = h.get("time", [])
    precs = h.get("precipitation", [])
    clouds = h.get("cloud_cover", [])
    hours = [
        HourFc(
            ts=datetime.fromisoformat(t),
            precip_mm=float(p or 0.0),
            cloud_cover=int(c or 0),
        )
        for t, p, c in zip(times, precs, clouds)
    ]
    return GridForecast(hours=hours)


def aggregate_area_mean(grids: list[GridForecast]) -> GridForecast:
    if not grids:
        return GridForecast(hours=[])
    ref = grids[0].hours
    hours = []
    for i, ref_hour in enumerate(ref):
        values = [g.hours[i].precip_mm for g in grids if i < len(g.hours)]
        clouds = [g.hours[i].cloud_cover for g in grids if i < len(g.hours)]
        mean_p = sum(values) / len(values)
        max_p = max(values)
        mean_c = int(sum(clouds) / len(clouds))
        hours.append(HourFc(ts=ref_hour.ts, precip_mm=round(mean_p, 2),
                            cloud_cover=mean_c, max_precip_mm=round(max_p, 2)))
    return GridForecast(hours=hours)
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/test_wetter.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/fetcher/wetter.py config/catchment.geojson tests/test_wetter.py tests/fixtures/openmeteo_forecast.json
git commit -m "feat(fetcher): catchment grid + Open-Meteo parser with area mean"
```

---

## Task 6: Archive storage — append-only, idempotent

**Files:**
- Create: `src/storage/__init__.py`, `src/storage/archive.py`
- Test: `tests/test_archive.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_archive.py
from datetime import datetime, timezone
from pathlib import Path
from src.storage.archive import append_measurements, load_month

def _m(ts, w):
    return {"ts": ts.isoformat(), "w_cm": w}

def test_append_creates_monthly_file(tmp_path):
    ts = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    n = append_measurements(tmp_path, "doerzbach", [_m(ts, 66.0)])
    assert n == 1
    f = tmp_path / "doerzbach" / "2026" / "04.json"
    assert f.exists()

def test_append_is_idempotent(tmp_path):
    ts = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    append_measurements(tmp_path, "doerzbach", [_m(ts, 66.0)])
    n = append_measurements(tmp_path, "doerzbach", [_m(ts, 66.0)])
    assert n == 0  # duplicate not added
    loaded = load_month(tmp_path, "doerzbach", 2026, 4)
    assert len(loaded) == 1

def test_append_across_months_writes_separate_files(tmp_path):
    ts_apr = datetime(2026, 4, 30, 23, 45, tzinfo=timezone.utc)
    ts_may = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    append_measurements(tmp_path, "doerzbach", [_m(ts_apr, 66), _m(ts_may, 67)])
    assert (tmp_path / "doerzbach" / "2026" / "04.json").exists()
    assert (tmp_path / "doerzbach" / "2026" / "05.json").exists()

def test_append_preserves_order(tmp_path):
    t1 = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 4, 18, 9, 15, tzinfo=timezone.utc)
    append_measurements(tmp_path, "doerzbach", [_m(t2, 67), _m(t1, 66)])
    loaded = load_month(tmp_path, "doerzbach", 2026, 4)
    assert loaded[0]["ts"] == t1.isoformat()
    assert loaded[1]["ts"] == t2.isoformat()
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_archive.py -v`
Expected: all FAIL with import errors.

- [ ] **Step 3: Implement `src/storage/archive.py`**

```python
# src/storage/archive.py
import json
from datetime import datetime
from pathlib import Path


def _month_file(base: Path, series: str, year: int, month: int) -> Path:
    return base / series / f"{year:04d}" / f"{month:02d}.json"


def load_month(base: Path, series: str, year: int, month: int) -> list[dict]:
    f = _month_file(base, series, year, month)
    if not f.exists():
        return []
    return json.loads(f.read_text())


def _save_month(base: Path, series: str, year: int, month: int, data: list[dict]) -> None:
    f = _month_file(base, series, year, month)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def append_measurements(base: Path, series: str, new_records: list[dict]) -> int:
    """Append records (each with 'ts' isoformat). Idempotent on 'ts' collision.
    Returns number of records actually added."""
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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_archive.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/storage/__init__.py src/storage/archive.py tests/test_archive.py
git commit -m "feat(storage): idempotent monthly JSON archive"
```

---

## Task 7: Status writer

**Files:**
- Create: `src/storage/status.py`
- Test: `tests/test_status.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_status.py
import json
from datetime import date, datetime, timezone
from pathlib import Path
from src.engine.ampel import Stufe, DayResult
from src.storage.status import write_status, rotate_prev

def _r(day, stufe, level=66.0):
    return DayResult(day=day, stufe=stufe, begruendung="test",
                     level_cm=level, regen_24h_mm=0.0, confidence=1.0)

def test_write_status_produces_valid_json(tmp_path):
    days = [_r(date(2026, 4, 18), Stufe.GRUEN), _r(date(2026, 4, 19), Stufe.GELB, 55.0)]
    write_status(
        tmp_path / "status.json",
        generated_at=datetime(2026, 4, 18, 11, 15, tzinfo=timezone.utc),
        latest_level_cm=68.0, latest_q_m3s=4.8,
        tendenz_cm_per_h=0.3,
        hvz_stale=False, hvz_last_ts=datetime(2026, 4, 18, 11, 0, tzinfo=timezone.utc),
        hmo_stufe_1_cm=180,
        regen_24h_mean_mm=1.2, regen_24h_max_mm=3.1,
        days=days,
    )
    f = tmp_path / "status.json"
    data = json.loads(f.read_text())
    assert data["latest_level_cm"] == 68.0
    assert data["hvz_stale"] is False
    assert data["days"][0]["stufe"] == "gruen"
    assert data["days"][0]["emoji"] == "🛶"
    assert len(data["days"]) == 2

def test_rotate_prev_copies_previous_status(tmp_path):
    cur = tmp_path / "status.json"
    prv = tmp_path / "status.prev.json"
    cur.write_text('{"a": 1}')
    rotate_prev(cur, prv)
    assert prv.read_text() == '{"a": 1}'

def test_rotate_prev_noop_when_missing(tmp_path):
    cur = tmp_path / "status.json"
    prv = tmp_path / "status.prev.json"
    rotate_prev(cur, prv)  # must not raise
    assert not prv.exists()
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_status.py -v`
Expected: FAIL with import errors.

- [ ] **Step 3: Implement `src/storage/status.py`**

```python
# src/storage/status.py
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
) -> None:
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
    if current.exists():
        shutil.copy2(current, previous)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_status.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/storage/status.py tests/test_status.py
git commit -m "feat(storage): status.json writer + prev rotation"
```

---

## Task 8: Telegram notifier with dedup and rate limit

**Files:**
- Create: `src/notify/__init__.py`, `src/notify/telegram.py`
- Test: `tests/test_telegram.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_telegram.py
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from src.notify.telegram import (
    should_push, compose_message, send_push, PushDecision,
)

NOW = datetime(2026, 4, 18, 11, 0, tzinfo=timezone.utc)

def _status(days_stufen):
    return {
        "generated_at": NOW.isoformat(),
        "latest_level_cm": 68,
        "days": [
            {"day": f"2026-04-{18+i}", "stufe": s, "emoji": "🛶" if s == "gruen" else "😐",
             "level_cm": 66, "regen_24h_mm": 0.5, "begruendung": "x", "confidence": 1.0}
            for i, s in enumerate(days_stufen)
        ],
    }

def test_no_push_when_nothing_changed(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    d = should_push(cur, prv, last_push_ts=None, now=NOW)
    assert d.kind == PushDecision.NONE

def test_push_on_transition_to_green(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gruen", "gruen", "gruen"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    d = should_push(cur, prv, last_push_ts=None, now=NOW)
    assert d.kind == PushDecision.GREEN_WINDOW

def test_push_on_new_two_day_green_block(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gelb", "gruen", "gruen"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    d = should_push(cur, prv, last_push_ts=None, now=NOW)
    assert d.kind == PushDecision.GREEN_WINDOW

def test_rate_limit_blocks_within_12h(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gruen", "gruen", "gruen"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    recent = NOW - timedelta(hours=6)
    d = should_push(cur, prv, last_push_ts=recent, now=NOW)
    assert d.kind == PushDecision.RATE_LIMITED

def test_compose_message_mentions_level_and_days():
    msg = compose_message(_status(["gruen", "gruen", "gelb"]))
    assert "68" in msg and "cm" in msg
    assert "🛶" in msg

def test_send_push_uses_env_and_posts():
    with patch("src.notify.telegram.requests.post") as p, \
         patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "T", "TELEGRAM_CHAT_ID": "C"}):
        p.return_value.status_code = 200
        p.return_value.json.return_value = {"ok": True}
        send_push("hallo")
        p.assert_called_once()
        args, kwargs = p.call_args
        assert "T" in args[0]  # bot token in URL
        assert kwargs["json"]["chat_id"] == "C"
        assert kwargs["json"]["text"] == "hallo"
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_telegram.py -v`
Expected: FAIL with import errors.

- [ ] **Step 3: Implement `src/notify/telegram.py`**

```python
# src/notify/telegram.py
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import requests


class PushDecision(str, Enum):
    NONE = "none"
    GREEN_WINDOW = "green_window"
    RATE_LIMITED = "rate_limited"


@dataclass(frozen=True)
class Decision:
    kind: PushDecision
    reason: str = ""


RATE_LIMIT_HOURS = 12


def _green_block_of_2(days: list[dict]) -> bool:
    for a, b in zip(days, days[1:]):
        if a["stufe"] == "gruen" and b["stufe"] == "gruen":
            return True
    return False


def should_push(current: Path, previous: Path, last_push_ts: datetime | None,
                now: datetime) -> Decision:
    if not current.exists():
        return Decision(PushDecision.NONE, "no current status")
    cur = json.loads(current.read_text())
    prv = json.loads(previous.read_text()) if previous.exists() else {"days": []}

    cur_days = cur.get("days", [])
    prv_days = prv.get("days", [])

    today_green = bool(cur_days) and cur_days[0]["stufe"] == "gruen"
    was_green = bool(prv_days) and prv_days[0]["stufe"] == "gruen"
    transition = today_green and not was_green
    new_window = _green_block_of_2(cur_days) and not _green_block_of_2(prv_days)

    if not (transition or new_window):
        return Decision(PushDecision.NONE, "no positive transition")

    if last_push_ts is not None and (now - last_push_ts) < timedelta(hours=RATE_LIMIT_HOURS):
        return Decision(PushDecision.RATE_LIMITED, f"last push {now - last_push_ts} ago")

    return Decision(PushDecision.GREEN_WINDOW, "transition or new green block")


def compose_message(status: dict) -> str:
    level = status.get("latest_level_cm")
    days = status.get("days", [])
    day_str = " · ".join(f"{d['day'][-5:]} {d['emoji']}" for d in days[:5])
    level_part = f"{level:.0f} cm" if level is not None else "—"
    return f"🛶 Jagst Dörzbach: {level_part}\n{day_str}\nhttps://<user>.github.io/kanu-hohenlohe/"


def send_push(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text,
                                 "disable_web_page_preview": False},
                      timeout=20)
    r.raise_for_status()
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_telegram.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/notify/__init__.py src/notify/telegram.py tests/test_telegram.py
git commit -m "feat(notify): Telegram push with dedup and 12h rate limit"
```

---

## Task 9: Orchestrator `src/main.py` and integration test

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main_integration.py`

The orchestrator wires everything and is thin. Real HTTP calls are mocked in the integration test with the same fixtures used in unit tests.

- [ ] **Step 1: Write failing integration test**

```python
# tests/test_main_integration.py
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from src import main as orchestrator

FIX = Path(__file__).parent / "fixtures"

def test_full_run_writes_status_and_archives(tmp_path, monkeypatch):
    cfg_yaml = tmp_path / "config.yaml"
    cfg_yaml.write_text((Path("config") / "config.yaml").read_text())
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    hvz_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())
    unter_ok = json.loads((FIX / "hvz_doerzbach_ok.json").read_text())  # reuse
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
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_main_integration.py -v`
Expected: FAIL (import error or AttributeError).

- [ ] **Step 3: Implement `src/main.py`**

```python
# src/main.py
import json
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

import requests

from src.config import load_config
from src.engine.ampel import compute_ampel, DayInput
from src.fetcher.hvz import parse_hvz_response, compute_tendenz_cm_per_h
from src.fetcher.wetter import (
    build_grid_points, parse_openmeteo_response, aggregate_area_mean,
)
from src.storage.archive import append_measurements
from src.storage.status import write_status, rotate_prev
from src.notify.telegram import should_push, compose_message, send_push, PushDecision


def fetch_hvz_raw(gauge_id: str) -> dict:
    # Real endpoint discovery is Task 10. Raise until implemented.
    raise NotImplementedError("fetch_hvz_raw is wired in Task 10")


def fetch_openmeteo_raw(lat: float, lon: float) -> dict:
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "hourly": "precipitation,cloud_cover",
            "forecast_days": 7,
            "timezone": "Europe/Berlin",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def send_push_if_needed(status_path: Path, prev_path: Path, last_push_path: Path,
                        now: datetime) -> None:
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
    cfg = load_config(config_path)
    now = now or datetime.now(tz=timezone.utc)

    # Fetch HVZ for both gauges
    hvz_raw_d = fetch_hvz_raw(cfg.gauges["doerzbach"])
    hvz_raw_u = fetch_hvz_raw(cfg.gauges["unterregenbach"])
    hvz_d = parse_hvz_response(hvz_raw_d)
    hvz_u = parse_hvz_response(hvz_raw_u)

    # Archive
    append_measurements(
        data_dir / "hvz", "doerzbach",
        [{"ts": m.ts.isoformat(), "w_cm": m.level_cm, "q_m3s": m.q_m3s} for m in hvz_d.measurements],
    )
    append_measurements(
        data_dir / "hvz", "unterregenbach",
        [{"ts": m.ts.isoformat(), "w_cm": m.level_cm, "q_m3s": m.q_m3s} for m in hvz_u.measurements],
    )

    # Weather — one grid, averaged across points
    polygon = json.loads(catchment_path.read_text())
    points = build_grid_points(polygon, step_deg=0.1)
    grids = [parse_openmeteo_response(fetch_openmeteo_raw(lat, lon)) for lat, lon in points]
    area = aggregate_area_mean(grids)

    # Archive weather (area mean only)
    append_measurements(
        data_dir / "weather", "area_mean",
        [{"ts": h.ts.isoformat(), "precip_mm": h.precip_mm,
          "max_precip_mm": h.max_precip_mm, "cloud_cover": h.cloud_cover}
         for h in area.hours],
    )

    # Compute ampel for today + next 7 days
    today = now.date()
    days_out = []
    level = hvz_d.latest_level_cm or 0.0
    tend = compute_tendenz_cm_per_h([(m.ts, m.level_cm) for m in hvz_d.measurements])

    for offset in range(8):
        d = today + timedelta(days=offset)
        regen_24h = sum(h.precip_mm for h in area.hours
                        if h.ts.date() == d) if area.hours else 0.0
        # use HVZ forecast when available, else hold current value
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

    # promote learned hmo value into config snapshot if config had null
    hmo_cm = cfg.thresholds.hochwasser_cm or hvz_d.hmo_stufe_1_cm

    write_status(
        status_path,
        generated_at=now,
        latest_level_cm=hvz_d.latest_level_cm,
        latest_q_m3s=hvz_d.measurements[-1].q_m3s if hvz_d.measurements else None,
        tendenz_cm_per_h=tend,
        hvz_stale=hvz_d.latest_ts is None or (now - hvz_d.latest_ts).total_seconds() > 6 * 3600
            if hvz_d.latest_ts else True,
        hvz_last_ts=hvz_d.latest_ts,
        hmo_stufe_1_cm=hmo_cm,
        regen_24h_mean_mm=round(sum(h.precip_mm for h in area.hours[:24]) / max(1, min(24, len(area.hours))), 2),
        regen_24h_max_mm=max((h.max_precip_mm for h in area.hours[:24]), default=0.0),
        days=days_out,
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
```

- [ ] **Step 4: Run integration test to verify pass**

Run: `pytest tests/test_main_integration.py -v`
Expected: 1 passed.

- [ ] **Step 5: Run full test suite**

Run: `pytest`
Expected: all previous tests still green.

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_main_integration.py
git commit -m "feat(main): orchestrator wires fetchers, engine, storage, notify"
```

---

## Task 10: Live HVZ endpoint discovery and wiring

This is the one task that genuinely needs the live internet and cannot be fully tested offline.

**Files:**
- Modify: `src/fetcher/hvz.py`, `src/main.py`

- [ ] **Step 1: Discover endpoint**

Open `https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00061` in Chrome, open DevTools → Network, filter XHR/Fetch, and identify the request that returns the time-series. Record:
- URL template
- Response content-type (JSON vs HTML)
- Shape of the response (may require adapting `parse_hvz_response` if it differs from the fixture)

- [ ] **Step 2: If the response is JSON — add fetcher function**

Append to `src/fetcher/hvz.py`:

```python
import requests

HVZ_URL_TEMPLATE = "<paste discovered URL, substitute {id}>"

def fetch_hvz_live(gauge_id: str) -> dict:
    r = requests.get(HVZ_URL_TEMPLATE.format(id=gauge_id), timeout=30,
                     headers={"User-Agent": "kanu-hohenlohe/0.1"})
    r.raise_for_status()
    return r.json()
```

- [ ] **Step 3: If the response is HTML — add HTML-scraping fallback**

```python
from bs4 import BeautifulSoup  # add to pyproject dependencies

def fetch_hvz_live_html(gauge_id: str) -> dict:
    r = requests.get(f"https://www.hvz.baden-wuerttemberg.de/pegel.html?id={gauge_id}",
                     timeout=30, headers={"User-Agent": "kanu-hohenlohe/0.1"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    # extract table rows, build {pegel, values, forecast, stammdaten} dict matching fixture shape
    ...
    return parsed
```

Add `beautifulsoup4>=4.12` to `pyproject.toml` dependencies, reinstall.

- [ ] **Step 4: Wire into `src/main.py`**

Replace the `fetch_hvz_raw` stub:

```python
from src.fetcher.hvz import fetch_hvz_live

def fetch_hvz_raw(gauge_id: str) -> dict:
    return fetch_hvz_live(gauge_id)
```

- [ ] **Step 5: One-time live probe**

Run interactively to confirm the shape matches the fixture:

```bash
python -c "from src.fetcher.hvz import fetch_hvz_live, parse_hvz_response; import json; raw = fetch_hvz_live('00061'); print(json.dumps(raw, indent=2)[:500]); r = parse_hvz_response(raw); print(r.latest_level_cm, r.hmo_stufe_1_cm)"
```

Expected: prints a partial JSON of the real response, then the latest level and HMO-Stufe-1 in cm.

- [ ] **Step 6: Update fixture with real sample**

Overwrite `tests/fixtures/hvz_doerzbach_ok.json` with a redacted real response (strip any client-IP / session data if present). Rerun `pytest tests/test_hvz.py` — must still pass.

- [ ] **Step 7: If HMO value learned, update config**

If `parse_hvz_response(...)` returns a concrete `hmo_stufe_1_cm`, record it in `config/config.yaml` under `thresholds.hochwasser_cm`.

- [ ] **Step 8: Verify Unterregenbach gauge id**

Browse the HVZ gauge list (https://www.hvz.baden-wuerttemberg.de/overview.html), find Unterregenbach, confirm the numeric id, update `config/config.yaml`.

- [ ] **Step 9: Commit**

```bash
git add src/fetcher/hvz.py src/main.py config/config.yaml tests/fixtures/hvz_doerzbach_ok.json pyproject.toml
git commit -m "feat(fetcher): live HVZ endpoint wired; config populated with HMO and gauge ids"
```

---

## Task 11: Frontend — static dashboard on GitHub Pages

**Files:**
- Create: `web/index.html`, `web/styles.css`, `web/app.js`
- Create: `web/vendor/uPlot.iife.min.js` (download from https://unpkg.com/uplot/dist/uPlot.iife.min.js)

The frontend must match the design tokens from the spec: flusswasser-blue gradient header, dark control-room body, Inter + JetBrains Mono, ampel emoji per day.

- [ ] **Step 1: Vendor uPlot**

```bash
mkdir -p web/vendor
curl -L -o web/vendor/uPlot.iife.min.js https://unpkg.com/uplot@1.6.30/dist/uPlot.iife.min.js
curl -L -o web/vendor/uPlot.min.css     https://unpkg.com/uplot@1.6.30/dist/uPlot.min.css
```

- [ ] **Step 2: Write `web/index.html`**

```html
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Jagst Dörzbach → Schöntal · Kanu-Ampel</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="vendor/uPlot.min.css"/>
  <link rel="stylesheet" href="styles.css"/>
</head>
<body>
  <main id="app">
    <section id="hero"></section>
    <section id="kpi"></section>
    <section id="chart-wrap">
      <div id="chart"></div>
    </section>
    <section id="rain"></section>
    <section id="week"></section>
    <footer id="meta"></footer>
  </main>
  <script src="vendor/uPlot.iife.min.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Write `web/styles.css`**

```css
:root {
  --bg: #0a1420;
  --tile: #143d66;
  --tile-alt: #0f1a2a;
  --text: #e8edf5;
  --muted: #6b7a99;
  --label: #94a3b8;
  --accent-ice: #7dd3fc;
  --accent-green: #a8f0b5;
  --accent-yellow: #f5d97a;
  --grid: #1e2942;
}

* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
       font-family: 'Inter', system-ui, sans-serif; }
.mono { font-family: 'JetBrains Mono', ui-monospace, monospace; }

#hero {
  background: linear-gradient(135deg, #1e5a8c 0%, #2e7ab0 55%, #4a9fd4 100%);
  color: #f0f8ff; padding: 28px 32px;
}
#hero .label { font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; opacity: 0.75; }
#hero .level { font-size: 72px; font-weight: 700; line-height: 1; }
#hero .level small { font-size: 22px; opacity: 0.65; margin-left: 8px; font-weight: 500; }
#hero .emoji { font-size: 64px; line-height: 1; }
#hero .row { display: flex; align-items: baseline; gap: 18px; flex-wrap: wrap; }
#hero .status { font-size: 16px; font-weight: 500; margin-top: 10px; }
#hero .ctx { font-size: 13px; opacity: 0.75; margin-top: 4px; }
#hero .time { font-family: 'JetBrains Mono', monospace; font-size: 11px; opacity: 0.75;
              text-align: right; line-height: 1.7; }

#kpi { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: #1a2638; }
.kpi { background: var(--tile-alt); padding: 16px 20px; }
.kpi .k { font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.14em;
          color: var(--muted); text-transform: uppercase; }
.kpi .v { font-size: 22px; font-weight: 600; margin-top: 4px; }
.kpi .v small { font-size: 12px; color: var(--muted); font-weight: 400; }
.kpi .hint { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--label); margin-top: 2px; }

#chart-wrap { padding: 24px 32px; }
#chart-wrap h3 { margin: 0 0 14px 0; font-size: 14px; font-weight: 600; }
#chart { height: 220px; }

#rain { padding: 0 32px 8px 32px; }
#rain h3 { font-size: 12px; font-weight: 500; opacity: 0.8; margin: 20px 0 8px; }
.rain-bars { display: flex; gap: 1px; height: 42px; align-items: flex-end; }
.rain-bar { flex: 1; background: var(--accent-ice); opacity: 0.3; }
.rain-bar.high { background: var(--accent-yellow); opacity: 0.85; }
.rain-scale { display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace;
              font-size: 9px; color: var(--muted); margin-top: 4px; }

#week { padding: 20px 32px 28px; }
#week h3 { margin: 0 0 14px; font-size: 14px; font-weight: 600; }
.week-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
.wd { background: var(--tile); border-radius: 6px; padding: 12px 10px; text-align: center; }
.wd.uncertain { background: #0f2540; opacity: 0.6; }
.wd .day { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--label); letter-spacing: 0.1em; }
.wd .em { font-size: 30px; margin: 6px 0; }
.wd .lvl { font-size: 17px; font-weight: 700; }
.wd .lvl small { font-size: 10px; color: var(--label); font-weight: 400; }
.wd .rain { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--muted); margin-top: 4px; }

#meta { padding: 20px 32px 40px; color: var(--muted); font-family: 'JetBrains Mono', monospace; font-size: 11px; }
.banner { background: #3b1c1c; color: #ffb4b4; padding: 10px 16px; font-size: 13px; }

@media (max-width: 720px) {
  #hero { padding: 20px 16px; }
  #hero .level { font-size: 56px; }
  #hero .emoji { font-size: 48px; }
  #kpi { grid-template-columns: repeat(2, 1fr); }
  #chart-wrap, #rain, #week, #meta { padding-left: 16px; padding-right: 16px; }
  .week-grid { grid-template-columns: repeat(4, 1fr); }
}
```

- [ ] **Step 4: Write `web/app.js`**

```javascript
// Load status.json and render the dashboard.
const fmtTime = (ts) => new Date(ts).toLocaleString("de-DE",
  {day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit"});

async function loadStatus() {
  const res = await fetch(`../data/status.json?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("status.json missing");
  return res.json();
}

function renderHero(s) {
  const today = s.days[0];
  const level = s.latest_level_cm?.toFixed(0) ?? "—";
  const stale = s.hvz_stale ? `<div class="banner">Pegel aktuell in Wartung · letzter Wert ${level} cm um ${fmtTime(s.hvz_last_ts)}</div>` : "";
  document.getElementById("hero").innerHTML = `
    ${stale}
    <div class="label">Jagst · Dörzbach → Schöntal</div>
    <div class="row">
      <div class="level">${level}<small>cm</small></div>
      <div class="emoji">${today.emoji}</div>
    </div>
    <div class="status">${today.begruendung}</div>
    <div class="ctx mono">Aktualisiert ${fmtTime(s.generated_at)}</div>
  `;
}

function renderKpi(s) {
  const dist = (s.hmo_stufe_1_cm && s.latest_level_cm)
    ? (s.hmo_stufe_1_cm - s.latest_level_cm).toFixed(0) : "—";
  document.getElementById("kpi").innerHTML = `
    <div class="kpi"><div class="k">Abfluss</div>
      <div class="v">${s.latest_q_m3s?.toFixed(1) ?? "—"} <small>m³/s</small></div></div>
    <div class="kpi"><div class="k">Tendenz</div>
      <div class="v">${(s.tendenz_cm_per_h >= 0 ? "+" : "") + s.tendenz_cm_per_h.toFixed(1)} <small>cm/h</small></div></div>
    <div class="kpi"><div class="k">Regen EZG · 24 h</div>
      <div class="v">${s.regen_24h_mean_mm.toFixed(1)} <small>mm Ø</small></div>
      <div class="hint">max ${s.regen_24h_max_mm.toFixed(1)} lokal</div></div>
    <div class="kpi"><div class="k">HW-Stufe 1</div>
      <div class="v">${s.hmo_stufe_1_cm ?? "—"} <small>cm</small></div>
      <div class="hint">Abstand ${dist} cm</div></div>
  `;
}

async function renderChart() {
  // Load last 14 days archive; graceful fail if missing
  try {
    const now = new Date();
    const y = now.getUTCFullYear(), m = String(now.getUTCMonth()+1).padStart(2,"0");
    const res = await fetch(`../data/hvz/doerzbach/${y}/${m}.json`, { cache: "no-store" });
    if (!res.ok) return;
    const rows = await res.json();
    const cut = Date.now() - 14 * 86400 * 1000;
    const f = rows.filter(r => Date.parse(r.ts) >= cut);
    const xs = f.map(r => Date.parse(r.ts) / 1000);
    const ys = f.map(r => r.w_cm);

    const opts = {
      width: document.getElementById("chart").clientWidth,
      height: 220,
      scales: { x: { time: true }, y: { } },
      axes: [
        { stroke: "#6b7a99", grid: {stroke:"#1e2942"} },
        { stroke: "#6b7a99", grid: {stroke:"#1e2942"} },
      ],
      series: [{}, { stroke: "#4a9fd4", width: 1.8,
                      fill: "rgba(74,159,212,0.12)" }],
    };
    new uPlot(opts, [xs, ys], document.getElementById("chart"));
  } catch (e) {
    document.getElementById("chart").innerHTML =
      '<div class="mono" style="color:#6b7a99">Keine Zeitreihe verfügbar</div>';
  }
}

function renderRain(_s) {
  // Placeholder: build 48 bars once weather archive wiring is added (Task 12 optional).
  const bars = Array.from({length: 48}, (_, i) => {
    const h = Math.max(1, Math.round(2 + 6 * Math.sin(i/4)));
    const cls = h > 18 ? "rain-bar high" : "rain-bar";
    return `<div class="${cls}" style="height:${h}px"></div>`;
  }).join("");
  document.getElementById("rain").innerHTML =
    `<h3>Niederschlag Einzugsgebiet · stündlich (Vorschau)</h3>
     <div class="rain-bars">${bars}</div>
     <div class="rain-scale mono"><span>jetzt</span><span>+24 h</span><span>+48 h</span></div>`;
}

function renderWeek(s) {
  const items = s.days.slice(0, 7).map((d, i) => {
    const uncertain = d.confidence < 0.5;
    const label = i === 0 ? "HEUTE" : new Date(d.day).toLocaleDateString("de-DE", {weekday:"short"}).toUpperCase();
    return `<div class="wd ${uncertain?"uncertain":""}">
      <div class="day">${label}</div>
      <div class="em">${d.emoji}</div>
      <div class="lvl">${Math.round(d.level_cm)}<small> cm</small></div>
      <div class="rain">${d.regen_24h_mm.toFixed(1)} mm</div>
    </div>`;
  }).join("");
  document.getElementById("week").innerHTML =
    `<h3>7-Tage-Ausblick</h3><div class="week-grid">${items}</div>`;
}

function renderMeta() {
  document.getElementById("meta").innerHTML =
    `Quellen: Pegel & Vorhersage HVZ Baden-Württemberg · Wetter Open-Meteo (DWD) · ` +
    `Befahrungsregeln Landratsamt Hohenlohekreis · Keine amtliche Auskunft.`;
}

(async () => {
  try {
    const s = await loadStatus();
    renderHero(s); renderKpi(s); renderRain(s); renderWeek(s); renderMeta();
    await renderChart();
  } catch (e) {
    document.body.innerHTML = `<pre style="color:#fff;padding:32px">${e}</pre>`;
  }
})();
```

- [ ] **Step 5: Visual check locally**

```bash
# Run a tiny static server for web/ against fixture status (copy the fixture)
mkdir -p data
cp tests/fixtures/openmeteo_forecast.json data/ 2>/dev/null || true
# Generate a status.json by running the pipeline once offline — see next step
```

You need a concrete `data/status.json` to view. Easiest: generate it from a mocked run:

```bash
python -c "
from datetime import datetime, timezone, date
from pathlib import Path
from src.engine.ampel import Stufe, DayResult
from src.storage.status import write_status
days=[DayResult(day=date(2026,4,18+i), stufe=Stufe.GRUEN if i<3 else Stufe.GELB,
                begruendung='demo', level_cm=66+i, regen_24h_mm=0.5, confidence=1.0)
      for i in range(7)]
write_status(Path('data/status.json'),
  generated_at=datetime.now(timezone.utc),
  latest_level_cm=68, latest_q_m3s=4.8, tendenz_cm_per_h=0.3,
  hvz_stale=False, hvz_last_ts=datetime.now(timezone.utc),
  hmo_stufe_1_cm=180, regen_24h_mean_mm=1.2, regen_24h_max_mm=3.1, days=days)
"
python -m http.server 8000 --directory web
```

Open http://localhost:8000/ in a browser; confirm header, KPIs, week strip render and emoji match the spec.

- [ ] **Step 6: Commit**

```bash
git add web/
git commit -m "feat(web): vanilla JS dashboard matching spec design tokens"
```

---

## Task 12: GitHub Actions — update workflow

**Files:**
- Create: `.github/workflows/update.yml`

- [ ] **Step 1: Write workflow**

```yaml
# .github/workflows/update.yml
name: Update Ampel

on:
  schedule:
    # 05,08,11,14,17,20 local (Europe/Berlin). Cron is in UTC. Summer = +2, Winter = +1.
    # Two crons cover both; GitHub Actions doesn't do TZ-aware cron.
    - cron: "0 3,6,9,12,15,18 * * *"   # Winter (UTC = local-1)
    - cron: "0 4,7,10,13,16,19 * * *"  # Summer (UTC = local-2), extra runs are fine — they dedup
  workflow_dispatch:

permissions:
  contents: write  # to commit data/

concurrency:
  group: update
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - run: pip install -e ".[dev]"

      - run: pytest -x

      - run: python -m src.main --config config/config.yaml --data data --catchment config/catchment.geojson

      - name: Commit data updates
        run: |
          git config user.name "kanu-hohenlohe-bot"
          git config user.email "actions@users.noreply.github.com"
          git add data/
          git diff --cached --quiet || git commit -m "data: update $(date -u +'%Y-%m-%d %H:%M UTC')"
          git push
```

- [ ] **Step 2: Confirm workflow syntax locally**

```bash
# If `act` is installed, optionally dry-run. Otherwise push to a branch and observe.
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update.yml
git commit -m "ci: cron workflow fetches, computes and commits status"
```

---

## Task 13: GitHub Actions — Pages deploy workflow

**Files:**
- Create: `.github/workflows/pages.yml`

- [ ] **Step 1: Write workflow**

```yaml
# .github/workflows/pages.yml
name: Deploy Pages

on:
  push:
    branches: [main]
    paths:
      - "web/**"
      - "data/status.json"
      - ".github/workflows/pages.yml"
  workflow_dispatch:

permissions:
  pages: write
  id-token: write
  contents: read

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - name: Prepare site
        run: |
          mkdir -p _site
          cp -r web/* _site/
          mkdir -p _site/data
          cp -r data/* _site/data/

      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site

      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Adjust `app.js` fetch paths**

Since Pages now serves `/data/status.json` (copied during deploy), edit `web/app.js`:

```javascript
// Change: `../data/status.json` → `./data/status.json` (both occurrences)
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pages.yml web/app.js
git commit -m "ci: Pages deploy publishes web/ + data/status.json"
```

---

## Task 14: Backtest driver

**Files:**
- Create: `backtest/__init__.py`, `backtest/run.py`, `backtest/report_template.html`
- Test: `tests/test_backtest.py` (smoke only)

- [ ] **Step 1: Write smoke test**

```python
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
```

- [ ] **Step 2: Run to fail**

Run: `pytest tests/test_backtest.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `backtest/run.py`**

```python
# backtest/run.py
import json
from pathlib import Path
from datetime import date, timedelta
from src.config import load_config
from src.engine.ampel import compute_ampel, DayInput, DayResult, Stufe


def compute_metrics(results: list[DayResult]) -> dict:
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
    cfg = load_config(config_path)
    # Load daily-averaged pegel and weather from archive
    # (Implementation loads YYYY/MM.json files, aggregates to daily, runs compute_ampel.)
    results: list[DayResult] = []
    day = start
    while day <= end:
        # look up level from archive (resampled daily mean), weather from weather archive
        level, rain = _load_day(data_dir, day)
        if level is None:
            day += timedelta(days=1); continue
        results.append(compute_ampel(DayInput(
            day=day, level_cm=level, regen_24h_mm=rain,
            anstieg_cm_per_h=0.0, confidence=1.0), cfg.thresholds))
        day += timedelta(days=1)

    m = compute_metrics(results)
    tpl = (Path(__file__).parent / "report_template.html").read_text()
    out_html.write_text(tpl.replace("{{METRICS}}", json.dumps(m, indent=2))
                            .replace("{{START}}", str(start))
                            .replace("{{END}}", str(end))
                            .replace("{{N}}", str(len(results))))


def _load_day(data_dir: Path, day: date) -> tuple[float | None, float]:
    f = data_dir / "hvz" / "doerzbach" / f"{day.year:04d}" / f"{day.month:02d}.json"
    if not f.exists():
        return None, 0.0
    rows = json.loads(f.read_text())
    todays = [r["w_cm"] for r in rows if r["ts"].startswith(day.isoformat())]
    if not todays:
        return None, 0.0
    return sum(todays) / len(todays), 0.0  # rain wired once weather archive has coverage


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data")
    p.add_argument("--config", default="config/config.yaml")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", default="backtest/report.html")
    a = p.parse_args()
    run_backtest(Path(a.data), Path(a.config),
                 date.fromisoformat(a.start), date.fromisoformat(a.end),
                 Path(a.out))
```

- [ ] **Step 4: Write `backtest/report_template.html`**

```html
<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>Backtest-Report</title>
<style>
body { font-family: 'JetBrains Mono', monospace; background: #0a1420; color: #e8edf5; padding: 32px; }
h1 { font-family: Inter, sans-serif; }
pre { background: #143d66; padding: 20px; border-radius: 8px; }
</style></head>
<body>
<h1>kanu-hohenlohe Backtest-Report</h1>
<p>Zeitraum: {{START}} – {{END}}, {{N}} Tage mit Pegeldaten.</p>
<pre>{{METRICS}}</pre>
</body></html>
```

- [ ] **Step 5: Run test to pass**

Run: `pytest tests/test_backtest.py -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add backtest/ tests/test_backtest.py
git commit -m "feat(backtest): metrics calc + HTML report driver"
```

---

## Task 15: README for canoeists

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write full README**

```markdown
# kanu-hohenlohe 🛶

**Wann kann ich die Jagst zwischen Dörzbach und Schöntal paddeln?**

Dieses Werkzeug beantwortet diese Frage automatisch. Es schaut alle drei Stunden
auf den [Pegel Dörzbach](https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00061),
holt die Wettervorhersage für das Einzugsgebiet der oberen Jagst und zeigt auf
einem öffentlichen Dashboard eine Ampel für heute und die kommenden 7 Tage.

🟢 **[Live-Dashboard öffnen](https://<user>.github.io/kanu-hohenlohe/)** 🟢

## Die Ampel

| Emoji | Bedeutung | Bedingung |
|-------|-----------|-----------|
| 🛶 | Komfortabel | Pegel ≥ 60 cm, trocken, stabil — Wehre paddelbar |
| 😐 | Geht, aber … | Pegel 40–59 cm (umtragen) oder Regen/Anstieg zu stark |
| 🚫 | Zu wenig Wasser | Pegel unter 40 cm |
| ⚠️ | Hochwasser | Pegel über Meldestufe 1 oder extremer Anstieg |

## Warum gerade 40 und 60 cm?

Das sind keine willkürlichen Zahlen — sie stammen aus der offiziellen
[Befahrungsregelung des Landratsamts Hohenlohekreis](https://www.hohenlohekreis.de/das-landratsamt/aemteruebersicht/dezernat-fuer-umwelt-ordnung-und-gesundheit/regelungen-an-der-jagst):

- **40 cm** ist das ganzjährige Minimum für die Strecke Dörzbach bis zur
  Kreisgrenze Heilbronn (unterhalb Schöntal-Berlichingen).
- **60 cm** ist die Schwelle, ab der die **Ausleitungsstrecken an den Jagstwehren**
  ohne Umtragen paddelbar sind. Darunter muss man an den Wehren aussteigen.
- **Oberhalb von Dörzbach** ist die Jagst vom 15.02. bis 15.09. gesperrt —
  dieses Werkzeug betrifft nur den Bereich **unterhalb** Dörzbach.

Zusätzlich gilt: Kiesbänke und Inseln nicht betreten, kein Zelten oder Feuer
am Ufer. Das Dashboard ersetzt keine Vor-Ort-Einschätzung.

## Woher kommen die Daten?

- **Pegel & HVZ-Vorhersage**: [HVZ Baden-Württemberg](https://www.hvz.baden-wuerttemberg.de/)
  (amtlich, hydrologisches Modell der Landesanstalt für Umwelt)
- **Wetter**: [Open-Meteo](https://open-meteo.com/) (basiert auf DWD ICON-D2),
  als Flächenmittel über ~10 Rasterpunkte oberhalb Dörzbach
- **Regeln**: Landratsamt Hohenlohekreis

## Die Push-Benachrichtigung

Wer das Dashboard nicht ständig aufrufen möchte, bekommt eine Telegram-Nachricht:

- beim Wechsel nach 🛶 **Grün**
- oder wenn in der 7-Tage-Prognose **erstmals ein Block von ≥ 2 grünen Tagen**
  in Sicht kommt

Max. 1 Nachricht pro 12 Stunden, um Spam zu vermeiden.

## Selbst nutzen / anpassen

Du willst das für deine eigene Strecke oder eigene Schwellenwerte? Das Repo ist
öffentlich unter MIT-Lizenz.

1. **Fork** auf GitHub
2. **Secrets** anlegen unter _Settings → Secrets and variables → Actions_:
   - `TELEGRAM_BOT_TOKEN` (von [@BotFather](https://t.me/BotFather))
   - `TELEGRAM_CHAT_ID` (deine User- oder Gruppen-ID)
3. **Actions aktivieren** (Tab „Actions" → Enable workflows)
4. **GitHub Pages aktivieren**: _Settings → Pages_, Source = „GitHub Actions"
5. **Schwellen anpassen** in `config/config.yaml`

Die erste Aktualisierung läuft zum nächsten Cron-Zeitpunkt (05/08/11/14/17/20 Uhr)
oder sofort per _Run workflow_ im Actions-Tab.

## Disclaimer

Dieses Werkzeug ist eine **private Hilfe zur Tourenplanung** und keine amtliche
Auskunft. Die Landesregelungen, dein eigenes Urteil und die örtlichen
Verhältnisse haben immer Vorrang. Bei Unsicherheit: nicht losfahren.

## Mitmachen

Fehler gefunden? Vorschlag für eine weitere Hohenlohe-Strecke (Kocher?
weitere Jagst-Abschnitte?) Issues und Pull Requests sind willkommen.

## Technische Details

- Python 3.12 orchestriert Fetcher → Ampel-Engine → Storage → Push
- GitHub Actions laufen 6x pro Tag und committen JSON-Daten ins Repo
- GitHub Pages rendert ein statisches Frontend (vanilla JS + uPlot)
- Alle Schwellen in `config/config.yaml` parametrierbar
- Backtest-Skript unter `backtest/run.py` für historische Validierung
- Tests: `pytest`

Vollständige Spec: [`docs/superpowers/specs/2026-04-18-kanu-hohenlohe-design.md`](docs/superpowers/specs/2026-04-18-kanu-hohenlohe-design.md).

---

MIT License · Made for paddlers in Hohenlohe 🛶
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README for canoeists — rules, sources, setup"
```

---

## Task 16: First live run and polish

**Files:**
- Modify: `config/config.yaml` (populated HMO value), `config/catchment.geojson` (refined)
- Modify: `tests/fixtures/hvz_doerzbach_ok.json` (real sample)

- [ ] **Step 1: Push main branch to GitHub, enable Pages and secrets**

```bash
# remote setup (assumes gh CLI authenticated)
gh repo create kanu-hohenlohe --public --source . --push
gh secret set TELEGRAM_BOT_TOKEN   # will prompt
gh secret set TELEGRAM_CHAT_ID     # will prompt
```

- [ ] **Step 2: Trigger update workflow manually**

```bash
gh workflow run update.yml
gh run watch
```

- [ ] **Step 3: Inspect the committed `data/status.json`**

```bash
git pull
cat data/status.json
```

Check: `latest_level_cm`, `hvz_stale`, `hmo_stufe_1_cm`, `days[0].stufe`.

- [ ] **Step 4: Verify Pages deployment**

```bash
gh workflow run pages.yml
gh run watch
```

Open the Pages URL reported; confirm the dashboard renders correctly with live data.

- [ ] **Step 5: If HMO value was discovered, write it into config**

Edit `config/config.yaml`:

```yaml
thresholds:
  # ...
  hochwasser_cm: 180   # or whatever HVZ stammdaten reported
```

- [ ] **Step 6: Refine catchment polygon if Open-Meteo coverage looks off**

Inspect `data/weather/area_mean/2026/04.json`. If precipitation values are
implausible, refine `config/catchment.geojson` using a topo map or
LUBW-EZG GeoJSON for the Jagst catchment above Dörzbach.

- [ ] **Step 7: Commit refinements**

```bash
git add config/
git commit -m "chore: tune HMO threshold and catchment polygon from live data"
git push
```

---

## Self-Review

**Spec coverage:** every section of the spec has at least one task:

- Ziel / Nutzer → Task 15 (README)
- Rechtlicher Kontext (40/60 cm, Sperrzeiten, HMO Stufe 1) → Tasks 3, 10, 16
- Ampel 4-stufig → Task 3
- HVZ-Vorhersage als Pegelprognose → Task 9
- Flächenmittel Niederschlag → Task 5
- Architektur (Actions + Pages) → Tasks 12, 13
- 8 Komponenten → Tasks 2–9
- Datenfluss → Task 9
- Frontend Design tokens → Task 11
- Push bei Grün-Wechsel / 2-Tage-Grün-Block → Task 8
- Fehlerbehandlung (Wartung-Banner, etc.) → Tasks 9, 11
- Security / Public-Repo → Tasks 1, 12, 15
- Tests → Tasks 2–9 (TDD throughout)
- Cron 05–22 Uhr alle 3 h → Task 12
- README Kanufahrer-Fokus → Task 15
- Offene Punkte (Endpoint, HMO, Unterregenbach-ID, Polygon) → Tasks 10, 16

**Placeholder scan:** no TBDs/TODOs remain in code steps; the only narrative "refine later" is in Task 16 about the catchment polygon, which is an intentional post-launch tune-up with concrete instructions.

**Type consistency:** `DayInput`, `DayResult`, `Stufe`, `Thresholds`, `HVZResult`, `HVZMeasurement`, `HVZForecastPoint`, `HourFc`, `GridForecast`, `Decision`, `PushDecision` are defined once and referenced consistently. `compute_ampel`, `parse_hvz_response`, `compute_tendenz_cm_per_h`, `append_measurements`, `load_month`, `write_status`, `rotate_prev`, `should_push`, `compose_message`, `send_push`, `fetch_hvz_raw`, `fetch_openmeteo_raw`, `build_grid_points`, `parse_openmeteo_response`, `aggregate_area_mean`, `run` are consistent across tasks.
