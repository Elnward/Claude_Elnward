"""
Unit tests for v4.22.0: keyword-mechanic gap batch 2 - Prowess, Delve,
Cycling, Flashback. (Kicker is intentionally NOT implemented - see the
"v4.22.0 scope note" comment right after delve_discount in App/engine.py
for why: it needs cast_option's own total-cost decision to go UP before
find_payment runs, and the resolution path to know afterward whether the
extra was paid - real surgery on the core casting path, not an additive
hook like the four mechanics below, and no real Kicker card in any audited
deck to calibrate a "when is it worth it" heuristic against.)

Run from the project root:
    python -m unittest tests.test_keyword_gaps_2 -v
"""
from __future__ import annotations

import dataclasses
import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App.combat_model import interaction as combat_interaction  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    card = engine.Card(**{k: v for k, v in defaults.items() if k in field_names})
    # keywords is normally derived from oracle_text via keyword_set(), not
    # passed in directly - mirror that so e.g. "prowess"/"delve" in
    # oracle_text actually populate card.keywords like a real Card would.
    return dataclasses.replace(card, keywords=engine.keyword_set(card))


def make_state(**overrides):
    # turn=5 (not 1) so creatures entered_turn=1 aren't summoning-sick -
    # matches tests/test_old_gnawbone.py's convention.
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


ALWAYS_UNBLOCKED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
}


def with_weights(weights, fn):
    original = combat_interaction._WEIGHTS
    try:
        combat_interaction._WEIGHTS = weights
        return fn()
    finally:
        combat_interaction._WEIGHTS = original


def _fake_payment(state, strategy, total_cost, req, *args, **kwargs):
    """Always-affordable payment, same pattern as
    tests/test_boardwipe_payment_path.py's _fake_payment - lets a test cast
    a spell without constructing real lands."""
    return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)


class PatchedPaymentTestCase(unittest.TestCase):
    """Shared setUp/tearDown for tests that monkeypatch find_payment."""

    def setUp(self):
        self._orig_find = engine.find_payment
        engine.find_payment = _fake_payment

    def tearDown(self):
        engine.find_payment = self._orig_find


class ProwessTests(PatchedPaymentTestCase):
    def test_casting_a_noncreature_spell_buffs_a_prowess_creature(self):
        def run():
            prowess_creature = engine.Permanent(
                card=make_card("Young Pyromancer-ish", power=1, toughness=1, oracle_text="Prowess"),
                entered_turn=1, tapped=False,
            )
            state = make_state(
                battlefield=[prowess_creature],
                hand=[make_card("Shock", type_line="Instant", mana_cost="{R}", mana_value=1, power=None, toughness=None)],
            )
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
            self.assertEqual(engine.creature_power(prowess_creature, state), 1.0)
            self.assertTrue(engine.try_cast_card(state, strategy, state.hand[0]))
            self.assertEqual(engine.creature_power(prowess_creature, state), 2.0)  # 1 base + 1 prowess

            engine.attack_phase(state, strategy, random.Random(1))
            self.assertEqual(state.opponents[0], 38.0)  # 40 - 2 (buffed power)
        with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_creature_spells_do_not_trigger_prowess(self):
        prowess_creature = engine.Permanent(
            card=make_card("Prowess Guy", power=1, toughness=1, oracle_text="Prowess"),
            entered_turn=1, tapped=False,
        )
        state = make_state(
            battlefield=[prowess_creature],
            hand=[make_card("Some Bear", type_line="Creature", mana_cost="{1}{G}", mana_value=2)],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        self.assertTrue(engine.try_cast_card(state, strategy, state.hand[0]))
        self.assertEqual(engine.creature_power(prowess_creature, state), 1.0)  # unchanged

    def test_multiple_noncreature_spells_stack_the_bonus(self):
        prowess_creature = engine.Permanent(
            card=make_card("Stacker", power=1, toughness=1, oracle_text="Prowess"),
            entered_turn=1, tapped=False,
        )
        state = make_state(
            battlefield=[prowess_creature],
            hand=[
                make_card("Bolt A", type_line="Instant", mana_cost="{R}", mana_value=1, power=None, toughness=None),
                make_card("Bolt B", type_line="Instant", mana_cost="{R}", mana_value=1, power=None, toughness=None),
            ],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        for card in list(state.hand):
            engine.try_cast_card(state, strategy, card)
        self.assertEqual(engine.creature_power(prowess_creature, state), 3.0)  # 1 + 1 + 1

    def test_prowess_bonus_expires_at_the_next_untap_step(self):
        prowess_creature = engine.Permanent(
            card=make_card("Fader", power=1, toughness=1, oracle_text="Prowess"),
            entered_turn=1, tapped=False,
        )
        state = make_state(
            battlefield=[prowess_creature],
            hand=[make_card("Bolt", type_line="Instant", mana_cost="{R}", mana_value=1, power=None, toughness=None)],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.try_cast_card(state, strategy, state.hand[0])
        self.assertEqual(engine.creature_power(prowess_creature, state), 2.0)
        state.turn = 6
        engine.untap_step(state)
        self.assertEqual(engine.creature_power(prowess_creature, state), 1.0)


class DelveTests(unittest.TestCase):
    def test_delve_discount_is_capped_by_the_generic_portion_of_the_cost(self):
        card = make_card(
            "Big Delver", type_line="Sorcery", mana_cost="{4}{U}", mana_value=5,
            oracle_text="Delve\nDraw two cards.", power=None, toughness=None,
        )
        state = make_state(graveyard=[make_card(f"GY{i}") for i in range(10)])
        discount, attribution = engine.delve_discount(card, state)
        self.assertEqual(discount, 4)  # generic portion only, never the U pip
        self.assertEqual(attribution, {"Delve": 4})

    def test_delve_discount_is_capped_by_graveyard_size(self):
        card = make_card(
            "Small Yard", type_line="Sorcery", mana_cost="{4}{U}", mana_value=5,
            oracle_text="Delve\nDraw two cards.", power=None, toughness=None,
        )
        state = make_state(graveyard=[make_card("GY1"), make_card("GY2")])
        discount, attribution = engine.delve_discount(card, state)
        self.assertEqual(discount, 2)

    def test_non_delve_card_gets_no_discount(self):
        card = make_card("Plain Sorcery", type_line="Sorcery", mana_cost="{4}{U}", mana_value=5, power=None, toughness=None)
        state = make_state(graveyard=[make_card(f"GY{i}") for i in range(10)])
        discount, attribution = engine.delve_discount(card, state)
        self.assertEqual(discount, 0)
        self.assertEqual(attribution, {})

    def test_casting_a_delve_spell_actually_exiles_the_graveyard_cards_used(self):
        def fake_payment(state, strategy, total_cost, req, *a, **k):
            return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)
        orig = engine.find_payment
        engine.find_payment = fake_payment
        try:
            card = make_card(
                "Treasure Cruise-ish", type_line="Sorcery", mana_cost="{7}{U}", mana_value=8,
                oracle_text="Delve\nDraw three cards.", power=None, toughness=None, color_identity={"U"},
            )
            gy_cards = [make_card(f"GY{i}") for i in range(10)]
            state = make_state(
                graveyard=list(gy_cards), hand=[card],
                library=[make_card(f"Lib{i}") for i in range(5)],
            )
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
            opt = engine.cast_option(card, state, strategy)
            self.assertEqual(opt.total_cost, 1)  # 8 - 7 generic delved away
            self.assertTrue(engine.try_cast_option(state, strategy, opt))
            self.assertEqual(len(state.exile), 7)  # 7 of the 10 GY cards delved away
            # Delve doesn't exile the spell ITSELF (that's the spell's own
            # normal "goes to graveyard after resolving" behavior) - so the
            # graveyard ends up with the 3 non-delved cards plus the spell.
            self.assertEqual(len(state.graveyard), 4)
            self.assertIn(card, state.graveyard)
            self.assertEqual(len(state.hand), 3)  # drew 3 (the spell's own effect)
        finally:
            engine.find_payment = orig


class CyclingTests(unittest.TestCase):
    def test_cycling_discards_and_draws_when_affordable(self):
        def fake_payment(state, strategy, total_cost, req, *a, **k):
            return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0) if total_cost <= 2 else None
        orig = engine.find_payment
        engine.find_payment = fake_payment
        try:
            cycler = make_card(
                "Cycler", type_line="Sorcery", mana_cost="{3}{U}", mana_value=4,
                oracle_text="Cycling {2} ({2}, Discard this card: Draw a card.)",
                power=None, toughness=None,
            )
            state = make_state(
                hand=[cycler],
                library=[make_card(f"Lib{i}") for i in range(5)],
            )
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
            engine.maybe_cycle_cards(state, strategy)
            self.assertNotIn(cycler, state.hand)
            self.assertIn(cycler, state.graveyard)
            self.assertEqual(len(state.hand), 1)  # drew a replacement
        finally:
            engine.find_payment = orig

    def test_cheapest_cycling_card_goes_first_and_unaffordable_ones_are_skipped(self):
        def fake_payment(state, strategy, total_cost, req, *a, **k):
            return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0) if total_cost <= 1 else None
        orig = engine.find_payment
        engine.find_payment = fake_payment
        try:
            cheap = make_card(
                "Cheap Cycler", oracle_text="Cycling {1}", type_line="Sorcery",
                mana_cost="{2}", mana_value=2, power=None, toughness=None,
            )
            pricey = make_card(
                "Pricey Cycler", oracle_text="Cycling {3}", type_line="Sorcery",
                mana_cost="{4}", mana_value=4, power=None, toughness=None,
            )
            state = make_state(
                hand=[pricey, cheap],
                library=[make_card(f"Lib{i}") for i in range(5)],
            )
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
            engine.maybe_cycle_cards(state, strategy)
            self.assertIn(cheap, state.graveyard)
            self.assertIn(pricey, state.hand)  # too expensive under this fake payment
        finally:
            engine.find_payment = orig

    def test_no_cycling_cards_in_hand_is_a_no_op(self):
        state = make_state(hand=[make_card("Plain Bear")])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.maybe_cycle_cards(state, strategy)
        self.assertEqual(len(state.hand), 1)


class FlashbackTests(unittest.TestCase):
    def test_flashback_casts_from_the_graveyard_and_then_exiles(self):
        def fake_payment(state, strategy, total_cost, req, *a, **k):
            return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)
        orig = engine.find_payment
        engine.find_payment = fake_payment
        try:
            spell = make_card(
                "Regrowth-ish", type_line="Sorcery", mana_cost="{2}{G}", mana_value=3,
                oracle_text="Flashback {4}{G}\nDraw a card.", power=None, toughness=None,
            )
            state = make_state(
                graveyard=[spell],
                library=[make_card(f"Lib{i}") for i in range(5)],
            )
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
            engine.maybe_flashback_cards(state, strategy)
            self.assertNotIn(spell, state.graveyard)
            self.assertIn(spell, state.exile)
            self.assertEqual(len(state.hand), 1)  # the spell's own "draw a card" resolved
        finally:
            engine.find_payment = orig

    def test_permanents_are_never_flashbacked(self):
        # Real templating: Flashback is (almost) exclusively an instant/
        # sorcery mechanic - a permanent card is out of scope here.
        creature = make_card(
            "Not Flashback-able", type_line="Creature", oracle_text="Flashback {1}",
            power=2, toughness=2,
        )
        self.assertIsNone(engine._flashback_cost(creature))

    def test_no_flashback_cards_in_graveyard_is_a_no_op(self):
        state = make_state(graveyard=[make_card("Plain Sorcery", type_line="Sorcery", power=None, toughness=None)])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.maybe_flashback_cards(state, strategy)
        self.assertEqual(len(state.graveyard), 1)


if __name__ == "__main__":
    unittest.main()
