# Flavor-Strategie-Matrix — Rot, Portion 4 von 15 (v4.51.0)

## Fortsetzung (eigenständig, ohne erneute Aufgabenstellung)

Vierte Portion der Nutzer-Dokument-Auswertung. Der Nutzer hat gebeten,
eigenständig iterativ durch die restlichen Farben zu arbeiten, ohne
jedes Mal neu angestoßen zu werden — diese Portion entsteht daher direkt
im Anschluss an Schwarz (v4.50.0), mit derselben Methodik wie Weiß
(v4.48.0), Blau (v4.49.0) und Schwarz (v4.50.0): die Dokumente liefern
Flavor/Commander/EDHREC-Link als Recherche-Gerüst, alle
Zustandsfunktionswerte werden selbst aus der echten, verlinkten
Bracket-3-Decklist ausgezählt.

Vollständige Rohdaten: `Docs/scratch/red_flavor_pilot_raw.md`.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Entfernung | Wipes | Ramp | Passive Value | Combo | Opfer/Drain | Disruption |
|---|---|---|---|---|---|---|---|---|
| Goblins/Go-Wide (Krenko) | 48,4% | 4,7% | 1,6% | 6,3% | ~0% | 0 (Kiki ohne Partner) | 4,7% | 0% |
| Burn/Group Slug (Ojer Axonil) | 30,8% | **9,2%** | 1,5% | 7,7% | 9,2% (s.u.) | 0 | 0% | 3,1% (kein Game-Changer) |
| Artefakte/Reanimation (Daretti) | 35,9% | 6,3% | **6,3%** | **12,5%** | 4,7% | **bestätigt** (Rings+Basalt Monolith) | 3,1% | 0% |
| Storm/Spellslinger (Zada) | 32,8% | 1,6% | 1,6% | 4,7% | 3,1% | Storm-Paket 4,7% | 0% | 0% |
| Drachen/Tribal (Lathliss) | 45,2% | 4,8% | 3,2% | 6,5% | 3,2% | 0 | 0% | 0% |
| Equipment/Voltron (Valduk) | **18,75%** (niedrigst) | 3,1% | 1,6% | 3,1% | 3,1% | 0 | 3,1% | 0% |

**Sieben nicht-triviale Befunde dieser Portion:**
1. **Vierter bestätigter vollständiger Combo-Fund des Projekts:** Rings
   of Brighthearth + Basalt Monolith, beide real in derselben
   Daretti-Liste (nach Heliod+Ballista/Weiß v4.48.0, Isochron+Dramatic
   Reversal+Basalt/Blau v4.49.0, Sanguine Bond+Exquisite Blood/Schwarz
   v4.50.0).
2. **Kiki-Jiki-Combo-Fehlanzeige real erneut bestätigt:** die
   Krenko-Liste enthält Kiki-Jiki, Mirror Breaker, aber keinen der
   bekannten Combo-Partner (Restoration Angel, Zealous Conscripts,
   Deceiver Exarch) — deckt sich exakt mit der ursprünglichen
   v4.39.0-Kalibrierungsnotiz für dieselbe Karte in derselben Rolle.
3. **Storm real bestätigt** über EDHRECs eigenes "Storm 147"-Tag bei
   Zada — der klarste Kombo-Rennen-Flavor des gesamten Projekts bisher
   (kaum Interaktion: nur 1,6% Entfernung, 1,6% Wipe, 0% Disruption).
4. **Voltron (Valduk) zeigt dieselbe Board-Präsenz-Modellgrenze wie
   Preston/Light-Paws (Weiß, v4.48.0):** sehr wenige, teuer
   ausgerüstete Kreaturen statt Board-Breite — board_presence_growth
   bleibt strukturell zu niedrig für den tatsächlichen aggressiven
   Impact des Decks.
5. **Group Slug (Ojer Axonil) offenbart eine neue Modellgrenze:**
   stehende Schadens-Verzauberungen (Sulfuric Vortex, Manabarbs,
   Pyrohemia, Roiling Vortex) erzeugen laufenden Direktschaden statt
   Karten-/Manavorteil — hilfsweise auf `passive_value_growth`
   gemappt, aber ein Kandidat für ein künftiges dediziertes Feld,
   parallel zum Discard-Befund bei Tinybones (Schwarz, v4.50.0).
6. **Daretti zeigt die höchste Wipe-Dichte (6,3%) und höchste
   Ramp-Dichte (12,5%) des Rot-Samples** — für Mono-Rot ungewöhnlich
   hoch, konsistent mit dem Artefakt-Toolbox-/Control-Charakter statt
   klassischem Rot-Aggro.
7. **Methodische Entscheidung gegen "goldfish" für Zada/Storm:** obwohl
   Zada die mit Abstand niedrigste Interaktions-/Wipe-/
   Disruption-Dichte des Projekts zeigt, wird die Kurve NICHT als
   `goldfish` klassifiziert — dieses Profil ist laut eigenem
   `_comment` in `opponent_state_weights.json` explizit für "kein
   echter Gegner (reines Goldfishing)" reserviert, nicht für ein reales
   Opponent-Archetyp. Stattdessen: `aggro` mit stark angehobenem
   `combo_growth`-Kandidaten (siehe Zelle 4) — die sachlich treffendere
   Einordnung für ein reales, wenn auch extrem non-interaktives,
   Renn-Deck.

## Die Matrix (Rot)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Goblins/Go-Wide | – | **✓ (Zelle 1)** | – | – | – |
| Burn/Group Slug | – | – | – | **✓ (Zelle 2)** | – |
| Artefakte/Reanimation | – | – | – | **✓ (Zelle 3)** | – |
| Storm/Spellslinger | – | **✓ (Zelle 4, s. Befund 7)** | – | – | – |
| Drachen/Tribal | – | – | **✓ (Zelle 5)** | – | – |
| Equipment/Voltron | – | **✓ (Zelle 6)** | – | – | – |

**Zelle 2 (Burn/Group Slug) und Zelle 3 (Artefakte/Reanimation) wurden
zu "control" statt der Dokument-Label ("Burn"/"Reanimator") präzisiert:**
beide zeigen reale Dichtemuster (niedrige bis moderate Board-Präsenz,
spürbare Interaktion/Wipes, stehende Value-/Damage-Engines statt
Combat-Fokus), die strukturell näher an Control als an Aggro/Midrange
liegen — analog zur Reklassifizierung von Orvar (Blau, v4.49.0) und
Marrow-Gnawer (Schwarz, v4.50.0) in den Vorportionen.

### Zelle 1: Goblins/Go-Wide als Aggro

```
board_presence_growth: 0.72   (Kandidat fuer Absenkung vom R-modifizierten Aggro-Basiswert 0.9775 (0.85*1.15):
                                reale Dichte 48,4%, niedriger als der hohe R-Board-Modifikator fuer ein
                                "typisches" Kreatur-Deck erwarten laesst)
interaction_growth:    0.04   (nah am unmodifizierten Aggro-Basiswert 0.035 - reale Punkt-Entfernungsdichte 4,7%)
wipe_growth:           0.01   (Kandidat fuer leichte Anhebung von 0.0: Blasphemous Act real vorhanden, 1,6%)
combo_growth:          0.015  (Kandidat fuer Absenkung vom Aggro-Basiswert 0.03: Kiki-Jiki, Mirror Breaker real
                                vorhanden, aber OHNE Combo-Partner in der Liste - bestaetigt exakt die
                                urspruengliche v4.39.0-Kalibrierungsnotiz fuer dieselbe Karte)
passive_value_growth:  0.005  (Kandidat fuer Absenkung von 0.01: reale Dichte praktisch 0% - nur
                                Kampf-Anthems (Coat of Arms, Shared Animosity), keine stehenden Value-Engines)
sac_drain_growth:      0.03   (Kandidat fuer Anhebung vom Aggro-Basiswert 0.01: reale Dichte 4,7% - Goblin
                                Bombardment, Skirk Prospector, Goblin Chirurgeon)
disruption_growth:     0.005
mana_growth:           0.15   (Kandidat fuer Absenkung vom R-modifizierten Basiswert 0.187 (0.17*1.10): reale
                                Ramp-Dichte nur 6,3% - Goblin-Aggro kurvt ueber billige Koerper statt Manarocks;
                                Battle Hymn/Brightstone Ritual als separate Burst-Rituale nicht eingerechnet)
variance_amplitude:    0.32   (leicht ueber Basiswert 0.30 - Ritual-abhaengige Explosivitaet einzelner Zuege)
dead_turn_chance_base: 0.09   (nah am R-modifizierten Basiswert 0.09 (0.10*0.90))
```

### Zelle 2: Burn/Group Slug als Control

```
board_presence_growth: 0.33   (nah am R-modifizierten Control-Basiswert 0.345 (0.30*1.15) - reale Dichte 30,8%)
interaction_growth:    0.13   (Kandidat fuer leichte Absenkung vom Basiswert 0.16: reale Punkt-Entfernung 9,2%,
                                aber der eigentliche "Interaktions"-Charakter dieses Decks laeuft stark ueber
                                Damage-over-time statt klassisches Removal, siehe Reflexion)
wipe_growth:           0.02   (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.11: reale Dichte nur 1,5% -
                                Group Slug gewinnt ueber Zeit statt ueber Sweeper-Kontrolle)
combo_growth:          0.02   (Kandidat fuer Absenkung vom Basiswert 0.06: kein bestaetigter Combo gefunden)
passive_value_growth:  0.09   (Kandidat fuer DEUTLICHE Anhebung vom Basiswert 0.05: reale Dichte 9,2% (Burning
                                Earth, Manabarbs, Pyrohemia, Roiling Vortex, Spellshock, Sulfuric Vortex) - ABER
                                Modellgrenze: das Feld bildet eigentlich Karten-/Manavorteil ab, nicht laufenden
                                Direktschaden; als bestmoegliche Naeherung uebernommen, siehe Reflexion)
sac_drain_growth:      0.0    (real 0%)
disruption_growth:     0.04   (Kandidat fuer leichte Absenkung vom Basiswert 0.05: Harsh Mentor/Rampaging
                                Ferocidon real vorhanden (3,1%), ABER keine der 9 im Projekt getrackten
                                unmapped_persistent_disruption-Game-Changer - schwaechere Evidenzklasse als der
                                Zur-the-Enchanter-Befund, der den Basiswert urspruenglich stuetzt)
mana_growth:           0.12   (Kandidat fuer Absenkung vom R-modifizierten Basiswert 0.154 (0.14*1.10): reale
                                Ramp-Dichte 7,7%)
variance_amplitude:    0.24   (unter Basiswert 0.26 - stehende Damage-Engines liefern konstanten statt
                                variablen Schaden)
dead_turn_chance_base: 0.075  (nah am R-modifizierten Basiswert 0.072)
```

### Zelle 3: Artefakte/Reanimation als Control

```
board_presence_growth: 0.37   (leicht ueber dem R-modifizierten Control-Basiswert 0.345 - reale Dichte 35,9%)
interaction_growth:    0.11   (Kandidat fuer Absenkung vom Basiswert 0.16: reale Punkt-Entfernungsdichte 6,3%)
wipe_growth:           0.10   (nah am Basiswert 0.11 - reale Wipe-Dichte 6,3% (All Is Dust, Blasphemous Act,
                                Nevinyrral's Disk, Portal to Phyrexia), fuer Mono-Rot auffaellig hoch)
combo_growth:          0.085  (Kandidat fuer Anhebung vom Basiswert 0.06: Rings of Brighthearth + Basalt
                                Monolith BEIDE real vorhanden - vierter bestaetigter vollstaendiger Combo-Fund
                                des Projekts)
passive_value_growth:  0.045  (nah am Basiswert 0.05 - reale Dichte 4,7% (Trading Post, Mystic Forge, Ichor
                                Wellspring))
sac_drain_growth:      0.02   (Kandidat fuer leichte Anhebung vom Basiswert 0.01: reale Dichte 3,1% - Krark-Clan
                                Ironworks/Trading Post als Outlets, aber keine dedizierten Drain-Payoffs)
disruption_growth:     0.0    (Kandidat fuer Absenkung vom Basiswert 0.05: real 0%, keine der 9 Game-Changer
                                vorhanden)
mana_growth:           0.19   (Kandidat fuer DEUTLICHE Anhebung vom R-modifizierten Basiswert 0.154: reale
                                Ramp-Dichte 12,5% - mit Abstand hoechste des Rot-Samples, deckt sich mit dem
                                Artefakt-Toolbox-Charakter)
variance_amplitude:    0.27   (leicht ueber Basiswert 0.26 - Combo-Backup erhoeht die Explosivitaet einzelner
                                Zuege)
dead_turn_chance_base: 0.07   (nah am Basiswert 0.072)
```

### Zelle 4: Storm/Spellslinger als Aggro (nicht Goldfish, s. Befund 7)

```
board_presence_growth: 0.60   (Kandidat fuer DEUTLICHE Absenkung vom R-modifizierten Aggro-Basiswert 0.9775:
                                reale Dichte nur 32,8% - Storm-Slots gehen an Rituale/Cantrips statt Kreaturen)
interaction_growth:    0.02   (Kandidat fuer Absenkung vom Basiswert 0.035: reale Punkt-Entfernungsdichte nur
                                1,6% - niedrigste des gesamten Rot-Samples)
wipe_growth:           0.01   (Kandidat fuer leichte Anhebung von 0.0: Blasphemous Act real vorhanden, 1,6%)
combo_growth:          0.11   (Kandidat fuer MASSIVE Anhebung vom Aggro-Basiswert 0.03: Empty the Warrens,
                                Grapeshot, Past in Flames zusammen mit 4 Ritualen (Battle Hymn, Brightstone
                                Ritual, Mana Geyser, Seething Song) und Jeska's Will bilden ein dichtes
                                Sturm-Finish-Paket, real bestaetigt ueber EDHRECs eigenes "Storm 147"-Tag -
                                hoechster combo_growth-Kandidat des gesamten Rot-Samples)
passive_value_growth:  0.02   (leicht ueber Basiswert 0.01: Storm-Kiln Artist/Young Pyromancer als
                                Cast-Trigger-Value-Engines, reale Dichte 3,1%)
sac_drain_growth:      0.0    (real 0%)
disruption_growth:     0.005  (unveraendert, real 0%)
mana_growth:           0.16   (Kandidat fuer leichte Absenkung vom R-modifizierten Basiswert 0.187: reale
                                Steady-Ramp-Dichte nur 4,7%, ABER 4 zusaetzliche Burst-Rituale separat vorhanden,
                                die eher Einmal-Explosivitaet (siehe combo_growth) als stetiges mana_growth
                                abbilden)
variance_amplitude:    0.38   (Kandidat fuer DEUTLICHE Anhebung vom Aggro-Basiswert 0.30: Storm-Decks sind
                                extrem bimodal - entweder "totes" Setup oder explosiver Kill-Zug)
dead_turn_chance_base: 0.13   (Kandidat fuer Anhebung vom R-modifizierten Basiswert 0.09: die hohe Kartenzahl
                                muss erst "online" kommen, bevor der Storm-Zug funktioniert)
```

### Zelle 5: Drachen/Tribal als Midrange

```
board_presence_growth: 0.58   (Kandidat fuer leichte Absenkung vom R-modifizierten Midrange-Basiswert 0.6325
                                (0.55*1.15) - reale Dichte 45,2%)
interaction_growth:    0.06   (Kandidat fuer Absenkung vom Basiswert 0.09: reale Dichte 4,8%)
wipe_growth:           0.025  (nah am Basiswert 0.03 - reale Dichte 3,2%)
combo_growth:          0.03   (Kandidat fuer Absenkung vom Basiswert 0.05: kein bestaetigter Combo gefunden)
passive_value_growth:  0.03   (nah am Basiswert - reale Dichte 3,2% (Herald's Horn, Dragon's Hoard))
sac_drain_growth:      0.0    (Kandidat fuer DEUTLICHE Absenkung vom Basiswert 0.04: real 0%, keine
                                Opfer-Synergien im Dragons-Tribal-Shell)
disruption_growth:     0.01   (Kandidat fuer leichte Absenkung vom Basiswert 0.015: real 0%)
mana_growth:           0.14   (Kandidat fuer Absenkung vom R-modifizierten Basiswert 0.1705: reale
                                Ramp-Dichte nur 6,5%, niedriger als die Dokument-Erwartung fuer einen
                                "Big-Mana"-nahen Flavor)
variance_amplitude:    0.26   (unter Basiswert 0.28 - redundante teure Drachen-Threats puffern gegen
                                Kartenpech)
dead_turn_chance_base: 0.08   (nah am Basiswert 0.081)
```

### Zelle 6: Equipment/Voltron als Aggro

```
board_presence_growth: 0.45   (Kandidat fuer MASSIVE Absenkung vom R-modifizierten Aggro-Basiswert 0.9775:
                                reale Kreaturendichte nur 18,75% - niedrigste des Rot-Samples. Modellgrenze
                                (siehe Reflexion): Voltron konzentriert Wert auf wenige, stark ausgeruestete
                                Kreaturen statt auf Board-Breite - die reale aggressive Wirkung ist hoeher, als
                                die reine Kreaturenzahl suggeriert, Parallel-Befund zu Preston/Light-Paws
                                (Weiss, v4.48.0))
interaction_growth:    0.03   (nah am Basiswert 0.035 - reale Dichte 3,1%)
wipe_growth:           0.01   (leicht ueber 0.0 - reale Dichte 1,6%)
combo_growth:          0.02   (Kandidat fuer leichte Absenkung: kein bestaetigter Infinite, nur eine starke
                                Ashnod's Altar+Skullclamp-Value-Schleife ohne Wiederkehr-Motor)
passive_value_growth:  0.02   (leicht ueber Basiswert 0.01: Idol of Oblivion/Outpost Siege, reale Dichte 3,1%)
sac_drain_growth:      0.025  (Kandidat fuer Anhebung vom Basiswert 0.01: reale Dichte 3,1% - Ashnod's Altar,
                                Goblin Bombardment)
disruption_growth:     0.005  (unveraendert, real 0%)
mana_growth:           0.10   (Kandidat fuer DEUTLICHE Absenkung vom R-modifizierten Basiswert 0.187: reale
                                Ramp-Dichte nur 3,1%, niedrigste des Samples - Equipment-Decks investieren Mana
                                in Ausruestung statt Rocks)
variance_amplitude:    0.34   (Kandidat fuer Anhebung vom Basiswert 0.30: Voltron ist "feast or famine" - wird
                                die Schluesselkreatur entfernt, bricht der Plan zusammen)
dead_turn_chance_base: 0.12   (Kandidat fuer Anhebung vom R-modifizierten Basiswert 0.09: wenige Kreaturen
                                bedeuten haeufigere Zuege ohne sinnvolles Bord-Ziel fuer Ausruestung)
```

## Reflexion & Grenzen dieser Portion

1. Alle 24 bisherigen Zellen (6 Weiß + 6 Blau + 6 Schwarz + 6 Rot)
   bleiben Kandidaten, keine Gewichtsänderung in
   `opponent_state_weights.json`.
2. **Wichtigste methodische Entscheidung:** Zada/Storm wurde bewusst
   NICHT als `goldfish` klassifiziert, obwohl die reale Interaktions-/
   Wipe-/Disruption-Dichte fast bei null liegt — `goldfish` ist im
   Modell explizit für "kein echter Gegner" reserviert. Stattdessen
   `aggro` mit massiv angehobenem `combo_growth`-Kandidaten (0.11
   gegenüber Basiswert 0.03), was den Renn-Charakter des Decks
   sachlich treffender abbildet als eine Zuordnung, die dem Deck
   fälschlich unterstellen würde, es habe gar keine Zustandsfunktion.
3. **Neue Modellgrenze (Group Slug/Ojer Axonil):** stehende
   Schadens-Verzauberungen (Sulfuric Vortex, Manabarbs, Pyrohemia,
   Roiling Vortex) erzeugen laufenden Direktschaden gegen den Gegner,
   was weder `passive_value_growth` (Karten-/Manavorteil) noch
   `sac_drain_growth` (Opferschleifen) sauber trifft. Hilfsweise auf
   `passive_value_growth` gemappt, aber ein Kandidat für ein künftiges
   dediziertes "Damage-over-time"-Feld — dieselbe Art von Lücke wie
   beim Discard-Befund bei Tinybones (Schwarz, v4.50.0).
4. **Der R-Farbmodifikator (`board_presence: 1.15, mana_growth: 1.10,
   dead_turn_chance: 0.90`) bleibt unangetastet.** Die reale
   Board-Präsenz-Spanne dieser Portion (18,75% bis 48,4%) ist so breit,
   dass sie die bestehende Farb-weite Erwartung nicht in Frage stellt,
   sondern unterstreicht, warum die Flavor-Ebene (diese Matrix) statt
   der Farb-Ebene (`opponent_state_weights.json`) die richtige Stelle
   für diese Differenzierung ist. Weder `passive_value_growth` noch
   `sac_drain_growth` noch `disruption_growth` werden für R ergänzt:
   das Sample bestätigt die JSON-eigene Einschätzung (keine der Farb-
   Modifikator-Lücken wurde durch einen starken, wiederholten Fund
   widerlegt; die real gefundene Ojer-Disruption gehört nicht zu den 9
   getrackten Game-Changer-Karten).
5. Fortsetzung folgt unmittelbar mit Grün (inkl. Taxonomie-Abgleich
   zwischen dem 5-Flavor-Piloten v4.47.0 und dem 6-Flavor-Dokument),
   danach die 10 Gilden — derselbe Sitzungsdurchgang, wie vom Nutzer
   gewünscht.
