# Flavor-Strategie-Matrix — Golgari (BG), Gilden-Portion 8 von 10 (v4.60.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Achte Gilden-Portion, direkt im Anschluss an Izzet (v4.59.0), gleicher
Sitzungsdurchgang. Dieselbe Methodik: Dokument als Recherche-Gerüst,
alle Werte aus echten EDHREC-Bracket-3-Listen.

Vollständige Rohdaten: `Docs/scratch/golgari_flavor_pilot_raw.md`.

## Kombinierte BG-Farbmodifikatoren

| Dimension | B | G | BG kombiniert |
|---|---|---|---|
| passive_value_growth | 1.15 | 1.15 | **1.3225** (multiplikativ) |
| interaction_availability | 1.20 | – | **1.20** |
| wipe_readiness | 1.10 | – | **1.10** |
| combo_finish_readiness | 1.20 | – | **1.20** |
| sac_drain_growth | 1.55 | – | **1.55** |
| disruption_growth | 1.35 | – | **1.35** |
| mana_growth | – | 1.30 | **1.30** |
| board_presence | – | 1.10 | **1.10** |

**Golgari kombiniert nur auf EINER Dimension (passive_value_growth) —
anders als bei Izzet (mana_growth, nahezu neutral) ist diese
Überlappung hier real deutlich verstärkend (1,3225×, beide Farben
tragen echten Aufwärtsdruck bei), nicht nahezu neutralisierend.** Auf
den übrigen sechs Dimensionen liefert jeweils nur eine der beiden
Farben einen Modifikator (Union statt Produkt). Real bestätigt: die
beiden Game-Changer-Funde außerhalb der 9 Disruption-Karten (Field of
the Dead, Seedborn Muse) sind beide passive-value-/finish-nahe Effekte
und stützen damit indirekt den verstärkten kombinierten
passive_value-Multiplikator.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption | Eigener Kern |
|---|---|---|---|---|---|---|---|---|---|
| Graveyard & Reanimator (Meren) | 57,8% | 4,7% | 3,1% | 14,1% | 4,7% | 0 | 15,6% | 0% | Graveyard/Reanimator-Kern 15,6% |
| Sacrifice (Mazirek) | 50,0% | 6,3% | 1,6% | 12,5% | 4,7% | 0 | **21,9%** (2.-höchster Wert) | 0% | Counter-Kern 14,1% (4 Verdoppler) |
| Lands in the Graveyard (The Gitrog Monster) | 44,8% | 6,9% | 3,4% | 20,7% | 1,7% | 0 (Field of the Dead real) | 1,7% | 0% | Landfall/Grave-Kern 19,0% |
| +1/+1-Counter (Skullbriar) | **29,7%** (5. Voltron-Instanz) | 6,3% | 1,6% | 7,8% | 1,6% | 0 | 0% | 0% | **Counter-Kern 42,2%** (Projekt-Höchstwert) |
| Elves (Lathril) | 53,8% | 6,2% | 3,1% | 16,9% | 4,6% | **bestätigt** (Elfball, 14. Fund) | 0% | 0% | Elves-Kern ≈ Board-Präsenz |
| Fungus & Saprolings (Slimefoot) | 40,6% | 6,3% | 3,1% | 17,2% | 3,1% | 0 | 14,1% | 0% | Fungus-Kern ≈ Board-Präsenz |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Vierzehnter bestätigter Combo-Fund des Projekts, erster seiner
   Art:** Priest of Titania + Staff of Domination bei Lathril - das
   klassische "Elfball"-Infinite-Mana-Combo.
2. **Zwei weitere Altar-Doppel-Funde (Ashnod's + Phyrexian Altar)
   OHNE dritten Combo-Baustein** bei Mazirek und Slimefoot - bestätigt
   die methodische Zurückhaltung des Projekts weiter.
3. **Neuer Projekt-Höchstwert Counter-Verdoppler-Dichte zweimal in
   einer Portion übertroffen:** Mazirek (vier Verdoppler) und dann
   Skullbriar (fünf Verdoppler, 42,2% Gesamt-Kern) - mit Abstand die
   dichteste thematische Kern-Dimension des gesamten Projekts.
4. **Fünfte Voltron-Board-Präsenz-Modellgrenze:** Skullbriar mit
   29,7% (nach Preston/Weiß, Valduk/Rot, Bruna/Azorius, Stangg/Gruul).
5. **Zwei neue Game-Changer-Funde außerhalb der 9
   Disruption-Karten:** Field of the Dead (Gitrog) und Seedborn Muse
   (Lathril) - erweitert die Game-Changer-Beobachtung über die
   Disruption-Dimension hinaus.

## Die Matrix (Golgari)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Graveyard & Reanimator | – | – | **✓ (Zelle 1)** | – | – |
| Sacrifice | – | – | **✓ (Zelle 2)** | – | – |
| Lands in the Graveyard | – | – | – | **✓ (Zelle 3)** | – |
| +1/+1-Counter | – | **✓ (Zelle 4)** | – | – | – |
| Elves | – | **✓ (Zelle 5)** | – | – | – |
| Fungus & Saprolings | – | – | **✓ (Zelle 6)** | – | – |

### Zelle 1: Graveyard & Reanimator als Midrange

```
board_presence_growth: 0.55   (nah am BG-modifizierten Basiswert 0.605: reale Dichte 57,8%)
interaction_growth:    0.06   (Absenkung vom BG-modifizierten Basiswert 0.108: reale Dichte 4,7%)
wipe_growth:            0.03  (nah am BG-modifizierten Basiswert 0.033: reale Dichte 3,1%, inkl. Culling
                                Ritual als Mini-Wipe)
**combo_growth:         0.07** (Kandidat fuer leichte Anhebung vom BG-modifizierten Basiswert 0.06: kein
                                bestaetigter Infinite - Yawgmoth ohne 0-Kosten-Recursion-Kreatur - aber
                                dichter Graveyard/Reanimator-Kern (15,6%: Entomb/Buried Alive/Reanimate/
                                Animate Dead/Living Death/Victimize/Eldritch Evolution) wirkt als
                                Toolbox-Value-Engine - hilfsweise mitgemappt, siehe Reflexion)
passive_value_growth:  0.04   (nah am BG-modifizierten Basiswert 0.039675: reale Dichte 4,7%)
**sac_drain_growth:     0.14** (Kandidat fuer Anhebung vom BG-modifizierten Basiswert 0.062: reale Dichte
                                15,6% - starkes Aristokraten-Grundgerüst trotz Reanimator-Fokus)
disruption_growth:     0.01   (Absenkung vom BG-modifizierten Basiswert 0.02025: 0 der 9 Game-Changer)
mana_growth:            0.15  (Absenkung vom BG-modifizierten Basiswert 0.2015: reale Ramp-Dichte nur 14,1%)
variance_amplitude:    0.27   (nah am Basiswert 0.28)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

### Zelle 2: Sacrifice als Midrange

```
board_presence_growth: 0.46   (Absenkung vom BG-modifizierten Basiswert 0.605: reale Dichte 50,0%)
interaction_growth:    0.07   (Absenkung vom BG-modifizierten Basiswert 0.108: reale Dichte 6,3%)
wipe_growth:            0.025 (Absenkung vom Basiswert 0.033: reale Dichte 1,6%, einziger Wipe ist ein
                                symmetrischer Edict-Effekt)
**combo_growth:         0.08** (Kandidat fuer Anhebung vom BG-modifizierten Basiswert 0.06: kein bestaetigter
                                Infinite trotz beider Opfer-Altaere, aber der VIERFACHE
                                Counter-Verdoppler-Kern (Corpsejack Menace, Hardened Scales, Winding
                                Constrictor, Doubling Season, 14,1%) wirkt als explosive
                                Skalierungs-Engine - hilfsweise mitgemappt, siehe Reflexion)
passive_value_growth:  0.04   (nah am BG-modifizierten Basiswert 0.039675: reale Dichte 4,7%)
**sac_drain_growth:     0.17** (Kandidat fuer DEUTLICHE Anhebung vom BG-modifizierten Basiswert 0.062: reale
                                Dichte 21,9% - zweithoechster Wert des Projekts nach Teysa/Orzhov 25,0%)
disruption_growth:     0.01   (Absenkung: 0 der 9 Game-Changer)
mana_growth:            0.14  (Absenkung vom BG-modifizierten Basiswert 0.2015: reale Ramp-Dichte 12,5%)
variance_amplitude:    0.30   (ueber Basiswert 0.28: Counter-Explosion erhoeht die Varianz)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

### Zelle 3: Lands in the Graveyard als Control

```
board_presence_growth: 0.38   (Kandidat fuer Anhebung vom BG-modifizierten Basiswert 0.33: reale Dichte
                                44,8% - viele Ramp-Kreaturen zaehlen selbst als Board-Praesenz)
**interaction_growth:  0.10** (Kandidat fuer DEUTLICHE Absenkung vom BG-modifizierten Basiswert 0.192: reale
                                Dichte 6,9%)
**wipe_growth:          0.05** (Kandidat fuer DEUTLICHE Absenkung vom BG-modifizierten Basiswert 0.121: reale
                                Dichte nur 3,4%)
combo_growth:           0.08  (leichte Anhebung vom BG-modifizierten Basiswert 0.072: kein garantierter
                                Infinite, aber Field of the Dead - ERSTER Fund dieses offiziellen
                                Game-Changers im Projekt - liefert ein reales alternatives
                                Siegcondition-Element, siehe Reflexion)
**passive_value_growth: 0.02** (Kandidat fuer DEUTLICHE Absenkung vom BG-modifizierten Basiswert 0.066125:
                                reale Dichte nur 1,7%)
sac_drain_growth:       0.02  (nah am Basiswert 0.0155: reale Dichte 1,7%, nur Zuran Orb)
**disruption_growth:    0.02** (Kandidat fuer DEUTLICHE Absenkung vom BG-modifizierten Basiswert 0.0675: 0
                                der 9 Disruption-Game-Changer)
mana_growth:            0.19  (leichte Anhebung vom BG-modifizierten Basiswert 0.182: reale Ramp-Dichte
                                20,7% - hoechster Ramp-Wert der Portion)
variance_amplitude:    0.24   (unter Basiswert 0.26: Land-Rekursions-Engine ist eher stetig als swingy)
dead_turn_chance_base: 0.07   (nah am Basiswert 0.08)
```

### Zelle 4: +1/+1-Counter als Aggro

```
**board_presence_growth: 0.30** (Kandidat fuer MASSIVE Absenkung vom BG-modifizierten Aggro-Basiswert 0.935:
                                reale Dichte nur 29,7% - FUENFTE Voltron-Modellgrenze des Projekts, siehe
                                Reflexion)
interaction_growth:    0.06   (leichte Anhebung vom Basiswert 0.042: reale Dichte 6,3% - mehrere
                                counter-konditionierte Removal-Spells wie Blood Curdle)
wipe_growth:            0.02  (Anhebung vom Basiswert 0.0: reale Dichte 1,6%)
**combo_growth:         0.14** (Kandidat fuer MASSIVE Anhebung vom Basiswert 0.036: kein bestaetigter
                                Infinite, aber der EXTREME Counter-Kern (27 Karten, 42,2%, NEUER
                                PROJEKT-HOECHSTWERT aller thematischen Kern-Dimensionen) wirkt als die mit
                                Abstand dominanteste Skalierungs-Engine des Projekts - hilfsweise
                                mitgemappt, siehe Reflexion)
passive_value_growth:  0.015  (nah am Basiswert 0.013225: reale Dichte 1,6%)
sac_drain_growth:       0.0   (keine Opfer-/Drain-Elemente)
disruption_growth:     0.005  (nah am Basiswert 0.00675: 0 der 9 Game-Changer)
**mana_growth:          0.12** (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.221: reale Ramp-Dichte nur
                                7,8% - typisches Voltron-Muster, wenig Ramp-Investition)
**variance_amplitude:   0.38** (Kandidat fuer DEUTLICHE Anhebung vom Basiswert 0.30: extremer Counter-Stack
                                macht den Voltron-Threat hoch swingy - "feast or famine", analog zu
                                Bruna/Valduk)
dead_turn_chance_base: 0.12   (Anhebung vom Basiswert 0.10: wenige Kreaturen bedeuten haeufigere Zuege ohne
                                sinnvolles Ziel, analog zum Voltron-Muster)
```

### Zelle 5: Elves als Aggro

```
board_presence_growth: 0.52   (Absenkung vom BG-modifizierten Aggro-Basiswert 0.935: reale Dichte 53,8% -
                                deutlich hoeher als Skullbriars Voltron-Wert, da Go-Wide-Typal-Plan)
interaction_growth:    0.06   (leichte Anhebung vom Basiswert 0.042: reale Dichte 6,2%)
wipe_growth:            0.03  (Anhebung vom Basiswert 0.0: reale Dichte 3,1% - Kindred Dominance als
                                einseitiger Typal-Wipe)
**combo_growth:         0.16** (Kandidat fuer MASSIVE Anhebung vom Basiswert 0.036: bestaetigter Infinite -
                                VIERZEHNTER Combo-Fund des Projekts, Priest of Titania + Staff of
                                Domination "Elfball"-Manacombo, real beide Karten gemeinsam vorhanden)
**passive_value_growth: 0.03** (Anhebung vom Basiswert 0.013225: reale Dichte 4,6%, inkl. Seedborn Muse als
                                zweiter Game-Changer-Fund ausserhalb der Disruption-9)
sac_drain_growth:       0.0   (keine Opfer-/Drain-Elemente)
disruption_growth:     0.005  (nah am Basiswert 0.00675: 0 der 9 Disruption-Game-Changer)
mana_growth:            0.17  (Absenkung vom Basiswert 0.221: reale Ramp-Dichte 16,9%, dennoch dank
                                Elfen-Mana-Basis strukturell hoch)
variance_amplitude:    0.34   (ueber Basiswert 0.30: Combo-Finish plus Craterhoof-Alpha-Strike erhoehen die
                                Varianz)
dead_turn_chance_base: 0.08   (unter Basiswert 0.10: konstanter Mana-Nachschub reduziert tote Zuege)
```

### Zelle 6: Fungus & Saprolings als Midrange

```
board_presence_growth: 0.38   (Kandidat fuer DEUTLICHE Absenkung vom BG-modifizierten Basiswert 0.605: reale
                                Dichte 40,6%)
interaction_growth:    0.07   (Absenkung vom BG-modifizierten Basiswert 0.108: reale Dichte 6,3%)
wipe_growth:            0.03  (nah am Basiswert 0.033: reale Dichte 3,1%)
combo_growth:           0.04  (Absenkung vom BG-modifizierten Basiswert 0.06: kein bestaetigter Infinite
                                trotz beider Opfer-Altaere - dritter Altar-Doppel-Fund der Portion ohne
                                dritten Baustein, analog Mazirek)
passive_value_growth:  0.035  (nah am BG-modifizierten Basiswert 0.039675: reale Dichte 3,1%)
**sac_drain_growth:     0.10** (Kandidat fuer Anhebung vom BG-modifizierten Basiswert 0.062: reale Dichte
                                14,1%)
disruption_growth:     0.01   (Absenkung: 0 der 9 Game-Changer)
mana_growth:            0.18  (leichte Absenkung vom BG-modifizierten Basiswert 0.2015: reale Ramp-Dichte
                                17,2%)
variance_amplitude:    0.27   (nah am Basiswert 0.28)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

## Reflexion & Grenzen dieser Portion

1. Alle 84 bisherigen Zellen (78 Vorportionen + 6 Golgari) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Vierzehnter bestätigter Combo-Fund, erstes "Elfball"-Muster:**
   Priest of Titania + Staff of Domination bei Lathril - im
   Unterschied zu den bisher dominanten Yawgmoth- und Exquisite-
   Blood+Sanguine-Bond-Mustern ein reines Infinite-Mana-Combo ohne
   Sacrifice-Bezug.
3. **Wiederkehrende Modellgrenze, drei neue Fälle in einer Portion:**
   der Counter-Kern (Skullbriar, Mazirek) und die Typal-/Fungus-Kerne
   (Lathril, Slimefoot) lassen sich nicht sauber einem bestehenden
   Feld zuordnen — hilfsweise je nach Funktion auf combo_growth
   (explosive Skalierung ohne bestätigten Infinite: Skullbriar,
   Mazirek) oder implizit über board_presence/mana_growth (Lathril,
   Slimefoot, da strukturell deckungsgleich mit der Kreaturenbasis)
   behandelt. Die wachsende Liste (Rot, Dimir, Rakdos, Gruul,
   Selesnya, Orzhov, Izzet, jetzt vierfach bei Golgari) bestätigt den
   Bedarf für ein dediziertes "thematische Kern-Dichte"-Feld weiter.
4. **Fünfte Bestätigung der Voltron-Board-Präsenz-Modellgrenze**
   (Preston, Valduk, Bruna, Stangg, jetzt Skullbriar) — mit 29,7% der
   bisher am wenigsten extreme Fall, aber strukturell klar demselben
   Muster zugehörig.
5. **Game-Changer-Beobachtung erstmals über die Disruption-Dimension
   hinaus erweitert:** Field of the Dead (alt_win_condition) und
   Seedborn Muse (draw_engine/passive_value) sind die ersten realen
   Funde von Game-Changern außerhalb der 9 getrackten
   Disruption-Karten — beide passen exakt zu ihrer projekteigenen
   Tagging-Kategorie (`combo_finish_readiness` bzw.
   `passive_value_by_type`), was die Konsistenz von
   `game_changer_archetypes.json` real bestätigt.
6. Fortsetzung folgt unmittelbar mit den übrigen 2 Gilden (Boros,
   Simic) — derselbe Sitzungsdurchgang, wie vom Nutzer gewünscht
   ("Arbeite bitte weiter").
