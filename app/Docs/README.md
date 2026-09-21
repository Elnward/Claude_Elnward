# Commander Goldfish

## v4.75.0 — Fix: Absturz beim Programmstart ohne installiertes `numpy`

**Ausgangspunkt:** Nutzer meldete direkt nach v4.74.0 einen Absturz beim
Programmstart (`Start_Goldfish_GUI.bat` → `commander_goldfish.py`) mit
`ModuleNotFoundError: No module named 'numpy'`, tief verschachtelt hinter
mehreren `ModuleNotFoundError: No module named 'archetype_profile'`.

**Ursache:** seit v4.68.0 importiert `App/engine.py` das
`App/archetype_profile`-Paket bereits beim reinen Modul-Laden (nicht erst
bei Bedarf), und `App/archetype_profile/__init__.py` importiert dabei
selbst `numpy` (über `reference_model.py`). War `numpy` in der
Python-Umgebung des Nutzers nicht installiert, schlug **die gesamte App**
schon beim Start fehl — obwohl `numpy` sonst keine Abhängigkeit dieses
Tools ist (Goldfishing, Win-Condition-Tests, Gegnermodell etc. sind reines
Stdlib) und `numpy` nur für den einzelnen Tab "Vergleich (1.585 Decks)"
gebraucht wird. Dieser eine Tab hatte in `App/gui.py` bereits eine
try/except-Absicherung mit freundlicher Fehlermeldung — die half aber
nichts, weil der Absturz schon beim Import von `engine.py` selbst
passierte, lange bevor die GUI überhaupt startet.

**Fix:** der `archetype_profile`-Import in `App/engine.py` fängt einen
Import-Fehler jetzt ab, merkt sich die Fehlermeldung, und lässt den Rest
der App normal starten. Erst wenn der Vergleichs-Tab tatsächlich benutzt
wird, kommt eine klare, verständliche Fehlermeldung ("... fehlt 'numpy' in
dieser Python-Umgebung - 'pip install numpy' beheben und die App neu
starten. Der Rest des Tools funktioniert davon unabhängig.") statt eines
Absturzes. Mit installiertem `numpy` (Normalfall) ändert sich nichts am
Verhalten — reine Zusatz-Robustheit für den Fehlerfall. Verifiziert per
Subprozess-Test mit künstlich blockiertem `numpy`-Import: `engine.py` und
`gui.py` laden jetzt beide erfolgreich durch, die beiden betroffenen
Funktionen werfen die neue klare Fehlermeldung statt abzustürzen.

**Sofortmaßnahme für den Nutzer:** in derselben Python-Umgebung, mit der
die App gestartet wird, `pip install numpy` (bzw. `python -m pip install
numpy`) ausführen, dann startet auch der Vergleichs-Tab. Der Rest des
Tools läuft ab sofort unabhängig davon.

9 neue Tests (`test_v4750_graceful_archetype_profile_degradation.py`),
davon 4 per Subprozess mit blockiertem `numpy`-Import.

## v4.74.0 — CURATED_OVERRIDES-Erweiterung, Runde 3 (252 → 415 Karten) — Ziel erreicht

**Auftrag:** Autonome Fortsetzung von v4.73.0 nach dem Auftrag "Bitte
arbeite dich bis zu dem Ziel iterativ Step für Step durch und das
eigenständig. Sobald du das Ziel erreicht hast, sag mir bitte Bescheid, ob
das Tool jetzt einwandfrei funktioniert." — dieselbe, bereits zweimal
etablierte datengetriebene Methodik ein drittes Mal angewendet, diesmal mit
auf Quantity ≥ 10 abgesenkter Schwelle (Runde 1/2 nutzten ≥ 15), um den
300-500-Zielkorridor zu erreichen.

**Methodik:** identisch zu Runde 1/2. Zunächst erneut nach allgemeinen
Regel-Lücken gesucht — **4 neue Muster** gefunden (`land_type_fixing` in
`_RAMP_RULES`, mit Abstand die wirkungsstärkste Einzelregel der gesamten
Erweiterung: 266 Gesamt-Quantity für nur 2 Karten, Yavimaya Cradle of
Growth und Urborg Tomb of Yawgmoth; `impulse_draw` in
`_CARD_ADVANTAGE_RULES`; `untap_all_nonland_combo` sowie eine um die
"shuffle"-Formulierung erweiterte `wheel_effect`-Regel in
`_STRATEGY_RULES`) — zusammen 11 Karten (373 Quantity) automatisch korrekt
klassifiziert, ohne Einzelkarten-Overrides. Danach die verbleibenden 170
Top-Kandidaten einzeln anhand ihres echten Oracle-Texts kuratiert — 163
neue `CURATED_OVERRIDES`-Einträge (Desecrate Reality bis Erdwal
Illuminator), sieben bewusst ausgelassen (Ornithopter, Sire of Seven
Deaths, Rograkh Son of Rohgahh, Healer's Hawk, Shrike Force, Deadly
Recluse, Bygone Colossus — alle reine Vanilla-/Keyword-Körper ohne
eigenständigen Effekt).

**Ergebnis:** `CURATED_OVERRIDES` jetzt **415 Karten — der ursprünglich
angepeilte Zielkorridor von 300-500 ist damit erreicht.** Fallback-Anteil
(Kartenanzahl) von 17,9 % auf 15,7 % gesunken, quantitätsgewichtet (nach
echter Spielhäufigkeit) nur noch 4,0 %. Betrifft weiterhin ausschließlich
`App/archetype_profile/classify.py` — kein Einfluss auf
`removal_target_types` oder `opponent_state_weights.json`/das
Gegner-Zustandsmodell. Volle Tabellen, Begründungen und die
Statusübersicht (inkl. Erklärung, warum diese Runde die letzte planmäßige
dieses Auftrags ist): `Docs/curated_overrides_expansion_v4_74_0.md`. 11
neue Tests (`test_v4740_curated_overrides_expansion_round3.py`).

## v4.73.0 — CURATED_OVERRIDES-Erweiterung, Runde 2 (85 → 252 Karten)

**Auftrag:** Autonome Fortsetzung von v4.72.0 nach explizitem Nutzer-Auftrag
("Bitte arbeite dich bis zu dem Ziel iterativ Step für Step durch und das
eigenständig") — dieselbe, bereits etablierte datengetriebene Methodik
(Kartenhäufigkeits-Ranking, keine externen/gildenspezifischen Gewichtungen)
ein zweites Mal angewendet, um näher an das 300-500-Ziel heranzukommen.

**Methodik:** identisch zu Runde 1. Ausgangspunkt: die 191 nach Runde 1
verbliebenen Fallback-Karten mit Gesamt-Quantity ≥ 15. Zunächst erneut
nach allgemeinen Regel-Lücken gesucht — **6 neue Muster** gefunden
(`mana_doubler` in `_RAMP_RULES`; eine verbreiterte "draws X additional
cards"-Fassung sowie eine "look at top card, if it's a land"-Regel in
`_CARD_ADVANTAGE_RULES`; `cascade_value` und `evasion_unblockable` in
`_STRATEGY_RULES`; `fog_effect` in `_INTERACTION_RULES`) — zusammen 21
Karten (u. a. Maelstrom Wanderer, Nyxbloom Ancient, Slither Blade, Fog)
automatisch korrekt klassifiziert, ohne Einzelkarten-Overrides. Danach die
verbleibenden 170 Top-Kandidaten einzeln anhand ihres echten Oracle-Texts
kuratiert — 167 neue `CURATED_OVERRIDES`-Einträge (Venser, Shaper Savant
bis Bruse Tarl, Boorish Herder), drei bewusst ausgelassen (Ornithopter,
Sire of Seven Deaths — beide tatsächlich vanilla/reine Keyword-Häufung,
Fallback war schon korrekt; Indomitable Ancients — leerer Oracle-Text in
der Datenquelle, reine Datenlücke statt Klassifikationsproblem).

**Ergebnis:** `CURATED_OVERRIDES` jetzt **252 von den ursprünglich
angepeilten 300-500 Karten**. Fallback-Anteil (Kartenanzahl) von 21,5 %
auf 17,9 % gesunken, quantitätsgewichtet (nach echter Spielhäufigkeit) nur
noch 5,8 %. Betrifft weiterhin ausschließlich
`App/archetype_profile/classify.py` — kein Einfluss auf
`removal_target_types` oder `opponent_state_weights.json`/das
Gegner-Zustandsmodell. Volle Tabellen, Begründungen und die
Statusübersicht: `Docs/curated_overrides_expansion_v4_73_0.md`. 6 neue
Tests (`test_v4730_curated_overrides_expansion_round2.py`). Ziel noch
nicht erreicht — nächste Runde folgt automatisch im Rahmen des laufenden
Auftrags.

## v4.72.0 — CURATED_OVERRIDES-Erweiterung, Runde 1 (11 → 85 Karten)

**Auftrag:** Fortsetzung des im Nachtrag zu v4.71.0 geklärten Punkts —
"Mach weiter, änder den Code" zur präzisierten Methodik: `CURATED_OVERRIDES`
soll ausschließlich aus der vollen, bereits vorhandenen Datengrundlage
abgeleitet werden (Kartenhäufigkeits-Ranking), nicht durch händische
Einzelauswahl von außen.

**Methodik:** alle 8.445 eindeutigen Karten aus `deck_cards_slim.csv` nach
Gesamt-Stückzahl über alle 1.585 echten Decks sortiert; für jede noch nicht
kuratierte Karte geprüft, ob die Regel-Engine (`classify_card`) nur den
generischen Fallback liefert (23,6 % aller Karten, 1.995/8.445). Vor der
Einzelkarten-Kuratierung wurden **5 echte, allgemeine Regel-Lücken**
gefunden und als neue `_RAMP_RULES`/`_STRATEGY_RULES`-Muster behoben
(`land_recursion`, `trigger_doubler`, `clone_effect`, `extra_untap_steps`,
`damage_multiplier`, plus eine um eine "mit Mana Value N oder weniger"-
Einschränkung erweiterte `graveyard_recursion`-Regex) — zusammen 102
Karten (u. a. Sun Titan, Seedborn Muse, Panharmonicon, Phyrexian
Metamorph) korrekt klassifiziert, **ohne** dafür Einzelkarten-Overrides zu
brauchen; diese Regeln greifen künftig automatisch auch für neue Karten
mit derselben Formulierung. Erst danach wurden die verbleibenden
Top-Kandidaten (≥ 27 Kopien gesamt) einzeln anhand ihres echten
Oracle-Texts kuratiert — 74 neue `CURATED_OVERRIDES`-Einträge (Deflecting
Swat bis Comet Storm), zwei bewusst ausgelassen (Ornithopter, Slither
Blade — tatsächlich vanilla bzw. nahe dran, Fallback war hier schon
korrekt).

**Ergebnis:** `CURATED_OVERRIDES` jetzt **85 von den ursprünglich
angepeilten 300-500 Karten**. Fallback-Anteil gesamt von 23,6 % auf 21,5 %
gesunken. Betrifft nur `App/archetype_profile/classify.py` (Kartenklassifikation
für Deck-Statistik/Vergleichs-Tab) — wirkt sich nicht auf
`removal_target_types` oder `opponent_state_weights.json`/das
Gegner-Zustandsmodell aus, daher kein Versionssprung der Weights-Version.
Volle Ranking-Tabellen, die vollständige Liste und Begründung: `Docs/curated_overrides_expansion_v4_72_0.md`.
Nächster sinnvoller Fortsetzungsschritt (kein neuer Nutzer-Input nötig):
denselben Ranking-Schritt erneut laufen lassen und den nächsten
Quantitäts-Streifen kuratieren, bis das 300-500-Ziel erreicht ist.

15 neue Tests (`test_v4720_curated_overrides_expansion.py`), 873 gesamt,
keine Regression.

---

## v4.71.0 — Engine-Integrations-Audit + logarithmische Wertigkeits-Funktion

**Auftrag (Nutzer, wörtlich):**
"Kannst du bitte die [seit v4.43.0] offene Lücke schließen und die Engine
Integration diesbezüglich nutzbar machen? Des Weiteren sagst du, dass es
noch offen ist, dass die echte Zug-für-Zug-Validierung der neuen
Halbwertszeiten nur dann möglich wäre, wenn man Turn genau gelockte
Spielverläufe betrachtet. Das ist durchaus in Ordnung, wenn das nur offen
ist. Es ist ja eine grobe Abschätzung, die sich allein darauf stützt, äh,
die Halbwertszeit, wie viel Interaktion ist theoretisch wahrscheinlich und
dann wie wertig ist das zu interagierende Medium, ob sich dann die äh,
Interaktion wirklich lohnt. Und das soll dann quasi diese Halbwertszeit
beschreiben. Dabei wäre es gut, wenn wir äh, die Funktion der Wertigkeit
nicht linear halten, sondern logarithmisch: kleine Änderungen im Preis
machen schon einiges aus, aber der Unterschied zwischen der Wertigkeit bei
einer 30-Euro-Karte und einer 500-Euro-Karte sollte kaum merkbar sein.
Keine Karte soll jemals nie interagierend sein, das heißt, ein Wert von 0
oder ähnliches sollte eine Karte nicht durch ihre Wertigkeit immun machen,
ungewollt. Ansonsten gehe bitte durch unsere bisherigen Schritte einmal
durch, um zu gucken, ob alles jetzt implementiert ist und läuft. Wenn nicht
alles implementiert ist, dann implementiere es und sorge dafür, dass ich
das Tool einwandfrei verwenden kann. Wenn noch offene Fragen sind,
Näherungen sind, die irgendwie noch pauschalisiert sind oder irgendwelche
losen Enden nicht abgeschlossen sind, dann sage das bitte."

**Teil 1 — Engine-Integrations-Audit:** die in `opponent_state_weights.json`s
`note`-Feld seit v4.43.0 mitgeschleppte Zeile "Verbleibend offen: [...] die
eigentliche Engine-Integration (App/engine.py-Zugschleife)" war **veraltete
Dokumentation, kein realer Mangel**. Die echte Zugschleifen-Integration
(`advanced_opponent_model`/`advanced_opponent_seats`) wurde bereits in
v4.63.0-v4.66.0 gebaut: eigenes `OpponentProfile`/`OpponentState`-Paar pro
Sitzplatz, echter Aufruf während der Simulation, GUI-Dialog samt
Status-Indikator und Ergebnis-Tab, 34 dedizierte Tests inkl. eines echten
End-to-End-Laufs. Die Notiz wurde an der Fundstelle mit einem
`[KORRIGIERT v4.71.0: ...]`-Zusatz versehen (nicht gelöscht). Weiterhin
bewusst begrenzt (kein Bug): nur 1-2 Farben und nur Bracket 3 pro
Sitzplatz, hart durchgesetzt via `_validate_advanced_opponent_seats`.

**Teil 2 — Neue "Wertigkeits-Funktion" für Permanente:** ergänzt (nicht
ersetzt) `impact_half_life_multiplier` um einen zweiten, multiplikativ
kombinierten Faktor, der den Preis des Permanents selbst (nicht der
Removal-Antwort wie in v4.70.0) einbezieht — "wie wertig ist das zu
interagierende Medium". Neue Datenbasis `permanent_type_value_usd`:
spielhäufigkeitsgewichtete, log1p-gemittelte Durchschnittspreise über alle
1.585 echten Decks (creature 2.60, artifact 2.64, enchantment 3.96,
planeswalker 5.12, land 1.46 USD) — bewusst ohne Bracket-Aufschlüsselung,
da der volle Datensatz keine verifizierten Bracket-Label hat.

Die Kurve `_card_value_weight(p) = floor + (1-floor) · log1p(p)/(log1p(p)+k)`
(k=0.25, floor=0.3) erfüllt beide Vorgaben gleichzeitig: Differenz 0 vs.
5 USD = 0.58 (deutlich spürbar), Differenz 30 vs. 500 USD = nur 0.029
(kaum merkbar) — zwangsläufig konzentriert sich die Differenzierung damit
im Bereich $0-$10, wo auch die real gemessenen Bucket-Durchschnitte liegen
(disclosed, keine zufällige Nebenwirkung). `_bucket_value_multiplier`
bildet das auf einen Halbwertszeit-Multiplikator zwischen 0.65 und 1.25 ab.

**Immunitäts-Garantie (zweifach erzwungen, wie vom Nutzer gefordert):**
(1) der `floor` verhindert, dass die Wertigkeit je exakt 0 wird, (2) die
neue Kombinationsfunktion `_effective_half_life` wendet den bestehenden
`guardrails.half_life_ceiling_turns`-Guardrail (30 Züge) ein zweites Mal
auf das FINALE, bereits kombinierte Ergebnis an — strukturell redundant zu
(1), damit auch eine künftige Fehlkalibrierung keine faktische Immunität
erzeugen kann. Dedizierter Adversarial-Test simuliert genau diesen
Fehlerfall (Preis=0, `max_multiplier` künstlich auf 10) und bestätigt die
Deckelung.

**Teil 3 — Vollständiger Lücken-Audit:** alle bisher offen ausgewiesenen
Punkte durchgegangen; nur die Engine-Integrations-Notiz war fälschlich als
offen markiert, alles Weitere (4-/5-farbige Identitäten, Gilden-Synergie,
`impact_half_life_multiplier` bracket-seitig, Zug-für-Zug-Validierung,
`removal_target_types`-Abstimmungslücke, aggro/horde `wipe_growth`,
`CURATED_OVERRIDES`, Strategy-Fallback-Anteil) bleibt echt offen und ist in
`Docs/opponent_model_calibration_v4_71_0.md` vollständig tabellarisch
aufgeführt. Zusätzlich beim Audit gefunden und behoben: ein
URL-Kodierungs-Bug in `Training data/export_card_training_data.py`s
Scryfall-Named-Fallback, der 278 von 8.445 Karten (3,3 %, v.a. Transform-/
MDFC-Karten mit Komma oder Apostroph im Namen wie "Aang, Swift Savior")
ohne Manavalue/Typ ließ — behoben via `urllib.parse.quote()`; wirkt erst
nach dem nächsten lokalen Skript-Lauf.

Volle Herleitung, Preistabellen und Formel-Kalibrierung:
`Docs/opponent_model_calibration_v4_71_0.md`.

`Data/Models/opponent_state_weights.json` version → "1.9".

---

## v4.70.0 — Halbwertszeiten-Recherche: empirische Herleitung von permanent_type_half_life_turns

**Auftrag (Nutzer, wörtlich):**
"Vielen Dank. Damit kommen wir ja dem Ganzen einen Schritt näher. Kannst du
jetzt aus dem Verständnis der Decks und Farben entsprechende Gegnerfunktion
abbilden. Oder müssen noch weitere Fragen geklärt werden? Ansonsten beginne
damit, die Zustandsgleichungen aufzustellen, beziehungsweise die Funktion
aufzustellen, die diese Zustände bearbeitet und lege entsprechende
Halbwertszeiten an permanente Elemente. Falls du nicht ganz genau weißt,
wie du diese Halbwertszeit anlegen sollst, dann kannst du ja einmal
stichprobenartig herausfinden, zu wie viel Prozent eine Hand eines der
möglichen Gegner ein Removal Spell hat, der auf diese permanente aus der
Stichprobe passt. Und dann kannst du über den Kartenpreis abschätzen, ganz
grob, wie wertvoll die jeweilige Karte ist. Das mag zwar im Einzelfall
anders sein, aber es ist zumal ein Indikator für die Qualität einer Karte,
ihr Preis. Und den findest du ja auch in den Datenbanken. Damit hast du
gegebenenfalls so eine ganz grobe Orientierung, welcher Effekt oder welche
Mana-Kosten oder wie Auch immer du das gewichten möchtest, welchen Einfluss
auf die Halbwertszeit einer Karte auf dem Board haben, die durch die
Funktion eines Gegnerprofils in die Zustandsgleichung des Gegners
eingeführt worden ist."

**Erste Teilantwort:** die Gegner-Zustandsgleichung (`state_equation.py`)
existiert bereits seit v4.38.0 und wurde seither wiederholt kalibriert
(zuletzt v4.69.0) — keine Neuentwicklung von Grund auf, sondern eine
weitere gezielte Kalibrierungsrunde für einen bislang unbelegten Teil
dieses bestehenden Modells: `permanent_type_half_life_turns`, seit v4.40.0
als reine, unbelegte "ERST-SCHÄTZWERTE" dokumentiert (creature 4, artifact
7, enchantment 9, planeswalker 6, land 12).

**Methodik, exakt wie vom Nutzer vorgeschlagen, zweiteilig:**

1. **Hand-Sampling-Stichprobe:** `App/archetype_profile/classify.py` erhielt
   eine neue, additive Funktion `removal_target_types(oracle_text)` (welche
   der 5 Permanenttypen kann eine Karte per destroy/exile/Wipe/Bounce/
   -X/-X/Schaden entfernen — Gegenzauber bewusst ausgeschlossen). Für alle
   1.585 echten EDHREC-Average-Decks wurde der volle, nach `quantity`
   expandierte Kartenpool gebildet und 40 zufällige 7-Karten-Hände pro Deck
   gezogen (63.400 Hände insgesamt) — je Permanenttyp wurde die
   Trefferhäufigkeit gemessen: creature 34.81 %, artifact 19.52 %,
   enchantment 18.10 %, planeswalker 16.93 %, land 2.18 %.
2. **Kartenpreis als Qualitäts-Proxy:** das lokale
   `Training data/export_card_training_data.py`-Skript wurde um Scryfalls
   `prices`-Feld erweitert (kostet keine zusätzlichen Anfragen) und vom
   Nutzer lokal neu ausgeführt (92.9 % der Karten mit `price_usd`). Für
   jede Hand mit Treffer wurde der höchste aufgelöste Preis unter den
   treffenden Karten notiert und log1p-gemittelt — der Preis erwies sich
   dabei überraschend als NUR SCHWACHER Differenzierer zwischen den 4
   Nicht-Land-Typen (relative Gewichte 0.986–1.021), Häufigkeit bleibt der
   dominante Faktor.

Beide Signale wurden zu einem `Häufigkeit × Preis`-"Removal-Druck"
kombiniert und am alten Vier-Typen-Durchschnitt (6.5) verankert — dieselbe
"Anker am alten Durchschnitt, neu verteilt nach neuer Evidenz"-Methodik wie
bei den Farb-/Strategie-Kurven in v4.67.0/v4.69.0. Volle Herleitung,
Rohwerte-Tabellen und die Preisgewichtungs-Formel:
`Docs/opponent_model_calibration_v4_70_0.md`.

**Ergebnis:**

- **Hauptkorrektur:** `artifact` (alt: Halbwertszeit 7) war LÄNGER als
  `planeswalker` (alt: 6) angesetzt — obwohl Artefakte in der Stichprobe
  HÄUFIGER beantwortet werden als Planeswalker. Jetzt korrekt umgekehrt:
  artifact **7.5** < planeswalker **8.4**.
- `enchantment` fällt von 9 auf **8.0** (dritthäufigste Trefferquote, nicht
  mehr per Konvention die längste).
- `creature` bleibt mit **4.2** nahe am alten Wert (mit Abstand häufigste
  Trefferquote — jetzt belegt statt geraten).
- **Land ist ein disclosed Policy-Sonderfall, kein reiner Datenwert:** die
  rohe inverse Häufigkeits-Extrapolation ergibt ~63.8 Züge — mehr als
  dieses Tool überhaupt simulieren kann (`App/gui.py`s Zug-Spinbox geht bis
  30). Ein neuer, genereller Guardrail
  (`guardrails.half_life_ceiling_turns = 30`, angewendet auf ALLE fünf
  Permanenttypen) deckelt Land entsprechend (12 → **30**) — eine bewusste
  Modellierungsentscheidung im selben Sinne wie v4.67.0s grüne
  Wipe-Readiness-Untergrenze, nur in die andere Richtung.
- **Zwei kleine, echte Regex-Lücken** in `removal_target_types` beim
  Testschreiben gefunden und behoben: die `-X/-X`-Erkennung deckte Toxic
  Deluges tatsächlichen Wortlaut ("each creature gets -X/-X") noch nicht
  ab (nur die Ziffern-Variante), und die Landzerstörungs-Erkennung deckte
  nur den Imperativ ("Sacrifice a land"), nicht die 3.-Person-Form
  ("Target player sacrifices a land") ab.

**Disclosed Limitationen:** die Hand-Sampling-Simulation ist eine
statische Eröffnungshand-Momentaufnahme, keine Zug-für-Zug-Simulation über
eine ganze Partie; Kartenpreis ist ein grober, korrelativer statt
kausaler Qualitäts-Proxy und hat sich als schwacher Differenzierer
erwiesen; `removal_target_types` bleibt eine dokumentierte
Regex-Näherung mit bekannter Lücke bei abstimmungsbasierten Effekten
(Council's Judgment, kein "target"-Schlüsselwort).

`Data/Models/opponent_state_weights.json` version → "1.8".

---

## v4.69.0 — Kalibrierungs-Synthese Teil 3: Entkonfundierung Farbe x Strategie

**Auftrag (Nutzer, wörtlich):**
"Ich habe deine erste Frage zu Version 4.67.0 so beantwortet, weil ich gerne
noch einmal expliziter darauf eingehen möchte. Dieses Kalibrierungsmodell
soll quasi auf der einen Seite abbilden, welchen Effekt tatsächlich die
Farben und welchen Effekt die Strategien auf die Zusammenstellung von Decks,
der Ausrichtung ihrer Effekte und die Verteilung von Kartentypen haben. Das
soll in irgendeiner Weise vernünftig abgebildet werden. Sollte bisher diese
Abbildung nicht anhand der Daten verifiziert worden sein können, möchte ich,
dass du einen Weg findest, wie du aus diesen Daten diese Informationen
bekommst. Ich kann mir vorstellen, dass sich vieles angleicht, wenn in
einer Farbe unterschiedliche Strategien vereinheitlicht werden zu einem
sich ausmittelnden Wert, quasi ähm, wenn es Unterschiede gibt in den
Strategien, aber eine Farbe diese Stärken und Schwächen dynamisch
bearbeiten kann, dann wird natürlich bei der Betrachtung der Farbe diese
Dynamik mit abgebildet, diese Breite der Fähigkeiten. Und bei einer
Strategie sieht das ähnlich aus. Sobald ich ähm, in unterschiedlichen
Farben, mit unterschiedlichen Stärken und Schwächen verschiedene Ansätze
habe, wie ich mit ähm, Strategien umgehe, dann wird auch da die Stärken und
die Schwächen der einzelnen Farben sich über die betrachteten Strategien
hinweg ausgleichen. Meine Bitte jetzt an dich ist, dass du genau
herausfindest, welche Gemeinsamkeiten und welche Unterschiede auf der
Farbebene und welche auf der Strategieebene relevant sind, um vernünftige
Aussagen darüber herzustellen, ähm, wie sich Decks einer gewissen Farbe bei
einer gewissen Strategie wahrscheinlich anfühlen müssen. Und da können sich
durchaus Informationen überlagern. Ich möchte es aber nicht, dass das
Ergebnis ist, dass es quasi äh, immer genau den Mittelwert aller Decks
abbildet."

**Ausgangslage:** v4.67.0 hatte `color_modifiers`/`strategy_curves` per
MARGINALER Poolung kalibriert (eine Strategie-Tag-Dichte über alle Farben
gemittelt, eine Farb-Dichte über alle Strategien gemittelt) und dabei zwei
Einebnungs-Befunde (Interaktion, Wipe-Wachstum je Strategie) bewusst
NICHT übernommen, weil sie der bisherigen, gezielten Kalibrierung
widersprachen. Der Nutzer stellte diese Methodik direkt in Frage: marginale
Poolung kann einen echten Effekt auf der einen Achse verdecken, wenn die
Mischung der anderen Achse (Farbmischung innerhalb eines Strategie-Tags,
oder umgekehrt) nicht repräsentativ ist — eine klassische
Konfundierungs-Situation.

**Methodik:** eine echte Zwei-Wege-OLS-Regression (`numpy.linalg.lstsq`,
kein Intercept) auf n=337 Decks (die 4 EDHREC-Tags Aggro/Midrange/Control/
Tokens, gezogen aus ALLEN 32 Farbidentitäten statt nur den 5 Monofarben)
mit 5 Farb-Dummy-Spalten UND 4 Strategie-Tag-Dummy-Spalten gleichzeitig als
Regressoren — isoliert den Farbeffekt bei festgehaltener Strategiemischung
und umgekehrt. Signifikanz: `|Koeffizient| > 2×Standardfehler`. Volle
Herleitung inkl. Koeffizienten-/Signifikanztabellen für jede Farbe/Strategie
und jede der vier Dichte-Dimensionen: `Docs/opponent_model_calibration_v4_69_0.md`.

**Ergebnis — eine gemischte, nicht-degenerierte Antwort, wie vom Nutzer
gefordert:**

- **Hauptbefund (Korrektur):** `color_modifiers.B.interaction_availability`
  fällt von 1.20 (seit v4.39.0, aus der echten Endrek-Sahr-Stichprobe) auf
  **0.85** — ein statistisch SIGNIFIKANTER, der alten Annahme
  entgegengesetzter Befund, kein blosses "nicht signifikant". Im Kontrast
  dazu bleibt `U.interaction_availability` bei 1.45 (Blaus Ergebnis ist nur
  UNSCHLÜSSIG, nicht widersprüchlich — eine bestehende, echte
  Decklisten-Evidenz wird dadurch nicht entwertet).
- **Echte, robuste Strategieeffekte bestätigt und verstärkt:**
  `board_presence_growth` für Aggro/Midrange liegt nach Entkonfundierung
  SIGNIFIKANT über Control (0.826/0.811 vs. 0.604) — ein grösserer, nicht
  kleinerer Abstand als v4.67.0s marginale Schätzung zeigte, weil die
  marginale Poolung den reinen Strategieeffekt teilweise durch die
  Farbmischung verdeckt hatte.
- **Echte, robuste Farbeffekte neu sichtbar gemacht:** mehrere zuvor als
  "nicht belastbar" verworfene Farb-Dimensionen (`W.interaction_availability`,
  `B.board_presence`, `B.mana_growth`, `G.interaction_availability`) werden
  nach Entkonfundierung signifikant und neu aufgenommen.
- **Bestätigt (nicht widerlegt) flach:** die v4.67.0-Einebnung bei
  `interaction_growth`/`wipe_growth`/`mana_growth` auf der Strategie-Achse
  ist nach Entkonfundierung immer noch statistisch nicht signifikant — ein
  echter Nullbefund, keine Methoden-Schwäche. `control`s vormals stark
  überhöhte `interaction_growth`/`wipe_growth`-Werte (0.16/0.11) wurden
  entsprechend deutlich nach unten korrigiert (0.078/0.040), da sie sich
  gegenüber Aggro/Midrange als nicht haltbar erwiesen.
- **Nicht-signifikante, unbelegte Werte auf neutral zurückgesetzt:**
  `W.mana_growth`, `U.mana_growth`, `U.board_presence`, `R.board_presence`
  entfernt — sie stammten ausschliesslich aus v4.67.0s eigener, jetzt in
  Frage gestellter marginaler Methode, ohne unabhängige Vorevidenz.
- `G.wipe_readiness`s v4.67.0-Policy-Untergrenze (0.15, wegen eines rohen
  Null-Medians in nur 50 Mono-Grün-Decks) wird durch einen echten,
  signifikanten, aus allen grün-beteiligten Decks abgeleiteten Wert (0.40)
  abgelöst.

**Verbleibend offen:** `aggro`/`horde.wipe_growth` erhalten zwar neue
Werte > 0, bleiben aber durch `wipe_min_turn=999` verhaltens-inaktiv (kein
Turn-Timing-Beleg vorhanden). `horde.board_presence_growth` bleibt aus
denselben, bereits in v4.67.0 dokumentierten strukturellen Gründen
(Tokens-Tag erfasst keine Nicht-Kreatur-Token-Generierung) unverändert bei
1.30 — eine Zwei-Wege-Regression kann eine fehlende Datendimension nicht
nachträglich sichtbar machen. `combo_finish_readiness`/`sac_drain_growth`/
`passive_value_growth`/`disruption_growth` weiterhin nicht von
`deck_profiles.csv` abgebildet. Volle Details, jede einzelne
Wert-Entscheidung mit Begründung, und die direkte Beantwortung der
Nutzerfrage ("welche Gemeinsamkeiten/Unterschiede sind auf Farb- bzw.
Strategieebene relevant"): `Docs/opponent_model_calibration_v4_69_0.md`.

## v4.68.0 — Kalibrierungs-Synthese Teil 2, Integration: archetype_profile angeschlossen + neuer Vergleichs-Tab

**Auftrag (Nutzer, wörtlich, zweiter Teil derselben Nachricht wie v4.67.0):**
"Darüber hinaus ermöglicht der Datensatz nun, dass individuell hochgeladene
Decks, die getestet werden, verglichen werden können mit anderen Decks. In
der Auswertungsmaske wäre es gut, einen Reiter zu haben, der dies halt
ermöglicht, dass man dort sehen kann, wie das getestete Deck sich mit einem
Deck der gleichen Farbidentität bzw. einem Deck mit der gleichen Strategie
verhält." Laut Nutzer explizit parallel zu v4.67.0 bearbeitbar (unabhängig
von der Gewichte-Kalibrierung, reine Anzeige-Funktion).

**Ausgangslage:** `App/archetype_profile/` (Deck-Klassifikation +
Referenzmodell aus denselben 1.585 EDHREC-Decks) existierte bereits als
fertiges, aber laut eigenem README "Prototyp, noch nicht an
`engine.py`/`gui.py` angeschlossen" - nur auf dem echten Gerät vorhanden,
in dieser Session erstmals in die Cloud-Arbeitskopie synchronisiert (siehe
`App/archetype_profile/README.md`s eigene "Nächste Schritte"-Liste, die
genau diesen Auftrag bereits vorwegnahm).

**Umsetzung** (alle 4 in der README dokumentierten Integrationsschritte
erledigt, siehe dortige aktualisierte Checkliste):

- `App/archetype_profile/`s interne Imports auf relative Imports
  umgestellt (`from . import classify` etc.) - vorher nur als flache
  Standalone-Skripte lauffähig, nicht als echtes Unterpaket.
- `App/engine.py`: `commander_identity_slug()` (reale Farbidentität aus
  dem/den gewählten Commander(n), nicht mehr aus Manapips geschätzt) und
  `compare_deck_to_archetype_reference()` (neuer GUI-facing Einstiegspunkt,
  nimmt `App.engine.Card`-Objekte direkt statt eines Zwischenformats,
  inkl. Live-Klassifikation für Karten außerhalb der 8.445-Karten-Referenz).
  `_STRATEGY_TAG_TO_ARCHETYPE_TAG`: die 14 in-App-Strategie-Tags
  (`engine.STRATEGY_TAGS`) haben alle eine direkte 1:1-Entsprechung zu
  EDHREC-kanonischen Tags (z. B. "voltron"→"Voltron", "lands"→"Lands
  Matter") - reine Vokabular-Brücke, kein neuer Rechercheaufwand.
- `App/gui.py`: neuer Tab "Vergleich (1.585 Decks)" in der Auswertungsmaske
  (`AnalysisPage._build_deck_comparison`) - zeigt das getestete Deck neben
  der Farbidentitäts-Referenz sowie (wenn mindestens ein ausgewählter
  Strategie-Tag in der Referenz erkannt wird) einer zusätzlichen
  Farbidentität+Strategie-Spalte; degradiert sauber (mit Hinweistext) auf
  reinen Farbidentitäts-Vergleich, wenn kein Tag erkannt wird oder kein
  Deck/Commander geladen ist.

**Tests:** 13 neue Tests
(`tests/test_v4680_archetype_profile_integration.py`) - Gruppe 1 prüft den
Paket-Import selbst (inkl. Regressionstest, dass die relativen Imports
tatsächlich in den Dateien stehen), Gruppe 2 die Commander-Farbidentität
(inkl. Partner-Commander-Vereinigung), Gruppe 3 die volle
`compare_deck_to_archetype_reference`-Logik inkl. aller 14
Strategie-Tag-Zuordnungen und beider Graceful-Degradation-Pfade, Gruppe 4
ein echter Lauf gegen die reale `Decks/Bilbo V1.txt`. 772 Tests insgesamt
(zuvor 759), keine Regression.

ENGINE_VERSION/GUI-Titel auf 4.68.0 angehoben.

## v4.67.0 — Kalibrierungs-Synthese Teil 2: statistisch breite Neukalibrierung aus 1.585 echten EDHREC-Decks

**Auftrag (Nutzer, wörtlich):** "Ich habe in einem anderen Teil unseres
Projekts die Gegnerprofile trainiert. Und nun bezüglich Strategie und
Farbidentität auf der Basis von 1585 Commander Decks diese Grundlage
erarbeitet. Ich möchte nun, dass du diese Daten aus dem Ordner nutzt, um die
Gegnerprofile, die Funktionen abzubilden. Auf die Art und Weise, wie wir es
schon häufig diskutiert haben." Genau die "statistisch breite Kalibrierung",
die seit dem v4.39.0-Eintrag als offener, vom Nutzer selbst benannter
Folgeschritt geführt wurde (damals: 10 echte Decklisten, "keine breite
Kalibrierung" - siehe dort) ist mit der in einem separaten Projektteil
bereits fertiggestellten EDHREC-Trainingsdaten-Pipeline (1.585 reale
Average-Deck-Profile, `App/archetype_profile/`, siehe Projektnotiz
`edhrec-bracket3-database.md`) jetzt verfügbar. Das Paket lag bislang nur
auf dem echten Gerät (`A:\MTG_Proxy\Commander_Goldfish\App\archetype_profile`)
und wurde in dieser Session erstmals in die Cloud-Arbeitskopie synchronisiert.

**Vorgehen und ein wichtiger Zwischenbefund:** exakt dieselbe
Dichteverhältnis-Methodik wie v4.39.0 (Rollen-Kartenzahl-Anteil an
Nicht-Land-Slots), jetzt mit n=50 Decks je Monofarbe (statt 2) und n=41-131
Decks je Strategie-Tag (statt 2). Eine erste vollständige Berechnung aller
Dimensionen zeigte jedoch: für `interaction_availability`/
`interaction_growth` differenzieren Aggro/Midrange/Control in der breiten
Stichprobe praktisch NICHT (0.22/0.22/0.22 Interaktionsanteil), und Blau
fiel dabei sogar hinter Weiß zurück - eine naive Übernahme hätte die
bewusst gestaffelte Modell-Differenzierung eingeebnet bzw. umgekehrt. Dieser
Befund wurde dem Nutzer vorgelegt (inkl. eines zweiten Versuchs mit
verfeinertem Signal, der dieselbe Einebnung zeigte); auf seine Entscheidung
hin blieben `interaction_availability`/`interaction_growth` sowie
`strategy_curves.*.wipe_growth` auf der bisherigen, kleineren aber
gezielteren v4.39.0/v4.43.0-Kalibrierung - offen ausgewiesene Lücke statt
stillschweigend "verbessert". Übernommen wurden dagegen
`color_modifiers.{board_presence,wipe_readiness,mana_growth}` (alle 5
Farben) und `strategy_curves.{board_presence_growth,mana_growth}` (aggro/
midrange/control; horde nur bei mana_growth, NICHT bei board_presence_growth
- siehe unten). Mono-Grüns rohe Wipe-Dichte kam exakt bei 0.0 heraus; statt
eines harten 0.0-Multiplikators (der im multiplikativen Farbmodell JEDE
grün-beteiligte Identität auf wipe_readiness=0 zwingen würde) wurde eine
offen ausgewiesene Policy-Untergrenze von 0.15 gesetzt. `horde.
board_presence_growth` blieb ebenfalls bewusst unverändert (1.30): echte
"Tokens"-Decks (EDHREC führt kein eigenes "Horde"-Tag) zeigen keine erhöhte
Creature-TYP-Kartendichte, weil eine Token-Strategie ihre Brett-Präsenz
überwiegend über token-ERZEUGENDE Nicht-Kreatur-Karten aufbaut - eine reine
Decklisten-Kartentyp-Zählung kann das strukturell nicht abbilden.
`combo_finish_readiness`/`sac_drain_growth`/`passive_value_growth`/
`disruption_growth` bleiben unverändert (von `deck_profiles.csv`s Schema
granular nicht abgedeckt). Volle Herleitung, Rohwerte-Tabellen und die
vollständige Diskussion beider offen ausgewiesenen negativen Befunde:
`Docs/opponent_model_calibration_v4_67_0.md`.

**Tests:** 14 neue Tests (`tests/test_v4670_opponent_recalibration.py`) -
Gruppe 1 prüft die konkreten neuen JSON-Werte, Gruppe 2 dass
`state_equation.py` sie tatsächlich über den bestehenden Ladepfad liest,
Gruppe 3 eine echte `advance_opponent_state`-Integration (Aggro baut trotz
kleinerer Differenz weiterhin schneller Board-Präsenz auf als Control; Grün
kann jetzt vereinzelt Wipe-Bereitschaft tragen, bleibt aber weit hinter
Weiß/Rot zurück). 759 Tests insgesamt (zuvor 745), keine Regression.

ENGINE_VERSION/GUI-Titel auf 4.67.0 angehoben.

## v4.66.0 — Kalibrierungs-Synthese Teil 1: Flavor-Strategie-Matrix als abfragbare Engine-Datenstruktur + opt-in Simulations-Override

**Auftrag (Nutzer, wörtlich):** "Die Flavor-Strategie-Matrix bzw. die
Erkenntnisse aus der Recherche müssen zwingend noch vor der Bearbeitung des
Frontends eingepflegt werden. Ohne diese Übertragung ist es ja auch nicht
möglich, die jeweiligen Strategien und Auslegungen der Farbidentitäten
entsprechend abzubilden." Explizite Umkehrung der zuvor besprochenen
Session-Reihenfolge ("neue Session fürs Frontend") - die
Kalibrierungs-Synthese der 90 in v4.47.0-v4.62.0 erarbeiteten
Flavor-Strategie-Zellen (5 Monofarben + 10 Gilden x je 6 Flavors) wird als
nächster Schritt noch in dieser Session bearbeitet.

**Vorgehen (evidenzbasiert, additiv, disclosed-limitation statt
Vollersatz):** alle 15 `Docs/flavor_strategy_matrix_*.md`-Dokumente
(v4.47.0-v4.62.0) wurden vollständig erneut gelesen. Jedes dieser Dokumente
markiert seine eigenen Zahlen ausdrücklich und wiederholt als "Kandidaten,
keine Gewichtsänderung" - jede Zelle beruht auf GENAU EINER echten
EDHREC-Bracket-3-Decklist, nicht auf der "mehrere Decks pro Zelle"-Breite,
mit der `Data/Models/opponent_state_weights.json`s eigentliche
Default-Gewichte (color_modifiers/strategy_curves) in v4.39.0-v4.43.0
kalibriert wurden (10, dann +10, dann +10 echte Decklisten). Eine stille
Übernahme dieser N=1-Stichproben in die projektweiten Default-Gewichte wäre
daher genau die Art spekulativer, nicht breit belegter Änderung, die dieses
Projekt ablehnt ("evidence-based iteration", "no speculation-driven
fixes") - `opponent_state_weights.json` bleibt in dieser Version daher
numerisch **unverändert**.

Stattdessen: die 90 Zellen wurden verlustfrei, ohne neue Recherche, in eine
neue Datei `Data/Models/flavor_strategy_matrix.json` übertragen (90 aktive
Zellen + 1 Legacy-Zelle "Ramp/Big-Mana" aus dem ursprünglichen
Grün-Piloten v4.47.0, die nicht mehr Teil der aktiven 6-Flavor-Taxonomie
ist, aber weiterhin gültig bleibt; außerdem die 17 im Projekt bestätigten
vollständigen Combo-Funde und die 2 projektweit am häufigsten
dokumentierten Modellgrenzen als eigene, strukturierte Einträge). Diese
Datei ist damit erstmals maschinenlesbar und für ein künftiges Frontend
direkt abfragbar (genau der vom Nutzer benannte Zweck: "die jeweiligen
Strategien und Auslegungen der Farbidentitäten entsprechend abbilden").

`App/opponent_model/state_equation.py` bekommt einen neuen, streng
**opt-in** Mechanismus: `OpponentProfile.flavor` (neues Feld, Default
`None`). Ohne gesetztes `flavor` ist das Verhalten jedes bestehenden
Aufrufers byte-identisch zu vorher (durch Regressionstests abgesichert,
u. a. Seed-Reproduzierbarkeit vor/nach dieser Änderung). Wird `flavor`
gesetzt (Format `"<Farbidentität>/<Flavor-Slug>"` oder nur `"<Flavor-
Slug>"`, wenn eindeutig), verwendet `advance_opponent_state` für GENAU
DIESEN einen simulierten Gegner die 10 Zellenwerte direkt anstelle von
`curve[dimension] * color_modifier(dimension)` - die Zellenwerte SIND
bereits der in den Quelldokumenten vorgeschlagene Ersatzwert für die
kombinierte Kurve, keine zusätzliche Multiplikationsebene. Ein Sonderfall
wurde dabei bewusst separat behandelt: `dead_turn_chance_base` hätte bei
naiver Wiederverwendung des generischen Overrides den Farbmodifikator
(z. B. R: 0.90) doppelt angewendet - eigens per Test abgesichert
(`test_dead_turn_chance_base_does_not_double_apply_the_color_modifier_
when_flavor_active`). Unbekannte/nicht passende Flavor-Schlüssel fallen
sicher auf das bisherige Verhalten zurück statt abzustürzen.
`App/engine.py`s bestehende Mehrgegner-Integration
(`advanced_opponent_seats`, seit v4.63.0) bekommt denselben opt-in Schlüssel
`"flavor"` pro Sitzplatz - `_validate_advanced_opponent_seats` prüft ihn
(unbekannter oder zur Sitzplatz-Farbe nicht passender Flavor wird laut
zurückgewiesen, dieselbe "harter Fehler statt stiller Fallback"-Praxis wie
alle bisherigen Prüfungen dieser Funktion), `_build_advanced_opponent_table`
reicht ihn durch. Bracket-Skalierung und die harten Wipe-/Combo-Gates
bleiben unverändert und unabhängig von einem aktiven Flavor.

**Bewusst offen gelassen (disclosed, nicht verschwiegen):** die beiden
projektweit am häufigsten dokumentierten Modellgrenzen aus der
Flavor-Recherche - "thematischer Kern überschneidet sich mit
Basisdimension" (>10 Einzelzellen) und das Voltron-Board-Präsenz-Muster (6
von 10 Gilden) - werden in `flavor_strategy_matrix.json` als strukturierte
Einträge (`documented_model_limitations`) festgehalten, aber NICHT behoben.
Beide erfordern eine neue Engine-Dimension bzw. eine strukturelle
Erweiterung von `state_equation.py`, keine reine Datenübertragung, und
bleiben ein eigener, späterer Schritt. Ebenfalls nicht Teil dieser Version:
eine GUI-Oberfläche zur Flavor-Auswahl pro Sitzplatz (der Mechanismus ist
aktuell nur über `advanced_opponent_seats[i]["flavor"]` direkt erreichbar,
nicht über einen GUI-Dialog) - explizit als Frontend-Thema zurückgestellt,
konsistent mit der eigenen Session-Priorität des Nutzers.

**Dateien:** `Data/Models/flavor_strategy_matrix.json` (neu),
`App/opponent_model/state_equation.py` (Moduldoc-Abschnitt "v4.66.0",
`OpponentProfile.flavor`, `_flavor_cell`, `_growth_rate`,
`_canonical_color_key`, `reload_flavor_matrix`), `App/engine.py`
(`_validate_advanced_opponent_seats`/`_build_advanced_opponent_table`
opt-in "flavor"-Wrap), `tests/test_v4660_flavor_strategy_matrix.py` (neu,
30 Tests: Datenintegrität der JSON-Datei, `_flavor_cell`-Lookup,
Regressionsschutz ohne Flavor, Override-Verhalten mit Flavor inkl.
dead-turn-Sonderfall, Engine-Sitzplatz-Verdrahtung, Ende-zu-Ende-Lauf).

**Tests:** 745 Tests, 1 übersprungen (vorher 715 + 30 neue = 745, alle
bestehenden Tests unverändert grün - keine Regression).

## v4.65.3 — Bilbo-Drain-Payoff-Coverage: Selbstbericht korrigiert (Sanguine Bond/Vito bereits real simuliert), generischer Parser-Fix für "loses that much life"

**Auftrag (Nutzer, wörtlich):** "Ja, an die Bilbo-Drain-Payoff-Coverage auch
ranmachen" - Folgeauftrag zum in v4.65.1 offengelegten, zunächst nicht
angefassten Kontextpunkt: "Bilbos Drain-Payoff-Karten (Vito, Sanguine Bond,
Corpse Knight, Dina, Marauding Blight-Priest) sind nur 'generic'-abgedeckt
... selbst ein Szenario-Match würde nicht verifizieren, dass der Drain-
Schaden tatsächlich simuliert wird."

**Befund nach genauer Prüfung (`card_model_coverage.csv` + die tatsächliche
Engine-Logik in `App/engine.py:gain_life`):** die frühere Einschätzung war
zu pessimistisch. "generic" bedeutet in diesem Tool NICHT "unsimuliert" -
es heißt nur "kein `KNOWN_COVERAGE_NOTES`-Eintrag, nutzt den generischen
Parser". Im Detail:

- **Corpse Knight, Marauding Blight-Priest, Dinas Kern-Trigger:** waren
  bereits korrekt als "1/1"/"1/2 exact" ausgewiesen - real vollständig
  simuliert, keine Lücke, keine Änderung nötig.
- **Sanguine Bond UND Vitos Drain-Zeile** ("Whenever you gain life, target
  opponent loses that much life."): werden in `gain_life()`
  (`App/engine.py`, Abschnitt "High-impact Bilbo card fixes") bereits real
  und exakt ausgeführt (`lose_target_opponent` mit dem tatsächlich
  gewonnenen Betrag, inklusive Lebensgewinn aus Kampf-Lifelink, da
  Kampf-Lifelink ebenfalls über `gain_life()` läuft). Der
  **Coverage-Selbstbericht** zeigte hier aber fälschlich 0/1 bzw. 1/2
  "executable", weil die generische "opponent loses N life"-Regex
  (`_parse_semantic_actions`) nur feste Zahlen/Zahlwörter erkennt, nicht
  die dynamische Formulierung "loses THAT MUCH life" (Betrag = gerade
  gewonnenes Leben). Das ist ein **Selbstbericht-Genauigkeitsfehler**
  ("syntax-korrekt, aber inhaltlich falsch" im Sinne des ursprünglichen
  Nutzerauftrags), keine fehlende Spielmechanik.
- **Dinas zweite Fähigkeit** (`{1}, Opfere eine weitere Kreatur: Dina
  erhält +X/+0`) ist die einzige ECHTE, verbleibende Lücke - eine bedingte
  Kampftrick-Opfer-Entscheidung außerhalb des Drain-Payoff-Kerns dieser
  Karte, weiterhin offen und ehrlich als solche benannt.

**Fix (additiv, zweigleisig, `App/engine.py`, Block direkt vor
`main_v470`):**
1. Neuer `_parse_semantic_actions`-Wrapper erkennt zusätzlich "each
   opponent loses that much life"/"target opponent loses that much life"
   als exakte `opponent_life_loss`-Aktion (`amount=0.0` als bewusst
   inerter Platzhalter für "dynamisch, keine feste Zahl") - macht den
   Coverage-Selbstbericht für JEDE Karte mit dieser generischen, häufigen
   Formulierung korrekt, nicht nur für die beiden hier untersuchten.
   `amount=0.0` ist sicher: die einzige Stelle, die
   `opponent_life_loss`-Aktionen numerisch aufsummiert
   (`_loyalty_ability_value`, ausschließlich für Planeswalker-
   Loyalitätsfähigkeiten) überspringt bereits explizit falsy/0-Beträge -
   keine verzerrte Bewertung möglich. Nichts in dieser Engine führt
   generisch eine GETRIGGERTE Fähigkeit aus dieser Aktionsliste aus
   (`try_generic_semantic_activations` behandelt ausschließlich
   "activated"-Fähigkeiten) - die tatsächliche Ausführung bleibt exakt so
   wie vorher in `gain_life()`; diese Ergänzung macht nur den
   Selbstbericht ehrlich.
2. `KNOWN_COVERAGE_NOTES`-Einträge für alle fünf Karten (direkt im
   bestehenden Dict ergänzt - Präzedenzfall: die `config={...}`-
   Dict-Bearbeitung in `run_pipeline_v440`, v4.64.0) korrigieren die
   Coverage-Stufe/Notiz von "generic" auf "strong" (Sanguine Bond, Vito,
   Corpse Knight, Marauding Blight-Priest) bzw. "partial+" (Dina, mit der
   echten Sac-Pump-Lücke weiterhin ehrlich benannt).

**Verifikation:**
- Direkter Parser-Test: `Sanguine Bond` 0/1 → 1/1, `Vito, Thorn of the
  Dusk Rose` 1/2 → 2/2, jeweils `execution_mode="exact"`.
- End-to-End-Smoke-Test mit dem echten Bilbo-V1-Deck durch die komplette
  Pipeline (`run_pipeline_v440`, 20 Runs): das ausgelieferte
  `card_model_coverage.csv` zeigt die korrigierten Werte tatsächlich in der
  Datei, nicht nur isoliert getestet.
- Laufzeit-Regressionstest bestätigt: `gain_life()`s tatsächliches
  Drain-Verhalten für Sanguine Bond/Vito (inkl. Lifelink-Lebensgewinn) ist
  unverändert korrekt - dieser Fix ändert nur den Selbstbericht, nicht die
  Simulation selbst.
- Sicherheitstest: der neue `amount=0.0`-Platzhalter beeinflusst
  `_loyalty_ability_value` (die einzige numerische Verwendung) nachweislich
  nicht (Ergebnis 0.0, kein negativer/verzerrter Score).

**Tests:** `tests/test_v4653_drain_payoff_coverage.py` (16 neue Tests):
`ParseSemanticActionsDynamicDrainTests` (5), `CardModelCoverageDrainPayoffTests`
(5, mit dem echten Oracle-Text aller fünf Karten), `KnownCoverageNotesTests`
(3), `LoyaltyAbilityValueDynamicAmountSafetyTests` (1),
`GainLifeRuntimeRegressionTests` (2). Vollständige Regressionssuite vor und
nach der Änderung ausgeführt, Anzahl wie erwartet gestiegen (699 → 715),
Ergebnis weiterhin "OK". `App/gui.py`-Titel auf v4.65.3 synchronisiert (keine
inhaltliche GUI-Änderung nötig - `card_model_coverage.csv` wird in keinem
GUI-Tab angezeigt, nur im Ergebnis-ZIP ausgeliefert); per `py_compile`
geprüft.

## v4.65.2 — Aziza-Match-vs-Sieg-Lücke: generischer Ziel-Scope pro Win-Condition-Szenario + Match/tatsächlicher-Sieg-Kreuzvergleich

**Auftrag (Nutzer, wörtlich):** "Ja, an die Aziza-Siegdefinitionslücke auch
ranmachen" - Folgeauftrag zum im v4.65.1-Bericht offengelegten, aber
zunächst nicht angefassten Kontextpunkt: Azizas beide Win-Condition-
Szenarien matchten in den hochgeladenen Runs zu 99%, die Partie wurde aber
0% tatsächlich gewonnen.

**Befund (keine Engine-Logik-Bug, sondern eine reale Definitionslücke):**
Azizas Win-Condition-Szenarien (`Data/Scenarios/aziza_alpha_strike_v1.json`)
nutzen das `x_spell_lethal`-Prädikat mit `target="any"` -
`App/scenario_predicates/handlers.py` prüft dabei nur, ob EIN Gegner (der
mit dem geringsten Leben, `min(lives)`) lethal getroffen werden könnte.
`check_win()` in `App/engine.py` markiert eine Partie aber erst dann als
gewonnen, wenn ALLE Einträge von `state.opponents` <= 0 sind - der reale
Mehrspieler-Sieg (alle Gegner eliminiert), nicht "ein Gegner erledigt".
Das ist generisch für JEDES Deck relevant, nicht Aziza-spezifisch: alle
drei target-bewussten Prädikat-Typen (`opponent_life_at_or_below`,
`x_spell_lethal`, `commander_damage_lethal`) defaulten laut
`scenario_predicates/definitions.json` ohnehin auf `target="any"`, sobald
"target" im Szenario gar nicht gesetzt ist.

**Fix (additiv, generisch, KEINE Änderung an `check_win()`/den
Praedikat-Ergebnissen selbst - nur zusätzliche Transparenz):**
- `_wc_scenario_target_scope(sc)` (neu, `App/engine.py`, Block direkt vor
  `main_v470`): leitet aus den `derived`-Prädikaten eines Win-Condition-
  Szenarios automatisch ab, ob ein Match nur EIN Ziel betrifft
  (`"any"`/fester Index), ALLE Gegner (`"each"`), gemischt (`"mixed"`),
  oder gar nicht anwendbar ist (`"n/a"`, z. B. reine Leben-/Ressourcen-
  Schwelle ohne Gegnerbezug) - rein aus der Szenario-Konfiguration
  abgeleitet, keine Kartennamen hartcodiert.
- Neuer `StreamingStatsV440.add`-Wrapper: erfasst pro Run zusätzlich, ob
  ein WC-Match (irgendein aktiviertes WC-Szenario in diesem Run erreicht)
  mit einem ECHTEN vollständigen Sieg (`rr["win_turn"]` gesetzt) zusammenfällt.
- Neuer `streaming_summary_v440`-Wrapper: schreibt
  `outcomes["win_condition_reach_and_full_win_pct"]` (Match UND echter
  Sieg), `outcomes["win_condition_reach_but_no_full_win_pct"]` (Match ohne
  echten Sieg - die eigentliche Lücke als Zahl) sowie
  `outcomes["win_condition_single_target_names"]`, und trägt
  `scenarios[].target_scope` pro Szenario ein.
- Neuer `build_analysis_overview`-Wrapper: fügt bei mindestens einer
  konfigurierten Einzelziel-WC mit Reach > 0% eine eigene Beobachtung mit
  beiden Prozentzahlen hinzu (Match % · davon mit tatsächlichem Sieg %).
- Das bestehende `win_condition_reach_pct` (Match, unabhängig vom Scope)
  bleibt unverändert bestehen - rückwärtskompatibel für evtl. externe
  Auswertungen; keine bestehende Kennzahl wurde umdefiniert.

**Neu in `App/gui.py`:**
- Übersicht: die "Win Condition"-Box zeigt bei mindestens einer
  Einzelziel-WC zusätzlich "davon Partie gewonnen: Y %".
- "Win Conditions"-Tab: neue Spalte "Ziel-Scope" ("alle Gegner"/
  "Einzelziel"/"gemischt"/"–") in der Szenario-Tabelle; der erklärende
  Hinweistext unter der Tabelle wurde um den Ziel-Scope-Zusammenhang
  ergänzt.

**Verifikation (End-to-End-Smoke-Test mit dem echten Aziza-V2-Deck +
der echten Szenario-Datei, 60 Runs, goldfish-Profil, Offline-Cache):**
`win_condition_reach_pct` 100.00% (Match), `win_condition_reach_and_full_
win_pct` nur 1.67% (tatsächlicher Sieg) - die Lücke ist jetzt direkt als
Zahl sichtbar statt nur interpretativ im Fließtext eines früheren
Berichts. Beide konfigurierten Aziza-Szenarien werden korrekt als
`target_scope="any"` erkannt; die neue Beobachtung erscheint mit den
korrekten Prozentwerten.

**Tests:** `tests/test_v4652_aziza_win_gap.py` (19 neue Tests):
`WcScenarioTargetScopeTests` (7, inkl. eines Tests mit der exakten
Aziza-Szenario-Form), `StreamingStatsAddFullWinCrosstabTests` (4),
`StreamingSummaryFullWinCrosstabTests` (3, isolierte Wrapper-Tests nach
demselben Muster wie v4.65.1s `RezipAfterFinalWrapperTests`),
`BuildAnalysisOverviewTargetScopeObservationTests` (4). Vollständige
Regressionssuite vor und nach der Änderung ausgeführt, Anzahl wie erwartet
gestiegen (680 → 699), Ergebnis weiterhin "OK". `App/gui.py` zusätzlich
mit `py_compile` geprüft (Tkinter-Laufzeittests weiterhin nicht möglich in
dieser Cloud-Umgebung - unveränderte, offengelegte Einschränkung).

### Nicht verändert (weiterhin offen, kein Fix angefordert)

- Bilbos Drain-Payoff-Karten (Vito, Sanguine Bond, Corpse Knight, Dina,
  Marauding Blight-Priest) sind laut `card_model_coverage.csv` weiterhin
  nur "generic"-abgedeckt - eine bestehende, bereits offengelegte
  Limitation, kein neuer Bug, aus dieser Version unverändert.

## v4.65.1 — Zwei Bugfixes aus kritischer Durchsicht echter Runs: irreführende "goldfish"-Beschriftung bei aktivem Gegnerprofil + fehlender ZIP-Inhalt seit v4.44.0

**Auftrag (Nutzer, wörtlich):** "ich habe dir hier zwei runs hochgeladen. Was
kannst du hieraus ableiten? Funktioniert unser Programm oder gibt es noch
default werte? Ungereimtheiten bzw. syntax-korrekte aber inhaltlich falsche
Ergebnisse? Reflektiere unseren Status kritisch und versuche zu debuggen."
(zwei echte GUI-Runs beigefügt: `Bilbo V1_v4_7_0_20260914-220219.zip`,
`Aziza V2_v4_7_0_20260914-220059.zip`, beide mit aktivem v4.64.0-
"Gegnerprofil"-Dialog gefahren). Nach kritischer Analyse wurden dem Nutzer
zwei bestätigte Befunde per `AskUserQuestion` vorgelegt; beide wurden zum
Fixen freigegeben: "Ja, jetzt fixen" (ZIP-Bug) und "Anzeige/Export
korrigieren" (Gegnerprofil-Beschriftung).

Beide Bugs sind NICHT in dieser Session eingeführt worden, sondern
vorbestehend (ZIP-Bug seit v4.44.0, Beschriftungs-Bug seit v4.64.0) und
wurden ausschließlich durch die vom Nutzer angeforderte kritische Durchsicht
echter Ergebnisse gefunden - kein proaktives Audit.

### Bug 1: irreführende "goldfish"-Beschriftung bei aktivem Gegnerprofil (advanced_opponent_model)

**Befund:** `simulation_config.json`, das GUI-Label "Gewählter Modus" und der
Übersichts-Kasten "Opponent: X" zeigten immer nur den einfachen Dropdown-
Wert von `strategy.opponent_profile` (z. B. `"goldfish"`) - auch dann, wenn
über den v4.64.0-"Gegnerprofil"-Dialog (`strategy.advanced_opponent_model` /
`strategy.advanced_opponent_seats`) in Wahrheit reale, schadenverursachende
Mehrgegner-Sitzplätze simuliert wurden
(`_apply_advanced_multi_opponent_phase`, zieht direkt von `state.life` ab -
komplett unabhängig vom abstrakten `GameState.opponents`-3er-Ziel, das
`check_win`/die eigene Offensive nutzen).

**Beweis (aus den zwei hochgeladenen Runs):** `OPPONENT_PROFILES["goldfish"]`
ist per Definition `damage_scale=0.0` (kein Schaden möglich) - trotzdem
zeigten beide `turns.csv`-Eventlogs wiederholt Einträge wie "ADVANCED
aggro/BW: took X combat/pressure damage". Zusätzlich zeigte das neu
angezeigte `combat_and_removal_diagnostics` (aus v4.65.0), dass Bilbos/
Azizas Commander über 200 Runs 288-mal bzw. 408-mal vom Gegner entfernt
wurde - beides unter einem nominell als "goldfish" beschrifteten Lauf
strukturell unmöglich, wenn tatsächlich ein passiver Goldfish-Gegner
gelaufen wäre.

**Fix (additiv, `App/engine.py`, neuer Wrapper-Block direkt vor `main_v470`,
nach dem v4.65.0-Block):**
- `_advanced_opponent_actual_seat_summary(seats, seed, runs)` - rekonstruiert
  für jeden konfigurierten Sitzplatz, wie oft welche (Strategie, Farben)-
  Kombination über die Läufe hinweg tatsächlich aufgelöst wurde (inkl. "?"-
  Zufallsmarker), unter Verwendung DESSELBEN Resolvers, der auch zur
  Simulationszeit läuft (`_resolve_advanced_opponent_seats_for_run`) - keine
  eigene, potenziell abweichende Logik.
- Neuer `streaming_summary_v440`-Wrapper: schreibt
  `simulation["advanced_opponent_model"/"advanced_opponent_seat_specs"/
  "advanced_opponent_actual_seat_summary"/"advanced_opponent_label"]`.
- Neuer `build_analysis_overview`-Wrapper: schreibt
  `overview["advanced_opponent_summary"]` (active/label/seat_specs/
  actual_seat_summary) und stellt bei aktivem Gegnerprofil eine Warnung als
  ERSTE Beobachtung voran (genau die Stelle, die in den zwei hochgeladenen
  Runs übersehen wurde).
- `App/gui.py`: "Gewählter Modus"-Label (Opponent-Tab) und der "Opponent: X"-
  Detailtext im "Runs"-Kasten der Übersicht zeigen bei aktivem Gegnerprofil
  jetzt zusätzlich `advanced_opponent_summary["label"]` sowie (im Opponent-
  Tab) die tatsächlich simulierten Sitzplätze pro Sitz; bei inaktivem
  Gegnerprofil bleibt die Anzeige unverändert (nur der einfache
  `opponent_profile`-Wert).
- Bei inaktivem `advanced_opponent_model` bleiben alle neuen Felder/die
  Warnung vollständig weg - keine Verhaltensänderung für klassische
  Goldfish-/Random-Läufe ohne Gegnerprofil-Dialog.

### Bug 2: `opponent_model_cross_check.json` fehlt seit v4.44.0 in jedem ausgelieferten ZIP

**Befund:** der `result_dir` wird von mehreren, nacheinander gewrappten
Pipeline-Wrappern befüllt, wobei jeder frühere Wrapper das ZIP bereits einmal
baut/überschreibt. Zwei ältere Wrapper (v4.6x/v4.7x-Herkunft) mussten dieses
exakte Bug-Muster bereits für IHRE EIGENEN neuen Dateien beheben (siehe deren
eigene Kommentare "Base wrapper zipped before these new files were created.
Rebuild the ZIP...") - der v4.44.0-Wrapper (schreibt
`opponent_model_cross_check.json` sowie einen zugehörigen Abschnitt in
`AI_ANALYSIS_INSTRUCTIONS.md`) bekam aber nie ein eigenes Re-Zip und läuft
VOR diesen beiden bereits reparierten Wrappern - seine Dateien fehlten daher
in JEDEM ausgelieferten ZIP seit ihrer Einführung.

**Beweis:** in beiden hochgeladenen ZIPs endet `AI_ANALYSIS_INSTRUCTIONS.md`
nachweislich VOR dem Abschnitt "v4.44.0 Opponent-Model-Cross-Check"; die
Datei `opponent_model_cross_check.json` fehlt in beiden ZIPs vollständig,
obwohl sie laut Code auf Disk in `result_dir` geschrieben wird.

**Fix (additiv, `App/engine.py`, gleicher Wrapper-Block):** neuer
`run_pipeline_v440`-Wrapper, der - nach demselben bereits zweimal bewährten
Muster - das ZIP ein letztes Mal, am Ende der GESAMTEN Wrapper-Kette, aus dem
kompletten `result_dir` neu baut. Best-effort (`try/except`, wie beim
v4.44.0-Wrapper selbst) - ein Problem beim Re-Zip darf niemals die primäre
Ergebnis-Auslieferung verhindern.

### Tests

`tests/test_v4651_bugfixes.py` (10 neue Tests):
- `AdvancedOpponentActualSeatSummaryTests` (5): leere Sitzplatzliste, feste
  Sitzplätze lösen sich jeden Run identisch auf, "?"-Zufallsmarker streut
  über mehrere Läufe, exakter Abgleich gegen den echten
  `_resolve_advanced_opponent_seats_for_run`-Resolver Run für Run, mehrere
  Sitzplätze werden unabhängig getrackt.
- `BuildAnalysisOverviewAdvancedOpponentTests` (3): inaktives Gegnerprofil
  erzeugt keine Warnung, aktives Gegnerprofil erzeugt `advanced_opponent_
  summary` UND die Warnung als erste Beobachtung, bestehende Engine-
  Integritäts-Beobachtung bleibt neben der neuen Warnung erhalten.
- `RezipAfterFinalWrapperTests` (2): Re-Zip nimmt eine nach dem Basis-ZIP
  geschriebene Datei tatsächlich mit auf; ein fehlendes/ungültiges
  `result_dir` lässt den Wrapper nicht abstürzen (best-effort).

Vollständige Regressionssuite vor und nach der Änderung ausgeführt (siehe
`tests/`), Anzahl wie erwartet gestiegen (670 → 680), Ergebnis weiterhin
"OK". `App/gui.py` wurde zusätzlich mit `python -m py_compile` geprüft
(Tkinter-Laufzeittests sind in dieser Cloud-Umgebung wie bei jeder GUI-
Änderung zuvor nicht möglich - offengelegte Einschränkung, unverändert seit
früheren Versionen).

### Nicht verändert (bewusst offengelegte Kontextpunkte aus der Durchsicht, kein Fix angefordert)

- Azizas 99 % "Win Condition"-Match bei 0 % tatsächlichem "Win": liegt daran,
  dass `check_win` ALLE 3 abstrakten Gegner bei ≤0 Leben verlangt, während
  das Alpha-Strike-Szenario (`x_spell_lethal`, `target="any"`) nur EINEN von
  3 auf 0 bringen muss - eine reale Mehrspieler-Semantiklücke in der vom
  Single-Opponent-Modell geerbten Siegdefinition. Dem Nutzer im kritischen
  Bericht offengelegt, aber (noch) nicht als Änderungsauftrag erteilt.
- Bilbos Drain-Payoff-Karten (Vito, Sanguine Bond, Corpse Knight, Dina,
  Marauding Blight-Priest) sind laut `card_model_coverage.csv` nur
  "generic"-abgedeckt (kein dediziertes Resolver-Modell) - eine bestehende,
  bereits offengelegte Limitation, kein neuer Bug.

## v4.65.0 — Auswertung: flexible Win-Condition-Anzeige statt fester "111 Leben"-Schwelle + Handzusammensetzung im Zeitverlauf + eigenständige Durchsicht der Auswertung

**Auftrag (Nutzer, wörtlich sinngemäß):** bevor der v4.64.0-"Gegnerprofil"-
Dialog getestet wird, sollte die Auswertung überarbeitet werden. Zwei Teile:
(A) die Auswertung zeigt noch hart codiert einen "111 Leben"-Tracker; das
soll flexibel werden - was auch immer auf der Win-Condition/Setup-Oberfläche
als Zielbedingung eingestellt wird (Leben, Graveyard-Karten, sonstige Win
Conditions), soll entsprechend in der Auswertung abgebildet/geplottet
werden. (B) eigenständige Durchsicht der GESAMTEN Auswertung: liefern die
gezeigten Darstellungen wirklich nützliche Performance-Informationen, gibt
es sinnvolle zusätzliche Darstellungen, und ist alles Gezeigte tatsächlich
notwendig? Als illustratives (nicht verpflichtendes) Beispiel wurde eine
Handzusammensetzung-über-die-Zeit-Darstellung genannt (gestapeltes
Balkendiagramm: x = Turn, y = Kartenanzahl, gestapelt/farblich nach
Kategorie wie Länder/Interaction/Ramp/Kreaturen/Sorceries).

### Teil A: Flexible Win-Condition-Anzeige

**Befund vor dieser Version:** die Analyse-Oberfläche
(`App/gui.py:AnalysisPage`) zeigte in der Übersicht und im Opponent-
Breakdown eine feste "111 Life %"-Kennzahl
(`GameState.milestones`/`check_life_milestones`/`reach_111_life_pct`/
`reach_111_pct` in `App/engine.py`) - UNABHÄNGIG davon, was der Nutzer
tatsächlich auf der Scenario-Oberfläche (`ScenarioPage`) als Win Condition
konfiguriert hatte. Das Scenario-System selbst
(`new_scenario`/`normalize_scenario`/`scenario_status`) unterstützte
bereits beliebige Schwellen (Leben, Länder, Food, Treasure, Clues) UND
beliebige Kartenanforderungen/derived-Prädikate für Szenarien vom Kind
`"Win Condition"` - diese Flexibilität war nur in der separaten
"Win Conditions"-Tabelle (Match %/Median Turn) sichtbar, nicht aber in der
Übersicht/im Opponent-Breakdown.

**Änderung:** die Übersicht/der Opponent-Breakdown zeigen jetzt eine
GENERISCHE Kennzahl, aggregiert über alle aktivierten Szenarien vom Kind
`"Win Condition"` (`sc.get("kind") == "Win Condition"` - dasselbe
Filterkriterium, das an anderer Stelle im Code bereits verwendet wird, z. B.
für `wc_preservation_bias`). Ist keine Win Condition konfiguriert, wird das
EHRLICH so angezeigt ("keine Win Condition konfiguriert") statt
stillschweigend auf 111 zurückzufallen - passend zum Projektgrundsatz,
keine Zahlen zu erfinden/zu verschleiern.

**Neu in `App/engine.py`** (additiver Wrapper-Block direkt vor `main_v470`):
- `_wc_kind_scenarios(scenarios)` - Filterhilfsfunktion.
- Neuer `StreamingStatsV440.add`-Wrapper: trackt pro Run, ob IRGENDEIN
  konfiguriertes Win-Condition-Szenario erreicht wurde (und auf welchem
  frühesten Turn, bei mehreren Szenarien der früheste), global UND je
  Opponent-Profil (`group["wc_reached"]`).
- Neuer `streaming_summary_v440`-Wrapper: schreibt
  `outcomes["win_condition_configured"/"win_condition_names"/
  "win_condition_reach_pct"/"win_condition_median_turn"]` sowie je
  Opponent-Profil `opponent_breakdown[...]["win_condition_reach_pct"]`.
- Neuer `build_analysis_overview`-Wrapper: ersetzt die alte "111-Life-
  Schwelle"-Beobachtungszeile durch eine Win-Condition-Beobachtung (oder den
  ehrlichen "nicht konfiguriert"-Hinweis).
- Das alte milestones-System (`life_50_turn` … `life_111_turn`,
  `reach_111_life_pct`, `reach_111_pct`) bleibt UNVERÄNDERT im Hintergrund
  bestehen (rückwärtskompatibel für evtl. externe Auswertungen/Tests) - es
  wird nur nicht mehr als GUI-Hauptkennzahl angezeigt. Bilbo, Birthday
  Celebrant's eigene echte Karten-Fähigkeit (`state.life >= 111` für die
  Command-Zone-Aktivierung) ist davon KOMPLETT unberührt - das ist eine
  andere, kartenspezifische Spielmechanik, keine Analyse-Anzeige.

**Neu in `App/gui.py`:**
- Übersicht: neue Metrik-Box "Win Condition" (Reach %, Szenarioname(n),
  Median Turn) ersetzt die alte "111 Life: X %"-Unterzeile bei "Ø
  Endleben".
- Opponent-Tabelle: Spalte "111 Life %" → "Win Condition %"
  (`row["win_condition_reach_pct"]`).
- "Win Conditions"-Tab: neues Liniendiagramm "Win Condition erreicht ·
  kumulativ nach Turn" über alle Szenarien vom Kind "Win Condition"
  (Daten kamen bereits vorher aus `cumulative_reach_by_turn_pct`, wurden
  aber nie geplottet, nur als Einzelwert in der Tabelle gezeigt) - das ist
  die direkte Umsetzung von "flexibel … geplottet" aus dem Nutzerauftrag.

### Teil B: eigenständige Durchsicht der Auswertung

**Durchsicht-Ergebnis** (alle fünf Tabs der `AnalysisPage` geprüft:
Übersicht/Rundenverlauf/Win Conditions/Strategy/Opponent): die meisten
Darstellungen sind zweckmäßig und bleiben unverändert. Zwei konkrete
Lücken gefunden und behoben:

1. **Handzusammensetzung über die Zeit fehlte komplett** - obwohl
   `avg_hand_size` pro Turn bereits getrackt wurde, gab es keine
   Aufschlüsselung NACH KATEGORIE. Umgesetzt wie vom Nutzer vorgeschlagen
   (als Beispiel genannt, hier tatsächlich gebaut, da es genau zum
   Deck-Konsistenz-Zweck dieses Tools passt): neues gestapeltes
   Balkendiagramm im "Rundenverlauf"-Tab. Kategorien nutzen die bereits
   bestehende, deckweit kalibrierte `role_set()`-Klassifikation
   (`ROLE_REACTIVE` etc.) statt einer neu erfundenen Heuristik - eine
   Kreatur mit Ramp-Rolle ("Mana-Dork") zählt als Ramp, nicht als Kreatur,
   analog zur sonstigen Rollen-Verwendung im Code. Sieben sich gegenseitig
   ausschließende, erschöpfende Kategorien: Länder, Ramp, Interaction,
   Card Advantage (Draw/Tutor/Engine), Kreaturen, sonstige Spells,
   Sonstiges (Artefakte/Verzauberungen/Planeswalker/Battles ohne erkannte
   Rolle).
   - Neu in `App/engine.py`: `_hand_composition_category`/
     `_hand_composition_counts`, additiver `_turn_row_v440`-Wrapper
     (schreibt `hand_lands`/`hand_ramp`/…/`hand_other` in jede Turn-Zeile),
     additive Wrapper für `StreamingStatsV440.add`/
     `_average_dashboard_turns` (Aggregation zu `avg_hand_*` je Turn,
     global UND je Opponent-Profil).
   - Neu in `App/gui.py`: `SimpleStackedBarChart` (abhängigkeitsfreies
     Tkinter-Canvas-Balkendiagramm, gleiche Zeichenkonventionen wie das
     bestehende `SimpleLineChart`), `HAND_COMPOSITION_CATEGORIES`
     (Kategorien+Farben), eingebunden im "Rundenverlauf"-Tab.
2. **`combat_and_removal_diagnostics` wurde bereits seit WP6/WP7 berechnet,
   aber nie an die GUI weitergereicht** (`build_analysis_overview` gab es
   nicht weiter) und war dadurch in der Oberfläche nirgends sichtbar -
   obwohl "welche meiner Karten sterben/werden entfernt" eine für die
   Deck-Abstimmung direkt nützliche Frage ist. Jetzt in
   `build_analysis_overview` durchgereicht und in der Übersicht als neuer
   Abschnitt "Kampf & Entfernung" angezeigt (Ø Tode im Kampf/Run, Ø vom
   Gegner entfernt/Run, gesamt geboardwiped, häufigste Kampftode/
   Entfernungsziele).

**Bewusst NICHT umgesetzt** (disclosed für eine spätere Version, statt
unautorisiert in diese ohnehin schon große Änderung hineinzuziehen):
Mulligan-Anzahl-Verteilung (Histogramm statt nur Ø-Wert - macht bimodale
Konsistenzrisiken sichtbar, die ein Durchschnitt verdeckt) und ein
eigenes Mana-Verfügbarkeits-Diagramm über die Zeit (aktuell nur als
Tabellenspalte "Ø Mana Main" sichtbar). Beides wäre eine sinnvolle
Ergänzung, aber kein Teil des konkreten Auftrags.

**Tests** (`tests/test_flexible_analysis_v465.py`, 27 neue):
Handzusammensetzungs-Kategorisierung (Land-Vorrang, Rolle-vor-Type-Line,
Type-Line-Fallback, "Sonstiges"-Auffangbecken, Summe == Handgröße für jede
Hand); `_wc_kind_scenarios`-Filterung (aktiviert/Kind/Default);
`StreamingStatsV440.add`-Erweiterung direkt mit handgebauten rr/tr/sr-Zeilen
(kein voller Simulationslauf nötig) - Win-Condition-Zählung bei
Erreichen/Nicht-Erreichen/mehreren Szenarien (frühester Turn gewinnt),
Handzusammensetzungs-Akkumulation global UND je Opponent-Profil;
`_average_dashboard_turns`-Mittelwertbildung für die neuen Felder;
`build_analysis_overview`-Beobachtungstext (ersetzte 111-Zeile, ehrlicher
Fallback, Weiterreichung von `combat_and_removal_diagnostics`). Zusätzlich
manuell End-zu-Ende gegen die echte `Bilbo V1`-Deck-Pipeline
(offline, Scryfall-Cache) mit drei Konfigurationen verifiziert: (1) eine
"Win Condition"-Szenario mit `thresholds.life=111` (Bilbos echter
Karten-Schwellenwert, jetzt über das generische System statt hart codiert)
- 0 % erreicht bei 8 Turns/15 Runs, plausibel; (2) ein künstlich leicht
erreichbares Testszenario (`thresholds.life=41`) - 95 % erreicht, exakt
gegen `scenario_runs.csv` gegengerechnet (19/20 Runs, Median Turn 3 -
stimmt überein); (3) gar keine Szenario-Datei - korrekter ehrlicher
"nicht konfiguriert"-Fallback. Handzusammensetzungs-Summen zusätzlich
gegen `turns.csv` (Rohdaten je Run/Turn) gegengerechnet: Summe der sieben
Kategorien entspricht in JEDER geprüften Zeile exakt `hand_size`. Volle
Testsuite vor und nach dieser Version grün (670/670, 1 vorbestehender,
unveränderter Skip - 643 bestehende + 27 neue). Die neue `App/gui.py`-
Oberfläche selbst konnte in dieser Cloud-Arbeitsumgebung wie bereits in
v4.64.0 NICHT automatisiert getestet werden (kein Tkinter/Display
verfügbar) - stattdessen sorgfältige manuelle Code-Durchsicht plus
`py_compile`-Syntaxprüfung; ein echter Klick-/Sichttest ist erst auf dem
Windows-Rechner des Nutzers möglich.

## v4.64.0 — GUI: "Gegnerprofil"-Dialog für das v4.63.0-Mehrgegner-Zustandsmodell (bis zu 4 Gegner, Farb-/Strategie-Symbole inkl. "?" für zufällig)

**Auftrag:** das in v4.63.0 nur über eine Strategie-JSON-Datei erreichbare
erweiterte Mehrgegner-Zustandsmodell braucht eine echte Bedienoberfläche: ein
Knopf "Gegnerprofil", der einen Dialog öffnet, in dem bis zu vier Gegner mit
je einer Farbe (dargestellt durch die echten Mana-Symbole) und einer
Strategie eingestellt werden können - für beides zusätzlich mit einer
"zufällig"-Option, dargestellt durch ein Fragezeichen-Symbol.

**Neu in `App/gui.py`:**
- `ColorPickerRow` - fünf anklickbare WUBRG-Mana-Symbol-Pips (dieselbe Optik
  wie die bereits bestehenden `ManaPip`/`_draw_single_mana`-Bausteine aus dem
  Win-Condition-Editor) plus ein sechstes "?"-Pip. Anklicken togglet eine
  Farbe an/aus, höchstens zwei gleichzeitig (die älteste weicht einer
  dritten) - deckt sich exakt mit dem Umfang, den
  `engine._validate_advanced_opponent_seats` ohnehin durchsetzt (1-2 Farben
  je Sitzplatz, siehe v4.63.0). "?" ist exklusiv zu jeder Farbauswahl.
- `AdvancedOpponentDialog` - der eigentliche "Gegnerprofil"-Dialog: eine
  Checkbox zum Aktivieren (überschreibt für diesen Lauf die einfache
  "Opponent"-Dropdown-Auswahl), ein Spinner "Anzahl Gegner" (1-4), und je
  Gegner eine `ColorPickerRow` plus eine Strategie-Combobox
  (aggro/midrange/control/horde/"?"). Änderungen wirken sich erst mit
  "Übernehmen" aus - "Abbrechen"/Fenster schließen verwirft sie
  (Dialog-lokale Kopien der Einstellungen, erst beim Übernehmen auf
  `app.advanced_opponent_*` zurückgeschrieben).
- Neuer Knopf "Gegnerprofil …" plus Statusanzeige ("Erweitert: N Gegner
  (aktiv)" / "Erweitert: aus") direkt neben der bestehenden
  "Opponent"-Combobox in der Simulationsleiste.
- Konfiguration bleibt über mehrere Dialog-Öffnungen und einen ganzen
  Simulationslauf hinweg auf der `GoldfishApp`-Instanz erhalten
  (`advanced_opponent_seat_specs`), wird aber bewusst NICHT in
  `save_project`/`load_project` mitgespeichert - ein disclosed offener
  Punkt für eine spätere Version, kein stillschweigend fallengelassenes
  Feature.

**Neu in `App/engine.py`:**
- `apply_advanced_opponent_model_override` - dieselbe additive
  Override-Logik wie das bereits bestehende Vorbild
  `apply_voltron_target_override`: ein expliziter GUI-/Pipeline-Wert
  überschreibt, was eine Strategie-Datei gesetzt hat. `run_pipeline_v440`
  bekommt dafür zwei neue optionale Parameter
  (`advanced_opponent_model`/`advanced_opponent_seats`), die durch alle
  bestehenden `*args, **kwargs`-Wrapper-Schichten unverändert durchgereicht
  werden.
- **"?" (zufällig) pro Sitzplatz, für Farbe UND Strategie unabhängig
  auswählbar** - aufgelöst GENAU EINMAL PRO RUN (nicht einmal pro
  GUI-Klick, nicht einmal pro Zug), mit derselben reproduzierbaren
  Vorgehensweise wie das bereits bestehende `"random"`-`opponent_profile`
  (`RANDOM_OPPONENT_CHOICES`/`simulate_game_v440`), aber über eine eigene,
  unabhängige `random.Random`-Instanz, damit beide Zufallsentscheidungen
  einander nicht korrelieren. Neu: `RANDOM_ADVANCED_OPPONENT_COLOR_CHOICES`
  (alle 5 mono- und 10 zweifarbigen Identitäten - exakt der Umfang, den
  diese erste Integrationsstufe ohnehin zulässt),
  `_resolve_advanced_opponent_seats_for_run` (der eigentliche Resolver),
  und ein weiterer additiver Wrapper von `simulate_game_v440`, der vor dem
  eigentlichen Spielstart aufgelöste Sitzplätze in die Strategie einsetzt -
  ohne jeden "?"-Marker ein reiner Durchreich-Wrapper ohne
  Verhaltensänderung.

**Tests** (`tests/test_advanced_opponent_model.py`, 9 neue): die neue
Override-Funktion (None lässt bestehende Felder unverändert, ein expliziter
Wert überschreibt und kopiert statt zu aliasen); Marker-Erkennung für
"random"/"?"/"zufällig"/"zufaellig"; Auflösung in einen gültigen
Farb-/Strategiewert; Reproduzierbarkeit bei gleichem Seed+Run-ID;
unterschiedliche Auflösung über verschiedene Run-IDs hinweg; ein
Ende-zu-Ende-Test durch die echte `simulate_game_v440`-Wrapper-Kette (nicht
nur den Resolver direkt), der bestätigt, dass ein "?"-Sitzplatz zum
Zeitpunkt der echten Zugschleife bereits vollständig aufgelöst und damit
`_validate_advanced_opponent_seats`-gültig ist. Volle Testsuite vor und
nach dieser Version grün (643/643, 1 vorbestehender, unveränderter Skip -
634 bestehende + 9 neue). Die neue `App/gui.py`-Oberfläche selbst konnte in
dieser Cloud-Arbeitsumgebung NICHT automatisiert getestet werden (kein
Tkinter/Display hier verfügbar, und dieses Projekt hatte noch nie
GUI-Tests) - stattdessen sorgfältige manuelle Code-Durchsicht plus
`py_compile`-Syntaxprüfung; ein echter Klick-/Sichttest ist erst auf dem
Windows-Rechner des Nutzers möglich, sobald diese Version dort läuft.

**Weiterhin offen:** Persistenz der "Gegnerprofil"-Konfiguration in
Projekt-Dateien (`save_project`/`load_project`); alles bereits unter
v4.63.0 "Weiterhin offen" Gelistete (drei-/vier-/fünffarbige Identitäten,
weitere Brackets, Konsum der drei zerfallenden Bestände in einen echten
Spieleffekt, eine echte Gewinnbedingung für `combo_finish_readiness`,
Synchronisierung der Sitzplatz-Tischgröße mit `state.opponents`).

## v4.63.0 — Gegner-Zustandsmodell "Punkt 3" abgeschlossen: echte Mehrgegner-Turnschleifen-Integration (mono-/zweifarbig, Bracket 3) + Mehrspieler-Zielverteilung

**Auftrag:** Nach dem additiven, rein synthetischen Cross-Check seit v4.44.0
wurde jetzt die echte Integration von `App/opponent_model/state_equation.py`
in die tatsächliche Zugschleife verlangt - ausdrücklich zunächst nur für
ein- und zweifarbige Gegner-Identitäten und Bracket 3 (die einzige
Kombination mit ausreichend breiten, echten EDHREC-Kalibrierungsdaten),
mit einem eigenen, individuellen Zustand JE Gegner statt eines einzigen
Gesamtprofils, PLUS einer neuen Anforderung: die Wahrscheinlichkeit, dass
die Einzelziel-Aktion eines Gegners bei n Spielern am Tisch das getestete
Deck trifft, im Mittel 1/(n-1) (der Gegner wählt unter den übrigen n-1
Spielern). Drei-/vier-/fünffarbige Identitäten, weitere Brackets und eine
breitere Trainingsdeck-Vielfalt sind nach eigener Nutzer-Vorgabe
ausdrücklich späteren Schritten vorbehalten.

**Architekturentscheidung (die vom Nutzer selbst offen gelassene Frage aus
der letzten Rückmeldung):** individuelles Profil pro Gegner, nicht ein
Gesamtprofil. `Strategy` bekommt zwei neue Felder: `advanced_opponent_model`
(bool, Default `False` - ändert am bestehenden Verhalten für JEDEN
bisherigen Aufrufer nichts) und `advanced_opponent_seats` (eine Liste, EIN
Eintrag je Sitzplatz: `{"strategy": "aggro"/"midrange"/"control"/"horde",
"colors": ["U","B"]}`). Ist der neue Modus aktiv, bekommt jeder Sitzplatz
sein eigenes, unabhängiges `OpponentProfile`/`OpponentState`-Paar - das
bestehende `opponent_profile`-Feld wird in diesem Modus ignoriert.

**Neu: `App/engine.py::_apply_advanced_multi_opponent_phase`** (additiv
neben, nicht anstelle von, `OPPONENT_PROFILES` - derselbe risikoarme Stil
wie der v4.44.0-Cross-Check, diesmal aber ein ECHTER Bestandteil der
Zugschleife statt eines Seiten-Durchlaufs). Je Aufruf (= eine Runde) rückt
jeder Sitzplatz seinen eigenen Zustand per `advance_opponent_state()` genau
einmal vor (inklusive aller bestehenden Mechaniken: Zugqualität, toter Zug,
Wipe-/Kombo-Mindestzug-Schranken, Halbwertszeit-Zerfall für
passive_value/sac_drain/disruption_lockout) und wird danach über
`query_castable_state()` abgefragt. `_validate_advanced_opponent_seats`
setzt den Umfang hart durch (Fehler statt stiller Fallback): 1-2 Farben je
Sitzplatz, Bracket ausschließlich 3, `strategy` eine der vier echten Typen
(nicht `goldfish`). Der Sitzplatz-Tisch wird einmalig pro Partie aufgebaut
und lose an `state` gehängt (`state._advanced_opponent_table`, dynamisches
Attribut wie das bereits bestehende `state._current_opponent_rng`), damit
er über mehrere Runden hinweg weiterwächst statt neu zu starten.

**Mehrspieler-Zielverteilung (`_advanced_opponent_targeting_dilution`):**
bei n Spielern am Tisch (getesteter Spieler + alle Sitzplätze) trifft die
Einzelziel-Aktion eines einzelnen Gegners das getestete Deck im Mittel mit
Wahrscheinlichkeit 1/(n-1) - unter der (offengelegten, vereinfachenden)
Annahme einer Gleichverteilung über alle möglichen Ziele. Angewendet auf
gezielte Entfernung (`has_interaction`) UND auf Kampf-/Präsenzdruck aus
`board_presence` (ein Angreifer wählt in Commander real genau EIN Ziel).
Bewusst NICHT verdünnt: Board-Wipes (treffen symmetrisch den ganzen Tisch,
unabhängig von der Tischgröße) und `combo_finish_readiness` (typischerweise
eine "du gewinnst"-Bedingung ohne Einzelziel). Die drei zerfallenden
Bestände `passive_value_by_type`/`sac_drain_by_type`/
`disruption_lockout_by_type` wachsen je Sitzplatz unverändert weiter, werden
aber - genau wie im additiven Cross-Check seit v4.40.0 bereits offengelegt -
in dieser Version noch in KEINEN echten Spieleffekt umgesetzt (nur
mitgeführt, für eine spätere Integrationsstufe).

Die tatsächliche Auflösung von Entfernung und Wipe (Zielwahl unter den
Battlefield-Permanents, Hexproof/Ward/Indestructible-Prüfung,
Schutzkarten-Reaktion, Wipe-Zielort) verwendet dieselben, bereits
bestehenden Helferfunktionen wie der alte Aggregat-Pfad
(`_spot_remove_target`, `choose_removal_type`, `try_reactive_protection`,
`try_semantic_board_protection`, `move_permanent_to_zone`,
`combat_importance.choose_removal_target`) - nur WELCHER Sitzplatz WANN
WELCHE Wahrscheinlichkeit auslöst, ist neu.

**Anbindung:** ein weiterer additiver Wrapper von
`apply_abstract_opponent_phase` (derselbe etablierte Stil wie die
vorherigen Versionierungs-Wrapper in dieser Datei) - aktiv nur bei
`strategy.advanced_opponent_model=True`, sonst bytegleich der alte Pfad.
`load_strategy` liest beide neuen Felder aus einer Strategie-JSON-Datei.

**Reasonierte, offengelegte Konstante:** `_ADVANCED_OPPONENT_COMBAT_DAMAGE_
PER_BOARD_UNIT = 1.0` - so gewählt, dass ein Bracket-3-Midrange-Gegner mit
vollem Board (board_presence-Cap 10.0) bei genau einem Gegner am Tisch
(Verdünnung 1.0) größenordnungsmäßig im Bereich des alten
`OPPONENT_PROFILES["midrange"]["damage_scale"]`-Modells liegt - keine
exakte Äquivalenz beansprucht.

**Tests** (`tests/test_advanced_opponent_model.py`, 19 neue): Validierung
(leere Sitzliste, `goldfish` als Sitzplatz-Strategie, unbekannte Farbe,
3-Farben-Sitzplatz, farbloser Sitzplatz, Bracket ≠ 3 - jeweils ein Fehler);
Tischaufbau (unabhängige Zustände je Sitzplatz, Zwischenspeicherung über
mehrere Aufrufe); Zielverdünnungs-Formel (n=2 → 1.0, n=4 → 1/3, monoton
fallend); Integrationstests inklusive eines empirischen Belegs, dass EIN
konkreter Sitzplatz seine EIGENE Trefferquote verdünnt, wenn weitere
Sitzplätze dazukommen (deterministisch 100% bei n=2, spürbar niedriger bei
n=4) - eine frühere Version dieses Tests verglich stattdessen den
GESAMTSCHADEN zwischen Tischgrößen, was durch die zusätzliche Aggregat-
Präsenz weiterer Sitzplätze selbst konfundiert war und korrigiert wurde.
Ein manueller Rauchtest über 60 Partien × 15 Runden mit echten
Battlefield-Kreaturen (Entfernung UND Wipes lösen sichtbar aus, siehe
Event-Log) bestätigte zusätzlich, dass keine Ausnahme auftritt. Volle
Testsuite vor und nach dieser Version grün (634/634, 1 vorbestehender,
unveränderter Skip - 615 bestehende + 19 neue).

**Weiterhin offen (nach eigener Nutzer-Vorgabe spätere Schritte):**
drei-/vier-/fünffarbige Gegner-Identitäten; weitere Brackets; eine
statistisch breitere Trainingsdeck-Stichprobe je Zelle; Konsum der drei
zerfallenden Bestände (passive_value/sac_drain/disruption_lockout) in einen
echten Spieleffekt; eine echte Gewinnbedingung für `combo_finish_readiness`;
Synchronisierung der neuen Sitzplatz-Tischgröße mit der bestehenden
`state.opponents`-Listenlänge; GUI-Anbindung (Sitzplatz-Konfiguration ist
bislang nur über eine Strategie-JSON-Datei erreichbar, keine eigene
Bedienoberfläche).

## v4.62.0 — Flavor-Strategie-Matrix: Simic (GU), Gilden-Portion 10/10 — Gilden-Ebene abgeschlossen (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Abschluss der Gilden-Ebene nach Boros (v4.61.0). Alle 6
Simic-Flavors (Elfen-Ramp/Ezuri, Landfall-Ramp/Aesi, Sea Monsters/
Arixmethes, Klone & Populate/Adrix and Nev, Merfolk/Kumena,
Mana-Doubling-Combo/Kinnan) gegen echte EDHREC-Bracket-3-"Average
Deck – Upgraded"-Listen verifiziert; das Guild-Dokument diente nur
als Recherche-Gerüst. Damit ist die komplette zweifarbige
Gilden-Ebene (10 Gilden × 6 Flavors = 60 Zellen) fertiggestellt;
zusammen mit der vorherigen Monofarben-Ebene (5 Farben × 6 Flavors =
30 Zellen) sind projektweit nun 90 Flavor-Zellen erarbeitet.

**Befund:** Sechzehnter und siebzehnter bestätigter Combo-Fund des
Projekts: Biovisionary + Rite of Replication (kicked) als
alternative Siegbedingung bei Adrix and Nev, und Basalt Monolith +
Dramatic Reversal ("Kinnan-Combo", durch Kinnans eigene
Mana-Verdopplung verstärkt) bei Kinnan. Neuer Projekt-Höchstwert
Ramp-Dichte bei Aesi (37,3 %, vorheriger Rekord 20,7 % bei Gitrog)
und neuer Höchstwert Token/Klon-Kern bei Adrix and Nev (45,2 %,
vorheriger Rekord 43,8 % bei Neyali). GU kombiniert seine
Farbmodifikatoren auf zwei Dimensionen (mana_growth 1,235× und
passive_value_growth 1,61× — der zweithöchste kombinierte
Einzelmodifikator des Projekts nach Orzhovs disruption_growth
1,62×). Das "thematischer Kern überschneidet sich mit
Basisdimension"-Modelllimit trat in dieser Portion siebenfach auf
(Ezuri/Elfen, Aesi/Landfall, Arixmethes/Sea-Monsters,
Kumena/Merfolk, Kinnan/Mana-Engine u.a.) und ist damit projektweit
das am häufigsten dokumentierte Modelllimit. Kinnan weist als
Kontroll-Flavor null Wipe-Karten auf, kompensiert dies aber über
Zählschutz und Combo-Absicherung.

**Zusammenfassung der gesamten Gilden-Ebene (Portionen 1–10):**
projektweit 17 bestätigte Combos über 6 unterscheidbare
Strukturmuster; wiederkehrende Game-Changer außerhalb der
9 Disruption-Karten (u. a. Smothering Tithe dreifach in Boros
gefunden, Rhystic Study mehrfach guildübergreifend, Seedborn Muse
dreifach, Cyclonic Rift wiederholt als Wipe-Analogon); das
Voltron-Limitationsmuster bestätigt in 6 von 10 Gilden; das
"thematischer Kern"-Modelllimit in über 10 Einzelfällen
dokumentiert. Reine Recherche- und Dokumentationsarbeit ohne
Code- oder Gewichtsänderung; `ENGINE_VERSION` und GUI-Titel wurden
ausschließlich zur Versionskennzeichnung synchron angehoben.
Testsuite unverändert bei 615 Tests (1 übersprungen). Weitere
Schritte (Kalibrierungs-Synthese, Behebung der dokumentierten
Modelllimitationen) liegen außerhalb dieser Sitzung.

## v4.61.0 — Flavor-Strategie-Matrix: Boros (RW), Gilden-Portion 9/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Golgari (v4.60.0). Alle
6 Boros-Flavors (Equipment/Wyleth, Tokens/Neyali, Extra Combats/
Aurelia, Artefakte & Recycling/Osgir, Burn & Damage-Lifegain/Firesong
and Sunspeaker, Humans & Soldiers/Adriana) gegen echte
EDHREC-Bracket-3-"Average Deck – Upgraded"-Listen verifiziert; das
Guild-Dokument diente nur als Recherche-Gerüst.

**Befund:** Fünfzehnter bestätigter Combo-Fund des Projekts und neues
Muster: Boros Reckoner + Stuffy Doll (Schaden-Echo-Infinite) bei
Firesong and Sunspeaker, verstärkt durch Fiery Emancipation. Neuer
Projekt-Höchstwert Wipe-Dichte mit großem Abstand: Firesong and
Sunspeaker mit neun Wipes (13,8%), mehr als doppelt so hoch wie der
bisherige Höchstwert Liesa/Orzhov (6,3%) — und fast exakt auf dem
RW-modifizierten Control-Wipe-Basiswert, eine der genauesten
Vorhersage-Übereinstimmungen des Projekts. Smothering Tithe als
projektweit am häufigsten gefundener einzelne Game-Changer: drei
unabhängige Funde allein in dieser Portion (Aurelia, Osgir, Adriana).
Sechste Voltron-Board-Präsenz-Modellgrenze bei Wyleth (23,4%).
Dritter gildenübergreifender Fund des Disruption-Game-Changers Grand
Abolisher (Aurelia). Boros kombiniert die RW-Farbmodifikatoren nur
auf einer Dimension (board_presence, 1,2075× — real multiplikativ,
die genaue Umkehrung des Golgari-Falls mit passive_value_growth als
einziger Überlappung). Methodischer Vorbehalt bei Adriana: nur 18
EDHREC-Decks getrackt, kleinste Stichprobe des Projekts.

**Dateien:** `Docs/scratch/boros_flavor_pilot_raw.md` (Rohdaten, alle
6 Decks), `Docs/flavor_strategy_matrix_boros_v4_61_0.md` (vollständige
6-Zellen-Matrix mit RW-Farbmodifikator-Tabelle, Dichte-Auswertung, 5
nicht-trivialen Befunden, allen 10-Feld-Zustandsfunktionen und
Reflexion). Keine Code- oder Gewichtsänderung; alle 6 Zellen bleiben
Kandidaten für `Data/Models/opponent_state_weights.json`.

**Tests:** 615 Tests, 1 übersprungen, unverändert vor und nach dieser
Portion (`python3 -m unittest discover -s tests`).

## v4.60.0 — Flavor-Strategie-Matrix: Golgari (BG), Gilden-Portion 8/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Izzet (v4.59.0). Alle
6 Golgari-Flavors (Graveyard & Reanimator/Meren, Sacrifice/Mazirek,
Lands in the Graveyard/The Gitrog Monster, +1/+1-Counter/Skullbriar,
Elves/Lathril, Fungus & Saprolings/Slimefoot) gegen echte
EDHREC-Bracket-3-"Average Deck – Upgraded"-Listen verifiziert; das
Guild-Dokument diente nur als Recherche-Gerüst.

**Befund:** Vierzehnter bestätigter Combo-Fund des Projekts und
erstes "Elfball"-Muster: Priest of Titania + Staff of Domination bei
Lathril (Infinite Mana). Zwei weitere Altar-Doppel-Funde (Ashnod's +
Phyrexian Altar) ohne dritten Combo-Baustein bei Mazirek und
Slimefoot — die methodische Zurückhaltung des Projekts bestätigt sich
weiter. Neuer Projekt-Höchstwert für gestapelte
Counter-Verdoppler-Dichte gleich zweimal in einer Portion übertroffen:
Mazirek mit vier, dann Skullbriar mit fünf gleichzeitigen
Verdopplern und einem Gesamt-Counter-Kern von 42,2% — die dichteste
thematische Kern-Dimension des gesamten Projekts. Fünfte
Voltron-Board-Präsenz-Modellgrenze bei Skullbriar (29,7%, nach
Preston, Valduk, Bruna, Stangg). Zwei neue Game-Changer-Funde
außerhalb der 9 getrackten Disruption-Karten: Field of the Dead
(Gitrog, alt_win_condition) und Seedborn Muse (Lathril,
draw_engine/passive_value) — beide bestätigen die Tagging-Konsistenz
von `game_changer_archetypes.json`. Golgari kombiniert die BG-
Farbmodifikatoren nur auf einer Dimension (passive_value_growth,
1,3225× — real deutlich verstärkend, anders als Izzets nahezu
neutraler Einzel-Overlap).

**Dateien:** `Docs/scratch/golgari_flavor_pilot_raw.md` (Rohdaten,
alle 6 Decks), `Docs/flavor_strategy_matrix_golgari_v4_60_0.md`
(vollständige 6-Zellen-Matrix mit BG-Farbmodifikator-Tabelle,
Dichte-Auswertung, 5 nicht-trivialen Befunden, allen 10-Feld-
Zustandsfunktionen und Reflexion). Keine Code- oder
Gewichtsänderung; alle 6 Zellen bleiben Kandidaten für
`Data/Models/opponent_state_weights.json`.

**Tests:** 615 Tests, 1 übersprungen, unverändert vor und nach dieser
Portion (`python3 -m unittest discover -s tests`).

## v4.59.0 — Flavor-Strategie-Matrix: Izzet (UR), Gilden-Portion 7/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Orzhov (v4.58.0). Alle
6 Izzet-Flavors (Spellslinger & Magecraft/Mizzix, Artefakte &
Thopters/Jhoira, Wheels & Draw-Punisher/The Locust God, Spell
Copy/Melek, Dragons & Big Spells/Lozhan, Coin Flips & Chaos/Yusri)
gegen echte EDHREC-Bracket-3-"Average Deck – Upgraded"-Listen
verifiziert; das Guild-Dokument diente nur als Recherche-Gerüst.

**Befund:** Neuer Projekt-Tiefstwert Board-Präsenz bei Mizzix
(16,7%, unterbietet Eriette/Orzhov 26,6%) — Spellslinger-Decks sind
strukturell die kreaturenärmste Deck-Kategorie des Projekts (Melek
mit 20,3% zweitniedrigster Wert). Dritte Gilde in Folge ohne
bestätigten Combo-Fund (nach Gruul, Selesnya) — das prominente
Okaun+Zndrsplt-Synergiepaar bei Yusri wurde bewusst NICHT als
vollständiger Infinite gezählt, da kein dritter freier
Wiederholungs-Baustein in der Liste identifizierbar war. Neuer
Projekt-Höchstwert Dragons/Typal-Dichte bei Lozhan (58,1%,
übertrifft Atarka/Gruul 39,7%). Extremwert Spell-Dichte bei Mizzix
(65,2% aller Nicht-Land-Karten Instants/Sorceries, Projekt-
Höchstwert). Die kombinierte UR-Mana-Growth-Modifikation (0,95×
1,10=1,045×) ist die bisher am nächsten an Neutralität liegende
Farbkombination des Projekts — die einzige der 7 Dimensionen, auf
der beide Farben überhaupt überlappen. Sechs neue Fälle des
"thematischen Kern"-Problems (Spellslinger-, Artefakte-, Wheel-,
Dragons/Typal-, Spell-Copy- und Coin-Flip-Kern), hilfsweise je nach
Funktion auf combo_growth, mana_growth oder passive_value_growth
gemappt.

**Dateien:** `Docs/scratch/izzet_flavor_pilot_raw.md` (Rohdaten, alle
6 Decks), `Docs/flavor_strategy_matrix_izzet_v4_59_0.md`
(vollständige 6-Zellen-Matrix mit UR-Farbmodifikator-Tabelle,
Dichte-Auswertung, 5 nicht-trivialen Befunden, allen 10-Feld-
Zustandsfunktionen und Reflexion). Keine Code- oder
Gewichtsänderung; alle 6 Zellen bleiben Kandidaten für
`Data/Models/opponent_state_weights.json`.

**Tests:** 615 Tests, 1 übersprungen, unverändert vor und nach dieser
Portion (`python3 -m unittest discover -s tests`).

## v4.58.0 — Flavor-Strategie-Matrix: Orzhov (WB), Gilden-Portion 6/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Selesnya (v4.57.0). Alle
6 Orzhov-Archetypen (Sacrifice/Aristocrats, Lifegain & Drain/Midrange-
Voltron, Tokens/Go-Wide-Aristocrats, Reanimator & Recursion/Value-
Control, Auren & Curses/Enchantment-Control, Taxes & Pillowfort/
Attrition-Control) real per EDHREC-Bracket-3-Liste ausgezählt.
Kombinierter WB-Farbmodifikator berechnet: wipe_readiness 1,43×,
passive_value_growth 1,4375×, disruption_growth 1,62× (drei
überlappende Dimensionen, fast gleichauf mit Dimirs vier).

**Befund:** Dichteste Combo-Portion des Projekts — DREI bestätigte
Combo-Funde in einer einzigen Gilden-Portion (bisheriger Höchstwert:
Rakdos mit zwei). Teysa Karlov liefert den elften Combo-Fund
(Yawgmoth-Pattern, dritte Bestätigung) UND einen neuen
Projekt-Höchstwert bei Opfer/Drain-Dichte (25,0%, übertrifft Judith/
Rakdos 16,9% und Yawgmoth/Schwarz 17,2%). Karlov of the Ghost Council
und Kambal, Consul of Allocation liefern den zwölften und
dreizehnten Combo-Fund — beide Exquisite Blood+Sanguine Bond, damit
der am häufigsten real bestätigte Combo-Typ des Projekts (drei
unabhängige Funde). Grand Abolisher wird bei Kambal real bestätigt —
dritter Game-Changer-Fund über Gilden-Grenzen hinweg (nach Grand
Arbiter Augustin IV/Azorius, Drannith Magistrate/Selesnya). Eriette of
the Charmed Apple bestätigt mit 26,6% Board-Präsenz ein drittes Mal
die strukturelle Board-Präsenz-Limitation dichter Enchantment-Engines
(nach Sythis/Selesnya, Stangg/Gruul-Voltron). Alle 6 Zellen als
Kandidat dokumentiert, KEINE Übernahme in
`opponent_state_weights.json`. Vollständige Ausarbeitung:
`Docs/flavor_strategy_matrix_orzhov_v4_58_0.md`, Rohdaten:
`Docs/scratch/orzhov_flavor_pilot_raw.md`. Tests unverändert 615/615.
Fortsetzung (die übrigen 4 Gilden) folgt im selben Durchgang.

## v4.57.0 — Flavor-Strategie-Matrix: Selesnya (GW), Gilden-Portion 5/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Gruul (v4.56.0). Alle 6
Selesnya-Archetypen (Tokens/Go-Wide Midrange, +1/+1-Counter/Creature-
Midrange, Enchantress & Auren/Engine-Voltron, Lifegain/Counters-
Midrange, Humans/Typal Aggro, Hatebears & Creature Toolbox/Stax-
Midrange) real per EDHREC-Bracket-3-Liste ausgezählt. Kombinierter
GW-Farbmodifikator berechnet: board_presence 1,155×,
**passive_value_growth 1,4375× (neuer Projekt-Höchstwert)**.

**Befund:** Zweite Gilde in Folge ganz ohne bestätigten Combo-Fund
(nach Gruul). Zwei Reklassifizierungen: Sythis, Harvest's Hand
(Enchantress & Auren) von "Engine/Voltron" zu control (Pillow-Fort-
statt Kampf-Fokus, 32,8% Board-Präsenz) und Yasharn, Implacable Earth
(Hatebears) von "Stax-Midrange" zu control (höchste Interaktions-,
Wipe- und Disruption-Werte der Portion). Neuer Projekt-Höchstwert-
Kandidat Board-Präsenz: Hamza, Guardian of Arashin mit 60,0%. Neue
Projekt-Höchstwerte bei Passive Value: Sythis mit 17,2% klassisch bzw.
50,0% Enchantment-Typ-Anteil insgesamt — dichteste Passive-Value-
Engine des Projekts. Drannith Magistrate wird bei Yasharn ein zweites
Mal real bestätigt (nach Grand Arbiter Augustin IV, Azorius v4.53.0) —
erster Game-Changer-Wiederfund über Gilden-Grenzen hinweg. Alle 6
Zellen als Kandidat dokumentiert, KEINE Übernahme in
`opponent_state_weights.json`. Vollständige Ausarbeitung:
`Docs/flavor_strategy_matrix_selesnya_v4_57_0.md`, Rohdaten:
`Docs/scratch/selesnya_flavor_pilot_raw.md`. Tests unverändert
615/615. Fortsetzung (die übrigen 5 Gilden) folgt im selben Durchgang.

## v4.56.0 — Flavor-Strategie-Matrix: Gruul (RG), Gilden-Portion 4/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Rakdos (v4.55.0). Alle 6
Gruul-Archetypen (Power Matters/Stompy-Aggro, Lands & Landfall/Engine-
Midrange, Dragons/Typal-Big-Mana Aggro, +1/+1-Counter & Modified/
Aggro-Midrange, Auren & Equipment/Voltron-Combat, Werewolves & Wolves/
Typal Aggro) real per EDHREC-Bracket-3-Liste ausgezählt. Kombinierter
RG-Farbmodifikator berechnet: board_presence 1,265× und mana_growth
1,43× — **beides neue Projekt-Höchstwerte** unter allen bisherigen
Gilden-Kombinationen (WU, UB, BR).

**Befund:** Vierte Bestätigung der Voltron-Board-Präsenz-Limitation
des Projekts bei Stangg, Echo Warrior (22,7% — niedrigster Wert der
gesamten Rot/Grün-Ebene, nach Preston/Weiß v4.48.0, Valduk/Rot
v4.51.0, Bruna/Azorius v4.53.0). Fünf von sechs Flavors wurden real
evidenzbasiert zu aggro eingeordnet (nur Lands & Landfall zu
midrange) — die einseitigste Verteilung einer Gilden-Portion bisher,
aber konsistent mit Gruuls realer Identität als aggressivste
Zweifarb-Gilde. Erste Gilden-Portion des Projekts ganz ohne
bestätigten Combo-Fund. Durchgängig niedrigste kombinierte
Interaktions-Werte des Projekts (1,6%–4,6% über alle 6 Flavors).
Fünf von sechs Flavors zeigen einen dichten thematischen Kartenkern
(Landfall 31,7%, Dragons 39,7%, +1/+1-Counter 33,8%, Auren/Equipment
43,9%, Werewolves 47,7%) ohne sauberes bestehendes Feld — dieselbe
Modellgrenze wie in Rot/Dimir/Rakdos, hier auf fast die gesamte Gilde
ausgeweitet. Alle 6 Zellen als Kandidat dokumentiert, KEINE Übernahme
in `opponent_state_weights.json`. Vollständige Ausarbeitung:
`Docs/flavor_strategy_matrix_gruul_v4_56_0.md`, Rohdaten:
`Docs/scratch/gruul_flavor_pilot_raw.md`. Tests unverändert 615/615.
Fortsetzung (die übrigen 6 Gilden) folgt im selben Durchgang.

## v4.55.0 — Flavor-Strategie-Matrix: Rakdos (BR), Gilden-Portion 3/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Dimir (v4.54.0). Alle 6
Rakdos-Archetypen (Sacrifice/Aristocrats, Madness & Discard, Treasure
& Exile-Cast, Group Slug/Burn, Demons/Big-Mana, Vampires) real per
EDHREC-Bracket-3-Liste ausgezählt. Kombinierter BR-Farbmodifikator
berechnet: **erster Fund des Projekts ohne jede Feld-Überlappung** —
B und R modifizieren keine gemeinsame Dimension in
`opponent_state_weights.json`, die Kombination ist reine Vereinigung
(B: interaction 1,20×, wipe 1,10×, combo_finish 1,20×, sac_drain
1,55×, passive_value 1,15×, disruption 1,35×; R: board_presence
1,15×, mana_growth 1,10×, dead_turn_chance 0,90×), anders als bei
Azorius (2 von 7 überlappend) und Dimir (4 von 7 überlappend).

**Befund:** Neunter bestätigter vollständiger Combo-Fund des Projekts:
Yawgmoth, Thran Physician + kostenlos-rekursive Kreatur
(Reassembling Skeleton/Bloodghast/Nether Traitor) + Ashnod's Altar bei
Judith, the Scourge Diva — zweite reale Bestätigung des exakt gleichen
Musters nach dem Mono-Schwarz-Fund (v4.50.0), bestätigt den
B-Modifikator sac_drain_growth (1,55×) unabhängig ein zweites Mal
(16,9% Opfer/Drain-Dichte, nahe am Rekordwert 17,2%). Zehnter
bestätigter vollständiger Combo-Fund des Projekts: Exquisite Blood +
Sanguine Bond bei Olivia Voldaren — erster realer Fund dieses
klassischen Infinite-Lifegain-Drain-Musters, beide Karten real
vorhanden. Mogis (Group Slug/Burn) liefert mit 4,7% den
Portions-Höchstwert bei Wipes und mit 32,8% den Portions-Tiefstwert
bei Board-Präsenz — klare Control-Signatur, zu Control eingeordnet.
Treasure & Exile-Cast (Prosper) und Group Slug (Mogis) zeigen dieselbe
bereits aus Dimir bekannte Modellgrenze: ein dichter, thematisch
zentraler Kartenkern (29,2% bzw. 28,1%), der sich nicht sauber in ein
bestehendes Feld einordnen lässt, hilfsweise auf mana_growth bzw.
passive_value_growth gemappt. Alle 6 Zellen als Kandidat dokumentiert,
KEINE Übernahme in `opponent_state_weights.json`. Vollständige
Ausarbeitung: `Docs/flavor_strategy_matrix_rakdos_v4_55_0.md`,
Rohdaten: `Docs/scratch/rakdos_flavor_pilot_raw.md`. Tests unverändert
615/615. Fortsetzung (die übrigen 7 Gilden) folgt im selben Durchgang.

## v4.54.0 — Flavor-Strategie-Matrix: Dimir (UB), Gilden-Portion 2/10 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der Gilden-Ebene nach Azorius (v4.53.0). Alle 6
Dimir-Archetypen (Mill, Zombies, Rogues & Ninjas, Self-Mill &
Reanimator, Theft & Copy, Flash) real per EDHREC-Bracket-3-Liste
ausgezählt. Kombinierter UB-Farbmodifikator berechnet: interaction
(1,74×), combo_finish (1,38×), passive_value (1,61×), disruption
(1,62×) — kombiniert auf vier statt zwei Dimensionen wie bei Azorius.

**Befund:** Siebter bestätigter vollständiger Combo-Fund des Projekts:
Rooftop Storm + Gravecrawler + freier Opfer-Outlet (Carrion
Feeder/Ashnod's Altar/Phyrexian Altar), alle real bei Wilhelt, the
Rotcleaver. Notion Thief wurde DREIFACH real bestätigt in dieser einen
Gilde (Anowon, Xanathar, Nymris) — die dichteste Wiederholung eines der
9 getrackten unmapped_persistent_disruption-Game-Changer im Projekt
bisher. Xanathar liefert den zweiten Doppel-Game-Changer-Fund des
Projekts (Notion Thief + Opposition Agent gemeinsam, nach Grand Arbiter
Augustin IV + Drannith Magistrate, Azorius). Nymris liefert mit 25,0%
kombinierter Interaktionsdichte einen neuen Projekt-Höchstwert
(übertrifft Ojutai, Azorius, 23,8%) — bestätigt direkt den kombinierten
UB-Multiplikator. Zombies (Wilhelt) wurde von "Typal/Aristocrats" zu
"horde" reklassifiziert (EDHREC-Tag "Tokens 303" dominiert vor
"Aristocrats 267"). Mill (Phenax) und Theft & Copy (Xanathar) zeigen
dieselbe Modellgrenze: ein dichter, thematisch zentraler Kartenkern
(26,6% bzw. 22,2%), der weder Removal/Wipe noch klassisches 2-Karten-
Combo ist, hilfsweise über combo_growth abgebildet. Alle 6 Zellen als
Kandidat dokumentiert, KEINE Übernahme in `opponent_state_weights.json`.
Vollständige Ausarbeitung: `Docs/flavor_strategy_matrix_dimir_v4_54_0.md`,
Rohdaten: `Docs/scratch/dimir_flavor_pilot_raw.md`. Tests unverändert
615/615. Fortsetzung (die übrigen 8 Gilden) folgt im selben Durchgang.

## v4.53.0 — Flavor-Strategie-Matrix: Azorius (WU), Gilden-Portion 1/10 (Beginn Zweifarb-Ebene, eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Mit Grün (v4.52.0) ist die Monofarben-Ebene abgeschlossen.
Nutzer bat darum, eigenständig iterativ weiterzuarbeiten — diese Portion
beginnt die zweite Hälfte: die 10 Zweifarb-Gilden aus
`Commander_Zweifarben_Gilden_Bracket_3.md`. Alle 6 Azorius-Archetypen
(Draw-Go, Blink & ETB, Artefakte & Fahrzeuge, Spirits & Flying,
Auren/Voltron, Taxes & Pillowfort) real per EDHREC-Bracket-3-Liste
ausgezählt. Neu: Farbmodifikatoren aus `opponent_state_weights.json`
werden für Zweifarb-Identitäten multiplikativ kombiniert (W×U).

**Befund:** Sechster bestätigter vollständiger Combo-Fund des Projekts:
Peregrine Drake + Deadeye Navigator, beide real bei Brago, King Eternal
(nach Heliod+Ballista/Weiß, Isochron+Dramatic Reversal+Basalt/Blau,
Sanguine Bond+Exquisite Blood/Schwarz, Rings of Brighthearth+Basalt
Monolith/Rot, Wirewood Symbiote+Priest of Titania/Grün). Grand Arbiter
Augustin IV liefert mit 26,2% (17 Karten) den neuen Projekt-Höchstwert
für Disruption — er selbst UND Drannith Magistrate sind gleichzeitig
real vorhanden (2 der 9 getrackten unmapped_persistent_disruption-
Game-Changer in einer Liste, analog zum bisher einzigen Doppel-Fund Zur
the Enchanter, v4.42.0, jetzt erstmals auf Zweifarb-Ebene). Der
kombinierte WU-Passive-Value-Multiplikator (1,25×1,40=1,75, höchster
Wert aller bisherigen Modifikatoren) wird direkt durch Smothering
Tithe+Rhystic Study+Mystic Remora GLEICHZEITIG in derselben Liste
bestätigt. Narset, Parter of Veils liefert den ersten echten
Blau-Decklisten-Beleg für einen der 9 Game-Changer (vorher nur über
Karten-Farbidentität angenommen). Auren/Voltron (Bruna) bestätigt die
Voltron-Board-Präsenz-Modellgrenze zum dritten Mal (22,2%, nach
Preston/Weiß und Valduk/Rot). Artefakte & Fahrzeuge (Shorikai) wurde
von "Synergy-Midrange" zu "Control" reklassifiziert (niedrige
Board-Präsenz, moderate Wipe-Dichte). Alle 6 Zellen als Kandidat
dokumentiert, KEINE Übernahme in `opponent_state_weights.json`.
Vollständige Ausarbeitung: `Docs/flavor_strategy_matrix_azorius_v4_53_0.md`,
Rohdaten: `Docs/scratch/azorius_flavor_pilot_raw.md`. Tests unverändert
615/615. Fortsetzung (die übrigen 9 Gilden) folgt im selben Durchgang.

## v4.52.0 — Flavor-Strategie-Matrix: Grün, Portion 5/15 (Taxonomie-Abgleich + eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Nutzer bat darum, eigenständig iterativ durch die
restlichen Farben zu arbeiten, ohne jedes Mal neu angestoßen zu werden.
Grün erforderte zusätzlich einen Taxonomie-Abgleich: der Grün-Pilot
(v4.47.0) nutzte noch 5 selbst gewählte Flavors, das neue
Nutzerdokument benennt 6. Entscheidung: die 4 deckungsgleichen Flavors
(Landfall/Ashaya, Elfball/Marwyn, Stompy/Ghalta, +1/+1-Counter/
Vorinclex) unverändert aus v4.47.0 übernommen; Ramp/Big-Mana (Azusa)
aus der aktiven Taxonomie entfernt, aber NICHT gelöscht (bleibt in
`green_flavor_strategy_matrix_pilot_v4_47_0.md` erhalten); die 2 echt
neuen Flavors (Tokens/Go-Wide=Ruxa, Patient Professor; Creature
Toolbox/Flash=Yeva, Nature's Herald) frisch per EDHREC-Bracket-3-Liste
recherchiert.

**Befund:** Fünfter bestätigter vollständiger Combo-Fund des Projekts:
Wirewood Symbiote + Priest of Titania, beide real in derselben
Yeva-Liste (nach Heliod+Ballista/Weiß, Isochron+Dramatic
Reversal+Basalt/Blau, Sanguine Bond+Exquisite Blood/Schwarz, Rings of
Brighthearth+Basalt Monolith/Rot). Yeva liefert zwei neue
Projekt-Höchstwerte gleichzeitig: Board-Präsenz 66,2% (bisheriger
Rekord: Elfen/Marwyn 58%) und Ramp-Dichte 26,2% (bisheriger Rekord:
Landfall/Ashaya ~17,5%) — eine reine Kreatur-Toolbox-Liste maximiert
beide Dimensionen gleichzeitig. Ruxa widerlegt real das Dokument-Label
"Tokens/Go-Wide" (nur 2 echte Token-Generatoren) und wurde zu
"Vanilla-Kreaturen/Anthems" reklassifiziert (Muraganda Petroglyphs,
Gaea's Anthem, Sylvan Anthem, Beastmaster Ascension). Grün bleibt über
alle 6 Flavors bei praktisch 0% Wipes/Disruption/Opfer-Drain, bestätigt
zum sechsten Mal die G-Farbmodifikator-Lücken in
`opponent_state_weights.json`. Mit dieser Portion ist die
Monofarben-Ebene (5 von 5: Weiß, Blau, Schwarz, Rot, Grün) vollständig
abgeschlossen — 30 Flavor-Zellen, 5 bestätigte vollständige
Combo-Funde. Alle Zellen als Kandidat dokumentiert, KEINE Übernahme in
`opponent_state_weights.json`. Vollständige Ausarbeitung:
`Docs/flavor_strategy_matrix_gruen_v4_52_0.md`, Rohdaten (2 neue
Decks): `Docs/scratch/green_flavor_pilot_raw_v4_52_0_addendum.md`.
Tests unverändert 615/615. Fortsetzung (die 10 Zweifarb-Gilden) folgt
im selben Durchgang.

## v4.51.0 — Flavor-Strategie-Matrix: Rot, Portion 4/15 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Nutzer bat darum, eigenständig iterativ durch die
restlichen Farben zu arbeiten, ohne jedes Mal neu angestoßen zu werden.
Alle 6 Rot-Archetypen aus `Commander_Monofarben_Bracket_3.md` (Goblins/
Go-Wide, Burn/Group Slug, Artefakte/Reanimation, Storm/Spellslinger,
Drachen/Tribal, Equipment/Voltron) real per EDHREC-Bracket-3-Liste
ausgezählt.

**Befund:** Vierter bestätigter vollständiger Combo-Fund des Projekts:
Rings of Brighthearth + Basalt Monolith, beide real in derselben
Daretti-Liste (nach Heliod+Ballista/Weiß, Isochron+Dramatic
Reversal+Basalt/Blau, Sanguine Bond+Exquisite Blood/Schwarz). Die
Krenko-Liste bestätigt real erneut die ursprüngliche v4.39.0-Notiz zu
Kiki-Jiki, Mirror Breaker (Karte vorhanden, aber kein Combo-Partner in
der Liste). Storm wurde über EDHRECs eigenes "Storm 147"-Tag bei Zada,
Hedron Grinder real bestätigt — der interaktionsärmste Flavor des
gesamten Projekts (1,6% Entfernung, 1,6% Wipe, 0% Disruption), bewusst
NICHT als `goldfish` klassifiziert (dieses Profil ist im Modell explizit
für "kein echter Gegner" reserviert), sondern als `aggro` mit stark
angehobenem `combo_growth`-Kandidaten. Equipment/Voltron (Valduk) zeigt
mit 18,75% die niedrigste Board-Präsenz-Dichte des Rot-Samples — dieselbe
Modellgrenze wie Preston/Light-Paws (Weiß, v4.48.0): Voltron konzentriert
Wert auf wenige Kreaturen statt Board-Breite. Burn/Group Slug (Ojer
Axonil) offenbart eine neue Modellgrenze: stehende Schadens-
Verzauberungen (Sulfuric Vortex, Manabarbs, Pyrohemia, Roiling Vortex)
erzeugen laufenden Direktschaden, der weder sauber auf
`passive_value_growth` noch auf `sac_drain_growth` passt. Burn/Group
Slug und Artefakte/Reanimation (Daretti) wurden von den Dokument-Labels
zu "control" präzisiert (niedrige bis moderate Board-Präsenz, spürbare
Interaktion/Wipes/Value-Engines statt Combat-Fokus). Daretti zeigt mit
6,3% Wipe- und 12,5% Ramp-Dichte die höchsten Werte des Rot-Samples —
für Mono-Rot ungewöhnlich hoch. Alle 6 Zellen als Kandidat dokumentiert,
KEINE Übernahme in `opponent_state_weights.json`. Vollständige
Ausarbeitung: `Docs/flavor_strategy_matrix_rot_v4_51_0.md`, Rohdaten:
`Docs/scratch/red_flavor_pilot_raw.md`. Tests unverändert 615/615.
Fortsetzung (Grün, danach die 10 Gilden) folgt im selben Durchgang.

## v4.50.0 — Flavor-Strategie-Matrix: Schwarz, Portion 3/15 (eigenständige Fortsetzung, keine Code-/Gewichtsänderung)

**Auftrag:** Nutzer bat darum, eigenständig iterativ durch die
restlichen Farben zu arbeiten, ohne jedes Mal neu angestoßen zu werden.
Alle 6 Schwarz-Archetypen aus `Commander_Monofarben_Bracket_3.md`
(Aristokraten/Sacrifice, Reanimator, Lifedrain/Big-Mana/Devotion,
Discard, Zombies, Ratten) real per EDHREC-Bracket-3-Liste ausgezählt.

**Befund:** Yawgmoth (Aristokraten) liefert den stärksten Sac-Drain-Fund
des gesamten Projekts (17,2%, 11 Karten) — dichter als die ursprüngliche
v4.40.0-Kalibrierungsquelle (Endrek Sahr Expensive, damals nur 4 benannte
Karten) selbst. Dritter bestätigter vollständiger Combo-Fund des
Projekts: Sanguine Bond + Exquisite Blood, beide real in derselben
Vito-Liste (nach Urza und Orvar in Blau, v4.49.0) — Vito bestätigt
zugleich erneut (nach v4.46.0) den fehlenden Opfer-Bezug von mono-
schwarzem Lifedrain (nur 1,6% Opfer/Drain-Dichte). Tergrid, God of
Fright — eine der 9 im Projekt getrackten unmapped_persistent_
disruption-Game-Changer — wurde real in einer Bracket-3-Discard-Liste
bestätigt. Ramp wird auch bei Schwarz im Nutzerdokument tendenziell
überschätzt (Vito real 7,8% vs. Dokument "12-16"). Ratten (Marrow-
Gnawer) wurde von "Aggro bis Combo" zu "horde" präzisiert (Go-Wide-
Token-Schwarm-Muster wie Myrel/Weiß und Elfen/Grün). Alle 6 Zellen als
Kandidat dokumentiert, KEINE Übernahme in `opponent_state_weights.json`.
Vollständige Ausarbeitung: `Docs/flavor_strategy_matrix_schwarz_v4_50_0.md`,
Rohdaten: `Docs/scratch/black_flavor_pilot_raw.md`. Tests unverändert
615/615. Fortsetzung (Rot, Grün) folgt im selben Durchgang.

## v4.49.0 — Flavor-Strategie-Matrix: Blau, Portion 2/15 (Nutzerwunsch: Verteilungen noch konsequenter an Realität kalibriert, keine Code-/Gewichtsänderung)

**Auftrag:** Fortsetzung der in v4.48.0 begonnenen Portionierung; Nutzer
bat ausdrücklich darum, die geschätzten Verteilungen entsprechend
anzupassen, sodass sie die Realität abbilden. Alle 6 Blau-Archetypen aus
`Commander_Monofarben_Bracket_3.md` (Spellslinger/Drakes, Artefakte/
Combo-Control, Mill, Draw-Matters, Meervolk, Klone/Diebstahl) real per
EDHREC-Bracket-3-Liste ausgezählt (Tier A, wie bei Weiß) statt die
Dokument-Rollenprofile zu übernehmen.

**Befund:** Blaus reale Interaktionsdichte übertrifft jeden bisherigen
Weiß-Fund massiv (Talrand, Spellslinger: 31,25% Konter+Bounce/Removal —
höchster Projektwert bislang, W und U zusammen). Zwei vollständige, real
bestätigte Combos gefunden (Urza: Isochron Scepter+Dramatic
Reversal+Basalt Monolith; Orvar: Peregrine Drake+Ghostly Flicker) — der
stärkste Combo-Befund des Projekts bislang. Talrands Drake-Token-
Mechanik zeigt eine echte Modellgrenze: rohe Kreaturenzahl (15,6%)
unterschätzt die tatsächliche Board-Entwicklung, weil 41 von 64
Nicht-Land-Karten selbst potenzielle Token-Trigger sind — dieselbe Art
von Grenze wie bei Voltron in der Weiß-Portion, nur umgekehrt (dort zu
hoch geschätzt, hier zu niedrig). Ein echter Opfer-Outlet (Ashnod's
Altar) tauchte in einem mono-blauen Deck (Minn) auf — schwacher, aber
realer Gegenbeleg zur pauschalen "Blau = 0% Opfer/Drain"-Annahme. Blau
clustert stark in "Control" (3 von 6 Flavors), nur Meervolk ist ein
echter Aggro-Ausreißer — deckt sich mit der Schnellvergleich-Einordnung
des Nutzerdokuments selbst ("Blau: Control/Tempo"). Klone/Diebstahl
(Orvar) wurde von "Control-Midrange" zu reinem "Midrange" präzisiert
(niedrigste Interaktionsdichte der drei Control-Kandidaten bei
gleichzeitig starkem Combo-Signal). Alle 6 Zellen als Kandidat
dokumentiert, KEINE Übernahme in `opponent_state_weights.json`.
Vollständige Ausarbeitung: `Docs/flavor_strategy_matrix_blau_v4_49_0.md`,
Rohdaten: `Docs/scratch/blue_flavor_pilot_raw.md`. Portionierungsplan
unverändert: Schwarz, Rot, Grün, dann die 10 Gilden. Tests unverändert
615/615.

## v4.48.0 — Flavor-Strategie-Matrix: Weiß, Portion 1/15 (Nutzer-Dokumente als Recherche-Gerüst, keine Code-/Gewichtsänderung)

**Auftrag:** Der Nutzer hat zwei ChatGPT-recherchierte Dokumente
(`Commander_Monofarben_Bracket_3.md`, `Commander_Zweifarben_Gilden_
Bracket_3.md`, zusammen 90 Archetyp-Zeilen über 5 Monofarben + 10 Gilden)
in den `Docs`-Ordner gelegt, weil die rein manuelle Moxfield-/EDHREC-
Recherche der Vorversionen für diesen Umfang zu langsam war. Auftrag:
diese Profile in das Flavor-Strategie-Matrix-Format überführen,
portioniert über mehrere Sitzungen; offene Frage nach hilfreichen
"Plugins".

**Bewertung der Nutzer-Dokumente:** strukturell gut und im Kern
vertrauenswürdig — jeder Archetyp verlinkt eine echte EDHREC-
`average-decks/<commander>/upgraded`-Seite (Bracket-3-Filter,
stichprobenartig für alle 6 Weiß-Links gegengeprüft: alle real, alle
mit aktivem Bracket-3-Filter), Farbidentitäten sind korrekt (Lathril,
Blade of the Elves korrekt als Golgari geführt — derselbe Fehler, der im
Grün-Piloten v4.47.0 selbst gemacht und korrigiert wurde). Aber: die
angegebenen Rollenprofil-Kartenzahlen sind generische Archetyp-
Einschätzungen, keine Auszählung der jeweils verlinkten Liste selbst (bei
4 von 6 geprüften Weiß-Decks liegt die reale Ramp-Dichte spürbar unter
der Dokument-Angabe). **Methodik-Entscheidung:** die Dokumente werden als
Recherche-Gerüst genutzt (Flavor-/Commander-Auswahl + EDHREC-Link — der
zeitintensivste Schritt der Orzhov-Runde entfällt dadurch), die
tatsächlichen Zustandsfunktionswerte werden weiterhin selbst aus der
echten, verlinkten Decklist ausgezählt (Tier A, wie beim Grün-Piloten) —
keine Abkehr vom Belegprinzip, sondern eine Effizienzsteigerung an
unbedenklicher Stelle. Zur "Plugins"-Frage: keines nötig — der
eingebaute Browser öffnete alle 6 EDHREC-Links dieser Portion ohne das
von Moxfield bekannte Rate-Limit-Problem.

**Befund (Weiß, alle 6 Archetypen real ausgezählt):** Ramp wird im
Nutzerdokument systematisch überschätzt; Wipe-Dichte variiert innerhalb
Weiß stark nach Flavor (1,5% Preston/Blink bis 6,3% Heliod/Lifegain)
statt gleichmäßig hoch, wie es der pauschale W-Wipe-Farbmodifikator
nahelegt; Board-Präsenz korreliert nicht mit dem Strategie-Label — das
"control"-gelabelte Taxes/Hatebears-Deck (Thalia) hat mit 61,9% die
höchste Kreaturendichte UND mit 22,2% (14 Karten) die mit Abstand
höchste je in diesem Projekt gefundene Disruption-/Stax-Dichte
(bisheriger Höchstwert: Zur the Enchanter mit 2/9, v4.42.0) — moderne
Hatebears-Karten sind fast ausschließlich Kreaturen, nicht Verzauberungen/
Artefakte wie das generische Stax-Modell unterstellt. Preston/Blink-ETB
wurde von "Value-Control" (Dokument-Label) zu "midrange" umklassifiziert,
weil die reale Liste hohe Board-Präsenz und die niedrigste Wipe-Dichte
der gesamten Weiß-Stichprobe zeigt. Alle 6 Zellen als "Kandidat für
Verfeinerung" mit vollständiger Zustandsfunktion dokumentiert, KEINE
Übernahme in `opponent_state_weights.json` in dieser Version. Vollständige
Ausarbeitung: `Docs/flavor_strategy_matrix_weiss_v4_48_0.md`, Rohdaten:
`Docs/scratch/white_flavor_pilot_raw.md`. Portionierungsplan für die
Fortsetzung (Blau, Schwarz, Rot, Grün-Neuabgleich, dann die 10 Gilden)
am Ende des Dokuments. Tests unverändert 615/615 (reine Dokumentations-
/Versionsänderung, kein Code-Verhalten betroffen).

## v4.47.0 — Flavor-Strategie-Matrix: Grün-Pilot (neuer Ansatz zu Punkt 2, keine Code-/Gewichtsänderung)

**Auftrag:** neuer Ansatz für die Gilden-/Cross-Dimension-Lücke (Punkt 2):
statt Farben nur über ihre Wachstumskurven abzubilden, soll pro Farbe eine
**Flavor-Strategie-Matrix** entstehen — Zeilen sind die typischen "Flavors"
einer Farbe (Grün: Landfall, Elfen, Ramp/Big-Mana, große Kreaturen,
+1/+1-Zähler), Spalten die bestehenden 5 Engine-Strategien (`goldfish,
aggro, midrange, control, horde`). Auf Rückfrage wurde vom Nutzer
festgelegt: (1) erst EINE Farbe als Pilot durchexerzieren statt direkt
alle 15 Identitäten, (2) die bestehenden 5 Strategien als Spalten
wiederverwenden statt einer neuen Achse.

**Vorgehen:** 5 echte, mono-grüne Commander gewählt (einer je Flavor,
über `edhrec.com/tags/<flavor>/mono-green` recherchiert), deren
vollständige EDHREC-"Average-Deck"-Liste abgerufen und nach echter
Interaktions-/Board-Präsenz-/Mana-/Passive-Value-/Combo-/Wipe-/
Disruption-/Sac-Drain-Dichte ausgewertet (Azusa=Ramp, Ashaya=Landfall,
Marwyn=Elfen, Ghalta=Stompy, Vorinclex=+1/+1-Zähler). **Selbstkorrektur
während der Recherche:** Lathril, Blade of the Elves wurde zunächst aus
einer WebFetch-Zusammenfassung fälschlich als mono-grüner Top-Elfen-
Commander übernommen, per Gegenprüfung aber als Golgari (Schwarz/Grün)
identifiziert und durch die echt mono-grüne Marwyn ersetzt.

**Befund:** alle 5 Flavors bestätigen (mit 5 weiteren unabhängigen
Belegen) 0 Wipes/0 Stax-Disruption/0 Sac-Drain für Grün. Echte
Interaktionsdichte ist durchgängig sehr niedrig (~2%, nur Beast Within),
außer bei Elfen und Stompy, wo sie sich real verdoppelt bis verdreifacht
(~4,8%) — ein Flavor-Unterschied, den die reine Farb-Ebene nicht abbilden
würde. Nur 5 von 25 möglichen Matrix-Zellen ließen sich real belegen
(Ramp→Midrange, Landfall→Midrange, Elfen→Horde, Stompy→Aggro,
Zähler→Midrange) - für "control"/"goldfish" fand sich in keinem der 5
echten Decks ein Beleg, konsistent mit Grüns bekanntem Fehlen echter
Kontroll-Werkzeuge. Vollständige Matrix, Dichte-Tabellen und
State-Function-Werte je belegter Zelle (als Kalibrierungs-KANDIDATEN
gekennzeichnet, nicht sofort übernommen) siehe
Docs/green_flavor_strategy_matrix_pilot_v4_47_0.md.

**Bewusst KEINE Code-/Gewichtsänderung in dieser Version** — reiner
Format-/Methodik-Pilot, der erst mit dem Nutzer abgestimmt wird, bevor er
auf die restlichen 4 Monofarben und 10 Zweifarb-Identitäten ausgeweitet
wird. Tests: keine Code-Änderung - volle Testsuite unverändert grün
(615/615, 1 vorbestehender, unveränderter Skip).

## v4.46.0 — Moxfield-Methodik + Orzhov-Runde 2: Pro-Deck-Lifegain-Synergieerkennung statt Gilden-Kreuzterm

**Auftrag:** Fortsetzung von Punkt 2 nach dem v4.45.0-Pilotversuch. Diesmal:
Moxfield (statt/zusätzlich zu EDHREC) als Quelle für beliebte/echte
Spielerdecks nutzen, Stichprobe auf 10 Decks pro Sub-Strategie erhöhen, auf
Bracket 2+3 beschränken, danach dieselbe Tiefe auf Gruul und Izzet
übertragen, die Gegnerfunktion mit den Ergebnissen trainieren, und das
Vorgehen so dokumentieren, dass es sich selbstständig auf weitere Gilden
übertragen lässt. Auf explizite Nachfrage (da "10 pro Sub-Strategie" über 3
Gilden hinweg 60-150+ Decks bedeuten würde) hat der Nutzer "wörtlich 10 pro
Sub-Strategie" gewählt und dabei selbst bestätigt, dass dies nicht in einem
Durchgang abschließbar ist — diese Version deckt daher nur Orzhov ab.

**Kritischer technischer Befund:** Moxfields Decklisten sind nur über einen
echten, JavaScript-ausführenden Browser erreichbar (WebFetch liefert nur
die leere SPA-Ladehülle; die interne API ist per robots.txt gesperrt). Mit
dem in dieser Sitzung verbundenen Browser klappte der Zugriff (nach
einmaligem Ablehnen des EU-Cookie-Consent-Dialogs pro Browser-Profil) -
ABER nach ca. 15-18 Abrufen innerhalb weniger Minuten begannen praktisch
ALLE weiteren Anfragen sitzungsweit dauerhaft zu hängen (auch die
Moxfield-Startseite selbst) - ein bislang unbekanntes Rate-Limit/eine
Ressourcenerschöpfung, klar unterscheidbar von einzelnen toten/privaten
Decks (die sofort 404 oder für genau eine URL dauerhaft leer bleiben).
Nebenbefund: "meistkommentiert" ist auf Moxfield praktisch kein nutzbares
Kriterium (nur 2 von 14 untersuchten Decks hatten überhaupt einen
Kommentar); die Decks mit dem höchsten Engagement (Views/Likes) hatten in
dieser Stichprobe durchgängig hohe Bracket-Werte (5 echte Game-Changer),
lagen also außerhalb der Bracket-2/3-Zielgruppe - ein echter Zielkonflikt.
Vollständige, wiederverwendbare Methodik (inkl. Schritt-für-Schritt-
Workflow für künftige Gilden) siehe
Docs/opponent_model_moxfield_methodology_v4_46_0.md.

**Inhaltlicher Befund:** Aristokraten-Sub-Strategie (Teysa Karlov) jetzt an
5 unabhängigen echten Decks (4 neue von Moxfield + 1 EDHREC-Bestandsdeck
aus v4.45.0) geprüft - 5 von 5 zeigen Schwarz durchgängig selbstgenügsam
(eigene Opferausgänge UND eigene Drain-Payoffs), KEINE unidirektionale
Weiß→Schwarz-Abhängigkeit. Lebenspunkte-Drain-Sub-Strategie jetzt an 3
unabhängigen echten Commandern geprüft (Karlov of the Ghost Council/Kambal
aus v4.45.0 + neu Vito, Thorn of the Dusk Rose per EDHREC, da die
Moxfield-Recherche für diese Sub-Strategie dem o.g. Rate-Limit zum Opfer
fiel) - 2 von 3 zeigen die echte Weiß-Quelle→Schwarz-Payoff-Abhängigkeit,
der dritte (Vito) erreicht denselben Sanguine-Bond/Exquisite-Blood-Payoff
komplett selbstgenügsam über schwarze Lifelink-Vampire, ganz ohne Weiß.
**Schlussfolgerung: selbst innerhalb einer sauber abgegrenzten
Sub-Strategie ist die Cross-Color-Abhängigkeit commander-/build-abhängig,
nicht einmal sub-strategie-weit garantiert** - ein weiterer, noch engerer
statischer Kreuz-Term (nach dem in v4.45.0 bereits verworfenen
gilden-weiten) wäre also ebenfalls die falsche Form der Lösung.

**Umgesetzte Konsequenz ("Training" der Gegnerfunktion):** statt eines
weiteren statischen Eintrags in `Data/Models/opponent_state_weights.json`
wurde ein neues, additives Diagnose-Modul ergänzt, das die Erkenntnis
PRO GETESTETEM DECK statt pro Gilde/Sub-Strategie operationalisiert -
`App/synergy_profile/classifier.py` (neu): erkennt aus dem echten
Oracle-Text eines Decks, ob es einen "whenever you gain life"-Payoff
enthält (Sanguine Bond, Vito, Cliffhaven Vampire, Bloodchief Ascension -
alle real per WebSearch/WebFetch verifiziert) und ob dessen Lifegain-Quelle
(z. B. Soul Warden) aus einer ANDEREN Farbe stammt (echte Cross-Color-
Abhängigkeit) oder das Deck farblich selbstgenügsam ist. Additiv in
`_opponent_model_cross_check` (v4.44.0) eingehängt als neues Feld
`lifegain_synergy_profile` - ändert kein bestehendes Simulationsergebnis.
Offengelegte Lücke: Lifelink (Schlüsselwort statt Fließtext) wird NICHT als
Lifegain-Quelle erkannt - genau die Mechanik, mit der Vitos reales
Average-Deck seine Selbstgenügsamkeit erreicht; bewusst als Lücke
ausgewiesen statt geraten.

**Tests:** 13 neue Tests (`tests/test_synergy_profile.py`, 12 Tests, echter
Oracle-Text von Soul Warden/Sanguine Bond/Vito/Cliffhaven Vampire/Exquisite
Blood; plus 1 neuer Integrationstest in
`tests/test_opponent_model_cross_check.py`) - volle Suite 615/615 grün (1
vorbestehender, unveränderter Skip).

**Offen für Folgeversionen:** Gruul und Izzet auf derselben Tiefe (0 Decks
diese Runde - komplett verschoben, siehe Methodik-Dokument für die
Begründung und den direkt anwendbaren Workflow); die Aristokraten-
Stichprobe blieb bei 5 statt 10 Decks; die in v4.45.0 identifizierten
Reanimator/Board-Wipe-Control- und "praktisch-mono-schwarz"-Sub-Strategien
wurden diese Runde nicht vertieft.

## v4.45.0 — Orzhov-Tiefenrecherche (Pilotversuch zu Punkt 2, keine Code-/Gewichtsänderung)

**Auftrag:** statt der bisherigen 1-Deck-pro-Gilde-Methodik exemplarisch für
EINE Gilde (Orzhov, WB - gewählt wegen der bereits in v4.41.0 offengelegten
Cross-Dimension-Synergie-Lücke) so viel echte Information wie sinnvoll
zusammentragen, um zu prüfen, wie die Ergebnisqualität dabei ausfällt und
ob sich die Synergie-Lücke damit bestimmen lässt.

**Vorgehen:** 5 echte, bewusst UNTERSCHIEDLICHE Orzhov-Commander-
Durchschnittsdecks von EDHREC (Teysa Karlov/Aristokraten, Karlov of the
Ghost Council/Lebenspunkte-Voltron, Kambal Consul of Allocation/Tax-
Control, Yahenni Undying Partisan/Aristokraten-Edikt, Athreos Shroud-
Veiled/Reanimator-Wipe-Control) vollständig abgerufen, jede Karte gegen die
53-Karten-Game-Changers-Liste geprüft und einzeln nach Farbe/Mechanik
klassifiziert.

**Kernbefund:** die ursprüngliche v4.41.0-Hypothese ("Weiß füttert über
Token-Erzeugung Schwarz' Opferschleifen-Drain") ist zu grob - real zeigt
sich bei Teysa Karlov eine BEIDSEITIGE Verstärkung statt eines
unidirektionalen Gefälles (Schwarz erzeugt in der echten Liste genauso
eigenes Fallmaterial: Bitterblossom, Ophiomancer, Sifter of Skulls). Ein
ANDERES, SAUBERERES Muster taucht stattdessen in 2 von 5 Decks auf (Karlov
of the Ghost Council, Kambal): Weiß liefert dichte reine
Lebenspunkte-Trigger (Soul Warden, Guide of Souls, Daxos u. a.), Schwarz/WB
konvertiert sie in Schaden/Kartenvorteil (Sanguine Bond, Exquisite Blood,
Vito, Sheoldred the Apocalypse, Debt to the Deathless). Yahenni erwies sich
im echten Aggregat als praktisch MONO-SCHWARZ (28× Swamp, kein Plains) -
keine nennenswerte Cross-Color-Synergie trotz WB-Farbidentität. Athreos
zeigte gar kein Aristokraten-/Drain-Muster (Reanimator-/Wipe-Shell
stattdessen). Zusatzbefund: Bracket-Streuung sogar innerhalb einer Gilde
(4× Bracket 3, 1× Bracket 2 bei Yahenni/0 Game Changer) - bestätigt
konkret, dass ein Ein-Deck-Beleg pro Gilde (wie in v4.41.0) durch Zufall
1-2 Bracket-Stufen daneben liegen kann.

**Antwort auf die Bestimmbarkeits-Frage:** teilweise ja (ein präziseres,
staerker belegtes Muster wurde gefunden), teilweise nein (es gibt KEINE
einzelne "Orzhov-Zahl" - welches Muster (wenn überhaupt) auftritt, hängt
von der Sub-Strategie ab, nicht von der Farbidentität allein; ein
gildenweiter Fix wäre die falsche Lösungsform).

**Aufwand:** ca. das 5-fache an Prüfaufwand gegenüber der bisherigen
1-Deck-pro-Gilde-Kalibrierung - für nur eine von 10 Zweifarb-Gilden; eine
gleich tiefe Prüfung aller 10 wäre ein realistischer ~10-facher
Gesamtaufwand.

**Bewusst KEINE Code-/Gewichtsänderung in dieser Version** - reiner
Bestimmbarkeits-Pilotversuch, drei offene Optionen fürs weitere Vorgehen
dokumentiert (nur das sauberste Teilmuster jetzt umsetzen / weitere Gilden
auf derselben Tiefe prüfen / hier stehen bleiben). Volle Herleitung in
`Docs/opponent_model_orzhov_deep_dive_v4_45_0.md`.

**Tests:** keine Code-Änderung - volle Testsuite unverändert grün
(602/602, 1 vorbestehender, unveränderter Skip).

## v4.44.0 — Punkt 3 (Engine-Integration): additiver Opponent-Model-Cross-Check + neuer Permanenttyp-Entfernungs-Klassifikator

**Auftrag:** Nachdem v4.43.0 die Punkte 1, 4, 5, 6 abgearbeitet hatte, wurde
für Punkt 3 (App/opponent_model ist seit v4.38.0 nicht in die echte
Zugschleife von App/engine.py eingebunden) die angekündigte Rückfrage
gestellt: vollständiger Ersatz des bestehenden `OPPONENT_PROFILES`-Systems,
additiver Cross-Check, schrittweise Migration, oder Zurückstellen? Antwort:
**additiver Cross-Check** (kleinster, risikoärmster Schritt - bestehendes
System bleibt vollständig unverändert aktiv).

**Zwischenbefund vor der Umsetzung:** die ursprüngliche, in
`state_equation.py`s Moduldoc (v4.40.0, "Iteration 3") formulierte Annahme,
"App/engine.py verfolgt die Entfernungs-Breite des getesteten Decks bereits
an anderer Stelle", stimmt bei genauer Prüfung NICHT: es existiert zwar ein
generischer `"removal"`-Wertetag im Goldfish-Value-Model (nur für die
Kartenbewertung, keine Permanenttyp-Aufschlüsselung) und ein separates
`removal_type`-Konzept (destroy/exile/bounce/tuck - aber das beschreibt, WIE
der ABSTRAKTE GEGNER die Permanents des GETESTETEN Spielers entfernt, also
die entgegengesetzte Richtung), aber KEINE echte "kann dieses Deck ein
Artefakt/eine Verzauberung/einen Planeswalker/ein Land entfernen"-
Klassifikation für die getestete Decklist. Dieser Fund wurde dem Nutzer vor
der Umsetzung transparent gemeldet (mit einer zweiten Rückfrage zum
dadurch vergrößerten Umfang) - Antwort: **neue Klassifikation bauen.**

**Neu: `App/removal_profile/classifier.py`** - ordnet einer echten Karte
(`Card.oracle_text`, aus Scryfall, nie erfunden) zu, welche der 5
Permanenttyp-Buckets (Artefakt/Verzauberung/Kreatur/Planeswalker/Land) sie
per Destroy/Exile/Bounce beantworten kann. Methodik: Mustererkennung anhand
ECHTER, standardisierter Magic-Textbausteine ("Destroy target X.", "Exile
target X.", "Return target X to its owner's hand.") statt einer
handkuratierten Kartenliste - z. B. wurde die exakte Formulierung "destroy
target artifact or enchantment" während der Recherche als reale,
standardisierte Textvorlage bestätigt, die 130+ gedruckte Karten teilen
(Gatherer-Regeltext-Suche). Bewusst offengelegte Lücken (lieber ein echtes
Unterzählen als ein erfundenes Übertreffen): Opfer-/Edikt-Effekte
("sacrifices a creature") werden NICHT erkannt (Risiko falscher Treffer
durch Eigenopfer-Kosten zu hoch für diesen ersten Durchgang); reiner
Schadens-basierter Kreaturen-Tod ("deals 4 damage to target creature") wird
NICHT erkannt (kein Destroy/Exile-Verb, keine Sterbeschwelle erfunden).
23 neue Tests (`tests/test_removal_profile.py`) gegen echte, verifizierte
Kartentexte (u. a. Vindicate, Beast Within, Assassin's Trophy, Anguished
Unmaking, Utter End, Cyclonic Rift, Disenchant, Nature's Claim, Return to
Dust, Swords to Plowshares, Path to Exile, Vandalblast).

**Der eigentliche Cross-Check** (`App/engine.py::_opponent_model_cross_check`,
angehängt an `run_pipeline_v440`): baut 30 unabhängige, rein synthetische
`OpponentState`-Verläufe auf (je so viele Züge wie der echte Lauf, mit einer
EIGENEN, vom echten Spiel-RNG komplett unabhängigen `random.Random`-Instanz
- `state_equation.py` hängt ohnehin nur von Strategie/Farbe/Bracket/Zugzahl
ab, nie vom echten Spielzustand, kann also als reiner Seiten-Durchlauf
laufen), mittelt `query_board_effects()` über alle 30 Samples und vergleicht
das Ergebnis mit `deck_removal_coverage()` des getesteten Decks. Jeder
Permanenttyp, für den der simulierte Gegner spürbaren Bestand aufbaut (≥
0.15, ein reasonierter, nicht gemessener Schwellenwert), das Deck aber laut
Klassifikator KEINE Entfernung dafür besitzt, wird als `coverage_gaps`-
Eintrag gemeldet. Bracket fest auf 3 (Referenzniveau) und Gegnerfarben leer
gelassen, da `App/engine.py` aktuell weder ein Bracket- noch ein
Gegnerfarb-Konzept kennt - offengelegte Vereinfachung, kein gemessener Wert.
Ein "random"-Gegnerprofil fällt ebenfalls auf "midrange" zurück (ebenfalls
offengelegt). Ergebnis landet als eigene `opponent_model_cross_check.json`
im Ergebnisordner UND als `summary["opponent_model_cross_check"]` im
zurückgegebenen Python-Objekt - **bestehende Dateien
(`summary.json`, `analysis_overview.json`, `runs.csv` usw.) werden an
KEINER Stelle verändert**, und der Cross-Check ist in einen `try/except`
gekapselt, der einen eigenen Fehler niemals die eigentliche
Ergebnisauslieferung gefährden lässt.

**Tests** (`tests/test_removal_profile.py` 23 neue, `tests/
test_opponent_model_cross_check.py` 7 neue, gesamt jetzt 602): u. a.
reproduzierbar bei gleichem Seed, ein Deck mit "Destroy target permanent."
(Vindicate) meldet nie eine Lücke, ein Deck ganz ohne Entfernung meldet bei
`control`-Strategie zuverlässig mindestens eine Lücke, `goldfish` (alle
Wachstumsraten 0.0) meldet nie eine Lücke, die übergebene Deckliste wird
nicht verändert. Volle Testsuite vor und nach dieser Version grün
(602/602, 1 vorbestehender, unveränderter Skip).

**Weiterhin offen:** Punkt 2 (Gilden-Cross-Dimension-Synergie) unverändert.
Diese Version ist bewusst nur der additive Cross-Check, kein Ersatz des
bestehenden `OPPONENT_PROFILES`-Systems - die Frage, ob/wann ein tieferer
Umbau sinnvoll ist, bleibt für später offen.

## v4.43.0 — Offene Punkte 1-6 abgearbeitet: `disruption_lockout_by_type`, Kombo-Audit-Korrektur, Bracket-1-Recherche, Halbwertszeit-Recherche (ergebnislos)

**Auftrag:** Der Nutzer bat, die in v4.42.0 zusammengestellten sechs offenen
Punkte selbstständig abzuarbeiten, mit der ausdrücklichen Erlaubnis, bei
einer echten Vorgehensentscheidung eine offene Frage oder Antwortoptionen
zu stellen. Für Punkt 6 (Halbwertszeit-Multiplikatoren) wurde zusätzlich um
eine gezielte Recherche gebeten: über Vorab-Einträge, Gameplan-
Beschreibungen und Berichte realer gespielter Partien prüfen, ob sich
`impact_half_life_multiplier` irgendwie belegen lässt - falls nicht, wurde
eine mögliche künftige numerische Zwischensimulation (Interaktions-
verfügbarkeit/Handwahrscheinlichkeit je Bracket, abgeglichen mit
Kartenstärke) als denkbarer, aber nicht in dieser Version zu bauender
Zwischenschritt benannt.

**Punkt 1 - `unmapped_persistent_disruption` geschlossen:** neue dritte
verfallende Zustandsgröße `OpponentState.disruption_lockout_by_type`,
gleicher Wachstum-plus-Halbwertszeit-Mechanismus wie
`passive_value_by_type`/`sac_drain_by_type` (v4.40.0), aber ein eigenes,
BREITERES Permanenttyp-Bucket-Set
(`DISRUPTION_PERMANENT_TYPE_BUCKETS = artifact/enchantment/creature/
planeswalker/land`) statt des bestehenden 3er-Sets - notwendig, weil 2 der 9
betroffenen Game Changer keine der drei bisherigen Typen sind: Narset,
Parter of Veils ist ein Planeswalker, The Tabernacle at Pendrell Vale ein
Land (beide via scrollvault.net/guides/game-changers.html verifiziert). Neue
Farbverteilung der 9 Karten (ebenfalls dort verifiziert): Schwarz 4, Weiß 3,
Blau 3, Rot 0, Grün 0 - daraus abgeleitet: `disruption_growth` neu in allen
5 `strategy_curves` (control am höchsten, ECHT belegt durch Zur the
Enchanter/Esper aus der v4.42.0-Dreifarb-Stichprobe, die gleich zwei der 9
Karten führte: Drannith Magistrate + Opposition Agent) sowie in den
`color_modifiers` von W/U/B (nicht R/G, da keine der 9 Karten rot oder grün
ist). `permanent_type_half_life_turns` um `planeswalker` (6 Züge) und `land`
(12 Züge, am längsten - Landzerstörung ist am Commander-Tisch die seltenste
und oft unerwünschteste Entfernungsart) ergänzt, `permanent_type_distribution
.disruption_lockout` exakt aus der 9-Karten-Permanenttyp-Zählung (6 Kreatur,
je 1 Verzauberung/Planeswalker/Land) abgeleitet.
`Data/Models/game_changer_archetypes.json` (v1.1): alle 9 Karten von
`feeds: "unmapped_persistent_disruption"` auf `feeds:
"disruption_lockout_by_type"` umgetagged. Neue Testklasse
`DisruptionLockoutTests` (8 Tests) plus Erweiterung von 4 bestehenden
Struktur-/Konsistenztests.

**Punkt 4 - Kombo-Audit dreier zuvor als unklar markierter Grenzfälle
(commanderspellbook.com):**

- **Izzet/Niv-Mizzet, Parun (v4.41.0): ECHTER, bislang übersehener Fehler
  gefunden und korrigiert.** Die reale EDHREC-Decklist führt neben
  Niv-Mizzet, Parun auch **Curiosity** - ein bei commanderspellbook.com
  verifizierter 2-Karten-Infinite-Combo (genutzt in 67.575 realen
  EDHREC-Decks). Nach dem offiziellen Regelwerk macht bereits EIN
  2-Karten-Combo ein Deck automatisch zu Bracket 5 - Izzet war also fälschlich
  Bracket 4 statt 5. Korrigiert in `Docs/opponent_model_calibration_v4_41_0.md`
  (samt Korrekturhinweis) und oben in diesem Dokument. Kein rückwirkender
  Effekt auf bestehende Gewichte (die Einzeldeck-Klassifikation fließt nicht
  direkt als Zahl in `state_equation.py`/`opponent_state_weights.json` ein,
  sondern nur in die Bracket-Verteilungs-AUSSAGEN im Fließtext).
- **Dimir/Yuriko, the Tiger's Shadow (v4.41.0): bestätigt korrekt Bracket 4.**
  commanderspellbook.com liefert für keine Kombination aus Yurikos
  Decklisten-Karten einen 2-Karten-Combo - keine Korrektur nötig.
- **Abzan/Karador, Ghost Chieftain (v4.42.0): kein Bracket-Wechsel, aber eine
  Nebenbeobachtung.** Karmic Guide + Reveillark allein bilden KEINEN
  2-Karten-Combo (commanderspellbook.com bestätigt kein solches Paar), erst
  zu dritt mit Viscera Seer entsteht ein echter, verifizierter Combo. Da
  Karador bereits unabhängig davon über die Game-Changer-Zahl korrekt
  Bracket 3 war, ändert das die Einordnung nicht - hier nur zur
  Vollständigkeit festgehalten, kein 3-Karten-Combo-Audit war Teil dieses
  Durchgangs.

Dieser Fund bestätigt eine bereits mehrfach offengelegte Einschränkung: die
bisherigen Bracket-Einordnungen (v4.39.0-v4.42.0) beruhten auf der
Game-Changer-Zahl PLUS Mass-Land-Destruction-/Extra-Turn-Prüfung, aber
KEINEM systematischen 2-Karten-Combo-Audit über alle 30 Belegdecks hinweg.
Dieser Durchgang prüfte gezielt nur die 3 zuvor selbst als unklar markierten
Grenzfälle, nicht alle 30 Decks neu - ein vollständiger Combo-Audit über die
gesamte Stichprobe bleibt ein offener, potenziell noch weitere Korrekturen
liefernder Punkt (z. B. wurde Dimir mit 6 Game Changern nur stichprobenartig,
nicht vollständig geprüft - siehe Korrekturhinweis in
`opponent_model_calibration_v4_41_0.md`).

**Punkt 5 - Bracket 1 ("Exhibition"): echte Regelwerk-Evidenz gefunden, aber
strukturell KEINE Decklisten-Dichte-Evidenz möglich.** EDHREC führt einen
offiziellen "Adapting Your Decks to the Exhibition Bracket 1"-Guide
(edhrec.com/articles/adapting-your-decks-to-the-exhibition-bracket-1) sowie
einen allgemeinen Brackets-Guide (edhrec.com/guides/edhrec-guide-to-
commander-brackets). Beide bestätigen die bestehenden Code-Annahmen für
Bracket 1: keine Game Changer, keine Mass Land Destruction, keine
Extra-Turn-Karten, keine 2-Karten-Combos erlaubt, UND wörtlich "games
expected to last at least nine turns before anyone wins or loses" - eine
reale, zitierfähige Bestätigung, dass Bracket 1 spürbar langsamer/schwächer
laufen MUSS als die bestehenden `power_multiplier`/`variance_multiplier`-
Werte für Bracket 1 bereits unterstellen (0.55/1.40 - beide bereits die
schwächste/schwankendste Stufe aller 5 Brackets).

Der wichtigere strukturelle Befund: EDHREC's eigenes Bracket-1-Arbeitsbeispiel
(Lumra, Bellow of the Woods, Bär-Tribal) zeigt, dass EDHREC's eigenes
"Average Deck"-Aggregat für Lumra selbst 5 echte Game Changer enthält -
also GENAU DIE Kategorie von Decklisten (populäre EDHREC-Average-Aggregate),
die dieses Projekt für JEDE bisherige Bracket-Einordnung (v4.39.0-v4.42.0)
verwendet hat, kann Bracket 1 strukturell NICHT abbilden. Bracket 1 verlangt
bewusste Spieler-Zurückhaltung/Absicht beim Deckbau (explizit gebannte
Kartenkategorien nicht spielen, obwohl sie einem zur Verfügung stünden) -
etwas, das eine popularitätsgewichtete Aggregation von "was Leute tatsächlich
einbauen" per Definition nicht erfassen kann. Es existiert also kein Weg,
über die bisherige Methodik (echte EDHREC-Average-Decks je Farbidentität) an
eine Bracket-1-Belegdeckliste zu kommen - `opening_mana_boost`=0.0 und
`impact_half_life_multiplier`=1.0 für Bracket 1 bleiben unverändert reine,
durch das REGELWERK (nicht durch eine Decklist) plausibilisierte
Platzhalterwerte. Punkt 5 bleibt damit ein offener, aber jetzt zumindest
regelwerks-fundierter statt völlig unbelegter Punkt.

**Punkt 6 - `impact_half_life_multiplier`: Recherche nach Draft-/Pick-Logs,
Gameplan-Beschreibungen und echten Partieberichten ergebnislos.** Gezielt
gesucht nach jeder Form von Beleg, wie viele Züge ein Permanent an einem
echten Commander-Tisch tatsächlich überlebt, bevor es beantwortet wird
(Voraussetzung für eine gemessene statt reasonierte Halbwertszeit): weder
Turnier-Datenbanken noch Content-Ersteller-Spielberichte noch Foren-
/Reddit-Diskussionen veröffentlichen turn-genau geloggtes Material dieser
Art - was existiert, sind ausschließlich subjektive Ratgeber-Artikel
("spiele deine Bomben früh/spät" etc.), keine zählbaren Rohdaten. Dieses
Ergebnis bestätigt lediglich, was bereits in v4.41.0 offen zugegeben wurde
(die Werte 1.0/1.0/0.9/0.75/0.6 sind reasoniert, nicht gemessen) - es ändert
nichts an Code oder Gewichten.

Genau wie vom Nutzer selbst vorgeschlagen, bleibt die Alternative - eine
eigenständige NUMERISCHE Zwischensimulation, die Interaktionsverfügbarkeit/
Handwahrscheinlichkeit je Bracket gegen Kartenstärke abgleicht und daraus
eine grobe, simulierte Halbwertszeit ableitet - ein möglicher, aber
BEWUSST NICHT in dieser Version gebauter künftiger Zwischenschritt. Er
würde eine eigene, von der Haupt-Engine unabhängige Simulationslogik
brauchen (kein triviales Gewichts-Update) und wird hier nur als Kandidat
dokumentiert, nicht umgesetzt.

**Punkte 2 und 3 - weiterhin offen, absichtlich nicht in dieser Version
bearbeitet:**

- **Punkt 2 (Gilden-Cross-Dimension-Synergie, Orzhov/Izzet):** unverändert -
  bräuchte mehrere Belegdecks pro Gilde für eine verantwortbare Kalibrierung
  (siehe v4.41.0), nicht Teil des in dieser Version verlangten
  Punkte-1-bis-6-Umfangs.
- **Punkt 3 (Engine-Integration):** unverändert der gewichtigste offene
  Punkt gemessen am ursprünglichen Nutzerziel - `App/opponent_model` ist
  seit v4.38.0 weiterhin vollständig eigenständig und nicht in
  `App/engine.py`s echte Zugschleife verdrahtet. Das bestehende
  `OPPONENT_PROFILES`/`apply_abstract_opponent_phase`-System in
  `App/engine.py` ist bereits ein real funktionierendes, mehrfach
  überschriebenes System (Last-Definition-Wins-Architektur, u. a. mit
  seed­basierter Interaktion, Tuck-Effekten und verzögerter Blink-Auflösung) -
  eine Integration ist damit eine echte Architekturentscheidung und keine
  reine Ergänzung. Da dies eine "explizite Frage zum weiteren Vorgehen" im
  Sinne des Nutzerauftrags ist, wird sie separat gestellt, statt hier ohne
  Rückfrage eine Richtung vorwegzunehmen.

**Versionsstände:** `ENGINE_VERSION`/GUI-Titel 4.42.0 → 4.43.0,
`opponent_state_weights.json` 1.4 → 1.5, `game_changer_archetypes.json`
1.0 → 1.1.

**Tests** (`tests/test_opponent_model.py`, 8 neue Tests in der neuen Klasse
`DisruptionLockoutTests`, gesamt jetzt 572): volle Testsuite vor und nach
dieser Version grün (572/572, 1 vorbestehender, unveränderter Skip).

## v4.42.0 — "Iteration 5" (Teil 1): Offene-Punkte-Review + 10 echte Dreifarb-Decklisten, Bracket-Heuristik verfeinert

**Auftrag:** Der Nutzer bestätigte die bisherige Sample-Größe (2 Decks/
Monofarbe, 1 Deck/Zweifarb-Gilde) als ausreichend für jetzt, mit einer
tieferen Neukalibrierung erst als "Updateaufgabe hinten raus", sobald die
Mechanik vollständig steht und ins Design integriert ist. Danach bat er,
offene Punkte durchzugehen und - falls nichts dagegenspricht - direkt in
"Iteration 5" tiefer in die verbleibenden Farbidentitäten einzusteigen (die
zwei-/einfarbigen Fälle ausgenommen).

**Offene-Punkte-Review** (nichts davon blockiert Iteration 5 - alle sind
unabhängige, bereits offengelegte, bewusst vertagte Lücken):

1. **`unmapped_persistent_disruption`** (v4.40.0): 9 der 53 Game Changers
   (Braids, Drannith Magistrate, Grand Arbiter Augustin IV, Humility,
   Narset Parter of Veils, Notion Thief, Opposition Agent, Tergrid, The
   Tabernacle at Pendrell Vale) haben noch keine eigene Zustandsdimension.
2. **Gilden-Synergie-Lücke** (v4.41.0): Orzhov-Opferdrain über
   weiße Token-Fütterung, Izzet-Kartenvorteil über Spellslinger-Tempo -
   cross-dimensionale Effekte, die das Pro-Farbe-Pro-Dimension-Modell nicht
   abbildet.
3. **Die eigentliche, vom Nutzer selbst benannte Motivation für die
   Permanenttyp-Bindung** - der Abgleich zwischen dem simulierten Gegner-
   Board (`query_board_effects`) und der tatsächlichen Entfernungs-Breite des
   GETESTETEN Decks - ist weiterhin NICHT gebaut. Das gesamte
   `opponent_model`-Modul bleibt seit v4.38.0 bewusst eigenständig und ist
   noch nicht in `App/engine.py`s echte Zugschleife verdrahtet (in jeder
   Versions-Moduldoc als "separater, späterer Integrationsschritt"
   offengelegt). Das ist der gewichtigste offene Punkt gemessen am
   ursprünglichen Nutzerziel.
4. Kein vollständiger 2-Karten-Kombo-Audit (seit v4.39.0 offengelegt) -
   Bracket-4/5-Grenzfälle bleiben Ermessensentscheidungen.
5. Bracket 1 ("Exhibition") hat über alle 30 bislang klassifizierten
   Decks hinweg KEINEN einzigen echten Beleg - `opening_mana_boost` und
   `impact_half_life_multiplier` sind dort reine Platzhalterwerte.
6. `impact_half_life_multiplier`-Größenordnungen bleiben reasoniert, nicht
   Decklisten-gemessen (v4.41.0, dort bereits offengelegt).

Keiner dieser Punkte hindert die Fortsetzung der Farbidentitäts-Recherche -
sie bleiben als Kandidaten für künftige Iterationen dokumentiert.

**Iteration 5, Teil 1 - 10 echte Dreifarb-Decklisten (Wedges/Shards):**
gleiche Methodik wie v4.41.0 (1 EDHREC-Average-Deck je Identität, per
Game-Changers-Regelwerk in echte Brackets eingeordnet). Ergebnis: Bant/Rafiq
of the Many (1 GC, Bracket 3), Esper/Zur the Enchanter (10 GC, Bracket 5),
Grixis/The Scarab God (1 GC, Bracket 3), Jund/Korvold Fae-Cursed King (4 GC,
Bracket 4), Naya/Marath Will of the Wild (2 GC, Bracket 3), Abzan/Karador
Ghost Chieftain (1 GC, Bracket 3), Jeskai/Kykar Wind's Fury (5 GC, Bracket
4), Sultai/Muldrotha the Gravetide (4 GC, Bracket 4), Mardu/Alesha Who
Smiles at Death (0 GC, Bracket 2), Temur/Yidris Maelstrom Wielder (1 GC,
Bracket 3).

**Diese Version ändert bewusst KEINE Gewichtszahl.** Jeder Befund bestätigte
das bestehende multiplikative Farbmodell, statt eine Lücke aufzudecken:
Esper (WUB, alle drei Farben mit hohem `passive_value_growth`) zeigte die
dichteste Passive-Value-/Stax-Häufung der GESAMTEN bisherigen Stichprobe
(vorhergesagter Multiplikator 2.01 - der höchste bislang berechnete Wert);
Jund (BRG, Korvold) bestätigte zum DRITTEN Mal (nach mono-Schwarz und
Orzhov) Schwarz als robust opferdrain-tragende Farbe unabhängig vom
Partner. Aus nur einem Beleg-Deck pro Identität neue Zahlen abzuleiten, wäre
keine verantwortbare Kalibrierung gewesen - reine Bestätigung wird hier
bewusst NICHT in eine (unnötige) Gewichtsänderung übersetzt.

**Eine echte, evidenzbasierte Verfeinerung der Klassifikationsheuristik** (für
künftige Kalibrierungsrunden, kein Code in `state_equation.py`): Zur the
Enchanter liefert mit 10 Game Changern und OHNE auffällige Ritual-/
Opferaltar-Häufung einen sauberen Beleg, dass ab etwa 7 Game Changern ein
Deck unabhängig von einem Zusatzsignal als Bracket 5 gilt - die v4.39.0-Regel
verlangte diese Zusatzhäufung bislang immer. Keine der 29 anderen bisherigen
Klassifikationen ändert sich dadurch rückwirkend.

**Stand der Farbidentitäten:** 25 von 32 abgedeckt (5 mono + 10 zweifarbig +
10 dreifarbig). Verbleibend offen: 5 vierfarbige, 1 fünffarbige, 1 farblose
Identität - dort ist auf EDHREC deutlich weniger Deck-Population zu
erwarten, was offen benannt wird, sobald diese Runde ansteht. Volle Tabelle
und Herleitung in `Docs/opponent_model_calibration_v4_42_0.md`.

**Tests:** keine Code-/Verhaltensänderung in dieser Version - volle
Testsuite unverändert grün (564/564, 1 vorbestehender, unveränderter Skip),
zur Bestätigung vor UND nach dieser Version erneut ausgeführt.

## v4.41.0 — Gegner-Zustandsmodell "Iteration 3b"/beginnende "Iteration 4": LSV-Recherche + Halbwertszeit-Verfeinerung, erste Zweifarb-Gilden-Kalibrierung

**Auftrag, Teil 1:** Der Nutzer bat darum, beim Training bezüglich Bracket/
Farbe/Strategie auf die offizielle LSV-(Luis-Scott-Vargas-)Bewertungsskala
Bezug zu nehmen, um daraus die Halbwertszeit von Karten abzuschätzen, und den
Gedanken iterativ zu vertiefen.

**Recherche-Ergebnis (ehrlich, nicht wie erhofft direkt nutzbar):** Die
LSV-Skala ist ein pro-Set FRISCH vergebenes Limited-Draft-Bewertungssystem
(z. B. "S: lächerliche Bombe" bis "F: unspielbar"), keine universelle
Datenbank mit einer Bewertung für jede jemals gedruckte Karte. Für alte oder
reine Constructed-/Commander-Staples wie Mana Vault, Necropotence oder
Rhystic Study existiert schlicht keine LSV-Zahl zum Nachschlagen - das wurde
per WebSearch/WebFetch verifiziert (u. a. anhand eines echten Limited-Set-
Review-Beispiels, das die Skala explizit als "primarily a Draft review"
beschreibt). Eine Pro-Karte-LSV-Zahl zu verwenden, wäre daher eine Erfindung
gewesen und widerspricht der eigenen Projekt-Konvention - das wird an keiner
Stelle im Code getan.

**Was stattdessen trägt:** das der Nutzer-Recherche zugrunde liegende, von
LSV unabhängige Prinzip - das "Threat Relevance"/"Dies to Removal"-
Paradoxon: hoher Karten-Einfluss → schnelle Antwort/kurzes Board-Leben,
niedriger Einfluss → wird ignoriert, überlebt lange. Da dieses Projekt genau
EIN echtes, regelverifiziertes "Bomben-Tier"-Signal besitzt (Mitgliedschaft
in der 53-Karten-Game-Changers-Liste) und dessen Dichte bereits nachweislich
mit dem Bracket korreliert, wird das Paradoxon auf BRACKET-Ebene angewendet:
neues `bracket_scaling.<bracket>.impact_half_life_multiplier`
(1.0/1.0/0.9/0.75/0.6 für Bracket 1-5) verkürzt die effektive Halbwertszeit
von `passive_value_by_type`/`sac_drain_by_type` bei höherem Bracket, über
`_impact_half_life_multiplier()` in `state_equation.py`. Die Werte sind
reasonierte Schätzwerte (kein Zug-genau geloggtes Spielmaterial vorhanden,
um sie exakt zu belegen) - offen als solche gekennzeichnet, keine
verschleierte Präzision.

**Auftrag, Teil 2:** Training auf alle Farbkombinationen erweitern, mit dem
Ziel von 50 Decks je Bracket × Farbidentität × Strategie, ohne dass der
Nutzer selbst etwas heraussuchen muss.

**Ehrliche Machbarkeits-Einschätzung:** 32 Farbidentitäten × 5 Brackets ×
mehrere Strategien × 50 Decks wäre eine Größenordnung von mehreren Tausend
einzeln zu beschaffenden, echten Decklisten - in einem Durchgang nicht ohne
entweder Erfindung von Zahlen oder einen mehrsitzungsübergreifenden Aufwand
leistbar. Diese Version macht stattdessen den nächsten, zur v4.39.0-Monofarb-
Runde proportionalen Schritt: **alle 10 Zweifarb-Gilden, je eine echte
EDHREC-Average-Deck-Liste** (bekannter Commander, konventionelle Strategie
je Gilde), per Game-Changers-Regelwerk in echte Brackets eingeordnet -
genauso wie beim Monofarb-Durchgang.

**Bracket-Verteilung der 10 Gilden-Decks:** Bracket 2 (Golgari/Meren, 0 Game
Changer), Bracket 3 (Rakdos, Gruul, Selesnya, Orzhov, Simic - je 1-3 Game
Changer), Bracket 4 (Azorius, Dimir, Izzet, Boros - je 4-6 Game Changer)¹ -
bestätigt, dass die Game-Changer-Zahl-basierte Bracket-Klassifikation ohne
Änderung auf Zweifarb-Decks generalisiert.

¹ **Korrigiert in v4.43.0:** Izzet/Niv-Mizzet, Parun ist tatsächlich Bracket
5 (echter, verifizierter 2-Karten-Combo mit Curiosity, beim ursprünglichen
Kombo-Audit hier übersehen) - siehe Docs/README.md v4.43.0 und den
Korrekturhinweis in `Docs/opponent_model_calibration_v4_41_0.md`.

**Bestätigung:** das bestehende multiplikative Farbmodell (zwei
Farb-Multiplikatoren pro Dimension werden schlicht multipliziert) hält im
Kern - Azorius (WU, beide Farben mit hohem `passive_value_growth`) zeigte
tatsächlich die dichteste Passive-Value-Engine-Häufung der gesamten
Stichprobe.

**Neue, bewusst NICHT geschlossene Lücke gefunden:** zwei Gilden zeigten eine
Dichte, die das rein pro-Farbe-pro-Dimension multiplikative Modell nicht
vorhersagen würde, weil die reale Synergie eine ANDERE Dimension in der
JEWEILS ANDEREN Farbe anzapft: Orzhov (WB, Teysa Karlov) hatte die dichteste
Opfer-/Aristokraten-Drain-Häufung der gesamten bisherigen Stichprobe -
dichter noch als das mono-schwarze Referenzdeck -, obwohl Weiß selbst kein
`sac_drain_growth`-Gewicht trägt (Weiß liefert hier das Fallmaterial/Token,
nicht den Drain-Effekt selbst). Izzet (UR, Niv-Mizzet Parun) zeigte
ungewöhnlich dichten Kartenvorteil, obwohl Rot kein
`passive_value_growth`-Gewicht trägt (Spellslinger-Tempo befeuert
Kartenvorteil). Beide sind reale, aber aus nur EINEM Beleg-Deck pro Gilde
nicht verantwortbar kalibrierbare Cross-Dimension-Synergien - als Kandidat
für eine mögliche künftige "Iteration 5" offen dokumentiert statt aus dünner
Evidenz in ein Gewicht gegossen. Volle Deck-Tabelle, Dichte-Belege und alle
Einschränkungen in `Docs/opponent_model_calibration_v4_41_0.md`.

**Tests** (`tests/test_opponent_model.py`, 2 neue Tests, gesamt jetzt 564):
`impact_half_life_multiplier` wird nachweislich aus der Gewichtsdatei pro
Bracket gelesen (gültiger Bereich 0 < x ≤ 1.0), und ein identischer
Anfangsbestand zerfällt bei Bracket 5 nachweislich schneller als bei
Bracket 2 unter sonst gleichen Bedingungen. Die "jedes deklarierte Bracket-
Feld wird auch gelesen"-Strukturtests wurden um das neue Feld erweitert.
Volle Testsuite grün (564/564, 1 vorbestehender, unveränderter Skip).

## v4.40.0 — Gegner-Zustandsmodell "Iteration 3": generalisierte, permanenttyp-gebundene Effekt-Bestände mit Halbwertszeit + Game-Changer-Archetyp-Tagging

**Auftrag:** direkte Fortsetzung von v4.39.0. Der Nutzer schlug vor, die zwei
dort bewusst offengelassenen Lücken (passive Value-/Tax-Engines; schwarze
Opfer-/Aristokraten-Drain-Schleifen) NICHT über einzelne Kartenmodelle zu
schließen, sondern über generische, an einen Permanenttyp (Artefakt/
Verzauberung/Kreatur) gebundene Effekt-"Bestände" mit einer Halbwertszeit
statt einer festen Dauer (weil das Modell keine Interaktion ZWISCHEN den
simulierten Gegnern selbst abbildet). Auf Nachfrage stellte der Nutzer klar:
die Permanenttyp-Bindung dient in erster Linie NICHT einer "Tischpolitik"-
Begründung der Halbwertszeit, sondern soll perspektivisch einen Abgleich
ermöglichen, ob das GETESTETE Deck genug Interaktion/Entfernung für genau
den Permanenttyp mitbringt, der bei einem simulierten Gegnertyp typischerweise
liegen bleibt (dieser Abgleich selbst ist nicht Teil dieser Version). Der
Nutzer bat danach ausdrücklich darum, sowohl (a) die neuen Bestände zu bauen
als auch (b) alle 53 Game Changers in Wirk-Archetypen einzuordnen, beides
selbstständig und ohne weitere manuelle Zuarbeit des Nutzers.

**(a) Zwei neue, generalisierte Zustands-Bestände:**
`OpponentState.passive_value_by_type` und `OpponentState.sac_drain_by_type`,
je ein Dict über die Buckets `artifact`/`enchantment`/`creature`. Beide
zerfallen JEDEN Zug über eine bucket-spezifische Halbwertszeit
(`Data/Models/opponent_state_weights.json::permanent_type_half_life_turns`:
Kreatur 4, Artefakt 7, Verzauberung 9 Züge - kürzer für Kreaturen, weil
Kreatur-Entfernung im Format am dichtesten vorkommt) und wachsen pro Zug in
einen per Gewichtsverteilung gewürfelten Bucket
(`permanent_type_distribution`: passive Value fällt überwiegend auf
Verzauberungen/Artefakte, Opfer-Drain überwiegend auf Artefakte/Kreaturen -
abgeleitet aus den Permanenttypen der jeweils dafür getaggten echten
Game-Changer-Karten, siehe (b)). Neuer Keyword-Parameter `table_size`
(Default 4) an `advance_opponent_state()`: skaliert NUR das
passive-Value-Wachstum (mehr Mitspieler = wertvollere Rhystic-Study-artige
Engine), NICHT das Opfer-Drain-Wachstum (typischerweise gezielt gegen einen
Spieler, nicht automatisch tischgrößenabhängig) - eine bewusste, durch einen
eigenen Test abgesicherte Asymmetrie. Neue rein lesende Query-Funktion
`query_board_effects()` für beide Bestände. Farbe-/Strategie-Gewichte
(`passive_value_growth`, `sac_drain_growth` in `strategy_curves` und
`color_modifiers`) wurden aus der bestehenden 10-Decks-Stichprobe (v4.39.0)
plus der neuen Game-Changer-Klassifikation abgeleitet, NICHT aus einer neuen
Decklisten-Erhebung - volle Herleitung mit allen Einschränkungen in
`Docs/opponent_model_calibration_v4_40_0.md`.

**(b) Game-Changer-Archetyp-Tagging:** neue Datei
`Data/Models/game_changer_archetypes.json` ordnet alle 53 verifizierten
Game Changers (siehe v4.39.0-Eintrag für die Quellenverifikation) je einem
von 8 Wirk-Archetypen (fast_mana, tutor_consistency, draw_engine, wipe,
protection, combo_piece, alt_win_condition, disruption) und genau einer
bestehenden oder neuen Zustandsdimension zu, auf die sie einzahlt. Diese
Datei wird zur Laufzeit NICHT von `state_equation.py` gelesen - reines
Kalibrierungs-/Analyse-Hilfsmittel für künftige Decklisten-Audits.

**Neu gefundene, noch offene Lücke (dritte, in dieser Version NICHT
geschlossen):** Beim Tagging fiel auf, dass 9 der 53 Game Changers (Braids
Cabal Minion, Drannith Magistrate, Grand Arbiter Augustin IV, Humility,
Narset Parter of Veils, Notion Thief, Opposition Agent, Tergrid God of
Fright, The Tabernacle at Pendrell Vale) stehende, STATISCHE Stax-/
Hemm-Effekte sind, die weder zur reaktiven `interaction_availability` noch
zu den beiden neuen Draw-/Drain-Beständen passen - sie verwehren dem Tisch
dauerhaft eine Option, statt Kartenvorteil oder Lebenspunkte-Drain zu
erzeugen. Diese 9 Karten wurden explizit auf ein neues, noch NICHT als
Zustandsdimension gebautes `feeds`-Ziel `unmapped_persistent_disruption`
getaggt statt sie in eine schlecht passende Kategorie zu zwingen - ein
Kandidat für eine mögliche künftige "Iteration 4" (eigene
Restriktions-/Denial-Dimension).

**Tests** (`tests/test_opponent_model.py`, 17 neue Tests, gesamt jetzt 562):
neue Klasse `PassiveValueAndSacDrainTests` (10 Tests) prüft Start-bei-Null,
die Farbe-/Strategie-Rangordnung beider Bestände, die
Tischgrößen-Asymmetrie, den Halbwertszeit-Zerfall (inklusive
"Kreatur-Bucket zerfällt schneller als Verzauberungs-Bucket"), die
statistische Bucket-Verteilung von `_pick_permanent_type` über 2000
Durchläufe sowie `query_board_effects` als rein lesend und
nicht-aliasing. Neue Klasse `GameChangerArchetypesFileTests` (7 Tests)
prüft die neue JSON-Datei gegen die unabhängig im Test selbst hinterlegte
Liste der 53 verifizierten Namen (exakte Übereinstimmung), gültige
Archetyp-/Feeds-/Permanenttyp-Werte für jeden Eintrag, dass jede
Draw-/Drain-Karte tatsächlich einen Permanenttyp hat, und dass genau 9
Karten als `unmapped_persistent_disruption` markiert sind. Kein neuer
Implementierungsfehler wurde diesmal gefunden - volle Testsuite grün
(562/562, 1 vorbestehender, unveränderter Skip).

**Ausdrücklich offengelegte Grenzen dieser Version:** die
Halbwertszeit-Werte und die Bucket-Verteilungsprozente sind fachliche
Schätzungen aus bekannten Kartenbeispielen, keine Auszählung eines
vollständigen Kartenpools (anders als die auf echten Deck-Dichten
beruhenden Farbe-Multiplikatoren aus v4.39.0); die neu gefundene
`unmapped_persistent_disruption`-Lücke bleibt offen; der geplante
Abgleich zwischen simulierten Gegner-Permanenttypen und der
Entfernungs-Breite des getesteten Decks ist vorbereitet (Typ-Bindung
existiert), aber noch nicht gebaut.

## v4.39.0 — Gegner-Zustandsmodell "Iteration 2": Kalibrierung an 10 echten Decklisten + zwei geschlossene Lücken

**Auftrag:** Der Nutzer bat um genau den in v4.38.0 selbst angekündigten
nächsten Schritt: zunächst prüfen, ob sich reale Karten überhaupt in die
Zustandsgleichung eingliedern lassen oder ob diese noch Lücken hat, und
danach die Gewichte anhand echter, online verfügbarer Decklisten (zunächst
nur Monofarbe) trainieren.

**Vorgehen:** 10 echte Decklisten von EDHREC ("Average Deck"-Aggregate, kein
erfundenes Beispiel) besorgt - je eine Bracket-2/3-Liste ("Budget") und eine
Bracket-4/5-Liste ("Expensive") pro Monofarbe, mit einer für die Farbe
kanonischen Strategie: mono-R Krenko, Mob Boss (Aggro), mono-W Giada, Font
of Hope (Aggro), mono-U Lier, Disciple of the Drowned (Control), mono-B
Endrek Sahr, Master Breeder (Aristokraten, hier als Midrange-Variante
behandelt), mono-G Azusa, Lost but Seeking (Ramp, ebenfalls als
Midrange-Variante behandelt - die bestehende Strategie-Taxonomie kennt
weder "Aristokraten" noch "Ramp" als eigene Kategorie; dies ist eine
offengelegte, nicht stillschweigende Vereinfachung). Jede Liste wurde NICHT
anhand ihres Quellen-Labels, sondern anhand des echten Bracket-Regelwerks
eingeordnet: die offizielle 53-Karten-"Game Changers"-Liste wurde direkt von
`magic.wizards.com` abgerufen und gegen zwei unabhängige Spiegel-Quellen
(playgroup.gg, scrollvault.net) auf Übereinstimmung geprüft (eine erste,
einzelne Abfrage hatte abweichende/zusätzliche Karteneinträge geliefert und
wurde deshalb verworfen).

**Bracket-Einordnung der 10 Decks** (Anzahl gefundener Game-Changer-Karten):
Krenko-Budget 0, Giada-Budget 0, Endrek-Budget 0 → Bracket 2. Lier-Standard
3 (Cyclonic Rift, Rhystic Study, Mystical Tutor), Azusa-Standard 2 (Gaea's
Cradle, Crop Rotation) → Bracket 3 (innerhalb des Bracket-3-Limits "bis zu
3"). Krenko-Expensive 5, Giada-Expensive 4, Lier-Expensive 4, Azusa-Expensive
5 → Bracket 4. Endrek-Expensive 5 plus auffällig dichte
Tutor-/Ritual-/Opferaltar-Häufung (Demonic Tutor, Vampiric Tutor, Imperial
Seal, Necropotence, Bolas's Citadel, Ashnod's Altar UND Phyrexian Altar
gemeinsam) → Bracket 5. In keiner der 10 Listen wurde Mass Land Destruction
oder eine Extra-Turn-Karte gefunden; ein vollständiger 2-Karten-Kombo-Audit
war nicht Teil dieses Durchgangs (offengelegte Einschränkung der
Bracket-Einordnung).

**Zwei echte, belegte Lücken gefunden und geschlossen:**

1. **Turn-1-Fast-Mana-Sprung:** JEDE der vier "Expensive"-Listen (alle
   Farben außer Schwarz, dort sogar noch dichter) fügte gegenüber ihrem
   günstigeren Gegenstück einen Cluster expliziter Turn-1-Mana-Beschleuniger
   hinzu (Ancient Tomb, Mana Vault, Chrome Mox, Jeweled Lotus, Lotus Petal,
   Ashnod's/Phyrexian Altar), der in KEINER der günstigeren Listen auch nur
   einmal vorkam. Das bestehende `mana_growth` bildet nur stetiges
   Wachstum ab, keinen einmaligen Sprung. Neu:
   `bracket_scaling.<bracket>.opening_mana_boost`, einmalig in Zug 1
   angewendet (`state_equation.py::advance_opponent_state`) - 0.0 für
   Bracket 1-3 (durch 5 der 10 echten Listen belegt), 0.12 für Bracket 4
   (durch 4 Listen belegt), 0.22 für Bracket 5 (durch 1 Liste belegt, daher
   unsicherer).
2. **Fehlende Kombo-/Alternativsieg-Dimension:** Die Game-Changer-Dichte
   sprang scharf nach Bracket (0-2 Karten bei Bracket ≤3, 4-5+ bei Bracket
   ≥4 in JEDER einzelnen der 10 Listen) - das reale Bracket-System bildet zu
   einem großen Teil genau das ab, was v4.38.0 überhaupt nicht modellierte.
   Neu: `OpponentState.combo_finish_readiness` plus
   `strategy_curves.*.combo_growth`, hart gegatet auf Bracket ≥
   `GUARDRAIL_COMBO_MIN_BRACKET` (4) UND Zug ≥ Kombo-Mindestzug-Guardrail
   (3) - exakt dasselbe doppelte Hard-Floor-Muster wie beim bestehenden
   Wipe-Guardrail, aus demselben Grund (kein manipuliertes Gewicht darf
   einen frühen Kombo-Sieg erzwingen). `CastabilityQuery.has_combo_finish`
   als neues, ebenfalls rein lesendes Abfragefeld ergänzt.

**Zwei weitere Lücken bewusst NICHT geschlossen, sondern offen
dokumentiert** (kleine Stichprobe, jede würde eine echte neue Mechanik statt
nur Gewichts-Tuning brauchen): passive Value-/Tax-Engines ohne diskretes
"Karte ziehen"-Ereignis (Rhystic Study, Smothering Tithe, Sylvan Library,
Necropotence); Schwarz' Opfer-/Aristokraten-Drain-Schleifen (Ashnod's Altar
+ Phyrexian Altar + Death-Trigger) als eigener Lebenspunkte-Druckvektor
getrennt von Kampf und Spot-Removal.

**Kalibrierung bestehender Gewichte anhand echter Dichteverhältnisse**
(gezählter Anteil an Nicht-Land-Slots je Kategorie, kein erfundener
Präzisionswert): `color_modifiers.U.interaction_availability` von 1.35 auf
1.45 angehoben (Lier zeigte 17-25 % Interaktions-/Gegenzauber-Dichte,
deutlich über den 3-11 % der anderen vier Farben);
`color_modifiers.G.mana_growth` von 1.20 auf 1.30 angehoben (Azusa zeigte
15-20 % Ramp-Dichte, gleichmäßig über beide Machtstufen, der höchste Wert
aller fünf Farben). `color_modifiers.W`/`R` unverändert gelassen - die
echten Daten bestätigten die v4.38.0-Erst-Schätzwerte, statt sie zu
widerlegen. Neu ergänzt: `color_modifiers.U.combo_finish_readiness`=1.15
und `color_modifiers.B.combo_finish_readiness`=1.20 (Thassa's Oracle +
Laboratory Maniac bei Lier; Yawgmoth + doppelte Opferaltar-Präsenz bei
Endrek-Expensive).

**Ausdrücklich weiterhin nur eine kleine, gerichtete Stichprobe** (2 echte
Decks pro Farbe = 10 insgesamt, nicht "viele Decks pro Bracket pro Farbe")
- das vom Nutzer selbst benannte, umfassendere Trainings-/Kalibrierungsziel
über viele Decks bleibt ein separater, weiterer Schritt.

**Tests** (`tests/test_opponent_model.py`, 11 neue Tests, gesamt jetzt 545):
`opening_mana_boost` wird nachweislich nur in Zug 1 angewendet und wirkt
für Bracket 4/5 tatsächlich höher als für Bracket 1-3; `combo_finish_readiness`
bleibt exakt 0 unterhalb des Bracket- UND des Zug-Guardrails (auch bei
absichtlich manipulierten Gewichten), wächst aber sobald beide Schwellen
erreicht sind; `CastabilityQuery.has_combo_finish` ist nachweislich
wahrscheinlichkeitsbasiert und rein lesend; die bestehenden
"jedes deklarierte Gewicht wird auch gelesen"-Strukturtests wurden um die
drei neuen Felder erweitert. Ein Implementierungsfehler wurde dabei selbst
gefunden und behoben: der Kombo-Mindestzug-Helfer fiel mangels eines
`combo_min_turn`-Schlüssels in JEDER Strategie-Kurve auf einen
Default von 999 zurück (analog zum Wipe-Muster, wo 999 bei
aggro/horde/goldfish ausdrücklich "so gut wie nie" bedeutet) und blockierte
dadurch `combo_finish_readiness` versehentlich für ALLE Strategien
dauerhaft - Default auf 0 korrigiert, sodass allein der Guardrail (Zug ≥ 3)
greift, wenn keine Strategie-Kurve explizit einen höheren Wert setzt.

## v4.38.0 — Neues Modul: rudimentäres Gegner-Zustandsmodell (`App/opponent_model/`)

**Auftrag (Nutzer, wörtlich sinngemäß übersetzt):** Die bestehende
Gegnerabbildung (`OPPONENT_PROFILES` + `apply_abstract_opponent_phase`) ist
eine flache, pro Profil konstante Tabelle, die rein rundenschwellenbasiert
Schaden/Removal/Wipe auswürfelt - es gibt darin kein Konzept von einem
gegnerischen Board, einer Hand oder Manabasis, und auch kein Bracket-Konzept
(reales Commander-Bracket-System, verifiziert über
`mtg.wiki/page/Commander_Brackets`: 1 Exhibition, 2 Core, 3 Upgraded,
4 Optimized, 5 cEDH). Der Nutzer wollte stattdessen eine **einzige
Zustandsgleichung**, die für JEDEN Gegnertyp identisch aussieht, aber deren
GEWICHTUNG von Strategie, Farbe(n) und Bracket abhängt, echte Varianz
(tote Hände, Mana-Screw, suboptimale Runden) statt reiner
Erwartungswert-Rechnung abbildet, und an klar benannten Zeitpunkten
(Combat-Phase; jede "was ist castbar"-Prüfung, egal ob im eigenen oder im
gegnerischen Zug) abgefragt bzw. aktualisiert wird. Ausdrücklich NICHT Teil
dieser Version: Kalibrierung der Gewichte anhand realer, online verfügbarer
Decklisten - das ist der vom Nutzer selbst benannte nächste Schritt.

**Umsetzung** (`App/opponent_model/state_equation.py`, neues
"engine-agnostisches, ops-übergebenes" Modul nach dem etablierten Muster von
`App/combat_model/interaction.py` und `App/resource_planner/planner.py`,
Gewichte in `Data/Models/opponent_state_weights.json`):

- `OpponentProfile(strategy, colors, bracket)` - die drei vom Nutzer
  genannten Stellparameter (Bracket wird auf 1-5 geklemmt, unbekannte
  Farbbuchstaben werden verworfen).
- `OpponentState` - abstrakter, kartenunabhängiger Zustand: `life` und
  `cards_remaining` (die zwei vom Nutzer explizit genannten konkreten
  Werte), plus vier 0..1-Bereitschafts-Proxys (`board_presence`,
  `interaction_availability`, `wipe_readiness`, `mana_availability`,
  `hand_quality`) und ein `dead_turn`-Flag - bewusst NICHT einzelne Karten,
  sondern die Zustände, die Karten auf dem Board/gegen den Spieler auslösen
  können (siehe Nutzer-Vorgabe).
- `advance_opponent_state(state, profile, rng)` - EINE Funktion, EIN
  Codepfad für jedes Profil (per Test strukturell abgesichert: es gibt
  genau eine `advance_opponent_state*`-Funktion im Modul). Nur die
  Gewichte unterscheiden sich: eine Strategie-Kurve
  (`strategy_curves.<strategie>`), Farb-Multiplikatoren
  (`color_modifiers.<farbe>`, multiplizieren sich bei mehrfarbigen Gegnern),
  und eine Bracket-Skalierung (`bracket_scaling.<1..5>`: `power_multiplier`
  skaliert alle Wachstumsraten, `variance_multiplier` skaliert Varianz UND
  Tote-Runden-Wahrscheinlichkeit gemeinsam, `consistency_floor` ist eine
  Mindestkonsistenz für Mana/Hand-Qualität). Wird genau einmal pro
  simuliertem GEGNERZUG aufgerufen (das "Update").
- **Echte Varianz:** pro Zug EIN gemeinsamer, stetiger
  "wie lief die Runde"-Wurf (`variance_amplitude`, von Bracket gedämpft)
  PLUS ein separater, diskreter "tote Runde"-Bernoulli-Wurf
  (`dead_turn_chance_base`, ebenfalls Bracket- und Farb-gewichtet über
  `color_modifiers.*.dead_turn_chance`) - eine tote Runde dämpft das
  Wachstum aller Dimensionen fast auf null, löscht aber nicht bereits
  vorhandenes `board_presence` aus früheren Runden.
- **Wipe-Guardrail** (Nutzer-Vorgabe wörtlich: "Board-Wipes nie günstiger
  als ca. 4-5 Mana"): `wipe_readiness` bleibt exakt 0.0 vor Zug 4,
  hart über `GUARDRAIL_WIPE_MIN_TURN = 4` (Python-Konstante) UND
  `guardrails.wipe_min_turn_hard_floor` (JSON) erzwungen, jeweils per
  `max()` zusätzlich zu jeder `strategy_curves.*.wipe_min_turn` - selbst
  eine (versehentlich) auf 1 herunterkalibrierte JSON-Datei kann dieses
  Mindestalter nicht unterlaufen (eigener Regressionstest).
- `query_combat_state(state)` und `query_castable_state(state, rng)` - die
  vom Nutzer genannten Abfragepunkte (Combat-Phase; "was ist gerade
  castbar"), rein lesend (mutieren `state` nie), wahrscheinlichkeitsbasiert
  statt deterministischer Schwellenwert-Prüfung (derselbe Zustand kann bei
  zwei Abfragen unterschiedlich antworten).
- `life` wird von der Gleichung bewusst NICHT verändert - Kampf-/Lebens-
  punkteverluste bleiben Aufgabe des aufrufenden Engines/Kampfsystems; das
  Feld existiert hier nur, weil der Nutzer es explizit als zu trackenden
  Wert genannt hat.

**Bewusst offengelassen (dokumentierte, keine stille Vereinfachung):** Die
eigentliche Verdrahtung dieser Funktionen in `App/engine.py`s Zugschleife
(`attack_phase`, `apply_abstract_opponent_phase`, Castability-Prüfungen) ist
ein separater, späterer Integrationsschritt - dieses Modul steht für sich
und ist eigenständig vollständig getestet, exakt wie
`App/combat_model/interaction.py` es vorher auch war, bevor es in
`attack_phase` eingebunden wurde. Die Kalibrierung der Gewichte anhand
realer Decklisten ist, wie vom Nutzer selbst gefordert, ebenfalls nicht Teil
dieser Version - jede Zahl in `Data/Models/opponent_state_weights.json` ist
als Erst-Schätzwert ohne externe Referenzdaten gekennzeichnet.

**Tests** (`tests/test_opponent_model.py`, 25 neue Tests, gesamt jetzt 534):
Bracket-Klemmung/Farbfilterung; ein einzelner Gleichungs-Codepfad für alle
Strategien plus tatsächlich divergierendes Verhalten unter identischen
Zufallszahlen (aggro vs. control, goldfish bleibt bei 0); Bracket skaliert
Wachstum UND Mindestkonsistenz messbar hoch; Farb-Multiplikatoren wirken
einzeln und multiplikativ kombiniert; die Wipe-Guardrail hält auch gegen
absichtlich manipulierte Gewichte (JSON- UND Code-Ebene); Reproduzierbarkeit
bei gleichem Seed; eine tote Runde dämpft Wachstum nachweisbar; `life` bleibt
unangetastet; `cards_remaining` fällt nie unter 0; beide Query-Funktionen
sind nachweislich rein lesend und wahrscheinlichkeitsbasiert statt
deterministisch; und - nach dem `aliases`/`expects`-Fund aus v4.36.0 als
Lehre übernommen - ein struktureller Test, dass JEDES in der Gewichtsdatei
deklarierte Feld auch tatsächlich vom Code gelesen wird (kein totes
Tunable).

## v4.37.0 — Externe Code-Review (ChatGPT): "last-definition-wins" aufgeräumt (42 tote Funktionsdefinitionen entfernt)

**Ausgangslage:** `App/engine.py` folgt einer über viele Versionen gewachsenen
Konvention: statt eine bestehende Funktion in-place zu ändern, wurde oft
einfach ein weiteres `def name(...):` weiter unten in der Datei ergänzt -
Python behält pro Modul immer nur die LETZTE Definition eines Namens, alles
Frühere ist ab dem Moment der Neudefinition unerreichbar. ChatGPT kritisierte
das zu Recht als fragiles Muster. Vor dem Aufräumen wurde jede der 75
mehrfach definierten Top-Level-Funktionen einzeln per AST-Analyse (nicht nur
Text-Grep) klassifiziert, um zwei grundverschiedene Fälle zu trennen:

1. **Absichtliche Wrapper-Ketten** (46 Namen, z. B. `apply_payment`,
   `attack_phase`, `gain_life`): die ältere Version wird VOR der
   Neudefinition unter einem Alias-Namen gesichert (Muster
   `_V4xx_name_old = name`) und von der neuen Version aus explizit
   aufgerufen - der alte Code ist also bewusst weiter erreichbar und Teil
   der neuen Logik. Diese 46 Ketten wurden NICHT angefasst.
2. **Echter toter Code** (42 Definitionen über 38 Namen, 1123 Zeilen): eine
   frühere Definition wird schlicht überschrieben, ohne jemals irgendwo
   gesichert zu werden - ab dem Moment der Neudefinition zu 100 % nicht mehr
   aufrufbar, für immer. Vor dem Löschen wurde für jede dieser 42 Stellen
   zusätzlich per AST geprüft, dass keine Standardargument-Auswertung, kein
   Decorator, keine Klassenkörper-Zuweisung und keine sonstige
   Modul-Top-Level-Anweisung den alten Wert doch noch irgendwo einfängt (nur
   simple `x = name`-Zuweisungen zählen als Sicherung) - Aufrufe wie
   `gain_life(...)` INNERHALB anderer Funktionskörper zählen nicht, da
   Python solche Namen erst beim tatsächlichen Aufruf nachschlägt und dann
   ohnehin immer die letzte/lebende Definition trifft.

**Entfernt (38 Namen, 42 Definitionen, 1123 Zeilen):**
`_apply_semantic_protection_effect`, `_blink_creatures`,
`_find_semantic_payment`, `_pay_semantic_cost`, `_perm_ready`,
`_spot_remove_target`, `apply_abstract_opponent_phase`, `attack_phase`,
`cast_one_commander_v41`, `cast_option`, `check_win`, `end_step`,
`enrich_semantics`, `ensure_runtime_dependencies`, `find_payment`,
`gain_life`, `init_scenario_progress`, `keyword_set`, `load_scenarios`,
`load_strategy`, `move_permanent_to_zone`, `pay_additional_cost`,
`put_basic_from_library`, `run_pipeline_v43`, `save_scenarios`,
`scenario_cast_adjustment`, `scenario_package_cast_bonus`,
`scenario_preserve_untapped`, `scenario_requires_board_card`,
`scenario_requires_graveyard_spell`, `scenario_requires_hand_only`,
`scenario_run_rows`, `semantic_ability_score`, `try_cast_card`,
`try_cast_option`, `try_generic_semantic_activations`,
`update_scenario_progress`, `use_clue` (jeweils nur die toten
Zwischenversionen - die aktive letzte Definition jedes Namens ist
unverändert).

**Warum das sicher ist:** Da die entfernten Definitionen beweisbar nie
gebunden/aufgerufen wurden, kann ihr Entfernen das Programmverhalten nicht
ändern - Python hätte sie so oder so nie ausgeführt. Die volle Test-Suite
lief vor und nach dem Entfernen mit exakt demselben Ergebnis (505 Tests,
identisch grün), CLI-Smoke-Test (`--help`) und Modul-Import wurden zusätzlich
geprüft.

**Neue Absicherung:** `tests/test_no_dead_top_level_definitions.py` (4
Tests) portiert dieselbe AST-Analyse als dauerhaften Wächter - schlägt
namentlich fehl, sobald künftig wieder eine Funktion überschrieben statt
gesichert wird, statt die Datei stillschweigend weiter mit totem Code
wachsen zu lassen.

**Tests:** 505 -> 509 (die 4 neuen Struktur-Tests), alle grün.

## v4.36.0 — Externe Code-Review (ChatGPT): Keyword-Bibliothek war nicht wirklich deklarativ (`aliases`/`expects` folgenlos)

**Bug (bestätigt):** `App/keyword_library/registry.py` liest `aliases` und
`expects` aus `definitions.json` in jede `KeywordDefinition` ein - beide
Felder wurden aber NIRGENDS im Code tatsächlich gelesen/ausgewertet.
`aliases` steht zwar in jedem Eintrag als leere Liste bereit, hätte aber
selbst mit Inhalt nichts bewirkt. `expects` ist für alle 15 echten
Keyword-Einträge befüllt (z. B. `draw` -> `["amount"]`), beschrieb also
korrekt, welche Felder der jeweilige Handler braucht - wurde aber nie
geprüft, sodass ein zukünftiger Parser-Fehler (eine Aktion, die `amount`
vergisst zu setzen) den Handler stillschweigend mit einem wirkungslosen
Default aufgerufen hätte, ohne dass irgendwo ein Hinweis erscheint. Exakt
diese Fehlerklasse wurde in v4.26.0/v4.30.0 bereits für einzelne konkrete
Felder gefunden und behoben - dies schliesst den allgemeinen Fall.

**Fix:** `aliases` wird jetzt zu einem echten Alias-Index verarbeitet
(`_build_alias_index`) - `get_definition`/`is_known`/`resolve_action`
lösen einen alternativ benannten `action.kind` genau wie die kanonische
ID auf; eine Kollision mit einer echten ID gewinnt immer gegen einen Alias.
Kein Eintrag in der echten `definitions.json` nutzt aktuell Aliase, aber
der Mechanismus funktioniert jetzt tatsächlich für zukünftige Einträge
(z. B. eine neue Set-Karte mit alternativem Namen für einen mechanisch
identischen Keyword). `expects` wird jetzt in `resolve_action` GEPRÜFT: für
jedes erwartete Feld, das noch beim SemanticAction-Dataclass-Default steht
(vermutlich unbeabsichtigt statt echt Null), wird eine nicht-blockierende
Diagnose-Metrik (`keyword_expects_gap:<id>:<felder>`) aufgezeichnet - der
Handler wird trotzdem immer normal aufgerufen, es ändert sich also am
Verhalten bestehender, korrekt funktionierender Karten NICHTS.

**Tests:** `tests/test_keyword_library.py` um zwei Testklassen erweitert:
`KeywordAliasTests` (4 Tests, mit einer temporären, in `tearDown`
zurückgesetzten Registry, da `definitions.json` aktuell keine Aliase
enthält) und `KeywordExpectsGapDiagnosticTests` (4 Tests: fehlendes
`amount` löst eine Diagnose aus, führt den Handler aber trotzdem aus; ein
korrekt befülltes Feld löst keine Diagnose aus; `target` wird sowohl über
das String-Feld als auch über das aufgelöste Ziel-Objekt akzeptiert). Volle
Suite lief davor und danach unverändert grün. 505 Tests gesamt, alle grün.

## v4.35.0 — Externe Code-Review (ChatGPT): Hybridmana-Lücken (Farb-Zahlungspflicht falsch herum, Mehrfachauswahl-Manaquellen unvollständig)

**Bug 1 (bestätigt, betrifft reale Projekt-Karten):** `parse_mana_cost`
gab einem Zwei-Farben-Hybrid ohne generische Alternative (z. B. `{W/U}`)
GAR KEINE Farbanforderung mit - der reale Zahlungspfad
(`find_payment`/`payment_meets` behandelt `req` als harte
UND-Bedingung) hätte das also mit JEDER beliebigen Farbe (z. B. purem
Grün) bezahlen lassen, was nach den echten Regeln illegal ist. Konkret im
eigenen Scryfall-Cache nachgewiesen: Sokka, Lateral Strategist
(`{1}{W/U}{W/U}`), Kirol, Attentive First-Year (`{1}{R/W}{R/W}`),
Practiced Scrollsmith (`{R}{R/W}{W}`), Raph & Leo, Sibling Rivals
(`{1}{R/W}{R/W}`).

**Bug 2 (bestätigt, umgekehrte Richtung):** Ein einfarbiges Hybrid MIT
generischer Alternative (z. B. `{2/W}`) bekam eine ZWINGENDE Farbanforderung
(`req["W"] += 1`), obwohl `{2/W}` nach den echten Regeln immer mit 2
generischem Mana JEDER Farbe bezahlbar ist. Der reale Zahlungspfad hätte
also einen völlig legalen Zauberspruch fälschlich verweigert, sobald kein
weißes Mana verfügbar war - selbst mit genug generischem Mana. Kein
`{N/Farbe}`-Hybrid liegt aktuell im Projekt-Cache vor, aber der Mechanismus
ist real und wird hiermit vorsorglich mitgeschlossen.

**Fix:** Die beiden Hybrid-Formen werden jetzt unterschieden. Zahl+Farbe
(`{2/W}`-Form): keine Farbanforderung mehr, stattdessen wird der GENERISCHE
(teurere) Betrag zu `total` addiert - kann nie eine illegale Zahlung
zulassen und nie einen legalen Zauber blockieren, auf Kosten einer manchmal
zu hoch geschätzten Minimalkosten (die von dieser Funktion selbst
dokumentierte "konservative" Auslegung). Farbe+Farbe-Form (`{W/U}`-Form):
verlangt jetzt die ZUERST genannte Farbe (dieselbe Konvention, die die
Funktion bereits für den Einzelfarben-Fall kannte, nur nicht auf den
Mehrfarben-Fall angewendet hatte) - unvollkommen (ein Deck mit nur der
zweiten Farbe wird zu Unrecht blockiert), aber strikt korrekter als gar
keine Anforderung.

**Bug 3 (bestätigt):** `parse_add_mana_options` erkannte bei einer
kommagetrennten Auswahl-Liste mit 3+ Optionen ("Add {W}, {U}, or {B}." -
das klassische Triome-Land-Muster) nur die ERSTE Option; die anderen beiden
wurden stillschweigend verworfen (die bisherige "X or Y"-Regex deckte nur
genau 2 Optionen ab, danach griff die Kontiguierte-Symbole-Regex, die nur
das erste `{...}` direkt nach "Add " nimmt). Kein Triome-Land liegt aktuell
im Projekt-Cache vor, aber das Muster ist real und in Commander verbreitet.

**Fix:** Neue Regex erkennt eine kommagetrennte "X, Y, ..., or Z"-Liste
beliebiger Länge und erzeugt für jede genannte Farbe eine eigene
Wahlmöglichkeit - vor der alten Kontiguierte-Symbole-Regex geprüft, damit
deren erstes Symbol nicht doppelt/falsch übernommen wird. 2-Optionen-Listen
und feste Mehrfach-Symbol-Ausgaben (`Add {C}{C}`, `Add {G}{W}`) bleiben
unverändert korrekt.

**Tests:** neue Datei `tests/test_hybrid_mana_parsing.py` (12 Tests):
`{W/U}`/`{R/W}` verlangen jetzt eine echte Farbe (inkl. End-to-End über
`payment_meets`, das eine reine-Grün-Zahlung ablehnt); `{2/W}` hat keine
Farbanforderung mehr (inkl. End-to-End, das eine reine-generische-Zahlung
akzeptiert); Phyrexian-Mana (`{W/P}`) bleibt unverändert; 3- und
4-Optionen-Listen liefern jetzt alle Optionen, 2-Optionen-Listen und feste
Mehrfach-Symbol-Fälle bleiben unverändert. Volle Suite lief davor und
danach unverändert grün - kein bestehender Test hing vom alten,
fehlerhaften Verhalten ab. 497 Tests gesamt, alle grün.

## v4.34.0 — Externe Code-Review (ChatGPT): Doppel-Karten waren gleichzeitig beide Kartentypen

**Bug (bestätigt, betrifft bereits Karten im eigenen Scryfall-Cache):**
`card_from_scryfall` bildete `type_line` per
`obj.get("type_line") or " // ".join(...)`. Scryfall liefert für JEDE Karte
mit `card_faces` (Transform-DFCs, modale DFCs UND Adventure-Karten) bereits
auf oberster Ebene die kombinierte "Vorderseite // Rückseite"-Zeile - der
Fallback-Join wurde also nie erreicht. `Card.is_creature`/`is_sorcery`/
`is_planeswalker`/etc. sind reine Substring-Prüfungen auf `type_line`, also
war JEDE Karte mit `card_faces` das ganze Spiel über gleichzeitig BEIDE
Kartentypen. Konkret im eigenen Scryfall-Cache nachgewiesen: "Glóin the
Mighty // Easy Pickings" (Adventure-Karte, Vorderseite Kreatur/Rückseite
Hexerei) galt zugleich als `is_creature=True` UND `is_sorcery=True`. Der
schwerwiegendste Fall (komplett verschiedene Kartentypen wie bei Nicol
Bolas, the Ravager // Nicol Bolas, the Arisen: Kreatur- // Planeswalker-
Rückseite) ist in keinem aktuell im Cache liegenden Deck vorhanden, aber
exakt dieselbe Ursache.

**Fix:** `card_from_scryfall` verwendet jetzt bei vorhandenen `card_faces`
gezielt die `type_line` der VORDERSEITE (`f0`) statt der kombinierten
Zeile - genau die Seite, die tatsächlich im Spiel liegt/gecastet wird
(dieselbe Konvention, der `power`/`toughness`/`loyalty`/`defense` bereits
über ihren eigenen `f0`-Fallback folgen). `oracle_text` bleibt unverändert
kombiniert (wird u. a. für Battle-Rückseiten-Belohnungen gebraucht).

**Tests:** neue Datei `tests/test_dfc_card_type_line.py` (4 Tests): das
reale Projekt-Cache-Objekt "Glóin the Mighty // Easy Pickings" ist nur noch
`is_creature`, nicht mehr zusätzlich `is_sorcery`; ein evidenzbasiertes
Nicol-Bolas-Fixture (Vorderseite/Rückseite-Werte gegen Scryfall/mtg.wtf
verifiziert) ist nur noch `is_creature`, nicht mehr `is_planeswalker`, und
`card.loyalty` bleibt `None` statt von der Rückseite zu lecken;
`oracle_text` bleibt nachweislich weiterhin kombiniert; eine normale
einseitige Karte (Sol Ring) ist unverändert. Volle Suite (alle bestehenden
Tests inkl. `card_from_scryfall`-Nutzern) lief davor und danach unverändert
grün - kein bestehender Test verliess sich auf das alte, fehlerhafte
Verhalten. 485 Tests gesamt, alle grün.

## v4.33.0 — Externe Code-Review (ChatGPT): Blasphemous Acts ECHTER Kartentext bekam keinen Rabatt

**Bug (bestätigt, per Scryfall-Recherche verifiziert):** Der reale
Oracle-Text von Blasphemous Act lautet "This spell costs {1} less to cast
for each creature **on the battlefield**." - NICHT "for each creature you
control", wie es das eigene Test-Fixture in
`tests/test_boardwipe_payment_path.py` (und mehrere Docstring-Kommentare in
`App/engine.py`) bisher unterstellten. `_count_self_scaling_condition`
erkannte "creature" nur in Kombination mit dem Substring "you control" -
der echte Kartentext fiel also durch JEDEN Zweig durch und landete beim
finalen `return 0`. Das eigene Regressionstest-Fixture "funktionierte" nur,
weil es zufällig die falsche (nicht-reale) Formulierung verwendete - ein
klassischer "Tautologie-Fallstrick" (Test und Implementierung teilen
denselben blinden Fleck), wie von ChatGPT in der externen Review konkret
benannt.

**Fix:** `_count_self_scaling_condition` erkennt jetzt sowohl "you control"
als auch "on the battlefield" für die Kreatur-/Artefakt-Zählung (dieses
Goldfish-Modell führt ohnehin kein separates Gegner-Board, `state.battlefield`
enthält nur die eigenen Permanents - beide Formulierungen zählen also
identisch). Alle betroffenen Docstrings (`boardwipe_effective_cost_estimate`,
`boardwipe_self_scaling_discount`) korrigiert, damit sie nicht länger die
falsche Formulierung als "die klassische Blasphemous-Act-Regel" zitieren.

**Tests:** `tests/test_boardwipe_payment_path.py`s Fixture
`BLASPHEMOUS_ACT_SHAPED_TEXT` auf den echten Wortlaut korrigiert; neue
Testklasse `BlasphemousActRealWordingTests` (3 Tests) pinnt den EXAKTEN,
per Scryfall verifizierten Oracle-Text wörtlich fest (Rabatt-Erkennung,
leeres Baord -> kein Rabatt, End-to-End durch `cast_option` inkl. echtem
Payment-Pfad); zusätzlicher Test `test_you_control_wording_still_works_too`
stellt sicher, dass die alte Formulierung weiterhin erkannt wird. 481 Tests
gesamt, alle grün.

## v4.32.0 — Externe Code-Review (ChatGPT): Resource Planner - `future_value` invertiert & `max_units` verbrauchte zu viele freie Ressourcen

**Bug 1 (bestätigt):** `plan_allocation` (`App/resource_planner/planner.py`)
sortierte kostenpflichtige Ressourcen nach `opportunity_cost - future_value`.
`future_value` ist laut eigener Feld-Dokumentation "der Wert, die Ressource
NICHT auszugeben" - also selbst ein zusätzlicher KOSTENFAKTOR beim Ausgeben,
kein Rabatt darauf. Durch die Subtraktion bekam eine Ressource mit hohem
`future_value` (sehr wertvoll, wenn man sie behält) einen künstlich
NIEDRIGEN Sortierschlüssel und wurde dadurch fälschlich als "günstigste"
Option zuerst ausgegeben - exakt umgekehrt zu dem, was das Feld bedeuten
soll. In der einzigen echten Integration (`maybe_use_waterbend`) blieb der
Fehler bisher folgenlos, weil dort nie ein `future_value != 0.0` gesetzt
wird (siehe Docstring-Verweis auf `tests/test_resource_planner.py` für den
Fall, in dem es etwas ändert) - das Modul ist aber laut eigenem Docstring
für zukünftige Integrationen (Convoke, Improvise, Crew, Equip) vorgesehen,
in denen `future_value` echt befüllt werden dürfte.

**Bug 2 (bestätigt):** Im selben Loop wurde `used_resources = list(free) +
chosen_costly` unabhängig davon gebildet, ob `Action.max_units` die
tatsächlich nutzbaren `units` unter die Summe der freien Ressourcen
gedeckelt hat. Ein Plan mit `max_units=4` bei 10 freien Ressourcen meldete
(und in der echten Engine-Integration tatsächlich TAPPTE, siehe
`maybe_use_waterbend`s `for r in plan.used_resources: tap_permanent(...)`)
alle 10 statt nur der 4 tatsächlich benötigten Ressourcen. In der aktuellen
Waterbend-Integration ist `max_units` immer `None`, daher bisher folgenlos
- aber ein echter Bug für jede künftige Integration mit hartem
Maximalwert (z. B. Crew N, Equip-Auswahl).

**Fix:** Sortierschlüssel auf `opportunity_cost + future_value` geändert
(Bug 1). Vor dem Erstellen des `AllocationPlan` wird jetzt aus der freien
Liste nur so viel entnommen, wie `units` tatsächlich benötigt (frühzeitiger
Abbruch, sobald die Teilsumme `units` erreicht) - `chosen_costly` bleibt
unverändert, damit `attackers_lost`/`value` weiterhin exakt zu dem `k`
passen, das `goal_fn` tatsächlich bewertet hat (Bug 2).

**Tests:** `tests/test_resource_planner.py` um zwei Testklassen erweitert:
`FutureValueIsACostNotADiscountTests` (eine teure, aber "wertvoll zu
behaltende" Ressource darf nicht vor einer strikt günstigeren ausgegeben
werden) und `MaxUnitsDoesNotOverConsumeFreeResourcesTests` (ein auf 4
Einheiten gedeckelter Plan mit 10 freien Ressourcen nutzt/meldet genau 4;
der Trim betrifft nachweislich nur die freie Liste, nicht die gewählten
kostenpflichtigen Ressourcen). 477 Tests gesamt, alle grün.

## v4.31.0 — Externe Code-Review (ChatGPT): Selbstziel-Text ("this creature") landete auf einer anderen Kreatur

**Bug (bestätigt):** `_semantic_target_creature` (`App/engine.py`) hat die
Quelle (`source`) IMMER aus den Kandidaten ausgeschlossen, sobald
irgendeine andere Kreatur auf dem Feld stand - unabhängig davon, was der
Fähigkeitstext tatsächlich sagt. Damit landete z. B.
`{T}: Put a +1/+1 counter on this creature.` auf einer FREMDEN Kreatur
(der mit dem höchsten `generic_tutor_score`), sobald mindestens eine
andere Kreatur im Spiel war - der Zähler ging also nie auf die Kreatur,
die ihn laut Kartentext eigentlich bekommen sollte.

**Fix:** `_semantic_target_creature` bekommt jetzt den Rohtext der
Aktion/Fähigkeit übergeben und nutzt die bereits bestehende
`text_references_source`-Hilfsfunktion (dieselbe, die
`_apply_semantic_protection_effect` schon für genau diese
Selbstreferenz-Erkennung nutzt: "this creature"/"this permanent"/"itself"
oder der eigene Kartenname) - bei Selbstreferenz wird `source` selbst
zurückgegeben, bei echtem Fremdziel-Text ("target creature", "another
target creature") bleibt der bisherige Ausschluss von `source` unverändert
bestehen.

**Tests:** neue Datei `tests/test_semantic_self_targeting.py` (5 Tests:
"this creature"-Text trifft die Quelle selbst, der eigene Kartenname zählt
ebenfalls als Selbstreferenz, "target creature"-Text schliesst die Quelle
weiterhin aus, kein Text fällt auf das alte Verhalten zurück, sowie ein
End-to-End-Test über `execute_semantic_action`). 474 Tests gesamt, alle
grün.

## v4.30.0 — Externe Code-Review (ChatGPT): "+1/+1 counter"-Menge wurde nicht aus dem Text gelesen

**Bug (bestätigt):** `_parse_semantic_actions` (`App/engine.py`) bestimmte
die Anzahl zu verteilender +1/+1-Zähler über
`len(re.findall(r"\+1/\+1 counter", low))` - also darüber, wie oft die
literale Zeichenkette "+1/+1 counter" im Effekttext vorkommt. Das traf bei
"Put a +1/+1 counter ..." zufällig zu (genau ein Treffer -> 1), las aber an
keiner Stelle das tatsächlich genannte Zahlwort/die Ziffer. "Put three
+1/+1 counters on target creature." enthält die Zeichenkette nur EINMAL
("counters" matcht "+1/+1 counter" als Teilstring), wurde also fälschlich
zu 1 statt 3 - eine still falsche Unterzählung, die überall dort
durchschlägt, wo dieser generische Pfad tatsächlich ausgeführt wird (z. B.
Battle-Rückseiten-Belohnungen, siehe `complete_battle`).

**Fix:** neue Regex `\b(<Zahlwort>|\d+)\s+\+1/\+1 counters?\b`, deren
Treffer über `parse_number_token` aufsummiert werden (mehrere getrennte
Klauseln in einem Text werden addiert). Bleibt der Text unquantifizierbar
(z. B. "equal to the number of Elves you control") wird weiterhin
konservativ auf 1 zurückgefallen, statt eine Zahl zu erfinden - das ist
eine bewusste, unveränderte Vereinfachung, kein neuer Fehler.

**Tests:** neue Datei `tests/test_plus1_counter_amount_parsing.py` (7 Tests:
ein/zwei/drei/vier Zähler, Ziffern- und Zahlwort-Form, zwei getrennte
Klauseln werden summiert, unquantifizierbarer Text fällt weiterhin auf 1
zurück, sowie ein End-to-End-Test über eine echte Battle-Rückseiten-
Belohnung). 469 Tests gesamt, alle grün.

## v4.29.0 — Externe Code-Review (ChatGPT): Auto-Equip gab Mana überhaupt nicht aus

**Bug (bestätigt):** `auto_equip_step` (`App/combat_model/equipment.py`)
prüfte Bezahlbarkeit nur über `available_mana_value(state, strategy) < cost`
- einen groben Vergleichswert, der bei jedem Aufruf frisch aus allen
verfügbaren Manaquellen neu berechnet wird - und rief an KEINER Stelle
`find_payment`/`apply_payment` auf. Dokumentiert war bislang nur die
kleinere Einschränkung "keine farbgenaue Bezahlung, nur Gesamtwert" - real
war es schlimmer: derselbe ungetappte Land konnte in einem einzigen
Auto-Equip-Schritt beliebig viele Equip-Aktivierungen finanzieren, und das
Mana stand danach im selben Zug immer noch für Zaubersprüche zur Verfügung.

**Fix:** `auto_equip_step` bezahlt jetzt echt über `find_payment`/
`apply_payment` - dieselbe DP-Mana-Solver-Infrastruktur, die jede andere
Ausgabe im Engine (Zaubersprüche, aktivierte Fähigkeiten, Cycling,
Flashback, ...) bereits nutzt - mit dem geparsten Equip-Kosten-Wert als
reiner Colorless-/Generic-Betrag (`parse_equip_cost` liefert ohnehin nur
einen groben Integer-Wert, auch für die seltenen farbigen Fälle - das
bleibt unverändert die dokumentierte Vereinfachung). Land/Artefakt-Quellen
werden dadurch tatsächlich getappt und stehen weder für ein zweites Equip
noch für einen späteren Spruch im selben Zug nochmal zur Verfügung.

**Tests:** `tests/test_equipment.py`s `AutoEquipStepTests` von
`available_mana_value`-Monkeypatches auf einen echten (Wastes-artigen)
Land-Fixture umgestellt, plus 1 neuer Test
(`test_v4_29_0_mana_is_actually_spent_not_reusable_for_a_second_equip`:
ein Land finanziert von zwei gleich teuren Equip-{1}-Ausrüstungen nur
genau EINE, nie beide, und das Land ist danach getappt). 462 Tests gesamt,
alle grün.

## v4.28.0 — Externe Code-Review (ChatGPT): Commander-Damage wurde bei mehreren Commandern (Partner) gepoolt

**Bug (bestätigt):** `state.commander_damage_dealt` war nur nach
Gegner-Index geführt (`Dict[int, float]`), mit dem im Code-Kommentar
festgehaltenen Vorbehalt "dieses Engine hat ohnehin nur je einen
Commander". Das stimmt aber nachweislich nicht - `build_deck_v4`/
`build_deck_v3` sammeln bereits alle Karten mit `card.commander=True` in
den `command_zone` (Partner/Background-Co-Commander sind ein real
unterstützter Fall, das CLI hat sogar ein wiederholbares
`--commander`-Flag "for Partner/background co-commanders"). Zwei
verschiedene Commander, die je 11 Combat-Damage an denselben Gegner
austeilen, wurden dadurch zu 22 gepoolt und lösten fälschlich die
21-Schaden-Niederlage aus, obwohl real (Regel 903.10a: pro Commander
einzeln gezählt) KEINER der beiden Commander für sich 21 erreicht hat.
Dieselbe Pooling-Lücke betraf zusätzlich zwei Konsument-Stellen der
Ledger, die "wie nah ist DIESER Commander an 21" einschätzen sollen:
`App/scenario_predicates/handlers.py` (`commander_damage_lethal`-Prädikat)
und `App/combat_model/posture.py` (Passiv-Haltung: "noch angreifen, um
Commander-Damage abzuschliessen") - beide lasen denselben gepoolten,
nicht-commanderspezifischen Wert.

**Fix:** Ledger jetzt nach `(commander_kartenname, gegner_index)` geführt
statt nur nach `gegner_index` - an allen drei Stellen (Schreiben in
`attack_phase`, beide Lese-Stellen oben) konsistent umgestellt. Reale
21-Schaden-Elimination durch EINEN Commander bleibt unverändert korrekt;
Partner-Decks werden jetzt nicht mehr fälschlich früher eliminiert, als
die echten Regeln es vorsehen.

**Tests:** 3 neue Tests in `tests/test_commander_damage.py`
(`MultiCommanderLedgerTests`: zwei Commander mit je 11 Schaden poolen NICHT
zu einer falschen Elimination; ein einzelner Commander mit 25 Power bleibt
weiterhin korrekt lethal; das Prädikat liest ausschliesslich den
spezifischen Commander seiner eigenen Ledger-Zeile). Zusätzlich mussten 9
bestehende Assertions in `tests/test_commander_damage.py`,
`tests/test_commander_posture.py`, `tests/test_scenario_predicates.py` und
`tests/test_wp10_voltron_and_alpha_strike.py` von direkten
Int-Key-Zugriffen (`state.commander_damage_dealt[0]`) auf die neuen
Tupel-Keys umgestellt werden - reine Testinfrastruktur-Anpassung an die
neue Ledger-Form, keine Verhaltensänderung dieser bestehenden Tests. 461
Tests gesamt, alle grün.

## v4.27.0 — Externe Code-Review (ChatGPT): "Each opponent loses N life" wirkte beim tatsächlichen Casten nicht

**Bug (bestätigt):** ein Sorcery/Instant, dessen einziger Effekt
"Each opponent loses N life." lautet, wurde von `parse_oracle_semantics`
korrekt als `execution_mode="exact"` klassifiziert (dieser Wert taucht u. a.
in der Coverage-Auswertung auf) - aber `resolve_direct_spell_effects`
(`App/engine.py`), die Funktion, die beim tatsächlichen Casten eines
Instants/Sorcerys aufgerufen wird, hat dafür überhaupt keinen Zweig. Diese
Funktion ist ein eigener, komplett separater Regex-Pfad (feste Karten per
Namen, dann generisches Draw / Scry-Surveil-Connive / feste Lebensgewinn-
Sätze / Food-Treasure-Clue-Erzeugung) und läuft NICHT über den generischen
`execute_semantic_action`/`keyword_registry`-Dispatcher, den z. B. Loyalty-
und aktivierte Fähigkeiten benutzen - obwohl für `opponent_life_loss` dort
längst ein Handler existiert (`App/keyword_library/handlers.py`). Ergebnis:
eine solche Karte tat beim Casten schlicht gar nichts, obwohl die
Modell-Coverage-Anzeige "exact" meldete - eine still falsche Diskrepanz
zwischen gemeldeter und tatsächlicher Abdeckung.

**Fix:** neuer, eng begrenzter generischer Block in
`resolve_direct_spell_effects`, nach demselben Muster wie die direkt
darüberliegenden Blöcke (feste Lebensgewinn-Sätze, Food/Treasure/Clue) -
erkennt "each/target opponent loses N life" (Zahl oder Zahlwort), mit
demselben when/whenever-Trigger-Ausschluss wie die Nachbarblöcke, und ruft
`lose_each_opponent`/`lose_target_opponent` direkt auf. Bewusst NICHT als
grössere Vereinheitlichung von `resolve_direct_spell_effects` mit dem
generischen Aktions-Dispatcher umgesetzt (der Dispatcher erwartet einen
`Permanent`-Quelle plus Ziel, die ein resolvendes Instant/Sorcery nicht hat)
- das wäre ein deutlich grösserer Umbau, hier bewusst nicht Teil eines
einzelnen, evidenzbasierten Bugfixes.

**Tests:** neue Datei `tests/test_direct_opponent_life_loss.py` (5 Tests:
"each opponent", "target opponent", Zahlwort-Betrag, Trigger-Zeilen bleiben
weiterhin ausgeschlossen, sowie ein Kontrolltest, der bestätigt, dass die
Parser-Seite schon vor dem Fix korrekt war - nur die Cast-Auflösung fehlte).
458 Tests gesamt, alle grün.

## v4.26.0 — Externe Code-Review (ChatGPT): "Discard a card"-Aktivierungskosten wurden ignoriert

**Bug (bestätigt):** eine Aktivierungskosten-Zeile wie
`{T}, Discard a card: Draw a card.` (reales, häufiges "Looting"-Muster) hatte
für den generischen Aktivierungs-Parser (`App/engine.py`) keinerlei
Repräsentation für "Discard a card" - im Gegensatz zu
"Sacrifice a Food/Treasure/Clue" (erkannt) oder "Sacrifice ein sonstiges
Objekt" (per `unrecognized_sacrifice_cost` bewusst als NICHT ausführbar
markiert), gab es für "Discard" gar keinen Mechanismus. Weil dieselbe
Kostenzeile aber oft zusätzlich ein `{T}` enthält, wurde `recognized_cost`
trotzdem "wahr" (Tap-Kosten erkannt = scheinbar vollständig bezahlbar), die
Fähigkeit lief als `exact` durch und wurde automatisch ausgeführt - bezahlt
wurde nur das Tappen, der Karten-Discard fiel komplett unter den Tisch. Ein
reiner Kartenfilter-Effekt (Handgrösse netto unverändert: eine Karte weg,
eine Karte gezogen) wurde dadurch zu einem kostenlosen Extra-Zug.

**Fix:** neues `SemanticAbility.discard_count`-Feld, befüllt aus einer
"discard (a|two|three|...) cards?"-Regex im Kostentext, symmetrisch in
`recognized_cost` eingerechnet (genau wie `sacrifice_resource`). In
`execute_semantic_ability` wird die Fähigkeit erst gar nicht ausgeführt,
wenn die Hand nicht genug Karten für die Kosten hat (fail closed, gleiches
Muster wie die Food/Treasure/Clue-Prüfungen), und beim tatsächlichen Bezahlen
werden `discard_count` Karten wirklich abgeworfen - mit derselben
"am wenigsten wertvolle Karte zuerst"-Heuristik (`discard_score`), die
Connive bereits nutzt. Zusätzlich bekommt `semantic_ability_score`
(End-Step-Priorisierung in `try_generic_semantic_activations`) einen
Abzug pro abzuwerfender Karte (Stärke/Vorzeichen wie das bereits bestehende
`discard_self`-Gewicht im Value Model), damit dieses Engine nicht jede Runde
blind Karten wegwirft, nur weil "Draw a card" isoliert positiv bewertet wird.

**Tests:** neue Datei `tests/test_discard_activation_cost.py` (5 Tests:
Kostenerkennung, Karten tatsächlich abgeworfen bei netto unveränderter
Handgrösse, Ablehnung bei leerer Hand, End-to-End über `end_step`). 453
Tests gesamt, alle grün.

## v4.25.0 — Externe Code-Review (ChatGPT): Planeswalker-Loyalty-Fähigkeiten wurden am End Step ein zweites Mal gratis ausgeführt

**Bug (bestätigt):** `parse_oracle_semantics` (`App/engine.py`) klassifiziert
jede Zeile mit Doppelpunkt als normale "activated"-Fähigkeit - auch
Loyalty-Zeilen eines Planeswalkers ("+1: ...", "-3: ...", "0: ..."), deren
"Kosten" (z. B. "+1") keine echten Mana-/Tap-/Sacrifice-Symbole enthalten.
Dadurch kam `recognized_cost` fälschlich auf "wahr" (kein Kostenanteil
erkannt = scheinbar kostenlos), und `try_generic_semantic_activations`
(aufgerufen aus `end_step`) hat KEINE planeswalkerspezifische Ausnahme - nur
die kleine, fest kodierte `DEDICATED_RESOLVERS`-Namensliste - und prüft
`p.loyalty` an keiner Stelle. Ergebnis: jeder Planeswalker, dessen
Loyalty-Fähigkeit vom generischen Aktions-Vokabular erkannt wird (Draw,
Lebensverlust, Token, ...), bekam diese Fähigkeit am End Step ein zweites
Mal gratis ausgeführt - zusätzlich zur korrekten, bereits in v4.19.0
gebauten Einmal-pro-Zug-Aktivierung über `activate_planeswalker_loyalty_abilities`,
ohne dass sich die Loyalty dabei änderte oder eine Verfügbarkeitsprüfung
stattfand. Nachgestellt am tatsächlich live geschalteten Code vor dem Fix
(siehe Testkommentar in `tests/test_planeswalker_loyalty.py`): ein simpler
"+1: Draw a card."-Walker zog am End Step eine zusätzliche, komplett
kostenlose Karte.

**Fix:** `parse_oracle_semantics` überspringt Zeilen, die für einen
Planeswalker (`card.is_planeswalker`) auf das bereits bestehende
`_LOYALTY_ABILITY_RE` (dieselbe Regex, die `parse_loyalty_abilities` für
die korrekte Aktivierung nutzt) oder auf `"0:"` matchen, komplett - sie
tauchen dann gar nicht erst als generische "activated"-Fähigkeit auf und
können von `try_generic_semantic_activations` nicht mehr angefasst werden.
Alle sonstigen Doppelpunkt-Fähigkeiten (normale Activated Abilities auf
Kreaturen/Artefakten/etc.) sind unverändert.

**Tests:** 2 neue Tests in `tests/test_planeswalker_loyalty.py`
(`test_end_step_does_not_grant_a_free_second_loyalty_activation`,
`test_generic_semantic_activations_skip_loyalty_lines_entirely`) - manuell
zusätzlich am tatsächlichen Bug-Mechanismus nachvollzogen (Regex-Guard
deaktiviert -> End Step zieht wieder zwei zusätzliche gratis Karten). 448
Tests gesamt, alle grün.

## v4.24.0 — Externe Code-Review (ChatGPT): Token-Gruppen-Schaden korrigiert

**Auftrag:** die als ZIP exportierte v4.23.0-Codebasis wurde bewusst extern
(ChatGPT) auf genau zwei Dinge geprüft - Deckinterpretation und
Spielsimulation, explizit ohne Gegnerfunktion (siehe
`chatgpt_review_prompt.md`). Die Rückmeldung enthielt mehrere konkrete,
reproduzierbare Fehler; dieser Eintrag behebt den mit Abstand
schwerwiegendsten davon, jeder weitere folgt als eigene, einzeln testbare
Version (one-fix-per-version, siehe bisherige Konvention). Jede Behauptung
wurde vor der Korrektur am tatsächlich live geschalteten Code (nicht an
irgendeiner der 5-6 überschatteten Vorgängerdefinitionen) nachvollzogen,
nicht blind übernommen.

**Bug (bestätigt):** `attack_phase`s Schadensberechnung für Token-Gruppen
(`App/engine.py`) lautete
`power = token_group_power(g, state) + global_bonus * g.count` - der
Team-Bonus wurde korrekt mit der Tokenanzahl multipliziert, die
Basis-Power des einzelnen Tokens (`token_group_power`, pro Token, nicht
pro Gruppe) dagegen NICHT. Eine Gruppe aus 10 gruppierten 1/1-Token-Kreaturen
(z. B. Storm Herd, White Sun's Zenith - beide real in den geprüften Decks)
verursachte beim ungeblockten Angriff dadurch nur 1 Schaden statt 10, ohne
Crash oder Warnung - eine still falsche, nicht offensichtliche Fehlkalkulation,
die insbesondere "Go-wide"-Pläne (viele kleine Token statt weniger grosser
Kreaturen) im Testergebnis systematisch schlechter aussehen liess, als sie
tatsächlich sind. Fix: `power = (token_group_power(g, state) + global_bonus)
* g.count` - beide Anteile werden jetzt korrekt pro Token skaliert, bevor mit
der Tokenanzahl multipliziert wird.

**Zusätzlich (gleicher Fund, gleiche Ursache):** die Kampf-Interaktionsengine
(`App/combat_model/interaction.py`) behandelte eine ganze Token-Gruppe für
`wide_board`s Soft-Cap/Decay-Berechnung (mehr Angreifer -> pro Angreifer
niedrigere Blockwahrscheinlichkeit) als GENAU EINEN Angreifer, unabhängig von
`g.count` - ein Brett mit einer einzelnen Kreatur plus einer 10er-Token-Gruppe
zählte als "2 Angreifer" statt real 11. Neues `AttackerInfo.attack_weight`
(Default 1.0, für Token-Gruppen auf `g.count` gesetzt) fliesst jetzt in die
`n_attackers`-Summe ein. Die eigentliche Block-/Trade-Auflösung pro Gruppe
bleibt bewusst unverändert ein einzelner Wurf für die ganze Gruppe (Tod
reduziert weiterhin nur `g.count -= 1`, siehe bereits bestehende
Moldervine-Reclamation-/Equipment-Sterbetrigger-Konvention) - eine echte
Pro-Token-Blocksimulation wäre eine deutlich grössere, hier nicht
gerechtfertigte Umbau-Massnahme, da dieses Engine ohnehin kein echtes
gegnerisches Board simuliert.

**Nicht übernommen (bewusst zurückgestellt):** die Testabdeckungs-Kritik am
gelieferten ZIP ("410 von 443 grün, Rest Errors/Skips") ist ein Artefakt des
kuratierten Review-Pakets (fehlende Scryfall-Cache-Datei und `Decks/Fremd`
waren absichtlich ausgeschlossen, siehe `chatgpt_review_prompt.md`), nicht
ein echter Fehler im Projekt selbst - im echten Arbeitsverzeichnis liefen zu
jedem Zeitpunkt alle 443 (jetzt 446) Tests grün.

**Tests:** 3 neue Regressionstests in `tests/test_combat_interaction.py`
(`test_unblocked_token_group_deals_count_times_power_damage`,
`test_unblocked_token_group_scales_with_a_global_team_bonus_too`,
`test_token_group_attack_weight_counts_toward_wide_board_math`) - 446 Tests
gesamt, alle grün.

## v4.23.0 — Sekundäre "das viele X"-Lücken: Chatterfang, Doubling Season, Augusta, Zimone, Mycoloth/Ribtruss Roaster

**Auftrag:** die im v4.18.0-Audit zurückgestellten "das viele X"-proportionalen
Trigger-Lücken schliessen. Alle fünf sind echte, im Audit per
`card_impact.csv`/`card_model_coverage.csv` bestätigte Karten aus den
hochgeladenen Testläufen (Korvold, Lorehold Spirit, Quandrix Unlimited,
Witherbloom Pestilence) - kein einziger Zahlenwert wurde geraten.

**Chatterfang, Squirrel General** ("If one or more tokens would be created
under your control, those tokens plus that many 1/1 green Squirrel creature
tokens are created instead.") und **Doubling Season** ("... it creates twice
that many of those tokens instead. ... it puts twice that many of those
counters ... instead.") sind beides Replacement-Effekte auf
Token-/Zähler-Erzeugung - statt an jeder einzelnen Erzeugungsstelle im
15.000-Zeilen-File einzeln zu patchen, sitzen beide jetzt an der EINEN
gemeinsamen Wurzel: der zentralen `create_tokens`-Funktion (jede
Token-Erzeugung im ganzen Engine läuft da durch) und dem generischen
`plus1_counter`-Handler (`App/keyword_library/handlers.py`, der Pfad, den
der generische Fähigkeiten-Parser für praktisch jeden Kartentext mit
"+1/+1 counter" nutzt). Doubling Season verdoppelt zusätzlich die
Start-Loyalität eines eintretenden Planeswalkers und die Start-Verteidigung
einer eintretenden Schlacht (der wohl bekannteste reale Anwendungsfall der
Karte überhaupt) sowie die Zähler aus Devour (v4.21.0) - alles an der
jeweils schon vorhandenen, EINEN Stelle. Bewusste Lücke: die vielen
exakten Karten-Resolver an Einzelstellen im restlichen Code (z. B. Connive,
Persist/Undying-Rückkehr) werden von diesem Pass nicht erfasst - dokumentiert,
nicht stillschweigend übergangen.

**Augusta, Order Returned** ("Whenever Augusta attacks, each player exiles
a card from their graveyard. When one or more nonland cards are exiled this
way, put that many +1/+1 counters on target attacking creature.") - neuer
Hook direkt in `attack_phase`, nachdem Angreifer feststehen: da dieses
Engine grundsätzlich NUR den eigenen Friedhof modelliert (kein einziger
gegnerischer Friedhof existiert irgendwo im Code - reiner "goldfish"-Simulator),
wird "each player exiles a card" bewusst zu "wir exilieren eine Karte aus
unserem eigenen Friedhof" vereinfacht - eine offengelegte Vereinfachung,
keine Erfindung von nicht modelliertem Gegnerzustand. Der Zähler landet
immer auf Augusta selbst (die naheliegende reale Wahl), inklusive Neusync
von `attacker_infos`, damit der Bonus noch im selben Kampf zählt (gleiches
Muster wie die bereits existierenden Blossoming-Bogbeast-/Waterbend-Resyncs).

**Zimone, All-Questioning** ("At the beginning of your end step, if a land
entered the battlefield under your control this turn and you control a
prime number of lands, create Primo, the Indivisible, ..., then put that
many +1/+1 counters on it.") - neuer End-Step-Hook mit echter
Primzahl-Prüfung (`_is_prime`) und Abgleich, ob `entered_turn == state.turn`
für mindestens ein Land gilt.

**Mycoloth / Ribtruss Roaster** (beide Devour-Kreaturen mit
Folge-Fähigkeit "erzeuge Token gleich der Anzahl +1/+1-Zähler auf dieser
Kreatur", einmal im Upkeep, einmal im End Step) - der generische
"create N tokens"-Parser versteht nur feste Zahlen/Zahlwörter, keine
dynamische, spielabhängige Zählergrösse; beide Karten bekommen daher einen
eigenen, kleinen Hook, der auf dem in v4.21.0 bereits generisch gebauten
Devour-Grundmechanismus aufbaut (Mycoloth/Ribtruss Roaster bekommen ihre
Start-Zähler bereits automatisch über den generischen Devour-Code aus
v4.21.0 - hier kommt nur die wiederkehrende Folge-Erzeugung dazu).

23 neue Tests in `tests/test_keyword_gaps_3.py`. Gesamte Suite danach
443/443 grün (keine Regression).

## v4.22.0 — Keyword-Lücken Batch 2: Prowess, Delve, Cycling, Flashback (Kicker bewusst ausgelassen)

**Prowess** ("Whenever you cast a noncreature spell, this creature gets
+1/+1 until end of turn.") - Hook in `try_cast_option`, der EINEN Trichter,
durch den jeder erfolgreiche Zauberspruch-Cast (Kreatur wie Nicht-Kreatur)
läuft; nutzt den bereits vorhandenen `BoardModifier`-Mechanismus
(`team_pt_bonus` mit `target_id`), verfällt automatisch beim nächsten
Enttappen. Nur Angriffskraft wird gebufft, da dieses Engine nirgendwo eine
Widerstandskraft-basierte Kampfrechnung führt (Kampf läuft rein über
Angriffskraft + abstrakten Block/Trade-Wurf).

**Delve** ("Each card you exile from your graveyard while casting this
spell pays for {1}.") - echter, tatsächlich bezahlter Kostenrabatt, keine
kostenlose Reduktion: `delve_discount` reiht sich in `cast_option`s
bestehende Rabatt-Pipeline ein (gleiche Stelle wie der schon existierende
`boardwipe_self_scaling_discount`), gedeckelt auf den generischen Anteil der
Kosten (kann farbige Manasymbole nicht reduzieren) und die tatsächliche
Friedhofgrösse; das eigentliche Exilieren passiert dann in `try_cast_option`,
sobald der Cast wirklich stattfindet.

**Cycling** ("{cost}, Discard this card: Draw a card.") und **Flashback**
("You may cast this card from your graveyard for its flashback cost. Then
exile it.") laufen beide als eigenständige Phase am Ende von "end main 2",
BEVOR `end_step` - sie verbrauchen nur, was die beiden regulären
Cast-Durchläufe an Mana übrig gelassen haben, über dieselben
`find_payment`/`apply_payment`-Grundfunktionen, die auch jeder normale
Zauberspruch nutzt (kein erratenes "das ist wertvoll"-Bonus). Flashback
zuerst (ein echter zweiter Zaubereffekt schlägt Cycling bei gleichem Mana),
danach Cycling, günstigste bezahlbare Karte zuerst, mit Sicherheitslimit
gegen eine unbeschränkte Cycling-Kette.

**Kicker bewusst NICHT gebaut:** anders als die vier Mechaniken oben
bräuchte Kicker einen echten Eingriff in `cast_option`s eigene
Gesamtkosten-Entscheidung (Kosten müssten VOR `find_payment` bedingt nach
OBEN gehen) und eine Rückmeldung an den Resolve-Pfad, ob der Aufpreis
bezahlt wurde - kein additiver Hook wie bei den anderen vieren, sondern ein
Eingriff in den bestehenden, funktionierenden Cast-Pfad, und keine einzige
reale Kicker-Karte in den 14 Testdecks, an der sich eine "wann lohnt es
sich"-Heuristik kalibrieren liesse. Ehrlich als offene Lücke dokumentiert
statt flach/falsch verdrahtet.

14 neue Tests in `tests/test_keyword_gaps_2.py`. Gesamte Suite danach
420/420 grün (keine Regression).

## v4.21.0 — Keyword-Lücken Batch 1: Infect, Persist, Undying, generisches Devour (Wither bewusst ausgelassen)

**Infect** ("Damage dealt to a player by a source with infect ... causes
that many poison counters instead.") - neues `state.poison_counters`-Dict,
in `attack_phase`s bestehendem Schadens-Zweig wird für Infect-Quellen jetzt
Gift statt Lebenspunkte abgezogen; 10+ Gift-Zähler eliminiert den Gegner
genauso wie die bereits existierende 21-Kommandant-Schaden-Regel (direktes
Nullsetzen).

**Persist** / **Undying** hängen sich an die EINE geteilte Stelle, an der
ein echtes, eigenes Kreaturen-Permanent stirbt (`move_permanent_to_zone`,
Ziel "graveyard") - dieselbe Wurzel, die schon Moldervine Reclamation
nutzt. Damit greift es bei JEDEM Tod (Kampf, Opfer, zukünftige Devour-Opfer,
...), nicht nur bei Kampftod. Neues `Permanent.minus1_counters`-Feld
parallel zu `counters` (+1/+1).

**Generisches Devour** ("As this creature enters the battlefield, you may
sacrifice any number of creatures. This creature enters with N +1/+1
counters on it for each creature devoured this way.") - da keine einzige
echte Devour-Karte in den 14 Testdecks vorkam, bewusst konservativ:
geopfert werden ausschliesslich TOKEN-Kreaturen (nie eine benannte,
echte Kreatur, wofür ohne Kalibrierungsdaten keine seriöse
Wert-Abwägung möglich wäre), kleinste Angriffskraft zuerst.

**Wither bewusst NICHT gebaut:** wirkt real ausschliesslich bei Schaden an
einer Kreatur - dieses Engine modelliert nirgendwo gegnerische Kreaturen
(reiner "goldfish"-Simulator), Wither kann hier also strukturell nie einen
beobachtbaren Effekt haben. Bewusst unimplementiert statt totem Code für
ein Ereignis, das nie eintreten kann.

Nebenbei entdeckter, echter Bug, der ALLE Karten betrifft, nicht nur
Battles/Devour: der generische `create_token`-Handler
(`App/keyword_library/handlers.py`) hat nie `creature=True` an
`ops.create_tokens` weitergereicht - jede generisch geparste
Kreaturen-Token-Beschreibung ("3/3 Green Bear Creature") war ein
kompletter, stiller No-Op, nur Food/Treasure/Clue funktionierten. Gefixt.

13 + 3 (Handler-Fix) neue Tests. Gesamte Suite danach 406/406 grün.

## v4.20.0 — Schlachten (Battles): Verteidigungszähler, eigene Kreaturen greifen an, Umwandlungs-Belohnung

Keine einzige echte Battle-Karte kam in den 14 Testdecks vor - komplettes
Neuland ohne Kalibrierungsdaten, entsprechend offen dokumentiert. Neue
`Card.defense`/`Permanent.defense`-Felder. Da dieses Engine grundsätzlich
KEINE gegnerischen Kreaturen modelliert, greifen zwangsläufig die EIGENEN
Kreaturen die selbst gecastete Schlacht an (reale Regel: der Caster ist nie
"Beschützer" seiner eigenen Schlacht) - kleinste Angriffskraft zuerst,
niemals Kommandant/Engine-Rolle-Kreaturen, unbedingt verbindend (dieselbe
"keine Blocker"-Vereinfachung wie beim Spieler-Schaden). Bei 0 Verteidigung
wandert die Schlacht in den Friedhof; falls die Rückseite einer
umwandelnden Schlacht zu mindestens einer ausführbaren generischen Aktion
parst, feuert das einmalig als Annäherung an "die Belohnung der
Umwandlung" - OHNE die Rückseite als dauerhaftes Permanent zu modellieren
(dafür bräuchte es generische DFC-Umwandlung, die dieses Engine nirgendwo
sonst hat).

Nebenbei entdeckt: derselbe `create_token`-Handler-Bug wie oben in v4.21.0
beschrieben, hier zuerst beim Testen der Umwandlungs-Belohnung gefunden.

12 neue Tests in `tests/test_battles.py`. Gesamte Suite danach 393/393 grün.

## v4.19.0 — Planeswalker: Loyalitäts-Zähler + Fähigkeiten-Aktivierung einmal pro Zug

Neue `Card.loyalty`/`Permanent.loyalty`-Felder, automatisch aus dem
gedruckten Startwert befüllt (`Permanent.__post_init__`, dieselbe
"Fix an der Wurzel"-Logik wie der v4.15.6-Baron-Bertram-Fix, statt an
jeder der sechs `Permanent(card=...)`-Konstruktionsstellen einzeln). Neuer
`_LOYALTY_ABILITY_RE`, der sowohl "-" als auch das echte Unicode-Minus "−"
erkennt (bestätigt an echtem Ugin-Oracle-Text aus den Testdaten). Einmal
pro Zug, sorcery-speed, wählt eine gierige Heuristik die wertvollste
BEZAHLBARE Fähigkeit über die bereits existierende
`ValueModel.metric_value`-Bewertung - bevorzugt automatisch die Ultimate,
sobald bezahlbar, ohne eine eigens gebaute "Loyalität für die Ultimate
sparen"-Regel. Nur Fähigkeiten, deren Effekt im bestehenden generischen
Aktions-Vokabular ausführbar ist (Schaden an spielerartigem Ziel / Karten
ziehen / Leben gewinnen / Token erzeugen), werden wirklich ausgeführt -
alles andere (Exil, gegnerische Permanents als Ziel, Embleme, ...) wird
zwar als Fähigkeit erkannt, aber ehrlich nicht ausgeführt.

Nebenbei gefundener, echter Bug: die geteilten Zahlwort-Regexe im
generischen Aktions-Parser deckten nur "eins" bis "fünf" ab, obwohl
`NUMBER_WORDS` bereits sechs bis zehn unterstützt - gefunden an Ugins
echter "-10: ... draw seven cards ..."-Fähigkeit, die nur die
Leben-gewinnen-Hälfte parste. Auf alle betroffenen Regexe (Draw, Gain Life,
Opponent Life Loss, Create Token, Scry/Surveil/Connive) erweitert.

13 neue Tests in `tests/test_planeswalker_loyalty.py`. Gesamte Suite danach
378/378 grün.

## v4.18.0 — Modell-Coverage-Audit über alle 14 echten Testläufe: Old Gnawbone gefixt, Planeswalker/Schlachten/Keyword-Lücken dokumentiert

**Auftrag:** kritische Durchsicht aller 14 vom Nutzer hochgeladenen echten
Ergebnis-ZIPs (Krenko, Scarab God, Korvold, Blight Curse, Lorehold Spirit,
Old Gnawbone, Prismari Artistry, Quandrix Unlimited, Silverquill Influence,
Sultai Arisen, The Ur-Dragon, Witherbloom Pestilence) darauf, ob Mechaniken
korrekt erkannt/abgebildet werden, ob es "Default-Probleme" gibt, und
insbesondere wie Planeswalker und Schlachten behandelt werden. Ausdrücklich
NICHT per Einzel-Keyword-Testdecks geprüft, sondern per Workaround: die
vom Programm selbst pro Lauf erzeugten `card_model_coverage.csv` /
`semantic_runtime_report.csv` (die eigene "exact/simplified/probabilistic/
review"-Tier-Klassifizierung jeder geparsten Fähigkeit) wurden über alle
14 Läufe (789 einzigartige Karten) aggregiert und Zeile für Zeile gegen die
tatsächlich GEMESSENEN `card_impact.csv`-Werte (Mana generiert, Treasure
erzeugt, Karten gezogen, ...) gegengeprüft — das zeigt echte Lücken, ohne
dass jedes Keyword in einem eigens gebauten Deck vorkommen muss.

**Wichtiger methodischer Fund zuerst:** die "review"-Tier-Markierung in
`card_model_coverage.csv` bedeutet NICHT "wird nicht ausgeführt". Sol Ring
und Llanowar Elves sind dort als "review"/"generic" markiert (der generische
Fähigkeiten-Parser erkennt `{T}: Add {C}{C}` nicht als sicher ausführbar),
erzeugen aber laut `card_impact.csv` tatsächlich 244 bzw. 141 Mana über die
echten Testläufe - die Mana-Erzeugung läuft über eine komplett separate,
dedizierte Funktion (`parse_add_mana_options`), die der Tier-Report gar
nicht kennt. Gleiches gilt für Land-Ramp (Cultivate, Kodama's Reach, ...) -
die "search your library for a basic land ... battlefield"-Erkennung ist
eine eigene, dedizierte Text-Regel. Für eine künftige KI-Durchsicht von
`card_model_coverage.csv` heisst das: "review" ist ein Hinweis, dass man
nachsehen sollte, kein Beweis für eine Lücke.

**Echter, gefundener UND gefixter Bug: Old Gnawbone.** Die einzige,
namensgebende Fähigkeit des Commanders ("Whenever a creature you control
deals combat damage to a player, create that many Treasure tokens.") war
komplett unmodelliert - über den gesamten Testlauf (173 echte Casts, als
Commander in 77.5 % aller Spiele auf dem Feld) stand in `card_impact.csv`
für "Treasure created" konstant 0. Root Cause: `attack_phase` hat zwar
bereits pro Angreifer die genaue ausgeteilte Kampfschaden-Menge
(`outcome.damage_dealt`, exakt das Ereignis "eine Kreatur, die du
kontrollierst, fügt einem Spieler Kampfschaden zu" - dieselbe Stelle, die
schon für den Equipment-Kopier-Trigger genutzt wird), aber nichts hat
diese Zahl je an eine Treasure-Erzeugung angebunden. Fix: in genau diesem
bereits vorhandenen `outcome.damage_dealt > 0`-Zweig wird jetzt, wenn Old
Gnawbone im Spiel ist, `create_tokens(state, strategy, "Treasure",
int(round(outcome.damage_dealt)), source="Old Gnawbone")` aufgerufen -
gilt auch für Old Gnawbones eigenen Schaden (der Kartentext schliesst sich
selbst nicht aus) und funktioniert automatisch korrekt mit Double Strike,
da `damage_dealt` dort bereits die verdoppelte Schadensmenge ist. Old
Gnawbone wurde zu `DEDICATED_RESOLVERS` und `KNOWN_COVERAGE_NOTES`
("strong") hinzugefügt. 5 neue Tests in `tests/test_old_gnawbone.py`
(eigener Schaden, fremder Angreifer während Old Gnawbone im Spiel,
kein Old Gnawbone -> kein Treasure, vollständig geblockt -> kein Treasure,
Double Strike verdoppelt Treasure korrekt mit).

**Planeswalker - ehrlicher Befund, bewusst NICHT in diesem Schritt
gebaut:** 10 einzigartige Planeswalker über 4 der 14 Decks (Liliana,
Dreadhorde General / Death's Majesty / Untouched by Death / the Last Hope /
Death Wielder; Vraska, Betrayal's Sting; Quintorius, History Chaser; Nicol
Bolas, the Ravager; Sarkhan, the Dragonspeaker; Ugin, the Spirit Dragon).
`type_line`-Prüfung auf "planeswalker" existiert im gesamten Code genau
EINMAL, in `Card.is_permanent`. Es gibt keine Lealitäts-Zähler, keine
Aktivierung von +/- Fähigkeiten, keine Möglichkeit, dass ein Planeswalker
im Kampf angegriffen/getötet wird. In den echten Läufen wurden Ugin/Bolas/
Sarkhan zwar regelmässig gecastet (12/32/15 mal), "Died in combat" und
"Removed by opponent" stehen aber durchgehend auf 0 - sie liegen nach dem
Cast nur als Körper mit generischem ETB-/Text-Wert auf dem Feld, ihre
eigentliche Fähigkeit passiert nie. Das ist kein Bug, sondern ein bislang
schlicht nicht gebautes Feature - wie vom Nutzer selbst erwartet.

**Schlachten (Battles) - noch nicht einmal in den Testdaten vorgekommen:**
kein einziges Battle-Kartenobjekt in irgendeinem der 14 Decks. Kein
`is_battle`, keine Verteidigungszähler-Logik, keine "battle"-Erkennung
irgendwo im Code. Komplettes Neuland, weder getestet noch gebaut.

**Default-Werte geprüft, kein Drift gefunden:** `Data/Models/
goldfish_value_model.json` gegen `DEFAULT_VALUE_MODEL` (App/engine.py)
programmatisch verglichen - alle 14 gefundenen Unterschiede sind reine
`_comment*`-Dokumentationsfelder, die nur in der JSON existieren; kein
einziger tatsächlicher Zahlenwert weicht ab. `combat_interaction_weights.json`
/ `resource_planner_weights.json` haben ohnehin keine Code-Kopie, sondern
werden zur Laufzeit direkt eingelesen - dort ist Drift architektonisch
ausgeschlossen.

**Statische Kampf-Keywords vollständig:** `KNOWN_KEYWORDS` (Flying, First
strike, Double strike, Deathtouch, Haste, Hexproof, Indestructible,
Lifelink, Menace, Reach, Trample, Vigilance, Ward, Flash, Defender,
Protection, Shroud) deckt gegen alle 789 echten getesteten Karten jedes
tatsächlich vorkommende kampfrelevante statische Keyword ab - kein einziges
fehlendes gefunden.

**Nicht-kampfbezogene Keyword-Mechaniken - dokumentierte Lücke, bewusst
NICHT in diesem Schritt angefasst:** über die 789 Karten hinweg tauchen
mindestens 40 echte, offizielle Keyword-Mechaniken auf, die weder als
statisches Kampf-Keyword noch über einen der nur 6 existierenden
`DEDICATED_RESOLVERS`-Sonderfälle abgedeckt sind und damit auf die
generische Heuristik zurückfallen: Cycling (11x), Flashback (6x), Wither
(6x), Delve (5x), Persist/Kicker/Prowess/Encore (je 3x), Overload/Storm/
Echo/Decayed/Devoid/Demonstrate/Cascade/Escape/Affinity/Shadow/Devour
(je 2x), sowie einmalig u. a. Exalted, Dash, Undying, Convoke, Dredge,
Eternalize, Annihilator, Bestow, Ascend, Gravestorm, Skulk, Replicate,
Split Second, Suspend, Retrace, Myriad, Backup, Living Weapon, Landwalk-
Varianten, Intimidate, Fear, Changeling, Mentor, Compleated. Cycling,
Flashback, Wither und Delve sind wegen ihrer Häufigkeit die naheliegendsten
Kandidaten für künftige dedizierte Resolver, falls das priorisiert wird.

**Sekundärer, ähnlich gelagerter Verdacht - nicht gefixt, nur notiert:**
einige weitere "das viele X" / proportionale Trigger zeigen auffällig
niedrige gemessene Werte und riechen nach derselben Lückenklasse wie Old
Gnawbone, aber auf Nebenkarten statt auf einen ganzen Spielplan: Zimone,
All-Questioning (Primo-Erzeugung bei Primzahl-Ländern), Augusta, Order
Returned (Exil-Karten -> +1/+1-Zähler), Chatterfang, Squirrel General,
Mycoloth/Ribtruss Roaster (Devour). Absichtlich nicht in diesem Schritt
angefasst (ein Fix pro Version, Priorität liegt bei Old Gnawbone als
tatsächlichem Commander-Gameplan).

**Engine-Integrität:** `engine_invariants` stand in allen 14 Läufen auf
PASS (0 resource_invariant_violations, 0 payment_resource_conflicts).

Volle Suite: 365 Tests grün (360 vorher + 5 neu für Old Gnawbone).

## v4.17.0 — Der v4.16.0-Fix hat nie gegriffen: `get_many` wird zweimal ueberschrieben, echte Live-Version jetzt gefixt + Fehler-Aggregation + Fuzzy-Fallback + Check-Skript

**Ausgangslage:** der Nutzer hat mehrere Fremd-Decks (Lorehold Spirit,
Quandrix Unlimited, Silverquill Influence, Witherbloom Pestilence, The
Ur-Dragon, Old Gnawbone) lokal online laufen lassen und meldete u. a., dass
`Duskwatch Recruiter` (Old Gnawbone) IMMER NOCH als „nicht bekannt"
gemeldet wurde — obwohl das laut v4.16.0-Changelog genau die Karte war, die
dort schon gefixt sein sollte. Das war der Hinweis auf einen viel groesseren
Fehler als die ursprüngliche Doppelseiten-Karten-Karten-Indizierung.

**Der eigentliche Bug (schwerwiegender als der v4.16.0-Fund selbst):**
`App/engine.py` ueberschreibt `ScryfallProvider.get_many` NACH der
Klassendefinition zweimal auf Modul-Ebene (`ScryfallProvider.get_many =
_scryfall_get_many_requests` bei einer frueheren Version, dann
`ScryfallProvider.get_many = _scryfall_get_many_urllib` gut 2400 Zeilen
spaeter) — nach Pythons "letzte Zuweisung gewinnt"-Regel ist beim Import
IMMER `_scryfall_get_many_urllib` die tatsaechlich aktive Methode, komplett
unabhaengig davon, was im Klassenkoerper selbst steht. Der v4.16.0-Fix
(DFC-Indizierung ueber `card_faces`) wurde ausschliesslich in den
Klassenkoerper eingebaut — also in genau die Kopie, die beim Laden des
Moduls sofort wieder verworfen wird. Der Fix war also nie live, in keinem
einzigen lokalen Lauf. Das ist exakt die Falle, vor der die eigenen
Projekt-Konventionen warnen ("prüfe die letzte Definition, bevor du eine
Funktion änderst") — nur dass hier nicht dieselbe Funktion zweimal
definiert war, sondern zwei VOLLSTÄNDIG UNABHÄNGIGE Kopien derselben Logik
per Monkey-Patch ausgetauscht wurden, was beim reinen Durchsuchen nach
`^def get_many` nicht auffällt (man muss zusätzlich nach
`\.get_many\s*=` suchen).

**Fix:** die komplette Batch-Fetch-/Fehlerbehandlungs-Logik wurde in eine
einzige, geteilte Methode `ScryfallProvider._resolve_missing()` ausgelagert
(inklusive der v4.16.0-DFC-Indizierung über `index_scryfall_cards()`). Alle
drei bisherigen `get_many`-Kopien (Klassenkörper, `_requests`-Variante,
`_urllib`-Variante — die tatsächlich lebende) sind jetzt dünne Wrapper, die
nur noch ihren jeweiligen HTTP-Layer bereitstellen und den Rest an diese
eine Methode delegieren. Ein neuer Regressionstest
(`test_get_many_is_bound_to_the_live_urllib_implementation`) prüft explizit
`ScryfallProvider.get_many is _scryfall_get_many_urllib`, damit ein
zukünftiger dritter Monkey-Patch nicht wieder unbemerkt live geht.

**Zwei zusätzliche echte Verbesserungen, direkt aus der Nutzer-Frage
entstanden ("bricht das Programm ab, sobald die erste Karte nicht gefunden
wurde, oder prüft es alle Karten?"):**

1. **Fehler-Aggregation über das GANZE Deck:** vorher brach `get_many` beim
   ERSTEN Scryfall-Batch (max. 70 Karten) mit einem `not_found` sofort mit
   einer Exception ab — bei einem ~99-Karten-Deck mit mehr als 70 fehlenden
   Karten wurde der zweite Batch nie angefragt, dessen Probleme also nie
   gemeldet. Jetzt werden alle Batches durchlaufen, alle nicht auflösbaren
   Karten über das GESAMTE Deck gesammelt, und erst am Ende genau EIN
   Fehler mit der vollständigen Liste geworfen.
2. **Fuzzy-Fallback über Scryfalls eigene Suche:** eine namensbasierte
   Karte, die die exakte Collection-Suche nicht findet (fehlendes Komma,
   krummer Apostroph, Gedankenstrich statt Bindestrich, ...) wird jetzt
   automatisch einmal über `/cards/named?fuzzy=...` nachgeschlagen, bevor
   sie als nicht identifizierbar gilt. Das behebt die "Sarkhan the
   Dragonspeaker"-Klasse von Fehlern automatisch, ohne dass hier weiter
   geraten werden muss — Scryfalls eigener Fuzzy-Matcher ist die
   Instanz, die "meintest du X" tatsächlich beantworten kann, nicht wir.

**Zur konkreten Fehlerliste des Nutzers:** `Duskwatch Recruiter` (Old
Gnawbone) und `Nicol Bolas, the Ravager` (The Ur-Dragon, vom Nutzer als
"Nicolas Bolas, the Ravanger" transkribiert) sind beides echte
doppelseitige Karten (Transform bzw. planeswalker-Transform) — beide sollten
mit diesem Fix jetzt tatsächlich (nicht nur behauptet) funktionieren, da der
Fix jetzt in der live gebundenen Methode steckt. `Brazen Borrower`
(Adventure-Karte, gleicher `card_faces`-Mechanismus) ebenso. Für `Kirol,
History Buff` (Lorehold Spirit), `Elusive Otter` (Quandrix Unlimited),
`Defacing Duskmage` (Silverquill Influence) und `Eccentric Pestfinder`
(Witherbloom Pestilence) gilt: das sind reale Karten aus offenbar sehr
neuen (2026er) Sets, zu denen schlicht keine verlässliche Kenntnis vorliegt,
um Tippfehler zu erkennen oder auszuschließen — hier muss der neue
Fuzzy-Fallback zeigen, ob es sich um kleine Formatierungsabweichungen
handelt oder um etwas, das eine echte manuelle Korrektur der Deck-Datei
braucht.

**Neu: `check_fremd_decks.py`** (Projekt-Root) — ein eigenständiges Skript,
das ALLE Decks unter `Decks/Fremd/` (inkl. `Precons/`) nacheinander lädt
(nur Metadaten-Auflösung, keine volle Simulation), OHNE beim ersten
Ladefehler abzubrechen, und am Ende eine vollständige Zusammenfassung mit
Status pro Deck ausgibt (inkl. aller nicht auflösbaren Kartennamen dank der
neuen Fehler-Aggregation). Muss lokal mit echtem Internetzugang laufen
(`python check_fremd_decks.py`) — von der Cloud-Sandbox aus ist Scryfall
weiterhin blockiert, weshalb dieses Skript dort nicht selbst ausgeführt
werden konnte.

Volle Suite (348 Tests, davon 6 neu für dieses Kapitel) grün, keine
Regression.

**Update — Nutzer-Bestätigung + Testsuite-Integration (task #24/#25
abgeschlossen):** der Nutzer hat `check_fremd_decks.py` lokal laufen lassen
und alle 12 Fremd-Decks erfolgreich gebaut (elf frische
`v4_7_0`-Ergebnis-Bundles zurückgeschickt; Krenko/Scarab
God/Korvold liefen bereits vorher erfolgreich). Alle 12 zeigen
`engine_invariants: {"resource_invariant_violations": 0,
"payment_resource_conflicts": 0, "status": "PASS"}` — keine Auffälligkeit.
Einzige Anmerkung: bei Quandrix Unlimited wurde im GUI versehentlich
„Primo, the Unbounded" statt des echten Precon-Commanders „Zimone, Infinite
Analyst" als Commander gewählt (Nutzer bestätigt: für die reine Testphase
unerheblich, keine Korrektur nötig).

Die 12 Decks sind jetzt als feste, netzwerkfreie Regressionstests in
`tests/test_decklist_parsing.py::FremdDeckFilesParseCleanlyTests`
aufgenommen (Parser sauber, keine verstümmelten Namen, exakt 100 Karten
total, `detect_commander_hints` liefert die tatsächlich beim echten Lauf
verwendete Commander-Auswahl — bzw. bewusst leer für die 3 Dateien ohne
Header/Annotation: The Ur-Dragon, Quandrix Unlimited, Prismari Artistry).
Dieselbe 100-Karten-Prüfung wurde rückwirkend auch den 4 ursprünglichen
Decks (`RealDeckFilesParseCleanlyTests`) hinzugefügt, da alle vier sie
ebenfalls erfüllen. Volle Suite: 360 Tests grün, keine Regression.

## v4.16.0 — Fremd-Deck-Phase: echte Import-Bugs aus dem ersten lokalen Online-Lauf gefixt + 7 echte Precons importiert

**Ausgangslage:** der Nutzer hat 3 der 5 v4.15.9-Fremd-Decks (Krenko Mob
Boss, The Scarab God, Korvold Fae-Cursed King) einmal lokal mit echtem
Internetzugang laufen lassen (wie in v4.15.9 als offener Punkt vereinbart)
und die vollständigen `v4_7_0`-Ergebnis-Bundles zurückgeschickt — alle drei
mit `engine_invariants: PASS`, keine Resource-Konflikte. Die übrigen zwei
Decks (Old Gnawbone, The Ur-Dragon) scheiterten am Import mit zwei echten
Fehlern:

- `No metadata for Duskwatch Recruiter`
- `No metadata for Dragonspeaker` (Ur-Dragon-Liste enthielt versehentlich
  `Sarkhan the Dragonspeaker` ohne Komma — korrekter Kartenname ist
  `Sarkhan, the Dragonspeaker`; als reiner Datenfehler in der Decklist-Datei
  korrigiert, kein Code-Fix)

**Echter Code-Bug gefunden und gefixt — doppelseitige Karten (DFC) bei
Namens-only-Lookup:** `Duskwatch Recruiter` ist eine echte
Transform-Karte (Vorderseite `Duskwatch Recruiter`, Rückseite `Krallenhorde
Howler`). Scryfalls Collection-API liefert für eine solche Karte ein Objekt
mit dem KOMBINIERTEN Namen `"Duskwatch Recruiter // Krallenhorde Howler"`
im obersten `name`-Feld zurück — landet also nicht in `not_found` (Scryfall
hat die Karte klar gefunden), aber `ScryfallProvider.get_many()` indizierte
`by_name` bisher nur unter diesem kombinierten Namen. Eine Decklist-Zeile,
die (wie praktisch jeder echte Export) nur die Vorderseite nennt
(`Duskwatch Recruiter`), fand darüber keinen Treffer mehr, obwohl die Karte
tatsächlich geladen wurde — daher die irreführende Meldung „No metadata für
X" statt eines harten, klar benannten Scryfall-Fehlers. Fix: die
Indizierungs-Logik wurde in eine eigene, netzwerkfreie Funktion
`index_scryfall_cards()` ausgelagert (dadurch direkt testbar ohne
Netzzugriff) und indiziert jetzt zusätzlich jeden einzelnen `card_faces`-
Namen (kombinierter Treffer hat weiterhin Vorrang, wird nie überschrieben).

**Zweiter echter Format-Fund — Precon-Text-Exporte ganz ohne Header:** der
Nutzer hat 7 echte, offizielle Wizards-Precon-Decklisten eingereicht
(Secrets of Strixhaven Commander ×5, Lorwyn Eclipsed Commander, Tarkir:
Dragonstorm Commander). Diese Exporte nutzen GAR KEINEN Sektions-Header —
eine reine flache Kartenliste — und markieren den Commander stattdessen
(nicht einmal durchgängig) inline direkt auf seiner eigenen Zeile, z. B.
`1 Dina, Essence Brewer (Commander)`. Ungehandhabt wäre dieses Suffix genau
wie früher ein Foil-Marker in den geparsten Kartennamen gerutscht und hätte
den Scryfall-Lookup zerstört. Fix:

- `load_txt_entries` entfernt ein abschließendes `(Commander)`
  (case-insensitive) von jeder Kartenzeile, bevor der Name irgendwo
  verwendet wird.
- `detect_commander_hints` erkennt dieselbe Inline-Annotation jetzt
  zusätzlich zur bestehenden Header-basierten Erkennung — unabhängig davon,
  ob überhaupt ein Header existiert — und dedupliziert gegen
  Header-Treffer.
- Nicht jede reale Precon-Zeile trägt die Annotation (2 der 7 eingereichten
  Listen markieren den Commander gar nicht); für diesen Fall bleibt das
  bestehende Verhalten (Import gelingt trotzdem, Commander muss im GUI
  manuell gewählt werden) unverändert und ist bewusst kein Fehler.

**Neue Fremd-Decks (7 echte, offizielle Precon-Decklisten, unverändert
importiert nach `Decks/Fremd/Precons/`):** Witherbloom Pestilence (BG,
Dina Essence Brewer), Silverquill Influence (WB, Killian Decisive Mentor),
Quandrix Unlimited (GU, Zimone Infinite Analyst — keine Inline-Annotation),
Lorehold Spirit (RW, Quintorius History Chaser), Prismari Artistry (UR,
Rootha Mastering the Moment — keine Inline-Annotation), Blight Curse (BRG,
Auntie Ool Cursewretch), Sultai Arisen (BUG, Teval the Balanced Scale).
Alle 12 Fremd-Decks (5 aus v4.15.9 + diese 7) parsen jetzt sauber, je genau
100 Karten, keine Duplikate, keine übrig gebliebenen Annotationen.

**Kombo-Loop-Hinweis vom Nutzer (Design-Notiz, kein Bug-Fix in dieser
Version):** Decks können echte Infinite-Combos enthalten. Manche sind
tatsächlich unbrechbare Loops (werden in der Praxis meist durch einen
Spielfehler ausgelöst und enden in einem Draw) — solche sollen NICHT
simuliert werden. Andere Loops fragen zwischenzeitlich state-based actions
ab oder sind abbrechbar — diese sind erwünscht und sollen sauber
funktionieren. Die 3 erfolgreichen lokalen Läufe zeigen aktuell keine
Auffälligkeit (`engine_invariants: PASS`, keine Anomalien in
`turns.csv`/`combo_scenarios.json`); im Engine-Code existiert bisher aber
auch kein genereller Loop-Breaker (nur die bereits vorhandene, konfigurierte
Obergrenze `max_food_activations_per_turn` für Food-spezifische
Wiederholungen). Da eine Unterscheidung "unbrechbar → Draw" vs.
"unterbrechbar → normal weiterspielen" ein eigenständiges Engine-Design
braucht (und laut Projekt-Konvention keine Kalibrierungswerte ohne
Evidenz erfunden werden sollen), wird das bewusst NICHT in dieser Version
mit-gefixt, sondern als eigener, klar abgegrenzter Folge-Task vorgemerkt.

Volle Suite (342 Tests, davon 12 neu für dieses Kapitel) grün, keine
Regression. Alle 12 Fremd-Deck-Dateien parser-verifiziert
(`load_txt_entries` + `detect_commander_hints`, ohne Netzzugriff).

## v4.15.9 — Start Fremd-Deck-Phase: Deck-Parser robuster gegen unterschiedliche Export-Schreibweisen

**Ausgangslage:** erster Schritt der neuen Phase nach WP6 — echte, fremde
Commander-Decks (EDHREC/Moxfield) testen. Bevor Decklisten von dort
importiert werden, musste der TXT-Parser (`TXT_LINE_RE`, `load_txt_entries`,
`detect_commander_hints` in `App/engine.py`) robuster gegen die real
existierende Formatvielfalt werden — vorher krachte jede Zeile, die nicht
exakt `<Anzahl> <Name> [(SET) Sammelnummer [*Foil*]]` entsprach, mit einem
harten `ValueError` (z. B. jede Kategorie-Überschrift ohne führendes `//`).

**Recherche:** da direkter Scryfall-/Moxfield-Zugriff aus der Cloud-Umgebung
teils blockiert ist (SPA-Seiten, robots.txt), wurden die real dokumentierten
Konventionen über den quellenoffenen Cross-Site-Importer decklist.gg
verifiziert (der genau die Header-Familien Commander/Commanders/EDH,
Deck/Main Deck/Maindeck/Mainboard, Sideboard/Side Board/SB/Maybeboard,
Companion sowie beide Mengennotationen `4 Card` und `4x Card` dokumentiert)
sowie über EDHRECs eigenen Nutzungsleitfaden (Clipboard-Export als reiner
Text, ohne Set/Sammelnummer).

**Fixes (alle rückwärtskompatibel, 0 Regression an den 4 bestehenden Decks):**

- **Mengennotation:** `4x Lightning Bolt` wird jetzt neben `4 Lightning
  Bolt` akzeptiert.
- **Foil-Marker ohne Set/Sammelnummer:** `1 Sol Ring *F*` (ohne
  vorangehendes `(SET) Nummer`) wurde vorher komplett in den Kartennamen
  gemischt (fehlgeschlagener Scryfall-Lookup); der Foil-Marker ist jetzt
  eine unabhängige, optionale Gruppe.
- **Freistehende Sektions-Header ohne `//`:** `Commander`, `Commanders`,
  `EDH`, `Deck`, `Main Deck`, `Maindeck`, `Mainboard`, `Sideboard`, `Side
  Board`, `SB`, `Maybeboard`, `Companion` (case-insensitive, optionaler
  Zähler wie `Sideboard (5)` wird abgeschnitten) werden jetzt erkannt und
  schalten den Sideboard-Status genauso wie das bisherige `// ...`-Format.
- **Tolerante Restfälle:** jede andere Zeile ohne führende Ziffer (eine
  unbekannte Kategorie-Überschrift wie `Creatures (24)`, ein
  Freitext-Absatz wie Moxfields `About`-Metadatenblock) wird jetzt als
  Kommentar übersprungen statt den Import abzubrechen. Das
  Sicherheitsnetz bleibt bestehen: eine Zeile, die MIT einer Ziffer
  beginnt, aber trotzdem nicht geparst werden kann, wirft weiterhin einen
  Fehler (z. B. echte Zeilenverstümmelung).
- `detect_commander_hints` (GUI-Vorauswahl des Commanders vor dem vollen
  Deck-Build) erkennt dieselben Header jetzt ebenfalls ohne `//`.

**Offener Punkt (kein Code-Fix, sondern eine Infrastruktur-Frage):** der
Scryfall-Metadaten-Cache (`App/.scryfall_card_cache_v4.json`) wird
set+sammelnummer-basiert befüllt; ein Karten-Import ganz ohne Set-Angabe
(wie EDHRECs Clipboard-Export ihn liefert) braucht entweder einen echten
Online-Lauf oder einen Namens-basierten Cache-Eintrag. Direkter
Scryfall-Zugriff ist aus der Cloud-Sandbox blockiert (Organisations-Policy
+ Scryfall selbst weist automatisierte Anfragen ab). Für die als Nächstes
folgenden Fremd-Decks wird der Cache deshalb einmalig lokal (mit
normalem Internetzugang, nicht `--offline`) aufgebaut.

Volle Suite (330 Tests, davon 30 neu für dieses Kapitel) grün, keine
Regression; End-to-End-Smoke-Lauf gegen alle 4 bestehenden Decks bestätigt
`engine_invariants: PASS`.

## v4.15.8 — WP6 Abschluss: Interne Verifikation (task #19) + gefundener Doku/Code-Drift in SCENARIO_SCHEMA.md

**Ausgangslage:** letzter Schritt von WP6 vor der zukünftigen EDHREC/Moxfield-
Fremd-Deck-Phase — ein abschließender Verifikationsdurchgang über das eigene
Karten-/Mechanik-/Zug-Verständnis (task #19), nicht mehr Feature-Arbeit.

**Vorgehen (evidenzbasiert, real gegen alle 4 Projekt-Decks):**

1. Volle Testsuite (312 Tests) grün.
2. Echte End-to-End-Smoke-Runs (25/200 Runs) für alle 4 Decks (Aziza V2,
   Bilbo V1, Katara V3, Mice with Swords) — durchgängig
   `engine_invariants: PASS`, keine Abstürze.
3. `card_model_coverage.csv` aller 4 Decks geprüft: keine einzige Karte auf
   `none` (komplett unmodelliert); die einzigen `partial`-Karten sind die
   bereits aus der v4.15.6-Review bewusst offen gelassenen drei (Gyome,
   Kambal, Lobelia — Opponent-Interaktion, außerhalb des WP6-Scopes).
4. Voller Sweep über den kompletten eigenen Scryfall-Cache-Kartenpool aller
   4 Decks (283 eindeutige Karten) gegen den `unrecognized_sacrifice_cost`-
   Guard aus v4.15.6: 17 Fähigkeiten mit ungedecktem Sacrifice-Kostentext
   gefunden — alle entweder korrekt in `DEDICATED_RESOLVERS` ausgeschlossen
   (Baron Bertram, Lobelia, Peregrin Took) oder korrekt fail-closed nie
   automatisch ausgeführt (u. a. Evolving Wilds, Terramorphic Expanse,
   Myriad Landscape, Commander's Sphere, Mind Stone, Nettle Guard). Bestätigt:
   der v4.15.6-Fix wirkt vollständig über den echten Kartenpool, keine
   Rest-Lücke gefunden. (Diese Karten liefern dadurch aktuell auch KEINEN
   Wert aus ihrer Sacrifice-Fähigkeit — sicher, aber eine dokumentierte
   Unterschätzung für ein mögliches späteres Work Package, kein Bug.)

**Konkreter Fund (Dokumentations-/Code-Drift, jetzt behoben):** die
automatisch generierte `SCENARIO_SCHEMA.md` (landet in jedem Ergebnis-ZIP,
Referenztext für menschliche UND KI-gestützte Szenario-Autoren) war seit
Einführung des v4.4 "derived"-Blocks (`resource_available`,
`opponent_life_at_or_below`, `x_spell_lethal`, `commander_damage_lethal`)
nie aktualisiert worden — sie beschrieb weiterhin nur das alte v4.2-Schema
ohne jede Erwähnung von `derived[]`. Das hätte insbesondere die kommende
EDHREC/Moxfield-Phase (KI-gestützte Szenario-Autorenschaft für fremde
Decks) in die Irre geführt. Fix: `scenario_json_schema_markdown()`
aktualisiert (Version, neuer `## Derived conditions`-Abschnitt mit allen 4
implementierten Prädikat-Typen aus `definitions.json`, inkl. der
v4.15.6/7-Teilkredit-Erweiterung; Minimalbeispiel um ein `derived`-Feld
ergänzt). 2 neue Regressionstests, die künftiges erneutes Auseinanderlaufen
zwischen Doku und implementierten Prädikat-Typen aktiv verhindern.

Volle Suite (312 Tests, 1 übersprungen) grün, keine Regression. Damit ist
WP6 (task #10–#19) vollständig abgeschlossen.

## v4.15.7 — WP6: Kleinere offene Punkte (task #18) — Farblos-Fallback-Recherche, Token-Kurve-Audit, derived-Teilkredit, Voltron-GUI-Feld

**Ausgangslage:** die vier restlichen, als "kleiner" eingestuften offenen
Punkte aus der WP6-Aufgabenliste (task #18), nach Abschluss der
Coverage-Review in v4.15.6.

**1. Farblos-Fallback-Recherche (`color_category_multiplier`):** die alte
Konstante für farblose Karten (`color_category_multipliers_colorless_fallback:
0.5`) war ein geratener Platzhalter ohne Quelle. Recherche (WebSearch/
WebFetch) fand eine offizielle WotC-Designaussage von Mark Rosewater
("Just Artifacts, Ma'am", magic.wizards.com, 2005; bestätigt auch von
edhrec.com/articles/are-colorless-cards-part-of-magics-color-pie):
"any ability you give to artifacts you are giving to the weakest color
in that ability." Umsetzung: farblose Karten werden jetzt am schlechtesten
Wert in der jeweils relevanten Kategorie-Tabelle selbst gefloored
(`min()` über die 5 Farbwerte der Kategorie), statt einer pauschalen,
kategorie-unabhängigen Konstante. Die alte Konstante bleibt nur noch als
letzter Notfall-Fallback für eine Kategorie ganz ohne Farbtabelle (sollte
in der Praxis nicht mehr erreicht werden). 3 betroffene Tests aktualisiert,
1 neuer Test für den echten Notfall-Fallback-Pfad ergänzt.

**2. Token-Kurve — Audit-Ergebnis: bereits vollständig umgesetzt.**
Geprüft, ob die "erhöhte Rückkehr bei mehr Token"-Idee noch fehlt. Ergebnis:
der v4.10.0-Mechanismus (`ValueModel.curved_count`, `value_curve_exponents.
creature_tokens = 1.15` in `goldfish_value_model.json`) ist bereits
durchgängig verdrahtet — jede Token-Erzeugung läuft über den einen
Chokepoint `create_tokens`, der `record_impact(..., "creature_tokens", ...)`
aufruft, und dieser Metrik-Pfad wendet die Kurve bereits an
(inkl. der neuen v4.15.6-Token-Karten wie Trudge Garden). Kein Code-Fix
nötig; dieser Punkt war de facto schon aus früherer Arbeit erledigt.

**3. Derived-Teilkredit (`scenario_feasibility`):** die "derived"-Prädikate
im Scenario-Schema v4.4 (`resource_available`, `opponent_life_at_or_below`,
`x_spell_lethal`, `commander_damage_lethal`) gaben bislang nur binär 1.0/0.0
Kredit — ein explizit als Vereinfachung markierter v4.15.0-Kommentar. Fix:
neues optionales Feld `PredicateResult.progress` (0..1, von jedem Handler
selbst berechnet, aus Daten, die er ohnehin schon hat — keine
Duplizierung der "wie nah dran"-Logik an zentraler Stelle) plus
`effective_progress`-Property (fällt ohne gesetztes `progress` auf die alte
binäre Lesart zurück, jeder Alt-Handler bleibt also unverändert korrekt).
`scenario_feasibility` nutzt jetzt den Mittelwert von `effective_progress`
über alle derived-Prädikate statt der binären Summe. 4 neue Tests.

**4. Voltron-GUI-Feld:** `Strategy.voltron_target_index` (seit v4.15.0 im
Engine/JSON-Layer voll funktionsfähig, siehe `attack_phase`) hatte bislang
keine GUI-Anbindung — nur über eine handgeschriebene Strategy-JSON-Datei
erreichbar. Jetzt: neues Kombinationsfeld "Voltron-Ziel" (Aus/Gegner 0/1/2)
in der Simulation-Einstellungsleiste, neben "Opponent". Verdrahtung: neuer
`voltron_target_index`-Parameter auf `run_pipeline_v440` (überschreibt einen
per Strategy-Datei gesetzten Wert nur, wenn die GUI explizit einen Wert
gewählt hat — "Aus" löscht einen vorhandenen Strategy-Datei-Wert NICHT
versehentlich), Übernahme in `run_simulation`/`_simulation_worker`, sowie
Persistenz in `.goldfish.json`-Projektdateien (`project_payload_v43`/
`load_project_v43`, rückwärtskompatibel — fehlt der Schlüssel in einer
alten Projektdatei, wird "Aus"/`None` angenommen). Die eigentliche
Kampf-Logik (`attack_phase`) war bereits vorher korrekt und ist unverändert;
dieser Fix betrifft ausschließlich die Erreichbarkeit über die GUI. Die
Override-Logik wurde in eine eigene, direkt testbare Funktion
(`apply_voltron_target_override`) ausgelagert, statt inline in der
schweren Pipeline-Funktion zu bleiben. 8 neue Tests (Override-Logik +
Projektdatei-Rundtrip inkl. Rückwärtskompatibilität).

Volle Suite (310 Tests, 1 übersprungen) grün, keine Regression.

## v4.15.6 — WP6: Card-Model-Coverage-Review (11 partial/partial+ Karten) + wichtiger Fund: ungedeckelte Sacrifice-Kosten

**Ausgangslage:** planmäßige Review-Runde (task #17) über die 11 in
`KNOWN_COVERAGE_NOTES` als `partial`/`partial+` markierten Karten (alle aus
Bilbo V1.txt), mit dem Ziel, echte, im Scope liegende Lücken zu schließen
und den Rest bewusst und begründet offen zu lassen.

**Wichtigster Fund (kein Feature, ein Korrektheits-Bug):** beim Review von
Baron Bertram Graywaters `{1}{B}, Sacrifice another creature or artifact:
Draw a card.` fiel auf, dass diese Karte NICHT in `DEDICATED_RESOLVERS` war
und ihr Sacrifice-Kostentext vom generischen Parser nicht erkannt wird (nur
Food/Treasure/Clue werden erkannt). Der generische Aktivierungs-Loop
(`try_generic_semantic_activations`) hätte deshalb nur die {1}{B}-Mana
bezahlt und das Sacrifice komplett übersprungen — ein kostenloser Karten-Zug.
Eine anschließende Sweep-Prüfung über den kompletten eigenen Scryfall-Cache
(`App/.scryfall_card_cache_v4.json`) zeigte: das Muster betraf nicht nur
Baron Bertram, sondern u. a. auch echte Karten im eigenen Manabase
(Evolving Wilds, Mind Stone, Burnished Hart, Commander's Sphere, Myriad
Landscape, Wayfarer's Bauble, Gates of Istfell, Skybridge Towers, Axgard
Armory, Terramorphic Expanse, Nettle Guard, Glittering Stockpile) —
"Sacrifice this land/artifact/creature: ..."-Kosten wären potenziell jede
Runde kostenlos ausgelöst worden, OHNE dass die Quelle je das Battlefield
verlässt (einmal pro Runde pro Quelle, aber die Quelle bleibt liegen).

**Fix (an der Wurzel, nicht nur für eine Karte):** neues Feld
`SemanticAbility.unrecognized_sacrifice_cost` — gesetzt, wenn eine
`activated`-Fähigkeit "sacrifice" im Kostentext enthält, aber kein
Food/Treasure/Clue-Muster matcht. `execute_semantic_ability` und
`try_semantic_board_protection` (beide Ausführungspfade) verweigern jetzt
die Ausführung, wenn dieses Flag gesetzt ist — fail closed statt fail open,
gilt automatisch für jede zukünftige Karte mit diesem Kosten-Shape, nicht
nur für händisch identifizierte Fälle.

**Zusätzlich geschlossene Feature-Lücken (4 der 11 Karten, jetzt `partial+`):**

- **Baron Bertram Graywater** — die Sacrifice-to-Draw-Linie ist jetzt real
  modelliert (`use_baron_bertram_sac_draw`): wandelt am Ende des Zugs ein
  wirklich übrig gebliebenes, ungenutztes Treasure in eine Karte, wenn
  {1}{B} noch bezahlbar ist. Kreaturen/Food dafür zu opfern bleibt bewusst
  unautomatisiert (echter strategischer Trade-off).
- **Trudge Garden** — das wiederholte "you may pay {2}, create a 4/4
  trample"-Trigger pro Lifegain-Event ist jetzt real modelliert
  (`use_trudge_garden`): ein Zähler pro echtem Lifegain-Ereignis
  (`trudge_garden_triggers_this_turn`, inkrementiert in `gain_life`), am
  Ende des Zugs gegen tatsächlich übrige Mana aufgelöst — gleiches Muster
  wie `use_well_of_lost_dreams`.
- **Field-Tested Frying Pan** — der Equip-Lifegain-Pump ("Equipped creature
  gets +X/+X ... where X is the amount of life gained") wird jetzt auf das
  eigene ETB-Halfling-Token angewendet (`frying_pan_bonus_this_turn`, in
  `token_group_power` verrechnet), solange Pfanne und Halfling im Spiel
  bleiben. Ein Umrüsten auf eine andere Kreatur wird nicht modelliert
  (Goldfish hat keinen Grund, das ETB-Ziel zu wechseln).
- **Moldervine Reclamation** — der Death-Trigger (1 Leben, 1 Karte pro
  gestorbener eigener Kreatur) feuert jetzt bei jedem tatsächlich
  getrackten Kreaturtod: echte Permanents über den gemeinsamen
  `move_permanent_to_zone`-Friedhof-Pfad, Token-Gruppen über einen
  separaten Hook direkt in `attack_phase` (Tokens sind keine Permanents und
  laufen nie durch `move_permanent_to_zone`).

**Bewusst unverändert gelassen (begründet, nicht vergessen):** Kambal
(Kopieren gegnerischer Tokens braucht Gegner-Deck-Wissen), Lobelia
(Stolen-Card-Modus braucht Gegner-Deck-Wissen), Gyome (die generische
Indestructible-Schutz-Engine existiert bereits, bleibt aber bewusst
reaktiv/entfernungs-getriggert und damit außerhalb des aktuellen
WP6-Scopes ohne Gegner-Turn-Interaktion) — alle drei bleiben in
`KNOWN_COVERAGE_NOTES` mit aktualisierter, präziserer Begründung stehen.
Gilded Goose, Unlucky Cabbage Merchant, Well of Lost Dreams und Bilbo waren
bereits `partial+` mit tragfähigen Notizen und wurden im Review bestätigt,
nicht weiter verändert.

**Tests:** `tests/test_wp6_lifegain_engine_review.py` (neu, 23 Tests) —
Sacrifice-Guard (direkt + generischer Loop + Sweep über echte Manabase-
Karten), Trudge Garden, Field-Tested Frying Pan, Baron Bertram, Moldervine
(beide Todes-Pfade). Volle Suite (297 Tests, 1 übersprungen) grün, keine
Regression. Zusätzlicher End-to-End-Smoke-Test (25 Runs, Bilbo V1) bestätigt
fehlerfreien Durchlauf.

## v4.15.5 — Board-Wipe-Selbst-Skalierung: echte Anbindung an den Payment-Pfad

**Ausgangslage:** `ValueModel.boardwipe_effective_cost_estimate` (seit v4.12.0)
lieferte nur eine reine Rangordnungs-Schätzung für Karten mit selbstbezüglicher
Kostenreduktion ("This spell costs {N} less to cast for each ...") — der
eigene Docstring flaggte klar: "wiring the actual payment/casting path ... is
a separate, not-yet-built feature". Der reale `cast_option`-Payment-Pfad
kannte bisher nur externe Reduktionen (`effective_cost_discount`, z. B. "Cost
Reducer"-Permanents), nicht die Selbstreferenz einer Karte auf ihren eigenen
Text.

**Umgesetzt:** neue Modul-Funktion `boardwipe_self_scaling_discount(card,
state)` in `App/engine.py` — parst den Karten-eigenen "costs {N} less ... for
each <condition>"-Text direkt (nicht nur ein caller-übergebenes
`scaling_count` wie die bestehende Schätz-Methode) und liefert einen echten
Rabatt aus dem tatsächlichen Board-/Friedhof-Zustand. Erkannte Bedingungen:
Kreaturen/Artefakte unter eigener Kontrolle, Friedhof-Karten (optional nach
Instant/Sorcery/Kreatur gefiltert), Gegner-Anzahl — ein nicht erkannter
Bedingungstext liefert bewusst 0 statt geraten zu werden (gleiche Vorsicht
wie bei `effective_cost_discount`). In `cast_option` (Nicht-X-Zweig) additiv
zu `effective_cost_discount` verrechnet; beide Rabatt-Quellen erscheinen
gemeinsam in `discount_attribution`.

**Bewusst ausgeschlossen:** Additional-Cost-CHOICE-Skalierung ("As an
additional cost ..., exile ... this way") — mechanisch etwas anderes (eine
Wahl beim Bezahlen, kein passiver Board-Zustand). Reales Beispiel: March of
Wretched Sorrow (Bilbo V1.txt) — bleibt unangetastet, ohnehin irrelevant, da
X-Spells `cast_option`s X-Zweig nie durch `effective_cost_discount` laufen.

**Grounding an echten Projekt-Karten:** Furygale Flocking (Aziza V2.txt,
"{1} less ... for each instant and sorcery card in your graveyard") —
gedruckte {8}{R}{R} (10), mit 3 Instants/Sorcerys im Friedhof jetzt real 7 im
Payment-Pfad. Ein synthetisches Blasphemous-Act-Muster ("for each other
creature you control") bestätigt zusätzlich, dass "other" beim Bezahlen einer
Karte, die noch nicht auf dem Battlefield liegt, keine Karten vom Board
abzieht (Regel-Präzisierung gegenüber der ersten Implementierung, per Test
gefunden und korrigiert).

**Tests:** `tests/test_boardwipe_payment_path.py` (neu, 10 Tests) — 6
Unit-Tests direkt gegen `boardwipe_self_scaling_discount` (Furygale Flocking
real, Kreaturen-Zählung übers ganze Board, 0-Fälle, March-of-Wretched-Sorrow-
Ausschluss, unbekannte Bedingung), 4 End-to-End-Tests durch das echte
`cast_option` (Gesamtkosten inkl. Rabatt, kein Friedhof-Fuel, farbige-Pips-
Untergrenze bei 50 Kreaturen, externer + Selbst-Skalierungs-Rabatt kombiniert
additiv in einem `discount_attribution`-Dict). Volle Suite (274 Tests, 1
übersprungen) grün, keine Regression.

## v4.15.4 — Ressourcen-zu-Mana-Konversion (Leben, Delve, Convoke/Improvise, Opfern, Stun-Counter, Uptime)

**Ausgangslage:** die größte einzelne offene Lücke laut Inventory. `Docs/
DEFAULT_VALUES_AND_COLOR_PIE_v1.md` Abschnitt 5.1/5.1.1 und `Data/Models/
default_value_table_and_color_pie.json::resource_to_mana_conversion` hatten
das Framework vollständig durchdacht (Leben, Opfern, Delve, Convoke/
Improvise, Discard, Echo, Stun-Counter, Suspend, Decayed, bedingte Angriffs-
sperren) — 0 % davon war im Code umgesetzt (per grep bestätigt).

**Umgesetzt (7 neue `ValueModel`-Methoden, `App/engine.py`), gespiegelt in
`Data/Models/goldfish_value_model.json::resource_to_mana_conversion`:**

- `life_as_mana_equivalent` — **offizieller WotC-Kurs** aus dem Phyrexian-
  Mana-Templating (New Phyrexia {C/P}: 1 farbiges Mana ODER 2 Leben zahlen):
  **2 Leben = 1 Mana** (`life_as_cost_rate: 0,5`).
- `delve_mana_equivalent` — **offizieller Kurs**: eine Friedhofskarte exilieren
  ersetzt exakt {1} generisches Mana (Treasure Cruise, Dig Through Time,
  Tasigur) — `delve_rate: 1,0`.
- `convoke_improvise_mana_equivalent` — **offizieller Kurs**: eine ungetappte
  Kreatur/ein Artefakt tappen ersetzt {1} generisches Mana —
  `convoke_improvise_rate: 1,0`. Echtes Projekt-Beispiel: **Hour of
  Reckoning** (`Decks/Aziza V2.txt`, Convoke, {4}{W}{W}{W}).
- `sacrifice_cost_equivalent` — **dynamischer Lookup statt fester Zahl**,
  offiziell bestätigt durch Emerges eigenen Reminder-Text ("gleich dem
  Mana-Wert der exilierten Kreatur"): nutzt `predefined_static_value` der
  konkret geopferten Karte — ein 1-Mana-Token kostet fast nichts, eine
  fertig ausgebaute Bombe ist teuer.
- `stun_counter_value_multiplier` (bevorzugte Methode: prozentualer Abschlag
  auf den EIGENEN Wert des betroffenen Permanents) und
  `stun_counter_mana_equivalent_fallback` (Fallback: fixer Mana-Betrag, nur
  falls der Permanent-Wert selbst noch unbekannt ist) — **niedrige
  Konfidenz**, klar so gekennzeichnet: anders als bei Leben/Delve/Convoke
  gibt es hier KEINEN offiziellen Umrechnungskurs, `stun_counter_value_
  discount_per_counter: 0,15` ist ein Erst-Schätzwert.
- `uptime_value_discount` — allgemeine Bucket-B-Form (Leben/Delve/Convoke/
  Opfern sind Bucket A: eine echte Ressource wechselt den Besitzer; Stun-
  Counter/Suspend/Decayed/bedingte Angriffssperren sind Bucket B: keine
  Ressource wird bezahlt, nur die Nutzbarkeit ist eingeschränkt — eine
  Mana-Umrechnung wäre hier laut Konzept-Doku ein Kategorienfehler). EINE
  gemeinsame Implementierung für bedingte Angriffs-/Blocksperren, Suspend
  und Decayed, genau wie die Konzept-Doku es explizit vorschlägt ("dieselbe
  Bucket-B-Logik, keine neue Formel nötig") — keine drei separaten,
  fast identischen Methoden.

**Bewusster Scope-Rahmen, klar benannt (gleiche Praxis wie bei
`boardwipe_effective_cost_estimate`):** dies sind reine
Value-Estimation-Utilities. Sie ändern NICHT, was ein Zauber tatsächlich
bezahlen kann — der echte Payment-Pfad (`available_mana_value`) bleibt
unverändert. Eine echte alternative-Kosten-bewusste Zahlungssimulation ist
ein separates, größeres, noch nicht gebautes Feature (dieselbe Klasse Lücke
wie beim Board-Wipe-Schätzer, siehe Aufgabenliste Punkt "Board-Wipe an
echten Payment-Pfad anbinden").

**Verifiziert mit 30 neuen Tests** (`tests/test_resource_to_mana_conversion.py`):
Leben/Delve/Convoke mit den zitierten offiziellen Kursen geprüft (inkl.
einem Treasure-Cruise-förmigen Beispiel und einem echten Hour-of-Reckoning-
förmigen Beispiel mit den tatsächlichen Kartendaten aus `Decks/Aziza
V2.txt`), Opfern mit größerer/kleinerer Kreatur (unterschiedliche Kosten,
nie negativ, funktioniert auch ohne explizite Strategy), Stun-Counter
strukturell geprüft (monoton fallend, nie negativ, bevorzugte und Fallback-
Methode unabhängig konfigurierbar — keine der beiden Zahlen wird als
"korrekt" behauptet, nur als Erst-Schätzwert), Uptime-Discount inkl.
Clamping in beide Richtungen, ein Regressions-Test, dass `Data/Models/
goldfish_value_model.json` exakt mit `DEFAULT_VALUE_MODEL` übereinstimmt
(Projekt-Konvention), sowie ein Fallback-Test für alte Strategy-Dateien ohne
diesen Abschnitt. Gesamt-Suite: **264/264 grün** (234 bisherige + 30 neue,
1 weiterhin bewusst übersprungen wegen fehlender Datendatei in diesem
Cowork-Checkout).

**Weiterhin bewusst NICHT umgesetzt:** Discard-als-Zusatzkosten (nutzt laut
Konzept-Doku bewusst den bestehenden `discard_self`-Knopf statt einer neuen
Zahl — kein neuer Code nötig) und Echo (zeitversetzte Zahlung, laut
Konzept-Doku nur katalogisiert, nicht ausgearbeitet — bleibt offen).

## v4.15.3 — Equipment-Lücken: dynamische X-Boni, zwei generische Attack-Trigger-Familien

**Ausgangslage** (`App/combat_model/equipment.py`, seit WP7): drei benannte
Lücken. Geprüft anhand der ECHTEN Mabel-Deckliste (`Decks/Mice with
Swords.txt`) und ihrer tatsächlichen Oracle-Texte (Scryfall-Cache dieses
Checkouts):

1. **Dynamische P/T-Boni** (`gets +X/+0, where X is the number of _ counters
   on this Equipment`, z. B. **Chainsaw**) — bisher ein echter, stiller
   Fehl-Parse: `_EQUIPPED_BONUS_RE` matchte nur literale Ziffern, "+X/+0"
   fiel komplett durch und wurde als 0/0 behandelt, ohne Fehler oder Warnung.
2. **"Whenever equipped creature attacks, ..."-Trigger** — komplett
   unimplementiert, obwohl im Moduldocstring seit WP7 als Lücke benannt.
   Reales Beispiel: **Captain America's Shield** ("tap target creature
   defending player controls").
3. **"Whenever equipped creature deals combat damage to a player, ..."-
   Trigger** — ebenfalls unimplementiert. Reales Beispiel: **Bloodforged
   Battle-Axe** ("create a token that's a copy of this Equipment").

**Fix 1 — dynamische X-Boni:** `parse_equipment_bonus` akzeptiert jetzt
sowohl eine nackte `Card` (statisch, altes Verhalten für X ohne Counter-Info)
als auch ein Equipment-`Permanent` (löst X über dessen eigene
`named_counters` auf). Neue Regex `_EQUIPPED_X_BONUS_RE`/`_X_DEFINITION_RE`
erkennen "+X/+N", "+N/+X" oder "+X/+X" plus die zugehörige "where X is the
number of _ counters on this Equipment"-Definition.

**Fix 2 — Attack-Tap-Trigger (Näherung):** da dieses Modell keine echten
gegnerischen Kreaturen kennt (siehe `interaction.py`-Moduldocstring), wird
der Tap-Effekt als reduzierte Blockchance FÜR DEN AUSGERÜSTETEN ANGREIFER
SELBST angenähert — neues Feld `AttackerInfo.equipment_evasion_multiplier`
(`App/combat_model/interaction.py`), neue Funktion
`equipment_attack_tap_multiplier` (`equipment.py`), neues Gewicht
`equipment.attack_tap_trigger_block_rate_multiplier` (Default **0,6**,
Erst-Schätzwert, `Data/Models/combat_interaction_weights.json`). Gleicher
Stil wie `evasion_keyword_multiplier` (Flying/Menace/Trample), nur
equipment- statt keyword-ausgelöst.

**Fix 3 — Combat-Damage-Copy-Trigger:** neue Funktion
`equipment_combat_damage_copy_triggers` erkennt das Trigger-Muster generisch
(Textform, kein Kartenname); `attack_phase` (`App/engine.py`) erstellt bei
JEDEM ungeblockten Schaden an einen Gegner (`outcome.damage_dealt > 0`
passiert laut `resolve_combat_interaction` nur bei ungeblockten Outcomes,
also exakt "dealt combat damage to a player") ein neues Equipment-`Permanent`
als Kopie der Karte.

**Bonus-Fund dabei — "Whenever one or more creatures die"-Counter (Chainsaw):**
damit Fix 1 für Chainsaw überhaupt etwas bewirkt, war ein Counter-Zähl-
Mechanismus nötig. Neue Funktion `creature_death_equipment_triggers`,
aufgerufen EINMAL pro Combat aus `attack_phase`, wenn mindestens ein Tod in
diesem Combat vorkam (real-regelkonform: ein Trigger pro Ereignis-Batch,
nicht pro Kreatur). **Bewusste Grenze:** nur an Combat-Tode gebunden — Tode
durch Spot-Removal, Board-Wipes oder Sacrifice außerhalb des Combats zählen
NICHT mit, weil dieses Modell ~18 verschiedene "in den Friedhof legen"-
Stellen im Code hat und ein vollständiger Hook einen größeren Refactor
bräuchte, der über diesen Equipment-Punkt hinausgeht. In README/Modul-
Docstring klar so benannt statt still halb-implementiert zu bleiben.

**Weiterhin bewusst NICHT umgesetzt:** Valiant (braucht weiterhin das noch
nicht existierende "Target Event"-Konzept) und eine echte farbgebundene
Mana-Payment-Simulation für `auto_equip_step` (bleibt bei der simplen
Gesamt-Manawert-Prüfung — ein echter Fix bräuchte dieselbe Payment-
Infrastruktur wie die separate Ressourcen-zu-Mana-Konversion, siehe
Aufgabenliste, statt einer Ad-hoc-Dopplung).

**Verifiziert mit 17 neuen Tests** (`tests/test_equipment.py`: 14 reine
Parsing-/Trigger-Funktionstests für alle drei Fixes gegen die ECHTEN
Kartentexte von Chainsaw/Captain America's Shield/Bloodforged Battle-Axe,
plus 3 End-to-End-Tests durch `engine.attack_phase` selbst — Token-Kopie
entsteht bei ungeblocktem Schaden, Rev-Counter entsteht bei einem echten
Combat-Tod, KEIN Rev-Counter ohne Tod). Zusätzlich mit einem echten 30-Run-
Smoke-Test gegen die komplette Mabel-Deckliste geprüft (`Decks/Mice with
Swords.txt`, alle drei Karten erscheinen wie erwartet in den Impact-Zeilen,
kein Crash). Gesamt-Suite: **234/234 grün** (217 bisherige + 17 neue, 1
weiterhin bewusst übersprungen wegen fehlender Datendatei in diesem
Cowork-Checkout).

Kein Value-Model-Update diese Version.

## v4.15.2 — WP6: Double Strike/First Strike — zweistufiger Combat-Schritt (angenähert)

**Ausgangslage:** seit v4.7.5 offen. `App/combat_model/interaction.py` kannte
bisher nur EINEN Effekt für `double strike`: unblockter Schaden wurde
verdoppelt. Das Prädikat `first strike` (Teil von `KEYWORDS` seit Projektbeginn,
mit eigenem Value-Model-Gewicht `0,35`, siehe `Data/Models/
default_value_table_and_color_pie.json`) hatte dagegen **keinerlei**
Combat-Wirkung — ein echter, beim Nachlesen des Codes gefundener Lücken-Fund,
nicht nur eine unvollständige Kalibrierung. Der eigentlich offene Punkt: ein
Angreifer mit First-/Double-Strike-Timing schlägt VOR einem normal-timed
Blocker zu und tötet diesen oft, bevor der Blocker selbst zurückschlagen kann
— sollte also seltener im Trade sterben als ein normaler Angreifer.

**Fix (Näherung, kein echtes Blocker-Statusmodell vorhanden):** neues Gewicht
`first_strike.trade_rate_multiplier` (`Data/Models/
combat_interaction_weights.json`, Default **0,5** — Erst-Schätzwert, kein
externes Referenzdatum verfügbar, gleiche Praxis wie
`commander_targeting.block_bias`/`x_spell_proximity_bonus_max`).
`resolve_combat_interaction` reduziert `trade_rate_given_blocked` mit diesem
Faktor für jeden geblockten Angreifer mit `first strike` ODER `double strike`
im Keyword-Set — beide bekommen bewusst DENSELBEN Faktor, weil beide im ersten
Schadensschritt gleich viel Power zufügen; der zweite Schlag von Double Strike
wirkt sich nur auf den GEGNER aus, nicht auf die eigene Überlebenschance im
Trade. Die bestehende Verdopplung des UNBLOCKED-Schadens bei `double strike`
bleibt unverändert (v4.7.5).

**Verifiziert mit 8 neuen Tests** (`tests/test_combat_interaction.py`,
`FirstStrikeTradeRateTests`): reine Multiplikator-Funktionsprüfung, Double
Strike bekommt exakt denselben Effekt wie First Strike (gleicher rng-Seed,
gleiches Ergebnis), `trade_rate_multiplier=1,0` reproduziert das alte
Verhalten (für First Strike war das vorher der EINZIGE Zustand, da First
Strike bislang gar keine Wirkung hatte), ein fehlender `first_strike`-Block in
den Gewichten fällt sicher auf `1,0` zurück, unbeteiligte Keywords (z. B.
`flying`) bleiben unberührt, ein Test gegen die echten, ungemockten
Projekt-Gewichte über 500 Angreifer (First-Strike-Angreifer sterben seltener
als baugleiche normale Angreifer) sowie ein Regressionstest, dass die
UNBLOCKED-Schadensverdopplung von Double Strike unverändert bleibt.
Gesamt-Suite: **217/217 grün** (209 bisherige + 8 neue, 1 weiterhin bewusst
übersprungen wegen fehlender Datendatei in diesem Cowork-Checkout).

Kein Value-Model-Update diese Version (reine Combat-Gewichts-Arbeit).
Bewusst NICHT umgesetzt: ein echtes zweistufiges Damage-Step-Modell mit
tatsächlichen Blocker-Powertoughness-Werten — dafür müsste das Combat-System
einen abstrakten Blocker mit eigenen Stats einführen, was über den Rahmen
dieses Punkts hinausgeht; die hier gewählte Näherung (reduzierte Trade-Rate)
ist im selben Stil wie alle anderen abstrakten Combat-Wahrscheinlichkeiten
(`block_rate_base`, `target_focus_chance`, `commander_targeting.block_bias`)
und macht keine falsche Präzision vor.

## v4.15.1 — WP6 Iteration 2+: Commander-spezifischer Block-Bias

**Ausgangslage:** seit v4.7.5 offen benannt: "the commander painted a target on
itself" — ein Commander ist ab Zug 1 öffentlich bekannt (Command Zone, meist die
zentrale Spielplan-Karte) und sollte deshalb beim gegnerischen Blocken bevorzugt
werden, unabhängig davon, ob er in diesem Run schon messbare Aktivität gezeigt
hat. Bisher gab es dafür **keinen** eigenen Mechanismus — nur den bereits
bestehenden, impact-basierten `importance_targeting.combat_block_weight`
(`App/combat_model/importance.py::combat_block_multiplier`), der einen
Commander erst bevorzugt, NACHDEM er in diesem Run bereits etwas Messbares
getan hat (Kampfschaden, Kartenzug-Trigger usw.) — in frühen Zügen also noch
gar nicht wirkt.

**Fix:** neues Gewicht `commander_targeting.block_bias`
(`Data/Models/combat_interaction_weights.json`, Default **1,25** — reiner
Erst-Schätzwert, kein externes Referenzdatum verfügbar, gleiche Praxis wie
`x_spell_proximity_bonus_max`/`value_curve_exponents`). `App/combat_model/
interaction.py::block_rate_for` bekommt einen neuen optionalen Parameter
`is_commander` (Default `False`, rückwärtskompatibel) und multipliziert die
Blockchance NUR für den Commander-Angreifer mit diesem Bias, zusätzlich zur
bestehenden Turn-Ramp-/Wide-Board-/Evasion-Kette und zum separaten
impact-basierten Bonus (beide Effekte stapeln bewusst — ein Commander, der
sowohl öffentlich bekannt ALS AUCH bereits aktiv war, ist plausibel ein noch
attraktiveres Blockziel). `resolve_combat_interaction` reicht `a.is_commander`
(bereits seit WP10 auf jedem `AttackerInfo` vorhanden) direkt durch — keine
Änderung an `attack_phase` selbst nötig, der `is_commander`-Flag wurde dort
schon für die Voltron-Zielfixierung gesetzt.

**Verifiziert mit 12 neuen Tests** (`tests/test_combat_interaction.py`,
`CommanderBlockBiasTests` + `AttackPhaseCommanderBlockBiasIntegrationTests`):
reiner `block_rate_for`-Vergleich (Commander > Nicht-Commander bei sonst
identischen Eingaben), `block_bias=1.0` reproduziert exakt das alte Verhalten,
extreme Werte bleiben auf `[0, 1]` geklammert, das "goldfish"-Profil (unsere
eigene Simulation) bleibt unberührt (`block_rate_base=0` greift vor dem
Bias-Multiplikator), ein Test gegen die echten, ungemockten Projekt-Gewichte
über 400 Angreifer sowie ein End-to-End-Test durch `engine.attack_phase`
selbst (mit `commander_posture="aggressive"`, um den separaten Posture-Gate-
Mechanismus — der einen einzelnen Commander sonst ganz vom Angriff abhalten
kann — bewusst zu umgehen und nicht mit dem hier getesteten Block-Bias zu
vermischen). Gesamt-Suite: **209/209 grün** (197 bisherige + 12 neue, 1
weiterhin bewusst übersprungen wegen fehlender Datendatei in diesem
Cowork-Checkout).

Damit gilt Punkt 3 der WP6-Aufgabenliste (Iteration 2+) als abgeschlossen.
Kein Value-Model-Update diese Version, reine Combat-Gewichts-Arbeit.

## Diagnostik (nach v4.15.0) — WP6, Punkt 1+2: Frischer 200er-Run (alle 4 Decks) + Combat-Gewichte-Review

**Kein Code-Change diese Eintragung** — `ENGINE_VERSION` bleibt `4.15.0`. Dies
ist die evidenzsammelnde Diagnostik für WP6 (siehe Task-Liste #10/#11), auf dem
aktuellen v4.15.0-Stand (Posture-Generalisierung, Equipment, Waterbend,
Value-Model-Routen B–E, WP10 — die v4.8.2/v4.8.3-Baseline-Daten waren nur mit
Bilbo und einem deutlich älteren Engine-Stand erhoben).

**Lauf-Protokoll** (identisch zu v4.8.2/v4.8.3, jetzt für alle 4 Decks statt
nur Bilbo): `runs=200, turns=10, seed=1, opponent_profile="random"`, kein
Scenario-File. Bilbo weiter mit `strategy_tags={"lifegain"}` (Kontinuität zum
Baseline-Vergleich); Katara/Aziza/Mabel ohne `strategy_tags` (automatische
Archetyp-Inferenz — es existierte nie ein vorheriger Tag-Baseline für diese
drei, also kein Kontinuitätsbruch). Skript: `run_diagnostics_v4_15_0.py`
(neu, im Projekt-Root, nicht Teil der Test-Suite — reines Diagnose-Werkzeug
wie `run_bilbo_v482.py`/`run_bilbo_v483.py`).

**Ergebnis — `combat_and_removal_diagnostics` (Removal-Konzentration auf den
Commander):**

| Deck | Removed gesamt | davon Commander | Commander-Anteil |
|---|---|---|---|
| Bilbo V1 | 135 | 42 | 31,1 % |
| Katara V3 | 180 | 55 | 30,6 % |
| Aziza V2 | 180 | 77 | 42,8 % |
| Mice with Swords (Mabel) | 179 | 76 | 42,5 % |

Zum Vergleich der historische v4.8.2-Baseline (vor `target_focus_chance`,
faktisch deterministisch): Bilbo + Doctor Strange zusammen 60,6 % auf **zwei**
Karten. Der jetzige Bilbo-Wert (42/135 = 31,1 % auf die **eine** Commander-
Karte allein) bestätigt, dass `target_focus_chance=0,35` (eingeführt in
v4.8.3) die Über-Konzentration wie geplant spürbar gesenkt hat, und dass sich
dieser Effekt auch auf die drei neu gemessenen Decks überträgt. Aziza/Mabel
liegen mit ~43 % höher als Bilbo/Katara mit ~31 % — plausibel erklärbar durch
`removal_target_score` selbst: beide Commander sind die mit Abstand
wirkungsvollsten Karten ihrer jeweiligen Strategie (Aziza triggert X-Spell-
Kopien, Mabel trägt das gesamte Voltron-Equipment), erzeugen also einen
höheren `live_impact_score`-Vorsprung vor dem Rest des Boards als Bilbo/Katara
— keine Auffälligkeit im Zielwahl-Mechanismus selbst, sondern ein erwartetes
Resultat unterschiedlich konzentrierter Decklisten.

**Combat-Tode und Board-Wipes** streuen zwischen den Decks deutlicher
(`avg_died_in_combat_per_run`: Katara 0,77, Aziza 0,90, Bilbo 1,05, Mabel
1,77; `total_wiped_by_opponent`: Katara 92, Aziza 57, Bilbo 115, Mabel 140).
Mabels fast doppelt so hoher Combat-Tod-Wert ist plausibel deck-erklärt (breites
Kreaturen-Voltron-Board mit vielen kleinen Angreifern pro Zug, siehe
`Decks/Mice with Swords.txt`) statt ein Hinweis auf einen Gewichtungsfehler —
`combat_block_weight`/`trade_rate_given_blocked` sind deck-unabhängige globale
Gewichte, eine Verzerrung dort müsste sich als Anomalie relativ zur jeweiligen
Board-Breite zeigen, nicht als plausible Differenz zwischen einem 1-2-Kreaturen-
Value-Deck (Katara/Aziza) und einem breiten Wide-Board-Aggro-Deck (Mabel).

**Entscheidung (WP6, Punkt 2 — `combat_interaction_weights.json` NICHT
geändert):** Die v4.8.3-Werte (`removal_weight=0,8`, `combat_block_weight=0,5`,
`target_focus_chance=0,35`, `trade_rate_given_blocked` unverändert) zeigen über
alle 4 echten Decks hinweg ein plausibles, deck-differenziertes Bild ohne
erneute Über-Konzentration wie beim v4.8.2-Fund. Der offene v4.8.3-"Nächster
Schritt" ("WP11 … kann denselben `target_focus_chance`-Wert direkt mitnutzen,
ohne separate Kalibrierung") ist damit durch echte Daten bestätigt statt nur
angenommen. Evidenzbasiert heißt hier: keine Zahl ohne Befund ändern — der
Befund stützt die aktuellen Werte, also bleiben sie unverändert. Punkt 2 der
WP6-Aufgabenliste gilt damit als abgeschlossen; Punkt 3 (commander-
spezifischer Block-Bias, seit v4.7.5 offen: "the commander painted a target on
itself" beim BLOCKEN, nicht beim Removal) bleibt ein separater, echter
offener Punkt (siehe folgender Abschnitt).

Rohdaten: `Goldfish_Results/wp6_diagnostic_v4_15_0_summary.json` sowie die
vier einzelnen Run-Ordner unter `Goldfish_Results/<Deck>/`.

## v4.15.0 — WP10: Voltron-Zielfixierung + Aziza-Alpha-Strike/Mabel-Voltron-Szenarien

**Ausgangslage:** WP10 war seit v4.7.7 offen benannt: "Commander-Schaden geht
weiterhin an den Gegner mit dem aktuell höchsten Leben (bestehende Heuristik)
statt an ein bewusst gewähltes Voltron-Ziel." und seit v4.9.2/v4.9.3: "ein
dediziertes, mehrzügiges 'Aziza-Alpha-Strike'-Szenario im Win-Condition-
Framework bleibt trotzdem für WP10 sinnvoll." Beide Punkte sind jetzt
umgesetzt — **kein Value-Model-Update** diese Version, reine Engine-/
Scenario-Arbeit, deshalb keine Änderungen an
`Data/Models/goldfish_value_model.json`.

**1. Voltron-Zielfixierung für Commander-Schaden** (`Strategy.voltron_target_index`,
neues Feld, Default `None` = unverändertes Verhalten): `attack_phase`s
Zielwahl-Schleife wählte für JEDE Schadensinstanz — auch Commander-Schaden —
bislang `argmax(state.opponents)`, den Gegner mit dem aktuell höchsten Leben,
neu ausgewertet pro Outcome. Das verteilt Commander-Schaden faktisch über
wechselnde Gegner, je nachdem wessen Leben gerade am höchsten ist — für Mabels
Plan "21 Commander Damage auf EIN festes Ziel" ungeeignet. Jetzt: wenn
`strategy.voltron_target_index` gesetzt UND das Ziel noch am Leben ist (>0),
wird NUR Commander-Schaden dorthin gelenkt; regulärer Kampfschaden bleibt
bewusst unverändert auf der alten Heuristik (kein genereller Targeting-
Umbau, gezielt auf den "21-auf-ein-Ziel"-Plan begrenzt). Ist das feste Ziel
bereits eliminiert (0 Leben), fällt die Logik automatisch auf die alte
Heuristik zurück — kein verschwendeter Schaden, kein Crash. Konfigurierbar
über eine Strategy-JSON-Datei (`"voltron_target_index": <0-basierter Index>`),
end-to-end über den bestehenden GUI-Strategie-Lade-Pfad (`load_strategy_v41`
→ `load_strategy`) geprüft.

**2. `derived`-Block jetzt auch für Steering, nicht nur für "Reached"-Status**
(echter, beim Lesen des Codes gefundener Lücken-Fund): `scenario_feasibility`
— die Heuristik, die entscheidet, worauf der Goldfish AKTIV hinsteuert (Karten
zurückhalten, Kreaturen ungetappt lassen usw.) — berücksichtigte seit WP4
(v4.7.4) NIE den `derived`-Block, nur `requirements`/`packages`/`thresholds`/
`mana`. Ein Szenario wie Aziza Alpha-Strike, dessen eigentliche Bedingungen
(3 ungetappte Kreaturen, X-Spell erreicht lethal) komplett `derived` sind und
nur EIN plain requirement (Aziza selbst) hat, bekam dadurch praktisch keine
Steering-Gewichtung — der Goldfish hätte es nur zufällig erreicht, nie aktiv
verfolgt. Jetzt trägt jedes `derived`-Prädikat einen einfachen 1,0/0,0-Kredit
bei (erfüllt/nicht, "nicht berechenbar" zählt als noch-nicht-erfüllt statt
als Fehler), gemittelt über alle Prädikate im Block, mit Gewicht 0,25 im
bestehenden gewichteten Feasibility-Mix. Bewusst einfach gehalten (kein
Pro-Prädikat-Teilkredit wie bei Packages/Thresholds), um nicht die interne
Logik jedes einzelnen Handlers hier zu duplizieren.

**3. Zwei echte Szenario-Dateien** (`Data/Scenarios/aziza_alpha_strike_v1.json`,
`Data/Scenarios/mabel_voltron_v1.json`), ladbar über den bereits bestehenden
GUI-Button "Win Conditions laden …" — keine neue GUI-Infrastruktur nötig:
- **Aziza Alpha-Strike**: zwei Win-Condition-Einträge (Banefire- und Crater's-
  Claws-Kopie — beide echte X-Schadenszauber aus dem tatsächlichen Aziza-V2-
  Deck, siehe `Decks/Aziza V2.txt`), je mit `resource_available`
  (3 ungetappte Kreaturen — Azizas echter Oracle-Text-Kostenpunkt: "tap three
  untapped creatures you control", kein Mana) + `x_spell_lethal`
  (`copy_multiplier: 2`) als `derived`-Bedingungen. Zwei separate Szenarien
  statt einer ODER-Verknüpfung, weil `derived`-Einträge innerhalb eines
  Szenarios UND-verknüpft sind (bestehende Schema-Semantik).
- **Mabel Voltron**: ein Win-Condition-Eintrag um Mabel, Heir to Cragflame
  (echte Karte aus `Decks/Mice with Swords.txt`) mit dem bereits seit WP7
  implementierten `commander_damage_lethal`-Prädikat. Das Szenario selbst
  prüft nur die Opportunity gegen `target: "any"` — WELCHER Gegner tatsächlich
  anvisiert wird, entscheidet zur Laufzeit `strategy.voltron_target_index`,
  nicht das Szenario (zwei bewusst getrennte Zuständigkeiten: Scenario/
  Reporting vs. echtes Targeting).

**Ergebnis:** 15 neue Tests in `tests/test_wp10_voltron_and_alpha_strike.py`
(Voltron-Zielfixierung: Default unverändert, festes Ziel überschreibt die
Heuristik, Fallback bei eliminiertem Ziel, Nicht-Commander-Schaden bleibt
unberührt, wiederholte Angriffe erreichen kumulativ 21 auf dasselbe Ziel;
`derived`-Steering: Szenario ohne `derived` unverändert, erfülltes Prädikat
hebt Feasibility, nicht-berechenbares Prädikat zählt als offen statt als
Fehler; beide echten Szenario-Dateien: Struktur-Validierung, Save/Load-
Roundtrip, hohe Feasibility bei vollständig aufgebautem Board, niedrige bei
fehlenden Teilen, echter End-to-End-Angriff mit festem Ziel). Zusätzlich
zwei echte End-to-End-Smoke-Läufe über die volle `run_pipeline_v440` mit den
echten Aziza- und Mice-with-Swords-Decks und den neuen Szenario-Dateien
(15 Runs, keine Crashes) — danach verworfen (Testdaten). Voller Suite-Lauf:
**202 Tests, alle grün** (1 Skip), keine Regression. `ENGINE_VERSION`/
GUI-Titel auf 4.15.0.

**Bewusst nicht Teil dieser Version:** kein neues GUI-Feld für
`voltron_target_index` (aktuell nur über eine Strategy-JSON-Datei setzbar,
end-to-end über den bestehenden Lade-Pfad geprüft) — eine dedizierte
Tkinter-Eingabe dafür wäre ein separater, in dieser Umgebung visuell nicht
testbarer UI-Eingriff und wurde bewusst zurückgestellt statt ungetestet
geliefert.

## v4.14.0 — Win-Condition-Einfluss + situativer Kontext (WP: Route E des Value-Models — Abschluss der Routen B–E)

**Ausgangslage:** letzter Punkt der vom Nutzer beauftragten Value-Model-
Routen B–E. Route E war laut ihrem eigenen Konzeptdokument
(`Docs/WINCON_AND_CONTEXT_VALUE_v1.md`) explizit von Route D abhängig
("Block 3 setzt logisch auf Block 2 auf") und ausdrücklich NICHT bis zur
Formel-Ebene ausformuliert — mit der offen benannten Begründung, dass es
dafür keine belastbare externe Referenz gibt (kein EDHREC-Äquivalent,
kein offizieller WotC-Kurs), anders als beim Rot-Piloten oder der
Ressourcen-Konversion.

**Was diese Version umsetzt:** die STRUKTUR aus dem Konzeptdokument, real
und getestet, aber bewusst mit ungeprüften Startwerten (siehe unten):

- `ValueModel.win_condition_preservation_multiplier` (Abschnitt 2 des
  Konzepts) — ein weicher Abschlag auf die "jetzt spielen"-Attraktivität
  einer Karte, wenn sie Teil einer definierten Win Condition ist. Skaliert
  invers mit der Anzahl definierter WCs (Abschnitt 2.1: eine einzelne WC
  bei 5 Alternativen zu bewahren ist weniger kritisch als bei nur einer)
  und wird durch einen groben Redundanz-Näherungswert diskontiert
  (Abschnitt 2.2 — wie viele verschiedene Karten die jeweilige WC insgesamt
  braucht; explizit KEIN echter Austauschbarkeits-Test, der bräuchte eine
  Requirements-Schema-Erweiterung, die bewusst zurückgestellt wurde, um
  WP10s bevorstehender Scenario-Arbeit nicht vorzugreifen). Geflooret bei
  `wc_preservation_floor_multiplier` (0,5) — kein Hard-Lock, wie in
  Abschnitt 2.3 explizit gefordert: der Effekt kann eine Karte weniger
  attraktiv machen, sie aber nie faktisch aus der Auswahl ausschließen.
- `ValueModel.hand_board_context_multiplier` (Abschnitt 3) — eine
  kontextabhängige Modulationsschicht, konzeptionell ein Geschwister des
  bestehenden archetyp-basierten `multiplier(metric, tags)`, nur
  hand-/board-zustandsabhängig: fast leere Hand hebt Draw-Rollen an, ein
  großes eigenes Board hebt passive/Engine-Rollen an — genau die zwei
  Beispiele aus dem Konzeptdokument.

**Ehrlich benannt, nicht stillschweigend übersprungen:** alle sechs neuen
Konstanten (`wc_preservation_bias_strength`,
`wc_preservation_floor_multiplier`, `context_empty_hand_threshold`,
`context_empty_hand_draw_boost`, `context_large_board_threshold`,
`context_large_board_passive_boost`) sind erste Startschätzungen ohne
externe Referenz — derselbe Umgang wie bei `x_spell_proximity_bonus_max`
(v4.9.3) oder `value_curve_exponents` (v4.10.0), nicht anders behandelt
als eine "fertig kalibrierte" Zahl. Die im Konzeptdokument selbst
vorgesehene Kalibrierungs-Voraussetzung (echte, über mehrere Läufe
akkumulierte `card_impact.csv`-Auswertungen) existiert durch Route D
(`Data/Learned/engine_value_store.json`) jetzt zwar als Mechanismus, der
Store ist aber bei einem frischen Checkout weiterhin leer — es liegen noch
keine echten Daten vor, gegen die sich diese Konstanten kalibrieren
ließen. Deshalb NICHT an `cast_score_v4`/die laufende Spielentscheidung
angebunden, dieselbe Reporting/Utility-Vorsicht wie bei Route D, hier
sogar strenger begründet. Die offene Systemfrage aus Abschnitt 4
(soll der vom abstrahierten Gegner-Interaktions-Modell erzeugte
Gegnerdruck ebenfalls in den Kontext einfließen?) bleibt bewusst
unbeantwortet, vorgesehen für die Diskussion nach dem als nächstes
anstehenden Gegner-Typ-Simulationsprojekt.

**Ergebnis:** 15 neue Tests in `tests/test_wincon_and_context_value.py`
(WC-Multiplikator: unbeteiligte Karte unverändert, deaktivierte WCs
ignoriert, Floor hält auch bei extremer Überlappung vieler WCs auf
derselben Karte, mehr definierte WCs schwächen den Bias pro Karte ab, eine
WC mit mehr Teilen diskontiert jedes einzelne Teil weniger stark, die am
wenigsten redundante beteiligte WC entscheidet statt eines Durchschnitts;
Kontext-Multiplikator: leere Hand hebt Draw an, volle Hand nicht, großes
Board hebt Engine-Rollen an, kleines Board nicht, unbeteiligte Rollen
bleiben in jedem Kontext neutral, Boosts sind einzeln begrenzt statt
unbegrenzt zu stapeln), alle grün. Voller Suite-Lauf: 187 Tests, alle grün
(1 Skip), **keine Regression** — wie bei Route D bewusst nicht an
`cast_score_v4` angebunden. `ENGINE_VERSION`/GUI-Titel auf 4.14.0.

**Damit sind die Routen B bis E des Value-Models, wie vom Nutzer
beauftragt, abgeschlossen** (v4.12.0 B+C, v4.13.0 D, v4.14.0 E). Laut
Auftrag geht es als Nächstes mit WP10 (Win-Condition-Framework: Aziza-
Alpha-Strike-Szenario, Mabels 21-Commander-Damage-auf-festes-Ziel-Plan)
weiter, danach WP6 und die übrigen offenen Punkte, danach die Entwicklung
eines Verfahrens für Gegner-Typ-Funktionen (rundenabhängig, strategie-
abhängig, farbabhängig).

## v4.13.0 — Engine Value (WP: Route D des Value-Models — vordefinierter + erlernter Wert)

**Ausgangslage:** Route D war von Anfang an als der schwierigste der vier
B–E-Punkte angekündigt — der Nutzer beschrieb die Grundidee früh im
Projekt: den vordefinierten, kartenform-basierten Wert (Routen A–C) mit
einem Wert mischen, der aus ECHTEN Simulationsläufen gelernt wird. Das ist
eine echte Erweiterung, kein Rebranding — vordefinierte Bewertung reagiert
nie darauf, ob eine Karte in der Praxis oft ohne Ziel bleibt, wegen
Mana-Knappheit nie gecastet wird oder durch Synergien überdurchschnittlich
oft trifft. Vollständiges Konzeptdokument: `Docs/ENGINE_VALUE_v1.md`.

**Umsetzung — zwei unabhängige Signale, dieselbe Währung:**
- `predefined_static_value(card, strategy)` (neu): eine reine
  Kartenform-Schätzung OHNE GameState, die exakt dieselben, bereits
  kalibrierten Bausteine wiederverwendet, die auch `cast_score_v4` nutzt
  (`metric_value` mit Farbmultiplikator für Draw/Removal/Board-Wipe/Ramp-
  Rollen, `keyword_value`, `creature_body_value`, den Instant-Speed-
  Aufschlag, feste Tutor/Recursion/Protection-Raten). Beantwortet: "Was
  sollte diese Karte laut Text wert sein, wenn sie einmal genau das tut,
  was sie sagt?"
- Der bereits bestehende `"Estimated value / seen"`-Wert aus
  `card_impact.csv` (echte, in Spielen erfasste Metrik-Ereignisse) wird
  jetzt zum ersten Mal über die Grenze eines einzelnen Goldfish-Laufs
  hinaus PERSISTIERT: `Data/Learned/engine_value_store.json`,
  aktualisiert nach jedem Lauf via `update_engine_value_store` (Seen-
  gewichteter laufender Mittelwert über alle bisherigen Läufe). Das ist
  der eigentlich neue Teil von Route D — bisher endete jede Aggregation
  an der Grenze eines einzelnen Aufrufs.

**Mischung:** `ValueModel.engine_value` — ein Bayesianischer Shrinkage-
Schätzer (dieselbe Familie wie z. B. IMDBs alte "weighted rating"-Formel):
`engine_value_cold_start_pseudo_seen` (Startwert 30) repräsentiert, wie
viele Spiele Vertrauen die vordefinierte Schätzung von Haus aus mitbringt;
bei `learned_seen = 0` (frischer Checkout oder eine noch nie geloggte
Karte) ist das Ergebnis BYTE-IDENTISCH mit dem vordefinierten Wert — kein
Sonderfall nötig, dasselbe Sicherheitsprinzip wie beim
`color_identity=None`-Fallback aus v4.11.0. `engine_value_max_learned_weight`
(Startwert 0,85) verhindert, dass der gelernte Wert die vordefinierte
Schätzung je vollständig verdrängt, selbst bei riesigem Stichprobenumfang
— ein bewusster Rest-Anker, weil erfasste Metrik-Ereignisse selbst nur ein
unvollständiges Bild sind (z. B. wird der Kampfbeitrag eines reinen
Kreatur-Körpers nur teilweise über `combat_damage_per_point` erfasst).

**Bewusste Scope-Grenzen (v1), ehrlich benannt statt stillschweigend
übersprungen:** NICHT an `cast_score_v4`/die laufende Spielentscheidung
angebunden — nur eine neue Report-Datei (`engine_value.csv` pro Lauf,
Spalten "Predefined value (card shape)", "Learned value / seen
(all-time)", "Learned sample size (all-time seen)", "Engine value
(blended)"). Grund: der Store ist bei einem frischen Checkout leer und
selbst nach einigen Läufen statistisch dünn — das Anbinden an den am
breitesten genutzten Bewertungspfad der Engine wäre ein ungetesteter
Eingriff, bevor genug echte Daten vorliegen, um das Verhalten zu
verifizieren. Außerdem (v1): kein Decay (ein Lauf von vor zehn
Engine-Versionen zählt gleich viel wie einer von heute), kein Deck-
Namespace (der Store ist global pro Kartenname, nicht pro Deck — eine
Karte wie Sol Ring sammelt über alle Decks hinweg Erfahrung, was zum
bestehenden Deck-agnostischen Charakter der vordefinierten Bewertung
passt, aber Deck-spezifische Synergien in den Durchschnitt verwässert),
und keine Kausalitäts-/Gewinnkorrelation (gemessen werden erfasste
Ereignisse, nicht ob das Spiel gewonnen wurde). Alle vier Punkte sind
benannte, bewusste v2-Kandidaten in `Docs/ENGINE_VALUE_v1.md` §5, nicht
vergessene Lücken.

**Ergebnis:** 18 neue Tests in `tests/test_engine_value.py` (Blend-Logik
inkl. Cold-Start-Byte-Identität, Deckel-Test bei riesigem Stichproben-
umfang, exakte Formel-Probe bei `seen == pseudo_seen`;
`predefined_static_value` inkl. echter Katara-Karte; Store-Merge-
Arithmetik inkl. Unveränderlichkeit des Original-Dicts und Skip bei
Seen=0; Store-Persistenz-Roundtrip inkl. fehlender/korrupter Datei; ein
End-to-End-Test, der über mehrere simulierte "Läufe" hinweg zeigt, dass
sich der gemischte Wert tatsächlich in Richtung der real beobachteten
Performance bewegt, ohne sie je zu erreichen). Zusätzlich ein echter
End-to-End-Smoke-Test über die volle `run_pipeline_v440` mit dem echten
Bilbo-Deck (20 Runs) bestätigt, dass `engine_value.csv` geschrieben und
`Data/Learned/engine_value_store.json` korrekt befüllt wird (danach
verworfen, da Testdaten, nicht Teil des Auslieferungsstands). Voller
Suite-Lauf: 172 Tests, alle grün (1 Skip), **keine Regression** — Route D
fasst `cast_score_v4` bewusst nicht an. `ENGINE_VERSION`/GUI-Titel auf
4.13.0.

## v4.12.0 — Value-Model Route B (EDHREC-Kreuzvalidierung) + Route C (Baukastensystem: Keywords, Kreatur-Körper, Board-Wipe-Schätzer)

**Ausgangslage:** Fortsetzung von v4.11.0. Der Nutzer bat darum, das
Value-Model entlang der zuvor skizzierten Routen B bis E ausführlich
fertigzustellen, beginnend mit B und C. Route B validiert die in v4.11.0
per WotC-Farbrad übernommenen `color_category_multipliers` gegen echte
Deck-Daten; Route C füllt die zuvor offen gelassenen Kategorien
(Keywords, Stärke+Widerstandskraft, Board-Wipe-Zweiparameter-Modell)
und bündelt sie im Sinne des vom Nutzer gewünschten "Baukastensystems" —
unabhängig voneinander justierbare additive Faktoren statt einer
monolithischen Formel.

**Route B — EDHREC-Kreuzvalidierung für alle 5 Farben:** Da Scryfall aus
der Sandbox weiterhin nicht erreichbar ist (403), wurden die v4.11.0-
Multiplikatoren stattdessen gegen reale EDHREC-Deck-Inclusion-Daten
geprüft: Mono-Weiß-Control (Wrath of God, 23 %/312 von 1350 Decks),
Mono-Blau-Card-Draw (Counterspell/Brainstorm/Psychosis Crawler, 3580
Decks), Mono-Schwarz-Control (Toxic Deluge/Damnation/Go for the
Throat/Infernal Grasp, 3560 Decks), Mono-Grün-Ramp (Llanowar
Elves/Cultivate/Rampant Growth, 9000 Decks — Rampant Growth selbst bei
38 %/3410 Decks, bestätigt direkt die Ramp-Referenzkarte). Ergebnis: vier
der fünf Farben/Kategorien halten der Realdaten-Probe stand, eine echte
Korrektur war nötig — `color_category_multipliers.removal.W` von 0,70 auf
0,80 angehoben, nachdem die Daten zeigten, dass Weißes Control real über
Swords to Plowshares (75 %, 1010 Decks) und Path to Exile (68 %, 912
Decks) läuft — eine günstige, bedingungslose EXIL-Removal-Form (mit
echtem Preis: Gegner bekommt ein Basic Land oder Leben), die die
ursprüngliche, "destroy"-fokussierte WotC-Quelle unterschätzt hatte.
Details mit Quellenangaben in
`Docs/DEFAULT_VALUES_AND_COLOR_PIE_v1.md` §5.2.

**Route C — Baukastensystem:** Drei neue, unabhängig kalibrierbare
`ValueModel`-Methoden, alle in `cast_score_v4` verankert:

- `keyword_value(keywords)` — bündelt ALLE Schlüsselwörter (Fliegen,
  Lebensverknüpfung, Verstoßen, …) unter einer Kategorie, wie vom Nutzer
  explizit gewünscht ("Lifelink etc. zusammen unter Keyword"). Summiert
  (nicht mittelt) über alle vorhandenen Schlüsselwörter einer Karte;
  unbekannte/zukünftige Schlüsselwörter fallen auf
  `keyword_weight_default` (0,25) zurück statt auf 0 — eine neue
  Fähigkeit ist nie wertlos, nur ungewichtet geschätzt.
- `creature_body_value(power, toughness)` — Stärke+Widerstandskraft als
  SUMME (Nutzer-Vorschlag, nicht getrennt geführt), kalibriert über Mark
  Rosewaters "Vanilla-Test": eine fair bepreiste Vanilla-Kreatur hat
  P+W ≈ 2× Manawert (z. B. eine 3-Mana-3/3), also ergibt die Rate 0,5,
  dass eine reine Statur-Kreatur ohne Text ungefähr ihren eigenen
  Manawert wert ist (net_value ≈ 0) — Text/Schlüsselwörter heben eine
  Karte darüber oder darunter. Löst `cast_score`s alte Pauschale
  (jede Kreatur +1,0, unabhängig von der Größe) ab — Kreaturgröße
  beeinflusst jetzt tatsächlich die Sequenzierung.
- `boardwipe_effective_cost_estimate(base_cost, scaling_count)` —
  Zweiparameter-Schätzer für selbstskalierende Board Wipes im Stil von
  "kostet {1} weniger für jede andere Kreatur, die du kontrollierst"
  (Blasphemous-Act-Form), mit Floor. Der Rot-Pilot hatte diese Lücke
  bereits als offen markiert. Über den Scryfall-Cache des Projekts
  bestätigt, dass dieses Kartenmuster real vorkommt (March of Wretched
  Sorrow, Furygale Flocking — beide nutzen "weniger … für jede").
  **Bewusster Scope-Grenzfall, offen benannt:** dies ist reine
  Werte-Schätzung, NICHT an den echten Mana-Zahlungspfad angebunden —
  gleiche Kategorie Lücke wie Delve/Convoke/Improvise/Emerge (laut
  v4.11.0 weiterhin ungeparst).
- Zusätzlich als eigener Baustein: `instant_speed_premium` (0,5,
  pauschal additiv für Instant-Geschwindigkeit) — bewusst als
  unabhängiger, separat justierbarer Knopf statt in eine andere Metrik
  eingerechnet.

Alle neuen Schlüssel sind in `Data/Models/goldfish_value_model.json`
gespiegelt (`keyword_weights`, `keyword_weight_default`,
`creature_pt_sum_rate`, `instant_speed_premium`,
`boardwipe_scaling_discount_per_creature`,
`boardwipe_scaling_cost_floor`), mit Kalibrierungs-Kommentaren analog zu
den bestehenden `_comment_*`-Einträgen.

**Ergebnis:** 15 neue Tests in `tests/test_baukastensystem.py` (Keyword-
Wert isoliert inkl. echter Katara-Karte mit Vigilance, Kreatur-Körper-
Wert inkl. Vanilla-Test-Regressionsschutz und echter Katara-3/3,
Board-Wipe-Schätzer inkl. Floor und echten selbstskalierenden Karten aus
dem Deck-Cache, sowie End-to-End über `cast_score_v4` mit echter
Katara/Deadly-Dispute-Karte), plus 1 neuer Test in
`tests/test_color_category_value.py` für die Weiß-Removal-Korrektur —
alle grün. Vollständiger Suite-Lauf (`python -m unittest discover -s
tests -v`): 154 Tests, alle grün (1 Skip, vorbestehend), **keine
Regression** — anders als bei v4.11.0 (wo `cast_score_v4`s viel breitere
Nutzung im laufenden Spiel eine Wiederholung des Farb-Fallstricks
befürchten ließ) blieben diesmal alle schwellenwert-kalibrierten Tests
unverändert grün. `ENGINE_VERSION`/GUI-Titel auf 4.12.0.

**Offen (bewusst nicht Teil dieses WP):** Route D (Engine Value — Blend
aus vordefiniertem und aus echten Simulationsläufen erlerntem Wert) und
Route E (Win-Condition-Einfluss + situativer Kontext, abhängig von
Route D) folgen als nächste Schritte.

## v4.11.0 — Farbabhängige Kategorie-Multiplikatoren (WP: Farbidentität × Erwartungswert)

**Ausgangslage:** Fortsetzung der v4.10.0-Diskussion — der Nutzer bat darum,
die Werte-Kalibrierung zusätzlich nach Farbidentität zu differenzieren
("ein Drawspell in Rot für fünf Mana muss mir was bringen"). Recherche in
mehreren Konzept-Dokumenten (`Docs/COLOR_VALUE_PILOT_v1_red.md`,
`Docs/DEFAULT_VALUES_AND_COLOR_PIE_v1.md`) ergab: Scryfall ist aus der
Sandbox nicht erreichbar (403), aber EDHREC schon (echte Deck-Inclusion-
Daten für Mono-Rot Draw/Control), und WotCs eigene offizielle "Mechanical
Color Pie 2021"-Dokumentation liefert eine zitierfähige primary/secondary/
tertiary-Einstufung je Farbe und Mechanik für alle 5 Farben auf einmal —
diese Klassifikation, nicht die aufwendigere Pro-Farbe-EDHREC-Recherche,
wurde als Datengrundlage für dieses Work Package gewählt (breiter, sofort
für alle 5 Farben nutzbar).

**Umsetzung:** `ValueModel.color_category_multiplier(category, color_identity)`
skaliert die bestehenden, bereits kalibrierten Pro-Punkt-/Pro-Event-Raten
(`opponent_life_loss_per_point`, `removal_event`, `boardwipe_event`,
`mana_generated`, sowie die `draw_curve`) mit einem Faktor zwischen 0 und 1.
Bewusst als **Obergrenze bei 1,0** entworfen, nicht als Ersatz der
bestehenden Zahlen: die Farbe, die laut WotC für eine Kategorie "primary"
ist, bleibt exakt beim bisherigen Wert (Rot bei Schaden, Schwarz bei
Einzelziel-Removal, Weiß bei Board Wipes, Grün bei Ramp, Blau beim Ziehen);
alle anderen Farben werden abgestuft günstiger discountet. Dadurch kann
dieses WP niemanden BESSER machen als vorher — nur ehrlicher abstufen, wer
in einer Kategorie tatsächlich schlechter ist. Mehrfarbige Karten nehmen
den BESTEN zutreffenden Farbwert (Maximum, kein Mittelwert) — eine Rot/Grün-
Karte, die Schaden macht, wird wie Rot bewertet, nicht durch Grün
heruntergezogen. Farblose Karten nutzen einen pauschalen Fallback (0,5),
grob geschätzt, nicht recherchiert. Die konkreten Multiplikatoren liegen in
`Data/Models/goldfish_value_model.json` unter `color_category_multipliers`
und sind in `Docs/DEFAULT_VALUES_AND_COLOR_PIE_v1.md` mit Quellen belegt.

Angebunden an drei reale Stellen: `best_x_plan` (die X-Spruch-Entscheidung,
beide Zweige — lethal und value mode), `impact_rows_from_aggregate`
(speist die "Estimated total value"-Spalte in `card_impact.csv`), und den
Draw-Bonus in `cast_score_v4`. Bewusst NICHT angebunden: die im selben Zuge
recherchierten Zusatzkosten-Konversionen (Leben/Delve/Convoke/Opfern) aus
`Docs/DEFAULT_VALUES_AND_COLOR_PIE_v1.md` §5 — Recherche im laufenden Code
ergab, dass Delve/Convoke/Phyrexian-Mana von der Engine aktuell gar nicht
geparst werden (kein Mana-Kosten-Alternativsystem vorhanden) und Sacrifice-
als-Zusatzkosten zwar schon real erkannt und ausgeführt wird (siehe
`"as an additional cost to cast this spell, sacrifice..."`-Handling), aber
noch nicht mit einer Werte-Konsequenz verknüpft ist. Beides bewusst nicht in
dieses WP gequetscht, sondern als eigene, noch offene Punkte vorgemerkt statt
stillschweigend als "erledigt" zu behandeln.

**Echter Fund während der Testarbeit:** die neue Farb-Logik unterscheidet
scharf zwischen `color_identity=None` (Aufrufer kennt/übergibt keine Farbe →
unverändert, Multiplikator 1,0) und `color_identity=set()` (Karte hat
bestätigt KEINE Farbe → Farblos-Fallback 0,5). Das deckte einen echten
Fallstrick auf: `make_card()` in den bestehenden Tests setzt `color_identity`
standardmäßig auf `set()` — vorher folgenlos, jetzt real als "farblos"
gewertet. Zwei bestehende Proximity-Tests in `tests/test_x_spell_copy.py`
(`test_getting_close_to_lethal_makes_it_castable`,
`test_a_potential_aziza_copy_brings_a_spell_within_proximity_range...`)
waren exakt an ihrer ROI-/Net-Value-Schwelle kalibriert und kippten dadurch
von castbar zu nicht-castbar. Behoben durch einen expliziten
`color_identity={"R"}` auf dem synthetischen Burn-Spell-Helfer (`_burn_spell`)
— inhaltlich korrekt, da es sich um einen Schadenszauber handelt, und stellt
exakt die ursprünglich kalibrierten Werte wieder her. Lehre für künftige
Tests: ein synthetischer Spruch für Draw/Burn/Removal/Board-Wipe/Ramp
braucht ab jetzt eine explizite Farbe, sonst greift stillschweigend der
Farblos-Fallback.

**Ergebnis:** `python -m unittest discover -s tests` — 138 Tests, davon 15
neu in `tests/test_color_category_value.py` (Multiplikator-Logik isoliert,
Rückwärtskompatibilität ohne Farbangabe, echte Banefire-Karte aus dem
Scryfall-Cache plus farbvertauschte Klone durch `best_x_plan` und
`impact_rows_from_aggregate`), alle grün (1 Skip, vorbestehend, unabhängig
von dieser Änderung). `ENGINE_VERSION`/GUI-Titel auf 4.11.0.

## v4.10.0 — Nicht-lineare Werte-Kurven statt flacher Pro-Punkt-Rate (WP: Erwartungswert-Kalibrierung)

**Ausgangslage:** ein zweiter echter GUI-Lauf mit v4.9.3 (Aziza V2, 200 Runs)
bestätigte den Näherungs-Bonus eindrucksvoll — realer Log-Beleg:
`CAST Banefire X=14 || ... || Aziza, Mage Tower Captain: copied Banefire`
gegen einen Gegner bei 25 Leben, macht effektiv 28 Schaden in einem Zug,
genau das vom Nutzer beschriebene Alpha-Strike-Muster. Crater's Claws blieb
bei 0 Casts (plausibel Stichproben-Zufall: selbst die günstigste real
aufgetretene Konstellation — 16 Mana, Gegner bei 34 — reichte knapp nicht;
bei einer Trefferquote wie bei Banefire, ~5 %, ist 0 von 39 nicht
unwahrscheinlich). White Sun's Zenith blieb bei 0 Casts aus einem ganz
anderen Grund: reiner Token-Zauber, vom Näherungs-Bonus gar nicht erfasst
(der gilt nur für `opponent_life_loss`). Nachgerechnet: mit den echten
Kosten `{X}{W}{W}{W}` (3 Sockel-Mana zusätzlich zu X) und dem alten, rein
linearen Token-Wert lag der wirtschaftliche Break-even bei **X=45** — bei
real nie mehr als 17 verfügbarem Mana (200 Runs, Turn 10) unerreichbar.

**Einwand des Nutzers, der zum eigentlichen Kern des Problems führte:**
weder Schaden noch Kreaturenanzahl sollten pauschal linear pro Punkt
bewertet werden — mit demselben Lightning-Bolt-vs-Banefire-Vergleich wie
schon bei v4.9.3 (ein günstiger, effizienter Bolt ist pro Manapunkt
eigentlich besser als ein großer X-Spruch), aber diesmal zusätzlich mit der
Beobachtung, dass drei zusätzlich investierte Mana für Token-Erzeugung
schlechter sind als fünf — sprich: Breite auf dem Board (Board-Wipe-
Resistenz, Blocker-/Angreifer-Mathematik, Go-Wide-Synergien) ist
überproportional wertvoll, nicht nur proportional. Der Vorschlag: eine Art
Erwartungswert-Bibliothek für verschiedene Effekt-Kategorien (Kartenvorteil,
Board-Präsenz, Kreaturenanzahl, Schaden) in einer separaten, zu
Spielbeginn abgefragten Datei — mit dem Ziel, dass Karten, die es real ins
Deck schaffen, vom Modell auch nicht grundlos unspielbar gemacht werden.

**Umsetzung:** `draw_curve`/`draw_extra_each` demonstrieren dieses Prinzip
im Projekt bereits seit v4.7.x für die Kategorie "draw" (abnehmender
Grenznutzen: die erste gezogene Karte ist mehr wert als die zehnte). Statt
eine neue, separate Kurven-Engine mit Stützpunkt-Tabellen für jede Kategorie
zu bauen, generalisiert `ValueModel.curved_count(category, amount)` dieselbe
Grundidee auf einen einzigen, klar benannten Potenzgesetz-Exponenten pro
Kategorie (`value_curve_exponents` in `Data/Models/goldfish_value_model.json`):
`effective = amount ** exponent`. Exponent 1.0 (Default für jede nicht
gelistete Kategorie) reproduziert exakt das alte, flache Verhalten — echte
Zusatzarbeit, keine stille Neukalibrierung aller bisherigen Metriken.
Zwei Kategorien bewusst in entgegengesetzte Richtungen kalibriert:

- **`opponent_life_loss`: Exponent 0.85 (abnehmend).** Ein Lightning Bolt
  ist pro Schadenspunkt mana-effizienter als ein riesiger X-Spruch — genau
  das Argument des Nutzers. Getrennt vom (unverändert bestehen bleibenden)
  Näherungs-Bonus aus v4.9.3: der Näherungs-Bonus beantwortet "bringt das
  einen Kill näher", die neue Kurve beantwortet "wie effizient ist der
  Schaden an sich" — beide Effekte addieren sich, und der Näherungs-Bonus
  rechnet bewusst weiterhin mit dem RAW-Schadenswert (nicht dem
  kurvenbereinigten), damit die reine Lethal-Prüfung (im Lethal-Zweig von
  `best_x_plan`, der direkt auf `metrics.get("opponent_life_loss")`
  zugreift, nicht über `ValueModel`) von der Werte-Kurve unberührt bleibt —
  X Schaden ist und bleibt X Schaden für die Frage "reicht das zum Töten".
- **`creature_tokens`: Exponent 1.15 (zunehmend).** Ein breites Kreaturen-
  Board ist überproportional mehr wert als dieselben Kreaturen einzeln
  gezählt — die Umkehrung von `draw`s abnehmendem Grenznutzen, mit
  derselben Mechanik, nur umgekehrtem Exponenten.

**Konkreter Effekt, real nachvollzogen:** White Sun's Zenith (echte Karte,
`{X}{W}{W}{W}`, 2/2-Katzen) fällt mit dem neuen, zunehmenden Token-Exponenten
von Break-even X=45 auf **X=8** (macht mit dem 3-Mana-Sockel 11 Mana Gesamt-
kosten) — komfortabel innerhalb der real beobachteten ~9–13 Mana bei Zug 9–10.
Der synthetische Test-Zauber aus v4.9.2 (ohne Sockel-Kosten) fällt von X=12
auf X=4. Bei den Schadenszaubern verschiebt sich der Break-even unter
Näherungs-Bedingungen von X=19 (v4.9.3) auf X=24 (v4.10.0) — die abnehmende
Effizienz-Kurve macht den Grund-Beitrag etwas kleiner, sodass etwas mehr X
nötig ist, bevor der (unveränderte) Näherungs-Bonus über die Schwelle trägt.

**Bewusste Vereinfachung, dokumentiert statt versteckt:** die Kurve wirkt auf
die bereits vor-multiplizierte Metrik-Menge (bei `creature_tokens` also
Körper-Wert × Anzahl, nicht die reine Stückzahl). Für einen einzelnen
Zauber, der N gleich große Token erzeugt (der Normalfall, und genau der Fall
der realen Evidenz), ist das äquivalent zu einer reinen Mengen-Kurve, da der
Pro-Token-Wert über den Cast hinweg konstant bleibt; beim Vergleich zweier
UNTERSCHIEDLICH großer Token-Typen ist es nicht exakt. Eine strikte
Mengen-Kurve bräuchte zwei getrennte Counter-Schlüssel (Anzahl und
Körper-Wert) statt einer vor-multiplizierten Zahl — zurückgestellt für eine
künftige Iteration, falls reale Evidenz das nötig macht.

**Bewusst NICHT in diesem Schritt:** die vom Nutzer skizzierte volle
"Erwartungswert-Bibliothek pro Mana-Kosten, mit Verdopplungs-/Synergie-
Effekten über den Spielverlauf" ist eine deutlich größere Erweiterung
(bräuchte eine Verbindung zwischen Kartenkosten und erwarteter Effektmenge,
plus einen Mechanismus für Laufzeit-Anpassungen). Diese Version generalisiert
gezielt nur den bereits bewährten Kurven-Mechanismus (`draw_curve`) auf die
zwei vom Nutzer konkret benannten, real belegten Problemfälle
(Schaden, Kreaturenanzahl) — mit echten Zahlen aus zwei echten Läufen
hinterlegt, nicht spekulativ auf Vorrat gebaut.

**Tests:** `tests/test_x_spell_copy.py` — bestehende Overkill-/Proximity-
Tests auf die neuen Break-even-Werte aktualisiert (X=12→4, X=19→24, jeweils
mit Herleitung im Kommentar); neuer Test lädt die echte White-Sun's-Zenith-
Karte aus dem Offline-Scryfall-Cache und bestätigt X=8; zwei neue direkte
Kurven-Tests zeigen mechanismus-nah, dass 5 Token überproportional mehr wert
sind als 3 (`value(5)/value(3) > 5/3`) und dass 1 Schadenspunkt pro Punkt
mehr wert ist als Punkt 40 (`value(1)/1 > value(40)/40`). **Gesamt-Suite:
123/123 grün**, 1 weiterhin bewusst übersprungen.

**Kein GUI-Code geändert** (nur `self.title(...)` synchron auf v4.10.0
hochgezählt).

## v4.9.3 — Näherungs-Bonus für X-Schadenszauber ("wie nah an einem Kill?")

**Ausgangslage:** die in v4.9.2 dokumentierte, separate Kalibrierungslücke
(Banefire/Crater's Claws im Aziza-V2-Deck sind unter `DEFAULT_VALUE_MODEL`
bei JEDEM X unter der ROI-Schwelle — ROI(X) = 0,42·X/(X+0,75) nähert sich
für X→∞ nur 0,42, weit unter `x_min_roi=0.88`) wurde bewusst nicht
mitgefixt, sondern dem Nutzer zur Entscheidung vorgelegt.

**Entscheidung des Nutzers, mit einer eigenen, wichtigen Beobachtung:** rein
lineare Pro-Punkt-Bewertung ist der falsche Ansatz für X-Schadenszauber.
Der ROI eines Banefire hängt nicht linear vom Schaden ab, sondern davon,
wie nah der Zauber (ggf. inklusive einer Aziza/Mica-Kopie) an einen
tatsächlichen Kill herankommt — Chip-Schaden weit vom Sieg entfernt ist zu
Recht schwache Value (das war schon vorher korrekt modelliert), aber Schaden,
der das Spiel fast beendet, sollte deutlich mehr wert sein als dieselbe
Schadenszahl über ein volles 40-Leben-Spiel verteilt. Genau dieses Muster
liefert im Aziza-Kontext die eigentliche Win-Condition (X-Mana + 3
Kreaturen tappen + Kopie = potenziell fast das gesamte Gegnerleben in einem
Zug) — die generische Bewertungslücke betrifft aber jedes Deck mit
X-Schadenszaubern, nicht nur Aziza, und wurde deshalb hier als generische
Erweiterung von `best_x_plan` behoben (ein dediziertes, mehrzügiges
"Aziza-Alpha-Strike"-Szenario im Win-Condition-Framework bleibt trotzdem
für WP10 sinnvoll, siehe README-Abschnitt v4.9.2/COWORK_HANDOFF Abschnitt 6).

**Umsetzung:** neue, nicht-mutierende Funktion
`_x_spell_proximity_bonus(metrics, state, copy_multiplier, vm)` — bewusst
im selben Stil wie `_potential_cast_copy_multiplier` (nur Bewertung, kein
Board-Effekt). Sie berechnet `proximity = min(1, (Schaden × potenzieller
Kopie-Multiplikator) / verbleibendes Gegnerleben)` und addiert
`Schaden × x_spell_proximity_bonus_max × proximity` zum `gross_value` im
Value-Modus-Zweig von `best_x_plan` (der Lethal-Zweig bleibt unverändert —
der ist bereits threshold-basiert und braucht diesen Bonus nicht). Ein
einzelner, klar benannter, JSON-tunable Knopf
(`x_spell_proximity_bonus_max`, Startwert 1.0 in
`Data/Models/goldfish_value_model.json`) — dieselbe Konvention wie
`draw_curve`/`x_min_roi`, kein erfundenes Pro-Effekt-Modell. Da `proximity`
in der Praxis immer < 1 bleibt (ein Cast mit `proximity = 1` wäre bereits
vom Lethal-Zweig abgefangen worden und würde diesen Value-Modus-Code gar
nicht erreichen), bleibt reiner Chip-Schaden weit vom Kill entfernt
unverändert konservativ bewertet — der Bonus wirkt gezielt nur in der Nähe
eines Kills.

**Beispielrechnung (aus den Tests):** X-Schadenszauber, Gegner bei 30 Leben,
25 Mana verfügbar (mehr als die Basiskosten reichen für X=25, aber 25<30
ist nicht tödlich). Ohne Bonus: `net_value` fällt für jedes X negativ aus
(0,42·X − X − 0,75 wird mit steigendem X sogar noch negativer) — der Zauber
war vorher bei JEDEM X unwirkbar, unabhängig vom Gegnerleben. Mit Bonus
(`bonus_max=1.0`): das kleinste X, das die Schwelle erreicht, ist X=19
(`net_value≈0,26`, `ROI≈1,01`) — nah genug an den 30 Leben, um sich zu
lohnen. Bei einem potenziellen Aziza-Copy-Multiplikator zählt die doppelte
Schadenszahl auch für die Näherung, nicht nur für die reine
Lethal-Prüfung: ein Zauber, der bei 60 Gegnerleben ohne Kopie weiterhin
unwirkbar bleibt, wird mit einer möglichen Aziza-Kopie (2×25=50 von 60,
`proximity≈0,83`) bei X=19 castbar.

**Ausdrücklich als vorläufig markiert:** `x_spell_proximity_bonus_max=1.0`
ist eine erste Schätzung, noch nicht durch einen echten Simulationslauf
gegengeprüft (anders als die übrigen X-Spell-Gewichte, die bereits über
`card_impact.csv` verifiziert wurden). In `Data/Models/goldfish_value_model.json`
als solche kommentiert — nach dem nächsten echten Lauf mit Banefire/
Crater's Claws im Deck sollte geprüft werden, ob dieser Wert zu aggressiv
oder zu vorsichtig kalibriert ist.

**Tests:** `tests/test_x_spell_copy.py`, neue Klasse
`BestXPlanProximityToLethalTests` (3 Tests): Chip-Schaden weit vom Kill
bleibt weiterhin unwirkbar (Regressionsschutz für die bewusst konservative
Behandlung); ein X-Schadenszauber wird castbar, sobald das leistbare X nah
genug an das Gegnerleben herankommt; ein potenzieller Aziza-Copy zählt für
die Näherung genauso wie für die Lethal-Prüfung. Alle bisherigen 117 Tests
unverändert grün (der Bonus betrifft ausschließlich Karten mit
`opponent_life_loss`-Metrik, token-/draw-/lifegain-Zauber sind nicht
berührt). **Gesamt-Suite: 120/120 grün**, 1 weiterhin bewusst übersprungen.

**Kein GUI-Code geändert** (nur `self.title(...)` synchron auf v4.9.3
hochgezählt).

## v4.9.2 — Fix: Value-Modus-Overkill-Vermeidung konnte hohe X dauerhaft unterdrücken (gefunden per echtem GUI-Lauf)

**Ausgangslage:** v4.8.3/v4.9.0/v4.9.1 wurden erstmals nicht nur per
`py_compile` und Unittests, sondern per zwei echten GUI-Läufen verifiziert
(Katara V3 und Aziza V2, je 200 Runs/10 Turns/Seed 1, `opponent_profile=
random`, Engine-Version laut `simulation_config.json` bestätigt 4.9.1).

**Bestätigt funktionierend, mit echten Log-/CSV-Belegen:**
- **Waterbend (WP8):** `card_impact.csv` zeigt 466 `Semantic ability uses`
  für Katara über 200 Runs; `turns.csv` enthält 466 reale
  `WATERBEND Katara, Water Tribe's Hope: X=… (tapped … creature(s) + …
  artifact(s)), creatures you control -> base N/N until end of turn`-Zeilen
  mit plausiblen X-Werten — die Vigilance-Sequenzierung und die
  Board-Modifier-Anwendung laufen im echten Spiel wie vorgesehen.
- **Aziza/Mica-Copy (WP9, Ziel 2-4):** `card_impact.csv` zeigt für Aziza
  Cast=307/Copies=156 und für Mica Cast=35/Copies=30 — der zuvor tote
  Copy-Trigger feuert im echten Spiel und bezahlt echte Kosten (das war vor
  WP9 nachweislich 0/0, siehe v4.9.1-Abschnitt unten).

**Neu gefundener, selbstverschuldeter Bug (WP9-Regression):** im selben
Aziza-Lauf zeigten drei echte X-Zauber `Cast: 0` trotz 42-49 `Seen` über 200
Runs: Banefire, Crater's Claws, White Sun's Zenith. `deck_enriched.csv`s
`Roles`-Spalte schließt "bewusst reaktiv zurückgehalten" aus (keine der drei
ist als `interaction`/`protection` getaggt — anders als z. B. Abrade oder
Boros Charm, die zu Recht bei 0% Cast-Rate bleiben). Nachrechnung ergab zwei
verschiedene Ursachen:

1. **Echte Regression, behoben:** White Sun's Zenith (Standard-Gewichte:
   Pro-Token-Wert 0,35 + 2·0,25 + 2·0,12 = 1,09, knapp über `mana_unit=1.0`)
   wird erst ab X=12 profitabel genug (`net_value` bei X=11 noch 0,24, knapp
   unter der Schwelle 0,25; bei X=12 bereits 0,33). Das in v4.9.1 eingeführte
   `ValueModel.diminish_x_value` ("Overkill-Vermeidung" per Diminishing-
   Returns-Kurve ab X=6) hat den Wert aber schon lange vor X=12 so weit
   herunterskaliert, dass die Schwelle **nie mehr** erreicht wurde — der
   Zauber war im Value-Modus dauerhaft uncastbar, nicht nur bei kleinem X.
   **Fix:** `best_x_plan`s Value-Modus-Suche folgt jetzt demselben Muster wie
   die bereits bestehende Kleinstes-X-für-lethal-Suche — X wird aufsteigend
   durchprobiert, und der **erste** X-Wert, dessen **ungewichteter**
   `net_value`/ROI die Schwellen (`x_min_net_value`/`x_min_roi`) bereits
   erreicht, wird sofort zurückgegeben. Damit erübrigt sich die Diminishing-
   Kurve komplett: "Overkill vermeiden" ergibt sich automatisch daraus, immer
   den kleinsten tragfähigen X zu nehmen, statt den größten leistbaren X zu
   nehmen und danach künstlich herunterzuskalieren. Entfernt:
   `ValueModel.diminish_x_value`, `x_spell_soft_cap_units`,
   `x_spell_soft_cap_decay` (Code, `DEFAULT_VALUE_MODEL` und
   `Data/Models/goldfish_value_model.json`) — ersatzlos, nicht nur
   deaktiviert.
2. **Separates, vorbestehendes Kalibrierungsproblem, NICHT in diesem Fix
   behoben — Entscheidung bei dir:** Banefire und Crater's Claws
   (`opponent_life_loss_per_point=0.42`) können unter dem Standard-
   `ValueModel` **bei keinem X** die ROI-Schwelle `x_min_roi=0.88`
   überschreiten — ROI(X) = 0,42·X/(X+0,75) nähert sich für X→∞ asymptotisch
   nur 0,42. Das ist unabhängig von WP8/WP9 und existierte bereits vorher
   (weder die Gate-Logik noch die Pro-Punkt-Gewichte wurden von mir
   geändert) — durch den echten Lauf nur erstmals sichtbar geworden, weil
   beide Karten jetzt (dank des Bugfixes oben) tatsächlich Kandidaten für den
   Value-Modus wären, wenn die Schwelle erreichbar wäre. Eine Änderung hier
   (z. B. `opponent_life_loss_per_point` anheben oder `x_min_roi` für reine
   Burn-Effekte senken) betrifft die Bewertung **jedes** Decks mit
   X-Schadenszaubern, nicht nur Aziza — deshalb hier bewusst nicht blind
   mitgefixt, sondern als offene Frage stehen gelassen.

**Tests:** `tests/test_x_spell_copy.py` — `DiminishXValueUnitTests` komplett
entfernt (testete eine jetzt nicht mehr existierende Methode);
`BestXPlanOverkillAvoidanceTests` neu geschrieben: ein Test mit großzügigen
Gewichten bestätigt jetzt "kleinstes tragfähiges X" (X=1) statt "größtes
leistbares X" (vorher X=25 im Vergleichstest), ein neuer Regressionstest
reproduziert exakt die White-Sun's-Zenith-Form unter den echten
Standard-Gewichten und verlangt X=12. Alle anderen WP9-Tests (Kleinstes-X-
für-lethal, Aziza/Mica-Kostenprüfung, echte-Karten-Test) unverändert und
weiterhin grün, da sie den lethal-Zweig bzw. die Copy-Kostenprüfung testen,
die von diesem Fix nicht berührt werden.

**Gesamt-Suite: 117/117 grün** (120 aus v4.9.1 − 3 entfernte
Diminish-Tests), 1 weiterhin bewusst übersprungen
(`bilbo_win_conditions.json` fehlt in diesem Checkout).

**Kein GUI-Code geändert** (nur `self.title(...)` synchron auf v4.9.2
hochgezählt).

## v4.9.1 (WP9) — X-Spell/Copy-Verfeinerung (Aziza, Mage Tower Captain / Mica, Reader of Ruins)

**Ziel 1: X ist nicht mehr automatisch maximal.** `App/engine.py::best_x_plan`
(die tatsächliche Cast-Entscheidung, nicht nur die Bewertung) sucht jetzt
zuerst nach einem **tödlichen X** — exakt dieselbe Kleinstes-X-für-lethal-Suche
wie `scenario_predicates.handlers._p_x_spell_lethal` (dort bereits gelöst;
diese Vorlage wurde jetzt in die generische Engine-Logik übernommen). Gibt es
kein tödliches X, greift im "Value-Modus" ein neues, JSON-konfigurierbares
Diminishing-Returns-Gewicht (`ValueModel.diminish_x_value`,
`x_spell_soft_cap_units`/`x_spell_soft_cap_decay` in
`Data/Models/goldfish_value_model.json`, Default 6 Einheiten / 0,85 Zerfall pro
Einheit darüber) — dieselbe Konvention wie `draw_curve`/`draw_extra_each`
(ein einzelner, klar benannter Knopf, kein erfundenes Pro-Effekt-Modell), damit
ein rein linear skalierender Effekt (X Schaden, X Leben, X Tokens — ohne
eigene Diminishing-Kurve wie "draw") nicht mehr für immer "je größer X, desto
besser" ist, sobald genug Mana verfügbar ist.

**Aziza/Mica-Copy-Interaktion mit der lethal-Suche:** eine neue,
nicht-mutierende `_potential_cast_copy_multiplier(state)` erkennt, ob Aziza
(≥3 ungetappte Kreaturen) oder Mica (≥1 Artefakt) den Spruch verdoppeln
könnten, und die Kleinstes-X-für-lethal-Suche rechnet damit — genau das
`copy_multiplier`-Konzept, das `x_spell_lethal` bereits kennt (dort ein von
Hand gesetzter Szenario-Parameter; hier automatisch aus dem echten Board-State
abgeleitet, da `best_x_plan` keine Szenario-Parameter hat).

**Ziel 2 (Copy ≠ Cast) — echter Bugfix, kein neues Feature:** eine frühere,
"sehr konservative" generische "whenever you cast an instant or sorcery
spell, copy it"-Erkennung existierte bereits weiter oben in dieser Datei —
aber durch das Last-Definition-gewinnt-Muster dieses Moduls (siehe
COWORK_HANDOFF.md Abschnitt 3) lag sie in einer längst überschriebenen,
nie erreichten Definition von `try_cast_option`. Das Feature war in jedem
echten Lauf **komplett tot** — Aziza/Mica haben nie kopiert. Neu und in der
tatsächlich aktiven `try_cast_option` verankert:
`_maybe_copy_cast_instant_or_sorcery` + `_pay_cast_copy_trigger_cost`, bewusst
auf genau diese zwei realen Karten begrenzt (nicht die alte
Freikopie-für-jedes-Textmuster-Version wiederbelebt):
- **Aziza** (Ziel 3): Kosten = 3 ungetappte Kreaturen tappen — wiederverwendet
  das bestehende `resource_available`-Scenario-Predicate für die Prüfung
  (`min_count=3`), tappt dann tatsächlich 3 ungetappte Kreaturen (Aziza selbst
  zählt mit, wie im echten Regeltext).
- **Mica** (Ziel 4): Kosten = ein Artefakt opfern — bewusst **kein**
  `resource_available`/`untapped_artifacts`-Check (Opfern ist kein Tap-Kosten,
  der Tap-Status ist irrelevant) und **kein** Resource-Planner-Einsatz aus
  Teil 1: eine reine Ja/Nein-Existenzprüfung ohne X-Wahl und ohne
  konkurrierende Kandidaten würde die Allokations-Suche des Planners nur
  überdimensionieren — eine 3-Zeilen-Standalone-Lösung, wie es der Auftrag für
  diesen Fall ausdrücklich erlaubt.
- Eine kopierte X-Zauber-Wirkung nutzt garantiert **dasselbe** X wie das
  Original (kein neuer `best_x_plan`-Lauf für die Kopie), und die Kopie
  triggert **nicht** erneut "whenever you cast" (auch nicht die eigene
  Aziza/Mica-Fähigkeit) — verifiziert über den `cast`-Impact-Zähler, der bei
  genau 1 bleibt, obwohl die Wirkung zweimal eintritt.

**Nebenbei gefundener und behobener Bug (kein WP9-Ziel, aber durch den
Pflicht-Realkarten-Test aufgedeckt):** `resolve_x_spell` kannte das Muster
"deals X damage to (any target|target player|each opponent)" nur in der
**Bewertung** (`x_effect_metrics`), nicht in der tatsächlichen Auflösung —
ein echter Deck-Karten-Burn-Spruch wie **Banefire** (im Aziza-V2-Deck) wurde
für die KI-Entscheidung korrekt bewertet, tat beim tatsächlichen Wirken aber
nichts. Ergänzt (`lose_target_opponent`/`lose_each_opponent`, je nach Text).

**Tests:** `tests/test_x_spell_copy.py` (13 Tests): reine
`ValueModel.diminish_x_value`-Formeltests; Kleinstes-X-für-lethal mit und
ohne Aziza-Copy-Potenzial; Value-Modus-Overkill-Vermeidung samt
Gegenprobe (`x_spell_soft_cap_decay=1.0` reproduziert exakt das alte
"immer maximal"-Verhalten, beweist also, dass der neue Cap die Ursache ist,
nicht Zufall); Aziza kopiert nur mit zahlbaren 3 Kreaturen, sonst nicht;
Mica kopiert nur mit einem Artefakt (auch getappt), sonst nicht; Kopie
triggert `cast` nicht erneut; Kopie nutzt garantiert dasselbe X. Ein Test
lädt Aziza und das echte Banefire direkt aus dem Projekt-eigenen Offline-
Scryfall-Cache (nicht von Hand nachgebaut) und prüft die komplette Kette
Ende-zu-Ende (inkl. des oben gefundenen Bugfixes).

**Gesamt-Suite: 120/120 grün** (107 aus v4.9.0 + 13 neue), **1 weiterhin
bewusst übersprungen** (`bilbo_win_conditions.json` fehlt in diesem Checkout,
unabhängig von WP8/WP9).

**Kein GUI-Code geändert** (nur `self.title(...)` synchron auf v4.9.1
hochgezählt); wie immer nur `py_compile`-verifiziert, echte Bestätigung
braucht einen realen Windows-GUI-Lauf.

## v4.9.0 (WP8) — Resource Allocation Planner + Waterbend (Katara, Water Tribe's Hope)

**Neues wiederverwendbares Modul:** `App/resource_planner/` (`planner.py`), im
selben engine-agnostischen Registry-Stil wie `combat_model`/`keyword_library`/
`scenario_predicates` (kein `import engine`, keine zyklischen Imports). Kernidee:
`Resource` (Kosten-Kandidat, mit `costs_attacker`/`opportunity_cost`/
`future_value`), `Action` (min/max Einheiten) und `plan_allocation(resources,
action, goal_fn)` — eine bewusst **kleine, beschränkte Suche** (freie Ressourcen
werden immer voll genutzt; kostenpflichtige Kandidaten werden nach
`opportunity_cost - future_value` sortiert, auf max. 10 gekappt, und jedes Präfix
`k=0..10` gegen `goal_fn` durchprobiert) statt einer Brute-Force-Teilmengensuche.
Gedacht als Baustein nicht nur für Waterbend, sondern langfristig auch für
Convoke/Improvise/Crew/Aziza-Copy-Kosten/Equip-Entscheidungen (WP9 nutzt es
teilweise bereits, siehe unten). Tunables liegen wie üblich in JSON
(`Data/Models/resource_planner_weights.json`), auch wenn der Planer selbst aktuell
keine echte Kalibrierung braucht.

**Erster konkreter Nutzer: Waterbend.** `App/engine.py::maybe_use_waterbend`,
registriert in `DEDICATED_RESOLVERS` unter `Katara, Water Tribe's Hope`
("Waterbend {X}: Creatures you control have base power and toughness X/X until
end of turn. X can't be 0. [...] you can tap your artifacts and creatures to
help. Each one pays for {1}."). Setzt die Basis-P/T aller eigenen Kreaturen über
einen `set_base_pt`-`BoardModifier` (bestehende Infrastruktur, siehe
`creature_power()` — kein neuer Modifier-Typ nötig) bis Zugende.

**Die eigentliche Regel, um die es in diesem Auftrag ging (Vigilance-Sequencing):**
`maybe_use_waterbend` wird in `attack_phase` **nach** der Angreifer-Festlegung
aufgerufen, nicht davor. Eine Vigilance-Kreatur ist nach dem Deklarieren als
Angreifer weiterhin ungetappt (Vigilance tappt beim Angriff nie); wird sie danach
zum Bezahlen von Waterbend getappt, bleibt sie trotzdem im Kampf — Tappen ist
keine Rückkehr aus dem Kampf, und `tap_permanent()` rührt `attacker_infos` nicht
an. Jede Kreatur, die `maybe_use_waterbend` als Zahlungsquelle anbieten kann, ist
deshalb entweder (a) ein noch ungetappter Vigilance-Angreifer, der im Kampf
bleibt, oder (b) eine Kreatur, die diesen Zug gar nicht angegriffen hat — in
beiden Fällen "kostet" das Tappen keinen Angreifer. Genau deshalb ist in der
echten Integration jede Kreatur-Ressource `costs_attacker=False`; der abstrakte
Fall, in dem `costs_attacker=True` das Ergebnis tatsächlich ändert (die
"(N-k)·X"-Formel aus dem Auftrag), wird separat gegen den nackten Planer getestet
(`tests/test_resource_planner.py`), nicht gegen die echte Katara-Integration.

**Aktivierungs-Gate (über den Auftrag hinaus, aber notwendig für korrektes
Verhalten):** Waterbend *setzt* die Basis-P/T, es erhöht sie nicht additiv. Ein
X, das kleiner ist als die aktuelle Angreifermacht, würde also den eigenen
Schaden **verringern** — z. B. eine einzelne 3/3-Katara, die nur sich selbst
für X=1 tappt. `maybe_use_waterbend` vergleicht deshalb den geplanten
Gesamtschaden (`(Angreifer − verlorene Angreifer) × X`) gegen den tatsächlichen
Ist-Schaden vor Aktivierung und aktiviert nur, wenn Waterbend wirklich mehr
Schaden bringt — sonst bleibt die Fähigkeit ungenutzt (siehe
`test_vigilance_keeps_katara_untapped_when_waterbend_is_not_worth_activating`).

**Bewusst ausgeklammert (dokumentierte Grenze, kein stiller Kompromiss):**
- **Kein generisches Mana als Zahlungsquelle** (nur ungetappte Non-Creature-Artefakte
  und ungetappte Kreaturen) — siehe Kommentar in
  `Data/Models/resource_planner_weights.json` (`waterbend.include_generic_mana`):
  korrekt zu wissen, wie viel Mana zu diesem späten Zeitpunkt im Zug noch frei
  ist, bräuchte eine zweite vollständige Mana-Neuberechnung (Doppelzählungsrisiko
  mit bereits ausgegebenem Mana) — genau die Art von falscher Präzision, die
  dieses Projekt vermeidet.
- **Toughness-Hälfte von "X/X" hat keine Kampf-Auswirkung in diesem Modell:**
  `combat_model.interaction.AttackerInfo` hat kein Toughness-Feld — Sterben wird
  hier über eine feste `trade_rate_given_blocked`-Wahrscheinlichkeit gewürfelt,
  nicht über echte Power/Toughness-Kampfmathematik. Der `set_base_pt`-Modifier
  setzt `toughness` trotzdem korrekt mit (für den Fall, dass ein zukünftiges
  Feature Toughness direkt liest), aber er verändert aktuell keine
  Kampf-Wahrscheinlichkeit. Ehrlich benannt statt stillschweigend ignoriert.
- **`keyword_library`s `set_base_pt`/`team_pt_bonus`-Handler wurden geprüft, aber
  bewusst NICHT verwendet:** dieses Handler-System ist für generische, aus
  Oracle-Text geparste statische Fähigkeiten gedacht (siehe
  `App/keyword_library/handlers.py`). Waterbend ist eine aktivierte,
  X-kosten-abhängige Fähigkeit mit eigener Ressourcenentscheidung, die schon
  vorher in `DEDICATED_RESOLVERS` (wie Bilbo, Doctor Strange, etc.) landet — der
  bestehende `BoardModifier`/`creature_power()`-Mechanismus selbst (den auch die
  generischen Handler am Ende benutzen) ist hier die richtige Wiederverwendung,
  nicht die Registry-Schicht darüber.

**Tests:** `tests/test_resource_planner.py` (7 Tests, reiner Planer ohne
GameState) reproduziert beide Rechenbeispiele aus dem Auftrag exakt (N=10/R=10 →
k=0, Schaden=100; N=10/R=0 → k=5, Schaden=25 — Formel `(N-k)·X`, Maximum bei
k=5 da `(10-k)·k` dort sein Maximum 25 hat) sowie einen Test, der zeigt, dass
ein "Untap-Effekt" (z. B. Dramatic Reversal, vereinfacht als niedrigere
`opportunity_cost` einer Ressource modelliert) messbar **welche** Ressourcen der
Plan wählt, nicht nur eine ungenutzte Zahl ändert. `tests/test_waterbend.py`
(5 Tests) testet Ende-zu-Ende gegen den echten `attack_phase`-Pfad (kein
Mock): das Vigilance-Sequencing selbst (Katara bleibt im Kampf, obwohl sie zum
Bezahlen getappt wird — Schaden kommt mit dem neuen X durch, nicht mit ihrer
ursprünglichen Power), das Aktivierungs-Gate (keine Aktivierung, wenn es den
Schaden verschlechtern würde), und ein Regressionstest ohne Katara auf dem
Feld. Mindestens ein Test lädt Kataras echte Karte direkt aus dem Projekt-eigenen
Offline-Scryfall-Cache (`App/.scryfall_card_cache_v4.json`, über
`card_from_scryfall`, nicht von Hand nachgebaut) — die Kara-V3/Aziza-V2/Mice-Decklisten
waren in diesem Cowork-Checkout ebenfalls nachträglich vom Gerät nachgeladen
worden, wodurch nebenbei auch die 3 zuvor aus Datenmangel übersprungenen
`test_decklist_parsing`-Tests jetzt grün laufen (vorher bewusst übersprungen wie
bei v4.8.3 dokumentiert).

**Gesamt-Suite: 107/107 grün** (95 bisherige + 12 neue: 7 Resource-Planner + 5
Waterbend), **1 weiterhin bewusst übersprungen** (`bilbo_win_conditions.json`
fehlt in diesem Checkout — unabhängig von WP8, gleicher Grund wie zuvor).

**Kein GUI-Code geändert** (nur `self.title(...)` synchron auf v4.9.0 hochgezählt);
`App/gui.py` bleibt `py_compile`-clean, aber wie immer nur echt verifiziert durch
einen realen Windows-GUI-Lauf, nicht durch dieses Cowork-Sandbox-Environment.

## v4.8.3 — Spot-Removal-Zielwahl: nicht mehr deterministisch auf ein Ziel fixiert

Direkt aus dem 200er-Diagnostic-Run (v4.8.2, siehe Nachtrag unten) abgeleitet:
`importance_targeting` wählte das Spot-Removal-Ziel bisher **immer** deterministisch
per `max(targets, key=removal_target_score)` — kein Zufall, keine Ausnahme. Über
200 Runs landeten dadurch **~61 % des gesamten gegnerischen Removals im ganzen
Deck (97 von 160 Events) auf genau 2 Karten** (Bilbo, Doctor Strange), obwohl
beide zusammen nur 2 von ~59 Nicht-Land-Karten sind. Combat-Tode waren dagegen
schon (dank Posture) bei 0 für beide — das eigentliche Problem war also nicht
Posture, sondern die Zielwahl-Determinismus selbst.

**Fix:** neue Funktion `App/combat_model/importance.py::choose_removal_target`.
Neues Gewicht `importance_targeting.target_focus_chance` (`Data/Models/
combat_interaction_weights.json`, Default **0,35**): mit dieser Wahrscheinlichkeit
trifft der Gegner weiterhin das laut `removal_target_score` wichtigste Ziel;
sonst fällt die Wahl gleichverteilt zufällig auf ein beliebiges legales Ziel.
`1.0` reproduziert das alte, voll deterministische Verhalten (regressionsgetestet),
`0.0` wäre komplett zufällig. Bewusst **kein** echtes Entscheidungsmodell des
Gegners (Mana, Farbe, Timing werden weiterhin nicht simuliert) — nur eine einzelne,
klar benannte Wahrscheinlichkeit, im selben Stil wie `block_rate_base` oder
`trade_rate_given_blocked`. `combat_block_multiplier` (Combat-Blockchance) war
bereits vorher probabilistisch und blieb unverändert.

**Verifiziert mit 4 neuen Tests** (`tests/test_importance_targeting.py`,
`ChooseRemovalTargetTests` + ein zusätzlicher End-to-End-Test in
`RemovalPhaseIntegrationTests`, alle gegen `apply_abstract_opponent_phase`/
`choose_removal_target` selbst, nicht nur Mocks): `target_focus_chance=1.0`
reproduziert exakt das alte deterministische Verhalten; `target_focus_chance=0.0`
ist über 2000 Trials annähernd gleichverteilt (40–60 %); die real ausgelieferten
Projekt-Gewichte (0,35, aus der echten JSON-Datei geladen, nicht gemockt) wählen
das wichtigste Ziel weiterhin öfter als ein untätiges, aber garantiert **nicht**
mehr in praktisch 100 % der Fälle. Gesamt-Suite: **95/95 grün** (91 bisherige +
4 neue, 4 weiterhin bewusst übersprungen wegen fehlender Datendateien in diesem
Cowork-Checkout).

**Verifikation mit echtem 200er-Bilbo-Run (headless, seed=1, random-Gegner,
gleiches Protokoll wie der v4.8.2-Nachtrag):**

| | v4.8.2 (Baseline-Run) | v4.8.3 (dieser Run) |
|---|---|---|
| Win % | 2,0 % | 2,0 % |
| Avg End Life | 29,4 | 27,1 |
| Bilbo Activation | 0,0 % | 1,0 % |
| Removed by opponent (gesamt) | 160 | 151 |
| davon Bilbo + Doctor Strange | 97 (60,6 %) | 57 (37,7 %) |

Konzentration auf die zwei Engine-Karten von ~61 % auf ~38 % gesenkt, mit mehr
verschiedenen Karten unter den Top-5 (`Prosperous Innkeeper`, `Great Divide
Guide`, `Sol Ring` treffen jetzt auch nennenswert). Win %/Avg Life bewegen sich
weiterhin im Rauschband bei 200 Runs/seed=1 — das war auch nicht das Ziel dieser
Änderung; das Ziel war, die falsche Exaktheit der Zielwahl selbst zu beheben,
nicht garantiert die Gesamtzahlen zu heben. Ergebnis-ZIP:
`Bilbo V1_v4_7_0_20260906-125942.zip`.

**Nächster Schritt:** dem Nutzer zur Bestätigung vorlegen (Windows-GUI-Lauf/
Review), da dies eine Änderung an gemeinsam genutzten Combat-Gewichten ist, die
alle vier Decks betrifft, nicht nur Bilbo — siehe Praxis-Hinweis zu
GUI-Änderungen in `AI_SCENARIO_AUTHORING_PROMPT.md`/Handoff-Dokument. Danach:
WP11 (200er-Diagnostic-Runs für Mabel/Aziza/Katara) kann denselben
`target_focus_chance`-Wert direkt mitnutzen, ohne separate Kalibrierung.

## v4.8.2 — Combat-/Removal-Diagnostik sichtbar gemacht

Dein neuester Run (v4.8.1, generalisierte Posture) zeigte **keine klare
Verbesserung** gegenüber dem reinen Commander-Posture-Stand (Win 1,0 % vs. 2,5 %,
Avg Life 26,5 vs. 28,0 — beides im Rauschbereich bei 200 Runs). Auffällig: Doctor
Stranges "Estimated total value" fiel von 1034 auf 745 — er greift jetzt kaum noch
an und verliert dadurch seinen eigenen Lifelink-Beitrag, ohne dass sich die
Gesamtzahlen sichtbar verbessert hätten. Das ist ein ehrlicher Nicht-Erfolg: die
Rollen-basierte Generalisierung ist vermutlich zu grob für eine Karte, die selbst
über Lifelink Wert aus dem Angreifen zieht.

**Statt weiter an der Angriffs-Heuristik zu raten, mache ich das Verhalten
messbar**, bevor ich es nochmal ändere:

- `record_impact(..., "removed_by_opponent", 1)` beim Single-Target-Removal-Erfolg
  und `"wiped_by_opponent"` beim Boardwipe — existierte bisher nirgends,
  `died_in_combat`/`combat_blocked` (aus WP6) liefen zwar schon mit, waren aber nie
  exportiert.
- Neue Spalten in `card_impact.csv`: **Died in combat, Blocked in combat, Removed
  by opponent, Wiped by opponent, Commander damage lethal hits.**
- Neuer Abschnitt `combat_and_removal_diagnostics` in `summary.json`: Summen +
  Durchschnitt/Run + Top-5-Karten für Combat-Tode und gegnerisches Removal.

Damit zeigt der nächste Run direkt, **wie oft** und **welche Karten** sterben,
statt dass wir das aus Gesamt-Win-%-Verschiebungen erraten müssen.

Verifiziert mit 2 neuen Tests (`tests/test_combat_removal_diagnostics.py`), einer
davon end-to-end gegen die echte `attack_phase`. Gesamt-Suite: **91/91 grün**.

```powershell
python -m unittest discover -s tests -v
```

**Nächster Schritt:** Bitte noch einen 200er-Bilbo-Run (random-Gegner) — diesmal
schicke ich dich nicht auf Verdacht in eine weitere Verhaltensänderung, sondern wir
lesen aus `combat_and_removal_diagnostics` und den neuen CSV-Spalten ab, was
wirklich passiert, bevor die nächste Entscheidung (Posture weiter verfeinern vs.
Combat-/Removal-Gewichte direkt anfassen) ansteht.

### Nachtrag — der angeforderte 200er-Run liegt jetzt vor (headless, seed=1, random-Gegner)

Selbes Protokoll wie die bisherige Baseline-Tabelle (200 Runs, 10 Turns, seed=1,
`strategy_tags={"lifegain"}`, kein Scenario-File, `opponent_profile=random`),
gegen den echten v4.8.2-Code gefahren (Ergebnis-Ordner
`Bilbo V1_v4_7_0_20260906-094437`, `summary.json.version = "4.8.2"`):

| | v4.8.1 (Nachtrag oben) | v4.8.2 (dieser Run) |
|---|---|---|
| Win % | 1,0 % | 2,0 % |
| Avg End Life | 26,5 | 29,4 |
| Bilbo Activation | 0,5 % | 0,0 % |
| Commander zone returns (Bilbo) | 73/200 | 83/200 |

Innerhalb der üblichen Streuung bei 200 Runs/seed=1 — keine Verhaltensänderung
in v4.8.2 zu erwarten, da nur Diagnostik ergänzt wurde. Die eigentlich neue
Information steckt in `combat_and_removal_diagnostics`:

- **Died in combat (gesamt 187, Ø 0,935/Run):** verteilt sich auf günstige
  Drain-/Lifegain-Payoff-Kreaturen (Top 5: Dina Soul Steeper 20, Elas il-Kor 19,
  Vito 18, Kambal 18, Corpse Knight 16). **Weder Bilbo noch Doctor Strange
  sterben im Kampf (0 in beiden Spalten)** — Posture tut also exakt, was sie
  soll: die beiden Engine-Karten werden nicht mehr sinnlos verheizt.
- **Removed by opponent (gesamt 160, Ø 0,8/Run):** hier zeigt sich das eigentliche
  Muster — **Bilbo 70 und Doctor Strange 27 = 97/160 = ~61 % des gesamten
  gegnerischen Removals im gesamten Deck**, obwohl beide zusammen nur 2 von
  ~59 Nicht-Land-Karten sind. Nächstgrößter Wert: Prosperous Innkeeper mit nur 10.
- **Wiped by opponent:** Bilbo zusätzlich 22×, Doctor Strange 6× durch Board-Wipes
  getroffen (kein Top-5 für diese Spalte im Summary, aber in `card_impact.csv`
  einsehbar).

**Lesart:** Posture hat das Combat-Todesrisiko der Engine-Karten bereits auf 0
gedrückt — das ist ein voller Erfolg für das, was Posture eigentlich adressieren
sollte. Win % und Avg Life haben sich trotzdem nicht erholt, weil ein *anderer*
Verlustkanal dominiert, den Posture gar nicht anfassen kann: das
importance-gewichtete Removal-Targeting (WP6 Iteration 2) konzentriert sich mit
~61 % fast ausschließlich auf genau die zwei Karten, die Posture schützt. Doctor
Stranges durch Passivität verlorener Lifelink-Beitrag (Estimated total value
889 in diesem Run, zuvor 1034→745 dokumentiert — beides im Rauschen bei
Einzel-Seed-200-Runs) bleibt also ein zweiter, kleinerer Effekt, aber nicht die
Hauptursache.

**Damit evidenzbasiert statt geraten:** Die Daten sprechen für Option 2 aus dem
Nächste-Schritte-Katalog — **`importance_targeting.removal_weight` in
`Data/Models/combat_interaction_weights.json` direkt anfassen** (z. B. Deckelung,
wie stark Removal auf die höchstwertige Karte konzentriert wird), statt Posture
weiter zu verfeinern (Lifelink-Sonderfall für Doctor Strange würde sein
Combat-Todesrisiko senken, das aber laut dieser Daten bereits 0 ist — würde also
vermutlich nichts am Gesamtergebnis ändern). Vor einer Gewichtsänderung bitte
Rücksprache, da das direkt das Combat-Modell für alle vier Decks betrifft, nicht
nur Bilbo.

Ergebnis-ZIP: `Bilbo V1_v4_7_0_20260906-094437.zip` (headless in Cowork erzeugt,
identisches Format wie ein GUI-Run).

## v4.8.1 — Posture verallgemeinert auf Value-Engine-Kreaturen

Direkt aus deinem Diagnostic-Run abgeleitet: Posture allein reduzierte Bilbos
"Commander zone returns" um 78 % (276→62/200 Runs), aber Win % (2 %→2,5 %) und
Avg End Life (23,8→28,0) blieben weit unter der alten Baseline (14 %, 39,3).

Ursache: **Doctor Strange, Surgeon** — Rollen `engine|lifegain|lifegain_replacement`,
der höchste gemessene Kartenwert im gesamten Deck (Lifegain-Verdoppler, zentral für
Bilbos 111-Leben-Plan) — ist NICHT der Commander und wurde von Posture bisher gar
nicht erfasst. Er griff weiterhin jede Runde bedingungslos an, mit echtem
Sterberisiko (WP6) und als wahrscheinlichstes Ziel für importance-gewichtetes
Removal (WP6 Iteration 2).

**Fix:** `commander_should_attack` → `creature_should_attack`, jetzt zuständig für
den Commander **und** jede Kreatur mit einer Engine-artigen Rolle (`engine`,
`lifegain_replacement`, `tutor`, `draw_engine` — dieselben Tags wie beim
AUTO-Posture-Inferenz, jetzt nicht mehr auf "ist Commander" beschränkt). Gewöhnliche
Kreaturen ohne diese Rollen greifen weiterhin unverändert bedingungslos an — das ist
bewusst eng gehalten, nicht "irgendeine Angriffs-KI fürs ganze Board".

Verifiziert mit 6 neuen Tests (Bestandteil von `tests/test_commander_posture.py`,
jetzt 23 Tests insgesamt), inkl. eines End-to-End-Tests mit einer exakten
Doctor-Strange-Nachbildung (Rollen, Lifelink, Power) neben einem gewöhnlichen
Schläger — bestätigt: die Engine-Karte bleibt zurück, der Schläger greift normal
an. Gesamt-Suite: **89/89 grün**.

**Nächster Schritt:** Neuer Diagnostic-Run (random-Gegner) zur Verifikation, bevor
über eine Neukalibrierung der Combat-/Removal-Gewichte selbst nachgedacht wird.

```powershell
python -m unittest discover -s tests -v
```

## v4.8.0 — Commander Posture (WP5, revisited)

Vorgezogen aus dem eigentlichen Zeitplan, weil der 200er-Testlauf aller vier Decks
(dein letzter Upload) einen deutlichen, konsistenten Leistungseinbruch zeigte
(Win % über alle Decks auf 0–2 %, Avg End Life von ~39 auf 6–24). Ursache: seit
WP6/WP7 sterben Kreaturen wirklich im Combat und Removal trifft bevorzugt die
wichtigste Karte — aber jede Kreatur (auch der Commander) griff weiterhin
bedingungslos jede Runde an, egal wie zerbrechlich. Bilbo, Birthday Celebrant
(ein 2/3-Werte-Motor) kam dadurch **276-mal in 200 Runs** in die Command Zone
zurück (~1,4×/Spiel) und "Bilbo Activation" fiel auf 0 %.

Neues Modul `App/combat_model/posture.py`. Neues Strategy-Feld
`commander_posture: "auto" | "passive" | "balanced" | "aggressive"`.

- **AGGRESSIVE**: Commander greift immer an (bisheriges Verhalten, unverändert).
- **PASSIVE**: Commander greift NUR an, wenn er (a) eine eigene
  "Whenever ~ attacks"-Value-Fähigkeit hat (generisch aus Oracle-Text erkannt,
  keine Kartennamen-Sonderfälle), oder (b) der Angriff gerade ein Ziel eliminieren
  würde, oder (c) er damit seine Commander-Damage-Ledger gegen ein Ziel, das
  bereits > 0 hat, tatsächlich auf 21 abschließen würde. Ein "erster Poke" auf ein
  Ziel bei 0 zählt bewusst NICHT als Grund.
- **BALANCED**: wie Passive, plus: greift zusätzlich an, wenn bereits mindestens
  `posture.balanced_min_other_attackers` (Default 2, `combat_interaction_weights.json`)
  andere Kreaturen angreifen — mehr Angreifer verdünnen die Blockchance pro
  Angreifer ohnehin (bestehender wide-board-Effekt aus WP6), das Risiko für den
  Commander ist dann geringer.
- **AUTO**: leitet eine Tendenz aus den vorhandenen Karten-Rollen ab (`finisher` →
  aggressive; `engine`/`lifegain_replacement`/`tutor`/`draw_engine` → passive;
  sonst balanced) — Bilbo (Rollen `engine|lifegain_replacement|tutor`) bekommt so
  automatisch PASSIVE, ohne dass irgendwo sein Name vorkommt.

**Bewusst kein Sicherheits-/Risikomodell** (siehe Moduldoku): Die Engine kennt
weiterhin keine gegnerischen Blocker, gegen die man "sicher" oder "unsicher"
angreifen könnte. Posture unterscheidet nur Value-Gründe von Kein-Grund, nicht
"riskant" von "sicher".

Verifiziert mit 17 neuen Tests (`tests/test_commander_posture.py`), inkl. eines
End-to-End-Tests mit exakt Bilbos Rollen-Signatur. Gesamt-Suite: **83/83 grün**.

**Nächster Schritt (noch offen):** Auch bei aktivierter Posture bleibt fraglich,
ob die WP6-Gewichte (`trade_rate_given_blocked`, `importance_targeting`) insgesamt
zu hart kalibriert sind — das lässt sich erst nach einem neuen Diagnostic-Run mit
Posture beurteilen.

```powershell
python -m unittest discover -s tests -v
```

## v4.7.9 — Bugfix: Deck-Zeilen mit Foil-Marker (*F*/*E*) scheiterten an Scryfall

**Gefunden über echte GUI-Nutzung** (Mabel- und Aziza-Deck luden nicht vollständig).

Ursache: `TXT_LINE_RE` kannte das Suffix `*F*`/`*E*` (Foil/Etched-Kennzeichnung,
wie es Moxfield/Archidekt beim Export anhängen) nicht. Bei einer Zeile wie

```
1 Wyleth, Soul of Steel (CMR) 362 *F*
```

schlug dadurch die komplette `(SET) Nummer`-Erkennung fehl (der reguläre Ausdruck
verlangte direkt nach der Collector-Number das Zeilenende), und die GESAMTE Zeile
inklusive `(CMR) 362 *F*` landete im Kartennamen. Scryfall konnte diesen
"Namen" natürlich nicht finden — das war kein Scryfall-Problem, sondern ein
Parser-Bug vor dem eigentlichen Lookup.

**Betroffen waren mindestens:** Wyleth, Soul of Steel (Mabel-Deck), Hordeling
Outburst und The Scarlet Witch (Aziza-Deck) — alle drei jetzt geprüft und korrekt.
Alle vier Decklisten (Bilbo, Mice with Swords, Aziza, Katara) wurden komplett neu
durchgeparst: **keine verbleibenden Zeilen mit unaufgelöstem `(...)`-Rest im
Namen.**

Fix: `TXT_LINE_RE` erlaubt jetzt optional ein `\s+\*[A-Za-z]+\*` nach der
Collector-Number, bevor das Zeilenende geprüft wird.

Verifiziert mit 11 neuen Tests (`tests/test_decklist_parsing.py`), inkl. eines
vollständigen Parse-Sweeps über alle vier echten Decklisten. Gesamt-Suite: **66/66
grün**.

```powershell
python -m unittest discover -s tests -v
```

Bitte bei dir erneut "GO FISHING" mit dem Mabel- und Aziza-Deck versuchen — die
Metadaten sollten jetzt vollständig laden.

## v4.7.8 — Equipment-Modell (WP7, Iteration 2)

Zweiter Teil von WP7. Neues Modul `App/combat_model/equipment.py`, generisch aus
Oracle-Text geparst (keine Kartennamen-Sonderfälle):

- `Permanent.attached_to` — neues Feld: an welche Kreatur ein Equipment-Permanent
  aktuell angelegt ist (`None` = nicht angelegt).
- `parse_equip_cost()` — liest die generische Manawertung aus "Equip {N}".
- `parse_equipment_bonus()` — liest "Equipped creature gets +X/+Y and has
  <Keywords>" aus der Equipment-Textzeile (auf diese Zeile begrenzt, damit z. B.
  "Whenever equipped creature deals combat damage..." nicht versehentlich mit
  hineinparst).
- `creature_power()` und `effective_keywords_in_state()` berücksichtigen jetzt
  angelegte Equipment-Boni/-Keywords automatisch.
- `auto_equip_step()` — vereinfachte Precombat-Automatik: nicht angelegtes,
  bezahlbares Equipment wird an die beste verfügbare Kreatur angelegt (Commander
  bevorzugt, sonst höchste Power). Bereits angelegtes Equipment wird nicht
  umgehängt.
- `detach_if_creature_left()` — fällt automatisch ab, wenn die getragene Kreatur
  das Schlachtfeld verlässt (z. B. durch die neue Combat-Interaction aus WP6).

**Bewusst außerhalb dieser Iteration (siehe Moduldoku):**
- "Whenever equipped creature ..."-Trigger (z. B. Bloodforged Battle-Axe' Token-
  Erzeugung) — das ist eine getriggerte Fähigkeit, kein statischer Bonus, und
  braucht eine andere Anbindung.
- Equipment-Tutor/-Recursion — brauchen keine neue Infrastruktur, sobald eine
  Equipment-Karte ein normales Tutor-/Recursion-Ziel ist; nicht gesondert gebaut.
- Valiant ("first time this creature becomes the target...") — braucht ein
  "Target Event"-Konzept, das noch nicht existiert.
- **Vereinfachung bei der Bezahlbarkeits-Prüfung:** `auto_equip_step` prüft nur die
  gesamte verfügbare Manawertung, keine echte farbgebundene Payment-Simulation.

Verifiziert mit 12 neuen Tests (`tests/test_equipment.py`), inkl. echter Parsing-
Tests gegen Colossus-Hammer-artigen Oracle-Text. Gesamt-Suite: **55/55 grün**. Noch
nicht gegen echte Scryfall-Metadaten des Mabel-Decks getestet (kein Netzwerkzugriff
in meiner Umgebung) — das sollte beim nächsten GUI-Testlauf mit dem Mice-with-
Swords-Deck mitgeprüft werden.

```powershell
python -m unittest discover -s tests -v
```

## v4.7.7 — Commander-Damage-Ledger + Double Strike (WP7, Iteration 1)

Erster Teil von WP7 (Equipment folgt als eigene Iteration). `GameState` bekommt ein
neues Feld `commander_damage_dealt: Dict[int, float]` — **pro Gegner-Index**, passend
zu `state.opponents` (bewusst so gebaut, damit ein späteres Mehrspieler-Update
[WP12] hier nichts umbauen muss).

- `attack_phase` erkennt jetzt, ob ein Angreifer der Commander ist
  (`AttackerInfo.is_commander`, schon aus WP6 vorhanden) und schreibt dessen
  Combat-Damage zusätzlich in die Ledger.
- **21 Commander Damage gegen einen Gegner** eliminiert diesen Gegner: sein Leben
  wird auf 0 gesetzt, was den bereits bestehenden "alle Gegner bei 0 = Win"-Check
  automatisch mitgreifen lässt — keine neue Sieg-Bedingung nötig, nur ein neuer Weg,
  bestehende Zustände zu erreichen.
- **Double Strike wird jetzt tatsächlich simuliert**: ungeblockter Schaden wird
  verdoppelt (vereinfachend — kein zweistufiger First-Strike/Regular-Damage-Schritt,
  siehe Docs).
- Der WP4-Platzhalter `commander_damage_lethal` ist jetzt implementiert: prüft, ob
  die aktuelle Commander-Power (inkl. Double Strike) für die restlichen bis 21
  reicht. **Wichtig:** Das ist eine OPPORTUNITY-Aussage ("wäre lethal, WENN
  unblockiert"), keine Garantie — ob der Angriff wirklich durchkommt, entscheidet
  weiterhin die probabilistische Combat-Interaction-Funktion (WP6) zur Laufzeit.

**Bekannte Einschränkung (transparent, nicht versteckt):** Commander-Schaden geht
weiterhin an den Gegner mit dem *aktuell höchsten Leben* (bestehende Heuristik) statt
an ein bewusst gewähltes Voltron-Ziel. Für Mabels "21 Commander Damage auf ein festes
Ziel"-Plan (WP10) wird das wahrscheinlich eine gezieltere Angriffs-Priorisierung
brauchen — vorgemerkt, hier bewusst noch nicht mitgelöst, um WP7/Iteration 1 klein
zu halten.

**Noch nicht enthalten (folgt als Iteration 2):** Equipment (attach/detach, Boni,
Valiant, Tutor/Recursion). Damit deals dieser Teil nur mit Damage-Tracking und
Double Strike auf Basis der reinen Kreatur-Power.

Verifiziert mit 9 neuen Tests (`tests/test_commander_damage.py`), End-to-End gegen
die echte `attack_phase`. Gesamt-Suite: 43/43 grün.

```powershell
python -m unittest discover -s tests -v
```

## v4.7.6 — Impact-gewichtetes Targeting (WP6, Iteration 2)

Removal-Zielwahl und Combat-Blockchance berücksichtigen jetzt, wie viel eine Karte
**in diesem Run bereits geleistet hat** (`state.impact`, laufend während der
Simulation befüllt) — zusätzlich zur bestehenden statischen `tutor_priority`-Liste,
nicht als Ersatz dafür. Neues Modul `App/combat_model/importance.py`.

- `removal_target_score()` — ersetzt in `apply_abstract_opponent_phase` die reine
  `generic_tutor_score`-Sortierung für Spot-Removal-Ziele um einen Bonus aus
  `live_impact_score()` (Summe der bisherigen Impact-Werte der Karte, normalisiert
  auf "pro Zug", damit früh/spät im Spiel vergleichbar bleibt).
- `combat_block_multiplier()` — der aktuell aktivste Angreifer eines Combats bekommt
  einen Bonus auf seine Blockchance relativ zu den übrigen Angreifern (nicht
  absolut) — ein untätiger Spielstand liefert keinen Bonus (Multiplikator 1.0).
- Beide Gewichte (`removal_weight`, `combat_block_weight`) liegen in
  `Data/Models/combat_interaction_weights.json` unter `importance_targeting` — frei
  justierbar.

**Bewusste Begrenzung:** Nur **kausal, innerhalb desselben Runs** — nutzt ausschließlich
Impact-Daten, die im *aktuellen* simulierten Spiel bereits entstanden sind, keine
aggregierten Werte aus früheren Batches. Eine spätere Erweiterung um
"historisch gelernte Kartenwichtigkeit" (z. B. aus einem abgeschlossenen 200er-Batch)
wäre ein eigenes, separat zu kennzeichnendes Feature — sie hat ein
Survivorship-Bias-Risiko: eine Karte, die deshalb öfter entfernt wird, weil sie
wichtig war, zeigt in genau den Daten, die diese Einschätzung stützen sollen,
danach möglicherweise WENIGER gemessene Wirkung.

Verifiziert mit 8 neuen Tests (`tests/test_importance_targeting.py`), inkl. eines
statistischen End-to-End-Tests direkt gegen die echte `apply_abstract_opponent_phase`
(nicht nur gegen die isolierte Scoring-Funktion). Gesamt-Suite: 34/34 grün.

```powershell
python -m unittest discover -s tests -v
```

## v4.7.5 — Combat-Interaction-Funktion (WP6, Iteration 1)

Ersetzt den bisherigen pauschalen `block_factor` (ein fester Multiplikator auf den
gesamten Combat-Schaden pro Zug) durch eine **pro Angreifer gewürfelte** Interaktion:
geblockt-und-getauscht (Angreifer stirbt), geblockt-und-gechumpt (Angreifer überlebt,
0 Schaden) oder ungeblockt (voller Schaden). Neues Modul `App/combat_model/`.

**Warum keine echte Blocker-Simulation:** Es gibt weiterhin kein Board aus benannten
gegnerischen Kreaturen — das wäre für 5.000 Runs zu teuer und würde dem "kein
vollständiger Rules-Engine-Klon"-Grundsatz widersprechen. Stattdessen: eine
gewichtete Zufallsfunktion mit Parametern in
`Data/Models/combat_interaction_weights.json` (frei justierbar, ohne Code zu
ändern) — gleiches Prinzip wie schon `OPPONENT_PROFILES`, nur pro Angreifer statt
als eine feste Zahl fürs ganze Combat.

Gewichtungsfaktoren pro Gegnerprofil:
- `block_rate_base` — Grundwahrscheinlichkeit, geblockt zu werden.
- `trade_rate_given_blocked` — Wahrscheinlichkeit, dass ein Block den Angreifer tötet
  (vs. nur Schaden verhindert).
- `evasion_keyword_multiplier` — Flying/Menace/Trample reduzieren die Blockchance
  multiplikativ.
- `wide_board` — mehr Angreifer als der Gegner "abdecken" kann, senkt die
  Blockchance pro Angreifer.
- `turn_ramp` — früh im Spiel hat der Gegner weniger Blocker/Removal verfügbar.

**Kalibrierung:** `block_rate_base` ist so gewählt, dass der **Erwartungswert** des
durchkommenden Schadens ungefähr dem alten `block_factor` entspricht (bei Turn 6,
1 Angreifer: Aggro 0.803 vs. altes 0.78, Midrange 0.718 vs. 0.68, Control 0.627 vs.
0.58, Horde 0.751 vs. 0.72 — Abweichung stammt bewusst vom Turn-Ramp: früh im Spiel
etwas weniger Block als das alte Pauschalmodell). Das ist eine erste Eichung, keine
reale Matchup-Statistik.

**Echte Konsequenz, die es vorher nicht gab:** Kreaturen können jetzt tatsächlich im
Combat sterben (Permanent → Friedhof inkl. Commander-Zonen-Logik; Token-Gruppen:
`count` sinkt). Indestructible wird respektiert (übersteht ein tödliches Block-
Ergebnis). Das ist auch die Voraussetzung für eine ehrliche Commander-Posture
später (WP7) — vorher gab es kein Risiko, das eine "vorsichtige" Posture hätte
vermeiden können.

Reproduzierbarkeit: `attack_phase` bekommt jetzt den seed-gebundenen `rng` aus der
Turn-Loop durchgereicht (vorher unbenutzt für Combat).

Verifiziert mit 11 neuen Unit-Tests (`tests/test_combat_interaction.py`) + einem
statistischen Sanity-Check (20.000 Wiederholungen pro Profil, siehe oben) +
vollständige Regression (26/26 Tests insgesamt):

```powershell
python -m unittest discover -s tests -v
```

**Offen für Iteration 2+ (nach deiner Rückmeldung):** Commander-spezifische
Gewichtung (Commander wird evtl. bevorzugt geblockt — "the commander painted a
target on itself"), Kopplung an das kommende Commander-Damage-Ledger, ggf. eigene
Gewichte für Extra-Combat-Phasen.

## v4.7.4 — Scenario-Schema v4.4: dynamische Bedingungen (WP4)

Neues Modul `App/scenario_predicates/` (gleiches Muster wie die Keyword-Bibliothek)
fügt Win-Conditions einen optionalen `derived`-Block hinzu, mit dem **berechnete/
dynamische** Bedingungen deckübergreifend formuliert werden können — nicht nur
„Karte X in Zone Y":

- `App/scenario_predicates/definitions.json` — deklariert jeden Prädikat-Typ
  (Parameter, Modellgüte, Beschreibung).
- `App/scenario_predicates/handlers.py` — implementiert: `resource_available`
  (Mana/ungetappte Kreaturen/Artefakte/Food/Treasure/Clue), `opponent_life_at_or_below`
  (aktuelles GEGNERleben, nicht das eigene), `x_spell_lethal` (sucht das kleinste
  bezahlbare X eines benannten X-Spells, das inkl. Copy-Multiplikator gegen das
  Restleben eines Ziels reicht — nutzt die bestehende `x_effect_metrics`/`best_x_plan`-
  Infrastruktur).
- `commander_damage_lethal` ist bereits als Vertrag/Parameterform deklariert
  (`"handler": null`), damit Mabels Scenario-Datei strukturell korrekt vorbereitet
  werden kann — die eigentliche Berechnung kommt erst mit dem Commander-Damage-
  Ledger/Equipment-Modell (spätere Work Packages). Bis dahin liefert die Auswertung
  explizit `derived_computable: False` statt eines stillschweigend falschen
  Ergebnisses.
- **Abwärtskompatibel:** Bestehende v4.3-Dateien ohne `derived`-Schlüssel verhalten
  sich exakt wie zuvor (per Regressionstest gegen die echte
  `bilbo_win_conditions.json` geprüft).
- `derived` wird jetzt korrekt durch `normalize_scenario`/`save_scenarios`/
  `load_scenarios` durchgereicht (vorher hätte ein naiver Round-Trip das Feld
  stillschweigend verworfen — per Test abgesichert).

Details und Beispiele: `Docs/SCENARIO_SCHEMA.md`.

Verifiziert mit 9 neuen, Tk-freien Unit-Tests (`tests/test_scenario_predicates.py`,
zusammen mit WP3 jetzt 15/15 grün):

```powershell
python -m unittest discover -s tests -v
```

## v4.7.3 — Keyword-Bibliothek (WP3)

Neues Modul `App/keyword_library/` ersetzt die bisherige if/elif-Kette in
`execute_semantic_action` durch eine datengetriebene Registry:

- `App/keyword_library/definitions.json` — deklarative Beschreibung jedes erkannten
  Keywords/Mechanik (Kategorie, Modellgüte exact/simplified/probabilistic/review,
  deutsche Beschreibung, erwartete Parameter, verweisender Handler).
- `App/keyword_library/handlers.py` — die eigentliche Spiellogik je Handler
  (1:1 aus der alten if/elif-Kette übernommen, Verhalten unverändert).
- `App/keyword_library/registry.py` — lädt die JSON-Datei, verwaltet die
  Handler-Registrierung, stellt `resolve_action(...)` bereit.

**Wichtig für Erweiterung:** Eine neue, mechanisch identische Mechanik (z. B. eine
neue Set-Fähigkeit mit Ähnlichkeit zu Connive) braucht **keinen neuen Python-Code** —
nur einen neuen Eintrag in `definitions.json`, der auf einen bestehenden Handler
verweist. Als Beispiel liegt bereits `hobbit_second_breakfast` in der Datei: ein
Platzhalter-Eintrag, der testweise auf den `connive`-Handler zeigt. Sobald der exakte
Oracle-Wortlaut der neuen Hobbit-Mechanik bekannt ist, muss geprüft werden, ob die
Regeln wirklich 1:1 zu Connive passen (dann reicht `aliases` befüllen) oder ob echte
Unterschiede bestehen (dann eigener Handler + `model_layer` anpassen).

Unbekannte Mechaniken werden jetzt explizit gezählt (`unhandled_semantic_action:<kind>`
als Engine-Metrik) statt einfach stillschweigend zu `False` zu werden — das macht
Modelllücken in `card_model_coverage.csv`/`semantic_runtime_report.csv` sichtbar.

Verifiziert per echtem (Tk-freiem) Funktionstest gegen `App/engine.py`: `draw`,
`gain_life`, `plus1_counter` und ein unbekannter Aktionstyp wurden mit konstruierten
Dummy-States direkt durch `execute_semantic_action` geschickt und die State-Mutation
(Handgröße, Leben, Counter) geprüft — keine GUI/Tkinter nötig für diesen Test.

## v4.7.2 — Analysis-Page (WP2)

„Auswertung" öffnet die Ergebnisse jetzt **im selben Hauptfenster** statt in einem
separaten Tkinter-Toplevel-Fenster:

- `AnalysisWindow(tk.Toplevel)` wurde zu `AnalysisPage(ttk.Frame)`, registriert im
  selben Seiten-Container wie Home/Main/Win-Conditions-Setup.
- Neuer Button **„Zurück zum Deck"** führt zurück zur Simulationsseite (`MainPage`).
- Der Button „Auswertung" (neben „Ergebnisordner öffnen“) bleibt wie bisher bis zum
  ersten erfolgreichen Run deaktiviert und wird danach aktiviert.
- Da sich der Ergebnisordner zwischen Runs ändert, baut `AnalysisPage.load(result_dir)`
  das Notebook (Übersicht/Rundenverlauf/Win Conditions/Strategy/Opponent) bei jedem
  Öffnen neu auf — kein neues OS-/Tk-Fenster mehr.

Inhaltlich unverändert gegenüber v4.7.0: alle fünf Auswertungs-Tabs, Metriken und
Diagramme sind identisch, nur die Fenstermechanik hat sich geändert.

## v4.7.1 — Projektstruktur (Zwischenschritt vor v4.8)

Diese Version ändert **nur** die Datei-/Ordnerstruktur und den Deck-Autoscan.
Simulationslogik, GUI-Seiten und Auswertung sind inhaltlich unverändert gegenüber v4.7.0.

Neue Struktur:

```
Commander_Goldfish/
├─ commander_goldfish.py       (Launcher)
├─ Start_Goldfish_GUI.bat
├─ App/
│  ├─ engine.py                (ehem. commander_goldfish_v4_7_0.py)
│  └─ gui.py                   (ehem. commander_goldfish_v4_7_0_gui.py)
├─ Decks/                      (auto-gescannt; "Deks" wird als Alias erkannt)
├─ Goldfish_Results/<Deckname>/<Run>
├─ Data/
│  ├─ Scenarios/  Strategies/  Models/  Cache/
├─ Projects/
└─ Docs/
```

Was sich funktional ändert:

- Die Startseite listet Decks aus `Decks/` automatisch in einer Combobox
  (`.txt`/`.csv`), zusätzlich weiterhin manuelles Laden von beliebigem Pfad möglich.
- Ergebnisse landen unter `Goldfish_Results/<Deckname>/` statt neben der Deckdatei.
- Der Scryfall-/Metadaten-Cache liegt jetzt unter `Data/Cache/scryfall_card_cache.json`.
- Scenario-Dialoge öffnen standardmäßig in `Data/Scenarios/`.
- Der Crash-Log liegt im Projekt-Root statt in `App/`.
- `PYTHONDONTWRITEBYTECODE=1` im Launcher/BAT hält `__pycache__` aus dem Nutzerordner.

Bekannte offene Punkte für v4.8 (siehe Projekt-Prompt): Analysis-Page-Umbau,
Commander Posture, Equipment/Combat/Commander-Damage-Modell, Keyword-Bibliothek,
erweitertes Scenario-Schema, Resource-Allocation-Planner, Mabel/Aziza/Katara-Szenarien.

---

# Commander Goldfish v4.7.0

## Ergebnis des v4.6-Aggro-Checks

Der hochgeladene 5.000er-v4.6-Lauf bestätigt:

- `engine_invariants.status = PASS`
- Resource invariant violations = 0
- Payment resource conflicts = 0
- Food/Treasure enden nie negativ
- Royal Treatment: 157 Uses / 157 Mana
- Heroic Intervention: 88 Uses / 176 Mana
- Eerie Interlude: 54 Uses / 162 Mana
- Arwen: 37 Protection Uses / 74 +1/+1-Counter
- Bilbo:
  - 98,12 % der Spiele mindestens einmal gecastet
  - 1,347 Casts pro Run
  - 6.547 Command-Zone-Casts
  - 187 Hand-Casts
  - 1.968 Command-Zone-Returns
  - 3.674 Mana Commander Tax

Der Run hatte **keine ausgewählten Strategy-Tags**. Lifegain wurde daher nicht als
Strategy-Pilotbias benutzt; die Auswertung darf Lifegain nur aus den Deckrollen erkennen.

## Drei zusätzliche v4.6-Korrekturen

### 1. Board Modifier im Combat
Temporäre/statische Team-Keywords und Team-P/T-Modifikatoren werden jetzt auch im echten
Combat-Pfad gelesen, inklusive Creature Tokens.

### 2. Semantic Timing
Combat-Buffs werden nicht mehr unnötig erst im End Step aktiviert.

Es gibt nun grobe Aktivierungsfenster:
- `precombat` für Team-P/T/Combat-Keywords
- `value` für Draw, Scry, Lifegain, Token-/Counter-Value

### 3. Reproduzierbares Tuck
Library-Shuffle bei abstraktem Tuck verwendet keinen unseeded globalen Zufall mehr.

## Eerie Interlude
Blink wird zeitlich besser abgebildet:
- Kreaturen verlassen das Battlefield als Reaktion;
- die abstrakte Interaktion resolved;
- anschließend kehren die Kreaturen zurück und erzeugen ihre ETB-Ereignisse.

Dies bleibt eine vereinfachte Stack-/Timing-Repräsentation.

---

# Random Opponent

Neuer Opponent-Modus:

`random`

Er verwendet:
- Aggro
- Midrange
- Control
- Horde

Goldfish ist nicht enthalten.

Random läuft in **balancierten, seed-reproduzierbaren 4er-Zyklen**:
Jede vollständige Gruppe von vier Runs enthält jedes Profil exakt einmal, aber in zufällig
gemischter Reihenfolge.

Ein Diagnostic-Run mit 200 Spielen ergibt daher exakt:
- 50 Aggro
- 50 Midrange
- 50 Control
- 50 Horde

`runs.csv`, `turns.csv`, `opening_hands.csv` und `scenario_runs.csv` enthalten das
tatsächlich verwendete `opponent_profile`.

`summary.json -> opponent_breakdown` enthält die Profilvergleiche.

---

# Direkte Auswertungsoberfläche

Neben `Ergebnisordner öffnen` befindet sich jetzt der Button:

**Auswertung**

Vor einer abgeschlossenen Simulation ist er deaktiviert.

Nach dem Lauf öffnet er eine lokale, vollständig KI-freie Auswertung mit fünf Tabs.

## Übersicht
- Runs
- Win %
- Loss %
- noch aktive Spiele am Turn-Limit
- Engine-Invariant-Status
- Ø Endleben
- Ø Endhand
- Opening Lands / Mulligans
- Strategy
- regelbasierte Auffälligkeiten
- relative Card-Highlights

## Rundenverlauf
Charts und Tabelle für:
- Ø Life
- kumulativ gewonnenes Life
- kumulative Win-/Loss-/Aktiv-Prozente
- Handgröße
- Mana
- Tokens

Cumulative Outcomes beziehen sich auf alle gestarteten Runs.
Durchschnittliche Board-/Life-Werte beziehen sich auf die Spiele, die am jeweiligen Turn
noch aktiv sind oder dort enden. Die Oberfläche weist deshalb ausdrücklich auf Survivor
Bias hin.

## Win Conditions
Pro Scenario:
- Match / Reach %
- Median Turn
- Cards-/Threshold-ready %
- Focus Turns
- häufigster Bottleneck

## Strategy
Strategy-abhängige Darstellung.

Derzeit besonders:
- Lifegain: Life, kumulativer Lifegain, Lifegain/Turn
- Tokens: aktuelle Tokens, Creature Tokens, Food, kumulativ erstellte Tokens
- Counters: +1/+1 und benannte Counter

Wenn keine Strategy ausgewählt wurde, kann das Dashboard Deckrollen zur **Anzeige**
inferieren. Diese Inferenz verändert niemals rückwirkend die Simulation.

## Opponent
Bei Random:
- Runs pro Profil
- Win/Loss/Aktiv %
- Ø Endlife
- Ø Damage
- 111-Life %
- Profilcharakteristika

Bei einem festen Gegner wird dessen einzelnes Profil angezeigt.

---

# Neue Ergebnisdateien

Zusätzlich zu den bisherigen Dateien:

- `analysis_overview.json`
- `analysis_turns.csv`

`card_impact.csv` enthält außerdem:
- Semantic ability uses
- Probabilistic semantic events
- Blinked creatures

---

# Validierung

v4.7 wurde getestet mit:

- festem Aggro-Profil
- Random 200
- Random Seed-Reproduzierbarkeit
- Eerie-delayed-blink
- Analysis-Handoff
- GUI-Import
- Resource-/Payment-Invarianten

Random 200 Test:
- Aggro 50
- Midrange 50
- Control 50
- Horde 50
- Resource invariant violations 0
- Payment resource conflicts 0
- Engine status PASS

## Start

```powershell
python commander_goldfish_v4_7_0_gui.py
```

oder:

`Start_Goldfish_v4_7_0_GUI.bat`
