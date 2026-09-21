"""
Generic resource-allocation planner (WP8).

Goal: a reusable "spend variable resources against an optimization goal"
building block - not only for Waterbend, but longer-term also for Convoke,
Improvise, Crew, Aziza's copy cost, equip decisions (see COWORK_HANDOFF.md
section 6 / the original WP8 task brief). Engine-agnostic: no `import engine`
here (circular import) - same pattern as combat_model/keyword_library/
scenario_predicates. The engine module ("ops") is passed in by the caller when
a concrete integration needs engine primitives; this module itself only needs
plain data.

Model quality (said out loud, no false precision):
- No multi-turn lookahead. `opportunity_cost` / `future_value` on a Resource
  are single numbers the CALLER assigns for THIS decision point - not an
  independent simulation of what happens next turn.
- The search is a bounded/small exhaustive search: candidate resources that
  cost something (see `costs_attacker` below) are pre-sorted by net cost and
  capped at `_MAX_EXHAUSTIVE_COSTLY` (10) before searching, per the WP8 brief
  ("Kandidatenreduktion... bounded/kleine exhaustive search bei <=10 relevanten
  Ressourcen"). With more than 10 relevant costly candidates, only the
  cheapest 10 are ever considered - this is a disclosed scope limit, not a
  silent truncation; callers with larger boards should be aware the true
  optimum could theoretically use an 11th-cheapest resource in rare ties.
- "costs_attacker" is a generic name for "this resource is not free to spend
  from the goal function's point of view" - the Waterbend integration in
  App/engine.py uses it for creatures that would actually lose their attack,
  which, thanks to Vigilance sequencing (see maybe_use_waterbend), turns out
  to be none of the real candidates it ever offers - see
  tests/test_resource_planner.py for the abstract case where it matters, and
  tests/test_waterbend.py for why it doesn't in the real integration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence

_MAX_EXHAUSTIVE_COSTLY = 10


@dataclass
class Resource:
    """One thing that could be spent toward an action's cost."""
    key: str
    type: str = "generic"          # "mana" | "artifact" | "creature" | ...
    amount: float = 1.0            # how many cost-units this resource pays for if used
    costs_attacker: bool = False   # True if spending it has a goal-relevant cost THIS decision
    opportunity_cost: float = 0.0  # caller-supplied value given up by spending it
    future_value: float = 0.0      # caller-supplied value of leaving it unspent
    ref: Any = None                # opaque reference the caller can act on (e.g. a Permanent)


@dataclass
class Action:
    """One thing resources can be spent on."""
    key: str
    min_units: int = 0
    max_units: Optional[int] = None   # None = unbounded (capped by available resources)


@dataclass
class AllocationPlan:
    action_key: str
    units: int
    used_resources: List[Resource]
    value: float
    attackers_lost: int


def plan_allocation(
    resources: Sequence[Resource],
    action: Action,
    goal_fn: Callable[[int, int], float],
) -> Optional[AllocationPlan]:
    """
    Decide how many resource units to commit to `action`, and which specific
    resources fund it, maximizing `goal_fn(units, attackers_lost)`.

    Free resources (costs_attacker=False) are always fully used - there is
    never a reason to withhold something with zero modeled cost when the goal
    is monotonically non-decreasing in units, which is the only kind of goal
    this planner is currently asked to optimize. Costly resources are added in
    increasing order of (opportunity_cost + future_value), one at a time,
    trying every prefix (k = 0..len(costly)) and keeping whichever k scores
    highest under goal_fn - this is the "small bounded search" the WP8 brief
    asks for, not a brute-force search over all subsets (subsets of the same
    size and homogeneous per-unit amount are interchangeable for goal_fn, so
    trying every subset would waste time without changing the answer).

    `future_value` is "the value of leaving this resource unspent" (see the
    Resource docstring) - i.e. it is itself a COST of spending the resource,
    on top of `opportunity_cost`, not a discount against it. A candidate that
    is cheap to spend right now (low opportunity_cost) but very valuable to
    keep unspent (high future_value) is a worse pick than one that is cheap on
    both counts, so the two are ADDED for the sort key, never subtracted -
    see tests/test_resource_planner.py's FutureValueIsACostNotADiscountTests
    for the worked case where this previously picked the wrong resource.
    """
    free = [r for r in resources if not r.costs_attacker]
    costly_all = [r for r in resources if r.costs_attacker]
    costly = sorted(
        costly_all, key=lambda r: r.opportunity_cost + r.future_value,
    )[:_MAX_EXHAUSTIVE_COSTLY]

    free_total = sum(r.amount for r in free)
    best: Optional[AllocationPlan] = None

    for k in range(0, len(costly) + 1):
        chosen_costly = costly[:k]
        raw_units = free_total + sum(r.amount for r in chosen_costly)
        units = int(raw_units)
        if action.max_units is not None:
            units = min(units, action.max_units)
        if units < action.min_units:
            continue
        value = goal_fn(units, k)
        if best is None or value > best.value:
            # `units` may have been capped below what `free` alone already
            # provides (Action.max_units) - only report/consume as many free
            # resources as the plan actually needs, not the entire free list
            # unconditionally. Costly resources are left as the exact
            # `chosen_costly` prefix that produced `value` above, since
            # trimming those after the fact would make the returned
            # `attackers_lost` disagree with the k that goal_fn actually
            # scored (see tests/test_resource_planner.py
            # MaxUnitsDoesNotOverConsumeFreeResourcesTests).
            free_needed: List[Resource] = []
            free_used_total = 0.0
            for r in free:
                if free_used_total >= units:
                    break
                free_needed.append(r)
                free_used_total += r.amount
            best = AllocationPlan(
                action_key=action.key,
                units=units,
                used_resources=free_needed + chosen_costly,
                value=value,
                attackers_lost=k,
            )
    return best
