"""
Unit/integration tests for v4.12.0 (Route C): the "Baukastensystem" -
modular, independently-tunable card-shape value factors (keywords, creature
power+toughness sum, instant-speed premium) plus the board-wipe two-
parameter cost estimator (Route C's answer to the red pilot's flagged
Blasphemous-Act-shaped gap).

Covers:
  1. ValueModel.keyword_value - bundles all keywords into one additive
     score (per the user's explicit "lump Lifelink etc. under one Keyword
     category" request), known keywords use their table weight, unknown
     ones fall back to keyword_weight_default rather than being worth 0.
  2. ValueModel.creature_body_value - uses the SUM of power+toughness
     (per the user's own suggestion), calibrated so a "vanilla test"
     creature (P+T == 2x mana value) is worth roughly its own mana cost.
  3. ValueModel.boardwipe_effective_cost_estimate - the two-parameter
     (base cost, scaling count) estimate for self-scaling-cost board wipes,
     floored, with real cards from the project's own Scryfall cache
     confirming the underlying mechanic (self-referential "costs less for
     each X") is real, not hypothetical, even though it isn't wired into
     the live payment path yet (documented scope boundary, same class of
     gap as Delve/Convoke).
  4. cast_score_v4 end-to-end with real cards (Katara: vigilance + 3/3;
     Defiant Bloodlord: flying + 4/5; Deadly Dispute: a real instant) -
     confirms the new factors actually move the sequencing score, and that
     a creature with real stats now scores differently from one with none
     (previously ALL creatures got the same flat +1.0 regardless of size).

Run from the project root:
    python -m unittest tests.test_baukastensystem -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402

_SCRYFALL_CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"


def _load_real_card(name: str) -> engine.Card:
    with _SCRYFALL_CACHE_PATH.open("r", encoding="utf-8") as f:
        cache = json.load(f)
    for obj in cache.values():
        if isinstance(obj, dict) and obj.get("name") == name:
            entry = engine.DeckEntry(name=name)
            return engine.card_from_scryfall(entry, obj, commander_name=None)
    raise AssertionError(f"{name!r} not found in {_SCRYFALL_CACHE_PATH}")


def _has_self_scaling_cost_text(card: engine.Card) -> bool:
    low = card.oracle_text.lower()
    return "less to cast for each" in low


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class KeywordValueTests(unittest.TestCase):
    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_known_keyword_uses_its_table_weight(self):
        self.assertAlmostEqual(self.vm.keyword_value({"flying"}), float(self.vm.values["keyword_weights"]["flying"]))

    def test_multiple_keywords_are_summed_not_averaged(self):
        single = self.vm.keyword_value({"flying"})
        double = self.vm.keyword_value({"flying", "deathtouch"})
        self.assertAlmostEqual(double, single + self.vm.keyword_value({"deathtouch"}))
        self.assertGreater(double, single)

    def test_unknown_keyword_falls_back_to_default_not_zero(self):
        value = self.vm.keyword_value({"some_future_keyword_not_in_the_table"})
        self.assertAlmostEqual(value, float(self.vm.values["keyword_weight_default"]))
        self.assertGreater(value, 0.0)

    def test_no_keywords_is_zero(self):
        self.assertEqual(self.vm.keyword_value(set()), 0.0)
        self.assertEqual(self.vm.keyword_value(None), 0.0)

    def test_real_katara_keywords_include_vigilance_and_score_above_zero(self):
        katara = _load_real_card("Katara, Water Tribe's Hope")
        self.assertIn("vigilance", katara.keywords)
        self.assertGreater(self.vm.keyword_value(katara.keywords), 0.0)


class CreatureBodyValueTests(unittest.TestCase):
    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_vanilla_test_creature_is_worth_roughly_its_own_mana_cost(self):
        # Mark Rosewater's "vanilla test": a fairly-costed vanilla creature
        # has power+toughness ~= 2x mana value (e.g. a 3-mana 3/3). At the
        # default rate (0.5), body_value should land close to the mana
        # value itself - net_value ~= 0 for "just stats, no text".
        for mana_value in (2, 3, 4, 5):
            power = toughness = mana_value
            body_value = self.vm.creature_body_value(power, toughness)
            self.assertAlmostEqual(body_value, mana_value, places=6)

    def test_bigger_body_scores_higher_than_smaller_body(self):
        small = self.vm.creature_body_value(1, 1)
        big = self.vm.creature_body_value(4, 4)
        self.assertLess(small, big)

    def test_no_power_or_toughness_is_zero(self):
        self.assertEqual(self.vm.creature_body_value(None, None), 0.0)

    def test_real_katara_body_value_matches_her_printed_3_3(self):
        katara = _load_real_card("Katara, Water Tribe's Hope")
        self.assertEqual(katara.power, 3.0)
        self.assertEqual(katara.toughness, 3.0)
        self.assertAlmostEqual(self.vm.creature_body_value(katara.power, katara.toughness), 3.0)


class BoardwipeEffectiveCostEstimateTests(unittest.TestCase):
    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_more_scaling_count_lowers_the_effective_cost(self):
        no_scale = self.vm.boardwipe_effective_cost_estimate(base_cost=9, scaling_count=0)
        some_scale = self.vm.boardwipe_effective_cost_estimate(base_cost=9, scaling_count=4)
        full_scale = self.vm.boardwipe_effective_cost_estimate(base_cost=9, scaling_count=8)
        self.assertEqual(no_scale, 9.0)
        self.assertLess(some_scale, no_scale)
        self.assertLess(full_scale, some_scale)

    def test_never_goes_below_the_floor(self):
        # Blasphemous Act's real floor is {R} (1 generic-equivalent unit),
        # regardless of how many creatures are controlled beyond that point.
        estimate = self.vm.boardwipe_effective_cost_estimate(base_cost=9, scaling_count=50)
        self.assertEqual(estimate, float(self.vm.values["boardwipe_scaling_cost_floor"]))

    def test_real_cards_with_this_scaling_cost_shape_exist_in_the_project_deck_cache(self):
        # Confirms the underlying mechanic is real, not hypothetical -
        # neither of these is a board wipe specifically, but both prove the
        # engine's cards actually use this "costs less for each X" template,
        # same class of card the boardwipe estimator is built for.
        march = _load_real_card("March of Wretched Sorrow")
        furygale = _load_real_card("Furygale Flocking")
        self.assertTrue(_has_self_scaling_cost_text(march))
        self.assertTrue(_has_self_scaling_cost_text(furygale))


class CastScoreV4BaukastensystemEndToEndTests(unittest.TestCase):
    """cast_score_v4 (the base definition engine.py's wrapper chain
    ultimately calls into) now adds keyword/body/instant-speed factors on
    top of the pre-existing role-based heuristics - these tests exercise it
    through a real CastOption/GameState/Strategy, not the ValueModel methods
    in isolation."""

    def _score(self, card, state=None, strategy=None):
        state = state or make_state()
        strategy = strategy or engine.ScenarioStrategy(opponent_profile="goldfish")
        opt = engine.CastOption(card=card, total_cost=card.min_cost, payment=None, x_plan=None)
        return engine.cast_score_v4(opt, state, strategy)

    def test_real_katara_scores_higher_than_a_vanilla_creature_with_no_keywords_or_stats(self):
        katara = _load_real_card("Katara, Water Tribe's Hope")
        blank = engine.Card(name="Blank Test Creature", mana_cost="{3}", mana_value=3, type_line="Creature")

        katara_score = self._score(katara)
        blank_score = self._score(blank)

        self.assertGreater(
            katara_score, blank_score,
            "a real 3/3 with vigilance should outscore a statless/keywordless creature",
        )

    def test_bigger_creature_body_now_actually_moves_the_score(self):
        # Before v4.12.0, cast_score's creature bonus was a flat +1.0
        # regardless of size - this is the regression-guard that it no
        # longer is.
        small = engine.Card(name="Small Test Creature", mana_cost="{1}", mana_value=1, type_line="Creature", power=1, toughness=1)
        big = engine.Card(name="Big Test Creature", mana_cost="{1}", mana_value=1, type_line="Creature", power=6, toughness=6)

        self.assertGreater(self._score(big), self._score(small))

    def test_real_instant_gets_the_instant_speed_premium(self):
        deadly_dispute = _load_real_card("Deadly Dispute")
        self.assertTrue(deadly_dispute.is_instant)

        vm = engine.ValueModel.load()
        state = make_state(hand=[deadly_dispute, deadly_dispute, deadly_dispute, deadly_dispute, deadly_dispute])  # avoid its own len(hand)<=4 bonus
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=vm)
        opt = engine.CastOption(card=deadly_dispute, total_cost=deadly_dispute.min_cost, payment=None, x_plan=None)

        with_premium = engine.cast_score_v4(opt, state, strategy)
        # Same card, same everything, but comparing against the instant
        # premium being zeroed out isolates exactly its contribution.
        vm_no_premium = engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL, instant_speed_premium=0.0))
        strategy_no_premium = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=vm_no_premium)
        without_premium = engine.cast_score_v4(opt, state, strategy_no_premium)

        self.assertAlmostEqual(with_premium - without_premium, float(vm.values["instant_speed_premium"]))


if __name__ == "__main__":
    unittest.main()
