# Urza's Spearfishing Guide

Lokales Tool zum Testen von Commander-Decklisten: echte Goldfish-Simulationen
gegen `app/App/engine.py`, dazu eine Web-Oberflaeche mit Scryfall-Kartenbildern,
Combo-Builder und einer 1.585-Deck-EDHREC-Referenz.

## Starten

**Windows:** Doppelklick auf `Start_Urzas_Spearfishing_Guide.bat`.

**Alle Plattformen:**
```
python Start_Urzas_Spearfishing_Guide.py
```

Das Skript prueft beim Start automatisch, ob alle noetigen Python-Pakete
(`flask`, `numpy`, `pandas`, `pillow`, `requests`) installiert sind. Fehlt
eines, wird `install_dependencies.py` automatisch aufgerufen und installiert
alles aus `requirements.txt` mit dem gerade laufenden Python. Das kann auch
manuell vorab ausgefuehrt werden:
```
python install_dependencies.py
```

Danach oeffnet sich automatisch ein Browserfenster unter
`http://127.0.0.1:8765/`. Zum Beenden das Konsolenfenster schliessen bzw.
Strg+C. Mit `--port 9000` laesst sich ein anderer Port waehlen, mit
`--no-browser` das automatische Oeffnen unterdruecken -- beide Optionen
direkt an `Start_Urzas_Spearfishing_Guide.py` bzw. die `.bat` anhaengen.

Voraussetzung: **Python 3.10 oder neuer**. Fuer die Scryfall-Kartenbilder
wird eine normale Internetverbindung gebraucht (die Bilder werden direkt vom
Browser bei Scryfall geladen, es verlaesst sonst nichts diesen Rechner).

## Ordnerstruktur

```
Urzas_Spearfishing_Guide/
├── Start_Urzas_Spearfishing_Guide.py   <- einziger Startpunkt
├── Start_Urzas_Spearfishing_Guide.bat  <- Windows-Doppelklick-Variante
├── install_dependencies.py             <- Installer fuer fehlende Pakete
├── requirements.txt
├── README.md
└── app/                                 <- alle uebrigen Ressourcen
    ├── App/              Engine (engine.py, archetype_profile, combat_model, ...)
    ├── Data/              Referenzmodelle/Gewichte
    ├── Decks/             Beispiel- und Fremd-Decklisten (.txt)
    ├── Docs/              Entwicklungs-Dokumentation
    ├── Goldfish_Results/  Ergebnisse eigener Laeufe (wird beim Laufen befuellt)
    ├── tests/             automatisierte Tests der Engine
    ├── webui/             die Web-Oberflaeche selbst
    ├── dev_tools/          Entwickler-Skripte (nicht fuer den normalen Betrieb noetig)
    ├── web_server.py      Flask-Server, ruft die Engine live auf
    ├── webui_transform.py Engine-Ergebnis -> UI-JSON
    └── commander_goldfish.py  alte Desktop-Oberflaeche (Tkinter, optional)
```

## Was aktuell wirklich live laeuft -- und was noch nicht

Das hier ist bewusst ehrlich dokumentiert, damit klar ist, was jemand, der
sich dieses Paket herunterlaedt, tatsaechlich bekommt:

- **Simulation & Analyse fuer "Bilbo V1"**: vollstaendig live. "Start
  goldfishing" / "Run again" rechnet einen echten, neuen Batch gegen die
  Engine, mit echtem Fortschrittsbalken und live neu berechneter
  EDHREC-Referenz.
- **Combo-Builder → Simulation**: gespeicherte Combos werden beim naechsten
  Lauf als Win-Condition-Szenarien an die Engine uebergeben.
- **Kartenbilder**: echte Scryfall-Bilder, laden automatisch bei
  vorhandener Internetverbindung.
- **Andere mitgelieferte Decks** (Katara, Aziza, Mice with Swords) und die
  Decks in `app/Decks/Fremd/`: liegen bereits als Decklisten vor und die
  Server-API (`POST /api/simulate`) nimmt bereits `deck_file` /
  `commander_names` entgegen -- die Oberflaeche selbst bietet aber noch
  **keinen Deck-Wechsel oder Datei-Upload an**. Das ist der naechste
  logische Ausbauschritt, um wirklich beliebige, selbst hochgeladene Decks
  testen zu koennen, und noch nicht Teil dieses Pakets.

## Alte Desktop-Oberflaeche

`app/commander_goldfish.py` startet weiterhin die urspruengliche
Tkinter-Anwendung, falls die Web-Oberflaeche aus irgendeinem Grund nicht
nutzbar sein sollte:
```
python app/commander_goldfish.py
```
