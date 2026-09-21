#!/usr/bin/env python3
"""Urza's Spearfishing Guide -- Installer fuer fehlende Python-Pakete.

Wird automatisch von Start_Urzas_Spearfishing_Guide.py aufgerufen, sobald
beim Start ein benoetigtes Paket (flask, numpy, pandas, ...) fehlt. Kann
aber auch manuell gestartet werden:

    python install_dependencies.py

Installiert einfach `pip install -r requirements.txt` mit dem gerade
laufenden Python-Interpreter -- also genau der Python-Installation, mit
der das Programm ohnehin gestartet wurde, kein Raten ueber `python` vs.
`python3` vs. `py`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"


def main() -> int:
    print("=" * 60)
    print("Urza's Spearfishing Guide -- Installation der Abhaengigkeiten")
    print("=" * 60)

    if not REQUIREMENTS.exists():
        print(f"FEHLER: {REQUIREMENTS} wurde nicht gefunden.")
        return 1

    print(f"Verwende Python: {sys.executable}")
    print(f"Installiere Pakete aus: {REQUIREMENTS}")
    print()

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "-r", str(REQUIREMENTS)]
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print()
        print("Die Installation ist fehlgeschlagen (siehe Fehler oben).")
        print("Haeufigste Ursache: kein pip installiert, oder keine")
        print("Internetverbindung. Pruefe ggf. manuell mit:")
        print(f"    {sys.executable} -m pip install -r requirements.txt")
        return result.returncode

    print()
    print("Fertig. Alle Pakete sind installiert -- das Programm kann jetzt")
    print("ueber Start_Urzas_Spearfishing_Guide.py / .bat gestartet werden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
