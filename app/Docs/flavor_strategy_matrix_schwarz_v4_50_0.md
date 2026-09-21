# Flavor-Strategie-Matrix — Schwarz, Portion 3 von 15 (v4.50.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Dritte Portion der Nutzer-Dokument-Auswertung. Der Nutzer hat gebeten,
eigenständig iterativ durch die restlichen Farben zu arbeiten, ohne
jedes Mal neu angestoßen zu werden — diese und die folgenden Portionen
(Rot, Grün) entstehen daher in einem Durchgang, mit derselben Methodik
wie Weiß (v4.48.0) und Blau (v4.49.0): die Dokumente liefern Flavor/
Commander/EDHREC-Link als Recherche-Gerüst, alle Zustandsfunktionswerte
werden selbst aus der echten, verlinkten Bracket-3-Decklist ausgezählt.

Vollständige Rohdaten: `Docs/scratch/black_flavor_pilot_raw.md`.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Entfernung | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Aristokraten (Yawgmoth) | 48,4% | 6,3% | 3,1% | 7,8% | 3,1% | ~3 Teile | **17,2%** (Projekt-Höchstwert) | 0% |
| Reanimator (Chainer) | 47,6% | 6,3% | 4,8% | 9,5% | 4,8% | ~3 Teile | 9,5% | 0% |
| Lifedrain (Vito) | 40,6% | 7,8% | 3,1% | 7,8% | 10,9% | **bestätigt** (Sanguine Bond+Exquisite Blood) | 1,6% | 0% |
| Discard (Tinybones) | 31,3% | 7,8% | 3,1% | 9,4% | 4,7% | 0 | 0% | **1,6%** (Tergrid bestätigt) |
| Zombies (Gisa) | 46,0% | 6,3% | 1,6% | 7,9% | 3,2% | ~2-3 Teile | 6,3% | 0% |
| Ratten (Marrow-Gnawer) | 52,3% (verzerrt, s.u.) | 6,2% | 1,5% | 6,2% | 4,6% | ~2 Teile | 4,6% | 0% |

**Sechs nicht-triviale Befunde dieser Portion:**
1. **Yawgmoth liefert den stärksten Sac-Drain-Fund des gesamten
   Projekts** (17,2%, 11 Karten) — dichter als die ursprüngliche
   v4.40.0-Kalibrierungsquelle (Endrek Sahr Expensive, damals nur 4
   benannte Karten) selbst.
2. **Dritter bestätigter vollständiger Combo-Fund des Projekts:**
   Sanguine Bond + Exquisite Blood, beide real in derselben Vito-Liste
   (nach Urza und Orvar in Blau, v4.49.0).
3. Vito bestätigt erneut (nach v4.46.0) den fehlenden Opfer-Bezug von
   mono-schwarzem Lifedrain: nur 1,6% Opfer/Drain-Dichte trotz
   "Lifedrain"-Namen — der Drain läuft über Lifegain-Trigger, nicht über
   Opferschleifen.
4. **Tergrid, God of Fright** — eine der 9 im Projekt getrackten
   unmapped_persistent_disruption-Game-Changer — real in einer Bracket-
   3-Discard-Liste bestätigt.
5. Ramp wird auch bei Schwarz im Nutzerdokument tendenziell überschätzt
   (Vito real 7,8% vs. Dokument "12-16") — derselbe Trend wie bei Weiß
   und Blau.
6. Rat Colony (Marrow-Gnawer) zeigt dieselbe Modellgrenze wie Persistent
   Petitioners (Bruvac, v4.49.0): eine einzige, oft kopierte Karte
   verzerrt die rohe Board-Präsenz-Prozentzahl nach oben.

## Die Matrix (Schwarz)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Aristokraten/Sacrifice | – | – | **✓ (Zelle 1)** | – | – |
| Reanimator | – | – | **✓ (Zelle 2)** | – | – |
| Lifedrain/Devotion | – | – | **✓ (Zelle 3)** | – | – |
| Discard | – | – | – | **✓ (Zelle 4)** | – |
| Zombies | – | – | **✓ (Zelle 5)** | – | – |
| Ratten | – | – | – | – | **✓ (Zelle 6, umklassifiziert von "Aggro")** |

**Zelle 6 (Ratten) wurde von "Aggro bis Combo" (Dokument-Label) zu
"horde" präzisiert:** die reale Marrow-Gnawer-Liste ist strukturell ein
Go-Wide-Token-Schwarm (17 Kopien von Rat Colony + Pack Rat + weitere
billige, redundante Körper) — dasselbe Muster wie Myrel/Tokens-Go-Wide
in Weiß (v4.48.0) und Elfen/Go-Wide in Grün (v4.47.0), die beide
ebenfalls als "horde" statt "aggro" eingeordnet wurden. Damit bleibt die
Farbe-Strategie-Zuordnung konsistent mit den beiden vorherigen Portionen.

### Zelle 1: Aristokraten/Sacrifice als Midrange

```
board_presence_growth: 0.55   (nah am Basiswert - reale Dichte 48,4%)
interaction_growth:    0.07   (Kandidat fuer Absenkung vom B-modifizierten Basiswert 0.108: reale
                                Punkt-Entfernung nur 6,3%)
wipe_growth:           0.035  (nah am B-modifizierten Basiswert 0.033 - reale Dichte 3,1%)
combo_growth:          0.075  (Kandidat fuer leichte Anhebung ueber B-modifizierten Basiswert 0.06:
                                Reassembling Skeleton/Bloodghast/Nether Traitor (0-Kosten-Wiederkehr) +
                                Ashnod's/Phyrexian Altar sind der klassische Yawgmoth-Infinite-Loop)
passive_value_growth:  0.035  (nah am B-modifizierten Basiswert 0.0345 - reale Dichte 3,1%)
sac_drain_growth:      0.10   (Kandidat fuer MASSIVE Anhebung: B-modifizierter Basiswert nur 0.062 - reale
                                Dichte 17,2% (11 von 64 Nicht-Land-Karten: Ashnod's Altar, Phyrexian Altar,
                                Viscera Seer als Outlets + Blood Artist, Zulaport Cutthroat, Vengeful
                                Bloodwitch, Syr Konrad the Grim, Grave Pact, Bastion of Remembrance,
                                Pitiless Plunderer, Warren Soultrader als Payoffs) ist DICHTER als die
                                urspruengliche v4.40.0-Kalibrierungsquelle selbst (Endrek Sahr Expensive: nur
                                4 benannte Karten) - der bislang staerkste Sac-Drain-Fund des Projekts)
disruption_growth:     0.01
mana_growth:           0.12   (Kandidat fuer Absenkung: Basiswert 0.155 - reale Dichte 7,8%)
variance_amplitude:    0.24   (unter Basiswert 0.28 - dichte redundante Wiederkehr-Kreaturen puffern ab)
dead_turn_chance_base: 0.08
```

### Zelle 2: Reanimator als Midrange

```
board_presence_growth: 0.52   (nah am Basiswert - reale Dichte 47,6%)
interaction_growth:    0.07   (Kandidat fuer Absenkung vom B-modifizierten Basiswert 0.108: reale Dichte 6,3%)
wipe_growth:           0.045  (leicht ueber B-modifiziertem Basiswert 0.033 - reale Dichte 4,8%)
combo_growth:          0.075  (Kandidat fuer Anhebung: B-modifizierter Basiswert 0.06 - Yawgmoth (als
                                Kreatur) + Ashnod's Altar + Phyrexian Altar + Altar of Dementia sind ein
                                starkes sekundaeres Combo-Signal)
passive_value_growth:  0.045  (leicht ueber B-modifiziertem Basiswert 0.0345 - reale Dichte 4,8%)
sac_drain_growth:      0.075  (Kandidat fuer Anhebung ueber B-modifizierten Basiswert 0.062, aber DEUTLICH
                                unter Yawgmoth (17,2%): reale Dichte 9,5% - Reanimator nutzt Opfer-Altaere
                                eher als Combo-Enabler denn als durchgaengige Drain-Engine)
disruption_growth:     0.01
mana_growth:           0.13   (Kandidat fuer Absenkung: Basiswert 0.155 - reale Dichte 9,5%)
variance_amplitude:    0.30   (ueber Basiswert 0.28 - Reanimator braucht das richtige Friedhof-Setup,
                                strukturell hoehere Varianz)
dead_turn_chance_base: 0.08
```

### Zelle 3: Lifedrain/Big-Mana/Devotion als Midrange

```
board_presence_growth: 0.48   (Kandidat fuer leichte Absenkung: Basiswert 0.55 - reale Dichte 40,6%)
interaction_growth:    0.075  (Kandidat fuer Absenkung: B-modifizierter Basiswert 0.108 - reale Dichte 7,8%)
wipe_growth:           0.035  (nah am B-modifizierten Basiswert - reale Dichte 3,1%)
combo_growth:          0.09   (Kandidat fuer DEUTLICHE Anhebung: B-modifizierter Basiswert nur 0.06 -
                                Sanguine Bond + Exquisite Blood sind BEIDE real in der Liste vorhanden, eine
                                bekannte, vollstaendige Infinite-Lifedrain-Combo. Dritter bestaetigter
                                vollstaendiger Combo-Fund des Projekts)
passive_value_growth:  0.065  (Kandidat fuer DEUTLICHE Anhebung: B-modifizierter Basiswert nur 0.0345 -
                                reale Dichte 10,9% (Bolas's Citadel, Black Market Connections, Phyrexian
                                Arena, Bloodchief Ascension, Revenge of Ravens, Alhammarret's Archive,
                                Demon's Horn GEMEINSAM) - dichteste Passive-Value-Haeufung dieser Portion)
sac_drain_growth:      0.02   (Kandidat fuer DEUTLICHE Absenkung vom B-modifizierten Basiswert 0.062: reale
                                Dichte nur 1,6% (nur Blood Artist, KEINE Opfer-Outlets) - bestaetigt den
                                v4.46.0-Befund, dass mono-schwarzes Lifedrain ueber Lifegain-Trigger statt
                                ueber Opferschleifen laeuft)
disruption_growth:     0.01
mana_growth:           0.11   (Kandidat fuer DEUTLICHE Absenkung: Basiswert 0.155, Dokument-Angabe sogar
                                "12-16" - reale Dichte nur 7,8%)
variance_amplitude:    0.26   (Combo-Backup-Plan reduziert Varianz leicht gegenueber reinem Value-Midrange)
dead_turn_chance_base: 0.08
```

### Zelle 4: Discard als Control

```
board_presence_growth: 0.32   (nah am unmodifizierten Basiswert 0.30 - reale Dichte 31,3%)
interaction_growth:    0.13   (Kandidat fuer Absenkung vom B-modifizierten Basiswert 0.192, ABER mit
                                Vorbehalt: reine Punkt-Entfernung ist nur 7,8%, die eigentliche Interaktion
                                dieses Decks laeuft ueber Discard/Ressourcen-Entzug, nicht ueber Removal -
                                dieses Feld bildet "Discard als Interaktion" strukturell nicht sauber ab,
                                siehe Reflexion)
wipe_growth:           0.05   (Kandidat fuer Absenkung: B-modifizierter Basiswert 0.121 - reale Dichte 3,1%)
combo_growth:          0.03   (Kandidat fuer Absenkung: B-modifizierter Basiswert 0.072 - kein bestaetigter
                                2-Karten-Combo gefunden)
passive_value_growth:  0.045  (Kandidat fuer leichte Absenkung: B-modifizierter Basiswert 0.0575)
sac_drain_growth:      0.0
disruption_growth:     0.08   (Kandidat fuer Anhebung ueber B-modifizierten Basiswert 0.0675: Tergrid, God
                                of Fright - eine der 9 unmapped_persistent_disruption-Game-Changer - real in
                                dieser Bracket-3-Liste bestaetigt, zusaetzlich zur enormen generischen
                                Discard-Dichte der thematischen Kernkarten (~42% der Nicht-Land-Karten,
                                deutlich ueber der Dokument-Schaetzung "12-18 plus 8-12"))
mana_growth:           0.11   (Kandidat fuer Absenkung: Basiswert 0.14 - reale Dichte 9,4%)
variance_amplitude:    0.26   (nah am Basiswert)
dead_turn_chance_base: 0.08
```

### Zelle 5: Zombies als Midrange

```
board_presence_growth: 0.50   (Kandidat fuer leichte Absenkung: Basiswert 0.55 - reale Dichte 46,0%)
interaction_growth:    0.07   (Kandidat fuer Absenkung: B-modifizierter Basiswert 0.108 - reale Dichte 6,3%)
wipe_growth:           0.02   (Kandidat fuer Absenkung: B-modifizierter Basiswert 0.033 - reale Dichte 1,6%)
combo_growth:          0.065  (leicht ueber B-modifiziertem Basiswert 0.06 - Ashnod's Altar + Phyrexian
                                Altar + Mikaeus, the Unhallowed (Undying-Doubler) als solides Combo-Signal)
passive_value_growth:  0.035  (nah am B-modifizierten Basiswert - reale Dichte 3,2%)
sac_drain_growth:      0.055  (nah, leicht unter B-modifiziertem Basiswert 0.062 - reale Dichte 6,3%,
                                deutlich unter Yawgmoths spezialisierter 17,2%-Dichte)
disruption_growth:     0.01
mana_growth:           0.12   (Kandidat fuer Absenkung: Basiswert 0.155 - reale Dichte 7,9%)
variance_amplitude:    0.27
dead_turn_chance_base: 0.09
```

### Zelle 6: Ratten als Horde (präzisiert von "Aggro bis Combo")

```
board_presence_growth: 1.15   (Kandidat fuer leichte Absenkung unter den Horde-Basiswert 1.30: reale Dichte
                                52,3% ist teilweise durch 17 Kopien von Rat Colony auf einem Karten-Slot
                                verzerrt - die tatsaechliche Kartenvielfalt ist geringer, als die reine
                                Slot-Zahl suggeriert, aber die Grundmechanik - viele billige, redundante
                                Koerper - passt echt zum Horde-Profil)
interaction_growth:    0.05   (Kandidat fuer Anhebung ueber den B-modifizierten Horde-Basiswert 0.024:
                                reale Dichte 6,2% - schwarzes Aggro/Horde behaelt trotz Go-Wide-Ausrichtung
                                eine spuerbare Removal-Grundausstattung, die reines weisses/gruenes Horde
                                (v4.47.0/v4.48.0) nicht zeigte)
wipe_growth:           0.015  (Kandidat fuer Anhebung von 0.0: Swarmyard Massacre als einseitiger
                                Fight-Sweeper real vorhanden)
combo_growth:          0.035  (leicht ueber B-modifiziertem Basiswert 0.024 - Rat Colony + Thrumming Stone
                                als Viel-Namen-Payoff-Engine, Kindred Dominance als Edikt-Finisher)
passive_value_growth:  0.025  (ueber B-modifiziertem Basiswert 0.0115 - reale Dichte 4,6%)
sac_drain_growth:      0.045  (Kandidat fuer Anhebung ueber B-modifizierten Basiswert 0.031: reale Dichte
                                4,6% - Deadly Dispute, Village Rites, Grave Pact)
disruption_growth:     0.007
mana_growth:           0.13   (Kandidat fuer DEUTLICHE Absenkung: Horde-Basiswert 0.19 - reale Dichte nur
                                6,2%, Ratten-Aggro kurvt ueber billige Kreaturen statt ueber Mana-Rampe)
variance_amplitude:    0.28   (unter Horde-Basiswert 0.32 - hohe Redundanz durch Rat-Colony-Kopien senkt
                                Varianz)
dead_turn_chance_base: 0.07
```

## Reflexion & Grenzen dieser Portion

1. Alle 18 bisherigen Zellen (6 Weiß + 6 Blau + 6 Schwarz) bleiben
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Wichtigster Einzelfund:** Yawgmoths sac_drain_growth-Kandidat
   (0.10) übertrifft sogar den Wert, der ursprünglich aus der
   Endrek-Sahr-Stichprobe (v4.40.0) abgeleitet wurde — ein starkes
   Signal, dass eine spezialisierte "Aristokraten"-Flavor-Zelle
   eigenständig kalibriert werden sollte, statt sich auf den
   generischen Midrange-Basiswert zu verlassen.
3. **Neue Modellgrenze (Discard/Tinybones):** `interaction_growth`
   bildet Discard-als-Ressourcenentzug strukturell schlecht ab, weil das
   Feld ursprünglich für Punkt-Removal/Counterspells konzipiert wurde.
   Eine mögliche künftige Erweiterung (nicht in dieser Version
   umgesetzt): ein eigenes "Ressourcenentzug"-Signal für Discard-lastige
   Decks, analog zum bereits bestehenden `sac_drain_growth`-Feld.
4. Fortsetzung folgt unmittelbar mit Rot und Grün (derselbe
   Sitzungsdurchgang, wie vom Nutzer gewünscht), danach die 10 Gilden.
