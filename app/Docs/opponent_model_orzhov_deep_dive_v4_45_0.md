# Orzhov-Tiefenrecherche (v4.45.0) — Pilotversuch zu Punkt 2 (Gilden-Cross-Dimension-Synergie)

## Auftrag

Statt der bisherigen Methodik (1 Beleg-Deck pro Farbidentität, siehe
v4.41.0/v4.42.0) wurde für EINE Gilde exemplarisch das Gegenteil versucht:
so viel echte Information wie sinnvoll vertretbar zusammentragen, um zu
prüfen, (a) wie die Ergebnisqualität dabei ausfällt und (b) ob sich die in
v4.41.0 offengelegte, bewusst nicht geschlossene Cross-Dimension-Synergie-
Lücke damit tatsächlich bestimmen lässt. Gewählte Gilde: **Orzhov (WB)** -
diejenige der beiden in v4.41.0 gefundenen Lücken, für die bereits ein
konkreter Verdacht bestand ("Weiß füttert über Token-Erzeugung Schwarz'
Opferschleifen-Drain").

## Methodik

5 echte, bewusst UNTERSCHIEDLICHE Orzhov-Commander gewählt (nicht 5x
dieselbe Aristokraten-Strategie), je die reale EDHREC-"Average Deck"-
Aggregatliste vollständig abgerufen (13.09.2026), jede Karte gegen die
echte, zweifach verifizierte 53-Karten-Game-Changers-Liste geprüft und
Bracket zugeordnet, danach jede relevante Karte einzeln nach Farbe und
Mechanik (Token-Erzeugung / Opferausgang / Sterbe-Drain-Payoff /
Lebenspunkte-Trigger / Lebenspunkte-zu-Schaden-Konverter) klassifiziert.

## Die 5 Decks

| Commander | Sub-Strategie | Game Changers | Bracket |
|---|---|---|---|
| Teysa Karlov | Aristokraten (Tod-Trigger/Token/Opfer) | 2 (Bolas's Citadel, Smothering Tithe) | 3 |
| Karlov of the Ghost Council | Lebenspunkte-Voltron/Drain-Konversion | 3 (Bolas's Citadel, Demonic Tutor, Smothering Tithe) | 3 |
| Kambal, Consul of Allocation | Lebenspunkte-Tax-Control/Drain-Konversion | 3 (Bolas's Citadel, Demonic Tutor, Smothering Tithe) | 3 |
| Yahenni, Undying Partisan | Aristokraten/Edikt (real fast mono-schwarz) | 0 | 2 |
| Athreos, Shroud-Veiled | Reanimator/Board-Wipe-Control | 2 (Farewell, Smothering Tithe) | 3 |

Quelle je Deck: `edhrec.com/average-decks/<commander-slug>`.

## Befund 1: Die ursprüngliche v4.41.0-Hypothese ist zu grob — real gibt es MEHRERE, unterschiedliche Cross-Dimension-Muster

**Teysa Karlov** (das v4.41.0-Beleg-Deck) bestätigt bei genauerer Prüfung
NICHT sauber "Weiß erzeugt Token, Schwarz drained sie": Weiß liefert zwar 4
echte Token-Erzeuger (Doomed Traveler, Hunted Witness, Ministrant of
Obligation, Hallowed Spiritkeeper - alle über die "Afterlife"/Tod-Mechanik),
aber Schwarz erzeugt sich sein Fallmaterial in diesem Deck genauso selbst
(Bitterblossom, Ophiomancer, Sifter of Skulls - 3 Karten) UND stellt praktisch
alle Opferausgänge (Ashnod's Altar, Phyrexian Altar, Viscera Seer, Carrion
Feeder, Priest of Forgotten Gods, Village Rites) sowie fast alle Drain-
Payoffs (Blood Artist, Zulaport Cutthroat, Elenda the Dusk Rose, Pitiless
Plunderer, Grim Haruspex, Midnight Reaper, Syr Konrad the Grim, Warren
Soultrader, Grave Pact, Dictate of Erebos, The Meathook Massacre). Die
"Cross-Color-Synergie" ist hier eher eine BEIDSEITIGE Verstärkung
(Schwarz allein wäre schon dicht) als ein echtes unidirektionales
"Weiß→Schwarz"-Gefälle.

**Ein anderes, SAUBERERES Muster taucht in 2 der 5 Decks auf:** Karlov of
the Ghost Council und Kambal, Consul of Allocation zeigen ein deutlich
klareres "Farbe A erzeugt, Farbe B konvertiert"-Gefälle - aber bei
LEBENSPUNKTEN statt bei Token/Opfer: Weiß liefert eine dichte Häufung
reiner Lebenspunkte-Trigger ohne eigenen Drain-Effekt (Soul Warden, Soul's
Attendant, Guide of Souls, Daxos Blessed by the Sun, Suture Priest, Auriok
Champion, Lunarch Veteran, Starscape Cleric, Voice of the Blessed,
Spectrum Sentinel, Exemplar of Light, Serra Ascendant, Felidar Sovereign,
Cliffhaven Vampire - 10+ Karten je Deck), während Schwarz (oder WB-Gold)
diese Lebenspunkte-Ereignisse in echten Schaden/Kartenvorteil umwandelt
(Sanguine Bond, Exquisite Blood, Vito Thorn of the Dusk Rose, Sheoldred the
Apocalypse, Debt to the Deathless, Marauding Blight-Priest, Kambal selbst).
Dieses Muster ist SAUBERER unidirektional als das Token/Opfer-Muster bei
Teysa und taucht in 2 von 5 Decks in praktisch identischer Form auf -
deutlich stärker belegt als die ursprüngliche v4.41.0-Vermutung.

**Yahenni, Undying Partisan** ist im echten EDHREC-Average-Deck praktisch
MONO-SCHWARZ (28× Swamp, KEIN Plains in der Manabasis) - obwohl Yahenni
selbst WB-Farbidentität hat, enthält das reale Aggregat keine nennenswerte
weiße Beimischung. Hier gibt es schlicht KEINE Cross-Color-Synergie zu
belegen, weil die reale Kartenpopulation kaum die zweite Farbe nutzt - ein
wichtiger, eigenständiger Befund: nicht jeder nominell zweifarbige Commander
erzeugt real ein zweifarbiges Durchschnittsdeck.

**Athreos, Shroud-Veiled** ist ein Reanimator-/Board-Wipe-Control-Shell
(Karmic Guide, Sun Titan, Sepulchral Primordial, Priest of Fell Rites,
Farewell, Wrath of God, Kaya's Wrath, Austere Command) - eine völlig andere
Spielweise ohne nennenswerte Aristokraten- ODER Lebenspunkte-Drain-Dichte.
Auch hier: kein Cross-Dimension-Muster in nennenswerter Ausprägung.

## Befund 2: Bracket-Streuung sogar INNERHALB einer Gilde

4 von 5 Decks liegen bei Bracket 3, aber Yahenni bei Bracket 2 (0 Game
Changer) - ein Beleg dafür, dass ein einzelnes Beleg-Deck pro Gilde (wie in
v4.41.0 praktiziert) selbst innerhalb einer Farbidentität durch Zufall der
Commander-Wahl 1-2 Bracket-Stufen daneben liegen kann. Das bestätigt die in
v4.41.0/v4.42.0 bereits offengelegte Unsicherheit der Ein-Deck-Stichprobe,
diesmal konkret quantifiziert statt nur vermutet.

## Antwort auf die eigentliche Frage: ist das Problem so bestimmbar?

**Teilweise ja, teilweise nein:**

**Ja** — die 5-fache Tiefe hat tatsächlich ein PRÄZISERES, staerker
belegtes Cross-Dimension-Muster zutage gefördert als die ursprüngliche
1-Deck-Vermutung (Lebenspunkte-Trigger→Drain-Konversion statt
Token→Opfer-Drain), das in 2 von 5 unabhängigen echten Decks nahezu
identisch auftritt.

**Nein** — die Tiefe hat gleichzeitig gezeigt, dass es KEINE EINZELNE
"Orzhov-Synergie-Zahl" gibt, die die Gilde als Ganzes beschreiben würde.
Welches (wenn überhaupt ein) Cross-Dimension-Muster ein reales Orzhov-Deck
zeigt, hängt von der SUB-STRATEGIE ab (Aristokraten vs. Lebenspunkte-
Drain vs. Reanimator vs. real-mono-schwarz), nicht von der Farbidentität
allein. Ein einzelner, guild-weiter Multiplikator (wie ursprünglich in
v4.41.0 als möglicher Fix skizziert) wäre damit die FALSCHE Form der
Lösung - er würde 3 von 5 realen Decks (Yahenni, Athreos, und Teysa nur
teilweise) unpassend beeinflussen, um 2 von 5 Decks (Karlov Ghost Council,
Kambal) korrekt abzubilden.

## Aufwands-Beobachtung (wie vom Nutzer erbeten)

Diese Tiefe für EINE Gilde bedeutete: 5 vollständige reale Decklisten
abrufen, ca. 150 Einzelkarten gegen die Game-Changers-Liste UND nach
Farbe/Mechanik klassifizieren, plus eine Zusatzrecherche zur Klärung einer
einzelnen Kartenfarbe (Bastion of Remembrance, tatsächlich WB statt der
zunächst vermuteten reinen Weiß-Zuordnung). Das ist ungefähr das 5-fache
an Recherche-/Prüfaufwand gegenüber dem bisherigen 1-Deck-pro-Gilde-Tempo
(v4.41.0/v4.42.0) - für NUR eine von 10 Zweifarb-Gilden. Eine gleich tiefe
Prüfung aller 10 Gilden wäre entsprechend ein realistischer ~10-facher
Gesamtaufwand gegenüber der bisherigen Kalibrierungsrunde.

## Empfehlung (keine Umsetzung in dieser Version)

Es wurde bewusst KEINE Code-/Gewichtsänderung vorgenommen - das war laut
Auftrag zunächst ein reiner Bestimmbarkeits-Pilotversuch. Drei ehrliche
Optionen für das weitere Vorgehen:

1. **Nur das sauberste Teilmuster jetzt umsetzen:** einen neuen,
   ausdrücklich als "Lebenspunkte-Trigger→Drain-Konversion" (nicht
   "Orzhov-Synergie" allgemein) benannten Cross-Term ergänzen, belegt durch
   2 von 5 realen Decks - ein kleiner, konservativer, klar abgegrenzter
   Schritt statt eines Gilden-weiten Fixes.
2. **Noch 1-2 weitere Gilden auf derselben Tiefe prüfen**, um zu sehen, ob
   sich das "Erzeuger-Farbe → Konverter-Farbe"-Muster als generelles
   Modellierungsprinzip (nicht nur für Orzhov) bestätigt, bevor irgendeine
   Gewichtsänderung gemacht wird.
3. **Hier stehen bleiben** - der Befund selbst (die Lücke ist real, aber
   strategie- statt gildenabhängig) ist bereits ein Erkenntnisgewinn
   gegenüber v4.41.0's offener Vermutung, ohne dass daraus zwingend sofort
   Code folgen muss.
