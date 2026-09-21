"""
Unit tests for v4.18.0: Old Gnawbone's "Whenever a creature you control deals
combat damage to a player, create that many Treasure tokens." trigger.

Found unmodeled during the v4.18.0 model-coverage audit (comparing
card_model_coverage.csv's semantic-tier classification against real,
measured card_impact.csv output across 14 uploaded real-deck result
bundles): Old Gnawbone was cast in 77.5% of its own commander's games
(155/200) but "Treasure created" was 0 in every single run - its entire
game plan was silently a no-op. The trigger fires in attack_phase, in the
same "outcome.damage_dealt > 0" branch already used for the equipment
copy-token trigger (see App/engine.py's comment there: damage_dealt > 0
only ever happens on an unblocked outcome, so no separate blocked-check
is needed).

Run from the project root:
    python -m unittest tests.test_old_gnawbone -v
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
        power=5, toughness=5, commander=False,
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


OLD_GNAWBONE_TEXT = (
    "Flying\n"
    "Whenever a creature you control deals combat damage to a player, "
    "create that many Treasure tokens."
)

ALWAYS_UNBLOCKED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
}

ALWAYS_BLOCKED_AND_TRADED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
}


class OldGnawboneTreasureTriggerTests(unittest.TestCase):
    def _with_weights(self, weights, fn):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = weights
            fn()
        finally:
            combat_interaction._WEIGHTS = original

    def test_old_gnawbone_own_combat_damage_creates_that_many_treasure(self):
        def run():
            gnawbone = engine.Permanent(
                card=make_card("Old Gnawbone", power=5, toughness=4, oracle_text=OLD_GNAWBONE_TEXT, commander=True),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[gnawbone], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.opponents[0], 35.0)  # 40 - 5 damage
            self.assertEqual(state.treasure, 5)  # that many == damage dealt
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_other_attackers_combat_damage_also_creates_treasure_while_gnawbone_is_out(self):
        def run():
            gnawbone = engine.Permanent(
                card=make_card("Old Gnawbone", power=5, toughness=4, oracle_text=OLD_GNAWBONE_TEXT, commander=True),
                entered_turn=1, tapped=False,
            )
            sidekick = engine.Permanent(
                card=make_card("Sidekick", power=3, toughness=3),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[gnawbone, sidekick], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.opponents[0], 32.0)  # 40 - 5 - 3
            self.assertEqual(state.treasure, 8)  # 5 (Gnawbone) + 3 (Sidekick)
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_no_treasure_without_old_gnawbone_in_play(self):
        def run():
            sidekick = engine.Permanent(
                card=make_card("Sidekick", power=3, toughness=3),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[sidekick], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.opponents[0], 37.0)
            self.assertEqual(state.treasure, 0)
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_blocked_and_traded_attacker_deals_no_player_damage_so_no_treasure(self):
        def run():
            gnawbone = engine.Permanent(
                card=make_card("Old Gnawbone", power=5, toughness=4, oracle_text=OLD_GNAWBONE_TEXT, commander=True),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[gnawbone], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.opponents[0], 40.0)  # fully blocked, no player damage
            self.assertEqual(state.treasure, 0)
        self._with_weights(ALWAYS_BLOCKED_AND_TRADED_WEIGHTS, run)

    def test_double_strike_gnawbone_treasure_matches_the_doubled_damage(self):
        def run():
            gnawbone = engine.Permanent(
                card=make_card(
                    "Old Gnawbone", power=5, toughness=4,
                    oracle_text=OLD_GNAWBONE_TEXT, commander=True,
                    keywords={"double strike"},
                ),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[gnawbone], opponents=[40.0])
            engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"), random.Random(1))
            self.assertEqual(state.opponents[0], 30.0)  # 40 - (5 * 2)
            self.assertEqual(state.treasure, 10)  # that many == the doubled damage
        self._with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)


if __name__ == "__main__":
    unittest.main()
