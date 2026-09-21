"""
Unit tests for v4.65.2: the "Aziza win-definition gap" the user asked to be
tackled as a follow-up to the v4.65.1 critical review ("Ja, an die
Aziza-Siegdefinitionslücke auch ranmachen").

Background: Aziza V2's two configured Win-Condition scenarios
(Data/Scenarios/aziza_alpha_strike_v1.json) use the x_spell_lethal
predicate with target="any" - App/scenario_predicates/handlers.py checks
this against only the WEAKEST of the (up to) 3 abstract opponents
(min(lives)). check_win() in App/engine.py, however, only marks a run as
won once ALL entries of state.opponents are <= 0. A 99% scenario "Match"
with a 0% actual "win" is therefore not an engine bug, but a genuine gap
between "the combo goes off against one opponent" and "the whole
multiplayer game is over" - and it is generic to any deck using
target="any"/an index in a Win-Condition scenario, not special-cased to
Aziza's card names.

This file tests the additive, generic fix: _wc_scenario_target_scope()
(derives "each"/"any"/"mixed"/"n/a" purely from a scenario's own 'derived'
predicates), the new StreamingStatsV440.add crosstab counter
(_wc_reached_and_full_win_count), the new streaming_summary_v440 output
fields, and the new build_analysis_overview observation.

Run from the project root:
    python -m unittest tests.test_v4652_aziza_win_gap -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402


class WcScenarioTargetScopeTests(unittest.TestCase):
    def test_x_spell_lethal_target_any_is_single_target_scope(self):
        sc = {"derived": [{"type": "x_spell_lethal", "params": {"card": "Banefire", "target": "any"}}]}
        self.assertEqual(engine._wc_scenario_target_scope(sc), "any")

    def test_missing_target_param_defaults_to_any_matching_the_real_predicate_default(self):
        # scenario_predicates/handlers.py's x_spell_lethal/opponent_life_at_or_below/
        # commander_damage_lethal all do params.get("target", "any") - a scenario
        # that omits "target" entirely is therefore scope "any", not "n/a".
        sc = {"derived": [{"type": "x_spell_lethal", "params": {"card": "Banefire"}}]}
        self.assertEqual(engine._wc_scenario_target_scope(sc), "any")

    def test_target_each_is_full_table_scope(self):
        sc = {"derived": [{"type": "opponent_life_at_or_below", "params": {"threshold": 0, "target": "each"}}]}
        self.assertEqual(engine._wc_scenario_target_scope(sc), "each")

    def test_a_fixed_opponent_index_counts_as_single_target_scope(self):
        sc = {"derived": [{"type": "commander_damage_lethal", "params": {"target": 0}}]}
        self.assertEqual(engine._wc_scenario_target_scope(sc), "any")

    def test_mixed_each_and_any_in_the_same_scenario_is_reported_as_mixed(self):
        sc = {"derived": [
            {"type": "x_spell_lethal", "params": {"card": "X", "target": "each"}},
            {"type": "opponent_life_at_or_below", "params": {"threshold": 10, "target": "any"}},
        ]}
        self.assertEqual(engine._wc_scenario_target_scope(sc), "mixed")

    def test_scenario_with_no_target_aware_predicates_is_not_applicable(self):
        sc = {"derived": [{"type": "resource_available", "params": {"resource": "mana", "min_count": 3}}]}
        self.assertEqual(engine._wc_scenario_target_scope(sc), "n/a")

    def test_empty_or_missing_derived_is_not_applicable(self):
        self.assertEqual(engine._wc_scenario_target_scope({}), "n/a")
        self.assertEqual(engine._wc_scenario_target_scope({"derived": []}), "n/a")

    def test_matches_the_real_aziza_scenario_shape(self):
        # Exact shape of Data/Scenarios/aziza_alpha_strike_v1.json's first
        # entry (resource_available + x_spell_lethal target="any").
        sc = {
            "name": "Aziza Alpha-Strike (Banefire Copy)",
            "kind": "Win Condition",
            "derived": [
                {"type": "resource_available", "params": {"resource": "untapped_creatures", "min_count": 3}},
                {"type": "x_spell_lethal", "params": {"card": "Banefire", "copy_multiplier": 2, "target": "any"}},
            ],
        }
        self.assertEqual(engine._wc_scenario_target_scope(sc), "any")


class StreamingStatsAddFullWinCrosstabTests(unittest.TestCase):
    """Directly exercises the v4.65.2 StreamingStatsV440.add wrap (which
    sits on top of the v4.65.0 wrap) with hand-built rr/tr/sr rows, same
    harness style as tests/test_flexible_analysis_v465.py's
    StreamingStatsAddWinConditionTests."""

    def _make_stats(self):
        return engine.StreamingStatsV440(runs=1, turns=3)

    def _rr(self, win_turn=""):
        return {
            "opponent_profile": "goldfish",
            "win_turn": win_turn, "loss_turn": "", "bilbo_activation_turn": "",
            "mulligans": 0, "opening_land_count": 0, "opening_early_ramp": 0,
            "hand_size_end": 0, "life_end": 40, "cards_drawn_total": 0,
            "scry_count": 0, "surveil_count": 0, "connive_count": 0,
        }

    def _sr(self, kind, reached_turn):
        return {
            "scenario_id": "sid", "scenario_name": "Test WC", "kind": kind,
            "reached": int(reached_turn is not None),
            "first_reached_turn": "" if reached_turn is None else reached_turn,
        }

    def _tr(self, turn):
        return [{"turn": turn, "opponent_profile": "goldfish"}]

    def test_wc_reached_and_full_win_is_counted(self):
        stats = self._make_stats()
        stats.add(self._rr(win_turn=6), self._tr(1), [self._sr("Win Condition", 4)])
        self.assertEqual(stats._wc_reached_and_full_win_count, 1)
        # the v4.65.0 counter this wrap builds on top of must still work.
        self.assertEqual(stats._wc_reached_count, 1)

    def test_wc_reached_but_no_full_win_is_not_counted(self):
        stats = self._make_stats()
        stats.add(self._rr(win_turn=""), self._tr(1), [self._sr("Win Condition", 4)])
        self.assertEqual(stats._wc_reached_and_full_win_count, 0)
        self.assertEqual(stats._wc_reached_count, 1)  # match still happened

    def test_full_win_without_a_reached_wc_scenario_is_not_counted(self):
        stats = self._make_stats()
        stats.add(self._rr(win_turn=6), self._tr(1), [self._sr("Win Condition", None)])
        self.assertEqual(stats._wc_reached_and_full_win_count, 0)

    def test_accumulates_correctly_across_multiple_runs(self):
        stats = self._make_stats()
        stats.add(self._rr(win_turn=6), self._tr(1), [self._sr("Win Condition", 4)])   # match + win
        stats.add(self._rr(win_turn=""), self._tr(1), [self._sr("Win Condition", 4)])  # match, no win
        stats.add(self._rr(win_turn=8), self._tr(1), [self._sr("Win Condition", None)])  # win, no match
        self.assertEqual(stats._wc_reached_and_full_win_count, 1)
        self.assertEqual(stats._wc_reached_count, 2)


class StreamingSummaryFullWinCrosstabTests(unittest.TestCase):
    """Exercises the v4.65.2 streaming_summary_v440 wrap in isolation by
    stubbing out _V4652_summary_old (the captured reference to the
    v4.65.0-wrapped function) with a lightweight fixed base summary - same
    isolation technique as v4.65.1's RezipAfterFinalWrapperTests."""

    def _run(self, stats, strategy, base_summary):
        original = engine._V4652_summary_old
        engine._V4652_summary_old = lambda *a, **k: base_summary
        try:
            return engine.streaming_summary_v440(
                deck=[], stats=stats, cfg=None, strategy=strategy,
                impact_rows=[], detailed_runs_logged=0, log_policy="",
            )
        finally:
            engine._V4652_summary_old = original

    def test_computes_crosstab_percentages_and_target_scope_from_the_aziza_shaped_scenario(self):
        stats = engine.StreamingStatsV440(runs=1, turns=1)
        stats.run_count = 20
        stats._wc_reached_count = 10
        stats._wc_reached_and_full_win_count = 4

        strategy = SimpleNamespace(scenarios=[
            {
                "id": "s1", "name": "Aziza Alpha-Strike (Banefire Copy)", "kind": "Win Condition",
                "enabled": True,
                "derived": [
                    {"type": "resource_available", "params": {"resource": "untapped_creatures", "min_count": 3}},
                    {"type": "x_spell_lethal", "params": {"card": "Banefire", "target": "any"}},
                ],
            },
        ])
        base_summary = {
            "outcomes": {"win_condition_configured": True},
            "scenarios": [
                {"id": "s1", "name": "Aziza Alpha-Strike (Banefire Copy)", "kind": "Win Condition"},
            ],
        }
        data = self._run(stats, strategy, base_summary)

        self.assertAlmostEqual(data["outcomes"]["win_condition_reach_and_full_win_pct"], 20.0)  # 4/20
        self.assertAlmostEqual(data["outcomes"]["win_condition_reach_but_no_full_win_pct"], 30.0)  # 6/20
        self.assertEqual(
            data["outcomes"]["win_condition_single_target_names"],
            ["Aziza Alpha-Strike (Banefire Copy)"],
        )
        self.assertEqual(data["scenarios"][0]["target_scope"], "any")

    def test_each_scope_scenario_is_not_flagged_as_single_target(self):
        stats = engine.StreamingStatsV440(runs=1, turns=1)
        stats.run_count = 10
        stats._wc_reached_count = 5
        stats._wc_reached_and_full_win_count = 5

        strategy = SimpleNamespace(scenarios=[
            {
                "id": "s1", "name": "Full-Table Wipe", "kind": "Win Condition", "enabled": True,
                "derived": [{"type": "opponent_life_at_or_below", "params": {"threshold": 0, "target": "each"}}],
            },
        ])
        base_summary = {
            "outcomes": {"win_condition_configured": True},
            "scenarios": [{"id": "s1", "name": "Full-Table Wipe", "kind": "Win Condition"}],
        }
        data = self._run(stats, strategy, base_summary)

        self.assertEqual(data["outcomes"]["win_condition_single_target_names"], [])
        self.assertEqual(data["scenarios"][0]["target_scope"], "each")
        # reach == full-win here (5/10 both), no gap - still correctly reported.
        self.assertAlmostEqual(data["outcomes"]["win_condition_reach_and_full_win_pct"], 50.0)
        self.assertAlmostEqual(data["outcomes"]["win_condition_reach_but_no_full_win_pct"], 0.0)

    def test_no_win_condition_configured_yields_zero_percentages(self):
        stats = engine.StreamingStatsV440(runs=1, turns=1)
        stats.run_count = 10
        stats._wc_reached_count = 0
        stats._wc_reached_and_full_win_count = 0

        strategy = SimpleNamespace(scenarios=[])
        base_summary = {"outcomes": {"win_condition_configured": False}, "scenarios": []}
        data = self._run(stats, strategy, base_summary)

        self.assertAlmostEqual(data["outcomes"]["win_condition_reach_and_full_win_pct"], 0.0)
        self.assertAlmostEqual(data["outcomes"]["win_condition_reach_but_no_full_win_pct"], 0.0)
        self.assertEqual(data["outcomes"]["win_condition_single_target_names"], [])


class BuildAnalysisOverviewTargetScopeObservationTests(unittest.TestCase):
    def _summary(self, **outcome_overrides):
        outcomes = {
            "win_by_turn_limit_pct": 0.0, "loss_by_turn_limit_pct": 0.0,
            "avg_end_hand": 4.0, "reach_111_life_pct": 0.0,
        }
        outcomes.update(outcome_overrides)
        return {
            "outcomes": outcomes,
            "simulation": {"runs": 10},
            "engine_invariants": {"status": "PASS"},
            "dashboard_strategy": {"selected": [], "inferred_for_display_only": []},
            "opening": {},
            "dashboard_by_turn": [],
            "cumulative_outcomes_by_turn": [],
            "scenarios": [],
            "opponent_breakdown": {},
            "combat_and_removal_diagnostics": {},
        }

    def test_single_target_gap_is_reported_with_both_percentages(self):
        overview = engine.build_analysis_overview(
            self._summary(
                win_condition_configured=True,
                win_condition_names=["Aziza Alpha-Strike (Banefire Copy)"],
                win_condition_reach_pct=99.0,
                win_condition_reach_and_full_win_pct=0.0,
                win_condition_single_target_names=["Aziza Alpha-Strike (Banefire Copy)"],
            ),
            [],
        )
        joined = " | ".join(overview["observations"])
        self.assertIn("Ziel-Scope-Hinweis", joined)
        self.assertIn("Aziza Alpha-Strike (Banefire Copy)", joined)
        self.assertIn("99.00%", joined)
        self.assertIn("0.00%", joined)

    def test_full_table_scope_only_does_not_trigger_the_gap_observation(self):
        overview = engine.build_analysis_overview(
            self._summary(
                win_condition_configured=True,
                win_condition_names=["Full-Table Wipe"],
                win_condition_reach_pct=50.0,
                win_condition_reach_and_full_win_pct=50.0,
                win_condition_single_target_names=[],
            ),
            [],
        )
        joined = " | ".join(overview["observations"])
        self.assertNotIn("Ziel-Scope-Hinweis", joined)

    def test_zero_reach_does_not_trigger_the_gap_observation_even_if_single_target(self):
        overview = engine.build_analysis_overview(
            self._summary(
                win_condition_configured=True,
                win_condition_names=["Never Matched"],
                win_condition_reach_pct=0.0,
                win_condition_reach_and_full_win_pct=0.0,
                win_condition_single_target_names=["Never Matched"],
            ),
            [],
        )
        joined = " | ".join(overview["observations"])
        self.assertNotIn("Ziel-Scope-Hinweis", joined)

    def test_no_win_condition_configured_does_not_crash_or_trigger_the_gap_observation(self):
        overview = engine.build_analysis_overview(
            self._summary(win_condition_configured=False), []
        )
        joined = " | ".join(overview["observations"])
        self.assertNotIn("Ziel-Scope-Hinweis", joined)
        self.assertIn("Keine Win Condition", joined)


if __name__ == "__main__":
    unittest.main()
