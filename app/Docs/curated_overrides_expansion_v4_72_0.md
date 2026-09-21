# Kartenklassifikation — CURATED_OVERRIDES-Erweiterung, Runde 1 (v4.72.0)

Begleitdokument zu `App/archetype_profile/classify.py` (`CURATED_OVERRIDES`,
jetzt 85 statt 11 Eintraege, plus 5 neue allgemeine `_RAMP_RULES`/
`_STRATEGY_RULES`-Muster) und `Docs/README.md` (v4.72.0-Eintrag). Setzt die
im Nachtrag zu `Docs/opponent_model_calibration_v4_71_0.md` geklaerte
Methodik um: die Erweiterung soll "ausschliesslich aus der vollen,
bereits vorhandenen Datengrundlage abgeleitet werden", nicht durch
haendisch von aussen ausgewaehlte Einzelkarten.

## Methodik

1. **Ranking:** alle 8.445 eindeutigen Karten aus `deck_cards_slim.csv`
   nach Gesamt-Stueckzahl (`quantity`-Summe) ueber alle 1.585 echten Decks
   sortiert — dieselbe Datengrundlage, die auch v4.70.0/v4.71.0s
   Halbwertszeiten-Herleitung verwendet hat.
2. **Filter:** Basisland (Plains/Island/Swamp/Mountain/Forest/Wastes)
   ausgeschlossen (keine Klassifikation noetig); Karten, die bereits in
   `CURATED_OVERRIDES` stehen, ausgeschlossen; fuer jede verbleibende Karte
   wurde `classify_card` mit dem echten Oracle-Text aus
   `unique_cards_enriched.csv` aufgerufen und geprueft, ob das Ergebnis in
   den generischen Fallback faellt (`effect_tags[0] in
   {"unclassified", "vanilla_or_unclassified_body"}`).
3. Ergebnis vor jeder Aenderung: **1.995 von 8.445 Karten** (~23,6%)
   landeten im Fallback — bei weitem nicht alle davon sind "falsch"
   klassifiziert (einige, z. B. Ornithopter oder Slither Blade, SIND
   tatsaechlich vanilla bzw. nahezu vanilla und brauchen keinen Override —
   das wurde bei der Kuratierung individuell gegengeprueft, siehe unten).

## Schritt 1: allgemeine Regel-Luecken vor der Einzelkarten-Kuratierung

Bevor einzelne Karten kuratiert wurden, wurde die Fallback-Liste nach
**wiederkehrenden Formulierungsmustern** durchsucht — mit dem Ziel, echte
Regel-Luecken systematisch statt Karte-fuer-Karte zu schliessen (mehr
Wirkung pro Aenderung, konsistenter mit der bestehenden Regel-Engine, kein
unnoetig aufgeblaehtes `CURATED_OVERRIDES`). Fuenf Muster wurden gefunden
und behoben:

| Neues Muster | Ort | Treffer | Gesamt-Stueckzahl | Beispiele |
|---|---|---:|---:|---|
| `graveyard_recursion`-Regex erweitert um optionale "mit Mana Value N oder weniger"-Einschraenkung | `_STRATEGY_RULES` | 12 | — | Sun Titan, Sevinne's Reclamation |
| `land_recursion` ("play lands from your graveyard") | `_RAMP_RULES` (neu) | 5 | 305 | Ramunap Excavator, Crucible of Worlds, Conduit of Worlds |
| `trigger_doubler` ("triggers an additional time") | `_STRATEGY_RULES` (neu) | 21 | 662 | Panharmonicon, Harmonic Prodigy, Delney, Veyran |
| `clone_effect` ("copy of any/target artifact/creature/...") | `_STRATEGY_RULES` (neu) | 44 | 446 | Phyrexian Metamorph, Sculpting Steel, Mirrormade |
| `extra_untap_steps` ("untap all ... during each other player's/opponent's untap step") | `_STRATEGY_RULES` (neu) | 5 | 194 | Seedborn Muse, Unwinding Clock |
| `damage_multiplier` ("deals double/triple/twice/three times that/the damage") | `_STRATEGY_RULES` (neu) | 17 | 213 | Twinflame Tyrant, City on Fire, Fiery Emancipation |

**Zusammen 102 Karten** (nach Ueberschneidung, roh addiert 104) direkt
richtig klassifiziert, **ohne** dass dafuer ein einziger
`CURATED_OVERRIDES`-Eintrag noetig war — jede dieser 5 Regeln greift
zukuenftig automatisch auch fuer beliebige neue Karten mit derselben
Formulierung (z. B. neue Druckungen, die noch gar nicht in der
Trainingsdatenbank stehen). `trigger_doubler` und `clone_effect` waren mit
Abstand am ergiebigsten — beides sind seit einigen Jahren sehr haeufige
Vorlagen im Kartendesign (ETB-Trigger-Verdoppler bzw. Klon-Effekte).

Fallback-Liste danach: **1.893 Karten** (von 1.995).

## Schritt 2: Einzelkarten-Kuratierung der verbleibenden Top-Kandidaten

Die verbleibenden Fallback-Karten wurden erneut nach Gesamt-Stueckzahl
sortiert; alle Karten mit **>= 27 Kopien insgesamt** (bzw. mit Ausreissern
bis 27, siehe unten) wurden individuell anhand ihres echten Oracle-Texts
geprueft und — wo tatsaechlich ein nicht-triviales Muster vorliegt — als
neuer `CURATED_OVERRIDES`-Eintrag (role/effect_tags/simple_effect/
halbwertszeit) erfasst. Zwei Karten wurden bewusst **nicht** kuratiert,
obwohl sie in der Liste auftauchten:

- **Ornithopter** (38 Kopien): Text ist tatsaechlich nur "Flying" — der
  Fallback ("body/stats only") ist hier korrekt, kein Override noetig.
- **Slither Blade** (28 Kopien): Text ist nur "This creature can't be
  blocked" — naeher an vanilla als an einem eigenen Muster; bewusst als
  kleine, bekannte Ungenauigkeit offen gelassen (der Fallback-Text "body/
  stats only" ist fuer eine Evasion-Faehigkeit nicht perfekt praezise,
  aber die praktische Auswirkung auf die Statistik ist gering) statt einer
  eigenen, kaum aussagekraeftigen Override-Zeile.

**74 neue Eintraege** wurden ergaenzt (Liste komplett und mit Begruendung
in `App/archetype_profile/classify.py` direkt neben den Original-11
einsehbar) — von Deflecting Swat (161 Kopien) bis Comet Storm (30 Kopien).
`CURATED_OVERRIDES` hat damit jetzt **85 Eintraege** (vorher 11).

Wie bei den Original-11 ist `halbwertszeit` eine grobe, rein informative
0-1-Einschaetzung ("wie zuverlaessig/oft tritt der vereinfachte Effekt pro
Zug tatsaechlich ein") — subjektiv gesetzt nach demselben Massstab wie die
bestehenden 11 Beispiele, fliesst nicht in die Kern-Statistik ein.

## Statusbericht

- Fallback-Anteil gesamt: von 1.995/8.445 (23,6%) auf **1.819/8.445
  (21,5%)** gesunken (102 durch die 5 neuen Regeln + 74 durch
  Einzelkuratierung minus die 2 bewusst ausgelassenen = 176 Karten
  insgesamt geklaert; die 1.819 verbleibenden sind ueberwiegend Karten mit
  sehr geringer Gesamt-Stueckzahl — lange Tail-Verteilung).
- `CURATED_OVERRIDES`: **85 von den urspruenglich angepeilten 300-500**
  (Pareto-Ziel aus dem 2026-09-16-Klassifikationsplan) — der naechste
  sinnvolle Fortsetzungsschritt ist, dieselbe Skript-Methodik erneut
  laufen zu lassen und den naechsten Quantitaets-Streifen (z. B. 15-29
  Kopien) zu kuratieren, bis das Ziel erreicht ist. Kein neuer Input vom
  Nutzer noetig dafuer — reine Fleissarbeit nach bereits geklaerter
  Methodik.
- Diese Aenderung betrifft **nur** `App/archetype_profile/classify.py`
  (Kartenklassifikation fuer die Deck-Statistik/den Vergleichs-Tab) — sie
  wirkt sich NICHT auf `removal_target_types` (separate, eigene
  Regex-Logik) oder `opponent_state_weights.json`/das Gegner-Zustandsmodell
  aus. Kein Versionssprung der `opponent_state_weights.json`-Version
  noetig; `ENGINE_VERSION`/GUI-Titel wurden trotzdem auf 4.72.0 angehoben
  (projektweite Tool-Version).
