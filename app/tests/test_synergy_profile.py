"""
Unit tests for App.synergy_profile.classifier (v4.46.0) - see that module's
docstring, Docs/opponent_model_orzhov_deep_dive_v4_45_0.md and
Docs/opponent_model_moxfield_methodology_v4_46_0.md for the research this
classifier operationalizes.

All oracle text below is REAL, verified via WebSearch/WebFetch during
v4.46.0 research (Soul Warden, Sanguine Bond, Vito Thorn of the Dusk Rose,
Cliffhaven Vampire) - never invented, consistent with this project's
evidence-over-invention convention.

Run from the project root:
    python -m unittest tests.test_synergy_profile -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402
from App.synergy_profile import classifier  # noqa: E402

SOUL_WARDEN_TEXT = (
    "Whenever another creature enters the battlefield under your control, "
    "you gain 1 life."
)
SANGUINE_BOND_TEXT = "Whenever you gain life, target opponent loses that much life."
VITO_TEXT = (
    "Whenever you gain life, an opponent of your choice loses that much life.\n"
    "{3}{B}{B}: Creatures you control gain lifelink until end of turn."
)
CLIFFHAVEN_VAMPIRE_TEXT = "Flying\nWhenever you gain life, each opponent loses 1 life."
EXQUISITE_BLOOD_TEXT = "Whenever an opponent loses life, you gain that much life."


def _card(name: str, oracle_text: str, colors: set) -> engine.Card:
    return engine.Card(name=name, oracle_text=oracle_text, color_identity=set(colors))


class ClassifyLifegainRoleTests(unittest.TestCase):
    def test_soul_warden_is_a_source(self):
        self.assertEqual(classifier.classify_lifegain_role(SOUL_WARDEN_TEXT), "source")

    def test_sanguine_bond_is_a_payoff(self):
        self.assertEqual(classifier.classify_lifegain_role(SANGUINE_BOND_TEXT), "payoff")

    def test_vito_is_a_payoff(self):
        self.assertEqual(classifier.classify_lifegain_role(VITO_TEXT), "payoff")

    def test_cliffhaven_vampire_is_a_payoff(self):
        self.assertEqual(classifier.classify_lifegain_role(CLIFFHAVEN_VAMPIRE_TEXT), "payoff")

    def test_exquisite_blood_is_neither_a_source_nor_a_payoff(self):
        # Exquisite Blood's trigger is "an opponent loses life", not "you
        # gain life" - a real, disclosed gap (see module docstring): this
        # classifier only recognizes the "whenever you gain life" payoff
        # shape, not its Exquisite-Blood-style inverse.
        self.assertEqual(classifier.classify_lifegain_role(EXQUISITE_BLOOD_TEXT), "")

    def test_empty_text_is_neither(self):
        self.assertEqual(classifier.classify_lifegain_role(""), "")

    def test_unrelated_text_is_neither(self):
        self.assertEqual(
            classifier.classify_lifegain_role("Destroy target creature."), ""
        )


class DeckLifegainSynergyProfileTests(unittest.TestCase):
    def test_white_source_black_payoff_is_a_cross_color_dependency(self):
        # The Karlov of the Ghost Council / Kambal pattern (v4.45.0): a
        # White source feeding a Black payoff.
        deck = [
            _card("Soul Warden", SOUL_WARDEN_TEXT, {"W"}),
            _card("Sanguine Bond", SANGUINE_BOND_TEXT, {"B"}),
        ]
        profile = classifier.deck_lifegain_synergy_profile(deck)
        self.assertTrue(profile["cross_color_dependency"])
        self.assertEqual(profile["source_cards"], ["Soul Warden"])
        self.assertEqual(profile["payoff_cards"], ["Sanguine Bond"])
        self.assertEqual(profile["source_colors"], ["W"])
        self.assertEqual(profile["payoff_colors"], ["B"])

    def test_mono_black_source_and_payoff_is_self_sufficient(self):
        # The Vito real-average-deck pattern (v4.46.0): both roles filled
        # by Black cards - no cross-color dependency exists even though a
        # payoff (Vito himself) is present, because a real in-color source
        # (here modeled as a Black-identity Soul-Warden-shaped card, since
        # this classifier cannot detect lifelink - see module docstring)
        # covers the source role too.
        deck = [
            _card("Vito, Thorn of the Dusk Rose", VITO_TEXT, {"B"}),
            _card("Black Soul-Warden-shaped source", SOUL_WARDEN_TEXT, {"B"}),
        ]
        profile = classifier.deck_lifegain_synergy_profile(deck)
        self.assertFalse(profile["cross_color_dependency"])

    def test_payoff_with_no_source_at_all_is_not_a_dependency(self):
        # cross_color_dependency requires BOTH sides present - a payoff
        # with no detected source is a (disclosed) detection gap, not a
        # claimed cross-color dependency.
        deck = [_card("Sanguine Bond", SANGUINE_BOND_TEXT, {"B"})]
        profile = classifier.deck_lifegain_synergy_profile(deck)
        self.assertFalse(profile["cross_color_dependency"])
        self.assertEqual(profile["source_cards"], [])

    def test_a_card_matching_both_patterns_counts_only_as_payoff(self):
        both_text = "Whenever you gain life, you gain 1 life."
        self.assertEqual(classifier.classify_lifegain_role(both_text), "payoff")

    def test_empty_deck_has_no_dependency(self):
        profile = classifier.deck_lifegain_synergy_profile([])
        self.assertFalse(profile["cross_color_dependency"])
        self.assertEqual(profile["source_cards"], [])
        self.assertEqual(profile["payoff_cards"], [])


if __name__ == "__main__":
    unittest.main()
