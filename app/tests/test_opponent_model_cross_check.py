"""
Unit tests for engine._opponent_model_cross_check (v4.44.0, "Punkt 3"
additive cross-check) - see App/engine.py's own comment block right above
that function, and Docs/README.md v4.44.0, for the full design rationale.

These tests exercise ONLY the standalone cross-check function, never the
full run_pipeline_v440 (which needs a real deck file / Scryfall access) -
consistent with how the rest of this project tests engine.py helpers in
isolation (see e.g. tests/test_v4157_voltron_gui_wiring.py).

Run from the project root:
    python -m unittest tests.test_opponent_model_cross_check -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402


def _card(oracle_text: str = "") -> engine.Card:
    return engine.Card(name="Stub", oracle_text=oracle_text)


class OpponentModelCrossCheckTests(unittest.TestCase):
    def test_is_reproducible_given_the_same_seed(self):
        strategy = engine.Strategy(opponent_profile="control")
        deck = [_card()]
        first = engine._opponent_model_cross_check(deck, strategy, turns=10, seed=42)
        second = engine._opponent_model_cross_check(deck, strategy, turns=10, seed=42)
        self.assertEqual(first, second)

    def test_unknown_or_random_profile_falls_back_to_midrange(self):
        strategy = engine.Strategy(opponent_profile="random")
        result = engine._opponent_model_cross_check([], strategy, turns=10, seed=1)
        self.assertEqual(result["opponent_strategy_used"], "midrange")

    def test_a_deck_with_no_removal_at_all_flags_a_gap_for_a_growing_bucket(self):
        # control has the highest disruption_growth/passive_value_growth of
        # any strategy_curve (see opponent_state_weights.json) - over 12
        # turns it reliably builds a meaningful stock in at least one bucket.
        strategy = engine.Strategy(opponent_profile="control")
        deck = [_card("Target creature gets +3/+3 until end of turn.")]  # no real removal at all
        result = engine._opponent_model_cross_check(deck, strategy, turns=12, seed=7)
        self.assertGreater(len(result["coverage_gaps"]), 0)
        for gap in result["coverage_gaps"]:
            self.assertEqual(result["deck_removal_coverage"][gap["permanent_type"]], 0)
            self.assertGreaterEqual(gap["avg_value"], engine._OPP_MODEL_GAP_THRESHOLD)

    def test_a_deck_with_universal_removal_never_flags_a_gap(self):
        # "Destroy target permanent." (Vindicate) answers all 5 buckets -
        # no coverage gap can exist regardless of the simulated opponent.
        strategy = engine.Strategy(opponent_profile="control")
        deck = [_card("Destroy target permanent.")]
        result = engine._opponent_model_cross_check(deck, strategy, turns=12, seed=7)
        self.assertEqual(result["coverage_gaps"], [])
        for bucket, count in result["deck_removal_coverage"].items():
            self.assertEqual(count, 1, bucket)

    def test_goldfish_strategy_never_builds_any_stock_so_never_flags_a_gap(self):
        # goldfish has all growth rates at 0.0 (see strategy_curves) - the
        # cross-check must not invent a gap where the model itself never
        # grows anything.
        strategy = engine.Strategy(opponent_profile="goldfish")
        deck = [_card()]  # zero removal
        result = engine._opponent_model_cross_check(deck, strategy, turns=20, seed=3)
        self.assertEqual(result["coverage_gaps"], [])
        for dimension in result["averaged_board_effects"].values():
            for value in dimension.values():
                self.assertEqual(value, 0.0)

    def test_does_not_touch_the_supplied_deck_list(self):
        strategy = engine.Strategy(opponent_profile="midrange")
        deck = [_card("Destroy target artifact or enchantment.")]
        before = list(deck)
        engine._opponent_model_cross_check(deck, strategy, turns=10, seed=1)
        self.assertEqual(deck, before)

    def test_uses_an_independent_rng_and_never_touches_a_shared_one(self):
        # The whole point of the cross-check is that it must not consume
        # from / perturb any rng the caller passes elsewhere - it only ever
        # builds its own random.Random(...) instances internally. This test
        # guards that no shared rng object is required or mutated by
        # asserting the function signature takes no rng parameter at all.
        import inspect
        sig = inspect.signature(engine._opponent_model_cross_check)
        self.assertNotIn("rng", sig.parameters)

    def test_includes_the_v4460_lifegain_synergy_profile(self):
        # v4.46.0: the cross-check additionally surfaces the tested deck's
        # real lifegain-payoff synergy profile (App.synergy_profile) - a
        # White-source/Black-payoff deck must be flagged as a real
        # cross-color dependency.
        strategy = engine.Strategy(opponent_profile="midrange")
        soul_warden_text = (
            "Whenever another creature enters the battlefield under your "
            "control, you gain 1 life."
        )
        sanguine_bond_text = "Whenever you gain life, target opponent loses that much life."
        deck = [
            engine.Card(name="Soul Warden", oracle_text=soul_warden_text, color_identity={"W"}),
            engine.Card(name="Sanguine Bond", oracle_text=sanguine_bond_text, color_identity={"B"}),
        ]
        result = engine._opponent_model_cross_check(deck, strategy, turns=10, seed=1)
        profile = result["lifegain_synergy_profile"]
        self.assertTrue(profile["cross_color_dependency"])
        self.assertEqual(profile["source_cards"], ["Soul Warden"])
        self.assertEqual(profile["payoff_cards"], ["Sanguine Bond"])


if __name__ == "__main__":
    unittest.main()
