"""
Unit tests for v4.65.1: two bugfixes found through a critical, evidence-
based review of two real GUI runs the user uploaded (Bilbo V1 + Aziza V2,
2026-09-14), both run with the v4.64.0 "Gegnerprofil" dialog active.

Fix 1: strategy.opponent_profile (and therefore simulation_config.json's
"opponent_profile", the GUI's "Gewählter Modus" label, and the Overview's
"Opponent: X" box) stayed on the simple dropdown value ("goldfish", which
by definition deals 0 damage - see OPPONENT_PROFILES) even when
advanced_opponent_model was active and real, damage-dealing per-seat
opponents were actually running. Confirmed in the uploaded runs via
turns.csv event log entries ("ADVANCED aggro/BW: took X combat/pressure
damage") that are structurally impossible under a true goldfish opponent.
See App/engine.py's own module comment directly above
_advanced_opponent_actual_seat_summary for the full write-up.

Fix 2: opponent_model_cross_check.json (and its AI_ANALYSIS_INSTRUCTIONS.md
section) is written by the v4.44.0 run_pipeline_v440 wrapper AFTER the v4.7
wrapper already rebuilt the ZIP - so it has been silently missing from
EVERY delivered result ZIP since v4.44.0. Directly confirmed: the uploaded
ZIPs' AI_ANALYSIS_INSTRUCTIONS.md provably ends before the "v4.44.0
Opponent-Model-Cross-Check" section, and opponent_model_cross_check.json is
absent from both ZIPs entirely, despite being written to result_dir on
disk. Same fix pattern as the pre-existing v4.6/v4.7 precedents (see their
own "Base wrapper zipped before these new files were created." comments):
rebuild the ZIP once more, at the very end of the whole wrapper chain.

Run from the project root:
    python -m unittest tests.test_v4651_bugfixes -v
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402


class AdvancedOpponentActualSeatSummaryTests(unittest.TestCase):
    def test_empty_seats_yields_empty_summary(self):
        self.assertEqual(engine._advanced_opponent_actual_seat_summary([], seed=1, runs=10), [])

    def test_fixed_non_random_seats_resolve_to_themselves_every_run(self):
        seats = [{"strategy": "aggro", "colors": ["B", "W"]}]
        out = engine._advanced_opponent_actual_seat_summary(seats, seed=1, runs=5)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["seat_index"], 0)
        self.assertEqual(out[0]["configured"], seats[0])
        self.assertEqual(out[0]["actual_counts"], {"aggro/BW": 5})

    def test_random_marker_seat_distributes_across_multiple_runs(self):
        seats = [{"strategy": "?", "colors": ["?"]}]
        out = engine._advanced_opponent_actual_seat_summary(seats, seed=1, runs=30)
        counts = out[0]["actual_counts"]
        self.assertEqual(sum(counts.values()), 30)
        # More than one distinct (strategy, colors) combo should appear
        # across 30 runs - otherwise the "?" marker isn't actually being
        # resolved at all (a real, plausible way this could silently break).
        self.assertGreater(len(counts), 1)

    def test_matches_the_real_per_run_resolver_exactly(self):
        # The summary must not invent its own resolution logic - it has to
        # reconstruct exactly what _resolve_advanced_opponent_seats_for_run
        # (the function actually used at simulation time) produces for each
        # run_id, or the reported "actual" seats could silently diverge from
        # what was really simulated.
        seats = [{"strategy": "?", "colors": ["W", "U"]}, {"strategy": "control", "colors": ["?"]}]
        out = engine._advanced_opponent_actual_seat_summary(seats, seed=7, runs=12)
        for run_id in range(1, 13):
            resolved = engine._resolve_advanced_opponent_seats_for_run(seats, 7, run_id)
            for seat_index, seat in enumerate(resolved):
                colors = "".join(sorted(seat.get("colors", []))) or "C"
                label = f"{seat.get('strategy', '?')}/{colors}"
                self.assertIn(
                    label, out[seat_index]["actual_counts"],
                    f"run {run_id} seat {seat_index} resolved to {label}, "
                    "not reflected in the reconstructed summary",
                )

    def test_multiple_seats_are_tracked_independently(self):
        seats = [
            {"strategy": "aggro", "colors": ["R"]},
            {"strategy": "control", "colors": ["U"]},
        ]
        out = engine._advanced_opponent_actual_seat_summary(seats, seed=1, runs=4)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["actual_counts"], {"aggro/R": 4})
        self.assertEqual(out[1]["actual_counts"], {"control/U": 4})


class BuildAnalysisOverviewAdvancedOpponentTests(unittest.TestCase):
    def _summary(self, sim_overrides=None):
        sim = {"runs": 10, "advanced_opponent_model": False}
        sim.update(sim_overrides or {})
        return {
            "outcomes": {
                "win_by_turn_limit_pct": 0.0, "loss_by_turn_limit_pct": 0.0,
                "avg_end_hand": 4.0, "reach_111_life_pct": 0.0,
            },
            "simulation": sim,
            "engine_invariants": {"status": "PASS"},
            "dashboard_strategy": {"selected": [], "inferred_for_display_only": []},
            "opening": {},
            "dashboard_by_turn": [],
            "cumulative_outcomes_by_turn": [],
            "scenarios": [],
            "opponent_breakdown": {},
            "combat_and_removal_diagnostics": {},
        }

    def test_inactive_advanced_opponent_model_adds_no_misleading_warning(self):
        overview = engine.build_analysis_overview(self._summary(), [])
        self.assertFalse(overview["advanced_opponent_summary"]["active"])
        self.assertFalse(
            any("Gegnerprofil aktiv" in o for o in overview["observations"])
        )

    def test_active_advanced_opponent_model_is_surfaced_and_warned_about_first(self):
        summary = self._summary({
            "advanced_opponent_model": True,
            "advanced_opponent_seat_specs": [{"strategy": "aggro", "colors": ["B", "W"]}],
            "advanced_opponent_actual_seat_summary": [
                {"seat_index": 0, "configured": {"strategy": "aggro", "colors": ["B", "W"]},
                 "actual_counts": {"aggro/BW": 10}},
            ],
            "advanced_opponent_label": "Gegnerprofil aktiv (1 Sitzplätze) statt nur 'goldfish'",
        })
        overview = engine.build_analysis_overview(summary, [])
        wc = overview["advanced_opponent_summary"]
        self.assertTrue(wc["active"])
        self.assertEqual(wc["seat_specs"], [{"strategy": "aggro", "colors": ["B", "W"]}])
        self.assertEqual(wc["actual_seat_summary"][0]["actual_counts"], {"aggro/BW": 10})
        # The warning must be the FIRST observation - a user skimming only
        # the top of the list must not miss it (this is exactly what went
        # unnoticed in the two uploaded runs).
        self.assertIn("Gegnerprofil aktiv", overview["observations"][0])
        self.assertIn("goldfish", overview["observations"][0])

    def test_engine_integrity_observation_is_preserved_alongside_the_new_warning(self):
        summary = self._summary({
            "advanced_opponent_model": True,
            "advanced_opponent_label": "Gegnerprofil aktiv (2 Sitzplätze) statt nur 'goldfish'",
        })
        overview = engine.build_analysis_overview(summary, [])
        joined = " | ".join(overview["observations"])
        self.assertIn("Engine-Integrität: PASS", joined)
        self.assertIn("Gegnerprofil aktiv", joined)


class RezipAfterFinalWrapperTests(unittest.TestCase):
    """Directly exercises the v4.65.1 re-zip wrapper in isolation, without
    running a real deck pipeline: swaps out _V4651_pipeline_old (the
    captured reference to the previous run_pipeline_v440, i.e. the v4.44.0
    wrapper) for a stub that reproduces exactly the bug's precondition - a
    ZIP built before a later file was written to result_dir."""

    def test_rebuilds_the_zip_to_include_files_written_after_the_base_pipeline_already_zipped(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            result_dir = tmp / "result"
            result_dir.mkdir()
            (result_dir / "a.txt").write_text("a", encoding="utf-8")
            zip_path = tmp / "result.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.write(result_dir / "a.txt", arcname="a.txt")

            # Reproduces exactly what the v4.44.0 wrapper does: write a file
            # to result_dir AFTER the zip already exists - this file is the
            # stand-in for opponent_model_cross_check.json.
            (result_dir / "opponent_model_cross_check.json").write_text("{}", encoding="utf-8")

            # Sanity check the bug precondition actually holds before the fix runs.
            with zipfile.ZipFile(zip_path) as zf:
                self.assertNotIn("opponent_model_cross_check.json", zf.namelist())

            original = engine._V4651_pipeline_old
            engine._V4651_pipeline_old = lambda *a, **k: {
                "result_dir": result_dir, "zip_path": zip_path,
            }
            try:
                result = engine.run_pipeline_v440()
            finally:
                engine._V4651_pipeline_old = original

            self.assertEqual(Path(result["zip_path"]), zip_path)
            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
            self.assertIn("opponent_model_cross_check.json", names)
            self.assertIn("a.txt", names)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_missing_result_dir_does_not_raise_and_still_returns_the_result(self):
        # The re-zip is a best-effort diagnostic convenience (same
        # philosophy as the v4.44.0 wrapper's own try/except) - it must
        # never break primary result delivery if something is wrong with
        # result_dir/zip_path.
        original = engine._V4651_pipeline_old
        engine._V4651_pipeline_old = lambda *a, **k: {
            "result_dir": "/nonexistent/path/should/not/crash",
            "zip_path": "/nonexistent/path/should/not/crash.zip",
        }
        try:
            result = engine.run_pipeline_v440()
        finally:
            engine._V4651_pipeline_old = original
        self.assertEqual(result["result_dir"], "/nonexistent/path/should/not/crash")


if __name__ == "__main__":
    unittest.main()
