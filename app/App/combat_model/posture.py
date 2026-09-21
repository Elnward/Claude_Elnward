"""
Commander Posture (WP5, revisited) - now generalized to value-engine creatures.

Originally deferred (see project history) until combat had a real risk model -
before WP6, attacking never killed a creature, so "protect the commander from a
bad attack" had nothing to protect against. Now that WP6/WP7 give combat real
death consequences and impact-weighted removal targeting, a fragile value-engine
commander (the motivating real example: Bilbo, Birthday Celebrant) can be ground
down by repeatedly attacking for no reason - this module gives such a commander a
way to stay home.

Generalization (from real 200-run data): protecting only the commander was not
enough. Doctor Strange, Surgeon - Bilbo's highest-measured-value card
(roles: engine|lifegain|lifegain_replacement), not the commander - kept attacking
and dying every turn even after the commander itself was protected. The same
value-vs-no-reason gate now applies to ANY creature tagged with an engine-ish role,
not just the commander (see creature_should_attack / _ENGINE_ROLES below). Ordinary
creatures (beaters, tokens, anything without such a role) are unaffected.

Honest scope: this is NOT a safety/risk evaluation (the engine still has no
opposing-blocker model to reason about). It only distinguishes VALUE reasons to
attack (an attack-triggered ability, a lethal/near-lethal swing) from attacking for
no reason. See Docs/README.md for the fuller rationale.

Engine-agnostic on purpose (no `import engine`) - `ops` is passed by the caller
(the engine module).
"""
from __future__ import annotations

import re
from typing import Any

from .interaction import _WEIGHTS

_ATTACK_TRIGGER_RE = re.compile(
    r"whenever\s+(?:this creature|~|[^,.]+?)\s+attacks", re.IGNORECASE
)

_ENGINE_ROLES = {"engine", "lifegain_replacement", "tutor", "draw_engine"}
_AGGRESSIVE_ROLES = {"finisher"}


def _posture_weights() -> dict:
    return _WEIGHTS.get("posture", {"balanced_min_other_attackers": 2})


def infer_auto_posture(card: Any) -> str:
    """AUTO: derive a tendency from the commander's own tagged roles.
    Simplified, three-way heuristic - no per-card special-casing."""
    roles = getattr(card, "roles", set()) or set()
    if roles & _AGGRESSIVE_ROLES:
        return "aggressive"
    if roles & _ENGINE_ROLES:
        return "passive"
    return "balanced"


def has_attack_value_trigger(card: Any) -> bool:
    """Simplified detection of a self-referential 'whenever this attacks' ability
    (Oracle text mentions its own name or 'this creature'/'~' in an attack trigger).
    A false negative here just means AUTO/PASSIVE under-values attacking a bit -
    it never blocks a card from attacking under AGGRESSIVE."""
    text = card.oracle_text or ""
    if _ATTACK_TRIGGER_RE.search(text):
        return True
    # Also catch "Whenever <Card Name> attacks" phrasing (self-name reference).
    name = getattr(card, "name", "")
    if name and re.search(
        rf"whenever\s+{re.escape(name)}\s+attacks", text, re.IGNORECASE
    ):
        return True
    return False


def is_lethal_or_ledger_progressing_opportunity(ops: Any, state: Any, p: Any) -> bool:
    """True if this creature's current power (Double Strike doubled) would either
    finish off the currently-targeted opponent outright, or - for the commander
    specifically - meaningfully progress its Commander-Damage Ledger. 'Meaningfully'
    = the OPPORTUNITY check from scenario_predicates.commander_damage_lethal, reused
    here directly rather than re-implemented."""
    if not state.opponents:
        return False
    kws = ops.effective_keywords_in_state(p, state)
    power = ops.creature_power(p, state)
    if "double strike" in kws:
        power *= 2.0

    # Outright kill on the softest target - applies to any gated creature.
    if power >= min(state.opponents):
        return True

    if not bool(p.card.commander):
        return False

    # Commander-Damage Ledger: is this swing enough to finish the 21 on ANY target
    # that's already partway there? (Pure "start the clock at 0" doesn't count as
    # a reason to attack on its own under PASSIVE - only closing it out does.)
    # v4.28.0: keyed per-commander (p.card.name) - THIS commander's own progress
    # toward 21, not (as before the fix) an opponent-indexed total pooled across
    # every commander a Partner/background deck may have on the battlefield.
    ledger = getattr(state, "commander_damage_dealt", {})
    for i in range(len(state.opponents)):
        already = float(ledger.get((p.card.name, i), 0.0))
        if already > 0 and power >= max(0.0, 21.0 - already):
            return True
    return False


def creature_should_attack(
    ops: Any, state: Any, strategy: Any, p: Any, *, other_attacker_count: int = 0,
) -> bool:
    """
    Generalized Posture gate: applies to the commander AND to any non-commander
    creature tagged with an engine-ish role (see _ENGINE_ROLES). Ordinary creatures
    (no such role, not the commander) are unaffected and always attack if able -
    this is deliberately narrow, not a general 'should I attack' AI for the whole
    board (see module docstring for why: no risk model exists to reason about for
    an ordinary beater, only for cards whose value comes from surviving on the
    battlefield rather than from attacking).

    Real motivating example (from actual 200-run data, not speculation): Doctor
    Strange, Surgeon (roles: engine|lifegain|lifegain_replacement) is Bilbo's
    highest-measured-value card and was still attacking - and dying - every turn
    even after the commander itself was protected by Posture.
    """
    roles = getattr(p.card, "roles", set()) or set()
    is_commander = bool(p.card.commander)
    if not is_commander and not (roles & _ENGINE_ROLES):
        return True  # ordinary creature: unchanged default behavior

    posture = (getattr(strategy, "commander_posture", "auto") or "auto").lower()
    if posture == "auto":
        posture = infer_auto_posture(p.card)

    if posture == "aggressive":
        return True

    value_trigger = has_attack_value_trigger(p.card)
    opportunity = is_lethal_or_ledger_progressing_opportunity(ops, state, p)

    if posture == "passive":
        return value_trigger or opportunity

    # "balanced" (and any unrecognized value, defensively)
    min_others = _posture_weights().get("balanced_min_other_attackers", 2)
    board_is_wide_enough = other_attacker_count >= min_others
    return value_trigger or opportunity or board_is_wide_enough


# Backward-compatible alias: a commander is always gated by creature_should_attack
# regardless of its roles, so the two functions agree for commanders by construction.
commander_should_attack = creature_should_attack
