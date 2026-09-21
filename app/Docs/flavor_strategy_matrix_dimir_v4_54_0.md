# Flavor-Strategie-Matrix — Dimir (UB), Gilden-Portion 2 von 10 (v4.54.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Zweite Gilden-Portion, direkt im Anschluss an Azorius (v4.53.0),
gleicher Sitzungsdurchgang. Dieselbe Methodik: Dokument als
Recherche-Gerüst, alle Werte aus echten EDHREC-Bracket-3-Listen.

Vollständige Rohdaten: `Docs/scratch/dimir_flavor_pilot_raw.md`.

## Kombinierte UB-Farbmodifikatoren

| Dimension | U | B | UB kombiniert |
|---|---|---|---|
| interaction_availability | 1.45 | 1.20 | **1.74** (multiplikativ) |
| combo_finish_readiness | 1.15 | 1.20 | **1.38** (multiplikativ) |
| passive_value_growth | 1.40 | 1.15 | **1.61** (multiplikativ) |
| disruption_growth | 1.20 | 1.35 | **1.62** (multiplikativ) |
| wipe_readiness | – | 1.10 | **1.10** |
| sac_drain_growth | – | 1.55 | **1.55** |
| mana_growth | 0.95 | – | **0.95** |

**Dimir kombiniert auf VIER Dimensionen gleichzeitig (interaction,
combo_finish, passive_value, disruption) — mehr als Azorius (2 von 7,
WU). Real bestätigt:** Nymris liefert mit 25,0% die höchste kombinierte
Interaktionsdichte des Projekts (über dem WU-Wert von Ojutai, 23,8%);
Notion Thief wurde DREIFACH real bestätigt (Anowon, Xanathar, Nymris);
Xanathar liefert den zweiten Doppel-Game-Changer-Fund des Projekts
(Notion Thief + Opposition Agent).

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Mill (Phenax) | 39,1% | 14,1% | 1,6% | 7,8% | 1,6% | Mill-Kern 26,6% (Alt-Sieg) | 0% | 1,6% |
| Zombies (Wilhelt) | 48,4% | 9,4% | 3,1% | 7,8% | 4,7% | **bestätigt** (Rooftop Storm+Gravecrawler+Outlet) | **10,9%** | 0% |
| Rogues/Ninjas (Anowon) | 48,4% | 14,1% | 1,6% | 10,9% | 1,6% | 0 | 1,6% | 1,6% (Notion Thief) |
| Self-Mill/Reanimator (Araumi) | 51,6% | 10,9% | 1,6% | 7,8% | 0% | Reanimations-Kern 15,6% | 1,6% | 0% |
| Theft & Copy (Xanathar) | 30,2% | 17,5% | 1,6% | 12,7% | 1,6% | 0 | 0% | **4,8%** (2 Game-Changer) |
| Flash (Nymris) | 32,8% | **25,0%** (Projekt-Höchstwert) | 3,1% | 9,4% | 0% | 0 | 0% | 3,1% (Notion Thief) |

**Fünf nicht-triviale Befunde dieser Portion:**
1. **Siebter bestätigter vollständiger Combo-Fund des Projekts:**
   Rooftop Storm + Gravecrawler + freier Opfer-Outlet (Carrion
   Feeder/Ashnod's Altar/Phyrexian Altar), alle real bei Wilhelt.
2. **Notion Thief DREIFACH real bestätigt** in dieser einen Gilde
   (Anowon, Xanathar, Nymris) — dichteste Einzelkarten-Wiederholung
   eines der 9 Game-Changer im Projekt bisher.
3. **Zweiter Doppel-Game-Changer-Fund des Projekts:** Notion Thief +
   Opposition Agent gemeinsam bei Xanathar (nach Grand Arbiter
   Augustin IV + Drannith Magistrate, Azorius v4.53.0).
4. **Neuer Projekt-Höchstwert kombinierte Interaktion:** Nymris mit
   25,0%, real bestätigt durch den kombinierten UB-Multiplikator 1,74.
5. Wilhelt (Zombies) wird abweichend vom Dokument-Label
   "Typal/Aristocrats" zu **horde** reklassifiziert (EDHREC-Tag
   "Tokens 303" dominiert vor "Aristocrats 267"; Board-Präsenz 48,4%
   plus Go-Wide-Token-Generatoren).

## Die Matrix (Dimir)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Mill | – | – | – | **✓ (Zelle 1)** | – |
| Zombies | – | – | – | – | **✓ (Zelle 2, umklassifiziert von "Typal/Aristocrats")** |
| Rogues & Ninjas | – | **✓ (Zelle 3)** | – | – | – |
| Self-Mill & Reanimator | – | – | **✓ (Zelle 4)** | – | – |
| Theft & Copy | – | – | – | **✓ (Zelle 5)** | – |
| Flash | – | – | – | **✓ (Zelle 6)** | – |

### Zelle 1: Mill als Control

```
board_presence_growth: 0.36   (nah am Basiswert 0.30 - reale Dichte 39,1%)
interaction_growth:    0.14   (nah am UB-modifizierten Basiswert 0.2784, Kandidat fuer deutliche Absenkung:
                                reale Dichte 14,1%)
wipe_growth:            0.03  (Kandidat fuer deutliche Absenkung vom UB-modifizierten Basiswert 0.121: reale
                                Dichte nur 1,6%)
combo_growth:           0.11  (Kandidat fuer DEUTLICHE Anhebung vom UB-modifizierten Basiswert 0.0828: der
                                Mill-Kern (26,6%) ist funktional eine alternative Wincondition, hilfsweise auf
                                combo_growth gemappt - Modellgrenze, siehe Reflexion)
passive_value_growth:  0.045  (Kandidat fuer Absenkung: reale Dichte 1,6%, aber Rhystic Study real vorhanden)
sac_drain_growth:       0.0
disruption_growth:     0.015  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.081: reale Dichte 1,6%,
                                keine Game-Changer)
mana_growth:            0.09  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.133: reale Dichte 7,8%)
variance_amplitude:    0.24
dead_turn_chance_base: 0.08
```

### Zelle 2: Zombies als Horde (umklassifiziert von "Typal/Aristocrats")

```
board_presence_growth: 1.10   (Kandidat fuer Absenkung vom UB-modifizierten Horde-Basiswert 1.30: reale Dichte
                                48,4%)
interaction_growth:    0.05   (Kandidat fuer Anhebung vom UB-modifizierten Basiswert 0.0348: reale Dichte 9,4%
                                - UB-Zombie-Horde behaelt mehr Antworten als reines Go-Wide anderer Farben)
wipe_growth:            0.02  (Kandidat fuer Anhebung von 0.0: The Meathook Massacre/Toxic Deluge real
                                vorhanden, 3,1%)
combo_growth:           0.08  (Kandidat fuer DEUTLICHE Anhebung vom UB-modifizierten Basiswert 0.0276: Rooftop
                                Storm+Gravecrawler+Outlet real bestaetigt - siebter vollstaendiger Combo-Fund)
passive_value_growth:  0.03   (ueber dem UB-modifizierten Basiswert 0.0161 - reale Dichte 4,7%)
**sac_drain_growth:     0.09** (Kandidat fuer DEUTLICHE Anhebung vom UB-modifizierten Basiswert 0.031: reale
                                Dichte 10,9% - naeher an Yawgmoths Rekordwert (Schwarz, 17,2%) als am generischen
                                Horde-Basiswert)
disruption_growth:     0.005
mana_growth:            0.14  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.1805: reale Dichte 7,8%)
variance_amplitude:    0.29
dead_turn_chance_base: 0.06
```

### Zelle 3: Rogues & Ninjas als Aggro

```
board_presence_growth: 0.72   (Kandidat fuer Absenkung vom UB-modifizierten Aggro-Basiswert 0.85: reale Dichte
                                48,4%)
interaction_growth:    0.13   (Kandidat fuer DEUTLICHE Anhebung vom UB-modifizierten Basiswert 0.0609: reale
                                Dichte 14,1% - UB-Tempo behaelt deutlich mehr Antworten als generisches Aggro,
                                analog zu Azorius Spirits/Flying)
wipe_growth:            0.015 (leicht ueber 0.0 - reale Dichte 1,6%)
combo_growth:           0.025 (Kandidat fuer Absenkung: kein bestaetigter Infinite)
passive_value_growth:  0.02   (leicht ueber Basiswert - reale Dichte 1,6%)
sac_drain_growth:       0.01
disruption_growth:     0.015  (Kandidat fuer Anhebung vom UB-modifizierten Basiswert 0.0081: Notion Thief real
                                bestaetigt, 1,6%)
mana_growth:            0.14  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.1615: reale Dichte
                                10,9%)
variance_amplitude:    0.28
dead_turn_chance_base: 0.09
```

### Zelle 4: Self-Mill & Reanimator als Midrange

```
board_presence_growth: 0.52   (nah am Basiswert 0.55 - reale Dichte 51,6%)
interaction_growth:    0.10   (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.1566: reale Dichte
                                10,9%)
wipe_growth:            0.02  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.033: reale Dichte 1,6%)
combo_growth:           0.09  (Kandidat fuer DEUTLICHE Anhebung vom UB-modifizierten Basiswert 0.069: der
                                Reanimations-Kern (15,6%) ist der zentrale Gameplan, hilfsweise auf combo_growth
                                gemappt trotz fehlendem 2-Karten-Infinite in DIESER spezifischen Liste)
passive_value_growth:  0.02   (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.0483: reale Dichte 0%
                                dedizierte Engines)
sac_drain_growth:       0.02  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.062: reale Dichte nur
                                1,6%, Altar of Dementia ohne dedizierten Payoff)
disruption_growth:     0.005
mana_growth:            0.12  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.14725: reale Dichte
                                7,8%)
variance_amplitude:    0.31   (ueber Basiswert 0.28 - Reanimator braucht das richtige Friedhof-Setup)
dead_turn_chance_base: 0.08
```

### Zelle 5: Theft & Copy als Control

```
board_presence_growth: 0.31   (nah am Basiswert 0.30 - reale Dichte 30,2%)
interaction_growth:    0.18   (nah am UB-modifizierten Basiswert 0.2784, Kandidat fuer Absenkung: reale Dichte
                                17,5%)
wipe_growth:            0.03  (Kandidat fuer DEUTLICHE Absenkung vom UB-modifizierten Basiswert 0.121: reale
                                Dichte nur 1,6% - Theft&Copy verlaesst sich auf Diebstahl statt Sweeper)
combo_growth:           0.10  (Kandidat fuer Anhebung vom UB-modifizierten Basiswert 0.0828: der Theft/Copy-Kern
                                (22,2%) ist funktional ein alternativer Ressourcen-Angriff, hilfsweise ueber
                                combo_growth abgebildet, siehe Reflexion)
passive_value_growth:  0.045  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.0805: reale Dichte 1,6%)
sac_drain_growth:       0.0
**disruption_growth:    0.075** (nah am UB-modifizierten Basiswert 0.081: reale Dichte 4,8% - Notion Thief UND
                                Opposition Agent GEMEINSAM real bestaetigt, zweiter Doppel-Game-Changer-Fund des
                                Projekts)
mana_growth:            0.13  (nah am UB-modifizierten Basiswert 0.133 - reale Dichte 12,7%)
variance_amplitude:    0.25
dead_turn_chance_base: 0.075
```

### Zelle 6: Flash als Control

```
board_presence_growth: 0.33   (nah am Basiswert 0.30 - reale Dichte 32,8%)
**interaction_growth:   0.26** (nah am UB-modifizierten Basiswert 0.2784: reale Dichte 25,0% - PROJEKT-
                                HOECHSTWERT kombinierter Interaktion, bestaetigt den 1,74x-UB-Multiplikator
                                direkt)
wipe_growth:            0.05  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.121: reale Dichte 3,1%)
combo_growth:           0.04  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.0828: kein bestaetigter
                                Infinite in dieser Liste, nur Value-Engines wie Snapcaster Mage/Torrential
                                Gearhulk)
passive_value_growth:  0.02   (Kandidat fuer DEUTLICHE Absenkung vom UB-modifizierten Basiswert 0.0805: reale
                                Dichte 0% dedizierte Engines in dieser spezifischen Liste)
sac_drain_growth:       0.0
disruption_growth:     0.03   (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.081: Notion Thief real
                                bestaetigt (dritter Fund dieser Gilde), reale Dichte 3,1%)
mana_growth:            0.09  (Kandidat fuer Absenkung vom UB-modifizierten Basiswert 0.133: reale Dichte 9,4%)
variance_amplitude:    0.22   (deutlich unter Basiswert 0.26 - 27 Instants bedeuten maximale Flexibilitaet auf
                                gegnerische Zuege)
dead_turn_chance_base: 0.07
```

## Reflexion & Grenzen dieser Portion

1. Alle 42 bisherigen Zellen (36 Vorportionen + 6 Dimir) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Neue, wiederkehrende Modellgrenze:** sowohl Mill (Phenax) als
   auch Theft & Copy (Xanathar) haben einen dichten, thematisch
   zentralen Kartenkern (26,6% bzw. 22,2%), der weder klassisches
   Removal/Wipe noch ein 2-Karten-Infinite ist, aber klar die
   Sieg-Logik des Decks trägt. Beide wurden hilfsweise über
   `combo_growth` abgebildet (alternative Wincondition-Dichte statt
   klassischem Combo), analog zum bereits in Rot (Zada, Storm-Paket)
   etablierten Muster — ein wiederkehrender Kandidat für ein
   künftiges dediziertes "Alt-Sieg-Dichte"-Feld, getrennt von
   `combo_growth` im engeren (Infinite-Loop-)Sinn.
3. **UB kombiniert auf mehr Dimensionen als WU** (4 von 7 Feldern
   gegenüber 2 von 7 bei Azorius) — reale Belege stützen das direkt
   (Notion Thief dreifach, Opposition Agent, neuer
   Interaktions-Höchstwert).
4. Fortsetzung folgt unmittelbar mit den übrigen 8 Gilden (Rakdos,
   Gruul, Selesnya, Orzhov, Izzet, Golgari, Boros, Simic) — derselbe
   Sitzungsdurchgang, wie vom Nutzer gewünscht.
