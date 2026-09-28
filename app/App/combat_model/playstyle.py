"""
Deck-wide play style (v4.77.0 WP-A): three per-deck sliders that shape how
readily ORDINARY creatures (no commander, no engine-ish role -- see
combat_model.posture._ENGINE_ROLES, which is untouched by this module and
stays the sole authority over the commander/engine gate) attack and block.

Motivation (user-reported, Lathril Elfball diagnosis, v4.76.0): 1/1 mana
elves were attacking and dying on offense every single turn with no real
upside (avg_died_in_combat_per_run ~1.7 for that deck), and before WP2
(v4.76.0) untapped creatures never blocked the abstract opponent pressure at
all. Commander Posture (posture.py) already solves the "should I attack"
question for the commander and engine-role creatures; this module gives the
REST of the board the same kind of say -- WITHOUT ever forbidding an attack
or a block outright, only shifting probabilities/thresholds, exactly like
the user asked for.

Three sliders, each 0..100, stored per deck in Decks/.deck_meta.json
alongside strategy tags (see web_server.py::_resolve_playstyle) and carried
on Strategy.playstyle (a plain dict; see ScenarioStrategy in engine.py and
apply_playstyle_override just above run_pipeline_v440):

  aggression          - how often a creature BELOW the attacker_selection
                        strength bar attacks anyway. 0 = never (outside an
                        alpha strike); 100 (default) = always, i.e. today's
                        unfiltered behavior.
  attacker_selection  - where that strength bar sits. 100 (default) = bar at
                        0 power, so no creature is ever "below" it (today's
                        behavior -- aggression is then moot); 0 = the bar
                        sits at attacker_selection_max_power (Data/Models/
                        combat_interaction_weights.json -> "playstyle"), so
                        only creatures at/above that power, or with an
                        evasion keyword, or tagged "finisher", clear it
                        unconditionally.
  block_willingness   - 50 (default) = today's fixed WP2 defense.py
                        constants exactly (chump_only_below_life from
                        combat_interaction_weights.json -> "defense",
                        protected creatures block only vs lethal, every
                        viable blocker is used). Above 50 blocks more
                        readily (higher chump threshold; protected
                        creatures may chump pre-lethal at 80+). Below 50
                        blocks less readily (lower chump threshold, and
                        only a willingness/50 share of the available
                        blockers is even considered, cut from the bottom of
                        an already toughness-sorted list so the sturdiest
                        blockers go first). Applied in
                        combat_model/defense.py, not here.

An "alpha strike" (a lethal team swing this turn, or a team-wide pump/anthem
active this turn -- e.g. Craterhoof, Ezuri, Overrun) always bypasses
aggression/attacker_selection: the sliders shape ordinary turns, never a
combo finish. See attack_phase's v4.77.0 wrapper in engine.py for how that
is detected and where creatures are actually held back (a pre-tap/hide
trick, the same one scenario_preserve_untapped already uses -- fully
additive, the unfiltered old attack_phase is never modified).

All threshold constants are disclosed first estimates (Data/Models/
combat_interaction_weights.json -> "playstyle"), same practice as
commander_targeting.block_bias / defense's own constants -- no external
reference data exists for "how strong does a creature need to be to always
attack".

Engine-agnostic on purpose (no `import engine`) -- callers pass their own
rng / creature data in.
"""
from __future__ import annotations

from typing import Any, Dict, Set

from .interaction import _WEIGHTS
from .posture import _ENGINE_ROLES

DEFAULT_PLAYSTYLE: Dict[str, float] = {
    "aggression": 100.0,
    "attacker_selection": 100.0,
    "block_willingness": 50.0,
}

_EVASION_KEYWORDS = {"flying", "menace", "trample"}
_ALWAYS_STRONG_ROLES = {"finisher"}


def _playstyle_weights() -> dict:
    return _WEIGHTS.get("playstyle", {"attacker_selection_max_power": 3.0})


def get(strategy: Any) -> Dict[str, float]:
    """``strategy.playstyle`` (a plain dict, possibly partial or absent),
    defaulted and clamped to [0, 100] per slider. A malformed or missing
    value for one slider falls back to that slider's own default rather
    than discarding the whole dict, so a partially-specified import (e.g.
    only "block_willingness" from an AI-authored scenario file) still
    works as intended."""
    raw = getattr(strategy, "playstyle", None) or {}
    out = dict(DEFAULT_PLAYSTYLE)
    for k, default in DEFAULT_PLAYSTYLE.items():
        try:
            v = float(raw.get(k, default))
        except (TypeError, ValueError):
            continue
        out[k] = max(0.0, min(100.0, v))
    return out


def is_gated(p: Any) -> bool:
    """Same commander/engine-role gate as posture.py::creature_should_attack
    (and attack_phase's own ``_is_gated``) -- a creature this module never
    touches; commander_posture stays the sole authority over it."""
    roles = getattr(p.card, "roles", set()) or set()
    return bool(p.card.commander) or bool(roles & _ENGINE_ROLES)


def attacker_strength_threshold(playstyle: Dict[str, float]) -> float:
    max_power = float(_playstyle_weights().get("attacker_selection_max_power", 3.0))
    return max(0.0, (100.0 - playstyle["attacker_selection"]) / 100.0) * max_power


def is_weak_attacker(power: float, keywords: Set[str], roles: Set[str], threshold: float) -> bool:
    """A creature below the current strength bar -- the ONLY ones
    aggression's roll applies to; everything else always attacks, same as
    before this module existed."""
    if threshold <= 0:
        return False
    if keywords & _EVASION_KEYWORDS:
        return False
    if roles & _ALWAYS_STRONG_ROLES:
        return False
    return power < threshold


def should_ordinary_creature_attack(
    rng: Any,
    playstyle: Dict[str, float],
    power: float,
    keywords: Set[str],
    roles: Set[str],
    alpha_strike: bool,
) -> bool:
    """Ordinary (``not is_gated``) creature only -- gated creatures are left
    to commander_posture entirely, unaffected by this function."""
    if alpha_strike:
        return True
    threshold = attacker_strength_threshold(playstyle)
    if not is_weak_attacker(power, keywords, roles, threshold):
        return True
    return bool(rng.random() < (playstyle["aggression"] / 100.0))
