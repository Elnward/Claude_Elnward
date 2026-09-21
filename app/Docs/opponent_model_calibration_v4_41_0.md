# Gegner-Zustandsmodell — Kalibrierungs-Rechercheeintrag v4.41.0

Begleitdokument zu `Docs/README.md` (v4.41.0-Eintrag) und
`App/opponent_model/state_equation.py`. Zwei unabhängige Teile: (1) die
Recherche zur offiziellen LSV-Bewertungsskala und ihre Anwendbarkeit auf
dieses Projekt, (2) die erste Zweifarb-Erweiterung der Decklisten-Stichprobe.

## Teil 1: Die LSV-Skala — was sie ist, und was sie NICHT ist

**Frage des Nutzers:** ob die offizielle LSV-(Luis Scott-Vargas-)
Bewertungsskala genutzt werden kann, um daraus die Halbwertszeit von Karten
abzuleiten.

**Recherche (WebSearch/WebFetch, 06.09./13.09.2026):**

- Die LSV-Skala ist ein **Limited-Draft-Bewertungssystem**, das ChannelFireball
  (und andere Limited-Reviewer) für JEDES neue Set FRISCH vergeben - üblich
  ist eine Buchstaben- oder Zahlenskala (z. B. S/A/B/C+/C/D/F oder eine
  äquivalente 0-5-Bandbreite: "S: lächerliche Bombe, dominiert das Spiel
  sofort" bis "F: größtenteils bis vollständig unspielbar"). Quelle für die
  exakte Rubrik-Formulierung: [MTG Arena Zone Theros Beyond Death Limited Set
  Review](https://mtgazone.com/theros-beyond-death-limited-set-review-introduction-and-white/)
  - dort explizit: "This is primarily a Draft review and should be taken as
  such."
- Es gibt **keine einzige, universelle LSV-Bewertung für jede jemals gedruckte
  Karte**. Alte oder Reprint-Commander-Staples wie Mana Vault, Necropotence
  oder Rhystic Study waren nie selbst Gegenstand eines Limited-Set-Reviews
  (teils weil sie aus Sets vor der modernen Limited-Review-Ära stammen, teils
  weil sie in KEINEM aktuellen Draft-Format überhaupt limitiert spielbar
  sind) - eine Suche nach einer "LSV-Bewertung von Mana Vault" liefert
  lediglich Verkaufsangebote, keine Bewertung.
- **Konsequenz für dieses Projekt:** Eine "LSV-Zahl pro Karte" als zitierten
  Fakt zu verwenden, wäre eine Erfindung gewesen - das widerspricht der
  eigenen Projekt-Konvention "belegbasiert, nichts erfinden". Es wird daher
  an KEINER Stelle im Code eine Pro-Karte-LSV-Zahl verwendet.

**Was aus der Nutzer-eigenen Recherche trotzdem trägt:** unabhängig vom
LSV-Namen selbst beschreibt die vom Nutzer zitierte Gemini-Antwort ein reales,
in der Community bekanntes Prinzip - das "Threat Relevance"-/"Dies to
Removal"-Paradoxon: eine Karte mit hohem Spiel-Einfluss ("Bomben-Tier") wird
bevorzugt beantwortet und überlebt im Schnitt wenige Züge; eine unauffällige
Füllkarte wird ignoriert und bleibt oft viele Züge liegen, weil niemand
knappe Removal-Ressourcen dafür "verschwendet". Dieses Prinzip ist unabhängig
von einer konkreten Zahlenskala plausibel und mit dem bereits bestehenden
Befund aus `opponent_model_calibration_v4_39_0.md` konsistent ("eine solide
3.0-Utility-Karte im EDH kann problemlos 8 Züge liegen bleiben").

**Umsetzung:** Da dieses Projekt genau EIN echtes, regelverifiziertes
"Bomben-Tier"-Signal besitzt - die Mitgliedschaft in der offiziellen 53-Karten
-Game-Changers-Liste - und diese Dichte bereits nachweislich mit dem Bracket
korreliert (siehe v4.39.0 und Teil 2 unten), wird das Paradoxon auf
BRACKET-Ebene statt auf Einzelkarten-Ebene angewendet:
`bracket_scaling.<bracket>.impact_half_life_multiplier` verkürzt die
effektive Halbwertszeit beider v4.40.0-Bestände bei höherem Bracket (mehr
Bomben-Tier-Permanente im Schnitt -> schneller beantwortet). Werte:
Bracket 1-2 = 1.0 (kein Abschlag, praktisch keine Game Changer vorhanden),
Bracket 3 = 0.9, Bracket 4 = 0.75, Bracket 5 = 0.6. Diese Zahlen sind
**reasonierte Schätzwerte**, keine aus Decklisten gezählten Dichten (anders
als z. B. `opening_mana_boost`) - es existiert schlicht kein Zug-genau
geloggtes Spielmaterial, aus dem sich "wie viele Züge überlebt eine Bombe im
Schnitt" objektiv auszählen ließe. Das wird hier bewusst genauso offen gelegt
wie bereits die v4.40.0-Halbwertszeiten selbst.

## Teil 2: Zweifarb-Erweiterung (10 Gilden, je 1 echte Decklist)

**Auftrag:** "erweitere bitte dein Training auf alle Farbkombinationen und
trainiere dich bitte an 50 verschiedenen Decks pro Bracket, Farbidentität und
Strategie."

**Ehrliche Machbarkeits-Einschätzung (offengelegt statt stillschweigend
unterschritten):** Es gibt 32 Farbidentitäten (farblos, 5 monofarbig, 10
zweifarbig, 10 dreifarbig, 5 vierfarbig, 1 fünffarbig). "50 echte, verifizierte
Decks je Bracket × Farbidentität × Strategie" wäre - selbst bei nur 3-4
realistischen Strategien je Identität - eine Größenordnung von mehreren
Tausend einzeln zu beschaffenden und zu prüfenden Decklisten. Das ist in
einem einzelnen Durchgang nicht als echte, belegte Datenbasis leistbar, ohne
entweder Zahlen zu erfinden (widerspricht der Projekt-Konvention) oder einen
mehrsitzungsübergreifenden Rechercheaufwand zu betreiben. Diese Version macht
stattdessen den nächsten, in der Größenordnung zur v4.39.0-Monofarb-Runde
passenden Schritt: alle 10 Zweifarb-Gilden, je EINE echte EDHREC-Average-Deck
-Liste mit einem bekannten Commander und einer konventionellen Strategie.

### Quelle

Alle 10 Decklisten: EDHREC "Average Deck"-Aggregate
(`edhrec.com/average-decks/<commander-slug>`), abgerufen 13.09.2026.
Anders als beim Monofarb-Durchgang wurde hier NUR die Standard-Variante
abgerufen (kein Budget/Expensive-Paar je Gilde) - das ergibt zwar keine
Machtstufen-Progression INNERHALB einer Gilde, dafür aber automatisch eine
Bracket-Streuung ÜBER die 10 Gilden hinweg (siehe Tabelle).

### Die 10 Gilden-Decks

| Gilde | Commander | Strategie | Game Changers gefunden | Bracket |
|---|---|---|---|---|
| Azorius (WU) | Aminatou, the Fateshifter | Blink-Control | 5 (Cyclonic Rift, Demonic Tutor, Vampiric Tutor, Rhystic Study, Smothering Tithe) | 4 |
| Dimir (UB) | Yuriko, the Tiger's Shadow | Ninjutsu-Tempo | 6 (Fierce Guardianship, Vampiric Tutor, Mystical Tutor, Demonic Tutor, Imperial Seal, Rhystic Study) | 4 |
| Rakdos (BR) | Rakdos, Lord of Riots | Aggro/Big-Creatures | 1 (Demonic Tutor) | 3 |
| Gruul (RG) | Xenagos, God of Revels | Ramp-Stompy | 1 (Worldly Tutor) | 3 |
| Selesnya (GW) | Trostani, Selesnya's Voice | Tokens | 1 (Aura Shards) | 3 |
| Orzhov (WB) | Teysa Karlov | Aristokraten | 2 (Bolas's Citadel, Smothering Tithe) | 3 |
| Golgari (BG) | Meren of Clan Nel Toth | Aristokraten/Reanimator | 0 | 2 |
| Simic (GU) | Tatyova, Benthic Druid | Landfall-Value | 3 (Cyclonic Rift, Crop Rotation, Rhystic Study) | 3 |
| Izzet (UR) | Niv-Mizzet, Parun | Spellslinger | 6 (Cyclonic Rift, Fierce Guardianship, Mystical Tutor, Gamble, Rhystic Study, Narset Parter of Veils) | ~~4~~ **5 (siehe Korrektur v4.43.0 unten)** |
| Boros (RW) | Aurelia, the Warleader | Aggro/Voltron | 4 (Enlightened Tutor, Teferi's Protection, Farewell, Smothering Tithe) | 4 |

Bracket-Verteilung: 1×Bracket 2 (Golgari), 5×Bracket 3 (Rakdos, Gruul,
Selesnya, Orzhov, Simic), 4×Bracket 4 (Azorius, Dimir, Boros), 1×Bracket 5
(Izzet, korrigiert - siehe unten). Kein Deck erreichte 6+ Game Changer mit
zusätzlicher auffälliger Ritual-/Opferaltar-Häufung (das v4.39.0-Kriterium
für Bracket 5) - Dimir liegt mit 6 Game Changern zwar über dem in v4.39.0
für Bracket 5 verwendeten Schwellenwert (5 + Zusatzsignal), zeigt aber keine
vergleichbar auffällige Engine-/Ritual-Dichte wie das Endrek-Expensive-
Referenzdeck - daher weiterhin konservativ als Bracket 4 statt 5
eingeordnet. Das ist eine Ermessensentscheidung, kein vollständiger
2-Karten-Kombo-Audit (dieselbe offengelegte Einschränkung wie in v4.39.0).

> **Korrektur (v4.43.0, selbst gefunden im Rahmen des dort durchgeführten
> Kombo-Audits von Punkt 4):** Izzet/Niv-Mizzet, Parun wurde hier fälschlich
> als Bracket 4 eingeordnet. Die reale EDHREC-Decklist enthält NEBEN
> Niv-Mizzet, Parun selbst auch **Curiosity** - zusammen ein bei
> commanderspellbook.com verifizierter, ECHTER 2-Karten-Infinite-Combo
> (Niv-Mizzet, Parun + Curiosity, in 67.575 realen EDHREC-Decks genutzt).
> Nach dem offiziellen Bracket-Regelwerk macht bereits ein einziger
> 2-Karten-Combo ein Deck automatisch zu Bracket 5, unabhängig von der
> Game-Changer-Zahl - dieser Aspekt wurde bei der ursprünglichen v4.41.0-
> Einordnung schlicht übersehen (der damalige Fokus lag auf der
> Game-Changer-Zählung, ein 2-Karten-Combo-Audit war für diese Version
> explizit als offene Einschränkung benannt, siehe oben). Izzet ist damit
> korrekt Bracket 5, nicht Bracket 4. Da `state_equation.py`/
> `opponent_state_weights.json` diese Einzeldeck-Klassifikation nicht direkt
> als Zahl referenzieren (nur die Bracket-Verteilungs-AUSSAGEN im Fließtext
> oben und in Docs/README.md v4.41.0 beruhen darauf), hat dieser Fehler
> KEINEN rückwirkenden Effekt auf bestehende Gewichte - er wird hier rein
> zur Korrektheit der Dokumentation richtiggestellt. Siehe Docs/README.md
> v4.43.0 für den vollständigen Kombo-Audit-Befund (inkl. der ebenfalls
> geprüften, aber NICHT zu einer Korrektur führenden Fälle Yuriko/Dimir und
> Karador/Abzan).

### Befund 1: Die Bracket-Klassifikation über das Game-Changers-Regelwerk
generalisiert auf Zweifarb-Decks

Genau wie im Monofarb-Durchgang korreliert die Game-Changer-Zahl klar mit dem
Bracket (0 → Bracket 2, 1-3 → Bracket 3, 4-6 → Bracket 4) - keine Änderung an
der Klassifikationsmethode nötig.

### Befund 2: Das bestehende multiplikative Farbmodell hält im Kern

`color_modifiers` werden für Mehrfarb-Profile bereits multiplikativ
kombiniert (bestehende Architektur, siehe `ColorMultiplierTests`). Azorius
(WU, hohe `passive_value_growth` bei BEIDEN Farben: W=1.25, U=1.40) zeigte
tatsächlich die dichteste Passive-Value-Engine-Häufung der Stichprobe
(Mystic Remora, Rhystic Study, Smothering Tithe) - eine Bestätigung, keine
Widerlegung des bestehenden Modells.

### Befund 3: Eine echte, NEUE Lücke — Gilden-spezifische Cross-Dimension-Synergien

Zwei Decks zeigten eine Dichte, die das bestehende Modell (ein Multiplikator
pro Farbe UND Dimension) so nicht vorhersagen würde:

- **Orzhov (WB, Teysa Karlov):** die dichteste Opfer-/Aristokraten-Drain-
  Häufung der GESAMTEN bisherigen Stichprobe (Blood Artist, Cruel Celebrant,
  Zulaport Cutthroat, Elenda the Dusk Rose, Priest of Forgotten Gods,
  Pitiless Plunderer, Grave Pact, Dictate of Erebos, The Meathook Massacre,
  Ashnod's Altar, Phyrexian Altar, Warren Soultrader, Viscera Seer, Carrion
  Feeder) - dichter noch als das mono-schwarze Endrek-Expensive-Referenzdeck.
  Weiß selbst hat kein `sac_drain_growth`-Gewicht; das Modell würde
  `sac_drain_growth` für WB rein aus Schwarz ableiten (B=1.55 × W-Default
  1.0 = 1.55, identisch zu einem ungepaarten Schwarz-Deck). Real trägt Weiß
  hier aber sehr wohl bei - nicht durch einen eigenen Drain-Effekt, sondern
  durch TOKEN-ERZEUGUNG (Fallmaterial für die Opferschleifen), die eine
  andere Dimension in einer anderen Farbe füttert.
- **Izzet (UR, Niv-Mizzet, Parun):** ungewöhnlich dichte Passive-Value-/
  Card-Draw-Häufung (Rhystic Study, Mystic Remora, Curiosity, Ophidian Eye,
  Teferi's Ageless Insight) für eine Gilde, in der Rot selbst kein
  `passive_value_growth`-Gewicht beiträgt - wieder eine reale, aber
  cross-dimensionale Synergie (Spellslinger-Tempo befeuert Kartenvorteil),
  die das Modell nicht sieht.

**Diese Lücke wird in dieser Version bewusst NICHT geschlossen.** Ein
generisches "Gilden-Synergie-Bonus"-Feld aus je EINEM Beleg-Deck pro Gilde
abzuleiten, wäre keine verantwortbare Kalibrierung (zu dünne Stichprobe, zu
hohes Risiko einer erfundenen Zahl) - dafür bräuchte es mehrere Decks pro
Gilde, genau wie der Monofarb-Durchgang zwei statt eines Decks pro Farbe
nutzte. Kandidat für eine mögliche künftige Iteration ("Iteration 5").

### Grenzen dieser Version (offengelegt)

- Nur EIN Deck pro Gilde statt einer Budget/Expensive-Progression wie bei
  Monofarbe - keine Machtstufen-Bandbreite innerhalb einer Gilde beobachtbar.
- Nur die 10 Zweifarb-Gilden - drei-, vier- und fünffarbige sowie farblose
  Identitäten bleiben vollständig offen (auch das ein vom Nutzer selbst
  benanntes, größeres Ziel, das über mehrere weitere Versionen verteilt
  werden muss).
- Die Bracket-4-vs-5-Grenzentscheidung bei Dimir (6 Game Changer ohne
  zusätzliche Ritual-Dichte) ist eine Ermessensentscheidung, kein
  vollständiger Kombo-Audit. Izzet wurde ursprünglich ebenfalls hier
  eingeordnet, aber in v4.43.0 anhand eines echten, verifizierten
  2-Karten-Combos auf Bracket 5 korrigiert (siehe Korrekturhinweis oben) -
  ein Hinweis darauf, dass auch Dimir bei einem vollständigen Combo-Audit
  noch einmal geprüft werden sollte (nicht in v4.43.0 geschehen, siehe
  Docs/README.md v4.43.0).
- `impact_half_life_multiplier` bleibt ein reasonierter, nicht
  Decklisten-gezählter Schätzwert (siehe Teil 1).
