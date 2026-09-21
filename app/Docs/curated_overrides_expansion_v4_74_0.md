# CURATED_OVERRIDES-Erweiterung, Runde 3 (v4.74.0) — Ziel erreicht

## Kontext

Dritte und (fuer diesen Auftrag) letzte planmaessige Runde der
CURATED_OVERRIDES-Erweiterung, ausgeloest durch den expliziten Auftrag
"Bitte arbeite dich bis zu dem Ziel iterativ Step für Step durch und das
eigenständig. Sobald du das Ziel erreicht hast, sag mir bitte Bescheid, ob
das Tool jetzt einwandfrei funktioniert." Nach Runde 2 (v4.73.0) stand
CURATED_OVERRIDES bei 252 Eintraegen — noch unterhalb des Zielkorridors von
300-500. Diese Runde wendet dieselbe, bereits zweimal etablierte
datengetriebene Methodik ein drittes Mal an, mit dem Ziel, den
300-500-Korridor zu erreichen.

## Methodik (unveraendert gegenueber Runde 1/2)

1. Alle eindeutigen Karten aus `deck_cards_slim.csv` nach summierter
   `quantity` ueber alle 1.585 echten Decks ranken.
2. Basisländer und bereits kuratierte Karten (jetzt: die 252 aus Runde 1+2)
   ausschliessen.
3. Fuer jede verbleibende Karte `classify_card` mit dem echten `oracle_text`
   aus `unique_cards_enriched.csv` ausfuehren und pruefen, ob
   `effect_tags[0]` in `{"unclassified", "vanilla_or_unclassified_body"}`
   liegt (Fallback-Treffer).
4. Vor jeder Einzelkuratierung zuerst nach wiederkehrenden Formulierungs-
   mustern suchen, die sich als NEUE ALLGEMEINE REGEX-REGEL lohnen - erst
   danach die verbleibenden Karten einzeln mit ihrem echten Oracle-Text
   kuratieren.

**Neu in dieser Runde:** die Schwelle wurde von Gesamt-Quantity >= 15 auf
>= 10 abgesenkt (Runde 1/2 arbeiteten mit >= 15), um genug Volumen fuer den
300-500-Korridor zu erreichen, sobald das >=15-Segment erschoepft war.

## Ausgangslage

Nach Runde 2 (v4.73.0): 252 kuratierte Karten. Beim erneuten Ranking-Lauf
fiel auf, dass zwei sehr hochfrequente Karten — Yavimaya, Cradle of Growth
(Quantity 164) und Urborg, Tomb of Yawgmoth (Quantity 102) — bislang in
keiner der beiden Vorrunden im Fallback-Batch aufgetaucht waren (Land-Typ
"Legendary Land" statt der ueblichen nichtland-permanenten Karten, die den
Grossteil der Stichproben bildeten). Mit Schwelle >= 10 ergaben sich 181
Fallback-Karten insgesamt fuer diese Runde.

## Neue allgemeine Regeln (Runde 3)

Wirkung gemessen gegen den 181-Karten-Batch (vor Runde-3-Kuration):

| Tag | Regel-Ort | Muster (sinngemaess) | Karten | Summe Quantity | Beispiele |
|---|---|---|---|---|---|
| `land_type_fixing` | `_RAMP_RULES` | "each land is a [Basic Land Type] in addition to its other land types" | 2 | 266 | Yavimaya Cradle of Growth, Urborg Tomb of Yawgmoth |
| `impulse_draw` | `_CARD_ADVANTAGE_RULES` | "exile the top [N/X] card(s) ... you may play that card/those cards/it" | 4 | 46 | Wrenn's Resolve, Commune with Lava |
| `untap_all_nonland_combo` | `_STRATEGY_RULES` | "untap all nonland permanents you control" | 2 | 25 | Dramatic Reversal, Unstoppable Plan |
| `wheel_effect` (erweitert) | `_STRATEGY_RULES` | "shuffles ... hand (and graveyard) into library, then draws that many/seven cards" | 3 | 36 | Winds of Change, Echo of Eons, Molten Psyche |

Summe: 11 Karten (373 Quantity) automatisch durch 4 neue generelle Regeln
gefixt, ohne eine einzige davon manuell zu kuratieren. Die
`land_type_fixing`-Regel hat trotz nur 2 betroffener Karten mit Abstand die
groesste Einzelwirkung der gesamten dreirundigen Erweiterung (266 Quantity
fuer 2 Karten) — ein Beleg dafuer, dass sich das Ranking-Verfahren auch in
Runde 3 noch lohnt und nicht bereits ausgeschoepft war.

## Manuell kuratierte Karten (163 neue CURATED_OVERRIDES-Eintraege)

Nach Abzug der 11 durch neue Regeln automatisch gefixten Karten blieben 170
Karten mit Quantity >= 10 im Fallback. Davon wurden 163 einzeln mit ihrem
echten Oracle-Text kuratiert (role/effect_tags/simple_effect/
halbwertszeit, exakt wie in Runde 1/2). Die volle Liste der 163 neuen
Namen steht direkt im Quellcode (`App/archetype_profile/classify.py`,
Abschnitt "v4.74.0: CURATED_OVERRIDES-Erweiterung Runde 3") — der erste
Eintrag dieser Runde ist Desecrate Reality, der letzte Erdwal Illuminator.

### Bewusst ausgelassen (7 Karten)

- **Ornithopter** (qty 38), **Sire of Seven Deaths** (qty 25): unveraendert
  aus Runde 1/2 uebernommene Begruendung (reiner Vanilla-Effekt bzw. reine
  Keyword-Haufung ohne eigenstaendigen Effekt).
- **Rograkh, Son of Rohgahh** (qty 13): reine Keyword-Haufung (first
  strike, menace, trample) plus der Deckbau-Mechanik Partner, die selbst
  keinen spielinternen Effekt darstellt — die bestehende Fallback-
  Klassifikation ist bereits korrekt.
- **Healer's Hawk** (qty 12), **Shrike Force** (qty 10), **Deadly
  Recluse** (qty 10): jeweils reine Zwei-Keyword-Koerper (flying+lifelink;
  flying+double strike+vigilance; reach+deathtouch) ohne eigenstaendigen,
  ueber die Keywords hinausgehenden Effekt — analog zur bereits in Runde 1
  fuer Ornithopter etablierten Begruendung.
- **Bygone Colossus** (qty 10): reiner grosser Vanilla-Koerper mit der
  generischen Warp-Mechanik (Zeitlich begrenztes Ausspielen aus der Hand);
  Warp selbst ist ein wiederkehrender Spielmechanismus, kein
  kartenspezifischer Effekt, der eine Einzelkuration rechtfertigt.

## Statusbericht nach Runde 3 — Ziel erreicht

- CURATED_OVERRIDES: 252 → **415 Eintraege** (Zielkorridor 300-500:
  **erreicht**).
- Generelle Regex-Regeln insgesamt: 11 (Runde 1) + 6 (Runde 2) + 4
  (Runde 3) = 21 neue Muster seit Beginn der Erweiterung.
- Fallback-Anteil (Kartenanzahl, ueber alle Karten mit vorhandenem
  Oracle-Text, Basislaender ausgenommen): 15,7 % (Runde 1: 21,5 %; Runde 2:
  17,9 %; Runde 3: 15,7 %).
- Fallback-Anteil quantitaetsgewichtet (nach Spielhaeufigkeit ueber alle
  1.585 Decks): 4,0 % (Runde 2: 5,8 %) — die ganz grosse Mehrheit der
  tatsaechlich gespielten Karten ist jetzt korrekt klassifiziert; der
  verbleibende Fallback-Anteil liegt praktisch vollstaendig im Long Tail
  (Karten mit sehr niedriger Einzel-Quantity, meist < 10 Kopien insgesamt
  ueber alle 1.585 Decks).
- Kein Einfluss auf `removal_target_types` oder
  `Data/Models/opponent_state_weights.json` - diese Erweiterung betrifft
  ausschliesslich die Karten-Klassifikation fuer Statistik-/Vergleichs-
  zwecke, nicht das Gegner-Zustandsmodell.
- **Damit ist das im Auftrag genannte Ziel (300-500 kuratierte Karten)
  erreicht.** Eine weitere Runde (Schwelle < 10 Quantity) wuerde
  ueberwiegend Karten mit sehr geringer Spielhaeufigkeit erschliessen und
  ist im Rahmen dieses Auftrags nicht mehr vorgesehen; die Methodik bleibt
  fuer eine spaetere, separat beauftragte Fortsetzung dokumentiert und
  wiederholbar.
