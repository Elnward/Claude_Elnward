#!/usr/bin/env python3
"""
Commander Goldfish — root launcher.

Keeps __pycache__ out of the user's working directory (PYTHONDONTWRITEBYTECODE) and
starts the single-window GUI from App/gui.py.

Run:
    python commander_goldfish.py
or:
    Start_Goldfish_GUI.bat
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Keep bytecode caches out of the distribution folder in normal desktop use.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from App.gui import launch_gui
    launch_gui()


if __name__ == "__main__":
    main()
