"""
Unit tests for v4.67.0 ("Kalibrierungs-Synthese Teil 2" - statistisch breite
Neukalibrierung).

SUPERSEDED NOTICE (v4.69.0): the marginal-pooling values this file originally
pinned down (color_modifiers/strategy_curves as first computed in v4.67.0)
were replaced in v4.69.0 by a proper two-way (color x strategy) deconfounded
OLS recalibration - the user explicitly identified that v4.67.0's marginal
pooling could hide real per-axis effects behind confounding (a color's or a
strategy's genuine variation "averaging out" when the other axis isn't held
fixed) and asked for a way to verify this from the data. See:
  - Data/Models/opponent_state_weights.json (version "1.7" as of v4.69.0)
  - App/opponent_model/state_equation.py's module docstring "v4.69.0" section
  - Docs/opponent_model_calibration_v4_69_0.md (full regression/significance
    tables and the decision framework used for every changed/kept/removed value)
  - tests/test_v4690_deconfounded_recalibration.py (the new version's own
    dedicated test file - Black's interaction_availability reversal, the
    kept-vs-reverted decision framework, removed/added color_modifiers keys)

The value assertions below were updated in place to the current (v4.69.0)
numbers so this file keeps passing and still documents what v4.67.0 itself
established structurally (that a broad, real-decklist-derived recalibration
happened at all, and roughly in which direction) - the ORIGINAL v4.67.0
numbers remain visible in git history and in
Docs/opponent_model_calibration_v4_67_0.md.

Three groups: (1) the weights JSON's own internal consistency and the
CURRENT values, (2) that color_modifiers keys removed in v4.69.0 for lack of
significance are indeed gone, (3) a real advance_opponent_state integration
run confirming the current numbers still move simulated state in the
expected direction (aggro still outpaces control on board presence; green's
wipe_readiness is nonzero but still far below white/red).

Run from the project root:
    python -m unittest tests.test_v4670_opponent_recalibration -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App.opponent_model import state_equation as se  # noqa: E402

_WEIGHTS_PATH = ROOT / "Data" / "Models" / "opponent_state_weights.json"
_CALIBRATION_DOC = ROOT / "Docs" / "opponent_model_calibration_v4_67_0.md"


def _load_weights():
    return json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))


class WeightsFileValueTests(unittest.TestCase):
    """Group 1: the weights JSON's current (post-v4.69.0) values."""

    @classmethod
    def setUpClass(cls):
        cls.data = _load_weights()

    def test_version_bumped_past_v467(self):
        # "1.6" was v4.67.0's version string; v4.69.0 bumped it to "1.7",
        # v4.70.0 bumped it to "1.8" (Halbwertszeiten-Recherche), and v4.71.0
        # bumped it further to "1.9" (Wertigkeits-Funktion - see
        # test_v4710_value_weighting.py).
        self.assertEqual(self.data["version"], "1.9")

    def test_strategy_board_presence_growth_current_values(self):
        curves = self.data["strategy_curves"]
        self.assertAlmostEqual(curves["aggro"]["board_presence_growth"], 0.826, places=3)
        self.assertAlmostEqual(curves["midrange"]["board_presence_growth"], 0.811, places=3)
        self.assertAlmostEqual(curves["control"]["board_presence_growth"], 0.604, places=3)
        # horde deliberately UNCHANGED since v4.38.0 - Tokens-tag proxy cannot
        # capture horde's non-creature token generation, see docstring.
        self.assertAlmostEqual(curves["horde"]["board_presence_growth"], 1.30, places=3)

    def test_strategy_mana_growth_current_values(self):
        curves = self.data["strategy_curves"]
        self.assertAlmostEqual(curves["aggro"]["mana_growth"], 0.150, places=3)
        self.assertAlmostEqual(curves["midrange"]["mana_growth"], 0.166, places=3)
        self.assertAlmostEqual(curves["control"]["mana_growth"], 0.161, places=3)
        self.assertAlmostEqual(curves["horde"]["mana_growth"], 0.178, places=3)

    def test_strategy_interaction_and_wipe_growth_now_near_flat(self):
        """v4.69.0 CONFIRMED (not just suspected) that Aggro/Midrange/Control
        genuinely do not differ significantly in interaction/wipe density,
        even after deconfounding color out of the picture - so these were
        moved off the old, small-sample-staggered v4.39.0/v4.43.0 values onto
        the new, closely-clustered but not identical deconfounded values."""
        curves = self.data["strategy_curves"]
        self.assertAlmostEqual(curves["aggro"]["interaction_growth"], 0.079, places=3)
        self.assertAlmostEqual(curves["midrange"]["interaction_growth"], 0.082, places=3)
        self.assertAlmostEqual(curves["control"]["interaction_growth"], 0.078, places=3)
        self.assertAlmostEqual(curves["aggro"]["wipe_growth"], 0.032, places=3)
        self.assertAlmostEqual(curves["midrange"]["wipe_growth"], 0.032, places=3)
        self.assertAlmostEqual(curves["control"]["wipe_growth"], 0.040, places=3)

    def test_color_modifiers_current_values(self):
        mods = self.data["color_modifiers"]
        self.assertAlmostEqual(mods["W"]["wipe_readiness"], 1.30, places=3)
        self.assertAlmostEqual(mods["W"]["board_presence"], 1.08, places=3)
        self.assertAlmostEqual(mods["B"]["wipe_readiness"], 1.10, places=3)
        self.assertAlmostEqual(mods["R"]["mana_growth"], 1.23, places=3)
        self.assertAlmostEqual(mods["R"]["wipe_readiness"], 1.77, places=3)
        self.assertAlmostEqual(mods["G"]["mana_growth"], 1.33, places=3)
        self.assertAlmostEqual(mods["G"]["board_presence"], 1.12, places=3)

    def test_green_wipe_readiness_now_data_derived_not_policy_floor(self):
        """v4.67.0 needed a hand-set 0.15 POLICY floor because raw mono-green
        median wipe density was exactly 0.0 (n=50 mono-green decks only).
        v4.69.0's two-way regression uses every green-inclusive deck across
        all 32 identities and produces a real, significant, data-derived
        value instead - see color_modifiers.G's _comment."""
        g_wipe = self.data["color_modifiers"]["G"]["wipe_readiness"]
        self.assertAlmostEqual(g_wipe, 0.40, places=3)
        self.assertGreater(g_wipe, 0.0)

    def test_black_interaction_availability_reversed(self):
        """Headline v4.69.0 finding: Black's interaction_availability, which
        had stood at 1.20 since v4.39.0 (a real Endrek Sahr decklist), turns
        out to be a SIGNIFICANT overestimate once color and strategy mix are
        deconfounded - it drops to 0.85."""
        self.assertAlmostEqual(self.data["color_modifiers"]["B"]["interaction_availability"], 0.85, places=3)

    def test_blue_interaction_availability_kept_despite_inconclusive_new_data(self):
        """Contrast case for the decision framework: Blue's deconfounded
        result is merely NOT significant (not contradictory), so the
        existing real-decklist-evidenced v4.39.0 value (1.45, from the Lier
        decklist) is kept rather than discarded."""
        self.assertAlmostEqual(self.data["color_modifiers"]["U"]["interaction_availability"], 1.45, places=3)

    def test_white_interaction_availability_now_added(self):
        """New in v4.69.0: White's raw interaction-density edge over Blue
        (already disclosed as a raw finding in v4.67.0's note) is now
        statistically confirmed after deconfounding, so it was added."""
        self.assertAlmostEqual(self.data["color_modifiers"]["W"]["interaction_availability"], 1.15, places=3)

    def test_calibration_docs_exist(self):
        self.assertTrue(_CALIBRATION_DOC.exists(), f"missing {_CALIBRATION_DOC}")
        v469_doc = ROOT / "Docs" / "opponent_model_calibration_v4_69_0.md"
        self.assertTrue(v469_doc.exists(), f"missing {v469_doc}")


class RemovedNonSignificantKeysTests(unittest.TestCase):
    """Group 2: color_modifiers keys v4.67.0 introduced from marginal pooling
    alone, which v4.69.0's deconfounded regression found NOT significant and
    with no independent prior evidence, were removed (reverted to neutral)
    rather than carried forward unexamined."""

    @classmethod
    def setUpClass(cls):
        cls.mods = _load_weights()["color_modifiers"]

    def test_white_mana_growth_removed(self):
        self.assertNotIn("mana_growth", self.mods["W"])

    def test_blue_mana_growth_and_board_presence_removed(self):
        self.assertNotIn("mana_growth", self.mods["U"])
        self.assertNotIn("board_presence", self.mods["U"])

    def test_red_board_presence_removed(self):
        self.assertNotIn("board_presence", self.mods["R"])


class StateEquationLoadingTests(unittest.TestCase):
    """Group 3 (part a): state_equation.py actually reads these current
    values through its own loading path (not just that the JSON parses)."""

    def test_color_multiplier_reads_current_green_wipe_readiness(self):
        se.reload_flavor_matrix()  # forces a fresh weights read path
        mult = se._color_multiplier({"G"}, "wipe_readiness")
        self.assertAlmostEqual(mult, 0.40, places=3)

    def test_color_multiplier_reads_current_red_wipe_readiness(self):
        mult = se._color_multiplier({"R"}, "wipe_readiness")
        self.assertAlmostEqual(mult, 1.77, places=3)

    def test_multicolor_multiplies_current_green_and_red_wipe(self):
        # Gruul (R+G): both colors carry real evidence for this dimension,
        # multiplied together as always.
        mult = se._color_multiplier({"R", "G"}, "wipe_readiness")
        self.assertAlmostEqual(mult, 1.77 * 0.40, places=3)

    def test_color_multiplier_falls_back_to_neutral_for_removed_key(self):
        """Red's board_presence key was removed in v4.69.0 (not significant)
        - the multiplier must fall back to the neutral default (1.0), not
        raise or silently reuse a stale cached value."""
        mult = se._color_multiplier({"R"}, "board_presence")
        self.assertAlmostEqual(mult, 1.0, places=3)


class IntegrationDirectionTests(unittest.TestCase):
    """Group 3 (part b): a real advance_opponent_state run confirms the
    current numbers still move state in the expected direction."""

    def test_aggro_still_outpaces_control_on_board_presence(self):
        # Independent rng streams per profile (NOT one shared/interleaved
        # stream - sharing one stream means whichever call happens to run
        # first each turn "claims" that turn's draw, which can swamp a real
        # but modest per-turn growth-rate difference with pure draw-order
        # noise over only a few turns).
        profile_aggro = se.OpponentProfile(strategy="aggro", colors={"R"}, bracket=3)
        profile_control = se.OpponentProfile(strategy="control", colors={"U"}, bracket=3)
        state_aggro = se.OpponentState()
        state_control = se.OpponentState()
        rng_aggro = __import__("random").Random(42)
        rng_control = __import__("random").Random(43)
        for _ in range(8):
            state_aggro = se.advance_opponent_state(state_aggro, profile_aggro, rng_aggro)
            state_control = se.advance_opponent_state(state_control, profile_control, rng_control)
        self.assertGreater(
            state_aggro.board_presence, state_control.board_presence,
            "aggro should still build more board presence than control after the deconfounded "
            "recalibration - if anything the gap is now WIDER than the v4.67.0 marginal estimate",
        )

    def test_green_still_lags_white_on_wipe_readiness(self):
        """Green's wipe_readiness multiplier changed (0.15 policy floor ->
        0.40 data-derived value in v4.69.0), but the qualitative ordering
        (green far below white) must still hold."""
        profile_control_green = se.OpponentProfile(strategy="control", colors={"G"}, bracket=3)
        profile_control_white = se.OpponentProfile(strategy="control", colors={"W"}, bracket=3)
        state_green = se.OpponentState()
        state_white = se.OpponentState()
        rng_green = __import__("random").Random(7)
        rng_white = __import__("random").Random(8)
        for _ in range(7):
            state_green = se.advance_opponent_state(state_green, profile_control_green, rng_green)
            state_white = se.advance_opponent_state(state_white, profile_control_white, rng_white)
        self.assertGreater(state_green.wipe_readiness, 0.0)
        self.assertLess(
            state_green.wipe_readiness, state_white.wipe_readiness,
            "green should still lag behind white on wipe readiness with the new data-derived value",
        )


if __name__ == "__main__":
    unittest.main()
