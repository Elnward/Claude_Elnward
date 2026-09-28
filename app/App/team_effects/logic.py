"""
Engine-agnostic calculations for the team-effect registry (v4.76.0, WP3).

`ops` is the engine module. Nothing here mutates state except
`apply_team_pump`, which only appends BoardModifiers that expire at the end
of the current turn (the engine's own untap step already expires them).
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

try:
    from ..mana_scaling.handlers import _is_type, count_matching, singular
except (ImportError, ValueError):
    from mana_scaling.handlers import _is_type, count_matching, singular

from . import registry

TYPED_KIND = "typed_pt_bonus"


def _token_matches(group: Any, kind: str) -> bool:
    if kind in {"creature", "permanent"}:
        return True
    return kind in {singular(w) for w in (group.name or "").lower().split()}


def static_anthems(ops: Any, state: Any) -> List[Tuple[Any, str, float, List[str], bool]]:
    """(source permanent, type, +N, keywords, other) for every typed anthem on
    our battlefield. Parsed from Oracle text; memoized per card text."""
    out = []
    dedicated = getattr(ops, "DEDICATED_RESOLVERS", {})
    for src in state.battlefield:
        if src.card.name in dedicated:
            continue  # same rule as the engine's generic static loops
        for info in _anthems_for_card(ops, src.card):
            out.append((src,) + info)
    return out


_ANTHEM_CACHE: dict = {}


def _anthems_for_card(ops: Any, card: Any) -> List[Tuple[str, float, List[str], bool]]:
    key = (card.name, card.oracle_text)
    if key not in _ANTHEM_CACHE:
        found = []
        for line in ops.split_oracle_lines(card.oracle_text or ""):
            low = ops.strip_reminder_text(line).lower().strip()
            if ":" in low:
                continue
            a = registry.parse_anthem(low)
            if a:
                found.append(a)
        _ANTHEM_CACHE[key] = found
    return _ANTHEM_CACHE[key]


def typed_power_bonus(ops: Any, state: Any, p: Any) -> float:
    """Typed anthems + active typed pumps that apply to permanent p."""
    bonus = 0.0
    for src, kind, n, _kws, other in static_anthems(ops, state):
        if other and src is p:
            continue
        if _is_type(p.card, kind):
            bonus += n
    for m in ops.board_modifiers(state):
        if m.kind == TYPED_KIND and _is_type(p.card, m.scope):
            bonus += m.amount
    return bonus


def typed_token_bonus(ops: Any, state: Any, group: Any) -> float:
    bonus = 0.0
    for _src, kind, n, _kws, _other in static_anthems(ops, state):
        if _token_matches(group, kind):
            bonus += n
    for m in ops.board_modifiers(state):
        if m.kind == TYPED_KIND and _token_matches(group, m.scope):
            bonus += m.amount
    return bonus


def typed_keywords(ops: Any, state: Any, p: Any) -> set:
    out = set()
    for src, kind, _n, kws, other in static_anthems(ops, state):
        if other and src is p:
            continue
        if kws and _is_type(p.card, kind):
            out.update(kws)
    for m in ops.board_modifiers(state):
        if m.kind == TYPED_KIND and m.keyword and _is_type(p.card, m.scope):
            out.update(k for k in m.keyword.split(",") if k)
    return out


def creature_count(state: Any) -> int:
    return count_matching(state, "creature")


def apply_team_pump(ops: Any, state: Any, source_name: str, amount: float,
                    keywords: List[str], kind: str = "creature") -> None:
    mods = ops.board_modifiers(state)
    if kind == "creature":
        mods.append(ops.BoardModifier(source=source_name, expires_turn=state.turn,
                                      kind="team_pt_bonus", amount=float(amount)))
        for kw in keywords:
            mods.append(ops.BoardModifier(source=source_name, expires_turn=state.turn,
                                          kind="grant_keyword", keyword=kw))
    else:
        mods.append(ops.BoardModifier(source=source_name, expires_turn=state.turn, kind=TYPED_KIND,
                                      scope=kind, amount=float(amount), keyword=",".join(keywords)))


def attackers_of_type(ops: Any, state: Any, kind: str) -> int:
    """Creatures (incl. tokens) that could still attack this turn."""
    n = 0
    for p in state.battlefield:
        if not p.card.is_creature or p.tapped:
            continue
        kws = ops.effective_keywords_in_state(p, state)
        if "defender" in kws or (p.entered_turn == state.turn and "haste" not in kws):
            continue
        if _is_type(p.card, kind):
            n += 1
    for g in getattr(state, "creature_tokens", []) or []:
        if g.count > 0 and g.entered_turn != state.turn and _token_matches(g, kind):
            n += int(g.count)
    return n


def choose_tutor_target(ops: Any, state: Any, strategy: Any, max_mv: int,
                        info: dict) -> Optional[Tuple[Any, str]]:
    """Best creature card with mana value <= max_mv in library (and graveyard
    if allowed). An ETB team finisher (Craterhoof-shape) wins once at least
    four creatures could attack (disclosed heuristic threshold); otherwise the
    deck's own tutor priority decides. Returns (card, zone) or None."""
    color = (info.get("color") or "").lower()
    color_letter = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"}.get(color)
    zones = [("library", state.library)]
    if info.get("graveyard"):
        zones.append(("graveyard", state.graveyard))
    prio = getattr(strategy, "tutor_priority", []) or []
    board = attackers_of_type(ops, state, "creature")
    best = None
    for zone, cards in zones:
        for c in cards:
            if not c.is_creature or float(c.mana_value) > max_mv:
                continue
            if color_letter and color_letter not in (c.color_identity or set()):
                continue
            score = float(ops.generic_tutor_score(c, prio)) + 0.1 * float(c.mana_value)
            if registry.etb_team_pump(ops, c.oracle_text) and board >= 4:
                score += 1000.0
            if best is None or score > best[0]:
                best = (score, c, zone)
    return (best[1], best[2]) if best else None
