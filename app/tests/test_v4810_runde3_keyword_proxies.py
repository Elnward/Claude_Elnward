"""
v4.81.0 "Runde 3" (vollstaendige Keyword-Recherche + Proxy-Implementierungen):
Amass, Mill (echter Bugfix - vorher nur Value-Metrik-Stub), Explore, Bolster,
Fabricate, Monstrosity, Populate, Support, Discover, Monarch (befristete
Vereinfachung), City's Blessing/Ascend (Zustands-Flag), sowie das neue
App/hand_evaluation-Modul und dessen erster Verbraucher - eine generische
"discard a card"/"discard N cards"-EFFEKT-Aktion.

Siehe Docs/README.md v4.81.0 fuer die vollstaendige Keyword-Datenbank/
Uebersicht (alle recherchierten MTG-Keywords, Status, Proxy-Design) und die
Begruendung fuer die in diesem Paket bewusst nicht umgesetzten Mechaniken
(Convoke-Realzahlung, Disguise/Morph/Manifest, Kicker, Madness, Goad/Fight/
Ninjutsu/Detain - alle strukturell unsimulierbar ohne ein Gegner-Board-Modell
oder mit unverhaeltnismaessigem Eingriff in die Kern-Zahlungs-Pipeline).

Run from the project root:
    python -m unittest tests.test_v4810_runde3_keyword_proxies -v
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
from App import hand_evaluation  # noqa: E402


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


def make_permanent(card, **overrides):
    defaults = dict(card=card, entered_turn=0)
    defaults.update(overrides)
    return engine.Permanent(**defaults)


class HandEvaluationTests(unittest.TestCase):
    def test_worst_land_preferred_when_land_flooded(self):
        state = make_state(turn=6, battlefield=[
            make_permanent(make_card(f"Land{i}", type_line="Land"))
            for i in range(6)
        ])
        excess_land = make_card("Excess Land", type_line="Land")
        finisher = make_card("Finisher", mana_cost="{6}{G}{G}", roles={"finisher"})
        state.hand = [excess_land, finisher]
        chosen = hand_evaluation.choose_worst_hand_cards(state, 1)
        self.assertEqual(chosen, [excess_land])

    def test_protected_roles_are_never_chosen_over_a_disposable_card(self):
        state = make_state(turn=3, battlefield=[
            make_permanent(make_card(f"Land{i}", type_line="Land")) for i in range(3)
        ])
        tutor = make_card("Vital Tutor", roles={"tutor"})
        filler = make_card("Filler Bear", mana_cost="{7}")
        state.hand = [tutor, filler]
        chosen = hand_evaluation.choose_worst_hand_cards(state, 1)
        self.assertEqual(chosen, [filler])

    def test_exclude_parameter_skips_named_cards(self):
        state = make_state(turn=3)
        a = make_card("A", mana_cost="{8}")
        b = make_card("B", mana_cost="{9}")
        state.hand = [a, b]
        # Without exclusion, b (higher cost => more disposable) is picked first.
        self.assertEqual(hand_evaluation.choose_worst_hand_cards(state, 1), [b])
        # With b excluded, a must be returned instead.
        chosen = hand_evaluation.choose_worst_hand_cards(state, 1, exclude=[b])
        self.assertEqual(chosen, [a])


class DiscardHandActionTests(unittest.TestCase):
    def test_bare_discard_a_card_effect_is_recognized_and_self_scoped(self):
        actions = engine._parse_semantic_actions("Discard a card.")
        kinds = [a.kind for a in actions]
        self.assertIn("discard_hand", kinds)

    def test_target_opponent_discard_is_not_captured_as_self_action(self):
        actions = engine._parse_semantic_actions("Target opponent discards a card.")
        kinds = [a.kind for a in actions]
        self.assertNotIn("discard_hand", kinds)

    def test_execution_discards_the_worst_card(self):
        state = make_state(turn=3)
        expensive = make_card("Expensive", mana_cost="{9}")
        keeper = make_card("Keeper", roles={"finisher"})
        state.hand = [expensive, keeper]
        action = engine.SemanticAction(kind="discard_hand", amount=1.0, raw="Discard a card.")
        handled = engine.execute_semantic_action(state, engine.Strategy(), None, action)
        self.assertTrue(handled)
        self.assertIn(expensive, state.graveyard)
        self.assertIn(keeper, state.hand)
        self.assertNotIn(expensive, state.hand)


class MillTests(unittest.TestCase):
    def test_parses_self_mill_as_effect(self):
        actions = engine._parse_semantic_actions("Mill three cards.")
        mill_actions = [a for a in actions if a.kind == "mill"]
        self.assertEqual(len(mill_actions), 1)
        self.assertEqual(mill_actions[0].amount, 3.0)

    def test_opponent_mill_not_captured(self):
        actions = engine._parse_semantic_actions("Target opponent mills three cards.")
        self.assertFalse(any(a.kind == "mill" for a in actions))

    def test_mill_library_actually_moves_cards(self):
        state = make_state()
        state.library = [make_card(f"L{i}") for i in range(10)]
        n = engine.mill_library(state, engine.Strategy(), 4, source="Test")
        self.assertEqual(n, 4)
        self.assertEqual(len(state.library), 6)
        self.assertEqual(len(state.graveyard), 4)

    def test_mill_opponent_target_is_a_documented_no_op(self):
        state = make_state()
        state.library = [make_card(f"L{i}") for i in range(5)]
        n = engine.mill_library(state, engine.Strategy(), 3, target="each_opponent", source="Test")
        self.assertEqual(n, 0)
        self.assertEqual(len(state.library), 5)


class AmassTests(unittest.TestCase):
    def test_creates_new_army_if_none_exists(self):
        state = make_state()
        self.assertTrue(engine.amass(state, engine.Strategy(), subtype="Zombie", n=2, source="Test"))
        self.assertEqual(len(state.creature_tokens), 1)
        group = state.creature_tokens[0]
        self.assertIn("army", group.name.lower())
        self.assertEqual(group.power, 2.0)
        self.assertEqual(group.toughness, 2.0)

    def test_grows_existing_army_instead_of_creating_a_second_one(self):
        state = make_state()
        engine.amass(state, engine.Strategy(), subtype="Zombie", n=2, source="Test")
        engine.amass(state, engine.Strategy(), subtype="Orc", n=3, source="Test")
        self.assertEqual(len(state.creature_tokens), 1)
        group = state.creature_tokens[0]
        self.assertEqual(group.power, 5.0)
        self.assertEqual(group.toughness, 5.0)

    def test_doubling_season_doubles_amass_counters(self):
        state = make_state(battlefield=[make_permanent(make_card("Doubling Season", type_line="Enchantment"))])
        engine.amass(state, engine.Strategy(), subtype="Zombie", n=2, source="Test")
        group = state.creature_tokens[0]
        self.assertEqual(group.power, 4.0)

    def test_parsing_recognizes_typed_and_bare_amass(self):
        typed = engine._parse_semantic_actions("Amass Orcs 1.")
        bare = engine._parse_semantic_actions("Amass 3.")
        self.assertTrue(any(a.kind == "amass" and a.amount == 1.0 for a in typed))
        self.assertTrue(any(a.kind == "amass" and a.amount == 3.0 for a in bare))


class ExploreTests(unittest.TestCase):
    def test_land_goes_to_hand(self):
        state = make_state()
        state.library = [make_card("Some Forest", type_line="Basic Land - Forest")]
        p = make_permanent(make_card("Explorer"))
        state.battlefield = [p]
        self.assertTrue(engine.explore(state, engine.Strategy(), p, source="Test"))
        self.assertEqual(state.hand, [state.hand[0]])
        self.assertEqual(state.hand[0].name, "Some Forest")
        self.assertEqual(p.counters, 0)

    def test_nonland_grants_a_counter_to_the_explorer(self):
        state = make_state(turn=1)
        state.library = [make_card("Big Spell", mana_cost="{9}")]
        p = make_permanent(make_card("Explorer"))
        state.battlefield = [p]
        engine.explore(state, engine.Strategy(), p, source="Test")
        self.assertEqual(p.counters, 1)

    def test_valuable_nonland_stays_on_top_instead_of_graveyard(self):
        state = make_state(turn=5)
        tutor = make_card("Great Tutor", mana_cost="{9}", roles={"tutor"})
        state.library = [tutor]
        p = make_permanent(make_card("Explorer"))
        state.battlefield = [p]
        engine.explore(state, engine.Strategy(), p, source="Test")
        self.assertEqual(state.library, [tutor])
        self.assertEqual(state.graveyard, [])

    def test_parsing_recognizes_bare_explore(self):
        actions = engine._parse_semantic_actions("Explore.")
        self.assertTrue(any(a.kind == "explore" for a in actions))


class BolsterTests(unittest.TestCase):
    def test_targets_least_toughness_creature(self):
        state = make_state()
        weak = make_permanent(make_card("Weak", power=1, toughness=1))
        strong = make_permanent(make_card("Strong", power=4, toughness=4))
        state.battlefield = [strong, weak]
        engine.bolster(state, engine.Strategy(), 2, source="Test")
        self.assertEqual(weak.counters, 2)
        self.assertEqual(strong.counters, 0)

    def test_parsing_recognizes_bolster_n(self):
        actions = engine._parse_semantic_actions("Bolster 2.")
        self.assertTrue(any(a.kind == "bolster" and a.amount == 2.0 for a in actions))


class FabricateMonstrosityTests(unittest.TestCase):
    def test_fabricate_adds_counters_to_the_creature_itself(self):
        state = make_state()
        p = make_permanent(make_card("Fab Creature"))
        state.battlefield = [p]
        engine.fabricate(state, engine.Strategy(), 2, p, source="Test")
        self.assertEqual(p.counters, 2)

    def test_monstrosity_only_fires_once(self):
        state = make_state()
        p = make_permanent(make_card("Monster"))
        state.battlefield = [p]
        first = engine.monstrosity(state, engine.Strategy(), 4, p, source="Test")
        second = engine.monstrosity(state, engine.Strategy(), 4, p, source="Test")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(p.counters, 4)

    def test_parsing_recognizes_fabricate_and_monstrosity(self):
        self.assertTrue(any(a.kind == "fabricate" for a in engine._parse_semantic_actions("Fabricate 2.")))
        self.assertTrue(any(a.kind == "monstrosity" for a in engine._parse_semantic_actions("Monstrosity 4.")))


class PopulateSupportTests(unittest.TestCase):
    def test_populate_copies_the_strongest_token_group(self):
        state = make_state()
        weak = engine.TokenGroup(name="Weak Token", count=1, power=1, toughness=1)
        strong = engine.TokenGroup(name="Strong Token", count=1, power=5, toughness=5)
        state.creature_tokens = [weak, strong]
        self.assertTrue(engine.populate(state, engine.Strategy(), source="Test"))
        self.assertEqual(strong.count, 2)
        self.assertEqual(weak.count, 1)

    def test_populate_no_op_without_tokens(self):
        state = make_state()
        self.assertFalse(engine.populate(state, engine.Strategy(), source="Test"))

    def test_support_spreads_counters_to_weakest_first(self):
        state = make_state()
        weak = make_permanent(make_card("Weak", power=1, toughness=1))
        mid = make_permanent(make_card("Mid", power=2, toughness=2))
        strong = make_permanent(make_card("Strong", power=5, toughness=5))
        state.battlefield = [strong, mid, weak]
        engine.support(state, engine.Strategy(), 2, source="Test")
        self.assertEqual(weak.counters, 1)
        self.assertEqual(mid.counters, 1)
        self.assertEqual(strong.counters, 0)

    def test_parsing_recognizes_populate_and_support(self):
        self.assertTrue(any(a.kind == "populate" for a in engine._parse_semantic_actions("Populate.")))
        self.assertTrue(any(a.kind == "support" and a.amount == 2.0 for a in engine._parse_semantic_actions("Support 2.")))


class DiscoverTests(unittest.TestCase):
    def test_finds_first_qualifying_nonland_and_mills_the_rest(self):
        state = make_state()
        land = make_card("Island", type_line="Basic Land - Island")
        pricey = make_card("Pricey", mana_cost="{9}")
        cheap_hit = make_card("Cheap Hit", mana_cost="{2}")
        state.library = [land, pricey, cheap_hit, make_card("Never Reached")]
        self.assertTrue(engine.discover(state, engine.Strategy(), 4, source="Test"))
        self.assertIn(cheap_hit, state.hand)
        self.assertIn(land, state.graveyard)
        self.assertIn(pricey, state.graveyard)
        self.assertEqual(state.library, [make_card("Never Reached")])

    def test_no_qualifying_card_still_mills_everything_scanned(self):
        state = make_state()
        state.library = [make_card("Too Big", mana_cost="{9}")]
        found = engine.discover(state, engine.Strategy(), 2, source="Test")
        self.assertFalse(found)
        self.assertEqual(state.library, [])
        self.assertEqual(len(state.graveyard), 1)

    def test_parsing_recognizes_discover_n(self):
        actions = engine._parse_semantic_actions("Discover 4.")
        self.assertTrue(any(a.kind == "discover" and a.amount == 4.0 for a in actions))


class MonarchTests(unittest.TestCase):
    def test_become_monarch_grants_two_bonus_draws_over_two_end_steps(self):
        state = make_state()
        state.library = [make_card(f"L{i}") for i in range(5)]
        engine.become_monarch(state, engine.Strategy(), source="Test")
        self.assertEqual(state.monarch_draws_remaining, 2)
        engine.end_step(state, engine.Strategy())
        self.assertEqual(len(state.hand), 1)
        self.assertEqual(state.monarch_draws_remaining, 1)
        engine.end_step(state, engine.Strategy())
        self.assertEqual(len(state.hand), 2)
        self.assertEqual(state.monarch_draws_remaining, 0)
        engine.end_step(state, engine.Strategy())
        self.assertEqual(len(state.hand), 2)  # no further bonus draws

    def test_parsing_recognizes_become_the_monarch(self):
        actions = engine._parse_semantic_actions("You become the monarch.")
        self.assertTrue(any(a.kind == "monarch" for a in actions))


class CityBlessingTests(unittest.TestCase):
    def test_flag_latches_once_ten_permanents_reached(self):
        state = make_state(battlefield=[
            make_permanent(make_card(f"P{i}", type_line="Land")) for i in range(9)
        ])
        self.assertFalse(engine.has_city_blessing(state))
        engine.end_step(state, engine.Strategy())
        self.assertFalse(engine.has_city_blessing(state))
        state.battlefield.append(make_permanent(make_card("P10", type_line="Land")))
        engine.end_step(state, engine.Strategy())
        self.assertTrue(engine.has_city_blessing(state))

    def test_flag_stays_true_even_if_permanent_count_drops_again(self):
        state = make_state(battlefield=[
            make_permanent(make_card(f"P{i}", type_line="Land")) for i in range(10)
        ])
        engine.end_step(state, engine.Strategy())
        self.assertTrue(engine.has_city_blessing(state))
        state.battlefield = state.battlefield[:2]
        engine.end_step(state, engine.Strategy())
        self.assertTrue(engine.has_city_blessing(state))


if __name__ == "__main__":
    unittest.main()
