# Flavor-Strategie-Matrix — Rakdos (BR), Gilden-Portion 3 von 10 (v4.55.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Dritte Gilden-Portion, direkt im Anschluss an Dimir (v4.54.0), gleicher
Sitzungsdurchgang. Dieselbe Methodik: Dokument als Recherche-Gerüst,
alle Werte aus echten EDHREC-Bracket-3-Listen.

Vollständige Rohdaten: `Docs/scratch/rakdos_flavor_pilot_raw.md`.

## Kombinierte BR-Farbmodifikatoren

| Dimension | B | R | BR kombiniert |
|---|---|---|---|
| interaction_availability | 1.20 | – | **1.20** |
| wipe_readiness | 1.10 | – | **1.10** |
| combo_finish_readiness | 1.20 | – | **1.20** |
| sac_drain_growth | 1.55 | – | **1.55** |
| passive_value_growth | 1.15 | – | **1.15** |
| disruption_growth | 1.35 | – | **1.35** |
| board_presence | – | 1.15 | **1.15** |
| mana_growth | – | 1.10 | **1.10** |
| dead_turn_chance | – | 0.90 | **0.90** |

**Erster Fund des Projekts ohne jede Feld-Überlappung: B und R
modifizieren laut `opponent_state_weights.json` keine einzige
gemeinsame Dimension.** Die "Kombination" ist hier reine Vereinigung
beider Farb-Sets — auf keinem Feld findet eine tatsächliche
Multiplikation statt. Das steht im Kontrast zu Azorius (WU, 2 von 7
Feldern überlappend) und Dimir (UB, 4 von 7 Feldern überlappend) und
ist selbst ein bemerkenswerter Befund: Schwarz liefert bei Rakdos die
gesamte Interaktions-/Combo-/Drain-/Disruption-Seite, Rot ausschließlich
Board-Präsenz, Mana und Dead-Turn-Reduktion — die beiden Farben
"teilen sich die Arbeit" statt sich gegenseitig zu verstärken.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Sacrifice/Aristocrats (Judith) | **55,4%** | 6,2% | 1,5% | 4,6% | 3,1% | **bestätigt** (Yawgmoth+Skeleton+Altar, 9. Fund) | **16,9%** | 0% |
| Madness & Discard (Anje) | 43,9% | 6,1% | 1,5% | 7,6% | 1,5% | 0 | 0% | 0% |
| Treasure & Exile-Cast (Prosper) | 38,5% | 9,2% | 1,5% | 9,2% | 3,1% | 0 | 7,7% | 0% |
| Group Slug/Burn (Mogis) | 32,8% | 12,5% | **4,7%** | 10,9% | 3,1% | 0 | 6,3% | 0% |
| Demons/Big-Mana (Rakdos, Lord of Riots) | 53,1% | 7,8% | 3,1% | 9,4% | 1,6% | 0 | 3,1% | 0% |
| Vampires (Olivia Voldaren) | 42,9% | 11,1% | 1,6% | 7,9% | 4,8% | **bestätigt** (Exquisite Blood+Sanguine Bond, 10. Fund) | 12,7% | 0% |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Neunter bestätigter vollständiger Combo-Fund des Projekts:**
   Yawgmoth, Thran Physician + kostenlos rekursive Kreatur
   (Reassembling Skeleton/Bloodghast/Nether Traitor) + Ashnod's Altar
   bei Judith — zweite reale Bestätigung des exakt gleichen Musters
   nach dem Mono-Schwarz-Fund (v4.50.0).
2. **Zehnter bestätigter vollständiger Combo-Fund des Projekts:**
   Exquisite Blood + Sanguine Bond bei Olivia Voldaren — erster realer
   Fund dieses klassischen Infinite-Lifegain-Drain-Musters.
3. **Erster Feld-Überlappungs-freier Farbmodifikator-Fund des
   Projekts:** B und R teilen sich auf keiner der neun modifizierten
   Dimensionen — reine additive statt multiplikative Kombination.
4. Judith bestätigt den B-Modifikator sac_drain_growth (1,55×) ein
   zweites Mal unabhängig (16,9%, nahe am Yawgmoth-Rekordwert
   Schwarz 17,2%).
5. Mogis (Group Slug) liefert mit 4,7% den Portions-Höchstwert bei
   Wipes und mit 32,8% den Portions-Tiefstwert bei Board-Präsenz —
   klare Control-Signatur trotz des "Burn"-Tags im Dokument.

## Die Matrix (Rakdos)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Sacrifice/Aristocrats | – | **✓ (Zelle 1)** | – | – | – |
| Madness & Discard | – | – | **✓ (Zelle 2)** | – | – |
| Treasure & Exile-Cast | – | – | **✓ (Zelle 3)** | – | – |
| Group Slug/Burn | – | – | – | **✓ (Zelle 4)** | – |
| Demons/Big-Mana | – | **✓ (Zelle 5)** | – | – | – |
| Vampires | – | – | **✓ (Zelle 6)** | – | – |

### Zelle 1: Sacrifice/Aristocrats als Aggro

```
board_presence_growth: 0.62   (Kandidat fuer DEUTLICHE Absenkung vom BR-modifizierten Basiswert 0.9775: reale
                                Dichte 55,4%, viele Karten sind kleine 0-1-Mana-Recursion-/Utility-Stuecke statt
                                klassischer Beater)
interaction_growth:    0.06   (leicht ueber dem BR-modifizierten Basiswert 0.042: reale Dichte 6,2%)
wipe_growth:            0.015 (leicht ueber 0.0: Blasphemous Act real vorhanden, reale Dichte 1,5%)
combo_growth:           0.10  (Kandidat fuer DEUTLICHE Anhebung vom BR-modifizierten Basiswert 0.036: bestaetigter
                                Infinite - neunter Combo-Fund des Projekts, zweite Bestaetigung des Yawgmoth-Musters)
passive_value_growth:  0.025  (leicht ueber dem BR-modifizierten Basiswert 0.0115: reale Dichte 3,1%)
**sac_drain_growth:     0.15** (Kandidat fuer DEUTLICHE Anhebung vom BR-modifizierten Basiswert 0.0155: reale
                                Dichte 16,9% - nahe am Yawgmoth-Rekordwert Schwarz 17,2%, zweite unabhaengige
                                Bestaetigung des B-Modifikators 1,55x)
disruption_growth:     0.005
mana_growth:            0.09  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.187: reale Dichte nur 4,6%)
variance_amplitude:    0.32   (leicht ueber Basiswert 0.30 - Combo-Finish erhoeht die Varianz)
dead_turn_chance_base: 0.08
```

### Zelle 2: Madness & Discard als Midrange

```
board_presence_growth: 0.50   (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.6325: reale Dichte 43,9%)
interaction_growth:    0.07   (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.108: reale Dichte 6,1%)
wipe_growth:            0.02  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.033: reale Dichte 1,5%)
combo_growth:           0.03  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.06: kein bestaetigter
                                Infinite trotz EDHREC-Tag "Combo 45" in dieser spezifischen Liste)
passive_value_growth:  0.02   (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.0345: reale Dichte 1,5%)
sac_drain_growth:       0.01  (Kandidat fuer DEUTLICHE Absenkung vom BR-modifizierten Basiswert 0.062: reale
                                Dichte 0% - keine dedizierten Sac-Outlets in dieser Liste)
disruption_growth:     0.01
mana_growth:            0.11  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.1705: reale Dichte 7,6%)
variance_amplitude:    0.33   (ueber Basiswert 0.28 - Madness/Discard-Engine ist stark handabhaengig)
dead_turn_chance_base: 0.10   (ueber Basiswert 0.081 - Discard-Engine kann eigene leere Hand erzeugen)
```

### Zelle 3: Treasure & Exile-Cast als Midrange

```
board_presence_growth: 0.45   (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.6325: reale Dichte 38,5%)
interaction_growth:    0.10   (nah am BR-modifizierten Basiswert 0.108: reale Dichte 9,2%)
wipe_growth:            0.02  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.033: reale Dichte 1,5%)
combo_growth:           0.04  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.06: kein Infinite,
                                Disciple of the Vault + Artefakt-Sac ist eine Burn-Engine statt Loop)
passive_value_growth:  0.03   (nah am BR-modifizierten Basiswert 0.0345: reale Dichte 3,1%)
sac_drain_growth:       0.06  (nah am BR-modifizierten Basiswert 0.062: reale Dichte 7,7%)
disruption_growth:     0.015  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.02025: reale Dichte 0%
                                der 9 Game-Changer)
**mana_growth:          0.22** (Kandidat fuer DEUTLICHE Anhebung vom BR-modifizierten Basiswert 0.1705: reale
                                klassische Ramp-Dichte 9,2%, aber dichter eigener Treasure-Erzeugungs-Kern
                                (29,2% - Birgi/Storm-Kiln Artist/Reckless Fireweaver u.a.) erzeugt zusaetzliche,
                                klassisch nicht gezaehlte Mana-Quellen, hilfsweise hier abgebildet)
variance_amplitude:    0.30   (ueber Basiswert 0.28 - Exile-Cast/Impulse-Draw erhoeht die Kartenqualitaets-Varianz)
dead_turn_chance_base: 0.07
```

### Zelle 4: Group Slug/Burn als Control

```
board_presence_growth: 0.33   (nah am BR-modifizierten Basiswert 0.345: reale Dichte 32,8% - Portions-Tiefstwert)
interaction_growth:    0.14   (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.192: reale Dichte 12,5%)
wipe_growth:            0.09  (nah am BR-modifizierten Basiswert 0.121: reale Dichte 4,7% - Portions-Hoechstwert)
combo_growth:           0.02  (Kandidat fuer DEUTLICHE Absenkung vom BR-modifizierten Basiswert 0.072: kein
                                bestaetigter Infinite)
**passive_value_growth: 0.08** (Kandidat fuer DEUTLICHE Anhebung vom BR-modifizierten Basiswert 0.0575: klassische
                                Passive-Value-Dichte nur 3,1%, aber der Group-Slug-Kern (28,1% - Underworld
                                Dreams/Spiteful Visions/Sulfuric Vortex u.a.) sind funktional passive
                                Dauerschaden-Engines, hilfsweise hier zusaetzlich abgebildet, siehe Reflexion)
sac_drain_growth:       0.05  (Kandidat fuer Anhebung vom BR-modifizierten Basiswert 0.0155: reale Dichte 6,3%)
disruption_growth:     0.02   (Kandidat fuer DEUTLICHE Absenkung vom BR-modifizierten Basiswert 0.0675: reale
                                Dichte 0% der 9 Game-Changer - Harsh Mentor/Crawlspace sind generischer Stax)
mana_growth:            0.14  (nah am BR-modifizierten Basiswert 0.154: reale Dichte 10,9%)
variance_amplitude:    0.22   (unter Basiswert 0.26 - Mogis spielt konstanten Dauerschaden statt Spikes)
dead_turn_chance_base: 0.06
```

### Zelle 5: Demons/Big-Mana als Aggro

```
board_presence_growth: 0.75   (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.9775: reale Dichte 53,1%
                                - wenige, aber extreme Top-End-Bomben (2x Ulamog, Kozilek, Vilis) statt schneller
                                Curve)
interaction_growth:    0.06   (Kandidat fuer Anhebung vom BR-modifizierten Basiswert 0.042: reale Dichte 7,8%)
wipe_growth:            0.03  (Kandidat fuer Anhebung vom BR-modifizierten Basiswert 0.0: reale Dichte 3,1%,
                                Blasphemous Act/Toxic Deluge real vorhanden)
combo_growth:           0.025 (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.036: kein bestaetigter
                                Infinite, It That Betrays+Ulamog ist Battlecruiser-Synergie)
passive_value_growth:  0.015  (leicht ueber dem BR-modifizierten Basiswert 0.0115: reale Dichte 1,6%)
sac_drain_growth:       0.025 (Kandidat fuer Anhebung vom BR-modifizierten Basiswert 0.0155: reale Dichte 3,1%)
disruption_growth:     0.005
**mana_growth:          0.21** (Kandidat fuer Anhebung vom BR-modifizierten Basiswert 0.187: reale klassische
                                Ramp-Dichte 9,4%, aber Neheb the Eternal (Mana-Burst) und die
                                kostenreduzierende Commander-Faehigkeit selbst erzeugen zusaetzliche,
                                klassisch nicht gezaehlte effektive Mana-Verfuegbarkeit)
variance_amplitude:    0.34   (ueber Basiswert 0.30 - sehr hohe Curve-Varianz durch mehrere 8-10-Mana-Bomben)
dead_turn_chance_base: 0.12   (ueber Basiswert 0.09 - hohe Manakurve birgt Gefahr toter Zuege ohne fruehe Rampe)
```

### Zelle 6: Vampires als Midrange

```
board_presence_growth: 0.48   (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.6325: reale Dichte 42,9%)
interaction_growth:    0.11   (nah am BR-modifizierten Basiswert 0.108: reale Dichte 11,1%)
wipe_growth:            0.02  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.033: reale Dichte 1,6%)
**combo_growth:         0.11** (Kandidat fuer DEUTLICHE Anhebung vom BR-modifizierten Basiswert 0.06: bestaetigter
                                Infinite - zehnter Combo-Fund des Projekts, Exquisite Blood+Sanguine Bond)
passive_value_growth:  0.045  (nah am BR-modifizierten Basiswert 0.0345: reale Dichte 4,8%)
sac_drain_growth:       0.10  (Kandidat fuer Anhebung vom BR-modifizierten Basiswert 0.062: reale Dichte 12,7%)
disruption_growth:     0.015
mana_growth:            0.14  (Kandidat fuer Absenkung vom BR-modifizierten Basiswert 0.1705: reale Dichte 7,9%)
variance_amplitude:    0.29
dead_turn_chance_base: 0.08
```

## Reflexion & Grenzen dieser Portion

1. Alle 54 bisherigen Zellen (48 Vorportionen + 6 Rakdos) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Erster Feld-Überlappungs-freier Farbmodifikator-Fund des
   Projekts:** anders als bei Azorius (2 von 7 Feldern überlappend)
   und Dimir (4 von 7 Feldern überlappend) teilen sich B und R
   keine einzige modifizierte Dimension — die BR-Kombination ist
   reine Vereinigung, keine Multiplikation. Das ist methodisch
   bemerkenswert: die reale Gameplay-Erfahrung von Rakdos-Decks
   (aggressive Removal-Dichte plus rohe Board-Präsenz) entsteht hier
   nicht aus verstärkenden Farbmodifikatoren, sondern aus der
   additiven Kombination klar getrennter Farbrollen.
3. **Wiederkehrende Modellgrenze, dritter und vierter Fall:** sowohl
   der Treasure & Exile-Cast-Kern (Prosper, 29,2%) als auch der
   Group-Slug-Kern (Mogis, 28,1%) sind dichte, thematisch zentrale
   Kartenkerne, die sich nicht sauber in ein einzelnes bestehendes
   Feld einordnen lassen. Beide wurden hilfsweise auf ein
   naheliegendes Feld gemappt (Treasure → mana_growth als
   zusätzliche Ressourcenquelle; Group Slug → passive_value_growth
   als passive Dauerschaden-Engine) — analog zum bereits in Rot
   (Zada), Grün (kein Fall) und Dimir (Mill, Theft & Copy)
   etablierten Muster eines künftigen dedizierten Feldes für
   thematische Kern-Dichten außerhalb der zehn bestehenden
   Dimensionen.
4. **Zwei neue Combo-Funde in einer Portion (9. und 10.)** — die
   höchste Combo-Dichte einer einzelnen Gilden-Portion bisher (Azorius:
   0, Dimir: 1). Beide sind klassische, bekannte zwei- bis
   dreiteilige Infinite-Muster, keine Neuerfindungen.
5. Fortsetzung folgt unmittelbar mit den übrigen 7 Gilden (Gruul,
   Selesnya, Orzhov, Izzet, Golgari, Boros, Simic) — derselbe
   Sitzungsdurchgang, wie vom Nutzer gewünscht ("Arbeite bitte
   weiter").
