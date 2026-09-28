"""
Unit tests for v4.71.0 ("Wertigkeits-Funktion" + Engine-Integration audit).
See:
  - Data/Models/opponent_state_weights.json (version "1.9",
    permanent_type_value_usd, card_value_weighting)
  - App/opponent_model/state_equation.py's module docstring "v4.71.0" section
    and _card_value_weight/_bucket_value_multiplier/_effective_half_life
  - Docs/opponent_model_calibration_v4_71_0.md (curve derivation, engine-
    integration audit, full gap status list)

This version does not re-verify anything already covered by
test_v4700_halflife_recalibration.py / test_advanced_opponent_model.py -
it targets what is actually NEW in v4.71.0: the log-scale value-weighting
functions, their combination into _effective_half_life, the immunity
guardrail, and that the JSON's stale "Engine-Integration still open" note
was corrected (not that the integration itself works end-to-end - that is
already test_advanced_opponent_model.py's job).

Run from the project root:
    python -m unittest tests.test_v4710_value_weighting -v
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
_CALIBRATION_DOC = ROOT / "Docs" / "opponent_model_calibration_v4_71_0.md"
_STATE_EQ_SRC = ROOT / "App" / "opponent_model" / "state_equation.py"
_GUI_SRC = ROOT / "App" / "gui.py"
_README = ROOT / "Docs" / "README.md"


def _load_weights():
    return json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))


class VersionSyncTests(unittest.TestCase):
    def test_weights_version_is_1_9(self):
        self.assertEqual(_load_weights()["version"], "1.9")

    def test_engine_version_is_4_71_0(self):
        # v4.73.0 bumped ENGINE_VERSION further (CURATED_OVERRIDES-Erweiterung
        # Runde 2, siehe test_v4730_curated_overrides_expansion_round2.py) -
        # this test's name is kept (established precedent: assertion body
        # updated, not renamed).
        self.assertEqual(engine.ENGINE_VERSION, "4.87.0")

    def test_gui_title_mentions_4_71_0(self):
        src = _GUI_SRC.read_text(encoding="utf-8")
        self.assertIn("Commander Goldfish v4.87.0", src)

    def test_state_equation_docstring_has_v4710_section(self):
        src = _STATE_EQ_SRC.read_text(encoding="utf-8")
        self.assertIn("v4.71.0", src)
        self.assertIn("_card_value_weight", src)
        self.assertIn("_effective_half_life", src)

    def test_calibration_doc_exists_and_mentions_key_terms(self):
        self.assertTrue(_CALIBRATION_DOC.exists())
        text = _CALIBRATION_DOC.read_text(encoding="utf-8")
        self.assertIn("Wertigkeit", text)
        self.assertIn("advanced_opponent_model", text)

    def test_readme_has_v4710_entry(self):
        text = _README.read_text(encoding="utf-8")
        self.assertIn("v4.71.0", text)

    def test_stale_engine_integration_note_is_corrected(self):
        """The v4.43.0-era 'Verbleibend offen ... Engine-Integration' line
        must now carry a visible correction, not silently vanish or keep
        claiming the integration is still missing."""
        note = _load_weights()["note"]
        idx = note.find("die eigentliche Engine-Integration")
        self.assertNotEqual(idx, -1)
        # The correction must appear shortly after the stale claim.
        self.assertIn("KORRIGIERT v4.71.0", note[idx:idx + 400])


class CardValueWeightTests(unittest.TestCase):
    """_card_value_weight(price_usd): the log-scale, floor-bounded curve."""

    def setUp(self):
        se.reload_weights()
        self.addCleanup(se.reload_weights)

    def test_zero_price_hits_the_floor_not_zero(self):
        w = se._card_value_weight(0.0)
        self.assertAlmostEqual(w, 0.3, places=3)
        self.assertGreater(w, 0.0)

    def test_negative_price_is_clamped_like_zero(self):
        self.assertAlmostEqual(se._card_value_weight(-5.0), se._card_value_weight(0.0), places=6)

    def test_weight_is_monotonically_increasing_in_price(self):
        prices = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 100.0, 500.0]
        weights = [se._card_value_weight(p) for p in prices]
        for a, b in zip(weights, weights[1:]):
            self.assertLess(a, b)

    def test_weight_never_reaches_or_exceeds_1(self):
        for p in [0.0, 1.0, 100.0, 1_000_000.0]:
            self.assertLess(se._card_value_weight(p), 1.0)

    def test_30_vs_500_is_barely_distinguishable(self):
        # User's explicit calibration anchor: the difference between a 30
        # and a 500 (EUR/USD) card should be "kaum merkbar".
        w30 = se._card_value_weight(30.0)
        w500 = se._card_value_weight(500.0)
        self.assertLess(w500 - w30, 0.03)

    def test_low_end_price_changes_are_clearly_noticeable(self):
        # In contrast, small changes near the bottom of the price range must
        # move the weight substantially - this is the whole point of using
        # log1p rather than a flat/linear or overly-saturated curve.
        w0 = se._card_value_weight(0.0)
        w5 = se._card_value_weight(5.0)
        self.assertGreater(w5 - w0, 0.3)


class BucketValueMultiplierTests(unittest.TestCase):
    def setUp(self):
        se.reload_weights()
        self.addCleanup(se.reload_weights)

    def test_reads_current_permanent_type_value_usd(self):
        table = _load_weights()["permanent_type_value_usd"]
        for bucket in ("creature", "artifact", "enchantment", "planeswalker", "land"):
            self.assertIn(bucket, table)

    def test_multiplier_is_within_configured_bounds(self):
        cfg = _load_weights()["card_value_weighting"]
        min_mult = cfg["min_multiplier"]
        max_mult = cfg["max_multiplier"]
        for bucket in ("creature", "artifact", "enchantment", "planeswalker", "land"):
            mult = se._bucket_value_multiplier(bucket)
            self.assertGreaterEqual(mult, min_mult)
            self.assertLessEqual(mult, max_mult)

    def test_pricier_bucket_gets_a_lower_multiplier(self):
        # planeswalker (real avg ~$5.12) is the priciest bucket; land (~$1.46)
        # the cheapest - planeswalker should therefore get a SHORTER-pulling
        # (lower) multiplier than land.
        self.assertLess(
            se._bucket_value_multiplier("planeswalker"),
            se._bucket_value_multiplier("land"),
        )

    def test_unknown_bucket_falls_back_without_raising(self):
        # Should not raise - falls back to a default price rather than KeyError.
        se._bucket_value_multiplier("not_a_real_bucket")


class EffectiveHalfLifeTests(unittest.TestCase):
    """_effective_half_life: the combined, ceiling-enforced result."""

    def setUp(self):
        se.reload_weights()
        self.addCleanup(se.reload_weights)

    def _bracket_cfg(self, bracket=3):
        return _load_weights()["bracket_scaling"][str(bracket)]

    def test_matches_manual_combination_for_a_real_bucket(self):
        bracket_cfg = self._bracket_cfg(3)
        base = se._permanent_type_half_life("creature")
        impact = se._impact_half_life_multiplier(bracket_cfg)
        value_mult = se._bucket_value_multiplier("creature")
        expected = min(base * impact * value_mult, se._half_life_ceiling())
        self.assertAlmostEqual(se._effective_half_life("creature", bracket_cfg), expected, places=6)

    def test_never_exceeds_the_ceiling_even_with_an_inflated_multiplier(self):
        """The user's explicit requirement: a value of 0 must never make a
        card permanently immune. Simulate the exact failure mode this
        guards against - a very cheap bucket price combined with a
        deliberately raised max_multiplier - and confirm the FINAL combined
        half-life still respects the ceiling, not just the raw table value."""
        original = se._WEIGHTS
        try:
            patched = json.loads(json.dumps(original))
            patched["permanent_type_value_usd"]["creature"] = 0.0
            patched["card_value_weighting"]["max_multiplier"] = 10.0  # deliberately extreme
            se._WEIGHTS = patched
            bracket_cfg = patched["bracket_scaling"]["3"]
            result = se._effective_half_life("creature", bracket_cfg)
            self.assertLessEqual(result, se._half_life_ceiling())
        finally:
            se._WEIGHTS = original

    def test_effective_half_life_feeds_into_a_valid_decay_multiplier(self):
        bracket_cfg = self._bracket_cfg(3)
        for bucket in se.PERMANENT_TYPE_BUCKETS:
            eff = se._effective_half_life(bucket, bracket_cfg)
            decay = se._half_life_decay_multiplier(eff)
            self.assertGreater(decay, 0.0)
            self.assertLess(decay, 1.0)

    def test_disruption_buckets_are_also_covered(self):
        bracket_cfg = self._bracket_cfg(3)
        for bucket in se.DISRUPTION_PERMANENT_TYPE_BUCKETS:
            eff = se._effective_half_life(bucket, bracket_cfg)
            self.assertGreater(eff, 0.0)
            self.assertLessEqual(eff, se._half_life_ceiling())


class AdvanceOpponentStateIntegrationTests(unittest.TestCase):
    """A real advance_opponent_state() run must actually go through
    _effective_half_life (not the old flat impact_mult path) without
    raising or producing nonsensical (negative/NaN) bucket values."""

    def test_passive_value_and_sac_drain_decay_stay_in_bounds_over_many_turns(self):
        import random

        se.reload_weights()
        profile = se.OpponentProfile(strategy="midrange", colors={"B"}, bracket=3)
        state = se.OpponentState()
        rng = random.Random(20260919)
        for _ in range(20):
            se.advance_opponent_state(state, profile, rng, table_size=4)
            for bucket, val in state.passive_value_by_type.items():
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)
            for bucket, val in state.sac_drain_by_type.items():
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)
            for bucket, val in state.disruption_lockout_by_type.items():
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)


if __name__ == "__main__":
    unittest.main()
