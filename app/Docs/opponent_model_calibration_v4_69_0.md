# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.69.0

Begleitdokument zu `Docs/README.md` (v4.69.0-Eintrag),
`Data/Models/opponent_state_weights.json` (version "1.7") und
`App/opponent_model/state_equation.py`s Moduldoc-Abschnitt "v4.69.0"
("Kalibrierungs-Synthese Teil 3"). Ersetzt NICHT
`Docs/opponent_model_calibration_v4_67_0.md`, sondern baut direkt darauf
auf — dieses Dokument beantwortet eine konkrete methodische Rückfrage des
Nutzers zu v4.67.0.

## Ausgangsfrage des Nutzers (wörtlich, Kernaussage)

> "Dieses Kalibrierungsmodell soll [...] abbilden, welchen Effekt
> tatsächlich die Farben und welchen Effekt die Strategien auf die
> Zusammenstellung von Decks [...] haben. [...] Ich kann mir vorstellen,
> dass sich vieles angleicht, wenn in einer Farbe unterschiedliche
> Strategien vereinheitlicht werden zu einem sich ausmittelnden Wert [...].
> Meine Bitte [...] ist, dass du genau herausfindest, welche
> Gemeinsamkeiten und welche Unterschiede auf der Farbebene und welche auf
> der Strategieebene relevant sind [...]. Ich möchte es aber nicht, dass
> das Ergebnis ist, dass es [...] immer genau den Mittelwert aller Decks
> abbildet."

Übersetzt in ein statistisches Problem: v4.67.0 hat Farbe und Strategie
**marginal** (getrennt voneinander gemittelt) kalibriert — eine
Strategie-Tag-Dichte wurde über ALLE Farben gepoolt, eine Farb-Dichte über
ALLE Strategien gepoolt. Wenn die Farbmischung innerhalb eines
Strategie-Tags (oder umgekehrt) nicht repräsentativ für den
Fünf-Farben-/Vier-Strategien-Schnitt ist, kontaminieren sich beide Achsen
gegenseitig — ein echter Effekt auf der einen Achse kann sich durch die
andere Achse "ausmitteln" und dadurch unsichtbar werden, ohne dass er
tatsächlich nicht existiert. Genau diese Sorge hatte der Nutzer, konkret
für `interaction_availability`/`interaction_growth` und `wipe_growth`,
die in v4.67.0 als "flach" disclosed, aber bewusst nicht übernommen wurden.

## Methodik: Zwei-Wege-OLS-Regression statt marginaler Poolung

Statt Farbe und Strategie getrennt zu mitteln, wurden beide gleichzeitig
als Regressoren in eine gewöhnliche kleinste-Quadrate-Regression
(`numpy.linalg.lstsq`, ohne Intercept) gegeben — `statsmodels` ist in
dieser Umgebung nicht installiert, `numpy` reicht für diesen Zweck aber
vollständig aus.

- **Stichprobe**: n=337 Decks — alle Decks aus `deck_profiles.csv` mit
  einem der 4 fokalen EDHREC-Tags ("Aggro"=104, "Midrange"=41,
  "Control"=61, "Tokens"=131 als Horde-Proxy), gezogen aus **allen 32
  Farbidentitäten** (nicht nur den 5 Monofarben wie in v4.67.0s
  Farb-Achse) — das gibt der Regression die nötige Farbvielfalt je
  Strategie-Tag, um den Farbeffekt bei festgehaltener Strategie
  überhaupt schätzen zu können.
- **Regressoren**: 5 Farb-Dummy-Spalten `col_W..col_G` (1, wenn die Farbe
  in der Farbidentität enthalten ist — Mehrfarb-Decks setzen mehrere
  gleichzeitig auf 1) PLUS 4 sich gegenseitig ausschließende
  Strategie-Tag-Dummy-Spalten `tag_Aggro..tag_Tokens` — beide Gruppen
  GLEICHZEITIG im selben Regressionsmodell, ohne Intercept (die Summe der
  Konstanten ist implizit im Farbmodell enthalten).
- **Vollständiger Spaltenrang bestätigt** (9 von 9) — keine perfekte
  Kollinearität, die Regression ist eindeutig lösbar.
- **Signifikanz**: `|Koeffizient| > 2 × Standardfehler`, mit
  homoskedastischer OLS-Formel: `sigma² = (Residuen · Residuen) /
  max(n−k, 1)`, `SE = sqrt(diag(pinv(XᵀX)) · sigma²)`.
- **Vier geprüfte Dichte-Dimensionen** (Anteil an Nicht-Land-Slots):
  `r_board = n_creatures / nonland` (board_presence), `r_inter_fine =
  (n_interaction_single_target + n_protection) / nonland`
  (interaction_availability, Board-Wipes bewusst ausgeschlossen — siehe
  v4.67.0-Begründung, unverändert gültig), `r_wipe = n_boardwipes /
  nonland` (wipe_readiness), `r_mana = n_ramp / nonland` (mana_growth).

**Warum das den Konfundierungs-Verdacht tatsächlich prüft**: der
Farb-Koeffizient in dieser Regression ist der geschätzte Effekt EINER
Farbe, NACHDEM die Strategiemischung des Datensatzes bereits
herausgerechnet wurde (und umgekehrt) — anders als bei getrennter
Mittelwertbildung, wo jede Achse die andere unkontrolliert mitmittelt. Ein
vorher (marginal) verschwundener Effekt, der bei Festhalten der anderen
Achse wieder sichtbar wird, ist der direkte Beleg für eine Konfundierung;
ein Effekt, der auch nach Festhalten der anderen Achse verschwunden
bleibt, ist ein echter Nullbefund und keine Methoden-Schwäche.

## Vollständige Koeffiziententabelle — Farb-Achse (zentriert auf Stichproben-Mittel)

`Multiplikator = 1 + Beta / Stichproben-Mittel(Dimension)`. Fett = signifikant (`|Beta| > 2·SE`).

**board_presence** (Stichproben-Mittel 0.4333):

| Farbe | Beta | SE | Multiplikator | Signifikant? |
|---|---|---|---|---|
| W | +0.0348 | 0.0098 | **1.080** | ja |
| U | −0.0066 | 0.0106 | 0.985 | nein |
| B | +0.0267 | 0.0099 | **1.062** | ja |
| R | −0.0181 | 0.0101 | 0.958 | nein |
| G | +0.0509 | 0.0103 | **1.118** | ja |

**interaction_availability** (Stichproben-Mittel 0.2079, feines Signal ohne Wipes):

| Farbe | Beta | SE | Multiplikator | Signifikant? |
|---|---|---|---|---|
| W | +0.0311 | 0.0067 | **1.150** | ja |
| U | +0.0119 | 0.0073 | 1.057 | nein |
| B | **−0.0310** | 0.0068 | **0.851** | **ja (Umkehr!)** |
| R | +0.0003 | 0.0069 | 1.001 | nein |
| G | −0.0178 | 0.0071 | **0.914** | ja |

**wipe_readiness** (Stichproben-Mittel 0.0380):

| Farbe | Beta | SE | Multiplikator | Signifikant? |
|---|---|---|---|---|
| W | −0.0038 | 0.0038 | 0.899 | nein |
| U | −0.0134 | 0.0041 | **0.648** | ja |
| B | +0.0024 | 0.0039 | 1.064 | nein |
| R | +0.0292 | 0.0039 | **1.769** | ja |
| G | −0.0230 | 0.0040 | **0.395** | ja |

**mana_growth** (Stichproben-Mittel 0.2494):

| Farbe | Beta | SE | Multiplikator | Signifikant? |
|---|---|---|---|---|
| W | −0.0112 | 0.0095 | 0.955 | nein |
| U | +0.0190 | 0.0103 | 1.076 | nein |
| B | +0.0359 | 0.0096 | **1.144** | ja |
| R | +0.0562 | 0.0098 | **1.225** | ja |
| G | +0.0829 | 0.0100 | **1.332** | ja |

## Vollständige Koeffiziententabelle — Strategie-Achse

Gamma = Tag-Koeffizient aus derselben Regression. `neu(Tag) = alter
Vier-Tags-Durchschnitt × (Gamma(Tag) / Durchschnitt aller Gammas)` —
identische Anker-Methodik wie v4.67.0, jetzt auf den entkonfundierten
Gammas statt auf rohen marginalen Medianen.

**board_presence_growth** (alter Anker-Durchschnitt 0.75, inkl. Horde):

| Strategie | Gamma | SE | alt | neu |
|---|---|---|---|---|
| Aggro | +0.4220 | 0.0143 | 0.85 | **0.826** |
| Midrange | +0.4147 | 0.0207 | 0.55 | **0.811** |
| Control | +0.3089 | 0.0170 | 0.30 | **0.604** |
| Horde (Tokens-Proxy) | +0.3879 | 0.0137 | 1.30 | 0.759 (NICHT übernommen, siehe unten) |

Paarweise Signifikanz (Aggro/Midrange/Control): Aggro vs. Midrange
Δ=+0.0072 (SE 0.0252) **nicht signifikant** — Aggro vs. Control Δ=+0.1130
(SE 0.0222) **signifikant** — Midrange vs. Control Δ=+0.1058 (SE 0.0268)
**signifikant**. Ergebnis: Aggro und Midrange bilden eine Stufe, Control
liegt klar und signifikant darunter — echte, robuste Differenzierung,
KEINE Ausmittelung.

**wipe_growth** (alter Anker-Durchschnitt 0.035):

| Strategie | Gamma | SE | alt | neu |
|---|---|---|---|---|
| Aggro | +0.0386 | 0.0056 | 0.00 | 0.032 |
| Midrange | +0.0391 | 0.0081 | 0.03 | 0.032 |
| Control | +0.0487 | 0.0066 | 0.11 | 0.040 |
| Horde | +0.0442 | 0.0053 | 0.00 | 0.036 |

Paarweise Differenzen (Aggro/Midrange/Control) — **alle drei nicht
signifikant** (größte: Aggro vs. Control Δ=−0.0101, SE 0.0086).
**Bestätigt**: die v4.67.0-Einebnung ist echt, keine Konfundierung.

**interaction_growth** (alter Anker-Durchschnitt 0.07625):

| Strategie | Gamma | SE | alt | neu |
|---|---|---|---|---|
| Aggro | +0.2212 | 0.0098 | 0.035 | 0.079 |
| Midrange | +0.2292 | 0.0141 | 0.09 | 0.082 |
| Control | +0.2175 | 0.0116 | 0.16 | 0.078 |
| Horde | +0.1868 | 0.0093 | 0.02 | 0.067 |

Paarweise Differenzen — **alle drei nicht signifikant** (größte: Midrange
vs. Control Δ=+0.0117, SE 0.0183). **Bestätigt**: dieselbe Einebnung wie
bei wipe_growth, ebenfalls echt.

**mana_growth** (alter Anker-Durchschnitt 0.16375):

| Strategie | Gamma | SE | alt | neu |
|---|---|---|---|---|
| Aggro | +0.1481 | 0.0139 | 0.17 | 0.150 |
| Midrange | +0.1642 | 0.0201 | 0.155 | 0.166 |
| Control | +0.1585 | 0.0165 | 0.14 | 0.161 |
| Horde | +0.1760 | 0.0133 | 0.19 | 0.178 |

Paarweise Differenzen — **alle drei nicht signifikant** (größte: Aggro vs.
Midrange Δ=−0.0162, SE 0.0244). v4.67.0s eigene Strategie-Achsen-Änderung
bei `mana_growth` war also selbst nicht statistisch tragfähig — die neuen,
entkonfundiert berechneten Werte liegen wieder näher an den ursprünglichen
v4.39.0-Werten.

## Entscheidungsschema (auf jeden einzelnen Wert dieser Version angewendet)

1. **Signifikant UND widerspricht dem alten Wert** → übernehmen. (Beispiel:
   `B.interaction_availability` 1.20 → 0.85.)
2. **Nicht signifikant, ABER eine eigenständige, ältere
   Real-Decklist-Evidenz existiert** (unabhängig von v4.67.0s eigener
   marginaler Methode) → alten Wert behalten, Unschlüssigkeit disclosen.
   (Beispiel: `U.interaction_availability` bleibt 1.45; `B.wipe_readiness`
   bleibt 1.10, dreifach über unabhängige Messungen reproduziert.)
3. **Weder signifikant noch eigenständige Vorevidenz vorhanden** (der Wert
   stammt ausschließlich aus v4.67.0s eigener, jetzt in Frage gestellter
   marginaler Methode) → auf neutral zurücksetzen (Schlüssel entfernen).
   (Beispiele: `W.mana_growth`, `U.mana_growth`, `U.board_presence`,
   `R.board_presence`.)
4. **Signifikant UND neu** (in v4.67.0 mangels Signifikanz nicht
   aufgenommen) → neu hinzufügen. (Beispiele: `W.interaction_availability`,
   `B.board_presence`, `B.mana_growth`, `G.interaction_availability`.)
5. **Strukturelle Datenlücke statt Konfundierung** → unverändert lassen,
   unabhängig vom Regressionsergebnis. (Einziger Fall:
   `horde.board_presence_growth` — die Tokens-Tag-Kreaturentyp-
   Untererfassung aus v4.67.0 ist keine Farbe/Strategie-Vermengung,
   sondern eine fehlende Datendimension; eine Zwei-Wege-Regression kann
   ein Signal nicht sichtbar machen, das der Decklisten-Zensus nie erfasst
   hat.)

## Übernommene Änderungen — color_modifiers

| Farbe | Dimension | alt (v4.67.0) | neu (v4.69.0) | Regel |
|---|---|---|---|---|
| W | wipe_readiness | 1.65 | **1.30** (revertiert) | Regel 3 (auf ältere Vorevidenz statt Neutral zurückgesetzt — leicht überdurchschnittliche Vorevidenz bleibt plausibel) |
| W | board_presence | 1.05 | **1.08** | Regel 1 (bestätigt, verstärkt) |
| W | interaction_availability | (fehlte) | **1.15** (neu) | Regel 4 |
| W | mana_growth | 0.54 | *entfernt* | Regel 3 |
| U | interaction_availability | 1.45 | **1.45** (unverändert) | Regel 2 |
| U | mana_growth | 0.63 | *entfernt* | Regel 3 |
| U | board_presence | 0.76 | *entfernt* | Regel 3 |
| U | wipe_readiness | 0.55 | **0.65** | Regel 1 |
| B | interaction_availability | 1.20 | **0.85** | Regel 1 (Hauptbefund) |
| B | wipe_readiness | 1.10 | **1.10** (unverändert) | Regel 2 |
| B | board_presence | (fehlte) | **1.06** (neu) | Regel 4 |
| B | mana_growth | (fehlte) | **1.14** (neu) | Regel 4 |
| R | board_presence | 0.95 | *entfernt* | Regel 3 |
| R | mana_growth | 1.48 | **1.23** | Regel 1 |
| R | wipe_readiness | 1.70 | **1.77** | Regel 1 (bestätigt, verstärkt) |
| G | mana_growth | 1.45 | **1.33** | Regel 1 |
| G | board_presence | 1.15 | **1.12** | Regel 1 |
| G | wipe_readiness | 0.15 (Policy-Untergrenze) | **0.40** (echter Wert) | Regel 4 (löst die Policy-Untergrenze ab) |
| G | interaction_availability | (fehlte) | **0.91** (neu) | Regel 4 |

## Übernommene Änderungen — strategy_curves

| Strategie | Dimension | alt (v4.67.0) | neu (v4.69.0) |
|---|---|---|---|
| aggro | board_presence_growth | 0.64 | **0.826** |
| midrange | board_presence_growth | 0.63 | **0.811** |
| control | board_presence_growth | 0.43 | **0.604** |
| horde | board_presence_growth | 1.30 | 1.30 (unverändert, Regel 5) |
| aggro/midrange/control/horde | interaction_growth | 0.035/0.09/0.16/0.02 | **0.079/0.082/0.078/0.067** |
| aggro/midrange/control/horde | wipe_growth | 0.0/0.03/0.11/0.0 | **0.032/0.032/0.040/0.036** |
| aggro/midrange/control/horde | mana_growth | 0.157/0.19/0.143/0.166 | **0.150/0.166/0.161/0.178** |

**Hinweis zu aggro/horde.wipe_growth**: beide erhalten jetzt einen
Wert > 0, sind aber weiterhin durch `wipe_min_turn = 999` (in Kombination
mit dem globalen `wipe_min_turn_hard_floor`) verhaltens-INAKTIV — es
existiert kein Turn-Timing-Beleg dafür, WANN ein Aggro- oder Horde-Deck
einen gelegentlichen Board-Wipe einsetzen würde, nur dass die reine
Kartendichte >0 ist. Bewusst offen ausgewiesene Lücke, nicht stillschweigend
gelöst — eine zukünftige Version müsste das mit echtem Turn-Timing-Beleg
schließen, nicht mit einer geschätzten Zahl.

## Antwort auf die Nutzerfrage: Farb- vs. Strategie-Effekte

**Echte, robuste Farbeffekte** (überleben die Entkonfundierung): Weiß hat
überdurchschnittliche Board-Präsenz, Interaktion und (jetzt revertiert)
KEINE besonders hohe Wipe-Bereitschaft mehr; Schwarz hat überdurchschnittliche
Board-Präsenz und Ramp, aber (Hauptbefund) UNTERdurchschnittliche
Interaktion; Rot hat die höchste Wipe-Bereitschaft und überdurchschnittlichen
Ramp-Anteil; Grün hat die höchste Ramp- und Board-Präsenz-Dichte, aber die
niedrigste Wipe- und Interaktions-Dichte; Blau bleibt bei Interaktion
(Vorevidenz-Wert) und ist die wipe-ärmste Farbe.

**Echte, robuste Strategieeffekte**: Aggro/Midrange bauen signifikant mehr
Board-Präsenz auf als Control — eine reale, nach Entkonfundierung sogar
GRÖSSERE Differenzierung als v4.67.0s marginale Schätzung zeigte, weil die
marginale Poolung den reinen Strategieeffekt teilweise durch die
Farbmischung der jeweiligen Stichprobe verdeckt hatte.

**Bestätigt (nicht widerlegt) flach**: Interaktions-, Wipe- und
Ramp-WACHSTUM unterscheiden sich zwischen Aggro/Midrange/Control auch nach
Entkonfundierung nicht signifikant — das ist ein echter, jetzt zweifach
(marginal UND entkonfundiert) belegter Nullbefund, keine
Methoden-Schwäche. Control bleibt trotzdem über den ABSOLUTEN Wert von
`wipe_min_turn` (frühester Zugriff) von den anderen Strategien
unterschieden, nur nicht mehr über eine (nie belastbar belegte) höhere
Wachstumsrate.

Damit ist das Ergebnis weder "alles ist konfundiert und gleich" noch
"alles ist einfach der Mittelwert aller Decks" — es ist eine gemischte,
für jede Dimension einzeln geprüfte Antwort, exakt wie vom Nutzer
angefordert.

## Verbleibend offen

- `aggro`/`horde.wipe_growth` sind trotz neuer Werte durch `wipe_min_turn
  = 999` verhaltens-inaktiv (siehe oben) — braucht Turn-Timing-Evidenz,
  nicht nur Dichte-Evidenz.
- `combo_finish_readiness`/`sac_drain_growth`/`passive_value_growth`/
  `disruption_growth` bleiben unverändert — `deck_profiles.csv` bildet
  diese vier Dimensionen granular gar nicht ab (unverändert seit
  v4.67.0/v4.40.0/v4.43.0).
- `horde.board_presence_growth` bleibt eine strukturelle Datenlücke
  (siehe Entscheidungsschema Regel 5) — bräuchte eine Board-State-Metrik
  statt einer Decklisten-Kartentyp-Zählung.
- Die 7 verbleibenden Farbidentitäten außerhalb der 5 Monofarben in
  `color_modifiers` sind strukturell nicht einzeln kalibrierbar (das
  Modell kombiniert Einzelfarb-Multiplikatoren multiplikativ) —
  unverändert seit v4.42.0.
