# Urza's Spearfishing Guide — Web-Oberfläche (live an die Engine angebunden)

Diese Oberfläche läuft lokal auf diesem Rechner und ruft für jede Simulation
wirklich `App/engine.py` auf — es ist keine Wiedergabe eines aufgezeichneten
Laufs mehr, sondern ein echter, neuer Goldfish-Batch, inklusive echtem
Fortschrittsbalken (der Fisch verlässt die Dose exakt im Takt der
tatsächlich abgeschlossenen Partien) und einer live neu berechneten
1.585-Deck-Referenz (`App/archetype_profile`).

## Einmalig einrichten

Flask ist die einzige neue Abhängigkeit gegenüber der bestehenden Desktop-App:

```
pip install flask
```

(numpy/pandas/Pillow etc. werden bereits von der Tkinter-App vorausgesetzt
und sind damit vermutlich schon vorhanden.)

## Starten

Doppelklick auf `Start_Goldfish_Web.bat` (oder `python web_server.py` in
diesem Ordner). Es öffnet sich automatisch ein Browser-Fenster unter
`http://127.0.0.1:8765/`. Zum Beenden das Konsolenfenster schließen bzw.
Strg+C.

## Was ist bereits live, was noch nicht

- **Simulation (Seite „Simulation")**: „Start goldfishing" / „Run again"
  startet einen echten Lauf mit den eingestellten Parametern (Spiele, Züge,
  Seed, Gegnertyp, Strategie-Tags aus dem Profil). Der Fortschrittsbalken
  zeigt den tatsächlichen Spielstand aus der Engine.
- **Analyse-Seite**: alle Zahlen (Win/Loss-Quote, Lebenspunkte-Verteilung,
  Manakurve, Win-Condition-Erreichbarkeit, Karten-Highlights,
  Kampf-Diagnostik, **und der neue „Reference: 1,585 EDHREC decks"-
  Abschnitt**) werden nach jedem Lauf aus dem echten Ergebnis neu gebaut.
- **Combo-Builder → Simulation**: aktuell gespeicherte Combos werden beim
  nächsten Lauf als Win-Condition-Szenarien an die Engine übergeben (über
  dasselbe JSON-Format wie `Data/Scenarios/*.json`). Ohne gespeicherte
  Combos fällt der Server auf die mitgelieferten drei Bilbo-Szenarien
  (`Decks/bilbo_win_conditions_40_each_v4_3.json`) zurück.
- **Kartenbilder**: laufen über diese lokale Seite ohne die
  Sicherheitsbeschränkung, die die veröffentlichte Vorschau (Artifact)
  betrifft — echte Scryfall-Bilder laden hier automatisch, sofern der
  Rechner Internetzugang hat.
- **Deck-Auswahl**: bislang fest auf Bilbo V1 (samt Commander und den drei
  Szenarien) verdrahtet — die anderen hinterlegten Decks (Katara, Aziza,
  Mice with Swords) zeigen weiterhin nur ihren letzten aufgezeichneten
  Lauf. Das Umschalten auf eine andere Datei live mitzuschalten ist der
  naheliegende nächste Schritt; die API (`POST /api/simulate`) nimmt dafür
  bereits `deck_file`/`commander_names` entgegen, nur die Oberfläche bietet
  noch keinen Deck-Wechsel an.
- **Profil-Speicherung**: weiterhin nur im Browser (localStorage) des
  jeweiligen Rechners, noch nicht in einer Projektdatei.

## Dateien

- `web_server.py` — Flask-Server, ruft `App/engine.run_pipeline_v440` und
  `App/engine.compare_deck_to_archetype_reference` direkt auf.
- `webui_transform.py` — wandelt das rohe Engine-Summary in das JSON-Format
  um, das die Oberfläche erwartet (dieselbe Funktion baut auch die
  eingebettete Vorschau in der veröffentlichten Web-Vorschau/Artifact).
- `webui/index.html` — die Oberfläche selbst (identisch mit der separat
  gelieferten Vorschau-Datei, nur ohne die zusätzliche „Live"-Prüfung
  auszukommentieren — die ist bereits eingebaut und schaltet sich
  automatisch frei, sobald dieser Server erreichbar ist).
