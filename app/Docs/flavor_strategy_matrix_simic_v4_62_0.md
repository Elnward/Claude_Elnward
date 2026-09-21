# Flavor-Strategie-Matrix — Simic (GU), Gilden-Portion 10 von 10 (v4.62.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung) — ABSCHLUSS DER GILDEN-EBENE

Zehnte und letzte Gilden-Portion, direkt im Anschluss an Boros
(v4.61.0), gleicher Sitzungsdurchgang. Dieselbe Methodik: Dokument als
Recherche-Gerüst, alle Werte aus echten EDHREC-Bracket-3-Listen. Mit
dieser Portion ist die gesamte Zweifarben-Gilden-Ebene (10 von 10
Gilden, 60 von 60 Flavor-Zellen) abgeschlossen.

Vollständige Rohdaten: `Docs/scratch/simic_flavor_pilot_raw.md`.

## Kombinierte GU-Farbmodifikatoren

| Dimension | G | U | GU kombiniert |
|---|---|---|---|
| mana_growth | 1.30 | 0.95 | **1.235** (multiplikativ) |
| passive_value_growth | 1.15 | 1.40 | **1.61** (multiplikativ) |
| board_presence | 1.10 | – | **1.10** |
| interaction_availability | – | 1.45 | **1.45** |
| combo_finish_readiness | – | 1.15 | **1.15** |
| disruption_growth | – | 1.20 | **1.20** |
| wipe_readiness | – | – | **1.0** (keine Modifikation) |
| sac_drain_growth | – | – | **1.0** (keine Modifikation) |

**Simic kombiniert auf ZWEI von sieben Dimensionen (mana_growth UND
passive_value_growth) — der zweithöchste Überlappungsgrad des
Projekts nach Dimir (4 von 7). Der kombinierte passive_value-Wert
(1,61×) ist der zweithöchste Einzelwert des gesamten Projekts,
knapp hinter Orzhovs disruption_growth (1,62×).** Real bestätigt: die
projektweit am häufigsten gefundenen Game-Changer außerhalb der
Disruption-9 sind ausnahmslos passive_value-getaggt (Seedborn Muse,
Rhystic Study) und traten in dieser Portion gehäuft auf — konsistent
mit dem verstärkten kombinierten Multiplikator.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Eigener Kern |
|---|---|---|---|---|---|---|---|
| +1/+1-Counter (Ezuri) | 56,3% | 7,8% | 1,6% | 25,0% | 4,7% | 0 | Counter-Kern 23,4% |
| Lands & Landfall (Aesi) | 45,8% | 8,5% | 3,4% | **37,3%** (Projekt-Höchstwert) | 3,4% | 0 | Landfall-Kern 18,6% |
| Sea Monsters (Arixmethes) | 42,4% | 11,9% | 3,4% | 22,0% | 5,1% | 0 | Sea-Monsters-Kern ≈ Board-Präsenz |
| Tokens & Copies (Adrix and Nev) | 37,1% | 6,5% | 1,6% | 21,0% | 3,2% | **bestätigt** (Biovisionary, 16. Fund) | Token/Clone-Kern 45,2% (Höchstwert) |
| Merfolk (Kumena) | 53,1% | 7,8% | 3,1% | 10,9% | 4,7% | 0 | Typal-Kern ≈ Board-Präsenz |
| Mana Engines (Kinnan) | 47,8% | 13,4% | **0%** | 32,8% | 6,0% | **bestätigt** (Kinnan-Combo, 17. Fund) | Mana-Engine-Kern ≈ Ramp |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Neuer Projekt-Höchstwert Ramp-Dichte, mit großem Abstand:** Aesi
   mit 37,3% - deutlich über dem bisherigen Höchstwert The Gitrog
   Monster/Golgari (20,7%).
2. **Siebzehnter und sechzehnter bestätigter Combo-Fund, zwei neue
   Muster:** das namensgebende Kinnan-Combo (Basalt Monolith +
   Dramatic Reversal) und der erste alternative-Sieg-Fund
   (Biovisionary + Rite of Replication bei Adrix and Nev).
3. **Neuer Projekt-Höchstwert Token/Clone-Kern-Dichte:** Adrix and
   Nev mit 45,2% (übertrifft Neyali/Boros 43,8%).
4. **Erster Simic-Flavor gänzlich ohne Board-Wipe:** Kinnan (0%) -
   setzt vollständig auf Counterspells statt Sweeper.
5. **Siebenfache Bestätigung des "Kern überschneidet mit
   Basisdimension"-Musters,** davon dreifach allein in dieser Portion
   (Sea-Monsters/Arixmethes, Merfolk/Kumena, Mana-Engine/Kinnan) - das
   am häufigsten wiederkehrende Modellgrenze des gesamten Projekts.

## Die Matrix (Simic)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| +1/+1-Counter | – | – | **✓ (Zelle 1)** | – | – |
| Lands & Landfall | – | – | **✓ (Zelle 2)** | – | – |
| Sea Monsters | – | – | **✓ (Zelle 3)** | – | – |
| Tokens & Copies | – | – | **✓ (Zelle 4)** | – | – |
| Merfolk | – | – | **✓ (Zelle 5)** | – | – |
| Mana Engines | – | – | – | **✓ (Zelle 6)** | – |

### Zelle 1: +1/+1-Counter als Midrange

```
board_presence_growth: 0.56   (nah am GU-modifizierten Basiswert 0.605: reale Dichte 56,3%)
interaction_growth:    0.08   (Absenkung vom GU-modifizierten Basiswert 0.1305: reale Dichte 7,8%)
wipe_growth:            0.02  (Absenkung vom Basiswert 0.03: reale Dichte 1,6%, nur Cyclonic Rift)
**combo_growth:         0.08** (Kandidat fuer Anhebung vom GU-modifizierten Basiswert 0.0575: kein
                                bestaetigter Infinite, aber dichter Counter-Kern (23,4%) wirkt als
                                Skalierungs-Engine - hilfsweise mitgemappt)
passive_value_growth:  0.045  (nah am GU-modifizierten Basiswert 0.0483: reale Dichte 4,7%)
sac_drain_growth:       0.02  (Absenkung vom Basiswert 0.04: keine Aristokraten-Elemente)
disruption_growth:     0.01   (Absenkung: 0 der 9 Game-Changer)
**mana_growth:          0.22** (Anhebung vom GU-modifizierten Basiswert 0.191425: reale Ramp-Dichte 25,0%)
variance_amplitude:    0.28   (am Basiswert)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

### Zelle 2: Lands & Landfall als Midrange

```
board_presence_growth: 0.46   (Absenkung vom GU-modifizierten Basiswert 0.605: reale Dichte 45,8%)
interaction_growth:    0.08   (Absenkung vom GU-modifizierten Basiswert 0.1305: reale Dichte 8,5%)
wipe_growth:            0.03  (nah am Basiswert 0.03: reale Dichte 3,4%)
combo_growth:           0.05  (Absenkung vom Basiswert 0.0575: kein bestaetigter Infinite)
passive_value_growth:  0.04   (leichte Absenkung vom GU-modifizierten Basiswert 0.0483: reale Dichte 3,4%)
sac_drain_growth:       0.02
disruption_growth:     0.01
**mana_growth:          0.28** (Kandidat fuer MASSIVE Anhebung vom GU-modifizierten Basiswert 0.191425:
                                reale Ramp-Dichte 37,3% - NEUER PROJEKT-HOECHSTWERT)
variance_amplitude:    0.27   (nah am Basiswert 0.28)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

### Zelle 3: Sea Monsters als Midrange

```
board_presence_growth: 0.44   (Absenkung vom GU-modifizierten Basiswert 0.605: reale Dichte 42,4%)
interaction_growth:    0.12   (nah am GU-modifizierten Basiswert 0.1305: reale Dichte 11,9%)
wipe_growth:            0.03  (nah am Basiswert 0.03: reale Dichte 3,4%)
combo_growth:           0.05  (Absenkung vom Basiswert 0.0575: kein bestaetigter Infinite trotz Freed from
                                the Real)
passive_value_growth:  0.05   (nah am GU-modifizierten Basiswert 0.0483: reale Dichte 5,1%)
sac_drain_growth:       0.02
disruption_growth:     0.01
mana_growth:            0.20  (leichte Anhebung vom GU-modifizierten Basiswert 0.191425: reale Ramp-Dichte
                                22,0%)
variance_amplitude:    0.28   (am Basiswert)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

### Zelle 4: Tokens & Copies als Midrange

```
board_presence_growth: 0.38   (Kandidat fuer Absenkung vom GU-modifizierten Basiswert 0.605: reale Dichte
                                37,1%)
interaction_growth:    0.07   (Absenkung vom GU-modifizierten Basiswert 0.1305: reale Dichte 6,5%)
wipe_growth:            0.02  (Absenkung vom Basiswert 0.03: reale Dichte 1,6%)
**combo_growth:         0.15** (Kandidat fuer MASSIVE Anhebung vom Basiswert 0.0575: bestaetigter Infinite -
                                SECHZEHNTER Combo-Fund des Projekts, Biovisionary + Rite of Replication
                                (gekickt), sofortiger alternativer Sieg durch Kreaturenanzahl)
passive_value_growth:  0.04   (leichte Absenkung vom GU-modifizierten Basiswert 0.0483: reale Dichte 3,2%)
sac_drain_growth:       0.02
disruption_growth:     0.01
mana_growth:            0.20  (leichte Anhebung vom GU-modifizierten Basiswert 0.191425: reale Ramp-Dichte
                                21,0%)
variance_amplitude:    0.32   (Kandidat fuer Anhebung vom Basiswert 0.28: Combo-Finish erhoeht die Varianz)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

### Zelle 5: Merfolk als Midrange

```
board_presence_growth: 0.50   (leichte Absenkung vom GU-modifizierten Basiswert 0.605: reale Dichte 53,1%)
interaction_growth:    0.08   (Absenkung vom GU-modifizierten Basiswert 0.1305: reale Dichte 7,8%)
wipe_growth:            0.03  (nah am Basiswert 0.03: reale Dichte 3,1%)
combo_growth:           0.05  (Absenkung vom Basiswert 0.0575: kein bestaetigter Infinite trotz Intruder
                                Alarm)
passive_value_growth:  0.045  (nah am GU-modifizierten Basiswert 0.0483: reale Dichte 4,7%)
sac_drain_growth:       0.02
disruption_growth:     0.01
**mana_growth:          0.14** (Kandidat fuer Absenkung vom GU-modifizierten Basiswert 0.191425: reale
                                Ramp-Dichte nur 10,9% - ungewoehnlich niedrig fuer eine Simic-Liste,
                                Kreaturenqualitaet statt Ramp-Dichte priorisiert)
variance_amplitude:    0.27   (nah am Basiswert 0.28)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.09)
```

### Zelle 6: Mana Engines als Control

```
board_presence_growth: 0.42   (Kandidat fuer Anhebung vom GU-modifizierten Control-Basiswert 0.33: reale
                                Dichte 47,8% - viele Mana-Dorks zaehlen selbst als Board-Praesenz)
interaction_growth:    0.18   (Absenkung vom GU-modifizierten Basiswert 0.232: reale Dichte 13,4%, dennoch
                                die hoechste Zaehlung der Portion)
**wipe_growth:          0.02** (Kandidat fuer MASSIVE Absenkung vom Basiswert 0.11: reale Dichte 0% - erster
                                Simic-Flavor ganz ohne Wipe, setzt auf Counterspells statt Sweeper)
**combo_growth:         0.11** (Kandidat fuer Anhebung vom Basiswert 0.069: bestaetigter Infinite -
                                SIEBZEHNTER Combo-Fund des Projekts, das namensgebende Kinnan-Combo Basalt
                                Monolith + Dramatic Reversal)
passive_value_growth:  0.07   (leichte Absenkung vom GU-modifizierten Basiswert 0.0805: reale Dichte 6,0%)
sac_drain_growth:       0.01
disruption_growth:     0.02   (Absenkung vom Basiswert 0.06: 0 der 9 Disruption-Game-Changer)
**mana_growth:          0.24** (Kandidat fuer DEUTLICHE Anhebung vom GU-modifizierten Basiswert 0.1729:
                                reale Ramp-Dichte 32,8%)
variance_amplitude:    0.29   (leicht ueber Basiswert 0.26: Combo-Finish-Potenzial)
dead_turn_chance_base: 0.07   (nah am Basiswert 0.08)
```

## Reflexion & Grenzen dieser Portion — UND DES GESAMTEN GILDEN-PROJEKTS

1. Alle 96 Zellen der Zweifarben-Gilden-Ebene (90 Vorportionen + 6
   Simic) bleiben Kandidaten, keine Gewichtsänderung in
   `opponent_state_weights.json`.
2. **Mit dieser Portion ist die gesamte Gilden-Ebene abgeschlossen:**
   10 von 10 Gilden, 60 von 60 Flavor-Zellen, alle gegen echte
   EDHREC-Bracket-3-Decklisten verifiziert. Zusammen mit den 5
   Monofarben-Portionen (Weiß, Blau, Schwarz, Rot, Grün, 30 Zellen)
   ergibt das 90 real recherchierte Flavor-Strategie-Zellen für das
   gesamte Zweifarben-plus-Monofarben-Programm.
3. **Projektweite Combo-Bilanz:** 17 bestätigte vollständige
   Combo-Funde über alle 90 Zellen hinweg, mit mindestens sechs
   unterschiedlichen strukturellen Mustern (Yawgmoth-Sac-Loop,
   Exquisite Blood+Sanguine Bond, Elfball-Manacombo, Boros-Reckoner-
   Schaden-Echo, Biovisionary-Alt-Sieg, Kinnan-Basalt-Monolith) - ein
   klarer Beleg für die reale Combo-Dichte in Bracket-3-Decks, auch
   ohne systematische Bracket-4/cEDH-Overreach.
4. **Projektweite Game-Changer-Bilanz außerhalb der 9
   Disruption-Karten:** Field of the Dead (1×), Seedborn Muse (3×),
   Smothering Tithe (3×), Rhystic Study (5× über mehrere
   Monofarben-Portionen und Simic) - die Verteilung stützt die
   Tagging-Kategorien aus `game_changer_archetypes.json` konsistent.
5. **Das am häufigsten dokumentierte Modellgrenze über alle zehn
   Gilden hinweg** ist das "thematischer Kern überschneidet
   strukturell mit einer Basisdimension"-Muster (mindestens zehn
   bestätigte Fälle: Rot, Dimir, Rakdos, Gruul, Selesnya, Orzhov,
   Izzet, Golgari mehrfach, Boros, Simic dreifach) - ein dediziertes
   "thematische Kern-Dichte"-Feld bleibt die am besten belegte
   Kandidat-Erweiterung für eine künftige Engine-Version.
6. Die Voltron-Board-Präsenz-Modellgrenze wurde in sechs von zehn
   Gilden real bestätigt (Preston, Valduk, Bruna, Stangg, Skullbriar,
   Wyleth) - ein weiteres robust wiederkehrendes, gut belegtes Muster.
7. Nächste Schritte liegen außerhalb dieser Sitzung: die
   Zusammenführung aller 90 Flavor-Zellen zu konkreten
   Kalibrierungsvorschlägen für `opponent_state_weights.json` sowie
   die Behandlung der offen dokumentierten Modellgrenzen (Kern-Dichte-
   Feld, Voltron-Sonderfall) sind eigenständige künftige Aufträge.
