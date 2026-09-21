# Flavor-Strategie-Matrix — Weiß, Portion 1 von 15 (v4.48.0)

## Auftrag & Ausgangslage

Der Nutzer hat zwei ChatGPT-recherchierte Dokumente in den `Docs`-Ordner
gelegt: `Commander_Monofarben_Bracket_3.md` (5 Farben × 6 Archetypen) und
`Commander_Zweifarben_Gilden_Bracket_3.md` (10 Gilden × 6 Archetypen) —
zusammen 90 Archetyp-Zeilen. Grund: die manuelle Moxfield-/EDHREC-
Recherche der Vorversionen war für den angestrebten Umfang zu langsam.
Auftrag: diese Profile in eine "detaillierte Ausarbeitung" überführen,
die das Projekt-Format (Flavor-Strategie-Matrix, siehe Grün-Pilot
v4.47.0) sauber abbildet — portioniert über mehrere Sitzungen, mit
offener Frage nach hilfreichen "Plugins".

## Bewertung der beiden Nutzer-Dokumente

Beide Dokumente sind **strukturell gut und im Kern vertrauenswürdig**:
- Jeder Archetyp verlinkt eine ECHTE EDHREC-`average-decks/<commander>/
  upgraded`-Seite (Bracket-3-Filter). Stichprobe: alle 6 Weiß-Links wurden
  in dieser Sitzung geöffnet — alle 6 existieren, zeigen den genannten
  Commander und den aktiven Bracket-3-Filter.
- Farbidentitäten sind korrekt: Lathril, Blade of the Elves wird im
  Gilden-Dokument korrekt als Golgari (Schwarz/Grün) geführt — exakt der
  Fehler, den ich selbst im Grün-Piloten (v4.47.0) zunächst gemacht und
  dann korrigiert hatte. Das ist ein starkes Qualitätssignal.
- Die Dokumente benennen ihre eigenen Grenzen ehrlich (EDHREC-Average-
  Decks sind dynamische Nutzer-Aggregate, keine kuratierten Einzellisten;
  Bracket-Selbstangabe statt redaktioneller Prüfung) — das deckt sich mit
  der bereits in diesem Projekt etablierten Vorsicht gegenüber EDHREC als
  Quelle.
- **Aber:** die angegebenen Rollenprofil-Kartenzahlen (Länder/Ramp/
  Kartenfluss/Punkt/Wipes/Stack/Schutz/Kern) sind erkennbar generische
  Archetyp-Einschätzungen, keine Auszählung der jeweils VERLINKTEN Liste
  selbst. Bei 4 von 6 in dieser Portion geprüften Weiß-Decks liegt die
  reale Ramp-Dichte spürbar unter der Dokument-Angabe (siehe Rohdaten).

**Daraus folgt die Methodik für diese und alle künftigen Portionen:**
Die beiden Dokumente werden als **Recherche-Gerüst** genutzt (welcher
Flavor, welcher Commander, welcher EDHREC-Link) — das spart genau den
Schritt, der in der Orzhov-/Moxfield-Runde am meisten Zeit gekostet hat
(die Commander-/Flavor-Auswahl selbst). Die tatsächlichen Zustands-
funktionswerte werden aber weiterhin **selbst aus der echten,
verlinkten Decklist ausgezählt** — genau wie beim Grün-Piloten. Damit
bleibt die Evidenzqualität unverändert hoch (Tier A: echte Decklisten,
selbst ausgezählt), während der langsamste Teil des bisherigen Prozesses
(Commander-Recherche) entfällt. Das ist keine Abkehr vom "nie erfundene
Zahlen"-Prinzip, sondern eine Effizienzsteigerung genau an der Stelle,
an der sie unbedenklich ist.

## Zur "Plugins"-Frage

Es wird **kein zusätzliches Plugin benötigt**. Der eingebaute Browser
(dieselbe Technik wie beim Grün-Piloten) öffnet alle 6 EDHREC-Links
dieser Portion ohne das von Moxfield bekannte Rate-Limit-Problem
(v4.46.0) — EDHREC scheint dafür deutlich robuster zu sein. Sollte sich
das über mehr Abrufe hinweg ändern, wird das wie bei Moxfield dokumentiert.

## Methodik dieser Portion

Alle 6 Weiß-Archetypen aus `Commander_Monofarben_Bracket_3.md`
übernommen (Tokens/Go-Wide, Auren/Ausrüstung/Voltron, Engel/Flying,
Lifegain/+1+1-Counter, Blink/ETB, Taxes/Hatebears/Pillowfort), deren
jeweils referenzierter EDHREC-"Average Deck – Upgraded" real abgerufen
und nach denselben Dimensionen wie beim Grün-Piloten ausgezählt: Board-
Präsenz, echte Punkt-Entfernung, Wipes, Stack/Gegenzauber, Ramp, passive
Value-Engines, Combo/Alt-Sieg-Signale, Opfer-/Drain-Payoffs, Disruption/
Stax. Vollständige Rohdaten mit kompletten Decklisten:
`Docs/scratch/white_flavor_pilot_raw.md`.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Punkt-Entfernung | Wipes | Ramp | Passive Value | Combo | Disruption/Stax |
|---|---|---|---|---|---|---|---|
| Tokens/Go-Wide (Myrel) | 42,9% | 4,8% | 3,2% (2) | 6,3% | 6,3% | 0 | 0 |
| Voltron (Light-Paws) | **21,9%** (niedrigste) | 3,1% | 1,6% (1) | 4,7% | 4,7% | 0 | 0 |
| Engel/Flying (Giada) | 49,2% | 4,6% | 4,6% (3) | 10,8% | 9,2% | 0 | 1,5% |
| Lifegain/Counter (Heliod) | 48,4% | 6,3% | 6,3% (4, höchste) | 6,3% | 9,4% | **2 Teile** (Ballista+Triskelion) | 3,1% |
| Blink/ETB (Preston) | 50,8% | 6,2% | **1,5%** (1, niedrigste) | 9,2% | 4,6% | Engine-Schleife | 0 |
| Taxes/Hatebears (Thalia) | **61,9%** (höchste) | 4,8% | 3,2% (2) | 4,8% | 9,5% | 0 | **22,2%** (14 Karten, mit Abstand höchster Projektwert) |

**Drei nicht-triviale Befunde dieser Portion:**
1. **Ramp wird im Nutzerdokument systematisch überschätzt** (siehe
   Bewertung oben) — bei 4 von 6 Flavors real deutlich niedriger.
2. **Wipe-Dichte variiert innerhalb Weiß stark nach Flavor** (1,5% bei
   Preston bis 6,3% bei Heliod) statt gleichmäßig hoch zu sein, wie es
   ein reiner Farb-Multiplikator (`wipe_readiness: 1.30` für W)
   nahelegen würde.
3. **Board-Präsenz korreliert nicht mit dem Strategie-Label**: das
   "Control"-gelabelte Taxes/Hatebears-Deck hat die höchste
   Kreaturendichte aller 6 Weiß-Flavors (61,9%) UND gleichzeitig die
   höchste je in diesem Projekt gefundene Disruption-/Stax-Dichte
   (22,2%, 14 Karten) — moderne Hatebears-Karten sind fast ausschließlich
   Kreaturen, nicht Verzauberungen/Artefakte wie das generische Stax-
   Modell unterstellt.

## Die Matrix (Weiß)

Spalten = bestehende Engine-Strategien (`goldfish, aggro, midrange,
control, horde`). Strategiezuordnung folgt der REALEN Dichte, nicht
immer dem Label aus dem Nutzerdokument (siehe Anmerkungen je Zelle).

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Tokens/Go-Wide | – | – | – | – | **✓ (Zelle 1)** |
| Voltron (Auren/Ausrüstung) | – | **✓ (Zelle 2)** | – | – | – |
| Engel/Flying | – | – | **✓ (Zelle 3)** | – | – |
| Lifegain/+1+1-Counter | – | – | **✓ (Zelle 4)** | – | – |
| Blink/ETB | – | – | **✓ (Zelle 5, umklassifiziert)** | – | – |
| Taxes/Hatebears/Pillowfort | – | – | – | **✓ (Zelle 6)** | – |

**Zelle 5 (Blink/ETB) wurde bewusst von "Value-Control" (Dokument-Label)
zu "midrange" umklassifiziert:** die reale Preston-Liste zeigt hohe
Board-Präsenz (50,8%, dritthöchste aller 6) und die NIEDRIGSTE
Wipe-Dichte der gesamten Weiß-Stichprobe (1,5%) — beides untypisch für
"control" in diesem Modell (control-Basiswert: `board_presence_growth
0.30`, `wipe_growth 0.11`, also niedrige Präsenz UND hohe Wipe-Bereit-
schaft). Ein Blink-Deck will seine eigenen Kreaturen am Leben halten, um
sie wiederholt zu blinken — es investiert daher strukturell WENIGER in
eigene Wipes als andere weiße Kontrolldecks. Das ist derselbe Befund-Typ
wie die Lathril-Korrektur im Grün-Piloten: eine plausible Label-
Übernahme wurde durch echte Decklisten-Daten widerlegt und korrigiert,
bevor sie in eine Zustandsfunktion eingeflossen wäre.

### Zelle 1: Tokens/Go-Wide als Horde

```
board_presence_growth: 1.30   (nah am horde-Basiswert*W-Modifikator 1.365 - reale Dichte 42,9% liegt in der Mitte
                                der bisherigen Horde-/Go-Wide-Beispiele; Anthems/Doubler kompensieren die im
                                Vergleich zu Gruen-Elfen (58%) niedrigere reine Kreaturenzahl)
interaction_growth:    0.045  (Kandidat fuer Anhebung: horde-Basiswert 0.02 zu niedrig - reale Dichte 4,8%,
                                deckungsgleich mit den Gruen-Pilot-Werten fuer aehnlich hohe reale Interaktion)
wipe_growth:           0.02   (Kandidat fuer Abweichung von 0.0: horde geht i.d.R. von 0 Wipes aus, aber DIESES
                                Weiss-Go-Wide-Deck fuehrt real 2 Wipes/Pseudo-Wipes (Farewell, Martial Coup) -
                                ein Weiss-spezifischer Unterschied zu Gruens 0-Wipe-Befund bei Horde/Elfen)
combo_growth:          0.015  (kein echter Kombo-Baustein gefunden, leicht unter Basiswert 0.02)
passive_value_growth:  0.02   (Kandidat fuer Anhebung: Basiswert*W-Modifikator 0.0125 - reale Dichte 6,3% ist
                                doppelt so hoch wie beim generischen Horde-Ansatz unterstellt)
sac_drain_growth:      0.0    (Kandidat fuer Absenkung: horde-Basiswert 0.02 - real 0 Opferteile in der Liste)
disruption_growth:     0.0
mana_growth:           0.14   (Kandidat fuer Absenkung: Basiswert 0.19 - reale Ramp-Dichte nur 6,3%, Weiss-
                                Go-Wide investiert in Anthems/Token-Motoren statt in klassischen Ramp)
variance_amplitude:    0.29   (leicht unter Basiswert 0.32 - 2 redundante Anthems (Field Marshal, Daru
                                Warchief) puffern Einzelkarten-Verluste ab)
dead_turn_chance_base: 0.07
```

### Zelle 2: Voltron (Auren/Ausrüstung) als Aggro

```
board_presence_growth: 0.55   (Kandidat fuer DEUTLICHE Absenkung: aggro-Basiswert*W-Modifikator 0.8925 - reale
                                Board-Praesenz ist mit 21,9% die NIEDRIGSTE aller 6 Weiss-Flavors. Wichtige
                                Modellgrenze: Voltron gewinnt ueber konzentrierten Schaden auf 1-2 Kreaturen,
                                nicht ueber Breite - das bildet dieses Feld strukturell nicht ideal ab, siehe
                                Reflexion unten)
interaction_growth:    0.04   (leicht ueber Basiswert 0.035 - reale Dichte inkl. 1 Gegenzauber ~4,7%)
wipe_growth:           0.01   (Kandidat fuer Abweichung von 0.0: 1 einseitiger Wipe (Winds of Rath) real
                                vorhanden, aber die mit Abstand niedrigste Wipe-Dichte aller 6 Flavors)
combo_growth:          0.02   (kein Kombo-Baustein, leicht unter Basiswert 0.03)
passive_value_growth:  0.02   (Kandidat fuer Anhebung: Basiswert*W-Modifikator 0.0125 - Aura-Draw-Trigger
                                (Mesa Enchantress, Starfield Mystic, Sage's Reverie) liefern real 4,7% Dichte)
sac_drain_growth:      0.0
disruption_growth:     0.006
mana_growth:           0.12   (Kandidat fuer Absenkung: Basiswert 0.17 - reale Ramp-Dichte nur 4,7%, Voltron
                                will effiziente Auren statt Mana)
variance_amplitude:    0.36   (Kandidat fuer DEUTLICHE Anhebung: Basiswert 0.30 - strukturell hohe Varianz,
                                weil der gesamte Plan an 1-2 Kreaturen haengt; ein einzelnes Removal auf den
                                Traeger kann das gesamte Deck lahmlegen)
dead_turn_chance_base: 0.12   (ueber Basiswert 0.10 - Auren ohne passenden Traeger auf der Hand sind tote Zuege)
```

### Zelle 3: Engel/Flying als Midrange

```
board_presence_growth: 0.58   (nah am Basiswert*W-Modifikator 0.5775 - reale Dichte 49,2% bestaetigt)
interaction_growth:    0.05   (Kandidat fuer Absenkung: Basiswert 0.09 - reale Punkt-Entfernung nur 4,6%)
wipe_growth:           0.045  (Kandidat fuer leichte Anhebung: Basiswert*W-Modifikator 0.039 - reale Dichte
                                4,6% deckt sich mit der Dokument-Angabe "3-4 Wipes", einer der wenigen Faelle
                                in dieser Portion, wo die Dokument-Schaetzung real bestaetigt wurde)
combo_growth:          0.03   (Kandidat fuer Absenkung: Basiswert 0.05 - kein echter Kombo-Baustein gefunden)
passive_value_growth:  0.06   (Kandidat fuer DEUTLICHE Anhebung: Basiswert*W-Modifikator 0.0375 - reale Dichte
                                9,2% ist die zweithoechste aller 6 Flavors: Smothering Tithe, Land Tax,
                                Luminarch Ascension, Angelic Accord, Court of Grace, Authority of the Consuls
                                GEMEINSAM in derselben Liste)
sac_drain_growth:      0.0    (bestaetigt die bestehende W-Farb-Annahme: keine Opferteile)
disruption_growth:     0.018  (nah am Basiswert*W-Modifikator - nur Authority of the Consuls)
mana_growth:           0.145  (leicht unter Basiswert 0.155 - reale Dichte 10,8% inkl. Kostenreduktion)
variance_amplitude:    0.30   (leicht ueber Basiswert - teure Engel-Kurve ohne viel Redundanz im unteren Bereich)
dead_turn_chance_base: 0.09
```

### Zelle 4: Lifegain/+1+1-Counter als Midrange

```
board_presence_growth: 0.55   (nah am Basiswert*W-Modifikator 0.5775 - reale Dichte 48,4%)
interaction_growth:    0.06   (Kandidat fuer Absenkung: Basiswert 0.09 - reale Punkt-Entfernung 6,3%)
wipe_growth:           0.05   (Kandidat fuer Anhebung: Basiswert*W-Modifikator 0.039 - reale Dichte 6,3% ist
                                die HOECHSTE aller 6 Weiss-Flavors, hoeher als die Dokument-Angabe "2-3 Wipes")
combo_growth:          0.08   (Kandidat fuer DEUTLICHE Anhebung: Basiswert 0.05 - Walking Ballista UND
                                Triskelion sind BEIDE real in derselben Bracket-3-getaggten Liste vorhanden,
                                eine bekannte Heliod-Zwei-Karten-Combo-Gefahr, die das Nutzerdokument selbst
                                explizit benennt und hier real bestaetigt wird)
passive_value_growth:  0.06   (Kandidat fuer Anhebung: Basiswert*W-Modifikator 0.0375 - reale Dichte 9,4%)
sac_drain_growth:      0.0
disruption_growth:     0.025  (leicht ueber Basiswert*W-Modifikator 0.018 - Blind Obedience + Ghostly Prison)
mana_growth:           0.12   (Kandidat fuer Absenkung: Basiswert 0.155 - reale Ramp-Dichte nur 6,3%, deutlich
                                unter der Dokument-Angabe "8-10 Ramp")
variance_amplitude:    0.27
dead_turn_chance_base: 0.08
```

### Zelle 5: Blink/ETB als Midrange (umklassifiziert von "Control")

```
board_presence_growth: 0.62   (Kandidat fuer Anhebung: Basiswert*W-Modifikator 0.5775 - reale Dichte 50,8% ist
                                die dritthoechste aller 6 Flavors - fast jede Karte im Deck MUSS eine Kreatur
                                mit ETB-Effekt sein, damit der Blink-Plan funktioniert)
interaction_growth:    0.055  (nah am angepassten Midrange-Wert - reale Dichte 6,2%)
wipe_growth:           0.02   (Kandidat fuer DEUTLICHE Absenkung: Basiswert*W-Modifikator 0.039 - reale Dichte
                                nur 1,5% (1 Wipe), die niedrigste aller 6 Weiss-Flavors trotz hohem W-Wipe-
                                Modifikator - ein Blink-Deck will die eigenen Kreaturen am Leben halten)
combo_growth:          0.06   (leicht ueber Basiswert 0.05 - Panharmonicon+Conjurer's Closet als reale,
                                wiederholbare Engine-Schleife, aber kein harter Insta-Win wie bei Heliod)
passive_value_growth:  0.04   (nah am Basiswert*W-Modifikator - reale Dichte 4,6%)
sac_drain_growth:      0.0
disruption_growth:     0.01
mana_growth:           0.13   (leicht unter Basiswert 0.155 - reale Dichte 9,2%)
variance_amplitude:    0.25   (unter Basiswert - viele ETB-Ziele sind untereinander redundant austauschbar)
dead_turn_chance_base: 0.07
```

### Zelle 6: Taxes/Hatebears/Pillowfort als Control

```
board_presence_growth: 0.58   (Kandidat fuer DEUTLICHE Anhebung: Basiswert*W-Modifikator NUR 0.315 - reale
                                Dichte 61,9% ist die HOECHSTE aller 6 Weiss-Flavors trotz "control"-Label.
                                Wichtiger Modellbefund: das generische "control = wenig Board" nimmt an, dass
                                Stax/Disruption ueber Verzauberungen/Artefakte laeuft - moderne Hatebears sind
                                aber fast ausschliesslich Kreaturen)
interaction_growth:    0.08   (Kandidat fuer Absenkung: Basiswert 0.16 - reale reine Punkt-Entfernung nur
                                4,8% (+2 Gegenzauber-aehnliche Karten); ein Grossteil der "Interaktion" dieses
                                Decks laeuft ueber die Disruption-Kreaturen selbst, nicht ueber Punkt-Removal)
wipe_growth:           0.05   (Kandidat fuer Absenkung: Basiswert*W-Modifikator 0.143 - reale Dichte nur 3,2%
                                (2 Wipes), deutlich unter dem generischen Control-Anspruch)
combo_growth:          0.02   (Kandidat fuer Absenkung: Basiswert 0.06 - kein Kombo-Baustein gefunden)
passive_value_growth:  0.07   (Kandidat fuer Anhebung: Basiswert*W-Modifikator 0.0625 - reale Dichte 9,5%)
sac_drain_growth:      0.0
disruption_growth:     0.15   (STAERKSTER Einzelbefund dieser Portion, Kandidat fuer MASSIVE Anhebung:
                                Basiswert*W-Modifikator nur 0.06 - reale Dichte 22,2% (14 von 63 Nicht-Land-
                                Karten: Archon of Emeria, Aven Mindcensor, Drannith Magistrate, Eidolon of
                                Rhetoric, Ethersworn Canonist, Hushbringer, Leonin Arbiter, Spirit of the
                                Labyrinth, Vryn Wingmare, Thorn of Amethyst, Deafening Silence, Ghostly Prison,
                                Blind Obedience, Authority of the Consuls) ist mit Abstand die hoechste je in
                                diesem Projekt gefundene Disruption-Dichte - der bisherige Hoechstwert war Zur
                                the Enchanter mit 2 von 9 unmapped_persistent_disruption-Karten, v4.42.0)
mana_growth:           0.09   (Kandidat fuer DEUTLICHE Absenkung: Basiswert 0.14 - reale Ramp-Dichte nur 4,8%,
                                deutlich unter der Dokument-Angabe "8-10 Ramp" - Taxes-Decks sind kurvenbasiert
                                und effizient, nicht ramp-lastig)
variance_amplitude:    0.22   (unter Basiswert 0.26 - viele redundante kleine Stax-Kreaturen, niedrige Varianz)
dead_turn_chance_base: 0.06   (unter Basiswert 0.08 - die meisten Stax-Kreaturen sind guenstige 1-2-Mana-Zuege)
```

## Reflexion & Grenzen dieser Portion

1. **Alle 10 Zustandsfunktions-Zellen sind weiterhin KANDIDATEN, keine
   Gewichtsänderung** — dieselbe Regel wie beim Grün-Piloten. Für eine
   tatsächliche Integration in `opponent_state_weights.json` bräuchte es
   mehrere Decks pro Zelle statt einem.
2. **Modellgrenze bei Voltron erkannt:** `board_presence_growth` bildet
   Voltron-Decks strukturell schlecht ab, weil ihr Sieg über
   konzentrierten Schaden auf 1-2 Kreaturen läuft, nicht über Breite.
   Eine mögliche künftige Erweiterung (nicht in dieser Version
   umgesetzt): ein eigenes "Konzentrations-Signal" pro Flavor, das
   niedrige Board-Präsenz + hohe Passive-Value/Schutz-Dichte als
   "Voltron-Typ" statt als "schwache Aggro-Variante" kennzeichnet.
3. **Thalia/Taxes-Hatebears ist der bislang stärkste Einzelbefund** in
   der gesamten Flavor-Strategie-Matrix-Arbeit (22,2% Disruption-Dichte)
   und sollte bei einer echten Kalibrierung Priorität vor den übrigen 89
   Zeilen bekommen.
4. **Portionierungsplan für die Fortsetzung** (wie vom Nutzer
   ausdrücklich über mehrere Sitzungen erlaubt):
   - Portion 2: Blau (6 Archetypen)
   - Portion 3: Schwarz (6 Archetypen)
   - Portion 4: Rot (6 Archetypen)
   - Portion 5: Grün-Monofarbe NEU nach der 6-Flavor-Taxonomie des
     Nutzerdokuments (die überschneidet sich mit, ist aber nicht
     identisch zu den 5 Flavors des Grün-Piloten v4.47.0 - Abgleich
     nötig, siehe unten)
   - Portionen 6-15: die 10 Zweifarb-Gilden aus
     `Commander_Zweifarben_Gilden_Bracket_3.md`, je 1 Gilde pro Portion
   - Danach optional: Zusammenführung aller 15 Matrizen in eine
     Gesamtübersicht und Diskussion, welche Kandidatenwerte tatsächlich
     in `opponent_state_weights.json` übernommen werden sollen.
5. **Offener Abgleichspunkt Grün:** das neue Monofarben-Dokument listet
   6 Grün-Flavors (Lands/Landfall, Elfball, Stompy, +1/+1-Counter/
   Go-Tall, Tokens/Go-Wide, Creature Toolbox/Flash), der Grün-Pilot
   hatte 5 andere (Ramp/Big-Mana separat von Landfall, kein Tokens/
   Go-Wide, kein Toolbox/Flash). Empfehlung: bei Portion 5 die
   6-Flavor-Taxonomie des Nutzerdokuments übernehmen (sie deckt mit
   Toolbox/Flash und reinem Tokens/Go-Wide zwei reale Muster ab, die der
   Pilot nicht hatte) und die 5 Pilot-Zellen dort einsortieren, wo sie
   passen, statt beide Versionen parallel zu pflegen.
