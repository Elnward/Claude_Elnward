"""
Predicate implementations for App/scenario_predicates.

Signature: handler(ops, params, state, strategy) -> PredicateResult

`ops` exposes the engine's helpers (available_mana_value, best_x_plan,
x_effect_metrics, ...) - passed in by the caller (in practice the engine module),
kept out of a direct import here to avoid a circular dependency with engine.py.
"""
from __future__ import annotations

from .registry import PredicateResult, register_predicate

# combat_model.interaction is a standalone leaf module (no import of
# engine.py or scenario_predicates), so importing it directly here -- unlike
# engine.py's own helpers, reached only through the passed-in `ops` -- does
# not create a circular import. Relative, matching this file's own `.registry`
# import style so it resolves the same way whether this package loads as
# `App.scenario_predicates` or as a bare `scenario_predicates` (see engine.py's
# own try/except import of this package's `registry` module).
from ..combat_model.interaction import block_rate_for as _combat_block_rate_for


def _opponent_indices(state, target) -> list:
    n = len(state.opponents)
    if target in ("any", "each", None):
        return list(range(n))
    try:
        idx = int(target)
    except (TypeError, ValueError):
        return list(range(n))
    return [idx] if 0 <= idx < n else []


@register_predicate("resource_available")
def _p_resource_available(ops, params, state, strategy) -> PredicateResult:
    resource = params.get("resource")
    min_count = params.get("min_count", 1)

    if resource == "mana":
        have = ops.available_mana_value(state, strategy)
    elif resource == "untapped_creatures":
        have = sum(
            1 for p in state.battlefield
            if p.card.is_creature and not p.tapped
        )
    elif resource == "untapped_artifacts":
        have = sum(
            1 for p in state.battlefield
            if p.card.is_artifact and not p.tapped
        )
    elif resource == "food":
        have = state.food
    elif resource == "treasure":
        have = state.treasure
    elif resource == "clues":
        have = state.clues
    else:
        return PredicateResult.not_computable(f"unknown resource '{resource}'")

    # v4.15.7: partial credit toward the threshold, not just pass/fail -
    # 0 resources vs (min_count - 1) resources should steer differently
    # even though both are "not satisfied".
    progress = min(1.0, have / min_count) if min_count > 0 else 1.0
    return PredicateResult(
        satisfied=have >= min_count,
        detail=f"{resource}: have {have}, need {min_count}",
        progress=progress,
    )


@register_predicate("opponent_life_at_or_below")
def _p_opponent_life_at_or_below(ops, params, state, strategy) -> PredicateResult:
    threshold = params.get("threshold")
    if threshold is None:
        return PredicateResult.not_computable("missing 'threshold'")
    target = params.get("target", "any")
    indices = _opponent_indices(state, target)
    if not indices:
        return PredicateResult.not_computable(f"no opponent matches target '{target}'")

    lives = [state.opponents[i] for i in indices]
    if target == "each":
        ok = all(life <= threshold for life in lives)
    else:  # "any" or a specific index
        ok = any(life <= threshold for life in lives)

    # v4.15.7: per-opponent closeness = threshold/life (1.0 once life has
    # dropped to the threshold, 0 at very high life) - a plain ratio, not a
    # rules claim, same spirit as scenario_feasibility's own threshold
    # ratios elsewhere. "each" needs every opponent there, so the worst
    # (lowest-progress) opponent gates the combined score; "any"/a specific
    # index only needs the best one.
    def _life_progress(life: float) -> float:
        if life <= threshold:
            return 1.0
        if life <= 0:
            return 1.0
        return max(0.0, min(1.0, threshold / life)) if threshold > 0 else 0.0

    life_progress = [_life_progress(life) for life in lives]
    progress = min(life_progress) if target == "each" else max(life_progress)

    return PredicateResult(
        satisfied=ok,
        detail=f"opponent life {lives} vs threshold {threshold} (target={target})",
        progress=progress,
    )


@register_predicate("x_spell_lethal")
def _p_x_spell_lethal(ops, params, state, strategy) -> PredicateResult:
    card_name = params.get("card")
    if not card_name:
        return PredicateResult.not_computable("missing 'card'")
    copy_multiplier = max(1, int(params.get("copy_multiplier", 1)))
    target = params.get("target", "any")

    card = next((c for c in state.hand if c.name == card_name), None)
    if card is None:
        return PredicateResult.not_computable(f"'{card_name}' not in hand this state")
    if not ops.has_x_cost(card):
        return PredicateResult.not_computable(f"'{card_name}' has no {{X}} cost")

    indices = _opponent_indices(state, target)
    if not indices:
        return PredicateResult.not_computable(f"no opponent matches target '{target}'")
    lives = [state.opponents[i] for i in indices]
    remaining = min(lives) if target != "each" else max(lives)
    if remaining <= 0:
        return PredicateResult(satisfied=True, detail="target already at/below 0 life")

    # Simplification (see definitions.json): total available mana as the X budget,
    # rather than running the full colored-mana payment solver for every candidate X.
    base_cost, _req = ops.x_base_cost_and_req(card)
    budget = ops.available_mana_value(state, strategy)
    max_x = max(0, budget - base_cost)
    if max_x <= 0:
        # v4.15.7: still some signal worth steering toward - how close is
        # the mana budget to even affording the base cost (X=0)?
        progress = min(1.0, budget / base_cost) if base_cost > 0 else 0.0
        return PredicateResult(
            satisfied=False, detail=f"no mana left for X after base cost {base_cost}",
            progress=progress,
        )

    # Smallest X that reaches lethal (see project brief section 16: minimize X for
    # lethal, don't just take the biggest affordable X).
    for x in range(1, max_x + 1):
        metrics = ops.x_effect_metrics(card, x, state, strategy)
        damage = float(metrics.get("opponent_life_loss", 0.0)) * copy_multiplier
        if damage >= remaining:
            return PredicateResult(
                satisfied=True,
                detail=f"X={x} (of max {max_x}) * copies={copy_multiplier} -> {damage:.1f} dmg >= {remaining:.1f} needed",
            )

    best_damage = float(ops.x_effect_metrics(card, max_x, state, strategy).get("opponent_life_loss", 0.0)) * copy_multiplier
    # v4.15.7: how close the biggest affordable X gets to lethal - already
    # computed above (best_damage, remaining), just expose it as progress.
    progress = min(1.0, best_damage / remaining) if remaining > 0 else 1.0
    return PredicateResult(
        satisfied=False,
        detail=f"even X={max_x} * copies={copy_multiplier} only reaches {best_damage:.1f} dmg, needed {remaining:.1f}",
        progress=progress,
    )


@register_predicate("commander_damage_lethal")
def _p_commander_damage_lethal(ops, params, state, strategy) -> PredicateResult:
    commander_name = params.get("commander")
    target = params.get("target", "any")

    commander_p = next((p for p in state.creatures() if p.card.commander), None)
    if commander_p is None:
        return PredicateResult.not_computable("no commander creature on the battlefield in this state")
    if commander_name and commander_p.card.name != commander_name:
        return PredicateResult.not_computable(
            f"battlefield commander is '{commander_p.card.name}', not '{commander_name}'"
        )

    kws = ops.effective_keywords_in_state(commander_p, state)
    power = ops.creature_power(commander_p, state)
    if "double strike" in kws:
        power *= 2.0

    indices = _opponent_indices(state, target)
    if not indices:
        return PredicateResult.not_computable(f"no opponent matches target '{target}'")

    # v4.28.0: the ledger is keyed per-commander since state.commander_damage_dealt
    # can hold entries for multiple Partner/background co-commanders - must look
    # up THIS commander's own entry, not (as before the fix) an opponent-indexed
    # total pooled across every commander on the battlefield.
    ledger = getattr(state, "commander_damage_dealt", {})
    checks = []
    for i in indices:
        already = float(ledger.get((commander_p.card.name, i), 0.0))
        remaining = max(0.0, 21.0 - already)
        checks.append((i, remaining, power >= remaining))

    if target == "each":
        ok = all(c[2] for c in checks)
    else:
        ok = any(c[2] for c in checks)

    # v4.15.7: power/remaining per opponent as the closeness signal (already
    # 21 damage in matters more than 3) - "each" needs every opponent
    # there, gated by the worst; "any"/an index only needs the best one.
    per_opponent_progress = [
        (min(1.0, power / rem) if rem > 0 else 1.0) for _i, rem, _ok in checks
    ]
    progress = min(per_opponent_progress) if target == "each" else max(per_opponent_progress)

    detail = ", ".join(f"opp{i}: need {rem:.1f}, have {power:.1f}" for i, rem, _ in checks)
    return PredicateResult(
        satisfied=ok,
        detail=f"OPPORTUNITY only (assumes unblocked): {detail}",
        progress=progress,
    )


@register_predicate("board_damage_lethal")
def _p_board_damage_lethal(ops, params, state, strategy) -> PredicateResult:
    """v4.79.0 (Runde 1, original Punkt 6): is the current board (creatures +
    token groups able to attack right now) lethal against the target
    opponent(s)' CURRENT life -- not a fixed assumed-40 starting life.

    Before this predicate existed, an alpha-strike or token-swarm win
    condition had no dedicated way to express "my board is lethal this
    turn" at all, so scenarios for that shape typically fell back to a
    fixed "total power >= 40" requirement authored by hand (or by the AI
    scenario prompt) as a stand-in for "opponent's starting life" -- which
    silently stopped meaning "lethal" the moment the opponent had already
    taken damage from anything else that game (a big one-time swing against
    an already-damaged opponent then went unrecognized as a win).

    Simplification (disclosed, same spirit as x_spell_lethal's mana-budget
    stand-in for a full payment solver): reads tapped/summoning-sickness
    state as-is from the current snapshot (so this reflects "if everyone
    who COULD attack right now did"), and uses each attacker's EXPECTED
    damage (power * (1 - block_rate), the same per-attacker block-rate
    model real combat resolution uses) rather than a full stochastic
    resolution of who actually gets blocked. Equipment/trigger-based
    evasion multipliers are not folded in here (those only apply inside
    the real attack_phase resolution, not this feasibility estimate).
    """
    target = params.get("target", "any")
    indices = _opponent_indices(state, target)
    if not indices:
        return PredicateResult.not_computable(f"no opponent matches target '{target}'")
    lives = [state.opponents[i] for i in indices]
    remaining = min(lives) if target != "each" else max(lives)
    if remaining <= 0:
        return PredicateResult(satisfied=True, detail="target already at/below 0 life")

    entries = []  # (power, keywords, is_commander)
    for p in state.creatures():
        if getattr(p, "tapped", False):
            continue
        kws = ops.effective_keywords_in_state(p, state)
        power = ops.creature_power(p, state)
        if power > 0:
            entries.append((power, kws, bool(p.card.commander)))
    for g in state.creature_tokens:
        if g.count <= 0:
            continue
        if g.entered_turn == state.turn and "haste" not in set(g.keywords):
            continue
        power = ops.token_group_power(g, state) * g.count
        if power > 0:
            entries.append((power, set(g.keywords), False))

    if not entries:
        return PredicateResult(satisfied=False, detail="no creature able to attack this turn", progress=0.0)

    n_attackers = len(entries)
    profile, turn = strategy.opponent_profile, state.turn
    expected = 0.0
    for power, kws, is_cmd in entries:
        if "double strike" in kws:
            power *= 2.0
        rate = _combat_block_rate_for(profile, turn, n_attackers, kws, is_commander=is_cmd)
        expected += power * (1.0 - rate)

    ok = expected >= remaining
    progress = min(1.0, expected / remaining) if remaining > 0 else 1.0
    return PredicateResult(
        satisfied=ok,
        detail=(f"estimated damage after blockers {expected:.1f} vs {remaining:.1f} needed "
                f"(target={target}, current life, {n_attackers} potential attacker(s))"),
        progress=progress,
    )
