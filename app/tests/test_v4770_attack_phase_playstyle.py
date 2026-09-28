"""
v4.77.0 WP-A: engine.attack_phase's playstyle wrapper -- end-to-end tests
that weak ordinary creatures are held back (or not) exactly as
App/combat_model/playstyle.py intends, while commander/engine-gated
creatures and the wrapped attack_phase's own logic stay untouched.

Run from the project root:
    python -m unittest tests.test_v4770_attack_phase_playstyle -v
"""
from __future__ import annotations

import dataclasses
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App.combat_model import interaction as combat_interaction  # noqa: E402

ALWAYS_UNBLOCKED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
    "posture": {"balanced_min_other_attackers": 2},
    "playstyle": {"attacker_selection_max_power": 3.0},
}


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=1, toughness=1, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class AttackPhasePlaystyleTest(unittest.TestCase):
    def _run(self, battlefield, playstyle, opponents=None, tokens=None):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = ALWAYS_UNBLOCKED_WEIGHTS
            state = make_state(battlefield=battlefield, opponents=opponents or [40.0])
            if tokens:
                state.creature_tokens.extend(tokens)
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", playstyle=playstyle)
            engine.attack_phase(state, strategy, random.Random(1))
            return state
        finally:
            combat_interaction._WEIGHTS = original

    def test_default_playstyle_is_byte_identical_to_unfiltered_attack(self):
        elf = engine.Permanent(card=make_card("Mana Elf", power=1, toughness=1), entered_turn=1)
        state = self._run([elf], {})
        self.assertTrue(elf.tapped)
        self.assertEqual(state.opponents[0], 39.0)

    def test_weak_creature_held_back_at_zero_aggression(self):
        elf = engine.Permanent(card=make_card("Mana Elf", power=1, toughness=1), entered_turn=1)
        state = self._run([elf], {"aggression": 0, "attacker_selection": 0})
        self.assertFalse(elf.tapped)
        self.assertEqual(state.opponents[0], 40.0)

    def test_strong_creature_still_attacks_at_zero_aggression(self):
        beater = engine.Permanent(card=make_card("Big Beater", power=5, toughness=5), entered_turn=1)
        state = self._run([beater], {"aggression": 0, "attacker_selection": 0})
        self.assertTrue(beater.tapped)
        self.assertEqual(state.opponents[0], 35.0)

    def test_evasive_weak_creature_still_attacks(self):
        flier = engine.Permanent(card=make_card("Weak Flier", power=1, toughness=1, keywords={"flying"}), entered_turn=1)
        state = self._run([flier], {"aggression": 0, "attacker_selection": 0})
        self.assertTrue(flier.tapped)
        self.assertEqual(state.opponents[0], 39.0)

    def test_finisher_role_weak_creature_still_attacks(self):
        finisher = engine.Permanent(card=make_card("Weak Finisher", power=1, toughness=1, roles={"finisher"}), entered_turn=1)
        state = self._run([finisher], {"aggression": 0, "attacker_selection": 0})
        self.assertTrue(finisher.tapped)
        self.assertEqual(state.opponents[0], 39.0)

    def test_commander_and_engine_role_creatures_are_untouched_by_playstyle(self):
        # Commander posture defaults to "auto"; roles={"engine"} -> infer_auto_posture
        # returns "passive", so with no attack-value trigger and no lethal, it
        # should NOT attack -- an outcome that must be identical regardless of
        # how restrictive playstyle is, since playstyle never touches gated creatures.
        commander = engine.Permanent(card=make_card("Cmdr", power=2, roles={"engine"}, commander=True), entered_turn=1)
        for ps in ({}, {"aggression": 0, "attacker_selection": 0}, {"aggression": 100, "attacker_selection": 100}):
            with self.subTest(playstyle=ps):
                state = self._run([commander], ps)
                self.assertFalse(commander.tapped)
                self.assertEqual(state.opponents[0], 40.0)
                commander.tapped = False

    def test_lethal_alpha_strike_bypasses_restriction(self):
        # Two weak (power 1 < threshold 3) creatures whose COMBINED power is
        # lethal (opponent at 2 life) -- both attack despite aggression=0.
        e1 = engine.Permanent(card=make_card("Elf A", power=1, toughness=1), entered_turn=1)
        e2 = engine.Permanent(card=make_card("Elf B", power=1, toughness=1), entered_turn=1)
        state = self._run([e1, e2], {"aggression": 0, "attacker_selection": 0}, opponents=[2.0])
        self.assertTrue(e1.tapped)
        self.assertTrue(e2.tapped)
        self.assertEqual(state.opponents[0], 0.0)

    def test_non_lethal_weak_creatures_stay_home_even_together(self):
        e1 = engine.Permanent(card=make_card("Elf A", power=1, toughness=1), entered_turn=1)
        e2 = engine.Permanent(card=make_card("Elf B", power=1, toughness=1), entered_turn=1)
        state = self._run([e1, e2], {"aggression": 0, "attacker_selection": 0}, opponents=[40.0])
        self.assertFalse(e1.tapped)
        self.assertFalse(e2.tapped)
        self.assertEqual(state.opponents[0], 40.0)

    def test_weak_token_group_held_back(self):
        state = self._run([], {"aggression": 0, "attacker_selection": 0},
                          tokens=[engine.TokenGroup(name="Elf Warrior", count=3, power=1, toughness=1, entered_turn=1)])
        self.assertEqual(state.opponents[0], 40.0)
        self.assertEqual(len(state.creature_tokens), 1)
        self.assertEqual(state.creature_tokens[0].count, 3)  # untouched, just didn't attack

    def test_strong_token_group_still_attacks(self):
        state = self._run([], {"aggression": 0, "attacker_selection": 0},
                          tokens=[engine.TokenGroup(name="Big Tokens", count=2, power=4, toughness=4, entered_turn=1)])
        self.assertEqual(state.opponents[0], 32.0)  # 2 * 4 power unblocked

    def test_partial_slider_leaves_the_other_at_default(self):
        # attacker_selection default (100) -> threshold 0 -> nothing is "weak"
        # regardless of aggression, so a weak-power creature still attacks.
        elf = engine.Permanent(card=make_card("Mana Elf", power=1, toughness=1), entered_turn=1)
        state = self._run([elf], {"aggression": 0})
        self.assertTrue(elf.tapped)
        self.assertEqual(state.opponents[0], 39.0)


if __name__ == "__main__":
    unittest.main()
