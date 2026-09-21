# archetype_profile -- Analyse-Prototyp

Dieser Ordner ist der erste Baustein dafür, hochgeladene Commander-Decks gegen eine aus
1.585 EDHREC-Average-Decks gelernte Referenz (32 Farbidentitäten × Strategie-Tags) zu
bewerten. Er entstand aus der Trainingsdaten-Pipeline unter `Training data/auswertung_v1`
und ist bewusst als eigenständiges, von EDHREC/Scryfall zur Laufzeit unabhängiges Paket
gehalten -- alle benötigten Referenzwerte liegen bereits fertig berechnet unter `data/`.

Die volle Methodik (Kartenklassifikation, Tag-Normalisierung, Statistik, Farbbias-
Korrektur-Formel) ist ausführlich in `Training data/auswertung_v1/commander_report.md`
dokumentiert -- dieses README beschreibt nur die neue Schicht: die Anwendung auf ein
konkretes, hochgeladenes Deck.

## Status

**Seit v4.68.0 an `engine.py`/`gui.py` angeschlossen.** Das Paket ist jetzt ein
sauberes Unterpaket mit relativen Imports (`from . import classify` etc., siehe
`__init__.py`) und über `from App.archetype_profile import DeckAnalyzer` (mit
Standalone-Fallback, gleiches Muster wie `resource_planner`/`combat_model`)
aus `App/engine.py` importierbar. Integrationsschritte 1-4 aus "Nächste
Schritte" (Paketstruktur, Farbidentität aus dem Commander, GUI-Anbindung)
sind erledigt - siehe `App/engine.py::compare_deck_to_archetype_reference`/
`commander_identity_slug` und `App/gui.py::AnalysisPage._build_deck_comparison`
(Tab "Vergleich (1.585 Decks)" in der Auswertungsmaske). Schritt 2 (echter
Deck-Parser statt Hand-Dict) ist over-erfüllt: die Integration nutzt
`App.engine.Card`-Objekte direkt, inklusive Live-Klassifikation für Karten
außerhalb der 8.445-Karten-Referenz (siehe `compare_deck_to_archetype_
reference`s Docstring). Nur Schritt 5 (`CURATED_OVERRIDES` erweitern) bleibt
offen. Die Dateien sind weiterhin auch einzeln lauffähig (siehe
`deck_analyzer.py`s `__main__`-Block).

## Dateien

| Datei | Zweck |
|---|---|
| `mana_utils.py` | Manakosten-String -> Farbpip-Vektor (`parse_pips`), Hybrid-/Phyrexian-Mana anteilig gewichtet. |
| `classify.py` | Kartenklassifikation: Rolle (Interaction > Ramp > CardAdvantage > Strategy), Effekt-Tags, vereinfachter Effekttext. Regelbasiert (~35 Regex-Muster) + kuratierte Overrides für die wichtigsten Karten (Rhystic Study, Sol Ring, Cyclonic Rift, ...). |
| `tag_normalize.py` | 182 rohe EDHREC-Tags -> 115 kanonische Tags (`CANONICAL_TAG_MAP`, z. B. alle Kreaturtyp-Tags -> "Tribal"). |
| `stats_utils.py` | Gewichtete Statistik: `weighted_quantile`, `weighted_stats`, `weighted_histogram`. Gewicht ist immer die Stückzahl (`quantity`), nie reine Kartenanzahl. |
| `identity_colors.py` | Tabelle der 32 EDHREC-Farbidentitäten (Slug ↔ Farbkombination), plus `detect_identity_slug()`: schätzt die Farbidentität aus den aufsummierten Manapips einer Decklist. |
| `reference_model.py` | (= `model.py` aus `auswertung_v1`) `AverageDeckModel`: reine Referenz-Abfrage "wie sieht ein durchschnittliches Identität×Tag-Deck aus", ohne eigene Decklist. Farbbias-Korrektur-Formel: `Baseline(Identität) + [Tag-Profil − Referenzprofil]`. |
| `deck_analyzer.py` | **Neu.** `DeckAnalyzer`: nimmt eine konkrete hochgeladene Decklist, klassifiziert jede Karte, baut ein Deck-Profil und vergleicht es gegen `reference_model`. Das ist der eigentliche Analyse-Einstiegspunkt für die App. |
| `data/` | Exportierte Referenzdaten (siehe unten). Read-only zur Laufzeit. |

### `data/`

- `unique_cards_classified.csv` -- 8.445 bereits klassifizierte Karten (Typ, Manakosten,
  CMC, P/T, Rolle, Effekt-Tags, Oracle-Text). Dient `deck_analyzer.py` als primäre
  Nachschlagetabelle: die meisten hochgeladenen Karten sind hier bereits drin, dann ist
  keine Live-Klassifikation nötig.
- `identity_type_summary.json` -- Manavalue-/P-T-Verteilung je Farbidentität × Kartentyp.
- `identity_tag_summary.json` -- dieselbe Verteilung je (normalisiertem) Strategie-Tag,
  gepoolt über alle Farben, **nur Karten mit Rolle "Strategy"** (bewusster Ausschluss von
  Ramp/CardAdvantage/Interaction, siehe commander_report.md Abschnitt 1).
- `strategy_reference_profile.json` -- farbneutrale Referenz für die Residual-Formel.
- `deck_profiles.csv` -- die 1.585 realen Average-Deck-Profile selbst (Basis für Median-
  Baseline je Identität/Tag in `reference_model.py`).

## Verwendung

```python
from deck_analyzer import DeckAnalyzer

analyzer = DeckAnalyzer.load()  # laedt data/ einmalig (~1-2 Sekunden)

decklist = [
    {"name": "Sol Ring", "quantity": 1},
    {"name": "Rhystic Study", "quantity": 1},
    {"name": "Cyclonic Rift", "quantity": 1},
    {"name": "Forest", "quantity": 20},
    # ... restliche 96 Karten
]

result = analyzer.analyze(
    decklist,
    identity_slug="simic",     # optional; ohne Angabe wird aus den Manapips geschaetzt
    tags=["Landfall"],         # optional; leer = nur Farbidentitaets-Baseline, kein Tag-Overlay
)

print(result.report_text)          # fertiger deutscher Textbericht
result.comparison                  # Liste von {field, label, observed, expected, diff, diff_pct}
result.deck_profile                # volles Profil (Rollen-Zaehlwerte, Manakurve, P/T-Stats)
result.unclassified_cards          # Karten, die weder in der Referenz-DB noch klassifizierbar waren
```

Für Karten, die **nicht** in `unique_cards_classified.csv` vorkommen (neue Sets, sehr
seltene Karten), kann pro Deckliste-Eintrag optional `mana_cost`, `type`, `oracle_text`,
`power`, `toughness` mitgegeben werden -- dann klassifiziert `classify.py` live nach
denselben Regeln wie beim Aufbau der Trainingsdaten. Ohne diese Zusatzdaten landet die
Karte in `result.unclassified_cards` und fließt mit `type=None`/`role=None` nicht in die
Zähl-Statistik ein (wird aber in der Kartenanzahl-Summe transparent ausgewiesen).

## Bekannte Einschränkungen (v1, ehrlich dokumentiert)

- **Farbidentitäts-Erkennung ist eine Näherung.** `detect_identity_slug()` schätzt die
  Identität aus den Manakosten der eingereichten Karten, nicht aus der formalen "Color
  Identity" (die auch Regeltext-Symbole und den Commander selbst einschließt). Wo die App
  die Farbidentität des Commanders bereits kennt, sollte `identity_slug` **explizit**
  übergeben werden statt sich auf die Schätzung zu verlassen.
- **~47 % der "Strategy"-Karten** in der Referenzdatenbank haben nur einen generischen
  Fallback-Effekt-Tag statt eines spezifischen (siehe commander_report.md Abschnitt 5).
  Das beeinflusst nur die Tag-Feinheit, nicht die grundlegenden Rollen-Zählwerte
  (Land/Ramp/CardAdvantage/Interaction/Creature bleiben unabhängig davon korrekt gezählt).
- **278 Karten (3,3 %)** in der Referenzdatenbank fehlt Manavalue/P-T durch einen
  URL-Encoding-Bug im ursprünglichen Export-Skript (betrifft vor allem Transform-/MDFC-
  Karten) -- wird bei Nachschlagen als "kein Wert" (None) behandelt, nicht als 0.
- Diese Version rechnet nur mit den **beim letzten Pipeline-Lauf exportierten** Referenz-
  daten (Stand siehe `commander_report.md`). Ein neuer EDHREC-Import + erneuter Lauf von
  `step1`-`step6` in `auswertung_v1/code` aktualisiert `data/` hier nicht automatisch --
  das Kopieren der neuen Exporte in dieses `data/`-Verzeichnis ist ein manueller Schritt.

## Nächste Schritte (Integration in Commander Goldfish)

1. ~~**Paketstruktur angleichen**~~ **erledigt (v4.68.0)**: relative Imports
   (`from . import classify` etc.), `from App.archetype_profile import DeckAnalyzer`
   funktioniert aus `engine.py`/`gui.py` (Standalone-Fallback wie bei `resource_planner`).
2. ~~**Deck-Parser anschließen**~~ **erledigt (v4.68.0), über Plan hinaus**: die
   Integration nutzt direkt `App.engine.Card`-Objekte (`engine.py::
   compare_deck_to_archetype_reference`) statt eines Zwischenformats -- inklusive
   Live-Klassifikation für Karten außerhalb der 8.445-Karten-Referenz über die schon
   an Bord befindlichen `mana_cost`/`type_line`/`oracle_text`/`power`/`toughness`-Felder.
3. ~~**Farbidentität aus dem Commander übernehmen**~~ **erledigt (v4.68.0)**:
   `engine.py::commander_identity_slug()` nimmt die reale Farbidentität der gewählten
   Commander (Vereinigung bei Partner-Commandern), nicht mehr `detect_identity_slug()`s
   Pip-Schätzung.
4. ~~**GUI-Anbindung**~~ **erledigt (v4.68.0)**: neuer Tab "Vergleich (1.585 Decks)" in
   der Auswertungsmaske (`App/gui.py::AnalysisPage._build_deck_comparison`) -- Vergleich
   gegen die Farbidentitäts-Referenz sowie, falls in der App ausgewählt und in der
   Referenz erkannt, zusätzlich gegen die Farbidentität+Strategie-Referenz.
5. **`CURATED_OVERRIDES` in `classify.py` erweitern** (aktuell ~10 Karten nach dem
   Pareto-Prinzip) -- lohnt sich hier doppelt, weil jede zusätzliche kuratierte Karte
   sowohl die Referenzdaten als auch jede zukünftige Live-Klassifikation hochgeladener
   Decks genauer macht. **Einzig noch offener Schritt.**
