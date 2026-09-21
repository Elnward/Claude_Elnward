"""
Unit tests for v4.65.3: the "Bilbo drain-payoff coverage" follow-up the user
asked to be tackled after the v4.65.1 critical review ("Ja, an die
Bilbo-Drain-Payoff-Coverage auch ranmachen").

Background: card_model_coverage.csv showed Sanguine Bond, Vito, Corpse
Knight, Marauding Blight-Priest and Dina, Soul Steeper all as "generic"
coverage, which an earlier report read (too pessimistically) as "the drain
damage may not actually be simulated". Closer investigation showed:

- Corpse Knight, Marauding Blight-Priest, and Dina's core trigger were
  ALREADY correctly self-reported as fully executable (1/1 or 1/2 "exact") -
  no gap there, "generic" here just means "no KNOWN_COVERAGE_NOTES entry",
  not "unsimulated".
- Sanguine Bond's and Vito's drain line ("Whenever you gain life, target
  opponent loses that much life.") IS already executed for real at runtime,
  in gain_life() (App/engine.py) - via a dedicated, exact text-match calling
  lose_target_opponent() with the real gained amount. But the coverage
  SELF-REPORT undercounted it (0/1 and 1/2 "executable"), because
  _parse_semantic_actions's "opponent loses N life" regex only recognizes a
  literal number, not the dynamic "loses THAT MUCH life" phrasing. That is a
  self-report accuracy bug ("syntax-correct but content-wise wrong"), not a
  missing simulation feature.
- Dina's second ability (a sacrifice-for-pump activated ability) is a real,
  still-disclosed gap, unrelated to the drain-payoff mechanic itself.

This file tests the fix: _parse_semantic_actions recognizing the dynamic
"loses that much life" phrasing as an exact opponent_life_loss action (so
the coverage self-report becomes accurate for ANY card with this common
templated wording, not just these two), and the corrected
KNOWN_COVERAGE_NOTES entries for all five cards. The underlying runtime
mechanic in gain_life() was not changed - it already worked - so this file
also includes a runtime regression check confirming that stayed true.

Run from the project root:
    python -m unittest tests.test_v4653_drain_payoff_coverage -v
"""
from __future__ import annotations

import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Enchantment", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=None, toughness=None, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0, 40.0, 40.0], turn=1,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


SANGUINE_BOND_TEXT = "Whenever you gain life, target opponent loses that much life."
VITO_TEXT = (
    "Whenever you gain life, target opponent loses that much life.\n"
    "{3}{B}{B}: Creatures you control gain lifelink until end of turn."
)
CORPSE_KNIGHT_TEXT = "Whenever another creature you control enters, each opponent loses 1 life."
MARAUDING_BLIGHT_PRIEST_TEXT = "Whenever you gain life, each opponent loses 1 life."
DINA_TEXT = (
    "Whenever you gain life, each opponent loses 1 life.\n"
    "{1}, Sacrifice another creature: Dina gets +X/+0 until end of turn, "
    "where X is the sacrificed creature's power."
)


class ParseSemanticActionsDynamicDrainTests(unittest.TestCase):
    def test_target_opponent_loses_that_much_life_is_recognized(self):
        actions = engine._parse_semantic_actions("target opponent loses that much life")
        kinds = [a.kind for a in actions]
        self.assertIn("opponent_life_loss", kinds)

    def test_each_opponent_loses_that_much_life_is_recognized_too(self):
        actions = engine._parse_semantic_actions("each opponent loses that much life")
        kinds = [a.kind for a in actions]
        self.assertIn("opponent_life_loss", kinds)

    def test_amount_is_the_inert_zero_sentinel_not_a_guessed_number(self):
        actions = engine._parse_semantic_actions("target opponent loses that much life")
        action = next(a for a in actions if a.kind == "opponent_life_loss")
        self.assertEqual(action.amount, 0.0)

    def test_does_not_duplicate_when_the_literal_number_pattern_already_matched(self):
        # "each opponent loses 1 life" already matches the pre-existing
        # literal-number regex - must not ALSO append a second, redundant
        # opponent_life_loss action for the same line.
        actions = engine._parse_semantic_actions("each opponent loses 1 life")
        count = sum(1 for a in actions if a.kind == "opponent_life_loss")
        self.assertEqual(count, 1)

    def test_unrelated_text_does_not_spuriously_match(self):
        actions = engine._parse_semantic_actions("you gain 3 life")
        kinds = [a.kind for a in actions]
        self.assertNotIn("opponent_life_loss", kinds)


class CardModelCoverageDrainPayoffTests(unittest.TestCase):
    """End-to-end through parse_oracle_semantics with the real oracle text
    of all five affected Bilbo V1 cards (Decks/Bilbo V1.txt)."""

    def test_sanguine_bond_is_now_fully_executable(self):
        card = make_card("Sanguine Bond", oracle_text=SANGUINE_BOND_TEXT)
        abilities = engine.parse_oracle_semantics(card)
        self.assertEqual(len(abilities), 1)
        self.assertEqual(abilities[0].execution_mode, "exact")
        self.assertTrue(abilities[0].actions)

    def test_vito_both_lines_are_now_fully_executable(self):
        card = make_card("Vito, Thorn of the Dusk Rose", oracle_text=VITO_TEXT, type_line="Creature")
        abilities = engine.parse_oracle_semantics(card)
        self.assertEqual(len(abilities), 2)
        self.assertTrue(all(a.execution_mode == "exact" for a in abilities))

    def test_corpse_knight_was_already_correct_and_remains_so(self):
        card = make_card("Corpse Knight", oracle_text=CORPSE_KNIGHT_TEXT, type_line="Creature")
        abilities = engine.parse_oracle_semantics(card)
        self.assertEqual(len(abilities), 1)
        self.assertEqual(abilities[0].execution_mode, "exact")

    def test_marauding_blight_priest_was_already_correct_and_remains_so(self):
        card = make_card("Marauding Blight-Priest", oracle_text=MARAUDING_BLIGHT_PRIEST_TEXT, type_line="Creature")
        abilities = engine.parse_oracle_semantics(card)
        self.assertEqual(len(abilities), 1)
        self.assertEqual(abilities[0].execution_mode, "exact")

    def test_dina_core_trigger_is_exact_but_the_sac_pump_ability_remains_a_disclosed_gap(self):
        card = make_card("Dina, Soul Steeper", oracle_text=DINA_TEXT, type_line="Creature")
        abilities = engine.parse_oracle_semantics(card)
        self.assertEqual(len(abilities), 2)
        drain, pump = abilities
        self.assertEqual(drain.execution_mode, "exact")
        self.assertTrue(drain.actions)
        self.assertFalse(pump.actions)  # still not modeled - a real, disclosed gap


class KnownCoverageNotesTests(unittest.TestCase):
    def test_all_five_cards_have_an_accurate_known_coverage_notes_entry(self):
        expected_tiers = {
            "Sanguine Bond": "strong",
            "Vito, Thorn of the Dusk Rose": "strong",
            "Corpse Knight": "strong",
            "Marauding Blight-Priest": "strong",
            "Dina, Soul Steeper": "partial+",
        }
        for name, tier in expected_tiers.items():
            self.assertIn(name, engine.KNOWN_COVERAGE_NOTES)
            actual_tier, note = engine.KNOWN_COVERAGE_NOTES[name]
            self.assertEqual(actual_tier, tier, msg=f"{name} tier mismatch")
            self.assertTrue(note)

    def test_dina_note_still_names_the_real_sac_pump_gap(self):
        _, note = engine.KNOWN_COVERAGE_NOTES["Dina, Soul Steeper"]
        self.assertIn("Opfere", note)

    def test_card_model_coverage_rows_applies_the_upgraded_tiers(self):
        cards = [
            make_card("Sanguine Bond", oracle_text=SANGUINE_BOND_TEXT),
            make_card("Vito, Thorn of the Dusk Rose", oracle_text=VITO_TEXT, type_line="Creature"),
            make_card("Corpse Knight", oracle_text=CORPSE_KNIGHT_TEXT, type_line="Creature"),
            make_card("Marauding Blight-Priest", oracle_text=MARAUDING_BLIGHT_PRIEST_TEXT, type_line="Creature"),
            make_card("Dina, Soul Steeper", oracle_text=DINA_TEXT, type_line="Creature"),
        ]
        rows = {r["Name"]: r for r in engine.card_model_coverage_rows(cards)}
        self.assertEqual(rows["Sanguine Bond"]["Coverage"], "strong")
        self.assertEqual(rows["Sanguine Bond"]["Generic semantic runtime coverage"], "1/1 parsed ability lines executable/approximable")
        self.assertEqual(rows["Vito, Thorn of the Dusk Rose"]["Coverage"], "strong")
        self.assertEqual(rows["Vito, Thorn of the Dusk Rose"]["Generic semantic runtime coverage"], "2/2 parsed ability lines executable/approximable")
        self.assertEqual(rows["Corpse Knight"]["Coverage"], "strong")
        self.assertEqual(rows["Marauding Blight-Priest"]["Coverage"], "strong")
        self.assertEqual(rows["Dina, Soul Steeper"]["Coverage"], "partial+")
        self.assertEqual(rows["Dina, Soul Steeper"]["Generic semantic runtime coverage"], "1/2 parsed ability lines executable/approximable")


class LoyaltyAbilityValueDynamicAmountSafetyTests(unittest.TestCase):
    """The only place a SemanticAction's numeric .amount is summed
    (_loyalty_ability_value, planeswalker loyalty scoring only) must not be
    thrown off by the new amount=0.0 sentinel - confirms the fix cannot
    silently distort any score, even in a contrived planeswalker-loyalty
    shape using this phrasing."""

    def test_dynamic_drain_action_contributes_nothing_and_is_not_penalized(self):
        action = engine.SemanticAction(kind="opponent_life_loss", amount=0.0, target="target opponent")
        ability = engine.LoyaltyAbility(
            sign="+", cost_text="1", text="target opponent loses that much life",
            actions=[action],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        value = engine._loyalty_ability_value(ability, strategy, None)
        self.assertEqual(value, 0.0)  # skipped (falsy amount), not negative/penalized


class GainLifeRuntimeRegressionTests(unittest.TestCase):
    """The actual gameplay mechanic in gain_life() was NOT changed by this
    fix - only the coverage self-report was. This is a regression check
    confirming it still fires exactly as before."""

    def test_sanguine_bond_still_drains_the_real_gained_amount_at_runtime(self):
        card = make_card("Sanguine Bond", oracle_text=SANGUINE_BOND_TEXT)
        perm = engine.Permanent(card=card, entered_turn=1)
        state = make_state(battlefield=[perm], opponents=[40.0, 20.0, 30.0])
        engine.gain_life(state, 5.0, source="Test")
        self.assertEqual(state.life, 45.0)
        # lose_target_opponent hits the highest-life opponent (its own
        # documented heuristic) - unchanged by this fix.
        self.assertEqual(state.opponents, [35.0, 20.0, 30.0])

    def test_vito_drains_lifelink_sourced_lifegain_too(self):
        card = make_card("Vito, Thorn of the Dusk Rose", oracle_text=VITO_TEXT, type_line="Creature")
        perm = engine.Permanent(card=card, entered_turn=1)
        state = make_state(battlefield=[perm], opponents=[40.0, 40.0, 40.0])
        # Combat lifelink routes through gain_life() (App/engine.py attack_phase) -
        # simulated directly here the same way that call site does.
        engine.gain_life(state, 4.0, source="Vito, Thorn of the Dusk Rose lifelink")
        self.assertEqual(state.life, 44.0)
        self.assertEqual(state.opponents, [36.0, 40.0, 40.0])


if __name__ == "__main__":
    unittest.main()
