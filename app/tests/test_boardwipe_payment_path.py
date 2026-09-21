"""
Unit tests for v4.15.5: wiring ValueModel.boardwipe_effective_cost_estimate's
long-flagged gap ("wiring the actual payment/casting path ... is a separate,
not-yet-built feature") to the REAL cast/payment path via the new module-level
`boardwipe_self_scaling_discount` function, called from `cast_option`
alongside the existing `effective_cost_discount`.

Run from the project root:
    python -m unittest tests.test_boardwipe_payment_path -v
"""
from __future__ import annotations

import dataclasses
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Sorcery", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=None, toughness=None, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_creature(name="Bear", **overrides):
    return make_card(name, type_line="Creature", power=2, toughness=2, **overrides)


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


FURYGALE_TEXT = (
    "This spell costs {1} less to cast for each instant and sorcery card in your graveyard.\n"
    "For each opponent, create two 3/3 blue and red Elemental creature tokens with flying "
    "that attack that opponent this turn if able. They gain haste until end of turn."
)

# The REAL Blasphemous Act oracle text (confirmed against Scryfall) -
# "for each creature ON THE BATTLEFIELD", NOT "you control". v4.33.0: this
# used to say "for each other creature you control" here, which happened to
# be recognized by _count_self_scaling_condition's "you control" branch and
# masked the fact that the real card's actual wording fell through every
# branch and got a silent zero discount - see BlasphemousActRealWordingTests
# below, which pins the exact real text.
BLASPHEMOUS_ACT_SHAPED_TEXT = (
    "This spell costs {1} less to cast for each creature on the battlefield.\n"
    "Blasphemous Act deals 13 damage to each creature."
)

MARCH_OF_WRETCHED_SORROW_TEXT = (
    "As an additional cost to cast this spell, you may exile any number of black cards "
    "from your hand. This spell costs {2} less to cast for each card exiled this way.\n"
    "March of Wretched Sorrow deals X damage to target creature or planeswalker and you gain X life."
)


class BoardwipeSelfScalingDiscountUnitTests(unittest.TestCase):
    def test_furygale_flocking_real_card_counts_instants_and_sorceries_in_graveyard(self):
        card = make_card("Furygale Flocking", mana_cost="{8}{R}{R}", mana_value=10, oracle_text=FURYGALE_TEXT)
        state = make_state(graveyard=[
            make_card("Bolt", type_line="Instant"),
            make_card("Char", type_line="Sorcery"),
            make_creature("Not a Spell"),
        ])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 2)
        self.assertEqual(attribution, {"Furygale Flocking": 2})

    def test_creature_on_the_battlefield_condition_counts_the_whole_board(self):
        card = make_card("Blasphemous-Act-Shaped", mana_cost="{6}{R}{R}", mana_value=8, oracle_text=BLASPHEMOUS_ACT_SHAPED_TEXT)
        state = make_state(battlefield=[
            engine.Permanent(card=make_creature("A"), entered_turn=1),
            engine.Permanent(card=make_creature("B"), entered_turn=1),
            engine.Permanent(card=make_creature("C"), entered_turn=1),
        ])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        # "creature on the battlefield": the card itself isn't on the
        # battlefield while being cast, so all 3 creatures present count
        # regardless (this engine has no separate opponent-battlefield model
        # to add on top of - see _count_self_scaling_condition's docstring).
        self.assertEqual(discount, 3)

    def test_you_control_wording_still_works_too(self):
        # The "you control" phrasing (some other real self-scaling cards use
        # this instead of "on the battlefield") must keep working exactly as
        # before - this fix only ADDS a second recognized phrasing.
        card = make_card(
            "You-Control-Shaped", mana_cost="{6}{R}{R}", mana_value=8,
            oracle_text="This spell costs {1} less to cast for each other creature you control.\nDeals 13 damage to each creature.",
        )
        state = make_state(battlefield=[
            engine.Permanent(card=make_creature("A"), entered_turn=1),
            engine.Permanent(card=make_creature("B"), entered_turn=1),
        ])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 2)

    def test_zero_matching_permanents_means_zero_discount(self):
        card = make_card("Furygale Flocking", oracle_text=FURYGALE_TEXT)
        state = make_state(graveyard=[])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 0)
        self.assertEqual(attribution, {})

    def test_march_of_wretched_sorrow_additional_cost_choice_is_not_handled(self):
        # Real card, same "costs {N} less to cast for each ..." text shape,
        # but a materially different mechanic (a CHOICE made while paying, not
        # a passive board-state count) - deliberately excluded, see docstring.
        card = make_card("March of Wretched Sorrow", mana_cost="{X}{B}", oracle_text=MARCH_OF_WRETCHED_SORROW_TEXT)
        state = make_state(hand=[make_card("Some Black Card", color_identity={"B"})])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 0)
        self.assertEqual(attribution, {})

    def test_a_card_with_no_scaling_text_at_all_is_unaffected(self):
        card = make_card("Plain Sorcery", oracle_text="Deal 3 damage to any target.")
        state = make_state(battlefield=[engine.Permanent(card=make_creature("A"), entered_turn=1)])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 0)

    def test_unrecognized_condition_text_yields_no_discount_rather_than_guessing(self):
        card = make_card(
            "Weird Hypothetical",
            oracle_text="This spell costs {1} less to cast for each plane you have visited.",
        )
        state = make_state(battlefield=[engine.Permanent(card=make_creature("A"), entered_turn=1)])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 0)


# The literal, real Blasphemous Act oracle text (confirmed against Scryfall,
# see Docs/README.md v4.33.0 entry) - pinned verbatim so no test fixture can
# silently drift back to the non-real "you control" wording again.
REAL_BLASPHEMOUS_ACT_ORACLE_TEXT = (
    "This spell costs {1} less to cast for each creature on the battlefield.\n"
    "Blasphemous Act deals 13 damage to each creature."
)


class BlasphemousActRealWordingTests(unittest.TestCase):
    """
    v4.33.0: ChatGPT external review flagged that this test file's own
    BLASPHEMOUS_ACT_SHAPED_TEXT fixture used "for each other creature you
    control", which is NOT the real card's wording - the real text is "for
    each creature on the battlefield". _count_self_scaling_condition only
    recognized "creature" together with "you control", so the real wording
    fell through to a silent 0 discount. This class exercises the exact real
    oracle text end to end.
    """

    def test_real_oracle_text_is_recognized_and_discounted(self):
        card = make_card(
            "Blasphemous Act", mana_cost="{8}{R}{R}", mana_value=10,
            oracle_text=REAL_BLASPHEMOUS_ACT_ORACLE_TEXT,
        )
        state = make_state(battlefield=[
            engine.Permanent(card=make_creature("A"), entered_turn=1),
            engine.Permanent(card=make_creature("B"), entered_turn=1),
            engine.Permanent(card=make_creature("C"), entered_turn=1),
            engine.Permanent(card=make_creature("D"), entered_turn=1),
        ])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 4)
        self.assertEqual(attribution, {"Blasphemous Act": 4})

    def test_real_oracle_text_with_an_empty_board_gives_no_discount(self):
        card = make_card(
            "Blasphemous Act", mana_cost="{8}{R}{R}", mana_value=10,
            oracle_text=REAL_BLASPHEMOUS_ACT_ORACLE_TEXT,
        )
        state = make_state(battlefield=[])
        discount, attribution = engine.boardwipe_self_scaling_discount(card, state)
        self.assertEqual(discount, 0)
        self.assertEqual(attribution, {})

    def test_end_to_end_through_cast_option_the_real_card_is_actually_cheaper(self):
        # Confirms the fix reaches the real cast/payment path (cast_option),
        # not just boardwipe_self_scaling_discount's own return value.
        card = make_card(
            "Blasphemous Act", mana_cost="{8}{R}{R}", mana_value=10,
            oracle_text=REAL_BLASPHEMOUS_ACT_ORACLE_TEXT, color_identity={"R"},
        )
        state = make_state(battlefield=[
            engine.Permanent(card=make_creature("A"), entered_turn=1),
            engine.Permanent(card=make_creature("B"), entered_turn=1),
            engine.Permanent(card=make_creature("C"), entered_turn=1),
        ])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        orig_mana = engine.available_mana_value
        orig_find = engine.find_payment
        engine.available_mana_value = lambda state, strategy: 25
        engine.find_payment = _fake_payment
        try:
            opt = engine.cast_option(card, state, strategy)
        finally:
            engine.available_mana_value = orig_mana
            engine.find_payment = orig_find
        self.assertIsNotNone(opt, "cast_option should offer to cast the discounted spell")
        # Base cost 10, discount 3 (3 creatures on the battlefield) -> 7.
        self.assertEqual(opt.total_cost, 7)
        self.assertEqual(opt.discount_attribution.get("Blasphemous Act"), 3)


def _fake_payment(state, strategy, total_cost, req, *args, **kwargs):
    return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)


class CastOptionRealPaymentPathIntegrationTests(unittest.TestCase):
    """End-to-end through cast_option itself, not just the unit-level
    boardwipe_self_scaling_discount call above - confirms the discount is
    actually threaded into the real total_cost a caller would pay."""

    def setUp(self):
        self._orig_mana = engine.available_mana_value
        self._orig_find = engine.find_payment
        engine.available_mana_value = lambda state, strategy: 25
        engine.find_payment = _fake_payment

    def tearDown(self):
        engine.available_mana_value = self._orig_mana
        engine.find_payment = self._orig_find

    def test_furygale_flocking_total_cost_reflects_the_real_discount(self):
        card = make_card("Furygale Flocking", mana_cost="{8}{R}{R}", mana_value=10, oracle_text=FURYGALE_TEXT, color_identity={"R"})
        state = make_state(graveyard=[
            make_card("Bolt", type_line="Instant"),
            make_card("Char", type_line="Sorcery"),
            make_card("Zap", type_line="Instant"),
        ])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        opt = engine.cast_option(card, state, strategy)
        self.assertIsNotNone(opt)
        self.assertEqual(opt.total_cost, 7)  # printed 10 - 3 instants/sorceries in graveyard
        self.assertEqual(opt.discount_attribution.get("Furygale Flocking"), 3)

    def test_no_graveyard_fuel_means_full_printed_cost(self):
        card = make_card("Furygale Flocking", mana_cost="{8}{R}{R}", mana_value=10, oracle_text=FURYGALE_TEXT, color_identity={"R"})
        state = make_state(graveyard=[])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        opt = engine.cast_option(card, state, strategy)
        self.assertIsNotNone(opt)
        self.assertEqual(opt.total_cost, 10)

    def test_never_reduced_below_the_colored_pip_floor(self):
        # A card whose color_requirements alone already exceed the scaled-down
        # total must still cost at least its colored pips.
        card = make_card(
            "Heavily Pipped Wipe", mana_cost="{R}{R}{R}", mana_value=3,
            oracle_text=BLASPHEMOUS_ACT_SHAPED_TEXT, color_identity={"R"},
        )
        state = make_state(battlefield=[
            engine.Permanent(card=make_creature(f"C{i}"), entered_turn=1) for i in range(50)
        ])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        opt = engine.cast_option(card, state, strategy)
        self.assertIsNotNone(opt)
        self.assertEqual(opt.total_cost, 3)  # floored at the 3 red pips, not driven to 0

    def test_external_and_self_scaling_discounts_combine_in_one_attribution_dict(self):
        # A cost-reducing permanent on board (external, effective_cost_discount)
        # PLUS the card's own self-scaling text (internal, this feature) should
        # both show up, additively, in the same discount_attribution dict.
        reducer = engine.Permanent(
            card=make_card("Cost Reducer", type_line="Artifact", oracle_text="Sorcery spells you cast cost {1} less."),
            entered_turn=1,
        )
        card = make_card("Furygale Flocking", mana_cost="{8}{R}{R}", mana_value=10, oracle_text=FURYGALE_TEXT, color_identity={"R"})
        state = make_state(
            battlefield=[reducer],
            graveyard=[make_card("Bolt", type_line="Instant"), make_card("Char", type_line="Sorcery")],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        opt = engine.cast_option(card, state, strategy)
        self.assertIsNotNone(opt)
        self.assertEqual(opt.total_cost, 7)  # 10 - 1 (external) - 2 (self-scaling)
        self.assertEqual(opt.discount_attribution.get("Cost Reducer"), 1)
        self.assertEqual(opt.discount_attribution.get("Furygale Flocking"), 2)


if __name__ == "__main__":
    unittest.main()
