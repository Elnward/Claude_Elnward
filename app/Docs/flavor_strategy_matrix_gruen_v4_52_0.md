# Flavor-Strategie-Matrix — Grün, Portion 5 von 15 (v4.52.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Fünfte Portion der Nutzer-Dokument-Auswertung, direkt im Anschluss an
Rot (v4.51.0), gleicher Sitzungsdurchgang, wie vom Nutzer gewünscht.
Grün ist die letzte Monofarbe und erfordert zusätzlich einen
**Taxonomie-Abgleich**: der Grün-Pilot (v4.47.0) verwendete noch 5
selbst gewählte Flavors, das neue Nutzerdokument
(`Commander_Monofarben_Bracket_3.md`) benennt 6 Flavors für Grün.

## Taxonomie-Abgleich (Pilot 5 Flavors vs. Dokument 6 Flavors)

| Pilot v4.47.0 (5 Flavors) | Dokument (6 Flavors) | Entscheidung |
|---|---|---|
| Landfall (Ashaya) | Lands/Landfall | **Deckungsgleich — Pilot-Daten unverändert übernommen** |
| Elfen/Go-Wide (Marwyn) | Elfball | **Deckungsgleich — Pilot-Daten unverändert übernommen** |
| Stompy (Ghalta) | Stompy/Power Matters | **Deckungsgleich — Pilot-Daten unverändert übernommen** |
| +1/+1-Zähler (Vorinclex) | +1/+1-Counter/Go-Tall | **Deckungsgleich — Pilot-Daten unverändert übernommen** |
| Ramp/Big-Mana (Azusa) | *(kein direktes Gegenstück)* | **Aus der aktiven 6-Flavor-Taxonomie entfernt** — bleibt als eigenständiger, weiterhin gültiger Beleg in `Docs/green_flavor_strategy_matrix_pilot_v4_47_0.md` erhalten, wird aber NICHT in diese Portion übernommen, um der Dokument-Struktur zu folgen |
| *(kein Gegenstück)* | Tokens/Go-Wide (Ruxa, Patient Professor) | **NEU recherchiert** — reale Daten widerlegen das Label (s. u.), reklassifiziert zu "Vanilla-Kreaturen/Anthems" |
| *(kein Gegenstück)* | Creature Toolbox/Flash (Yeva, Nature's Herald) | **NEU recherchiert** — Label real bestätigt (EDHREC-Tags: Ramp/Flash/Combo/Midrange) |

**Begründung:** die 4 deckungsgleichen Flavors wurden bereits im Piloten
mit vollständig echten EDHREC-Daten belegt (siehe deren Zellen unten,
Werte identisch zu v4.47.0 übernommen) — eine erneute Abfrage derselben
Decklisten hätte keinen neuen Erkenntniswert. Nur die 2 tatsächlich
neuen Flavors (Ruxa, Yeva) wurden frisch recherchiert. Rohdaten der 2
neuen Decks: `Docs/scratch/green_flavor_pilot_raw_v4_52_0_addendum.md`;
Rohdaten der 4 wiederverwendeten Decks weiterhin:
`Docs/scratch/green_flavor_pilot_raw.md` (v4.47.0).

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Entfernung | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Landfall (Ashaya) | 54% | ~2% | 0% | ~17,5% | 12% | Craterhoof (Alpha-Strike) | 0% | 0% |
| Elfball (Marwyn) | 58% | ~4,8% | 0% | ~13-16% | 6,5% | Craterhoof+Staff+Umbral Mantle | 0% | 0% |
| Stompy (Ghalta) | 53% | ~4,8% | 0% | ~14,5% | 6,5% | 0 (kein Craterhoof) | 0% | 0% |
| +1/+1-Counter (Vorinclex) | 47% | ~2% | 0% | ~17% | 5% | Triumph of the Hordes | 0% | 0% |
| Vanilla-Kreaturen/Anthems (Ruxa) | 43,1% | 6,2% | 0% | **18,5%** | 9,2% | 0 | 0% | 0% |
| Kreatur-Toolbox/Flash (Yeva) | **66,2%** (Projekt-Rekord) | 4,6% | 1,5% | **26,2%** (Projekt-Rekord) | 9,2% | **bestätigt** (Wirewood Symbiote+Priest of Titania) | 0% | 0% |

**Vier nicht-triviale Befunde dieser Portion:**
1. **Fünfter bestätigter vollständiger Combo-Fund des Projekts:**
   Wirewood Symbiote + Priest of Titania, beide real in derselben
   Yeva-Liste (nach Heliod+Ballista/Weiß, Isochron+Dramatic
   Reversal+Basalt/Blau, Sanguine Bond+Exquisite Blood/Schwarz, Rings
   of Brighthearth+Basalt Monolith/Rot).
2. **Zwei neue Projekt-Höchstwerte GLEICHZEITIG bei Yeva:**
   Board-Präsenz 66,2% (bisheriger Rekord: Elfen/Marwyn 58%, v4.47.0)
   UND Ramp-Dichte 26,2% (bisheriger Rekord: Landfall/Ashaya ~17,5%,
   v4.47.0) — eine reine Kreatur-Toolbox-Liste maximiert beide
   Dimensionen gleichzeitig, weil praktisch jeder Nicht-Land-Slot
   entweder eine Kreatur oder ein Kreatur-Ramp-/Tutor-Enabler ist.
3. **Ruxa widerlegt real das Dokument-Label "Tokens/Go-Wide":** nur 2
   echte Token-Generatoren (Avenger of Zendikar, Rampaging Baloths),
   dafür ein klares Vanilla-Kreaturen/Anthem-Muster (Muraganda
   Petroglyphs, Gaea's Anthem, Sylvan Anthem, Beastmaster Ascension) —
   als "Vanilla-Kreaturen/Anthems" reklassifiziert, sechste
   evidenzbasierte Umklassifizierung des Projekts (nach Preston/Weiß,
   Orvar/Blau, Marrow-Gnawer/Schwarz sowie den beiden methodischen
   "control statt Dokument-Label"-Entscheidungen bei Rot).
4. **Grün bleibt über alle 6 Flavors bei 0% Wipes/Disruption/Opfer-
   Drain** (Ausnahme: Bane of Progress bei Yeva, ein permanenttyp-
   gebundener statt klassischer Wipe) — bestätigt zum sechsten Mal in
   Folge (nach den 5 Piloten-Flavors) die G-Farbmodifikator-Lücken in
   `opponent_state_weights.json` (kein disruption_growth-/
   sac_drain_growth-Modifikator für Grün).

## Die Matrix (Grün)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Landfall | – | – | **✓ (Zelle 1, aus v4.47.0)** | – | – |
| Elfball | – | – | – | – | **✓ (Zelle 2, aus v4.47.0)** |
| Stompy/Power Matters | – | **✓ (Zelle 3, aus v4.47.0)** | – | – | – |
| +1/+1-Counter/Go-Tall | – | – | **✓ (Zelle 4, aus v4.47.0)** | – | – |
| Vanilla-Kreaturen/Anthems | – | – | **✓ (Zelle 5, NEU)** | – | – |
| Kreatur-Toolbox/Flash | – | – | **✓ (Zelle 6, NEU)** | – | – |

### Zelle 1: Landfall als Midrange (unverändert aus v4.47.0)

```
board_presence_growth: 0.55
interaction_growth:    0.02
wipe_growth:            0.0
combo_growth:           0.05
passive_value_growth:  0.045
sac_drain_growth:       0.0
disruption_growth:      0.0
mana_growth:            0.23   (reale Dichte ~17,5%, hoechste des Piloten - Landfall braucht MEHR Extra-
                                Landdrops als reines Ramp)
variance_amplitude:    0.22
dead_turn_chance_base: 0.05
```

### Zelle 2: Elfball als Horde (unverändert aus v4.47.0)

```
board_presence_growth: 1.35
interaction_growth:    0.045
wipe_growth:            0.0
combo_growth:           0.04
passive_value_growth:  0.015
sac_drain_growth:       0.0
disruption_growth:      0.0
mana_growth:            0.20
variance_amplitude:    0.30
dead_turn_chance_base: 0.06
```

### Zelle 3: Stompy/Power Matters als Aggro (unverändert aus v4.47.0)

```
board_presence_growth: 0.80
interaction_growth:    0.045
wipe_growth:            0.0
combo_growth:           0.02
passive_value_growth:  0.02
sac_drain_growth:       0.0
disruption_growth:      0.0
mana_growth:            0.19
variance_amplitude:    0.30
dead_turn_chance_base: 0.08
```

### Zelle 4: +1/+1-Counter/Go-Tall als Midrange (unverändert aus v4.47.0)

```
board_presence_growth: 0.50
interaction_growth:    0.02
wipe_growth:            0.0
combo_growth:           0.06   (Triumph of the Hordes als echter Alternative-Sieg-Finisher)
passive_value_growth:  0.035
sac_drain_growth:       0.0
disruption_growth:      0.0
mana_growth:            0.21
variance_amplitude:    0.26
dead_turn_chance_base: 0.07
```

### Zelle 5: Vanilla-Kreaturen/Anthems als Midrange (NEU, v4.52.0)

```
board_presence_growth: 0.52   (leicht unter dem G-modifizierten Midrange-Basiswert 0.605 (0.55*1.10) - reale
                                Dichte 43,1%)
interaction_growth:    0.06   (Kandidat fuer Absenkung vom Basiswert 0.09: reale Dichte 6,2%)
wipe_growth:            0.0   (real 0%, Kandidat fuer Absenkung vom Basiswert 0.03)
combo_growth:           0.02  (Kandidat fuer Absenkung vom Basiswert 0.05: kein bestaetigter Combo gefunden)
passive_value_growth:  0.045  (leicht ueber dem G-modifizierten Basiswert 0.0345 (0.03*1.15) - reale Dichte 9,2%)
sac_drain_growth:       0.0
disruption_growth:     0.01
mana_growth:            0.23  (Kandidat fuer deutliche Anhebung vom G-modifizierten Basiswert 0.2015
                                (0.155*1.30): reale Ramp-Dichte 18,5% - inhaltlich naeher an Azusa/Ramp-Big-
                                Mana (Pilot-Zelle 1, ebenfalls 0.20) als am Dokument-Label "Tokens/Go-Wide")
variance_amplitude:    0.25   (unter Basiswert 0.28 - hohe Ramp-Redundanz puffert Fehlstarts)
dead_turn_chance_base: 0.07   (unter Basiswert 0.09)
```

### Zelle 6: Kreatur-Toolbox/Flash als Midrange (NEU, v4.52.0)

```
board_presence_growth: 0.85   (Kandidat fuer MASSIVE Anhebung vom G-modifizierten Midrange-Basiswert 0.605:
                                reale Dichte 66,2% - NEUER PROJEKT-HOECHSTWERT, hoeher als Elfen/Marwyn (58%,
                                v4.47.0) - eine Toolbox-Liste mit Chord of Calling/Green Sun's Zenith/Finale of
                                Devastation/Summoner's Pact besteht praktisch nur aus Kreaturen)
interaction_growth:    0.05   (Kandidat fuer Absenkung vom Basiswert 0.09: reale Dichte 4,6%)
wipe_growth:            0.02  (Kandidat fuer leichte Absenkung vom Basiswert 0.03: reale Dichte 1,5% - Bane of
                                Progress ist ein permanenttyp-gebundener, kein klassischer Kreatur-Wipe)
combo_growth:           0.08  (Kandidat fuer deutliche Anhebung vom Basiswert 0.05: Wirewood Symbiote + Priest
                                of Titania real bestaetigt - FUENFTER vollstaendiger Combo-Fund des Projekts)
passive_value_growth:  0.045  (leicht ueber dem G-modifizierten Basiswert 0.0345 - reale Dichte 9,2%)
sac_drain_growth:       0.0
disruption_growth:     0.01
mana_growth:            0.28  (Kandidat fuer MASSIVE Anhebung vom G-modifizierten Basiswert 0.2015: reale Ramp-
                                Dichte 26,2% - NEUER PROJEKT-HOECHSTWERT, hoeher als Landfall/Ashaya (~17,5%,
                                v4.47.0))
variance_amplitude:    0.22   (deutlich unter Basiswert 0.28 - die dichteste Ramp-/Toolbox-Redundanz des
                                gesamten Projekts puffert Kartenpech maximal ab)
dead_turn_chance_base: 0.05   (deutlich unter Basiswert 0.09 - bei 43 Kreaturen + 17 Ramp-Karten ist praktisch
                                jede Hand spielbar)
```

## Reflexion & Grenzen dieser Portion

1. Alle 30 bisherigen Zellen (6 Weiß + 6 Blau + 6 Schwarz + 6 Rot + 6
   Grün, plus die 5 ursprünglichen Grün-Piloten-Zellen, von denen 4
   unverändert übernommen wurden) bleiben Kandidaten, keine
   Gewichtsänderung in `opponent_state_weights.json`.
2. **Ramp/Big-Mana (Azusa) wurde bewusst NICHT gelöscht**, sondern nur
   aus der aktiven 6-Flavor-Taxonomie herausgenommen, weil das neue
   Nutzerdokument keine eigene Zeile dafür vorsieht — die Daten bleiben
   in `Docs/green_flavor_strategy_matrix_pilot_v4_47_0.md` vollständig
   erhalten und referenzierbar.
3. **Mit Grün ist die Monofarben-Ebene (5 von 5) vollständig
   abgeschlossen** (Weiß v4.48.0, Blau v4.49.0, Schwarz v4.50.0, Rot
   v4.51.0, Grün v4.52.0) — 30 Flavor-Zellen, 5 bestätigte vollständige
   Combo-Funde, durchgängig dieselbe Methodik (Dokumente als
   Recherche-Gerüst, alle Zahlen aus echten EDHREC-Bracket-3-Listen).
4. Fortsetzung folgt unmittelbar mit den 10 Zweifarb-Gilden (Azorius,
   Dimir, Rakdos, Gruul, Selesnya, Orzhov, Izzet, Golgari, Boros,
   Simic) aus `Commander_Zweifarben_Gilden_Bracket_3.md` — derselbe
   Sitzungsdurchgang, wie vom Nutzer gewünscht.
