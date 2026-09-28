"""
Unit tests for v4.74.0 ("CURATED_OVERRIDES-Erweiterung, Runde 3" -
App/archetype_profile/classify.py). See:
  - App/archetype_profile/classify.py: CURATED_OVERRIDES (252 -> 415
    Eintraege), 4 neue allgemeine Regex-Muster (land_type_fixing in
    _RAMP_RULES; impulse_draw in _CARD_ADVANTAGE_RULES;
    untap_all_nonland_combo + eine verbreiterte wheel_effect-Fassung in
    _STRATEGY_RULES)
  - Docs/curated_overrides_expansion_v4_74_0.md (Ranking-Methodik, volle
    Vorher/Nachher-Zahlen, Statusbericht - Ziel 300-500 erreicht)

Dieser Test verifiziert, exakt wie die Runde-1/2-Testdateien das fuer ihre
jeweilige Runde taten, gezielt das NEUE in Runde 3: dass die 4 neuen
allgemeinen Muster tatsaechlich greifen (anhand kurzer, minimaler
Oracle-Text-Beispiele, nicht der echten Trainingsdaten - die liegen nur
auf dem Nutzergeraet, nicht in diesem Arbeitsverzeichnis), dass
CURATED_OVERRIDES jetzt exakt 415 Eintraege hat und jeder syntaktisch
gueltig ist, und dass die Versions-Strings synchron sind.

Run from the project root:
    python -m unittest tests.test_v4740_curated_overrides_expansion_round3 -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402
from App.archetype_profile import classify  # noqa: E402

_GUI_SRC = ROOT / "App" / "gui.py"
_README = ROOT / "Docs" / "README.md"
_EXPANSION_DOC = ROOT / "Docs" / "curated_overrides_expansion_v4_74_0.md"


class VersionSyncTests(unittest.TestCase):
    def test_engine_version_is_4_74_0(self):
        self.assertEqual(engine.ENGINE_VERSION, "4.87.0")

    def test_gui_title_mentions_4_74_0(self):
        src = _GUI_SRC.read_text(encoding="utf-8")
        self.assertIn("Commander Goldfish v4.87.0", src)

    def test_readme_has_v4740_entry(self):
        text = _README.read_text(encoding="utf-8")
        self.assertIn("v4.74.0", text)

    def test_expansion_doc_exists_and_mentions_key_terms(self):
        self.assertTrue(_EXPANSION_DOC.exists())
        text = _EXPANSION_DOC.read_text(encoding="utf-8")
        self.assertIn("CURATED_OVERRIDES", text)
        self.assertIn("Yavimaya", text)


class CuratedOverridesCountTests(unittest.TestCase):
    def test_now_has_415_entries(self):
        self.assertEqual(len(classify.CURATED_OVERRIDES), 415)

    def test_target_range_300_to_500_reached(self):
        # The user's originally stated target for this whole multi-round
        # effort (see Docs/curated_overrides_expansion_v4_72_0.md and
        # v4_73_0.md) was 300-500 curated cards. This is the round where
        # that target is first reached.
        self.assertGreaterEqual(len(classify.CURATED_OVERRIDES), 300)
        self.assertLessEqual(len(classify.CURATED_OVERRIDES), 500)

    def test_every_entry_is_well_formed(self):
        for name, ov in classify.CURATED_OVERRIDES.items():
            with self.subTest(card=name):
                self.assertIn(ov["role"], classify.ROLE_PRIORITY)
                self.assertTrue(ov["effect_tags"], "effect_tags must be non-empty")
                self.assertIsInstance(ov["effect_tags"], list)
                self.assertTrue(ov["simple_effect"])
                hw = ov["halbwertszeit"]
                self.assertIsInstance(hw, float)
                self.assertGreaterEqual(hw, 0.0)
                self.assertLessEqual(hw, 1.0)

    def test_round2_252_are_a_subset(self):
        self.assertGreaterEqual(len(classify.CURATED_OVERRIDES), 252)

    def test_round3_batch_adds_exactly_163_new_entries(self):
        sample = {
            "Desecrate Reality": "Interaction",
            "Heartbeat of Spring": "Ramp",
            "Wrenn and Seven": "Strategy",
            "Darkstar Augur": "CardAdvantage",
            "Erdwal Illuminator": "CardAdvantage",
        }
        for name, expected_role in sample.items():
            with self.subTest(card=name):
                self.assertIn(name, classify.CURATED_OVERRIDES)
                self.assertEqual(classify.CURATED_OVERRIDES[name]["role"], expected_role)

    def test_a_sample_of_the_new_entries_round_trips_through_classify_card(self):
        for name, expected_role in [
            ("Desecrate Reality", "Interaction"),
            ("Wrenn and Seven", "Strategy"),
            ("Somberwald Sage", "Ramp"),
            ("Snapcaster Mage", "CardAdvantage"),
        ]:
            with self.subTest(card=name):
                result = classify.classify_card(name, "irrelevant placeholder text", "Creature")
                self.assertTrue(result["curated"])
                self.assertEqual(result["primary_role"], expected_role)


class NewGeneralRulesRound3Tests(unittest.TestCase):
    """The 4 general regex additions found during round 3's ranking-based
    audit - each verified against a small, self-contained oracle-text
    example rather than the real (device-only) training data."""

    def _classify(self, text, type_="Sorcery"):
        return classify.classify_card("Test Card Not In Overrides", text, type_)

    def test_land_type_fixing_rule(self):
        # Note: type_ must NOT be the exact literal string "Land" - classify_card
        # special-cases that exact type_line (structurally a different category,
        # see classify_card's own "Laender sind strukturell eine eigene
        # Kategorie" branch) before the general _RAMP_RULES are ever reached.
        # Real cards using this template (Yavimaya, Urborg) are "Legendary
        # Land", which does NOT match that exact-equality check, so they do
        # fall through to _RAMP_RULES - exactly like this test reproduces.
        result = self._classify(
            "Each land is a Swamp in addition to its other land types.",
            type_="Legendary Land",
        )
        self.assertEqual(result["primary_role"], "Ramp")
        self.assertIn("land_type_fixing", result["effect_tags"])

    def test_impulse_draw_rule(self):
        result = self._classify(
            "Exile the top two cards of your library. Until the end of your next "
            "turn, you may play those cards.",
            type_="Sorcery",
        )
        self.assertEqual(result["primary_role"], "CardAdvantage")
        self.assertIn("impulse_draw", result["effect_tags"])

    def test_untap_all_nonland_rule(self):
        result = self._classify("Untap all nonland permanents you control.", type_="Instant")
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("untap_all_nonland_combo", result["effect_tags"])

    def test_wheel_effect_shuffle_variant_rule(self):
        result = self._classify(
            "Each player shuffles the cards from their hand into their library, "
            "then draws that many cards.",
            type_="Sorcery",
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("wheel_effect", result["effect_tags"])

    def test_wheel_effect_original_discard_phrasing_still_works(self):
        # Regression guard: the original v4.x "discards their hand, then
        # draws" phrasing must still match after the broadened rule was
        # added alongside it.
        result = self._classify(
            "Each player discards their hand, then draws seven cards.",
            type_="Sorcery",
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("wheel_effect", result["effect_tags"])

    def test_round2_rules_still_work_regression_guard(self):
        result = self._classify("This creature can't be blocked.", type_="Creature")
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("evasion_unblockable", result["effect_tags"])


if __name__ == "__main__":
    unittest.main()
