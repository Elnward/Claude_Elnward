# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.39.0

Begleitdokument zu `Docs/README.md` (v4.39.0-Eintrag) und
`App/opponent_model/state_equation.py`. Hält die Rohdaten und die
Bracket-Einordnung der 10 echten Decklisten fest, die für die Kalibrierung
dieser Version verwendet wurden, damit die Herleitung nachvollziehbar bleibt.

## Quelle

Alle 10 Decklisten: EDHREC "Average Deck"-Aggregate
(`edhrec.com/average-decks/<commander-slug>[/<modifier>]`), abgerufen
06.09.2026 (Session-Datum). "Budget"/"" = niedrigere Machtstufe,
"Expensive" = höhere Machtstufe.

## Verifiziertes Game-Changers-Regelwerk

Offizielle Liste (53 Karten) von `magic.wizards.com/en/news/announcements/
commander-brackets-beta-update-april-22-2025` abgerufen und gegen
`playgroup.gg/commander/game-changers` sowie `scrollvault.net/guides/
game-changers.html` auf Übereinstimmung geprüft (drei Quellen, exakt
deckungsgleich): Ad Nauseam, Ancient Tomb, Aura Shards, Biorhythm, Bolas's
Citadel, Braids Cabal Minion, Chrome Mox, Coalition Victory, Consecrated
Sphinx, Crop Rotation, Cyclonic Rift, Demonic Tutor, Drannith Magistrate,
Enlightened Tutor, Farewell, Field of the Dead, Fierce Guardianship, Force
of Will, Gaea's Cradle, Gamble, Gifts Ungiven, Glacial Chasm, Grand Arbiter
Augustin IV, Grim Monolith, Humility, Imperial Seal, Intuition, Jeska's
Will, Lion's Eye Diamond, Mana Vault, Mishra's Workshop, Mox Diamond,
Mystical Tutor, Narset Parter of Veils, Natural Order, Necropotence, Notion
Thief, Opposition Agent, Orcish Bowmasters, Panoptic Mirror, Rhystic Study,
Seedborn Muse, Serra's Sanctum, Smothering Tithe, Survival of the Fittest,
Teferi's Protection, Tergrid God of Fright, Thassa's Oracle, The One Ring,
The Tabernacle at Pendrell Vale, Underworld Breach, Vampiric Tutor, Worldly
Tutor. (Eine erste Einzelabfrage lieferte abweichende/zusätzliche Karten und
wurde deshalb verworfen - erst die Übereinstimmung zweier unabhängiger
Quellen wurde akzeptiert.)

## Die 10 Decks

| Farbe | Commander/Strategie | Variante | Game Changers gefunden | Bracket |
|---|---|---|---|---|
| Mono-R | Krenko, Mob Boss (Aggro) | Budget | 0 | 2 |
| Mono-R | Krenko, Mob Boss (Aggro) | Expensive | 5 (Chrome Mox, Mana Vault, Ancient Tomb, The One Ring, Jeska's Will) | 4 |
| Mono-W | Giada, Font of Hope (Aggro) | Budget | 0 | 2 |
| Mono-W | Giada, Font of Hope (Aggro) | Expensive | 4 (The One Ring, Smothering Tithe, Teferi's Protection, Enlightened Tutor) | 4 |
| Mono-U | Lier, Disciple of the Drowned (Control) | Standard | 3 (Cyclonic Rift, Rhystic Study, Mystical Tutor) | 3 |
| Mono-U | Lier, Disciple of the Drowned (Control) | Expensive (Bounce) | 4 (+ Mana Vault) | 4 |
| Mono-B | Endrek Sahr, Master Breeder (Aristokraten/Midrange) | Budget | 0 | 2 |
| Mono-B | Endrek Sahr, Master Breeder (Aristokraten/Midrange) | Expensive | 5 (Demonic Tutor, Bolas's Citadel, Necropotence, Imperial Seal, Vampiric Tutor) + dichte Ritual-/Opferaltar-Häufung | 5 |
| Mono-G | Azusa, Lost but Seeking (Ramp/Midrange) | Standard | 2 (Gaea's Cradle, Crop Rotation) | 3 |
| Mono-G | Azusa, Lost but Seeking (Ramp/Midrange) | Expensive (Landfall) | 5 (+ Natural Order, Field of the Dead, Ancient Tomb) | 4 |

Keine der 10 Listen enthielt Mass Land Destruction (Armageddon-artige
Effekte) oder eine Extra-Turn-Karte. Ein vollständiger 2-Karten-Kombo-Audit
wurde NICHT durchgeführt (offengelegte Einschränkung) - die
Bracket-4/5-Einordnung stützt sich hier ausschließlich auf die
Game-Changer-Zahl plus (bei Endrek-Expensive) die auffällige
Engine-/Tutor-Dichte, nicht auf einen verifizierten Kombo-Nachweis.

## Ausgezählte Kategorie-Dichten (Anteil an Nicht-Land-Slots, überschlägig)

| Deck | Board-Presence | Interaktion | Wipe | Mana/Ramp | Hand-Quality/Value |
|---|---|---|---|---|---|
| Krenko Budget | 60% | 5% | 0% | 9.5% | 6% |
| Krenko Expensive | 41% | 9.5% | 0% | 12.7% | 6% |
| Giada Budget | 51% | 11% | 3% | 9.5% | 1.5% |
| Giada Expensive | 47% | 10.6% | 6% | 9% | 9% |
| Lier Standard | 21.5% | 17% | 0%* | 12% | 23% |
| Lier Expensive | 18% | 25% | 0%* | 13.4% | 12% |
| Endrek Budget | 54% | 3% | 0% | 8% | 8% |
| Endrek Expensive | 42% | 4.5% | 4.5% | 15% | 15% |
| Azusa Standard | 48% | 3.5% | 0% | 19.6% | 10.7% |
| Azusa Expensive | 47% | 3.3% | 0% | 15% | 11.7% |

\* Blau wipet praktisch nie via "destroy all" - Cyclonic Rift/Aetherize
(Bounce-Alle-Effekte) sind hier unter "Interaktion" statt "Wipe" gezählt,
selbst wenn sie taktisch ähnlich wirken. Das ist eine Modellierungs-Nuance,
keine Lücke im engeren Sinn - im Modell bleibt `wipe_readiness` für
Control(Blau) trotzdem über den bestehenden `strategy_curves.control`-Wert
ungleich 0, weil die reale Control-Strategie-Kurve auch andere Farben
(z. B. Weiß/Schwarz) mit abdecken muss.

Diese Zählungen sind händisch aus den EDHREC-Kategorie-Listen abgeleitet,
keine programmatische Card-Datenbank-Abfrage - für eine "rudimentäre"
Kalibrierung ausreichend belastbar, aber explizit keine hochpräzise
Statistik. Die daraus abgeleiteten Gewichtsänderungen stehen mit Begründung
direkt in `Data/Models/opponent_state_weights.json` (jeweils im
`_comment`-Feld der betroffenen Farbe/Bracket-Stufe).

## Nächste Schritte (vom Nutzer selbst benannt, nicht Teil dieser Version)

- Volle Bracket × Farbe × Strategie-Matrix mit mehreren Decks pro Zelle
  statt 2 Decks pro Farbe.
- Mehrfarbige Gegnerprofile (aktuell nur Monofarbe untersucht).
- Die zwei bewusst offen gelassenen Lücken (passive Value-/Tax-Engines;
  schwarze Opfer-/Aristokraten-Drain-Schleifen als eigener
  Lebenspunkte-Druckvektor) als neue Dimensionen, sobald genug Datenpunkte
  vorliegen, um sie nicht aus einer einzelnen Deckliste zu erfinden.
