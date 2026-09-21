# Moxfield-Methodik & Orzhov-Runde 2 (v4.46.0)

## Auftrag

Fortsetzung von Punkt 2 (Gilden-Synergie-Luecke) nach dem Orzhov-Pilotversuch
(v4.45.0). Auftrag diesmal: Moxfield statt/zusaetzlich zu EDHREC als Quelle
fuer "beliebte/meistkommentierte" echte Spielerdecks nutzen, Stichprobe auf
10 Decks pro Sub-Strategie erhoehen, auf Bracket 2+3 beschraenken, danach
dieselbe Tiefe auf Gruul und Izzet uebertragen, die Gegnerfunktion mit den
Ergebnissen trainieren, und das Vorgehen so dokumentieren, dass es sich
selbststaendig auf weitere Gilden uebertragen laesst.

Diese Version deckt NUR Orzhov ab (Gruul/Izzet folgen in Folgeversionen -
Gruende siehe "Ehrliche Aufwands-/Ergebnisbilanz" unten). Das ist mit dem
Nutzer vorher abgestimmt: er hat auf explizite Nachfrage "woertlich 10 pro
Sub-Strategie" gewaehlt und dabei selbst bestaetigt, dass das nicht in
einem Durchgang abschliessbar ist.

## Teil 1: Die Moxfield-Zugriffsmethodik (das eigentlich Wiederverwendbare)

### 1.1 Warum ein einfacher Web-Fetch nicht funktioniert

`WebFetch` auf `https://moxfield.com/decks/public` und auf einzelne
`https://moxfield.com/decks/<id>`-Seiten liefert nur eine leere
JavaScript-Ladehuelle ("Loading Moxfield. This may take a minute...") -
Moxfield ist eine vollstaendig clientseitig gerenderte Single-Page-App,
ohne serverseitig vorgerendertes HTML fuer den Decklisten-Inhalt. Auch
Moxfields interne API (`api2.moxfield.com`) ist fuer automatisierte
Fetch-Tools per robots.txt gesperrt. **Ergebnis: Moxfield-Inhalte sind nur
ueber einen echten, JavaScript-ausfuehrenden Browser erreichbar**, nicht
ueber WebFetch/curl/requests.

### 1.2 Der funktionierende Weg: der eingebundene Browser

In dieser Sitzung stand ein echter Browser (im verbundenen Windows-Geraet
"zeus") zur Verfuegung. Vorgehen pro Deck:

1. `Claude_Browser__preview_start` bzw. `navigate` auf die Deck-URL.
2. **Cookie-Consent-Huerde (einmalig pro Browser-Profil):** Moxfield zeigt
   beim ersten Seitenaufruf aus einer EU-IP (das verbundene Geraet loest
   geografisch nach Deutschland auf) einen vollstaendigen IAB-TCF-Consent-
   Dialog ("Sie haben die Kontrolle ueber Ihren Datenschutz..."), der den
   eigentlichen Seiteninhalt vollstaendig verdeckt/blockiert. Datenschutz-
   freundlichste Wahl (siehe Systemregeln: nicht-essenzielle Cookies
   ablehnen): Klick auf "Erweiterte Einstellungen", danach "Alle
   ablehnen". Das Consent-Cookie gilt danach fuer die gesamte
   Browser-Profil-Sitzung (nicht nur den einen Tab) - der Dialog kam nach
   dem ersten erfolgreichen Ablehnen in keinem weiteren Tab dieser
   Sitzung mehr.
3. `get_page_text` auf `<main>` liefert Titel, Views/Likes/Comments,
   Selbst-Tags (Bracket/Archetyp, falls vom Ersteller gesetzt) UND die
   vollstaendige Decklist in einem Aufruf, SOBALD die Seite fertig
   geladen hat. Waehrend des Ladens liefert derselbe Aufruf nur "Loading
   Moxfield. This may take a minute..." - nicht unterscheidbar zwischen
   "laedt noch" und "haengt fest", ohne ein zusaetzliches `screenshot`.
4. Realistisches Timing: 3-10 Sekunden Wartezeit reichen bei einer
   funktionierenden Anfrage üblicherweise aus. Nach ca. 15-20 Sekunden
   ohne Fortschritt lohnt sich kein weiteres Warten mehr (siehe 1.3).

### 1.3 Kritischer Befund: Moxfield throttelt/haengt nach ca. 15-20 Anfragen pro Sitzung

Nach ca. 15 erfolgreichen bzw. versuchten Seitenaufrufen innerhalb weniger
Minuten begannen praktisch ALLE weiteren Anfragen dauerhaft zu haengen
("Loading Moxfield...", auch nach 20+ Sekunden Wartezeit, auch nach
Tab-Neustart, sogar fuer die reine Startseite `moxfield.com` selbst). Das
ist klar von einzelnen toten/privaten Decks zu unterscheiden (siehe 1.4):
Ein einzelner toter Link liefert entweder HTTP 404 ("Page Not Found",
sofort erkennbar) oder HTTP 200 mit dauerhaft leerer Datenlast fuer GENAU
diesen einen Link (mehrfach mit frischem Tab gegengeprueft). Die
Sitzungs-weite Blockade betraf dagegen JEDE URL gleichermassen, inklusive
der Startseite - ein serverseitiges Rate-Limit oder eine clientseitige
Ressourcenerschoepfung (die Netzwerk-Log zeigte massive Werbe-/Tracking-
Anfragen im Hintergrund, die den ohnehin schon schweren SPA-Ladevorgang
weiter belasten).

**Praktische Konsequenz fuer kuenftige Gilden-Runden:** in EINER
zusammenhaengenden Sitzung sind realistisch ca. 12-18 Moxfield-
Decklisten-Abrufe verlaesslich moeglich, nicht 60-150+. Fuer "10 Decks pro
Sub-Strategie" ueber mehrere Sub-Strategien braucht es entweder mehrere,
zeitlich klar getrennte Sitzungen (mit Pause dazwischen, um das Limit
zurueckzusetzen - in dieser Sitzung nicht getestet, ob eine Pause von
z. B. 10-20 Minuten reicht) ODER eine Mischstrategie: Moxfield gezielt fuer
die ersten ~10-15 Decks pro Runde (liefert echte Popularitaets-Metriken:
Views/Likes/Comments, die EDHREC nicht hat), danach Rueckgriff auf die
bereits etablierte, zuverlaessige EDHREC-"Average-Deck"-Methode (v4.39.0
ff., siehe Docs/opponent_model_calibration_v4_41_0.md) fuer den Rest der
Stichprobe.

### 1.4 Weitere reale Fehlerquellen (haeufig genug, um einzuplanen)

Von den in dieser Runde per WebSearch gefundenen Moxfield-URLs (aus
generischen Google-Suchtreffern, nicht aus Moxfields eigener
Sortierung/Filterung - siehe 1.6) liess sich ein erheblicher Anteil NICHT
verwenden:
  - **Tote/entfernte Decks:** liefern entweder sofort "Page Not Found"
    (klar erkennbar) oder haengen dauerhaft in der Lade-Ansicht selbst in
    einem frischen Tab (schwerer von 1.3 zu unterscheiden - Faustregel:
    wenn die UNMITTELBAR DAVOR erfolgreich geladene URL sofort danach
    ebenfalls haengt, ist es wahrscheinlich 1.3, nicht 1.4).
  - **Unvollstaendige Entwuerfe:** Titel ohne Commander-Angabe (z. B. nur
    "Good Orzhov - Commander" ohne Klammer-Commander) deuten auf
    unfertige/Scratch-Decks hin - vorab am Tab-Titel erkennbar, ohne die
    Seite selbst laden zu muessen.
  - **Zu hohe Bracket-Stufe:** ein ueberraschend grosser Anteil der ueber
    Suchtreffer gefundenen Decks (insbesondere solche mit hohem
    Engagement/vielen Likes - siehe 1.6) enthaelt 3+ echte Game-Changer
    und/oder ein Turn-1-Schnellmana-Paket und faellt damit unter Bracket
    2/3-Beschraenkungen aus der Zielstichprobe heraus.

### 1.5 Wiederverwendbarer Deck-Findungs-Workflow (fuer Gruul/Izzet/weitere Gilden)

1. Fuer die Ziel-Gilde die 1-2 beliebtesten Commander je erwarteter
   Sub-Strategie identifizieren (EDHREC "Top Commanders"-Liste je Gilde,
   z. B. `edhrec.com/commanders/<gilde>`, per WebFetch zuverlaessig
   erreichbar - liefert echte Deck-Zahlen als Popularitaets-Proxy).
2. Je Commander per `WebSearch` mit `moxfield <commander-name> <archetyp-
   stichwort> commander deck` einen Pool von 8-12 Kandidaten-URLs sammeln
   (liefert idR mehr Kandidaten als am Ende brauchbar sind - wichtig
   wegen der Ausfallrate aus 1.3/1.4).
3. Kandidaten der Reihe nach ueber den Browser abrufen (1.2), dabei:
   a. Tab-Titel VOR dem Warten pruefen (fehlende Commander-Angabe ->
      ueberspringen, siehe 1.4).
   b. Nach max. 2x Warten (insgesamt ca. 10-15s) ohne Fortschritt:
      ueberspringen und naechsten Kandidaten versuchen statt weiter zu
      warten (siehe 1.3 - ab einer bestimmten Sitzungslaenge lohnt sich
      KEIN weiteres Warten mehr, das Muster ist dann sitzungsweit, nicht
      pro Link).
   c. Jedes geladene Deck sofort nach Bracket vorfiltern (echte
      Game-Changers-Liste, siehe Data/Models/game_changer_archetypes.json
      + die etablierte Heuristik aus Docs/opponent_model_calibration_v4_
      41_0.md/v4_42_0.md) - NICHT dem Selbst-Tag des Erstellers blind
      vertrauen (der o.g. Kvad-Deck taggte sich selbst nicht als hohe
      Bracket, hatte aber 5 echte Game-Changer).
   d. Sobald ~12-15 Abrufe in der Sitzung erfolgt sind (egal ob
      erfolgreich oder nicht) UND die Erfolgsrate merklich einbricht: auf
      EDHREC-Average-Decks (zuverlaessig, kein bekanntes Rate-Limit)
      umsteigen, um die Ziel-Stichprobengroesse dennoch zu erreichen -
      klar kennzeichnen, welche Decks aus welcher Quelle stammen.
4. Jedes brauchbare Deck in eine Rohdaten-Tabelle eintragen (siehe
   Docs/scratch/moxfield_orzhov_raw.md dieser Runde als Vorlage): URL,
   Commander, Deckname, Views/Likes/Comments, Selbst-Tags, Bracket
   (selbst klassifiziert), Sub-Strategie, und die fuer die
   Cross-Dimension-Frage relevanten Karten mit Farbe+Mechanik.
5. Je Sub-Strategie: Farbe(n) der "Quelle" (was den Effekt/die Ressource
   erzeugt) gegen Farbe(n) des "Payoffs" (was die Ressource verwertet)
   vergleichen - siehe Teil 2 fuer das diesmal daraus abgeleitete,
   generische Erkennungsprinzip.

### 1.6 Nebenbefund: "beliebt"/"meistkommentiert" vs. "Bracket 2/3" ist ein echter Zielkonflikt

Moxfields Explore-Seite selbst liess sich technisch nur sehr
eingeschraenkt fuer Sortierung/Filterung nutzen (SPA-Klick-UI statt
URL-Parameter, siehe 1.1) - Popularitaet wurde daher indirekt ueber
WebSearch-Trefferrang + die auf der Decksseite selbst sichtbaren
Views/Likes/Comments ermittelt. Dabei zeigte sich: die tatsaechlich am
staerksten beachteten Decks der Stichprobe (z. B. "Teysa Aristocrats" von
Kvad, 3.861 Views/21 Likes/2 Kommentare - mit Abstand das hoechste
Engagement dieser Runde) hatten durchgaengig HOHE Bracket-Werte (5 echte
Game-Changer -> Bracket 4). Kommentare waren bei fast JEDEM untersuchten
Deck = 0 (nur 2 von 14 Kandidaten hatten ueberhaupt einen Kommentar) -
"meistkommentiert" ist auf Moxfield praktisch kein nutzbares
Auswahlkriterium, "meiste Views/Likes" schon, korreliert aber sichtbar mit
hoeherer Bracket-Stufe. Bracket-2/3-Beschraenkung und "die beliebtesten
Decks" sind auf Moxfield also teilweise gegenlaeufige Ziele - die
Bracket-Beschraenkung wurde in dieser Runde als das staerkere,
projekt-relevantere Kriterium behandelt (schliesst also einige der
"beliebtesten" Decks bewusst aus).

## Teil 2: Inhaltlicher Befund Orzhov-Runde 2

### 2.1 Aristokraten-Sub-Strategie: 5 unabhaengige echte Decks, durchgaengig BEIDSEITIG

| Quelle | Commander | Views/Likes/Comments | Bracket | Befund |
|---|---|---|---|---|
| Moxfield | Teysa Karlov ("Orzhov Sac") | 242/0/0 | ~2-3 | W liefert Token, B baut Opferausgaenge+Drain-Payoffs ueberwiegend selbst |
| Moxfield | Teysa Karlov ("Orzhov Aristocrats (Commander)") | 650/1/0 | 3 (Selbst-Tag) | W liefert Sister Hospitaller (Lifegain-Ausgleich fuer Junji-Combo) + Solitude; B stellt fast alle Drain-Payoffs |
| Moxfield | Teysa Karlov ("Teysa Karlov - Aristocrats") | 202/1/0 | ~2 | W: Token-Erzeuger UND reiner Token-Boost (Divine Visitation) ohne Drain-Bezug; B: fast komplett selbstgenuegsam |
| Moxfield | Teysa Karlov ("Prof's Teysa Karlov Aristocrats Deck") | 192/0/0 | 2 | Mainboard 0 Game-Changer; W: Afterlife-Token+Lifegain-Trigger; B: eigene Opferausgaenge+Drain komplett selbst |
| EDHREC (v4.45.0) | Teysa Karlov (Average Deck) | - | 3 | identisches Muster: B waere allein schon dicht |

**5 von 5 unabhaengigen, real ueberprueften Teysa-Karlov-Aristokraten-Decks
zeigen dasselbe Bild wie in v4.45.0 bereits an EINEM Deck vermutet:**
Schwarz ist in dieser Sub-Strategie durchgaengig selbstgenuegsam (eigene
Opferausgaenge UND eigene Drain-Payoffs), Weiss traegt zwar echte
Token-/Lifegain-Bausteine bei, aber es gibt KEINE unidirektionale
"Weiss-Quelle -> Schwarz-Payoff"-Abhaengigkeit, die ein Kreuz-Term sinnvoll
abbilden koennte. Diese Runde bestaetigt die v4.45.0-Vermutung mit 4
zusaetzlichen, unabhaengigen realen Belegen - **Schlussfolgerung: fuer die
Aristokraten-Sub-Strategie wird bewusst KEIN Kreuz-Term ergaenzt.**

### 2.2 Lebenspunkte-Drain-Sub-Strategie: 3 unabhaengige echte Commander, 2/3 mit echtem Kreuz-Muster

| Quelle | Commander | Befund |
|---|---|---|
| EDHREC (v4.45.0) | Karlov of the Ghost Council | W: 10+ reine Lifegain-Trigger ohne eigenen Drain; B: Sanguine Bond/Exquisite Blood/Vito/Sheoldred als Payoff. Echte Cross-Color-Abhaengigkeit. |
| EDHREC (v4.45.0) | Kambal, Consul of Allocation | identisches Muster |
| EDHREC (diese Runde) | Vito, Thorn of the Dusk Rose | Average Deck ist PRAKTISCH REIN SCHWARZ (kein einziges weisses Kartenbeispiel) - erreicht denselben Sanguine-Bond/Exquisite-Blood-Payoff ausschliesslich ueber schwarze Lifelink-Vampire (Gray Merchant of Asphodel, Whip of Erebos, Malakir Bloodwitch etc.) OHNE jede weisse Zufuhr. |

Moxfield-Abrufe fuer diese Sub-Strategie (Kambal/Karlov/Vito-Kandidaten aus
WebSearch) fielen fast vollstaendig der in 1.3 beschriebenen
Sitzungs-Blockade zum Opfer, bevor genug neue Daten gesammelt werden
konnten - siehe "Ehrliche Aufwands-/Ergebnisbilanz" unten. Vito wurde
stattdessen ueber die etablierte, zuverlaessige EDHREC-Average-Deck-Route
nachgezogen (Quelle klar gekennzeichnet).

**2 von 3 unabhaengigen Lebenspunkte-Drain-Commandern zeigen die echte
Cross-Color-Abhaengigkeit, der dritte (Vito) erreicht denselben Effekt
komplett selbstgenuegsam in einer einzigen Farbe.** Das bestaetigt: selbst
INNERHALB einer sauber abgegrenzten Sub-Strategie ist die
Cross-Color-Abhaengigkeit COMMANDER-/BUILD-ABHAENGIG, nicht einmal
sub-strategie-weit garantiert.

### 2.3 Schlussfolgerung: kein statischer Gewichtsterm, sondern eine Pro-Deck-Erkennung

Die urspruengliche v4.41.0-Idee (ein Gilden-weiter Kreuz-Multiplikator) war
bereits in v4.45.0 verworfen worden (zu grob). Diese Runde zeigt: selbst
eine SUB-STRATEGIE-weite Version davon waere noch zu grob (2.2 zeigt
2-von-3, nicht 3-von-3). Ein statischer Gewichtsterm auf JEDER
Aggregationsstufe wuerde immer einen relevanten Anteil echter Decks falsch
behandeln.

**Umgesetzte Konsequenz (siehe Docs/README.md v4.46.0 fuer die Code-Seite):**
statt eines weiteren Eintrags in `Data/Models/opponent_state_weights.json`
wurde ein neues, additives Diagnose-Modul (`App/synergy_profile/
classifier.py`) gebaut, das GENAU DAS pro getestetem Deck aus dessen
echten Kartendaten erkennt: hat dieses konkrete Deck einen "whenever you
gain life"-Payoff (Sanguine Bond, Vito, Cliffhaven Vampire, Bloodchief
Ascension - alle real per WebSearch/WebFetch verifiziert), und falls ja,
stammt die Lifegain-Quelle dafuer aus einer ANDEREN Farbe (echte
Cross-Color-Abhaengigkeit) oder ist das Deck selbstgenuegsam? Das Modul ist
additiv in `_opponent_model_cross_check` (v4.44.0) eingehaengt, aendert
also KEIN bestehendes Simulationsergebnis. Bekannte, offengelegte Luecke:
Lifelink (ein Schluesselwort, keine Fliesstext-Formulierung) wird NICHT als
Lifegain-Quelle erkannt - genau die Mechanik, mit der Vitos reales
Average-Deck seine Selbstgenuegsamkeit erreicht. Das ist bewusst als
Luecke ausgewiesen statt geraten (siehe Moduldoc).

## Ehrliche Aufwands-/Ergebnisbilanz dieser Runde

- **Erreicht:** vollstaendige Moxfield-Zugriffsmethodik inkl. des
  kritischen Rate-Limit-Befunds (Teil 1); 4 neue, unabhaengig prfbare
  Moxfield-Decks fuer Aristokraten (+1 EDHREC-Bestandsdeck aus v4.45.0 = 5
  gesamt); 1 neuer EDHREC-Beleg (Vito) fuer Lebenspunkte-Drain (+2
  EDHREC-Bestandsdecks aus v4.45.0 = 3 gesamt); ein neues, getestetes,
  additives Code-Modul (`App/synergy_profile`), das die gewonnene
  Erkenntnis (Pro-Deck- statt Pro-Gilde-Erkennung) direkt in die
  Engine "trainiert".
- **NICHT erreicht in dieser Runde:** die woertlichen "10 Decks pro
  Sub-Strategie" (erreicht: 4-5 pro Sub-Strategie, teils gemischter
  Herkunft); Gruul und Izzet (0 Decks - komplett auf spaetere Versionen
  verschoben); die weiteren, in v4.45.0 bereits identifizierten
  Orzhov-Sub-Strategien Reanimator/Board-Wipe-Control und
  "praktisch-mono-schwarz" wurden diese Runde nicht vertieft.
- **Grund:** die in Teil 1.3 dokumentierte Moxfield-Sitzungs-Blockade nach
  ca. 15-18 Abrufen - ein technischer Befund, der VOR dieser Runde nicht
  bekannt war und die realistische Reichweite einer einzelnen Sitzung
  stark einschraenkt.
- **Empfehlung fuer die Fortsetzung:** Gruul und Izzet in getrennten,
  neuen Sitzungen angehen (jeweils frisches Rate-Limit-Budget), dabei den
  in Teil 1.5 beschriebenen Workflow direkt anwenden (Moxfield fuer die
  ersten ~12-15 Decks, EDHREC-Average-Decks fuer den Rest der
  Ziel-Stichprobe) statt erneut bei Null zu recherchieren.
