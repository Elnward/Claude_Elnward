"""
Unit tests for v4.15.4: the resource-to-mana-conversion framework
(Docs/DEFAULT_VALUES_AND_COLOR_PIE_v1.md Sec. 5.1/5.1.1, mirrored in
Data/Models/default_value_table_and_color_pie.json::resource_to_mana_conversion
and implemented in Data/Models/goldfish_value_model.json::
resource_to_mana_conversion / ValueModel.life_as_mana_equivalent /
delve_mana_equivalent / convoke_improvise_mana_equivalent /
sacrifice_cost_equivalent / stun_counter_value_multiplier /
stun_counter_mana_equivalent_fallback / uptime_value_discount).

IMPORTANT, stated plainly (same honesty pattern as v4.14.0's Route E tests):
life/delve/convoke_improvise have an OFFICIAL WotC conversion rate (Phyrexian
mana / Delve / Convoke keyword templating) - those numbers are cited, not
guessed. stun_counter_value_discount_per_counter has NO official reference
and is a clearly-flagged first-guess constant; these tests check its
STRUCTURE (monotonic decrease, floored at 0) rather than asserting the 0.15
figure is "correct".

Run from the project root:
    python -m unittest tests.test_resource_to_mana_conversion -v
"""
from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


class LifeAsCostTests(unittest.TestCase):
    """Official WotC design rate (Phyrexian mana templating): 2 life = 1 mana."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_zero_life_is_zero_mana(self):
        self.assertEqual(self.vm.life_as_mana_equivalent(0), 0.0)

    def test_four_life_is_two_mana(self):
        self.assertEqual(self.vm.life_as_mana_equivalent(4), 2.0)

    def test_matches_the_official_two_life_per_mana_rate(self):
        # The rate itself, not just one example - 2 life must always equal
        # exactly 1 mana_unit under the default (uncustomized) value model.
        self.assertEqual(self.vm.life_as_mana_equivalent(2), 1.0)

    def test_negative_life_is_clamped_to_zero(self):
        self.assertEqual(self.vm.life_as_mana_equivalent(-10), 0.0)


class DelveTests(unittest.TestCase):
    """Official WotC keyword templating: 1 graveyard card exiled = 1 mana
    (Treasure Cruise, Dig Through Time, Tasigur)."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_three_cards_delved_is_three_mana(self):
        self.assertEqual(self.vm.delve_mana_equivalent(3), 3.0)

    def test_zero_cards_delved_is_zero(self):
        self.assertEqual(self.vm.delve_mana_equivalent(0), 0.0)

    def test_treasure_cruise_shaped_example(self):
        # Treasure Cruise: printed {7}{U} (mana value 8), Delve. Delving 6
        # graveyard cards should reduce the effective cost to 2, matching the
        # real card's famous "draw three for U" reputation.
        printed_mana_value = 8
        effective = printed_mana_value - self.vm.delve_mana_equivalent(6)
        self.assertEqual(effective, 2.0)


class ConvokeImproviseTests(unittest.TestCase):
    """Official WotC keyword templating: 1 tapped creature/artifact = 1 mana.
    Real project example: Hour of Reckoning (Decks/Aziza V2.txt), {4}{W}{W}{W}
    (mana value 7), Convoke."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_two_tapped_creatures_is_two_mana(self):
        self.assertEqual(self.vm.convoke_improvise_mana_equivalent(2), 2.0)

    def test_hour_of_reckoning_shaped_example(self):
        printed_mana_value = 7  # {4}{W}{W}{W}
        effective = printed_mana_value - self.vm.convoke_improvise_mana_equivalent(3)
        self.assertEqual(effective, 4.0)

    def test_zero_tapped_permanents_is_zero(self):
        self.assertEqual(self.vm.convoke_improvise_mana_equivalent(0), 0.0)


class SacrificeCostEquivalentTests(unittest.TestCase):
    """Dynamic lookup (Emerge's own reminder text: cost reduction = the
    exiled/sacrificed creature's own value) - NOT a flat constant."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_none_sacrificed_is_zero(self):
        self.assertEqual(self.vm.sacrifice_cost_equivalent(None), 0.0)

    def test_a_bigger_more_keyworded_creature_costs_more_to_sacrifice_than_a_small_one(self):
        token = make_card("1/1 Token", power=1, toughness=1, roles=set(), keywords=set())
        bomb = make_card(
            "Built-Up Bomb", power=8, toughness=8,
            keywords={"flying", "lifelink", "trample"}, roles={"draw"},
        )
        token_cost = self.vm.sacrifice_cost_equivalent(token)
        bomb_cost = self.vm.sacrifice_cost_equivalent(bomb)
        self.assertGreater(bomb_cost, token_cost)

    def test_never_negative(self):
        card = make_card("Weird Card", power=0, toughness=0, keywords=set(), roles=set())
        self.assertGreaterEqual(self.vm.sacrifice_cost_equivalent(card), 0.0)

    def test_works_without_an_explicit_strategy(self):
        # strategy=None must fall back gracefully (a bare Strategy(value_model=self)),
        # not crash - callers doing quick value-estimation shouldn't need a full
        # ScenarioStrategy on hand just to price a sacrifice.
        card = make_card("Bear", power=2, toughness=2)
        result = self.vm.sacrifice_cost_equivalent(card, strategy=None)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    def test_an_explicit_strategy_is_used_when_given(self):
        card = make_card("Bear", power=2, toughness=2)
        strategy = engine.ScenarioStrategy(value_model=self.vm)
        result = self.vm.sacrifice_cost_equivalent(card, strategy=strategy)
        self.assertGreaterEqual(result, 0.0)


class StunCounterTests(unittest.TestCase):
    """LOW-CONFIDENCE first-guess constants (no official WotC rate exists,
    unlike life/delve/convoke) - structure asserted, not the exact numbers."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_zero_counters_means_no_discount(self):
        self.assertEqual(self.vm.stun_counter_value_multiplier(0), 1.0)

    def test_more_counters_means_a_larger_discount(self):
        one = self.vm.stun_counter_value_multiplier(1)
        three = self.vm.stun_counter_value_multiplier(3)
        self.assertLess(three, one)
        self.assertLess(one, 1.0)

    def test_never_goes_negative_even_at_extreme_counter_counts(self):
        self.assertGreaterEqual(self.vm.stun_counter_value_multiplier(1000), 0.0)

    def test_fallback_flat_rate_scales_linearly_with_counters(self):
        self.assertEqual(self.vm.stun_counter_mana_equivalent_fallback(2), 2.0)
        self.assertEqual(self.vm.stun_counter_mana_equivalent_fallback(0), 0.0)

    def test_preferred_and_fallback_methods_are_independently_configured(self):
        # The two methods use two DIFFERENT constants (a percentage discount
        # vs. a flat mana rate) - changing one must not silently move the other.
        custom = engine.ValueModel(values=dict(
            engine.DEFAULT_VALUE_MODEL,
            resource_to_mana_conversion=dict(
                engine.DEFAULT_VALUE_MODEL["resource_to_mana_conversion"],
                stun_counter_value_discount_per_counter=0.5,
            ),
        ))
        self.assertEqual(custom.stun_counter_value_multiplier(1), 0.5)
        self.assertEqual(custom.stun_counter_mana_equivalent_fallback(1), 1.0)  # unchanged


class UptimeValueDiscountTests(unittest.TestCase):
    """Bucket B general form: conditional attack/block restrictions, Suspend,
    and Decayed all share this one implementation (design doc's own 'same
    bucket-B logic' conclusion) - not a mana conversion, a usability fraction."""

    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_full_uptime_is_unaffected(self):
        self.assertEqual(self.vm.uptime_value_discount(10.0, 1.0), 10.0)

    def test_half_uptime_halves_the_value(self):
        self.assertEqual(self.vm.uptime_value_discount(10.0, 0.5), 5.0)

    def test_zero_uptime_zeroes_the_value(self):
        self.assertEqual(self.vm.uptime_value_discount(10.0, 0.0), 0.0)

    def test_fraction_above_one_is_clamped(self):
        self.assertEqual(self.vm.uptime_value_discount(10.0, 2.0), 10.0)

    def test_fraction_below_zero_is_clamped(self):
        self.assertEqual(self.vm.uptime_value_discount(10.0, -1.0), 0.0)

    def test_negative_base_value_is_clamped(self):
        self.assertEqual(self.vm.uptime_value_discount(-5.0, 0.5), 0.0)

    def test_decayed_shaped_example_single_attack_only(self):
        # Decayed: usable for exactly one attack instead of ongoing board
        # presence - modeled as a steep uptime discount on the creature's
        # normal (multi-turn) value.
        ongoing_value = 8.0
        single_attack_uptime = 0.2  # first-guess proxy: "worth about 1/5 of staying on board"
        self.assertLess(self.vm.uptime_value_discount(ongoing_value, single_attack_uptime), ongoing_value)


class DefaultValueModelMirrorsJsonTests(unittest.TestCase):
    """Project convention: Data/Models/*.json must mirror DEFAULT_VALUE_MODEL
    exactly. Regression guard specifically for the new resource_to_mana_
    conversion section added in v4.15.4."""

    def test_json_file_matches_the_in_code_default_exactly(self):
        json_path = ROOT / "Data" / "Models" / "goldfish_value_model.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(
            data["resource_to_mana_conversion"],
            engine.DEFAULT_VALUE_MODEL["resource_to_mana_conversion"],
        )

    def test_default_value_model_has_all_five_documented_rates(self):
        section = engine.DEFAULT_VALUE_MODEL["resource_to_mana_conversion"]
        for key in (
            "life_as_cost_rate", "delve_rate", "convoke_improvise_rate",
            "stun_counter_mana_equivalent_rate", "stun_counter_value_discount_per_counter",
        ):
            self.assertIn(key, section)


class MissingSectionFallsBackSafelyTests(unittest.TestCase):
    """A hand-built ValueModel without a resource_to_mana_conversion section
    at all (e.g. an old strategy JSON predating v4.15.4) must not crash -
    every rate falls back to its documented default."""

    def setUp(self):
        values = {k: v for k, v in engine.DEFAULT_VALUE_MODEL.items() if k != "resource_to_mana_conversion"}
        self.vm = engine.ValueModel(values=values)

    def test_all_conversions_still_work_with_sensible_defaults(self):
        self.assertEqual(self.vm.life_as_mana_equivalent(2), 1.0)
        self.assertEqual(self.vm.delve_mana_equivalent(1), 1.0)
        self.assertEqual(self.vm.convoke_improvise_mana_equivalent(1), 1.0)
        self.assertEqual(self.vm.stun_counter_mana_equivalent_fallback(1), 1.0)
        self.assertEqual(self.vm.stun_counter_value_multiplier(1), 0.85)


if __name__ == "__main__":
    unittest.main()
