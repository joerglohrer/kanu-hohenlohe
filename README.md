# kanu-hohenlohe 🛶

**Wann kann ich die Jagst zwischen Dörzbach und Schöntal paddeln?**

Dieses Werkzeug beantwortet die Frage automatisch. Es schaut alle drei Stunden
auf den [Pegel Dörzbach](https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00061),
holt die Wettervorhersage für das Einzugsgebiet der oberen Jagst und zeigt auf
einem öffentlichen Dashboard eine Ampel für heute und die kommenden 7 Tage.

🟢 **Live-Dashboard:** `https://<user>.github.io/kanu-hohenlohe/` (bitte den Fork-Benutzernamen einsetzen)

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

- **Pegel**: [HVZ Baden-Württemberg](https://www.hvz.baden-wuerttemberg.de/)
  (amtliche Pegeldaten der Landesanstalt für Umwelt), Pegel Dörzbach (00061)
  für den aktuellen Stand und Pegel Jagstzell (00048) als Frühindikator
  flussaufwärts (~7–20 h Vorlaufzeit).
- **Wetter**: [Open-Meteo](https://open-meteo.com/) (basiert auf DWD ICON-D2),
  als Flächenmittel über mehrere Rasterpunkte im Einzugsgebiet oberhalb Dörzbach.
- **Regeln**: Landratsamt Hohenlohekreis.

## Die Push-Benachrichtigung

Wer das Dashboard nicht ständig aufrufen möchte, bekommt eine Telegram-Nachricht:

- beim Wechsel nach 🛶 **Grün**
- oder wenn in der 7-Tage-Prognose **erstmals ein Block von ≥ 2 grünen Tagen**
  in Sicht kommt

Max. 1 Nachricht pro 12 Stunden, um Spam zu vermeiden.

## Selbst nutzen / anpassen

Das Repo ist öffentlich unter MIT-Lizenz. So richtest du dein eigenes Dashboard
ein (fork benötigt einen GitHub-Account):

1. **Fork** auf GitHub.
2. **Secrets** anlegen unter *Settings → Secrets and variables → Actions*:
   - `TELEGRAM_BOT_TOKEN` (von [@BotFather](https://t.me/BotFather))
   - `TELEGRAM_CHAT_ID` (deine User- oder Gruppen-ID)
3. **Actions aktivieren** (Tab „Actions" → Enable workflows).
4. **GitHub Pages aktivieren**: *Settings → Pages*, Source = „GitHub Actions".
5. Optional: **Schwellen anpassen** in `config/config.yaml` (z.B. wenn du
   eine andere Strecke oder ein konservativeres Profil willst).

Die erste Aktualisierung läuft zum nächsten Cron-Zeitpunkt (05/08/11/14/17/20 Uhr
Europe/Berlin) oder sofort per *Run workflow* im Actions-Tab.

## Disclaimer

Dieses Werkzeug ist eine **private Hilfe zur Tourenplanung** und keine amtliche
Auskunft. Die Landesregelungen, dein eigenes Urteil und die örtlichen
Verhältnisse haben immer Vorrang. Bei Unsicherheit: nicht losfahren.

## Mitmachen

Fehler gefunden? Vorschlag für eine weitere Hohenlohe-Strecke (weitere
Jagst-Abschnitte, Kocher?) Issues und Pull Requests sind willkommen.

## Technische Details

- **Python 3.12** orchestriert Fetcher → Ampel-Engine → Storage → Push.
- **GitHub Actions** laufen 6× pro Tag, fetchen HVZ + Open-Meteo, berechnen
  die Ampel, committen JSON-Daten ins Repo.
- **GitHub Pages** rendert ein statisches Dashboard (Vanilla JS + uPlot).
- Alle Schwellen in `config/config.yaml` parametrierbar.
- Backtest-Skript unter `backtest/run.py` für historische Validierung.
- Tests: `pytest` (44 Tests).

Vollständige Spec: [`docs/superpowers/specs/2026-04-18-kanu-hohenlohe-design.md`](docs/superpowers/specs/2026-04-18-kanu-hohenlohe-design.md).

---

MIT License · Made for paddlers in Hohenlohe 🛶
