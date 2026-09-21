# Win-Condition-Einfluss & situativer Kontext auf den Spielwert v1

**Status (v4.14.0): STRUKTUR IMPLEMENTIERT, Kalibrierung offen.**
`ValueModel.win_condition_preservation_multiplier` (Abschnitt 2) und
`ValueModel.hand_board_context_multiplier` (Abschnitt 3) existieren, sind
getestet (`tests/test_wincon_and_context_value.py`, 15 Tests) und setzen
die hier beschriebene STRUKTUR real um (inverse Skalierung nach
WC-Anzahl, Redundanz-Diskontierung, Kein-Hard-Lock-Floor, kontext-
abhängige Boosts). Was NICHT passiert ist, bewusst: die konkreten
Stärke-Konstanten (`wc_preservation_bias_strength`,
`context_empty_hand_draw_boost`, usw.) sind weiterhin ungeprüfte
Startschätzungen — Abschnitt 5 unten gilt inhaltlich unverändert, nur die
Reihenfolge hat sich verschoben: Route D ("Erlernte Value/Engine Value")
existiert jetzt (v4.13.0, `Docs/ENGINE_VALUE_v1.md`), aber der Store
(`Data/Learned/engine_value_store.json`) ist bei einem frischen Checkout
weiterhin leer — es liegen noch keine echten, über mehrere Läufe
akkumulierten Daten vor, gegen die sich diese Konstanten kalibrieren
ließen. Auch NICHT an `cast_score_v4`/die laufende Spielentscheidung
angebunden — dieselbe Reporting-first-Vorsicht wie bei Route D, hier sogar
noch strenger begründet (siehe Ehrlichkeits-Hinweis in den Docstrings
beider Methoden). Die Redundanz-Erkennung (Abschnitt 2.2) bleibt auf einen
groben Näherungswert beschränkt (Anzahl verschiedener Karten, die eine WC
insgesamt braucht) statt echter Austauschbarkeits-Erkennung, die eine
Requirements-Schema-Erweiterung bräuchte — bewusst zurückgestellt, um
nicht vor WP10s bevorstehender Arbeit am Scenario-System vorzugreifen. Die
offene Systemfrage aus Abschnitt 4 (Gegnerdruck als Kontext-Signal) bleibt
unbeantwortet, vorgesehen für die Diskussion nach dem geplanten
Gegner-Typ-Simulationsprojekt.

Ursprünglicher Status bei Erstellung dieses Dokuments (nur zur
Nachvollziehbarkeit, inzwischen durch das Obige ersetzt): "KONZEPT — nur
festgehalten und strukturiert, NICHT ausformuliert bis zur Formel-Ebene,
NICHT implementiert." Anders als die vorherigen Dokumente (Rot-Pilot,
Default-Tabelle, Ressourcen-Konversion) war das hier kein abschlussreifer
Vorschlag, sondern eine saubere Strukturierung der Idee plus der offenen
Fragen darin — bewusst, weil das Thema groß genug war, um es nicht in
einem Rutsch mit erfundenen Zahlen "fertig" zu machen.

## 0. Bezug zur bestehenden Architektur

`engine.py` hat bereits ein Scenario/Win-Condition-System (`kind: "Win Condition"`, `requirements` mit `card` + `zones` wie `battlefield`/`hand`/`graveyard`, `_focused_scenario`, `scenario_status`, sowie pro Turn getrackte `scenario_focus_feasibility`/`scenario_focus_strength`). Es gibt außerdem bereits `hold_reactive_count` — die Engine "hält" also schon heute reaktive Karten bewusst zurück, statt sie sofort auszuspielen. Das ist der richtige Anknüpfungspunkt: Deine Idee ist keine komplett neue Baustelle, sondern eine Erweiterung dieses bestehenden Zurückhalte-Mechanismus auf Win-Condition-Teile.

## 1. Die drei Blöcke (dein Modell)

Der tatsächliche Spielwert einer Karte auf der Hand ergibt sich aus drei Blöcken:

1. **Vordefinierter Value** — das, woran wir bisher gearbeitet haben (Rot-Pilot, Default-Tabelle, Color-Pie, Ressourcen-Konversion).
2. **Erlernte Value / "Engine Value"** — bereits in `DEFAULT_VALUES_AND_COLOR_PIE_v1.md` §5.2 als offener Punkt vorgemerkt (Blend aus vordefiniertem Wert und tatsächlich in Simulationen beobachtetem `net_value`-Beitrag). Wichtig: **Block 3 unten setzt logisch auf Block 2 auf** — bevor es einen echten "erlernten" Wert gibt, kann man Block 3 nur gegen den vordefinierten Wert rechnen.
3. **Win-Condition-Einfluss** (NEU, hier ausgearbeitet) — siehe Abschnitt 2.

## 2. Win-Condition-Einfluss — Struktur

### 2.1 Skalierung nach Anzahl aktiver Win-Conditions

Grundidee: das Zurückhalten einer WC-Teilkarte ist umso weniger kritisch, je mehr alternative Win-Conditions im Deck definiert sind. Bei 5 definierten WCs ist das Bewahren einer einzelnen WC deutlich unwichtiger als wenn nur 1 WC überhaupt existiert. Konzeptionell also ein Faktor, der **invers mit der Anzahl aktiver/erreichbarer WCs skaliert** (nicht zwingend simpel 1/n — z. B. könnte eine WC mit gerade hoher `scenario_focus_feasibility` stärker gewichtet werden als eine, die ohnehin unrealistisch ist — das bestehende Feasibility-Tracking liefert dafür schon die Rohdaten).

### 2.2 Redundanz vs. Schlüsselkarte

Zweite Achse: ist die Karte Teil eines Pakets mehrerer austauschbarer Karten, die dieselbe Rolle in der WC erfüllen können (Redundanz — z. B. mehrere gleichwertige Tutoren/Enabler), oder ist sie eine einzige, alternativlose Schlüsselkarte, ohne die die WC gar nicht funktioniert? Hohe Redundanz → niedrigere Preservation-Priorität pro Einzelkarte (jede einzelne ist verzichtbar). Keine Redundanz/Schlüsselkarte → hohe Priorität. Das erfordert, dass Requirements pro WC nicht nur "diese Karte" sondern auch "wie viele andere Karten könnten dieselbe Rolle übernehmen" kennen — das ist im bestehenden `requirements`-Schema (Stand jetzt: `card` + `zones`) vermutlich noch nicht abgebildet und wäre eine Schema-Erweiterung, keine reine Value-Model-Änderung.

### 2.3 Harte Nebenbedingung — kein Hard-Lock

Ausdrücklich von dir gefordert: **niemals** darf eine Karte durch diesen Mechanismus komplett unspielbar werden oder dazu führen, dass gute, an der WC nicht beteiligte Pläne blockiert werden, nur weil die Karte formal Teil einer WC ist. Der Win-Condition-Einfluss ist ein **weicher Gewichtungs-Bias auf die Wahrscheinlichkeit**, eine Karte jetzt zu spielen — kein Verbot. Praktisch heißt das: der WC-Einfluss darf den Value einer Karte absenken (weniger attraktiv machen, was JETZT gespielt wird), aber nie auf einen Wert setzen, der sie aus der Auswahl komplett ausschließt.

## 3. Situativer Kontext (Hand-/Board-Zustand) — vierte, überlagernde Schicht

Deine Beispiele zeigen, dass der reine Card-Value nicht ausreicht — derselbe Kartenwert soll je nach Spielzustand unterschiedlich stark ins Gewicht fallen:

- **Fast leere Hand** (z. B. nur Drawspell + Interactionspell übrig) → Drawspell-Priorität steigt (Ressourcenmangel-Situation).
- **Großes eigenes Board + passive Effekte/Artefakte/große Bodies/Token-Generatoren auf der Hand** → passive/board-skalierende Effekte werden relativ wirksamer, wenn das Board schon groß ist (Synergie mit vorhandener Breite/Präsenz).

Das ist konzeptionell KEIN vierter Block neben den drei oben, sondern eine **kontextabhängige Modulationsschicht**, die auf das Ergebnis der drei Blöcke wirkt — ähnlich wie das bestehende `multiplier(metric, tags)` in `ValueModel` schon archetyp-basierte Gewichtung anwendet, nur jetzt zusätzlich hand-/board-zustandsabhängig statt nur archetyp-abhängig.

## 4. Offene Systemfrage (bewusst nicht beantwortet)

Du hast selbst die richtige Frage gestellt: die Engine simuliert keine echten Gegnerdecks, sondern eine abstrahierte Funktion, die Angriffs-/Interaktionsverhalten der Gegner beschreibt. Sollte das Ergebnis dieser Funktion (der von ihr erzeugte Gegner-Board-Zustand) ebenfalls in diese kontextuelle Gewichtung einfließen — z. B. "Gegnerdruck ist hoch → Interaction wird relativ wichtiger, auch wenn die Hand nicht leer ist"? Das ist eine echte, offene Designfrage mit Architektur-Implikationen (die kontextuelle Gewichtungsschicht müsste dann nicht nur den eigenen State, sondern auch den Output der Gegner-Interaktions-Funktion lesen). Hier bewusst nicht vorschnell beantwortet — das sollte eine eigene Diskussion sein, sobald Abschnitt 2 und 3 grundsätzlich stehen.

## 5. Warum das hier nicht weiter ausformuliert wird

Anders als beim Rot-Piloten oder der Ressourcen-Konversion gibt es hier keine belastbare externe Referenz (kein EDHREC-Äquivalent, kein offizieller WotC-Kurs) — jede konkrete Formel wäre an dieser Stelle freihändig erfunden, was der bisherigen Faustregel dieses Projekts widerspricht (evidenzbasiert statt geraten). Sinnvoller Ablauf, zur Diskussion:

1. Zuerst Abschnitt "Erlernte Value / Engine Value" (bereits vorgemerkt) umsetzen — sie liefert die Datenbasis, gegen die sich WC-Einfluss und Kontext-Gewichtung später kalibrieren lassen (z. B. über echte `card_impact.csv`-Auswertungen: wie oft wurde eine WC-Schlüsselkarte tatsächlich zu früh weggespielt, und was hat das Spielergebnis gekostet?).
2. Erst danach WC-Einfluss (Abschnitt 2) und situativer Kontext (Abschnitt 3) konkret mit Zahlen hinterlegen — mit echten Testläufen statt geschätzten Startwerten.

Das ist als eigenständiges, späteres Vorhaben zu verstehen, nicht Teil der aktuell laufenden Rot-Pilot-/Default-Value-Arbeit.
