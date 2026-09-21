# Flavor-Strategie-Matrix — Grün-Pilot (v4.47.0)

## Auftrag & Format-Entscheidungen

Neuer Ansatz zu Punkt 2 (Gilden-/Cross-Dimension-Lücke): statt Farben nur
über ihre bisherigen Wachstumskurven abzubilden, soll pro Farbe (später
auch pro Gilde) eine **Flavor-Strategie-Matrix** entstehen — Zeilen sind
die typischen "Flavors" einer Farbe (bei Grün z. B. Landfall, Elfen,
Ramp/Big-Mana, große Kreaturen, +1/+1-Zähler), Spalten sind die
grundlegenden Spielweisen. Jede ausgefüllte Zelle beschreibt die
Zustandsfunktion (dieselben Größen wie `strategy_curves` in
`Data/Models/opponent_state_weights.json`) für "dieser Flavor, gespielt
als diese Strategie" — nicht jede Zelle muss belegt sein, wenn es dafür
keine echten Decks gibt.

Zwei Format-Fragen wurden vorab geklärt:
1. **Umfang:** erst EINE Farbe (Grün) als Pilot durchexerzieren, um Format
   und Vorgehen zu prüfen, bevor auf alle 5 Mono- + 10 Zweifarb-
   Identitäten (15 insgesamt) skaliert wird — zur Einordnung: die
   Orzhov-Recherche der Vorversion hat für nur 2 Sub-Strategien EINER
   Gilde bereits einen vollen Durchgang gebraucht.
2. **Spalten:** die bestehenden 5 Engine-Strategien (`goldfish, aggro,
   midrange, control, horde` aus `opponent_state_weights.json`)
   wiederverwenden statt einer neuen, parallelen Strategie-Achse — Flavor
   wird damit ein ZUSATZ zu den bestehenden Kurven, keine Konkurrenz dazu.

**Diese Version ist ausdrücklich NUR der Grün-Pilot.** Es wurde bewusst
KEINE Code-/Gewichtsänderung vorgenommen — das Ziel ist, Format und
Methodik mit dir abzustimmen, bevor der (voraussichtlich sehr
aufwendige) Durchgang auf alle 15 Identitäten ausgeweitet wird.

## Methodik

5 echte, per EDHREC-Recherche bestätigte mono-grüne Commander gewählt, je
einer pro identifiziertem Flavor (Auswahl über `edhrec.com/tags/<flavor>/
mono-green` bzw. `edhrec.com/commanders/mono-green`), deren vollständige
"Average-Deck"-Aggregatliste abgerufen und nach denselben Dimensionen
ausgezählt, die du benannt hast: echte Interaktion/Entfernung, Board-
Präsenz (Kreaturendichte), Mana-/Ramp-Dichte, passive Value-Engines,
Combo-/Alternative-Sieg-Signale, Board-Wipes, Stax/Disruption,
Opfer-/Drain-Payoffs. Rohdaten mit vollständigen Decklisten:
`Docs/scratch/green_flavor_pilot_raw.md`.

**Selbstkorrektur während der Recherche:** Lathril, Blade of the Elves
wurde zunächst (aus einer WebFetch-Zusammenfassung) fälschlich als "der
meistgespielte mono-grüne Elfen-Commander" übernommen. Gegenprüfung
(Archidekt: "Golgari Commander deck") ergab, dass Lathril tatsächlich
**Golgari (Schwarz/Grün)** ist, keine mono-grüne Identität — sie wurde
verworfen und durch Marwyn, the Nurturer (echt mono-grün, per
`edhrec.com/tags/elves/mono-green` verifiziert) ersetzt. Ein Beispiel
dafür, warum jede Farbidentitätsangabe gegenverifiziert werden muss statt
einer einzelnen Quellen-Zusammenfassung zu vertrauen.

## Die 5 gewählten Grün-Flavors

| Flavor | Commander | Quelle | Reale Decks (Tag) |
|---|---|---|---|
| Ramp/Big-Mana | Azusa, Lost but Seeking | edhrec.com/average-decks/azusa-lost-but-seeking | 9.1K (mono-green ramp) |
| Landfall | Ashaya, Soul of the Wild | edhrec.com/average-decks/ashaya-soul-of-the-wild | – |
| Elfen/Go-Wide | Marwyn, the Nurturer | edhrec.com/average-decks/marwyn-the-nurturer | 3.6K (mono-green elves) |
| Stompy/Große Kreaturen | Ghalta, Primal Hunger | edhrec.com/average-decks/ghalta-primal-hunger | – |
| +1/+1-Zähler | Vorinclex, Monstrous Raider | edhrec.com/average-decks/vorinclex-monstrous-raider | 11K (mono-green counters) |

## Dichte-Auswertung pro Flavor (Anteil an nicht-Land-Karten)

| Flavor | Board-Präsenz (Kreaturen) | Echte Interaktion/Entfernung | Mana/Ramp | Passive Value-Engines | Combo/Alt-Sieg | Wipes | Stax/Disruption | Opfer/Drain |
|---|---|---|---|---|---|---|---|---|
| Ramp/Big-Mana (Azusa) | 48% (27/56) | ~2% (nur Beast Within) | ~14% + dichtes Land-Ökosystem (Crucible, Ramunap Excavator, Scute Swarm) | **14%** (Sylvan Library, Burgeoning, Exploration, Crucible, Horn of Greed, Garruk's Uprising, The Great Henge, Case of the Locked Hothouse) | Craterhoof Behemoth (Alpha-Strike) | 0 | 0 | 0 |
| Landfall (Ashaya) | 54% (31/57) | ~2% (nur Beast Within) | **~17,5%** (höchste Ramp-Dichte aller 5 - Landfall braucht MEHR Extra-Landdrops als reines Ramp) | 12% (Guardian Project, Leyline of Abundance, Wilderness Reclamation, Exploration, Druid Class, The Great Henge) | Craterhoof Behemoth | 0 | 0 | 0 |
| Elfen/Go-Wide (Marwyn) | **58% (36/62)** (höchste Board-Präsenz aller 5) | **~4,8%** (Beast Within, Elven Ambush, Nature's Claim - deutlich mehr echte Antworten als die anderen 4) | ~13-16% (Elfen-Manadorks sind gleichzeitig Ramp UND Stammes-Payoff) | 6,5% (Sylvan Library, Guardian Project, Lifecrafter's Bestiary, Regal Force) | Craterhoof Behemoth + Staff of Domination + Umbral Mantle (kombo-näher als die anderen) | 0 | 0 | 0 |
| Stompy (Ghalta) | 53% (33/62) | **~4,8%** (Beast Within, Ram Through, Boon of Boseiju) | ~14,5% | 6,5% (Greater Good, Colossal Majesty, Garruk's Uprising, The Great Henge) | KEIN Craterhoof - reine "große Kreaturen treffen ins Gesicht" ohne Kombo-Baustein | 0 | 0 | 0 |
| +1/+1-Zähler (Vorinclex) | 47% (27/58) | ~2% (nur Beast Within) | **~17%** (Zähler-Synergiekarten sind oft selbst Manadorks: Incubation Druid, Gyre Sage) | 5% (The Great Henge, Innkeeper's Talent, Garruk's Uprising) | **Triumph of the Hordes** (echter Alternative-Sieg-Finisher, infect-artig) | 0 | 0 | 0 |

**Durchgängiger Befund über alle 5 Flavors:** 0 Board-Wipes, 0
Stax/Disruption-Karten, 0 Opfer-/Drain-Payoffs — bestätigt (mit 5
zusätzlichen unabhängigen Belegen) die bereits in `opponent_state_
weights.json` hinterlegten G-Werte (kein disruption_growth-Farbmodifikator
für Grün, keine sac_drain_growth-Beteiligung). Echte Interaktion ist
durchgängig SEHR niedrig (1 Karte: Beast Within) außer bei Elfen und
Stompy, wo sie sich real verdoppelt bis verdreifacht (Elven Ambush/Nature's
Claim bzw. Ram Through/Boon of Boseiju) — ein nicht-offensichtlicher
Flavor-Unterschied, den die reine Farb-Ebene nicht abbilden würde.

## Die Matrix

Spalten = bestehende Engine-Strategien. Nur real belegte Zellen ausgefüllt
– die übrigen sind bewusst leer, weil in dieser Stichprobe kein
entsprechendes reales Deck gefunden wurde (siehe Begründung je Flavor
unten der Matrix).

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Ramp/Big-Mana | – | – | **✓ (Zelle 1)** | – | – |
| Landfall | – | – | **✓ (Zelle 2)** | – | – |
| Elfen/Go-Wide | – | – | – | – | **✓ (Zelle 3)** |
| Stompy/Große Kreaturen | – | **✓ (Zelle 4)** | – | – | – |
| +1/+1-Zähler | – | – | **✓ (Zelle 5)** | – | – |

**Warum die leeren Zellen leer bleiben:** in keinem der 5 real
untersuchten Decks fand sich ein Beleg für eine "control"-artige
Spielweise (keine Zug-Kontrolle, kaum Removal, keine Wipes — Grün hat
schlicht nicht das Werkzeug dafür) oder eine reine "goldfish"-artige
Spielweise (jedes Deck hatte zumindest 1-3 echte Interaktionskarten). Das
deckt sich mit dem allgemein bekannten Grün-Flavor in echten EDH-Decks:
Grün ist nahezu nie die kontrollierende Farbe. Für "horde" kam nur Elfen
in Frage (Anker-Lords + hohe Kreaturendichte = Go-Wide), nicht z. B. Ramp
(zu wenige, dafür große Bedrohungen statt vieler kleiner).

### Zelle 1: Ramp/Big-Mana als Midrange

```
board_presence_growth: 0.50   (nah am midrange-Basiswert 0.55 - reale Dichte 48% bestätigt)
interaction_growth:    0.02   (Kandidat fuer Abweichung: Basiswert 0.09 ist fuer diesen Flavor zu hoch - reale Dichte nur ~2%)
wipe_growth:           0.0    (bestaetigt: 0 von 0 Wipes in der Stichprobe)
combo_growth:          0.05   (Craterhoof-Alpha-Strike vorhanden, entspricht Basiswert)
passive_value_growth:  0.05   (Kandidat fuer Anhebung: Basiswert 0.03 - reale Dichte 14% ist die zweithoechste aller 5 Flavors)
sac_drain_growth:      0.0
disruption_growth:     0.0
mana_growth:           0.20   (Kandidat fuer Anhebung: Basiswert 0.155 * G-Farbmodifikator 1.30 = 0.2015 - reale Dichte bestaetigt diesen bereits hohen Wert, keine weitere Anhebung noetig)
variance_amplitude:    0.24   (niedriger als Basiswert 0.28 - dichte Redundanz an Ramp-Effekten senkt Fehlstart-Risiko)
dead_turn_chance_base: 0.06   (niedriger als Basiswert 0.09 - praktisch jede Ramp-Karte ist ein "produktiver" Zug)
```

### Zelle 2: Landfall als Midrange

```
board_presence_growth: 0.55   (Basiswert unveraendert - reale Dichte 54% passt)
interaction_growth:    0.02   (wie Zelle 1)
wipe_growth:           0.0
combo_growth:          0.05
passive_value_growth:  0.045  (leicht niedriger als Ramp - Landfall-Decks investieren mehr Slots in Land-Redundanz statt reine Value-Engines)
sac_drain_growth:      0.0
disruption_growth:     0.0
mana_growth:           0.23   (Kandidat fuer staerkste Anhebung aller 5 Zellen: reale Dichte ~17,5% ist die hoechste der Stichprobe - Landfall braucht MEHR Extra-Landdrops als reines Ramp, um seine eigene Ressource zu vervielfachen)
variance_amplitude:    0.22   (am niedrigsten aller 5 Zellen - die dichteste Ramp-Redundanz der gesamten Stichprobe)
dead_turn_chance_base: 0.05
```

### Zelle 3: Elfen/Go-Wide als Horde

```
board_presence_growth: 1.35   (leicht ueber Basiswert 1.30 - reale Dichte 58% ist die hoechste aller 5 Flavors)
interaction_growth:    0.045  (Kandidat fuer deutliche Anhebung: Basiswert 0.02 ist fuer diesen Flavor zu niedrig - reale Dichte ~4,8%, mehr als doppelt so hoch wie die generische Horde-Kurve annimmt)
wipe_growth:           0.0
combo_growth:          0.04   (Kandidat fuer Anhebung: Basiswert 0.02 - Craterhoof+Staff of Domination+Umbral Mantle zusammen sind ein staerkeres Kombo-Signal als bei generischem Horde)
passive_value_growth:  0.015  (nah am Basiswert 0.01)
sac_drain_growth:      0.0
disruption_growth:     0.0
mana_growth:           0.20   (Elfen-Manadorks sind gleichzeitig Ramp UND Stammes-Payoff - real dichter als der Horde-Basiswert 0.19 leicht andeutet)
variance_amplitude:    0.30   (leicht niedriger als Basiswert 0.32 - viele redundante kleine Bedrohungen puffern Einzelkarten-Verluste ab)
dead_turn_chance_base: 0.06
```

### Zelle 4: Stompy/Große Kreaturen als Aggro

```
board_presence_growth: 0.80   (nah am Aggro-Basiswert 0.85 - reale Dichte 53%, aber jede Kreatur ist deutlich groesser/wirkungsvoller als eine typische Aggro-Kreatur)
interaction_growth:    0.045  (Kandidat fuer deutliche Anhebung: Basiswert 0.035 - reale Dichte ~4,8%, genau wie bei Elfen deutlich mehr echte Antworten als die generische Aggro-Kurve annimmt)
wipe_growth:           0.0
combo_growth:          0.02   (Kandidat fuer Absenkung: Basiswert 0.03 - KEIN Craterhoof/Kombo-Baustein in dieser Stichprobe, reine "grosse Kreaturen"-Schwelle ohne Kombo-Anspruch)
passive_value_growth:  0.02   (leicht ueber Basiswert 0.01 - Greater Good/Colossal Majesty als echte, wenn auch duenne Value-Schicht)
sac_drain_growth:      0.0
disruption_growth:     0.0
mana_growth:           0.19   (nah am Basiswert 0.17 - Ramp dient hier v. a. dazu, die grossen Kreaturen frueher zu ermoeglichen, nicht als eigenstaendiges Value-Engine wie bei Zelle 1/2)
variance_amplitude:    0.30   (nah am Basiswert - wenige, aber sehr wirkungsvolle Bedrohungen bedeuten hohe Varianz, sobald eine davon beantwortet wird)
dead_turn_chance_base: 0.08
```

### Zelle 5: +1/+1-Zähler als Midrange

```
board_presence_growth: 0.50
interaction_growth:    0.02
wipe_growth:           0.0
combo_growth:          0.06   (Kandidat fuer leichte Anhebung: Basiswert 0.05 - Triumph of the Hordes ist ein echter, eigenstaendiger Alternative-Sieg-Finisher, kein reiner Alpha-Strike wie Craterhoof)
passive_value_growth:  0.035  (nah am Basiswert)
sac_drain_growth:      0.0
disruption_growth:     0.0
mana_growth:           0.21   (Kandidat fuer Anhebung: reale Dichte ~17% - Zaehler-Synergiekarten sind ueberraschend oft selbst Manadorks, ein nicht offensichtlicher Befund)
variance_amplitude:    0.26
dead_turn_chance_base: 0.07
```

## Reflexion zum Format (vor der Skalierung auf alle 15 Identitäten)

1. **Dichte-Werte sind Kalibrierungs-KANDIDATEN, keine sofortigen
   Gewichtsänderungen** — genau wie bei der ursprünglichen v4.39.0/
   v4.40.0-Kalibrierung sind das echte Dichte-Verhältnisse aus EINEM Deck
   pro Zelle, keine breite Stichprobe. Für eine tatsächliche Integration
   in `opponent_state_weights.json` bräuchte es mehrere Decks pro Zelle
   (wie bei der Moxfield/Orzhov-Recherche der Vorversion).
2. **Nicht jede Zelle lässt sich sauber einer einzigen Strategie
   zuordnen** — z. B. könnte man Elfen/Go-Wide auch als "aggro" statt
   "horde" lesen. Diese Version hat sich für die Strategie entschieden,
   die dem echten Decklisten-Muster am nächsten kommt (siehe Begründung
   je Zelle), aber das ist eine Interpretationsentscheidung, keine
   objektive Ableitung.
3. **Aufwand pro Farbe:** dieser Grün-Pilot (5 Flavors, je 1 Deck) hat 5
   EDHREC-Abrufe plus Recherche zur Flavor-/Commander-Auswahl gebraucht —
   deutlich weniger als die Moxfield-Rate-Limit-Problematik der
   Orzhov-Runde, weil EDHREC-Average-Decks zuverlässig und schnell
   abrufbar sind. Für 15 Identitäten (5 mono + 10 zweifarbig) mit je
   3-5 Flavors wären das realistisch 45-75 weitere Abrufe — machbar über
   mehrere Sitzungen, nicht in einer.
4. **Offene Frage an dich:** passt dieses Format (5 Flavors pro Farbe,
   Dichte-Tabelle, Matrix mit bewusst leeren Zellen, State-Function pro
   belegter Zelle mit "Kandidat für Verfeinerung"-Kennzeichnung), oder
   soll ich etwas daran ändern, bevor ich es auf die restlichen 4
   Monofarben und die 10 Zweifarb-Identitäten ausweite?
