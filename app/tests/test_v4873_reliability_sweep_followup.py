"""
Unit tests for v4.87.3: the reliability-sweep-v1 follow-up fixes.

Found via a Playwright-verified run of Aziza V2 (real user test, see project
chat/Docs/README.md v4.87.3) and the automated 200-deck reliability sweep
that followed it: two real cards (The Vision, The Scarlet Witch) were
silently under-modeled without ever surfacing as a `model_gaps` entry, and a
third (Shadowborn Apostle) WAS correctly flagged by model_gaps as "cast
often, modeled value near zero". Each fix below closes a real, generic gap
in the semantic-action parser or the cost-discount parser - not a
card-specific hardcode - so any other real card using the same templating
now works the same way.

Run from the project root:
    python -m unittest tests.test_v4873_reliability_sweep_followup -v
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


def make_card(name, **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    card = engine.Card(**{k: v for k, v in defaults.items() if k in field_names})
    return dataclasses.replace(card, keywords=engine.keyword_set(card))


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def make_cast_option(card):
    return engine.CastOption(
        card=card, total_cost=0,
        payment=engine.PaymentPlan(used=[], total=engine.Counter(), penalty=0.0),
        discount_attribution={},
    )


class TestScarlettWitchPowerScaledCostDiscount(unittest.TestCase):
    """The Scarlet Witch (MSH) - "Instant and sorcery spells you cast with
    mana value 4 or greater cost {X} less to cast, where X is The Scarlet
    Witch's power." Before v4.87.3, effective_cost_discount only recognized
    a FIXED integer reduction ("cost {N} less") restricted to creature/
    artifact/enchantment spells, plus one hardcoded life-gain-scaled special
    case - nothing matched a reduction scaled by the SOURCE's own power,
    gated by a spell-type-and-mana-value filter."""

    def setUp(self):
        self.witch = make_card(
            "The Scarlet Witch", type_line="Legendary Creature - Mutant Warlock Hero",
            mana_cost="{2}{R}", mana_value=3, power=2, toughness=3,
            oracle_text="Instant and sorcery spells you cast with mana value 4 or greater "
                        "cost {X} less to cast, where X is The Scarlet Witch's power.",
        )
        self.state = make_state(battlefield=[engine.Permanent(card=self.witch, entered_turn=1)])

    def test_qualifying_sorcery_gets_power_scaled_discount(self):
        big_sorcery = make_card("Big Sorcery", type_line="Sorcery", mana_value=5)
        discount, attrib = engine.effective_cost_discount(big_sorcery, self.state)
        self.assertEqual(discount, 2)
        self.assertEqual(attrib.get("The Scarlet Witch"), 2)

    def test_qualifying_instant_gets_power_scaled_discount(self):
        big_instant = make_card("Big Instant", type_line="Instant", mana_value=4)
        discount, _attrib = engine.effective_cost_discount(big_instant, self.state)
        self.assertEqual(discount, 2)

    def test_below_mana_value_threshold_gets_no_discount(self):
        small_instant = make_card("Small Instant", type_line="Instant", mana_value=2)
        discount, _attrib = engine.effective_cost_discount(small_instant, self.state)
        self.assertEqual(discount, 0)

    def test_wrong_spell_type_gets_no_discount(self):
        big_creature = make_card("Big Creature", type_line="Creature", mana_value=5)
        discount, _attrib = engine.effective_cost_discount(big_creature, self.state)
        self.assertEqual(discount, 0)

    def test_discount_scales_with_current_power(self):
        pumped = engine.Permanent(card=self.witch, entered_turn=1, counters=3)  # +1/+1 counters
        state = make_state(battlefield=[pumped])
        big_sorcery = make_card("Big Sorcery", type_line="Sorcery", mana_value=5)
        discount, _attrib = engine.effective_cost_discount(big_sorcery, state)
        self.assertEqual(discount, 5)  # base power 2 + 3 counters


class TestTheVisionRepeatingModalChoice(unittest.TestCase):
    """The Vision (MSH) - "Whenever you cast a noncreature spell, choose one
    that hasn't been chosen this turn - Solar Beam: ... double strike ...
    Density Control: ... indestructible ... Technopathy: Draw a card."
    Before v4.87.3 this whole header shape was deliberately (and correctly,
    for the time) never resolved at all - _modal_choice_blocks explicitly
    excludes "hasn't been chosen" headers because doing so needs real
    per-turn "which mode already fired" bookkeeping, which didn't exist yet.
    It now does (state.modal_chosen_this_turn, reset every turn)."""

    def setUp(self):
        self.vision = make_card(
            "The Vision", type_line="Legendary Artifact Creature - Robot Hero",
            mana_cost="{4}", mana_value=4, power=2, toughness=5,
            oracle_text=(
                "Flying, vigilance\n"
                "Whenever you cast a noncreature spell, choose one that hasn't been "
                "chosen this turn —\n"
                "• Solar Beam — The Vision gains double strike until end of turn.\n"
                "• Density Control — The Vision gains indestructible until end of turn.\n"
                "• Technopathy — Draw a card.\n"
            ),
        )
        self.perm = engine.Permanent(card=self.vision, entered_turn=1)
        self.strategy = engine.Strategy()
        self.state = make_state(battlefield=[self.perm], turn=3)

    def _cast_noncreature(self, name):
        spell = make_card(name, type_line="Instant", mana_value=1)
        self.state.hand.append(spell)
        return engine.try_cast_option(self.state, self.strategy, make_cast_option(spell))

    def test_first_cast_chooses_one_mode(self):
        self.assertTrue(self._cast_noncreature("Bolt 1"))
        chosen = self.state.modal_chosen_this_turn.get(id(self.perm), set())
        self.assertEqual(len(chosen), 1)

    def test_three_casts_grant_double_strike_and_indestructible(self):
        for i in range(3):
            self._cast_noncreature(f"Bolt {i}")
        self.assertIn("double strike", self.perm.temporary_keywords)
        self.assertIn("indestructible", self.perm.temporary_keywords)
        self.assertEqual(len(self.state.modal_chosen_this_turn.get(id(self.perm), set())), 3)

    def test_fourth_cast_same_turn_does_not_crash_or_repeat(self):
        for i in range(4):
            ok = self._cast_noncreature(f"Bolt {i}")
            self.assertTrue(ok)
        # All 3 modes exhausted; a 4th trigger has nothing left to choose.
        self.assertEqual(len(self.state.modal_chosen_this_turn.get(id(self.perm), set())), 3)

    def test_creature_spell_does_not_trigger(self):
        creature = make_card("Some Bear", type_line="Creature", mana_value=1)
        self.state.hand.append(creature)
        engine.try_cast_option(self.state, self.strategy, make_cast_option(creature))
        self.assertEqual(self.state.modal_chosen_this_turn.get(id(self.perm), set()), set())

    def test_new_turn_resets_and_can_choose_again(self):
        for i in range(3):
            self._cast_noncreature(f"Bolt {i}")
        self.state.turn = 4
        self.state.modal_chosen_this_turn = {}
        self.assertTrue(self._cast_noncreature("Bolt next turn"))
        self.assertEqual(len(self.state.modal_chosen_this_turn.get(id(self.perm), set())), 1)


class TestShadowbornApostleNamedSelfTutor(unittest.TestCase):
    """Shadowborn Apostle - "{1}{B}, Discard a card: Search your library for
    a card named Shadowborn Apostle, put it into your hand, then shuffle."
    Before v4.87.3 the mana+discard COST parsed fine (recognized_cost=True)
    but the EFFECT matched no known action at all, so the whole ability sat
    at execution_mode "review" despite being "recognized" - exactly the
    model_gaps report's real complaint (cast often, ~0 modeled value)."""

    def setUp(self):
        self.oracle_text = (
            "{1}{B}, Discard a card: Search your library for a card named "
            "Shadowborn Apostle, put it into your hand, then shuffle."
        )
        self.apostle = make_card(
            "Shadowborn Apostle", type_line="Creature - Human Cleric",
            mana_cost="{3}{B}", mana_value=4, power=1, toughness=1,
            oracle_text=self.oracle_text,
        )

    def test_ability_parses_as_exact_named_tutor(self):
        abilities = engine.parse_oracle_semantics(self.apostle)
        self.assertEqual(len(abilities), 1)
        ability = abilities[0]
        self.assertEqual(ability.ability_kind, "activated")
        self.assertEqual(ability.execution_mode, "exact")
        self.assertEqual(ability.discard_count, 1)
        self.assertEqual(len(ability.actions), 1)
        self.assertEqual(ability.actions[0].kind, "named_tutor_to_hand")
        self.assertEqual(ability.actions[0].token, "Shadowborn Apostle")

    def test_named_tutor_finds_exact_copy_in_library(self):
        lib_copy = make_card(
            "Shadowborn Apostle", type_line="Creature - Human Cleric",
            mana_cost="{3}{B}", mana_value=4, power=1, toughness=1,
            oracle_text=self.oracle_text,
        )
        other = make_card("Some Other Card", mana_value=2)
        state = make_state(library=[other, lib_copy], hand=[])
        perm = engine.Permanent(card=self.apostle, entered_turn=1)
        action = engine.SemanticAction(
            kind="named_tutor_to_hand", token="Shadowborn Apostle", raw=self.oracle_text,
        )
        handled = engine.execute_semantic_action(state, engine.Strategy(), perm, action)
        self.assertTrue(handled)
        self.assertIn("Shadowborn Apostle", [c.name for c in state.hand])
        self.assertNotIn(lib_copy, state.library)

    def test_named_tutor_is_a_noop_when_not_in_library(self):
        state = make_state(library=[make_card("Something Else", mana_value=2)], hand=[])
        perm = engine.Permanent(card=self.apostle, entered_turn=1)
        action = engine.SemanticAction(
            kind="named_tutor_to_hand", token="Shadowborn Apostle", raw=self.oracle_text,
        )
        handled = engine.execute_semantic_action(state, engine.Strategy(), perm, action)
        self.assertTrue(handled)  # ability recognized/attempted...
        self.assertEqual(state.hand, [])  # ...but nothing to find, so no-op


if __name__ == "__main__":
    unittest.main()
