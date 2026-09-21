"""
Unit tests for v4.69.0 ("Kalibrierungs-Synthese Teil 3" - Entkonfundierung
Farbe x Strategie). See:
  - Data/Models/opponent_state_weights.json (version "1.7")
  - App/opponent_model/state_equation.py's module docstring "v4.69.0" section
  - Docs/opponent_model_calibration_v4_69_0.md (full two-way OLS regression
    tables, per-value decision framework, and the direct answer to the
    user's methodological question about color vs. strategy effects)
  - tests/test_v4670_opponent_recalibration.py (updated in place to the
    current values this version introduced)

This version does NOT re-verify every single value already covered by
test_v4670_opponent_recalibration.py's updated assertions - it specifically
targets what is NEW about v4.69.0: the decision framework itself (apply a
significant contradiction / keep a prior on mere inconclusiveness / revert
non-significant-and-unevidenced to neutral), the newly-added color_modifiers
keys, the documented-but-inert aggro/horde wipe_growth values, and that the
version/engine/GUI/doc trail is fully wired up.

Run from the project root:
    python -m unittest tests.test_v4690_deconfounded_recalibration -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402
from App.opponent_model import state_equation as se  # noqa: E402

_WEIGHTS_PATH = ROOT / "Data" / "Models" / "opponent_state_weights.json"
_CALIBRATION_DOC = ROOT / "Docs" / "opponent_model_calibration_v4_69_0.md"
_STATE_EQ_SRC = ROOT / "App" / "opponent_model" / "state_equation.py"
_GUI_SRC = ROOT / "App" / "gui.py"
_README = ROOT / "Docs" / "README.md"


def _load_weights():
    return json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))


class VersionSyncTests(unittest.TestCase):
    """The version string, ENGINE_VERSION, GUI title, module docstring, and
    README changelog must all agree - the project's standing convention."""

    def test_weights_version_bumped_to_1_7(self):
        # "1.7" was v4.69.0's own version string; v4.70.0 bumped it to "1.8",
        # v4.71.0 bumped it further to "1.9" (see
        # test_v4710_value_weighting.py for the new version's own dedicated
        # assertions) - updated in place here exactly like this file itself
        # updated test_v4670_opponent_recalibration.py's analogous
        # pinned-version check past v4.67.0.
        self.assertEqual(_load_weights()["version"], "1.9")

    def test_engine_version_is_4_69_0(self):
        # v4.73.0 bumped ENGINE_VERSION further - updated in place here per
        # the project's standing convention (see this file's own comment above).
        self.assertEqual(engine.ENGINE_VERSION, "4.75.0")

    def test_gui_title_mentions_4_69_0(self):
        src = _GUI_SRC.read_text(encoding="utf-8")
        self.assertIn('Commander Goldfish v4.75.0', src)

    def test_state_equation_docstring_has_v4690_section(self):
        src = _STATE_EQ_SRC.read_text(encoding="utf-8")
        self.assertIn("v4.69.0", src)
        self.assertIn("deconfounding", src)

    def test_calibration_doc_exists_and_mentions_ols_regression(self):
        self.assertTrue(_CALIBRATION_DOC.exists())
        text = _CALIBRATION_DOC.read_text(encoding="utf-8")
        self.assertIn("OLS", text)
        self.assertIn("lstsq", text)

    def test_readme_has_v4690_entry(self):
        text = _README.read_text(encoding="utf-8")
        self.assertIn("v4.69.0", text)


class DecisionFrameworkTests(unittest.TestCase):
    """The three-way decision rule this version applies uniformly: (1) a
    SIGNIFICANT contradiction of an old value is applied even if it reverses
    the old assumption entirely; (2) a merely NON-significant new result
    does NOT override an existing value backed by independent real-decklist
    evidence; (3) a non-significant result with NO independent prior
    evidence is reverted to neutral (key removed)."""

    @classmethod
    def setUpClass(cls):
        cls.mods = _load_weights()["color_modifiers"]

    def test_rule1_significant_contradiction_applied_black_interaction(self):
        """Black's interaction_availability had stood at 1.20 since v4.39.0.
        The deconfounded regression found a SIGNIFICANT effect in the
        OPPOSITE direction, so it was applied, not merely disclosed."""
        self.assertAlmostEqual(self.mods["B"]["interaction_availability"], 0.85, places=3)
        self.assertLess(self.mods["B"]["interaction_availability"], 1.0)

    def test_rule2_inconclusive_result_keeps_prior_evidence_blue_interaction(self):
        """Blue's deconfounded result was merely non-significant (not
        contradictory) - the real Lier-decklist-evidenced 1.45 is kept."""
        self.assertAlmostEqual(self.mods["U"]["interaction_availability"], 1.45, places=3)

    def test_black_and_blue_get_different_treatment_despite_similar_pattern(self):
        """The core methodological point this version demonstrates: Black
        and Blue both had a pre-existing v4.39.0 interaction_availability
        value, but the new evidence treats them differently because one
        result was significant and the other wasn't - NOT because of an
        arbitrary choice between them."""
        self.assertNotAlmostEqual(self.mods["B"]["interaction_availability"], 1.20, places=3)
        self.assertAlmostEqual(self.mods["U"]["interaction_availability"], 1.45, places=3)

    def test_rule3_non_significant_unevidenced_keys_removed(self):
        """W/U.mana_growth and U/R.board_presence existed ONLY because of
        v4.67.0's own (now-superseded) marginal method - no independent
        prior evidence backs them, and the deconfounded result was not
        significant, so they were removed rather than carried forward."""
        self.assertNotIn("mana_growth", self.mods["W"])
        self.assertNotIn("mana_growth", self.mods["U"])
        self.assertNotIn("board_presence", self.mods["U"])
        self.assertNotIn("board_presence", self.mods["R"])

    def test_rule2_black_wipe_readiness_kept_on_replication_not_significance_alone(self):
        """Black's wipe_readiness deconfounded estimate (1.064) does not
        clear the significance bar either, but it replicates a value
        independently confirmed twice before (v4.39.0 real decklist AND
        v4.67.0's marginal n=50 pass) - kept rather than reset to neutral."""
        self.assertAlmostEqual(self.mods["B"]["wipe_readiness"], 1.10, places=3)


class NewlyAddedColorKeysTests(unittest.TestCase):
    """Color_modifiers keys that were NOT present before v4.69.0 because
    v4.67.0's marginal method did not find them significant, but the
    deconfounded regression does."""

    @classmethod
    def setUpClass(cls):
        cls.mods = _load_weights()["color_modifiers"]

    def test_white_interaction_availability_added(self):
        self.assertAlmostEqual(self.mods["W"]["interaction_availability"], 1.15, places=3)

    def test_black_board_presence_and_mana_growth_added(self):
        self.assertAlmostEqual(self.mods["B"]["board_presence"], 1.06, places=3)
        self.assertAlmostEqual(self.mods["B"]["mana_growth"], 1.14, places=3)

    def test_green_interaction_availability_added(self):
        self.assertAlmostEqual(self.mods["G"]["interaction_availability"], 0.91, places=3)


class ConfirmedFlatStrategyDimensionsTests(unittest.TestCase):
    """interaction_growth/wipe_growth/mana_growth are now CONFIRMED (not
    just suspected) flat across aggro/midrange/control after deconfounding -
    control in particular drops from being the clear outlier to being close
    to aggro/midrange."""

    @classmethod
    def setUpClass(cls):
        cls.curves = _load_weights()["strategy_curves"]

    def test_control_interaction_growth_no_longer_a_wide_outlier(self):
        # Old spread was 0.035 (aggro) to 0.16 (control) - a 4.5x gap.
        aggro = self.curves["aggro"]["interaction_growth"]
        control = self.curves["control"]["interaction_growth"]
        self.assertLess(abs(control - aggro), 0.02, "control should now sit close to aggro, not ~4.5x higher")

    def test_control_wipe_growth_no_longer_a_wide_outlier(self):
        # Old spread was 0.0 (aggro) to 0.11 (control).
        aggro = self.curves["aggro"]["wipe_growth"]
        control = self.curves["control"]["wipe_growth"]
        self.assertLess(control - aggro, 0.02, "control's wipe_growth should now be close to aggro's")

    def test_aggro_and_horde_wipe_growth_nonzero_but_behaviorally_inert(self):
        """Both now carry a real, data-derived nonzero wipe_growth value,
        but wipe_min_turn=999 (unchanged - no turn-timing evidence exists to
        justify unlocking it) means it never actually fires in
        advance_opponent_state. Documented, not silently broken."""
        for strat in ("aggro", "horde"):
            with self.subTest(strategy=strat):
                self.assertGreater(self.curves[strat]["wipe_growth"], 0.0)
                self.assertEqual(self.curves[strat]["wipe_min_turn"], 999)


class IntegrationTests(unittest.TestCase):
    """Real advance_opponent_state runs confirming the engine actually picks
    up the new numbers and that the headline reversal is visible in
    simulated state, not just in the JSON."""

    def test_black_interaction_availability_now_below_white(self):
        """Direct behavioral consequence of the headline finding: a mono-
        black opponent should now build LESS interaction_availability over
        time than a mono-white opponent of the same strategy - the reverse
        of what a pre-v4.69.0 model would have shown."""
        profile_b = se.OpponentProfile(strategy="control", colors={"B"}, bracket=3)
        profile_w = se.OpponentProfile(strategy="control", colors={"W"}, bracket=3)
        state_b = se.OpponentState()
        state_w = se.OpponentState()
        # Independent rng streams per profile - a single shared/interleaved
        # stream lets draw ORDER dominate a modest per-turn difference over
        # only a few turns (see test_v4670's equivalent comment).
        rng_b = __import__("random").Random(11)
        rng_w = __import__("random").Random(12)
        for _ in range(8):
            state_b = se.advance_opponent_state(state_b, profile_b, rng_b)
            state_w = se.advance_opponent_state(state_w, profile_w, rng_w)
        self.assertLess(
            state_b.interaction_availability, state_w.interaction_availability,
            "black should now trail white on interaction_availability after the v4.69.0 reversal",
        )

    def test_aggro_midrange_board_presence_gap_over_control_is_wide(self):
        """The deconfounded board_presence_growth gap between aggro/midrange
        and control is real and, if anything, WIDER than v4.67.0's marginal
        estimate - confirm this shows up after a few turns."""
        profile_aggro = se.OpponentProfile(strategy="aggro", colors={"R"}, bracket=3)
        profile_control = se.OpponentProfile(strategy="control", colors={"U"}, bracket=3)
        state_aggro = se.OpponentState()
        state_control = se.OpponentState()
        rng_aggro = __import__("random").Random(99)
        rng_control = __import__("random").Random(100)
        for _ in range(8):
            state_aggro = se.advance_opponent_state(state_aggro, profile_aggro, rng_aggro)
            state_control = se.advance_opponent_state(state_control, profile_control, rng_control)
        self.assertGreater(state_aggro.board_presence, state_control.board_presence * 1.1)


if __name__ == "__main__":
    unittest.main()
