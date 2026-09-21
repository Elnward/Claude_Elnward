# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.71.0

Begleitdokument zu `Docs/README.md` (v4.71.0-Eintrag),
`Data/Models/opponent_state_weights.json` (version "1.9",
`permanent_type_value_usd`, `card_value_weighting`, korrigierte
"Engine-Integration"-Notiz) und `App/opponent_model/state_equation.py`s
Moduldoc-Abschnitt "v4.71.0". Baut auf
`Docs/opponent_model_calibration_v4_70_0.md` auf.

## Ausgangsfrage des Nutzers (drei Teile, wörtlich zusammengefasst)

1. "Kannst du bitte die [seit v4.43.0] offene Lücke schließen und die
   Engine-Integration diesbezüglich nutzbar machen?"
2. "Die Funktion der Wertigkeit nicht linear halten, sondern logarithmisch:
   kleine Änderungen im Preis machen schon einiges aus, aber der
   Unterschied zwischen der Wertigkeit bei einer 30-Euro-Karte und einer
   500-Euro-Karte sollte kaum merkbar sein. Keine Karte soll jemals nie
   interagierend sein [...] ein Wert von 0 [...] sollte eine Karte nicht
   [...] immun machen."
3. "Gehe bitte durch unsere bisherigen Schritte einmal durch, um zu
   gucken, ob alles jetzt implementiert ist und läuft. [...] Wenn noch
   offene Fragen [...] sind, [...] sage das bitte."

## Teil 1: Engine-Integrations-Audit — Ergebnis: bereits fertig, nur die Doku war veraltet

Die Formulierung "Verbleibend offen: [...] die eigentliche
Engine-Integration (App/engine.py-Zugschleife)" stammt wörtlich aus
v4.43.0s Abschnitt des `note`-Felds in `opponent_state_weights.json`. Das
`note`-Feld wird bei jeder Version vorangestellt (neuester Eintrag zuerst),
der alte v4.43.0-Text bleibt dabei am Ende unverändert erhalten — genau
dieser alte Satz wurde nie aktualisiert, obwohl die Engine-Integration
längst gebaut wurde:

- **v4.63.0** ("ECHTE Turnschleifen-Integration"): `App/engine.py` erhielt
  ein vollständiges, opt-in `advanced_opponent_model`/
  `advanced_opponent_seats`-System — jeder Sitzplatz am Tisch bekommt sein
  eigenes `OpponentProfile`/`OpponentState`-Paar, `advance_opponent_state`
  wird während der echten Simulation pro Gegner-Zug aufgerufen
  (`_apply_advanced_opponent_phase`), inkl. Mehrspieler-Zielverteilung
  (`_advanced_opponent_targeting_dilution`).
- **v4.64.0**: `"?"`-Zufalls-Marker für Strategie/Farbe je Sitzplatz,
  deterministisch pro Run aufgelöst (`_resolve_advanced_opponent_seats_for_run`).
- **v4.65.1**: Bugfix, damit die tatsächlich verwendeten (aufgelösten)
  Sitzplätze korrekt im Ergebnis-JSON stehen, nicht nur die rohe Anfrage.
- **v4.66.0**: optionaler `flavor`-Schlüssel je Sitzplatz (feingranularere
  Farbe×Strategie-Zellen).
- **GUI**: `App/gui.py` hat einen eigenen "Erweitert"-Dialog
  (Sitzplatz-Anzahl, je Sitzplatz Farbe/Strategie/Flavor), einen
  Status-Indikator ("Erweitert: an/aus") und einen eigenen
  Ergebnis-Tab/-Abschnitt ("Opponent"), der die tatsächlich simulierten
  Sitzplätze zusammenfasst.
- **Tests**: `tests/test_advanced_opponent_model.py` (34 Tests) deckt
  Validierung, Tabellen-Konstruktion, Zielverteilung, UND einen echten
  End-to-End-Lauf durch `simulate_game_v440` ab
  (`test_end_to_end_through_apply_abstract_opponent_phase_via_simulate_game_v440`).

**Das ist also kein Prototyp und keine Baustelle — es läuft, ist getestet
und in der GUI bedienbar.** Der Satz wurde in
`Data/Models/opponent_state_weights.json`s `note`-Feld direkt an der
Fundstelle korrigiert (nicht gelöscht, um die Versionshistorie nicht zu
verfälschen — mit einem `[KORRIGIERT v4.71.0: ...]`-Zusatz).

### Tatsächlich noch bestehende, ABSICHTLICH gesetzte Grenzen dieser ersten Integrationsstufe

Diese sind keine Bugs, sondern per `_validate_advanced_opponent_seats` HART
durchgesetzte, in v4.63.0 vom Nutzer selbst so gewünschte Scope-Grenzen:

- Nur **ein- oder zweifarbige** Gegner-Identitäten pro Sitzplatz (3-5
  Farben werden mit einem klaren `ValueError` abgelehnt, nicht still
  toleriert).
- Nur **Bracket 3** pro Sitzplatz (andere Brackets werden ebenfalls
  abgelehnt) — der einzige Bracket, für den `opponent_state_weights.json`
  auf ausreichend breiten, echten Decklisten kalibriert wurde.

Eine Erweiterung auf mehr Farben/Brackets würde zunächst eine breitere,
bracket-verifizierte Kalibrierungsstichprobe für diese Fälle brauchen (siehe
Teil 3 unten) — das ist ein echter, aber bewusst vertagter nächster Schritt,
kein vergessener.

## Teil 2: Die "Wertigkeits-Funktion" (log-skaliert, floor-begrenzt)

### Neue Datenbasis: `permanent_type_value_usd`

Anders als v4.70.0s Preissignal (Preis der ANTWORTENDEN Removal-Karte) misst
dieser neue Wert den Preis des **Permanents selbst** — "wie wertig ist das
zu interagierende Medium". Berechnet aus allen 1.585 echten Decks
(`deck_cards_slim.csv`): für jede Karte, deren EDHREC-Kartentyp
(`unique_cards_classified.csv`s `type`-Feld: Creature/Artifact/
Enchantment/Planeswalker/Land) in einen der 5 Buckets fällt, wird ihr
Preis (dieselbe Preis-Fallback-Kette wie v4.70.0) log1p-transformiert und
nach tatsächlicher Spielhäufigkeit (Summe der `quantity` über alle Decks)
gewichtet gemittelt:

| Typ          | Ø Preis (USD, log-gewichtet) |
|--------------|------------------------------:|
| creature     | 2.60                           |
| artifact     | 2.64                           |
| enchantment  | 3.96                           |
| planeswalker | 5.12                           |
| land         | 1.46                           |

Verzauberungen und Planeswalker sind im gewichteten Mittel deutlich
teurer — beide Typen werden in Commander-Decks tendenziell knapper und
gezielter gewählt (Rhystic-Study-/Walker-Klasse statt Füllkreaturen/
generischer Manarocks). Land ist am billigsten, dominiert von Basic Lands.

Bewusst **keine** Aufschlüsselung nach Bracket: die vollen 1.585 Decks
haben keine verifizierten Bracket-Label (nur die kleine, gezielte
30-Decks-Stichprobe aus v4.39.0-v4.42.0 wurde echt eingeordnet) — eine
Bracket-Aufschlüsselung über den vollen Datensatz wäre erfundene Präzision
gewesen.

### Die Kurve selbst

`state_equation.py::_card_value_weight(price)`:

```
weight(p) = floor + (1 - floor) * log1p(p) / (log1p(p) + k)
```

mit `k = 0.25`, `floor = 0.3` (`card_value_weighting` in
`opponent_state_weights.json`). Kalibriert direkt gegen die Nutzer-Vorgabe:

| Preis | weight(p) |
|------:|----------:|
| 0 USD | 0.300 (= floor, NIE exakt 0) |
| 0.5 USD | 0.618 |
| 1 USD | 0.735 |
| 2 USD | 0.815 |
| 5 USD | 0.878 |
| 10 USD | 0.906 |
| **30 USD** | **0.932** |
| **500 USD** | **0.961** |

Differenz 30 vs. 500 USD: nur 0.029 (nach dem Floor-Faktor ~0.02 in der
finalen Wertigkeit) — "kaum merkbar", wie gefordert. Differenz 0 vs. 5 USD:
0.58 — deutlich spürbar, wie ebenfalls gefordert. Beide Vorgaben
gleichzeitig zu erfüllen bedeutet zwangsläufig, dass die reale
Differenzierungszone hauptsächlich im Bereich $0-$10 liegt (wo unsere
tatsächlich gemessenen `permanent_type_value_usd`-Werte auch liegen) —
das ist eine offen ausgewiesene, disclosed Konsequenz der Vorgabe, kein
Zufall.

`_bucket_value_multiplier(bucket)` bildet `weight(preis)` auf einen
Halbwertszeit-Multiplikator zwischen `min_multiplier=0.65` (teuerster
Bucket → kürzeste Halbwertszeit) und `max_multiplier=1.25` (billigster
Bucket → längste, aber ausdrücklich BEGRENZTE Halbwertszeit) ab:

| Typ          | Multiplikator |
|--------------|---------------:|
| planeswalker | 0.701 (teuerster Bucket → am stärksten verkürzt) |
| enchantment  | 0.707 |
| creature     | 0.719 |
| artifact     | 0.718 |
| land         | 0.741 (billigster Bucket → am wenigsten verkürzt) |

### Die Immunitäts-Garantie: zweifach durchgesetzt

Der Nutzer war explizit: "Keine Karte soll jemals nie interagierend sein
[...] ein Wert von 0 sollte eine Karte nicht [...] immun machen." Das wird
hier NICHT nur durch sorgfältige Kurvenwahl erreicht, sondern strukturell
erzwungen:

1. **Der `floor`** verhindert, dass `_card_value_weight` je exakt 0
   zurückgibt — selbst ein hypothetischer $0-Preis ergibt noch
   `weight=0.3`.
2. **`_effective_half_life`** (neue, zentrale Kombinationsfunktion) wendet
   `guardrails.half_life_ceiling_turns` (seit v4.70.0: 30 Züge) ein
   ZWEITES Mal auf das FINALE, bereits mit `impact_half_life_multiplier`
   UND dem neuen Wertigkeits-Multiplikator kombinierte Ergebnis an — nicht
   mehr nur auf den rohen `permanent_type_half_life_turns`-Tabellenwert wie
   in v4.70.0. Das ist absichtlich redundant zu Punkt 1: selbst wenn eine
   künftige Kalibrierung `max_multiplier` versehentlich sehr groß setzt,
   kann die kombinierte Halbwertszeit strukturell nicht über die
   Tool-eigene maximale Simulationslänge hinauswachsen. Ein dedizierter
   Test (`test_never_exceeds_the_ceiling_even_with_an_inflated_multiplier`
   in `tests/test_v4710_value_weighting.py`) simuliert genau diesen
   Fehlerfall (Preis=0 UND `max_multiplier` künstlich auf 10 gesetzt) und
   bestätigt, dass die Deckelung trotzdem greift.

`bracket_scaling.*.impact_half_life_multiplier` selbst bleibt unverändert
(weiterhin disclosed als "reasoniert, nicht gemessen" — es gibt weiterhin
keine verifizierten Bracket-Label für den vollen 1.585-Deck-Datensatz) und
wird MIT dem neuen Faktor kombiniert, nicht durch ihn ersetzt: Bracket
misst "wie stark ist das GANZE Deck", der neue Faktor misst "wie wertig ist
ein TYPISCHES Permanent dieses Typs" — zwei echte, unterschiedliche
Dimensionen.

## Teil 3: Vollständiger Lücken-Statusbericht (alle bisherigen Versionen)

| Lücke (seit) | Status | Nächster Schritt |
|---|---|---|
| Engine-Integration (Zugschleife) | **War bereits geschlossen** (v4.63.0), nur die Notiz war veraltet — jetzt korrigiert | keiner |
| 4-/5-farbige & farblose Identitäten (7 von 32) — echte Decklisten-Kalibrierung | weiterhin offen | 7 weitere echte Decklisten verifizieren (wie v4.39.0-v4.42.0), dann `color_modifiers` prüfen |
| Gilden-Synergie-Lücke (Orzhov/Izzet — spezifische Zweifarb-Chemie über das multiplikative Modell hinaus) | weiterhin offen | erfordert ein additives statt rein multiplikatives Farbmodell, oder gezielte Gilden-Stichproben |
| `advanced_opponent_seats`: nur 1-2 Farben, nur Bracket 3 | weiterhin bewusst begrenzt (siehe Teil 1) | breitere, bracket-verifizierte Stichprobe für 3+ Farben/andere Brackets, dann `_validate_advanced_opponent_seats` erweitern |
| `impact_half_life_multiplier` (Bracket-Ebene) | weiterhin reasoniert, nicht gemessen | bräuchte turn-genaue Spielprotokolle oder verifizierte Brackets für den vollen Datensatz |
| Echte Zug-für-Zug-Validierung der Halbwertszeiten (v4.70.0/v4.71.0) | weiterhin offen, dauerhaft ohne neue Datenquelle nicht schließbar | turn-genau geloggte reale Spielverläufe nötig (liegen nicht vor) |
| `removal_target_types`: abstimmungsbasierte Effekte (Council's Judgment) | weiterhin offen, klein | zusätzliches Regex-Muster für "choose a permanent"-Abstimmungstext |
| aggro/horde `wipe_growth` behaviorally inert (`wipe_min_turn=999`) | weiterhin offen | Turn-Timing-Beleg für frühere Board-Wipe-Verfügbarkeit bei Aggro/Horde nötig |
| 278 Karten (3.3%) ohne Manavalue/Typ wegen fehlender URL-Kodierung im Named-Fallback von `export_card_training_data.py` | **JETZT behoben** (`urllib.parse.quote()` ergänzt) — wirkt erst nach dem nächsten lokalen Skript-Lauf | Nutzer müsste das Skript einmal erneut lokal ausführen, dann `unique_cards_enriched.csv`/`deck_cards_slim.csv` neu übertragen |
| `CURATED_OVERRIDES` nur 11 Karten (Pareto-Ziel: 300-500) | weiterhin offen, unverändert seit 2026-09-16 | schrittweise Erweiterung nach Kartenhäufigkeit (`tag_catalog.csv`/Kartenkopien-Ranking) |
| "Strategy"-Rolle-Karten ohne spezifisches Muster (generischer Fallback) | **neu gemessen**: 19.6% der Strategy-Karten / 5.1% aller Kartenkopien (frühere Notiz sprach von ~47%/5.4% — die 5.1% des Gesamtdatensatzes sind praktisch unverändert, die 47%→19.6% deutet auf zwischenzeitliche Verbesserung der Regel-Engine hin, nicht neu verifizierbar ohne Versionsvergleich) | dieselbe `CURATED_OVERRIDES`-Erweiterung wie oben würde auch hier helfen |

**Kurzfassung**: von allen bisher offen ausgewiesenen Punkten war nur
einer (die Engine-Integration) tatsächlich fälschlich als offen markiert.
Alle anderen sind echte, weiterhin bestehende Lücken — die meisten
erfordern entweder mehr echte Decklisten-Verifikation (zeitaufwändig, aber
mit der etablierten Methodik machbar) oder Spieldaten, die schlicht nicht
existieren (turn-genaue Logs). Die URL-Encoding-Karten-Lücke wurde bei
diesem Audit zusätzlich gefunden und behoben.

## Nachtrag: Nutzer-Rückmeldung zum Gesamtkonzept (nach v4.71.0)

Der Nutzer hat im Anschluss das Gesamtkonzept der Zug-für-Zug-Simulation
und des Gegner-Zustandsmodells noch einmal zusammenfassend bestätigt und
dabei zwei Punkte aus der obigen Tabelle geklärt:

- **Gilden-Synergie-Lücke (Zeile 3 oben): explizit KEINE externe
  Gewichtung gewünscht.** Der Nutzer möchte ausdrücklich keine manuell
  ergänzten gildenspezifischen Synergien (z. B. eine feste
  Orzhov-/Izzet-Sonderregel). Gilden-Effekte sollen sich, wenn überhaupt,
  rein aus der bestehenden Datengrundlage (den 1.585 echten Decks) über
  das bestehende, rein multiplikative Farbmodell ergeben — falls sich
  dabei zufällig Gilden-Muster zeigen, ist das willkommen, aber kein
  Entwicklungsziel für sich. **Status geändert:** von "weiterhin offen,
  benötigt Entscheidung" zu **"kein Fix nötig — bewusst so gewollt, nicht
  fehlend"**, analog zur bereits geklärten Engine-Integration-Zeile.
- **`CURATED_OVERRIDES`-Erweiterung: Präzisierung der Methodik.** Die
  geplante Erweiterung über die aktuell 11 Karten hinaus soll ausschließlich
  aus der vollen, bereits vorhandenen Datengrundlage abgeleitet werden
  (z. B. Kartenhäufigkeits-Ranking aus `tag_catalog.csv`/Stückzahl über
  alle 1.585 Decks), nicht durch händisch von außen ausgewählte
  Einzelkarten. Der Punkt selbst bleibt offen (weiterhin nur 11/300-500
  Karten), aber die Methodik für die künftige Umsetzung ist damit
  präzisiert.
- Zur Rückfrage, ob die neue preisabhängige Halbwertszeit (Teil 2 oben,
  `_card_value_weight`/`_effective_half_life`) bestehen bleiben soll: der
  Nutzer hat bestätigt, dass sie bestehen bleibt — die hier beschriebene
  Funktion war eine spätere, explizite Weiterentwicklung des ursprünglich
  offen gelassenen Punkts, keine versehentliche Abweichung vom
  Gesamtkonzept.

Keine Code-Änderung durch diesen Nachtrag nötig (reine Status-/
Methodik-Klärung) — daher kein Versionssprung auf v4.72.0.
