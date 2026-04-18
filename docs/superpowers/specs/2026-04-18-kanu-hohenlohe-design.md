# kanu-hohenlohe — Design-Spec

**Stand:** 2026-04-18
**Repo-Name:** `kanu-hohenlohe`
**Lizenz:** MIT

## Ziel

Ein Werkzeug, das dem Nutzer verlässlich sagt, wann die Jagst-Strecke Dörzbach → Schöntal mit dem Kanu befahrbar ist. Es kombiniert amtliche Pegelmessungen, HVZ-Pegelvorhersage und Wettermodell-Flächenniederschlag, bewertet die Bedingungen über eine konfigurierbare vierstufige Ampel, publiziert ein öffentliches Dashboard auf GitHub Pages und benachrichtigt per Telegram-Push, wenn eine Tour realistisch wird.

Der erste Anwendungsfall ist Dörzbach → Schöntal. Repo-Name und Architektur sind offen für spätere Ergänzung weiterer Hohenlohe-Strecken (weitere Jagst-Abschnitte, Kocher).

## Nutzer und Nutzungskontext

Der Nutzer ist Kanufahrer im Hohenlohekreis. Er will nicht mehrmals täglich HVZ und Wetterdienst manuell checken, sondern informiert werden, wenn eine Tour in den nächsten Tagen realistisch wird. "Realistisch" heißt: ausreichend Wasser, kein Umtragen nötig, kein Dauerregen am Tourtag, keine Hochwassergefahr. Das Werkzeug läuft vollständig auf GitHub (Actions + Pages), das Repo ist öffentlich.

## Rechtlicher und hydrologischer Kontext

Maßgeblich ist der Pegel **Dörzbach an der Jagst** (HVZ-ID 00061, https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00061) sowie die Befahrungsregelungen des Landratsamts Hohenlohekreis:

- **Strecke Bauhof Dörzbach bis Kreisgrenze Heilbronn** (unterhalb Schöntal-Berlichingen) ganzjährig befahrbar ab **40 cm** am Pegel Dörzbach.
- **Ausleitungsstrecken an Jagstwehren** sind ohne Umtragen erst ab **60 cm** Pegel paddelbar.
- Oberhalb Dörzbach (Mulfingen-Eberbach bis Dörzbach) 15.02.–15.09. gesperrt. Diese Sperrung betrifft die Zielstrecke nicht.
- Weitere Vorgaben (Kiesbänke/Inseln nicht betreten, kein Zelten/Feuer am Ufer) werden in der README als Hinweis aufgenommen, aber nicht vom Werkzeug durchgesetzt.
- Hochwassergrenze: Ampel-Stufe "Rot-Hochwasser" setzt ab HVZ-Meldestufe 1 ein. Der cm-Wert ist dem Werkzeug zunächst unbekannt und wird beim ersten Live-Lauf aus den HVZ-Stammdaten gezogen; Override per Config möglich.

Als Frühindikator für aufziehendes Wasser wird zusätzlich ein oberhalb gelegener Pegel beobachtet (voraussichtlich **Unterregenbach** — exakte HVZ-ID beim ersten Lauf zu bestätigen).

## Ampel — die Entscheidungslogik

Vier Stufen, jeweils mit Emoji-Darstellung im Dashboard:

| Emoji | Stufe | Bedingung (Default, per Config überschreibbar) |
|-------|-------|-----------------------------------------------|
| 🛶 | Grün · komfortabel | Pegel ≥ 60 cm UND 24-h-Regenprognose Einzugsgebiet (Flächenmittel) ≤ 5 mm UND keine starke Anstiegstendenz (< 3 cm/h) UND Pegel < HW-Meldestufe 1 |
| 😐 | Gelb · pragmatisch | Pegel 40–59 cm (Ausleitungen umtragen), oder Grün-Bedingungen aber Regen/Tendenz verletzt |
| 🚫 | Rot · zu wenig | Pegel < 40 cm |
| ⚠️ | Rot · Hochwasser | Pegel ≥ HW-Meldestufe 1, oder extreme Anstiegstendenz |

Die Ampel wird für Heute und die folgenden 7 Tage berechnet. Ab dem Horizont, an dem die HVZ-Pegelvorhersage endet (typ. 24–48 h) oder die Wettervorhersage an Verlässlichkeit verliert, wird die Stufe als "ungewiss" markiert und im Dashboard grau dargestellt.

### Datengrundlage für die Prognose

Hybrider Ansatz (bewusst gewählt gegenüber eigenes hydrologisches Modell):

- **Pegelprognose**: wird von der HVZ übernommen. Die HVZ betreibt ein amtlich kalibriertes Niederschlag-Abfluss-Modell; wir duplizieren das nicht.
- **Wetterdaten**: dienen als **Komfortkriterium für den Tourtag** (Niederschlag, Bewölkung) und als **Tendenzsignal jenseits des HVZ-Horizonts**, nicht zur eigenen Pegelvorhersage.
- **Flächenmittel des Niederschlags** aus ~10 Rasterpunkten auf dem Einzugsgebiets-Polygon oberhalb Dörzbach. Punktmittel wäre bei Dauerregen-Szenarien unzureichend.

## Architektur

```
┌──────────────────────────────────────────────────────────────┐
│ GitHub Actions (Cron 05–22 Uhr, alle 3 h; + workflow_dispatch)│
│                                                                │
│   HVZ-Fetcher ─┐                                              │
│   Wetter-Fetcher ─┤→ Ampel-Engine → Storage ─┬→ status.json   │
│   (Config) ─────┘   (reine Funktion)        │                 │
│                                              ├→ Zeitreihen    │
│                                              │  (hvz/wetter)  │
│                                              └→ Notify (Push) │
│                                                                │
│   → Git-Commit                                                │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    GitHub Pages (statisch)
                    liest status.json + Zeitreihen
```

### Komponenten

Jede Datei unter ~200 Zeilen, klare Verantwortlichkeit, reine Funktionen wo immer möglich.

| Modul | Verantwortung |
|-------|---------------|
| `fetcher/hvz.py` | HVZ-API-Zugriff für Pegel Dörzbach und Unterregenbach; Parsing aktueller Messwerte, Historie der letzten 3 h, HVZ-Vorhersage, HW-Stammdaten. Kennt keine Entscheidungslogik. |
| `fetcher/wetter.py` | Open-Meteo-API-Zugriff für Rasterpunkte des Einzugsgebiets. Bildet Flächenmittel pro Stunde und maximalen Stundenwert (für Gewittererkennung). |
| `engine/ampel.py` | Reine Funktion: `(hvz_now, hvz_forecast, weather_forecast, config) → {day: (stufe, begründung, confidence)}`. Die gesamte Entscheidungslogik. |
| `storage/archive.py` | Monatliche JSON-Dateien (`data/hvz/2026/04.json`, `data/weather/2026/04.json`). Idempotentes Anhängen neuer Messwerte. |
| `storage/status.py` | Schreibt `data/status.json` (Single-Source-of-Truth für Frontend). |
| `notify/telegram.py` | Sendet Push. Liest `status.json` vs. `status.json.prev`, dedupliziert, respektiert Hard-Limit max. 1 Push / 12 h. |
| `web/` | Statische Seite (Vanilla JS + uPlot oder Chart.js). Liest `data/status.json` und Zeitreihen direkt aus dem Repo. |
| `backtest/run.py` | Einmaliges Skript: Simulation der Ampel über 5 Jahre historische HVZ- und Wetterdaten; erzeugt `backtest/report.html` mit Metriken. |
| `config.yaml` | Alle Schwellwerte (Pegel min/komfort/hochwasser, max. Regen mm, max. Anstieg cm/h, Pegel-IDs, Einzugsgebiets-Polygon-Referenz). |

### Datenfluss eines Cron-Laufs

1. HVZ-Fetcher holt Messwerte + Vorhersage für beide Pegel; beim allerersten Lauf auch Stammdaten (Meldestufen).
2. Wetter-Fetcher holt Open-Meteo-Forecast für Rasterpunkte, bildet Flächenmittel.
3. Ampel-Engine berechnet für Heute + 7 Tage Stufe, Begründung und Confidence.
4. Storage hängt neue Messwerte an Zeitreihen an, schreibt neues `status.json`.
5. Notify vergleicht mit `status.json.prev`, entscheidet Push (nur bei Wechsel nach Grün oder bei erstmaligem ≥2-Tage-Grün-Block in Prognose), deduppt via Zeitstempel.
6. Git-Commit "data update YYYY-MM-DD HH:MM"; Push → GitHub Pages aktualisiert automatisch.

Backtesting läuft separat (on-demand oder monatlich) und publiziert einen HTML-Report.

## Frontend-Design

### Visuelle Sprache

- **Header**: Farbverlauf `#1e5a8c → #2e7ab0 → #4a9fd4` (Flusswasser am Tag). Pegelzahl groß (72 px, Inter 700), Ampel-Emoji daneben (64 px), darunter Status in einem Satz und Kontextzeile mit Tendenz/Prognose. Rechts oben Zeitstempel und Status "Aktualisiert vor X min".
- **Body**: dunkel `#0a1420`, darauf Kacheln in `#143d66` / `#0f1a2a`. Wirkt wie ein Control-Room-Dashboard.
- **Typografie**: Inter für Zahlen und Überschriften; JetBrains Mono für Labels, Daten, Zeitstempel.
- **Akzentfarben**: Eisblau `#7dd3fc` (Messkurve), Hellgrün `#a8f0b5` (Grün-Status), Gelb `#f5d97a` (Gelb-Status), Rot wird nur durch Emoji ⚠️/🚫 transportiert, nicht durch Flächenfarbe.

### Layout von oben nach unten

1. **Hero / Status** — Pegelzahl, Ampel-Emoji, Statussatz, Kontextzeile, Zeitstempel
2. **KPI-Leiste** (4 Kacheln) — Abfluss (m³/s mit Tendenz), Tendenz (cm/h), Regen EZG 24 h (Flächenmittel + lokaler Max.), HW-Stufe 1 (Wert + Abstand)
3. **Hauptchart** — Pegel letzte 14 Tage + HVZ-48-h-Vorhersage, mit gestrichelten Referenzlinien bei 40 cm und 60 cm, Prognosebereich markiert
4. **Regenstreifen** — stündlicher Flächenmittel-Niederschlag nächste 48 h, starke Stunden in Gelb
5. **7-Tage-Ausblick** — 7 Kacheln mit Ampel-Emoji, erwartetem Pegel, Regen-Summe, Wetter-Icon; Kacheln jenseits des verlässlichen Horizonts sichtbar gedämpft ("ungewiss")
6. **Optional Kartenlayer** (spätere Ausbaustufe) — LUBW HWGK-Überflutungsflächen über Leaflet-WMS

### Push-Benachrichtigung

- Trigger: Wechsel von Gelb/Rot nach Grün, oder erstmaliges Erscheinen eines Grün-Blocks ≥ 2 Tage in der 7-Tage-Prognose.
- Nachricht in Deutsch, kurz, mit Pegel und Tagen: "🛶 Jagst Dörzbach paddelbar: Pegel 68 cm, Sa/So/Mo komfortabel. Regen erst Di."
- Kanal: Telegram, Bot-Token als GitHub-Actions-Secret.

## Fehlerbehandlung

Grundprinzip: niemals stille Fehler. Jeder fehlende Datensatz ist im Dashboard sichtbar, jeder fehlgeschlagene Run in den Action-Logs.

- **HVZ-Pegel in Wartung** (real beobachtet am 18.04.2026): Banner im Dashboard "Pegel in Wartung, letzter Wert XX cm am HH:MM". Ampel wird nur aus Daten ≤ 6 h alt berechnet; sonst "—".
- **HVZ-Endpoint/Format ändert sich**: Lauf scheitert, Action schlägt fehl, kein Commit. Alter Status bleibt sichtbar; Banner erscheint ab 12 h ohne Update.
- **Open-Meteo nicht erreichbar**: Pegel-Ampel weiter aktiv (ohne Wetter-Komfortfilter), Dashboard zeigt Hinweis.
- **Unterregenbach-Pegel ausgefallen**: Frühindikator entfällt; Ampel basiert dann nur auf Dörzbach.
- **Telegram-Send fehlschlägt**: Error-Log, aber Daten-Commit geschieht trotzdem. Nächster Lauf probiert erneut.
- **Push-Spam-Schutz**: Deduplizierung per `status.json.prev` + Hard-Limit 1 Push / 12 h.

## Security / Public-Repo-Policy

- Repo ist öffentlich unter MIT-Lizenz.
- Alle Credentials (Telegram-Bot-Token, Telegram-Chat-ID) ausschließlich als GitHub-Actions-Secrets; im Code `os.environ["TELEGRAM_BOT_TOKEN"]`.
- `.env.example` dokumentiert alle nötigen Variablen mit Platzhaltern; `.env` ist gitignored.
- README enthält klaren Fork-Setup-Leitfaden: "Fork → Secrets anlegen → Actions aktivieren".
- Keine Telegram-Chat-IDs, Usernames oder personenbezogenen Informationen in Commits, Issues oder Diskussionen.
- Config, Einzugsgebiets-Polygon, Zeitreihen, Backtest-Reports sind öffentliche Behördendaten und bleiben im Repo.

## Tests

- **Unit-Tests** (Python, pytest):
  - `engine/ampel.py`: Tabellentests mit Input-Kombinationen → erwartete Ampel. Deckt die Entscheidungslogik vollständig ab.
  - `fetcher/*`: Fixtures in `tests/fixtures/` mit echten HVZ-/Open-Meteo-Responses; Parsing wird ohne Netz getestet.
  - `storage/archive.py`: Idempotenz (doppeltes Einspielen erzeugt keine Dopplung).
- **Integrationstest**: End-to-End-Durchlauf aller Fetcher mit Fixtures → `status.json`-Snapshot.
- **Backtest als Validierung**: Über 5 Jahre historische Daten; Metriken Flapping-Rate, Anteil Grün-Tage, Ausreißer (Grün direkt vor Hochwasser). Report in `backtest/report.html`.
- **Kein automatisiertes Browser-Testing** für das Frontend — zu viel Aufwand. Snapshot-Test des erzeugten DOMs genügt.
- **TDD-Disziplin**: Ampel-Engine und Storage werden test-first geschrieben; Fetcher und Frontend begleitend.

## Cron-Schedule

- Wochentags und am Wochenende gleich: 05:00, 08:00, 11:00, 14:00, 17:00, 20:00 lokal (Europe/Berlin). 6 Läufe/Tag.
- Nachts kein Lauf (niemand paddelt um 3 Uhr).
- `workflow_dispatch` für manuelle Auslösung bleibt jederzeit verfügbar.
- HVZ-Archiv bleibt lückenlos in 15-min-Auflösung, weil pro Lauf die letzten 3 h HVZ-Daten nachgeladen werden.

## README (Zielgruppe Kanufahrer)

Deutsch, mit folgender Struktur:

1. **Idee**: "Wann kann ich die Jagst paddeln?" — ein Satz.
2. **Wie es funktioniert**: Pegel + Wetter + Regeln → Ampel + Push.
3. **Befahrungsregeln Hohenlohe**: Kurzfassung der offiziellen Regelungen mit Link.
4. **Live-Dashboard**: Link zu `https://<username>.github.io/kanu-hohenlohe/`.
5. **Limitations / Disclaimer**: "Amtliche Regelungen, eigene Einschätzung und örtliche Verhältnisse haben Vorrang. Das Werkzeug ersetzt keine Vor-Ort-Einschätzung."
6. **Mitmachen**: Wie man Schwellen anpasst, Fehler meldet, eigene Strecken vorschlägt.
7. **Setup für eigene Installation**: Fork → Secrets → Actions aktivieren.
8. **Technische Details** (Dev-Setup, Architektur-Überblick) am Ende.

## Offene Punkte (beim Implementieren zu klären)

- **HVZ-Endpoint für JSON/Rohdaten**: beim ersten Live-Lauf aus Browser-DevTools ermitteln. Fallback: HTML-Scraping der Pegel-Seite.
- **HW-Meldestufen in cm für Pegel Dörzbach**: aus HVZ-Stammdaten ziehen, in Config materialisieren.
- **Exakte HVZ-ID des Pegels Unterregenbach**: verifizieren.
- **Genaues Einzugsgebiets-Polygon**: beim Implementieren aus LUBW-EZG-Daten ableiten; Startnäherung Bounding Box Walxheim/Crailsheim/Langenburg.

Diese Punkte sind Implementierungsdetails, nicht Design-Entscheidungen — sie blockieren die Spec nicht.
