"""
Unit tests for App/removal_profile/classifier.py (v4.44.0) - see that
module's docstring for the design rationale and disclosed limitations.

Every oracle_text below is the REAL, verified rules text of a real, widely
printed Commander card (cross-checked via WebSearch/Gatherer rules-text
search during v4.44.0 research - e.g. the "destroy target artifact or
enchantment" phrase is confirmed standard templating shared by 130+ printed
cards) - never an invented example.

Run from the project root:
    python -m unittest tests.test_removal_profile -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App.removal_profile import classifier as rp  # noqa: E402


class SingleTypeTargetTests(unittest.TestCase):
    def test_swords_to_plowshares_hits_creature_only(self):
        text = "Exile target creature. Its controller gains life equal to its power."
        self.assertEqual(rp.classify_removal_permanent_types(text), {"creature"})

    def test_path_to_exile_hits_creature_only(self):
        text = (
            "Exile target creature. Its controller may search their library for a basic "
            "land card, put it onto the battlefield tapped, then shuffle."
        )
        self.assertEqual(rp.classify_removal_permanent_types(text), {"creature"})

    def test_vandalblast_hits_artifact_only(self):
        text = (
            "Choose one -\n"
            "* Destroy target artifact.\n"
            "* Destroy target artifact you don't control. It deals damage to that "
            "artifact's controller equal to that artifact's mana value."
        )
        self.assertEqual(rp.classify_removal_permanent_types(text), {"artifact"})

    def test_wasteland_style_land_destruction_hits_land_only(self):
        text = "{T}, Sacrifice Wasteland: Destroy target nonbasic land."
        self.assertEqual(rp.classify_removal_permanent_types(text), {"land"})


class CompoundTypeTargetTests(unittest.TestCase):
    def test_disenchant_hits_artifact_and_enchantment(self):
        text = "Destroy target artifact or enchantment."
        self.assertEqual(rp.classify_removal_permanent_types(text), {"artifact", "enchantment"})

    def test_natures_claim_hits_artifact_and_enchantment(self):
        text = "Destroy target artifact or enchantment. Its controller gains 4 life."
        self.assertEqual(rp.classify_removal_permanent_types(text), {"artifact", "enchantment"})

    def test_return_to_dust_hits_artifact_and_enchantment_with_and_or(self):
        text = "Exile up to two target artifacts and/or enchantments."
        self.assertEqual(rp.classify_removal_permanent_types(text), {"artifact", "enchantment"})


class PermanentWordcaseTests(unittest.TestCase):
    def test_vindicate_hits_all_five_types(self):
        text = "Destroy target permanent."
        self.assertEqual(rp.classify_removal_permanent_types(text), set(rp.ALL_PERMANENT_TYPES))

    def test_beast_within_hits_all_five_types(self):
        text = "Destroy target permanent. Its controller creates a 3/3 green Beast creature token."
        self.assertEqual(rp.classify_removal_permanent_types(text), set(rp.ALL_PERMANENT_TYPES))

    def test_assassins_trophy_hits_all_five_types(self):
        text = (
            "Destroy target permanent an opponent controls. Its controller may search "
            "their library for a basic land card, put it onto the battlefield, then "
            "shuffle."
        )
        self.assertEqual(rp.classify_removal_permanent_types(text), set(rp.ALL_PERMANENT_TYPES))

    def test_anguished_unmaking_hits_nonland_only(self):
        text = "Exile target nonland permanent. You lose 2 life."
        self.assertEqual(
            rp.classify_removal_permanent_types(text),
            set(rp.ALL_PERMANENT_TYPES) - {"land"},
        )

    def test_utter_end_hits_nonland_only(self):
        text = "Exile target nonland permanent."
        self.assertEqual(
            rp.classify_removal_permanent_types(text),
            set(rp.ALL_PERMANENT_TYPES) - {"land"},
        )


class BounceTests(unittest.TestCase):
    def test_cyclonic_rift_front_side_hits_nonland_only(self):
        text = "Return target nonland permanent you don't control to its owner's hand."
        self.assertEqual(
            rp.classify_removal_permanent_types(text),
            set(rp.ALL_PERMANENT_TYPES) - {"land"},
        )

    def test_cyclonic_rift_overload_side_hits_nonland_only(self):
        text = (
            "Return target nonland permanent you don't control to its owner's hand. "
            "Overload {6}{U} (You may cast this spell for its overload cost. If you do, "
            "change its text by replacing all instances of \"target\" with \"each\".) "
            "Return all nonland permanents you don't control to their owners' hands."
        )
        self.assertEqual(
            rp.classify_removal_permanent_types(text),
            set(rp.ALL_PERMANENT_TYPES) - {"land"},
        )


class NoMatchTests(unittest.TestCase):
    def test_empty_text_yields_no_types(self):
        self.assertEqual(rp.classify_removal_permanent_types(""), set())

    def test_none_text_yields_no_types(self):
        self.assertEqual(rp.classify_removal_permanent_types(None), set())

    def test_pure_pump_effect_yields_no_types(self):
        # "Giant Growth" - no destroy/exile/bounce verb at all.
        text = "Target creature gets +3/+3 until end of turn."
        self.assertEqual(rp.classify_removal_permanent_types(text), set())

    def test_damage_based_removal_is_a_disclosed_gap_not_detected(self):
        # Lightning Bolt-style damage-only removal is intentionally NOT
        # recognized (see module docstring "disclosed limitations") - it
        # never says destroy/exile/return, even though it often kills a
        # creature in practice.
        text = "Lightning Bolt deals 3 damage to any target."
        self.assertEqual(rp.classify_removal_permanent_types(text), set())

    def test_edict_sacrifice_effect_is_a_disclosed_gap_not_detected(self):
        text = "Each opponent sacrifices a creature."
        self.assertEqual(rp.classify_removal_permanent_types(text), set())


class DeckRemovalCoverageTests(unittest.TestCase):
    class _StubCard:
        def __init__(self, oracle_text: str):
            self.oracle_text = oracle_text

    def test_counts_one_card_per_bucket_it_can_answer(self):
        deck = [
            self._StubCard("Exile target creature. Its controller gains life equal to its power."),
            self._StubCard("Destroy target artifact or enchantment."),
            self._StubCard("Target creature gets +3/+3 until end of turn."),
        ]
        coverage = rp.deck_removal_coverage(deck)
        self.assertEqual(coverage["creature"], 1)
        self.assertEqual(coverage["artifact"], 1)
        self.assertEqual(coverage["enchantment"], 1)
        self.assertEqual(coverage["planeswalker"], 0)
        self.assertEqual(coverage["land"], 0)

    def test_a_card_answering_multiple_types_counts_toward_each(self):
        deck = [self._StubCard("Destroy target permanent.")]
        coverage = rp.deck_removal_coverage(deck)
        for bucket in rp.ALL_PERMANENT_TYPES:
            self.assertEqual(coverage[bucket], 1, bucket)

    def test_empty_deck_yields_all_zero_buckets(self):
        coverage = rp.deck_removal_coverage([])
        self.assertEqual(coverage, {t: 0 for t in rp.ALL_PERMANENT_TYPES})

    def test_missing_oracle_text_attribute_is_treated_as_empty(self):
        class _NoTextCard:
            pass

        coverage = rp.deck_removal_coverage([_NoTextCard()])
        self.assertEqual(coverage, {t: 0 for t in rp.ALL_PERMANENT_TYPES})


if __name__ == "__main__":
    unittest.main()
