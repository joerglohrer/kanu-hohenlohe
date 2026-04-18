# Release checklist — kanu-hohenlohe

Dieses Dokument listet die manuellen Schritte, die nötig sind, um das Repo
öffentlich auf GitHub zu stellen, die Actions zu aktivieren, die Telegram-
Secrets einzutragen und den ersten Live-Lauf auszulösen.

## 0. Voraussetzungen

- `gh` CLI installiert und eingeloggt (`gh auth status`)
- Einen Telegram-Bot anlegen via [@BotFather](https://t.me/BotFather) und Token
  sowie die Chat-ID notieren (letztere durch einmaliges `/start` im privaten
  Chat und Aufruf `https://api.telegram.org/bot<TOKEN>/getUpdates`)

## 1. Repo auf GitHub erzeugen und pushen

```bash
cd /Users/joerglohrer/repositories/kanu
gh repo create kanu-hohenlohe --public --source . --push --description "Jagst canoe traffic-light: Pegel + Wetter → Ampel + Telegram-Push"
```

## 2. Secrets setzen

```bash
gh secret set TELEGRAM_BOT_TOKEN   # prompt, then paste token
gh secret set TELEGRAM_CHAT_ID     # prompt, then paste chat id
```

## 3. Pages aktivieren

```bash
gh api -X POST "repos/:owner/kanu-hohenlohe/pages" -f source[branch]=main -f source[path]=/ || true
# or: in der GitHub-UI Settings → Pages → Source = „GitHub Actions"
```

## 4. Update-Workflow einmal manuell triggern

```bash
gh workflow run update.yml
gh run watch    # beobachte den Lauf
```

Wenn erfolgreich, pullt man die neu committeten Daten:

```bash
git pull
```

## 5. Pages-Workflow läuft von selbst

Durch den Push in Schritt 4 wird `data/status.json` aktualisiert und pages.yml
dadurch automatisch ausgelöst. URL aus der Actions-UI oder:

```bash
gh api "repos/:owner/kanu-hohenlohe/pages" --jq .html_url
```

## 6. Dashboard-URL im Frontend eintragen

`src/notify/telegram.py` enthält `https://<user>.github.io/kanu-hohenlohe/` als
Platzhalter. Nach Pages-Deploy den echten Username einsetzen. Auch in
`README.md`.

## 7. Laufende Pflege

- Bei HVZ-Format-Änderungen: `src/fetcher/hvz.py` anpassen (Tests mit Fixture schützen)
- Bei Schwellenwert-Kalibrierung: `config/config.yaml`
- Bei Einzugsgebiets-Verfeinerung: `config/catchment.geojson`

## Bekannte offene Punkte

- **Catchment-Polygon** ist aus Bounding-Box generiert; bei Bedarf aus LUBW-EZG-
  Daten verfeinern.
- **HVZ-Historie**: die aktuelle HVZ-Scraper liest nur den jüngsten Messwert
  pro Gauge (keine historische Zeitreihe aus einer einzigen Antwort). Der
  Zeitreihen-Aufbau geschieht durch die akkumulierten Cron-Läufe. Backtest
  auf 5 Jahre erfordert eine eigene Daten-Beschaffung (HVZ-Archiv per Hand
  herunterladen oder GIF-basierte Daten digitalisieren).
- **Frontend-Regen-Streifen** zeigt derzeit Vorschau-Daten. Integration mit dem
  Wetter-Archiv ist ein nice-to-have.
