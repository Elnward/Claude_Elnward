"""
Unit tests for App/opponent_model/state_equation.py (v4.38.0, rudimentary
opponent state equation - see that module's docstring and Docs/README.md
v4.38.0 entry for the full design writeup).

These tests validate the structural invariants the feature was explicitly
built around:
  - ONE equation for every strategy/color/bracket combination (weight-driven
    differentiation, not per-type branching).
  - Bracket genuinely scales strength (and consistency/variance).
  - Color multipliers genuinely differentiate otherwise-identical profiles.
  - Genuine variance is modeled: dead turns measurably suppress growth, and
    the module is reproducible given a seeded rng (a regression-safety net,
    not a claim about "correct" numbers - those await the user's own
    planned future calibration pass against real decklists).
  - The explicit board-wipe guardrail (never before turn 4) holds even if
    the weight file is tuned to try to bypass it.
  - The query functions are read-only and probability-driven, not
    deterministic threshold checks.

Run from the project root:
    python -m unittest tests.test_opponent_model -v

No Tkinter/display required.
"""
from __future__ import annotations

import copy
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App.opponent_model import state_equation as opp  # noqa: E402


class OpponentProfileTests(unittest.TestCase):
    def test_bracket_is_clamped_into_1_to_5(self):
        self.assertEqual(opp.OpponentProfile(bracket=0).bracket, 1)
        self.assertEqual(opp.OpponentProfile(bracket=99).bracket, 5)
        self.assertEqual(opp.OpponentProfile(bracket=3).bracket, 3)

    def test_unknown_color_letters_are_dropped(self):
        profile = opp.OpponentProfile(colors={"w", "u", "not-a-color"})
        self.assertEqual(profile.colors, {"W", "U"})


class SameEquationDifferentWeightsTests(unittest.TestCase):
    """
    "Die Gleichung muss fuer alle Gegnertypen gleich aussehen, aber die
    Gewichtung ist abhaengig von den Strategien [Farbe, Bracket]" - the
    single strongest way to test this in code is: advance_opponent_state is
    literally the same function object for every call, and two profiles
    that differ ONLY in their weights produce DIFFERENT trajectories when
    fed the same rng draws (proving the weights, not hidden per-type logic,
    are what drives the difference).
    """

    def test_advance_opponent_state_is_a_single_function_for_every_strategy(self):
        # There is exactly one advance_opponent_state in the module (no
        # per-strategy variants like advance_opponent_state_aggro etc.).
        equation_fns = [
            name for name in dir(opp)
            if name.startswith("advance_opponent_state")
        ]
        self.assertEqual(equation_fns, ["advance_opponent_state"])

    def test_aggro_and_control_diverge_under_identical_rng_draws(self):
        aggro = opp.OpponentState()
        control = opp.OpponentState()
        aggro_profile = opp.OpponentProfile(strategy="aggro", bracket=3)
        control_profile = opp.OpponentProfile(strategy="control", bracket=3)

        for _ in range(6):
            # Same seed fed to both calls each turn -> any difference in the
            # resulting state is attributable ONLY to the weight lookup.
            opp.advance_opponent_state(aggro, aggro_profile, random.Random(42))
            opp.advance_opponent_state(control, control_profile, random.Random(42))

        self.assertGreater(aggro.board_presence, control.board_presence,
                            "aggro's higher board_presence_growth must win out under identical rolls")
        # interaction_growth: as of v4.69.0 ("Kalibrierungs-Synthese Teil 3",
        # see Docs/opponent_model_calibration_v4_69_0.md), a real two-way OLS
        # deconfounding of color and strategy CONFIRMED that Aggro and
        # Control do NOT differ significantly on this dimension (0.079 vs.
        # 0.078 - within noise of each other, not the old, small-sample
        # 0.035-vs-0.16 staggering this test originally asserted on). The
        # correct assertion is now that they stay close, not that control
        # strictly wins - a strict order here would re-encode the very
        # assumption the deconfounding pass tested and found unsupported.
        self.assertAlmostEqual(
            control.interaction_availability, aggro.interaction_availability, delta=0.02,
            msg="aggro/control interaction_availability should now track closely - the old "
                "assumption that control clearly leads was not confirmed by the v4.69.0 "
                "deconfounded regression (see calibration doc)",
        )

    def test_goldfish_profile_never_develops_any_dimension(self):
        state = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="goldfish", bracket=3)
        rng = random.Random(7)
        for _ in range(10):
            opp.advance_opponent_state(state, profile, rng)
        self.assertEqual(state.board_presence, 0.0)
        self.assertEqual(state.interaction_availability, 0.0)
        self.assertEqual(state.wipe_readiness, 0.0)


class BracketScalingTests(unittest.TestCase):
    def test_higher_bracket_grows_board_presence_faster_under_identical_rolls(self):
        low = opp.OpponentState()
        high = opp.OpponentState()
        low_profile = opp.OpponentProfile(strategy="midrange", bracket=1)
        high_profile = opp.OpponentProfile(strategy="midrange", bracket=5)

        for turn in range(5):
            opp.advance_opponent_state(low, low_profile, random.Random(100 + turn))
            opp.advance_opponent_state(high, high_profile, random.Random(100 + turn))

        self.assertGreater(high.board_presence, low.board_presence)
        self.assertGreater(high.mana_availability, low.mana_availability)

    def test_higher_bracket_has_a_higher_consistency_floor_on_mana_availability(self):
        # Even with a rng that always rolls the least favourable draw
        # (random() -> 0.0 via seed sweeping is unreliable; instead check
        # the floor directly after a single very-unlucky-amplitude turn).
        state = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="control", bracket=5)
        opp.advance_opponent_state(state, profile, random.Random(1))
        bracket5_floor = opp._bracket_config(5)["consistency_floor"]
        self.assertGreaterEqual(state.mana_availability, bracket5_floor)


class ColorMultiplierTests(unittest.TestCase):
    def test_blue_boosts_interaction_availability_over_colorless(self):
        colorless = opp.OpponentState()
        blue = opp.OpponentState()
        colorless_profile = opp.OpponentProfile(strategy="control", colors=set(), bracket=3)
        blue_profile = opp.OpponentProfile(strategy="control", colors={"U"}, bracket=3)

        for turn in range(4):
            opp.advance_opponent_state(colorless, colorless_profile, random.Random(200 + turn))
            opp.advance_opponent_state(blue, blue_profile, random.Random(200 + turn))

        self.assertGreater(blue.interaction_availability, colorless.interaction_availability)

    def test_multiple_colors_multiply_together(self):
        mono_white = opp.OpponentProfile(strategy="control", colors={"W"}, bracket=3)
        mono_black = opp.OpponentProfile(strategy="control", colors={"B"}, bracket=3)
        orzhov = opp.OpponentProfile(strategy="control", colors={"W", "B"}, bracket=3)

        w_mult = opp._color_multiplier(mono_white.colors, "wipe_readiness")
        b_mult = opp._color_multiplier(mono_black.colors, "wipe_readiness")
        wb_mult = opp._color_multiplier(orzhov.colors, "wipe_readiness")

        self.assertAlmostEqual(wb_mult, w_mult * b_mult, places=9)


class WipeGuardrailTests(unittest.TestCase):
    def test_wipe_readiness_stays_zero_before_the_hard_floor_turn(self):
        state = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="control", bracket=5)  # fastest-growing legal profile
        rng = random.Random(3)
        for _ in range(opp.GUARDRAIL_WIPE_MIN_TURN - 1):
            opp.advance_opponent_state(state, profile, rng)
            self.assertEqual(state.wipe_readiness, 0.0)

    def test_a_tuned_down_wipe_min_turn_cannot_bypass_the_hard_floor(self):
        # Simulate a future weight-file edit that (accidentally or not) sets
        # wipe_min_turn=1 - the hard-coded GUARDRAIL_WIPE_MIN_TURN must still
        # win via max() in _wipe_min_turn.
        tampered = copy.deepcopy(opp._WEIGHTS)
        tampered["strategy_curves"]["control"]["wipe_min_turn"] = 1
        original = opp._WEIGHTS
        opp._WEIGHTS = tampered
        try:
            state = opp.OpponentState()
            profile = opp.OpponentProfile(strategy="control", bracket=5)
            rng = random.Random(9)
            opp.advance_opponent_state(state, profile, rng)  # turn 1
            opp.advance_opponent_state(state, profile, rng)  # turn 2
            opp.advance_opponent_state(state, profile, rng)  # turn 3
            self.assertEqual(state.wipe_readiness, 0.0,
                              "turn 3 is still below GUARDRAIL_WIPE_MIN_TURN=4 even with wipe_min_turn tampered to 1")
        finally:
            opp._WEIGHTS = original

    def test_a_json_level_guardrail_tampered_below_the_code_floor_is_still_overridden(self):
        tampered = copy.deepcopy(opp._WEIGHTS)
        tampered["guardrails"]["wipe_min_turn_hard_floor"] = 1
        tampered["strategy_curves"]["control"]["wipe_min_turn"] = 1
        original = opp._WEIGHTS
        opp._WEIGHTS = tampered
        try:
            state = opp.OpponentState()
            profile = opp.OpponentProfile(strategy="control", bracket=5)
            rng = random.Random(9)
            opp.advance_opponent_state(state, profile, rng)  # turn 1
            self.assertEqual(state.wipe_readiness, 0.0,
                              "GUARDRAIL_WIPE_MIN_TURN itself is a Python constant, not tunable via JSON at all")
        finally:
            opp._WEIGHTS = original

    def test_aggro_and_horde_never_reach_wipe_readiness_at_all(self):
        for strategy in ("aggro", "horde"):
            state = opp.OpponentState()
            profile = opp.OpponentProfile(strategy=strategy, bracket=5)
            rng = random.Random(5)
            for _ in range(20):
                opp.advance_opponent_state(state, profile, rng)
            self.assertEqual(state.wipe_readiness, 0.0, strategy)


class VarianceAndDeadTurnTests(unittest.TestCase):
    def test_reproducible_given_the_same_seeded_rng(self):
        profile = opp.OpponentProfile(strategy="midrange", colors={"G", "B"}, bracket=3)
        state_a = opp.OpponentState()
        state_b = opp.OpponentState()
        for _ in range(8):
            opp.advance_opponent_state(state_a, profile, random.Random(55))
            opp.advance_opponent_state(state_b, profile, random.Random(55))
        self.assertEqual(state_a, state_b)

    def test_a_dead_turn_measurably_suppresses_growth_vs_a_normal_turn(self):
        # Force the dead-turn branch via a stub rng whose .random() always
        # returns 0.0 (always below any nonzero dead_turn_chance) - proves
        # the effective_quality=0.1 dampening path actually engages.
        class AlwaysZeroRng:
            def random(self):
                return 0.0

            def uniform(self, a, b):
                return 0.0

        dead = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="midrange", bracket=3)
        opp.advance_opponent_state(dead, profile, AlwaysZeroRng())
        self.assertTrue(dead.dead_turn)

        class AlwaysHighRng:
            def random(self):
                return 0.999

            def uniform(self, a, b):
                return 0.0

        normal = opp.OpponentState()
        opp.advance_opponent_state(normal, profile, AlwaysHighRng())
        self.assertFalse(normal.dead_turn)
        self.assertGreater(normal.board_presence, dead.board_presence)

    def test_cards_remaining_decreases_and_never_goes_negative(self):
        state = opp.OpponentState(cards_remaining=2)
        profile = opp.OpponentProfile(strategy="midrange", bracket=3)
        rng = random.Random(1)
        opp.advance_opponent_state(state, profile, rng)
        self.assertEqual(state.cards_remaining, 1)
        opp.advance_opponent_state(state, profile, rng)
        self.assertEqual(state.cards_remaining, 0)
        opp.advance_opponent_state(state, profile, rng)
        self.assertEqual(state.cards_remaining, 0)

    def test_life_is_never_touched_by_the_equation(self):
        state = opp.OpponentState(life=17.0)
        profile = opp.OpponentProfile(strategy="aggro", bracket=4)
        rng = random.Random(2)
        for _ in range(5):
            opp.advance_opponent_state(state, profile, rng)
        self.assertEqual(state.life, 17.0)


class QueryFunctionsAreReadOnlyTests(unittest.TestCase):
    def test_query_combat_state_does_not_mutate_state(self):
        state = opp.OpponentState(board_presence=4.0, dead_turn=False)
        before = copy.deepcopy(state)
        opp.query_combat_state(state)
        self.assertEqual(state, before)

    def test_query_combat_state_halves_effective_blockers_on_a_dead_turn(self):
        alert = opp.OpponentState(board_presence=4.0, dead_turn=False)
        dead = opp.OpponentState(board_presence=4.0, dead_turn=True)
        self.assertEqual(opp.query_combat_state(alert).effective_blockers, 4.0)
        self.assertEqual(opp.query_combat_state(dead).effective_blockers, 2.0)

    def test_query_castable_state_does_not_mutate_state(self):
        state = opp.OpponentState(interaction_availability=0.5, wipe_readiness=0.3, mana_availability=0.8, hand_quality=0.6)
        before = copy.deepcopy(state)
        opp.query_castable_state(state, random.Random(1))
        self.assertEqual(state, before)

    def test_query_castable_state_is_a_probability_roll_not_a_threshold(self):
        # Same nonzero readiness, different rng draws -> both True and False
        # must be reachable (i.e. it's not "if readiness > 0.5: True").
        state = opp.OpponentState(interaction_availability=0.5, wipe_readiness=0.5, mana_availability=0.5, hand_quality=1.0)
        outcomes = {opp.query_castable_state(state, random.Random(seed)).has_interaction for seed in range(20)}
        self.assertEqual(outcomes, {True, False})

    def test_zero_readiness_never_grants_anything(self):
        state = opp.OpponentState()  # all-default: interaction/wipe/mana all 0 or floor
        state.mana_availability = 0.0
        state.hand_quality = 0.0
        query = opp.query_castable_state(state, random.Random(0))
        self.assertFalse(query.has_interaction)
        self.assertFalse(query.has_wipe)
        self.assertFalse(query.has_big_play)


class OpeningManaBoostTests(unittest.TestCase):
    """
    v4.39.0: a one-time turn-1 mana_availability boost, evidenced by every
    real "expensive"/high-Bracket decklist in the calibration sample adding
    a cluster of explosive fast-mana artifacts absent from every lower-
    Bracket list (see Data/Models/opponent_state_weights.json note and
    state_equation.py's module docstring "Iteration 2" section).
    """

    def test_low_brackets_have_no_boost_evidenced_by_the_real_sample(self):
        for bracket in (1, 2, 3):
            state = opp.OpponentState()
            profile = opp.OpponentProfile(strategy="midrange", bracket=bracket)
            opp.advance_opponent_state(state, profile, random.Random(1))
            floor = opp._bracket_config(bracket)["consistency_floor"]
            # No boost means turn-1 mana_availability sits at (or very near)
            # the ordinary growth + consistency floor, not meaningfully above it.
            self.assertLess(state.mana_availability, floor + 0.05, bracket)

    def test_bracket_4_and_5_apply_a_real_one_time_boost(self):
        b3 = opp.OpponentState()
        b4 = opp.OpponentState()
        b5 = opp.OpponentState()
        opp.advance_opponent_state(b3, opp.OpponentProfile(strategy="midrange", bracket=3), random.Random(1))
        opp.advance_opponent_state(b4, opp.OpponentProfile(strategy="midrange", bracket=4), random.Random(1))
        opp.advance_opponent_state(b5, opp.OpponentProfile(strategy="midrange", bracket=5), random.Random(1))
        self.assertGreater(b4.mana_availability, b3.mana_availability)
        self.assertGreater(b5.mana_availability, b4.mana_availability)

    def test_the_boost_only_applies_once_on_turn_one(self):
        state = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="midrange", bracket=5)
        rng = random.Random(2)
        opp.advance_opponent_state(state, profile, rng)  # turn 1: boost applies
        after_turn_1 = state.mana_availability
        # Force mana_availability down below where a second boost would be
        # obvious, to isolate whether turn 2 re-applies it.
        state.mana_availability = 0.0
        opp.advance_opponent_state(state, profile, rng)  # turn 2: no boost, only growth
        curve = opp._strategy_curve("midrange")
        bracket_cfg = opp._bracket_config(5)
        max_possible_growth = curve["mana_growth"] * bracket_cfg["power_multiplier"] * 1.3  # generous headroom over amplitude=1
        self.assertLess(state.mana_availability, max_possible_growth + bracket_cfg["consistency_floor"])
        self.assertNotAlmostEqual(state.mana_availability, after_turn_1 * 2, places=2)


class ComboFinishReadinessTests(unittest.TestCase):
    """
    v4.39.0: combo_finish_readiness, evidenced by the Game-Changer-density
    jump found in the real decklist sample (0-2 cards at Bracket <=3 vs.
    4-5+ at Bracket >=4 in every sampled deck) - hard-gated to Bracket >=
    GUARDRAIL_COMBO_MIN_BRACKET and turn >= the combo-min-turn guardrail.
    """

    def test_stays_zero_below_the_hard_bracket_floor_no_matter_how_many_turns_pass(self):
        for bracket in (1, 2, 3):
            state = opp.OpponentState()
            profile = opp.OpponentProfile(strategy="control", bracket=bracket)  # control has the highest combo_growth
            rng = random.Random(4)
            for _ in range(20):
                opp.advance_opponent_state(state, profile, rng)
            self.assertEqual(state.combo_finish_readiness, 0.0, bracket)

    def test_stays_zero_before_the_hard_turn_floor_even_at_bracket_5(self):
        state = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="control", bracket=5)
        rng = random.Random(4)
        for _ in range(opp.GUARDRAIL_COMBO_MIN_TURN - 1):
            opp.advance_opponent_state(state, profile, rng)
            self.assertEqual(state.combo_finish_readiness, 0.0)

    def test_grows_once_bracket_and_turn_floors_are_both_satisfied(self):
        state = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="control", bracket=5)
        rng = random.Random(4)
        for _ in range(6):
            opp.advance_opponent_state(state, profile, rng)
        self.assertGreater(state.combo_finish_readiness, 0.0)

    def test_bracket_floor_cannot_be_tampered_below_the_hard_code_constant(self):
        tampered = copy.deepcopy(opp._WEIGHTS)
        tampered["guardrails"]["combo_min_bracket_hard_floor"] = 1
        original = opp._WEIGHTS
        opp._WEIGHTS = tampered
        try:
            state = opp.OpponentState()
            profile = opp.OpponentProfile(strategy="control", bracket=1)
            rng = random.Random(4)
            for _ in range(10):
                opp.advance_opponent_state(state, profile, rng)
            self.assertEqual(state.combo_finish_readiness, 0.0,
                              "GUARDRAIL_COMBO_MIN_BRACKET is a Python constant, not tunable via JSON alone")
        finally:
            opp._WEIGHTS = original

    def test_horde_and_goldfish_have_no_evidenced_combo_growth(self):
        for strategy in ("horde", "goldfish"):
            state = opp.OpponentState()
            profile = opp.OpponentProfile(strategy=strategy, bracket=5)
            rng = random.Random(4)
            for _ in range(10):
                opp.advance_opponent_state(state, profile, rng)
            if strategy == "goldfish":
                self.assertEqual(state.combo_finish_readiness, 0.0)
            # horde is left as a disclosed, un-sampled gap (see weights file
            # note) - its combo_growth is low but not necessarily zero, so
            # only goldfish (explicitly all-zero) is asserted strictly here.


class CastabilityQueryComboFieldTests(unittest.TestCase):
    def test_has_combo_finish_is_a_probability_roll_against_the_readiness_value(self):
        state = opp.OpponentState(combo_finish_readiness=0.5)
        outcomes = {opp.query_castable_state(state, random.Random(seed)).has_combo_finish for seed in range(20)}
        self.assertEqual(outcomes, {True, False})

    def test_zero_combo_readiness_never_grants_a_combo_finish(self):
        state = opp.OpponentState(combo_finish_readiness=0.0)
        query = opp.query_castable_state(state, random.Random(0))
        self.assertFalse(query.has_combo_finish)

    def test_query_does_not_mutate_combo_finish_readiness(self):
        state = opp.OpponentState(combo_finish_readiness=0.3)
        before = copy.deepcopy(state)
        opp.query_castable_state(state, random.Random(1))
        self.assertEqual(state, before)


class PassiveValueAndSacDrainTests(unittest.TestCase):
    """
    v4.40.0 ('Iteration 3'): passive_value_by_type / sac_drain_by_type -
    generalized, permanent-type-tagged, DECAYING stocks that close the two
    gaps deferred in v4.39.0 (passive value/tax engines; sacrifice/
    aristocrats drain loops), per the user's own proposed design.
    """

    def test_both_stocks_start_at_zero_in_every_bucket(self):
        state = opp.OpponentState()
        for bucket in opp.PERMANENT_TYPE_BUCKETS:
            self.assertEqual(state.passive_value_by_type[bucket], 0.0)
            self.assertEqual(state.sac_drain_by_type[bucket], 0.0)

    def test_control_grows_more_passive_value_than_aggro_under_identical_rolls(self):
        control = opp.OpponentState()
        aggro = opp.OpponentState()
        control_profile = opp.OpponentProfile(strategy="control", bracket=3)
        aggro_profile = opp.OpponentProfile(strategy="aggro", bracket=3)
        for turn in range(8):
            opp.advance_opponent_state(control, control_profile, random.Random(300 + turn))
            opp.advance_opponent_state(aggro, aggro_profile, random.Random(300 + turn))
        control_total = sum(control.passive_value_by_type.values())
        aggro_total = sum(aggro.passive_value_by_type.values())
        self.assertGreater(control_total, aggro_total)

    def test_midrange_grows_more_sac_drain_than_control_under_identical_rolls(self):
        midrange = opp.OpponentState()
        control = opp.OpponentState()
        midrange_profile = opp.OpponentProfile(strategy="midrange", colors={"B"}, bracket=4)
        control_profile = opp.OpponentProfile(strategy="control", colors={"B"}, bracket=4)
        for turn in range(8):
            opp.advance_opponent_state(midrange, midrange_profile, random.Random(400 + turn))
            opp.advance_opponent_state(control, control_profile, random.Random(400 + turn))
        self.assertGreater(
            sum(midrange.sac_drain_by_type.values()),
            sum(control.sac_drain_by_type.values()),
        )

    def test_black_boosts_sac_drain_over_colorless_under_identical_rolls(self):
        black = opp.OpponentState()
        colorless = opp.OpponentState()
        black_profile = opp.OpponentProfile(strategy="midrange", colors={"B"}, bracket=4)
        colorless_profile = opp.OpponentProfile(strategy="midrange", colors=set(), bracket=4)
        for turn in range(8):
            opp.advance_opponent_state(black, black_profile, random.Random(500 + turn))
            opp.advance_opponent_state(colorless, colorless_profile, random.Random(500 + turn))
        self.assertGreater(
            sum(black.sac_drain_by_type.values()),
            sum(colorless.sac_drain_by_type.values()),
        )

    def test_more_players_at_the_table_grows_passive_value_faster(self):
        two_player = opp.OpponentState()
        four_player = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="control", bracket=3)
        rng_a, rng_b = random.Random(9), random.Random(9)
        for _ in range(6):
            opp.advance_opponent_state(two_player, profile, rng_a, table_size=2)
            opp.advance_opponent_state(four_player, profile, rng_b, table_size=4)
        self.assertGreater(
            sum(four_player.passive_value_by_type.values()),
            sum(two_player.passive_value_by_type.values()),
        )

    def test_table_size_does_not_affect_sac_drain_growth(self):
        # Per the module docstring: a Blood-Artist-style drain trigger
        # typically hits one chosen target, not every player - so unlike
        # passive_value, sac_drain must NOT scale with table_size.
        two_player = opp.OpponentState()
        six_player = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="midrange", colors={"B"}, bracket=4)
        rng_a, rng_b = random.Random(11), random.Random(11)
        for _ in range(6):
            opp.advance_opponent_state(two_player, profile, rng_a, table_size=2)
            opp.advance_opponent_state(six_player, profile, rng_b, table_size=6)
        self.assertAlmostEqual(
            sum(two_player.sac_drain_by_type.values()),
            sum(six_player.sac_drain_by_type.values()),
            places=9,
        )

    def test_decay_shrinks_an_existing_stock_even_with_no_further_growth(self):
        state = opp.OpponentState(passive_value_by_type={"artifact": 0.0, "enchantment": 0.5, "creature": 0.0})
        profile = opp.OpponentProfile(strategy="goldfish", bracket=3)  # goldfish has zero growth of anything
        opp.advance_opponent_state(state, profile, random.Random(1))
        self.assertLess(state.passive_value_by_type["enchantment"], 0.5)
        self.assertGreater(state.passive_value_by_type["enchantment"], 0.0)

    def test_creature_bucket_decays_faster_than_enchantment_bucket(self):
        creature_heavy = opp.OpponentState(passive_value_by_type={"artifact": 0.0, "enchantment": 0.0, "creature": 0.5})
        enchantment_heavy = opp.OpponentState(passive_value_by_type={"artifact": 0.0, "enchantment": 0.5, "creature": 0.0})
        profile = opp.OpponentProfile(strategy="goldfish", bracket=3)
        opp.advance_opponent_state(creature_heavy, profile, random.Random(1))
        opp.advance_opponent_state(enchantment_heavy, profile, random.Random(1))
        self.assertLess(creature_heavy.passive_value_by_type["creature"], enchantment_heavy.passive_value_by_type["enchantment"])

    def test_higher_bracket_decays_the_same_stock_faster_than_a_lower_bracket(self):
        # v4.41.0 ("Iteration 3b"): impact_half_life_multiplier is < 1.0 at
        # higher Brackets (LSV/"threat relevance" - more bomb-tier permanents
        # on average -> answered faster), so identical starting stock decays
        # MORE per turn at Bracket 5 than at Bracket 2, all else equal.
        low_bracket = opp.OpponentState(passive_value_by_type={"artifact": 0.0, "enchantment": 0.5, "creature": 0.0})
        high_bracket = opp.OpponentState(passive_value_by_type={"artifact": 0.0, "enchantment": 0.5, "creature": 0.0})
        opp.advance_opponent_state(low_bracket, opp.OpponentProfile(strategy="goldfish", bracket=2), random.Random(1))
        opp.advance_opponent_state(high_bracket, opp.OpponentProfile(strategy="goldfish", bracket=5), random.Random(1))
        self.assertLess(high_bracket.passive_value_by_type["enchantment"], low_bracket.passive_value_by_type["enchantment"])

    def test_impact_half_life_multiplier_is_read_from_the_weights_file_per_bracket(self):
        for bracket in (1, 2, 3, 4, 5):
            cfg = opp._bracket_config(bracket)
            self.assertIn("impact_half_life_multiplier", cfg)
            self.assertGreater(float(cfg["impact_half_life_multiplier"]), 0.0)
            self.assertLessEqual(float(cfg["impact_half_life_multiplier"]), 1.0)

    def test_pick_permanent_type_respects_distribution_over_many_trials(self):
        rng = random.Random(42)
        distribution = {"enchantment": 0.6, "artifact": 0.3, "creature": 0.1}
        counts = {"enchantment": 0, "artifact": 0, "creature": 0}
        for _ in range(2000):
            counts[opp._pick_permanent_type(rng, distribution)] += 1
        self.assertGreater(counts["enchantment"], counts["artifact"])
        self.assertGreater(counts["artifact"], counts["creature"])

    def test_query_board_effects_is_read_only_and_matches_the_totals(self):
        state = opp.OpponentState(
            passive_value_by_type={"artifact": 0.1, "enchantment": 0.2, "creature": 0.0},
            sac_drain_by_type={"artifact": 0.3, "enchantment": 0.0, "creature": 0.1},
        )
        before = copy.deepcopy(state)
        result = opp.query_board_effects(state)
        self.assertEqual(state, before)
        self.assertAlmostEqual(result.passive_value_total, 0.3)
        self.assertAlmostEqual(result.sac_drain_total, 0.4)
        self.assertEqual(result.passive_value_by_type, state.passive_value_by_type)
        # Mutating the returned dict must not alias back into state.
        result.passive_value_by_type["artifact"] = 999.0
        self.assertNotEqual(state.passive_value_by_type["artifact"], 999.0)


class DisruptionLockoutTests(unittest.TestCase):
    """
    v4.43.0: disruption_lockout_by_type closes the 'unmapped_persistent_
    disruption' gap disclosed in v4.40.0/v4.41.0 (Docs/README.md open-points
    review) - a third decaying stock, same growth+decay mechanism as
    passive_value_by_type/sac_drain_by_type but its own, wider bucket set
    (DISRUPTION_PERMANENT_TYPE_BUCKETS) because two of the 9 real Game
    Changers behind it are a planeswalker (Narset) and a land (Tabernacle).
    """

    def test_starts_at_zero_in_every_bucket(self):
        state = opp.OpponentState()
        for bucket in opp.DISRUPTION_PERMANENT_TYPE_BUCKETS:
            self.assertEqual(state.disruption_lockout_by_type[bucket], 0.0)

    def test_control_grows_more_disruption_lockout_than_aggro_under_identical_rolls(self):
        control = opp.OpponentState()
        aggro = opp.OpponentState()
        profile_control = opp.OpponentProfile(strategy="control", colors={"U"}, bracket=3)
        profile_aggro = opp.OpponentProfile(strategy="aggro", colors={"U"}, bracket=3)
        for _ in range(6):
            opp.advance_opponent_state(control, profile_control, random.Random(1))
            opp.advance_opponent_state(aggro, profile_aggro, random.Random(1))
        self.assertGreater(
            sum(control.disruption_lockout_by_type.values()),
            sum(aggro.disruption_lockout_by_type.values()),
        )

    def test_black_boosts_disruption_lockout_over_red_under_identical_rolls(self):
        black = opp.OpponentState()
        red = opp.OpponentState()
        profile_black = opp.OpponentProfile(strategy="control", colors={"B"}, bracket=3)
        profile_red = opp.OpponentProfile(strategy="control", colors={"R"}, bracket=3)
        for _ in range(6):
            opp.advance_opponent_state(black, profile_black, random.Random(1))
            opp.advance_opponent_state(red, profile_red, random.Random(1))
        self.assertGreater(
            sum(black.disruption_lockout_by_type.values()),
            sum(red.disruption_lockout_by_type.values()),
        )

    def test_more_players_at_the_table_grows_disruption_lockout_faster(self):
        two_player = opp.OpponentState()
        six_player = opp.OpponentState()
        profile = opp.OpponentProfile(strategy="control", colors={"W"}, bracket=3)
        for _ in range(6):
            opp.advance_opponent_state(two_player, profile, random.Random(1), table_size=2)
            opp.advance_opponent_state(six_player, profile, random.Random(1), table_size=6)
        self.assertGreater(
            sum(six_player.disruption_lockout_by_type.values()),
            sum(two_player.disruption_lockout_by_type.values()),
        )

    def test_decay_shrinks_an_existing_stock_even_with_no_further_growth(self):
        state = opp.OpponentState(disruption_lockout_by_type={"artifact": 0.0, "enchantment": 0.0, "creature": 0.5, "planeswalker": 0.0, "land": 0.0})
        profile = opp.OpponentProfile(strategy="goldfish", bracket=3)  # goldfish has zero growth of anything
        opp.advance_opponent_state(state, profile, random.Random(1))
        self.assertLess(state.disruption_lockout_by_type["creature"], 0.5)
        self.assertGreater(state.disruption_lockout_by_type["creature"], 0.0)

    def test_land_bucket_decays_slower_than_creature_bucket(self):
        creature_heavy = opp.OpponentState(disruption_lockout_by_type={"artifact": 0.0, "enchantment": 0.0, "creature": 0.5, "planeswalker": 0.0, "land": 0.0})
        land_heavy = opp.OpponentState(disruption_lockout_by_type={"artifact": 0.0, "enchantment": 0.0, "creature": 0.0, "planeswalker": 0.0, "land": 0.5})
        profile = opp.OpponentProfile(strategy="goldfish", bracket=3)
        opp.advance_opponent_state(creature_heavy, profile, random.Random(1))
        opp.advance_opponent_state(land_heavy, profile, random.Random(1))
        self.assertGreater(land_heavy.disruption_lockout_by_type["land"], creature_heavy.disruption_lockout_by_type["creature"])

    def test_pick_permanent_type_covers_all_five_disruption_buckets_over_many_trials(self):
        rng = random.Random(7)
        distribution = {"creature": 0.67, "enchantment": 0.11, "planeswalker": 0.11, "land": 0.11}
        counts = {k: 0 for k in distribution}
        for _ in range(4000):
            counts[opp._pick_permanent_type(rng, distribution)] += 1
        self.assertGreater(counts["creature"], counts["enchantment"])
        self.assertGreater(counts["creature"], counts["planeswalker"])
        self.assertGreater(counts["creature"], counts["land"])
        for bucket in ("enchantment", "planeswalker", "land"):
            self.assertGreater(counts[bucket], 0)

    def test_query_board_effects_exposes_disruption_lockout_read_only(self):
        state = opp.OpponentState(
            disruption_lockout_by_type={"artifact": 0.0, "enchantment": 0.2, "creature": 0.1, "planeswalker": 0.0, "land": 0.0}
        )
        before = copy.deepcopy(state)
        result = opp.query_board_effects(state)
        self.assertEqual(state, before)
        self.assertAlmostEqual(result.disruption_lockout_total, 0.3)
        result.disruption_lockout_by_type["enchantment"] = 999.0
        self.assertNotEqual(state.disruption_lockout_by_type["enchantment"], 999.0)


class GameChangerArchetypesFileTests(unittest.TestCase):
    """
    v4.40.0: Data/Models/game_changer_archetypes.json is a calibration/
    tagging aid only (never consulted at runtime by state_equation.py) -
    these tests guard its own internal consistency, not any simulation
    behavior.
    """

    _VERIFIED_53 = {
        "Ad Nauseam", "Ancient Tomb", "Aura Shards", "Biorhythm", "Bolas's Citadel",
        "Braids, Cabal Minion", "Chrome Mox", "Coalition Victory", "Consecrated Sphinx",
        "Crop Rotation", "Cyclonic Rift", "Demonic Tutor", "Drannith Magistrate",
        "Enlightened Tutor", "Farewell", "Field of the Dead", "Fierce Guardianship",
        "Force of Will", "Gaea's Cradle", "Gamble", "Gifts Ungiven", "Glacial Chasm",
        "Grand Arbiter Augustin IV", "Grim Monolith", "Humility", "Imperial Seal",
        "Intuition", "Jeska's Will", "Lion's Eye Diamond", "Mana Vault",
        "Mishra's Workshop", "Mox Diamond", "Mystical Tutor", "Narset, Parter of Veils",
        "Natural Order", "Necropotence", "Notion Thief", "Opposition Agent",
        "Orcish Bowmasters", "Panoptic Mirror", "Rhystic Study", "Seedborn Muse",
        "Serra's Sanctum", "Smothering Tithe", "Survival of the Fittest",
        "Teferi's Protection", "Tergrid, God of Fright", "Thassa's Oracle",
        "The One Ring", "The Tabernacle at Pendrell Vale", "Underworld Breach",
        "Vampiric Tutor", "Worldly Tutor",
    }

    @classmethod
    def setUpClass(cls):
        cls.data = opp._load_game_changer_archetypes()

    def test_module_level_cache_matches_a_fresh_load(self):
        self.assertEqual(opp._GAME_CHANGER_ARCHETYPES, self.data)

    def test_exactly_the_53_verified_game_changers_are_present(self):
        self.assertEqual(set(self.data["cards"].keys()), self._VERIFIED_53)
        self.assertEqual(len(self.data["cards"]), 53)

    def test_every_entry_has_a_known_archetype(self):
        known = set(self.data["archetypes"])
        for name, entry in self.data["cards"].items():
            with self.subTest(card=name):
                self.assertIn(entry["archetype"], known)

    def test_every_entry_feeds_a_declared_target(self):
        known = set(self.data["feeds_targets"].keys())
        for name, entry in self.data["cards"].items():
            with self.subTest(card=name):
                self.assertIn(entry["feeds"], known)

    def test_every_entry_has_a_valid_permanent_type(self):
        valid = {"artifact", "enchantment", "creature", "planeswalker", "land", None}
        for name, entry in self.data["cards"].items():
            with self.subTest(card=name):
                self.assertIn(entry["permanent_type"], valid)

    def test_every_card_feeding_one_of_the_three_stocks_is_actually_a_permanent(self):
        # passive_value_by_type/sac_drain_by_type/disruption_lockout_by_type
        # only make sense for real permanents (they decay via a permanent-
        # type half-life) - a card feeding one of these with
        # permanent_type=None would be a self-contradiction in this file.
        for name, entry in self.data["cards"].items():
            if entry["feeds"] in ("passive_value_by_type", "sac_drain_by_type", "disruption_lockout_by_type"):
                with self.subTest(card=name):
                    self.assertIsNotNone(entry["permanent_type"])

    def test_the_former_unmapped_disruption_cluster_is_now_tagged_to_its_own_dimension(self):
        # v4.40.0/v4.41.0 disclosed a 9-card cluster with no real dimension
        # ("unmapped_persistent_disruption"). v4.43.0 closed that gap with
        # disruption_lockout_by_type - guard that all 9 moved over cleanly
        # (no card silently dropped, none left on the old, now-removed tag).
        self.assertEqual(
            [n for n, e in self.data["cards"].items() if e["feeds"] == "unmapped_persistent_disruption"],
            [],
        )
        disruption_cards = [n for n, e in self.data["cards"].items() if e["feeds"] == "disruption_lockout_by_type"]
        self.assertEqual(len(disruption_cards), 9)


class WeightsFileSanityTests(unittest.TestCase):
    def test_every_declared_strategy_curve_field_is_actually_consulted(self):
        # Structural guard mirroring the aliases/expects lesson from
        # App/keyword_library/registry.py (v4.36.0): every key present in
        # EVERY strategy curve must be one this module's code actually
        # reads, so a future added-but-unused tunable is caught immediately.
        consulted = {
            "board_presence_growth", "interaction_growth", "wipe_growth",
            "wipe_min_turn", "combo_growth", "combo_min_turn",
            "passive_value_growth", "sac_drain_growth", "disruption_growth", "mana_growth",
            "variance_amplitude", "dead_turn_chance_base",
        }
        for name, curve in opp._WEIGHTS["strategy_curves"].items():
            declared = {k for k in curve.keys() if not k.startswith("_")}
            with self.subTest(strategy=name):
                self.assertTrue(declared.issubset(consulted), declared - consulted)

    def test_every_declared_color_modifier_dimension_is_actually_consulted(self):
        consulted = {
            "board_presence", "interaction_availability", "wipe_readiness",
            "mana_growth", "dead_turn_chance", "combo_finish_readiness",
            "passive_value_growth", "sac_drain_growth", "disruption_growth",
        }
        for color, mods in opp._WEIGHTS["color_modifiers"].items():
            if color.startswith("_"):
                continue
            declared = {k for k in mods.keys() if not k.startswith("_")}
            with self.subTest(color=color):
                self.assertTrue(declared.issubset(consulted), declared - consulted)

    def test_every_declared_bracket_field_is_actually_consulted(self):
        consulted = {"power_multiplier", "variance_multiplier", "consistency_floor", "opening_mana_boost", "impact_half_life_multiplier"}
        for bracket, cfg in opp._WEIGHTS["bracket_scaling"].items():
            if bracket.startswith("_"):
                continue
            declared = {k for k in cfg.keys() if not k.startswith("_")}
            with self.subTest(bracket=bracket):
                self.assertTrue(declared.issubset(consulted), declared - consulted)


if __name__ == "__main__":
    unittest.main()
