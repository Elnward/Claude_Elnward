# Color-Value-Pilot v1 — Rot (Draw / Interaction / Board Wipe)

**Status: PILOT / ENTWURF — noch NICHT in `ValueModel`/`engine.py` eingebaut.**
Dies ist die vom Nutzer angeforderte Rot-only-Pilotstudie, bevor der Aufwand auf alle 5 Farben und die restlichen Kategorien (Keywords, Power+Toughness) sowie das vollständige "Baukastensystem" (Kartentyp/Keyword-Kompositionsformel) ausgeweitet wird. Ergebnis ist zum Gegenlesen gedacht — keine Codeänderung, kein neuer `ENGINE_VERSION`.

## 0. Ausgangsfrage

> "Wenn ich jetzt in Rot bin, ich hab einen Drawspell für fünf Mana, muss mir das was bringen — oder: eine Karte ziehen kostet in Rot normalerweise so viel."

Die Idee: pro Farbe und Kategorie eine Erwartungs-Baseline pro Manawert aufbauen, gegen die eine konkrete Karte als über- oder unterdurchschnittlich bewertet werden kann.

## 1. Datenlage — was tatsächlich verfügbar war

- **Scryfall (API & Website) ist aus dieser Sandbox heraus nicht erreichbar** (beide Zugriffe lieferten HTTP 403). Das deckt sich mit der bereits in `COWORK_HANDOFF.md` §7 dokumentierten Einschränkung.
- **EDHREC ist erreichbar** und liefert echte Deck-Inclusion-/Synergie-Prozentsätze pro Tag+Farbe. Das ist die Datengrundlage dieser Pilotstudie.
- EDHREC liefert **keine** Manakosten oder Oracle-Text direkt — nur Kartennamen + Inclusion-%/Synergie-%/Deck-Anzahl. Manakosten und Karteneffekte der unten zitierten Karten stammen aus meinem eigenen MTG-Wissen und sind **nicht live gegen Scryfall verifiziert** in dieser Session. Das ist eine bewusste, transparente Einschränkung dieser Pilotstudie — keine stille Annahme.
- EDHREC hat **keinen eigenen "Removal"- oder "Board-Wipe"-Tag** für Mono-Rot. Der nächstliegende echte Tag ist `control` (mono-red), der Removal und Board-Wipes vermischt enthält. Die Board-Wipe-Kategorie unten ist deshalb schwächer datengestützt als Draw und Interaction — das wird explizit markiert.

## 2. Kategorie: Draw (Kartenziehen)

Quelle: `edhrec.com/tags/card-draw/mono-red`, 519 analysierte Mono-Rot-Decks.

| Karte | Manakosten (mein Wissen, nicht live verifiziert) | Effekt | EDHREC-Inclusion |
|---|---|---|---|
| Thrill of Possibility | {1}{R} (2) | Instant: Wirf 1 ab, ziehe 2 | 62% (323 Decks) |
| Faithless Looting | {R} (1)* | Sorcery: Ziehe 2, wirf 2 ab | 62% (321 Decks) |
| Tormenting Voice | {1}{R} (2) | Sorcery: Wirf 1 ab, ziehe 2 | 48% (247 Decks) |
| Unexpected Windfall | {1}{R} (2) | Sorcery: Wirf 1 ab, ziehe 2 (+Treasure bei Land) | 53% (276 Decks) |
| Cathartic Reunion | {1}{R} (2) | Sorcery: Wirf 2 ab, ziehe 3 | 45% (235 Decks) |
| Demand Answers | {2}{R} (3) | Sorcery: Top 4 ansehen, 1 nichtLand/nichtKreatur nehmen, Gegner legt ab | 53% (276 Decks) |

*Faithless Looting ist {R}, also 1 Mana — die 62%-Inclusion trotz Netto-0-Kartenvorteil (2 gezogen, 2 abgeworfen) zeigt, wie stark reines Filtern in Rot geschätzt wird, wenn es billig genug ist.

**Befund**: Rot hat auf Commander-Ebene praktisch keinen "sauberen" Draw-Spell. Der Baseline-Shape bei 2 Mana ist ein **Loot** (ziehe 2, wirf 1 ab) — das ergibt einen Netto-Kartenvorteil von **+1 Karte für 2 Mana**, nicht "ziehe 2 für 2 Mana" wie z. B. in Blau (Divination). Bei 1 Mana ist sogar Netto-0 (Faithless Looting) noch stark gespielt, weil Filtern selbst schon Wert hat.

**Für die Ausgangsfrage (5-Mana-Drawspell in Rot)**: In den EDHREC-Top-Karten für Mono-Rot-Card-Draw taucht **keine** einseitige Draw-Karte bei 5 Mana auf. Rot skaliert Kartenvorteil bei steigenden Manakosten nicht linear nach oben — die einzigen bekannten Hochkosten-Effekte sind **symmetrische** Wheel-Effekte (alle Spieler ziehen neu), die eine andere Werte-Kategorie sind (Board-weiter Reset, kein reiner Kartenvorteil). Ehrliches Ergebnis: **es gibt keine belastbare Baseline "5 Mana Draw in Rot"** — eine Karte in diesem Kostenbereich sollte nicht an einem erfundenen Kartenvorteils-Zielwert gemessen werden, sondern daran, ob sie zusätzlichen Nebennutzen (Schaden, Treasure, Symmetrie-Vorteil durch eigene leere Hand) liefert, der die fehlende Präzedenz kompensiert.

**Vorschlag für die Baseline-Zahl** (zur Diskussion):

```
draw_baseline_R:
  mv1: net_cards ≈ 0.0   (Filtern allein reicht bei 1 Mana)
  mv2: net_cards ≈ +1.0  (Loot-Standard: ziehe 2, wirf 1 ab)
  mv3: net_cards ≈ +1.0, aber mit Selektion/Gegner-Störung statt mehr Karten
  mv5: keine belastbare Präzedenz — nicht an Kartenzahl messen
```

## 3. Kategorie: Interaction (Removal)

Quelle: `edhrec.com/tags/control/mono-red`, 727 analysierte Decks (kein reiner "Removal"-Tag vorhanden, `control` ist der nächstliegende echte EDHREC-Tag und in der Praxis fast deckungsgleich mit "Rot-Removal-Paket").

| Karte | Manakosten | Effekt | Inclusion |
|---|---|---|---|
| Lightning Bolt | {R} (1) | 3 Schaden an Ziel | 43% (310) |
| Pyroblast | {R} (1) | Gegen Blau: Zauber/Permanent zerstören | 31% (14% Synergie) |
| Chaos Warp | {2}{R} (3) | Beliebiges Permanent ins Library, Besitzer deckt Top-Karte auf | **66%** (478) — meistgespielte Karte überhaupt in dieser Kategorie |
| Vandalblast | {1}{R} (2) / Overload {4}{R} | 1 Artefakt zerstören / alle gegnerischen Artefakte | 46% (336) |
| Blood Moon | {2}{R} (3) | Nichtbasisländer werden zu Bergen | 32% (12% Synergie) |

**Befund**: Rot hat bei 1 Mana einen sehr starken, gut etablierten Anker — Lightning Bolt liefert **3 Schadenspunkte pro Mana** und bleibt trotz 30+ Jahren Powercreep der Referenzpunkt. Bei 3 Mana ist die meistgespielte Karte überhaupt (Chaos Warp, 66% Inclusion — höher als jede Draw-Karte) eine **unconditional Removal für JEDES Permanent** mit einem Zufalls-Nachteil als Preis für die Reichweite.

**Vorschlag für die Baseline-Zahl**:

```
interaction_baseline_R:
  mv1: ~3.0 Effekt-Punkte/Mana (Lightning-Bolt-Referenz, reines Damage-Removal)
  mv2: ~1 Ziel neutralisiert/Mana bei eng zugeschnittenem Removal (Vandalblast: Artefakte)
  mv3: unconditional "entfernt fast alles" ist der Goldstandard-Preis (Chaos Warp = meistgespielte Karte der ganzen Kategorie)
```

## 4. Kategorie: Board Wipe

**Schwächer datengestützt** — kein eigener EDHREC-Tag, daher primär aus eigenem MTG-Wissen, mit einem einzigen bestätigten Datenpunkt aus dem `control`-Tag oben.

| Karte | Manakosten | Effekt | Beleg |
|---|---|---|---|
| Blasphemous Act | {8}{R}, −{1} je weiterer eigener Kreatur (min. {R}) | 13 Schaden an alle Kreaturen | **Bestätigt**: 64% Inclusion (464/727) im `control`-Tag |
| Fiery Cannonade | {1}{R} (2) | 2 Schaden an alle boden-Kreaturen (ohne Flieger) | Eigenes Wissen, nicht per EDHREC-Fetch dieser Session bestätigt |
| Anger of the Gods / Sweltering Suns | {1}{R}{R} (3) | 3 Schaden an alle Kreaturen | Eigenes Wissen, nicht bestätigt |
| Chain Reaction | {3}{R}{R} (5) | Schaden = Anzahl eigener Kreaturen, an alle Kreaturen | Eigenes Wissen, nicht bestätigt |

**Befund**: Der einzige EDHREC-bestätigte Datenpunkt (Blasphemous Act) zeigt eine grundsätzlich andere Wertform als die anderen Kategorien: **kein fester Preis pro Schadenspunkt**, sondern ein Rabattmechanismus, der genau dann am günstigsten wird, wenn man selbst viele Kreaturen hat (also potenziell selbst am meisten trifft) — ein bewusster Trade-off, kein lineares "X Mana = Y Schaden". Eine einzelne flache "Schaden pro Mana"-Zahl würde diese Karte falsch abbilden.

**Vorschlag**: Board Wipe braucht eher ein Zwei-Parameter-Modell (Basiskosten + Skalierungs-Rabatt-Bedingung) statt eines einzigen Erwartungswerts — das ist über diese Pilotstudie hinaus ein Designpunkt für die volle Umsetzung.

## 5. Offene Punkte für die volle Umsetzung (nach Review)

1. Manakosten/Oracle-Text der oben zitierten Karten sollten, sobald möglich, gegen eine echte Datenquelle verifiziert werden (Scryfall ist aus der Sandbox nicht erreichbar — ggf. vom Nutzer als Bulk-Data-Datei bereitgestellt).
2. Board Wipe braucht ein eigenes Werte-Schema (Basispreis + Rabattbedingung), keine einfache Erwartungszahl.
3. Die anderen 4 Farben sind komplett offen.
4. Keywords- und Power/Toughness-Kategorien sind komplett offen (inkl. der vom Nutzer vorgeschlagenen Idee, P+T als Summe statt getrennt zu betrachten).
5. Das "Baukastensystem" (Instant/Sorcery/Kreatur × Kategorie × Keywords als kombinierbare Faktoren) ist noch nicht entworfen — das ist die größte offene Design-Entscheidung und sollte erst nach Farb-Pilot-Review angegangen werden.

## 6. Begleitende Datei

`Data/Models/color_value_baseline_red_pilot.json` — maschinenlesbarer Entwurf der obigen Zahlen, testweise strukturiert, aber **nicht** von `ValueModel` geladen. Erst nach Freigabe in `goldfish_value_model.json`/`ValueModel` integrieren.
