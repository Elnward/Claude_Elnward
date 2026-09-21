"""
Unit tests for App/combat_model/posture.py (WP5, revisited after WP6/WP7).

Run from the project root:
    python -m unittest tests.test_commander_posture -v
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
from App.combat_model import posture as posture_model  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Legendary Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=3, commander=True,
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


ALWAYS_UNBLOCKED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
    "posture": {"balanced_min_other_attackers": 2},
}


class InferAutoPostureTests(unittest.TestCase):
    def test_engine_roles_infer_passive(self):
        card = make_card(roles={"engine", "lifegain_replacement", "tutor"})  # Bilbo-shaped
        self.assertEqual(posture_model.infer_auto_posture(card), "passive")

    def test_finisher_role_infers_aggressive(self):
        card = make_card(roles={"finisher"})
        self.assertEqual(posture_model.infer_auto_posture(card), "aggressive")

    def test_no_roles_infers_balanced(self):
        card = make_card(roles=set())
        self.assertEqual(posture_model.infer_auto_posture(card), "balanced")


class AttackValueTriggerTests(unittest.TestCase):
    def test_self_name_attack_trigger_detected(self):
        card = make_card("Wyleth, Soul of Steel", oracle_text="Trample\nWhenever Wyleth attacks, draw a card.")
        self.assertTrue(posture_model.has_attack_value_trigger(card))

    def test_this_creature_attack_trigger_detected(self):
        card = make_card(oracle_text="Whenever this creature attacks, create a Treasure token.")
        self.assertTrue(posture_model.has_attack_value_trigger(card))

    def test_no_trigger_for_unrelated_text(self):
        card = make_card(oracle_text="If you would gain life, you gain that much life plus 1 instead.")
        self.assertFalse(posture_model.has_attack_value_trigger(card))


class CommanderShouldAttackTests(unittest.TestCase):
    def test_aggressive_always_attacks_even_with_no_reason(self):
        commander = engine.Permanent(card=make_card(roles=set()), entered_turn=1)
        state = make_state(battlefield=[commander])
        strategy = engine.ScenarioStrategy(commander_posture="aggressive")
        self.assertTrue(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=0)
        )

    def test_passive_engine_commander_stays_home_with_no_reason(self):
        commander = engine.Permanent(
            card=make_card(roles={"engine", "lifegain_replacement", "tutor"}, power=2),
            entered_turn=1,
        )
        state = make_state(battlefield=[commander], opponents=[40.0])
        strategy = engine.ScenarioStrategy(commander_posture="passive")
        self.assertFalse(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=0)
        )

    def test_passive_commander_still_attacks_for_lethal(self):
        commander = engine.Permanent(card=make_card(power=50, roles={"engine"}), entered_turn=1)
        state = make_state(battlefield=[commander], opponents=[10.0])
        strategy = engine.ScenarioStrategy(commander_posture="passive")
        self.assertTrue(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=0)
        )

    def test_passive_commander_still_attacks_to_close_out_commander_damage(self):
        commander = engine.Permanent(card=make_card(power=11, roles={"engine"}), entered_turn=1)
        state = make_state(battlefield=[commander], opponents=[40.0])
        state.commander_damage_dealt[("Test Card", 0)] = 10.0  # 11 remaining, exactly lethal via commander damage
        strategy = engine.ScenarioStrategy(commander_posture="passive")
        self.assertTrue(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=0)
        )

    def test_passive_commander_does_not_attack_to_merely_start_the_ledger(self):
        # already == 0 -> "meaningfully progress" doesn't count a first poke as a reason.
        commander = engine.Permanent(card=make_card(power=3, roles={"engine"}), entered_turn=1)
        state = make_state(battlefield=[commander], opponents=[40.0])
        strategy = engine.ScenarioStrategy(commander_posture="passive")
        self.assertFalse(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=0)
        )

    def test_balanced_attacks_when_board_is_already_wide(self):
        commander = engine.Permanent(card=make_card(roles=set()), entered_turn=1)
        state = make_state(battlefield=[commander], opponents=[40.0])
        strategy = engine.ScenarioStrategy(commander_posture="balanced")
        self.assertTrue(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=2)
        )

    def test_balanced_stays_home_when_board_is_thin_and_no_other_reason(self):
        commander = engine.Permanent(card=make_card(roles=set()), entered_turn=1)
        state = make_state(battlefield=[commander], opponents=[40.0])
        strategy = engine.ScenarioStrategy(commander_posture="balanced")
        self.assertFalse(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=1)
        )

    def test_auto_infers_passive_for_bilbo_shaped_commander(self):
        commander = engine.Permanent(
            card=make_card(roles={"engine", "lifegain_replacement", "tutor"}, power=2),
            entered_turn=1,
        )
        state = make_state(battlefield=[commander], opponents=[40.0])
        strategy = engine.ScenarioStrategy(commander_posture="auto")
        self.assertFalse(
            posture_model.commander_should_attack(engine, state, strategy, commander, other_attacker_count=0)
        )


class AttackPhaseIntegrationTests(unittest.TestCase):
    def _run(self, commander, others, posture, opponents=None):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = ALWAYS_UNBLOCKED_WEIGHTS
            state = make_state(battlefield=[commander] + others, opponents=opponents or [40.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture=posture)
            engine.attack_phase(state, strategy, random.Random(1))
            return state
        finally:
            combat_interaction._WEIGHTS = original

    def test_passive_bilbo_like_commander_does_not_attack_alone(self):
        commander = engine.Permanent(
            card=make_card("Engine Commander", roles={"engine", "lifegain_replacement"}, power=2),
            entered_turn=1,
        )
        state = self._run(commander, [], "passive")
        self.assertFalse(commander.tapped)
        self.assertEqual(state.opponents[0], 40.0)

    def test_aggressive_commander_attacks_alone(self):
        commander = engine.Permanent(card=make_card("Aggro Commander", roles={"finisher"}, power=4), entered_turn=1)
        state = self._run(commander, [], "aggressive")
        self.assertTrue(commander.tapped)
        self.assertEqual(state.opponents[0], 36.0)

    def test_non_commander_creatures_are_never_gated_by_posture(self):
        commander = engine.Permanent(
            card=make_card("Engine Commander", roles={"engine"}, power=2), entered_turn=1,
        )
        sidekick = engine.Permanent(
            card=make_card("Sidekick", power=3, commander=False), entered_turn=1,
        )
        state = self._run(commander, [sidekick], "passive")
        self.assertFalse(commander.tapped)   # stays home
        self.assertTrue(sidekick.tapped)     # attacks as normal
        self.assertEqual(state.opponents[0], 37.0)  # only sidekick's 3 damage


class NonCommanderEngineGatingTests(unittest.TestCase):
    """WP5 generalization: engine-role creatures other than the commander are now
    gated the same way - motivated by real 200-run data (Doctor Strange, Surgeon)."""

    def test_ordinary_creature_without_engine_role_always_attacks(self):
        beater = engine.Permanent(card=make_card("Beater", commander=False, roles=set()), entered_turn=1)
        self.assertTrue(
            posture_model.creature_should_attack(engine, make_state(), engine.ScenarioStrategy(), beater, other_attacker_count=0)
        )

    def test_noncommander_engine_role_creature_is_gated_like_passive(self):
        doctor = engine.Permanent(
            card=make_card("Doctor Strange, Surgeon", commander=False, roles={"engine", "lifegain", "lifegain_replacement"}, power=2),
            entered_turn=1,
        )
        state = make_state(battlefield=[doctor], opponents=[40.0])
        strategy = engine.ScenarioStrategy(commander_posture="passive")
        self.assertFalse(
            posture_model.creature_should_attack(engine, state, strategy, doctor, other_attacker_count=0)
        )

    def test_noncommander_engine_role_creature_still_attacks_for_lethal(self):
        doctor = engine.Permanent(
            card=make_card("Doctor Strange, Surgeon", commander=False, roles={"engine"}, power=50),
            entered_turn=1,
        )
        state = make_state(battlefield=[doctor], opponents=[10.0])
        strategy = engine.ScenarioStrategy(commander_posture="passive")
        self.assertTrue(
            posture_model.creature_should_attack(engine, state, strategy, doctor, other_attacker_count=0)
        )

    def test_noncommander_engine_role_creature_respects_aggressive_posture(self):
        doctor = engine.Permanent(
            card=make_card("Doctor Strange, Surgeon", commander=False, roles={"engine"}, power=2),
            entered_turn=1,
        )
        state = make_state(battlefield=[doctor], opponents=[40.0])
        strategy = engine.ScenarioStrategy(commander_posture="aggressive")
        self.assertTrue(
            posture_model.creature_should_attack(engine, state, strategy, doctor, other_attacker_count=0)
        )

    def test_attack_phase_end_to_end_protects_doctor_strange_like_creature(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = ALWAYS_UNBLOCKED_WEIGHTS
            doctor = engine.Permanent(
                card=make_card("Doctor Strange, Surgeon", commander=False, roles={"engine", "lifegain", "lifegain_replacement"}, power=2, keywords={"lifelink"}),
                entered_turn=1,
            )
            state = make_state(battlefield=[doctor], opponents=[40.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="passive")
            engine.attack_phase(state, strategy, random.Random(1))
            self.assertFalse(doctor.tapped)
            self.assertEqual(state.opponents[0], 40.0)
        finally:
            combat_interaction._WEIGHTS = original

    def test_attack_phase_ordinary_creature_alongside_gated_engine_creature(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = ALWAYS_UNBLOCKED_WEIGHTS
            doctor = engine.Permanent(
                card=make_card("Doctor Strange, Surgeon", commander=False, roles={"engine"}, power=2), entered_turn=1,
            )
            beater = engine.Permanent(card=make_card("Beater", commander=False, roles=set(), power=5), entered_turn=1)
            state = make_state(battlefield=[doctor, beater], opponents=[40.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="passive")
            engine.attack_phase(state, strategy, random.Random(1))
            self.assertFalse(doctor.tapped)
            self.assertTrue(beater.tapped)
            self.assertEqual(state.opponents[0], 35.0)  # only the beater's 5 damage
        finally:
            combat_interaction._WEIGHTS = original


if __name__ == "__main__":
    unittest.main()
