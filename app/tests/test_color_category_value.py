"""
Unit/integration tests for v4.11.0: color-aware category value multipliers.

Covers:
  1. ValueModel.color_category_multiplier in isolation - primary color (1.0),
     off-color discount, multicolor picks the BEST applicable color (max,
     not average), colorless fallback, and the backward-compatibility rule
     that color_identity=None (an as-yet-unupdated call site) is a no-op
     (1.0), distinct from color_identity=set() (a confirmed colorless card,
     which uses the colorless fallback).
  2. metric_value/aggregate_value stay exactly unchanged for any call that
     doesn't pass color_identity - the core "nothing regresses" guarantee
     for the v4.10.0-era call sites this WP didn't touch.
  3. Real end-to-end proof via best_x_plan with the project's real Banefire
     card (from the offline Scryfall cache) and color-swapped clones of the
     exact same card (dataclasses.replace, so mana cost/oracle text/effect
     are identical - only color_identity differs): the smallest-lethal-X
     search itself is unaffected by color (same X for every clone, as it
     should be - color only affects how good the effect is judged, not
     whether it kills), but the reported gross_value scales exactly with
     the color multiplier.

Run from the project root:
    python -m unittest tests.test_color_category_value -v
"""
from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402

_SCRYFALL_CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"


def _load_real_card(name: str, *, commander: bool = False) -> engine.Card:
    """Same approach as tests/test_x_spell_copy.py::_load_real_card - builds a
    real Card from the project's own offline Scryfall cache via the actual
    card_from_scryfall import path, rather than hand-authoring one."""
    with _SCRYFALL_CACHE_PATH.open("r", encoding="utf-8") as f:
        cache = json.load(f)
    for obj in cache.values():
        if isinstance(obj, dict) and obj.get("name") == name:
            entry = engine.DeckEntry(name=name)
            return engine.card_from_scryfall(entry, obj, commander_name=name if commander else None)
    raise AssertionError(f"{name!r} not found in {_SCRYFALL_CACHE_PATH}")


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def _fake_payment(state, strategy, total_cost, req, *args, **kwargs):
    return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)


class _WithFakeManaMixin:
    """Same monkeypatch pattern as tests/test_x_spell_copy.py - exercises
    best_x_plan without needing a real board of lands."""

    MANA = 25

    def setUp(self):
        self._orig_mana = engine.available_mana_value
        self._orig_find = engine.find_payment
        engine.available_mana_value = lambda state, strategy: self.MANA
        engine.find_payment = _fake_payment

    def tearDown(self):
        engine.available_mana_value = self._orig_mana
        engine.find_payment = self._orig_find


class ColorCategoryMultiplierUnitTests(unittest.TestCase):
    """ValueModel.color_category_multiplier in isolation, against the real
    DEFAULT_VALUE_MODEL numbers (not a hand-rolled test model), so this also
    doubles as a regression check on the actual shipped table."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_primary_color_is_the_1_0_ceiling(self):
        # Blue is WotC-primary at draw; red is WotC-primary at damage
        # (opponent_life_loss). Both should sit at exactly 1.0 - "as good as
        # the pre-v4.11.0 flat rate", not boosted above it.
        self.assertEqual(self.vm.color_category_multiplier("draw", {"U"}), 1.0)
        self.assertEqual(self.vm.color_category_multiplier("opponent_life_loss", {"R"}), 1.0)

    def test_off_color_is_discounted_below_1_0(self):
        self.assertLess(self.vm.color_category_multiplier("draw", {"R"}), 1.0)
        self.assertLess(self.vm.color_category_multiplier("opponent_life_loss", {"U"}), 1.0)
        self.assertLess(self.vm.color_category_multiplier("boardwipe", {"G"}), 1.0)

    def test_white_removal_was_recalibrated_upward_after_edhrec_cross_validation(self):
        # v4.12.0 (Route B): real EDHREC data (Swords to Plowshares 75%,
        # Path to Exile 68% inclusion in mono-white control) showed white's
        # actual removal shape - cheap unconditional exile with a real cost
        # to the opponent - is closer to black's efficiency than the
        # "destroy"-only official color-pie framing suggested. Still below
        # black (1.0, true unconditional kill with no compensation to the
        # opponent), but no longer as low as red/green's 0.70/0.60.
        self.assertEqual(self.vm.color_category_multiplier("removal", {"W"}), 0.80)
        self.assertLess(
            self.vm.color_category_multiplier("removal", {"W"}),
            self.vm.color_category_multiplier("removal", {"B"}),
        )

    def test_multicolor_uses_the_best_applicable_color_not_an_average(self):
        # A Gruul (R/G) card doing ramp should be judged as green (primary,
        # 1.0), not dragged down by red's weaker ramp multiplier - and a
        # Gruul card doing draw should be judged as red's weak draw AND
        # green's weak draw, i.e. still low, since neither color is primary
        # there (confirms this isn't "any color present unlocks 1.0").
        self.assertEqual(self.vm.color_category_multiplier("mana_generated", {"R", "G"}), 1.0)
        rg_draw = self.vm.color_category_multiplier("draw", {"R", "G"})
        self.assertLess(rg_draw, 1.0)
        self.assertEqual(rg_draw, max(
            self.vm.color_category_multiplier("draw", {"R"}),
            self.vm.color_category_multiplier("draw", {"G"}),
        ))

    def test_color_identity_none_is_a_backward_compatible_no_op(self):
        # A call site that doesn't know/pass color info must be unaffected -
        # NOT the colorless fallback. This is the actual bug caught and
        # fixed while building this WP: None and set() must not collapse to
        # the same branch.
        self.assertEqual(self.vm.color_category_multiplier("draw", None), 1.0)
        self.assertEqual(self.vm.color_category_multiplier("boardwipe", None), 1.0)

    def test_explicitly_colorless_is_floored_at_the_categorys_own_worst_color(self):
        # v4.15.7 research finding (task #18): colorless is floored at the
        # WORST color already in the category's own table (Rosewater: "any
        # ability you give to artifacts you are giving to the weakest color
        # in that ability"), not the flat color_category_multipliers_
        # colorless_fallback constant - that constant is now an emergency
        # fallback only, for a category with no table at all.
        draw_table = self.vm.values["color_category_multipliers"]["draw"]
        self.assertEqual(self.vm.color_category_multiplier("draw", set()), min(draw_table.values()))
        self.assertLess(self.vm.color_category_multiplier("draw", set()), 1.0)

    def test_colorless_fallback_constant_only_applies_to_a_category_with_no_per_color_values(self):
        # A category key present but with an empty per-color table (distinct
        # from a category that isn't listed at all, which stays a 1.0
        # no-op) has nothing for min()-of-worst-color to floor against, so
        # it falls back to the flat constant.
        vm = engine.ValueModel(values=dict(
            engine.DEFAULT_VALUE_MODEL,
            color_category_multipliers={"draw": {}},
        ))
        fallback = float(vm.values["color_category_multipliers_colorless_fallback"])
        self.assertEqual(vm.color_category_multiplier("draw", set()), fallback)

    def test_unlisted_category_is_unaffected(self):
        # combat_damage, scry, etc. have no color_category_multipliers row -
        # must stay a pure no-op (1.0) regardless of color, not error out.
        self.assertEqual(self.vm.color_category_multiplier("combat_damage", {"R"}), 1.0)
        self.assertEqual(self.vm.color_category_multiplier("combat_damage", None), 1.0)


class MetricValueBackwardCompatibilityTests(unittest.TestCase):
    """Confirms metric_value/aggregate_value reproduce the exact pre-v4.11.0
    numbers for every call that doesn't pass color_identity - the "nothing
    already-tested regresses" guarantee for v4.9.x/v4.10.0 call sites this
    WP did not touch."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_opponent_life_loss_without_color_matches_pre_v4_11_0_formula(self):
        amount = 7.0
        expected = float(self.vm.values["opponent_life_loss_per_point"]) * self.vm.curved_count("opponent_life_loss", amount)
        self.assertAlmostEqual(self.vm.metric_value("opponent_life_loss", amount, set()), expected)

    def test_draw_without_color_matches_pre_v4_11_0_draw_curve(self):
        self.assertAlmostEqual(self.vm.metric_value("draw", 3, set()), self.vm.draw_value(3))

    def test_removal_and_boardwipe_and_ramp_without_color_are_unaffected(self):
        self.assertAlmostEqual(self.vm.metric_value("removal", 1, set()), float(self.vm.values["removal_event"]))
        self.assertAlmostEqual(self.vm.metric_value("boardwipe", 1, set()), float(self.vm.values["boardwipe_event"]))
        self.assertAlmostEqual(self.vm.metric_value("mana_generated", 2, set()), float(self.vm.values["mana_generated"]) * 2)

    def test_aggregate_value_without_color_matches_per_metric_sum(self):
        metrics = Counter({"draw": 2, "opponent_life_loss": 5})
        expected = self.vm.metric_value("draw", 2, set()) + self.vm.metric_value("opponent_life_loss", 5, set())
        self.assertAlmostEqual(self.vm.aggregate_value(metrics, set()), expected)


class RealCardColorMultiplierEndToEndTests(_WithFakeManaMixin, unittest.TestCase):
    """Real Banefire ({X}{R}, deals X damage to any target) from the
    project's offline Scryfall cache, plus color-swapped clones of the exact
    same card (dataclasses.replace - identical mana cost/oracle text, only
    color_identity differs) run through the real best_x_plan lethal-branch
    search. Numbers below were captured empirically from the actual engine
    (not hand-derived) and are pinned here as a regression baseline."""

    def test_lethal_x_is_identical_across_colors(self):
        # The smallest-lethal-X search reads raw (uncurved, uncolored)
        # damage - color must never change WHETHER a spell is lethal, only
        # how good its reported value is once cast. This is the correctness
        # property that justifies applying the multiplier inside
        # aggregate_value (post-lethal-check) rather than to the raw metric.
        banefire = _load_real_card("Banefire")
        blue_clone = dataclasses.replace(banefire, color_identity={"U"})
        state = make_state(opponents=[10.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")

        plan_red = engine.best_x_plan(banefire, state, strategy)
        plan_blue = engine.best_x_plan(blue_clone, state, strategy)

        self.assertIsNotNone(plan_red)
        self.assertIsNotNone(plan_blue)
        self.assertEqual(plan_red.x, 10)
        self.assertEqual(plan_blue.x, 10, "color must not change the lethal-X determination")

    def test_red_banefire_gross_value_is_unchanged_by_the_new_multiplier(self):
        # Red is WotC-primary at damage -> multiplier 1.0 -> this real card's
        # reported value must be bit-for-bit what it was pre-v4.11.0.
        banefire = _load_real_card("Banefire")
        state = make_state(opponents=[10.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        vm = strategy.value_model or engine.ValueModel.load()

        plan = engine.best_x_plan(banefire, state, strategy)

        metrics = engine.x_effect_metrics(banefire, plan.x, state, strategy)
        pre_v4_11_0_value = vm.aggregate_value(metrics, strategy.archetypes)  # no color arg = old behavior
        self.assertAlmostEqual(plan.gross_value, pre_v4_11_0_value)

    def test_off_color_clone_of_the_same_real_spell_is_discounted_proportionally(self):
        banefire = _load_real_card("Banefire")
        blue_clone = dataclasses.replace(banefire, color_identity={"U"})
        colorless_clone = dataclasses.replace(banefire, color_identity=set())
        state = make_state(opponents=[10.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        vm = strategy.value_model or engine.ValueModel.load()

        plan_red = engine.best_x_plan(banefire, state, strategy)
        plan_blue = engine.best_x_plan(blue_clone, state, strategy)
        plan_colorless = engine.best_x_plan(colorless_clone, state, strategy)

        u_mult = vm.color_category_multiplier("opponent_life_loss", {"U"})
        colorless_mult = vm.color_category_multiplier("opponent_life_loss", set())

        self.assertAlmostEqual(plan_blue.gross_value, plan_red.gross_value * u_mult)
        self.assertAlmostEqual(plan_colorless.gross_value, plan_red.gross_value * colorless_mult)
        # v4.15.7: colorless is now floored at the category's own WORST
        # color (Rosewater: "the weakest color in that ability") - for
        # opponent_life_loss/burn, that IS blue (U=0.10), so they're tied
        # here, not "blue worse than colorless" as under the old flat 0.5
        # placeholder.
        self.assertAlmostEqual(plan_blue.gross_value, plan_colorless.gross_value, msg="blue (0.10) IS the worst color at burn, so colorless is floored at exactly blue's rate")
        self.assertLess(plan_colorless.gross_value, plan_red.gross_value, "colorless is still worse than red, the primary color for burn")

    def test_multicolor_clone_uses_its_best_color_not_an_average(self):
        banefire = _load_real_card("Banefire")
        gruul_clone = dataclasses.replace(banefire, color_identity={"R", "G"})
        state = make_state(opponents=[10.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")

        plan_red = engine.best_x_plan(banefire, state, strategy)
        plan_gruul = engine.best_x_plan(gruul_clone, state, strategy)

        self.assertAlmostEqual(
            plan_gruul.gross_value, plan_red.gross_value,
            msg="R/G should be judged as red (1.0, primary at burn) not averaged down by green's weak burn multiplier",
        )


class ImpactRowsColorAwareTests(unittest.TestCase):
    """impact_rows_from_aggregate (feeds card_impact.csv) must also route
    color identity through, not just the X-spell decision path."""

    def test_card_impact_value_column_reflects_color_multiplier(self):
        banefire = _load_real_card("Banefire")
        blue_clone = dataclasses.replace(banefire, color_identity={"U"}, name="Test Blue Banefire")
        deck = [banefire, blue_clone]
        aggregate = {
            banefire.name: Counter({"opponent_life_loss": 10, "seen": 1, "cast": 1}),
            blue_clone.name: Counter({"opponent_life_loss": 10, "seen": 1, "cast": 1}),
        }
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        vm = strategy.value_model or engine.ValueModel.load()

        rows = engine.impact_rows_from_aggregate(deck, aggregate, runs=1, strategy=strategy)
        by_name = {r["Name"]: r for r in rows}

        u_mult = vm.color_category_multiplier("opponent_life_loss", {"U"})
        # Row values are rounded to 3 decimals for the CSV - compare at the
        # same precision rather than the raw float.
        self.assertAlmostEqual(
            by_name["Test Blue Banefire"]["Estimated total value"],
            round(by_name["Banefire"]["Estimated total value"] * u_mult, 3),
            places=3,
        )


if __name__ == "__main__":
    unittest.main()
