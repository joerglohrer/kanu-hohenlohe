# CLAUDE.md

Leitfaden für künftige Claude-Sessions, die in diesem Repo arbeiten.

## Worum geht's

`kanu-hohenlohe` ist ein öffentliches GitHub-Projekt, das automatisch eine Ampel
für die Befahrbarkeit der Jagst-Strecke Dörzbach → Schöntal ausgibt. Pegel-
und Wetterdaten werden per Cron alle 3 Stunden geholt, die Ampel berechnet,
ein statisches Dashboard deployed und bei positiven Transitionen ein Telegram-
Push gesendet. Architektur, Rationalia und Designentscheidungen stehen in
`docs/superpowers/specs/2026-04-18-kanu-hohenlohe-design.md` — das ist die
autoritative Referenz. Der Implementierungsplan steht daneben in
`docs/superpowers/plans/2026-04-18-kanu-hohenlohe.md`.

## Grundregeln für Änderungen

- **Sprache der Antworten:** Deutsch (auch Commit-Messages und User-facing Texte
  wie README, Dashboard, Telegram-Nachricht). Code-Kommentare: englisch ok.
- **TDD ist verbindlich** für die reine Entscheidungslogik (`src/engine/ampel.py`)
  und Storage (`src/storage/archive.py`). Immer: Test zuerst, dann Code.
- **Pure Functions** sind das Rückgrat: Fetcher haben keine Entscheidungslogik,
  die Ampel-Engine kennt kein HTTP, Storage kennt kein Schema. Diese Grenzen
  NICHT aufweichen.
- **Frozen Dataclasses** wo immer möglich. Mutation wird später zu Bugs.
- **Jede Datei unter ~200 Zeilen.** Wenn eine Datei wächst: Verantwortung
  falsch geschnitten. Aufteilen vor einer Erweiterung.
- **Keine neuen Top-Level-Dateien** ohne Grund. Keine Docs erzeugen, die nicht
  ausdrücklich gewünscht sind.
- **Secrets niemals in Commits, Kommentaren oder Prompts.** Alle Credentials
  ausschließlich als GitHub-Actions-Secrets. Wenn der Nutzer versehentlich
  einen Token hier paste, sofort stoppen und Rotation einfordern.

## Repo-Layout (Kurzfassung)

```
src/
  config.py          Typed YAML loader mit strikter Validierung.
  engine/ampel.py    Pure function (DayInput, Thresholds) -> DayResult.
                     Kennt die Ampel-Stufen und Emoji-Map. Kein I/O.
  fetcher/
    hvz.py           HVZ-Live-Fetch via JS stammdaten scraping
                     (hvz_peg_stmn.js) + parse_hvz_response für Fixture-Shape.
                     Liefert pro Call nur den jüngsten Messwert (HVZ-Seite
                     bietet keine Rohdaten-Zeitreihe).
    wetter.py        Open-Meteo-Batch (alle Catchment-Punkte in 1 Request)
                     mit 3× Retry, Flächenmittel, Grid-Builder via shapely.
  storage/
    archive.py       Monatliche JSON-Dateien, idempotenter Append.
    status.py        Single-Source-of-Truth status.json + rotate_prev.
  notify/telegram.py should_push (dedup + 12 h rate-limit), compose_message,
                     send_push (Bot API, liest Env Secrets).
  main.py            Orchestrator: fetch → ampel → archive → status → push.
                     run() ist keyword-only.

config/
  config.yaml        Schwellen (min 40, komfort 60, HMO 220) und Pegel-IDs
                     (Dörzbach 00061, Jagstzell 00048).
  catchment.geojson  Grob-Polygon des oberen Jagst-Einzugsgebiets.

tests/               47 pytest-Tests. Alle offline via Fixtures.
  fixtures/          HVZ + Open-Meteo Beispiel-Responses.

web/
  index.html / styles.css / app.js   Statisches Dashboard.
  vendor/uPlot*      Charts.

backtest/
  run.py             Historische Simulation + HTML-Report. First cut, noch
                     nicht produktiv verwendet (braucht Zeitreihen-Backfill).

.github/workflows/
  update.yml         Cron: 05/08/11/14/17/20 lokal, wenn Lauf erfolgreich
                     wird data/ committet und gepusht.
  pages.yml          Deployed web/ + data/* nach GitHub Pages bei Push auf main.

docs/
  superpowers/
    specs/…-design.md     Spec — autoritativ bei Konflikten mit Code.
    plans/…kanu-….md      Implementierungsplan (Task 1–16).
  RELEASE.md              Schritte für First Live Deploy (bereits gelaufen).
  HANDOFF.md              Stand, offene Punkte, Roadmap für nächste Session.

CLAUDE.md                 Diese Datei.
```

## Häufige Arbeiten

### Neue Ampel-Regel oder Schwelle ändern

1. Test zuerst in `tests/test_ampel.py` (Tabellen-Test-Stil beibehalten).
2. Logik in `src/engine/ampel.py`. Entscheidungs-Reihenfolge bleibt: confidence →
   extreme rise → HMO → min → komfort → regen → anstieg → grün.
3. Wenn parametrierbar: Feld in `Thresholds` (src/config.py) + Default in
   `config/config.yaml` + Validation.
4. Frontend zeigt neue Info? → `web/app.js` erweitern (stabile status.json-Schlüssel).
5. Commit: `feat(engine): …` oder `fix(engine): …`.

### Neuer Pegel / neue Strecke

- Nicht einfach `gauges.xyz` in der Config anhängen — die Ampel-Logik geht
  derzeit von genau 2 Pegeln aus (Dörzbach + Jagstzell als Frühindikator).
  Für eine echte Mehr-Strecken-Architektur müsste die Spec erweitert werden.
  Vorher mit Nutzer brainstormen (superpowers:brainstorming).

### HVZ-Format ändert sich (Schlüsselrisiko)

- `src/fetcher/hvz.py` hat Column-Position-Konstanten (POS_STN, POS_W, POS_HMO etc.).
  Wenn die HVZ-Baden-Württemberg die Reihenfolge ändert, bricht der Parser.
- Symptom: Action läuft durch, aber status.json zeigt unsinnige Werte
  (latest_level_cm: None oder extreme Zahlen).
- Fix: `hvz_peg_stmn.js` herunterladen, Zeile für Pegel 00061 inspizieren,
  Konstanten anpassen, Fixture aktualisieren, Tests laufen lassen.

### Open-Meteo API-Pfad / Parameter-Änderung

- `src/fetcher/wetter.py` in `fetch_openmeteo_batch`. Aktuell:
  `https://api.open-meteo.com/v1/forecast` mit komma-separierten
  `latitude`/`longitude` und `hourly=precipitation,cloud_cover`.
- Timeouts: 3 Retries mit Backoff (0/2/5 s), bei Ausfall graceful degradation
  (weather_stale=true, area=leer). NICHT ohne Grund ändern.

### Frontend-Änderung

- `web/` ist reines Vanilla JS + uPlot. Keine Build-Tools.
- Nach Änderung: lokal mit `python -m http.server 8765 --directory web` testen
  (vorher `cp data/status.json web/data/` für einen lokalen Render).
- Pages-Deploy geschieht automatisch bei Push auf main mit Änderung an `web/**`
  oder `data/status.json`.

### Dependency-Update

- `pyproject.toml` anpassen, `pip install -e ".[dev]"`, `pytest` laufen lassen.
- Bei Major-Versionen von `requests`, `shapely`, `beautifulsoup4` (aktuell nicht
  verwendet, entfernen wenn unbenutzt) genau hinschauen.

## Testen

```bash
source .venv/bin/activate
pytest -v                    # Kompletter Lauf (47 Tests in ~0.3s)
pytest tests/test_ampel.py   # Einzelnes Modul
```

Lokale End-to-End-Probe (ohne Push):

```bash
python - <<'PY'
import os
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "probe-dummy")
os.environ.setdefault("TELEGRAM_CHAT_ID", "probe-dummy")
import src.notify.telegram as tg
tg.send_push = lambda text: print(f"[probe] would send: {text[:80]}")
from pathlib import Path
from src import main
main.run(config_path=Path("config/config.yaml"),
         data_dir=Path("data"),
         catchment_path=Path("config/catchment.geojson"))
PY
```

## Deployment

- **Update-Workflow** läuft alle 3 h selbstständig. Manuell: `gh workflow run update.yml`.
- **Pages-Workflow** triggert bei Push auf `main` mit Änderung an `web/**` oder
  `data/status.json`. Manuell: `gh workflow run pages.yml`.
- Beide Workflows sind unter `.github/workflows/`.

## Sensible Punkte

- **Telegram-Token im Chat:** Nutzer hat beim ersten Deploy versehentlich einen
  Token im Klartext geschickt. Der wurde rotiert. Falls so etwas wieder
  passiert: sofort Rotation anordnen, nicht selbst verwenden.
- **HMO-Schwelle** hat zwei plausible Kandidaten in der HVZ-Datenstruktur
  (POS_HMO=220 cm vs. POS_HWB=225 cm). Wir nutzen POS_HMO (Hochwasser-
  meldeordnung) weil das die amtliche Meldestufe 1 ist. NICHT ohne
  Verifikation ändern.
- **Catchment-Polygon** ist ein Bounding-Box-Approximation der oberen Jagst.
  Für präziseres Wetter-Flächenmittel: LUBW-Einzugsgebietsdaten nutzen.

## Was NICHT tun

- Keine Session-Keys, Chat-IDs, Bot-Tokens in Commits, Kommentaren oder Tests.
- Keine Workflows mit `--no-verify` oder gesetztem `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true` nur wegen Deprecation-Warnungen. Das Upgrade auf
  checkout@v5 / setup-python@v6 wird ein eigener PR sein, bewusst gemacht.
- Keine `data/` manuell committen. Die Cron-Action macht das. Ausnahme: Backfill-
  Tasks (mit klarem Commit-Message-Präfix `data: backfill …`).
- Keine Emojis im Code anders als in `engine/ampel.py` (Stufe→Emoji-Map) und
  `web/` (Frontend). User-facing deutsche Texte dürfen Emojis haben,
  Log-/Debug-Strings nicht.

## Wie weitermachen

Siehe `docs/HANDOFF.md` für den aktuellen Stand, offene Punkte und Ideen für
die nächste Session.
