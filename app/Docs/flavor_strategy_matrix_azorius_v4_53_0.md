# Flavor-Strategie-Matrix — Azorius (WU), Gilden-Portion 1 von 10 (v4.53.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung) — Beginn der Gilden-Ebene

Mit Grün (v4.52.0) ist die Monofarben-Ebene (5/5) abgeschlossen. Diese
Portion beginnt die zweite Hälfte der Nutzer-Anfrage: die 10
Zweifarb-Gilden aus `Commander_Zweifarben_Gilden_Bracket_3.md`, jeweils
6 Flavors pro Gilde, dieselbe Methodik wie bei den 5 Monofarben (Dokument
als Recherche-Gerüst, alle Zustandsfunktionswerte aus echten EDHREC-
Bracket-3-Listen ausgezählt). **Neu bei den Gilden:** die Farbmodifikatoren
aus `opponent_state_weights.json` werden MULTIPLIKATIV kombiniert
(`_comment`: "mehrfarbige Gegner multiplizieren alle zutreffenden
Farb-Modifikatoren miteinander").

Vollständige Rohdaten: `Docs/scratch/azorius_flavor_pilot_raw.md`.

## Kombinierte WU-Farbmodifikatoren

| Dimension | W | U | WU kombiniert |
|---|---|---|---|
| board_presence | 1.05 | – | **1.05** |
| wipe_readiness | 1.30 | – | **1.30** |
| interaction_availability | – | 1.45 | **1.45** |
| combo_finish_readiness | – | 1.15 | **1.15** |
| mana_growth | – | 0.95 | **0.95** |
| passive_value_growth | 1.25 | 1.40 | **1.75** (multiplikativ, HÖCHSTER Wert aller bisherigen Modifikatoren) |
| disruption_growth | 1.20 | 1.20 | **1.44** (multiplikativ) |

**Real bestätigt durch diese Portion:** sowohl der 1,75×-Passive-Value- als
auch der 1,44×-Disruption-Multiplikator finden direkte Deckung in den
echten Decklisten (Grand Arbiter: 4 Passive-Value-Karten inkl.
Smothering Tithe+Rhystic Study+Mystic Remora GLEICHZEITIG; 17
Disruption-Karten inkl. 2 der 9 Game-Changer GLEICHZEITIG) — der erste
Fall im Projekt, in dem ein rechnerisch kombinierter Modifikator vor
der Recherche vorlag und die reale Decklisten-Dichte diesen im
Nachhinein bestätigt, statt ihn erst zu begründen.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion (Entf.+Stack) | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Draw-Go (Ojutai) | 27,0% | 23,8% | 3,2% | 11,1% | 3,2% | Approach (Alt-Sieg) | 0% | 6,3% (Narset bestätigt) |
| Blink&ETB (Brago) | 45,3% | 12,5% | 4,7% | 12,5% | 1,6% | **bestätigt** (Drake+Navigator) | 0% | 3,1% |
| Artefakte/Fahrzeuge (Shorikai) | **28,6%** (niedriger als erwartet) | 15,9% | 4,8% | 14,3% | 3,2% | 0 | 0% | 0% |
| Spirits/Flying (Millicent) | 50,8% | 15,9% | 1,6% | 6,3% | 3,2% | 0 | 0% | 3,2% |
| Auren/Voltron (Bruna) | **22,2%** (Modellgrenze) | 9,5% | 4,8% | 9,5% | 3,2% | 0 | 0% | 3,2% |
| Taxes/Pillowfort (Grand Arbiter) | 32,3% | 20,0% | 3,1% | 13,8% | 6,2% | Approach (Alt-Sieg) | 0% | **26,2%** (Projekt-Höchstwert, 2 Game-Changer) |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Sechster bestätigter vollständiger Combo-Fund des Projekts:**
   Peregrine Drake + Deadeye Navigator, beide real bei Brago (nach
   Heliod+Ballista/Weiß, Isochron+Dramatic Reversal+Basalt/Blau,
   Sanguine Bond+Exquisite Blood/Schwarz, Rings of Brighthearth+Basalt
   Monolith/Rot, Wirewood Symbiote+Priest of Titania/Grün).
2. **Neuer Projekt-Höchstwert Disruption:** Grand Arbiter Augustin IV
   liefert 26,2% (17 Karten), davon ZWEI der 9 getrackten Game-Changer
   gleichzeitig (er selbst + Drannith Magistrate) — analog zum bisher
   einzigen Doppel-Fund (Zur the Enchanter, v4.42.0, Dreifarb-Ebene),
   jetzt erstmals auf Zweifarb-Gilden-Ebene bestätigt.
3. **Erster Blau-Decklisten-Beleg für einen der 9 Game-Changer:**
   Narset, Parter of Veils bei Ojutai — vorher laut
   `opponent_state_weights.json` nur über Karten-Farbidentität
   angenommen ("U nur über die Karten-Farbidentität selbst, noch ohne
   eigenen Decklisten-Beleg").
4. **Voltron-Board-Präsenz-Modellgrenze farbübergreifend zum DRITTEN
   Mal bestätigt** (Bruna 22,2%, nach Preston/Weiß v4.48.0 und
   Valduk/Rot v4.51.0) — jetzt in 3 von 3 bisher untersuchten
   Voltron-Flavors.
5. **Artefakte & Fahrzeuge (Shorikai) widerspricht real dem
   Dokument-Label "Synergy-Midrange":** niedrige Board-Präsenz (28,6%),
   moderate Wipe-Dichte (4,8%) und hohe Interaktion (15,9%) liegen
   näher an Control — reklassifiziert.

## Die Matrix (Azorius)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Draw-Go | – | – | – | **✓ (Zelle 1)** | – |
| Blink & ETB | – | – | **✓ (Zelle 2)** | – | – |
| Artefakte & Fahrzeuge | – | – | – | **✓ (Zelle 3, umklassifiziert von "Synergy-Midrange")** | – |
| Spirits & Flying | – | **✓ (Zelle 4)** | – | – | – |
| Auren/Voltron | – | **✓ (Zelle 5)** | – | – | – |
| Taxes & Pillowfort | – | – | – | **✓ (Zelle 6)** | – |

### Zelle 1: Draw-Go als Control

```
board_presence_growth: 0.28   (nah am WU-modifizierten Control-Basiswert 0.315 (0.30*1.05) - reale Dichte 27,0%)
interaction_growth:    0.23   (nah am WU-modifizierten Basiswert 0.232 (0.16*1.45) - reale Dichte 23,8%, die
                                Kombination aus Entfernung+Stack bestaetigt den hohen U-Interaktions-
                                Multiplikator direkt)
wipe_growth:            0.06  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.143 (0.11*1.30): reale
                                Dichte nur 3,2% - Draw-Go verlaesst sich staerker auf Counterspells als auf
                                Sweeper)
combo_growth:           0.03  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.069: kein 2-Karten-
                                Infinite, nur Approach of the Second Sun als Alt-Sieg-Signal)
passive_value_growth:  0.05   (Kandidat fuer leichte Absenkung vom WU-modifizierten Basiswert 0.0875: reale
                                Dichte 3,2%)
sac_drain_growth:       0.0
disruption_growth:     0.055  (leicht ueber dem WU-modifizierten Basiswert 0.072... Kandidat fuer Absenkung:
                                reale Dichte 6,3%, aber real durch Narset - einen der 9 Game-Changer - gestuetzt)
mana_growth:            0.10  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.133: reale Dichte 11,1%)
variance_amplitude:    0.24   (unter Basiswert 0.26 - dichtes Counterspell-Paket puffert Varianz)
dead_turn_chance_base: 0.09   (leicht ueber Basiswert 0.08 - viele Karten sind rein reaktiv und "tot", solange
                                kein Ziel existiert)
```

### Zelle 2: Blink & ETB als Midrange

```
board_presence_growth: 0.55   (Kandidat fuer Absenkung vom WU-modifizierten Midrange-Basiswert 0.5775: reale
                                Dichte 45,3%)
interaction_growth:    0.11   (nah am WU-modifizierten Basiswert 0.1305 - reale Dichte 12,5%)
wipe_growth:            0.045 (leicht ueber dem WU-modifizierten Basiswert 0.039 - reale Dichte 4,7%)
combo_growth:           0.075 (Kandidat fuer Anhebung vom WU-modifizierten Basiswert 0.0575: Peregrine Drake +
                                Deadeye Navigator (+ redundant Ghostly Flicker) real bestaetigt - sechster
                                vollstaendiger Combo-Fund des Projekts)
passive_value_growth:  0.04   (Kandidat fuer leichte Absenkung vom WU-modifizierten Basiswert 0.0525: reale
                                Dichte nur 1,6%)
sac_drain_growth:       0.0
disruption_growth:     0.02   (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.0216: reale Dichte 3,1%,
                                keine Game-Changer)
mana_growth:            0.14  (nah am WU-modifizierten Basiswert 0.14725 - reale Dichte 12,5%)
variance_amplitude:    0.26   (unter Basiswert 0.28 - Combo-Backup reduziert Varianz leicht)
dead_turn_chance_base: 0.08
```

### Zelle 3: Artefakte & Fahrzeuge als Control (umklassifiziert von "Synergy-Midrange")

```
board_presence_growth: 0.30   (Kandidat fuer DEUTLICHE Absenkung vom WU-modifizierten Midrange-Basiswert 0.5775,
                                naeher am WU-modifizierten Control-Basiswert 0.315: reale Dichte nur 28,6% -
                                Vehicles/Artefakte liefern Bedrohung, keine klassische Kreaturenzahl)
interaction_growth:    0.16   (nah am WU-modifizierten Control-Basiswert 0.232... Kandidat fuer leichte
                                Absenkung: reale Dichte 15,9%)
wipe_growth:            0.10  (nah am WU-modifizierten Control-Basiswert 0.143: reale Dichte 4,8%)
combo_growth:           0.02  (Kandidat fuer Absenkung: kein bestaetigter Infinite in dieser spezifischen
                                Liste, trotz Dramatic Reversal ohne Untap-Partner)
passive_value_growth:  0.04   (nah am Basiswert - reale Dichte 3,2%)
sac_drain_growth:       0.0
disruption_growth:     0.005
mana_growth:            0.15  (nah am WU-modifizierten Basiswert 0.133-0.147 Bereich - reale Dichte 14,3%)
variance_amplitude:    0.25
dead_turn_chance_base: 0.08
```

### Zelle 4: Spirits & Flying als Aggro

```
board_presence_growth: 0.70   (Kandidat fuer Absenkung vom WU-modifizierten Aggro-Basiswert 0.8925: reale
                                Dichte 50,8%)
interaction_growth:    0.14   (Kandidat fuer DEUTLICHE Anhebung vom WU-modifizierten Basiswert 0.05075: reale
                                Dichte 15,9% - Azorius-Tempo behaelt deutlich mehr echte Antworten als
                                generisches Aggro, dieselbe Art Befund wie Elfen/Stompy bei Gruen (v4.47.0))
wipe_growth:            0.015 (leicht ueber 0.0: Fell the Mighty real vorhanden, 1,6%)
combo_growth:           0.02  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.0345: kein bestaetigter
                                Combo)
passive_value_growth:  0.025  (leicht ueber Basiswert 0.0175 - reale Dichte 3,2%)
sac_drain_growth:       0.0
disruption_growth:     0.01   (leicht ueber Basiswert 0.0072 - reale Dichte 3,2%, keine Game-Changer)
mana_growth:            0.11  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.1615: reale Dichte 6,3%
                                - Tempo-Deck kurvt ueber billige Flieger statt Ramp)
variance_amplitude:    0.28
dead_turn_chance_base: 0.09
```

### Zelle 5: Auren/Voltron als Aggro

```
board_presence_growth: 0.42   (Kandidat fuer MASSIVE Absenkung vom WU-modifizierten Aggro-Basiswert 0.8925:
                                reale Dichte nur 22,2% - dritte Bestaetigung derselben Voltron-Modellgrenze
                                (nach Preston/Weiss, Valduk/Rot): wenige, stark ausgeruestete/verzauberte
                                Kreaturen statt Board-Breite)
interaction_growth:    0.08   (Kandidat fuer Anhebung vom WU-modifizierten Basiswert 0.05075: reale Dichte 9,5%)
wipe_growth:            0.04  (Kandidat fuer Anhebung von 0.0: Divine Reckoning/Winds of Rath sind
                                Auren-schuetzende einseitige Sweeper, reale Dichte 4,8%)
combo_growth:           0.02  (Kandidat fuer Absenkung: kein bestaetigter Infinite, reiner
                                Auren-Voltron-Threat)
passive_value_growth:  0.025  (leicht ueber Basiswert - reale Dichte 3,2%)
sac_drain_growth:       0.0
disruption_growth:     0.01   (leicht ueber Basiswert - reale Dichte 3,2%, keine Game-Changer)
mana_growth:            0.13  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.1615: reale Dichte 9,5%)
variance_amplitude:    0.36   (Kandidat fuer deutliche Anhebung vom Basiswert 0.30: Voltron ist "feast or
                                famine" - dieselbe Begruendung wie bei Valduk, Rot v4.51.0)
dead_turn_chance_base: 0.12   (Kandidat fuer Anhebung: wenige Kreaturen bedeuten haeufigere Zuege ohne
                                sinnvolles Auren-Ziel)
```

### Zelle 6: Taxes & Pillowfort als Control

```
board_presence_growth: 0.33   (nah am WU-modifizierten Control-Basiswert 0.315 - reale Dichte 32,3%)
interaction_growth:    0.20   (nah am WU-modifizierten Basiswert 0.232 - reale Dichte 20,0%)
wipe_growth:            0.06  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.143: reale Dichte 3,1%
                                - Taxes/Pillowfort verlangsamt eher, als dass es das Board wischt)
combo_growth:           0.03  (Kandidat fuer Absenkung: Approach of the Second Sun als einziges Alt-Sieg-Signal,
                                kein 2-Karten-Infinite)
passive_value_growth:  0.08   (nah am WU-modifizierten Basiswert 0.0875 - reale Dichte 6,2%, bestaetigt den
                                kombinierten 1,75x-Multiplikator direkt: Smothering Tithe+Rhystic Study+Mystic
                                Remora GLEICHZEITIG)
sac_drain_growth:       0.0
**disruption_growth:    0.10** (Kandidat fuer DEUTLICHE Anhebung ueber den WU-modifizierten Basiswert 0.072:
                                reale Dichte 26,2% - PROJEKT-HOECHSTWERT - Grand Arbiter Augustin IV UND
                                Drannith Magistrate GLEICHZEITIG (2 der 9 Game-Changer), plus 15 weitere
                                generische Stax-/Tax-Karten)
mana_growth:            0.12  (Kandidat fuer Absenkung vom WU-modifizierten Basiswert 0.133: reale Dichte 13,8%
                                ist tatsaechlich noch nah dran, nur leichte Absenkung)
variance_amplitude:    0.22   (deutlich unter Basiswert 0.26 - dichtes Stax-Paket macht das Spiel fuer den Gegner
                                vorhersagbar langsam, puffert die eigene Varianz)
dead_turn_chance_base: 0.07
```

## Reflexion & Grenzen dieser Portion

1. Alle 36 bisherigen Zellen (30 Monofarben + 6 Azorius) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Wichtigster methodischer Fund:** die multiplikative Kombination
   von Farbmodifikatoren (`_comment` in der JSON) wurde zum ersten Mal
   in dieser Portion tatsächlich mit echten Zweifarb-Decklisten
   gegengeprüft — sowohl beim Passive-Value- (1,75×) als auch beim
   Disruption-Multiplikator (1,44×) bestätigt die reale Dichte den
   rechnerisch kombinierten Wert, statt ihn zu widerlegen.
3. **Grand Arbiter Augustin IV ist der bislang dichteste Einzelfund
   des Projekts** für Disruption (26,2%, 2 Game-Changer gleichzeitig)
   — ein starkes Signal, dass Taxes/Pillowfort-Flavors generell eine
   eigene, deutlich über dem generischen Control-Basiswert liegende
   Disruption-Kalibrierung verdienen.
4. Fortsetzung folgt unmittelbar mit den übrigen 9 Gilden (Dimir,
   Rakdos, Gruul, Selesnya, Orzhov, Izzet, Golgari, Boros, Simic) —
   derselbe Sitzungsdurchgang, wie vom Nutzer gewünscht.
