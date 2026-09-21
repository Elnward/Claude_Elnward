# Engine Value v1 — Route D (Value-Model)

**Status:** v1 implementiert in v4.13.0. Reporting-Layer (neue `engine_value.csv`
pro Run + persistenter Store), **nicht** an die Live-Entscheidungslogik
(`cast_score_v4`) angebunden — bewusste Scope-Grenze, siehe §5.

## 1. Ausgangslage und Ziel

Der Nutzer beschrieb die Idee früh im Projekt so: der vordefinierte,
kartenform-basierte Wert (Routen A–C: Manakosten-Kurven, Farbe, Keywords,
Kreatur-Körper, …) ist eine SCHÄTZUNG, bevor eine Karte je in einem echten
Spiel war. Ein "Engine Value" soll diese Schätzung mit einem Wert MISCHEN,
der aus echten Simulationsläufen GELERNT wurde — was eine Karte tatsächlich
an Metrik-Ereignissen (Karten gezogen, Schaden verursacht, Mana erzeugt, …)
produziert hat, wenn sie wirklich gespielt wurde.

Das ist eine **echte Erweiterung**, kein Rebranding: die vordefinierte
Bewertung reagiert nie darauf, ob eine Karte in der Praxis oft im Friedhof
landet, kein legales Ziel findet, wegen Mana-Knappheit nie gecastet wird
oder wegen guter Synergien überdurchschnittlich oft trifft. Der gelernte
Wert schon — vorausgesetzt, genug echte Läufe wurden bereits durchgeführt.

## 2. Zwei unabhängige Signale

**Vordefinierter Wert** (`predefined_static_value(card, strategy)`, neu in
v4.13.0): eine reine Kartenform-Schätzung OHNE GameState — kombiniert exakt
dieselben, bereits kalibrierten und getesteten Bausteine, die auch
`cast_score_v4` nutzt (`ValueModel.metric_value` für Draw/Removal/
Board-Wipe/Ramp-Rollen inkl. Farbmultiplikator, `keyword_value`,
`creature_body_value`, den Instant-Speed-Aufschlag, sowie feste Werte für
Tutor/Recursion/Protection-Rollen). Sie beantwortet: "Was sollte diese
Karte laut ihrem Text ungefähr wert sein, wenn sie genau einmal das tut,
was sie sagt?"

**Gelernter Wert** (`learned_value_per_seen`, persistiert): die bereits
bestehende `"Estimated value / seen"`-Spalte aus `card_impact.csv`
(`impact_rows_from_aggregate`, seit v4.x) — aber statt nur innerhalb EINES
Goldfish-Laufs zu leben, wird sie jetzt über mehrere, zeitlich getrennte
Läufe hinweg akkumuliert (siehe §3). Sie beantwortet: "Was hat diese Karte
in real simulierten Spielen tatsächlich an erfasstem Wert pro Mal, das sie
gezogen wurde, geliefert?"

Beide Seiten nutzen bewusst dieselbe `ValueModel`-Maschinerie (dieselben
Pro-Punkt-Raten, Farbmultiplikatoren usw.) — der Unterschied liegt nicht in
der Währung, sondern in der EINGABE (hypothetische Ein-mal-Ausführung vs.
echte, akkumulierte Spielereignisse).

## 3. Persistenz über Läufe hinweg (das eigentlich Neue an Route D)

Bisher endete jede Werte-Aggregation an der Grenze eines einzelnen
Goldfish-Aufrufs (`aggregate: Dict[str, Counter]` lebt nur für die Dauer
eines `run_pipeline_v440`-Aufrufs). Route D braucht eine Gedächtnis-Schicht,
die das überlebt.

Neue Datei: `Data/Learned/engine_value_store.json` — pro Kartenname:
```json
{"seen": 812.0, "learned_value_per_seen": 0.417, "runs_merged": 6, "last_updated": "..."}
```
Nach jedem abgeschlossenen Lauf verschmilzt `update_engine_value_store`
die frischen `impact_rows` (jede Zeile hat bereits `Seen` und
`Estimated value / seen`) gewichtet nach Stichprobengröße in den Store:
```
neue_seen = alte_seen + lauf_seen
neuer_avg = (alter_avg * alte_seen + lauf_avg * lauf_seen) / neue_seen
```
Das ist ein einfacher gewichteter laufender Mittelwert (keine Vergessens-
Rate/Decay in v1 — spätere Läufe werden nicht bevorzugt gegenüber
früheren). Eine Decay-Funktion (neuere Läufe zählen mehr, z. B. weil sich
die Engine selbst durch die B–C-Änderungen inzwischen verändert hat) ist
ein sinnvoller v2-Kandidat, aber bewusst nicht Teil von v1 — siehe §5.

**Scope-Entscheidung, bewusst gewählt:** der Store ist NICHT pro Deck
getrennt, sondern global über alle Decks hinweg pro Kartenname. Begründung:
`cast_score_v4`/die vordefinierte Bewertung sind heute ebenfalls Deck-
agnostisch (nur Farbe/Strategie-Archetyp-bewusst, nicht Deck-spezifisch) —
ein globaler Store passt zu diesem bestehenden Modell und lässt eine Karte
wie "Sol Ring" über alle Decks hinweg Erfahrung sammeln, was für eine
generische Mana-Rock-Karte sinnvoll ist. Der ehrliche Nachteil: Deck-
spezifische Synergien (eine Karte, die nur in EINEM bestimmten Deck
außergewöhnlich gut performt) werden in den globalen Durchschnitt verwässert
statt separat sichtbar zu sein. Für v1 akzeptiert; ein Deck-Namespace
(`store["decks"]["<deck>"]["cards"][...]`) wäre die naheliegende v2-
Erweiterung, sobald genug Läufe über mehrere Decks hinweg vorliegen, um zu
beurteilen, ob das den Unterschied tatsächlich lohnt.

## 4. Die Mischung: Bayesianisches Shrinkage statt harter Schwelle

`ValueModel.engine_value(predefined_value, learned_value_per_seen,
learned_seen)`:
```
blend_weight = min(engine_value_max_learned_weight,
                    learned_seen / (learned_seen + engine_value_cold_start_pseudo_seen))
engine_value = (1 - blend_weight) * predefined_value + blend_weight * learned_value_per_seen
```
Das ist dieselbe Grundidee wie ein gewichteter Bayes-Schätzer (z. B. IMDBs
alte "weighted rating"-Formel): ein Pseudo-Stichprobenumfang
(`engine_value_cold_start_pseudo_seen`, Startwert 30) repräsentiert, wie
viel Vertrauen die vordefinierte Schätzung von Haus aus mitbringt. Bei
`learned_seen = 0` (Karte wurde noch nie in einem geloggten Lauf gesehen —
der Store-Eintrag existiert schlicht nicht) ist `blend_weight = 0`:
`engine_value` ist dann BYTE-IDENTISCH mit dem vordefinierten Wert, kein
Sonderfall nötig. Das ist bewusst nach demselben Sicherheitsprinzip wie
`color_category_multiplier`s `color_identity=None`-Fallback entworfen
(v4.11.0) — ein frischer Checkout mit leerem Store verändert nichts an der
bestehenden Bewertung.

`engine_value_max_learned_weight` (Startwert 0,85) verhindert, dass der
gelernte Wert die vordefinierte Schätzung JEMALS vollständig verdrängt,
selbst bei riesigem Stichprobenumfang — ein Rest-Anker an die kartenform-
basierte Logik bleibt immer bestehen. Begründung: die aufgezeichneten
Metrik-Ereignisse sind selbst nur so vollständig wie die `record_impact()`-
Aufrufe, die sie erzeugen (z. B. erfasst ein reiner Kreatur-Körper ohne
Text kaum Metrik-Ereignisse — der gelernte Wert würde eine Vanilla-Kreatur
mit starkem Körper systematisch unterschätzen, weil Kampfschaden nur über
`combat_damage_per_point` und nicht konsequent für jede einzelne Blockade/
jeden Angriff erfasst wird). Ein Deckel schützt vor dieser bekannten Lücke,
statt sie stillschweigend zu ignorieren.

## 5. Bewusste Scope-Grenzen (v1)

Nach demselben ehrlichen Muster wie Delve/Convoke (v4.11.0) und der
Board-Wipe-Zwei-Parameter-Schätzung (v4.12.0):

- **Nicht an `cast_score_v4` angebunden.** `engine_value` wird in v1 NUR in
  einer neuen Report-Datei (`engine_value.csv`, pro Lauf im Result-Ordner)
  sichtbar gemacht, nicht in die Spielentscheidungen der laufenden
  Simulation eingespeist. Grund: der Store ist bei einem frischen Checkout
  leer und selbst nach einigen Läufen statistisch dünn — ihn direkt in die
  Sequenzierungs-Heuristik einzubauen, bevor genug echte Daten vorliegen,
  um das Verhalten zu verifizieren, wäre ein ungetesteter Eingriff in den
  am breitesten genutzten Bewertungspfad der Engine. Sobald über mehrere
  echte Deck-Läufe hinweg genug `engine_value_store.json`-Historie
  vorliegt, ist das Anbinden an `cast_score_v4` der naheliegende nächste
  Schritt (mit vollem Regressions-Testlauf, analog zu v4.11.0/v4.12.0).
- **Kein Decay/keine Rücknahme veralteter Daten.** Ein Lauf von vor zehn
  Engine-Versionen zählt gleich viel wie ein Lauf von heute. Für die
  aktuelle Phase (die Engine selbst ändert sich noch häufig) ist das ein
  bekanntes, aber akzeptiertes Risiko.
- **Kein Deck-Namespace** (siehe §3) — Karten-Performance wird global,
  nicht pro Deck gelernt.
- **Keine Kausalitäts-/Gewinnkorrelation.** `learned_value_per_seen` misst
  erfasste EREIGNISSE (Karten gezogen, Schaden verursacht, …), nicht ob das
  Spiel am Ende gewonnen wurde. Eine "hat diese Karte tatsächlich zum Sieg
  beigetragen"-Analyse (echte Kausalinferenz, mit den bekannten
  Konfundierungsproblemen) ist explizit NICHT Teil von Route D — das wäre
  ein eigenes, deutlich größeres Work Package.

## 6. Neue Tunables (`Data/Models/goldfish_value_model.json`)

| Schlüssel | Startwert | Bedeutung |
|---|---|---|
| `engine_value_cold_start_pseudo_seen` | 30.0 | Pseudo-Stichprobenumfang, der die vordefinierte Schätzung anfangs "wert" ist |
| `engine_value_max_learned_weight` | 0.85 | Obergrenze, wie stark der gelernte Wert die Mischung dominieren darf |

## 7. Dateien

- `App/engine.py`: `predefined_static_value`, `load_engine_value_store`,
  `save_engine_value_store`, `update_engine_value_store`,
  `ValueModel.engine_value`, Hook in `run_pipeline_v440` (schreibt
  `engine_value.csv` und aktualisiert `Data/Learned/engine_value_store.json`).
- `Data/Learned/engine_value_store.json`: der persistente Store (v1: leer/
  nicht vorhanden bei frischem Checkout — wird beim ersten echten Lauf
  angelegt).
- `tests/test_engine_value.py`: Unit-Tests für Blend-Logik (inkl. Cold-
  Start-Byte-Identität und Deckel), Store-Merge-Arithmetik, und
  `predefined_static_value` an echten Karten aus dem Projekt-Cache.
