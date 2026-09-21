"""
Unit tests for v4.19.0: planeswalker loyalty tracking + once-per-turn
loyalty-ability activation.

Found during the v4.18.0 model-coverage audit: "planeswalker" appeared
exactly once in the whole engine (Card.is_permanent) - no loyalty tracking,
no ability activation, ever, even though 10 different real planeswalkers
appeared across 4 of the 14 audited real decks (Ugin, Nicol Bolas, Sarkhan,
several Lilianas, Vraska, Quintorius). This is a goldfish-shaped model of
the mechanic (see the module comment right above
activate_planeswalker_loyalty_abilities in App/engine.py for the exact
scope boundaries) - this engine has no opposing creatures/permanents, so a
planeswalker can only ever lose loyalty to its own "-N" ability, never
combat, and only abilities whose effect is in the existing generic action
vocabulary (damage-to-a-player-shaped target / draw / gain life / create
tokens) are actually executed.

Run from the project root:
    python -m unittest tests.test_planeswalker_loyalty -v
"""
from __future__ import annotations

import dataclasses
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


def make_state(**overrides):
    defaults = dict(
        library=[make_card(f"Lib{i}") for i in range(20)],
        hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=1,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


UGIN_TEXT = (
    "+2: Ugin deals 3 damage to any target.\n"
    "−X: Exile each permanent with mana value X or less that's one or more colors.\n"
    "−10: You gain 7 life, draw seven cards, then put up to seven permanent "
    "cards from your hand onto the battlefield."
)

# A planeswalker whose only ability this engine can't execute at all - real
# rule shape (Sarkhan-like: becomes a creature; deals damage to a creature,
# not a player; grants an emblem), used to confirm the "stays fully inert,
# never crashes" path.
INERT_TEXT = (
    "+1: Until end of turn, this creature gains flying.\n"
    "−3: This deals 4 damage to target creature.\n"
    "−6: You get an emblem with \"Draw two additional cards each draw step.\""
)

# A cheap, easily-lethal-in-one-shot planeswalker used for the death test.
DIER_TEXT = "−2: Dier deals 1 damage to any target."


def make_ugin(loyalty=7):
    card = make_card(
        "Ugin, the Spirit Dragon", type_line="Legendary Planeswalker — Ugin",
        oracle_text=UGIN_TEXT, loyalty=loyalty, mana_value=8, power=None, toughness=None,
    )
    return card, engine.Permanent(card=card, entered_turn=1, tapped=False)


class ParseLoyaltyAbilitiesTests(unittest.TestCase):
    def test_parses_plus_minus_x_and_unicode_minus(self):
        card, _ = make_ugin()
        abilities = engine.parse_loyalty_abilities(card)
        self.assertEqual(len(abilities), 3)
        self.assertEqual(abilities[0].sign, "+")
        self.assertEqual(abilities[0].cost_text, "2")
        self.assertFalse(abilities[0].is_x)
        self.assertEqual(abilities[1].sign, "-")
        self.assertTrue(abilities[1].is_x)
        self.assertEqual(abilities[2].sign, "-")
        self.assertEqual(abilities[2].cost, 10.0)

    def test_plus_ability_actions_recognize_damage_as_opponent_life_loss(self):
        card, _ = make_ugin()
        abilities = engine.parse_loyalty_abilities(card)
        plus2 = abilities[0]
        self.assertEqual(len(plus2.actions), 1)
        self.assertEqual(plus2.actions[0].kind, "opponent_life_loss")
        self.assertEqual(plus2.actions[0].amount, 3)

    def test_x_ability_with_unrecognized_effect_has_no_actions(self):
        card, _ = make_ugin()
        abilities = engine.parse_loyalty_abilities(card)
        minus_x = abilities[1]
        self.assertEqual(minus_x.actions, [])

    def test_ultimate_recognizes_both_gain_life_and_extended_number_word_draw(self):
        # Regression guard for the v4.19.0 fix alongside this feature: "draw
        # seven cards" (word, not digit) must be recognized - before the fix
        # only the life-gain half of Ugin's real -10 text parsed.
        card, _ = make_ugin()
        abilities = engine.parse_loyalty_abilities(card)
        minus10 = abilities[2]
        kinds = {a.kind: a.amount for a in minus10.actions}
        self.assertEqual(kinds.get("gain_life"), 7)
        self.assertEqual(kinds.get("draw"), 7)

    def test_non_planeswalker_card_has_no_loyalty_abilities(self):
        card = make_card("Some Creature", oracle_text="+2: this does nothing on a creature.")
        self.assertEqual(engine.parse_loyalty_abilities(card), [])


class PermanentLoyaltySeedingTests(unittest.TestCase):
    def test_permanent_seeds_loyalty_from_the_card_on_construction(self):
        card, perm = make_ugin(loyalty=7)
        self.assertEqual(perm.loyalty, 7.0)

    def test_non_planeswalker_permanent_has_no_loyalty(self):
        perm = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        self.assertIsNone(perm.loyalty)

    def test_is_planeswalker_and_is_permanent(self):
        card, _ = make_ugin()
        self.assertTrue(card.is_planeswalker)
        self.assertTrue(card.is_permanent)
        self.assertFalse(card.is_battle)


class ActivateLoyaltyAbilitiesTests(unittest.TestCase):
    def test_plus_ability_used_when_ultimate_unaffordable(self):
        card, perm = make_ugin(loyalty=7)
        state = make_state(battlefield=[perm])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.activate_planeswalker_loyalty_abilities(state, strategy)
        self.assertEqual(perm.loyalty, 9.0)  # 7 + 2
        self.assertEqual(state.opponents[0], 37.0)  # 40 - 3
        self.assertEqual(perm.loyalty_activated_turn, 1)

    def test_ultimate_is_used_once_affordable_instead_of_repeating_plus(self):
        card, perm = make_ugin(loyalty=10)
        state = make_state(battlefield=[perm])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.activate_planeswalker_loyalty_abilities(state, strategy)
        self.assertEqual(perm.loyalty, 0.0)  # 10 - 10
        self.assertEqual(state.life, 47.0)  # 40 + 7
        self.assertEqual(len(state.hand), 7)  # drew 7
        self.assertEqual(state.opponents[0], 40.0)  # ultimate chosen, not +2

    def test_once_per_turn_guard(self):
        card, perm = make_ugin(loyalty=7)
        state = make_state(battlefield=[perm])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.activate_planeswalker_loyalty_abilities(state, strategy)
        engine.activate_planeswalker_loyalty_abilities(state, strategy)  # same turn again
        self.assertEqual(perm.loyalty, 9.0)  # still only one +2
        self.assertEqual(state.opponents[0], 37.0)

        state.turn = 2
        engine.activate_planeswalker_loyalty_abilities(state, strategy)
        self.assertEqual(perm.loyalty, 11.0)  # a second turn allows a second activation

    def test_fully_inert_planeswalker_never_activates_and_never_crashes(self):
        card = make_card(
            "Inert Walker", type_line="Legendary Planeswalker — Test",
            oracle_text=INERT_TEXT, loyalty=5,
        )
        perm = engine.Permanent(card=card, entered_turn=1)
        state = make_state(battlefield=[perm])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        for turn in range(1, 4):
            state.turn = turn
            engine.activate_planeswalker_loyalty_abilities(state, strategy)
        self.assertEqual(perm.loyalty, 5.0)  # never changed - nothing executable
        self.assertEqual(perm.loyalty_activated_turn, -1)  # never activated
        self.assertIn(perm, state.battlefield)  # still alive, no crash

    def test_loyalty_reaching_zero_moves_the_planeswalker_to_the_graveyard(self):
        card = make_card(
            "Dier", type_line="Legendary Planeswalker — Test",
            oracle_text=DIER_TEXT, loyalty=2,
        )
        perm = engine.Permanent(card=card, entered_turn=1)
        state = make_state(battlefield=[perm])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.activate_planeswalker_loyalty_abilities(state, strategy)
        self.assertNotIn(perm, state.battlefield)
        self.assertIn(card, state.graveyard)
        self.assertEqual(state.opponents[0], 39.0)  # the ability still resolved first


class GenericActivationDoesNotDoubleActivateLoyaltyTests(unittest.TestCase):
    """
    v4.25.0 regression, found via ChatGPT external review (Docs/README.md
    v4.25.0 entry). Reproduced on the live pre-fix code: a loyalty-ability
    line like "+1: Draw a card." contains a colon, so parse_oracle_semantics
    classified it as an ordinary "activated" SemanticAbility with
    cost_text="+1" - which _activation_mana() can't find any {mana} symbols
    in, so the ability came back with an apparently "recognized" (i.e. free)
    cost. try_generic_semantic_activations (called every end_step) has no
    loyalty-specific exclusion, only the small hardcoded DEDICATED_RESOLVERS
    name list, and never checks p.loyalty at all - so on the live pre-fix
    code, end_step executed the SAME "+1: Draw a card." a SECOND time, for
    free, on top of the correct once-per-turn loyalty resolver, without
    touching loyalty or checking availability.
    """

    def test_end_step_does_not_grant_a_free_second_loyalty_activation(self):
        card = make_card(
            "Simple Walker", type_line="Legendary Planeswalker — Test",
            oracle_text="+1: Draw a card.\n-2: Draw a card.", loyalty=3,
        )
        perm = engine.Permanent(card=card, entered_turn=1)
        state = make_state(battlefield=[perm], turn=1)
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")

        engine.activate_planeswalker_loyalty_abilities(state, strategy)
        self.assertEqual(perm.loyalty, 4.0)  # 3 + 1, the one legitimate activation
        self.assertEqual(len(state.hand), 1)  # exactly one draw so far

        engine.end_step(state, strategy)
        self.assertEqual(len(state.hand), 1)  # NOT a second free draw
        self.assertEqual(perm.loyalty, 4.0)  # loyalty untouched by end_step

    def test_generic_semantic_activations_skip_loyalty_lines_entirely(self):
        card = make_card(
            "Simple Walker 2", type_line="Legendary Planeswalker — Test",
            oracle_text="+1: Draw a card.\n0: Draw a card.\n−2: Draw a card.",
            loyalty=3,
        )
        for ability in engine.parse_oracle_semantics(card):
            self.assertNotEqual(
                ability.ability_kind, "activated",
                f"loyalty line leaked into generic activation: {ability.raw!r}",
            )


if __name__ == "__main__":
    unittest.main()
