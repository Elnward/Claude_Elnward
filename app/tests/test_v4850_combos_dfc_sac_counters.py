"""
v4.85.0: Kombo-Wirkungen, doppelseitige Karten, Opfer-Ausgaenge,
+1/+1-Marken-Ausloeser (Docs/README.md v4.85.0) - im Spielpfad getestet.

Run from the project root:
    python -m unittest tests.test_v4850_combos_dfc_sac_counters -v
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import App.engine as engine  # noqa: E402
from test_v4830_winrate_debug import make_card, noncreature, make_state, perm, state_with  # noqa: E402


def scenario(effect=None, kind="Combo", card="Piece", name="Test Combo"):
    raw = {"name": name, "kind": kind, "enabled": True,
           "requirements": [{"card": card, "count": 1, "zones": ["battlefield"]}], "mana": {"total": 0}}
    if effect is not None:
        raw["effect"] = effect
    return engine.normalize_scenario(raw, 0)


def dfc(front_name, front_type, front_text, back_name, back_type, back_text, layout, *, front_cost="{2}{G}",
        back_cost="", front_pt=(2, 2), back_pt=(None, None), cmc=3.0):
    obj = {"name": f"{front_name} // {back_name}", "layout": layout, "cmc": cmc, "type_line": f"{front_type} // {back_type}",
           "color_identity": ["G"], "keywords": [],
           "card_faces": [
               {"name": front_name, "mana_cost": front_cost, "type_line": front_type, "oracle_text": front_text,
                "power": None if front_pt[0] is None else str(front_pt[0]), "toughness": None if front_pt[1] is None else str(front_pt[1])},
               {"name": back_name, "mana_cost": back_cost, "type_line": back_type, "oracle_text": back_text,
                "power": None if back_pt[0] is None else str(back_pt[0]), "toughness": None if back_pt[1] is None else str(back_pt[1])}]}
    card = engine.card_from_scryfall(engine.DeckEntry(name=front_name), obj, None)
    return engine.enrich_semantics(card)


class ComboEffectTests(unittest.TestCase):
    def test_effect_survives_normalization(self):
        sc = scenario({"type": "resource", "resource": "tokens", "infinite": True, "haste": False})
        self.assertEqual(sc["effect"]["type"], "resource")
        self.assertTrue(sc["effect"]["infinite"])
        self.assertNotIn("effect", scenario())  # ohne Angabe bleibt das Feld weg (Altverhalten)

    def test_infinite_tokens_do_not_win_but_are_summoning_sick(self):
        strategy = engine.Strategy(opponent_profile="goldfish")
        strategy.scenarios = [scenario({"type": "resource", "resource": "tokens", "infinite": True})]
        st = make_state(battlefield=[perm(noncreature("Piece", "Artifact"))])
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertIsNone(st.win_turn)
        self.assertEqual(sum(g.count for g in st.creature_tokens), 100)
        self.assertTrue(all(g.entered_turn == st.turn for g in st.creature_tokens))
        before = sum(st.opponents)
        engine.attack_phase(st, strategy, random.Random(1))
        self.assertEqual(sum(st.opponents), before)          # sick this turn
        st.turn += 1
        engine.attack_phase(st, strategy, random.Random(1))
        self.assertLess(sum(st.opponents), before)           # next turn they swing

    def test_eliminate_one_and_win_all(self):
        strategy = engine.Strategy(opponent_profile="goldfish")
        strategy.scenarios = [scenario({"type": "eliminate_one"})]
        st = make_state(battlefield=[perm(make_card("Piece"))], opponents=[40.0, 20.0, 30.0])
        st._focus_targeting = True
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertEqual(st.opponents, [40.0, 0.0, 30.0])
        self.assertIsNone(st.win_turn)
        strategy.scenarios = [scenario({"type": "win_all"}, name="Other")]
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertEqual(st.win_turn, st.turn)

    def test_measure_only_and_repeat(self):
        strategy = engine.Strategy(opponent_profile="goldfish")
        strategy.scenarios = [scenario({"type": "none"}, kind="Win Condition")]
        st = make_state(battlefield=[perm(make_card("Piece"))])
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertIsNone(st.win_turn)
        strategy.scenarios = [scenario({"type": "resource", "resource": "life", "amount": 5, "repeat": "each_turn"})]
        engine.maybe_execute_focused_win_condition(st, strategy)
        engine.maybe_execute_focused_win_condition(st, strategy)   # same turn: once
        st.turn += 1
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertEqual(st.life, 50)

    def test_counters_and_mana_resources(self):
        strategy = engine.Strategy(opponent_profile="goldfish")
        strategy.scenarios = [scenario({"type": "resource", "resource": "counters", "amount": 7}),
                              scenario({"type": "resource", "resource": "mana", "amount": 4}, name="Mana")]
        piece = perm(make_card("Piece"))
        st = make_state(battlefield=[piece])
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertEqual(piece.counters, 7)
        self.assertEqual(st.treasure, 4)


    def test_bilbo_scenario_with_other_effect_is_executed(self):
        strategy = engine.Strategy(opponent_profile="goldfish")
        strategy.scenarios = [scenario({"type": "resource", "resource": "life", "amount": 5}, card=engine.BILBO_NAME)]
        st = make_state(battlefield=[perm(make_card(engine.BILBO_NAME))])
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertEqual(st.life, 45)


class DoubleFacedTests(unittest.TestCase):
    def test_mdfc_land_side_is_played_when_no_land(self):
        c = dfc("Ambush", "Instant", "Target creature you control fights target creature you don't control.",
                "Ambush Territory", "Land", "This land enters tapped.\n{T}: Add {G}.", "modal_dfc", back_pt=(None, None), front_pt=(None, None))
        st = make_state(hand=[c], battlefield=[], library=[])
        land = engine.choose_land(st, engine.Strategy())
        self.assertIsNotNone(land)
        self.assertEqual(land.name, "Ambush Territory")
        self.assertTrue(land.is_land)
        self.assertIs(engine._front_of(land), c)

    def test_mdfc_b_side_cast_when_a_unaffordable(self):
        c = dfc("Big Spell", "Sorcery", "Draw three cards.", "Small Creature", "Creature — Elf",
                "When this creature enters, draw a card.", "modal_dfc", front_cost="{15}", back_cost="{1}", cmc=15.0,
                front_pt=(None, None), back_pt=(1, 1))
        st = state_with(hand=[c])
        st.library = [noncreature(f"L{i}", "Basic Land — Forest", cost="", mv=0) for i in range(10)]
        opt = engine.cast_option(c, st, engine.Strategy())
        self.assertIsNotNone(opt)
        self.assertEqual(opt.card.name, "Small Creature")
        self.assertTrue(engine.try_cast_option(st, engine.Strategy(), opt))
        self.assertTrue(any(p.card.name == "Small Creature" for p in st.battlefield))
        self.assertNotIn(c, st.hand)

    def test_paid_transform_and_front_restored_on_death(self):
        c = dfc("Pup", "Creature — Human Werewolf", "{2}{G}: Transform this creature.", "Big Wolf", "Creature — Wolf",
                "Trample", "transform", back_pt=(5, 5))
        p = perm(c)
        st = state_with(p)
        engine._dfc_transform_step(st, engine.Strategy())
        self.assertEqual(p.card.name, "Big Wolf")
        engine.move_permanent_to_zone(st, engine.Strategy(), p, "graveyard", reason="test")
        self.assertIs(st.graveyard[-1], c)

    def test_daybound_turns_at_night(self):
        c = dfc("Villager", "Creature — Human Werewolf", "Daybound", "Night Wolf", "Creature — Werewolf",
                "Nightbound", "transform", back_pt=(4, 4))
        p = perm(c)
        st = state_with(p)
        st.spells_cast_this_turn = 0
        engine._dfc_transform_step(st, engine.Strategy())
        self.assertEqual(p.card.name, "Night Wolf")
        st.spells_cast_this_turn = 2
        engine._dfc_transform_step(st, engine.Strategy())
        self.assertEqual(p.card.name, "Villager")


class SacrificeOutletTests(unittest.TestCase):
    def test_outlet_in_response_to_wipe_triggers_death_payoffs(self):
        seer = make_card("Seer", oracle_text="Sacrifice another creature: Scry 1.")
        artist = make_card("Artist", oracle_text="Whenever another creature you control dies, each opponent loses 1 life.")
        bears = [perm(make_card(f"Bear{i}")) for i in range(2)]
        st = state_with(perm(seer), perm(artist), *bears)
        st.library = [noncreature(f"L{i}", "Basic Land — Forest", cost="", mv=0) for i in range(10)]
        strategy = engine.Strategy()
        prof = engine._build_advanced_opponent_table([{"strategy": "control", "colors": ["W"], "bracket": 3}])[0][0]
        engine._advanced_wipe_on_player(st, strategy, random.Random(1), prof, "control/W")
        self.assertIn("SACRIFICE OUTLET", " ".join(st.event_log))
        self.assertLess(sum(st.opponents), 120.0)

    def test_outlet_answers_targeted_removal(self):
        seer = make_card("Seer", oracle_text="Sacrifice another creature: Scry 1.")
        bear = perm(make_card("Bear"))
        st = state_with(perm(seer), bear)
        engine._spot_remove_target(st, engine.Strategy(), bear, "exile")
        self.assertNotIn(bear, st.battlefield)
        self.assertTrue(any(c.name == "Bear" for c in st.graveyard))   # sacrificed, not exiled


class CounterTriggerTests(unittest.TestCase):
    def test_counter_placed_trigger_draws(self):
        mage = make_card("Mage", oracle_text="Whenever a +1/+1 counter is put on this creature, draw a card.")
        p = perm(mage)
        st = state_with(p)
        st.library = [noncreature(f"L{i}", "Basic Land — Forest", cost="", mv=0) for i in range(10)]
        engine._V4850_ACTIVE.value = st
        try:
            p.counters += 1
            self.assertEqual(len(st.hand), 1)
            p.counters += 2
            self.assertEqual(len(st.hand), 2)
        finally:
            engine._V4850_ACTIVE.value = None

    def test_counter_hook_ignores_permanents_outside_the_game(self):
        p = perm(make_card("Mage", oracle_text="Whenever a +1/+1 counter is put on this creature, draw a card."))
        p.counters += 1          # no active state -> nothing happens, no error
        self.assertEqual(p.counters, 1)


if __name__ == "__main__":
    unittest.main()
