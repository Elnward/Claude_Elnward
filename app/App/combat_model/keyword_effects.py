"""
Farbabhaengiges Keyword-Kampfmodell (v4.82.0, "Runde 4").

Ausgangslage (Nutzer-Feedback zu v4.81.0): Kampf-/Blocker-Keywords wie
Flying, Deathtouch, Reach, Menace, ... waren entweder reine Tags oder hatten
einen FLACHEN, farbunabhaengigen Effekt (Flying = Blockchance x0.35 gegen
JEDEN Gegner). Dieses Engine-Modell simuliert kein echtes Gegner-Board -
aber es kennt seit v4.67-v4.71 die realen Decklisten jeder Farbidentitaet
(1.585 EDHREC-Bracket-3-Average-Decks). Daraus laesst sich fuer jede
Farbidentitaet messen, WIE GUT sie mit einem Keyword umgehen kann (z.B.:
welcher Anteil ihrer Kreaturen hat Flying/Reach und kann damit einen Flieger
blocken?) und - umgekehrt - wie haeufig SIE selbst dieses Keyword auf den
Tisch bringt (wie viel ihres Kampfdrucks fliegt, hat Deathtouch, ...).
Siehe Data/Models/color_keyword_profile.json (abgeleitet von
derive_color_keyword_profile.py in diesem Ordner).

Dieses Modul uebersetzt diese Messwerte in Wahrscheinlichkeiten fuer die
beiden bestehenden, abstrakten Kampffunktionen:

1. Eigene Angriffe (interaction.py::resolve_combat_interaction):
   "Eingeschraenkter-Blocker"-Keywords (Flying, Fear, Intimidate,
   Protection from X, Shadow, Horsemanship, Landwalk) nutzen EINE
   gemeinsame Formel: kann nur ein Anteil s der gegnerischen Kreaturen
   diesen Angreifer blocken, ist die Blockchance mit dem Faktor
       1 - (1 - s)^k
   skaliert - "mindestens einer der k Kreaturen, die realistischerweise zum
   Blocken bereitstehen, ist dazu faehig". k wird NICHT geraten, sondern
   genau so geeicht, dass der bisherige, bereits kalibrierte globale
   Flying-Faktor (0.35) beim ueber ALLE Decks gepoolten Flying/Reach-Anteil
   exakt reproduziert wird (k ~ 1.93) - dieselbe "am alten Mittel
   verankern"-Praxis wie v4.70.0. Gegen einen gemischten Tisch ohne
   Farbinformation (einfache Profile aggro/midrange/control/horde) gilt
   daher weiterhin exakt 0.35; gegen einen Azorius-Sitzplatz (41.8 %
   Flying/Reach-Kreaturen) steigt er auf ~0.65, gegen Gruul (12 %) faellt er
   auf ~0.22.
   Menace skaliert mit der Kreaturdichte der Farbe (braucht zwei Blocker),
   verankert am bisherigen Faktor 0.55. Trample hat KEINEN Block-Faktor mehr,
   sondern verursacht beim Block den realen Ueberschussschaden (Power minus
   typische Toughness der Blockerfarbe; mit Deathtouch reicht 1 Schaden).
   Flanking/Bushido/Rampage senken die eigene Todeschance beim Block.

2. Gegnerischer Kampfdruck (defense.py::absorb_pressure): der fliegende
   Anteil des gegnerischen Drucks ist nur noch von eigenen Fliegern/Reach-
   Kreaturen blockbar (Bodenblocker koennen ihn nicht aufhalten); Menace-
   Angreifer binden zwei Blocker; Deathtouch-/First-Strike-Angreifer toeten
   Blocker haeufiger; Trample-Angreifer druecken Ueberschuss durch. Eigene
   Deathtouch-/Wither-/Infect-Blocker toeten den Angreifer (Attrition, siehe
   engine.record_opponent_attrition), eigene Lifelink-Blocker gewinnen Leben.

Engine-agnostisch (kein `import engine`), wie der Rest von combat_model.
Alle Konstanten: Data/Models/combat_interaction_weights.json -> "keyword_effects".
"""
from __future__ import annotations

import functools
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from .interaction import _WEIGHTS

_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "Data" / "Models"
_COLORS = "WUBRG"
_LAND_TYPE_COLOR = {"plains": "W", "island": "U", "swamp": "B", "mountain": "R", "forest": "G"}
_COLOR_WORD = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"}


def _kw_weights() -> Dict[str, Any]:
    return _WEIGHTS.get("keyword_effects", {"enabled": False})


def _load_profile() -> Optional[Dict[str, Any]]:
    name = _kw_weights().get("profile_file", "color_keyword_profile.json")
    path = _MODELS_DIR / name
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("identities")
    except (OSError, ValueError):
        return None


_PROFILE: Optional[Dict[str, Any]] = _load_profile()


def reload_profile() -> None:
    global _PROFILE
    _PROFILE = _load_profile()
    _k_eff.cache_clear()


def enabled() -> bool:
    return bool(_kw_weights().get("enabled", False)) and bool(_PROFILE) and "ALL" in (_PROFILE or {})


def identity_key(colors: Iterable[str]) -> str:
    up = {str(c).upper() for c in colors}
    key = "".join(c for c in _COLORS if c in up)
    return key or "C"


def identity_row(colors: Optional[Iterable[str]]) -> Dict[str, float]:
    """Messwerte fuer eine Farbidentitaet; None/leer -> 'ALL' (ueber alle
    1.585 Decks gepoolt = neutraler, farbloser Durchschnittsgegner)."""
    prof = _PROFILE or {}
    if colors is None:
        return prof.get("ALL", {})
    return prof.get(identity_key(colors)) or prof.get("ALL", {})


@dataclass
class KeywordCombatContext:
    """Die Farbzeilen der aktuell relevanten Gegner. `colored=False` heisst:
    keine Farbinformation (einfache Profile) -> eine einzige 'ALL'-Zeile."""
    rows: List[Dict[str, float]] = field(default_factory=list)
    seat_colors: List[Set[str]] = field(default_factory=list)
    colored: bool = False

    def mean(self, key: str, default: float = 0.0) -> float:
        vals = [float(r.get(key, default)) for r in self.rows] or [default]
        return sum(vals) / len(vals)


def build_context(seat_colors: Optional[List[Set[str]]] = None) -> Optional[KeywordCombatContext]:
    if not enabled():
        return None
    if seat_colors:
        rows = [identity_row(c) for c in seat_colors]
        return KeywordCombatContext(rows=rows, seat_colors=[set(c) for c in seat_colors], colored=True)
    return KeywordCombatContext(rows=[identity_row(None)], seat_colors=[], colored=False)


def deck_share_with_color(color: str) -> float:
    """Anteil aller Decks, deren Farbidentitaet `color` enthaelt (fuer
    Landwalk gegen einen Gegner ohne bekannte Farbe)."""
    prof = _PROFILE or {}
    total = hit = 0.0
    for key, row in prof.items():
        if key == "ALL":
            continue
        n = float(row.get("decks", 0))
        total += n
        if color in key:
            hit += n
    return hit / total if total else 0.5


@functools.lru_cache(maxsize=1)
def _k_eff() -> float:
    """Geeichte 'realistisch blockbereite Kreaturen' k, so dass
    1-(1-s_ALL)^k == evasion_keyword_multiplier.flying (0.35)."""
    anchor = float(_WEIGHTS.get("evasion_keyword_multiplier", {}).get("flying", 0.35))
    s_all = float(((_PROFILE or {}).get("ALL") or {}).get("air_blocker", 0.2))
    s_all = min(0.99, max(0.01, s_all))
    anchor = min(0.99, max(0.01, anchor))
    return math.log(1.0 - anchor) / math.log(1.0 - s_all)


def restricted_block_multiplier(eligible_share: float) -> float:
    s = max(0.0, min(1.0, float(eligible_share)))
    if s >= 1.0:
        return 1.0
    return 1.0 - (1.0 - s) ** _k_eff()


def _union(shares: Iterable[float]) -> float:
    miss = 1.0
    for s in shares:
        miss *= 1.0 - max(0.0, min(1.0, s))
    return 1.0 - miss


# ---------------------------------------------------------------------------
# Oracle-Text-Parser fuer seltene Kampf-Keywords, die engine.keyword_set()
# (nur KNOWN_KEYWORDS) NICHT fuehrt: Afflict, Toxic, Frenzy, Exalted,
# Battle cry, Fear, Intimidate, Shadow, Horsemanship, Landwalk, Training,
# Mentor, Annihilator, Flanking, Bushido, Rampage, Protection-Farben.
# Gleiche "statische Keyword-Zeile"-Konvention wie keyword_set(): nur Zeilen,
# die das Keyword der Karte SELBST geben, nicht solche, die es anderen
# verleihen ("creatures you control have ...").
# ---------------------------------------------------------------------------
_NUMERIC = ("afflict", "toxic", "frenzy", "annihilator", "bushido", "rampage", "flanking")
_FLAGS = ("exalted", "battle cry", "fear", "intimidate", "shadow", "horsemanship", "training", "mentor", "skulk")
_GRANT_PHRASES = (" gains ", " gain ", " have ", " gets ", " has ", " get ")


@functools.lru_cache(maxsize=4096)
def parse_combat_keywords(oracle_text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for raw in (oracle_text or "").split("\n"):
        line = re.sub(r"\([^()]*\)", "", raw).strip().lower()
        if not line or any(p in f" {line} " for p in _GRANT_PHRASES):
            continue
        parts = [p.strip() for p in re.split(r",\s*", line.rstrip("."))]
        for part in parts:
            for kw in _NUMERIC:
                m = re.fullmatch(rf"{kw}(?: (\d+))?", part)
                if m:
                    out[kw] = out.get(kw, 0) + int(m.group(1) or 1)
            for kw in _FLAGS:
                if part == kw:
                    out[kw] = out.get(kw, 0) + 1
            m = re.fullmatch(r"(plains|island|swamp|mountain|forest)walk", part)
            if m:
                out.setdefault("landwalk", set()).add(_LAND_TYPE_COLOR[m.group(1)])
            if part.startswith("protection from "):
                prot = out.setdefault("protection_from", set())
                rest = part[len("protection from "):]
                if "everything" in rest or "creatures" in rest:
                    prot.add("*")
                if "each color" in rest or "all colors" in rest:
                    prot.update(_COLORS)
                for word, c in _COLOR_WORD.items():
                    if word in rest:
                        prot.add(c)
    return out


# ---------------------------------------------------------------------------
# 1) Eigene Angreifer
# ---------------------------------------------------------------------------
def _seat_attack_multiplier(row: Dict[str, float], keywords: Set[str], extras: Dict[str, Any],
                            attacker_colors: Set[str], has_colors: bool) -> float:
    w = _kw_weights()
    mult = 1.0
    if "flying" in keywords:
        mult *= restricted_block_multiplier(row.get("air_blocker", 0.2))
    if "menace" in keywords:
        anchor = float(_WEIGHTS.get("evasion_keyword_multiplier", {}).get("menace", 0.55))
        cpd_all = float(((_PROFILE or {}).get("ALL") or {}).get("creatures_per_deck", 27.7)) or 27.7
        m = anchor * float(row.get("creatures_per_deck", cpd_all)) / cpd_all
        mult *= max(float(w.get("menace_min", 0.2)), min(float(w.get("menace_max", 0.9)), m))
    if extras.get("fear"):
        mult *= restricted_block_multiplier(min(1.0, row.get("artifact", 0.1) + row.get("color_B", 0.2)))
    if extras.get("intimidate"):
        share_colors = _union(row.get(f"color_{c}", 0.0) for c in attacker_colors)
        art = row.get("artifact", 0.1)
        mult *= restricted_block_multiplier(min(1.0, art + (1.0 - art) * share_colors))
    prot = extras.get("protection_from") or set()
    if "*" in prot:
        mult *= restricted_block_multiplier(0.0)
    elif prot:
        mult *= restricted_block_multiplier(1.0 - _union(row.get(f"color_{c}", 0.0) for c in prot))
    if extras.get("shadow") or extras.get("horsemanship"):
        mult *= restricted_block_multiplier(0.0)
    return mult


def attack_block_multiplier(keywords: Set[str], extras: Dict[str, Any], attacker_colors: Set[str],
                            ctx: KeywordCombatContext) -> float:
    """Ersetzt interaction._evasion_multiplier, wenn das Keyword-Modell aktiv
    ist. Gleichgewichteter Mittelwert ueber die Sitzplaetze (dieselbe
    offengelegte Gleichgewichtung wie v4.77.0 WP-B - dieses Modell weiss
    nicht, WELCHER Gegner einen Angriff verteidigt)."""
    kws = {k.lower() for k in keywords}
    vals = []
    for i, row in enumerate(ctx.rows):
        m = _seat_attack_multiplier(row, kws, extras, set(attacker_colors or set()), ctx.colored)
        walk = extras.get("landwalk") or set()
        if walk:
            if ctx.colored:
                seat = ctx.seat_colors[i] if i < len(ctx.seat_colors) else set()
                if walk & {c.upper() for c in seat}:
                    m *= 0.0
            else:
                m *= 1.0 - _union(deck_share_with_color(c) for c in walk)
        vals.append(m)
    return max(0.0, min(1.0, sum(vals) / len(vals))) if vals else 1.0


def trample_excess(power: float, keywords: Set[str], ctx: KeywordCombatContext) -> float:
    """Schaden, der bei einem GEBLOCKTEN Trampler zum Spieler durchgeht:
    Power minus typische Toughness eines Blockers der Gegnerfarbe(n); mit
    Deathtouch genuegt 1 zugewiesener Schaden fuer den Blocker (echte Regel)."""
    kws = {k.lower() for k in keywords}
    if "trample" not in kws:
        return 0.0
    need = 1.0 if "deathtouch" in kws else ctx.mean("mean_toughness", 3.0)
    return max(0.0, float(power) - need)


def trade_rate_multiplier(extras: Dict[str, Any]) -> float:
    w = _kw_weights()
    mult = 1.0
    if extras.get("flanking"):
        mult *= float(w.get("flanking_trade_rate_multiplier", 0.8)) ** int(extras["flanking"])
    if extras.get("bushido"):
        mult *= float(w.get("bushido_trade_rate_multiplier_per_point", 0.85)) ** int(extras["bushido"])
    if extras.get("rampage"):
        mult *= float(w.get("rampage_trade_rate_multiplier", 0.9))
    return mult


def attrition_credit(keywords: Set[str], power: float, ctx: KeywordCombatContext) -> float:
    """Wie viele gegnerische Kreaturen ein Kampf gegen DIESE Kreatur
    (angreifend geblockt oder blockend) im Erwartungswert entfernt:
    Deathtouch = sicher 1 (jeder Schaden ist toedlich), Wither/Infect =
    dauerhafte -1/-1-Counter, bis zu 1 je nach Power gegen die typische
    Toughness der Gegnerfarbe. Allgemeine 'Blocker stirbt am hoeheren
    Power-Wert'-Kills werden BEWUSST NICHT gutgeschrieben - das wuerde die
    v4.76.0-Kalibrierung des gesamten Blockmodells verschieben, nicht nur
    Keywords abbilden (offengelegte Grenze, siehe Docs/README.md v4.82.0)."""
    kws = {k.lower() for k in keywords}
    if "deathtouch" in kws and power > 0:
        return 1.0
    if kws & {"wither", "infect"} and power > 0:
        return min(1.0, float(power) / max(1.0, ctx.mean("mean_toughness", 3.0)))
    # v4.83.0: gewoehnliche Kampf-Kills (Blocker/Angreifer stirbt am hoeheren
    # Power-Wert) werden jetzt ebenfalls gutgeschrieben - vorher starb auf
    # Gegnerseite nie etwas durch normalen Kampf, waehrend die Kreaturen des
    # Spielers regulaer tauschten (Tisch-Asymmetrie, Docs/README.md v4.83.0).
    # ordinary_kill_credit=0 stellt das v4.82.0-Verhalten exakt wieder her.
    share = float(_kw_weights().get("ordinary_kill_credit", 0.0))
    if share > 0 and power > 0:
        return share * min(1.0, float(power) / max(1.0, ctx.mean("mean_toughness", 3.0)))
    return 0.0
