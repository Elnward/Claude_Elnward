"""
Unit tests for v4.15.6: WP6 card-model-coverage review of the 11
partial/partial+ marked cards (KNOWN_COVERAGE_NOTES, App/engine.py). Covers:

- A real, previously-undetected bug found DURING this review: Baron Bertram
  Graywater's "{1}{B}, Sacrifice another creature or artifact: Draw a card."
  was NOT in DEDICATED_RESOLVERS, and its "sacrifice ... creature or
  artifact" cost text isn't recognized by the generic sacrifice-cost parser
  (only Food/Treasure/Clue are) - so the generic activated-ability loop
  (try_generic_semantic_activations) would have paid only the {1}{B} mana
  and silently skipped the sacrifice entirely, handing out a free card draw.
  Fixed at the root (SemanticAbility.unrecognized_sacrifice_cost, checked in
  execute_semantic_ability and try_semantic_board_protection) so this can't
  recur for any other card with an unrecognized sacrifice-cost shape, not
  just Baron Bertram specifically.
- Baron Bertram Graywater's real sacrifice-to-draw resolver
  (use_baron_bertram_sac_draw): converts a genuinely leftover Treasure into
  a card.
- Trudge Garden (use_trudge_garden): per-lifegain-event {2}->4/4 trample
  token, resolved against real spare mana.
- Field-Tested Frying Pan: equipped-creature lifegain pump applied to its
  own ETB Halfling token.
- Moldervine Reclamation: creature-death gain-life/draw, both the Permanent
  path (move_permanent_to_zone) and the token-group combat-death path
  (attack_phase).

Run from the project root:
    python -m unittest tests.test_wp6_lifegain_engine_review -v
"""
from __future__ import annotations

import dataclasses
import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App.combat_model import interaction as combat_interaction  # noqa: E402


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
    return engine.ScenarioStrategy(opponent_profile=profile)


BARON_TEXT = (
    "Whenever one or more tokens you control enter, create a 1/1 black Vampire Rogue "
    "creature token with lifelink. This ability triggers only once each turn.\n"
    "{1}{B}, Sacrifice another creature or artifact: Draw a card."
)

TRUDGE_GARDEN_TEXT = (
    "Whenever you gain life, you may pay {2}. If you do, create a 4/4 green Fungus "
    "Beast creature token with trample."
)

FRYING_PAN_TEXT = (
    'When this Equipment enters, create a Food token, then create a 1/1 white Halfling '
    'creature token and attach this Equipment to it.\n'
    'Equipped creature has "Whenever you gain life, this creature gets +X/+X until end '
    'of turn, where X is the amount of life you gained."\n'
    'Equip {2}'
)

MOLDERVINE_TEXT = "Whenever a creature you control dies, you gain 1 life and draw a card."


def _fake_payment_always_succeeds(state, strategy, total_cost, req, *args, **kwargs):
    return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)


def _fake_payment_always_fails(state, strategy, total_cost, req, *args, **kwargs):
    return None


class _WithFakeManaMixin:
    """Same pattern as tests/test_x_spell_copy.py and
    tests/test_boardwipe_payment_path.py: patch find_payment (and
    available_mana_value, where the code under test consults it) so unit
    tests don't need a real land base, while still exercising the real
    calling code (find_payment call sites, apply_payment)."""

    payment_fn = staticmethod(_fake_payment_always_succeeds)

    def setUp(self):
        self._orig_mana = engine.available_mana_value
        self._orig_find = engine.find_payment
        engine.available_mana_value = lambda state, strategy: 25
        engine.find_payment = self.payment_fn

    def tearDown(self):
        engine.available_mana_value = self._orig_mana
        engine.find_payment = self._orig_find


class UnrecognizedSacrificeCostGuardTests(unittest.TestCase):
    """v4.15.6 root-cause fix: a "sacrifice <thing>" cost the parser can't
    actually collect (not Food/Treasure/Clue) must never be silently
    dropped - found via Baron Bertram Graywater during this review, but the
    fix and its tests are card-agnostic."""

    def test_baron_bertram_sacrifice_cost_is_flagged_unrecognized(self):
        card = make_card("Baron Bertram Graywater", mana_cost="{2}{W}{B}", oracle_text=BARON_TEXT)
        abilities = engine.parse_oracle_semantics(card)
        activated = [a for a in abilities if a.ability_kind == "activated"]
        self.assertEqual(len(activated), 1)
        ability = activated[0]
        self.assertTrue(ability.unrecognized_sacrifice_cost)
        self.assertNotEqual(ability.execution_mode, "exact")

    def test_recognized_food_sacrifice_cost_is_not_flagged(self):
        card = make_card(
            "Gyome, Master Chef", mana_cost="{2}{B}{G}",
            oracle_text="{1}, Sacrifice a Food: Target creature gains indestructible until end of turn. Tap it.",
        )
        abilities = engine.parse_oracle_semantics(card)
        activated = [a for a in abilities if a.ability_kind == "activated"]
        self.assertEqual(len(activated), 1)
        self.assertFalse(activated[0].unrecognized_sacrifice_cost)
        self.assertEqual(activated[0].sacrifice_resource, "Food")

    def test_execute_semantic_ability_refuses_an_unrecognized_sacrifice_cost(self):
        ability = engine.SemanticAbility(
            source="Fake Card", raw="{1}, Sacrifice a creature: Draw a card.",
            ability_kind="activated", mana_total=0, mana_requirements=Counter(),
            actions=[engine.SemanticAction(kind="draw", amount=1)],
            execution_mode="probabilistic", confidence=0.45,
            unrecognized_sacrifice_cost=True,
        )
        source = engine.Permanent(card=make_card("Fake Card"), entered_turn=1)
        state = make_state(battlefield=[source])
        did = engine.execute_semantic_ability(state, make_strategy(), source, ability)
        self.assertFalse(did)
        self.assertEqual(state.cards_drawn_total, 0)

    def test_generic_activation_loop_does_not_auto_fire_baron_bertram(self):
        # Integration: even with mana freely available (payment always
        # succeeds), the generic "value" activation loop must not draw a
        # card for Baron Bertram - his ability isn't in
        # try_generic_semantic_activations' candidate scoring bypass, so
        # this specifically exercises the unrecognized_sacrifice_cost guard
        # inside execute_semantic_ability, not just an unaffordable cost.
        baron = engine.Permanent(card=make_card("Baron Bertram Graywater", oracle_text=BARON_TEXT), entered_turn=1)
        state = make_state(battlefield=[baron])
        orig_find = engine.find_payment
        engine.find_payment = _fake_payment_always_succeeds
        try:
            count = engine.try_generic_semantic_activations(state, make_strategy(), limit=5, phase="value")
        finally:
            engine.find_payment = orig_find
        self.assertEqual(state.cards_drawn_total, 0)
        # has_dedicated_resolver now also excludes Baron Bertram from this
        # generic loop entirely (belt-and-suspenders with the guard above).
        self.assertEqual(count, 0)


class BroaderSelfSacrificeCostSweepTests(unittest.TestCase):
    """The v4.15.6 review of Baron Bertram Graywater turned up a much wider
    pre-existing exploit: a sweep of every card in the project's own
    Scryfall cache (App/.scryfall_card_cache_v4.json) for activated
    abilities with an unrecognized sacrifice cost found it wasn't just
    Baron Bertram - self-sacrifice-shaped costs on real cards already in
    these decks (mana rocks, fetch lands) hit the exact same gap: "{T},
    Sacrifice this land/artifact: <effect>" would have been auto-fired by
    try_generic_semantic_activations for the mana alone, WITHOUT the source
    ever leaving the battlefield - i.e. a free, repeatable (once/turn,
    forever, since the permanent never actually goes away) extra land
    search or card draw. The root-cause fix (unrecognized_sacrifice_cost,
    checked in execute_semantic_ability) closes this for every card with
    this cost shape, not just the one that was reviewed by name."""

    def test_self_sacrifice_land_fetch_is_not_auto_fired_for_free(self):
        # Real card, real project mana base: Evolving Wilds.
        card = make_card(
            "Evolving Wilds", type_line="Land", oracle_text=(
                "{T}, Sacrifice this land: Search your library for a basic "
                "land card, put it onto the battlefield tapped, then shuffle."
            ),
        )
        source = engine.Permanent(card=card, entered_turn=1, tapped=False)
        state = make_state(battlefield=[source], library=[make_card("Forest", type_line="Basic Land — Forest")])
        orig_find = engine.find_payment
        engine.find_payment = _fake_payment_always_succeeds
        try:
            count = engine.try_generic_semantic_activations(state, make_strategy(), limit=5, phase="value")
        finally:
            engine.find_payment = orig_find
        self.assertEqual(count, 0)
        self.assertIn(source, state.battlefield)  # never actually sacrificed
        self.assertEqual(len(state.library), 1)   # library untouched - no free tutor

    def test_self_sacrifice_mana_rock_draw_is_not_auto_fired_for_free(self):
        # Real card, real project artifact base: Mind Stone.
        card = make_card(
            "Mind Stone", type_line="Artifact",
            oracle_text="{1}, {T}, Sacrifice this artifact: Draw a card.",
        )
        source = engine.Permanent(card=card, entered_turn=1, tapped=False)
        state = make_state(battlefield=[source], library=[make_card("Library Card")])
        orig_find = engine.find_payment
        engine.find_payment = _fake_payment_always_succeeds
        try:
            engine.try_generic_semantic_activations(state, make_strategy(), limit=5, phase="value")
        finally:
            engine.find_payment = orig_find
        self.assertEqual(state.cards_drawn_total, 0)
        self.assertIn(source, state.battlefield)


class TrudgeGardenTests(_WithFakeManaMixin, unittest.TestCase):
    def test_gain_life_increments_trigger_counter_only_when_trudge_garden_in_play(self):
        garden = engine.Permanent(card=make_card("Trudge Garden", type_line="Enchantment", oracle_text=TRUDGE_GARDEN_TEXT), entered_turn=1)
        state = make_state(battlefield=[garden])
        engine.gain_life(state, 3, "Test Source")
        self.assertEqual(state.trudge_garden_triggers_this_turn, 1)
        engine.gain_life(state, 2, "Test Source 2")
        self.assertEqual(state.trudge_garden_triggers_this_turn, 2)

    def test_no_trudge_garden_means_no_counter(self):
        state = make_state(battlefield=[])
        engine.gain_life(state, 3, "Test Source")
        self.assertEqual(state.trudge_garden_triggers_this_turn, 0)

    def test_use_trudge_garden_creates_a_token_per_affordable_trigger(self):
        garden = engine.Permanent(card=make_card("Trudge Garden", type_line="Enchantment", oracle_text=TRUDGE_GARDEN_TEXT), entered_turn=1)
        state = make_state(battlefield=[garden])
        state.trudge_garden_triggers_this_turn = 3
        engine.use_trudge_garden(state, make_strategy())
        beasts = [g for g in state.creature_tokens if g.name == "Fungus Beast"]
        self.assertEqual(sum(g.count for g in beasts), 3)
        for g in beasts:
            self.assertEqual(g.power, 4)
            self.assertEqual(g.toughness, 4)
            self.assertIn("trample", g.keywords)

    def test_use_trudge_garden_does_nothing_without_the_card(self):
        state = make_state(battlefield=[])
        state.trudge_garden_triggers_this_turn = 2
        engine.use_trudge_garden(state, make_strategy())
        self.assertEqual(state.creature_tokens, [])

    def test_use_trudge_garden_stops_as_soon_as_payment_fails(self):
        garden = engine.Permanent(card=make_card("Trudge Garden", type_line="Enchantment", oracle_text=TRUDGE_GARDEN_TEXT), entered_turn=1)
        state = make_state(battlefield=[garden])
        state.trudge_garden_triggers_this_turn = 5
        orig_find = engine.find_payment
        engine.find_payment = _fake_payment_always_fails
        try:
            engine.use_trudge_garden(state, make_strategy())
        finally:
            engine.find_payment = orig_find
        self.assertEqual(state.creature_tokens, [])


class FieldTestedFryingPanPumpTests(_WithFakeManaMixin, unittest.TestCase):
    def test_gain_life_accumulates_bonus_only_with_pan_and_halfling_present(self):
        pan = engine.Permanent(card=make_card("Field-Tested Frying Pan", type_line="Artifact", oracle_text=FRYING_PAN_TEXT), entered_turn=1)
        halfling = engine.TokenGroup(name="Halfling", count=1, power=1, toughness=1, keywords=set(), entered_turn=1)
        state = make_state(battlefield=[pan], creature_tokens=[halfling])
        engine.gain_life(state, 5, "Test Source")
        self.assertEqual(state.frying_pan_bonus_this_turn, 5)

    def test_no_bonus_without_the_pan(self):
        halfling = engine.TokenGroup(name="Halfling", count=1, power=1, toughness=1, keywords=set(), entered_turn=1)
        state = make_state(battlefield=[], creature_tokens=[halfling])
        engine.gain_life(state, 5, "Test Source")
        self.assertEqual(state.frying_pan_bonus_this_turn, 0.0)

    def test_no_bonus_without_a_surviving_halfling(self):
        pan = engine.Permanent(card=make_card("Field-Tested Frying Pan", type_line="Artifact", oracle_text=FRYING_PAN_TEXT), entered_turn=1)
        state = make_state(battlefield=[pan], creature_tokens=[])
        engine.gain_life(state, 5, "Test Source")
        self.assertEqual(state.frying_pan_bonus_this_turn, 0.0)

    def test_token_group_power_applies_the_bonus_to_the_halfling_only(self):
        pan = engine.Permanent(card=make_card("Field-Tested Frying Pan", type_line="Artifact", oracle_text=FRYING_PAN_TEXT), entered_turn=1)
        halfling = engine.TokenGroup(name="Halfling", count=1, power=1, toughness=1, keywords=set(), entered_turn=1)
        other = engine.TokenGroup(name="Vampire Rogue", count=1, power=1, toughness=1, keywords=set(), entered_turn=1)
        state = make_state(battlefield=[pan], creature_tokens=[halfling, other])
        state.frying_pan_bonus_this_turn = 4.0
        self.assertEqual(engine.token_group_power(halfling, state), 5.0)
        self.assertEqual(engine.token_group_power(other, state), 1.0)


class BaronBertramSacDrawTests(_WithFakeManaMixin, unittest.TestCase):
    def test_draws_a_card_and_spends_a_treasure_when_affordable(self):
        baron = engine.Permanent(card=make_card("Baron Bertram Graywater", oracle_text=BARON_TEXT), entered_turn=1)
        state = make_state(battlefield=[baron], treasure=1, library=[make_card("Library Card")])
        engine.use_baron_bertram_sac_draw(state, make_strategy())
        self.assertEqual(state.treasure, 0)
        self.assertEqual(state.cards_drawn_total, 1)

    def test_no_treasure_means_no_effect(self):
        baron = engine.Permanent(card=make_card("Baron Bertram Graywater", oracle_text=BARON_TEXT), entered_turn=1)
        state = make_state(battlefield=[baron], treasure=0)
        engine.use_baron_bertram_sac_draw(state, make_strategy())
        self.assertEqual(state.cards_drawn_total, 0)

    def test_unaffordable_payment_means_no_effect(self):
        baron = engine.Permanent(card=make_card("Baron Bertram Graywater", oracle_text=BARON_TEXT), entered_turn=1)
        state = make_state(battlefield=[baron], treasure=1)
        orig_find = engine.find_payment
        engine.find_payment = _fake_payment_always_fails
        try:
            engine.use_baron_bertram_sac_draw(state, make_strategy())
        finally:
            engine.find_payment = orig_find
        self.assertEqual(state.treasure, 1)
        self.assertEqual(state.cards_drawn_total, 0)

    def test_no_baron_no_effect_even_with_treasure(self):
        state = make_state(battlefield=[], treasure=1)
        engine.use_baron_bertram_sac_draw(state, make_strategy())
        self.assertEqual(state.treasure, 1)
        self.assertEqual(state.cards_drawn_total, 0)


class MoldervineReclamationTests(unittest.TestCase):
    def test_permanent_creature_death_triggers_gain_life_and_draw(self):
        molder = engine.Permanent(card=make_card("Moldervine Reclamation", type_line="Enchantment", oracle_text=MOLDERVINE_TEXT), entered_turn=1)
        victim = engine.Permanent(card=make_card("Doomed Bear"), entered_turn=1)
        state = make_state(battlefield=[molder, victim], life=40, library=[make_card("Library Card")])
        engine.move_permanent_to_zone(state, make_strategy(), victim, "graveyard", reason="test kill")
        self.assertEqual(state.life, 41)
        self.assertEqual(state.cards_drawn_total, 1)

    def test_noncreature_death_does_not_trigger(self):
        molder = engine.Permanent(card=make_card("Moldervine Reclamation", type_line="Enchantment", oracle_text=MOLDERVINE_TEXT), entered_turn=1)
        artifact = engine.Permanent(card=make_card("Some Artifact", type_line="Artifact", power=None, toughness=None), entered_turn=1)
        state = make_state(battlefield=[molder, artifact], life=40)
        engine.move_permanent_to_zone(state, make_strategy(), artifact, "graveyard", reason="test sac")
        self.assertEqual(state.life, 40)
        self.assertEqual(state.cards_drawn_total, 0)

    def test_without_moldervine_no_trigger(self):
        victim = engine.Permanent(card=make_card("Doomed Bear"), entered_turn=1)
        state = make_state(battlefield=[victim], life=40)
        engine.move_permanent_to_zone(state, make_strategy(), victim, "graveyard", reason="test kill")
        self.assertEqual(state.life, 40)
        self.assertEqual(state.cards_drawn_total, 0)

    def test_token_group_combat_death_also_triggers(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
            }
            molder = engine.Permanent(card=make_card("Moldervine Reclamation", type_line="Enchantment", oracle_text=MOLDERVINE_TEXT), entered_turn=1)
            group = engine.TokenGroup(name="Soldier", count=2, power=1, toughness=1, keywords=set(), entered_turn=1)
            state = make_state(
                battlefield=[molder], creature_tokens=[group], turn=5, opponents=[40.0], life=40,
                library=[make_card("Library Card")],
            )
            strategy = make_strategy("control")
            engine.attack_phase(state, strategy, random.Random(3))
            self.assertEqual(group.count, 1)  # forced death confirms the trigger path ran
            self.assertEqual(state.life, 41)
            self.assertEqual(state.cards_drawn_total, 1)
        finally:
            combat_interaction._WEIGHTS = original


if __name__ == "__main__":
    unittest.main()
