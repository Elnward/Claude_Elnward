"""
Equipment model (WP7, Iteration 2; extended WP6/v4.15.3).

Scope, deliberately: attach/detach state (Permanent.attached_to), equip cost and
granted P/T-bonus/keywords parsed generically from Oracle text (no per-card
special-casing), a simple auto-equip heuristic, and (v4.15.3) two generic
"Whenever equipped creature ..." trigger families plus dynamic (counter-based)
P/T bonuses. Layered as SIMPLIFIED, not EXACT (see model_layer note below) -
it still does not implement:
  - Equipment tutoring/recursion (those are just normal tutor/recursion effects
    once an equipment card is a normal target - no new infrastructure needed there)
  - Valiant ("first time this creature becomes the target of a spell/ability you
    control each turn") - still planned as its own small module once Equip-as-
    targeting is wired into a "target event" concept; not yet present here.
  - Auto-equip (v4.29.0+) pays its Equip cost for real via find_payment/
    apply_payment, the same DP mana solver every spell/ability already pays
    through - mana is actually spent now (see auto_equip_step's own docstring
    for the v4.29.0 fix history). What remains simplified: `parse_equip_cost`
    still collapses a colored/hybrid Equip cost (rare in practice) to a plain
    generic-mana-value integer rather than a real colored requirement.
  - "Whenever one or more creatures die, put a _ counter on this Equipment"
    (e.g. Chainsaw) is wired ONLY to combat deaths (see
    `creature_death_equipment_triggers`, called once per combat with at least
    one death from `App/engine.py::attack_phase`) - deaths from spot removal,
    board wipes, or sacrifice outside combat do NOT increment these counters
    yet. A fully general hook would need every one of this engine's ~18
    separate "move to graveyard" call sites funneled through one place first;
    that is a larger refactor than this Equipment-scoped item, and is left as
    an explicit, documented boundary rather than silently half-implemented.

Engine-agnostic on purpose (no `import engine`), same pattern as the rest of
App/combat_model and App/keyword_library - callers pass `state`/`ops` as needed.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

_EQUIP_COST_RE = re.compile(r"equip(?:[^{\n]*?)\{([^}]*)\}", re.IGNORECASE)
_EQUIPPED_LINE_RE = re.compile(r"equipped creature[^.\n]*", re.IGNORECASE)
_EQUIPPED_BONUS_RE = re.compile(r"gets \+(\d+)/\+(\d+)", re.IGNORECASE)
_EQUIPPED_X_BONUS_RE = re.compile(r"gets \+(x|\d+)/\+(x|\d+)", re.IGNORECASE)
_X_DEFINITION_RE = re.compile(r"where x is the number of ([a-z]+) counters on this equipment", re.IGNORECASE)
_EQUIPPED_KEYWORDS_RE = re.compile(r"has ([a-z][a-z ,]*?)(?:\.|$)", re.IGNORECASE)

_KNOWN_KEYWORD_WORDS = (
    "flying", "first strike", "double strike", "deathtouch", "haste", "hexproof",
    "indestructible", "lifelink", "menace", "reach", "trample", "vigilance", "ward",
    "flash", "defender", "protection", "shroud",
)

# v4.15.3: two generic "Whenever equipped creature attacks/deals combat damage
# to a player, ..." trigger families, matched by effect shape (not card name) -
# real motivating cards from Decks/Mice with Swords.txt: Captain America's
# Shield ("Whenever equipped creature attacks, tap target creature defending
# player controls.") and Bloodforged Battle-Axe ("Whenever equipped creature
# deals combat damage to a player, create a token that's a copy of this
# Equipment."). Both are abstract-opponent-model approximations, same spirit as
# combat_interaction_weights.json's other single tunable probabilities: no real
# opposing creature exists to "tap", so the tap effect is approximated as a
# reduced block rate for THIS specific attacker instead (see
# equipment_attack_tap_multiplier / interaction.AttackerInfo.evasion_bonus_multiplier).
_ATTACK_TAP_TRIGGER_RE = re.compile(
    r"whenever equipped creature attacks,\s*tap target creature", re.IGNORECASE,
)
_ATTACK_DAMAGE_COPY_TRIGGER_RE = re.compile(
    r"whenever equipped creature deals combat damage to a player,.*?"
    r"create a token that('|’)s a copy of this equipment",
    re.IGNORECASE,
)
_DIES_COUNTER_TRIGGER_RE = re.compile(
    r"whenever one or more creatures die,?\s*put a ([a-z]+) counter on this equipment",
    re.IGNORECASE,
)


def parse_equip_cost(card: Any) -> Optional[int]:
    """Generic-mana-value of the (first) 'Equip {N}' cost, or None if unparseable/absent."""
    if not getattr(card, "is_equipment", False):
        return None
    m = _EQUIP_COST_RE.search(card.oracle_text or "")
    if not m:
        return None
    raw = m.group(1)
    try:
        return int(raw)
    except ValueError:
        # Colored/hybrid equip costs (rare) - count pip characters as a rough value.
        return len(re.findall(r"[WUBRGC0-9]", raw)) or None


def parse_equipment_bonus(card_or_permanent: Any) -> Tuple[float, float, Set[str]]:
    """(power_bonus, toughness_bonus, granted_keywords) an equipment statically
    grants. Accepts either a bare Card (static-only; the historical call shape,
    still used directly by tests) or an equipment Permanent - when a Permanent
    is passed, a dynamic "+X/+0"-style bonus (e.g. Chainsaw: "gets +X/+0, where
    X is the number of rev counters on this Equipment") resolves X from that
    Permanent's own `named_counters` (v4.15.3); a bare Card has no counters, so
    X resolves to 0 there, same as the old un-parseable behavior."""
    card = getattr(card_or_permanent, "card", card_or_permanent)
    counters: Dict[str, int] = getattr(card_or_permanent, "named_counters", {}) or {}
    text = card.oracle_text or ""
    power_bonus = toughness_bonus = 0.0
    granted: Set[str] = set()

    clause_match = _EQUIPPED_LINE_RE.search(text)
    if not clause_match:
        return power_bonus, toughness_bonus, granted
    clause = clause_match.group(0)

    m = _EQUIPPED_BONUS_RE.search(clause)
    if m:
        power_bonus, toughness_bonus = float(m.group(1)), float(m.group(2))
    else:
        mx = _EQUIPPED_X_BONUS_RE.search(clause)
        if mx:
            x_value = 0.0
            xdef = _X_DEFINITION_RE.search(clause) or _X_DEFINITION_RE.search(text)
            if xdef:
                x_value = float(counters.get(xdef.group(1).lower(), 0))
            p_raw, t_raw = mx.group(1), mx.group(2)
            power_bonus = x_value if p_raw.lower() == "x" else float(p_raw)
            toughness_bonus = x_value if t_raw.lower() == "x" else float(t_raw)

    m = _EQUIPPED_KEYWORDS_RE.search(clause)
    if m:
        fragment = m.group(1).lower()
        for kw in _KNOWN_KEYWORD_WORDS:
            if kw in fragment:
                granted.add(kw)
    return power_bonus, toughness_bonus, granted


def equipment_on(state: Any, creature) -> List[Any]:
    """All Equipment Permanents currently attached to `creature`."""
    return [
        eq for eq in state.battlefield
        if eq.card.is_equipment and eq.attached_to is creature
    ]


def equipment_power_bonus(state: Any, creature) -> float:
    return sum(parse_equipment_bonus(eq)[0] for eq in equipment_on(state, creature))


def equipment_toughness_bonus(state: Any, creature) -> float:
    return sum(parse_equipment_bonus(eq)[1] for eq in equipment_on(state, creature))


def equipment_granted_keywords(state: Any, creature) -> Set[str]:
    out: Set[str] = set()
    for eq in equipment_on(state, creature):
        out |= parse_equipment_bonus(eq)[2]
    return out


def equipment_attack_tap_multiplier(weights: Dict[str, Any], state: Any, creature) -> float:
    """v4.15.3: approximates "Whenever equipped creature attacks, tap target
    creature defending player controls" (e.g. Captain America's Shield) as a
    reduced block-rate multiplier for THIS attacker - see module docstring for
    why (no real opposing creature exists to tap in this abstraction). `weights`
    is the already-loaded combat_interaction_weights.json table (passed in by
    the caller, same pattern as interaction.py's own `_WEIGHTS`, to avoid a
    circular import between the two combat_model modules). Multiple qualifying
    Equipment on the same creature stack multiplicatively (each represents an
    independent tap effect), clamped to >= 0."""
    mult = 1.0
    default = weights.get("equipment", {}).get("attack_tap_trigger_block_rate_multiplier", 1.0)
    for eq in equipment_on(state, creature):
        if _ATTACK_TAP_TRIGGER_RE.search(eq.card.oracle_text or ""):
            mult *= default
    return max(0.0, mult)


def equipment_combat_damage_copy_triggers(state: Any, creature) -> List[Any]:
    """v4.15.3: cards attached to `creature` matching "Whenever equipped
    creature deals combat damage to a player, create a token that's a copy of
    this Equipment" (e.g. Bloodforged Battle-Axe). Returns the matching
    equipment Cards (one per qualifying Equipment; the caller is responsible
    for actually creating a new Permanent for each, once per instance of
    unblocked combat damage to a player - this function only identifies which
    equipment on the board currently has the trigger)."""
    return [
        eq.card for eq in equipment_on(state, creature)
        if _ATTACK_DAMAGE_COPY_TRIGGER_RE.search(eq.card.oracle_text or "")
    ]


def creature_death_equipment_triggers(state: Any) -> None:
    """v4.15.3: increments the named counter on every battlefield Equipment
    whose Oracle text reads "Whenever one or more creatures die, put a _
    counter on this Equipment" (e.g. Chainsaw's rev counter). Call ONCE per
    batch of deaths that are already known to have happened together (real
    rules: this triggers once per event, not once per creature) - currently
    only wired to combat deaths from `App/engine.py::attack_phase` (see the
    module docstring's boundary note: non-combat deaths are not covered yet)."""
    for eq in state.battlefield:
        if not eq.card.is_equipment:
            continue
        m = _DIES_COUNTER_TRIGGER_RE.search(eq.card.oracle_text or "")
        if m:
            eq.named_counters[m.group(1).lower()] += 1


def attach_equipment(state: Any, equipment, creature) -> None:
    """Attach `equipment` to `creature` (replaces any previous attachment of that equipment)."""
    equipment.attached_to = creature


def detach_if_creature_left(state: Any) -> None:
    """Equipment stays on the battlefield when its creature dies/leaves; only the
    attachment itself falls off. Call after any zone change that could have removed
    a creature (e.g. combat deaths, spot removal)."""
    battlefield_ids = {id(p) for p in state.battlefield}
    for eq in state.battlefield:
        if eq.card.is_equipment and eq.attached_to is not None:
            if id(eq.attached_to) not in battlefield_ids:
                eq.attached_to = None


def auto_equip_step(ops: Any, state: Any, strategy: Any) -> None:
    """
    Simplified precombat auto-equip: for each untapped, unattached Equipment the
    engine can afford, attach it to the best available creature (commander
    preferred, else highest current power) that isn't already wearing it.

    Simplification: `parse_equip_cost` already collapses a (rare) colored/hybrid
    Equip cost down to a plain generic-mana-value integer (see its own
    docstring), so this is not a full colored-mana payment plan for those rare
    cases - but as of v4.29.0 it IS a real payment: `ops.find_payment`/
    `ops.apply_payment` (the same DP mana solver every spell/activated ability
    pays through) are used with that integer as a pure generic cost, and the
    mana is actually spent. Before v4.29.0 this only checked
    `ops.available_mana_value(state, strategy) < cost` and never called
    find_payment/apply_payment at all - so the SAME mana could fund an
    unlimited number of Equip activations in one step, and was still fully
    available for casting spells afterward the same turn. Found via ChatGPT
    external review (Docs/README.md v4.29.0 entry) - substantially worse than
    the disclosed "not colored-accurate" simplification this docstring used to
    describe, since no mana was ever consumed at all.
    """
    detach_if_creature_left(state)

    creatures = [p for p in state.battlefield if p.card.is_creature]
    if not creatures:
        return

    def creature_priority(p):
        return (bool(p.card.commander), ops.creature_power(p, state))

    for eq in state.battlefield:
        if not eq.card.is_equipment or eq.attached_to is not None:
            continue
        cost = parse_equip_cost(eq.card)
        if cost is None:
            continue
        payment = ops.find_payment(state, strategy, cost, Counter())
        if payment is None:
            continue
        ops.apply_payment(state, payment, strategy)
        target = max(creatures, key=creature_priority)
        attach_equipment(state, eq, target)
        ops.record_impact(state, eq.card.name, "equip_activations", 1)
