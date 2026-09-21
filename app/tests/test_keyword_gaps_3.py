"""
Unit tests for v4.23.0: the secondary "that many"-proportional-trigger gaps
named explicitly in the original audit request - Chatterfang, Squirrel
General; Doubling Season; Augusta, Order Returned; Zimone, All-Questioning;
and the Mycoloth/Ribtruss Roaster Devour pair. All five are real cards
confirmed present (and, for the first three, confirmed via card_impact.csv
as actually cast) in the audited real-deck result bundles - see each
function's own docstring in App/engine.py for the exact source deck and the
real Oracle text this was built against.

Run from the project root:
    python -m unittest tests.test_keyword_gaps_3 -v
"""
from __future__ import annotations

import dataclasses
import random
import sys
import unittest
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


def make_land(name="Forest", **overrides):
    return make_card(name, type_line="Basic Land — Forest", power=None, toughness=None, **overrides)


def make_state(**overrides):
    # turn=5 (not 1) so creatures entered_turn=1 aren't summoning-sick -
    # matches tests/test_old_gnawbone.py's convention.
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


ALWAYS_UNBLOCKED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
}


def with_weights(weights, fn):
    original = combat_interaction._WEIGHTS
    try:
        combat_interaction._WEIGHTS = weights
        return fn()
    finally:
        combat_interaction._WEIGHTS = original


class ChatterfangTests(unittest.TestCase):
    def test_creating_food_also_creates_equal_squirrels(self):
        chatterfang = engine.Permanent(card=make_card("Chatterfang, Squirrel General"), entered_turn=1)
        state = make_state(battlefield=[chatterfang])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.create_tokens(state, strategy, "Food", 3)
        self.assertEqual(state.food, 3)
        squirrels = [g for g in state.creature_tokens if g.name == "Squirrel"]
        self.assertEqual(sum(g.count for g in squirrels), 3)

    def test_creating_creature_tokens_also_creates_equal_squirrels(self):
        chatterfang = engine.Permanent(card=make_card("Chatterfang, Squirrel General"), entered_turn=1)
        state = make_state(battlefield=[chatterfang])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.create_tokens(state, strategy, "Bear", 2, creature=True, power=2, toughness=2)
        bears = [g for g in state.creature_tokens if g.name == "Bear"]
        squirrels = [g for g in state.creature_tokens if g.name == "Squirrel"]
        self.assertEqual(sum(g.count for g in bears), 2)
        self.assertEqual(sum(g.count for g in squirrels), 2)

    def test_squirrels_do_not_recursively_trigger_more_squirrels(self):
        chatterfang = engine.Permanent(card=make_card("Chatterfang, Squirrel General"), entered_turn=1)
        state = make_state(battlefield=[chatterfang])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.create_tokens(state, strategy, "Squirrel", 4, creature=True, power=1, toughness=1)
        squirrels = [g for g in state.creature_tokens if g.name == "Squirrel"]
        self.assertEqual(sum(g.count for g in squirrels), 4)  # not doubled/re-triggered

    def test_without_chatterfang_no_bonus_squirrels(self):
        state = make_state()
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.create_tokens(state, strategy, "Food", 3)
        self.assertEqual(state.creature_tokens, [])


class DoublingSeasonTests(unittest.TestCase):
    def test_doubles_token_creation_count(self):
        ds = engine.Permanent(card=make_card("Doubling Season", type_line="Enchantment"), entered_turn=1)
        state = make_state(battlefield=[ds])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.create_tokens(state, strategy, "Food", 3)
        self.assertEqual(state.food, 6)

    def test_doubles_the_generic_plus1_counter_action(self):
        ds = engine.Permanent(card=make_card("Doubling Season", type_line="Enchantment"), entered_turn=1)
        target = engine.Permanent(card=make_card("Target"), entered_turn=1)
        state = make_state(battlefield=[ds, target])
        action = engine.SemanticAction(kind="plus1_counter", amount=2, raw="Put two +1/+1 counters.")
        handled = engine.execute_semantic_action(state, None, target, action, target=target)
        self.assertTrue(handled)
        self.assertEqual(target.counters, 4)  # 2 requested -> doubled to 4

    def test_doubles_a_planeswalkers_starting_loyalty(self):
        ds = engine.Permanent(card=make_card("Doubling Season", type_line="Enchantment"), entered_turn=1)
        state = make_state(battlefield=[ds])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        walker = make_card("Test Walker", type_line="Legendary Planeswalker — Test", loyalty=5, power=None, toughness=None)
        engine.permanent_enters(state, strategy, walker)
        perm = [p for p in state.battlefield if p.card.name == "Test Walker"][0]
        self.assertEqual(perm.loyalty, 10.0)

    def test_doubles_a_battles_starting_defense(self):
        ds = engine.Permanent(card=make_card("Doubling Season", type_line="Enchantment"), entered_turn=1)
        state = make_state(battlefield=[ds])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        battle = make_card("Test Siege", type_line="Battle — Siege", defense=5, power=None, toughness=None)
        engine.permanent_enters(state, strategy, battle)
        perm = [p for p in state.battlefield if p.card.name == "Test Siege"][0]
        self.assertEqual(perm.defense, 10.0)

    def test_doubles_devour_counters(self):
        ds = engine.Permanent(card=make_card("Doubling Season", type_line="Enchantment"), entered_turn=1)
        state = make_state(
            battlefield=[ds],
            creature_tokens=[engine.TokenGroup(name="Squirrel", count=3, power=1.0, toughness=1.0, keywords=set(), entered_turn=1)],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        devourer = make_card("Devourer", oracle_text="Devour 1")
        engine.permanent_enters(state, strategy, devourer)
        perm = [p for p in state.battlefield if p.card.name == "Devourer"][0]
        self.assertEqual(perm.counters, 6)  # 3 devoured * 1, doubled to 6

    def test_without_doubling_season_nothing_is_doubled(self):
        state = make_state()
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.create_tokens(state, strategy, "Food", 3)
        self.assertEqual(state.food, 3)


class AugustaTests(unittest.TestCase):
    def test_augusta_attacking_exiles_a_graveyard_card_and_nonland_grants_a_counter(self):
        def run():
            augusta = engine.Permanent(
                card=make_card(
                    "Augusta, Order Returned", power=3, toughness=4,
                    oracle_text="Flying, vigilance", keywords={"flying", "vigilance"},
                ),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[augusta], graveyard=[make_card("Some Instant", type_line="Instant", power=None, toughness=None)])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(state.graveyard, [])
            self.assertEqual(len(state.exile), 1)
            self.assertEqual(augusta.counters, 1)
            self.assertEqual(state.opponents[0], 36.0)  # 40 - (3 base + 1 counter)
        with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_augusta_attacking_with_only_a_land_in_graveyard_grants_no_counter(self):
        def run():
            augusta = engine.Permanent(
                card=make_card("Augusta, Order Returned", power=3, toughness=4),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[augusta], graveyard=[make_land("Forest")])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(len(state.exile), 1)  # still exiled...
            self.assertEqual(augusta.counters, 0)  # ...but it was a land, no counter
            self.assertEqual(state.opponents[0], 37.0)  # unbuffed 3 power
        with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_augusta_not_attacking_does_nothing(self):
        augusta = engine.Permanent(
            card=make_card("Augusta, Order Returned", power=3, toughness=4),
            entered_turn=1, tapped=True,  # already tapped -> can't attack
        )
        state = make_state(battlefield=[augusta], graveyard=[make_card("Some Instant", type_line="Instant", power=None, toughness=None)])
        engine.attack_phase(state, engine.ScenarioStrategy(opponent_profile="goldfish"), random.Random(1))
        self.assertEqual(len(state.graveyard), 1)  # untouched
        self.assertEqual(augusta.counters, 0)

    def test_empty_graveyard_is_a_no_op(self):
        def run():
            augusta = engine.Permanent(
                card=make_card("Augusta, Order Returned", power=3, toughness=4),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[augusta], graveyard=[])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(augusta.counters, 0)
        with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)


class ZimoneTests(unittest.TestCase):
    def test_creates_primo_sized_to_the_prime_land_count(self):
        zimone = engine.Permanent(card=make_card("Zimone, All-Questioning", power=1, toughness=1), entered_turn=1)
        lands = [make_land(f"Forest{i}") for i in range(6)]  # 7 total lands after the new one below is prime
        land_perms = [engine.Permanent(card=c, entered_turn=1) for c in lands]
        new_land = engine.Permanent(card=make_land("New Forest"), entered_turn=5)  # entered THIS turn
        state = make_state(battlefield=[zimone] + land_perms + [new_land])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.zimone_all_questioning_end_step_trigger(state, strategy)
        primos = [g for g in state.creature_tokens if g.name == "Primo, the Indivisible"]
        self.assertEqual(len(primos), 1)
        self.assertEqual(primos[0].power, 7.0)  # 7 lands, and 7 is prime
        self.assertEqual(primos[0].toughness, 7.0)

    def test_no_land_entered_this_turn_does_nothing(self):
        zimone = engine.Permanent(card=make_card("Zimone, All-Questioning", power=1, toughness=1), entered_turn=1)
        lands = [engine.Permanent(card=make_land(f"Forest{i}"), entered_turn=1) for i in range(7)]
        state = make_state(battlefield=[zimone] + lands)  # 7 lands, all entered on turn 1, not this turn (5)
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.zimone_all_questioning_end_step_trigger(state, strategy)
        self.assertEqual(state.creature_tokens, [])

    def test_non_prime_land_count_does_nothing(self):
        zimone = engine.Permanent(card=make_card("Zimone, All-Questioning", power=1, toughness=1), entered_turn=1)
        lands = [engine.Permanent(card=make_land(f"Forest{i}"), entered_turn=1) for i in range(5)]
        new_land = engine.Permanent(card=make_land("New Forest"), entered_turn=5)
        state = make_state(battlefield=[zimone] + lands + [new_land])  # 6 lands total, not prime
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.zimone_all_questioning_end_step_trigger(state, strategy)
        self.assertEqual(state.creature_tokens, [])

    def test_zimone_absent_does_nothing(self):
        new_land = engine.Permanent(card=make_land("New Forest"), entered_turn=5)
        state = make_state(battlefield=[new_land])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.zimone_all_questioning_end_step_trigger(state, strategy)
        self.assertEqual(state.creature_tokens, [])

    def test_is_prime_helper(self):
        self.assertFalse(engine._is_prime(0))
        self.assertFalse(engine._is_prime(1))
        self.assertTrue(engine._is_prime(2))
        self.assertTrue(engine._is_prime(7))
        self.assertFalse(engine._is_prime(9))
        self.assertTrue(engine._is_prime(11))


class DevourFollowUpTests(unittest.TestCase):
    def test_mycoloth_upkeep_creates_saprolings_equal_to_counters(self):
        mycoloth = engine.Permanent(card=make_card("Mycoloth", power=2, toughness=2), entered_turn=1, counters=3)
        state = make_state(battlefield=[mycoloth])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.mycoloth_upkeep_trigger(state, strategy)
        saprolings = [g for g in state.creature_tokens if g.name == "Saproling"]
        self.assertEqual(sum(g.count for g in saprolings), 3)

    def test_mycoloth_with_no_counters_creates_nothing(self):
        mycoloth = engine.Permanent(card=make_card("Mycoloth", power=2, toughness=2), entered_turn=1)
        state = make_state(battlefield=[mycoloth])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.mycoloth_upkeep_trigger(state, strategy)
        self.assertEqual(state.creature_tokens, [])

    def test_ribtruss_roaster_end_step_creates_pests_equal_to_counters(self):
        ribtruss = engine.Permanent(card=make_card("Ribtruss Roaster", power=2, toughness=2), entered_turn=1, counters=2)
        state = make_state(battlefield=[ribtruss])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.ribtruss_roaster_end_step_trigger(state, strategy)
        pests = [g for g in state.creature_tokens if g.name == "Pest"]
        self.assertEqual(sum(g.count for g in pests), 2)

    def test_devour_then_mycoloth_upkeep_end_to_end(self):
        # Devour seeds the counters when Mycoloth enters; a later upkeep
        # then creates Saprolings scaled to whatever Devour actually got.
        state = make_state(
            creature_tokens=[engine.TokenGroup(name="Squirrel", count=4, power=1.0, toughness=1.0, keywords=set(), entered_turn=1)],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        mycoloth_card = make_card("Mycoloth", oracle_text="Devour 2\nAt the beginning of your upkeep, create a 1/1 green Saproling creature token for each +1/+1 counter on this creature.")
        engine.permanent_enters(state, strategy, mycoloth_card)
        perm = [p for p in state.battlefield if p.card.name == "Mycoloth"][0]
        self.assertEqual(perm.counters, 8)  # 4 devoured * 2

        state.creature_tokens = [g for g in state.creature_tokens if g.count > 0]  # cleanup the spent Squirrels
        engine.mycoloth_upkeep_trigger(state, strategy)
        saprolings = [g for g in state.creature_tokens if g.name == "Saproling"]
        self.assertEqual(sum(g.count for g in saprolings), 8)


if __name__ == "__main__":
    unittest.main()
