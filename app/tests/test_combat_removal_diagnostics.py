"""
Regression test for the WP6/WP7 combat & removal diagnostics added to
card_impact.csv (previously tracked internally via record_impact but never
exported anywhere, making outcome shifts impossible to attribute with evidence).

Run from the project root:
    python -m unittest tests.test_combat_removal_diagnostics -v
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
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


class CombatRemovalDiagnosticColumnsTests(unittest.TestCase):
    def test_new_columns_present_and_correct(self):
        deck = [make_card("Doctor Strange, Surgeon"), make_card("Idle Card")]
        aggregate = {
            "Doctor Strange, Surgeon": Counter({
                "seen": 10, "cast": 8,
                "died_in_combat": 3, "combat_blocked": 5,
                "removed_by_opponent": 2, "wiped_by_opponent": 1,
                "commander_damage_lethal": 0,
            }),
            "Idle Card": Counter({"seen": 10, "cast": 1}),
        }
        strategy = engine.ScenarioStrategy()
        rows = engine.impact_rows_from_aggregate(deck, aggregate, runs=10, strategy=strategy)
        by_name = {r["Name"]: r for r in rows}

        doc = by_name["Doctor Strange, Surgeon"]
        self.assertEqual(doc["Died in combat"], 3)
        self.assertEqual(doc["Blocked in combat"], 5)
        self.assertEqual(doc["Removed by opponent"], 2)
        self.assertEqual(doc["Wiped by opponent"], 1)
        self.assertEqual(doc["Commander damage lethal hits"], 0)

        idle = by_name["Idle Card"]
        self.assertEqual(idle["Died in combat"], 0)
        self.assertEqual(idle["Removed by opponent"], 0)

    def test_attack_phase_death_is_visible_end_to_end_in_the_exported_columns(self):
        """A creature that actually dies in attack_phase should show up as
        'Died in combat' >= 1 once its impact is run through the same aggregation
        path the real pipeline uses."""
        from App.combat_model import interaction as combat_interaction
        import random

        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
                "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
                "posture": {"balanced_min_other_attackers": 2},
            }
            attacker = engine.Permanent(card=make_card("Doomed Attacker"), entered_turn=1, tapped=False)
            state = engine.GameState(
                library=[], hand=[], command_zone=[], graveyard=[], exile=[],
                battlefield=[attacker], creature_tokens=[], food=0, treasure=0,
                clues=0, life=40, opponents=[40.0], turn=5,
            )
            strategy = engine.ScenarioStrategy(opponent_profile="control")
            engine.attack_phase(state, strategy, random.Random(3))

            rows = engine.impact_rows_from_aggregate(
                [make_card("Doomed Attacker")], state.impact, runs=1, strategy=strategy,
            )
            row = next(r for r in rows if r["Name"] == "Doomed Attacker")
            self.assertGreaterEqual(row["Died in combat"], 1)
        finally:
            combat_interaction._WEIGHTS = original


if __name__ == "__main__":
    unittest.main()
