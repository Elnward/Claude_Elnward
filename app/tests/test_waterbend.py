"""
Unit/integration tests for WP8, Part 2: Katara, Water Tribe's Hope's Waterbend
ability (App/engine.py::maybe_use_waterbend), wired into the real
engine.attack_phase - not just the abstract planner in isolation (that's
tests/test_resource_planner.py).

The behavior under test that matters most is the Vigilance-sequencing rule
from the WP8 brief: a Vigilance creature that attacked is still untapped once
attackers are committed, so tapping it afterward to help pay for Waterbend
must NOT remove it from combat. This is exercised end-to-end against the real
attack_phase/combat_interaction path (not mocked), per the brief's explicit
requirement.

Run from the project root:
    python -m unittest tests.test_waterbend -v
"""
from __future__ import annotations

import dataclasses
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402

_SCRYFALL_CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def make_strategy(profile="goldfish"):
    # goldfish: never blocks, so combat damage always goes through cleanly -
    # keeps these tests about Waterbend, not about the block/trade RNG that
    # App/combat_model already has its own tests for. commander_posture is
    # forced to "aggressive" so Katara (the commander, gated by Commander
    # Posture - see App/combat_model/posture.py) actually attacks in these
    # small single-/few-creature test boards instead of being held back for
    # having no lethal/value-trigger reason to swing - Posture's own decision
    # logic already has its own tests in tests/test_commander_posture.py,
    # this file is about Waterbend, not about whether Katara chooses to attack.
    return engine.ScenarioStrategy(opponent_profile=profile, commander_posture="aggressive")


def _load_real_card(name: str, *, commander: bool = False) -> engine.Card:
    """
    Builds a real engine.Card for `name` from the project's own offline
    Scryfall cache (App/.scryfall_card_cache_v4.json) - the same cache the
    real Katara V3 deck resolves against - via the same card_from_scryfall
    the real import pipeline uses, rather than hand-authoring a Card. This is
    the "at least one test with real Katara V3 cards" the WP8 brief asked
    for: the cache is available offline in this sandbox (unlike the 4 tests
    v4.8.3 had to skip for missing metadata), so there is nothing to
    document as unavailable here.
    """
    with _SCRYFALL_CACHE_PATH.open("r", encoding="utf-8") as f:
        cache = json.load(f)
    for obj in cache.values():
        if isinstance(obj, dict) and obj.get("name") == name:
            entry = engine.DeckEntry(name=name)
            return engine.card_from_scryfall(entry, obj, commander_name=name if commander else None)
    raise AssertionError(f"{name!r} not found in {_SCRYFALL_CACHE_PATH} - cannot run the real-card test")


class RealKataraCardIsLoadableAndFlaggedForItsDedicatedResolverTests(unittest.TestCase):
    """Sanity-checks the real (Scryfall-sourced) Katara card before using her
    in the end-to-end tests below - if this fails, the failures further down
    are about card data, not about Waterbend logic."""

    def test_real_katara_card_has_vigilance_and_printed_3_3(self):
        katara = _load_real_card(engine.KATARA_HOPE_NAME, commander=True)
        self.assertIn("vigilance", katara.keywords)
        self.assertEqual(katara.power, 3.0)
        self.assertEqual(katara.toughness, 3.0)

    def test_katara_has_a_dedicated_resolver_registered(self):
        self.assertTrue(engine.has_dedicated_resolver(_load_real_card(engine.KATARA_HOPE_NAME)))


class VigilanceSequencingEndToEndTests(unittest.TestCase):
    """The core WP8 rule, against the real attack_phase - not the planner in
    isolation. Katara is real (Scryfall) data; the funding creatures are
    synthetic summoning-sick helpers (entered this turn, no haste, so they
    never attack and stay untapped) so the test controls exactly how many
    free resources are on offer."""

    def _katara_permanent(self):
        return engine.Permanent(
            card=_load_real_card(engine.KATARA_HOPE_NAME, commander=True),
            entered_turn=1, tapped=False,
        )

    def _summoning_sick_helper(self, name, turn):
        # entered_turn == state.turn and no haste -> never joins the attack,
        # stays untapped, so it's a legal Waterbend funding source (tapping a
        # creature to help pay a cost isn't an activated ability of that
        # creature, so summoning sickness doesn't block it).
        return engine.Permanent(
            card=make_card(name, power=2, toughness=2), entered_turn=turn, tapped=False,
        )

    def test_katara_stays_in_combat_after_being_tapped_post_declare_for_waterbend(self):
        katara = self._katara_permanent()
        helpers = [self._summoning_sick_helper(f"Helper {i}", turn=5) for i in range(3)]
        state = make_state(battlefield=[katara] + helpers, turn=5, opponents=[40.0])
        strategy = make_strategy("goldfish")

        engine.attack_phase(state, strategy, random.Random(1))

        # 4 free resources (Katara herself + 3 helpers) -> X=4, beating
        # Katara's natural power of 3, so Waterbend should have fired.
        self.assertEqual(state.opponents[0], 36.0, "expected 4 damage through (X=4), not Katara's un-waterbent power of 3")
        self.assertTrue(katara.tapped, "Katara should end up tapped - she was spent to help pay for Waterbend")
        self.assertTrue(all(h.tapped for h in helpers), "all 3 helpers should have been tapped to help fund X")
        self.assertTrue(
            any("WATERBEND" in line for line in state.event_log),
            "expected a WATERBEND log entry",
        )
        self.assertEqual(state.impact[engine.KATARA_HOPE_NAME]["semantic_ability_uses"], 1)

    def test_vigilance_keeps_katara_untapped_when_waterbend_is_not_worth_activating(self):
        # Katara alone: only 1 free resource (herself). X would be 1, which
        # is worse than her natural power of 3, so Waterbend should NOT
        # activate - and because she has Vigilance and nothing tapped her for
        # a cost, she should still be untapped after attacking.
        katara = self._katara_permanent()
        state = make_state(battlefield=[katara], turn=5, opponents=[40.0])
        strategy = make_strategy("goldfish")

        engine.attack_phase(state, strategy, random.Random(1))

        self.assertEqual(state.opponents[0], 37.0, "expected Katara's plain power of 3 through, unmodified")
        self.assertFalse(katara.tapped, "Vigilance: an attacker that wasn't tapped for any cost should remain untapped")
        self.assertNotIn(
            engine.KATARA_HOPE_NAME, state.impact,
            "Waterbend should not have fired at all when it wouldn't beat the un-waterbent attack",
        )

    def test_non_vigilant_creatures_are_unaffected_when_katara_is_absent(self):
        # Regression guard: maybe_use_waterbend must be a no-op with no
        # Katara on the battlefield, so ordinary combat is untouched.
        attacker = engine.Permanent(card=make_card("Plain Attacker", power=4, toughness=4), entered_turn=1, tapped=False)
        state = make_state(battlefield=[attacker], turn=5, opponents=[40.0])
        strategy = make_strategy("goldfish")
        engine.attack_phase(state, strategy, random.Random(1))
        self.assertEqual(state.opponents[0], 36.0)
        self.assertTrue(attacker.tapped)  # no vigilance -> tapped by the normal declare-attackers step


if __name__ == "__main__":
    unittest.main()
