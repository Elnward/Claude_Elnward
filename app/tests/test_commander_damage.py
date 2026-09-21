"""
Unit tests for the Commander Damage Ledger (WP7, Iteration 1).

Run from the project root:
    python -m unittest tests.test_commander_damage -v
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


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Legendary Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=5, toughness=5, commander=True,
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
}


class CommanderDamageLedgerTests(unittest.TestCase):
    def _with_deterministic_weights(self, fn):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = ALWAYS_UNBLOCKED_WEIGHTS
            fn()
        finally:
            combat_interaction._WEIGHTS = original

    def test_commander_combat_damage_is_recorded_in_the_ledger(self):
        def run():
            commander = engine.Permanent(card=make_card("Mabel, Heir to Cragflame", power=6, toughness=6), entered_turn=1, tapped=False)
            state = make_state(battlefield=[commander], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.commander_damage_dealt.get(("Mabel, Heir to Cragflame", 0), 0.0), 6.0)
        self._with_deterministic_weights(run)

    def test_noncommander_attacker_does_not_touch_the_ledger(self):
        def run():
            sidekick = engine.Permanent(card=make_card("Sidekick", power=4, commander=False), entered_turn=1, tapped=False)
            state = make_state(battlefield=[sidekick], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.commander_damage_dealt.get(0, 0.0), 0.0)
        self._with_deterministic_weights(run)

    def test_double_strike_commander_doubles_damage_and_ledger_entry(self):
        def run():
            commander = engine.Permanent(
                card=make_card("Fast Commander", power=5, keywords={"double strike"}),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[commander], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.opponents[0], 30.0)  # 40 - (5*2)
            self.assertEqual(state.commander_damage_dealt.get(("Fast Commander", 0), 0.0), 10.0)
        self._with_deterministic_weights(run)

    def test_21_commander_damage_eliminates_that_opponent_via_existing_win_check(self):
        def run():
            commander = engine.Permanent(card=make_card("Big Commander", power=25), entered_turn=1, tapped=False)
            state = make_state(battlefield=[commander], opponents=[100.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.opponents[0], 0.0)
            self.assertIsNotNone(state.win_turn)
        self._with_deterministic_weights(run)

    def test_below_21_commander_damage_does_not_eliminate(self):
        def run():
            commander = engine.Permanent(card=make_card("Modest Commander", power=10), entered_turn=1, tapped=False)
            state = make_state(battlefield=[commander], opponents=[100.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.commander_damage_dealt.get(("Modest Commander", 0), 0.0), 10.0)
            self.assertGreater(state.opponents[0], 0.0)
            self.assertIsNone(state.win_turn)
        self._with_deterministic_weights(run)


class CommanderDamageLethalPredicateTests(unittest.TestCase):
    def test_lethal_opportunity_when_power_covers_remaining_21(self):
        commander = engine.Permanent(card=make_card("Big Commander", power=15), entered_turn=1, tapped=False)
        state = make_state(battlefield=[commander], opponents=[40.0])
        state.commander_damage_dealt[("Big Commander", 0)] = 10.0  # 11 remaining, power 15 covers it
        result = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"target": "any"}, state, None,
        )
        self.assertTrue(result.computable)
        self.assertTrue(result.satisfied)

    def test_not_lethal_when_power_is_short(self):
        commander = engine.Permanent(card=make_card("Small Commander", power=3), entered_turn=1, tapped=False)
        state = make_state(battlefield=[commander], opponents=[40.0])
        result = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"target": "any"}, state, None,
        )
        self.assertTrue(result.computable)
        self.assertFalse(result.satisfied)

    def test_no_commander_on_battlefield_is_not_computable(self):
        state = make_state(battlefield=[])
        result = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"target": "any"}, state, None,
        )
        self.assertFalse(result.computable)

    def test_double_strike_is_accounted_for_in_the_predicate(self):
        commander = engine.Permanent(
            card=make_card("Fast Commander", power=6, keywords={"double strike"}),
            entered_turn=1, tapped=False,
        )
        state = make_state(battlefield=[commander], opponents=[40.0])
        state.commander_damage_dealt[("Fast Commander", 0)] = 10.0  # 11 remaining; 6*2=12 covers it, 6 alone would not
        result = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"target": "any"}, state, None,
        )
        self.assertTrue(result.satisfied)


class MultiCommanderLedgerTests(unittest.TestCase):
    """
    v4.28.0 regression, found via ChatGPT external review (Docs/README.md
    v4.28.0 entry): the ledger used to be keyed by opponent index alone, on
    the (incorrect - see the GameState.commander_damage_dealt docstring)
    assumption that this engine only ever has one commander. Two different
    Partner/background co-commanders each attacking for 11 must NOT pool
    into a false 22-damage kill - only a single commander reaching 21 on
    its own is lethal (real rule 903.10a).
    """

    def _with_deterministic_weights(self, fn):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = ALWAYS_UNBLOCKED_WEIGHTS
            fn()
        finally:
            combat_interaction._WEIGHTS = original

    def test_two_commanders_dealing_11_each_does_not_pool_into_a_false_21_kill(self):
        def run():
            commander_a = engine.Permanent(card=make_card("Partner A", power=11), entered_turn=1, tapped=False)
            commander_b = engine.Permanent(card=make_card("Partner B", power=11), entered_turn=1, tapped=False)
            state = make_state(battlefield=[commander_a, commander_b], opponents=[100.0])
            engine.attack_phase(
                state,
                engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            # 22 REAL damage total is fine (life totals track it correctly) -
            # what must NOT happen is a false commander-damage elimination,
            # since neither commander individually reached 21.
            self.assertEqual(state.opponents[0], 78.0)  # 100 - 11 - 11
            self.assertEqual(state.commander_damage_dealt.get(("Partner A", 0), 0.0), 11.0)
            self.assertEqual(state.commander_damage_dealt.get(("Partner B", 0), 0.0), 11.0)
            self.assertIsNone(state.win_turn)
        self._with_deterministic_weights(run)

    def test_one_of_two_commanders_individually_reaching_21_is_still_lethal(self):
        def run():
            commander_a = engine.Permanent(card=make_card("Partner A", power=25), entered_turn=1, tapped=False)
            commander_b = engine.Permanent(card=make_card("Partner B", power=1), entered_turn=1, tapped=False)
            state = make_state(battlefield=[commander_a, commander_b], opponents=[100.0])
            engine.attack_phase(
                state,
                engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(state.opponents[0], 0.0)
            self.assertIsNotNone(state.win_turn)
        self._with_deterministic_weights(run)

    def test_predicate_reads_the_specific_commanders_own_progress_only(self):
        commander_a = engine.Permanent(card=make_card("Partner A", power=3), entered_turn=1, tapped=False)
        state = make_state(battlefield=[commander_a], opponents=[40.0])
        # Only Partner B's (not on this battlefield) progress is stored here -
        # must not leak into Partner A's own lethal-opportunity check.
        state.commander_damage_dealt[("Partner B", 0)] = 20.0
        result = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"target": "any"}, state, None,
        )
        self.assertTrue(result.computable)
        self.assertFalse(result.satisfied)  # Partner A alone (power 3) is nowhere near 21


if __name__ == "__main__":
    unittest.main()
