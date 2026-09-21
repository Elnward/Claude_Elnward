"""
Unit tests for the v4.63.0 "advanced multi-opponent model" - the first REAL
turn-loop integration of App/opponent_model/state_equation.py (as opposed to
the v4.44.0 additive, purely synthetic side cross-check tested in
tests/test_opponent_model_cross_check.py).

See App/engine.py's own comment block directly above
_apply_advanced_multi_opponent_phase for the full design rationale:
individual per-seat OpponentProfile/OpponentState pairs (instead of one flat
OPPONENT_PROFILES aggregate), restricted in this first pass to mono-/two-
color opponent identities and Bracket 3, plus a new multiplayer targeting-
dilution factor (1/(n-1), n = seats + the tested player) for single-target
actions (spot removal, combat/pressure damage) - board wipes are
deliberately NOT diluted.

Run from the project root:
    python -m unittest tests.test_advanced_opponent_model -v
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


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class ValidationTests(unittest.TestCase):
    def test_empty_seats_is_rejected(self):
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats([])

    def test_goldfish_is_not_a_valid_seat_strategy(self):
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(
                [{"strategy": "goldfish", "colors": ["U"]}]
            )

    def test_unknown_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(
                [{"strategy": "cEDH-stax", "colors": ["U"]}]
            )

    def test_unknown_color_letter_is_rejected(self):
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(
                [{"strategy": "midrange", "colors": ["X"]}]
            )

    def test_three_color_seat_is_rejected_in_this_first_pass(self):
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(
                [{"strategy": "control", "colors": ["U", "B", "W"]}]
            )

    def test_colorless_seat_is_rejected_in_this_first_pass(self):
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(
                [{"strategy": "midrange", "colors": []}]
            )

    def test_non_bracket_3_is_rejected(self):
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(
                [{"strategy": "control", "colors": ["U"], "bracket": 4}]
            )

    def test_mono_and_two_color_bracket_3_seats_are_accepted(self):
        engine._validate_advanced_opponent_seats(
            [
                {"strategy": "aggro", "colors": ["R"]},
                {"strategy": "control", "colors": ["U", "B"]},
                {"strategy": "midrange", "colors": ["U"], "bracket": 3},
            ]
        )


class TableConstructionTests(unittest.TestCase):
    def test_builds_one_independent_profile_state_pair_per_seat(self):
        seats = [
            {"strategy": "aggro", "colors": ["R"]},
            {"strategy": "control", "colors": ["U", "B"]},
        ]
        table = engine._build_advanced_opponent_table(seats)
        self.assertEqual(len(table), 2)
        (profile_a, state_a), (profile_b, state_b) = table
        self.assertEqual(profile_a.strategy, "aggro")
        self.assertEqual(profile_a.colors, {"R"})
        self.assertEqual(profile_a.bracket, 3)
        self.assertEqual(profile_b.strategy, "control")
        self.assertEqual(profile_b.colors, {"U", "B"})
        # Each seat gets its OWN OpponentState instance - mutating one must
        # never affect the other (the whole point of "individual profile per
        # opponent" instead of one shared aggregate).
        self.assertIsNot(state_a, state_b)
        state_a.life = 1.0
        self.assertEqual(state_b.life, 40.0)

    def test_table_is_cached_on_state_across_multiple_calls(self):
        state = make_state()
        strategy = engine.Strategy(
            advanced_opponent_model=True,
            advanced_opponent_seats=[{"strategy": "midrange", "colors": ["G"]}],
        )
        first = engine._get_advanced_opponent_table(state, strategy)
        second = engine._get_advanced_opponent_table(state, strategy)
        self.assertIs(first, second)


class TargetingDilutionTests(unittest.TestCase):
    def test_one_on_one_table_never_dilutes(self):
        # n=2 (tested player + 1 opponent) -> the opponent has exactly one
        # other player to target, so every single-target action lands.
        self.assertEqual(engine._advanced_opponent_targeting_dilution(2), 1.0)

    def test_four_player_pod_dilutes_to_one_third(self):
        # n=4 (tested player + 3 opponents) -> 1/(4-1) = 1/3, exactly the
        # user's own worked example.
        self.assertAlmostEqual(engine._advanced_opponent_targeting_dilution(4), 1.0 / 3.0)

    def test_dilution_shrinks_as_the_table_grows(self):
        d3 = engine._advanced_opponent_targeting_dilution(3)
        d5 = engine._advanced_opponent_targeting_dilution(5)
        self.assertGreater(d3, d5)


class AdvancedPhaseIntegrationTests(unittest.TestCase):
    def test_default_strategy_never_touches_the_advanced_path(self):
        # advanced_opponent_model defaults to False - apply_abstract_opponent_phase
        # must remain byte-for-byte the old behavior unless explicitly opted in.
        state = make_state(turn=6)
        strategy = engine.Strategy(opponent_profile="control")
        state_life_before = state.life
        engine.apply_abstract_opponent_phase(state, strategy, random.Random(1))
        self.assertFalse(hasattr(state, "_advanced_opponent_table") and state._advanced_opponent_table)
        # (life may or may not have changed via the OLD path - this only
        # asserts the NEW per-seat table was never constructed)

    def test_advanced_mode_builds_and_reuses_a_seat_table(self):
        state = make_state(turn=6)
        strategy = engine.Strategy(
            advanced_opponent_model=True,
            advanced_opponent_seats=[
                {"strategy": "aggro", "colors": ["R"]},
                {"strategy": "control", "colors": ["U", "B"]},
            ],
        )
        rng = random.Random(42)
        for _ in range(5):
            engine.apply_abstract_opponent_phase(state, strategy, rng)
        table = state._advanced_opponent_table
        self.assertEqual(len(table), 2)
        for _profile, opp_state in table:
            self.assertEqual(opp_state.turn, 5)  # advanced once per call

    def test_life_total_can_drop_from_board_presence_pressure_over_many_turns(self):
        state = make_state(turn=1, life=40.0)
        strategy = engine.Strategy(
            advanced_opponent_model=True,
            advanced_opponent_seats=[{"strategy": "aggro", "colors": ["R"]}],
        )
        rng = random.Random(7)
        for turn in range(1, 15):
            state.turn = turn
            engine.apply_abstract_opponent_phase(state, strategy, rng)
        self.assertLess(state.life, 40.0)

    def test_reproducible_given_the_same_seed(self):
        seats = [
            {"strategy": "midrange", "colors": ["G"]},
            {"strategy": "control", "colors": ["W", "U"]},
        ]

        def run(seed):
            state = make_state(turn=1, life=40.0)
            strategy = engine.Strategy(
                advanced_opponent_model=True, advanced_opponent_seats=seats
            )
            rng = random.Random(seed)
            for turn in range(1, 10):
                state.turn = turn
                engine.apply_abstract_opponent_phase(state, strategy, rng)
            return state.life, state.damage_taken

        self.assertEqual(run(99), run(99))

    def test_a_single_seats_own_hit_rate_shrinks_as_more_seats_join_the_table(self):
        # Isolates ONE specific seat's own targeting-dilution behavior by
        # reading its own log entries, independent of how many OTHER seats
        # are also acting - adding more seats necessarily adds more
        # aggregate pressure (each seat is a full independent opponent), so
        # comparing TOTAL damage across table sizes (as an earlier version of
        # this test did) is confounded and not a valid check of dilution.
        # This is the user's own worked example directly: 1/(n-1) per seat.
        def aggro_r_hit_rate(extra_seats, trials=150):
            hits = 0
            seats = [{"strategy": "aggro", "colors": ["R"]}] + extra_seats
            for seed in range(trials):
                state = make_state(turn=1, life=10_000.0)
                strategy = engine.Strategy(
                    advanced_opponent_model=True, advanced_opponent_seats=seats
                )
                rng = random.Random(seed)
                engine.apply_abstract_opponent_phase(state, strategy, rng)
                if any(
                    "aggro/R" in line and "combat/pressure damage" in line
                    for line in state.event_log
                ):
                    hits += 1
            return hits / trials

        # n=2 (tested player + this one seat) -> dilution=1.0 -> deterministic hit.
        solo = aggro_r_hit_rate([])
        # n=4 (tested player + this seat + 2 padding seats) -> dilution=1/3.
        crowded = aggro_r_hit_rate(
            [
                {"strategy": "control", "colors": ["U", "B"]},
                {"strategy": "midrange", "colors": ["G"]},
            ]
        )
        self.assertEqual(solo, 1.0)
        self.assertLess(crowded, solo)

    def test_advanced_opponent_model_json_round_trips_through_load_strategy(self):
        import json
        import tempfile

        data = {
            "advanced_opponent_model": True,
            "advanced_opponent_seats": [{"strategy": "control", "colors": ["U", "B"]}],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(data, fh)
            path = Path(fh.name)
        try:
            strategy = engine.load_strategy(path, commander=None)
            self.assertTrue(strategy.advanced_opponent_model)
            self.assertEqual(
                strategy.advanced_opponent_seats,
                [{"strategy": "control", "colors": ["U", "B"]}],
            )
        finally:
            path.unlink(missing_ok=True)


class ApplyAdvancedOpponentModelOverrideTests(unittest.TestCase):
    # v4.64.0: mirrors tests one would write for apply_voltron_target_override
    # - the same additive-override pattern for the new GUI "Gegnerprofil" dialog.
    def test_none_leaves_existing_strategy_fields_untouched(self):
        strategy = engine.Strategy(
            advanced_opponent_model=True,
            advanced_opponent_seats=[{"strategy": "aggro", "colors": ["R"]}],
        )
        engine.apply_advanced_opponent_model_override(strategy, None, None)
        self.assertTrue(strategy.advanced_opponent_model)
        self.assertEqual(strategy.advanced_opponent_seats, [{"strategy": "aggro", "colors": ["R"]}])

    def test_explicit_values_override(self):
        strategy = engine.Strategy(advanced_opponent_model=False, advanced_opponent_seats=[])
        seats = [{"strategy": "control", "colors": ["U", "B"]}]
        engine.apply_advanced_opponent_model_override(strategy, True, seats)
        self.assertTrue(strategy.advanced_opponent_model)
        self.assertEqual(strategy.advanced_opponent_seats, seats)
        # Must copy, not alias, the seats list/dicts.
        self.assertIsNot(strategy.advanced_opponent_seats, seats)


class RandomSeatMarkerResolutionTests(unittest.TestCase):
    # v4.64.0: the GUI's "?" (random) pip/option for color and/or strategy,
    # resolved once per run - see App/gui.py's "Gegnerprofil" dialog and the
    # module comment above _resolve_advanced_opponent_seats_for_run.
    def test_seat_without_any_marker_is_returned_unchanged(self):
        seats = [{"strategy": "aggro", "colors": ["R"]}]
        resolved = engine._resolve_advanced_opponent_seats_for_run(seats, seed=1, run_id=1)
        self.assertEqual(resolved, seats)

    def test_random_strategy_marker_resolves_to_a_real_strategy(self):
        seats = [{"strategy": "?", "colors": ["U"]}]
        resolved = engine._resolve_advanced_opponent_seats_for_run(seats, seed=1, run_id=1)
        self.assertIn(resolved[0]["strategy"], engine.RANDOM_OPPONENT_CHOICES)
        self.assertEqual(resolved[0]["colors"], ["U"])

    def test_random_color_marker_resolves_to_a_valid_mono_or_two_color_identity(self):
        seats = [{"strategy": "midrange", "colors": ["?"]}]
        resolved = engine._resolve_advanced_opponent_seats_for_run(seats, seed=1, run_id=1)
        choices_as_sets = [frozenset(c) for c in engine.RANDOM_ADVANCED_OPPONENT_COLOR_CHOICES]
        self.assertIn(frozenset(resolved[0]["colors"]), choices_as_sets)
        self.assertEqual(resolved[0]["strategy"], "midrange")

    def test_both_markers_together_are_independently_resolved(self):
        seats = [{"strategy": "random", "colors": ["random"]}]
        resolved = engine._resolve_advanced_opponent_seats_for_run(seats, seed=5, run_id=2)
        choices_as_sets = [frozenset(c) for c in engine.RANDOM_ADVANCED_OPPONENT_COLOR_CHOICES]
        self.assertIn(resolved[0]["strategy"], engine.RANDOM_OPPONENT_CHOICES)
        self.assertIn(frozenset(resolved[0]["colors"]), choices_as_sets)

    def test_resolution_is_reproducible_given_the_same_seed_and_run_id(self):
        seats = [{"strategy": "?", "colors": ["?"]}, {"strategy": "control", "colors": ["W", "B"]}]
        first = engine._resolve_advanced_opponent_seats_for_run(seats, seed=42, run_id=7)
        second = engine._resolve_advanced_opponent_seats_for_run(seats, seed=42, run_id=7)
        self.assertEqual(first, second)

    def test_different_run_ids_can_resolve_differently(self):
        seats = [{"strategy": "?", "colors": ["?"]}]
        results = {
            tuple(engine._resolve_advanced_opponent_seats_for_run(seats, seed=1, run_id=r)[0]["colors"])
            + (engine._resolve_advanced_opponent_seats_for_run(seats, seed=1, run_id=r)[0]["strategy"],)
            for r in range(1, 30)
        }
        # Across 29 different run_ids, at least SOME variety must appear -
        # a constant resolution regardless of run_id would defeat the whole
        # point of "random per run".
        self.assertGreater(len(results), 1)

    def test_end_to_end_through_apply_abstract_opponent_phase_via_simulate_game_v440(self):
        # Full integration: a "?" seat must still build a valid, real seat by
        # the time the actual turn loop runs, going through the real
        # simulate_game_v440 wrapper chain (not calling the resolver directly).
        import dataclasses

        def make_card(name="Commander Test", **overrides):
            field_names = {f.name for f in dataclasses.fields(engine.Card)}
            defaults = dict(
                name=name, mana_cost="{1}{G}", mana_value=2, type_line="Legendary Creature",
                oracle_text="", color_identity={"G"}, produced_mana=set(), keywords=set(),
                roles=set(), power=2, toughness=2, commander=True,
            )
            defaults.update(overrides)
            return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})

        deck = [make_card()] + [make_card(f"Forest {i}", type_line="Basic Land — Forest", commander=False, mana_cost="", color_identity=set()) for i in range(38)]
        strategy = engine.ScenarioStrategy(
            tutor_priority=[],
            commander_colors={"G"},
            advanced_opponent_model=True,
            advanced_opponent_seats=[{"strategy": "?", "colors": ["?"]}],
        )
        cfg = engine.SimConfig(runs=1, turns=3, seed=3)
        policy = engine.MulliganPolicy()
        rng = random.Random(3)
        # Must not raise - the "?" markers have to be resolved into a
        # concrete, _validate_advanced_opponent_seats-legal seat before
        # apply_abstract_opponent_phase (and therefore _build_advanced_
        # opponent_table's hard validation) ever sees it.
        engine.simulate_game_v440(deck, strategy, cfg, policy, rng, run_id=1)


if __name__ == "__main__":
    unittest.main()
