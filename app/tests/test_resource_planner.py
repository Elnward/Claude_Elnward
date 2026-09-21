"""
Unit tests for App/resource_planner/planner.py (WP8, Part 1: the generic
resource-allocation planner).

These are pure, engine-agnostic tests of `plan_allocation` itself - no
GameState/Permanent/attack_phase involved. The real Katara/Waterbend
integration end-to-end (including the Vigilance-sequencing rule) is covered
separately in tests/test_waterbend.py; this file only has to reproduce the
two worked examples from the WP8 task brief and show that an "untap effect"
input measurably changes the planner's output, as requested.

Run from the project root:
    python -m unittest tests.test_resource_planner -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App.resource_planner import planner  # noqa: E402


def _waterbend_goal(n_attackers):
    """
    Damage = (N - k) * X, exactly the formula from the WP8 task brief: N
    attackers total, k of them tapped away to help fund X, leaving (N - k)
    creatures actually in combat, each now dealing X. This function does NOT
    include the "is it even worth activating" comparison against not
    activating at all - that lives in engine.maybe_use_waterbend, not in the
    abstract planner.
    """
    def goal(units: int, attackers_lost: int) -> float:
        return (n_attackers - attackers_lost) * units
    return goal


class WorkedExamplesFromTaskBriefTests(unittest.TestCase):
    """Reproduces the two example calculations the WP8 brief specified:
    N=10 attackers, R=10 free resources -> k=0, Damage=100.
    N=10 attackers, R=0 free resources (10 costly candidates instead) -> k=5, Damage=25.
    """

    def test_beispiel_a_all_resources_free_no_attacker_is_tapped(self):
        free = [
            planner.Resource(key=f"free{i}", type="creature", amount=1.0, costs_attacker=False)
            for i in range(10)
        ]
        # A handful of costly candidates are also on offer, to prove the
        # planner actually considers and rejects using them (k=0 is not just
        # "there was nothing else available").
        costly = [
            planner.Resource(key=f"atk{i}", type="creature", amount=1.0, costs_attacker=True)
            for i in range(5)
        ]
        action = planner.Action(key="waterbend", min_units=1)
        plan = planner.plan_allocation(free + costly, action, _waterbend_goal(n_attackers=10))

        self.assertIsNotNone(plan)
        self.assertEqual(plan.attackers_lost, 0, "k=0: no attacker should be tapped when 10 free resources already give the best X")
        self.assertEqual(plan.units, 10)
        self.assertEqual(plan.value, 100.0)

    def test_beispiel_b_no_free_resources_taps_half_the_attackers(self):
        # No free resources at all: every candidate costs an attacker.
        costly = [
            planner.Resource(key=f"atk{i}", type="creature", amount=1.0, costs_attacker=True)
            for i in range(10)
        ]
        action = planner.Action(key="waterbend", min_units=1)
        plan = planner.plan_allocation(costly, action, _waterbend_goal(n_attackers=10))

        self.assertIsNotNone(plan)
        # (10 - k) * k is maximized at k=5 (value 25); k=4 and k=6 both give 24.
        self.assertEqual(plan.attackers_lost, 5)
        self.assertEqual(plan.units, 5)
        self.assertEqual(plan.value, 25.0)

    def test_more_than_ten_costly_candidates_are_bounded_not_a_silent_truncation_error(self):
        # 15 costly candidates on offer: only the cheapest 10 are ever
        # considered (see planner.py module docstring / _MAX_EXHAUSTIVE_COSTLY).
        # This just pins that documented bound so it can't silently drift.
        costly = [
            planner.Resource(key=f"atk{i}", type="creature", amount=1.0, costs_attacker=True, opportunity_cost=float(i))
            for i in range(15)
        ]
        action = planner.Action(key="waterbend", min_units=1)
        plan = planner.plan_allocation(costly, action, _waterbend_goal(n_attackers=10))
        self.assertIsNotNone(plan)
        self.assertLessEqual(plan.attackers_lost, planner._MAX_EXHAUSTIVE_COSTLY)


class NoViableAllocationTests(unittest.TestCase):
    def test_no_resources_at_all_returns_none(self):
        action = planner.Action(key="waterbend", min_units=1)
        plan = planner.plan_allocation([], action, _waterbend_goal(n_attackers=3))
        self.assertIsNone(plan)

    def test_min_units_not_reachable_returns_none(self):
        free = [planner.Resource(key="only-one", amount=1.0, costs_attacker=False)]
        action = planner.Action(key="waterbend", min_units=5)  # can't reach 5 with only 1 unit available
        plan = planner.plan_allocation(free, action, _waterbend_goal(n_attackers=3))
        self.assertIsNone(plan)

    def test_max_units_caps_the_plan(self):
        free = [
            planner.Resource(key=f"free{i}", amount=1.0, costs_attacker=False)
            for i in range(10)
        ]
        action = planner.Action(key="waterbend", min_units=1, max_units=4)
        plan = planner.plan_allocation(free, action, _waterbend_goal(n_attackers=1))
        self.assertEqual(plan.units, 4)


class UntapEffectChangesTheOptimalSolutionTests(unittest.TestCase):
    """
    WP8 brief: "Untap effects (e.g. Dramatic Reversal) should measurably
    affect the opportunity cost calculation (bounded/simplified acceptable)."

    Modeled here, at the abstract planner level, as one specific costly
    resource whose true opportunity_cost is lower than its peers because an
    untap effect will restore it before it's actually missed (a simplified
    stand-in for "this creature gets untapped again by Dramatic Reversal
    before end of turn, so tapping it for Waterbend was nearly free"). The
    planner sorts costly candidates by (opportunity_cost - future_value), so
    giving one candidate a cheaper net cost should measurably change WHICH
    resources end up in the plan, even when the winning k (how many) stays
    the same - i.e. the untap effect changes the *solution*, not just a
    number nobody uses.
    """

    def test_cheaper_resource_from_an_untap_effect_is_preferred_over_earlier_ones(self):
        # 6 same-amount costly candidates, all equal cost except the last one
        # ("r5"), which stands in for a creature that gets untapped again -
        # its real cost is 0, not 1. max_units=3 so, once 3 units is reached,
        # additional k cannot improve the goal - isolating which THREE
        # resources get chosen rather than how many.
        plain = [
            planner.Resource(key=f"r{i}", amount=1.0, costs_attacker=True, opportunity_cost=1.0)
            for i in range(5)
        ]
        untap_assisted = planner.Resource(
            key="r5", amount=1.0, costs_attacker=True, opportunity_cost=0.0,
        )
        action = planner.Action(key="waterbend", min_units=1, max_units=3)

        def flat_goal(units, _attackers_lost):
            return units  # ignore attackers_lost so *which* resources are picked is decided purely by sort order

        without_untap = planner.plan_allocation(plain, action, flat_goal)
        with_untap = planner.plan_allocation(plain + [untap_assisted], action, flat_goal)

        without_keys = {r.key for r in without_untap.used_resources}
        with_keys = {r.key for r in with_untap.used_resources}

        self.assertEqual(without_untap.units, 3)
        self.assertEqual(with_untap.units, 3)
        self.assertNotIn("r5", without_keys, "sanity check: r5 doesn't exist in the baseline run")
        self.assertIn("r5", with_keys, "the untap-assisted resource should now be preferred over one of the plain ones")
        self.assertNotEqual(
            without_keys, with_keys,
            "the untap effect should measurably change which resources make up the optimal plan",
        )


class FutureValueIsACostNotADiscountTests(unittest.TestCase):
    """
    v4.32.0: `future_value` ("value of leaving this resource unspent") is a
    COST of spending, on top of `opportunity_cost` - the planner must sort
    costly candidates by (opportunity_cost + future_value), never
    (opportunity_cost - future_value).

    Found via ChatGPT external review (see Docs/README.md v4.32.0 entry).
    Reproduced on the live pre-fix code: a resource with a much higher
    future_value than its peers (very valuable to keep unspent) got a LOWER
    sort key via subtraction and was wrongly preferred as the "cheapest" pick
    first, exactly backwards from what "value of leaving it unspent" means.
    """

    def test_high_future_value_resource_is_not_spent_before_a_cheaper_one(self):
        # Same opportunity_cost for both - only future_value differs.
        precious = planner.Resource(
            key="precious", amount=1.0, costs_attacker=True,
            opportunity_cost=1.0, future_value=10.0,
        )
        disposable = planner.Resource(
            key="disposable", amount=1.0, costs_attacker=True,
            opportunity_cost=1.0, future_value=0.0,
        )
        action = planner.Action(key="waterbend", min_units=1, max_units=1)

        def flat_goal(units, _attackers_lost):
            return units  # decide purely by sort order, like the untap test above

        plan = planner.plan_allocation([precious, disposable], action, flat_goal)

        used_keys = {r.key for r in plan.used_resources}
        self.assertIn("disposable", used_keys)
        self.assertNotIn(
            "precious", used_keys,
            "the resource with the higher future_value (more valuable to keep "
            "unspent) must not be spent ahead of a strictly cheaper one",
        )


class MaxUnitsDoesNotOverConsumeFreeResourcesTests(unittest.TestCase):
    """
    v4.32.0: when Action.max_units caps `units` below what the free resources
    alone already provide, `used_resources` must only contain as many free
    resources as the capped plan actually needs - not the entire free list.

    Found via ChatGPT external review (see Docs/README.md v4.32.0 entry).
    Reproduced on the live pre-fix code: `used_resources = list(free) +
    chosen_costly` unconditionally included every free resource, so a plan
    capped to 4 units by max_units still reported (and, in the real
    engine.py::maybe_use_waterbend integration, actually TAPPED) all 10 free
    resources instead of only the 4 it needed.
    """

    def test_only_as_many_free_resources_as_units_needs_are_used(self):
        free = [
            planner.Resource(key=f"free{i}", amount=1.0, costs_attacker=False)
            for i in range(10)
        ]
        action = planner.Action(key="waterbend", min_units=1, max_units=4)
        plan = planner.plan_allocation(free, action, _waterbend_goal(n_attackers=1))

        self.assertEqual(plan.units, 4)
        self.assertEqual(
            len(plan.used_resources), 4,
            "only 4 of the 10 free resources were actually needed to reach "
            "the max_units=4 cap - the rest must not appear in used_resources",
        )

    def test_costly_resources_are_unaffected_by_the_free_trim(self):
        # 2 free + 3 costly, capped to 3 units: the plan should still be free
        # to choose costly candidates - trimming must only ever touch the
        # free list, never the costly prefix that goal_fn actually scored.
        free = [
            planner.Resource(key=f"free{i}", amount=1.0, costs_attacker=False)
            for i in range(2)
        ]
        costly = [
            planner.Resource(key=f"costly{i}", amount=1.0, costs_attacker=True, opportunity_cost=float(i))
            for i in range(3)
        ]
        action = planner.Action(key="waterbend", min_units=1, max_units=3)
        plan = planner.plan_allocation(free + costly, action, _waterbend_goal(n_attackers=5))

        used_keys = {r.key for r in plan.used_resources}
        self.assertEqual(plan.units, 3)
        self.assertEqual({"free0", "free1"}, {k for k in used_keys if k.startswith("free")})
        self.assertEqual(1, len([k for k in used_keys if k.startswith("costly")]))


if __name__ == "__main__":
    unittest.main()
