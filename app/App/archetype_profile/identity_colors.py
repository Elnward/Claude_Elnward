"""Farbidentitaets-Tabelle (die 32 EDHREC-Identitaeten) + eine einfache Erkennung der
Farbidentitaet aus den Manapips einer hochgeladenen Decklist.

Die Tabelle ist 1:1 aus `edhrec_bracket3_database.py` (_RAW_IDENTITIES) uebernommen, damit
die hier erzeugten `identity_slug`-Werte garantiert zu den Schluesseln in
identity_type_summary.json / identity_tag_summary.json / deck_profiles.csv passen.
"""
from __future__ import annotations

COLOR_ORDER = "WUBRG"

# (slug, label, farben, gruppe) -- identisch zu edhrec_bracket3_database.py
_RAW_IDENTITIES: tuple[tuple[str, str, str, str], ...] = (
    ("colorless", "Colorless", "", "colorless"),

    ("mono-white", "Mono-White", "W", "mono"),
    ("mono-blue", "Mono-Blue", "U", "mono"),
    ("mono-black", "Mono-Black", "B", "mono"),
    ("mono-red", "Mono-Red", "R", "mono"),
    ("mono-green", "Mono-Green", "G", "mono"),

    ("azorius", "Azorius", "WU", "two-color"),
    ("dimir", "Dimir", "UB", "two-color"),
    ("rakdos", "Rakdos", "BR", "two-color"),
    ("gruul", "Gruul", "RG", "two-color"),
    ("selesnya", "Selesnya", "GW", "two-color"),
    ("orzhov", "Orzhov", "WB", "two-color"),
    ("izzet", "Izzet", "UR", "two-color"),
    ("golgari", "Golgari", "BG", "two-color"),
    ("boros", "Boros", "RW", "two-color"),
    ("simic", "Simic", "GU", "two-color"),

    ("esper", "Esper", "WUB", "three-color"),
    ("grixis", "Grixis", "UBR", "three-color"),
    ("jund", "Jund", "BRG", "three-color"),
    ("naya", "Naya", "WRG", "three-color"),
    ("bant", "Bant", "WUG", "three-color"),
    ("abzan", "Abzan", "WBG", "three-color"),
    ("jeskai", "Jeskai", "WUR", "three-color"),
    ("sultai", "Sultai", "UBG", "three-color"),
    ("mardu", "Mardu", "WBR", "three-color"),
    ("temur", "Temur", "URG", "three-color"),

    ("yore-tiller", "Yore-Tiller", "WUBR", "four-color"),
    ("glint-eye", "Glint-Eye", "UBRG", "four-color"),
    ("dune-brood", "Dune-Brood", "WBRG", "four-color"),
    ("ink-treader", "Ink-Treader", "WURG", "four-color"),
    ("witch-maw", "Witch-Maw", "WUBG", "four-color"),

    ("five-color", "Five-Color", "WUBRG", "five-color"),
)


def normalize_color_identity(colors: str) -> str:
    present = {c.upper() for c in colors}
    return "".join(c for c in COLOR_ORDER if c in present)


# colors-string (WUBRG-Reihenfolge) -> slug, z.B. "GU" -> "simic"
COLORS_TO_SLUG: dict[str, str] = {
    normalize_color_identity(colors): slug for slug, _label, colors, _group in _RAW_IDENTITIES
}
SLUG_TO_LABEL: dict[str, str] = {slug: label for slug, label, _colors, _group in _RAW_IDENTITIES}
SLUG_TO_GROUP: dict[str, str] = {slug: group for slug, _label, _colors, group in _RAW_IDENTITIES}


def detect_identity_slug(pip_totals: dict[str, float], min_share: float = 0.02) -> str | None:
    """Schaetzt die Farbidentitaet aus aufsummierten Manapips (ueber alle Karten der
    Decklist, gewichtet mit Stueckzahl). Eine Farbe zaehlt als 'in der Identitaet', wenn
    ihr Pip-Anteil an der Gesamtsumme aller farbigen Pips mindestens `min_share` betraegt
    (Default 2 %) -- das filtert einzelne Farbindikatoren/vereinzelte Pips ohne echte
    Nutzung heraus, ohne echte Nebenfarben zu verlieren.

    Wichtiger Hinweis (Praezision v1): das ist eine Naeherung ueber die tatsaechlich im
    Deck gespielten Manakosten, NICHT die formale "Color Identity" (die auch Manasymbole
    in Regeltexten/auf der Rueckseite von Doppelkarten sowie den Commander selbst
    einschliesst). Fuer eine praezise Zuordnung sollte -- wo verfuegbar -- der
    `identity_slug` stattdessen direkt aus der Farbidentitaet des Commanders (bereits an
    anderer Stelle in der App bekannt) uebergeben werden; diese Funktion ist der
    Fallback, wenn nur eine reine Kartenliste vorliegt.
    """
    colored = {c: pip_totals.get(c, 0.0) for c in "WUBRG"}
    total = sum(colored.values())
    if total <= 0:
        return "colorless"
    present = "".join(c for c in COLOR_ORDER if colored[c] / total >= min_share)
    return COLORS_TO_SLUG.get(present)
