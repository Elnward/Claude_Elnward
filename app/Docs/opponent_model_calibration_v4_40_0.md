# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.40.0

Begleitdokument zu `Docs/README.md` (v4.40.0-Eintrag),
`App/opponent_model/state_equation.py` und `Data/Models/game_changer_archetypes.json`.
Baut direkt auf `Docs/opponent_model_calibration_v4_39_0.md` auf (dort steht die
Herkunft der 10 Decklisten und das verifizierte 53-Karten-Game-Changers-Regelwerk;
das wird hier nicht wiederholt).

## Ausgangslage: die zwei in v4.39.0 offengelassenen Lücken

1. Passive Value-/Tax-Engines (z. B. Rhystic Study, Smothering Tithe, Necropotence,
   The One Ring) — stehen dauerhaft auf dem Feld und generieren kontinuierlich
   Karten-/Ressourcenvorteil, ohne dass eine einzelne "Zug X spielt Karte Y"-Aktion
   das abbildet.
2. Schwarze Opfer-/Aristokraten-Drain-Schleifen (z. B. Blood Artist-Effekte,
   Endrek-Sahr-artige Token-Opfer-Ketten) — erzeugen einen eigenen,
   nicht-Kampf-gebundenen Lebenspunkte-Druckvektor.

Nutzer-Vorschlag zur Lösung (siehe Zusammenfassung des Gesprächs): keine einzelne
Karte modellieren, sondern das WIRK-VERSTÄNDNIS auf generische, permanenttyp-gebundene
Effekt-"Bestände" (Stocks) übertragen, die pro Zug wachsen UND mit einer Halbwertszeit
zerfallen — als Ersatz dafür, dass das Modell keine Interaktion ZWISCHEN den simulierten
Gegnern selbst abbildet ("irgendein anderer Spieler am Tisch räumt das Permanent
irgendwann weg"). Die Permanenttyp-Bindung (Artefakt/Verzauberung/Kreatur) ist dabei
NICHT in erster Linie für diese Halbwertszeit-Begründung gedacht, sondern soll künftig
einen Abgleich ermöglichen: hat das GETESTETE Deck genug Interaktion/Entfernung für
genau den Permanenttyp, der beim simulierten Gegner Bestand hat? (Diese Abgleich-Logik
selbst ist NICHT Teil dieser Version — das Modul bleibt eigenständig/engine-agnostisch;
die Typ-Bindung ist die Vorbereitung dafür.)

## Umsetzung

- Zwei neue `OpponentState`-Felder: `passive_value_by_type` und `sac_drain_by_type`,
  je ein Dict über die drei Buckets `artifact`/`enchantment`/`creature`.
- Halbwertszeit-Zerfall PRO ZUG, bucket-spezifisch, aus
  `permanent_type_half_life_turns` (`creature: 4`, `artifact: 7`, `enchantment: 9`):
  kürzere Halbwertszeit für Kreaturen, weil Kreatur-Entfernung im Schnitt am
  häufigsten und billigsten im Format vorkommt (Sorge/Removal-Dichte), während
  gezielte Verzauberungs-Entfernung erfahrungsgemäß seltener im Maindeck steht als
  Kreatur- oder sogar Artefakt-Entfernung — eine fachliche Einschätzung, keine aus
  den 10 Decklisten gezählte Größe (explizit offengelegt, siehe unten "Grenzen").
- Wachstum landet nicht deterministisch in einem festen Bucket, sondern wird
  über `permanent_type_distribution` gewürfelt (`_pick_permanent_type`,
  kumulative Gewichtung): `passive_value` fällt überwiegend auf Verzauberungen
  (60 %, z. B. Rhystic Study/Smothering Tithe/Necropotence), dann Artefakte
  (30 %, z. B. The One Ring/Bolas's Citadel), selten Kreaturen (10 %, z. B.
  Consecrated Sphinx/Seedborn Muse). `sac_drain` fällt überwiegend auf Artefakte
  (45 %, Opferaltäre wie Ashnod's Altar/Phyrexian Altar) und Kreaturen (40 %,
  Blood Artist-artige Ausgangspunkte), selten Verzauberungen (15 %, z. B.
  Grave Pact). Diese Prozentwerte sind eine grobe, aus der Kartentyp-Verteilung
  bekannter Beispiele DIESER zwei Archetypen abgeleitete Schätzung, keine
  Auszählung eines vollständigen Kartenpools (siehe "Grenzen").
- Neuer Parameter `table_size` (Keyword-only, Default 4) an
  `advance_opponent_state()`: skaliert NUR das Wachstum von
  `passive_value_by_type`, nicht von `sac_drain_by_type`. Begründung: eine
  Rhystic-Study-artige Engine wird bei mehr Mitspielern wertvoller (mehr Spieler
  = mehr potenzielle Steuerzahler pro Zug), während ein Blood-Artist-artiger
  Drain-Effekt in der Praxis meist GEZIELT gegen einen einzelnen Spieler
  eingesetzt wird und nicht automatisch mit der Spielerzahl skaliert. Das ist
  eine bewusste, offengelegte Asymmetrie, kein Versehen — durch einen eigenen
  Test (`test_table_size_does_not_affect_sac_drain_growth`) abgesichert.
- Neue Query-Funktion `query_board_effects()` (analog zu den bestehenden
  Query-Funktionen: liest nur, mutiert nichts, gibt Kopien statt Referenzen
  zurück) für den lesenden Zugriff auf beide neuen Bestände.

## Farbe-/Strategie-Gewichte: Herleitung

Die neuen `passive_value_growth`/`sac_drain_growth`-Werte in
`strategy_curves` und `color_modifiers` sind NICHT aus einer neuen
Decklisten-Stichprobe gezählt (das wäre eine dritte, noch größere Recherche-
Iteration gewesen), sondern aus der bereits in v4.39.0 zusammengetragenen
10-Decks-Stichprobe (siehe `opponent_model_calibration_v4_39_0.md`) UND der
in dieser Version ohnehin durchgeführten Game-Changer-Archetyp-Klassifikation
abgeleitet:

- Aus den 53 klassifizierten Game Changers tragen 8 zu `passive_value_by_type`
  bei (Bolas's Citadel, Consecrated Sphinx, Necropotence, Panoptic Mirror,
  Rhystic Study, Seedborn Muse, Smothering Tithe, The One Ring) — nach Farbe:
  6 davon sind Blau oder Blau-beteiligt (Consecrated Sphinx, Panoptic Mirror,
  Rhystic Study, Seedborn Muse [beide Farbidentität grün-blau, hier vereinfachend
  als "hat blaue Komponente" gewertet für die Monofarb-Kalibrierung nur bei reinem
  Blau verwendet], The One Ring ist farblos/jede Farbe spielbar), 2 sind Schwarz
  (Bolas's Citadel, Necropotence) — das stützt den in v4.39.0 bereits qualitativ
  beobachteten Befund (Lier/Mono-U-Decks hatten mit Abstand die höchste
  "Hand-Quality/Value"-Dichte der Stichprobe, 23 % bzw. 12 % gegenüber 1,5-15 %
  bei den übrigen Farben) — daher erhält Blau den höchsten
  `passive_value_growth`-Multiplikator (1.40), gefolgt von Weiß (1.25, gestützt
  durch Smothering Tithe im echten Giada-Expensive-Deck) und Schwarz/Grün
  (je 1.15, gestützt durch Necropotence/Bolas's Citadel im echten
  Endrek-Expensive-Deck bzw. keine starke Evidenz bei Grün — hier bewusst
  konservativ auf den Baseline-Wert plus einen kleinen Aufschlag gesetzt,
  da die 10-Decks-Stichprobe keine grüne passive Value-Engine enthielt).
  Rot bleibt ohne eigenen Multiplikator (kein Game Changer dieser Kategorie ist
  rot, und keines der beiden Krenko-Decks enthielt eine solche Karte).
- `sac_drain_growth` ist in KEINEM der 53 Game Changers vertreten (die Liste
  enthält keine reinen Aristokraten-Karten) — die Gewichte dafür stammen daher
  ausschließlich aus der v4.39.0-Beobachtung "dichte Ritual-/Opferaltar-Häufung"
  im Endrek-Sahr-Expensive-Deck (Mono-B, per Game-Changer-Zahl bereits als
  Bracket 5 eingestuft). Schwarz erhält daher den höchsten
  `sac_drain_growth`-Multiplikator (1.55); alle anderen Farben bleiben auf dem
  konservativen Baseline-Wert, weil keine der übrigen 8 Decklisten eine
  erkennbare Opfer-/Drain-Schleife enthielt.
- Strategie-seitig (`strategy_curves`) folgt die Rangordnung
  midrange > control > aggro > horde ≈ 0 für BEIDE neuen Wachstumsraten
  derselben Logik wie die bestehenden Dimensionen: Midrange/Control-Decks bauen
  eher auf langfristigem Kartenvorteil bzw. Ressourcenkontrolle auf als
  Aggro/Horde-Decks, die auf schnelle Boardpräsenz statt auf ein Value-Engine-
  Spiel setzen. Der `horde`-Wert (`passive_value_growth: 0.01`,
  `sac_drain_growth: 0.02`) ist NICHT aus einer echten Horde-Decklisten
  gestützt — Horde tauchte in keiner der 10 gesammelten Listen auf — und ist
  hier, wie bereits bei den v4.38.0-Basiswerten, als plausibilitätsbasierte
  Erstschätzung offengelegt statt stillschweigend als "belegt" behandelt.

## Game-Changer-Archetyp-Tagging: Vorgehen und Befund

Alle 53 verifizierten Game Changers wurden in
`Data/Models/game_changer_archetypes.json` einem von 8 Wirk-Archetypen
(fast_mana, tutor_consistency, draw_engine, wipe, protection, combo_piece,
alt_win_condition, disruption) und genau EINER bestehenden bzw. neuen
Zustandsdimension zugeordnet, auf die die Karte "einzahlt" (`feeds`). Diese
Datei wird zur Laufzeit NICHT von `state_equation.py` gelesen — sie ist ein
reines Kalibrierungs-/Analyse-Hilfsmittel für künftige Decklisten-Audits
(z. B. "wie viele Fast-Mana-Game-Changer stehen in diesem Deck" statt nur der
rohen v4.39.0-Gesamtzahl).

Bei dieser Klassifikation fiel eine dritte, bisher nicht benannte Lücke auf:

**9 der 53 Game Changers sind stehende, STATISCHE Stax-/Hemm-Effekte, die
weder zu einer reaktiven "in der Hand verfügbaren" Interaktion noch zu einem
Draw-/Drain-Profil passen:** Braids Cabal Minion, Drannith Magistrate, Grand
Arbiter Augustin IV, Humility, Narset Parter of Veils, Notion Thief,
Opposition Agent, Tergrid God of Fright, The Tabernacle at Pendrell Vale.
Diese wurden explizit auf `feeds: "unmapped_persistent_disruption"` getaggt
statt sie schlecht passend in `interaction_availability` (das wäre falsch,
weil sie nicht reaktiv sind, sondern dauerhaft wirken) oder eine der neuen
Stocks zu zwingen (das wäre ebenfalls falsch, weil sie weder Kartenvorteil
noch Lebenspunkte-Drain erzeugen, sondern dem Gegner/Tisch etwas VERWEHREN).
Das ist eine echte, in dieser Version bewusst NICHT geschlossene Lücke — ein
Kandidat für eine mögliche künftige "Iteration 4" (eigene
"Restriktions-/Denial"-Dimension), aber nicht Teil von v4.40.0.

Zwei Klassifikations-Grenzfälle wurden im jeweiligen `note`-Feld der JSON-Datei
offengelegt statt stillschweigend entschieden:
- **Cyclonic Rift**: als `wipe` getaggt, obwohl es strenggenommen ein
  Bounce-Alle- statt Destroy-Alle-Effekt ist (dieselbe Nuance, die bereits im
  v4.39.0-Dokument für "Blau wipet praktisch nie via destroy all" beschrieben
  ist).
- **Aura Shards / Orcish Bowmasters**: als `interaction_availability`
  (reaktiv) statt `unmapped_persistent_disruption` eingeordnet, weil beide bei
  jedem Trigger EINZELN und WIEDERHOLBAR reagieren (nicht permanent Optionen
  verbieten wie z. B. Drannith Magistrate) — näher am Charakter bestehender
  reaktiver Interaktion als am neu gefundenen Stax-Cluster.

## Grenzen dieser Version (offengelegt statt verschwiegen)

- Die Prozentwerte in `permanent_type_distribution` und die
  Halbwertszeit-Werte in `permanent_type_half_life_turns` sind fachliche
  Schätzungen aus der Kenntnis bekannter Kartenbeispiele, KEINE Auszählung
  eines vollständigen, repräsentativen Kartenpools — anders als die
  `color_modifiers`-Anpassungen für die bereits in v4.39.0 bestehenden
  Dimensionen, die auf realen Deck-Dichten beruhen.
- Die neu gefundene `unmapped_persistent_disruption`-Lücke (9 Karten) ist
  offen und nicht Teil dieser Version.
- Die grüne `passive_value_growth`- und die horde-Werte für beide neuen
  Dimensionen sind nicht durch eine reale Decklisten mit dieser Eigenschaft
  gestützt (siehe oben).
- Nach wie vor unverändert aus v4.39.0 gültig: nur Monofarbe untersucht, kein
  vollständiger 2-Karten-Kombo-Audit, 2 Decks pro Farbe statt einer breiten
  Bracket × Farbe × Strategie-Matrix.
