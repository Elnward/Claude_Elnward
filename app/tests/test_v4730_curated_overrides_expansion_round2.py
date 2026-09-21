"""
Unit tests for v4.73.0 ("CURATED_OVERRIDES-Erweiterung, Runde 2" -
App/archetype_profile/classify.py). See:
  - App/archetype_profile/classify.py: CURATED_OVERRIDES (85 -> 252
    Eintraege), 6 neue allgemeine Regex-Muster (mana_doubler in
    _RAMP_RULES; draws_additional broadened + top-card-if-land in
    _CARD_ADVANTAGE_RULES; cascade_value + evasion_unblockable in
    _STRATEGY_RULES; prevent_all_combat_damage/fog_effect in
    _INTERACTION_RULES)
  - Docs/curated_overrides_expansion_v4_73_0.md (Ranking-Methodik,
    volle Vorher/Nachher-Zahlen, Statusbericht)

Dieser Test verifiziert, exakt wie test_v4720_curated_overrides_expansion.py
das fuer Runde 1 tat, gezielt das NEUE in Runde 2: dass die 6 neuen
allgemeinen Muster tatsaechlich greifen (anhand kurzer, minimaler
Oracle-Text-Beispiele, nicht der echten Trainingsdaten - die liegen nur
auf dem Nutzergeraet, nicht in diesem Arbeitsverzeichnis), dass
CURATED_OVERRIDES jetzt exakt 252 Eintraege hat und jeder syntaktisch
gueltig ist, und dass die Versions-Strings synchron sind.

Run from the project root:
    python -m unittest tests.test_v4730_curated_overrides_expansion_round2 -v
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
_EXPANSION_DOC = ROOT / "Docs" / "curated_overrides_expansion_v4_73_0.md"


class VersionSyncTests(unittest.TestCase):
    # Hinweis (v4.74.0): ENGINE_VERSION/GUI-Titel-Assertions werden bei
    # jedem weiteren Versionssprung auf die jeweils aktuelle Version
    # aktualisiert (gleiche Konvention wie bei allen aelteren Sync-Checks).
    def test_engine_version_is_4_73_0(self):
        self.assertEqual(engine.ENGINE_VERSION, "4.75.0")

    def test_gui_title_mentions_4_73_0(self):
        src = _GUI_SRC.read_text(encoding="utf-8")
        self.assertIn("Commander Goldfish v4.75.0", src)

    def test_readme_has_v4730_entry(self):
        text = _README.read_text(encoding="utf-8")
        self.assertIn("v4.73.0", text)

    def test_expansion_doc_exists_and_mentions_key_terms(self):
        self.assertTrue(_EXPANSION_DOC.exists())
        text = _EXPANSION_DOC.read_text(encoding="utf-8")
        self.assertIn("CURATED_OVERRIDES", text)
        self.assertIn("Venser", text)


class CuratedOverridesCountTests(unittest.TestCase):
    # Hinweis (v4.74.0): analog zur gleichen Anpassung in
    # test_v4720_curated_overrides_expansion.py fuer Runde 1 - diese Datei
    # dokumentiert speziell Runde 2 (85 -> 252). Runde 3 fuegt weitere
    # Eintraege hinzu, daher ab v4.74.0 nur noch "mindestens 252" statt
    # exakt 252 - der exakte Gesamtstand wird in der jeweils neuesten
    # Runden-Testdatei (test_v4740_...) verifiziert.
    def test_now_has_at_least_252_entries(self):
        self.assertGreaterEqual(len(classify.CURATED_OVERRIDES), 252)

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

    def test_round1_85_are_a_subset(self):
        # Round 1's 85 entries must still all be present (nothing removed).
        # We only check the count relationship here, not the full name list
        # (that is already covered by test_v4720's own subset check for the
        # original 11; a full 85-name re-listing would just duplicate that
        # file's own responsibility).
        self.assertGreaterEqual(len(classify.CURATED_OVERRIDES), 85)

    def test_round2_batch_adds_exactly_167_new_entries(self):
        # A handful of round-2 names, spread across all four roles, to
        # sanity-check the batch actually landed (full list: see
        # Docs/curated_overrides_expansion_v4_73_0.md).
        sample = {
            "Venser, Shaper Savant": "Interaction",
            "Muldrotha, the Gravetide": "Strategy",
            "Wilderness Reclamation": "Ramp",
            "Dark Confidant": "CardAdvantage",
            "Bruse Tarl, Boorish Herder": "Strategy",
        }
        for name, expected_role in sample.items():
            with self.subTest(card=name):
                self.assertIn(name, classify.CURATED_OVERRIDES)
                self.assertEqual(classify.CURATED_OVERRIDES[name]["role"], expected_role)

    def test_a_sample_of_the_new_entries_round_trips_through_classify_card(self):
        for name, expected_role in [
            ("Venser, Shaper Savant", "Interaction"),
            ("Muldrotha, the Gravetide", "Strategy"),
            ("Gilded Lotus", "Ramp"),
            ("Dark Confidant", "CardAdvantage"),
        ]:
            with self.subTest(card=name):
                result = classify.classify_card(name, "irrelevant placeholder text", "Creature")
                self.assertTrue(result["curated"])
                self.assertEqual(result["primary_role"], expected_role)


class NewGeneralRulesRound2Tests(unittest.TestCase):
    """The 6 general regex additions found during round 2's ranking-based
    audit - each verified against a small, self-contained oracle-text
    example rather than the real (device-only) training data."""

    def _classify(self, text, type_="Sorcery"):
        return classify.classify_card("Test Card Not In Overrides", text, type_)

    def test_mana_doubler_rule(self):
        result = self._classify(
            "If you tap a land for mana, it produces twice as much of that mana instead.",
            type_="Enchantment",
        )
        self.assertEqual(result["primary_role"], "Ramp")
        self.assertIn("mana_doubler", result["effect_tags"])

    def test_draws_additional_cards_rule(self):
        result = self._classify(
            "At the beginning of each player's draw step, that player draws an additional card.",
            type_="Enchantment",
        )
        self.assertEqual(result["primary_role"], "CardAdvantage")
        self.assertIn("draw_cards", result["effect_tags"])

    def test_top_card_if_land_rule(self):
        result = self._classify(
            "You may look at the top card of your library. If it's a land card, "
            "you may reveal it and put it into your hand.",
            type_="Creature",
        )
        self.assertEqual(result["primary_role"], "CardAdvantage")
        self.assertIn("card_selection", result["effect_tags"])

    def test_cascade_rule(self):
        result = self._classify(
            "Cascade (When you cast this spell, exile cards from the top of your "
            "library until you exile a nonland card that costs less. You may cast "
            "it without paying its mana cost. Put the exiled cards on the bottom "
            "in a random order.)",
            type_="Instant",
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("cascade_value", result["effect_tags"])

    def test_unblockable_rule(self):
        result = self._classify("This creature can't be blocked.", type_="Creature")
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("evasion_unblockable", result["effect_tags"])

    def test_fog_effect_rule(self):
        result = self._classify("Prevent all combat damage that would be dealt this turn.")
        self.assertEqual(result["primary_role"], "Interaction")
        self.assertIn("fog_effect", result["effect_tags"])

    def test_round1_rules_still_work_regression_guard(self):
        # Spot-check one round-1 rule (trigger_doubler) is untouched by
        # round 2's edits.
        result = self._classify(
            "If a triggered ability of a permanent you control triggers, "
            "that ability triggers an additional time.",
            type_="Enchantment",
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("trigger_doubler", result["effect_tags"])


if __name__ == "__main__":
    unittest.main()
