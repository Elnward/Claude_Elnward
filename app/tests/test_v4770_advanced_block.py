"""
v4.77.0 WP-B: connect the advanced multi-seat opponent model's own board
state (App/opponent_model/state_equation.py::query_combat_state) to the
block rate our OWN attacks face (App/combat_model/interaction.py::
resolve_combat_interaction), replacing the previous silent fallback to
strategy.opponent_profile (often "random"/"?", not a registered
combat_interaction profile -> 0% block rate, i.e. no blocking at all in
advanced mode).

Run from the project root:
    python -m unittest tests.test_v4770_advanced_block -v
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402
from App.combat_model import interaction as combat_interaction  # noqa: E402
from App.opponent_model.state_equation import OpponentProfile, OpponentState  # noqa: E402


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def seated_state(seat_specs, **overrides):
    """seat_specs: list of (strategy, board_presence)."""
    st = make_state(**overrides)
    table = []
    for strat, board_presence in seat_specs:
        profile = OpponentProfile(strategy=strat, colors=set(), bracket=3)
        opp_state = OpponentState()
        opp_state.board_presence = board_presence
        table.append((profile, opp_state))
    st._advanced_opponent_table = table
    return st


class AdvancedBlockContextTests(unittest.TestCase):
    def test_non_advanced_strategy_is_a_pure_no_op(self):
        strategy = engine.ScenarioStrategy(advanced_opponent_model=False)
        self.assertEqual(engine._v477b_advanced_block_context(make_state(), strategy), (None, 1.0))

    def test_advanced_without_seats_is_a_no_op(self):
        strategy = engine.ScenarioStrategy(advanced_opponent_model=True, advanced_opponent_seats=[])
        self.assertEqual(engine._v477b_advanced_block_context(make_state(), strategy), (None, 1.0))

    def test_zero_board_presence_gives_neutral_multiplier(self):
        strategy = engine.ScenarioStrategy(advanced_opponent_model=True,
                                           advanced_opponent_seats=[{"strategy": "aggro", "colors": ["R"]}])
        st = seated_state([("aggro", 0.0)])
        rep, mult = engine._v477b_advanced_block_context(st, strategy)
        self.assertEqual(rep, "aggro")
        self.assertAlmostEqual(mult, 1.0)

    def test_high_board_presence_raises_the_multiplier(self):
        strategy = engine.ScenarioStrategy(advanced_opponent_model=True,
                                           advanced_opponent_seats=[{"strategy": "aggro", "colors": ["R"]}])
        st = seated_state([("aggro", 10.0)])   # well past the query_combat_state cap
        rep, mult = engine._v477b_advanced_block_context(st, strategy)
        self.assertEqual(rep, "aggro")
        self.assertAlmostEqual(mult, 2.0)   # capped: 1.0 + min(1.0, 10/5)

    def test_representative_is_the_most_common_seat_strategy(self):
        strategy = engine.ScenarioStrategy(
            advanced_opponent_model=True,
            advanced_opponent_seats=[{"strategy": "aggro", "colors": ["R"]}] * 2 + [{"strategy": "control", "colors": ["U"]}],
        )
        st = seated_state([("aggro", 0.0), ("aggro", 0.0), ("control", 0.0)])
        rep, _ = engine._v477b_advanced_block_context(st, strategy)
        self.assertEqual(rep, "aggro")

    def test_multiplier_is_the_mean_across_seats(self):
        strategy = engine.ScenarioStrategy(
            advanced_opponent_model=True,
            advanced_opponent_seats=[{"strategy": "aggro", "colors": ["R"]}] * 2,
        )
        st = seated_state([("aggro", 0.0), ("aggro", 10.0)])   # multipliers 1.0 and 2.0
        _, mult = engine._v477b_advanced_block_context(st, strategy)
        self.assertAlmostEqual(mult, 1.5)


class ResolveCombatInteractionWrapperTests(unittest.TestCase):
    def test_no_context_falls_through_unmodified(self):
        calls = []
        saved = engine._V477B_resolve_combat_interaction_old
        try:
            engine._V477B_resolve_combat_interaction_old = lambda *a, **kw: calls.append((a, kw)) or []
            engine._v477b_resolve_combat_interaction("goldfish", 5, [], random.Random(1), state=None)
            self.assertEqual(calls[0][0][0], "goldfish")
        finally:
            engine._V477B_resolve_combat_interaction_old = saved

    def test_context_swaps_profile_and_restores_weights(self):
        original_aggro = dict(combat_interaction._WEIGHTS["profiles"]["aggro"])
        calls = []
        saved = engine._V477B_resolve_combat_interaction_old

        def spy(profile_name, turn, attackers, rng, *, state=None):
            # Record the profile passed AND the block_rate_base in effect
            # during the call (must be the scaled value, restored after).
            calls.append((profile_name, dict(combat_interaction._WEIGHTS["profiles"]["aggro"])))
            return []

        try:
            engine._V477B_resolve_combat_interaction_old = spy
            fake_state = make_state()
            fake_state._v477b_block_context = ("aggro", 2.0)
            engine._v477b_resolve_combat_interaction("random", 5, [], random.Random(1), state=fake_state)
            self.assertEqual(calls[0][0], "aggro")
            self.assertAlmostEqual(
                calls[0][1]["block_rate_base"],
                min(1.0, original_aggro["block_rate_base"] * 2.0),
            )
            # restored after the call
            self.assertEqual(combat_interaction._WEIGHTS["profiles"]["aggro"], original_aggro)
        finally:
            engine._V477B_resolve_combat_interaction_old = saved
            combat_interaction._WEIGHTS["profiles"]["aggro"] = original_aggro

    def test_neutral_multiplier_still_swaps_profile(self):
        # mult == 1.0 but a representative profile IS known (e.g. all seats
        # at 0 board presence early game) -- "random"/"?" must still be
        # replaced by a real profiles key, not silently left as-is.
        calls = []
        saved = engine._V477B_resolve_combat_interaction_old
        try:
            engine._V477B_resolve_combat_interaction_old = lambda *a, **kw: calls.append(a[0]) or []
            fake_state = make_state()
            fake_state._v477b_block_context = ("aggro", 1.0)
            engine._v477b_resolve_combat_interaction("random", 5, [], random.Random(1), state=fake_state)
            self.assertEqual(calls[0], "aggro")
        finally:
            engine._V477B_resolve_combat_interaction_old = saved

    def test_weights_are_restored_even_on_exception(self):
        original_aggro = dict(combat_interaction._WEIGHTS["profiles"]["aggro"])
        saved = engine._V477B_resolve_combat_interaction_old

        def boom(*a, **kw):
            raise RuntimeError("boom")

        try:
            engine._V477B_resolve_combat_interaction_old = boom
            fake_state = make_state()
            fake_state._v477b_block_context = ("aggro", 2.0)
            with self.assertRaises(RuntimeError):
                engine._v477b_resolve_combat_interaction("random", 5, [], random.Random(1), state=fake_state)
            self.assertEqual(combat_interaction._WEIGHTS["profiles"]["aggro"], original_aggro)
        finally:
            engine._V477B_resolve_combat_interaction_old = saved
            combat_interaction._WEIGHTS["profiles"]["aggro"] = original_aggro


class AttackPhaseWiringTests(unittest.TestCase):
    """Confirms the attack_phase wrapper sets/clears the context around the
    wrapped call, and that the ubiquitous non-advanced case is a fast no-op
    (skips straight through without touching state at all)."""

    def test_non_advanced_run_never_sets_context(self):
        import dataclasses

        def make_card(name="Beater", **kw):
            field_names = {f.name for f in dataclasses.fields(engine.Card)}
            defaults = dict(name=name, mana_cost="", mana_value=0, type_line="Creature",
                            oracle_text="", color_identity=set(), produced_mana=set(),
                            keywords=set(), roles=set(), power=3, toughness=3, commander=False)
            defaults.update(kw)
            return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})

        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
                "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
                "posture": {"balanced_min_other_attackers": 2},
                "playstyle": {"attacker_selection_max_power": 3.0},
            }
            beater = engine.Permanent(card=make_card(), entered_turn=1)
            state = make_state(battlefield=[beater])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", advanced_opponent_model=False)
            engine.attack_phase(state, strategy, random.Random(1))
            self.assertIsNone(getattr(state, "_v477b_block_context", None))
        finally:
            combat_interaction._WEIGHTS = original


if __name__ == "__main__":
    unittest.main()
