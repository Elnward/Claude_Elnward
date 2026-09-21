# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.70.0

Begleitdokument zu `Docs/README.md` (v4.70.0-Eintrag),
`Data/Models/opponent_state_weights.json` (version "1.8",
`permanent_type_half_life_turns` und der neue Guardrail
`half_life_ceiling_turns`) und `App/opponent_model/state_equation.py`s
Moduldoc-Abschnitt "v4.70.0" ("Halbwertszeiten-Recherche"). Baut auf
`Docs/opponent_model_calibration_v4_69_0.md` auf, behandelt aber ein
anderes Teilmodell: nicht die Farb-/Strategie-Kurven, sondern
`permanent_type_half_life_turns` — bislang reine, unbelegte
Erst-Schätzwerte seit v4.40.0.

## Ausgangsfrage des Nutzers (wörtlich)

> "Kannst du jetzt aus dem Verständnis der Decks und Farben entsprechende
> Gegnerfunktion abbilden. Oder müssen noch weitere Fragen geklärt werden?
> Ansonsten beginne damit, die Zustandsgleichungen aufzustellen [...] und
> lege entsprechende Halbwertszeiten an permanente Elemente. Falls du
> nicht ganz genau weißt, wie du diese Halbwertszeit anlegen sollst, dann
> kannst du ja einmal stichprobenartig herausfinden, zu wie viel Prozent
> eine Hand eines der möglichen Gegner ein Removal Spell hat, der auf
> diese Permanente aus der Stichprobe passt. Und dann kannst du über den
> Kartenpreis abschätzen, ganz grob, wie wertvoll die jeweilige Karte ist.
> [...] Damit hast du gegebenenfalls so eine ganz grobe Orientierung,
> welcher Effekt oder welche Mana-Kosten [...] welchen Einfluss auf die
> Halbwertszeit einer Karte auf dem Board haben."

**Erster Teil der Frage beantwortet, bevor an der eigentlichen Aufgabe
gearbeitet wurde**: die Gegner-Zustandsgleichung (`state_equation.py`)
existiert bereits seit v4.38.0 und wurde seither wiederholt kalibriert
(v4.39.0/v4.40.0/v4.41.0/v4.42.0/v4.43.0/v4.67.0/v4.69.0) — es handelte
sich also **nicht** um eine Neuentwicklung von Grund auf, sondern um eine
weitere, gezielte Kalibrierungsrunde für einen bislang unbelegten Teil
dieses bestehenden Modells.

## Ausgangslage: `permanent_type_half_life_turns`

Seit v4.40.0 dokumentiert als (`Data/Models/opponent_state_weights.json`,
alte `_comment`):

```json
{"creature": 4, "artifact": 7, "enchantment": 9, "planeswalker": 6, "land": 12}
```

mit dem expliziten Zusatz "ALLE Werte sind ERST-SCHÄTZWERTE — es existiert
keine reale Statistik darüber [...], um das zu kalibrieren." Genau diese
Lücke sollte diese Version schließen.

## Methodik: zweiteilig, exakt wie vom Nutzer vorgeschlagen

### Teil 1 — `removal_target_types()`: welchen Permanenttyp trifft eine Karte?

`App/archetype_profile/classify.py`s bestehende Klassifikation kennt zwar
grobe Rollen ("removal_single_exile" etc.), wirft aber die eigentliche
Zielangabe (Kreatur vs. Artefakt vs. ...) weg. Neue, rein additive
Funktion `removal_target_types(oracle_text) -> frozenset[str]`, Teilmenge
von `{creature, artifact, enchantment, planeswalker, land}`:

- Board-Wipes (`destroy/exile all <Typ(en)>`, inkl. Mehrfachaufzählungen),
- Einzelziel destroy/exile/tuck (inkl. beliebiger `non-X`-Qualifier-Präfixe
  wie "nonblack creature" und Mehrfachaufzählungen wie "creature, artifact,
  or enchantment"),
- die umgekehrte Wortstellung "owner of target X shuffles it into their
  library" (Chaos Warp — hier steht "target X" vor dem Verb),
- `-X/-X`-Entwertung (sowohl digit- als auch literale "X"-Schreibweise —
  siehe Bugfix unten),
- Schadenseffekte ("to target creature" nur Kreaturen, "to any target"
  zusätzlich Planeswalker),
- Bounce ("return target X to its owner's hand", mit beliebigem
  Zwischentext wie bei Cyclonic Rift),
- Landzerstörung (`destroy target land`, `sacrifice(s) a land` — siehe
  Bugfix unten) als eigener, fünfter Bucket.

**Bewusst ausgeschlossen**: Gegenzauber (verhindern, dass ein Permanent
je aufs Brett kommt, entfernen aber kein bereits liegendes Permanent — für
die Frage "wie lange überlebt ein liegendes Permanent" nicht relevant).

**Bekannte, disclosed Lücke**: abstimmungsbasierte Effekte ohne
"target"-Schlüsselwort (Council's Judgment) werden nicht erkannt.

**Zwei echte Regex-Lücken beim Testschreiben für diese Version gefunden
und behoben** (zusätzlich zu den vier Chaos-Warp-artigen Bugs, die schon
während der ursprünglichen Entwicklung der Funktion an 18 echten
Testkarten gefunden wurden):

1. Die `-X/-X`-Erkennung deckte nur die Ziffern-Variante ("-5/-5") ab,
   nicht Toxic Deluges tatsächlichen Wortlaut ("Each creature gets
   **-X/-X**..."). Behoben durch eine vereinheitlichte Regex
   `(?:each|all) creatures? gets? -(?:\d+|x)/-(?:\d+|x)`.
2. Die Landzerstörungs-Erkennung deckte nur den Imperativ ("Sacrifice a
   land") ab, nicht die 3.-Person-Form ("Target player sacrifices a
   land", "Each player sacrifices a land"). Behoben durch
   `sacrifices? a land`.

Beide Fixes wurden VOR der finalen Hand-Sampling-Simulation eingespielt —
die unten berichteten Häufigkeitswerte spiegeln bereits die korrigierte
Version wider.

### Teil 2 — Kartenpreis als Qualitäts-Proxy

`Training data/export_card_training_data.py` (lokales Nutzer-Skript, nicht
Teil der Cloud-Umgebung, da nur der Nutzer selbst Zugriff auf
`api.scryfall.com` und die lokale `commander_bracket3.sqlite` hat) wurde um
das Auslesen von Scryfalls `prices`-Objekt erweitert
(`usd`/`usd_foil`/`eur`/`tix`) — kostet keine zusätzlichen Anfragen, das
Feld kam ohnehin schon in jeder Collection-/Named-Antwort mit. Der Nutzer
führte das Skript lokal neu aus: 8.422 von 8.445 Karten angereichert, davon
92.9 % mit einem `price_usd`-Wert.

**Preis-Fallback-Kette** (pro Karte, in dieser Reihenfolge): `price_usd` →
`price_usd_foil` → `price_eur × 1.08` (grobe EUR→USD-Näherung) →
`price_tix` (MTGO-Tix, bewusst als allerletzter, sehr grober Notanker) →
Median aller bekannten Preise (für die verbleibenden 400 Karten / 4.7 %
ganz ohne jede Preisangabe — überwiegend Karten, die Scryfall nicht fand,
aber auch 122 gefundene, generell verbreitete Staples wie Arcane Signet,
Command Tower oder Brainstorm ohne Preisfeld auf dem von der
Collection-API gewählten Druck — neutral statt 0 behandelt, um diese
Karten weder künstlich abzuwerten noch aufzuwerten).

## Hand-Sampling-Simulation

Für jedes der 1.585 echten EDHREC-Average-Decks (`deck_cards_slim.csv`)
wird der volle Kartenpool nach `quantity` expandiert (kritisch: eine
Basic-Land-Zeile mit `quantity=20` zählt als 20 einzelne Karten im Pool,
sonst wäre die Landdichte verzerrt). Pro Deck werden 40 zufällige
7-Karten-Hände ohne Zurücklegen gezogen (`random.Random(20260919)`,
insgesamt 63.400 Hände über alle Decks). Für jede Hand und jeden der 5
Permanenttypen wird geprüft: enthält die Hand ≥1 Karte, deren
`removal_target_types()` diesen Typ trifft? Bei Treffer wird zusätzlich der
höchste aufgelöste Preis unter den treffenden Karten notiert (log1p
-transformiert vor der Mittelung, damit eine einzelne sehr teure
Ausreißerkarte den Durchschnitt nicht dominiert).

Dies ist bewusst eine **statische Eröffnungshand-Momentaufnahme**, keine
Zug-für-Zug-Spielsimulation über eine ganze Partie — eine dokumentierte,
disclosed Vereinfachung.

## Ergebnisse

### Rohe Trefferhäufigkeit (Anteil Hände mit ≥1 passendem Removal)

| Permanenttyp  | Häufigkeit |
|---------------|-----------:|
| creature      | 34.81 %    |
| artifact      | 19.52 %    |
| enchantment   | 18.10 %    |
| planeswalker  | 16.93 %    |
| land          |  2.18 %    |

Schon diese Rohzahl allein zeigt einen echten Fehler in der alten,
geratenen Reihung: `artifact` (Halbwertszeit 7) war **länger** als
`planeswalker` (Halbwertszeit 6) — obwohl Artefakte in der Stichprobe
**häufiger** beantwortet werden als Planeswalker. Das war falsch herum.

### Preisgewichtung (log1p-gemittelter Bestpreis der treffenden Karten)

| Permanenttyp  | Ø Bestpreis (≈) | relatives Gewicht |
|---------------|----------------:|-------------------:|
| creature      | 2.08 $          | 0.986              |
| artifact      | 2.10 $          | 0.992              |
| enchantment   | 2.14 $          | 1.001              |
| planeswalker  | 2.21 $          | 1.021              |

Überraschend schwaches Ergebnis: der Kartenpreis differenziert zwischen
den 4 Nicht-Land-Typen nur **sehr schwach** (relative Gewichte fast alle
nahe 1.0) — anders als vom Nutzer vielleicht erwartet, dominiert die reine
Trefferhäufigkeit das Bild fast vollständig, der Preis wirkt nur als
leichte Korrektur, nicht als eigenständiger, gleichwertiger Faktor. Das
ist selbst ein disclosed, ungeschöntes Ergebnis — es wäre leicht gewesen,
das Preissignal künstlich zu verstärken, um es "wichtiger aussehen zu
lassen"; stattdessen wird der schwache reale Befund so übernommen.

### Kombiniertes "Removal-Druck"-Maß und finale Halbwertszeiten

`Druck(t) = Häufigkeit(t) × relatives_Preisgewicht(t)`, anschließend je
Typ auf den Durchschnitt der 4 Nicht-Land-Typen normiert
(`RelDruck(t)`), und die neue Halbwertszeit am alten Vier-Typen-
Durchschnitt (6.5) verankert: `neue_Halbwertszeit(t) = 6.5 / RelDruck(t)`
— dieselbe "Anker am alten Durchschnitt, neu verteilt nach neuer
Evidenz"-Methodik wie schon bei den Farb-/Strategie-Kurven in v4.67.0/
v4.69.0.

| Typ          | alt | neu (empirisch) |
|--------------|----:|-----------------:|
| creature     |   4 | **4.2**          |
| artifact     |   7 | **7.5**          |
| enchantment  |   9 | **8.0**          |
| planeswalker |   6 | **8.4**          |
| land         |  12 | **30** (Ceiling, siehe unten) |

Hauptkorrektur: `artifact` und `planeswalker` tauschen ihre relative
Reihung (artifact jetzt kürzer, nicht länger). `enchantment` fällt von der
längsten auf eine mittlere Position. `creature` bleibt nahe am alten Wert
— jetzt aber belegt statt geraten.

## Land-Sonderfall: eine disclosed Policy-Entscheidung, keine Datenübernahme

Die rohe inverse Häufigkeits-Extrapolation für Land
(`4.2 × (34.81% / 2.18%) ≈ 63.8` Züge) liegt **über der eigenen maximalen
Simulationslänge dieses Tools** (`App/gui.py`s `turns_var`-Spinbox geht bis
30, `App/engine.py`s CLI-Default ist 10 Züge). Eine Halbwertszeit von 63.8
Zügen wäre in **jeder** mit diesem Tool tatsächlich simulierbaren Partie
praktisch gleichbedeutend mit "Land verfällt nie" — ohne das offen
auszuweisen.

Statt den Rohwert stillschweigend zu übernehmen, wurde ein neuer,
genereller Guardrail eingeführt:

```json
"guardrails": {"half_life_ceiling_turns": 30}
```

angewendet in `state_equation.py::_permanent_type_half_life` auf **alle
fünf** Permanenttypen (nicht nur Land) — ein zusätzliches
Sicherheitsnetz, falls eine künftige Kalibrierungsrunde versehentlich
wieder einen unplausibel großen Wert einträgt. Land steht damit auf dem
Ceiling-Wert selbst (12 → 30): eine bewusste Modellierungsentscheidung,
kein aus den Daten unmittelbar übernommener Messwert — im selben Sinne wie
v4.67.0s grüne Wipe-Readiness-Untergrenze (0.15), nur in die andere
Richtung (eine Obergrenze statt einer Untergrenze).

## Disclosed Limitationen (unverändert wichtig, nicht stillschweigend übergangen)

- Die Hand-Sampling-Simulation ist eine statische Eröffnungshand-
  Momentaufnahme, keine Zug-für-Zug-Spielsimulation über eine ganze
  Partie.
- Kartenpreis ist ein grober, korrelativer Qualitäts-Proxy, keine kausale
  Messung der Removal-Effizienz — und hat sich empirisch als schwacher
  Differenzierer zwischen den 4 Nicht-Land-Typen erwiesen.
- `removal_target_types()` bleibt eine dokumentierte Regex-Näherung mit
  einer bekannten Lücke bei abstimmungsbasierten Effekten (Council's
  Judgment).
- Land bleibt ein Policy-Wert (Ceiling), kein direkt gemessener Wert wie
  die anderen vier.

## Verbleibend offen

- Die eigentliche Engine-Integration (`App/engine.py`s Zugschleife) nutzt
  `advance_opponent_state` noch nicht — unverändert seit v4.43.0 als
  offene Lücke dokumentiert.
- Eine echte Zug-für-Zug-Validierung der neuen Halbwertszeiten (statt der
  statischen Eröffnungshand-Näherung) wäre nur mit echten, turn-genau
  geloggten Spielverläufen möglich — solche Daten liegen weiterhin nicht
  vor (dieselbe Lücke, die schon `impact_half_life_multiplier` in v4.41.0/
  v4.43.0 betraf).
