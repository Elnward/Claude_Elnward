"""
Abstract combat interaction function (v4.7.5, "Iteration 1").

Replaces the flat per-turn `block_factor` damage multiplier with a per-attacker
stochastic roll: blocked-and-traded (attacker dies), blocked-and-chumped (attacker
survives, 0 damage), or unblocked (full damage). This is deliberately NOT a real
blocker simulation - there is no opposing board of named creatures. It is a weighted
random function, same spirit as the existing OPPONENT_PROFILES abstraction, just
resolved per attacker instead of as one flat multiplier for the whole combat.

Weights live in Data/Models/combat_interaction_weights.json so they can be tuned
without touching this file.

WP6, Iteration 2+ (v4.15.1): `commander_targeting.block_bias` applies a flat,
always-on multiplier to a commander attacker's block rate ("the commander
painted a target on itself"), independent of and stacking with the existing
impact-based `importance_targeting.combat_block_weight` bonus - see
`_commander_block_bias` below.

WP6 (v4.15.2): `first_strike.trade_rate_multiplier` approximates the two-stage
first-strike/regular-damage-step rule for a BLOCKED attacker with `first
strike` or `double strike` - see `_first_strike_trade_rate_multiplier` below.
`double strike` continues to double an UNBLOCKED attacker's damage, unchanged
since v4.7.5.

WP6 (v4.15.3): `AttackerInfo.equipment_evasion_multiplier` lets the caller
(App/engine.py::attack_phase) fold in an equipment "Whenever equipped creature
attacks, tap target creature ..." trigger as a per-attacker block-rate
reduction - see `App/combat_model/equipment.py::equipment_attack_tap_multiplier`.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_WEIGHTS_PATH = Path(__file__).resolve().parent.parent.parent / "Data" / "Models" / "combat_interaction_weights.json"

_EVASION_KEYWORDS = ("flying", "menace", "trample")


@dataclass
class AttackerInfo:
    """One attacker's inputs to the interaction function."""
    name: str
    power: float
    lifelink: bool
    keywords: Set[str]
    is_commander: bool = False
    source_kind: str = "permanent"   # "permanent" | "token_group"
    source_ref: Any = None           # Permanent or TokenGroup, for the caller to act on death
    # v4.15.3: multiplier on this attacker's block_rate from equipment with a
    # "Whenever equipped creature attacks, tap target creature ..." trigger
    # (see equipment.py::equipment_attack_tap_multiplier) - computed once by the
    # caller (App/engine.py::attack_phase) before combat resolution, since only
    # the caller knows which Permanent this attacker came from and what is
    # attached to it. 1.0 = no such equipment (default, unaffected).
    equipment_evasion_multiplier: float = 1.0
    # v4.24.0: how many real attacking creatures this ONE AttackerInfo entry
    # represents on the actual board, for wide_board's soft-cap/decay math
    # (see _wide_board_multiplier below). A token group of e.g. 10 Soldiers
    # is still resolved as a single block/no-block roll (unchanged - see
    # App/engine.py::attack_phase's "v4.24.0: token groups" comment for why
    # a full per-token block simulation is out of scope), but the group is
    # still 10 real attackers as far as an opponent deciding how thin their
    # blockers are spread is concerned. Defaults to 1.0 (a lone Permanent is
    # exactly one attacker); App/engine.py sets this to the token group's
    # `count` when building a token-group AttackerInfo.
    attack_weight: float = 1.0
    # v4.82.0 ("Runde 4", keyword_effects.py): Farben des Angreifers
    # (Intimidate) und aus dem Oracle-Text geparste seltene Kampf-Keywords
    # (Fear/Intimidate/Shadow/Landwalk/Protection-Farben/Flanking/...), die
    # `keywords` (nur KNOWN_KEYWORDS) nicht fuehrt. Beide bleiben leer, solange
    # der Aufrufer sie nicht setzt -> exakt altes Verhalten.
    colors: Set[str] = field(default_factory=set)
    combat_extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttackOutcome:
    name: str
    damage_dealt: float
    blocked: bool
    died: bool
    lifelink_gain: float
    source_kind: str = "permanent"
    source_ref: Any = None
    is_commander: bool = False


def _load_weights(path: Path = _WEIGHTS_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_WEIGHTS = _load_weights()


def reload_weights() -> None:
    global _WEIGHTS
    _WEIGHTS = _load_weights()


def _turn_ramp_multiplier(turn: int) -> float:
    ramp = _WEIGHTS["turn_ramp"]
    start_turn, max_turn = ramp["start_turn"], ramp["max_turn"]
    start_mult, max_mult = ramp["start_multiplier"], ramp["max_multiplier"]
    if turn <= start_turn:
        return start_mult
    if turn >= max_turn:
        return max_mult
    frac = (turn - start_turn) / max(1, (max_turn - start_turn))
    return start_mult + frac * (max_mult - start_mult)


def _wide_board_multiplier(n_attackers: int) -> float:
    wb = _WEIGHTS["wide_board"]
    soft_cap = wb["soft_cap_attackers"]
    if n_attackers <= soft_cap:
        return 1.0
    extra = n_attackers - soft_cap
    mult = wb["decay_per_extra_attacker"] ** extra
    return max(wb["min_multiplier"], mult)


def _evasion_multiplier(keywords: Set[str]) -> float:
    mult = 1.0
    table = _WEIGHTS["evasion_keyword_multiplier"]
    for kw in _EVASION_KEYWORDS:
        if kw in keywords:
            mult *= table.get(kw, 1.0)
    return mult


def _profile_weights(profile_name: str) -> Dict[str, float]:
    profiles = _WEIGHTS["profiles"]
    if profile_name in profiles:
        return profiles[profile_name]
    return profiles.get("goldfish", {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0})


_FIRST_STRIKE_TIMING_KEYWORDS = ("first strike", "double strike")


def _first_strike_trade_rate_multiplier(keywords: Set[str]) -> float:
    """WP6 (open since first_strike/double_strike were added to KEYWORDS/the
    value model - `first strike` itself had ZERO effect on combat resolution
    until this function, only a value-model weight; `double strike` only
    doubled UNBLOCKED damage). This module has no explicit opposing-blocker
    stats to run a real two-combat-damage-step simulation against, so the
    two-stage rule ("deals its damage before a normal-timing blocker can hit
    back, and can kill that blocker before it ever strikes") is approximated
    as a flat reduction on `trade_rate_given_blocked` - a first-strike-timing
    attacker is less likely to die when blocked, because a real first-strike
    or double-strike attacker often kills its blocker in the first damage
    step before the blocker deals any damage at all. `double strike` gets the
    SAME reduction as plain `first strike` here: the extra second hit only
    matters if the blocker survives the first step, which is independent of
    whether the ATTACKER itself survives - that is decided entirely by the
    first-strike-timing step, identical for both keywords. First-guess
    starting constant (Data/Models/combat_interaction_weights.json,
    `first_strike.trade_rate_multiplier`, default 0.5) - no external reference
    data exists for this, same "clearly-labeled first guess" treatment as
    `commander_targeting.block_bias`/`x_spell_proximity_bonus_max`."""
    if not (set(keywords) & set(_FIRST_STRIKE_TIMING_KEYWORDS)):
        return 1.0
    return _WEIGHTS.get("first_strike", {}).get("trade_rate_multiplier", 1.0)


def _commander_block_bias() -> float:
    """WP6, Iteration 2+ (open since v4.7.5: 'the commander painted a target on
    itself'). A commander is public information from turn 1 (command zone, usually
    the deck's central piece) - the opponent recognizes it as a priority block
    target independent of whether it has already shown measurable live-run impact
    (that is what `importance_targeting.combat_block_weight` measures separately,
    and it only ramps up once the commander HAS done something this run). This is a
    flat, always-on multiplier instead, applied only to the commander attacker.
    First-guess starting constant (Data/Models/combat_interaction_weights.json,
    `commander_targeting.block_bias`, default 1.25) - no external reference data
    exists for this, same "clearly-labeled first guess" treatment as
    x_spell_proximity_bonus_max/value_curve_exponents."""
    return _WEIGHTS.get("commander_targeting", {}).get("block_bias", 1.0)


def block_rate_for(
    profile_name: str, turn: int, n_attackers: int, keywords: Set[str], is_commander: bool = False,
    *, context: Any = None, attacker: Optional["AttackerInfo"] = None,
) -> float:
    """v4.82.0: `context` (keyword_effects.KeywordCombatContext) ersetzt den
    flachen _evasion_multiplier durch das farbabhaengige Keyword-Modell.
    context=None (Default) -> byte-identisch zum alten Verhalten."""
    profile = _profile_weights(profile_name)
    base = profile.get("block_rate_base", 0.0)
    if base <= 0:
        return 0.0
    if context is not None:
        from . import keyword_effects as _kwe  # local import: keyword_effects imports this module
        evasion = _kwe.attack_block_multiplier(
            keywords,
            getattr(attacker, "combat_extras", {}) or {},
            getattr(attacker, "colors", set()) or set(),
            context,
        )
    else:
        evasion = _evasion_multiplier(keywords)
    rate = base * _turn_ramp_multiplier(turn) * _wide_board_multiplier(n_attackers) * evasion
    if is_commander:
        rate *= _commander_block_bias()
    return max(0.0, min(1.0, rate))


def resolve_combat_interaction(
    profile_name: str,
    turn: int,
    attackers: List[AttackerInfo],
    rng: random.Random,
    *,
    state: Any = None,
) -> List[AttackOutcome]:
    """
    Resolve one combat's worth of attackers against an abstract opponent profile.
    Deterministic given `rng` (caller supplies the seeded engine rng).

    `state` is optional and, if supplied, enables importance-weighted block-rate
    (see importance.py): an attacker that has already proven impactful this run
    gets a somewhat higher chance of being blocked, on top of the base weights.
    """
    profile = _profile_weights(profile_name)
    trade_rate = profile.get("trade_rate_given_blocked", 0.0)
    # v4.24.0: wide_board's soft-cap/decay is meant to measure how many real
    # attacking creatures are on the board (see docstring above and
    # _wide_board_multiplier) - sum each entry's attack_weight (1.0 for a
    # lone Permanent, a token group's `count` for a token-group entry)
    # rather than just len(attackers), so a 10-token group doesn't silently
    # count as "1 attacker" for this purpose.
    n = sum(getattr(a, "attack_weight", 1.0) for a in attackers)
    outcomes: List[AttackOutcome] = []

    all_names = [a.name for a in attackers]
    # v4.82.0: farbabhaengiges Keyword-Modell (keyword_effects.py), vom
    # Aufrufer ueber state._kw_combat_ctx gesetzt - fehlt es, laeuft alles
    # exakt wie vor v4.82.0.
    kw_ctx = getattr(state, "_kw_combat_ctx", None) if state is not None else None
    if kw_ctx is not None:
        from . import keyword_effects as _kwe

    for a in attackers:
        rate = block_rate_for(profile_name, turn, n, a.keywords, is_commander=a.is_commander,
                              context=kw_ctx, attacker=a)
        if rate > 0 and a.equipment_evasion_multiplier != 1.0:
            rate = max(0.0, min(1.0, rate * a.equipment_evasion_multiplier))
        if state is not None and rate > 0:
            from . import importance as _importance  # local import: avoids a module-load-order dependency
            rate = min(1.0, rate * _importance.combat_block_multiplier(state, a.name, all_names))
        blocked = rate > 0 and rng.random() < rate
        if not blocked:
            damage = a.power * 2.0 if "double strike" in a.keywords else a.power
            outcomes.append(AttackOutcome(
                name=a.name, damage_dealt=damage, blocked=False, died=False,
                lifelink_gain=(damage if a.lifelink else 0.0),
                source_kind=a.source_kind, source_ref=a.source_ref,
                is_commander=a.is_commander,
            ))
            continue

        effective_trade_rate = max(0.0, min(1.0, trade_rate * _first_strike_trade_rate_multiplier(a.keywords)))
        excess = 0.0
        if kw_ctx is not None:
            effective_trade_rate *= _kwe.trade_rate_multiplier(a.combat_extras or {})
            # Trample: Ueberschussschaden eines GEBLOCKTEN Tramplers geht zum
            # Spieler durch (ersetzt im Keyword-Modell den alten flachen
            # evasion_keyword_multiplier.trample-Faktor).
            excess = _kwe.trample_excess(a.power, a.keywords, kw_ctx)
        died = rng.random() < effective_trade_rate
        outcomes.append(AttackOutcome(
            name=a.name, damage_dealt=excess, blocked=True, died=died,
            lifelink_gain=(excess if a.lifelink else 0.0), source_kind=a.source_kind, source_ref=a.source_ref,
            is_commander=a.is_commander,
        ))

    return outcomes
