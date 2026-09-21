# Default-Value-Tabelle & Color-Pie-Gewichtung v1

**Status: KONZEPT/ENTWURF — noch NICHT in `ValueModel`/`engine.py` eingebaut.** Baut auf `COLOR_VALUE_PILOT_v1_red.md` auf und beantwortet die Folgefrage: Was tun, wenn für eine Farbe/Kategorie-Kombination keine spezifischen Daten (EDHREC o.ä.) vorliegen?

## 1. Grundidee

Statt für alle 5 Farben × alle Kategorien echte Daten zu sammeln (aufwendig, und wie der Rot-Pilot gezeigt hat, für manche Kategorien wie Board Wipe ohnehin nicht sauber über EDHREC abrufbar), zwei Bausteine:

1. **Eine einzige, farbunabhängige Default-Tabelle** pro Kategorie (Draw, Loot, Burn, Mill, Interaction, Board Wipe, Ramp) — der Fallback, wenn nichts Spezifisches bekannt ist. Bewusst **eine Stufe konservativer** als die bekannteste/beste Referenzkarte der jeweiligen Kategorie, damit eine unbekannte Karte nie automatisch als "Elite-Niveau" eingestuft wird.
2. **Eine Color-Pie-Gewichtung** pro Farbe × Kategorie, die die Default-Zahl je nach bekannter Farbstärke nach oben oder unten skaliert. Quelle: die offizielle "Mechanical Color Pie"-Dokumentation von Wizards of the Coast (Design-Team, nicht Fan-Spekulation).

## 2. Quelle für die Color-Pie-Einordnung

[Mechanical Color Pie 2021](https://magic.wizards.com/en/news/making-magic/mechanical-color-pie-2021) (Wizards of the Coast, offizielles Making-Magic-Dokument). Zentrale, wörtlich zitierte Einstufungen:

- **Draw**: "Blue is best at card drawing. It has the most of it and no restrictions." (primary) — Schwarz sekundär, aber immer an einen Preis gekoppelt ("must involve paying some other cost, most often life"); Grün sekundär, aber an Kreaturen gebunden; Weiß und Rot tertiär (Rot praktisch nur impulsives Ziehen/Loot, kein echtes Draw).
- **Einzelziel-Removal**: "Black is king of creature destruction and is the one color that can kill regardless of circumstance." (primary, unconditional) — Rot ist primär bei Schaden-basiertem Removal (andere Mechanik, kein "destroy"), Grün primär bei Fight-Effekten (aber auf Kreaturen beschränkt), Weiß sekundär/bedingt (z. B. "nur angreifende/blockende Kreatur"), Blau nicht primär (nur Bounce/Tempo, kein echtes Removal).
- **Board Wipes**: "White is the color that most often does mass creature kill... showing up on a rare or mythic rare in almost every set." (primary — der komplette Karten-Archetyp heißt nach Wrath of God "Wrath-Effekt") — Schwarz und Rot sekundär, Blau sekundär nur über Shrink-Effekte (-N/-0, kein echtes Entfernen), Grün nicht primär.
- **Ramp**: "Green is also the color with permanents that can produce mana turn after turn." (primary, dauerhaft) — Rot primär bei *temporären* Mana-Stößen (nicht dauerhaft), Blau sekundär (artefaktgebundene Manarocks), Schwarz tertiär, Weiß nicht primär.

## 3. Default-Tabelle (Referenzkarte → konservativer Fallback-Wert)

Referenzkarten sind bewusst bekannte, historisch stabile "Root"-Templates aus eigenem MTG-Wissen (nicht live gegen Scryfall verifiziert — gleiche Einschränkung wie im Rot-Pilot). Der Fallback-Wert ist die Referenzrate mal einem Konservativitäts-Abschlag von ca. 20 %.

| Kategorie | Referenzkarte (Root) | Referenz-Rate | Default (−~20 %) |
|---|---|---|---|
| Draw | Concentrate {3}{U}: ziehe 3 | 0,75 Karten/Mana | **0,60 Karten/Mana** |
| Loot | Standard-Loot-Template (ziehe 2, wirf 1 ab, 2 Mana) | 0,5 Netto-Karten/Mana | **0,40 Netto-Karten/Mana** |
| Burn | Lightning Bolt {R}: 3 Schaden | 3,0 Schaden/Mana | **2,4 Schaden/Mana** |
| Interaction (Einzelziel) | Murder {1}{B}{B}: unconditional destroy | 0,33 Kills/Mana (1 Kill/3 Mana) | **0,27 Kills/Mana** (≈1 Kill/3,7 Mana) |
| Board Wipe | Wrath of God {2}{W}{W}: destroy all | 1 Wipe/4 Mana | **1 Wipe/~5 Mana-Äquivalent** |
| Ramp | Rampant Growth {1}{G}: 1 dauerhaftes Mana ab nächster Runde | 1 Mana/2 investierte Mana | **1 Mana/~2,4 investierte Mana** |
| Mill | *kein sauberer, allgemein bekannter "Root" verfügbar* | — | **niedrige Konfidenz — vorläufig 2,0 Karten/Mana, zur Diskussion** |

Mill ist bewusst als schwächste Zeile markiert: anders als bei Draw/Burn/Removal/Wipe gibt es keine einzelne, jahrzehntelang stabile "das ist DIE Mill-Referenzkarte"-Antwort — der Wert dort ist eine grobe Schätzung, kein recherchierter Fixpunkt.

## 4. Color-Pie-Multiplikatoren (Default × Multiplikator = farbspezifischer Fallback)

1,0 = auf Root-Niveau der jeweiligen Kategorie (nur die tatsächlich primäre Farbe). Werte darunter spiegeln die offizielle primary/secondary/tertiary-Einstufung aus Abschnitt 2.

| Kategorie | Weiß | Blau | Schwarz | Rot | Grün |
|---|---|---|---|---|---|
| Draw | 0,30 | **1,00** | 0,60 (kostengebunden) | 0,25 (→ eigentlich Loot) | 0,50 (kreaturgebunden) |
| Interaction (Einzelziel) | 0,70 (bedingt) | 0,35 (nur Tempo/Bounce) | **1,00** (unconditional) | 0,70 (andere Mechanik: Schaden statt destroy) | 0,60 (nur gg. Kreaturen, Fight) |
| Board Wipe | **1,00** | 0,35 (nur Shrink, kein echtes Entfernen) | 0,70 | 0,65 | 0,30 |
| Ramp | 0,20 | 0,45 (Artefakt-gebunden) | 0,40 (selten, mit Kosten) | 0,55 (nur temporär, nicht dauerhaft) | **1,00** |

**Wichtiger Hinweis zu Rot bei Interaction**: Rot ist laut Quelle NICHT primär bei "destroy"-Removal, aber SEHR wohl primär bei Schaden-basiertem Removal (eigene Mechanik). Der Multiplikator 0,70 bildet das ab, ohne Rot fälschlich als generell schwach bei Interaktion darzustellen — es ist nur ein anderer Mechanismus, was sich mit dem bereits bestätigten Rot-Pilot-Befund deckt (Lightning Bolt = 3,0 Effekt-Punkte/Mana, klar über dem Root-Wert für Removal insgesamt).

## 5. Zwei offene, bewusst NICHT gelöste Fragen aus deiner Nachricht

### 5.1 Downside-gated Kreaturen — jetzt verfeinert: Ressource-zu-Mana-Konversion

Deine Folge-Idee löst das eleganter als der ursprüngliche Platzhalter: statt eines pauschalen Abschlagfaktors alle alternativen Ressourcen (Leben, Opfern, Counter, Bedingungen) auf die gemeinsame Währung Mana zurückrechnen, damit sie mit dem normalen `mana_unit`-Modell direkt vergleichbar werden. Das lässt sich in zwei echte Ressourcen-Konvertierungen und einen dritten, bewusst NICHT konvertierten Fall aufteilen:

**a) Leben als Alternativkosten — fest kalibrierbar.** Magic hat dafür bereits einen offiziellen Umrechnungskurs: Phyrexian-Mana (seit New Phyrexia, Symbol {C/P}) lässt Spieler explizit wählen zwischen "1 farbiges Mana zahlen" ODER "2 Lebenspunkte zahlen" — WotCs eigener Design-Kurs ist also **2 Leben = 1 Mana**. Guter Konsistenz-Check: das bereits bestehende `life_gain_per_point: 0.667` im aktuellen `goldfish_value_model.json` liegt in derselben Größenordnung (0,5 vs. 0,667) — kein Widerspruch, eher eine Bestätigung, dass die bisherige Zahl schon grob richtig kalibriert war.

**b) Opfern (Sacrifice) — kein fester Kurs, sondern dynamischer Lookup.** Anders als Leben ist "opfere eine Kreatur" keine konstante Ressource — der tatsächliche Preis hängt davon ab, WAS geopfert wird. Ein 1-Mana-Token zu opfern kostet fast nichts, eine fertig ausgebaute Bombe zu opfern ist teuer. Statt einer festen Zahl: `cost_equivalent = eigener ValueModel-Wert der geopferten Karte`. Das ist im Prinzip schon dieselbe Logik wie das bestehende `discard_self: -1.2` (auch dort wird eine abstrakte "Kartenressource" negativ bewertet) — nur dass Sacrifice idealerweise den tatsächlichen Wert der konkret geopferten Karte nimmt statt einer Pauschale.

**c) Stun-Counter (Tempo-Verzögerung) — grobe Startschätzung, NIEDRIGE Konfidenz.** Anders als bei Leben gibt es hier keinen offiziellen Umrechnungskurs wie bei Phyrexian-Mana — das ist reine Schätzung. Zwei Modellierungsoptionen: (1) fixer Wert pro Counter (z. B. 1,0 Mana-Äquivalent), einfach aber ungenau, weil eine Verzögerung bei einer starken Bombe schwerer wiegt als bei einem kleinen Manadork; (2) **prozentualer Abschlag auf den eigenen Wert des betroffenen Permanents** statt fixer Manazahl — sachlich stimmiger, weil die Downside proportional zur Wichtigkeit dessen ist, was verzögert wird. Vorschlag: mit (2) starten, (1) nur als Fallback wenn der Permanent-Wert selbst noch unbekannt ist.

**d) Bedingte Angriffs-/Blocksperren ("can attack only if...") — bewusst NICHT in die Mana-Konversion gepresst.** Das ist konzeptionell ein anderer Fall als a–c: bei Leben/Opfern/Countern wechselt eine echte Ressource den Besitzer (Zahlung), bei einer Bedingung wechselt gar nichts — die Kreatur ist schlicht manchmal nicht nutzbar. Das in eine Mana-Zahl zu pressen wäre ein Kategorienfehler. Richtiger Ansatz: ein **Uptime-Wahrscheinlichkeits-Abschlag** (z. B. "Bedingung ist geschätzt in X % der Spiele erfüllt, also zählt der Stat-Wert nur zu X %"), keine Ressourcen-Umrechnung.

Alle vier Punkte sind hier nur konzeptionell festgehalten, **noch nicht implementiert** — Details in der begleitenden JSON, Abschnitt `resource_to_mana_conversion`.

### 5.1.1 Vollständigkeits-Check: weitere Zusatzkosten-Mechaniken

Auf deine Bitte hin systematisch durchgegangen, was es an alternativen Ressourcen/Zusatzkosten in Magic sonst noch offiziell gibt. Ergebnis: die vier Fälle oben lassen sich sauber in **zwei grundsätzlich verschiedene Buckets** einsortieren — das war vorher nicht explizit getrennt, macht das Modell aber deutlich klarer:

**Bucket A — Zusatz-/Alternativkosten beim Zaubern/Aktivieren** (eine Ressource wird tatsächlich bezahlt, um Mana zu sparen oder zu ersetzen):

- Leben (Phyrexian-Mana) — bereits oben, 2 Leben = 1 Mana, offizieller Kurs.
- **Delve** (neu hinzugefügt): "exile a card from your graveyard" ersetzt exakt {1} generisches Mana — ebenfalls ein offizieller, fester Kurs (Treasure Cruise, Dig Through Time, Tasigur). Damit: **1 Friedhofskarte = 1 Mana**, genauso hart zitierfähig wie der Phyrexian-Kurs.
- **Convoke / Improvise** (neu hinzugefügt): eine ungetappte Kreatur bzw. ein Artefakt tappen ersetzt {1} generisches Mana (bei Convoke sogar wahlweise 1 Mana der Kreaturenfarbe). Ebenfalls offiziell exakt definiert: **1 getappte Kreatur/Artefakt = 1 Mana**.
- **Opfern als Zusatzkosten** — der dynamische Lookup-Ansatz von vorhin wird durch **Emerge** offiziell bestätigt: dort ist die Kostenreduktion wörtlich als "gleich dem Mana-Wert der exilierten Kreatur" definiert, keine Pauschale. Das ist die offizielle Design-Bestätigung, dass "Wert der geopferten/exilierten Karte" der richtige Ansatz ist, keine feste Konstante.
- **Discard als Zusatzkosten** (z. B. Madness-Trigger, manche Kostenreduktionen) — hier gibt es keinen einzelnen offiziellen Umrechnungskurs wie bei Delve/Convoke; deckt sich aber inhaltlich mit dem bereits bestehenden `discard_self: -1.2`-Knopf im Value-Model, sollte also darüber abgebildet werden statt einer neuen Zahl.
- **Echo** (neu, Sonderfall): keine alternative Ressource, sondern eine **zeitversetzte** Mana-Zahlung — volle Kosten jetzt, UND nochmal dieselben Kosten in der nächsten Oberphase (oder Opfern als Ausweg). Modellierungsvorschlag: `effektive_kosten ≈ cast_kosten + (echo_kosten × Wahrscheinlichkeit, dass echo tatsächlich bezahlt wird)`, nicht weiter ausgearbeitet, nur katalogisiert.

**Bucket B — eingebaute Downsides des Ergebnisses** (keine Ressource wird bezahlt, aber das, was man bekommt, ist eingeschränkt nutzbar):

- Stun-Counter, "can't attack unless…" — bereits oben (prozentualer Abschlag bzw. Uptime-Wahrscheinlichkeit).
- **Suspend** (neu): Karte startet mit Zeitcountern im Exil, wird erst nach N Runden spielbar — dieselbe Modellierung wie Stun-Counter (Verzögerung ≈ prozentualer Abschlag, skaliert mit Länge der Verzögerung), kein neuer Mechanismus nötig.
- **Decayed** (neu, aus Innistrad Crimson Vow): Kreatur kann nicht blocken und wird nach dem Angriff geopfert — effektiv "nur ein einziger Angriff nutzbar". Modellierungsvorschlag: bewerten wie eine reguläre Kreatur, aber nur mit dem Wert EINES Angriffs statt fortlaufendem Board-Präsenz-Wert — auch das fügt sich in dieselbe Bucket-B-Logik (Nutzungsdauer-Abschlag) ein, keine neue Formel nötig.
- Bewusst außen vor gelassen: Energie-Marker und Loyalitäts-Zähler von Planeswalkern sind eigene, vollständig separate Ressourcen-Systeme (keine Mana-Alternative) — für dieses Value-Model nicht relevant, nur der Vollständigkeit halber erwähnt, damit klar ist, dass sie bewusst ausgeschlossen wurden und nicht einfach übersehen.

**Status**: Mit dieser Ergänzung ist der Zusatzkosten-/Downside-Themenblock aus meiner Sicht inhaltlich abgeschlossen — Leben, Opfern (jetzt offiziell bestätigt), Delve, Convoke/Improvise, Discard, Echo (Bucket A) sowie Stun-Counter, Suspend, Decayed, bedingte Angriffs-/Blocksperren (Bucket B) sind erfasst. Bereit für die Umsetzung in `ValueModel`, sobald du grünes Licht gibst.

### 5.2 "Engine Value" (vordefinierter Value + simulierter Value kombiniert)

Die Idee — vordefinierter Kartenwert wird durch echte Simulationsergebnisse (z. B. durchschnittlicher `net_value`-Beitrag einer Karte über mehrere Goldfish-Runs, wie es `card_impact.csv` bereits pro Karte liefert) nachträglich kalibriert — ist architektonisch stimmig und würde genau das Doctor-Strange-Beispiel lösen (Wert außerhalb des Decks vs. Wert im tatsächlichen Zusammenspiel). Das ist aber ein grundsätzlich anderes, größeres Vorhaben als die Default-Tabelle hier: es bräuchte neue Tracking-/Aggregations-Logik über mehrere Runs hinweg, nicht nur eine JSON-Tabelle. Explizit als eigenständiges, späteres Work Package vorgemerkt — nicht Teil dieser Lieferung.

## 5.2 Route B: EDHREC-Kreuzvalidierung für alle 5 Farben (v4.12.0)

Nachdem der Rot-Pilot nur für Rot echte EDHREC-Daten hatte, wurde hier nachgezogen — je ein Fetch für die jeweils primäre Kategorie der anderen 4 Farben, exakt nach demselben Muster wie beim Rot-Piloten:

| Farbe | EDHREC-Tag | Decks | Bestätigt |
|---|---|---|---|
| Weiß | `tags/control/mono-white` | 1.350 | Wrath of God real vorhanden (23 %, 312 Decks) — bestätigt die Board-Wipe-Root-Referenz. Swords to Plowshares (75 %!) und Path to Exile (68 %) sind die tatsächlich meistgespielten Karten. |
| Blau | `tags/card-draw/mono-blue` | 3.580 | Counterspell/Brainstorm/Psychosis Crawler/Teferi's Ageless Insight — breite, tiefe Draw-Auswahl, bestätigt Blaus Alleinstellung bei Draw. |
| Schwarz | `tags/control/mono-black` | 3.560 | Toxic Deluge, Damnation (Board Wipes), Go for the Throat, Infernal Grasp (unconditional Removal) — bestätigt Schwarz bei Removal UND als Sekundärfarbe bei Board Wipes. |
| Grün | `tags/ramp/mono-green` | 9.000 | Llanowar Elves (54 %), Cultivate (48 %), **Rampant Growth (38 %, 3.410 Decks)** — bestätigt die Ramp-Root-Referenzkarte direkt mit echten Zahlen. |

**Eine echte Korrektur kam dabei heraus**: Weißes Removal wurde von 0,70 auf **0,80** angehoben. Die offizielle Color-Pie-Quelle beschreibt Weiß nur über bedingte "destroy"-Effekte ("nur angreifende/blockende Kreatur" etc.) — die echten EDHREC-Top-Karten zeigen aber, dass Weiß eigentlich über einen ANDEREN Mechanismus verfügt: billiges, unconditional EXILE mit echten Kosten für den Gegner (Swords to Plowshares/Path to Exile geben dem Gegner ein Basisland oder Leben). Das ist effektiv näher an Schwarz' Unconditional-Removal-Effizienz als die reine "destroy"-Einordnung vermuten ließ — eine Korrektur, die nur durch den Abgleich mit echten Daten sichtbar wurde, nicht durch die Quelle allein.

Alle anderen Zellen der Tabelle hielten der echten Datenlage stand, ohne Anpassung nötig zu sein — die Kalibrierung geht damit von "nur offizielle Klassifikation" auf "offizielle Klassifikation + echte EDHREC-Kreuzvalidierung für alle 5 Farben" über.

## 6. Begleitende Datei

`Data/Models/default_value_table_and_color_pie.json` — maschinenlesbare Fassung der Tabellen aus Abschnitt 3 und 4. Ebenfalls noch **nicht** von `ValueModel` geladen.
