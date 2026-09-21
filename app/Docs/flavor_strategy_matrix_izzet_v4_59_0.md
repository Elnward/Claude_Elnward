# Flavor-Strategie-Matrix — Izzet (UR), Gilden-Portion 7 von 10 (v4.59.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Siebte Gilden-Portion, direkt im Anschluss an Orzhov (v4.58.0), gleicher
Sitzungsdurchgang. Dieselbe Methodik: Dokument als Recherche-Gerüst,
alle Werte aus echten EDHREC-Bracket-3-Listen.

Vollständige Rohdaten: `Docs/scratch/izzet_flavor_pilot_raw.md`.

## Kombinierte UR-Farbmodifikatoren

| Dimension | U | R | UR kombiniert |
|---|---|---|---|
| mana_growth | 0.95 | 1.10 | **1.045** (multiplikativ) |
| interaction_availability | 1.45 | – | **1.45** |
| combo_finish_readiness | 1.15 | – | **1.15** |
| passive_value_growth | 1.40 | – | **1.40** |
| disruption_growth | 1.20 | – | **1.20** |
| board_presence | – | 1.15 | **1.15** |
| dead_turn_chance | – | 0.90 | **0.90** |
| wipe_readiness | – | – | **1.0** (keine Modifikation) |
| sac_drain_growth | – | – | **1.0** (keine Modifikation) |

**Izzet kombiniert nur auf EINER Dimension (mana_growth) echt
multiplikativ — die bisher am nächsten an Neutralität liegende
Farbkombination des Projekts: Blaus leichte Mana-Bremse (0,95×) und
Rots leichter Mana-Bonus (1,10×) heben sich fast auf (1,045×).** Auf
allen anderen sechs Dimensionen liefert nur eine der beiden Farben
einen Modifikator (Union statt Produkt), auf zwei Dimensionen (wipe,
sac_drain) liefert keine der beiden Farben überhaupt einen Modifikator.
Dieses Muster ähnelt strukturell Rakdos (0 von 7 überlappend), ist
aber nicht identisch: Rakdos hatte gar keine Überlappung, Izzet hat
genau eine (mana_growth) — real bestätigt durch den Extremwert der
Ramp-Dichte-Varianz zwischen den sechs Flavors (7,8% bis 16,7%), die
trotz nahezu neutralem Modifikator stark auf reale Deckbau-Unterschiede
statt auf Farbeinfluss zurückgeht.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption | Eigener Kern |
|---|---|---|---|---|---|---|---|---|---|
| Spellslinger & Magecraft (Mizzix) | **16,7%** (Projekt-Tiefstwert) | 7,6% | 1,5% | 9,1%+Rituale | 1,5% | 0 | 0% | 0% | Spellslinger-Kern 19,7%, Spell-Dichte 65,2% (Projekt-Höchstwert) |
| Artefakte & Thopters (Jhoira) | 33,3% | 6,1% | 1,5% | 16,7% | 3,0% | 0 | 0% | 0% | Artefakte-Kern 43,9% (77,3% Artefakt-Bezug gesamt) |
| Wheels & Draw-Punisher (The Locust God) | 25,4% | 11,1% | 1,6% | 11,1% | 4,8% | 0 | 3,2% | 0% | Wheel-Kern 20,6% |
| Spell Copy (Melek) | 20,3% (2.-niedrigster Wert) | 4,7% | 1,6% | 7,8%+Rituale | 0% | 0 | 0% | 0% | Spell-Copy-Kern 7,8% (kombiniert 28,1%) |
| Dragons & Big Spells (Lozhan) | 45,2% | 8,1% | 1,6% | 8,1%+Rituale | 0% | 0 | 0% | 0% | **Dragons/Typal-Kern 58,1%** (neuer Projekt-Höchstwert) |
| Coin Flips & Chaos (Yusri) | 29,2% | 10,8% | 3,1% | 9,2% | 1,5% | Synergiepaar (nicht gezählt) | 0% | 0% | Coin-Flip/Chaos-Kern 36,9% |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Neuer Projekt-Tiefstwert Board-Präsenz: Mizzix mit 16,7%** —
   unterbietet den bisherigen Tiefstwert Eriette/Orzhov (26,6%)
   deutlich. Spellslinger-Decks sind strukturell die
   kreaturenärmste Deck-Kategorie des Projekts (Mizzix und Melek
   beide unter 21%).
2. **Kein einziger vollständig bestätigter Combo-Fund in der
   gesamten Izzet-Portion** — dritte Gilde ohne bestätigten Infinite
   (nach Gruul, Selesnya), trotz mehrfacher "Combo"-Tags auf EDHREC
   und eines prominenten realen Synergiepaars (Okaun+Zndrsplt bei
   Yusri) ohne identifizierten dritten Baustein in der
   Bracket-3-Liste — bewusst NICHT als bestätigter Fund gezählt.
3. **Neuer Projekt-Höchstwert Dragons/Typal-Dichte:** Lozhan mit
   58,1% (übertrifft Atarka/Gruul mit 39,7% deutlich).
4. **Extremwert Spell-Dichte:** bei Mizzix sind 65,2% aller
   Nicht-Land-Karten Instants/Sorceries — höchster Wert des
   gesamten Projekts.
5. **Nahezu neutraler Farbmodifikator real bestätigt:** die
   kombinierte UR-Mana-Growth-Modifikation (1,045×) ist die bisher
   am nächsten an Neutralität liegende Farbkombination — die
   beobachtete Ramp-Dichte-Streuung (7,8%–16,7%) über die sechs
   Flavors hinweg geht dementsprechend überwiegend auf reale
   Deckbau-Unterschiede statt auf Farbeinfluss zurück.

## Die Matrix (Izzet)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Spellslinger & Magecraft | – | – | – | **✓ (Zelle 1)** | – |
| Artefakte & Thopters | – | – | **✓ (Zelle 2)** | – | – |
| Wheels & Draw-Punisher | – | – | – | **✓ (Zelle 3)** | – |
| Spell Copy | – | – | – | **✓ (Zelle 4)** | – |
| Dragons & Big Spells | – | – | **✓ (Zelle 5)** | – | – |
| Coin Flips & Chaos | – | – | **✓ (Zelle 6)** | – | – |

### Zelle 1: Spellslinger & Magecraft als Control

```
board_presence_growth: 0.16   (Kandidat fuer DEUTLICHE Absenkung vom UR-modifizierten Basiswert 0.345: reale
                                Dichte nur 16,7% - NEUER PROJEKT-TIEFSTWERT, unterbietet Eriette 26,6%,
                                Stangg 22,7%, Sythis 32,8%)
interaction_growth:    0.09   (Absenkung vom UR-modifizierten Basiswert 0.232: reale Dichte 7,6%)
wipe_growth:            0.02  (Absenkung vom Basiswert 0.11: reale Dichte nur 1,5%)
**combo_growth:         0.09** (Kandidat fuer Anhebung vom UR-modifizierten Basiswert 0.069: kein bestaetigter
                                Infinite trotz "Combo 33"-Tag, aber dichter Spellslinger/Magecraft-Kern
                                (19,7%) plus extreme Spell-Dichte (65,2%, Projekt-Hoechstwert) wirken
                                funktional als Payoff-Engine - hilfsweise auf combo_growth gemappt, siehe
                                Reflexion)
passive_value_growth:  0.02   (Absenkung vom UR-modifizierten Basiswert 0.07: reale Dichte nur 1,5%)
sac_drain_growth:       0.0   (keine Opfer/Drain-Elemente in dieser Liste)
disruption_growth:     0.01   (Absenkung vom UR-modifizierten Basiswert 0.06: 0 der 9 Game-Changer)
mana_growth:            0.11  (Absenkung vom UR-modifizierten Basiswert 0.1463: reale Ramp-Dichte 9,1%,
                                zusaetzlich gestuetzt durch mehrere Rituale separat)
variance_amplitude:    0.34   (ueber Basiswert 0.26: hoher Spontanzauber-Anteil (65,2%) erhoeht die Varianz
                                strukturell)
dead_turn_chance_base: 0.06   (Absenkung vom UR-modifizierten Basiswert 0.072: R-Mana-Bonus und viele billige
                                Spells reduzieren tote Zuege)
```

### Zelle 2: Artefakte & Thopters als Midrange

```
board_presence_growth: 0.36   (Kandidat fuer Absenkung vom UR-modifizierten Basiswert 0.6325: reale Dichte
                                33,3%)
interaction_growth:    0.07   (Absenkung vom UR-modifizierten Basiswert 0.1305: reale Dichte 6,1%)
wipe_growth:            0.025 (nah am Basiswert 0.03: reale Dichte 1,5%)
combo_growth:           0.05  (nah am UR-modifizierten Basiswert 0.0575: kein bestaetigter Infinite - Urza,
                                Lord High Artificer + Mystic Forge starke Engine, aber kein garantierter
                                2-Karten-Loop in dieser Liste)
passive_value_growth:  0.04   (nah am UR-modifizierten Basiswert 0.042: reale Dichte 3,0%)
sac_drain_growth:       0.0   (keine Opfer/Drain-Elemente)
disruption_growth:     0.01   (Absenkung vom UR-modifizierten Basiswert 0.018: 0 der 9 Game-Changer)
**mana_growth:          0.19** (Kandidat fuer DEUTLICHE Anhebung vom UR-modifizierten Basiswert 0.16198:
                                reale Ramp-Dichte 16,7%, zusaetzlich extrem dichter Artefakte-Kern (43,9%,
                                77,3% Artefakt-Bezug insgesamt) wirkt strukturell wie zusaetzlicher
                                Mana-/Kostenreduktions-Verstaerker - hilfsweise mitgemappt, siehe Reflexion)
variance_amplitude:    0.27   (nah am Basiswert 0.28)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.081)
```

### Zelle 3: Wheels & Draw-Punisher als Control

```
board_presence_growth: 0.27   (Absenkung vom UR-modifizierten Basiswert 0.345: reale Dichte 25,4%)
interaction_growth:    0.15   (Kandidat fuer Absenkung vom UR-modifizierten Basiswert 0.232: reale Dichte
                                11,1%)
wipe_growth:            0.03  (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.11: reale Dichte nur 1,6%)
combo_growth:           0.05  (leichte Absenkung vom UR-modifizierten Basiswert 0.069: kein bestaetigter
                                Infinite - Laboratory Maniac + Wheel-Effekte ist alternative
                                Wincondition-Linie, kein garantierter Loop, nicht mitgezaehlt)
**passive_value_growth: 0.09** (Kandidat fuer Anhebung vom UR-modifizierten Basiswert 0.07: reale klassische
                                Dichte 4,8%, aber dichter Wheel/Draw-Punisher-Kern (20,6%) wirkt funktional
                                wie zusaetzliche Card-Advantage-Engine - hilfsweise mitgemappt, siehe
                                Reflexion)
sac_drain_growth:       0.04  (Anhebung vom Basiswert 0.01: reale Dichte 3,2%, Ashnod's Altar+Goblin
                                Bombardment ohne dedizierte Payoffs in dieser Liste)
disruption_growth:     0.01   (Absenkung vom UR-modifizierten Basiswert 0.06: 0 der 9 Game-Changer)
mana_growth:            0.13  (leichte Absenkung vom UR-modifizierten Basiswert 0.1463: reale Ramp-Dichte
                                11,1%)
variance_amplitude:    0.30   (ueber Basiswert 0.26: symmetrische Wheel-Effekte treffen alle Spieler,
                                erhoehen die Varianz strukturell)
dead_turn_chance_base: 0.07   (nah am Basiswert 0.072)
```

### Zelle 4: Spell Copy als Control

```
**board_presence_growth: 0.20** (Kandidat fuer DEUTLICHE Absenkung vom UR-modifizierten Basiswert 0.345:
                                reale Dichte 20,3% - zweitniedrigster Wert des Projekts nach Mizzix (16,7%))
interaction_growth:    0.06   (Kandidat fuer DEUTLICHE Absenkung vom UR-modifizierten Basiswert 0.232: reale
                                Dichte 4,7%)
wipe_growth:            0.02  (Absenkung vom Basiswert 0.11: reale Dichte nur 1,6%)
**combo_growth:         0.08** (Kandidat fuer Anhebung vom UR-modifizierten Basiswert 0.069: kein bestaetigter
                                Infinite, aber dichter Spell-Copy-Kern (7,8%) gestuetzt durch breiten
                                Spellslinger/Magecraft-Kern (kombiniert 28,1%) wirkt funktional als
                                Payoff-Engine - hilfsweise auf combo_growth gemappt, analog Zelle 1 (Mizzix))
passive_value_growth:  0.01   (Kandidat fuer DEUTLICHE Absenkung vom UR-modifizierten Basiswert 0.07: 0
                                dedizierte Value-Engines in dieser Liste)
sac_drain_growth:       0.0
disruption_growth:     0.01   (Absenkung vom UR-modifizierten Basiswert 0.06: 0 der 9 Game-Changer)
mana_growth:            0.09  (Kandidat fuer DEUTLICHE Absenkung vom UR-modifizierten Basiswert 0.1463: reale
                                Ramp-Dichte nur 7,8%, trotz zusaetzlicher Rituale separat)
variance_amplitude:    0.32   (ueber Basiswert 0.26: Spell-Copy-Effekte erhoehen die Varianz strukturell
                                stark)
dead_turn_chance_base: 0.06   (Absenkung vom Basiswert 0.072)
```

### Zelle 5: Dragons & Big Spells als Midrange

```
board_presence_growth: 0.48   (Kandidat fuer Absenkung vom UR-modifizierten Basiswert 0.6325: reale Dichte
                                45,2% - deckt sich exakt mit den 28 Dragon-Kreaturen des Dragons/Typal-Kerns)
interaction_growth:    0.09   (Absenkung vom UR-modifizierten Basiswert 0.1305: reale Dichte 8,1%)
wipe_growth:            0.025 (nah am Basiswert 0.03: reale Dichte 1,6%)
combo_growth:           0.04  (Absenkung vom UR-modifizierten Basiswert 0.0575: kein bestaetigter Infinite)
passive_value_growth:  0.03   (Absenkung vom UR-modifizierten Basiswert 0.042: 0 dedizierte Value-Engines im
                                klassischen Sinn - Typal-Support wirkt stattdessen auf mana_growth, siehe
                                unten)
**mana_growth:          0.17** (Kandidat fuer Anhebung vom UR-modifizierten Basiswert 0.16198: reale
                                Ramp-Dichte 8,1% plus separate Rituale, zusaetzlich gestuetzt durch den
                                NEUEN PROJEKT-HOECHSTWERT Dragons/Typal-Kern (58,1%, uebertrifft Atarka/Gruul
                                39,7%), dessen 8 Typal-Enabler teils Kostenreduktion bieten (Dragonlord's
                                Servant, Crucible of Fire) - hilfsweise mitgemappt, siehe Reflexion)
variance_amplitude:    0.29   (leicht ueber Basiswert 0.28: hohe Einzelkarten-Wirkstaerke der Big-Spells-
                                Dragons)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.081)
```

### Zelle 6: Coin Flips & Chaos als Midrange

```
board_presence_growth: 0.31   (Kandidat fuer DEUTLICHE Absenkung vom UR-modifizierten Basiswert 0.6325: reale
                                Dichte 29,2%)
interaction_growth:    0.11   (leichte Absenkung vom UR-modifizierten Basiswert 0.1305: reale Dichte 10,8%)
wipe_growth:            0.03  (nah am Basiswert 0.03: reale Dichte 3,1%)
**combo_growth:         0.08** (Kandidat fuer Anhebung vom UR-modifizierten Basiswert 0.0575: Okaun, Eye of
                                Chaos + Zndrsplt, Eye of Wisdom real GEMEINSAM vorhanden - bekanntestes
                                Coin-Flip-Synergiepaar des Formats, aber ohne identifizierten dritten freien
                                Wiederholungs-Baustein in dieser Liste NICHT als vollstaendiger Combo-Fund
                                gezaehlt; zusaetzlich sehr dichter Coin-Flip/Chaos-Kern (36,9%) wirkt als
                                Payoff-Engine - beides hilfsweise auf combo_growth gemappt, siehe Reflexion)
passive_value_growth:  0.03   (Absenkung vom UR-modifizierten Basiswert 0.042: reale Dichte 1,5%)
sac_drain_growth:       0.0
disruption_growth:     0.01   (Absenkung vom UR-modifizierten Basiswert 0.018: 0 der 9 Game-Changer)
mana_growth:            0.14  (leichte Absenkung vom UR-modifizierten Basiswert 0.16198: reale Ramp-Dichte
                                9,2%)
**variance_amplitude:   0.35** (Kandidat fuer DEUTLICHE Anhebung vom Basiswert 0.28: Coin-Flip/Chaos-Mechanik
                                ist strukturell die varianzreichste Dimension des gesamten Projekts)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.081)
```

## Reflexion & Grenzen dieser Portion

1. Alle 78 bisherigen Zellen (72 Vorportionen + 6 Izzet) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Neuer Projekt-Tiefstwert Board-Präsenz:** Mizzix mit 16,7% —
   unterbietet Eriette/Orzhov (26,6%) deutlich. Zusammen mit Melek
   (20,3%, zweitniedrigster Wert) bestätigt sich Spellslinger als
   strukturell kreaturenärmste Deck-Kategorie des Projekts.
3. **Dritte Gilde ohne bestätigten Combo-Fund** (nach Gruul,
   Selesnya) — bewusst methodische Zurückhaltung beim
   Okaun+Zndrsplt-Synergiepaar bei Yusri: prominent vorhanden, aber
   ohne identifizierten dritten freien Wiederholungs-Baustein in
   dieser spezifischen Bracket-3-Liste nicht als vollständiger
   Infinite gezählt, konsistent mit der bereits mehrfach gezeigten
   Zurückhaltung (Anje, Prosper, Araumi in früheren Portionen).
4. **Wiederkehrende Modellgrenze, vier neue Fälle in einer Portion:**
   der Spellslinger/Magecraft-Kern (Mizzix, Melek), der
   Artefakte-Kern (Jhoira), der Wheel-Kern (The Locust God), der
   Dragons/Typal-Kern (Lozhan) und der Coin-Flip/Chaos-Kern (Yusri)
   lassen sich alle nicht sauber einem bestehenden Feld zuordnen —
   je nach thematischer Funktion hilfsweise auf combo_growth
   (Payoff-Engines ohne bestätigten Infinite: Mizzix, Melek, Yusri),
   mana_growth (Kostenreduktions-/Ramp-Verstärkung: Jhoira, Lozhan)
   oder passive_value_growth (Card-Advantage-Ersatz: The Locust God)
   gemappt. Die wachsende Liste dieser Fälle (Rot, Dimir, Rakdos,
   Gruul, Selesnya, Orzhov, jetzt sechsfach allein bei Izzet) stützt
   den bereits mehrfach dokumentierten Bedarf für ein dediziertes
   "thematische Kern-Dichte"-Feld besonders deutlich.
5. **Nahezu neutraler Farbmodifikator real bestätigt:** UR
   kombiniert nur auf mana_growth (1,045×) — die am wenigsten
   ausgeprägte Farbkombinations-Wechselwirkung des Projekts bisher.
   Die real beobachtete Ramp-Dichte-Streuung (7,8% bis 16,7%) über
   die sechs Flavors hinweg bestätigt, dass hier reale
   Deckbau-Entscheidungen stärker wirken als der Farbmodifikator.
6. Fortsetzung folgt unmittelbar mit den übrigen 3 Gilden (Golgari,
   Boros, Simic) — derselbe Sitzungsdurchgang, wie vom Nutzer
   gewünscht ("Arbeite bitte weiter").
