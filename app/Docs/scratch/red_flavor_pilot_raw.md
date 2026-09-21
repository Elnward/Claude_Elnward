# Rot-Flavor-Portion: Rohdaten (v4.51.0)

Alle 6 Decks: echte EDHREC-"Average Deck – Upgraded" (Bracket-3-Filter),
abgerufen 14.09.2026. Alle 6 Links stammen aus
`Commander_Monofarben_Bracket_3.md`, real geöffnet und ausgezählt.

## 1. Goblins/Go-Wide-Aggro — Krenko, Mob Boss
edhrec.com/average-decks/krenko-mob-boss/upgraded
Lands(35): 29 Mountain + 6 nonbasic. Non-Land = 64.
Creatures(31), Instants(7), Sorceries(8), Artifacts(12), Enchantments(6).
Punkt-Entfernung: Abrade, Chaos Warp, Lightning Bolt = 3 (4,7%).
Wipes: Blasphemous Act = 1 (1,6%).
Ramp: Arcane Signet, Patriar's Seal, Ruby Medallion, Sol Ring = 4 (6,3%) —
zusätzlich Battle Hymn/Brightstone Ritual als Burst-Rituale (separat
gezählt, nicht in die Ramp-Dichte eingerechnet).
Passive Value: praktisch 0 — Purphoros, God of the Forge ist ein
Schadens-Payoff bei Kreatur-ETB, keine Karten-/Mana-Vorteils-Engine im
engeren Sinn. Coat of Arms/Quest for the Goblin Lord/Shared Animosity/
Boggart Shenanigans sind Anthems (Kampf-Boost), keine Value-Engines.
**Kiki-Jiki, Mirror Breaker vorhanden, ABER kein Combo-Partner
(Restoration Angel, Zealous Conscripts, Deceiver Exarch, Village
Bell-Ringer o.ä.) in der Liste — kein bestätigter Kiki-Combo, exakt wie
in `opponent_state_weights.json` v4.39.0 für die ursprüngliche
Krenko-Kalibrierungsliste selbst dokumentiert ("Kiki-Jiki... ohne
erkennbaren zweiten Kombopartner").** Combo: 0 (0%).
Opfer/Drain: Goblin Bombardment (Outlet+Payoff), Skirk Prospector
(Outlet), Goblin Chirurgeon (Outlet) = 3 (4,7%).
Disruption: 0. Board-Präsenz: 31/64 = 48,4%.

## 2. Burn/Group Slug — Ojer Axonil, Deepest Might
edhrec.com/average-decks/ojer-axonil-deepest-might/upgraded
Lands(34): 29 Mountain + 5 nonbasic. Non-Land = 65.
Creatures(20), Instants(13), Sorceries(13), Artifacts(10),
Enchantments(8), Planeswalker(1).
Punkt-Entfernung: Abrade, Chaos Warp, Gut Shot, Lava Dart, Lightning
Bolt, Spikefield Hazard = 6 (9,2%) — deutlich höher als Krenko/Zada.
Wipes: Blasphemous Act = 1 (1,5%).
Ramp: Arcane Signet, Fire Diamond, Mind Stone, Ruby Medallion, Sol Ring
= 5 (7,7%).
**Passive Value/Group-Slug-Engines (Modellgrenze, siehe unten): Burning
Earth, Manabarbs, Pyrohemia, Roiling Vortex, Spellshock, Sulfuric
Vortex = 6 (9,2%) — stehende Schadens-"Steuer"-Verzauberungen, die dem
Gegner jeden Zug Schaden zufügen. Diese werden hilfsweise auf
passive_value_growth gemappt, obwohl das Feld eigentlich für
Karten-/Mana-Vorteils-Engines konzipiert ist — hier generieren sie
stattdessen laufenden Direktschaden. Gleiche Kategorie-Unschärfe wie bei
Tinybones/Discard (Schwarz, v4.50.0), hier aber für "Damage-over-time"
statt Handzerstörung.**
Combo: 0 (kein bestätigter 2-Karten-Infinite gefunden).
Opfer/Drain: 0.
**Disruption: Harsh Mentor (tax auf aktivierte Fähigkeiten), Rampaging
Ferocidon (hosst Lifegain/Token-Erzeugung) = 2 (3,1%) — echte
Stax-/Hatebears-Dichte für ein Burn-Deck, aber KEINE der 9 im Projekt
getrackten unmapped_persistent_disruption-Game-Changer (Harsh
Mentor/Ferocidon stehen nicht auf dieser 53-Karten-Liste) — bestätigt
NICHT den bislang unbelegten R-Disruption-Modifikator in
opponent_state_weights.json, da es sich um eine andere, kleinere
Disruption-Kategorie handelt.**
Board-Präsenz: 20/65 = 30,8% — niedrigste Kreaturendichte im
Rot-Sample, konsistent mit einem Spell-/Enchantment-lastigen
Group-Slug-Plan statt Kreatur-Aggro.

## 3. Artefakte/Treasure/Friedhof-Rekursion — Daretti, Scrap Savant
edhrec.com/average-decks/daretti-scrap-savant/upgraded
Lands(35): 23 Mountain + 12 nonbasic. Non-Land = 64.
Creatures(23), Instants(4), Sorceries(8), Artifacts(27), Enchantment(1),
Planeswalker(1).
Punkt-Entfernung: Chaos Warp, Duplicant, Meteor Golem, Spine of Ish Sah
= 4 (6,3%).
**Wipes: All Is Dust, Blasphemous Act, Nevinyrral's Disk, Portal to
Phyrexia = 4 (6,3%) — auffällig hohe Wipe-Dichte für ein Mono-Rot-Deck,
höher als bei jedem anderen Rot-Flavor in dieser Stichprobe.**
Ramp: Arcane Signet, Basalt Monolith, Everflowing Chalice, Fellwar
Stone, Hedron Archive, Mind Stone, Sol Ring, Thran Dynamo = 8 (12,5%) —
mit Abstand höchste Ramp-Dichte des Rot-Samples, deckt sich mit dem
Artefakt-Toolbox-Charakter des Decks.
Passive Value: Trading Post, Mystic Forge, Ichor Wellspring = 3 (4,7%).
**Combo (VIERTER bestätigter vollständiger Combo-Fund des Projekts):
Rings of Brighthearth + Basalt Monolith BEIDE in derselben Liste — eine
bekannte, vollständige Infinite-Mana-Combo = 2 Teile (3,1%).**
Sekundär (nicht als vollständiger Combo gezählt): Krark-Clan Ironworks +
Trading Post bilden eine starke, aber nicht zwingend infinite
Artefakt-Opfer-Value-Schleife.
Opfer/Drain: Krark-Clan Ironworks, Trading Post (beide Outlets, keine
dedizierten Drain-Payoffs) = 2 (3,1%).
Disruption: 0. Board-Präsenz: 23/64 = 35,9%.

## 4. Spellslinger/Cantrip/Storm — Zada, Hedron Grinder
edhrec.com/average-decks/zada-hedron-grinder/upgraded
Lands(35): 28 Mountain + 7 nonbasic. Non-Land = 64.
Creatures(21), Instants(20), Sorceries(16), Artifacts(5),
Enchantments(2).
**EDHREC-eigenes Tag "Storm 147" bestätigt den Storm-Archetyp real
(nicht nur Dokument-Behauptung).**
Punkt-Entfernung: Chaos Warp = 1 (1,6%) — niedrigste Entfernungsdichte
des gesamten Rot-Samples.
Wipes: Blasphemous Act = 1 (1,6%).
Ramp: Arcane Signet, Ruby Medallion, Sol Ring = 3 (4,7%) — zusätzlich 4
Burst-Rituale (Battle Hymn, Brightstone Ritual, Mana Geyser, Seething
Song), die für den Storm-Endzug reserviert sind statt für stetiges
Ramp — separat ausgewiesen, nicht in die 4,7% eingerechnet.
Passive Value: Storm-Kiln Artist (Treasure-Engine bei Spell-Cast),
Young Pyromancer (Token-Engine bei Spell-Cast) = 2 (3,1%) — beides
stehende "Cast-Trigger→Value"-Engines, Kernstück des
Spellslinger-Plans.
**Combo/Storm-Paket (kein klassischer 2-Karten-Infinite, sondern ein
kumulatives Storm-Finish-Paket): Empty the Warrens, Grapeshot, Past in
Flames = 3 (4,7%) — zusammen mit den 4 Ritualen und Jeska's Will das
tragende Sturm-Gerüst. Ausdrücklich als andere Combo-Unterkategorie
markiert als der Rings+Basalt-Fund bei Daretti (kein zwingendes
2-Karten-Infinite, sondern additive Payoff-Dichte).**
Opfer/Drain: 0. Disruption: 0.
Board-Präsenz: 21/64 = 32,8%.

## 5. Drachen/Tribal-Midrange — Lathliss, Dragon Queen
edhrec.com/average-decks/lathliss-dragon-queen/upgraded
Lands(37): 29 Mountain + 8 nonbasic. Non-Land = 62.
Creatures(28), Instants(7), Sorceries(6), Artifacts(14), Enchantments(6),
Planeswalker(1).
Punkt-Entfernung: Chaos Warp, Sarkhan's Triumph (Exil bei Power ≥4),
Spit Flame = 3 (4,8%).
Wipes: Blasphemous Act, Earthquake = 2 (3,2%).
Ramp: Arcane Signet, Mox Jasper, Ruby Medallion, Sol Ring = 4 (6,5%) —
niedriger als Dokument-Erwartung für einen "Big-Mana"-nahen Flavor.
Passive Value: Herald's Horn (Kostenreduktion+Karten-Vorteil bei
Dragon-ETB), Dragon's Hoard (Manarock+Draw bei Dragon-ETB) = 2 (3,2%).
Combo: 0 (kein bestätigter 2-Karten-Infinite; Extra-Combat-Synergien
wie Hellkite Charger vorhanden, aber nicht infinite ohne weitere
Teile).
Opfer/Drain: 0. Disruption: 0.
Board-Präsenz: 28/62 = 45,2% — hohe Kreaturendichte, typisch für ein
Tribal-Deck mit großteils teuren Einzelthreats statt schmalem
Value-Unterbau.

## 6. Equipment/Voltron — Valduk, Keeper of the Flame
edhrec.com/average-decks/valduk-keeper-of-the-flame/upgraded
Lands(35): 27 Mountain + 8 nonbasic. Non-Land = 64.
Creatures(12), Instants(6), Sorceries(6), Artifacts(30), Enchantments(10).
**Board-Präsenz: 12/64 = 18,75% — NIEDRIGSTE Kreaturendichte des
gesamten Rot-Samples und eine der niedrigsten des gesamten Projekts,
Parallel-Befund zu Preston/Light-Paws (Weiß, v4.48.0): Voltron
konzentriert Wert auf wenige Kreaturen statt auf Board-Breite, wodurch
board_presence_growth strukturell unterschätzt bleibt.**
Punkt-Entfernung: Abrade, Chaos Warp = 2 (3,1%).
Wipes: Blasphemous Act = 1 (1,6%).
Ramp: Arcane Signet, Sol Ring = 2 (3,1%) — niedrigste Ramp-Dichte des
Samples, Equipment-Decks investieren Mana in Ausrüstung statt Rocks.
Passive Value: Idol of Oblivion, Outpost Siege = 2 (3,1%).
Combo: 0 (Ashnod's Altar+Skullclamp bilden eine starke Value-, aber
keine bestätigte Infinite-Schleife bei nur 12 Kreaturen).
Opfer/Drain: Ashnod's Altar (Outlet), Goblin Bombardment
(Outlet+Payoff) = 2 (3,1%).
Disruption: 0.

## Durchgängige Befunde über alle 6 Rot-Flavors

1. **Vierter bestätigter vollständiger Combo-Fund des Projekts:** Rings
   of Brighthearth + Basalt Monolith, beide real in derselben
   Daretti-Liste (nach Heliod+Ballista/Weiß, Isochron+Dramatic
   Reversal+Basalt/Blau, Sanguine Bond+Exquisite Blood/Schwarz).
2. **Kiki-Jiki-Combo-Fehlanzeige real erneut bestätigt**: die Krenko-
   Liste enthält Kiki-Jiki, Mirror Breaker, aber keinen der bekannten
   Combo-Partner — deckt sich exakt mit der ursprünglichen
   v4.39.0-Kalibrierungsnotiz für dieselbe Karte.
3. **Storm real bestätigt** über EDHRECs eigenes "Storm 147"-Tag bei
   Zada — der klarste goldfish-nahe Rennen-Flavor des gesamten Projekts
   bisher (kaum Interaktion: nur 1,6% Entfernung, 1,6% Wipe, 0%
   Disruption).
4. **Voltron (Valduk) zeigt die gleiche Board-Präsenz-Modellgrenze wie
   Preston/Light-Paws (Weiß)**: sehr wenige, teuer ausgerüstete
   Kreaturen statt Board-Breite — board_presence_growth strukturell zu
   niedrig für den tatsächlichen aggressiven Impact des Decks.
5. **Group Slug (Ojer Axonil) zeigt eine neue Modellgrenze**: stehende
   Schadens-Verzauberungen (Sulfuric Vortex, Manabarbs, Pyrohemia,
   Roiling Vortex) erzeugen laufenden Direktschaden, was keinem
   bestehenden Feld exakt entspricht — hilfsweise auf
   passive_value_growth gemappt, aber ein Kandidat für ein künftiges
   dediziertes Feld (parallel zum Discard-Befund bei Tinybones,
   Schwarz).
6. **Daretti zeigt die höchste Wipe-Dichte (6,3%) und höchste
   Ramp-Dichte (12,5%) des Rot-Samples** — für Mono-Rot ungewöhnlich
   hoch, aber konsistent mit dem Artefakt-Toolbox-/Control-Charakter
   des Decks statt eines klassischen Rot-Aggro-Musters.
7. **Der bestehende R-Farbmodifikator (`board_presence: 1.15,
   mana_growth: 1.10, dead_turn_chance: 0.90`) bleibt unangetastet** —
   Board-Präsenz-Werte zwischen 18,75% (Valduk) und 48,4% (Krenko)
   spannen einen sehr weiten Bereich auf, was die Notwendigkeit einer
   Flavor-spezifischen statt einer einzigen Farb-weiten
   Board-Präsenz-Erwartung unterstreicht (bereits in der
   Flavor-Strategie-Matrix selbst, nicht in `opponent_state_weights.json`
   abgebildet). Weder `passive_value_growth`/`sac_drain_growth` noch
   `disruption_growth` werden für R ergänzt: das Rot-Sample bestätigt
   die JSON-eigene Einschätzung ("keine der beiden Krenko-Belegdecks
   zeigte ein Beispiel"; die real gefundene Ojer-Disruption ist keine
   der 9 getrackten Game-Changer-Karten).
