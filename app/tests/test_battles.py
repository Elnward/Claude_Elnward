"""
Unit tests for v4.20.0: Battle defense counters + our-own-creatures-attack-it
combat modeling + completion.

Found during the v4.18.0 model-coverage audit: no Battle card appeared in
any of the 14 audited real decks, and the engine had zero Battle support at
all. Genuinely uncalibrated territory (see the "v4.20.0: Battles" module
comment right above complete_battle in App/engine.py for the exact scope
boundaries this engine commits to): this is a pure goldfish simulator with
no opposing creatures/permanents modeled anywhere, so a Battle we cast is
attacked by OUR OWN creatures (real rule: the caster is never a Battle's
"protector"), unconditionally connecting - the same "no blockers assumed"
simplification the rest of the engine already uses for player-facing
combat damage.

Fixture Battle cards below are synthetic (hand-constructed), not transcribed
from a real card's Oracle text - consistent with this project's standing
convention of preferring a clearly-synthetic fixture over risking a
misquoted real card when live network access isn't available to verify one.

Run from the project root:
    python -m unittest tests.test_battles -v
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
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    # turn=5 (not 1) so that creatures/battles entered_turn=1 aren't filtered
    # out as summoning-sick - matches tests/test_old_gnawbone.py's convention.
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def make_battle(name="Test Siege", defense=5, oracle_text="", **overrides):
    card = make_card(
        name, type_line="Battle — Siege", oracle_text=oracle_text,
        defense=defense, power=None, toughness=None, **overrides,
    )
    return card, engine.Permanent(card=card, entered_turn=1, tapped=False)


def make_creature(name, power, entered_turn=1, **overrides):
    card = make_card(name, power=power, toughness=power, **overrides)
    return engine.Permanent(card=card, entered_turn=entered_turn, tapped=False)


# Deterministic combat weights (same pattern as tests/test_old_gnawbone.py):
# no blocks, no evasion penalties, no attacker-count decay - isolates the
# Battle-diversion logic from the separate combat-interaction probability
# model.
ALWAYS_UNBLOCKED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
}

# Joined with the same "\n//\n" separator card_from_scryfall uses for any
# double-faced card's combined oracle text (see complete_battle's own
# module comment) - front face first, back face (the completion reward)
# after the separator.
BEAR_REWARD_TEXT = (
    "When Test Siege enters the battlefield, put a +1/+1 counter on target creature you control."
    "\n//\n"
    "Create a 3/3 green Bear creature token."
)
UNPARSEABLE_REWARD_TEXT = (
    "Front face text.\n//\nExile target player's graveyard. If you do, that player mills a card."
)


class BattlesTests(unittest.TestCase):
    def _with_weights(self, weights, fn):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = weights
            fn()
        finally:
            combat_interaction._WEIGHTS = original

    def test_single_creature_fully_depletes_defense_and_completes_the_battle(self):
        def run():
            battle_card, battle = make_battle(defense=5)
            attacker = make_creature("Attacker", power=5)
            state = make_state(battlefield=[battle, attacker])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(state.opponents[0], 40.0)  # diverted to the battle, not the opponent
            self.assertNotIn(battle, state.battlefield)  # completed -> left the battlefield
            self.assertIn(battle_card, state.graveyard)
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_partial_damage_leaves_the_battle_alive_with_reduced_defense(self):
        def run():
            battle_card, battle = make_battle(defense=10)
            attacker = make_creature("Attacker", power=3)
            state = make_state(battlefield=[battle, attacker])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(battle.defense, 7.0)  # 10 - 3
            self.assertIn(battle, state.battlefield)  # not completed
            self.assertEqual(state.opponents[0], 40.0)  # the one available attacker was diverted
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_smallest_power_creature_is_diverted_first(self):
        def run():
            battle_card, battle = make_battle(defense=3)
            small = make_creature("Small", power=2)
            big = make_creature("Big", power=10)
            state = make_state(battlefield=[battle, small, big])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            # Small (2) alone leaves 1 defense remaining, so Big is also
            # diverted (whole creatures only - a creature can't attack for
            # only part of its power) rather than left free to hit the
            # opponent; total dealt is capped at the battle's own defense.
            self.assertEqual(battle.defense, 0.0)
            self.assertNotIn(battle, state.battlefield)
            self.assertEqual(state.opponents[0], 40.0)  # both diverted, neither hit the opponent
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_extra_creatures_beyond_what_the_battle_needs_still_attack_the_opponent(self):
        def run():
            battle_card, battle = make_battle(defense=2)
            needed = make_creature("Needed", power=2)
            spare = make_creature("Spare", power=4)
            state = make_state(battlefield=[battle, needed, spare])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(battle.defense, 0.0)
            self.assertNotIn(battle, state.battlefield)
            self.assertEqual(state.opponents[0], 36.0)  # 40 - 4 (Spare, never diverted)
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_commander_creature_is_never_diverted_to_attack_a_battle(self):
        def run():
            battle_card, battle = make_battle(defense=5)
            commander = make_creature("Commander Bear", power=5, commander=True)
            state = make_state(battlefield=[battle, commander])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(battle.defense, 5.0)  # untouched
            self.assertIn(battle, state.battlefield)
            self.assertEqual(state.opponents[0], 35.0)  # commander attacked the opponent instead
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_no_eligible_attacker_leaves_the_battle_untouched_and_does_not_crash(self):
        def run():
            battle_card, battle = make_battle(defense=5)
            state = make_state(battlefield=[battle])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(battle.defense, 5.0)
            self.assertIn(battle, state.battlefield)
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_zero_defense_battle_is_ignored_by_the_diversion_loop(self):
        def run():
            battle_card, battle = make_battle(defense=0)
            attacker = make_creature("Attacker", power=5)
            state = make_state(battlefield=[battle, attacker])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(state.opponents[0], 35.0)  # attacker went face, battle already spent
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)


class CompleteBattleTests(unittest.TestCase):
    """Direct tests of complete_battle() itself, independent of the combat
    probability model."""

    def test_completion_with_executable_back_face_applies_the_one_shot_reward(self):
        card, battle = make_battle(defense=0, oracle_text=BEAR_REWARD_TEXT)
        state = make_state(battlefield=[battle])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.complete_battle(state, strategy, battle)
        self.assertNotIn(battle, state.battlefield)
        self.assertIn(card, state.graveyard)
        self.assertEqual(len(state.creature_tokens), 1)
        group = state.creature_tokens[0]
        self.assertEqual(group.power, 3.0)
        self.assertEqual(group.toughness, 3.0)

    def test_completion_with_unparseable_back_face_still_completes_without_crashing(self):
        card, battle = make_battle(defense=0, oracle_text=UNPARSEABLE_REWARD_TEXT)
        state = make_state(battlefield=[battle])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.complete_battle(state, strategy, battle)
        self.assertNotIn(battle, state.battlefield)
        self.assertIn(card, state.graveyard)
        self.assertEqual(state.creature_tokens, [])

    def test_non_transforming_battle_with_no_back_face_completes_with_no_reward(self):
        card, battle = make_battle(defense=0, oracle_text="A one-sided Battle with no // back face.")
        state = make_state(battlefield=[battle])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.complete_battle(state, strategy, battle)
        self.assertNotIn(battle, state.battlefield)
        self.assertIn(card, state.graveyard)
        self.assertEqual(state.creature_tokens, [])

    def test_battle_defense_seeded_from_card_on_permanent_construction(self):
        card, battle = make_battle(defense=5)
        self.assertEqual(battle.defense, 5.0)

    def test_is_battle_and_is_permanent(self):
        card, _ = make_battle(defense=5)
        self.assertTrue(card.is_battle)
        self.assertTrue(card.is_permanent)
        self.assertFalse(card.is_planeswalker)


if __name__ == "__main__":
    unittest.main()
