"""
v4.77.0 WP-A: deck-wide play style (App/combat_model/playstyle.py) -- pure
module-level tests, plus the engine-side wiring (ScenarioStrategy.playstyle,
apply_playstyle_override, run_pipeline_v440's new kwarg).

Run from the project root:
    python -m unittest tests.test_v4770_playstyle -v
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from App import engine as E  # noqa: E402
from App.combat_model import playstyle  # noqa: E402


class _Strategy:
    def __init__(self, playstyle=None):
        self.playstyle = playstyle


class GetDefaultsAndClampingTests(unittest.TestCase):
    def test_missing_attribute_returns_defaults(self):
        self.assertEqual(playstyle.get(object()), dict(playstyle.DEFAULT_PLAYSTYLE))

    def test_none_returns_defaults(self):
        self.assertEqual(playstyle.get(_Strategy(None)), dict(playstyle.DEFAULT_PLAYSTYLE))

    def test_empty_dict_returns_defaults(self):
        self.assertEqual(playstyle.get(_Strategy({})), dict(playstyle.DEFAULT_PLAYSTYLE))

    def test_partial_dict_defaults_the_rest(self):
        out = playstyle.get(_Strategy({"block_willingness": 90}))
        self.assertEqual(out["block_willingness"], 90.0)
        self.assertEqual(out["aggression"], playstyle.DEFAULT_PLAYSTYLE["aggression"])
        self.assertEqual(out["attacker_selection"], playstyle.DEFAULT_PLAYSTYLE["attacker_selection"])

    def test_out_of_range_values_are_clamped(self):
        out = playstyle.get(_Strategy({"aggression": -50, "attacker_selection": 500}))
        self.assertEqual(out["aggression"], 0.0)
        self.assertEqual(out["attacker_selection"], 100.0)

    def test_malformed_value_falls_back_to_default_for_that_slider_only(self):
        out = playstyle.get(_Strategy({"aggression": "not-a-number", "block_willingness": 10}))
        self.assertEqual(out["aggression"], playstyle.DEFAULT_PLAYSTYLE["aggression"])
        self.assertEqual(out["block_willingness"], 10.0)


class IsGatedTests(unittest.TestCase):
    def _perm(self, **kw):
        card = E.Card(name="X", roles=set(), commander=False)
        for k, v in kw.items():
            setattr(card, k, v)
        return E.Permanent(card=card, entered_turn=1)

    def test_commander_is_gated(self):
        self.assertTrue(playstyle.is_gated(self._perm(commander=True)))

    def test_engine_role_is_gated(self):
        self.assertTrue(playstyle.is_gated(self._perm(roles={"engine"})))

    def test_ordinary_creature_is_not_gated(self):
        self.assertFalse(playstyle.is_gated(self._perm(roles={"ramp"})))


class StrengthThresholdTests(unittest.TestCase):
    def test_selection_100_gives_zero_threshold(self):
        ps = playstyle.get(_Strategy({"attacker_selection": 100}))
        self.assertEqual(playstyle.attacker_strength_threshold(ps), 0.0)

    def test_selection_0_gives_max_threshold(self):
        ps = playstyle.get(_Strategy({"attacker_selection": 0}))
        max_power = playstyle._playstyle_weights()["attacker_selection_max_power"]
        self.assertAlmostEqual(playstyle.attacker_strength_threshold(ps), max_power)

    def test_selection_50_is_halfway(self):
        ps = playstyle.get(_Strategy({"attacker_selection": 50}))
        max_power = playstyle._playstyle_weights()["attacker_selection_max_power"]
        self.assertAlmostEqual(playstyle.attacker_strength_threshold(ps), max_power / 2.0)


class IsWeakAttackerTests(unittest.TestCase):
    def test_zero_threshold_nothing_is_weak(self):
        self.assertFalse(playstyle.is_weak_attacker(0.1, set(), set(), 0.0))

    def test_low_power_below_threshold_is_weak(self):
        self.assertTrue(playstyle.is_weak_attacker(1.0, set(), set(), 3.0))

    def test_power_at_or_above_threshold_is_not_weak(self):
        self.assertFalse(playstyle.is_weak_attacker(3.0, set(), set(), 3.0))

    def test_evasive_creature_is_never_weak(self):
        self.assertFalse(playstyle.is_weak_attacker(1.0, {"flying"}, set(), 3.0))
        self.assertFalse(playstyle.is_weak_attacker(1.0, {"menace"}, set(), 3.0))
        self.assertFalse(playstyle.is_weak_attacker(1.0, {"trample"}, set(), 3.0))

    def test_finisher_role_is_never_weak(self):
        self.assertFalse(playstyle.is_weak_attacker(1.0, set(), {"finisher"}, 3.0))


class ShouldOrdinaryCreatureAttackTests(unittest.TestCase):
    def test_alpha_strike_always_attacks_regardless_of_sliders(self):
        ps = playstyle.get(_Strategy({"aggression": 0, "attacker_selection": 0}))
        self.assertTrue(playstyle.should_ordinary_creature_attack(random.Random(1), ps, 1.0, set(), set(), True))

    def test_strong_creature_always_attacks(self):
        ps = playstyle.get(_Strategy({"aggression": 0, "attacker_selection": 0}))
        self.assertTrue(playstyle.should_ordinary_creature_attack(random.Random(1), ps, 10.0, set(), set(), False))

    def test_weak_creature_never_attacks_at_zero_aggression(self):
        ps = playstyle.get(_Strategy({"aggression": 0, "attacker_selection": 0}))
        for seed in range(10):
            self.assertFalse(
                playstyle.should_ordinary_creature_attack(random.Random(seed), ps, 1.0, set(), set(), False)
            )

    def test_weak_creature_always_attacks_at_full_aggression(self):
        ps = playstyle.get(_Strategy({"aggression": 100, "attacker_selection": 0}))
        for seed in range(10):
            self.assertTrue(
                playstyle.should_ordinary_creature_attack(random.Random(seed), ps, 1.0, set(), set(), False)
            )

    def test_default_playstyle_always_attacks(self):
        ps = playstyle.get(_Strategy(None))
        for seed in range(10):
            self.assertTrue(
                playstyle.should_ordinary_creature_attack(random.Random(seed), ps, 0.5, set(), set(), False)
            )


class EngineWiringTests(unittest.TestCase):
    def test_scenario_strategy_playstyle_defaults_to_empty_dict(self):
        self.assertEqual(E.ScenarioStrategy().playstyle, {})

    def test_apply_playstyle_override_none_leaves_untouched(self):
        strategy = E.ScenarioStrategy(playstyle={"aggression": 10})
        E.apply_playstyle_override(strategy, None)
        self.assertEqual(strategy.playstyle, {"aggression": 10})

    def test_apply_playstyle_override_sets_dict(self):
        strategy = E.ScenarioStrategy()
        E.apply_playstyle_override(strategy, {"block_willingness": 80})
        self.assertEqual(strategy.playstyle, {"block_willingness": 80})

    def test_apply_playstyle_override_copies_not_aliases(self):
        strategy = E.ScenarioStrategy()
        src = {"aggression": 10}
        E.apply_playstyle_override(strategy, src)
        src["aggression"] = 999
        self.assertEqual(strategy.playstyle["aggression"], 10)


if __name__ == "__main__":
    unittest.main()
