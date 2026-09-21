"""
Unit tests for v4.14.0 (Route E): the structural v1 implementation of
Docs/WINCON_AND_CONTEXT_VALUE_v1.md - a soft Win-Condition-preservation
bias (Sec. 2) and a hand-/board-state contextual modulation layer (Sec. 3).

IMPORTANT, stated plainly (matches the concept doc's own Sec. 5 and the
engine.py docstrings): the concrete bias-strength/boost constants here are
first, uncalibrated STARTING estimates - there is no EDHREC/WotC-style
external reference for "how much should preserving a Win Condition piece
discount its cast priority", unlike the color-pie or vanilla-test
calibrations elsewhere in this project. These tests verify STRUCTURE
(inverse scaling with WC count, the no-hard-lock floor, redundancy
discount direction, context boost direction/bounds) rather than asserting
specific "correct" numbers - the numbers themselves are flagged as pending
revisit once real Data/Learned/engine_value_store.json history exists.

Run from the project root:
    python -m unittest tests.test_wincon_and_context_value -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def _wc(name: str, *card_names: str, enabled: bool = True) -> dict:
    return engine.normalize_scenario({
        "name": name,
        "kind": "Win Condition",
        "enabled": enabled,
        "requirements": [{"card": c} for c in card_names],
    })


class WinConditionPreservationMultiplierTests(unittest.TestCase):
    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_card_not_part_of_any_win_condition_is_unaffected(self):
        scenarios = [_wc("WC1", "Sol Ring")]
        self.assertEqual(self.vm.win_condition_preservation_multiplier("Some Other Card", scenarios), 1.0)

    def test_no_win_conditions_defined_at_all_is_unaffected(self):
        self.assertEqual(self.vm.win_condition_preservation_multiplier("Sol Ring", []), 1.0)

    def test_disabled_win_conditions_are_ignored(self):
        scenarios = [_wc("WC1", "Sol Ring", enabled=False)]
        self.assertEqual(self.vm.win_condition_preservation_multiplier("Sol Ring", scenarios), 1.0)

    def test_lone_linchpin_card_gets_discounted_below_one(self):
        scenarios = [_wc("WC1", "Sol Ring")]
        result = self.vm.win_condition_preservation_multiplier("Sol Ring", scenarios)
        self.assertLess(result, 1.0)

    def test_bias_is_never_a_hard_lock_stays_above_the_floor(self):
        # Many overlapping single-card WCs, all involving the same card -
        # even in this extreme case the multiplier must never approach 0.
        scenarios = [_wc(f"WC{i}", "Sol Ring") for i in range(1, 30)]
        result = self.vm.win_condition_preservation_multiplier("Sol Ring", scenarios)
        floor = float(self.vm.values["wc_preservation_floor_multiplier"])
        self.assertGreaterEqual(result, floor)

    def test_more_defined_win_conditions_means_a_weaker_bias_per_piece(self):
        # Sec. 2.1: preserving one WC piece matters less when many
        # alternative WCs exist.
        one_wc = [_wc("WC1", "Sol Ring")]
        five_wcs = [_wc("WC1", "Sol Ring")] + [_wc(f"WCextra{i}", f"Other{i}") for i in range(4)]
        result_one = self.vm.win_condition_preservation_multiplier("Sol Ring", one_wc)
        result_five = self.vm.win_condition_preservation_multiplier("Sol Ring", five_wcs)
        self.assertGreater(result_five, result_one, "more alternative WCs should mean a smaller discount (closer to 1.0)")

    def test_a_win_condition_needing_more_pieces_discounts_each_piece_less(self):
        # Sec. 2.2 proxy: a WC that needs many cards is less fragile per
        # single piece than one that hinges on a single card.
        single_piece_wc = [_wc("WC1", "Sol Ring")]
        multi_piece_wc = [_wc("WC1", "Sol Ring", "Second Piece", "Third Piece")]
        result_single = self.vm.win_condition_preservation_multiplier("Sol Ring", single_piece_wc)
        result_multi = self.vm.win_condition_preservation_multiplier("Sol Ring", multi_piece_wc)
        self.assertGreater(result_multi, result_single, "a card that's one of several WC pieces should be discounted less than a lone linchpin")

    def test_uses_the_least_redundant_scenario_the_card_participates_in(self):
        # Sol Ring is a lone linchpin in WC1 but a minor piece of a big
        # multi-card WC2 - the STRONGER (more fragile) bias should apply,
        # not an average.
        scenarios = [_wc("WC1", "Sol Ring"), _wc("WC2", "Sol Ring", "A", "B", "C", "D")]
        lone_only = [_wc("WC1", "Sol Ring")]
        result_mixed = self.vm.win_condition_preservation_multiplier("Sol Ring", scenarios)
        result_lone_only = self.vm.win_condition_preservation_multiplier("Sol Ring", lone_only)
        # wc_count differs (2 vs 1) so this isn't a strict equality check,
        # but the mixed case must not be discounted LESS than what the
        # lone-WC-only redundancy would produce at the same wc_count.
        two_lone_wcs = [_wc("WC1", "Sol Ring"), _wc("WC2", "Other Card")]
        result_two_lone = self.vm.win_condition_preservation_multiplier("Sol Ring", two_lone_wcs)
        self.assertAlmostEqual(result_mixed, result_two_lone, places=6)


class HandBoardContextMultiplierTests(unittest.TestCase):
    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_near_empty_hand_boosts_draw_role(self):
        threshold = int(self.vm.values["context_empty_hand_threshold"])
        boosted = self.vm.hand_board_context_multiplier("draw", threshold, board_size=0)
        self.assertGreater(boosted, 1.0)

    def test_full_hand_does_not_boost_draw_role(self):
        threshold = int(self.vm.values["context_empty_hand_threshold"])
        result = self.vm.hand_board_context_multiplier("draw", threshold + 5, board_size=0)
        self.assertEqual(result, 1.0)

    def test_large_board_boosts_engine_role(self):
        threshold = int(self.vm.values["context_large_board_threshold"])
        boosted = self.vm.hand_board_context_multiplier("engine", hand_size=3, board_size=threshold)
        self.assertGreater(boosted, 1.0)

    def test_small_board_does_not_boost_engine_role(self):
        result = self.vm.hand_board_context_multiplier("engine", hand_size=3, board_size=0)
        self.assertEqual(result, 1.0)

    def test_unrelated_role_is_never_boosted_by_either_context(self):
        result = self.vm.hand_board_context_multiplier("removal", hand_size=0, board_size=50)
        self.assertEqual(result, 1.0)

    def test_both_conditions_can_stack_when_role_qualifies_for_neither_alone(self):
        # A role that isn't in either boost set stays completely neutral
        # regardless of how extreme the context is - the multiplier never
        # fires on a role it wasn't designed for.
        result = self.vm.hand_board_context_multiplier("tutor", hand_size=0, board_size=100)
        self.assertEqual(result, 1.0)

    def test_boosts_are_individually_bounded_not_unbounded_multiplicative_stacking(self):
        # draw role only ever gets the empty-hand boost, never the board
        # boost too - confirms boosts don't compound past their own design.
        draw_result = self.vm.hand_board_context_multiplier("draw", hand_size=0, board_size=100)
        self.assertAlmostEqual(draw_result, float(self.vm.values["context_empty_hand_draw_boost"]), places=6)


if __name__ == "__main__":
    unittest.main()
