# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.42.0

Begleitdokument zu `Docs/README.md` (v4.42.0-Eintrag). Erste Teilrunde der
vom Nutzer selbst so benannten "Iteration 5": Ausweitung auf die
verbleibenden Mehrfarb-Identitäten, hier die 10 dreifarbigen Wedges/Shards.
**Diese Version ändert KEINEN Code und KEINE Gewichtszahl** - sie ist eine
reine Validierungs-/Dokumentationsrunde (Begründung siehe unten) und wird
trotzdem versioniert, weil sie echte neue Erkenntnisse und eine Verfeinerung
der Bracket-Klassifikationsheuristik liefert.

## Ausgangslage: Sample-Größen-Entscheidung

Der Nutzer bestätigte explizit, die bisherige Sample-Größe beizubehalten (2
echte Decks je Monofarbe, 1 echtes Deck je Zweifarb-Gilde) statt sie sofort
zu vergrößern, und eine tiefere Neukalibrierung erst durchzuführen, "wenn wir
mit der gesamten Mechanik des Tools zu hundert Prozent vertraut sind und
sobald alles funktioniert und das Design auch passt" - also NACH der
(bislang noch nicht erfolgten) Integration in `App/engine.py`s echte
Zugschleife. Diese Version übernimmt dieselbe Sample-Größe (1 echtes Deck je
Dreifarb-Identität) für Konsistenz.

## Die 10 Dreifarb-Decks (Shards + Wedges)

Quelle wie gehabt: EDHREC "Average Deck"-Aggregate, abgerufen 13.09.2026.

| Identität | Commander | Strategie | Game Changers gefunden | Bracket |
|---|---|---|---|---|
| Bant (GWU) | Rafiq of the Many | Voltron | 1 (Enlightened Tutor) | 3 |
| Esper (WUB) | Zur the Enchanter | Enchantment-Control/Stax | 10 (Drannith Magistrate, Opposition Agent, Cyclonic Rift, Fierce Guardianship, Enlightened Tutor, Vampiric Tutor, Demonic Tutor, Necropotence, Rhystic Study, Smothering Tithe) | 5 |
| Grixis (UBR) | The Scarab God | Zombie-Reanimator | 1 (Cyclonic Rift) | 3 |
| Jund (BRG) | Korvold, Fae-Cursed King | Aristokraten/Value | 4 (Crop Rotation, Demonic Tutor, Vampiric Tutor, Worldly Tutor) | 4 |
| Naya (RGW) | Marath, Will of the Wild | Counters/Midrange | 2 (Enlightened Tutor, Worldly Tutor) | 3 |
| Abzan (WBG) | Karador, Ghost Chieftain | Reanimator | 1 (Aura Shards) | 3 |
| Jeskai (URW) | Kykar, Wind's Fury | Spellslinger-Tokens | 5 (Cyclonic Rift, Mystical Tutor, Jeska's Will, Rhystic Study, Smothering Tithe) | 4 |
| Sultai (BGU) | Muldrotha, the Gravetide | Graveyard-Value | 4 (Cyclonic Rift, Crop Rotation, Demonic Tutor, Rhystic Study) | 4 |
| Mardu (RWB) | Alesha, Who Smiles at Death | Aggro-Reanimator | 0 | 2 |
| Temur (GUR) | Yidris, Maelstrom Wielder | Cascade/Storm | 1 (Rhystic Study) | 3 |

Bracket-Verteilung: 1×Bracket 2 (Mardu), 5×Bracket 3 (Bant, Grixis, Naya,
Abzan, Temur), 3×Bracket 4 (Jund, Jeskai, Sultai), 1×Bracket 5 (Esper).

## Befund 1: Bracket-Klassifikationsheuristik verfeinert (evidenzbasiert)

Über alle bislang 30 echten, klassifizierten Decks (10 mono + 10 zweifarbig +
10 dreifarbig) zeichnet sich ein klarer, durchgängiger Bereich ab: 0 Game
Changer → Bracket 2, 1-3 → Bracket 3, 4-6 → Bracket 4. Die bisherige
v4.39.0-Regel für Bracket 5 verlangte zusätzlich zur GC-Zahl eine auffällige
Ritual-/Opferaltar-Häufung (am Beispiel Endrek-Expensive, 5 GC). Zur the
Enchanter liefert nun einen sauberen Gegenbeleg: 10 Game Changer, KEINE
auffällige Ritual-/Altar-Häufung, und dennoch zweifelsfrei ein cEDH-taugliches
Enchantment-Stax-Deck (Drannith Magistrate + Opposition Agent + Rhystic
Study + Necropotence + 3 Tutoren beim selben Deck ist eine Kombination, die
in einem Bracket-3/4-Umfeld nicht auftaucht). **Verfeinerte Heuristik (nur
für die eigene Kalibrierungs-Klassifikation künftiger Decks genutzt, KEIN
Code in state_equation.py):** ab 7 oder mehr Game Changern gilt ein Deck
unabhängig von einer zusätzlichen Ritual-/Altar-Häufung als Bracket 5; im
Bereich 4-6 bleibt die zusätzliche Häufung das entscheidende Unterscheidungs-
merkmal zwischen 4 und 5 (wie in v4.39.0 an Endrek gezeigt). Keine der
bisherigen 29 anderen Klassifikationen ändert sich rückwirkend durch diese
Verfeinerung.

## Befund 2: Das multiplikative Farbmodell validiert sich auch bei drei Farben

- Esper (WUB): vorhergesagter `passive_value_growth`-Multiplikator =
  W(1.25) × U(1.40) × B(1.15) = 2.01 - der höchste aller bisher berechneten
  Werte. Real zeigt Zur the Enchanter tatsächlich die dichteste
  Passive-Value-/Stax-Häufung der GESAMTEN bisherigen Stichprobe
  (Necropotence, Rhystic Study, Smothering Tithe, Mystic Remora). Starke
  Bestätigung.
- Jeskai (URW, Kykar): vorhergesagt U(1.40) × R(1.0) × W(1.25) = 1.75 - real
  ebenfalls eine dichte Value-Häufung (Mystic Remora, Rhystic Study,
  Smothering Tithe, Whirlwind of Thought). Bestätigung.
- Jund (BRG, Korvold): vorhergesagter `sac_drain_growth`-Multiplikator =
  B(1.55) × R(1.0) × G(1.0, kein eigenes Gewicht) = 1.55 - real eine der
  dichtesten Opfer-/Aristokraten-Häufungen der Stichprobe (Blood Artist,
  Zulaport Cutthroat, Mayhem Devil, Pitiless Plunderer, Viscera Seer, Warren
  Soultrader, Goblin Bombardment, Ashnod's Altar, Phyrexian Altar) -
  bestätigt zum DRITTEN Mal (nach mono-Schwarz Endrek und Orzhov/Teysa), dass
  Schwarz robust die Opfer-Drain-tragende Farbe ist, unabhängig vom
  Farbpartner. Keine Gewichtsänderung notwendig - zusätzliche, bestätigende
  Evidenz statt neuer Kalibrierung.

## Warum diese Version KEINE Gewichte ändert

Jede der 10 Dreifarb-Beobachtungen ist wie in v4.41.0 nur EIN Deck pro
Identität - aus einer solchen Einzelbeobachtung heraus neue Zahlen zu
kalibrieren (statt nur zu bestätigen oder als offene Lücke zu benennen), wäre
keine verantwortbare Evidenzbasis. Alle drei obigen Befunde bestätigen das
bestehende Modell, ohne es zu widerlegen - entsprechend bleibt
`opponent_state_weights.json` unverändert bis auf den beschreibenden
`note`-Text.

## Verbleibende, noch nicht untersuchte Farbidentitäten

Nach mono (5) + zweifarbig (10) + dreifarbig (10) = 25 von 32 Identitäten
verbleiben **7**: 5 vierfarbige (WUBR/WUBG/WURG/WBRG/UBRG), 1 fünffarbige
(WUBRG) und 1 farblose Identität. Für diese ist auf EDHREC deutlich weniger
Deck-Population zu erwarten (weniger Commander, geringere Popularität) - eine
belastbare Stichprobe wird dort voraussichtlich dünner ausfallen als bei
Zwei-/Dreifarb-Identitäten, unabhängig vom Aufwand. Das wird offen benannt,
sobald diese Runde ansteht, statt es zu verschweigen.
