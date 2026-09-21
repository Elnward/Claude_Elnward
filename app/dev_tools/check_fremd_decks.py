#!/usr/bin/env python3
"""Prueft ALLE Fremd-Decks (Decks/Fremd/*.txt und Decks/Fremd/Precons/*.txt)
auf Ladefehler (Karten, die Scryfall nicht identifizieren kann), OHNE beim
ersten fehlerhaften Deck abzubrechen - jedes Deck wird einzeln versucht, und
am Ende steht eine vollstaendige Zusammenfassung ueber ALLE Decks.

WICHTIG: braucht echten Internetzugang zu Scryfall. Muss LOKAL ausgefuehrt
werden (nicht in der Cloud-Sandbox, von der aus Scryfall blockiert ist).

Seit v4.17.0 sammelt ein einzelner fehlgeschlagener Deck-Build ALLE nicht
identifizierbaren Karten auf einmal (ueber alle Scryfall-Batches hinweg,
nicht nur die erste), und versucht vorher automatisch einen Fuzzy-Fallback
ueber Scryfalls eigene /cards/named-Suche fuer jede Karte, die die exakte
Suche nicht gefunden hat. Ein Deck, das hier als Ladefehler auftaucht, hat
also ein Problem, das weder die exakte noch die Fuzzy-Suche loesen konnte -
typischerweise ein echter Tippfehler in der Datei oder eine brandneue Karte,
die in der lokal installierten/aufgerufenen Scryfall-Datenbank noch nicht
auftaucht.

Aufruf (aus dem Projekt-Root, mit normalem Internetzugang):
    python check_fremd_decks.py

Exit-Code 0 = alle Decks laden sauber, 1 = mindestens ein Deck hat einen
Ladefehler (Details stehen in der Zusammenfassung am Ende, inkl. der
konkreten Kartennamen).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402

print("Engine version:", engine.ENGINE_VERSION)

FREMD_ROOT = ROOT / "Decks" / "Fremd"
CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"

deck_files = sorted(FREMD_ROOT.glob("*.txt")) + sorted((FREMD_ROOT / "Precons").glob("*.txt"))

if not deck_files:
    print(f"Keine Deck-Dateien unter {FREMD_ROOT} gefunden.")
    sys.exit(1)

results = []  # (label, status, detail)

for path in deck_files:
    label = str(path.relative_to(FREMD_ROOT))
    print("=" * 80)
    print("Pruefe:", label)

    try:
        hints = engine.detect_commander_hints(path)
    except Exception as exc:
        print("  PARSER-FEHLER:", exc)
        results.append((label, "PARSER-FEHLER", str(exc)))
        continue

    try:
        deck = engine.build_deck_v4(
            input_path=path,
            commander_names=hints,
            cache_path=CACHE_PATH,
            offline=False,
            metadata_csv=None,
        )
    except Exception as exc:
        print("  LADEFEHLER:", exc)
        results.append((label, "LADEFEHLER", str(exc)))
        continue

    commander_found = sorted({c.name for c in deck if c.commander})
    detail = f"{len(deck)} Karten total, Commander erkannt: {commander_found or '(keiner - im GUI manuell waehlen)'}"
    print("  OK -", detail)
    results.append((label, "OK", detail))

print("=" * 80)
print("ZUSAMMENFASSUNG")
print("=" * 80)
ok = [r for r in results if r[1] == "OK"]
bad = [r for r in results if r[1] != "OK"]

for label, status, detail in results:
    marker = "OK  " if status == "OK" else "FEHLER"
    print(f"[{marker}] {label}: {detail}")

print()
print(f"{len(ok)}/{len(results)} Decks laden fehlerfrei.")
if bad:
    print(f"{len(bad)} Deck(s) mit Ladefehlern - Details oben. Bitte die genannten Kartennamen pruefen")
    print("(Tippfehler in der Deck-Datei, oder eine sehr neue Karte, die in dieser Scryfall-Datenbank noch fehlt).")
    sys.exit(1)

print("Alle Fremd-Decks laden fehlerfrei.")
sys.exit(0)
