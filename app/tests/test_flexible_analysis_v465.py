"""
Unit tests for v4.65.0: flexible, setup-driven Win-Condition outcome
tracking (replacing the hardcoded "111 life" headline metric) and
hand-composition-by-category-over-time tracking.

Context (see App/engine.py's own module comment directly above
_hand_composition_category / _wc_kind_scenarios for the full design
rationale): the analysis output used to show a fixed "111 Leben"
percentage regardless of what the user actually configured on the
Win-Condition/Setup GUI page. The scenario system (new_scenario/
normalize_scenario/scenario_status) already supports arbitrary
thresholds and requirements per scenario, keyed by kind == "Win
Condition" - this version aggregates reach %/median turn over exactly
those configured scenarios instead of a fixed life threshold, and adds
per-turn hand-composition-by-category tracking (lands/ramp/interaction/
card_advantage/creatures/spells/other) reusing the existing role_set()
classification. The legacy milestones/reach_111_life_pct machinery is
left untouched for backward compatibility - only no longer the GUI
headline.

Run from the project root:
    python -m unittest tests.test_flexible_analysis_v465 -v
"""
from __future__ import annotations

import dataclasses
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


class HandCompositionCategoryTests(unittest.TestCase):
    def test_land_is_always_lands_regardless_of_roles(self):
        card = make_card("Forest", type_line="Basic Land — Forest", roles={"land"})
        # is_land is derived from type_line on Card, not settable directly -
        # use a real basic land type_line so card.is_land is True.
        self.assertTrue(card.is_land)
        self.assertEqual(engine._hand_composition_category(card), "lands")

    def test_interaction_role_wins_over_creature_type_line(self):
        # A removal creature ("Reclamation Sage"-style) should count as
        # interaction, not as a generic creature - matches how the rest of
        # the engine treats ROLE_REACTIVE cards (e.g. is_reactive_only).
        card = make_card("Removal Bear", type_line="Creature — Bear", roles={"interaction"})
        self.assertEqual(engine._hand_composition_category(card), "interaction")

    def test_ramp_role_wins_over_creature_type_line(self):
        card = make_card("Mana Dork", type_line="Creature — Elf Druid", roles={"ramp"})
        self.assertEqual(engine._hand_composition_category(card), "ramp")

    def test_burst_mana_role_counts_as_ramp(self):
        card = make_card("Treasure Maker", type_line="Sorcery", roles={"burst_mana"})
        self.assertEqual(engine._hand_composition_category(card), "ramp")

    def test_draw_role_is_card_advantage(self):
        card = make_card("Cantrip", type_line="Instant", roles={"draw"})
        self.assertEqual(engine._hand_composition_category(card), "card_advantage")

    def test_tutor_role_is_card_advantage(self):
        card = make_card("Tutor Spell", type_line="Sorcery", roles={"tutor"})
        self.assertEqual(engine._hand_composition_category(card), "card_advantage")

    def test_vanilla_creature_with_no_roles_is_creatures(self):
        card = make_card("Vanilla Bear", type_line="Creature — Bear", roles=set())
        self.assertEqual(engine._hand_composition_category(card), "creatures")

    def test_instant_with_no_roles_is_spells(self):
        card = make_card("Unclassified Instant", type_line="Instant", roles=set())
        self.assertEqual(engine._hand_composition_category(card), "spells")

    def test_sorcery_with_no_roles_is_spells(self):
        card = make_card("Unclassified Sorcery", type_line="Sorcery", roles=set())
        self.assertEqual(engine._hand_composition_category(card), "spells")

    def test_artifact_with_no_roles_falls_into_other(self):
        card = make_card("Mystery Artifact", type_line="Artifact", roles=set())
        self.assertEqual(engine._hand_composition_category(card), "other")

    def test_planeswalker_with_no_roles_falls_into_other(self):
        card = make_card("Mystery Walker", type_line="Legendary Planeswalker — Test", roles=set())
        self.assertEqual(engine._hand_composition_category(card), "other")


class HandCompositionCountsTests(unittest.TestCase):
    def test_counts_sum_exactly_to_hand_size_and_are_mutually_exclusive(self):
        hand = [
            make_card("Forest", type_line="Basic Land — Forest"),
            make_card("Removal Bear", type_line="Creature — Bear", roles={"interaction"}),
            make_card("Mana Dork", type_line="Creature — Elf", roles={"ramp"}),
            make_card("Cantrip", type_line="Instant", roles={"draw"}),
            make_card("Vanilla Bear", type_line="Creature — Bear", roles=set()),
            make_card("Bolt", type_line="Instant", roles=set()),
            make_card("Weird Artifact", type_line="Artifact", roles=set()),
        ]
        counts = engine._hand_composition_counts(hand)
        self.assertEqual(sum(counts.values()), len(hand))
        self.assertEqual(
            counts,
            {
                "hand_lands": 1,
                "hand_ramp": 1,
                "hand_interaction": 1,
                "hand_card_advantage": 1,
                "hand_creatures": 1,
                "hand_spells": 1,
                "hand_other": 1,
            },
        )

    def test_empty_hand_yields_all_zero_counts(self):
        counts = engine._hand_composition_counts([])
        self.assertEqual(sum(counts.values()), 0)
        self.assertEqual(set(counts), set(engine._HAND_COMPOSITION_FIELDS))


class WcKindScenariosTests(unittest.TestCase):
    def test_filters_to_enabled_win_condition_kind_only(self):
        scenarios = [
            {"id": "a", "name": "A", "kind": "Win Condition", "enabled": True},
            {"id": "b", "name": "B", "kind": "Setup", "enabled": True},
            {"id": "c", "name": "C", "kind": "Win Condition", "enabled": False},
            {"id": "d", "name": "D", "kind": "Combo", "enabled": True},
        ]
        result = engine._wc_kind_scenarios(scenarios)
        self.assertEqual([sc["id"] for sc in result], ["a"])

    def test_missing_enabled_key_defaults_to_true(self):
        scenarios = [{"id": "a", "name": "A", "kind": "Win Condition"}]
        result = engine._wc_kind_scenarios(scenarios)
        self.assertEqual([sc["id"] for sc in result], ["a"])

    def test_empty_or_none_input_returns_empty_list(self):
        self.assertEqual(engine._wc_kind_scenarios([]), [])
        self.assertEqual(engine._wc_kind_scenarios(None), [])


class StreamingStatsAddWinConditionTests(unittest.TestCase):
    """Directly exercises the StreamingStatsV440.add wrap (bypassing a full
    simulation) with hand-built rr/tr/sr rows, matching the field shapes
    scenario_run_rows()/the turn-row builders actually produce."""

    def _make_stats(self):
        return engine.StreamingStatsV440(runs=1, turns=3)

    def _rr(self):
        # Matches the field shapes StreamingStatsV440.add's original body
        # (App/engine.py) expects on a real run-row dict: turn-valued
        # fields are "" (not present/None) when unset, never a bare None -
        # the original add() does str(val).strip() before float(val).
        return {
            "opponent_profile": "goldfish",
            "win_turn": "", "loss_turn": "", "bilbo_activation_turn": "",
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

    def _tr(self, turn, **hand_fields):
        row = {"turn": turn, "opponent_profile": "goldfish"}
        row.update(hand_fields)
        return [row]

    def test_run_reaching_a_win_condition_scenario_is_counted(self):
        stats = self._make_stats()
        rr = self._rr()
        stats.add(rr, self._tr(1), [self._sr("Win Condition", 2)])
        self.assertEqual(stats._wc_reached_count, 1)
        self.assertEqual(stats._wc_reached_turns, [2])
        self.assertTrue(stats._wc_configured)

    def test_run_not_reaching_a_configured_win_condition_is_not_counted(self):
        stats = self._make_stats()
        rr = self._rr()
        stats.add(rr, self._tr(1), [self._sr("Win Condition", None)])
        self.assertEqual(stats._wc_reached_count, 0)
        self.assertTrue(stats._wc_configured)  # configured, just not reached this run

    def test_non_win_condition_kind_scenarios_do_not_count_as_configured(self):
        stats = self._make_stats()
        rr = self._rr()
        stats.add(rr, self._tr(1), [self._sr("Setup", 1)])
        self.assertFalse(stats._wc_configured)
        self.assertEqual(stats._wc_reached_count, 0)

    def test_multiple_win_condition_scenarios_take_the_earliest_reached_turn(self):
        stats = self._make_stats()
        rr = self._rr()
        sr = [self._sr("Win Condition", 5), self._sr("Win Condition", 2)]
        stats.add(rr, self._tr(1), sr)
        self.assertEqual(stats._wc_reached_count, 1)
        self.assertEqual(stats._wc_reached_turns, [2])

    def test_hand_composition_fields_are_accumulated_into_dashboard_turn_stats(self):
        stats = self._make_stats()
        rr = self._rr()
        tr = self._tr(1, hand_lands=2, hand_ramp=1, hand_interaction=0,
                       hand_card_advantage=1, hand_creatures=1, hand_spells=0, hand_other=0)
        stats.add(rr, tr, [])
        self.assertEqual(stats._dashboard_turn_stats[1]["hand_lands"], 2)
        self.assertEqual(stats._dashboard_turn_stats[1]["hand_ramp"], 1)
        self.assertEqual(stats._opponent_dashboard["goldfish"]["turns"][1]["hand_lands"], 2)

    def test_hand_composition_fields_accumulate_across_multiple_runs(self):
        stats = self._make_stats()
        rr = self._rr()
        stats.add(rr, self._tr(1, hand_lands=2), [])
        stats.add(rr, self._tr(1, hand_lands=3), [])
        self.assertEqual(stats._dashboard_turn_stats[1]["hand_lands"], 5)


class AverageDashboardTurnsHandCompositionTests(unittest.TestCase):
    def test_averages_hand_composition_fields_alongside_existing_fields(self):
        raw = defaultdict(Counter)
        raw[1]["count"] = 2
        raw[1]["life"] = 80.0
        raw[1]["hand_lands"] = 4.0
        raw[1]["hand_ramp"] = 2.0
        out = engine._average_dashboard_turns(raw, turns=1)
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertAlmostEqual(row["avg_life"], 40.0)
        self.assertAlmostEqual(row["avg_hand_lands"], 2.0)
        self.assertAlmostEqual(row["avg_hand_ramp"], 1.0)

    def test_turn_with_zero_active_games_is_skipped_like_before(self):
        raw = defaultdict(Counter)
        out = engine._average_dashboard_turns(raw, turns=2)
        self.assertEqual(out, [])


class BuildAnalysisOverviewWinConditionObservationTests(unittest.TestCase):
    def _summary(self, **outcome_overrides):
        outcomes = {
            "win_by_turn_limit_pct": 10.0,
            "loss_by_turn_limit_pct": 5.0,
            "avg_end_hand": 4.0,
            "reach_111_life_pct": 0.0,
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
            "combat_and_removal_diagnostics": {"total_died_in_combat": 3},
        }

    def test_no_win_condition_configured_yields_honest_fallback_observation(self):
        overview = engine.build_analysis_overview(
            self._summary(win_condition_configured=False), []
        )
        joined = " | ".join(overview["observations"])
        self.assertIn("Keine Win Condition", joined)
        self.assertNotIn("111-Life-Schwelle", joined)

    def test_configured_and_reached_win_condition_is_reported_by_name(self):
        overview = engine.build_analysis_overview(
            self._summary(
                win_condition_configured=True,
                win_condition_names=["Mein Combo-Plan"],
                win_condition_reach_pct=42.5,
                win_condition_median_turn=4.0,
            ),
            [],
        )
        joined = " | ".join(overview["observations"])
        self.assertIn("Mein Combo-Plan", joined)
        self.assertIn("42.50%", joined)
        self.assertNotIn("111-Life-Schwelle", joined)

    def test_combat_and_removal_diagnostics_are_forwarded_to_the_overview(self):
        overview = engine.build_analysis_overview(self._summary(), [])
        self.assertEqual(
            overview["combat_and_removal_diagnostics"]["total_died_in_combat"], 3
        )


if __name__ == "__main__":
    unittest.main()
