"""
Unit tests for v4.87.4: generic per-turn focus metrics for the Analysis page.

Before v4.87.4 the Analysis page only knew one per-turn series (average life)
and hard-coded life thresholds 50/60/80/100/111 - the 111 is Bilbo's win
condition and meaningless for every other deck. The engine now records a set
of deck-independent metrics per turn (life, creatures, tokens, power, hand,
counters, graveyard, mill, opponent life, mana ...) and summarizes each one as
a per-turn average with a 25-75 % band plus a per-game peak histogram, from
which the web UI derives any "reached at least once" benchmark itself.

Run from the project root:
    python -m unittest tests.test_v4874_focus_metrics -v
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
from webui_transform import to_frontend_run  # noqa: E402


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
        life=40, opponents=[40.0, 40.0, 40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class TestFocusMetricSnapshot(unittest.TestCase):
    def test_board_hand_and_opponent_values(self):
        bear = make_card("Bear", power=2, toughness=2)
        giant = make_card("Giant", power=5, toughness=5)
        state = make_state(
            battlefield=[engine.Permanent(card=bear, entered_turn=1),
                         engine.Permanent(card=giant, entered_turn=1, counters=2)],
            creature_tokens=[engine.TokenGroup(name="Soldier", count=3, power=1.0, toughness=1.0)],
            hand=[make_card("A"), make_card("B")],
            graveyard=[make_card("C")],
            opponents=[30.0, 12.0, 40.0],
            life=37,
        )
        v = engine._focus_metric_values(state, 4.0)
        self.assertEqual(v["creatures"], 5.0)          # 2 nontoken + 3 tokens
        self.assertEqual(v["creature_tokens"], 3.0)
        self.assertEqual(v["max_power"], 7.0)          # Giant 5 + two +1/+1 counters
        self.assertEqual(v["total_power"], 2.0 + 7.0 + 3.0)
        self.assertEqual(v["plus1_counters"], 2.0)
        self.assertEqual(v["hand"], 2.0)
        self.assertEqual(v["graveyard"], 1.0)
        self.assertEqual(v["opp_life_min"], 12.0)
        self.assertEqual(v["opp_damage"], 10.0 + 28.0 + 0.0)
        self.assertEqual(v["life"], 37.0)
        self.assertEqual(v["mana"], 4.0)

    def test_opponent_mill_comes_from_recorded_mill_impact(self):
        state = make_state()
        engine.record_impact(state, "Mind Grind", "mill", 7)
        engine.record_impact(state, "Other", "mill", 3)
        self.assertEqual(engine._focus_metric_values(state, 0.0)["opp_milled"], 10.0)

    def test_every_declared_metric_is_produced(self):
        v = engine._focus_metric_values(make_state(), 0.0)
        self.assertEqual(set(v), {m[0] for m in engine.FOCUS_METRICS})


def _rows(values_by_turn):
    """values_by_turn: list of dicts {metric: value} -> fake turn rows."""
    rows = []
    for i, vals in enumerate(values_by_turn, start=1):
        row = {"turn": i}
        for k in engine._FOCUS_KEYS:
            row[f"fm_{k}"] = vals.get(k, 0.0)
        rows.append(row)
    return rows


class TestFocusMetricAggregation(unittest.TestCase):
    def setUp(self):
        self.stats = engine.StreamingStatsV440(runs=2, turns=3)
        game_a = _rows([{"life": 40, "creature_tokens": 0, "opp_life_min": 40},
                        {"life": 44, "creature_tokens": 2, "opp_life_min": 31},
                        {"life": 41, "creature_tokens": 5, "opp_life_min": 20}])
        game_b = _rows([{"life": 38, "creature_tokens": 1, "opp_life_min": 39},
                        {"life": 36, "creature_tokens": 1, "opp_life_min": 35}])
        # Call only the v4.87.4 layer's own bookkeeping, not the whole chain of
        # older add() layers (those expect full engine rows).
        saved = engine._V4874_stats_add_old
        engine._V4874_stats_add_old = lambda self, rr, tr, sr: None
        try:
            engine._streaming_stats_add_v4874(self.stats, {}, game_a, [])
            engine._streaming_stats_add_v4874(self.stats, {}, game_b, [])
        finally:
            engine._V4874_stats_add_old = saved
        self.m = engine.build_focus_metrics(self.stats)

    def test_peak_uses_max_for_up_metrics(self):
        hist = dict((v, c) for v, c in self.m["life"]["peak"]["hist"])
        self.assertEqual(hist, {44.0: 1, 38.0: 1})
        tok = dict((v, c) for v, c in self.m["creature_tokens"]["peak"]["hist"])
        self.assertEqual(tok, {5.0: 1, 1.0: 1})

    def test_peak_uses_min_for_down_metrics(self):
        self.assertEqual(self.m["opp_life_min"]["dir"], "down")
        hist = dict((v, c) for v, c in self.m["opp_life_min"]["peak"]["hist"])
        self.assertEqual(hist, {20.0: 1, 35.0: 1})

    def test_by_turn_average_over_games_still_running(self):
        bt = {b["t"]: b for b in self.m["life"]["by_turn"]}
        self.assertAlmostEqual(bt[1]["avg"], 39.0)
        self.assertAlmostEqual(bt[2]["avg"], 40.0)
        self.assertEqual(bt[3]["n"], 1)          # only game A reached turn 3
        self.assertAlmostEqual(bt[3]["avg"], 41.0)
        self.assertLessEqual(bt[2]["p25"], bt[2]["p75"])
        self.assertEqual(self.m["life"]["peak"]["games"], 2)


class TestTransformPassesMetrics(unittest.TestCase):
    def _summary(self, **extra):
        s = {
            "simulation": {"runs": 10, "turns": 3, "seed": 1, "opponent_profile": "random"},
            "by_turn": {"1": {"avg_life": 39.0, "avg_mana_start_main": 1.0, "avg_lands": 1.0, "avg_hand_size": 7.0},
                        "2": {"avg_life": 38.0, "avg_mana_start_main": 2.0, "avg_lands": 2.0, "avg_hand_size": 6.0}},
            "outcomes": {"reach_50_life_pct": 10.0, "reach_111_life_pct": 0.0},
            "scenarios": [{"name": "Combo", "reach_pct": 40.0, "median_reached_turn": 6,
                           "cumulative_reach_by_turn_pct": {"0": 0, "1": 5.0, "2": 40.0}}],
        }
        s.update(extra)
        return s

    def test_new_metrics_are_passed_through(self):
        m = {"life": {"label": "Life total", "by_turn": [], "peak": {"games": 1, "hist": [[40.0, 1]]}}}
        out = to_frontend_run(self._summary(metrics=m), None, "run")
        self.assertEqual(out["metrics"], m)

    def test_legacy_runs_get_life_mana_lands_hand_with_fixed_thresholds(self):
        out = to_frontend_run(self._summary(), None, "run")
        self.assertEqual(set(out["metrics"]), {"life", "mana", "lands", "hand"})
        self.assertTrue(out["metrics"]["life"]["legacy"])
        self.assertEqual(out["metrics"]["life"]["fixed"], [[50, 10.0], [111, 0.0]])

    def test_scenario_median_turn_and_cumulative_reach(self):
        out = to_frontend_run(self._summary(), None, "run")
        sc = out["scen"][0]
        self.assertEqual(sc["median_turn"], 6)
        self.assertEqual(sc["cum"], [[0, 0], [1, 5.0], [2, 40.0]])


class TestCommanderPosturePassThrough(unittest.TestCase):
    """v4.87.4: the Simulation page's commander-posture choice now reaches
    ScenarioStrategy.commander_posture via run_pipeline_v440(commander_posture=...)."""

    def test_thread_local_posture_is_applied_with_the_playstyle(self):
        strategy = engine.ScenarioStrategy()
        engine._V4874_POSTURE.value = "passive"
        try:
            engine.apply_playstyle_override(strategy, None)
        finally:
            engine._V4874_POSTURE.value = None
        self.assertEqual(strategy.commander_posture, "passive")

    def test_without_a_choice_the_default_stays_auto(self):
        strategy = engine.ScenarioStrategy()
        engine.apply_playstyle_override(strategy, None)
        self.assertEqual(strategy.commander_posture, "auto")


if __name__ == "__main__":
    unittest.main()
