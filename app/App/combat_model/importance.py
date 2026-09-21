"""
Card-importance scoring for target selection (WP6, Iteration 2).

Idea: cards that have already proven impactful THIS RUN (state.impact, populated by
record_impact throughout the game - combat damage dealt, mana saved, card draw
triggered, etc.) should be somewhat more likely to attract opponent removal and
combat blocks than a redundant/idle card, on top of the existing static
`strategy.tutor_priority` authored list.

Deliberately causal and single-run: only uses impact accumulated earlier in the SAME
game being simulated, never data from other runs. Using historical cross-run
aggregates (e.g. "Doctor Strange is important based on the last 200 runs") is a
natural follow-up but introduces a self-fulfilling-prophecy / survivor-bias risk
(a card targeted more because it was important may then show LESS measured impact
in the very data that would justify targeting it) - if that is wanted later, it
should be a separate, explicitly-labeled feature, not silently blended in here.

`ops` is the engine module (for generic_tutor_score), passed by the caller to avoid
a circular import - same pattern as keyword_library/scenario_predicates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from .interaction import _WEIGHTS  # shared, already-loaded weights table


def _weights() -> Dict[str, float]:
    return _WEIGHTS.get("importance_targeting", {"removal_weight": 0.0, "combat_block_weight": 0.0})


def live_impact_score(state: Any, card_name: str) -> float:
    """'How much has this card already done this run', normalized to roughly a
    per-turn rate so early- and late-game runs are comparable."""
    counters = getattr(state, "impact", None)
    if not counters:
        return 0.0
    counter = counters.get(card_name)
    if not counter:
        return 0.0
    total = sum(v for v in counter.values() if isinstance(v, (int, float)))
    return total / max(1, getattr(state, "turn", 1))


def removal_target_score(ops: Any, state: Any, strategy: Any, card: Any) -> float:
    """Score used to pick the opponent's abstract removal target: higher = more likely target."""
    base = ops.generic_tutor_score(card, getattr(strategy, "tutor_priority", []))
    weight = _weights().get("removal_weight", 0.0)
    return base + weight * live_impact_score(state, card.name)


def choose_removal_target(ops: Any, state: Any, strategy: Any, targets: Iterable[Any], rng: Any) -> Any:
    """Pick which battlefield permanent the opponent's spot removal hits.

    v4.8.3: previously this was always `max(targets, key=removal_target_score)` -
    a fully deterministic "always kill the single best-scoring permanent" rule.
    The v4.8.2 combat/removal diagnostics (200-run Bilbo baseline, random opponent)
    showed this concentrates ~61% of ALL opponent removal in the whole deck onto
    just two engine cards (Bilbo, Doctor Strange), because their live_impact_score
    dwarfs everything else on the board as soon as they've done anything this run.

    `target_focus_chance` (Data/Models/combat_interaction_weights.json) is the
    probability the opponent actually removes the top-scoring target; otherwise the
    target is picked uniformly at random among all legal targets. This keeps
    high-impact cards a more likely target on average (same as before) without
    pretending the opponent has perfect, always-optimal removal targeting - no new
    precision is claimed, it is a single tunable probability like the other
    abstract-opponent rates (block_rate_base, trade_rate_given_blocked, ...).
    """
    targets = list(targets)
    if not targets:
        return None
    focus_chance = _weights().get("target_focus_chance", 1.0)
    if rng.random() < focus_chance:
        return max(targets, key=lambda p: removal_target_score(ops, state, strategy, p.card))
    return targets[rng.randrange(len(targets))]


def combat_block_multiplier(state: Any, name: str, all_names: Iterable[str]) -> float:
    """
    Multiplier (>=1.0) applied to a single attacker's block_rate, based on its
    live impact relative to the OTHER attackers in the same combat. The single
    most active attacker this combat gets the full bonus; a lone attacker or a
    group of equally-idle attackers gets no bonus (multiplier 1.0).
    """
    weight = _weights().get("combat_block_weight", 0.0)
    if weight <= 0:
        return 1.0
    scores = {n: live_impact_score(state, n) for n in all_names}
    peak = max(scores.values(), default=0.0)
    if peak <= 0:
        return 1.0
    return 1.0 + weight * (scores.get(name, 0.0) / peak)
