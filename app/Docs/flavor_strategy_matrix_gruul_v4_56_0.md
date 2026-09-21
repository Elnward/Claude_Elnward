# Flavor-Strategie-Matrix — Gruul (RG), Gilden-Portion 4 von 10 (v4.56.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Vierte Gilden-Portion, direkt im Anschluss an Rakdos (v4.55.0), gleicher
Sitzungsdurchgang. Dieselbe Methodik: Dokument als Recherche-Gerüst,
alle Werte aus echten EDHREC-Bracket-3-Listen.

Vollständige Rohdaten: `Docs/scratch/gruul_flavor_pilot_raw.md`.

## Kombinierte RG-Farbmodifikatoren

| Dimension | R | G | RG kombiniert |
|---|---|---|---|
| board_presence | 1.15 | 1.10 | **1.265** (multiplikativ, PROJEKT-HÖCHSTWERT) |
| mana_growth | 1.10 | 1.30 | **1.43** (multiplikativ, PROJEKT-HÖCHSTWERT) |
| passive_value_growth | – | 1.15 | **1.15** |
| dead_turn_chance | 0.90 | – | **0.90** |

**Gruul kombiniert auf zwei Dimensionen (board_presence, mana_growth)
— wie Azorius (2 von 7), aber mit den bisher höchsten Einzelwerten des
Projekts auf beiden Feldern.** Real bestätigt: Xenagos (23,4% Ramp)
und Omnath (39 Länder + 20,0% klassische Ramp + 31,7% Landfall-Kern)
stützen den 1,43×-Mana-Multiplikator direkt; die durchgängig hohen
Board-Präsenz-Werte bei Xenagos (50,0%), Halana & Alena (49,2%) und
Tovolar (47,7%) stützen den 1,265×-Board-Multiplikator.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Power Matters (Xenagos) | **50,0%** | 3,1% | 1,6% | **23,4%** | 7,8% | 0 | 0% | 0% |
| Lands & Landfall (Omnath) | 38,3% | 3,3% | 1,7% | 20,0% (+Landfall-Kern 31,7%) | 8,3% | 0 | 3,3% | 0% |
| Dragons (Atarka) | 42,9% | 1,6% | 3,2% | 17,5% | 3,2% | 0 | 0% | 0% |
| +1/+1-Counter (Halana & Alena) | 49,2% | 3,1% | 1,5% | 16,9% | 4,6% | 0 | 0% | 0% |
| Auren & Equipment (Stangg) | **22,7%** (Voltron) | 3,0% | 1,5% | 16,7% | 3,0% | 0 | 0% | 0% |
| Werewolves & Wolves (Tovolar) | 47,7% | 4,6% | 1,5% | 12,3% | 1,5% | 0 | 0% | 0% |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Vierte Bestätigung der Voltron-Board-Präsenz-Limitation:** Stangg
   mit 22,7% — niedrigster Wert der gesamten Rot/Grün-Ebene, nach
   Preston (Weiß, v4.48.0), Valduk (Rot, v4.51.0), Bruna (Azorius,
   v4.53.0).
2. **Fünf von sechs Flavors real zu aggro eingeordnet** — die
   einseitigste Verteilung einer Gilden-Portion bisher, aber
   konsistent mit der Dokument-Beschreibung von Gruul als der
   schnellsten Zweifarb-Gilde.
3. **Erste Gilde des Projekts ohne einen einzigen bestätigten
   Combo-Fund** in der gesamten Portion.
4. **Durchgängig niedrigste kombinierte Interaktions-Werte des
   Projekts:** 1,6%–4,6% über alle 6 Flavors, deutlich unter jedem
   bisherigen Durchschnitt.
5. **Neue Projekt-Höchstwerte bei beiden kombinierten
   RG-Farbmodifikatoren:** board_presence 1,265× und mana_growth
   1,43× übertreffen alle bisherigen Gilden-Kombinationen (WU, UB,
   BR) auf ihren jeweils stärksten Feldern.

## Die Matrix (Gruul)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Power Matters | – | **✓ (Zelle 1)** | – | – | – |
| Lands & Landfall | – | – | **✓ (Zelle 2)** | – | – |
| Dragons | – | **✓ (Zelle 3)** | – | – | – |
| +1/+1-Counter & Modified | – | **✓ (Zelle 4)** | – | – | – |
| Auren & Equipment | – | **✓ (Zelle 5)** | – | – | – |
| Werewolves & Wolves | – | **✓ (Zelle 6)** | – | – | – |

### Zelle 1: Power Matters als Aggro

```
board_presence_growth: 0.66   (Kandidat fuer DEUTLICHE Absenkung vom RG-modifizierten Basiswert 1.075: reale
                                Dichte 50,0%)
interaction_growth:    0.035  (nah am Basiswert 0.035: reale Dichte 3,1%)
wipe_growth:            0.015 (leicht ueber 0.0: reale Dichte 1,6%)
combo_growth:           0.02  (Kandidat fuer Absenkung vom Basiswert 0.03: kein bestaetigter Infinite)
**passive_value_growth: 0.05** (Kandidat fuer DEUTLICHE Anhebung vom RG-modifizierten Basiswert 0.0115: reale
                                Dichte 7,8% - Beast Whisperer/Greater Good/The Great Henge/Up the Beanstalk)
sac_drain_growth:       0.0
disruption_growth:     0.005
**mana_growth:          0.24** (nah am RG-modifizierten Basiswert 0.2431: reale Dichte 23,4%)
variance_amplitude:    0.32
dead_turn_chance_base: 0.08
```

### Zelle 2: Lands & Landfall als Midrange

```
board_presence_growth: 0.42   (Kandidat fuer Absenkung vom RG-modifizierten Basiswert 0.6958: reale Dichte 38,3%)
interaction_growth:    0.04   (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.09: reale Dichte nur 3,3%)
wipe_growth:            0.02  (Kandidat fuer Absenkung vom Basiswert 0.03: reale Dichte 1,7%)
combo_growth:           0.03  (kein bestaetigter Infinite trotz dichtem Land-Recursion-Paket)
passive_value_growth:  0.06   (Kandidat fuer Anhebung vom RG-modifizierten Basiswert 0.0345: reale Dichte 8,3%)
sac_drain_growth:       0.03  (nah am Basiswert 0.04: reale Dichte 3,3%, ohne dedizierten Payoff)
disruption_growth:     0.01
**mana_growth:          0.30** (Kandidat fuer DEUTLICHE Anhebung vom RG-modifizierten Basiswert 0.2217: klassische
                                Ramp-Dichte 20,0%, aber Landfall-Kern (31,7%) plus 39 statt 35-37 Laender
                                erzeugen strukturell mehr effektive Mana-Verfuegbarkeit als jede bisherige
                                Liste des Projekts, hilfsweise hier zusaetzlich abgebildet, siehe Reflexion)
variance_amplitude:    0.30   (ueber Basiswert 0.28 - Scapeshift/Splendid Reclamation als Explosivzuege)
dead_turn_chance_base: 0.07
```

### Zelle 3: Dragons als Aggro

```
board_presence_growth: 0.58   (Kandidat fuer DEUTLICHE Absenkung vom RG-modifizierten Basiswert 1.075: reale
                                Dichte 42,9%)
interaction_growth:    0.02   (Kandidat fuer Absenkung vom Basiswert 0.035: reale Dichte nur 1,6%)
wipe_growth:            0.03  (Kandidat fuer Anhebung vom Basiswert 0.0: reale Dichte 3,2%, Blasphemous
                                Act/Chain Reaction real vorhanden)
combo_growth:           0.02  (kein bestaetigter Infinite)
passive_value_growth:  0.02   (leicht ueber dem RG-modifizierten Basiswert 0.0115: reale Dichte 3,2%)
sac_drain_growth:       0.0
disruption_growth:     0.005
mana_growth:            0.19  (Kandidat fuer Absenkung vom RG-modifizierten Basiswert 0.2431: reale Dichte 17,5%)
variance_amplitude:    0.33   (ueber Basiswert 0.30 - hohe Kurve durch viele 6-8-Mana-Dragons)
dead_turn_chance_base: 0.11   (ueber Basiswert 0.09 - teure Kurve riskiert tote Zuege ohne fruehe Rampe)
```

### Zelle 4: +1/+1-Counter & Modified als Aggro

```
board_presence_growth: 0.65   (Kandidat fuer Absenkung vom RG-modifizierten Basiswert 1.075: reale Dichte 49,2%)
interaction_growth:    0.035  (nah am Basiswert: reale Dichte 3,1%)
wipe_growth:            0.015 (leicht ueber 0.0: reale Dichte 1,5%)
combo_growth:           0.02  (kein bestaetigter Infinite - Forgotten Ancient/Kami of Whispered Hopes sind
                                Value-Engines ohne Loop-Partner in dieser Liste)
passive_value_growth:  0.03   (Kandidat fuer Anhebung vom RG-modifizierten Basiswert 0.0115: reale Dichte 4,6%)
sac_drain_growth:       0.0
disruption_growth:     0.005
mana_growth:            0.18  (Kandidat fuer Absenkung vom RG-modifizierten Basiswert 0.2431: reale Dichte 16,9%)
variance_amplitude:    0.29
dead_turn_chance_base: 0.08
```

### Zelle 5: Auren & Equipment als Aggro (Voltron)

```
**board_presence_growth: 0.28** (Kandidat fuer EXTREME Absenkung vom RG-modifizierten Basiswert 1.075: reale
                                Dichte nur 22,7% - vierte Bestaetigung der Voltron-Board-Praesenz-Limitation,
                                das Deck konzentriert Wert auf sehr wenige Kreaturen statt Breite)
interaction_growth:    0.03   (nah am Basiswert: reale Dichte 3,0%)
wipe_growth:            0.015 (leicht ueber 0.0: reale Dichte 1,5%)
combo_growth:           0.02  (kein bestaetigter Infinite)
passive_value_growth:  0.02   (leicht ueber dem RG-modifizierten Basiswert 0.0115: reale Dichte 3,0%)
sac_drain_growth:       0.0
disruption_growth:     0.005
mana_growth:            0.18  (Kandidat fuer Absenkung vom RG-modifizierten Basiswert 0.2431: reale Dichte 16,7%)
**variance_amplitude:   0.35** (deutlich ueber Basiswert 0.30 - klassisches Voltron-Risiko: das Deck steht und
                                faellt mit einem einzigen ausgeruesteten Angreifer)
dead_turn_chance_base: 0.13   (deutlich ueber Basiswert 0.09 - ohne den einen Schluessel-Angreifer oder bei
                                fehlendem Schutz drohen tote Zuege)
```

### Zelle 6: Werewolves & Wolves als Aggro

```
board_presence_growth: 0.64   (Kandidat fuer Absenkung vom RG-modifizierten Basiswert 1.075: reale Dichte 47,7%)
interaction_growth:    0.045  (leicht ueber Basiswert 0.035: reale Dichte 4,6%)
wipe_growth:            0.015 (leicht ueber 0.0: reale Dichte 1,5%)
combo_growth:           0.02  (kein bestaetigter Infinite)
passive_value_growth:  0.015  (nah am RG-modifizierten Basiswert 0.0115: reale Dichte 1,5%)
sac_drain_growth:       0.0
disruption_growth:     0.005
**mana_growth:          0.15** (Kandidat fuer DEUTLICHE Absenkung vom RG-modifizierten Basiswert 0.2431: reale
                                Dichte nur 12,3% - niedrigster Ramp-Wert der gesamten Gruul-Portion)
variance_amplitude:    0.31   (ueber Basiswert 0.30 - Day/Night-Wechsel erzeugt zusaetzliche Varianz)
dead_turn_chance_base: 0.09
```

## Reflexion & Grenzen dieser Portion

1. Alle 60 bisherigen Zellen (54 Vorportionen + 6 Gruul) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Erste Gilde ohne einen einzigen bestätigten Combo-Fund** — nach
   Azorius (1), Dimir (1) und Rakdos (2) die erste Nullrunde. Das
   Ergebnis spiegelt eher die reale Kartenpool-Verteilung wider als
   eine Methodik-Schwäche: Gruul ist im echten EDH-Metagame die
   Gilde mit der geringsten Combo-Dichte unter den zehn Paaren.
3. **Fünf von sechs Flavors als aggro klassifiziert** — die
   einseitigste Verteilung einer Gilden-Portion bisher. Dies ist eine
   direkte, reale Konsequenz der Farbidentität (R+G = die zwei
   aggressivsten Einzelfarben-Ramp-Profile des Projekts) und keine
   methodische Verzerrung; die Dichte-Tabelle zeigt trotzdem klare
   quantitative Unterschiede zwischen den fünf aggro-Zellen (Board-
   Präsenz von 22,7% bis 50,0%).
4. **Wiederkehrende Modellgrenze auf fünf von sechs Flavors:**
   Landfall-, Dragons-, Counter-, Voltron- und Werewolf-Kerne (31,7%
   bis 47,7%) bestätigen erneut die bereits in Rot, Dimir und Rakdos
   beobachtete Lücke zwischen dichten thematischen Kartenkernen und
   den zehn bestehenden Engine-Feldern — hier stärker ausgeprägt als
   in jeder bisherigen Portion.
5. Fortsetzung folgt unmittelbar mit den übrigen 6 Gilden (Selesnya,
   Orzhov, Izzet, Golgari, Boros, Simic) — derselbe Sitzungsdurchgang,
   wie vom Nutzer gewünscht ("Arbeite bitte weiter").
