#!/usr/bin/env python3
"""Urza's Spearfishing Guide -- Haupt-Startpunkt.

Das ist die einzige Datei, die zum Starten des Programms aufgerufen werden
muss (per Doppelklick auf Start_Urzas_Spearfishing_Guide.bat unter Windows,
oder direkt mit `python Start_Urzas_Spearfishing_Guide.py`). Alle uebrigen
Ressourcen -- die Engine, die Web-Oberflaeche, Beispieldecks, Referenzdaten
-- liegen im Unterordner app/ und werden von hier aus gestartet.

Ablauf:
  1. Prueft, ob die benoetigten Python-Pakete (flask, numpy, pandas,
     pillow, requests) vorhanden sind.
  2. Fehlt eines davon, wird automatisch install_dependencies.py
     aufgerufen (das im Hintergrund `pip install -r requirements.txt`
     mit genau diesem Python-Interpreter ausfuehrt) und die Pruefung
     danach wiederholt.
  3. Startet app/web_server.py -- den echten Flask-Server, der die
     Simulation live gegen app/App/engine.py rechnet -- und oeffnet
     automatisch ein Browserfenster.

Zusaetzliche Kommandozeilen-Optionen (z.B. --port 9000 oder --no-browser)
werden unveraendert an app/web_server.py durchgereicht.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
WEB_SERVER = APP_DIR / "web_server.py"
INSTALLER = ROOT / "install_dependencies.py"
VENV_DIR = ROOT / ".venv"
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

# (Modulname-zu-Paketname, wo die beiden voneinander abweichen)
REQUIRED_MODULES = [
    ("flask", "flask"),
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("PIL", "pillow"),
    ("requests", "requests"),
]


def missing_packages() -> list[str]:
    missing = []
    for module_name, package_name in REQUIRED_MODULES:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
    return missing


def ensure_dependencies() -> bool:
    missing = missing_packages()
    if not missing:
        return True

    print(f"Fehlende Pakete erkannt: {', '.join(missing)}")
    print("Starte Installer (install_dependencies.py) ...")
    print()

    if not INSTALLER.exists():
        print(f"FEHLER: Installer nicht gefunden unter {INSTALLER}")
        return False

    result = subprocess.run([sys.executable, str(INSTALLER)])
    if result.returncode != 0:
        return False

    still_missing = missing_packages()
    if still_missing:
        print()
        print(f"Nach der Installation fehlen immer noch: {', '.join(still_missing)}")
        print("Bitte pruefen und ggf. manuell installieren:")
        print(f"    {sys.executable} -m pip install {' '.join(still_missing)}")
        return False

    print("Alle Abhaengigkeiten sind jetzt installiert.")
    print()
    return True


def reexec_into_venv_if_needed() -> int | None:
    """Falls unter .venv/ ein eigener Interpreter existiert und das Skript
    nicht schon darueber laeuft, sich selbst damit neu starten. So landen
    alle Startwege (bat, IDE, `python Start_...py`) automatisch in der
    projekteigenen, isolierten Umgebung statt im ggf. veralteten/geteilten
    System-Python."""
    if not VENV_PYTHON.exists():
        return None
    try:
        same_interpreter = Path(sys.executable).resolve() == VENV_PYTHON.resolve()
    except OSError:
        same_interpreter = False
    if same_interpreter:
        return None

    result = subprocess.run([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
    return result.returncode


def main() -> int:
    reexec_result = reexec_into_venv_if_needed()
    if reexec_result is not None:
        return reexec_result

    if not APP_DIR.exists() or not WEB_SERVER.exists():
        print(f"FEHLER: Der Ordner app/ mit web_server.py wurde nicht gefunden")
        print(f"(erwartet unter {WEB_SERVER}).")
        print("Bitte sicherstellen, dass Start_Urzas_Spearfishing_Guide.py auf")
        print("derselben Ebene liegt wie der app/-Ordner.")
        return 1

    if not ensure_dependencies():
        print()
        print("Start abgebrochen -- Abhaengigkeiten konnten nicht sichergestellt")
        print("werden (siehe Meldungen oben).")
        return 1

    print("Starte Urza's Spearfishing Guide ...")
    print()

    # web_server.py erwartet, als Skript in app/ ausgefuehrt zu werden (alle
    # relativen Pfade -- App/, Decks/, Goldfish_Results/, webui/ -- sind
    # relativ zu seinem eigenen Ordner). Darum als Subprozess mit cwd=app/
    # starten, statt es hier als Modul zu importieren.
    extra_args = sys.argv[1:]
    # v4.76.0: feste Hash-Saat. Ohne sie ordnet Python Mengen (set) in jedem
    # Prozess anders an; dieselbe Simulation mit demselben "Seed" lieferte
    # dadurch bei jedem Programmstart leicht andere Zahlen (gemessen: Bilbo V1,
    # 200 Spiele, 18.0 % vs. 15.0 % Niederlagen). Mit PYTHONHASHSEED=0 ist ein
    # Lauf bei gleichem Seed wieder exakt reproduzierbar.
    import os
    env = dict(os.environ, PYTHONHASHSEED="0")
    result = subprocess.run([sys.executable, str(WEB_SERVER), *extra_args], cwd=str(APP_DIR), env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
