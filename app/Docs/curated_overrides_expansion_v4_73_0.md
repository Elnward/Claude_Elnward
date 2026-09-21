# CURATED_OVERRIDES-Erweiterung, Runde 2 (v4.73.0)

## Kontext

Fortsetzung von v4.72.0 (Runde 1, 11 → 85 Eintraege). Nach Nutzer-Bestaetigung
("Bestehen lassen" fuer die preisabhaengige Halbwertszeit aus v4.71.0, plus
Praezisierung der CURATED_OVERRIDES-Methodik: ausschliesslich datengetrieben,
keine gildenspezifischen/extern konstruierten Gewichtungen) wurde die exakt
gleiche, bereits in Runde 1 etablierte Methodik ein zweites Mal angewendet,
mit dem expliziten Auftrag "Bitte arbeite dich bis zu dem Ziel iterativ Step
für Step durch und das eigenständig" (Ziel: 300-500 kuratierte Karten).

## Methodik (unveraendert gegenueber Runde 1)

1. Alle 8.445 eindeutigen Karten aus `deck_cards_slim.csv` nach summierter
   `quantity` ueber alle 1.585 echten Decks ranken.
2. Basisländer und bereits kuratierte Karten (jetzt: die 85 aus Runde 1)
   ausschliessen.
3. Fuer jede verbleibende Karte `classify_card` mit dem echten `oracle_text`
   aus `unique_cards_enriched.csv` ausfuehren und pruefen, ob
   `effect_tags[0]` in `{"unclassified", "vanilla_or_unclassified_body"}`
   liegt (Fallback-Treffer).
4. Vor jeder Einzelkuratierung zuerst nach wiederkehrenden Formulierungs-
   mustern suchen, die sich als NEUE ALLGEMEINE REGEX-REGEL lohnen (hoehere
   Hebelwirkung, wirkt auch auf zukuenftige/unbekannte Karten mit gleicher
   Vorlage) - erst danach die verbleibenden Karten einzeln mit ihrem echten
   Oracle-Text kuratieren.

## Ausgangslage

Nach Runde 1 (v4.72.0): 85 kuratierte Karten, 191 Fallback-Karten mit
Gesamt-Quantity >= 15 verblieben (Batch fuer Runde 2).

## Neue allgemeine Regeln (Runde 2)

Wirkung gemessen gegen genau diesen 191-Karten-Batch (vor Runde-2-Kuration):

| Tag | Regel-Ort | Muster (sinngemaess) | Karten | Summe Quantity | Beispiele |
|---|---|---|---|---|---|
| `mana_doubler` | `_RAMP_RULES` | "produces twice/three times as much [mana]" | 2 | 40 | Mana Reflection, Nyxbloom Ancient |
| `draw_cards` (erweitert) | `_CARD_ADVANTAGE_RULES` | "draws (a/an/two/.../X) additional card(s)" statt nur "draws X cards" | 4 | 97 | Font of Mythos, Dictate of Kruphix |
| `card_selection` (erweitert) | `_CARD_ADVANTAGE_RULES` | "look at/reveal the top card... if it's a land card" | 3 | 68 | Coiling Oracle, Risen Reef |
| `cascade_value` | `_STRATEGY_RULES` | `\bcascade\b` | 5 | 110 | Maelstrom Wanderer, Apex Devastator |
| `evasion_unblockable` | `_STRATEGY_RULES` | "can't be blocked" | 4 | 87 | Slither Blade, Tetsuko Umezawa |
| `fog_effect` | `_INTERACTION_RULES` | "prevent all combat damage" | 3 | 59 | Spore Frog, Dolmen Gate, Fog |

Summe: 21 Karten (461 Quantity) automatisch durch 6 neue generelle Regeln
gefixt, ohne eine einzige davon manuell zu kuratieren.

Hinweis: Slither Blade war in Runde 1 explizit als "korrekt vanilla, keine
Kuration noetig" dokumentiert (nur "can't be blocked") - durch die neue
`evasion_unblockable`-Regel wird sie jetzt automatisch korrekt klassifiziert,
statt weiterhin im generischen Fallback zu landen. Kein Widerspruch zur
Runde-1-Entscheidung, nur ein spaeterer, systematischerer Fix desselben
Sachverhalts.

## Manuell kuratierte Karten (167 neue CURATED_OVERRIDES-Eintraege)

Nach Abzug der 21 durch neue Regeln automatisch gefixten Karten blieben 170
Karten mit Quantity >= 15 im Fallback. Davon wurden 167 einzeln mit ihrem
echten Oracle-Text kuratiert (role/effect_tags/simple_effect/halbwertszeit,
exakt wie in Runde 1). Die volle Liste der 167 neuen Namen steht direkt im
Quellcode (`App/archetype_profile/classify.py`, Abschnitt
"v4.73.0: CURATED_OVERRIDES-Erweiterung Runde 2") — der erste Eintrag
dieser Runde ist Venser, Shaper Savant, der letzte Bruse Tarl, Boorish
Herder.

### Bewusst ausgelassen (3 Karten)

- **Ornithopter** (qty 38): reiner Vanilla-Effekt ("Flying" only) - die
  bestehende Fallback-Klassifikation ist bereits korrekt, keine Kuration
  noetig (gleiche Begruendung wie Runde 1 fuer Ornithopter/Slither Blade).
- **Sire of Seven Deaths** (qty 25): reine Stichwort-Haufung ohne
  eigenstaendigen, ueber die Einzelkeywords hinausgehenden Effekt - analog
  zur Runde-1-Begruendung fuer dieselbe Karte.
- **Indomitable Ancients** (qty 16): leerer `oracle_text` in der
  bereitgestellten Datenquelle (Datenluecke, kein Klassifikations-
  problem) - wird nicht als kartenspezifisches Problem dokumentiert,
  nur uebersprungen. Betrifft dieselbe bekannte, bereits offengelegte
  Datenluecke wie die 278 durch die URL-Encoding-Korrektur in
  `export_card_training_data.py` (v4.71.0) betroffenen Karten (dieser
  Re-Export wurde vom Nutzer noch nicht erneut lokal ausgefuehrt).

## Statusbericht nach Runde 2

- CURATED_OVERRIDES: 85 → 252 Eintraege (Ziel: 300-500).
- Generelle Regex-Regeln insgesamt: 11 (Runde 1) + 6 (Runde 2) = 17 neue
  Muster seit Beginn der Erweiterung.
- Fallback-Anteil (Kartenanzahl, ueber alle 8.434 Karten mit vorhandenem
  Oracle-Text, Basislaender ausgenommen): 17,9 % (vorher nach Runde 1:
  21,5 %).
- Fallback-Anteil quantitaetsgewichtet (nach Spielhaeufigkeit ueber alle
  1.585 Decks): 5,8 % - die grosse Mehrheit der tatsaechlich gespielten
  Karten ist bereits korrekt klassifiziert; der verbleibende Fallback-
  Anteil liegt ueberwiegend im Long Tail (seltener gespielte Karten mit
  niedriger Einzel-Quantity).
- Kein Einfluss auf `removal_target_types` oder
  `Data/Models/opponent_state_weights.json` - diese Erweiterung betrifft
  ausschliesslich die Karten-Klassifikation fuer Statistik-/Vergleichs-
  zwecke, nicht das Gegner-Zustandsmodell.
- Ziel (300-500) noch nicht erreicht - naechste Runde (v4.74.0, gleiche
  Methodik) folgt automatisch im Rahmen des laufenden Auftrags.
