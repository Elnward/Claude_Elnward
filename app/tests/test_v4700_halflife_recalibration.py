"""
Unit tests for v4.70.0 ("Halbwertszeiten-Recherche" - empirically deriving
permanent_type_half_life_turns). See:
  - Data/Models/opponent_state_weights.json (version "1.8",
    permanent_type_half_life_turns, guardrails.half_life_ceiling_turns)
  - App/opponent_model/state_equation.py's module docstring "v4.70.0" section
    and _permanent_type_half_life/_half_life_ceiling
  - App/archetype_profile/classify.py's new removal_target_types() function
  - Docs/opponent_model_calibration_v4_70_0.md (full hand-sampling
    methodology, raw frequency table, price-weighting formula, and the land
    half-life-ceiling policy decision)

This version does not re-verify anything already covered by
test_v4670_opponent_recalibration.py / test_v4690_deconfounded_recalibration.py
(those two files were updated in place for the new version/engine/GUI
strings) - it targets what is actually NEW in v4.70.0: removal_target_types()
itself, the new permanent_type_half_life_turns values, and the new
half_life_ceiling_turns guardrail.

Run from the project root:
    python -m unittest tests.test_v4700_halflife_recalibration -v
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
from App.archetype_profile.classify import removal_target_types, classify_card  # noqa: E402

_WEIGHTS_PATH = ROOT / "Data" / "Models" / "opponent_state_weights.json"
_CALIBRATION_DOC = ROOT / "Docs" / "opponent_model_calibration_v4_70_0.md"
_STATE_EQ_SRC = ROOT / "App" / "opponent_model" / "state_equation.py"
_GUI_SRC = ROOT / "App" / "gui.py"
_README = ROOT / "Docs" / "README.md"


def _load_weights():
    return json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))


class VersionSyncTests(unittest.TestCase):
    """The version string, ENGINE_VERSION, GUI title, module docstring, and
    README changelog must all agree - the project's standing convention."""

    def test_weights_version_is_1_8(self):
        # "1.8" was v4.70.0's own version string; v4.71.0 bumped it further
        # to "1.9" (Wertigkeits-Funktion - see test_v4710_value_weighting.py)
        # - updated in place here per the project's standing convention.
        self.assertEqual(_load_weights()["version"], "1.9")

    def test_engine_version_is_4_70_0(self):
        # v4.73.0 bumped ENGINE_VERSION further - updated in place here per
        # the project's standing convention (see test_v4700's own comment above).
        self.assertEqual(engine.ENGINE_VERSION, "4.87.0")

    def test_gui_title_mentions_4_70_0(self):
        src = _GUI_SRC.read_text(encoding="utf-8")
        self.assertIn("Commander Goldfish v4.87.0", src)

    def test_state_equation_docstring_has_v4700_section(self):
        src = _STATE_EQ_SRC.read_text(encoding="utf-8")
        self.assertIn("v4.70.0", src)
        self.assertIn("removal_target_types", src)
        self.assertIn("half_life_ceiling_turns", src)

    def test_calibration_doc_exists_and_mentions_hand_sampling(self):
        self.assertTrue(_CALIBRATION_DOC.exists())
        text = _CALIBRATION_DOC.read_text(encoding="utf-8")
        self.assertIn("removal_target_types", text)
        self.assertIn("63.400", text)  # simulated hand count (German thousands dot)

    def test_readme_has_v4700_entry(self):
        text = _README.read_text(encoding="utf-8")
        self.assertIn("v4.70.0", text)


class RemovalTargetTypesTests(unittest.TestCase):
    """removal_target_types() on representative real-card oracle text."""

    def test_creature_removal(self):
        text = "Destroy target creature. It can't be regenerated."
        self.assertEqual(removal_target_types(text), frozenset({"creature"}))

    def test_artifact_removal(self):
        text = "Destroy target artifact."
        self.assertEqual(removal_target_types(text), frozenset({"artifact"}))

    def test_enchantment_removal(self):
        text = "Destroy target enchantment."
        self.assertEqual(removal_target_types(text), frozenset({"enchantment"}))

    def test_planeswalker_removal(self):
        text = "Destroy target planeswalker."
        self.assertEqual(removal_target_types(text), frozenset({"planeswalker"}))

    def test_land_destruction(self):
        text = "Destroy target land."
        self.assertEqual(removal_target_types(text), frozenset({"land"}))

    def test_sacrifice_a_land_counts_as_land_removal(self):
        text = "Target player sacrifices a land."
        self.assertEqual(removal_target_types(text), frozenset({"land"}))

    def test_multi_target_or_enumeration(self):
        text = "Destroy target creature, artifact, or enchantment."
        self.assertEqual(
            removal_target_types(text),
            frozenset({"creature", "artifact", "enchantment"}),
        )

    def test_nonland_permanent_expands_to_all_four_nonland_types(self):
        text = "Destroy target nonland permanent."
        self.assertEqual(
            removal_target_types(text),
            frozenset({"creature", "artifact", "enchantment", "planeswalker"}),
        )

    def test_arbitrary_non_qualifier_prefix_doom_blade_style(self):
        # Doom Blade-style: "Destroy target nonblack creature."
        text = "Destroy target nonblack creature. It can't be regenerated."
        self.assertEqual(removal_target_types(text), frozenset({"creature"}))

    def test_board_wipe_destroy_all_creatures(self):
        text = "Destroy all creatures."
        self.assertEqual(removal_target_types(text), frozenset({"creature"}))

    def test_literal_x_x_toxic_deluge_style(self):
        text = "Each creature gets -X/-X until end of turn, where X is the amount of life paid this way."
        self.assertEqual(removal_target_types(text), frozenset({"creature"}))

    def test_chaos_warp_reversed_word_order(self):
        # Chaos Warp-style: "target X" appears BEFORE the verb, not after -
        # a separate regex pattern in removal_target_types handles this.
        text = "The owner of target permanent shuffles it into their library."
        result = removal_target_types(text)
        self.assertEqual(result, frozenset({"creature", "artifact", "enchantment", "planeswalker"}))

    def test_chaos_warp_reversed_word_order_single_type(self):
        text = "The owner of target artifact shuffles it into their library."
        self.assertEqual(removal_target_types(text), frozenset({"artifact"}))

    def test_bounce_effect(self):
        text = "Return target creature to its owner's hand."
        self.assertEqual(removal_target_types(text), frozenset({"creature"}))

    def test_bounce_effect_with_qualifier_gap_cyclonic_rift_style(self):
        text = "Return target nonland permanent you don't control to its owner's hand."
        self.assertEqual(
            removal_target_types(text),
            frozenset({"creature", "artifact", "enchantment", "planeswalker"}),
        )

    def test_damage_to_target_creature(self):
        text = "This spell deals 4 damage to target creature."
        self.assertEqual(removal_target_types(text), frozenset({"creature"}))

    def test_damage_to_any_target_includes_planeswalker_but_not_artifact(self):
        text = "This spell deals 3 damage to any target."
        result = removal_target_types(text)
        self.assertIn("creature", result)
        self.assertIn("planeswalker", result)
        self.assertNotIn("artifact", result)
        self.assertNotIn("enchantment", result)

    def test_counterspell_is_excluded(self):
        # Counters a spell before it resolves - never removes an already-
        # resolved permanent, so must NOT be treated as removal here.
        text = "Counter target spell unless its controller pays {3}."
        self.assertEqual(removal_target_types(text), frozenset())

    def test_no_removal_text_returns_empty(self):
        text = "Whenever a creature enters the battlefield under your control, draw a card."
        self.assertEqual(removal_target_types(text), frozenset())

    def test_non_string_input_is_safe(self):
        self.assertEqual(removal_target_types(None), frozenset())
        self.assertEqual(removal_target_types(""), frozenset())

    def test_classify_card_exposes_removal_targets_additively(self):
        result = classify_card("Test Doom Blade", "Destroy target nonblack creature.", "Instant")
        self.assertIn("removal_targets", result)
        self.assertEqual(result["removal_targets"], ["creature"])
        # Existing keys must still be present - additive, not replacing.
        self.assertIn("primary_role", result)
        self.assertIn("effect_tags", result)
        self.assertIn("simple_effect", result)


class HalfLifeValueTests(unittest.TestCase):
    """The new, empirically-derived permanent_type_half_life_turns values."""

    @classmethod
    def setUpClass(cls):
        cls.table = _load_weights()["permanent_type_half_life_turns"]

    def test_creature_half_life(self):
        self.assertAlmostEqual(self.table["creature"], 4.2, places=3)

    def test_artifact_half_life(self):
        self.assertAlmostEqual(self.table["artifact"], 7.5, places=3)

    def test_enchantment_half_life(self):
        self.assertAlmostEqual(self.table["enchantment"], 8.0, places=3)

    def test_planeswalker_half_life(self):
        self.assertAlmostEqual(self.table["planeswalker"], 8.4, places=3)

    def test_land_half_life_capped_at_ceiling(self):
        self.assertAlmostEqual(self.table["land"], 30, places=3)

    def test_artifact_now_shorter_than_planeswalker(self):
        # The v4.40.0 ordering had artifact(7) > planeswalker(6), which the
        # hand-sampling frequency evidence (artifacts answered more often
        # than planeswalkers: 19.52% vs 16.93%) showed was backwards.
        self.assertLess(self.table["artifact"], self.table["planeswalker"])

    def test_creature_remains_shortest(self):
        non_land = ["creature", "artifact", "enchantment", "planeswalker"]
        self.assertEqual(min(non_land, key=lambda t: self.table[t]), "creature")

    def test_land_remains_longest(self):
        numeric = {k: v for k, v in self.table.items() if k != "_comment"}
        self.assertEqual(max(numeric, key=lambda t: numeric[t]), "land")


class GuardrailCeilingTests(unittest.TestCase):
    """guardrails.half_life_ceiling_turns is wired into
    state_equation._permanent_type_half_life for ALL five permanent types,
    not just land - see the module docstring's v4.70.0 section."""

    def setUp(self):
        se.reload_weights()
        self.addCleanup(se.reload_weights)

    def test_ceiling_value_from_json(self):
        self.assertAlmostEqual(se._half_life_ceiling(), 30.0, places=3)

    def test_permanent_type_half_life_reads_current_creature_value(self):
        self.assertAlmostEqual(se._permanent_type_half_life("creature"), 4.2, places=3)

    def test_permanent_type_half_life_reads_current_land_value(self):
        self.assertAlmostEqual(se._permanent_type_half_life("land"), 30.0, places=3)

    def test_ceiling_is_enforced_even_if_a_future_edit_sets_a_larger_value(self):
        """Belt-and-suspenders: if some future weights edit accidentally sets
        a permanent_type_half_life_turns entry above the ceiling again (the
        exact mistake this guardrail exists to prevent - see the raw ~64.7
        turn land extrapolation discussed in the v4.70.0 docstring/note),
        _permanent_type_half_life must still clamp it, not just the JSON
        author's discipline."""
        original = se._WEIGHTS
        try:
            patched = json.loads(json.dumps(original))  # deep copy
            patched["permanent_type_half_life_turns"]["land"] = 999.0
            se._WEIGHTS = patched
            self.assertAlmostEqual(se._permanent_type_half_life("land"), 30.0, places=3)
        finally:
            se._WEIGHTS = original

    def test_missing_ceiling_key_falls_back_to_30(self):
        original = se._WEIGHTS
        try:
            patched = json.loads(json.dumps(original))
            del patched["guardrails"]["half_life_ceiling_turns"]
            patched["permanent_type_half_life_turns"]["land"] = 999.0
            se._WEIGHTS = patched
            self.assertAlmostEqual(se._permanent_type_half_life("land"), 30.0, places=3)
        finally:
            se._WEIGHTS = original


if __name__ == "__main__":
    unittest.main()
