"""
Unit tests for v4.21.0: keyword-mechanic gap batch 1 - Infect, Persist,
Undying, generic Devour (Wither is intentionally NOT implemented as an
executable mechanic - see the module comment below).

Found during the v4.18.0 model-coverage audit: none of these appeared
anywhere in App/engine.py at all before this version. Scope notes:

  - Wither ("this deals damage to a creature in the form of -1/-1 counters
    instead of damage") ONLY ever matters when dealing damage to a
    creature. This engine models no opposing creatures/permanents
    anywhere (pure goldfish - see the "v4.20.0: Battles" module comment
    for the same architectural fact), so Wither can never have an
    observable effect here. It is intentionally left unimplemented rather
    than adding dead code for an event that structurally cannot occur -
    honest scope, not an oversight. (Infect's OTHER half - poison counters
    from combat damage to a PLAYER - is very much observable and IS
    implemented below.)
  - Persist / Undying hook the single shared "a real creature Permanent
    died" event inside move_permanent_to_zone (destination == "graveyard"),
    the same root-cause hook Moldervine Reclamation already used - so this
    covers combat deaths and any other real death path, not just combat.
  - Devour is uncalibrated (no real Devour card in any audited deck): the
    conservative model only ever sacrifices creature TOKENS we control,
    never a named creature, since there is no calibration data to judge
    that trade.

Run from the project root:
    python -m unittest tests.test_keyword_gaps_1 -v
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
    card = engine.Card(**{k: v for k, v in defaults.items() if k in field_names})
    # keywords is normally derived from oracle_text via keyword_set(), not
    # passed in directly - mirror that so "infect"/"persist"/"undying" in
    # oracle_text actually populate card.keywords the same way a real
    # Scryfall-sourced Card would.
    return dataclasses.replace(card, keywords=engine.keyword_set(card))


def make_state(**overrides):
    # turn=5 (not 1) so creatures/tokens entered_turn=1 aren't filtered out
    # as summoning-sick - matches tests/test_old_gnawbone.py's convention.
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

ALWAYS_BLOCKED_AND_TRADED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
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


class InfectTests(unittest.TestCase):
    def test_infect_creature_combat_damage_becomes_poison_not_life_loss(self):
        def run():
            infector = engine.Permanent(
                card=make_card("Infector", power=5, toughness=5, oracle_text="Infect"),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[infector])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(state.life, 40)  # our life untouched (irrelevant anyway)
            self.assertEqual(state.opponents[0], 40.0)  # NOT life loss
            self.assertEqual(state.poison_counters[0], 5)
        with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_ten_poison_counters_eliminates_the_opponent(self):
        def run():
            infector = engine.Permanent(
                card=make_card("Big Infector", power=10, toughness=10, oracle_text="Infect"),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[infector])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(state.poison_counters[0], 10)
            self.assertEqual(state.opponents[0], 0.0)
            self.assertEqual(state.win_turn, 5)
        with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_non_infect_creature_unaffected(self):
        def run():
            vanilla = engine.Permanent(
                card=make_card("Vanilla", power=5, toughness=5),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[vanilla])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertEqual(state.opponents[0], 35.0)
            self.assertEqual(state.poison_counters.get(0, 0), 0)
        with_weights(ALWAYS_UNBLOCKED_WEIGHTS, run)

    def test_infect_keyword_actually_parses_from_oracle_text(self):
        card = make_card("Infector", oracle_text="Infect")
        self.assertIn("infect", card.keywords)


class PersistUndyingTests(unittest.TestCase):
    def test_undying_creature_returns_with_a_plus_one_counter(self):
        def run():
            walker = engine.Permanent(
                card=make_card("Walker", power=1, toughness=1, oracle_text="Undying"),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[walker])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            self.assertNotIn(walker, state.battlefield)  # the original object died
            self.assertNotIn(walker.card, state.graveyard)  # ... and came right back out
            revived = [p for p in state.battlefield if p.card.name == "Walker"]
            self.assertEqual(len(revived), 1)
            self.assertEqual(revived[0].counters, 1)
        with_weights(ALWAYS_BLOCKED_AND_TRADED_WEIGHTS, run)

    def test_persist_creature_returns_with_a_minus_one_counter(self):
        def run():
            walker = engine.Permanent(
                card=make_card("Persister", power=1, toughness=1, oracle_text="Persist"),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[walker])
            engine.attack_phase(
                state, engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive"),
                random.Random(1),
            )
            revived = [p for p in state.battlefield if p.card.name == "Persister"]
            self.assertEqual(len(revived), 1)
            self.assertEqual(revived[0].minus1_counters, 1)
        with_weights(ALWAYS_BLOCKED_AND_TRADED_WEIGHTS, run)

    def test_undying_creature_that_already_has_a_plus_one_counter_does_not_return(self):
        walker = engine.Permanent(
            card=make_card("Walker", power=1, toughness=1, oracle_text="Undying"),
            entered_turn=1, tapped=False, counters=1,
        )
        state = make_state(battlefield=[walker])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.move_permanent_to_zone(state, strategy, walker, "graveyard", reason="test")
        self.assertIn(walker.card, state.graveyard)
        self.assertEqual(state.battlefield, [])

    def test_persist_creature_that_already_has_a_minus_one_counter_does_not_return(self):
        walker = engine.Permanent(
            card=make_card("Persister", power=1, toughness=1, oracle_text="Persist"),
            entered_turn=1, tapped=False, minus1_counters=1,
        )
        state = make_state(battlefield=[walker])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.move_permanent_to_zone(state, strategy, walker, "graveyard", reason="test")
        self.assertIn(walker.card, state.graveyard)
        self.assertEqual(state.battlefield, [])

    def test_undying_creature_moved_to_exile_does_not_return(self):
        # Real rule: the trigger only exists for a graveyard death.
        walker = engine.Permanent(
            card=make_card("Walker", power=1, toughness=1, oracle_text="Undying"),
            entered_turn=1, tapped=False,
        )
        state = make_state(battlefield=[walker])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.move_permanent_to_zone(state, strategy, walker, "exile", reason="test")
        self.assertIn(walker.card, state.exile)
        self.assertEqual(state.battlefield, [])

    def test_plain_creature_with_neither_keyword_just_dies(self):
        walker = engine.Permanent(
            card=make_card("Plain Bear", power=1, toughness=1),
            entered_turn=1, tapped=False,
        )
        state = make_state(battlefield=[walker])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.move_permanent_to_zone(state, strategy, walker, "graveyard", reason="test")
        self.assertIn(walker.card, state.graveyard)
        self.assertEqual(state.battlefield, [])


class DevourTests(unittest.TestCase):
    def test_devour_consumes_token_creatures_for_plus1_counters(self):
        state = make_state(
            creature_tokens=[
                engine.TokenGroup(name="Squirrel", count=3, power=1.0, toughness=1.0, keywords=set(), entered_turn=1),
            ],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        devourer = make_card("Devourer", oracle_text="Devour 2 (As this creature enters the battlefield, you may sacrifice any number of creatures. This creature enters the battlefield with two +1/+1 counters on it for each creature devoured this way.)")
        engine.permanent_enters(state, strategy, devourer)
        perm = [p for p in state.battlefield if p.card.name == "Devourer"][0]
        self.assertEqual(perm.counters, 6)  # 3 devoured * 2
        self.assertEqual(state.creature_tokens[0].count, 0)

    def test_devour_with_no_tokens_available_devours_nothing(self):
        state = make_state(creature_tokens=[])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        devourer = make_card("Devourer", oracle_text="Devour 1")
        engine.permanent_enters(state, strategy, devourer)
        perm = [p for p in state.battlefield if p.card.name == "Devourer"][0]
        self.assertEqual(perm.counters, 0)

    def test_non_devour_creature_never_touches_tokens(self):
        state = make_state(
            creature_tokens=[
                engine.TokenGroup(name="Squirrel", count=2, power=1.0, toughness=1.0, keywords=set(), entered_turn=1),
            ],
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        vanilla = make_card("Vanilla", power=3, toughness=3)
        engine.permanent_enters(state, strategy, vanilla)
        self.assertEqual(state.creature_tokens[0].count, 2)


if __name__ == "__main__":
    unittest.main()
