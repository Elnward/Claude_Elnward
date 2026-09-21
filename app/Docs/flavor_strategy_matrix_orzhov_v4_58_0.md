# Flavor-Strategie-Matrix — Orzhov (WB), Gilden-Portion 6 von 10 (v4.58.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Sechste Gilden-Portion, direkt im Anschluss an Selesnya (v4.57.0),
gleicher Sitzungsdurchgang. Dieselbe Methodik: Dokument als
Recherche-Gerüst, alle Werte aus echten EDHREC-Bracket-3-Listen.

Vollständige Rohdaten: `Docs/scratch/orzhov_flavor_pilot_raw.md`.

## Kombinierte WB-Farbmodifikatoren

| Dimension | W | B | WB kombiniert |
|---|---|---|---|
| wipe_readiness | 1.30 | 1.10 | **1.43** (multiplikativ) |
| passive_value_growth | 1.25 | 1.15 | **1.4375** (multiplikativ) |
| disruption_growth | 1.20 | 1.35 | **1.62** (multiplikativ) |
| board_presence | 1.05 | – | **1.05** |
| interaction_availability | – | 1.20 | **1.20** |
| combo_finish_readiness | – | 1.20 | **1.20** |
| sac_drain_growth | – | 1.55 | **1.55** |

**Orzhov kombiniert auf drei Dimensionen (wipe, passive_value,
disruption) — wie Dimir (4 von 7) fast gleichauf, deutlich mehr als
Azorius, Rakdos, Gruul und Selesnya (je 0-2).** Real bestätigt: DREI
Combo-Funde in einer Portion (Rekord) sowie ein neuer
Opfer/Drain-Höchstwert von 25,0% (Teysa) stützen den kombinierten
1,55×-Modifikator direkt.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Sacrifice (Teysa Karlov) | 51,6% | 6,3% | 4,7% | 7,8% | 3,1% | **bestätigt** (Yawgmoth, 11. Fund) | **25,0%** (Projekt-Höchstwert) | 0% |
| Lifegain & Drain (Karlov) | 47,0% | 9,1% | 3,0% | 7,6% | 6,1% | **bestätigt** (Exquisite Blood+Sanguine Bond, 12. Fund) | 9,1% | 0% |
| Tokens (Thalisse) | 36,5% | 7,9% | 4,8% | 7,9% | 3,2% | 0 | 15,9% | 0% |
| Reanimator & Recursion (Liesa) | 51,6% | 9,4% | **6,3%** (Portions-Höchstwert) | 9,4% | 4,7% | 0 | 20,3% | 0% |
| Auren & Curses (Eriette) | **26,6%** | 4,7% | 1,6% | 6,3% | 6,3% | 0 | 0% | 0% |
| Taxes & Pillowfort (Kambal) | 38,5% | 9,2% | 3,1% | 10,8% | 9,2% | **bestätigt** (Exquisite Blood+Sanguine Bond, 13. Fund) | 9,2% | 1,5% (Grand Abolisher) |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Dichteste Combo-Portion des Projekts: drei bestätigte Funde in
   einer Gilden-Portion** — Rekord (bisher: Rakdos mit zwei).
2. **Neuer Projekt-Höchstwert Opfer/Drain-Dichte:** Teysa Karlov mit
   25,0%.
3. **Dritter Game-Changer-Fund über Gilden-Grenzen hinweg:** Grand
   Abolisher bei Kambal (nach Grand Arbiter Augustin IV/Azorius,
   Drannith Magistrate/Selesnya).
4. **Zweites Enchantment-Engine-Deck mit extrem niedriger
   Board-Präsenz:** Eriette mit 26,6% (nach Sythis/Selesnya 32,8%).
5. Exquisite Blood + Sanguine Bond ist mit drei unabhängigen Funden
   der am häufigsten real bestätigte Combo-Typ des Projekts.

## Die Matrix (Orzhov)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Sacrifice | – | **✓ (Zelle 1)** | – | – | – |
| Lifegain & Drain | – | – | **✓ (Zelle 2)** | – | – |
| Tokens | – | – | **✓ (Zelle 3)** | – | – |
| Reanimator & Recursion | – | – | – | **✓ (Zelle 4)** | – |
| Auren & Curses | – | – | – | **✓ (Zelle 5)** | – |
| Taxes & Pillowfort | – | – | – | **✓ (Zelle 6)** | – |

### Zelle 1: Sacrifice als Aggro

```
board_presence_growth: 0.58   (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.8925: reale Dichte 51,6%)
interaction_growth:    0.06   (nah am WB-modifizierten Basiswert 0.042: reale Dichte 6,3%)
wipe_growth:            0.045 (Kandidat fuer Anhebung vom Basiswert 0.0: reale Dichte 4,7%)
**combo_growth:         0.11** (Kandidat fuer DEUTLICHE Anhebung vom WB-modifizierten Basiswert 0.036: bestaetigter
                                Infinite - elfter Combo-Fund des Projekts, dritte Bestaetigung des
                                Yawgmoth-Musters, hier sogar mit BEIDEN Opfer-Altaeren gleichzeitig)
passive_value_growth:  0.03
**sac_drain_growth:     0.19** (Kandidat fuer DEUTLICHE Anhebung vom WB-modifizierten Basiswert 0.0155: reale
                                Dichte 25,0% - NEUER PROJEKT-HOECHSTWERT, uebertrifft Judith/Rakdos 16,9% und
                                Yawgmoth/Schwarz 17,2%)
disruption_growth:     0.005
mana_growth:            0.10  (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.17: reale Dichte nur 7,8%)
variance_amplitude:    0.33   (ueber Basiswert 0.30 - Combo-Finish erhoeht die Varianz)
dead_turn_chance_base: 0.08
```

### Zelle 2: Lifegain & Drain als Midrange

```
board_presence_growth: 0.48   (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.5775: reale Dichte 47,0%)
interaction_growth:    0.10   (nah am WB-modifizierten Basiswert 0.108: reale Dichte 9,1%)
wipe_growth:            0.03  (nah am WB-modifizierten Basiswert 0.0429: reale Dichte 3,0%)
**combo_growth:         0.10** (Kandidat fuer DEUTLICHE Anhebung vom WB-modifizierten Basiswert 0.06: bestaetigter
                                Infinite - zwoelfter Combo-Fund des Projekts, zweite Bestaetigung des
                                Exquisite-Blood+Sanguine-Bond-Musters)
passive_value_growth:  0.05   (Kandidat fuer Anhebung vom WB-modifizierten Basiswert 0.0431: reale Dichte 6,1%)
sac_drain_growth:       0.07  (nah am WB-modifizierten Basiswert 0.062: reale Dichte 9,1%)
disruption_growth:     0.015
mana_growth:            0.11  (Kandidat fuer Absenkung vom Basiswert 0.155: reale Dichte 7,6%)
variance_amplitude:    0.29   (ueber Basiswert 0.28 - Combo-Finish)
dead_turn_chance_base: 0.08
```

### Zelle 3: Tokens als Midrange

```
board_presence_growth: 0.40   (Kandidat fuer DEUTLICHE Absenkung vom WB-modifizierten Basiswert 0.5775: reale
                                Dichte 36,5%)
interaction_growth:    0.08   (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.108: reale Dichte 7,9%)
wipe_growth:            0.045 (nah am WB-modifizierten Basiswert 0.0429: reale Dichte 4,8%)
combo_growth:           0.03  (kein bestaetigter Infinite in dieser spezifischen Liste)
passive_value_growth:  0.035  (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.0431: reale Dichte 3,2%)
**sac_drain_growth:     0.13** (Kandidat fuer DEUTLICHE Anhebung vom WB-modifizierten Basiswert 0.062: reale
                                Dichte 15,9%)
disruption_growth:     0.015
mana_growth:            0.11  (Kandidat fuer Absenkung vom Basiswert 0.155: reale Dichte 7,9%)
variance_amplitude:    0.29
dead_turn_chance_base: 0.08
```

### Zelle 4: Reanimator & Recursion als Control

```
board_presence_growth: 0.42   (Kandidat fuer Anhebung vom WB-modifizierten Basiswert 0.315: reale Dichte 51,6% -
                                viele Aristokraten-Kreaturen sind selbst Boardpraesenz)
interaction_growth:    0.13   (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.192: reale Dichte 9,4%)
**wipe_growth:          0.10** (Kandidat fuer leichte Absenkung vom WB-modifizierten Basiswert 0.1573: reale
                                Dichte 6,3% - Portions-Hoechstwert, bestaetigt den Wipe-Multiplikator direkt)
combo_growth:           0.02  (kein bestaetigter Infinite - Sanguine Bond ohne Exquisite Blood, Karmic Guide
                                ohne Loop-Partner in dieser Liste)
passive_value_growth:  0.05   (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.0719: reale Dichte 4,7%)
**sac_drain_growth:     0.16** (Kandidat fuer DEUTLICHE Anhebung vom WB-modifizierten Basiswert 0.0155: reale
                                Dichte 20,3%)
disruption_growth:     0.02
mana_growth:            0.13  (nah am Basiswert 0.14: reale Dichte 9,4%)
variance_amplitude:    0.24
dead_turn_chance_base: 0.07
```

### Zelle 5: Auren & Curses als Control

```
**board_presence_growth: 0.24** (Kandidat fuer DEUTLICHE Absenkung vom WB-modifizierten Basiswert 0.315: reale
                                Dichte nur 26,6% - niedrigster Wert der Portion, drittes Enchantment-Engine-
                                Deck mit struktureller Board-Praesenz-Limitation nach Sythis/Selesnya und
                                Stangg/Gruul-Voltron)
interaction_growth:    0.06   (Kandidat fuer DEUTLICHE Absenkung vom WB-modifizierten Basiswert 0.192: reale
                                Dichte nur 4,7%)
wipe_growth:            0.05  (Kandidat fuer DEUTLICHE Absenkung vom WB-modifizierten Basiswert 0.1573: reale
                                Dichte 1,6%)
combo_growth:           0.02  (kein bestaetigter Infinite)
**passive_value_growth: 0.08** (Kandidat fuer Anhebung vom WB-modifizierten Basiswert 0.0719: reale klassische
                                Dichte 6,3%, aber dichter Auren/Curses-Kern (37,5%) wirkt funktional wie
                                zusaetzlicher Passive-Value-Ersatz, siehe Reflexion)
sac_drain_growth:       0.0
disruption_growth:     0.02   (Kandidat fuer DEUTLICHE Absenkung vom WB-modifizierten Basiswert 0.081: reale
                                Dichte 0% der 9 Game-Changer - Curses sind gezielte Malus-Effekte, keine der
                                getrackten Karten)
mana_growth:            0.09  (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.14: reale Dichte nur 6,3%)
variance_amplitude:    0.22
dead_turn_chance_base: 0.07
```

### Zelle 6: Taxes & Pillowfort als Control

```
board_presence_growth: 0.36   (Kandidat fuer Anhebung vom WB-modifizierten Basiswert 0.315: reale Dichte 38,5%)
interaction_growth:    0.14   (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.192: reale Dichte 9,2%)
wipe_growth:            0.08  (Kandidat fuer Absenkung vom WB-modifizierten Basiswert 0.1573: reale Dichte 3,1%)
combo_growth:           0.10  (Kandidat fuer Anhebung vom WB-modifizierten Basiswert 0.072: bestaetigter
                                Infinite - dreizehnter Combo-Fund des Projekts, dritte Bestaetigung des
                                Exquisite-Blood+Sanguine-Bond-Musters, zweiter Fund innerhalb dieser Portion)
passive_value_growth:  0.08   (nah am WB-modifizierten Basiswert 0.0719: reale Dichte 9,2%)
sac_drain_growth:       0.06  (Kandidat fuer Anhebung vom WB-modifizierten Basiswert 0.0155: reale Dichte 9,2%)
**disruption_growth:    0.07** (nah am WB-modifizierten Basiswert 0.081: Grand Abolisher real bestaetigt,
                                dritter Game-Changer-Fund des Projekts ueber Gilden-Grenzen hinweg)
mana_growth:            0.12  (nah am Basiswert 0.14: reale Dichte 10,8%)
variance_amplitude:    0.25
dead_turn_chance_base: 0.07
```

## Reflexion & Grenzen dieser Portion

1. Alle 72 bisherigen Zellen (66 Vorportionen + 6 Orzhov) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Dichteste Combo-Portion des Projekts:** drei bestätigte Funde
   (Yawgmoth bei Teysa; Exquisite Blood+Sanguine Bond bei Karlov UND
   Kambal) — WB bestätigt sich damit real als die combo-dichteste
   Gilde des Projekts, konsistent mit der Dokument-Warnung im
   Bracket-Hinweis ("Orzhov-Aristocrats enthält viele natürliche
   Zwei- und Drei-Karten-Schleifen").
3. **Wiederkehrende Modellgrenze, weiterer Fall:** der Auren/Curses-
   Kern bei Eriette (37,5%) lässt sich nicht sauber einem bestehenden
   Feld zuordnen, wurde hilfsweise auf passive_value_growth gemappt
   (analog zu Sythis/Selesnya) — die wachsende Liste dieser Fälle
   (Rot, Dimir, Rakdos, Gruul, Selesnya, jetzt Orzhov) stützt den
   bereits mehrfach dokumentierten Bedarf für ein dediziertes
   "thematische Kern-Dichte"-Feld.
4. **Dritte Bestätigung der Enchantment-Engine-Board-Präsenz-
   Limitation** (Sythis, Stangg, jetzt Eriette) — ein eigenständiges,
   von der Voltron-Limitation zu unterscheidendes, aber strukturell
   verwandtes Muster.
5. Fortsetzung folgt unmittelbar mit den übrigen 4 Gilden (Izzet,
   Golgari, Boros, Simic) — derselbe Sitzungsdurchgang, wie vom
   Nutzer gewünscht ("Arbeite bitte weiter").
