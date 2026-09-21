# Flavor-Strategie-Matrix — Blau, Portion 2 von 15 (v4.49.0)

## Fortsetzung der Portionierung

Zweite Portion der in v4.48.0 begonnenen Arbeit: die 90 Archetyp-Zeilen
aus den beiden Nutzer-Dokumenten (`Commander_Monofarben_Bracket_3.md`,
`Commander_Zweifarben_Gilden_Bracket_3.md`) portionsweise in das
Flavor-Strategie-Matrix-Format überführen. Diesmal: alle 6 Blau-
Archetypen. Methodik unverändert gegenüber der Weiß-Portion: die
Dokumente liefern Flavor/Commander/EDHREC-Link als Recherche-Gerüst, die
tatsächlichen Zustandsfunktionswerte werden selbst aus der echten,
verlinkten Bracket-3-Decklist ausgezählt (Tier A). Auf ausdrücklichen
Nutzerwunsch wurden die geschätzten Verteilungen in dieser Portion noch
konsequenter an der Realität kalibriert als zuvor — siehe die expliziten
"real vs. Basiswert"-Begründungen in jeder Zelle unten.

Vollständige Rohdaten mit kompletten Decklisten:
`Docs/scratch/blue_flavor_pilot_raw.md`.

## Dichte-Auswertung pro Flavor (Anteil an Nicht-Land-Karten)

| Flavor (Commander) | Board-Präsenz | Interaktion (Konter+Bounce/Removal) | Wipes | Ramp | Passive Value | Combo | Disruption |
|---|---|---|---|---|---|---|---|
| Spellslinger/Drakes (Talrand) | 15,6% (roh, siehe unten) | **31,25%** (höchster Projektwert) | 1,6% | 10,9% | 3,1% | 1 Teil | 1,6% |
| Artefakte/Combo-Control (Urza) | 30,3% | 13,6% | 0% | 12,1% | 7,6% | **4 Teile** (bestätigte Combo) | 0% |
| Mill (Bruvac) | 34,4% (verzerrt, s.u.) | 12,5% | 0% | 7,8% | 3,1% | 0 | 1,6% |
| Draw-Matters (Minn) | 34,4% | 14,1% | 0% | 7,8% | 9,4% | 2 Teile (Engine) | 0% |
| Meervolk (Svyelun) | **48,4%** (höchste) | 12,5% | 0% | 9,4% | 3,1% | 0 | 1,6% |
| Klone/Diebstahl (Orvar) | 28,8% | 9,1% (niedrigste der 3 Control-Decks) | 0% | 10,6% | 3,0% | **2-3 Teile** (bestätigte Combo) | 1,5% |

**Vier nicht-triviale Befunde dieser Portion:**
1. Blaus reale Interaktionsdichte übertrifft jeden bisherigen Weiß-Fund
   massiv (Talrand 31,25% vs. Weiß-Höchstwert 6,3%) — bestätigt den
   U-Farbmodifikator `interaction_availability: 1.45` deutlich.
2. Zwei vollständige, real bestätigte Combos gefunden (Urza: Isochron
   Scepter+Dramatic Reversal+Basalt Monolith; Orvar: Peregrine
   Drake+Ghostly Flicker) — der stärkste Combo-Befund des Projekts
   bislang.
3. Talrands Drake-Token-Mechanik zeigt eine echte Modellgrenze: rohe
   Kreaturenzahl (15,6%) unterschätzt die tatsächliche Board-Entwicklung
   bei Spell-Payoff-Commandern, weil hier 41 von 64 Nicht-Land-Karten
   selbst potenzielle Token-Trigger sind.
4. Ein echter Opfer-Outlet (Ashnod's Altar) tauchte in einem mono-
   blauen Deck (Minn) auf — schwacher, aber realer Gegenbeleg zur
   pauschalen "Blau = 0% Opfer/Drain"-Annahme.

## Die Matrix (Blau)

| Flavor \ Strategie | goldfish | aggro | midrange | control | horde |
|---|---|---|---|---|---|
| Spellslinger/Drakes | – | – | – | **✓ (Zelle 1)** | – |
| Artefakte/Combo-Control | – | – | – | **✓ (Zelle 2)** | – |
| Mill | – | – | – | **✓ (Zelle 3)** | – |
| Draw-Matters | – | – | **✓ (Zelle 4)** | – | – |
| Meervolk | – | **✓ (Zelle 5)** | – | – | – |
| Klone/Diebstahl | – | – | **✓ (Zelle 6, umklassifiziert)** | – | – |

**Blau clustert deutlich anders als Weiß:** 3 von 6 Flavors landen real
in "control" (statt einer gleichmäßigen Streuung wie bei Weiß) — das
deckt sich mit der eigenen Schnellvergleich-Einordnung des
Nutzerdokuments ("Blau: Control/Tempo"). **Zelle 6 (Klone/Diebstahl)**
wurde von "Control-Midrange" (Dokument-Label) zu reinem "midrange"
präzisiert: die reale Orvar-Liste hat die NIEDRIGSTE Interaktionsdichte
der drei Control-Kandidaten (9,1% vs. 31,25%/13,6%/12,5%) und eine
niedrige Board-Präsenz (28,8%) bei gleichzeitig starkem Combo-Signal —
ein tempo-/kombo-getriebenes Profil, das besser zu Midrange passt als zu
den beiden anderen, deutlich reaktiveren Control-Zellen.

### Zelle 1: Spellslinger/Drake-Tokens als Control

```
board_presence_growth: 0.38   (Kandidat fuer Anhebung UEBER den unmodifizierten Basiswert 0.30, TROTZ roher
                                Kreaturendichte von nur 15,6%: Talrand erzeugt bei JEDEM der 41 Nicht-Kreatur-
                                Zauber der Liste einen 2/2-Flieger - die reale effektive Boardentwicklung ist
                                deutlich hoeher, als die Kreaturenzahl allein zeigt. Modellgrenze: dieses Feld
                                misst "Kreaturen im Deck", nicht "potenzielle Token-Trigger" - siehe Reflexion)
interaction_growth:    0.26   (Kandidat fuer WEITERE Anhebung ueber den bereits U-modifizierten Basiswert
                                0.232 (0.16*1.45): reale Dichte 31,25% ist der hoechste Interaktionswert des
                                gesamten bisherigen Projekts, W und U zusammen - 20 von 64 Nicht-Land-Karten
                                sind Konter oder Bounce/Removal)
wipe_growth:           0.03   (Kandidat fuer DEUTLICHE Absenkung: unmodifizierter Basiswert 0.11 - reale
                                Dichte nur 1,6% (nur Cyclonic Rift als einseitiger Bounce-Reset, kein echter
                                Wrath-Effekt) - Blaues "Wipe" ist strukturell Tempo-Bounce, kein Permanent-Wrath)
combo_growth:          0.04   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.069 - nur Isochron
                                Scepter ohne bestaetigten zweiten Combopartner in dieser Liste)
passive_value_growth:  0.045  (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.07 - reale Dichte nur 3,1%)
sac_drain_growth:      0.0
disruption_growth:     0.03   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.06 - nur Propaganda,
                                keine dichte Stax-Haeufung wie bei Weiss/Thalia)
mana_growth:           0.11   (Kandidat fuer leichte Absenkung: U-modifizierter Basiswert 0.133 - reale
                                Dichte 10,9%)
variance_amplitude:    0.20   (Kandidat fuer DEUTLICHE Absenkung: Basiswert 0.26 - 17 Cantrips + 11 Konter
                                sind eine der dichtesten Redundanz-Haeufungen des gesamten Projekts, puffert
                                Einzelkarten-Verluste stark ab)
dead_turn_chance_base: 0.05   (Kandidat fuer Absenkung: Basiswert 0.08 - bei dieser Kartenselektionsdichte
                                sind tote Zuege selten)
```

### Zelle 2: Artefakte/Combo-Control als Control

```
board_presence_growth: 0.32   (nah am unmodifizierten Basiswert 0.30 - reale Dichte 30,3% bestaetigt)
interaction_growth:    0.16   (Kandidat fuer DEUTLICHE Absenkung vom U-modifizierten Basiswert 0.232 auf
                                naeherungsweise den UNMODIFIZIERTEN Wert: reale Dichte nur 13,6% - Urza
                                investiert deutlich mehr Slots in die Artefakt-/Mana-Engine als in reine
                                Konter-Dichte, anders als Talrand)
wipe_growth:           0.02   (Kandidat fuer DEUTLICHE Absenkung: Basiswert 0.11 - 0 dedizierte Wipes gefunden)
combo_growth:          0.11   (Kandidat fuer DEUTLICHE Anhebung: U-modifizierter Basiswert nur 0.069 - Isochron
                                Scepter, Dramatic Reversal UND Basalt Monolith sind ALLE DREI gemeinsam in
                                derselben Bracket-3-getaggten Liste vorhanden - eine bekannte, vollstaendige
                                Infinite-Mana-Combo, zusaetzlich Unwinding Clock als Redundanz. Staerkster
                                bestaetigter Combo-Fund des gesamten Projekts)
passive_value_growth:  0.065  (nah am U-modifizierten Basiswert 0.07 - reale Dichte 7,6%)
sac_drain_growth:      0.0
disruption_growth:     0.01   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.06 - kein Stax-Element
                                in dieser Liste gefunden)
mana_growth:           0.125  (nah am U-modifizierten Basiswert 0.133 - reale Dichte 12,1%)
variance_amplitude:    0.30   (ueber Basiswert 0.26 - eine Combo-Liste ist strukturell "funktioniert oder
                                funktioniert nicht", hoehere Varianz als reines Zug-um-Zug-Value-Control)
dead_turn_chance_base: 0.06   (unter Basiswert 0.08 - dichte Artefaktmana-Redundanz)
```

### Zelle 3: Mill als Control

```
board_presence_growth: 0.30   (Basiswert beibehalten TROTZ roher Dichte von 34,4% - Kandidat fuer bewusstes
                                NICHT-Anheben: die 34,4% sind fast vollstaendig durch 18 Kopien EINER Karte
                                (Persistent Petitioners) verzerrt, keine breite echte Kreaturenvielfalt)
interaction_growth:    0.15   (Kandidat fuer Absenkung vom U-modifizierten Basiswert 0.232: reale Dichte
                                nur 12,5%)
wipe_growth:           0.02   (Kandidat fuer Absenkung: Basiswert 0.11 - 0 dedizierte Wipes)
combo_growth:          0.03   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.069 - Grindstone ohne
                                Painter's-Servant-Partner in dieser Liste nicht vollstaendig, kein echter
                                Combo-Fund)
passive_value_growth:  0.045  (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.07 - reale Dichte 3,1%)
sac_drain_growth:      0.0
disruption_growth:     0.03   (nur Propaganda, aehnlich Zelle 1)
mana_growth:           0.10   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.133 - reale Dichte 7,8%)
variance_amplitude:    0.32   (Kandidat fuer Anhebung ueber Basiswert 0.26: Mill hat ein hartes, schmales
                                Win-Condition-Fenster (3 Bibliotheken muessen leer sein) - hoeheres Risiko
                                als typisches Value-Control)
dead_turn_chance_base: 0.09   (nah am Basiswert)
```

### Zelle 4: Draw-Matters/große Hand als Midrange

```
board_presence_growth: 0.52   (nah am Basiswert 0.55 - reale Dichte 34,4%)
interaction_growth:    0.13   (nah am U-modifizierten Basiswert 0.1305 - reale Dichte 14,1%, einer der
                                wenigen Faelle in dieser Portion, wo Basiswert und Realitaet fast exakt
                                uebereinstimmen)
wipe_growth:           0.01   (Kandidat fuer Absenkung: Basiswert 0.03 - 0 dedizierte Wipes)
combo_growth:          0.065  (Kandidat fuer leichte Anhebung: U-modifizierter Basiswert 0.0575 - Ashnod's
                                Altar + Skullclamp ist ein reales, wenn auch kein hartes Insta-Win-, Value-
                                Engine-Paar)
passive_value_growth:  0.07   (Kandidat fuer DEUTLICHE Anhebung: U-modifizierter Basiswert nur 0.042 - reale
                                Dichte 9,4% (Rhystic Study, Mystic Remora, Kindred Discovery, Ominous Seas,
                                Proft's Eidetic Memory, Teferi's Ageless Insight GEMEINSAM in derselben Liste,
                                zusaetzlich Draw-Kreaturen wie Consecrated Sphinx/Azami nicht mitgezaehlt))
sac_drain_growth:      0.01   (Kandidat fuer Absenkung vom Midrange-Basiswert 0.04, aber NICHT auf 0: Ashnod's
                                Altar ist ein realer Opfer-Outlet in einem mono-blauen Deck - ein schwacher,
                                aber echter Gegenbeleg zur pauschalen "Blau = 0%"-Annahme. Der Midrange-
                                Basiswert 0.04 selbst stammt aus einem schwarzen Aristokraten-Beleg-Deck und
                                ist fuer Blau klar zu hoch)
disruption_growth:     0.01
mana_growth:           0.11   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.14725 - reale Dichte 7,8%)
variance_amplitude:    0.24   (unter Basiswert 0.28 - dichte Draw-Redundanz)
dead_turn_chance_base: 0.06   (unter Basiswert 0.09 - viel Kartenselektion)
```

### Zelle 5: Meervolk als Aggro

```
board_presence_growth: 0.75   (Kandidat fuer Absenkung unter den Aggro-Basiswert 0.85: reale Dichte 48,4%
                                ist zwar die hoechste aller 6 Blau-Flavors, bleibt aber unter der Dichte
                                typischer Kreaturen-Aggro-Decks anderer Farben - Meervolk-Tempo bleibt trotz
                                "Aggro"-Einordnung strukturell zurueckhaltender)
interaction_growth:    0.09    (Kandidat fuer DEUTLICHE Anhebung ueber den U-modifizierten Aggro-Basiswert
                                0.05075: reale Dichte 12,5% ist auffaellig hoch fuer ein "Aggro"-Deck - Blaues
                                Tempo-Aggro behaelt eine fuer die Farbe typische Bounce-/Konter-Grundausstattung,
                                die reine Kreaturen-Aggro anderer Farben nicht hat)
wipe_growth:           0.01
combo_growth:          0.02   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.0345 - kein Combo-Fund)
passive_value_growth:  0.02   (leicht ueber U-modifiziertem Basiswert 0.014)
sac_drain_growth:      0.0
disruption_growth:     0.015  (leicht ueber Basiswert 0.006 - Spreading Seas)
mana_growth:           0.13   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.1615 - reale Dichte 9,4%,
                                tribale Decks kurven eher ueber Kreaturen als ueber Mana-Steine)
variance_amplitude:    0.28   (nah am Basiswert - lord-basiertes Tribal hat moderate Varianz)
dead_turn_chance_base: 0.09
```

### Zelle 6: Klone/Diebstahl als Midrange (präzisiert von "Control-Midrange")

```
board_presence_growth: 0.40   (Kandidat fuer Absenkung unter den Midrange-Basiswert 0.55: reale Dichte nur
                                28,8% - die meisten "Kreaturen" sind Klon-/Flicker-Ziele, der Sieg-Plan laeuft
                                ueber Instants (26 von 66 Nicht-Land-Karten), nicht ueber Kreaturenbreite)
interaction_growth:    0.09   (Kandidat fuer Absenkung vom U-modifizierten Midrange-Basiswert 0.1305: reale
                                Dichte nur 9,1% - die NIEDRIGSTE der drei "Control"-aehnlichen Blau-Decks
                                dieser Portion, ein Grund fuer die Umklassifizierung von "Control" zu
                                "Midrange")
wipe_growth:           0.015
combo_growth:          0.09   (Kandidat fuer DEUTLICHE Anhebung: U-modifizierter Basiswert 0.0575 - Peregrine
                                Drake + Ghostly Flicker ist eine bekannte, vollstaendige Infinite-Mana-Combo
                                mit Orvar, BEIDE Karten real in der Liste vorhanden, zusaetzlich Cloud of
                                Faeries als aehnliches Flicker-Ziel. Zweiter bestaetigter vollstaendiger
                                Combo-Fund dieser Portion nach Urza)
passive_value_growth:  0.035  (Kandidat fuer leichte Absenkung: U-modifizierter Basiswert 0.042 - reale
                                Dichte 3,0%)
sac_drain_growth:      0.0
disruption_growth:     0.018  (nah am Basiswert - Propaganda)
mana_growth:           0.13   (Kandidat fuer Absenkung: U-modifizierter Basiswert 0.14725 - reale Dichte 10,6%)
variance_amplitude:    0.32   (Kandidat fuer Anhebung ueber Basiswert 0.28: Klon-Effekte sind zielabhaengig -
                                ohne ein gutes gegnerisches Permanent auf dem Tisch ist der Plan schwaecher,
                                hoehere strukturelle Varianz)
dead_turn_chance_base: 0.10   (ueber Basiswert 0.09 - Zielabhaengigkeit kann zu toten Zuegen fuehren)
```

## Reflexion & Grenzen dieser Portion

1. Weiterhin gilt: alle 12 bisherigen Zellen (6 Weiß + 6 Blau) sind
   Kandidaten, keine Gewichtsänderung in `opponent_state_weights.json`.
2. **Neue Modellgrenze erkannt (Talrand):** analog zur Voltron-Grenze aus
   der Weiß-Portion zeigt sich bei Spell-Payoff-Commandern (Talrand,
   potenziell auch Osgir/Kalamax in künftigen Portionen), dass
   `board_presence_growth` die reale Boardentwicklung unterschätzt, wenn
   die meiste "Kreaturenerzeugung" über Token-Trigger auf Nicht-
   Kreatur-Zauber läuft statt über gelistete Kreaturenkarten.
3. **Blaus Farbmodifikatoren wirken tendenziell eher zu niedrig als zu
   hoch** — bei Weiß mussten mehrere Basiswerte nach unten korrigiert
   werden (v4.48.0), bei Blau zeigt sich das Gegenteil: die reale
   Interaktionsdichte (bis 31,25%) übertrifft selbst den bereits
   U-modifizierten Basiswert deutlich.
4. **Fortsetzungsplan unverändert:** Portion 3 = Schwarz, Portion 4 =
   Rot, Portion 5 = Grün (mit Taxonomie-Abgleich zum Grün-Piloten
   v4.47.0), Portionen 6-15 = die 10 Gilden.
