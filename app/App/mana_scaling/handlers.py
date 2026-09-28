"""
Handlers for the scaling-mana registry (v4.76.0, WP1).

Signature:  handler(ops, permanent, state, strategy, definition, match)
                -> Optional[List[Counter]]   (None = decline, fall through)

`ops` is the engine module (COLORS, creature_power, ...). Nothing here
mutates state: a handler only answers "what could ONE activation of this
permanent produce right now". Paying/tapping stays in the engine's own
payment solver, exactly as for every other mana source.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, List, Optional

from .registry import register_handler

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_IRREGULAR_PLURALS = {"elves": "elf", "dwarves": "dwarf", "wolves": "wolf", "fungi": "fungus",
                      "mice": "mouse", "oxen": "ox", "men": "man", "leaves": "leaf"}
_CARD_TYPES = {"creature", "artifact", "enchantment", "land", "planeswalker", "permanent"}


def singular(word: str) -> str:
    w = word.lower().strip()
    if w in _IRREGULAR_PLURALS:
        return _IRREGULAR_PLURALS[w]
    for suffix in ("ches", "shes", "sses", "xes"):
        if w.endswith(suffix):
            return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _symbol(sym: str) -> str:
    return sym.strip("{}").upper()


def _is_type(card: Any, kind: str) -> bool:
    tl = (card.type_line or "").lower()
    if kind == "permanent":
        return True
    if kind in _CARD_TYPES:
        return kind in tl
    # creature subtype: after the em dash / hyphen of the type line
    if "creature" not in tl:
        return False
    if "changeling" in {k.lower() for k in getattr(card, "keywords", set())}:
        return True
    sub = tl.split("—", 1)[1] if "—" in tl else (tl.split(" - ", 1)[1] if " - " in tl else "")
    return kind in sub.replace("//", " ").split()


def count_matching(state: Any, kind: str, *, untapped_only: bool = False, exclude: Any = None) -> int:
    """Own permanents of a card type / creature subtype, plus own creature
    token groups (tokens only for 'creature'/'permanent' or a subtype named
    in the token's name, e.g. 'Elf Warrior'). Opponents' permanents are not
    part of this engine's state, so 'on the battlefield' counts are a lower
    bound -- documented in definitions.json."""
    kind = singular(kind)
    n = 0
    for p in state.battlefield:
        if p is exclude:
            continue
        if untapped_only and p.tapped:
            continue
        if _is_type(p.card, kind):
            n += 1
    if kind in {"creature", "permanent"} or kind not in _CARD_TYPES:
        # Token groups carry no per-token tap state in this engine; they are
        # counted as available (a simplification noted in definitions.json).
        for g in getattr(state, "creature_tokens", []) or []:
            name_words = {singular(w) for w in (g.name or "").lower().split()}
            if kind in {"creature", "permanent"} or kind in name_words:
                n += int(g.count or 0)
    return n


def _colors(ops: Any, strategy: Any) -> List[str]:
    cols = getattr(strategy, "commander_colors", None) or set(ops.COLORS)
    return sorted(cols, key=lambda c: "WUBRG".index(c) if c in "WUBRG" else 9)


@register_handler("symbol_per_count")
def _h_symbol_per_count(ops, permanent, state, strategy, definition, m) -> Optional[list]:
    sym = _symbol(m.group(1))
    other = bool(m.group(2))
    kind = m.group(3)
    n = count_matching(state, kind, exclude=permanent if other else None)
    return [Counter({sym: n})] if n > 0 else []


@register_handler("any_one_color_per_count")
def _h_any_one_color_per_count(ops, permanent, state, strategy, definition, m) -> Optional[list]:
    n = count_matching(state, m.group(1))
    if n <= 0:
        return []
    return [Counter({c: n}) for c in _colors(ops, strategy)]


@register_handler("symbol_times_own_power")
def _h_symbol_times_own_power(ops, permanent, state, strategy, definition, m) -> Optional[list]:
    sym = _symbol(m.group(1))
    n = int(max(0.0, float(ops.creature_power(permanent, state))))
    return [Counter({sym: n})] if n > 0 else []


@register_handler("tap_n_untapped_type")
def _h_tap_n_untapped_type(ops, permanent, state, strategy, definition, m) -> Optional[list]:
    word = m.group(1)
    need = _NUMBER_WORDS.get(word) or (int(word) if word.isdigit() else 0)
    if need <= 0:
        return None
    if count_matching(state, m.group(2), untapped_only=True) < need:
        return []
    import re as _re
    symbols = _re.findall(r"\{([wubrgc])\}", m.group(3))
    return [Counter(s.upper() for s in symbols)]
