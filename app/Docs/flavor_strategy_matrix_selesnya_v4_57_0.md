# Flavor-Strategie-Matrix — Selesnya (GW), Gilden-Portion 5 von 10 (v4.57.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Fünfte Gilden-Portion, direkt im Anschluss an Gruul (v4.56.0), gleicher
Sitzungsdurchgang. Dieselbe Methodik: Dokument als Recherche-Gerüst,
alle Werte aus echten EDHREC-Bracket-3-Listen.

Vollständige Rohdaten: `Docs/scratch/selesnya_flavor_pilot_raw.md`.

## Kombinierte GW-Farbmodifikatoren

| Dimension | G | W | GW kombiniert |
|---|---|---|---|
| board_presence | 1.10 | 1.05 | **1.155** (multiplikativ) |
| passive_value_growth | 1.15 | 1.25 | **1.4375** (multiplikativ, PROJEKT-HÖCHSTWERT) |
| wipe_readiness | – | 1.30 | **1.30** |
| disruption_growth | – | 1.20 | **1.20** |
| mana_growth | 1.30 | – | **1.30** |

**Selesnya kombiniert auf zwei Dimensionen (board_presence,
passive_value_growth) — wie Azorius und Gruul (je 2 von 7), aber mit
dem bisher höchsten Einzelwert des Projekts bei passive_value_growth
(1,4375×).** Real bestätigt: Sythis liefert mit 17,2% klassischer
Passive-Value-Dichte (plus 50,0% Enchantment-Typ-Anteil insgesamt)
einen neuen Projekt-Höchstwert, der den Multiplikator direkt stützt.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Tokens (Rhys) | 39,4% | 6,1% | 4,5% | 19,7% | 6,1% | 0 | 0% | 0% |
| +1/+1-Counter (Hamza) | **60,0%** (Projekt-Höchstwert-Kandidat) | 6,2% | 1,5% | 12,3% | 4,6% | 0 | 0% | 0% |
| Enchantress & Auren (Sythis) | 32,8% | 4,7% | 3,1% | 10,9% | **17,2%** (Projekt-Höchstwert) | 0 | 0% | 0% |
| Lifegain (Lathiel) | 49,2% | 6,3% | 1,6% | 11,1% | 4,8% | 0 | 0% | 0% |
| Humans (Katilda) | 58,5% | 6,2% | 1,5% | 6,2% | 6,2% | 0 | 0% | 0% |
| Hatebears (Yasharn) | 54,0% | **7,9%** | **3,2%** | 17,5% | 9,5% | 0 | 0% | **1,6%** (Drannith Magistrate) |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Kein einziger Combo-Fund in der gesamten Selesnya-Portion** —
   zweite Gilde in Folge ohne bestätigten Infinite (nach Gruul).
2. **Zwei Reklassifizierungen:** Sythis (Enchantress & Auren) von
   "Engine/Voltron" zu control; Yasharn (Hatebears) von
   "Stax-Midrange" zu control.
3. **Neuer Projekt-Höchstwert-Kandidat Board-Präsenz:** Hamza mit
   60,0% — bislang dichteste Kreaturen-Präsenz einer Einzelliste im
   Projekt.
4. **Neue Projekt-Höchstwerte bei Passive Value:** Sythis mit 17,2%
   klassisch bzw. 50,0% Enchantment-Typ-Anteil insgesamt.
5. Drannith Magistrate wird bei Yasharn ein zweites Mal real
   bestätigt (nach Grand Arbiter Augustin IV, Azorius v4.53.0) —
   erster Game-Changer-Wiederfund über Gilden-Grenzen hinweg.

## Die Matrix (Selesnya)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Tokens | – | – | **✓ (Zelle 1)** | – | – |
| +1/+1-Counter | – | – | **✓ (Zelle 2)** | – | – |
| Enchantress & Auren | – | – | – | **✓ (Zelle 3, umklassifiziert von "Engine/Voltron")** | – |
| Lifegain | – | – | **✓ (Zelle 4)** | – | – |
| Humans | – | **✓ (Zelle 5)** | – | – | – |
| Hatebears | – | – | – | **✓ (Zelle 6, umklassifiziert von "Stax-Midrange")** | – |

### Zelle 1: Tokens als Midrange

```
board_presence_growth: 0.44   (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.6353: reale Dichte 39,4%)
interaction_growth:    0.065  (Kandidat fuer Absenkung vom Basiswert 0.09: reale Dichte 6,1%)
wipe_growth:            0.04  (nah am GW-modifizierten Basiswert 0.039: reale Dichte 4,5%)
combo_growth:           0.025 (Kandidat fuer Absenkung vom Basiswert 0.05: kein bestaetigter Infinite)
passive_value_growth:  0.045  (nah am GW-modifizierten Basiswert 0.0431: reale Dichte 6,1%)
sac_drain_growth:       0.01  (Kandidat fuer Absenkung vom Basiswert 0.04: reale Dichte 0%)
disruption_growth:     0.01   (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.018: reale Dichte 0%)
mana_growth:            0.19  (nah am GW-modifizierten Basiswert 0.2015: reale Dichte 19,7%)
variance_amplitude:    0.27
dead_turn_chance_base: 0.08
```

### Zelle 2: +1/+1-Counter als Midrange

```
**board_presence_growth: 0.62** (nah am GW-modifizierten Basiswert 0.6353, leicht darueber real: reale Dichte
                                60,0% - Projekt-Hoechstwert-Kandidat)
interaction_growth:    0.065  (Kandidat fuer Absenkung vom Basiswert 0.09: reale Dichte 6,2%)
wipe_growth:            0.02  (Kandidat fuer DEUTLICHE Absenkung vom GW-modifizierten Basiswert 0.039: reale
                                Dichte nur 1,5%)
combo_growth:           0.025 (kein bestaetigter Infinite)
passive_value_growth:  0.04   (nah am GW-modifizierten Basiswert 0.0431: reale Dichte 4,6%)
sac_drain_growth:       0.01
disruption_growth:     0.01
mana_growth:            0.13  (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.2015: reale Dichte 12,3%)
variance_amplitude:    0.26
dead_turn_chance_base: 0.07
```

### Zelle 3: Enchantress & Auren als Control (umklassifiziert von "Engine/Voltron")

```
board_presence_growth: 0.33   (nah am GW-modifizierten Basiswert 0.3465: reale Dichte 32,8% - strukturell
                                niedrig wie bei Voltron, aber hier aus Pillow-Fort-/Engine-Fokus statt
                                Kampf-Konzentration)
interaction_growth:    0.06   (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.16: reale Dichte nur 4,7%)
wipe_growth:            0.05  (Kandidat fuer DEUTLICHE Absenkung vom GW-modifizierten Basiswert 0.143: reale
                                Dichte 3,1%)
combo_growth:           0.03  (kein bestaetigter Infinite - Sigil of the Empty Throne ist alternative
                                Wincondition statt 2-Karten-Loop)
**passive_value_growth: 0.11** (Kandidat fuer DEUTLICHE Anhebung vom GW-modifizierten Basiswert 0.0719: reale
                                Dichte 17,2% - dichteste Passive-Value-Engine des Projekts, Enchantress-
                                Archetyp per Definition, plus 50,0% Enchantment-Typ-Anteil insgesamt)
sac_drain_growth:       0.0
disruption_growth:     0.02   (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.06: reale Dichte 0% der
                                9 Game-Changer - Pillow-Fort-Enchantments sind Schutz, keine Disruption im
                                engeren Sinn)
mana_growth:            0.12  (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.182: reale Dichte 10,9%)
variance_amplitude:    0.24   (unter Basiswert 0.26 - engine-basiert statt spike-artig)
dead_turn_chance_base: 0.06
```

### Zelle 4: Lifegain als Midrange

```
board_presence_growth: 0.52   (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.6353: reale Dichte 49,2%)
interaction_growth:    0.065  (Kandidat fuer Absenkung vom Basiswert 0.09: reale Dichte 6,3%)
wipe_growth:            0.02  (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.039: reale Dichte 1,6%)
combo_growth:           0.025 (kein bestaetigter Infinite trotz "Combo 13"-Tag in dieser spezifischen Liste)
passive_value_growth:  0.04   (nah am GW-modifizierten Basiswert 0.0431: reale Dichte 4,8%)
sac_drain_growth:       0.01
disruption_growth:     0.01
mana_growth:            0.13  (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.2015: reale Dichte 11,1%)
variance_amplitude:    0.27
dead_turn_chance_base: 0.08
```

### Zelle 5: Humans als Aggro

```
board_presence_growth: 0.72   (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.9818: reale Dichte
                                58,5%)
interaction_growth:    0.06   (Kandidat fuer Anhebung vom Basiswert 0.035: reale Dichte 6,2%)
wipe_growth:            0.015 (leicht ueber 0.0: reale Dichte 1,5%)
combo_growth:           0.02  (kein bestaetigter Infinite)
passive_value_growth:  0.04   (Kandidat fuer Anhebung vom GW-modifizierten Basiswert 0.0144: reale Dichte 6,2%)
sac_drain_growth:       0.0
disruption_growth:     0.005
**mana_growth:          0.10** (Kandidat fuer DEUTLICHE Absenkung vom GW-modifizierten Basiswert 0.221: reale
                                klassische Ramp-Dichte nur 6,2% - niedrigster Wert der Portion, die guenstige
                                Humans-Kurve selbst ersetzt dedizierte Rampe)
variance_amplitude:    0.29
dead_turn_chance_base: 0.09
```

### Zelle 6: Hatebears als Control (umklassifiziert von "Stax-Midrange")

```
board_presence_growth: 0.42   (Kandidat fuer Anhebung vom GW-modifizierten Basiswert 0.3465: reale Dichte 54,0%
                                - ungewoehnlich hoch fuer Control, da viele Hatebears selbst Kreaturen sind)
**interaction_growth:   0.15** (nah am GW-modifizierten Basiswert 0.16: reale klassische Dichte 7,9%
                                (Portions-Hoechstwert), aber der breitere Hatebears/Toolbox-Kern (23,8%) wirkt
                                funktional wie zusaetzliche permanente Interaktion)
wipe_growth:            0.08   (Kandidat fuer Absenkung vom GW-modifizierten Basiswert 0.143: reale Dichte 3,2%
                                - Portions-Hoechstwert)
combo_growth:           0.02  (kein bestaetigter Infinite)
passive_value_growth:  0.07   (nah am GW-modifizierten Basiswert 0.0719: reale Dichte 9,5%)
sac_drain_growth:       0.0
**disruption_growth:    0.05** (nah am GW-modifizierten Basiswert 0.06: Drannith Magistrate real bestaetigt
                                (1,6%, zweiter Fund nach Grand Arbiter Augustin IV/Azorius), plus dichter
                                Hatebears-Kern (23,8%) als permanente Stax-Disruption ueber die 9 getrackten
                                Karten hinaus)
mana_growth:            0.17  (nah am GW-modifizierten Basiswert 0.182: reale Dichte 17,5%)
variance_amplitude:    0.22   (unter Basiswert 0.26 - Hatebears-Decks spielen konstant statt spike-artig)
dead_turn_chance_base: 0.07
```

## Reflexion & Grenzen dieser Portion

1. Alle 66 bisherigen Zellen (60 Vorportionen + 6 Selesnya) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Zweite Gilde in Folge ganz ohne bestätigten Combo-Fund** (nach
   Gruul) — bestätigt den bereits bei Gruul beobachteten Trend, dass
   grün-dominierte Gilden im Bracket-3-Kontext seltener auf
   2-Karten-Infinites setzen als schwarz-/blau-dominierte.
3. **Zwei Reklassifizierungen in einer Portion** (Sythis, Yasharn) —
   die höchste Reklassifizierungsdichte einer einzelnen Gilden-Portion
   bisher (Azorius: 1, Dimir: 1, Rakdos: 0, Gruul: 0).
4. **Neue Modellgrenze:** Sythis zeigt, dass "Engine/Voltron" im
   Dokument zwei strukturell verschiedene Deck-Typen zusammenfasst
   (Kampf-Voltron wie Stangg/Bruna vs. Pillow-Fort-Engine wie
   Sythis) — real trennen sich diese klar in Board-Präsenz UND
   Strategie-Klassifikation.
5. Fortsetzung folgt unmittelbar mit den übrigen 5 Gilden (Orzhov,
   Izzet, Golgari, Boros, Simic) — derselbe Sitzungsdurchgang, wie
   vom Nutzer gewünscht ("Arbeite bitte weiter").
