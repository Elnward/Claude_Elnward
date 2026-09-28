#!/usr/bin/env python3
"""
Commander Goldfish v4.7.0 — single-window GUI.

Navigation is page-based inside ONE Tk root:
Home -> Main -> Win Conditions/Setups -> Back/Main/Home.

Metadata loading and simulation run in worker threads so the GUI remains responsive.
"""

from __future__ import annotations

import json
import base64
import queue
import threading
import urllib.parse
import urllib.request
import webbrowser
import sys
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk

try:
    # Normal case: gui.py lives in App/, engine.py sits right beside it as a package module.
    from App import engine
except ModuleNotFoundError:
    try:
        from . import engine  # gui.py imported as App.gui
    except ImportError as _engine_import_error:
        # Fallback for unusual layouts: locate engine.py beside this file directly.
        import importlib.util as _importlib_util
        import sys as _sys
        _here = Path(__file__).resolve().parent
        _candidates = [
            p for p in sorted(_here.glob("engine*.py"))
            if "gui" not in p.stem.lower()
        ]
        if not _candidates:
            raise _engine_import_error
        _spec = _importlib_util.spec_from_file_location("engine", _candidates[0])
        if _spec is None or _spec.loader is None:
            raise _engine_import_error
        engine = _importlib_util.module_from_spec(_spec)
        _sys.modules["engine"] = engine
        _spec.loader.exec_module(engine)

# ---------------------------------------------------------------------------
# v4.8 project layout
#
#   Commander_Goldfish/
#     commander_goldfish.py   <- launcher
#     App/gui.py               <- this file
#     App/engine.py
#     Decks/                   <- (legacy alias: "Deks/") auto-scanned deck lists
#     Goldfish_Results/<Deck>/<Run>
#     Data/Scenarios | Strategies | Models | Cache
#     Docs/
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECKS_DIRNAMES = ("Decks", "Deks")  # "Deks" recognized for backward compatibility only
DECK_SUFFIXES = (".txt", ".csv")
RESULTS_DIRNAME = "Goldfish_Results"
DATA_SCENARIOS_DIR = PROJECT_ROOT / "Data" / "Scenarios"
DATA_STRATEGIES_DIR = PROJECT_ROOT / "Data" / "Strategies"
DATA_MODELS_DIR = PROJECT_ROOT / "Data" / "Models"
DATA_CACHE_DIR = PROJECT_ROOT / "Data" / "Cache"


def decks_directory() -> Path | None:
    """Return the first existing canonical/legacy Decks folder under the project root, if any."""
    for name in DECKS_DIRNAMES:
        candidate = PROJECT_ROOT / name
        if candidate.is_dir():
            return candidate
    return None


def scan_decks() -> list[Path]:
    """List .txt/.csv deck files directly inside Decks/ (or legacy Deks/), sorted by name."""
    folder = decks_directory()
    if not folder:
        return []
    found = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in DECK_SUFFIXES
    ]
    return sorted(found, key=lambda p: p.stem.lower())


def results_root_for_deck(deck_path: Path) -> Path:
    """Goldfish_Results/<Deckname>/ under the project root — never inside Decks/."""
    return PROJECT_ROOT / RESULTS_DIRNAME / deck_path.stem

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    from io import BytesIO
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


# Andrew Gioia "Mana" font.
# Official CSS PUA mapping:
# W=e600 U=e601 B=e602 R=e603 G=e604, numbers e605..., C=e904.
MANA_FONT_FAMILY = "Mana"

# Deliberately high-contrast UI palette. White mana is yellow/cream; black mana
# is a saturated dark gray; colorless is neutral gray.
MANA_BG = {
    "W": "#eadf91",
    "U": "#9fc7e7",
    "B": "#575255",
    "R": "#dc8060",
    "G": "#86ad7b",
    "C": "#a9a9a9",
    "S": "#d8e1e6",
}
MANA_FG = {
    "W": "#151515",
    "U": "#10202d",
    "B": "#f6f6f6",
    "R": "#24120d",
    "G": "#102315",
    "C": "#171717",
    "S": "#202020",
}

MANA_GLYPHS = {
    "W": 0xE600,
    "U": 0xE601,
    "B": 0xE602,
    "R": 0xE603,
    "G": 0xE604,
    "0": 0xE605,
    "1": 0xE606,
    "2": 0xE607,
    "3": 0xE608,
    "4": 0xE609,
    "5": 0xE60A,
    "6": 0xE60B,
    "7": 0xE60C,
    "8": 0xE60D,
    "9": 0xE60E,
    "10": 0xE60F,
    "11": 0xE610,
    "12": 0xE611,
    "13": 0xE612,
    "14": 0xE613,
    "15": 0xE614,
    "X": 0xE615,
    "Y": 0xE616,
    "Z": 0xE617,
    "H": 0xE618,   # Phyrexian in current Mana releases
    "P": 0xE618,   # compatibility alias
    "S": 0xE619,
    "T": 0xE61A,   # tap
    "Q": 0xE61B,   # untap
    "16": 0xE62A,
    "17": 0xE62B,
    "18": 0xE62C,
    "19": 0xE62D,
    "20": 0xE62E,
    "C": 0xE904,
}


def mana_tokens(cost: str):
    import re
    return re.findall(r"\{([^}]+)\}", cost or "")


def mana_plain(cost: str) -> str:
    toks = mana_tokens(cost)
    return " ".join(toks) if toks else (cost or "")


def mana_display_text(cost: str) -> str:
    toks = mana_tokens(cost)
    return " ".join(toks) if toks else (cost or "")


def _mana_font(app, size=15) -> tuple:
    return (MANA_FONT_FAMILY, size) if getattr(app, "mana_font_available", False) else ("Segoe UI", max(8, int(size * 0.6)), "bold")


def _mana_glyph(token: str) -> str:
    token = (token or "").strip().upper()
    cp = MANA_GLYPHS.get(token)
    return chr(cp) if cp else ""


def _token_color(token: str) -> str:
    token = (token or "").strip().upper()
    if token in MANA_BG:
        return token
    if token.isdigit() or token in {"X", "Y", "Z", "H", "P"}:
        return "C"
    if "/" in token:
        parts = token.split("/")
        for part in reversed(parts):
            if part in MANA_BG:
                return part
    return "C"


def _draw_single_mana(canvas, app, token: str, x: float, y: float, diameter: int):
    token = (token or "").strip().upper()
    parts = token.split("/") if "/" in token else [token]
    x2, y2 = x + diameter, y + diameter
    center_x = x + diameter / 2
    center_y = y + diameter / 2

    # Hybrid/split symbols: two-color pip and two smaller glyphs.
    if len(parts) == 2 and all(p in MANA_BG or p.isdigit() or p in {"C", "H", "P"} for p in parts):
        k1 = _token_color(parts[0])
        k2 = _token_color(parts[1])
        canvas.create_oval(x, y, x2, y2, fill=MANA_BG[k1], outline="#454545", width=1)
        canvas.create_arc(
            x, y, x2, y2, start=225, extent=180,
            style="pieslice", fill=MANA_BG[k2], outline=""
        )
        if getattr(app, "mana_font_available", False):
            g1 = _mana_glyph(parts[0])
            g2 = _mana_glyph(parts[1])
            fs = max(7, int(diameter * 0.33))
            if g1:
                canvas.create_text(
                    x + diameter * 0.35, y + diameter * 0.33,
                    text=g1, font=(MANA_FONT_FAMILY, fs),
                    fill=MANA_FG[k1], anchor="center"
                )
            if g2:
                canvas.create_text(
                    x + diameter * 0.66, y + diameter * 0.67,
                    text=g2, font=(MANA_FONT_FAMILY, fs),
                    fill=MANA_FG[k2], anchor="center"
                )
        else:
            canvas.create_text(
                center_x, center_y, text=token,
                font=("Segoe UI", max(6, int(diameter * 0.26)), "bold"),
                fill="#111", anchor="center"
            )
        return

    key = _token_color(token)
    canvas.create_oval(x, y, x2, y2, fill=MANA_BG[key], outline="#454545", width=1)
    glyph = _mana_glyph(token)
    if getattr(app, "mana_font_available", False) and glyph:
        # Mana-font glyphs sit slightly high in Tk; lower them a touch so they look centered.
        font_size = max(8, int(diameter * 0.58))
        vertical_nudge = max(0.6, diameter * 0.055)
        canvas.create_text(
            center_x, center_y + vertical_nudge,
            text=glyph,
            font=(MANA_FONT_FAMILY, font_size),
            fill=MANA_FG[key],
            anchor="center",
        )
    else:
        label = token if len(token) <= 3 else token[:3]
        canvas.create_text(
            center_x, center_y + 0.2,
            text=label,
            font=("Segoe UI", max(7, int(diameter * 0.32)), "bold"),
            fill=MANA_FG[key],
            anchor="center",
        )


def draw_mana_cost(canvas, app, cost: str, *, diameter=18, left=3, top=2, gap=2):
    toks = mana_tokens(cost)
    x = left
    for tok in toks:
        _draw_single_mana(canvas, app, tok, x, top, diameter)
        x += diameter + gap
    return x


TABLE_MANA_DIAMETER = 16
DETAIL_MANA_DIAMETER = 24
WINCON_MANA_DIAMETER = 24

class ManaCostCanvas(tk.Canvas):
    """Reusable colored mana-cost renderer for tables/details."""
    def __init__(self, parent, app, cost="", height=24, compact=True, **kwargs):
        bg = kwargs.pop("bg", None) or _safe_widget_background(parent)
        super().__init__(
            parent, height=height, highlightthickness=0, bd=0,
            bg=bg, **kwargs
        )
        self.app = app
        self.cost = cost or ""
        self.compact = compact
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_cost(self, cost: str):
        self.cost = cost or ""
        self.redraw()

    def redraw(self):
        self.delete("all")
        d = TABLE_MANA_DIAMETER if self.compact else DETAIL_MANA_DIAMETER
        top = max(1, (int(self.cget("height")) - d) // 2)
        draw_mana_cost(self, self.app, self.cost, diameter=d, left=3, top=top, gap=3)


class ManaPip(tk.Canvas):
    """Single Mana-font pip used in the Win Condition editor."""
    def __init__(self, parent, app, token: str, size=WINCON_MANA_DIAMETER):
        super().__init__(
            parent, width=size, height=size,
            highlightthickness=0, bd=0,
            bg=_safe_widget_background(parent)
        )
        self.app = app
        self.token = token
        self.size = size
        self.redraw()

    def redraw(self):
        self.delete("all")
        _draw_single_mana(self, self.app, self.token, 2, 2, self.size - 4)


ADVANCED_OPPONENT_COLOR_PIP_SIZE = 26


class ColorPickerRow(ttk.Frame):
    """v4.64.0 ('Gegnerprofil'-Dialog, siehe AdvancedOpponentDialog): fünf
    anklickbare WUBRG-Manasymbol-Pips (dieselbe Optik wie ManaPip/
    _draw_single_mana oben) plus ein sechstes '?'-Pip für "Farbe zufällig
    wählen" (siehe engine._resolve_advanced_opponent_seats_for_run - pro Run
    neu ausgewürfelt, nicht hier im Dialog fest entschieden). Anklicken einer
    Farbe togglet sie an/aus; höchstens zwei gleichzeitig aktiv (die älteste
    Auswahl weicht einer dritten) - deckt sich mit
    engine._validate_advanced_opponent_seats' Umfang für diese erste
    Integrationsstufe (1-2 Farben je Sitzplatz). '?' ist exklusiv zu jeder
    Farbauswahl - Anklicken von '?' löscht eine bestehende Farbauswahl und
    umgekehrt."""

    def __init__(self, parent, app, initial_colors=None):
        super().__init__(parent)
        self.app = app
        initial_colors = list(initial_colors or [])
        self.random_active = initial_colors == ["?"]
        self.colors: List[str] = [] if self.random_active else [c for c in initial_colors if c in "WUBRG"]

        self.pip_canvases = {}
        for letter in "WUBRG":
            canvas = tk.Canvas(
                self, width=ADVANCED_OPPONENT_COLOR_PIP_SIZE, height=ADVANCED_OPPONENT_COLOR_PIP_SIZE,
                highlightthickness=0, bd=0, bg=_safe_widget_background(parent),
            )
            canvas.bind("<Button-1>", lambda _e, l=letter: self._toggle_color(l))
            canvas.pack(side="left", padx=2)
            self.pip_canvases[letter] = canvas

        self.random_canvas = tk.Canvas(
            self, width=ADVANCED_OPPONENT_COLOR_PIP_SIZE, height=ADVANCED_OPPONENT_COLOR_PIP_SIZE,
            highlightthickness=0, bd=0, bg=_safe_widget_background(parent),
        )
        self.random_canvas.bind("<Button-1>", lambda _e: self._toggle_random())
        self.random_canvas.pack(side="left", padx=(8, 2))

        self._redraw()

    def _toggle_color(self, letter: str):
        self.random_active = False
        if letter in self.colors:
            self.colors.remove(letter)
        else:
            if len(self.colors) >= 2:
                self.colors.pop(0)  # drop the oldest selection to make room
            self.colors.append(letter)
        self._redraw()

    def _toggle_random(self):
        if self.random_active:
            self.random_active = False
        else:
            self.random_active = True
            self.colors = []
        self._redraw()

    def get_spec(self) -> List[str]:
        """['?'] for random, or the 1-2 selected WUBRG letters. An empty,
        non-random selection (user deselected everything) also falls back to
        random rather than producing an invalid empty-colors seat."""
        if self.random_active or not self.colors:
            return ["?"]
        return list(self.colors)

    def _redraw(self):
        d = ADVANCED_OPPONENT_COLOR_PIP_SIZE
        for letter, canvas in self.pip_canvases.items():
            canvas.delete("all")
            _draw_single_mana(canvas, self.app, letter, 1, 1, d - 2)
            if letter in self.colors and not self.random_active:
                canvas.create_oval(0, 0, d, d, outline="#1a6dd8", width=3)

        self.random_canvas.delete("all")
        active = self.random_active
        self.random_canvas.create_oval(
            1, 1, d - 1, d - 1,
            fill=("#f6c945" if active else "#c9c9c9"), outline="#454545", width=1,
        )
        self.random_canvas.create_text(
            d / 2, d / 2, text="?", font=("Segoe UI", int(d * 0.5), "bold"), fill="#151515",
        )
        if active:
            self.random_canvas.create_oval(0, 0, d, d, outline="#1a6dd8", width=3)


class AdvancedOpponentDialog(tk.Toplevel):
    """v4.64.0: die 'Gegnerprofil'-Bedienoberfläche für
    engine.Strategy.advanced_opponent_model/advanced_opponent_seats (siehe
    Docs/README.md v4.63.0/v4.64.0 für das zugrundeliegende Zustandsmodell).
    Bis zu vier Sitzplätze, je Farbe (1-2 WUBRG-Pips oder '?' für zufällig)
    und Strategie (aggro/midrange/control/horde oder '?' für zufällig,
    unabhängig von der Farbwahl). Änderungen wirken sich erst mit
    'Übernehmen' auf app.advanced_opponent_* aus - 'Abbrechen'/Schließen des
    Fensters verwirft sie."""

    STRATEGY_CHOICES = ("aggro", "midrange", "control", "horde", "?")
    MAX_SEATS = 4

    def __init__(self, app: "GoldfishApp"):
        super().__init__(app)
        self.app = app
        self.title("Gegnerprofil")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()

        self.local_enabled = tk.BooleanVar(value=app.advanced_opponent_enabled_var.get())
        self.local_count = tk.IntVar(value=app.advanced_opponent_seat_count_var.get())

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Checkbutton(
            top,
            text="Erweitertes Mehrgegner-Modell verwenden (überschreibt die einfache Opponent-Auswahl)",
            variable=self.local_enabled,
        ).pack(anchor="w")
        count_frame = ttk.Frame(top)
        count_frame.pack(anchor="w", pady=(6, 0))
        ttk.Label(count_frame, text="Anzahl Gegner:").pack(side="left")
        ttk.Spinbox(
            count_frame, from_=1, to=self.MAX_SEATS, width=4,
            textvariable=self.local_count, command=self._update_seat_visibility,
        ).pack(side="left", padx=(4, 0))
        # Spinbox "command" only fires on the up/down arrows, not on typed
        # entry - a trace on the variable itself also catches typing/tabbing.
        self.local_count.trace_add("write", lambda *_a: self._update_seat_visibility())

        seats_container = ttk.Frame(self, padding=(10, 4, 10, 4))
        seats_container.pack(fill="both", expand=True)

        self.seat_frames = []
        self.color_rows = []
        self.strategy_vars = []
        for i in range(self.MAX_SEATS):
            spec = app.advanced_opponent_seat_specs[i]
            frame = ttk.LabelFrame(seats_container, text=f"Gegner {i + 1}", padding=8)
            row = ColorPickerRow(frame, app, initial_colors=spec.get("colors"))
            row.pack(side="left")
            svar = tk.StringVar(value=spec.get("strategy", "midrange"))
            ttk.Combobox(
                frame, textvariable=svar, values=self.STRATEGY_CHOICES,
                state="readonly", width=10,
            ).pack(side="left", padx=(16, 0))
            self.seat_frames.append(frame)
            self.color_rows.append(row)
            self.strategy_vars.append(svar)

        ttk.Label(
            self,
            text=(
                "Farb-Symbole anklicken zum Auswählen (höchstens 2 je Gegner - "
                "nur ein- und zweifarbige Gegner werden in dieser Ausbaustufe "
                "unterstützt). '?' wählt Farbe bzw. Strategie zufällig, für "
                "jeden Gegner unabhängig und für jeden einzelnen Simulations-"
                "Run neu ausgewürfelt - keine feste Wahl, die für die ganze "
                "Serie gilt. Bracket ist in dieser Ausbaustufe fest auf 3 "
                "gesetzt."
            ),
            wraplength=560, justify="left", padding=(10, 0, 10, 6),
        ).pack(fill="x")

        buttons = ttk.Frame(self, padding=10)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Übernehmen", command=self._apply).pack(side="right")
        ttk.Button(buttons, text="Abbrechen", command=self.destroy).pack(side="right", padx=(0, 8))

        self._update_seat_visibility()

    def _update_seat_visibility(self):
        try:
            count = max(1, min(self.MAX_SEATS, int(self.local_count.get() or 1)))
        except (tk.TclError, ValueError):
            count = self.MAX_SEATS
        for i, frame in enumerate(self.seat_frames):
            if i < count:
                frame.pack(fill="x", pady=4)
            else:
                frame.pack_forget()

    def _apply(self):
        self.app.advanced_opponent_enabled_var.set(self.local_enabled.get())
        try:
            count = max(1, min(self.MAX_SEATS, int(self.local_count.get() or 1)))
        except (tk.TclError, ValueError):
            count = self.MAX_SEATS
        self.app.advanced_opponent_seat_count_var.set(count)
        for i in range(self.MAX_SEATS):
            self.app.advanced_opponent_seat_specs[i] = {
                "colors": self.color_rows[i].get_spec(),
                "strategy": self.strategy_vars[i].get(),
            }
        if hasattr(self.app, "main"):
            self.app.main.refresh_advanced_opponent_status()
        self.destroy()


def _commander_eligible(card) -> bool:
    low_type = (card.type_line or "").lower()
    low_text = (card.oracle_text or "").lower()
    return (
        ("legendary" in low_type and "creature" in low_type)
        or "can be your commander" in low_text
    )


def _partner_capable(card) -> bool:
    low = (card.oracle_text or "").lower()
    return (
        "partner" in low
        or "friends forever" in low
    )


def legal_commander_choices(deck):
    """
    Return [(display_text, frozenset(names)), ...].

    Single commanders must cover the deck's complete color identity.
    Partner/Friends Forever pairs may cover it jointly.
    """
    unique = {}
    for card in deck:
        unique.setdefault(card.name, card)

    deck_ci = set()
    for card in unique.values():
        deck_ci.update(card.color_identity or set())

    candidates = [c for c in unique.values() if _commander_eligible(c)]
    singles = [
        c for c in candidates
        if deck_ci <= set(c.color_identity or set())
    ]

    choices = [(c.name, frozenset([c.name])) for c in sorted(singles, key=lambda x: x.name)]

    partners = [c for c in candidates if _partner_capable(c)]
    for i, a in enumerate(partners):
        for b in partners[i+1:]:
            if deck_ci <= (set(a.color_identity or set()) | set(b.color_identity or set())):
                names = tuple(sorted((a.name, b.name)))
                choices.append((f"{names[0]} + {names[1]}", frozenset(names)))

    # Dedupe by commander set.
    seen = set()
    out = []
    for display, names in choices:
        if names not in seen:
            seen.add(names)
            out.append((display, names))
    return out


def normalize_commander_selection(deck, current_names):
    choices = legal_commander_choices(deck)
    current = frozenset(current_names or ())
    valid_sets = [names for _, names in choices]

    if current in valid_sets:
        return set(current)

    # Salvage a legal subset from old projects (e.g. Bilbo + accidental Command Tower).
    contained = [names for names in valid_sets if names and names <= current]
    if contained:
        contained.sort(key=lambda x: (-len(x), sorted(x)))
        return set(contained[0])

    if len(valid_sets) == 1:
        return set(valid_sets[0])

    return set()


def _safe_widget_background(widget) -> str:
    """
    Return a usable Canvas background for both classic Tk and ttk parents.

    ttk.Frame/ttk.LabelFrame do not support cget("background"), which caused
    v4.3.2 to crash when creating the round GO FISHING Canvas button.
    """
    try:
        bg = widget.cget("background")
        if bg:
            return bg
    except (tk.TclError, KeyError):
        pass

    try:
        style = ttk.Style(widget)
        style_name = ""
        try:
            style_name = widget.cget("style")
        except (tk.TclError, KeyError):
            pass
        if not style_name:
            style_name = widget.winfo_class()
        bg = style.lookup(style_name, "background")
        if bg:
            return bg
    except Exception:
        pass

    try:
        return widget.winfo_toplevel().cget("background")
    except Exception:
        return "#f0f0f0"


class RoundFishingButton(tk.Canvas):
    """A real circular red Canvas button; decorative background can be added later."""
    def __init__(self, parent, command, diameter=190):
        super().__init__(
            parent, width=diameter, height=diameter,
            highlightthickness=0, bd=0, bg=_safe_widget_background(parent),
            cursor="hand2",
        )
        self.command = command
        self.diameter = diameter
        self.enabled = True
        self.normal = "#c62828"
        self.hover = "#a71919"
        pad = 6
        self.oval = self.create_oval(
            pad, pad, diameter-pad, diameter-pad,
            fill=self.normal, outline="", tags=("button",)
        )
        self.emblem = self.create_text(
            diameter/2, diameter/2 - 4,
            text="M",
            fill="#e5b0b0", font=("Georgia", 96, "bold"),
            justify="center", tags=("button",)
        )
        self.text = self.create_text(
            diameter/2, diameter/2 + 2,
            text="GO\nFISHING",
            fill="white", font=("Segoe UI", 20, "bold"),
            justify="center", tags=("button",)
        )
        self.tag_bind("button", "<Button-1>", self._click)
        self.tag_bind("button", "<Enter>", self._enter)
        self.tag_bind("button", "<Leave>", self._leave)

    def _click(self, _event=None):
        if self.enabled and self.command:
            self.command()

    def _enter(self, _event=None):
        if self.enabled:
            self.itemconfigure(self.oval, fill=self.hover)

    def _leave(self, _event=None):
        self.itemconfigure(self.oval, fill=self.normal if self.enabled else "#8d8d8d")

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        self.configure(cursor="hand2" if self.enabled else "arrow")
        self.itemconfigure(self.oval, fill=self.normal if self.enabled else "#8d8d8d")


class ManaStrip(ManaCostCanvas):
    """Larger card-detail mana strip using the same Mana-font renderer."""
    def __init__(self, parent, app, height=38):
        super().__init__(parent, app, cost="", height=height, compact=False)


class GoldfishApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Commander Goldfish v4.87.0")
        self.geometry("1540x920")
        self.minsize(1200, 740)

        self.q = queue.Queue()
        self.deck_path: Path | None = None
        self.project_path: Path | None = None
        self.strategy_file: Path | None = None
        self.value_model_file: Path | None = None
        self.pending_scenario_file: Path | None = None

        self.deck = []
        self.cards = {}
        self.commanders = set()
        self.scenarios = []
        self.image_cache = {}
        self.current_photo = None
        self.tree_mana_images = {}
        self.mana_font_available = MANA_FONT_FAMILY in set(tkfont.families(self))
        self.metadata_ready = False
        self.running = False

        self.runs_var = tk.IntVar(value=5000)
        self.run_mode_var = tk.StringVar(value="Standard (5,000)")
        self.turns_var = tk.IntVar(value=20)  # v4.83.0/v4.84.0: am Vierertisch ist nach 10 Zuegen erst ~die Haelfte entschieden
        self.seed_var = tk.IntVar(value=1)
        self.opponent_var = tk.StringVar(value="goldfish")
        # v4.15.7 (task #18, "Voltron-GUI-Feld"): GUI exposure for the
        # pre-existing engine field Strategy.voltron_target_index (a fixed
        # opponent index for commander-damage/Voltron plans, e.g. Mabel,
        # Heir to Cragflame). "Aus" (off) means None - unchanged pre-v4.15.0
        # behavior (commander damage follows the highest-life heuristic like
        # any other damage). "Gegner 0/1/2" match the 3-opponent default pod.
        self.voltron_target_var = tk.StringVar(value="Aus")
        self.tag_vars = {tag: tk.BooleanVar(value=False) for tag in engine.STRATEGY_TAGS}

        # v4.64.0: "Gegnerprofil"-Dialog (siehe AdvancedOpponentDialog) für
        # engine.Strategy.advanced_opponent_model/advanced_opponent_seats.
        # Persistiert über mehrere Dialog-Öffnungen hinweg (nicht nur
        # während der Dialog offen ist) und über einen ganzen Simulationslauf
        # hinweg, aber NICHT im Projekt-JSON (save_project/load_project
        # kennen diese Felder bislang nicht - ein disclosed offener Punkt,
        # siehe Docs/README.md v4.64.0). "colors": ["?"] bzw.
        # "strategy": "?" markiert "zufällig" - aufgelöst pro Run in
        # engine._resolve_advanced_opponent_seats_for_run, nicht hier.
        # v4.77.0 WP-C: default True (same default flip as the web UI's
        # "Advanced opponent model" checkbox) -- see Docs/README.md v4.77.0.
        self.advanced_opponent_enabled_var = tk.BooleanVar(value=True)
        self.advanced_opponent_seat_count_var = tk.IntVar(value=3)
        self.advanced_opponent_seat_specs = [
            {"colors": ["R"], "strategy": "aggro"},
            {"colors": ["G"], "strategy": "midrange"},
            {"colors": ["U", "B"], "strategy": "control"},
            {"colors": ["?"], "strategy": "?"},
        ]

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.home = HomePage(self.container, self)
        self.main = MainPage(self.container, self)
        self.setup = ScenarioPage(self.container, self)
        self.analysis = AnalysisPage(self.container, self)

        for page in (self.home, self.main, self.setup, self.analysis):
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_home()
        self.after(100, self.poll_queue)

    def report_callback_exception(self, exc, val, tb):
        """Write Tk callback crashes to a local log so test-machine errors are easy to share."""
        import traceback
        stamp = __import__("datetime").datetime.now().isoformat(timespec="seconds")
        detail = "".join(traceback.format_exception(exc, val, tb))
        try:
            log_path = PROJECT_ROOT / "goldfish_crash.log"
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"\n[{stamp}]\n{detail}\n")
        except Exception:
            pass
        try:
            if hasattr(self, "main") and self.metadata_ready:
                self.main.set_status(
                    "GUI-Fehler. Details wurden in goldfish_crash.log gespeichert.",
                    error=True,
                )
            elif hasattr(self, "home"):
                self.home.set_status(
                    "GUI-Fehler. Details wurden in goldfish_crash.log gespeichert.",
                    error=True,
                )
        except Exception:
            pass
        print(detail, file=sys.stderr)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_page(self, page):
        page.tkraise()

    def show_home(self):
        self.home.refresh()
        self.show_page(self.home)

    def show_main(self):
        if not self.metadata_ready:
            self.home.set_status("Metadaten sind noch nicht vollständig geladen.")
            self.show_home()
            return
        self.main.refresh_all()
        self.show_page(self.main)

    def show_setup(self):
        if not self.metadata_ready:
            self.main.set_status("Win Conditions können erst nach vollständigem Metadaten-Setup geöffnet werden.")
            return
        self.setup.load_from_app()
        self.show_page(self.setup)

    def show_analysis(self, result_dir: Path):
        self.analysis.load(result_dir)
        self.show_page(self.analysis)

    # ------------------------------------------------------------------
    # Home load flow
    # ------------------------------------------------------------------

    def choose_deck(self):
        p = filedialog.askopenfilename(
            title="Commander-Deckliste wählen",
            filetypes=[
                ("Deck lists", "*.txt *.csv *.tsv *.dek *.list"),
                ("All files", "*.*"),
            ],
        )
        if p:
            self.set_deck_path(Path(p))

    def set_deck_path(self, path: Path):
        """Shared entry point for both manual file browsing and the Decks/ autoscan."""
        self.deck_path = path
        self.project_path = None
        self.metadata_ready = False
        self.deck = []
        self.cards = {}
        self.commanders = set()
        self.home.refresh()
        self.home.set_status("Deck ausgewählt. Mit GO FISHING werden Metadaten vollständig geladen.")

    def choose_scenarios_home(self):
        p = filedialog.askopenfilename(
            title="Win-Condition / Scenario JSON laden",
            initialdir=str(DATA_SCENARIOS_DIR) if DATA_SCENARIOS_DIR.is_dir() else str(PROJECT_ROOT),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not p:
            return
        try:
            self.scenarios = engine.load_scenarios(Path(p))
            self.pending_scenario_file = Path(p)
            self.home.set_status(f"{len(self.scenarios)} Szenario(s) geladen. Jetzt Deck wählen bzw. GO FISHING.")
            self.home.refresh()
        except Exception as exc:
            self.home.set_status(f"Scenario JSON konnte nicht geladen werden: {exc}", error=True)

    def load_project(self):
        p = filedialog.askopenfilename(
            title="Goldfish-Projekt laden",
            filetypes=[("Goldfish project", "*.json"), ("All files", "*.*")],
        )
        if not p:
            return
        try:
            data = engine.load_project_v43(Path(p))
            self.project_path = Path(p)
            self.deck_path = data["deck_path"]
            self.commanders = set(data["commanders"])
            self.runs_var.set(data["runs"])
            if data["runs"] == 200:
                self.run_mode_var.set("Diagnostic (200)")
            elif data["runs"] == 5000:
                self.run_mode_var.set("Standard (5,000)")
            elif data["runs"] == 20000:
                self.run_mode_var.set("Deep (20,000)")
            else:
                self.run_mode_var.set("Custom")
            self.turns_var.set(data["turns"])
            self.seed_var.set(data["seed"])
            self.opponent_var.set(data["opponent_profile"])
            voltron_idx = data.get("voltron_target_index")
            self.voltron_target_var.set(
                f"Gegner {int(voltron_idx)}" if voltron_idx is not None else "Aus"
            )
            for tag, var in self.tag_vars.items():
                var.set(tag in data["strategy_tags"])
            self.scenarios = data["scenarios"]
            self.strategy_file = data["strategy_file"]
            self.value_model_file = data["value_model_file"]
            self.metadata_ready = False
            self.deck = []
            self.cards = {}
            self.home.set_status(
                f"Projekt geladen: {Path(p).name}. GO FISHING lädt jetzt Deck + Metadaten."
            )
            self.home.refresh()
        except Exception as exc:
            self.home.set_status(f"Projekt konnte nicht geladen werden: {exc}", error=True)

    def start_metadata_load(self):
        if not self.deck_path:
            self.home.set_status("Bitte zuerst eine Deckliste oder ein Projekt auswählen.", error=True)
            return
        if self.running:
            return
        self.running = True
        self.home.begin_loading("Initialisiere Scryfall-Cache …")
        deck_path = self.deck_path
        preset_commanders = set(self.commanders)
        threading.Thread(
            target=self._metadata_worker,
            args=(deck_path, preset_commanders),
            daemon=True,
        ).start()

    def _metadata_worker(self, deck_path: Path, preset_commanders: set[str]):
        try:
            engine.ensure_runtime_dependencies(
                include_images=True,
                status_callback=lambda text: self.q.put(("bootstrap_status", text)),
            )
            self.q.put(("bootstrap_status", "Lese Deckliste und lade Scryfall-Metadaten …"))
            hints = list(preset_commanders) or engine.detect_commander_hints(deck_path)
            DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache = DATA_CACHE_DIR / "scryfall_card_cache.json"
            deck = engine.build_deck_v4(
                deck_path,
                hints,
                cache_path=cache,
                offline=False,
                metadata_csv=None,
            )
            self.q.put(("metadata_done", deck, hints))
        except Exception as exc:
            self.q.put(("metadata_error", str(exc)))

    # ------------------------------------------------------------------
    # Project / scenario persistence
    # ------------------------------------------------------------------

    def save_project(self):
        if not self.deck_path:
            self.main.set_status("Kein Deck geladen.")
            return
        p = filedialog.asksaveasfilename(
            title="Goldfish-Projekt speichern",
            defaultextension=".goldfish.json",
            filetypes=[("Goldfish project", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.deck_path.stem}.goldfish.json",
        )
        if not p:
            return
        try:
            engine.save_project_v43(
                Path(p),
                deck_file=self.deck_path,
                commanders=sorted(self.commanders),
                runs=self.runs_var.get(),
                turns=self.turns_var.get(),
                seed=self.seed_var.get(),
                strategy_tags=self.selected_tags(),
                opponent_profile=self.opponent_var.get(),
                voltron_target_index=self.voltron_target_index(),
                scenarios=self.scenarios,
                strategy_file=self.strategy_file,
                value_model_file=self.value_model_file,
            )
            self.project_path = Path(p)
            self.main.set_status(f"Projekt gespeichert: {p}")
        except Exception as exc:
            self.main.set_status(f"Projekt konnte nicht gespeichert werden: {exc}", error=True)

    def load_scenarios_into_ready_deck(self):
        p = filedialog.askopenfilename(
            title="Scenario JSON laden",
            initialdir=str(DATA_SCENARIOS_DIR) if DATA_SCENARIOS_DIR.is_dir() else str(PROJECT_ROOT),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not p:
            return
        try:
            self.scenarios = engine.load_scenarios(Path(p))
            self.setup.load_from_app()
            self.setup.set_status(f"{len(self.scenarios)} Szenario(s) geladen.")
        except Exception as exc:
            self.setup.set_status(f"Scenario JSON konnte nicht geladen werden: {exc}", error=True)

    def save_scenarios(self):
        self.setup.commit_current()
        DATA_SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
        p = filedialog.asksaveasfilename(
            title="Scenario JSON speichern",
            defaultextension=".json",
            initialdir=str(DATA_SCENARIOS_DIR),
            filetypes=[("JSON", "*.json")],
            initialfile=(f"{self.deck_path.stem}_scenarios.json" if self.deck_path else "scenarios.json"),
        )
        if p:
            try:
                engine.save_scenarios(Path(p), self.scenarios)
                self.setup.set_status(f"Szenarien gespeichert: {p}")
            except Exception as exc:
                self.setup.set_status(f"Speichern fehlgeschlagen: {exc}", error=True)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def selected_tags(self):
        return {tag for tag, var in self.tag_vars.items() if var.get()}

    def voltron_target_index(self):
        """v4.15.7 (task #18, 'Voltron-GUI-Feld'): "Aus" -> None (unset,
        pre-v4.15.0 behavior); "Gegner N" -> the opponent index N."""
        choice = self.voltron_target_var.get()
        return int(choice.rsplit(" ", 1)[-1]) if choice != "Aus" else None

    def build_advanced_opponent_seats(self):
        """v4.64.0: aus dem im 'Gegnerprofil'-Dialog (AdvancedOpponentDialog)
        zuletzt übernommenen Zustand die advanced_opponent_seats-Liste für
        engine.run_pipeline_v440 bauen - nur die ersten
        advanced_opponent_seat_count_var Sitzplätze. "?"-Marker bleiben
        unverändert stehen; sie werden pro Run in
        engine._resolve_advanced_opponent_seats_for_run aufgelöst, nicht
        hier (siehe Docs/README.md v4.64.0)."""
        count = max(1, min(4, int(self.advanced_opponent_seat_count_var.get() or 1)))
        return [dict(self.advanced_opponent_seat_specs[i]) for i in range(count)]

    def run_simulation(self):
        if self.running or not self.metadata_ready:
            return
        if not self.commanders:
            self.main.set_status("Bitte mindestens einen Commander markieren.", error=True)
            return

        self.running = True
        self.main.begin_simulation()
        # Capture Tk values on main thread.
        deck_path = self.deck_path
        commanders = sorted(self.commanders)
        runs = int(self.runs_var.get())
        turns = int(self.turns_var.get())
        seed = int(self.seed_var.get())
        tags = set(self.selected_tags())
        opponent = self.opponent_var.get()
        voltron_target_index = self.voltron_target_index()
        # v4.64.0: "Gegnerprofil" - when enabled, this overrides the simple
        # opponent_profile dropdown for this run (see
        # engine.apply_advanced_opponent_model_override). Building the seat
        # list here (main thread) rather than in the worker thread keeps the
        # same "capture Tk values on main thread" discipline as every other
        # value above.
        advanced_opponent_model = bool(self.advanced_opponent_enabled_var.get())
        advanced_opponent_seats = (
            self.build_advanced_opponent_seats() if advanced_opponent_model else []
        )
        if not tags:
            self.main.set_status(
                "Hinweis: keine Strategy-Tags gewählt; Pilotlogik läuft neutral. "
                "Die Auswertung darf Deckrollen nur als Anzeige-Inferenz verwenden."
            )
        scenarios = json.loads(json.dumps(self.scenarios))
        strategy_file = self.strategy_file
        value_model_file = self.value_model_file

        threading.Thread(
            target=self._simulation_worker,
            args=(
                deck_path, commanders, runs, turns, seed, tags, opponent,
                scenarios, strategy_file, value_model_file, voltron_target_index,
                advanced_opponent_model, advanced_opponent_seats,
            ),
            daemon=True,
        ).start()

    def _simulation_worker(
        self, deck_path, commanders, runs, turns, seed, tags,
        opponent, scenarios, strategy_file, value_model_file,
        voltron_target_index=None,
        advanced_opponent_model=False, advanced_opponent_seats=None,
    ):
        try:
            result = engine.run_pipeline_v440(
                deck_path,
                commanders,
                runs=runs,
                turns=turns,
                seed=seed,
                strategy_file=strategy_file,
                strategy_tags=tags,
                opponent_profile=opponent,
                value_model_file=value_model_file,
                scenarios=scenarios,
                output_root=results_root_for_deck(deck_path),
                progress_callback=lambda done, total: self.q.put(("sim_progress", done, total)),
                voltron_target_index=voltron_target_index,
                advanced_opponent_model=advanced_opponent_model,
                advanced_opponent_seats=advanced_opponent_seats or [],
            )
            self.q.put(("sim_done", result))
        except Exception as exc:
            self.q.put(("sim_error", str(exc)))

    # ------------------------------------------------------------------

    def set_commanders(self, names):
        requested = set(names or ())
        legal_sets = {choice for _display, choice in legal_commander_choices(self.deck)}
        if frozenset(requested) not in legal_sets:
            self.main.set_status("Ungültige Commander-Auswahl wurde verworfen.", error=True)
            return
        self.commanders = requested
        self.deck = [
            engine.replace(c, commander=(c.name in self.commanders))
            for c in self.deck
        ]
        self.cards = {}
        for c in self.deck:
            self.cards.setdefault(c.name, c)
        self.main.refresh_commander_selector()
        self.main.refresh_deck_table()
        self.main.set_status("Commander: " + " + ".join(sorted(self.commanders)))

    def poll_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "bootstrap_status":
                    self.home.set_status(msg[1])

                elif kind == "metadata_done":
                    self.running = False
                    self.deck = msg[1]
                    hints = msg[2]
                    if hints:
                        self.commanders = set(hints)

                    # Only legal commander selections survive. This also repairs old
                    # projects in which a double-click accidentally marked a land.
                    self.commanders = normalize_commander_selection(self.deck, self.commanders)

                    self.deck = [
                        engine.replace(c, commander=(c.name in self.commanders))
                        for c in self.deck
                    ]
                    self.cards = {}
                    for c in self.deck:
                        self.cards.setdefault(c.name, c)
                    self.metadata_ready = True

                    # Pillow may have been installed during this same GO FISHING run.
                    global PIL_AVAILABLE, Image, ImageTk, ImageDraw, ImageFont, BytesIO
                    if not PIL_AVAILABLE:
                        try:
                            from PIL import (
                                Image as _Image,
                                ImageTk as _ImageTk,
                                ImageDraw as _ImageDraw,
                                ImageFont as _ImageFont,
                            )
                            from io import BytesIO as _BytesIO
                            Image, ImageTk = _Image, _ImageTk
                            ImageDraw, ImageFont = _ImageDraw, _ImageFont
                            BytesIO = _BytesIO
                            PIL_AVAILABLE = True
                        except Exception as _pil_reload_error:
                            PIL_AVAILABLE = False
                            self.home.set_status(
                                f"Kartenbild-/Mana-Icon-Modul konnte nach Installation nicht geladen werden: {_pil_reload_error}",
                                error=True,
                            )

                    self.home.end_loading()
                    self.show_main()
                    self.main.set_status(
                        f"{len(self.deck)} Karten vollständig geladen. "
                        f"Commander: {', '.join(sorted(self.commanders)) or 'bitte markieren'}"
                    )

                elif kind == "metadata_error":
                    self.running = False
                    self.home.end_loading()
                    self.home.set_status(f"Metadaten-Laden fehlgeschlagen: {msg[1]}", error=True)

                elif kind == "sim_progress":
                    done, total = msg[1], msg[2]
                    self.main.update_progress(done, total)

                elif kind == "sim_done":
                    self.running = False
                    result = msg[1]
                    self.main.end_simulation()
                    self.main.set_status(
                        f"Fertig. Upload-ZIP: {result['zip_path']}"
                    )
                    self.main.last_result_dir = Path(result["result_dir"])
                    self.main.last_zip = Path(result["zip_path"])
                    self.main.result_btn.configure(state="normal")
                    self.main.analysis_btn.configure(state="normal")

                elif kind == "sim_error":
                    self.running = False
                    self.main.end_simulation()
                    self.main.set_status(f"Simulation fehlgeschlagen: {msg[1]}", error=True)

                elif kind == "image_done":
                    name, image = msg[1], msg[2]
                    self.image_cache[name] = image
                    self.main.show_cached_image(name)

                elif kind == "image_png_done":
                    name, raw = msg[1], msg[2]
                    try:
                        encoded = base64.b64encode(raw)
                        photo = tk.PhotoImage(data=encoded, format="png")
                        # Scryfall PNG is large; integer subsample keeps aspect ratio and
                        # works without Pillow.
                        factor = max(
                            1,
                            (photo.width() + 284) // 285,
                            (photo.height() + 399) // 400,
                        )
                        if factor > 1:
                            photo = photo.subsample(factor, factor)
                        self.image_cache[name] = photo
                        self.main.show_cached_image(name)
                    except Exception as exc:
                        self.main.show_image_error(name, f"Tk-PNG-Fallback fehlgeschlagen: {exc}")

                elif kind == "image_error":
                    name, err = msg[1], msg[2]
                    self.main.show_image_error(name, err)
        except queue.Empty:
            pass
        self.after(100, self.poll_queue)


class HomePage(ttk.Frame):
    def __init__(self, parent, app: GoldfishApp):
        super().__init__(parent)
        self.app = app

        self._deck_scan_paths: list[Path] = []

        outer = ttk.Frame(self, padding=36)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer, text="Commander Goldfish",
            font=("Segoe UI", 30, "bold"),
            anchor="center",
        ).pack(pady=(32, 5), fill="x")
        ttk.Label(
            outer,
            text="Deckbuilding-Simulator · Setup-Analyse · Win-Condition-Status",
            font=("Segoe UI", 12), anchor="center",
        ).pack(pady=(0, 24), fill="x")

        card = ttk.Frame(outer, padding=18)
        card.pack(fill="x", padx=220)

        # Centered loader controls instead of left-aligned rows.
        loaders = ttk.Frame(card)
        loaders.pack(anchor="center", fill="x")

        scan_row = ttk.Frame(loaders)
        scan_row.pack(anchor="center", pady=(3, 8))
        ttk.Label(scan_row, text="Deck aus Decks/-Ordner:").pack(side="left", padx=(0, 6))
        self.deck_scan_var = tk.StringVar(value="")
        self.deck_scan_combo = ttk.Combobox(
            scan_row, textvariable=self.deck_scan_var, state="readonly", width=34,
        )
        self.deck_scan_combo.pack(side="left")
        self.deck_scan_combo.bind("<<ComboboxSelected>>", self._on_deck_scan_selected)
        ttk.Button(scan_row, text="↻", width=3, command=self.refresh_deck_scan).pack(side="left", padx=(4, 0))

        ttk.Button(loaders, text="Deck von anderer Stelle laden …", command=app.choose_deck, width=28).pack(anchor="center", pady=(3, 2))
        self.deck_label = ttk.Label(loaders, text="Noch kein Deck gewählt.", anchor="center", justify="center", wraplength=760)
        self.deck_label.pack(anchor="center", fill="x", pady=(0, 10))

        ttk.Button(loaders, text="Projekt laden …", command=app.load_project, width=28).pack(anchor="center", pady=(3, 2))
        self.project_label = ttk.Label(loaders, text="Portable Deck + Einstellungen + Win Conditions", anchor="center", justify="center", wraplength=760)
        self.project_label.pack(anchor="center", fill="x", pady=(0, 10))

        ttk.Button(loaders, text="Win Conditions laden …", command=app.choose_scenarios_home, width=28).pack(anchor="center", pady=(3, 2))
        self.scenario_label = ttk.Label(loaders, text="Optional: Scenario JSON vor dem Start laden", anchor="center", justify="center", wraplength=760)
        self.scenario_label.pack(anchor="center", fill="x", pady=(0, 12))

        self.go = RoundFishingButton(card, app.start_metadata_load, diameter=190)
        self.go.pack(anchor="center", pady=(16, 14))

        self.progress = ttk.Progressbar(card, mode="indeterminate", length=500)
        self.progress.pack(anchor="center", pady=5)
        self.status = ttk.Label(card, text="", wraplength=900, justify="center", anchor="center")
        self.status.pack(anchor="center", fill="x", pady=8)

        ttk.Label(
            outer,
            text=(
                "Deckliste ODER Goldfish-Projekt ist erforderlich; Win Conditions sind optional. "
                "GO FISHING lädt danach Kartendaten/Cache vollständig im Hintergrund und öffnet erst dann die Arbeitsoberfläche."
            ),
            wraplength=900, justify="center", anchor="center",
        ).pack(pady=18, fill="x")

    def refresh_deck_scan(self):
        self._deck_scan_paths = scan_decks()
        folder = decks_directory()
        if not self._deck_scan_paths:
            self.deck_scan_combo.configure(values=[])
            self.deck_scan_var.set("")
            self.deck_scan_combo.configure(
                state="disabled" if folder is None else "readonly"
            )
            if folder is None:
                self.deck_scan_combo.set("(kein Decks/-Ordner gefunden)")
            else:
                self.deck_scan_combo.set("(Decks/-Ordner ist leer)")
            return
        self.deck_scan_combo.configure(state="readonly")
        names = [p.stem for p in self._deck_scan_paths]
        self.deck_scan_combo.configure(values=names)
        if self.app.deck_path in self._deck_scan_paths:
            self.deck_scan_var.set(self.app.deck_path.stem)
        else:
            self.deck_scan_var.set("")

    def _on_deck_scan_selected(self, _event=None):
        idx = self.deck_scan_combo.current()
        if idx < 0 or idx >= len(self._deck_scan_paths):
            return
        self.app.set_deck_path(self._deck_scan_paths[idx])

    def refresh(self):
        self.refresh_deck_scan()
        if self.app.deck_path:
            self.deck_label.configure(text=str(self.app.deck_path))
        else:
            self.deck_label.configure(text="Noch kein Deck gewählt.")
        if self.app.project_path:
            self.project_label.configure(text=str(self.app.project_path))
        else:
            self.project_label.configure(text="Portable Deck + Einstellungen + Win Conditions")
        if self.app.scenarios:
            self.scenario_label.configure(text=f"{len(self.app.scenarios)} Win-Condition-Szenario(s) vorbereitet")
        else:
            self.scenario_label.configure(text="Optional: Scenario JSON vor dem Start laden")

    def set_status(self, text, error=False):
        self.status.configure(text=text, foreground=("#a00000" if error else ""))

    def begin_loading(self, text):
        self.go.set_enabled(False)
        self.progress.start(12)
        self.set_status(text)

    def end_loading(self):
        self.progress.stop()
        self.go.set_enabled(True)



class SimpleLineChart(tk.Canvas):
    """Small dependency-free line chart for the result dashboard."""
    def __init__(self, parent, *, title="", series=None, **kwargs):
        super().__init__(
            parent,
            height=220,
            highlightthickness=1,
            highlightbackground="#b8b8b8",
            background="white",
            **kwargs,
        )
        self.title_text = title
        self.series = series or {}
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_data(self, title, series):
        self.title_text = title
        self.series = series or {}
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = max(300, self.winfo_width())
        h = max(180, self.winfo_height())
        left, right, top, bottom = 48, 16, 30, 34

        self.create_text(
            10, 8, text=self.title_text,
            anchor="nw", font=("Segoe UI", 10, "bold"),
        )

        valid = {}
        all_points = []
        for name, points in self.series.items():
            clean = [
                (float(x), float(y))
                for x, y in points
                if y is not None
            ]
            if clean:
                valid[name] = clean
                all_points.extend(clean)

        if not all_points:
            self.create_text(
                w / 2, h / 2,
                text="Keine Daten",
                font=("Segoe UI", 10),
            )
            return

        min_x = min(x for x, _ in all_points)
        max_x = max(x for x, _ in all_points)
        min_y = min(y for _, y in all_points)
        max_y = max(y for _, y in all_points)

        if max_x <= min_x:
            max_x = min_x + 1
        if max_y <= min_y:
            pad = max(1.0, abs(max_y) * .1)
            min_y -= pad
            max_y += pad
        else:
            pad = (max_y - min_y) * .08
            min_y -= pad
            max_y += pad

        plot_w = max(1, w - left - right)
        plot_h = max(1, h - top - bottom)

        def xy(x, y):
            px = left + (x - min_x) / (max_x - min_x) * plot_w
            py = top + (max_y - y) / (max_y - min_y) * plot_h
            return px, py

        self.create_line(left, top, left, top + plot_h, fill="#777")
        self.create_line(left, top + plot_h, left + plot_w, top + plot_h, fill="#777")

        for i in range(5):
            frac = i / 4
            yv = max_y - frac * (max_y - min_y)
            py = top + frac * plot_h
            self.create_line(left - 4, py, left, py, fill="#777")
            self.create_text(
                left - 7, py,
                text=f"{yv:.1f}",
                anchor="e",
                font=("Segoe UI", 8),
            )

        x_values = sorted(set(x for x, _ in all_points))
        for x in x_values:
            px, py = xy(x, min_y)
            self.create_line(px, top + plot_h, px, top + plot_h + 4, fill="#777")
            self.create_text(
                px, top + plot_h + 7,
                text=str(int(x) if x.is_integer() else x),
                anchor="n",
                font=("Segoe UI", 8),
            )

        palette = ["#1565c0", "#c62828", "#2e7d32", "#6a1b9a", "#ef6c00", "#455a64"]
        legend_x = left + 8
        for index, (name, points) in enumerate(valid.items()):
            color = palette[index % len(palette)]
            coords = []
            for x, y in points:
                coords.extend(xy(x, y))
            if len(coords) >= 4:
                self.create_line(
                    *coords, fill=color, width=2, smooth=False
                )
            for x, y in points:
                px, py = xy(x, y)
                self.create_oval(
                    px - 2, py - 2, px + 2, py + 2,
                    fill=color, outline=color,
                )
            self.create_rectangle(
                legend_x, 21, legend_x + 9, 30,
                fill=color, outline=color,
            )
            self.create_text(
                legend_x + 13, 25,
                text=name, anchor="w",
                font=("Segoe UI", 8),
            )
            legend_x += 13 + max(65, len(name) * 6)


# v4.65.0: Handzusammensetzung nach Kategorie (Länder/Ramp/Interaction/
# Card Advantage/Kreaturen/sonstige Spells/Sonstiges) je Turn - siehe
# App/engine.py's Modulkommentar oberhalb von _hand_composition_category
# für die volle Herleitung. Kategorien+Farben hier fest verdrahtet (an die
# von engine._HAND_COMPOSITION_BUCKETS gelieferten avg_hand_*-Felder
# gekoppelt), damit Legende und Balkenfarben stabil und lesbar bleiben.
HAND_COMPOSITION_CATEGORIES = (
    ("avg_hand_lands", "Länder", "#8d6e63"),
    ("avg_hand_ramp", "Ramp", "#2e7d32"),
    ("avg_hand_interaction", "Interaction", "#c62828"),
    ("avg_hand_card_advantage", "Card Advantage", "#1565c0"),
    ("avg_hand_creatures", "Kreaturen", "#6a1b9a"),
    ("avg_hand_spells", "sonstige Spells", "#ef6c00"),
    ("avg_hand_other", "Sonstiges", "#455a64"),
)


class SimpleStackedBarChart(tk.Canvas):
    """Dependency-free gestapeltes Balkendiagramm fürs Result-Dashboard
    (v4.65.0). Gleiche Zeichenkonventionen wie SimpleLineChart (weißer
    Hintergrund, Redraw bei <Configure>), zeichnet aber pro x-Wert einen
    gestapelten Balken statt Linienpunkte."""
    def __init__(self, parent, *, title="", categories=None, series=None, **kwargs):
        super().__init__(
            parent,
            height=220,
            highlightthickness=1,
            highlightbackground="#b8b8b8",
            background="white",
            **kwargs,
        )
        self.title_text = title
        self.categories = categories or []  # [(field_key, label, color), ...]
        self.series = series or {}  # {x: {field_key: value, ...}, ...}
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_data(self, title, categories, series):
        self.title_text = title
        self.categories = categories or []
        self.series = series or {}
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = max(300, self.winfo_width())
        h = max(180, self.winfo_height())
        left, right, top, bottom = 48, 16, 30, 46

        self.create_text(
            10, 8, text=self.title_text,
            anchor="nw", font=("Segoe UI", 10, "bold"),
        )

        xs = sorted(self.series.keys())
        if not xs or not self.categories:
            self.create_text(
                w / 2, h / 2,
                text="Keine Daten",
                font=("Segoe UI", 10),
            )
            return

        totals = [
            sum(float(self.series[x].get(key, 0) or 0) for key, _label, _color in self.categories)
            for x in xs
        ]
        max_total = max(totals) if totals else 0.0
        if max_total <= 0:
            max_total = 1.0
        max_y = max_total * 1.08

        plot_w = max(1, w - left - right)
        plot_h = max(1, h - top - bottom)

        self.create_line(left, top, left, top + plot_h, fill="#777")
        self.create_line(left, top + plot_h, left + plot_w, top + plot_h, fill="#777")

        for i in range(5):
            frac = i / 4
            yv = max_y * (1 - frac)
            py = top + frac * plot_h
            self.create_line(left - 4, py, left, py, fill="#777")
            self.create_text(
                left - 7, py,
                text=f"{yv:.1f}",
                anchor="e",
                font=("Segoe UI", 8),
            )

        n = len(xs)
        slot_w = plot_w / n
        bar_w = max(3, slot_w * 0.62)
        label_stride = max(1, n // 20)
        for i, x in enumerate(xs):
            x_center = left + (i + 0.5) * slot_w
            x0 = x_center - bar_w / 2
            x1 = x_center + bar_w / 2
            y_cursor = top + plot_h
            row = self.series[x]
            for key, _label, color in self.categories:
                val = float(row.get(key, 0) or 0)
                if val <= 0:
                    continue
                y_top = y_cursor - (val / max_y) * plot_h
                self.create_rectangle(x0, y_top, x1, y_cursor, fill=color, outline="")
                y_cursor = y_top
            if i % label_stride == 0:
                self.create_text(
                    x_center, top + plot_h + 7,
                    text=str(int(x) if float(x).is_integer() else x),
                    anchor="n",
                    font=("Segoe UI", 8),
                )

        legend_x = left + 8
        legend_y = top + plot_h + 22
        for key, label, color in self.categories:
            self.create_rectangle(
                legend_x, legend_y, legend_x + 9, legend_y + 9,
                fill=color, outline=color,
            )
            self.create_text(
                legend_x + 13, legend_y + 4,
                text=label, anchor="w",
                font=("Segoe UI", 8),
            )
            legend_x += 13 + max(60, len(label) * 6)


class AnalysisPage(ttk.Frame):
    """Direct, non-AI result analysis for a completed simulation.

    Lives inside the main window's page container (like HomePage/MainPage/ScenarioPage).
    Content is rebuilt each time `load()` is called, since the result_dir changes
    between simulation runs.
    """
    def __init__(self, parent, app: GoldfishApp):
        super().__init__(parent)
        self.app = app
        self.result_dir: Path | None = None
        self.data: dict = {}

        self.header = ttk.Frame(self, padding=10)
        self.header.pack(fill="x")
        ttk.Label(
            self.header,
            text="Simulation · Auswertung",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        self.header_result_label = ttk.Label(self.header, text="")
        self.header_result_label.pack(side="left", padx=8)
        ttk.Button(
            self.header,
            text="Zurück zum Deck",
            command=self.app.show_main,
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            self.header,
            text="Ergebnisordner öffnen",
            command=self.open_folder,
        ).pack(side="right")

        self.book_container = ttk.Frame(self)
        self.book_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.book: ttk.Notebook | None = None

    def load(self, result_dir: Path):
        """(Re)build the whole page for a fresh result_dir. Raises on missing/invalid data."""
        self.result_dir = Path(result_dir)

        path = self.result_dir / "analysis_overview.json"
        if not path.exists():
            raise FileNotFoundError(
                "analysis_overview.json fehlt im Ergebnisordner."
            )
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self.header_result_label.configure(text=f"  {self.result_dir.name}")

        if self.book is not None:
            self.book.destroy()
        self.book = ttk.Notebook(self.book_container)
        self.book.pack(fill="both", expand=True)

        self._build_overview()
        self._build_turns()
        self._build_scenarios()
        self._build_strategy()
        self._build_opponents()
        self._build_deck_comparison()

    def open_folder(self):
        try:
            import os
            os.startfile(str(self.result_dir))
        except Exception:
            pass

    def _metric_box(self, parent, title, value, detail=""):
        box = ttk.LabelFrame(parent, text=title, padding=8)
        ttk.Label(
            box, text=value,
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        if detail:
            ttk.Label(
                box, text=detail, wraplength=220,
            ).pack(anchor="w", pady=(3, 0))
        return box

    def _build_overview(self):
        tab = ttk.Frame(self.book, padding=10)
        self.book.add(tab, text="Übersicht")

        outcomes = self.data.get("outcomes", {})
        opening = self.data.get("opening", {})
        strategy = self.data.get("strategy", {})
        engine_state = self.data.get("engine_invariants", {})

        top = ttk.Frame(tab)
        top.pack(fill="x")

        # v4.65.1: bei aktivem Gegnerprofil (advanced_opponent_model) war
        # dieses Detail bislang irreführend, da es immer nur den simplen
        # Dropdown-Wert (z.B. "goldfish", per Definition 0 Schaden) zeigte,
        # selbst wenn in Wahrheit reale, schadenverursachende Sitzplätze
        # simuliert wurden (siehe App/engine.py: advanced_opponent_summary /
        # AI_SCENARIO_AUTHORING... Fund aus den zwei hochgeladenen Runs).
        adv = self.data.get("advanced_opponent_summary", {})
        if adv.get("active"):
            opponent_detail = adv.get("label") or "Gegnerprofil aktiv (nicht nur Dropdown-Wert)"
        else:
            opponent_detail = f"Opponent: {self.data.get('opponent', '')}"

        metrics = [
            (
                "Runs",
                f"{int(self.data.get('runs', 0)):,}",
                opponent_detail,
            ),
            (
                "Gewonnen",
                f"{float(outcomes.get('win_by_turn_limit_pct', 0)):.2f} %",
                f"Median T{outcomes.get('median_win_turn_when_winning') or '–'}",
            ),
            (
                "Verloren",
                f"{float(outcomes.get('loss_by_turn_limit_pct', 0)):.2f} %",
                f"Median T{outcomes.get('median_loss_turn_when_losing') or '–'}",
            ),
            (
                "Noch aktiv",
                f"{float(outcomes.get('active_at_turn_limit_pct', 0)):.2f} %",
                "am Turn-Limit",
            ),
            (
                "Engine",
                str(engine_state.get("status", "–")),
                (
                    f"Ressource {engine_state.get('resource_invariant_violations', 0)} · "
                    f"Payment {engine_state.get('payment_resource_conflicts', 0)}"
                ),
            ),
        ]
        for i, info in enumerate(metrics):
            box = self._metric_box(top, *info)
            box.grid(
                row=0, column=i,
                sticky="nsew", padx=3,
            )
            top.columnconfigure(i, weight=1)

        # v4.65.0: statt der vormals fest hier eingetragenen "111 Life"-
        # Schwelle wird hier angezeigt, was tatsächlich auf der Setup/Win-
        # Condition-Oberfläche als Szenario vom Kind "Win Condition"
        # konfiguriert wurde (App/engine.py: _wc_kind_scenarios/outcomes
        # "win_condition_*"). Ist nichts konfiguriert, wird das ehrlich so
        # angezeigt statt stillschweigend auf 111 zurückzufallen.
        wc_configured = bool(outcomes.get("win_condition_configured"))
        if wc_configured:
            wc_names = ", ".join(outcomes.get("win_condition_names") or []) or "Win Condition"
            wc_value = f"{float(outcomes.get('win_condition_reach_pct', 0)):.2f} %"
            wc_median = outcomes.get("win_condition_median_turn")
            wc_detail = wc_names + (f" · Median T{wc_median:g}" if wc_median is not None else "")
            # v4.65.2: Nutzerauftrag "Aziza-Siegdefinitionslücke ranmachen" -
            # ein WC-"Match" (z.B. x_spell_lethal mit target="any") bedeutet
            # nur "Combo geht gegen (mind.) EINEN Gegner auf", nicht
            # zwingend "Partie gewonnen" (check_win verlangt ALLE Gegner auf
            # 0 Leben). Wenn mindestens eine konfigurierte WC laut
            # App/engine.py:_wc_scenario_target_scope nur Einzelziel-Scope
            # hat, wird die Lücke hier direkt als Zahl sichtbar gemacht statt
            # nur im Fließtext der Beobachtungen.
            single_target = outcomes.get("win_condition_single_target_names") or []
            if single_target:
                full_win_pct = float(outcomes.get("win_condition_reach_and_full_win_pct", 0) or 0)
                wc_detail += f" · davon Partie gewonnen: {full_win_pct:.2f} %"
        else:
            wc_value = "–"
            wc_detail = "keine Win Condition konfiguriert"

        second = ttk.Frame(tab)
        second.pack(fill="x", pady=(8, 0))
        extra = [
            (
                "Ø Endleben",
                f"{float(outcomes.get('avg_end_life', 0)):.1f}",
                f"Ø Draws: {float(outcomes.get('avg_cards_drawn', 0)):.2f}",
            ),
            (
                "Win Condition",
                wc_value,
                wc_detail,
            ),
            (
                "Ø Endhand",
                f"{float(outcomes.get('avg_end_hand', 0)):.2f}",
                "",
            ),
            (
                "Opening Lands",
                f"{float(opening.get('avg_opening_lands', 0)):.2f}",
                f"Ø Mulligans: {float(opening.get('avg_mulligans', 0)):.2f}",
            ),
            (
                "Strategy",
                ", ".join(strategy.get("selected", [])) or "neutral",
                (
                    "Anzeige-Inferenz: "
                    + ", ".join(strategy.get("inferred_for_display_only", []))
                    if strategy.get("inferred_for_display_only")
                    else "keine zusätzliche Inferenz"
                ),
            ),
        ]
        for i, info in enumerate(extra):
            box = self._metric_box(second, *info)
            box.grid(
                row=0, column=i,
                sticky="nsew", padx=3,
            )
            second.columnconfigure(i, weight=1)

        ttk.Label(
            tab, text="Auffälligkeiten",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(12, 4))
        obs = tk.Text(
            tab, height=6, wrap="word",
            font=("Segoe UI", 9),
        )
        obs.pack(fill="x")
        for line in self.data.get("observations", []):
            obs.insert("end", "• " + line + "\n")
        obs.configure(state="disabled")

        ttk.Label(
            tab, text="Relative Card-Highlights",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(12, 4))
        tree = ttk.Treeview(
            tab,
            columns=("tier", "name", "value"),
            show="headings",
            height=8,
        )
        tree.heading("tier", text="Tier")
        tree.heading("name", text="Karte")
        tree.heading("value", text="Value / Seen")
        tree.column("tier", width=60, stretch=False)
        tree.column("name", width=300)
        tree.column("value", width=120, stretch=False)
        for row in self.data.get("card_highlights", []):
            tree.insert(
                "", "end",
                values=(
                    row.get("tier", ""),
                    row.get("name", ""),
                    f"{float(row.get('value_per_seen', 0)):.2f}",
                ),
            )
        tree.pack(fill="both", expand=True)

        # v4.65.0: bislang von der Engine bereits berechnet (siehe
        # combat_and_removal_diagnostics in App/engine.py), aber nie in der
        # GUI angezeigt - eigenständige Durchsicht der Auswertung ergab,
        # dass diese Daten für die Deck-Abstimmung nützlich sind (welche
        # Karten sterben im Kampf/werden vom Gegner entfernt).
        combat = self.data.get("combat_and_removal_diagnostics", {})
        if combat:
            ttk.Label(
                tab, text="Kampf & Entfernung",
                font=("Segoe UI", 11, "bold"),
            ).pack(anchor="w", pady=(12, 4))
            ttk.Label(
                tab,
                text=(
                    f"Ø Tode im Kampf/Run: {float(combat.get('avg_died_in_combat_per_run', 0)):.2f} · "
                    f"Ø vom Gegner entfernt/Run: {float(combat.get('avg_removed_by_opponent_per_run', 0)):.2f} · "
                    f"gesamt geboardwiped: {int(combat.get('total_wiped_by_opponent', 0))}"
                ),
            ).pack(anchor="w")
            top_combat = combat.get("top_died_in_combat", [])
            top_removed = combat.get("top_removed_by_opponent", [])
            if top_combat:
                names = ", ".join(
                    f"{r.get('name', '?')} ({r.get('Died in combat', 0):g})" for r in top_combat
                )
                ttk.Label(
                    tab, text=f"Häufigste Kampftode: {names}", wraplength=1050,
                ).pack(anchor="w", pady=(2, 0))
            if top_removed:
                names = ", ".join(
                    f"{r.get('name', '?')} ({r.get('Removed by opponent', 0):g})" for r in top_removed
                )
                ttk.Label(
                    tab, text=f"Häufigste Entfernungsziele: {names}", wraplength=1050,
                ).pack(anchor="w", pady=(2, 0))

    def _build_turns(self):
        tab = ttk.Frame(self.book, padding=10)
        self.book.add(tab, text="Rundenverlauf")

        turns = self.data.get("turns", [])
        cumulative = {
            int(x["turn"]): x
            for x in self.data.get("cumulative_outcomes", [])
        }

        life_chart = SimpleLineChart(
            tab,
            title="Ø Lebenspunkte und kumulierter Lifegain · aktive/abschließende Spiele",
            series={
                "Life": [
                    (r["turn"], r.get("avg_life", 0))
                    for r in turns
                ],
                "Life gained": [
                    (r["turn"], r.get("avg_life_gained_total", 0))
                    for r in turns
                ],
            },
        )
        life_chart.pack(fill="x", pady=(0, 8))

        outcome_chart = SimpleLineChart(
            tab,
            title="Kumulative Ergebnisse · bezogen auf alle gestarteten Runs",
            series={
                "Win %": [
                    (t, x.get("win_pct", 0))
                    for t, x in sorted(cumulative.items())
                ],
                "Loss %": [
                    (t, x.get("loss_pct", 0))
                    for t, x in sorted(cumulative.items())
                ],
                "Aktiv %": [
                    (t, x.get("active_pct", 0))
                    for t, x in sorted(cumulative.items())
                ],
            },
        )
        outcome_chart.pack(fill="x", pady=(0, 8))

        # v4.65.0: Handzusammensetzung nach Kategorie über die Zeit -
        # eigenständige Durchsicht der Auswertung (Nutzerauftrag, siehe
        # Docs/README.md v4.65.0), macht sichtbar, ob die Hand im Schnitt
        # zu landlastig wird oder Interaction/Ramp im späten Spiel ausgeht.
        composition_series = {
            int(r["turn"]): r for r in turns
        }
        composition_chart = SimpleStackedBarChart(
            tab,
            title="Ø Handzusammensetzung nach Kategorie · aktive/abschließende Spiele je Turn",
            categories=HAND_COMPOSITION_CATEGORIES,
            series=composition_series,
        )
        composition_chart.pack(fill="x", pady=(0, 8))

        cols = (
            "turn", "active", "life", "hand", "mana",
            "win", "loss", "tokens",
        )
        tree = ttk.Treeview(
            tab, columns=cols,
            show="headings", height=10,
        )
        labels = {
            "turn": "Turn",
            "active": "aktive Spiele",
            "life": "Ø Life",
            "hand": "Ø Hand",
            "mana": "Ø Mana Main",
            "win": "Win kum. %",
            "loss": "Loss kum. %",
            "tokens": "Ø Tokens",
        }
        for c in cols:
            tree.heading(c, text=labels[c])
            tree.column(
                c,
                width=105 if c != "active" else 120,
                anchor="center",
            )
        for row in turns:
            t = int(row["turn"])
            co = cumulative.get(t, {})
            tree.insert(
                "", "end",
                values=(
                    t,
                    int(row.get("active_games", 0)),
                    f"{float(row.get('avg_life', 0)):.1f}",
                    f"{float(row.get('avg_hand_size', 0)):.2f}",
                    f"{float(row.get('avg_mana_available_start_main', 0)):.2f}",
                    f"{float(co.get('win_pct', 0)):.2f}",
                    f"{float(co.get('loss_pct', 0)):.2f}",
                    f"{float(row.get('avg_tokens_total_current', 0)):.2f}",
                ),
            )
        tree.pack(fill="both", expand=True)

        ttk.Label(
            tab,
            text=(
                "Hinweis: Ø Life/Hand/Board/Handzusammensetzung pro Turn beziehen sich "
                "auf Spiele, die zu diesem Turn noch aktiv sind oder dort enden. Der "
                "scheinbare Anstieg späterer Turn-Werte kann deshalb Survivor Bias sein."
            ),
            wraplength=1050,
        ).pack(anchor="w", pady=(6, 0))

    def _build_scenarios(self):
        tab = ttk.Frame(self.book, padding=10)
        self.book.add(tab, text="Win Conditions")

        # v4.65.0: kumulativer Match-Verlauf je Turn, für alle aktiven
        # Szenarien vom Kind "Win Condition" - macht die zuvor nur als
        # Einzelzahl (Match %/Median Turn) sichtbare Win-Condition-
        # Erreichbarkeit flexibel über die Zeit sichtbar, exakt anhand
        # dessen, was auf dieser Oberfläche tatsächlich konfiguriert wurde
        # (kein fester Leben-Schwellenwert mehr). Daten kommen unverändert
        # aus App/engine.py's cumulative_reach_by_turn_pct (_streaming_
        # scenario_summary) - hier nur erstmals als Chart statt nur als
        # Tabellenzeile dargestellt.
        wc_rows = [
            row for row in self.data.get("scenarios", [])
            if row.get("kind") == "Win Condition"
        ]
        series = {}
        for row in wc_rows:
            cumulative = row.get("cumulative_reach_by_turn_pct") or {}
            series[row.get("name", "?")] = sorted(
                (int(t), v) for t, v in cumulative.items()
            )
        wc_chart = SimpleLineChart(
            tab,
            title="Win Condition erreicht · kumulativ nach Turn (bezogen auf alle Runs)",
            series=series,
        )
        wc_chart.pack(fill="x", pady=(0, 8))

        cols = (
            "name", "reach", "median", "scope", "setup", "focus", "bottleneck",
        )
        tree = ttk.Treeview(
            tab, columns=cols,
            show="headings", height=18,
        )
        # v4.65.2: neue Spalte "Ziel-Scope" - generisch aus den 'derived'-
        # Praedikaten jedes Win-Condition-Szenarios abgeleitet
        # (App/engine.py:_wc_scenario_target_scope). Macht sichtbar, ob ein
        # Match nur EIN Ziel betrifft (any/Index - check_win() verlangt aber
        # ALLE Gegner fuer einen echten Sieg, siehe "davon Partie gewonnen"
        # in der Übersicht) oder wirklich alle Gegner (each).
        _SCOPE_LABELS = {
            "each": "alle Gegner",
            "any": "Einzelziel",
            "mixed": "gemischt",
            "n/a": "–",
        }
        heads = {
            "name": "Win Condition / Setup",
            "reach": "Match %",
            "median": "Median Turn",
            "scope": "Ziel-Scope",
            "setup": "Cards/Threshold %",
            "focus": "Focus Turns",
            "bottleneck": "häufigster Bottleneck",
        }
        widths = {
            "name": 300,
            "reach": 90,
            "median": 90,
            "scope": 100,
            "setup": 120,
            "focus": 90,
            "bottleneck": 400,
        }
        for c in cols:
            tree.heading(c, text=heads[c])
            tree.column(c, width=widths[c])
        for row in self.data.get("scenarios", []):
            bottlenecks = row.get("top_diagnostic_bottlenecks", [])
            top = ""
            if bottlenecks:
                first = bottlenecks[0]
                if isinstance(first, (list, tuple)) and len(first) >= 2:
                    top = f"{first[0]} ({first[1]})"
            scope_label = _SCOPE_LABELS.get(row.get("target_scope", "n/a"), "–")
            tree.insert(
                "", "end",
                values=(
                    row.get("name", ""),
                    f"{float(row.get('reach_pct', 0)):.3f}",
                    row.get("median_reached_turn") or "–",
                    scope_label,
                    f"{float(row.get('cards_thresholds_reached_pct', 0)):.3f}",
                    int(row.get("focused_turns_total", 0)),
                    top,
                ),
            )
        tree.pack(fill="both", expand=True)

        ttk.Label(
            tab,
            text=(
                "Match = der definierte Szenariozustand wurde beobachtet; "
                "es ist keine Garantie, dass eine echte Combo durch Interaktion resolved. "
                "Ziel-Scope \"Einzelziel\" bedeutet zusätzlich: das Szenario prüft nur EIN "
                "Ziel (z.B. den Gegner mit dem wenigsten Leben) - die Partie gilt aber erst "
                "als gewonnen, wenn ALLE Gegner auf 0 Leben sind (siehe \"davon Partie "
                "gewonnen\" in der Übersicht)."
            ),
            wraplength=1050,
        ).pack(anchor="w", pady=(8, 0))

    def _build_strategy(self):
        tab = ttk.Frame(self.book, padding=10)
        self.book.add(tab, text="Strategy")

        strategy = self.data.get("strategy", {})
        selected = list(strategy.get("selected", []))
        inferred = list(strategy.get("inferred_for_display_only", []))
        display_tags = selected or inferred

        ttk.Label(
            tab,
            text=(
                "Simulation Strategy: "
                + (", ".join(selected) if selected else "neutral")
            ),
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        if not selected and inferred:
            ttk.Label(
                tab,
                text=(
                    "Nur für diese Auswertung aus Deckrollen erkannt: "
                    + ", ".join(inferred)
                    + ". Diese Tags haben die Simulation NICHT gesteuert."
                ),
                wraplength=1000,
            ).pack(anchor="w", pady=(2, 8))

        turns = self.data.get("turns", [])
        if "lifegain" in display_tags:
            chart = SimpleLineChart(
                tab,
                title="Lifegain-Entwicklung",
                series={
                    "Life": [
                        (r["turn"], r.get("avg_life", 0))
                        for r in turns
                    ],
                    "kumulativ gained": [
                        (r["turn"], r.get("avg_life_gained_total", 0))
                        for r in turns
                    ],
                    "gain/Turn": [
                        (r["turn"], r.get("avg_life_gained_this_turn", 0))
                        for r in turns
                    ],
                },
            )
            chart.pack(fill="x", pady=(4, 8))

        if "tokens" in display_tags or any(
            float(r.get("avg_tokens_created_total", 0)) > 0
            for r in turns
        ):
            chart = SimpleLineChart(
                tab,
                title="Token-Entwicklung",
                series={
                    "aktuell gesamt": [
                        (r["turn"], r.get("avg_tokens_total_current", 0))
                        for r in turns
                    ],
                    "Creature Tokens": [
                        (r["turn"], r.get("avg_creature_tokens", 0))
                        for r in turns
                    ],
                    "Food": [
                        (r["turn"], r.get("avg_food", 0))
                        for r in turns
                    ],
                    "kumulativ erstellt": [
                        (r["turn"], r.get("avg_tokens_created_total", 0))
                        for r in turns
                    ],
                },
            )
            chart.pack(fill="x", pady=(4, 8))

        if "counters" in display_tags or any(
            float(r.get("avg_plus1_counters_on_board", 0)) > 0
            for r in turns
        ):
            chart = SimpleLineChart(
                tab,
                title="Counter auf dem Board",
                series={
                    "+1/+1": [
                        (r["turn"], r.get("avg_plus1_counters_on_board", 0))
                        for r in turns
                    ],
                    "benannt": [
                        (r["turn"], r.get("avg_named_counters_on_board", 0))
                        for r in turns
                    ],
                },
            )
            chart.pack(fill="x", pady=(4, 8))

        if not turns:
            ttk.Label(tab, text="Keine Turn-Daten verfügbar.").pack(anchor="w")

    def _build_opponents(self):
        tab = ttk.Frame(self.book, padding=10)
        self.book.add(tab, text="Opponent")

        requested = self.data.get("opponent", "")
        # v4.65.1: siehe gleichnamiger Fix im "Runs"-Kasten der Übersicht -
        # bei aktivem Gegnerprofil zeigt dieses Label jetzt zusätzlich die
        # tatsächlich simulierten Sitzplätze statt nur den irreführenden
        # Dropdown-Wert.
        adv = self.data.get("advanced_opponent_summary", {})
        mode_text = f"Gewählter Modus: {requested}"
        if adv.get("active"):
            mode_text += f"  —  {adv.get('label', 'Gegnerprofil aktiv')}"
        ttk.Label(
            tab,
            text=mode_text,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        if adv.get("active"):
            seat_lines = []
            for seat in adv.get("actual_seat_summary", []) or []:
                counts = seat.get("actual_counts", {})
                counts_str = ", ".join(
                    f"{label} ({n})" for label, n in sorted(counts.items(), key=lambda kv: -kv[1])
                )
                seat_lines.append(f"Sitz {seat.get('seat_index', '?')}: {counts_str}")
            if seat_lines:
                ttk.Label(
                    tab,
                    text="Tatsächlich simulierte Sitzplätze — " + "  |  ".join(seat_lines),
                    wraplength=1050,
                ).pack(anchor="w", pady=(2, 8))

        cols = (
            "profile", "runs", "share", "win", "loss",
            "active", "life", "damage", "wincond",
        )
        tree = ttk.Treeview(
            tab, columns=cols,
            show="headings", height=10,
        )
        heads = {
            "profile": "Profil",
            "runs": "Runs",
            "share": "Anteil %",
            "win": "Win %",
            "loss": "Loss %",
            "active": "Aktiv %",
            "life": "Ø Endlife",
            "damage": "Ø Damage",
            # v4.65.0: ersetzt die vormals fest verdrahtete "111 Life %"-
            # Spalte durch den generischen, je Setup konfigurierten Win-
            # Condition-Reach (siehe App/engine.py: outcomes["win_
            # condition_reach_pct"]/opponent_breakdown[...]["win_
            # condition_reach_pct"]).
            "wincond": "Win Condition %",
        }
        for c in cols:
            tree.heading(c, text=heads[c])
            tree.column(
                c,
                width=110 if c != "profile" else 130,
                anchor="center",
            )

        breakdown = self.data.get("opponent_breakdown", {})
        for profile, row in sorted(breakdown.items()):
            tree.insert(
                "", "end",
                values=(
                    profile,
                    int(row.get("runs", 0)),
                    f"{float(row.get('run_share_pct', 0)):.1f}",
                    f"{float(row.get('win_pct', 0)):.2f}",
                    f"{float(row.get('loss_pct', 0)):.2f}",
                    f"{float(row.get('active_at_limit_pct', 0)):.2f}",
                    f"{float(row.get('avg_end_life', 0)):.1f}",
                    f"{float(row.get('avg_damage_taken', 0)):.1f}",
                    f"{float(row.get('win_condition_reach_pct', 0)):.2f}",
                ),
            )
        tree.pack(fill="x", pady=(8, 10))

        descriptions = ttk.LabelFrame(
            tab, text="Profilcharakteristika", padding=8
        )
        descriptions.pack(fill="x")
        for profile in ("aggro", "midrange", "control", "horde", "goldfish"):
            cfg = engine.OPPONENT_PROFILES.get(profile, {})
            ttk.Label(
                descriptions,
                text=(
                    f"{profile:9s}  Damage {cfg.get('damage_scale', 0):.2f} · "
                    f"Removal {100*cfg.get('removal', 0):.1f}% · "
                    f"Wipe {100*cfg.get('wipe', 0):.1f}% · "
                    f"Combat-Faktor {cfg.get('block_factor', 1):.2f}"
                ),
                font=("Consolas", 9),
            ).pack(anchor="w")
        ttk.Label(
            descriptions,
            text=(
                "Random wählt pro Run gleichverteilt aus Aggro, Midrange, Control und Horde. "
                "Goldfish ist bewusst nicht enthalten."
            ),
            wraplength=1000,
        ).pack(anchor="w", pady=(6, 0))

    def _build_deck_comparison(self):
        """v4.68.0: neuer Tab "Vergleich (1.585 Decks)" - stellt das getestete
        Deck der aus App/archetype_profile gebauten Referenz aus 1.585 echten
        EDHREC-Average-Decks gegenüber (siehe App/engine.py::
        compare_deck_to_archetype_reference). Zwei Vergleichsbasen, wie vom
        Nutzer verlangt: (1) nur Farbidentität des Commanders, (2) zusätzlich
        die in dieser App aktuell ausgewählten Strategie-Tags, sofern
        mindestens einer davon in der Referenzdatenbank erkannt wird."""
        tab = ttk.Frame(self.book, padding=10)
        self.book.add(tab, text="Vergleich (1.585 Decks)")

        deck = list(self.app.deck)
        commanders = self.app.commanders
        cards = self.app.cards
        if not deck or not commanders:
            ttk.Label(
                tab,
                text="Kein geladenes Deck mit Commander verfügbar - Vergleich benötigt beides.",
            ).pack(anchor="w")
            return

        try:
            tags = self.app.selected_tags()
            result = engine.compare_deck_to_archetype_reference(deck, commanders, cards, tags=tags)
        except Exception as exc:
            ttk.Label(
                tab,
                text=f"Vergleich konnte nicht berechnet werden: {exc}",
            ).pack(anchor="w")
            return

        identity_only = result["identity_only"]
        with_strategy = result["with_strategy"]

        header_text = (
            f"Farbidentität (aus Commander): {result['identity_label']}  ·  "
            f"Referenzbasis: {identity_only.basis}"
        )
        ttk.Label(tab, text=header_text, font=("Segoe UI", 11, "bold"), wraplength=1050).pack(anchor="w")

        if result["requested_tags"] and not result["recognized_tags"]:
            ttk.Label(
                tab,
                text=(
                    "Hinweis: keiner der in dieser App ausgewählten Strategie-Tags "
                    f"({', '.join(sorted(result['requested_tags']))}) ist in der "
                    "1.585-Deck-Referenz hinterlegt - Vergleich zeigt nur die Farbidentitäts-Basis."
                ),
                wraplength=1050,
            ).pack(anchor="w", pady=(2, 4))
        elif result["recognized_tags"]:
            ttk.Label(
                tab,
                text=(
                    f"Strategie-Vergleich mit Tag(s) {', '.join(result['recognized_tags'])} "
                    f"[{with_strategy.basis}]"
                ),
                wraplength=1050,
            ).pack(anchor="w", pady=(2, 4))

        cols = ("field", "own", "ref_identity") + (("ref_strategy", "diff") if with_strategy else ("diff",))
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=10)
        tree.heading("field", text="Kategorie")
        tree.column("field", width=200, anchor="w")
        tree.heading("own", text="eigenes Deck")
        tree.column("own", width=110, anchor="center")
        tree.heading("ref_identity", text="Referenz (Farbe)")
        tree.column("ref_identity", width=130, anchor="center")
        if with_strategy:
            tree.heading("ref_strategy", text="Referenz (+Strategie)")
            tree.column("ref_strategy", width=150, anchor="center")
        tree.heading("diff", text="Diff (Farbe)")
        tree.column("diff", width=110, anchor="center")

        strategy_by_field = (
            {row["field"]: row for row in with_strategy.comparison} if with_strategy else {}
        )
        for row in identity_only.comparison:
            values = [row["label"], f"{row['observed']:.1f}", f"{row['expected']:.1f}"]
            if with_strategy:
                srow = strategy_by_field.get(row["field"])
                values.append(f"{srow['expected']:.1f}" if srow else "–")
            sign = "+" if row["diff"] >= 0 else ""
            pct = f" ({sign}{row['diff_pct']:.0f} %)" if row["diff_pct"] is not None else ""
            values.append(f"{sign}{row['diff']:.1f}{pct}")
            tree.insert("", "end", values=tuple(values))
        tree.pack(fill="both", expand=True, pady=(4, 8))

        if identity_only.unclassified_cards:
            preview = ", ".join(identity_only.unclassified_cards[:8])
            more = (
                f" (+{len(identity_only.unclassified_cards) - 8} weitere)"
                if len(identity_only.unclassified_cards) > 8 else ""
            )
            ttk.Label(
                tab,
                text=(
                    f"{len(identity_only.unclassified_cards)} Karte(n) nicht klassifizierbar "
                    f"(weder in der 8.445-Karten-Referenzdatenbank noch mit Rohdaten übergeben): "
                    f"{preview}{more}"
                ),
                wraplength=1050,
            ).pack(anchor="w", pady=(4, 0))

        ttk.Label(
            tab,
            text=(
                "Referenz: App/archetype_profile, aus 1.585 echten EDHREC-Average-Deck-Profilen "
                "(32 Farbidentitäten × 115 Strategie-Tags). \"beobachtet\" = reale Decks dieser "
                "genauen Identität+Tag-Kombination; \"überlagert\" = Farbidentitäts-Basis + "
                "tag-typische Abweichung, da keine exakte reale Kombination im Sample vorlag."
            ),
            wraplength=1050,
        ).pack(anchor="w", pady=(8, 0))


class MainPage(ttk.Frame):
    def __init__(self, parent, app: GoldfishApp):
        super().__init__(parent)
        self.app = app
        self.last_result_dir = None
        self.last_zip = None
        self.current_card = None

        header = ttk.Frame(self, padding=8)
        header.pack(fill="x")
        ttk.Button(header, text="⌂ Home", command=app.show_home).pack(side="left")
        ttk.Label(header, text="Commander Goldfish v4.7.0 — Deck", font=("Segoe UI", 15, "bold")).pack(side="left", padx=12)
        ttk.Button(header, text="Win Conditions / Setup →", command=app.show_setup).pack(side="left", padx=8)
        ttk.Button(header, text="Projekt speichern …", command=app.save_project).pack(side="left", padx=8)

        settings = ttk.LabelFrame(self, text="Simulation", padding=6)
        settings.pack(fill="x", padx=8, pady=(0, 5))

        ttk.Label(settings, text="Run-Modus").grid(row=0, column=0)
        self.run_mode_combo = ttk.Combobox(
            settings,
            textvariable=app.run_mode_var,
            values=("Diagnostic (200)", "Standard (5,000)", "Deep (20,000)", "Custom"),
            state="readonly",
            width=18,
        )
        self.run_mode_combo.grid(row=0, column=1, padx=(3, 8))
        self.run_mode_combo.bind("<<ComboboxSelected>>", self.apply_run_mode)

        ttk.Label(settings, text="Runs").grid(row=0, column=2)
        self.runs_spin = ttk.Spinbox(settings, from_=10, to=1000000, width=9, textvariable=app.runs_var)
        self.runs_spin.grid(row=0, column=3, padx=(3, 10))
        ttk.Label(settings, text="Turns").grid(row=0, column=4)
        ttk.Spinbox(settings, from_=3, to=30, width=5, textvariable=app.turns_var).grid(row=0, column=5, padx=(3, 10))
        ttk.Label(settings, text="Seed").grid(row=0, column=6)
        ttk.Spinbox(settings, from_=0, to=999999, width=7, textvariable=app.seed_var).grid(row=0, column=7, padx=(3, 10))
        ttk.Label(settings, text="Opponent").grid(row=0, column=8)
        ttk.Combobox(
            settings, textvariable=app.opponent_var,
            values=sorted(engine.OPPONENT_PROFILES),
            state="readonly", width=11,
        ).grid(row=0, column=9, padx=(3, 10))
        ttk.Label(settings, text="Voltron-Ziel").grid(row=0, column=10)
        ttk.Combobox(
            settings, textvariable=app.voltron_target_var,
            values=("Aus", "Gegner 0", "Gegner 1", "Gegner 2"),
            state="readonly", width=10,
        ).grid(row=0, column=11, padx=(3, 14))
        # v4.64.0: "Gegnerprofil" - bis zu vier individuelle Gegner (Farbe +
        # Strategie, je mit "?" für zufällig), siehe AdvancedOpponentDialog.
        # Aktiviert überschreibt die einfache "Opponent"-Combobox oben für
        # diesen Lauf (siehe run_simulation/_simulation_worker).
        ttk.Button(
            settings, text="Gegnerprofil …",
            command=lambda: AdvancedOpponentDialog(app),
        ).grid(row=0, column=12, padx=(3, 6))
        self.advanced_opponent_status = ttk.Label(settings, text="")
        self.advanced_opponent_status.grid(row=0, column=13, padx=(3, 10), sticky="w")
        self.refresh_advanced_opponent_status()

        tag_frame = ttk.Frame(settings)
        tag_frame.grid(row=1, column=0, columnspan=14, sticky="w", pady=(5, 0))
        ttk.Label(tag_frame, text="Strategy:").pack(side="left")
        for tag in engine.STRATEGY_TAGS:
            ttk.Checkbutton(
                tag_frame, text=tag, variable=app.tag_vars[tag],
                command=self.refresh_strategy_info,
            ).pack(side="left", padx=3)
        self.strategy_info = ttk.Label(
            settings, text="", wraplength=1280, justify="left",
        )
        self.strategy_info.grid(row=2, column=0, columnspan=10, sticky="w", pady=(4, 0))

        action = ttk.Frame(self, padding=(8, 3))
        action.pack(fill="x")
        self.start_btn = tk.Button(
            action, text="START FISHING",
            command=app.run_simulation,
            bg="#c62828", fg="white",
            activebackground="#a71919", activeforeground="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat", padx=20, pady=7,
        )
        self.start_btn.pack(side="left")
        self.progress = ttk.Progressbar(action, mode="determinate", maximum=100, length=360)
        self.progress.pack(side="left", padx=12)
        self.status = ttk.Label(action, text="", wraplength=650)
        self.status.pack(side="left", padx=5)
        self.result_btn = ttk.Button(action, text="Ergebnisordner öffnen", command=self.open_result, state="disabled")
        self.result_btn.pack(side="right")
        self.analysis_btn = ttk.Button(action, text="Auswertung", command=self.open_analysis, state="disabled")
        self.analysis_btn.pack(side="right", padx=(0, 6))

        commander_bar = ttk.LabelFrame(self, text="Commander", padding=(8, 5))
        commander_bar.pack(fill="x", padx=8, pady=(0, 5))
        ttk.Label(
            commander_bar,
            text="Legale Commander-Auswahl für die Farbidentität des geladenen Decks:"
        ).pack(side="left")
        self.commander_var = tk.StringVar(value="")
        self.commander_combo = ttk.Combobox(
            commander_bar,
            textvariable=self.commander_var,
            state="readonly",
            width=58,
        )
        self.commander_combo.pack(side="left", padx=8)
        self.commander_combo.bind("<<ComboboxSelected>>", self.commander_selected)
        self.commander_hint = ttk.Label(
            commander_bar,
            text="Kein Doppelklick-Commanderwechsel mehr."
        )
        self.commander_hint.pack(side="left", padx=6)
        self.commander_choice_map = {}

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=5)

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        cols = ("name", "cmd", "qty", "mana", "mv", "type", "roles")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        heads = {
            "name": "Name", "cmd": "Cmd", "qty": "Qty", "mana": "Mana",
            "mv": "MV", "type": "Type", "roles": "Goldfish roles",
        }
        widths = {
            "name": 255, "cmd": 42, "qty": 42, "mana": 122,
            "mv": 44, "type": 230, "roles": 290,
        }
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor="w", stretch=(c in {"name", "type", "roles"}))

        sy = ttk.Scrollbar(left, orient="vertical")
        sx = ttk.Scrollbar(left, orient="horizontal")

        def _tree_yview(*args):
            self.tree.yview(*args)
            self.after_idle(self.refresh_mana_overlays)

        def _tree_xview(*args):
            self.tree.xview(*args)
            self.after_idle(self.refresh_mana_overlays)

        sy.configure(command=_tree_yview)
        sx.configure(command=_tree_xview)

        def _yscroll(first, last):
            sy.set(first, last)
            self.after_idle(self.refresh_mana_overlays)

        def _xscroll(first, last):
            sx.set(first, last)
            self.after_idle(self.refresh_mana_overlays)

        self.tree.configure(yscrollcommand=_yscroll, xscrollcommand=_xscroll)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.card_selected)
        self.tree.bind("<Configure>", lambda _e: self.after_idle(self.refresh_mana_overlays))
        self.tree.bind("<MouseWheel>", lambda _e: self.after_idle(self.refresh_mana_overlays), add="+")
        self.tree.bind("<ButtonRelease-1>", lambda _e: self.after_idle(self.refresh_mana_overlays), add="+")
        self._mana_overlays = []

        self.card_title = ttk.Label(right, text="Karte auswählen", font=("Segoe UI", 13, "bold"))
        self.card_title.pack(anchor="w")
        self.mana_strip = ManaStrip(right, app, height=42)
        self.mana_strip.pack(fill="x", pady=(2, 1))
        self.font_hint = ttk.Frame(right)
        self.font_hint.pack(fill="x", pady=(0, 3))
        if not app.mana_font_available:
            ttk.Label(
                self.font_hint,
                text="Mana-Fallback aktiv. Desktop-Font „Mana“ wurde von Tk nicht erkannt."
            ).pack(side="left")
            ttk.Button(
                self.font_hint, text="Mana Icons öffnen",
                command=lambda: webbrowser.open(engine.MANA_FONT_URL),
            ).pack(side="left", padx=5)
        else:
            ttk.Label(
                self.font_hint,
                text="Mana-Symbole: Andrew Gioia „Mana“ erkannt."
            ).pack(side="left")
        self.image_label = ttk.Label(right, text="Scryfall-Bild (optional mit Pillow)")
        self.image_label.pack(pady=5)
        ttk.Button(right, text="Auf Scryfall öffnen", command=self.open_scryfall).pack(pady=2)
        self.detail = tk.Text(right, wrap="word")
        self.detail.pack(fill="both", expand=True, pady=5)
        self.detail.configure(state="disabled")

    def apply_run_mode(self, _event=None):
        mapping = {
            "Diagnostic (200)": 200,
            "Standard (5,000)": 5000,
            "Deep (20,000)": 20000,
        }
        if self.app.run_mode_var.get() in mapping:
            self.app.runs_var.set(mapping[self.app.run_mode_var.get()])
            self.set_status(
                "Run-Preset gesetzt. Detailed turns.csv wird bei großen Läufen nur als Stichprobe gespeichert; "
                "turn_aggregates.csv enthält die vollständige Turn-Statistik."
            )

    def refresh_all(self):
        self.refresh_commander_selector()
        self.refresh_deck_table()
        self.refresh_strategy_info()

    def refresh_strategy_info(self):
        self.strategy_info.configure(text=engine.strategy_explanation(self.app.selected_tags()))

    def refresh_advanced_opponent_status(self):
        """v4.64.0: kurzer Statustext neben dem 'Gegnerprofil'-Knopf, damit
        auf einen Blick sichtbar ist, ob das erweiterte Mehrgegner-Modell
        gerade die einfache 'Opponent'-Auswahl überschreibt."""
        if self.app.advanced_opponent_enabled_var.get():
            count = max(1, min(4, int(self.app.advanced_opponent_seat_count_var.get() or 1)))
            self.advanced_opponent_status.configure(
                text=f"Erweitert: {count} Gegner (aktiv)"
            )
        else:
            self.advanced_opponent_status.configure(text="Erweitert: aus")

    def refresh_commander_selector(self):
        choices = legal_commander_choices(self.app.deck)
        self.commander_choice_map = {display: set(names) for display, names in choices}
        values = [display for display, _names in choices]
        self.commander_combo.configure(values=values)

        current = frozenset(self.app.commanders)
        selected_display = next(
            (display for display, names in choices if names == current),
            ""
        )
        self.commander_var.set(selected_display)

        if not choices:
            self.commander_hint.configure(
                text="Keine legale Commander-Kombination deckintern gefunden."
            )
        elif selected_display:
            self.commander_hint.configure(text="Auswahl aktiv; Tabelle zeigt ★ nur als Status.")
        else:
            self.commander_hint.configure(text="Bitte Commander auswählen.")

    def commander_selected(self, _event=None):
        display = self.commander_var.get()
        names = self.commander_choice_map.get(display)
        if names:
            self.app.set_commanders(names)

    def _select_tree_item(self, name):
        if name in self.tree.get_children():
            self.tree.selection_set(name)
            self.tree.focus(name)
            self.card_selected()

    def refresh_mana_overlays(self):
        for widget in getattr(self, "_mana_overlays", []):
            try:
                widget.destroy()
            except Exception:
                pass
        self._mana_overlays = []

        if not self.tree.winfo_ismapped():
            return

        for iid in self.tree.get_children():
            bbox = self.tree.bbox(iid, "mana")
            if not bbox:
                continue
            x, y, w, h = bbox
            if w <= 4 or h <= 4:
                continue
            card = self.app.cards.get(iid)
            if not card or not card.mana_cost:
                continue

            cell = ManaCostCanvas(
                self.tree, self.app, card.mana_cost,
                height=max(18, h-2), compact=True,
            )
            cell.place(x=x+1, y=y+1, width=max(2, w-2), height=max(2, h-2))
            cell.bind("<Button-1>", lambda _e, name=iid: self._select_tree_item(name))
            self._mana_overlays.append(cell)

    def refresh_deck_table(self):
        old = self.tree.selection()
        self.tree.delete(*self.tree.get_children())

        counts = {}
        first = {}
        for c in self.app.deck:
            counts[c.name] = counts.get(c.name, 0) + 1
            first.setdefault(c.name, c)

        for name in sorted(first):
            c = first[name]
            self.tree.insert(
                "", "end", iid=name,
                values=(
                    name,
                    "★" if name in self.app.commanders else "",
                    counts[name],
                    "",  # Mana is drawn as real Mana-font icons over this cell.
                    c.mana_value,
                    c.type_line,
                    " | ".join(sorted(c.roles)),
                ),
            )

        if old and old[0] in self.tree.get_children():
            self.tree.selection_set(old[0])

        self.after_idle(self.refresh_mana_overlays)

    def set_status(self, text, error=False):
        self.status.configure(text=text, foreground=("#a00000" if error else ""))

    def begin_simulation(self):
        self.start_btn.configure(state="disabled")
        self.analysis_btn.configure(state="disabled")
        self.progress["value"] = 0
        self.set_status("Simulation läuft …")

    def update_progress(self, done, total):
        self.progress["value"] = 100 * done / max(1, total)
        self.set_status(f"Simulation {done}/{total} · Statistiken werden laufend aggregiert")

    def end_simulation(self):
        self.start_btn.configure(state="normal")
        self.progress["value"] = 100

    def open_result(self):
        if not self.last_result_dir:
            return
        try:
            import os
            os.startfile(str(self.last_result_dir))
        except Exception:
            self.set_status(str(self.last_result_dir))

    def open_analysis(self):
        if not self.last_result_dir:
            return
        try:
            self.app.show_analysis(self.last_result_dir)
        except Exception as exc:
            self.set_status(f"Auswertung konnte nicht geöffnet werden: {exc}", error=True)

    def card_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        name = sel[0]
        c = self.app.cards[name]
        self.current_card = c
        self.card_title.configure(text=c.name)
        self.mana_strip.set_cost(c.mana_cost)

        commander = next((x for x in self.app.deck if x.name in self.app.commanders), None)
        strategy = engine.load_strategy_v41(
            self.app.strategy_file,
            commander,
            archetypes=self.app.selected_tags(),
            opponent_profile=self.app.opponent_var.get(),
            value_model=engine.ValueModel.load(self.app.value_model_file),
            scenarios=self.app.scenarios,
        )
        text = (
            f"{c.name}\nMana Cost {mana_display_text(c.mana_cost)}\nMana Value {c.mana_value}\n{c.type_line}\n\n"
            f"{c.oracle_text}\n\n────────────────────────────\n"
            f"{engine.interpretation_text(c, strategy)}\n\n"
            f"{engine.semantic_card_summary(c)}"
        )
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

        if name in self.app.image_cache:
            self.show_cached_image(name)
        else:
            self.image_label.configure(text="Lade Kartenbild …", image="")
            threading.Thread(target=self._image_worker, args=(c,), daemon=True).start()

    def _image_worker(self, c):
        """
        Load card data/images with stdlib urllib only.

        Pillow path:
            Scryfall normal JPEG -> PIL -> thumbnail.

        No-Pillow path:
            Scryfall PNG -> raw bytes -> Tk PhotoImage on the main thread.
        """
        try:
            import urllib.error
            import urllib.parse
            import urllib.request

            headers = {
                "User-Agent": "CommanderGoldfishSimulator/4.7.0 (personal deck analysis)",
                "Accept": "application/json",
            }

            def get_json(url, timeout=15):
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))

            data = None
            errors = []

            if c.set_code and c.collector_number:
                api = (
                    "https://api.scryfall.com/cards/"
                    + urllib.parse.quote(str(c.set_code).lower(), safe="")
                    + "/"
                    + urllib.parse.quote(str(c.collector_number), safe="")
                )
                try:
                    data = get_json(api)
                except urllib.error.HTTPError as exc:
                    errors.append(f"printing lookup HTTP {exc.code}")
                except Exception as exc:
                    errors.append(f"printing lookup: {exc}")

            if data is None:
                for param in ("exact", "fuzzy"):
                    url = (
                        "https://api.scryfall.com/cards/named?"
                        + urllib.parse.urlencode({param: c.name})
                    )
                    try:
                        data = get_json(url)
                        break
                    except urllib.error.HTTPError as exc:
                        errors.append(f"named {param} HTTP {exc.code}")
                    except Exception as exc:
                        errors.append(f"named {param}: {exc}")

            if data is None:
                raise RuntimeError("; ".join(errors) or "Scryfall card lookup failed")

            # Pillow can use the smaller JPEG. Tk's native fallback wants PNG.
            image_key = "normal" if PIL_AVAILABLE else "png"
            url = (data.get("image_uris") or {}).get(image_key)
            if not url and data.get("card_faces"):
                for face in data["card_faces"]:
                    url = (face.get("image_uris") or {}).get(image_key)
                    if url:
                        break

            # Last fallback if a particular printing has no requested size.
            if not url:
                fallback_key = "png" if image_key == "normal" else "normal"
                url = (data.get("image_uris") or {}).get(fallback_key)
                if not url and data.get("card_faces"):
                    for face in data["card_faces"]:
                        url = (face.get("image_uris") or {}).get(fallback_key)
                        if url:
                            break

            if not url:
                raise RuntimeError("Scryfall liefert für diese Karte kein Kartenbild.")

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CommanderGoldfishSimulator/4.7.0"},
            )
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read()

            if PIL_AVAILABLE:
                img = Image.open(BytesIO(raw))
                img.thumbnail((285, 400))
                self.app.q.put(("image_done", c.name, img))
            else:
                self.app.q.put(("image_png_done", c.name, raw))

        except Exception as exc:
            self.app.q.put(("image_error", c.name, str(exc)))

    def show_cached_image(self, name):
        if not self.current_card or self.current_card.name != name:
            return
        cached = self.app.image_cache.get(name)
        if cached is None:
            return

        if isinstance(cached, tk.PhotoImage):
            self.app.current_photo = cached
        elif PIL_AVAILABLE:
            self.app.current_photo = ImageTk.PhotoImage(cached)
        else:
            return
        self.image_label.configure(image=self.app.current_photo, text="")

    def show_image_error(self, name, err):
        if self.current_card and self.current_card.name == name:
            self.image_label.configure(text=f"Bild nicht geladen: {err}", image="")

    def open_scryfall(self):
        if not self.current_card:
            return
        webbrowser.open(
            "https://scryfall.com/search?q=%21%22"
            + urllib.parse.quote(self.current_card.name)
            + "%22"
        )


class ScenarioPage(ttk.Frame):
    ZONES = {
        "library": "Library",
        "hand": "Hand",
        "battlefield": "Board",
        "graveyard": "Graveyard",
        "exile": "Exile",
        "command_zone": "Command Zone",
    }
    READY_LABELS = {
        "ignore": "Ignorieren",
        "ready": "Ready / nicht Summoning Sick",
        "sick": "Summoning Sick",
    }
    READY_VALUES = {v: k for k, v in READY_LABELS.items()}

    def __init__(self, parent, app: GoldfishApp):
        super().__init__(parent)
        self.app = app
        self.scenarios = []
        self.current_index = None
        self.current_req = None
        self.current_pkg_id = None
        self.loading = False

        self.name_var = tk.StringVar()
        self.kind_var = tk.StringVar(value="Setup")
        self.enabled_var = tk.BooleanVar(value=True)
        self.steer_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="")

        self.mana_vars = {k: tk.IntVar(value=0) for k in ("total", "W", "U", "B", "R", "G", "C")}
        self.th_vars = {k: tk.IntVar(value=0) for k in ("life", "lands", "food", "treasure", "clues")}

        self.req_zone_vars = {z: tk.BooleanVar(value=False) for z in self.ZONES}
        self.req_count_var = tk.IntVar(value=1)
        self.req_ready_var = tk.StringVar(value=self.READY_LABELS["ignore"])
        self.req_untapped_var = tk.BooleanVar(value=False)

        self.pkg_name_var = tk.StringVar(value="Package")
        self.pkg_min_var = tk.IntVar(value=1)
        self.pkg_zone_vars = {z: tk.BooleanVar(value=False) for z in self.ZONES}
        self.pkg_ready_var = tk.StringVar(value=self.READY_LABELS["ignore"])
        self.pkg_untapped_var = tk.BooleanVar(value=False)

        self._build()

    def _build(self):
        header = ttk.Frame(self, padding=8)
        header.pack(fill="x")
        ttk.Button(header, text="← Zurück zum Deck", command=self.back).pack(side="left")
        ttk.Button(header, text="⌂ Home", command=self.home).pack(side="left", padx=5)
        ttk.Label(header, text="Win Conditions / Setup", font=("Segoe UI", 15, "bold")).pack(side="left", padx=12)
        ttk.Button(header, text="Scenario JSON laden …", command=self.app.load_scenarios_into_ready_deck).pack(side="right")
        ttk.Button(header, text="Scenario JSON speichern …", command=self.app.save_scenarios).pack(side="right", padx=5)

        meta = ttk.LabelFrame(self, text="Aktuelles Szenario", padding=6)
        meta.pack(fill="x", padx=8, pady=(0, 5))
        ttk.Label(meta, text="Name").grid(row=0, column=0)
        ttk.Entry(meta, textvariable=self.name_var, width=34).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(meta, text="Typ").grid(row=0, column=2, padx=(8, 0))
        ttk.Combobox(meta, textvariable=self.kind_var, values=engine.SCENARIO_KINDS, state="readonly", width=16).grid(row=0, column=3, padx=4)
        ttk.Checkbutton(meta, text="Aktiv", variable=self.enabled_var).grid(row=0, column=4, padx=5)
        ttk.Checkbutton(meta, text="Auf Setup hin steuern", variable=self.steer_var).grid(row=0, column=5, padx=5)
        ttk.Button(meta, text="Änderungen übernehmen", command=self.commit_current).grid(row=0, column=6, padx=8)
        meta.columnconfigure(1, weight=1)

        r = 1
        ttk.Label(meta, text="Mana:").grid(row=r, column=0, sticky="w", pady=(6, 0))
        mana_frame = ttk.Frame(meta)
        mana_frame.grid(row=r, column=1, columnspan=6, sticky="w", pady=(6, 0))
        for k in ("total", "W", "U", "B", "R", "G", "C"):
            if k == "total":
                ttk.Label(mana_frame, text="Total").pack(side="left", padx=(5, 1))
            else:
                ManaPip(mana_frame, self.app, k, size=22).pack(side="left", padx=(5, 1))
            ttk.Spinbox(mana_frame, from_=0, to=30, width=4, textvariable=self.mana_vars[k]).pack(side="left")

        r = 2
        ttk.Label(meta, text="Minimum:").grid(row=r, column=0, sticky="w", pady=(5, 0))
        th = ttk.Frame(meta)
        th.grid(row=r, column=1, columnspan=6, sticky="w", pady=(5, 0))
        for k, label in (("life", "Life"), ("lands", "Lands"), ("food", "Food"), ("treasure", "Treasure"), ("clues", "Clues")):
            ttk.Label(th, text=label).pack(side="left", padx=(5, 1))
            ttk.Spinbox(th, from_=0, to=999, width=5, textvariable=self.th_vars[k]).pack(side="left")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=4)

        # Left: scenarios.
        left = ttk.LabelFrame(body, text="Szenarien", padding=5)
        body.add(left, weight=1)
        self.sc_tree = ttk.Treeview(left, columns=("name", "kind"), show="headings", selectmode="browse")
        self.sc_tree.heading("name", text="Name")
        self.sc_tree.heading("kind", text="Typ")
        self.sc_tree.column("name", width=230)
        self.sc_tree.column("kind", width=100)
        self.sc_tree.pack(fill="both", expand=True)
        self.sc_tree.bind("<<TreeviewSelect>>", self.on_scenario_select)
        sb = ttk.Frame(left)
        sb.pack(fill="x", pady=4)
        ttk.Button(sb, text="+ Neu", command=self.new_scenario).pack(side="left")
        ttk.Button(sb, text="Duplizieren", command=self.duplicate_scenario).pack(side="left", padx=3)
        ttk.Button(sb, text="Löschen", command=self.delete_scenario).pack(side="left", padx=3)

        # Middle: deck cards.
        mid = ttk.LabelFrame(body, text="Deckkarten", padding=5)
        body.add(mid, weight=2)
        self.deck_tree = ttk.Treeview(mid, columns=("name", "mv", "type"), show="headings", selectmode="extended")
        for c, h, w in (("name", "Name", 260), ("mv", "MV", 45), ("type", "Type", 230)):
            self.deck_tree.heading(c, text=h)
            self.deck_tree.column(c, width=w)
        dsy = ttk.Scrollbar(mid, orient="vertical", command=self.deck_tree.yview)
        self.deck_tree.configure(yscrollcommand=dsy.set)
        self.deck_tree.grid(row=0, column=0, sticky="nsew")
        dsy.grid(row=0, column=1, sticky="ns")
        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)
        db = ttk.Frame(mid)
        db.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(db, text="→ Pflichtkarte", command=self.add_single).pack(fill="x")
        ttk.Button(db, text="→ Neues Paket aus Auswahl", command=self.new_package_from_selection).pack(fill="x", pady=3)
        ttk.Button(db, text="→ Zum markierten Paket", command=self.add_to_package).pack(fill="x")

        # Right: setup components.
        right = ttk.LabelFrame(body, text="Setup-Bausteine", padding=5)
        body.add(right, weight=4)
        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)
        singles = ttk.Frame(nb, padding=5)
        packages = ttk.Frame(nb, padding=5)
        notes = ttk.Frame(nb, padding=5)
        nb.add(singles, text="Pflichtkarten")
        nb.add(packages, text="Kartenpakete / N-of-M")
        nb.add(notes, text="Beschreibung")
        self._build_singles(singles)
        self._build_packages(packages)
        self.description = tk.Text(notes, wrap="word")
        self.description.pack(fill="both", expand=True)

        status = ttk.Frame(self, padding=(8, 3))
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.status_var, wraplength=1200).pack(side="left")
        ttk.Label(
            status,
            text="Einzelkarten = AND · Zonen = OR · Paket = mindestens N von M · Pakete = AND",
        ).pack(side="right")

    def _build_singles(self, p):
        self.req_tree = ttk.Treeview(p, columns=("card", "zones", "ready", "tap"), show="headings", selectmode="browse", height=11)
        for c, h, w in (("card", "Karte", 260), ("zones", "Zonen", 250), ("ready", "Summoning", 170), ("tap", "Untapped", 70)):
            self.req_tree.heading(c, text=h)
            self.req_tree.column(c, width=w)
        self.req_tree.grid(row=0, column=0, columnspan=8, sticky="nsew")
        self.req_tree.bind("<<TreeviewSelect>>", self.req_selected)
        p.rowconfigure(0, weight=1)
        p.columnconfigure(0, weight=1)

        zones = ttk.LabelFrame(p, text="Erlaubte Zonen (OR)", padding=4)
        zones.grid(row=1, column=0, columnspan=8, sticky="ew", pady=5)
        for i, (z, label) in enumerate(self.ZONES.items()):
            ttk.Checkbutton(zones, text=label, variable=self.req_zone_vars[z]).grid(row=0, column=i, padx=4)

        edit = ttk.Frame(p)
        edit.grid(row=2, column=0, columnspan=8, sticky="ew")
        ttk.Label(edit, text="Count").pack(side="left")
        ttk.Spinbox(edit, from_=1, to=20, width=4, textvariable=self.req_count_var).pack(side="left", padx=(2, 8))
        ttk.Label(edit, text="Summoning").pack(side="left")
        ttk.Combobox(edit, textvariable=self.req_ready_var, values=list(self.READY_VALUES), state="readonly", width=29).pack(side="left", padx=3)
        ttk.Checkbutton(edit, text="Muss untapped sein", variable=self.req_untapped_var).pack(side="left", padx=6)
        ttk.Button(edit, text="Übernehmen", command=self.apply_single).pack(side="right")
        ttk.Button(edit, text="Entfernen", command=self.remove_single).pack(side="right", padx=4)

    def _build_packages(self, p):
        self.pkg_tree = ttk.Treeview(p, columns=("name", "need", "zones", "members"), show="headings", selectmode="browse", height=7)
        for c, h, w in (("name", "Paket", 220), ("need", "N-of-M", 80), ("zones", "Zonen", 220), ("members", "Karten", 55)):
            self.pkg_tree.heading(c, text=h)
            self.pkg_tree.column(c, width=w)
        self.pkg_tree.grid(row=0, column=0, columnspan=8, sticky="nsew")
        self.pkg_tree.bind("<<TreeviewSelect>>", self.pkg_selected)

        b = ttk.Frame(p)
        b.grid(row=1, column=0, columnspan=8, sticky="ew", pady=4)
        ttk.Button(b, text="+ Leeres Paket", command=self.new_empty_package).pack(side="left")
        ttk.Button(b, text="Duplizieren", command=self.duplicate_package).pack(side="left", padx=3)
        ttk.Button(b, text="Löschen", command=self.delete_package).pack(side="left", padx=3)

        config = ttk.LabelFrame(p, text="Paket-Einstellungen", padding=5)
        config.grid(row=2, column=0, columnspan=8, sticky="ew")
        ttk.Label(config, text="Name").grid(row=0, column=0)
        ttk.Entry(config, textvariable=self.pkg_name_var, width=30).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Label(config, text="Mindestens").grid(row=0, column=2, padx=(8, 0))
        ttk.Spinbox(config, from_=1, to=99, width=5, textvariable=self.pkg_min_var).grid(row=0, column=3)
        ttk.Label(config, text="verschiedene Karten").grid(row=0, column=4, sticky="w")
        config.columnconfigure(1, weight=1)

        zones = ttk.Frame(config)
        zones.grid(row=1, column=0, columnspan=6, sticky="w", pady=4)
        ttk.Label(zones, text="Zonen (OR):").pack(side="left")
        for z, label in self.ZONES.items():
            ttk.Checkbutton(zones, text=label, variable=self.pkg_zone_vars[z]).pack(side="left", padx=3)

        row = ttk.Frame(config)
        row.grid(row=2, column=0, columnspan=6, sticky="ew")
        ttk.Label(row, text="Summoning").pack(side="left")
        ttk.Combobox(row, textvariable=self.pkg_ready_var, values=list(self.READY_VALUES), state="readonly", width=29).pack(side="left", padx=3)
        ttk.Checkbutton(row, text="Muss untapped sein", variable=self.pkg_untapped_var).pack(side="left", padx=5)
        ttk.Button(row, text="Paket übernehmen", command=self.apply_package).pack(side="right")

        members = ttk.LabelFrame(p, text="Mitglieder des markierten Pakets", padding=4)
        members.grid(row=3, column=0, columnspan=8, sticky="nsew", pady=5)
        self.member_tree = ttk.Treeview(members, columns=("name", "mv", "type"), show="headings", selectmode="extended", height=8)
        for c, h, w in (("name", "Karte", 260), ("mv", "MV", 45), ("type", "Type", 260)):
            self.member_tree.heading(c, text=h)
            self.member_tree.column(c, width=w)
        self.member_tree.grid(row=0, column=0, sticky="nsew")
        members.rowconfigure(0, weight=1)
        members.columnconfigure(0, weight=1)
        mb = ttk.Frame(members)
        mb.grid(row=1, column=0, sticky="ew", pady=3)
        ttk.Button(mb, text="Deckauswahl hinzufügen", command=self.add_to_package).pack(side="left")
        ttk.Button(mb, text="Aus Paket entfernen", command=self.remove_from_package).pack(side="left", padx=4)

        p.rowconfigure(3, weight=1)
        p.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------

    def set_status(self, text, error=False):
        self.status_var.set(text)

    def load_from_app(self):
        self.scenarios = [
            engine.normalize_scenario(x, i)
            for i, x in enumerate(json.loads(json.dumps(self.app.scenarios)))
        ]
        if not self.scenarios:
            self.scenarios = [engine.new_scenario("Scenario 1")]
        self.populate_deck()
        self.refresh_scenarios(select=0)
        self.set_status("Setup-Seite bereit.")

    def populate_deck(self):
        self.deck_tree.delete(*self.deck_tree.get_children())
        for name in sorted(self.app.cards):
            c = self.app.cards[name]
            self.deck_tree.insert("", "end", iid=name, values=(name, c.mana_value, c.type_line))

    def current(self):
        if self.current_index is None:
            return None
        if 0 <= self.current_index < len(self.scenarios):
            return self.scenarios[self.current_index]
        return None

    def refresh_scenarios(self, select=None):
        self.loading = True
        self.sc_tree.delete(*self.sc_tree.get_children())
        for i, sc in enumerate(self.scenarios):
            self.sc_tree.insert("", "end", iid=str(i), values=(sc["name"], sc["kind"]))
        self.loading = False
        if select is not None and self.scenarios:
            select = max(0, min(select, len(self.scenarios)-1))
            self.sc_tree.selection_set(str(select))
            self.load_scenario(select)

    def on_scenario_select(self, _e=None):
        if self.loading:
            return
        sel = self.sc_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if self.current_index is not None and idx != self.current_index:
            self.commit_current()
        self.load_scenario(idx)

    def load_scenario(self, idx):
        self.loading = True
        self.current_index = idx
        sc = self.scenarios[idx]
        self.name_var.set(sc["name"])
        self.kind_var.set(sc["kind"])
        self.enabled_var.set(sc.get("enabled", True))
        self.steer_var.set(sc.get("steer", True))
        for k, v in self.mana_vars.items():
            v.set(sc.get("mana", {}).get(k, 0))
        for k, v in self.th_vars.items():
            v.set(sc.get("thresholds", {}).get(k, 0))
        self.description.delete("1.0", "end")
        self.description.insert("1.0", sc.get("description", ""))
        self.refresh_requirements()
        self.refresh_packages()
        self.clear_single_editor()
        self.clear_pkg_editor()
        self.loading = False

    def commit_current(self):
        sc = self.current()
        if sc is None or self.loading:
            return
        self.apply_package(silent=True)
        sc["name"] = self.name_var.get().strip() or sc["name"]
        sc["kind"] = self.kind_var.get()
        sc["enabled"] = bool(self.enabled_var.get())
        sc["steer"] = bool(self.steer_var.get())
        sc["mana"] = {k: max(0, int(v.get() or 0)) for k, v in self.mana_vars.items()}
        sc["thresholds"] = {k: max(0, int(v.get() or 0)) for k, v in self.th_vars.items()}
        sc["description"] = self.description.get("1.0", "end").strip()
        self.scenarios[self.current_index] = engine.normalize_scenario(sc, self.current_index)
        self.app.scenarios = json.loads(json.dumps(self.scenarios))
        iid = str(self.current_index)
        if iid in self.sc_tree.get_children():
            cur = self.scenarios[self.current_index]
            self.sc_tree.item(iid, values=(cur["name"], cur["kind"]))

    def new_scenario(self):
        if self.current_index is not None:
            self.commit_current()
        self.scenarios.append(engine.new_scenario(f"Scenario {len(self.scenarios)+1}"))
        self.refresh_scenarios(select=len(self.scenarios)-1)

    def duplicate_scenario(self):
        sc = self.current()
        if sc is None:
            return
        self.commit_current()
        clone = json.loads(json.dumps(sc))
        clone["name"] += " (copy)"
        clone["id"] += "-copy"
        self.scenarios.append(engine.normalize_scenario(clone, len(self.scenarios)))
        self.refresh_scenarios(select=len(self.scenarios)-1)

    def delete_scenario(self):
        if self.current_index is None:
            return
        del self.scenarios[self.current_index]
        if not self.scenarios:
            self.scenarios = [engine.new_scenario("Scenario 1")]
        self.current_index = None
        self.refresh_scenarios(select=0)

    # Singles.
    def add_single(self):
        sc = self.current()
        if sc is None:
            return
        existing = {r["card"] for r in sc.get("requirements", [])}
        for name in self.deck_tree.selection():
            if name not in existing:
                sc.setdefault("requirements", []).append({
                    "card": name,
                    "count": 1,
                    "zones": ["battlefield"] if name in self.app.commanders else ["library"],
                    "ready": "ignore",
                    "untapped": False,
                })
                existing.add(name)
        self.refresh_requirements()

    def refresh_requirements(self):
        self.req_tree.delete(*self.req_tree.get_children())
        sc = self.current()
        if not sc:
            return
        for r in sc.get("requirements", []):
            self.req_tree.insert(
                "", "end", iid=r["card"],
                values=(
                    r["card"],
                    " / ".join(self.ZONES.get(z, z) for z in r.get("zones", [])),
                    self.READY_LABELS.get(r.get("ready", "ignore"), r.get("ready", "")),
                    "✓" if r.get("untapped") else "",
                ),
            )

    def clear_single_editor(self):
        self.current_req = None
        self.req_count_var.set(1)
        self.req_ready_var.set(self.READY_LABELS["ignore"])
        self.req_untapped_var.set(False)
        for v in self.req_zone_vars.values():
            v.set(False)

    def req_selected(self, _e=None):
        sc = self.current()
        sel = self.req_tree.selection()
        if not sc or not sel:
            return
        name = sel[0]
        r = next((x for x in sc.get("requirements", []) if x["card"] == name), None)
        if not r:
            return
        self.current_req = name
        self.req_count_var.set(r.get("count", 1))
        self.req_ready_var.set(self.READY_LABELS.get(r.get("ready", "ignore"), self.READY_LABELS["ignore"]))
        self.req_untapped_var.set(bool(r.get("untapped", False)))
        zones = set(r.get("zones", []))
        for z, v in self.req_zone_vars.items():
            v.set(z in zones)

    def apply_single(self):
        sc = self.current()
        if not sc or not self.current_req:
            return
        r = next((x for x in sc.get("requirements", []) if x["card"] == self.current_req), None)
        if not r:
            return
        ready = self.READY_VALUES.get(self.req_ready_var.get(), "ignore")
        untapped = bool(self.req_untapped_var.get())
        zones = [z for z, v in self.req_zone_vars.items() if v.get()]
        if ready != "ignore" or untapped:
            zones = ["battlefield"]
        if not zones:
            zones = ["library"]
        r.update({
            "count": max(1, int(self.req_count_var.get() or 1)),
            "zones": zones,
            "ready": ready,
            "untapped": untapped,
        })
        self.scenarios[self.current_index] = engine.normalize_scenario(sc, self.current_index)
        self.refresh_requirements()

    def remove_single(self):
        sc = self.current()
        if not sc or not self.current_req:
            return
        sc["requirements"] = [r for r in sc.get("requirements", []) if r["card"] != self.current_req]
        self.clear_single_editor()
        self.refresh_requirements()

    # Packages.
    def current_pkg(self):
        sc = self.current()
        if not sc or not self.current_pkg_id:
            return None
        return next((p for p in sc.get("packages", []) if p["id"] == self.current_pkg_id), None)

    def refresh_packages(self):
        self.pkg_tree.delete(*self.pkg_tree.get_children())
        sc = self.current()
        if not sc:
            return
        for p in sc.get("packages", []):
            self.pkg_tree.insert(
                "", "end", iid=p["id"],
                values=(
                    p["name"],
                    f'≥ {p.get("min_required",1)} / {len(p.get("members",[]))}',
                    " / ".join(self.ZONES.get(z, z) for z in p.get("zones", [])),
                    len(p.get("members", [])),
                ),
            )

    def clear_pkg_editor(self):
        self.current_pkg_id = None
        self.pkg_name_var.set("Package")
        self.pkg_min_var.set(1)
        self.pkg_ready_var.set(self.READY_LABELS["ignore"])
        self.pkg_untapped_var.set(False)
        for v in self.pkg_zone_vars.values():
            v.set(False)
        self.member_tree.delete(*self.member_tree.get_children())

    def pkg_selected(self, _e=None):
        sel = self.pkg_tree.selection()
        sc = self.current()
        if not sel or not sc:
            return
        pid = sel[0]
        p = next((x for x in sc.get("packages", []) if x["id"] == pid), None)
        if not p:
            return
        self.current_pkg_id = pid
        self.pkg_name_var.set(p.get("name", "Package"))
        self.pkg_min_var.set(p.get("min_required", 1))
        self.pkg_ready_var.set(self.READY_LABELS.get(p.get("ready", "ignore"), self.READY_LABELS["ignore"]))
        self.pkg_untapped_var.set(bool(p.get("untapped", False)))
        zones = set(p.get("zones", []))
        for z, v in self.pkg_zone_vars.items():
            v.set(z in zones)
        self.refresh_members()

    def refresh_members(self):
        self.member_tree.delete(*self.member_tree.get_children())
        p = self.current_pkg()
        if not p:
            return
        for m in p.get("members", []):
            name = m["card"]
            c = self.app.cards.get(name)
            self.member_tree.insert(
                "", "end", iid=name,
                values=(name, "" if not c else c.mana_value, "" if not c else c.type_line),
            )

    def new_empty_package(self):
        sc = self.current()
        if not sc:
            return
        p = engine.new_card_package(f"Package {len(sc.get('packages',[]))+1}")
        sc.setdefault("packages", []).append(p)
        self.refresh_packages()
        self.pkg_tree.selection_set(p["id"])
        self.pkg_selected()

    def new_package_from_selection(self):
        sc = self.current()
        if not sc:
            return
        p = engine.new_card_package(f"Package {len(sc.get('packages',[]))+1}")
        p["members"] = [{"card": x} for x in self.deck_tree.selection()]
        p = engine.normalize_card_package(p)
        sc.setdefault("packages", []).append(p)
        self.refresh_packages()
        self.pkg_tree.selection_set(p["id"])
        self.pkg_selected()

    def add_to_package(self):
        p = self.current_pkg()
        sc = self.current()
        if not p or not sc:
            self.set_status("Bitte zuerst ein Kartenpaket markieren.", error=True)
            return
        existing = {m["card"] for m in p.get("members", [])}
        for name in self.deck_tree.selection():
            if name not in existing:
                p.setdefault("members", []).append({"card": name})
                existing.add(name)
        p2 = engine.normalize_card_package(p)
        sc["packages"] = [p2 if x["id"] == p["id"] else x for x in sc.get("packages", [])]
        self.current_pkg_id = p2["id"]
        self.refresh_packages()
        self.pkg_tree.selection_set(self.current_pkg_id)
        self.refresh_members()

    def remove_from_package(self):
        p = self.current_pkg()
        sc = self.current()
        if not p or not sc:
            return
        remove = set(self.member_tree.selection())
        p["members"] = [m for m in p.get("members", []) if m["card"] not in remove]
        p2 = engine.normalize_card_package(p)
        sc["packages"] = [p2 if x["id"] == p["id"] else x for x in sc.get("packages", [])]
        self.current_pkg_id = p2["id"]
        self.refresh_packages()
        self.pkg_tree.selection_set(self.current_pkg_id)
        self.refresh_members()

    def apply_package(self, silent=False):
        p = self.current_pkg()
        sc = self.current()
        if not p or not sc:
            return
        ready = self.READY_VALUES.get(self.pkg_ready_var.get(), "ignore")
        untapped = bool(self.pkg_untapped_var.get())
        zones = [z for z, v in self.pkg_zone_vars.items() if v.get()]
        if ready != "ignore" or untapped:
            zones = ["battlefield"]
        if not zones:
            zones = ["library"]
        p.update({
            "name": self.pkg_name_var.get().strip() or p["name"],
            "min_required": max(1, int(self.pkg_min_var.get() or 1)),
            "zones": zones,
            "ready": ready,
            "untapped": untapped,
        })
        p2 = engine.normalize_card_package(p)
        sc["packages"] = [p2 if x["id"] == p["id"] else x for x in sc.get("packages", [])]
        self.current_pkg_id = p2["id"]
        self.refresh_packages()
        if self.current_pkg_id in self.pkg_tree.get_children():
            self.pkg_tree.selection_set(self.current_pkg_id)
        self.refresh_members()
        if not silent:
            self.set_status(f'Paket "{p2["name"]}" übernommen.')

    def duplicate_package(self):
        p = self.current_pkg()
        sc = self.current()
        if not p or not sc:
            return
        clone = json.loads(json.dumps(p))
        clone["name"] += " (copy)"
        clone["id"] += "-copy"
        clone = engine.normalize_card_package(clone)
        sc.setdefault("packages", []).append(clone)
        self.refresh_packages()
        self.pkg_tree.selection_set(clone["id"])
        self.pkg_selected()

    def delete_package(self):
        sc = self.current()
        if not sc or not self.current_pkg_id:
            return
        sc["packages"] = [p for p in sc.get("packages", []) if p["id"] != self.current_pkg_id]
        self.clear_pkg_editor()
        self.refresh_packages()

    def back(self):
        self.commit_current()
        self.app.scenarios = json.loads(json.dumps(self.scenarios))
        self.app.show_main()

    def home(self):
        self.commit_current()
        self.app.scenarios = json.loads(json.dumps(self.scenarios))
        self.app.show_home()


def launch_gui():
    app = GoldfishApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
