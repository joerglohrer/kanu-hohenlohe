# Handoff — kanu-hohenlohe

**Stand:** 2026-04-18, nach initialem Live-Deployment.
**Repo:** https://github.com/joerglohrer/kanu-hohenlohe
**Dashboard:** https://joerglohrer.github.io/kanu-hohenlohe/

Kurze Orientierung für die nächste Person (oder die nächste Claude-Session).

## Was steht

- 47 pytest-Tests grün, 25+ saubere Commits auf `main`.
- Produktives Deployment: GitHub Pages serviert das Dashboard, Actions-Cron
  läuft alle 3 Stunden (05/08/11/14/17/20 Uhr Europe/Berlin) und committet
  frische Daten.
- Telegram-Push ist konfiguriert (Bot `@kanuhohenlohebot`, Secrets gesetzt).
- Aktueller Pegel Dörzbach zum Deployment-Zeitpunkt: 47 cm → 😐 Gelb.

## Architektur in einem Absatz

Ein Python-Orchestrator (`src/main.py`) holt alle 3 h zwei HVZ-Pegel (Dörzbach,
Jagstzell) über gescrapte JavaScript-Stammdaten der HVZ-BW, dazu eine Open-
Meteo-Flächenwetterprognose (Batch-Request über ein Grob-Polygon des oberen
Jagst-Einzugsgebiets). Eine reine Funktion (`src/engine/ampel.py`) berechnet
daraus eine 4-stufige Ampel (🛶/😐/🚫/⚠️) für heute und die nächsten 7 Tage.
Das Ergebnis landet als `data/status.json` im Repo (Single Source of Truth für
das Frontend) sowie in monatlichen Zeitreihen (`data/hvz/…`, `data/weather/…`).
GitHub Pages rendert ein Vanilla-JS-Dashboard. Bei Wechsel nach Grün oder
einem neuen ≥2-Tage-Grün-Block in der Prognose wird Telegram gepingt,
rate-limited auf max. 1 Push / 12 h. Spec:
[`docs/superpowers/specs/2026-04-18-kanu-hohenlohe-design.md`](superpowers/specs/2026-04-18-kanu-hohenlohe-design.md).

## Was der Code jetzt kann

| Fähigkeit | Status |
|-----------|--------|
| Pegel-Scraping Dörzbach (HVZ 00061) | ✅ live |
| Frühindikator-Pegel Jagstzell (HVZ 00048) | ✅ live |
| Ampel mit 4 Stufen + Begründung | ✅ |
| HMO-Hochwasser-Schwelle (220 cm) aus HVZ-Stammdaten | ✅ |
| Wettervorhersage Flächenmittel über oberes Jagst-EZG | ✅ batch + retry |
| Graceful degradation bei Wetterausfall (`weather_stale=true`) | ✅ |
| Monatliche Zeitreihen-Archive, idempotent | ✅ |
| GitHub Pages Dashboard (Flusswasser-Header + dunkler Body) | ✅ live |
| Telegram-Push bei positiven Transitionen, 12 h Rate-Limit | ✅ konfiguriert |
| Backtest-Driver (Metrics + HTML-Report) | ⚠️ nur Smoke-Test, noch nicht mit echten Daten |
| Regenstreifen im Dashboard zeigt echte Daten | ❌ zeigt Sinus-Vorschau |
| HWGK-Kartenlayer (LUBW) im Dashboard | ❌ nicht implementiert |

## Bekannte Einschränkungen

1. **HVZ liefert pro Request nur den jüngsten Messwert.** Historische Zeitreihen
   entstehen nur durch die akkumulierenden Cron-Läufe. Für ein 5-Jahres-Backtest
   müsste man entweder die HVZ-GIF-Diagramme digitalisieren oder eine externe
   Archiv-Quelle anzapfen (DGJ? GKD-BW? LUBW UDO?). Unklare Machbarkeit.
2. **`tendenz_cm_per_h` ist bis zum zweiten aufeinanderfolgenden Cron-Lauf 0.**
   Aus einem einzelnen Messwert lässt sich kein Anstieg berechnen. Nach ein
   paar Tagen Cron-Betrieb ergibt sich ein belastbarer Trend.
3. **Einzugsgebiets-Polygon** ist eine grobe Bounding Box. Für präzises
   Flächenmittel LUBW-EZG-Daten nutzen.
4. **Frontend-Regenstreifen** ist ein Placeholder, nicht echte Daten. Task 11
   des Ursprungsplans ließ das bewusst offen; echte Anbindung steht aus.
5. **Keine Atomizität** beim Schreiben der JSON-Artefakte. Im Actions-Kontext
   mit Single-Writer-Garantie unkritisch; bei parallelen Schreibvorgängen
   wäre ein temp-file-und-rename nötig.

## Was als Nächstes tun

### Quick Wins (je 30–60 Min)

- **Echte Regen-Daten ins Dashboard.** `web/app.js` → `renderRain()` soll die
  letzten/nächsten 48 h aus `data/weather/area_mean/YYYY/MM.json` laden. Path
  analog zu `renderChart()`. Starke Stunden (> 3 mm) gelb einfärben.
- **Telegram-Testnachricht.** `gh workflow run update.yml` mit einem
  manuellen Wechsel der Config-Schwelle (z.B. komfort_cm auf 45 setzen), damit
  die aktuelle Lage als Grün gilt und ein Push ausgelöst wird. Danach Config
  zurücksetzen. Wichtig: nur als Probe; danach unrotiert zurückbauen.
- **Pages-Workflow auch auf Data-Push reagieren.** Aktuell triggert pages.yml
  nur auf `paths: data/status.json`. Der Update-Workflow pusht aber das
  Commit-SHA als Bot-User — da kann GitHub den Pages-Trigger verzögern.
  Alternative: im Update-Workflow am Ende explizit `gh workflow run pages.yml`
  aufrufen.

### Mittelgross (Halbtag)

- **Node-20-Deprecation.** `actions/checkout@v5`, `actions/setup-python@v6`,
  `actions/upload-pages-artifact@v4` → Major-Bump auf die Nachfolger.
- **Wetter-Archiv in Regenstreifen.** Siehe Quick Win oben, nur gründlich mit
  Fallback, wenn das Monat-JSON noch nicht existiert.
- **HVZ-Retry/Backoff analog zu Open-Meteo.** Aktuell hat `fetch_hvz_live`
  keinen Retry. Bei Timeout fällt die komplette Cron-Iteration aus. 3 Retries
  mit 0/2/5 s Backoff einbauen.
- **Dashboard-Banner bei `hvz_stale` oder `weather_stale` prüfen.** Im
  `renderHero()` ist der Banner für `hvz_stale` da; `weather_stale` hätte
  einen eigenen Hinweis verdient („Wetterdaten aktuell nicht verfügbar").

### Grösser (Tage)

- **Historische HVZ-Zeitreihe beschaffen** (LUBW UDO? DGJ? DWD?) und den
  Backtest real fahren. Spec fordert Flapping-Rate, Grün-Anteil, Ausreißer-
  Analyse über 5 Jahre. Bislang nur Smoke-Test.
- **Mehrere Strecken.** Config-Schema auf Liste von Strecken umstellen, pro
  Strecke eigene Ampel. Architektur dafür ist offen — vorher brainstorming.
- **LUBW-HWGK-Layer ins Dashboard.** Leaflet + WMS. Nice-to-have, visuell stark.
- **Präziseres Einzugsgebietspolygon** aus LUBW-EZG-Shapefile (Wärmeperle!).
- **Tour-Logbuch** als optionale Validierungsgrundlage: Nutzer-Eingabe, wie
  Touren wirklich liefen. Für echte Präzision/Recall der Ampel.

## Wie man weitermacht (für Claude-Sessions)

1. **Immer zuerst** die aktuelle Session-Konventionen laden: `CLAUDE.md` im
   Repo-Root wird bei Claude Code automatisch berücksichtigt.
2. **Sprache:** Deutsch im User-facing und Commits, Code-Kommentare englisch ok.
3. **Bei neuen Features:** erst das `superpowers:brainstorming` Skill
   anwerfen, nicht sofort implementieren.
4. **Vor Deploy:** Immer `pytest -v` (47 Tests müssen grün sein), plus eine
   lokale End-to-End-Probe (siehe CLAUDE.md).
5. **Bei Unsicherheit über Design-Entscheidungen:** die Spec unter
   `docs/superpowers/specs/` ist autoritativ. Wenn dort etwas unklar ist: Nutzer
   fragen, nicht raten.

## Wo Secrets & externe Ressourcen leben

| Was | Wo |
|-----|-----|
| Telegram Bot | `@kanuhohenlohebot` (angelegt 2026-04-18) |
| TELEGRAM_BOT_TOKEN | GitHub Actions Secret (gesetzt) |
| TELEGRAM_CHAT_ID | GitHub Actions Secret (gesetzt) |
| HVZ-Pegel-Daten | https://www.hvz.baden-wuerttemberg.de/ |
| Open-Meteo API | https://api.open-meteo.com/v1/forecast |
| HVZ JS-Stammdaten | https://www.hvz.baden-wuerttemberg.de/js/hvz_peg_stmn.js |
| GitHub Repo | https://github.com/joerglohrer/kanu-hohenlohe |
| Live-Dashboard | https://joerglohrer.github.io/kanu-hohenlohe/ |

## Kontakt / Herkunft

- Projektinitiator: **Jörg Löhrer** (<socialmedia@comenius.de>).
- Ziel: eine verlässliche Push-Benachrichtigung, wann eine Kanutour
  Dörzbach → Schöntal in Frage kommt.
- Entstanden: im Rahmen einer gemeinsamen Claude-Code-Session am 2026-04-18.
  Brainstorming, Spec, Plan und 16 Task-Implementierungen in einer Sitzung.
