"""
Unit tests for v4.72.0 ("CURATED_OVERRIDES-Erweiterung, Runde 1" -
App/archetype_profile/classify.py). See:
  - App/archetype_profile/classify.py: CURATED_OVERRIDES (11 -> 85 Eintraege),
    5 neue allgemeine _RAMP_RULES/_STRATEGY_RULES-Muster
    (land_recursion, trigger_doubler, clone_effect, extra_untap_steps,
    damage_multiplier) plus eine erweiterte graveyard_recursion-Regex
  - Docs/curated_overrides_expansion_v4_72_0.md (Ranking-Methodik, volle
    Vorher/Nachher-Zahlen, Statusbericht)

Dieser Test verifiziert NICHT den bestehenden Regel-Engine-Kern (siehe
dafuer die aelteren archetype_profile-Tests) - er zielt gezielt auf das
NEUE in v4.72.0: dass die 5 neuen allgemeinen Muster tatsaechlich greifen
(anhand kurzer, minimaler Oracle-Text-Beispiele, nicht der echten
Trainingsdaten - die liegen nur auf dem Nutzergeraet, nicht in diesem
Arbeitsverzeichnis), dass CURATED_OVERRIDES jetzt 85 Eintraege hat und
jeder syntaktisch gueltig ist (role/effect_tags/simple_effect/
halbwertszeit vorhanden, role aus ROLE_PRIORITY, halbwertszeit in [0,1]),
und dass die Versions-Strings synchron sind.

Run from the project root:
    python -m unittest tests.test_v4720_curated_overrides_expansion -v
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
_EXPANSION_DOC = ROOT / "Docs" / "curated_overrides_expansion_v4_72_0.md"


class VersionSyncTests(unittest.TestCase):
    # Hinweis (v4.73.0): ENGINE_VERSION/GUI-Titel-Assertions werden bei
    # jedem Versionssprung auf die jeweils aktuelle Version aktualisiert
    # (Projekt-Konvention: "update in place, don't rename" fuer diese
    # Sync-Checks) - der Testdatei-Name bleibt trotzdem v4720, da er das
    # Feature (CURATED_OVERRIDES-Erweiterung Runde 1) benennt, nicht die
    # jeweils aktuellste Engine-Version.
    def test_engine_version_is_4_73_0(self):
        self.assertEqual(engine.ENGINE_VERSION, "4.75.0")

    def test_gui_title_mentions_4_73_0(self):
        src = _GUI_SRC.read_text(encoding="utf-8")
        self.assertIn("Commander Goldfish v4.75.0", src)

    def test_readme_has_v4720_entry(self):
        text = _README.read_text(encoding="utf-8")
        self.assertIn("v4.72.0", text)

    def test_expansion_doc_exists_and_mentions_key_terms(self):
        self.assertTrue(_EXPANSION_DOC.exists())
        text = _EXPANSION_DOC.read_text(encoding="utf-8")
        self.assertIn("CURATED_OVERRIDES", text)
        self.assertIn("Deflecting Swat", text)


class CuratedOverridesCountTests(unittest.TestCase):
    # Hinweis (v4.73.0): diese Datei dokumentiert speziell Runde 1 (11 ->
    # 85). Spaetere Runden fuegen weitere Eintraege hinzu, daher pruefen
    # die Zaehl-Assertions hier ab v4.73.0 nur noch "mindestens 85"
    # (Untermenge), statt exakt 85 - der exakte Gesamtstand wird in der
    # jeweils neuesten Runden-Testdatei (z.B. test_v4730_...) verifiziert.
    def test_now_has_at_least_85_entries(self):
        self.assertGreaterEqual(len(classify.CURATED_OVERRIDES), 85)

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

    def test_new_batch_does_not_collide_with_the_original_11(self):
        original_11 = {
            "Rhystic Study", "Smothering Tithe", "Mystic Remora", "Esper Sentinel",
            "Cyclonic Rift", "Sol Ring", "Demonic Tutor", "Swords to Plowshares",
            "Dockside Extortionist", "Skullclamp", "Toxic Deluge",
        }
        self.assertTrue(original_11.issubset(classify.CURATED_OVERRIDES.keys()))
        self.assertGreaterEqual(len(classify.CURATED_OVERRIDES) - len(original_11), 74)

    def test_a_sample_of_the_new_entries_round_trips_through_classify_card(self):
        # classify_card must return curated=True and the exact role we set,
        # regardless of what oracle_text/type_ we hand it (a curated
        # override always wins over the regex rule engine).
        for name, expected_role in [
            ("Deflecting Swat", "Interaction"),
            ("Craterhoof Behemoth", "Strategy"),
            ("Azusa, Lost but Seeking", "Ramp"),
            ("Sylvan Library", "CardAdvantage"),
        ]:
            with self.subTest(card=name):
                result = classify.classify_card(name, "irrelevant placeholder text", "Creature")
                self.assertTrue(result["curated"])
                self.assertEqual(result["primary_role"], expected_role)


class NewGeneralRulesTests(unittest.TestCase):
    """The 5 general regex additions found during the ranking-based audit -
    each verified against a small, self-contained oracle-text example
    rather than the real (device-only) training data."""

    def _classify(self, text, type_="Artifact"):
        return classify.classify_card("Test Card Not In Overrides", text, type_)

    def test_land_recursion_rule(self):
        result = self._classify("You may play lands from your graveyard.", type_="Creature")
        self.assertEqual(result["primary_role"], "Ramp")
        self.assertIn("land_recursion", result["effect_tags"])

    def test_trigger_doubler_rule(self):
        result = self._classify(
            "If a triggered ability of a permanent you control triggers, "
            "that ability triggers an additional time."
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("trigger_doubler", result["effect_tags"])

    def test_clone_effect_rule(self):
        result = self._classify(
            "You may have this artifact enter as a copy of any artifact on the battlefield."
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("clone_effect", result["effect_tags"])

    def test_extra_untap_steps_rule(self):
        result = self._classify(
            "Untap all artifacts you control during each other player's untap step."
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("extra_untap_steps", result["effect_tags"])

    def test_damage_multiplier_rule(self):
        result = self._classify(
            "If a source you control would deal damage to an opponent or a "
            "permanent an opponent controls, it deals double that damage instead."
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("damage_multiplier", result["effect_tags"])

    def test_graveyard_recursion_now_covers_the_mana_value_qualifier_phrasing(self):
        # This is the exact phrasing that broke the OLD regex (Sun Titan-
        # style templating: "card with mana value N or less from your
        # graveyard to the battlefield" - the qualifier clause used to sit
        # between "card" and "from", which the old pattern required to be
        # adjacent).
        result = self._classify(
            "Whenever this creature enters or attacks, you may return target "
            "permanent card with mana value 3 or less from your graveyard to "
            "the battlefield.",
            type_="Creature",
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("graveyard_recursion", result["effect_tags"])

    def test_graveyard_recursion_still_covers_the_old_simple_phrasing(self):
        # Regression guard: the qualifier group is optional, so the
        # original (pre-v4.72.0) simple phrasing must still match.
        result = self._classify(
            "Return target creature card from your graveyard to your hand.",
            type_="Instant",
        )
        self.assertEqual(result["primary_role"], "Strategy")
        self.assertIn("graveyard_recursion", result["effect_tags"])


if __name__ == "__main__":
    unittest.main()
