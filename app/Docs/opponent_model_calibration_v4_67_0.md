# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.67.0

Begleitdokument zu `Docs/README.md` (v4.67.0-Eintrag),
`Data/Models/opponent_state_weights.json` (version "1.6") und
`App/opponent_model/state_equation.py`s Moduldoc-Abschnitt "v4.67.0"
("Kalibrierungs-Synthese Teil 2"). Anders als v4.66.0 (Flavor-Strategie-
Matrix, N=1-Decklist-Kandidaten, bewusst NICHT in die Default-Gewichte
übernommen) ändert diese Version tatsächlich die aktiven
`color_modifiers`/`strategy_curves`-Werte — weil erstmals die vom Nutzer
selbst seit v4.39.0 als offener Folgeschritt benannte "statistisch breite
Kalibrierung" zur Verfügung steht.

## Quelle

`App/archetype_profile/data/deck_profiles.csv` — 1.585 reale EDHREC
"Average Deck"-Profile (Kartenzahl je Rolle/Typ, keine Einzelkarten) über
alle 32 Farbidentitäten und 115 kanonische Strategie-Tags, gebaut aus der in
einem separaten Projektteil bereits abgeschlossenen Trainingsdaten-Pipeline
(`Training data/edhrec_bracket3_database.py` → `auswertung_v1` →
`App/archetype_profile`, siehe Projektnotiz `edhrec-bracket3-database.md`
und `App/archetype_profile/README.md`). Für die Farb-Achse wurden die 5
Monofarb-Identitäten verwendet (n=50 Decks je Farbe); für die
Strategie-Achse die EDHREC-Tags "Aggro" (n=104), "Midrange" (n=41),
"Control" (n=61) und — mangels eines eigenen EDHREC-"Horde"-Tags — "Tokens"
(n=131) als nächstliegender Proxy für das Engine-Konzept "Horde"/Go-Wide,
gepoolt über alle Farbidentitäten (die Strategie-Kurven sind bewusst
farbneutral, siehe Moduldoc).

## Methodik (identisch zu v4.39.0, nur mit 20-50x größerer Stichprobe)

Für jede Farbe/jeden Strategie-Tag wird je Deck das Dichteverhältnis
`Rollenkartenzahl / (deck_size − n_lands)` gebildet (Anteil an
Nicht-Land-Slots), davon der Median über alle Decks dieser Gruppe genommen.

- **color_modifiers**: `Multiplikator(Farbe, Dimension) = Median(Farbe,
  Dimension) / Mittelwert der 5 Farb-Mediane(Dimension)` — direkt
  interpretierbar (>1 = überdurchschnittlich, <1 = unterdurchschnittlich),
  ersetzt den alten Wert 1:1.
- **strategy_curves**: da diese Werte absolute Wachstumsraten pro Zug sind
  (keine reinen Multiplikatoren) und EDHREC-Decklisten keine
  Zug-für-Zug-Tempodaten liefern, sondern nur eine statische Zusammenstellung,
  wurde der ALTE Durchschnitt über die betroffenen Strategien als Anker
  beibehalten und nur die RELATIVE Verteilung zwischen den Strategien anhand
  der neuen Dichteverhältnisse neu skaliert: `neu(Strategie) = alter
  Durchschnitt × (neues Dichteverhältnis(Strategie) / Durchschnitt der neuen
  Dichteverhältnisse))`. Das verhindert einen unvalidierten Sprung der
  absoluten Spieltempo-Kalibrierung bei gleichzeitiger Nutzung der neuen,
  belastbareren RELATIVEN Evidenz.

Nur Felder mit direkter Entsprechung in `deck_profiles.csv`s Spalten wurden
angefasst: `board_presence` (`n_creatures`), `wipe_readiness`/`wipe_growth`
(`n_boardwipes`), `mana_growth` (`n_ramp`). `combo_finish_readiness`,
`sac_drain_growth`, `passive_value_growth`, `disruption_growth` bleiben
unverändert — `deck_profiles.csv` bildet diese vier Dimensionen granular gar
nicht ab (reine Rollen-/Typ-Zählwerte, keine Karten-Einzel-Tags); das wäre
ein separater, größerer Zusatzschritt über `deck_cards_slim.csv` +
`unique_cards_classified.csv`s Karten-Einzel-Tags, nicht in dieser Version.

## Rohdaten: Farb-Achse (Median-Dichteverhältnis, n=50 je Monofarbe)

| Farbe | board_presence | wipe_readiness | mana_growth |
|---|---|---|---|
| Weiß | 0.434 | 0.046 | 0.092 |
| Blau | 0.305 | 0.015 | 0.108 |
| Schwarz | 0.421 | 0.030 | 0.154 |
| Rot | 0.382 | 0.047 | 0.252 |
| Grün | 0.460 | **0.000** | 0.247 |
| *Fünf-Farben-Mittel* | *0.400* | *0.028* | *0.171* |

## Rohdaten: Strategie-Achse (Median-Dichteverhältnis, gepoolt über alle Farbidentitäten)

| Strategie (EDHREC-Tag, n) | board_presence | wipe_readiness | mana_growth |
|---|---|---|---|
| Aggro (n=104) | 0.492 | 0.031 | 0.233 |
| Midrange (n=41) | 0.485 | 0.016 | 0.281 |
| Control (n=61) | 0.328 | 0.031 | 0.212 |
| Tokens/"Horde" (n=131) | 0.450 | 0.031 | 0.246 |

## Übernommene Änderungen

**color_modifiers** (neue Werte, siehe `opponent_state_weights.json` für die
vollständige, pro-Feld begründete `_comment`-Dokumentation):

| Farbe | wipe_readiness | board_presence | mana_growth |
|---|---|---|---|
| W | 1.30 → **1.65** | 1.05 (unverändert, <10 % Abweichung) | (neu) → **0.54** |
| U | (neu) → **0.55** | (neu) → **0.76** | 0.95 → **0.63** |
| B | 1.10 → **1.10** (bestätigt) | unverändert | unverändert (<10 %) |
| R | (neu) → **1.70** | 1.15 → **0.95** (revidiert) | 1.10 → **1.48** |
| G | (neu) → **0.15** (Policy-Untergrenze, siehe unten) | 1.10 → **1.15** | 1.30 → **1.45** |

**strategy_curves** (`board_presence_growth`/`mana_growth`, aggro/
midrange/control per 3er- bzw. 4er-Anker neu skaliert):

| Strategie | board_presence_growth | mana_growth |
|---|---|---|
| aggro | 0.85 → **0.64** | 0.17 → **0.157** |
| midrange | 0.55 → **0.63** | 0.155 → **0.19** |
| control | 0.30 → **0.43** | 0.14 → **0.143** |
| horde | **1.30 unverändert** (siehe unten) | 0.19 → **0.166** |

## Grün-Wipe-Policy-Untergrenze

Der rohe Median über alle 50 Mono-Grün-Decks war exakt 0.0 (kein einziges
davon führte eine als `removal_board`/`removal_board_scalable`/
`bounce_board_overload` getaggte Karte). Ein roher 0.0-Multiplikator würde
im multiplikativen Farbmodell (`state_equation.py::_color_multiplier`)
JEDE grün-beteiligte Farbidentität hart auf `wipe_readiness = 0`
zwingen — auch ein Gruul- oder Naya-Deck, das durchaus vereinzelt einen
Wipe führen kann (Chain Reaction, Starnheim Unleashed-artige Effekte
o. Ä.). Das ist eine Modellierungsentscheidung, keine Datenbehauptung:
statt der rohen 0.0 wurde eine offen ausgewiesene Policy-Untergrenze von
0.15 gesetzt.

## Bewusst NICHT übernommener Befund: Interaction/Wipe-Wachstum je Strategie

Für `interaction_availability`/`interaction_growth` sowie
`strategy_curves.*.wipe_growth` zeigte die breite Stichprobe, dass sich
Aggro/Midrange/Control in ihrer reinen Karten-Dichte an
Entfernung/Gegenzaubern kaum unterscheiden:

| Strategie | Interaction-Dichte (grob, Rolle "Interaction") | Interaction-Dichte (verfeinert: nur Einzelziel-Entfernung + Protection, ohne Wipes) |
|---|---|---|
| Aggro | 0.262 | 0.221 |
| Midrange | 0.246 | 0.219 |
| Control | 0.250 | 0.222 |

Beide Varianten wurden geprüft — zuerst die grobe `primary_role ==
"Interaction"`-Zählung, danach ein verfeinertes Signal (nur
`n_interaction_single_target` + `n_protection`, Board-Wipes explizit
ausgeschlossen, um keine Überschneidung mit der eigenen `wipe_growth`-
Dimension zu erzeugen — passend zur dokumentierten Semantik von
`OpponentState.interaction_availability`: "chance of live
removal/counterspell/protection in hand"). Beide Varianten zeigen dieselbe
Einebnung; zusätzlich fiel Blaus rohe Dichte (0.206–0.212) durchgängig
UNTER Weiß (0.246–0.292) und Rot (0.203–0.258), was Blaus in v4.39.0 real
belegter Sonderrolle (17-25 % Interaktionsanteil in der echten
Lier-Stichprobe) widerspricht. Plausibelste Erklärung: Commanders
Mehrspieler-Realität verlangt von jedem Archetyp eine gewisse
Grundausstattung an Antworten, und Weiß' zahlreiche günstige
Einzelziel-Exil-Entfernung überwiegt in reiner Kartenzahl gegenüber Blaus
selteneren, aber wirkungsstärkeren Gegenzaubern — echte Daten, aber nicht
das, was diese Dimension abbilden soll.

**Entscheidung**: `interaction_availability`/`interaction_growth` und
`strategy_curves.*.wipe_growth` bleiben auf der bisherigen v4.39.0/
v4.43.0-Kalibrierung. Eine Übernahme der rohen Dichtewerte hätte die
bewusst gestaffelte Aggro<Midrange<Control-Differenzierung eingeebnet und
Blaus dokumentierte Sonderrolle umgekehrt — das wird hier als offen
ausgewiesene Lücke behandelt statt stillschweigend "verbessert". Eine
sauberere Lösung (Zug-für-Zug-Kartennutzung statt statischer
Decklisten-Zusammensetzung, oder eine gezieltere Kartenauswahl über
`deck_cards_slim.csv`s Einzelkarten-Tags) bleibt ein möglicher künftiger
Schritt.

## Bewusst NICHT übernommener Befund: Horde board_presence_growth

Die echten "Tokens"-getaggten Decks (n=131) zeigen KEINE erhöhte
Creature-TYP-Kartendichte (0.450, kaum über dem Vier-Strategien-Schnitt von
0.439) — naheliegend, weil eine Token-Strategie ihre tatsächliche
Brett-Präsenz überwiegend über NICHT-Kreatur-Karten aufbaut, die WÄHREND
DES SPIELS Kreatur-Token erzeugen (Anthems, Aristokraten-Enabler,
token-erzeugende Verzauberungen/Hexereien), nicht über Creature-Typ-Karten
im Deck selbst. Die reine Decklisten-Kartentyp-Zählung kann diese Dimension
für Horde strukturell nicht abbilden. `strategy_curves.horde.
board_presence_growth` bleibt daher beim alten, design-begründeten
Schätzwert (1.30) statt durch eine irreführend niedrige, aber
"evidenzbasiert" beschriftete Zahl ersetzt zu werden.
`strategy_curves.horde.mana_growth`/`wipe_growth` (Ramp-/Wipe-Kartenzahl,
beides real decklisten-basiert und nicht von diesem Verzerrungseffekt
betroffen) wurden dagegen normal aus der Tokens-Stichprobe übernommen.

## Verbleibend offen

- Interaction-/Wipe-Wachstum je Strategie (siehe oben) — braucht entweder
  Zug-für-Zug-Spieldaten oder eine gezieltere Kartenauswahl, nicht nur mehr
  Decks.
- `combo_finish_readiness`/`sac_drain_growth`/`passive_value_growth`/
  `disruption_growth` — `deck_profiles.csv` bildet diese vier Dimensionen
  nicht ab; bräuchte einen Zusatz-Pass über Karten-Einzel-Tags
  (`deck_cards_slim.csv` + `unique_cards_classified.csv`).
- Horde board_presence_growth (siehe oben) — bräuchte eine Board-State-
  Metrik statt einer Decklisten-Kartentyp-Zählung.
- Die 7 verbleibenden Farbidentitäten außerhalb der 5 Monofarben in
  `color_modifiers` sind strukturell nicht einzeln kalibrierbar (das Modell
  kombiniert Einzelfarb-Multiplikatoren multiplikativ) — unverändert seit
  v4.42.0.
