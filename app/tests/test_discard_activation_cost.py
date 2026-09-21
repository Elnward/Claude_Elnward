"""
Unit tests for v4.26.0: "Discard a card"/"Discard N cards"-shaped generic
activated-ability costs (looting effects, e.g. "{T}, Discard a card: Draw
a card.").

Found via ChatGPT external review (see Docs/README.md v4.26.0 entry).
Reproduced on the live pre-fix code: this cost component was invisible to
the generic activation parser entirely - a real card whose activation also
happened to include a {T} symbol got auto-executed as "exact" (tap
recognized -> recognized_cost=True), paying only the tap and never
discarding, so a "loot" effect silently became a free extra draw with net
hand size going UP instead of staying flat.

Run from the project root:
    python -m unittest tests.test_discard_activation_cost -v
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
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=1,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


LOOTER_TEXT = "{T}, Discard a card: Draw a card."


def make_looter(hand_size=3):
    # An artifact, not a creature - real looters with this exact cost
    # shape are almost always artifacts (e.g. Barbed Spike), and this
    # sidesteps summoning sickness (_perm_ready), which isn't what this
    # test file is about.
    card = make_card("Test Looter", type_line="Artifact", power=None, toughness=None, oracle_text=LOOTER_TEXT)
    perm = engine.Permanent(card=card, entered_turn=1, tapped=False)
    hand = [make_card(f"Filler{i}") for i in range(hand_size)]
    return card, perm, hand


class ParseDiscardCostTests(unittest.TestCase):
    def test_discard_a_card_is_recognized_as_a_real_cost(self):
        card, _, _ = make_looter()
        abilities = engine.parse_oracle_semantics(card)
        self.assertEqual(len(abilities), 1)
        ability = abilities[0]
        self.assertEqual(ability.discard_count, 1)
        self.assertTrue(ability.tap_source)
        self.assertEqual(ability.execution_mode, "exact")

    def test_discard_two_cards_parses_the_count(self):
        card = make_card("Test Looter Two", oracle_text="{T}, Discard two cards: Draw a card.")
        ability = engine.parse_oracle_semantics(card)[0]
        self.assertEqual(ability.discard_count, 2)


class ExecuteDiscardCostTests(unittest.TestCase):
    def test_activation_actually_discards_a_card_net_hand_size_unchanged(self):
        card, perm, hand = make_looter(hand_size=3)
        state = make_state(battlefield=[perm], hand=list(hand), library=[make_card("Lib1")])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        ability = engine.parse_oracle_semantics(card)[0]

        result = engine.execute_semantic_ability(state, strategy, perm, ability)
        self.assertTrue(result)
        # Started with 3 cards; discarded 1 (cost), drew 1 (effect) -> still 3.
        self.assertEqual(len(state.hand), 3)
        self.assertEqual(len(state.graveyard), 1)
        self.assertTrue(perm.tapped)

    def test_cannot_activate_with_an_empty_hand(self):
        card, perm, _ = make_looter(hand_size=0)
        state = make_state(battlefield=[perm], hand=[], library=[make_card("Lib1")])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        ability = engine.parse_oracle_semantics(card)[0]

        result = engine.execute_semantic_ability(state, strategy, perm, ability)
        self.assertFalse(result)
        self.assertEqual(len(state.hand), 0)
        self.assertEqual(len(state.graveyard), 0)
        self.assertFalse(perm.tapped)  # nothing paid at all

    def test_end_step_looting_never_grows_hand_size_for_free(self):
        # End-to-end via the real generic-activation entry point (end_step),
        # not just the direct execute_semantic_ability call above.
        card, perm, hand = make_looter(hand_size=3)
        state = make_state(
            battlefield=[perm], hand=list(hand),
            library=[make_card(f"Lib{i}") for i in range(5)],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.end_step(state, strategy)
        self.assertEqual(len(state.hand), 3)  # net-neutral, not grown
        self.assertEqual(len(state.graveyard), 1)


if __name__ == "__main__":
    unittest.main()
