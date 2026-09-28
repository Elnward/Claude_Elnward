"""
v4.80.0 "Runde 2" (generische Interpreter-Erweiterungen, real-deck-usage-
priorisiert): generisches "Choose one/two" Bullet-Resolving (instant/sorcery
UND self-ETB-Trigger), Team-Pump-+-Keyword-Liste- und singulaere
"each creature you control"-Grant-Generalisierung, Proliferate als
ausfuehrbare Aktion, und Basic Landcycling.

Monarch/Amass/Support (die Zaehler-Spread-Mechanik)/City's Blessing/Ascend
sowie eine echte Convoke-Zahlungs-Integration und Disguise wurden bewusst
NICHT umgesetzt: eine Real-Deck-Nutzungspruefung ueber alle 5 aktuell
getesteten Decks (365 Karten) fand dafuer 0 (Monarch/Amass/Support/City's
Blessing), 2 (Convoke) bzw. 1 (Disguise) Treffer, gegenueber 21 Karten fuer
"Choose one/two" - siehe der Auslieferungsbericht fuer die volle Aufstellung.

Run from the project root:
    python -m unittest tests.test_v4800_runde2_generic_extensions -v
"""
from __future__ import annotations

import dataclasses
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=1, toughness=1, commander=False,
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


class TeamPumpKeywordListGrantTests(unittest.TestCase):
    """'Creatures you control get +N/+N and gain KEYWORD[, KEYWORD...] until
    end of turn' - a pump and a keyword grant combined in ONE clause -
    previously only ever produced the team_pt_bonus action; the trailing
    keyword(s) were silently dropped (Lorehold Charm's third mode)."""

    def test_single_trailing_keyword_after_pump_is_captured(self):
        actions = engine._parse_semantic_actions(
            "Creatures you control get +1/+1 and gain trample until end of turn."
        )
        kinds = {a.kind for a in actions}
        self.assertIn("team_pt_bonus", kinds)
        granted = {a.keyword for a in actions if a.kind == "grant_team_keyword"}
        self.assertEqual(granted, {"trample"})

    def test_multiple_trailing_keywords_after_pump_all_captured(self):
        actions = engine._parse_semantic_actions(
            "Creatures you control get +2/+2 and gain trample, haste, and vigilance "
            "until end of turn."
        )
        granted = {a.keyword for a in actions if a.kind == "grant_team_keyword"}
        self.assertEqual(granted, {"trample", "haste", "vigilance"})

    def test_each_creature_you_control_singular_grant(self):
        actions = engine._parse_semantic_actions(
            "Each creature you control gains hexproof and indestructible until end of turn."
        )
        granted = {a.keyword for a in actions if a.kind == "grant_team_keyword"}
        self.assertEqual(granted, {"hexproof", "indestructible"})

    def test_plain_pump_without_keyword_unaffected(self):
        actions = engine._parse_semantic_actions("Creatures you control get +3/+3 until end of turn.")
        kinds = [a.kind for a in actions]
        self.assertIn("team_pt_bonus", kinds)
        self.assertNotIn("grant_team_keyword", kinds)


class ProliferateTests(unittest.TestCase):
    def test_action_recognized_from_bare_proliferate_line(self):
        actions = engine._parse_semantic_actions("Proliferate.")
        self.assertEqual([a.kind for a in actions], ["proliferate"])

    def test_primitive_grows_own_plus1_counters_loyalty_and_named_counters(self):
        creature = engine.Permanent(
            card=make_card("Counter Guy", power=2, toughness=2), entered_turn=1, tapped=False, counters=1,
        )
        pw = engine.Permanent(
            card=make_card("Planeswalker Guy", type_line="Planeswalker", power=None, toughness=None),
            entered_turn=1, tapped=False, loyalty=3.0,
        )
        pw.named_counters["stun"] = 1
        state = make_state(battlefield=[creature, pw], opponents=[40.0, 40.0])
        state.poison_counters[0] = 2
        changed = engine.proliferate(state, engine.ScenarioStrategy())
        self.assertTrue(changed)
        self.assertEqual(creature.counters, 2)
        self.assertEqual(pw.loyalty, 4.0)
        self.assertEqual(pw.named_counters["stun"], 2)
        self.assertEqual(state.poison_counters[0], 3)
        self.assertEqual(state.poison_counters[1], 0)  # never had any -> stays at 0

    def test_doubling_season_doubles_our_own_counters_not_opponent_poison(self):
        creature = engine.Permanent(card=make_card("Counter Guy"), entered_turn=1, tapped=False, counters=1)
        doubler = engine.Permanent(card=make_card("Doubling Season"), entered_turn=1, tapped=False)
        state = make_state(battlefield=[creature, doubler])
        state.poison_counters[0] = 1
        engine.proliferate(state, engine.ScenarioStrategy())
        self.assertEqual(creature.counters, 3)   # +1 base, doubled -> +2
        self.assertEqual(state.poison_counters[0], 2)  # opponent poison never doubled

    def test_minus1_counters_never_touched(self):
        creature = engine.Permanent(card=make_card("Sad Guy"), entered_turn=1, tapped=False, minus1_counters=2)
        state = make_state(battlefield=[creature])
        engine.proliferate(state, engine.ScenarioStrategy())
        self.assertEqual(creature.minus1_counters, 2)

    def test_no_countable_state_is_a_clean_no_op(self):
        state = make_state(battlefield=[engine.Permanent(card=make_card("Nobody"), entered_turn=1, tapped=False)])
        self.assertFalse(engine.proliferate(state, engine.ScenarioStrategy()))


class ModalChoiceSpellTests(unittest.TestCase):
    """resolve_direct_spell_effects: generic 'Choose one/two' bullet
    resolution for instants/sorceries."""

    def test_single_resolvable_bullet_auto_resolves(self):
        # Artistic-Process-shaped: 2 of 3 modes need an opposing board
        # (unresolvable, by design - this engine models none), the 3rd is a
        # plain token creation.
        card = make_card(
            "Test Artistic", type_line="Sorcery", power=None, toughness=None,
            oracle_text=(
                "Choose one —\n"
                "• Test Artistic deals 6 damage to target creature.\n"
                "• Test Artistic deals 2 damage to each creature you don't control.\n"
                "• Create a 3/3 blue and red Elemental creature token with flying. "
                "It gains haste until end of turn."
            ),
        )
        state = make_state()
        engine.resolve_direct_spell_effects(state, engine.ScenarioStrategy(), card)
        self.assertEqual(len(state.creature_tokens), 1)
        self.assertEqual(state.creature_tokens[0].power, 3.0)

    def test_higher_value_bullet_chosen_over_lower_value_one(self):
        # Boros-Charm-shaped: fixed opponent damage should outscore a single
        # combat keyword grant under the disclosed priority heuristic.
        card = make_card(
            "Test Charm", type_line="Instant", power=None, toughness=None,
            oracle_text=(
                "Choose one —\n"
                "• Test Charm deals 4 damage to target player.\n"
                "• Target creature gains double strike until end of turn."
            ),
        )
        state = make_state(opponents=[40.0])
        engine.resolve_direct_spell_effects(state, engine.ScenarioStrategy(), card)
        self.assertEqual(state.opponents, [36.0])

    def test_choose_two_needs_two_resolvable_bullets_or_is_a_no_op(self):
        card = make_card(
            "Test Command Underfilled", type_line="Sorcery", power=None, toughness=None,
            oracle_text=(
                "Choose two —\n"
                "• Draw a card.\n"
                "• Destroy target artifact.\n"
                "• Exile target creature."
            ),
        )
        state = make_state(hand=[])
        engine.resolve_direct_spell_effects(state, engine.ScenarioStrategy(), card)
        self.assertEqual(len(state.hand), 0)  # only 1 of 2 needed modes resolvable -> no-op

    def test_choose_two_with_two_resolvable_bullets_resolves_both(self):
        card = make_card(
            "Test Command Full", type_line="Sorcery", power=None, toughness=None,
            oracle_text=(
                "Choose two —\n"
                "• Draw a card.\n"
                "• You gain 3 life.\n"
                "• Destroy target artifact."
            ),
        )
        state = make_state(hand=[], life=40, library=[make_card("Lib1")])
        engine.resolve_direct_spell_effects(state, engine.ScenarioStrategy(), card)
        self.assertEqual(len(state.hand), 1)
        self.assertEqual(state.life, 43)

    def test_no_resolvable_bullet_is_a_clean_no_op(self):
        card = make_card(
            "Test Abrade", type_line="Instant", power=None, toughness=None,
            oracle_text=(
                "Choose one —\n"
                "• Test Abrade deals 3 damage to target creature.\n"
                "• Destroy target artifact."
            ),
        )
        state = make_state()
        engine.resolve_direct_spell_effects(state, engine.ScenarioStrategy(), card)
        self.assertEqual(state.opponents, [40.0])
        self.assertEqual(state.creature_tokens, [])

    def test_dedicated_resolver_cards_are_skipped(self):
        engine.DEDICATED_RESOLVERS["Test Dedicated Modal"] = "test-only guard check"
        try:
            card = make_card(
                "Test Dedicated Modal", type_line="Sorcery", power=None, toughness=None,
                oracle_text="Choose one —\n• Draw a card.\n• Destroy target artifact.",
            )
            state = make_state(hand=[])
            engine.resolve_direct_spell_effects(state, engine.ScenarioStrategy(), card)
            self.assertEqual(len(state.hand), 0)
        finally:
            del engine.DEDICATED_RESOLVERS["Test Dedicated Modal"]


class ModalChoiceEtbTests(unittest.TestCase):
    """own_etb_effects: generic 'When ~ enters, choose one -' self-trigger
    resolution (White Widow, Free Agent-shaped) - restricted to an
    ETB-shaped header so an unrelated ACTIVATED ability's modal choice on
    the same card is never accidentally executed for free at ETB time."""

    def test_etb_self_trigger_modal_resolves_the_one_resolvable_mode(self):
        card = make_card(
            "Test Widow", type_line="Creature", power=2, toughness=2,
            oracle_text=(
                "When Test Widow enters, choose one —\n"
                "• Put a +1/+1 counter on target creature.\n"
                "• Return target artifact or enchantment card from your graveyard to your hand."
            ),
        )
        p = engine.Permanent(card=card, entered_turn=5, tapped=False)
        state = make_state(battlefield=[p], turn=5)
        engine.own_etb_effects(state, engine.ScenarioStrategy(), p)
        self.assertEqual(p.counters, 1)

    def test_activated_ability_modal_is_not_swept_in_by_etb_hook(self):
        card = make_card(
            "Test Activated Modal", type_line="Creature", power=2, toughness=2,
            oracle_text="{T}: Choose one —\n• Draw a card.\n• You gain 2 life.",
        )
        p = engine.Permanent(card=card, entered_turn=5, tapped=False)
        state = make_state(battlefield=[p], hand=[], life=40, turn=5)
        engine.own_etb_effects(state, engine.ScenarioStrategy(), p)
        self.assertEqual(len(state.hand), 0)
        self.assertEqual(state.life, 40)


class LandcyclingTests(unittest.TestCase):
    def test_landcycling_discards_and_fetches_a_basic_land_to_hand(self):
        def fake_payment(state, strategy, total_cost, req, *a, **k):
            return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0) if total_cost <= 2 else None
        orig = engine.find_payment
        engine.find_payment = fake_payment
        try:
            cycler = make_card(
                "Test Landcycler", type_line="Sorcery", mana_cost="{4}{W}", mana_value=5,
                oracle_text=(
                    "Create two 3/2 white Hero creature tokens with vigilance.\n"
                    "Basic landcycling {2} ({2}, Discard this card: Search your library for a "
                    "basic land card, reveal it, put it into your hand, then shuffle.)"
                ),
                power=None, toughness=None,
            )
            plains = make_card("Plains", type_line="Basic Land — Plains", oracle_text="")
            state = make_state(hand=[cycler], library=[plains])
            engine.maybe_cycle_cards(state, engine.ScenarioStrategy(opponent_profile="goldfish"))
            self.assertNotIn(cycler, state.hand)
            self.assertIn(cycler, state.graveyard)
            self.assertIn(plains, state.hand)
            self.assertNotIn(plains, state.library)
        finally:
            engine.find_payment = orig

    def test_no_landcycling_cards_in_hand_is_a_no_op(self):
        state = make_state(hand=[make_card("Plain Bear")])
        engine.maybe_cycle_cards(state, engine.ScenarioStrategy(opponent_profile="goldfish"))
        self.assertEqual(len(state.hand), 1)

    def test_no_basic_land_in_library_is_a_no_op(self):
        def fake_payment(state, strategy, total_cost, req, *a, **k):
            return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)
        orig = engine.find_payment
        engine.find_payment = fake_payment
        try:
            cycler = make_card(
                "Test Landcycler 2", type_line="Sorcery", oracle_text="Basic landcycling {2}",
                power=None, toughness=None,
            )
            state = make_state(hand=[cycler], library=[make_card("Nonbasic Thing")])
            engine.maybe_cycle_cards(state, engine.ScenarioStrategy(opponent_profile="goldfish"))
            self.assertIn(cycler, state.hand)  # nothing to fetch -> untouched
        finally:
            engine.find_payment = orig


if __name__ == "__main__":
    unittest.main()
