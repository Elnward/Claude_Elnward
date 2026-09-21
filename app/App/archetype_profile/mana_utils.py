"""Mana-Cost-Parsing: liefert Farbpip-Vektor (WUBRG, fraktional bei Hybrid) aus dem
Scryfall mana_cost-String. Manavalue (CMC) wird NICHT hieraus neu berechnet, sondern
direkt aus dem von Scryfall gelieferten `cmc`-Feld uebernommen (das ist die offizielle
Regel-Manavalue, u.a. korrekt fuer {X}=0)."""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\{([^}]+)\}")
WUBRG = ("W", "U", "B", "R", "G")


def parse_pips(mana_cost: str) -> dict:
    """Gibt {'W':float,'U':float,'B':float,'R':float,'G':float,'C':float,
    'generic':float,'has_x':bool} zurueck. Hybrid-/Phyrexian-Symbole werden anteilig
    (1/n je beteiligter Farbe) gezaehlt, Phyrexian-Mana (z.B. 'B/P') zaehlt voll als
    die jeweilige Farbe (vereinfachte Annahme: meist mit Mana bezahlt)."""
    pips = {c: 0.0 for c in WUBRG}
    pips["C"] = 0.0
    pips["generic"] = 0.0
    pips["has_x"] = False
    if not isinstance(mana_cost, str) or not mana_cost:
        return pips
    for token in _TOKEN_RE.findall(mana_cost):
        t = token.upper()
        if t.isdigit():
            pips["generic"] += int(t)
        elif t in ("X", "Y", "Z"):
            pips["has_x"] = True
        elif t == "C":
            pips["C"] += 1.0
        elif t == "S":
            pass  # Snow-Mana, selten, ignorieren fuer Farbstatistik
        elif "/" in t:
            parts = [p for p in t.split("/") if p != "P"]
            if not parts:
                continue
            weight = 1.0 / len(parts)
            for p in parts:
                if p in pips:
                    pips[p] += weight
                elif p.isdigit():
                    pips["generic"] += weight * int(p)
        elif t in pips:
            pips[t] += 1.0
    return pips


def dominant_colors(mana_cost: str) -> str:
    """Kurzform der tatsaechlich im Mana-Cost vorkommenden Farben, z.B. 'UB'."""
    pips = parse_pips(mana_cost)
    return "".join(c for c in WUBRG if pips[c] > 0)
