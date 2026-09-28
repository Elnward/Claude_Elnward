"""
v4.83.0 "Siegquoten-Debug": symmetrischer Vierertisch, generischer
Trigger-Bus, Ausfuehrung von Win-Condition-Szenarien, eigene Interaktion
gegen die Sitze, Fokus-Zielwahl (Docs/README.md v4.83.0).

Run from the project root:
    python -m unittest tests.test_v4830_winrate_debug -v
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
from App.trigger_bus import parse_trigger, card_matches  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="{1}", mana_value=1, type_line="Creature — Bear", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    card = engine.Card(**{k: v for k, v in defaults.items() if k in field_names})
    if "roles" not in overrides:
        try:
            card.roles = engine.role_set(card)
        except Exception:
            pass
    return card


def noncreature(name, type_line, text="", cost="{1}", mv=1):
    return make_card(name, type_line=type_line, oracle_text=text, mana_cost=cost, mana_value=mv, power=None, toughness=None)


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0, 40.0, 40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def perm(card, **kw):
    kw.setdefault("entered_turn", 0)
    return engine.Permanent(card=card, **kw)


def lands(n=10):
    return [perm(noncreature(f"Land{i}", "Basic Land — Wastes", cost="", mv=0)) for i in range(n)]


def fix_lands(ls):
    for p in ls:
        p.card.produced_mana = {"W", "U", "B", "R", "G"}
    return ls


def library(n=30):
    return [noncreature(f"Lib{i}", "Basic Land — Forest", cost="", mv=0) for i in range(n)]


def state_with(*perms, hand=None, **kw):
    return make_state(battlefield=list(perms) + fix_lands(lands()), library=library(), hand=list(hand or []), **kw)


def advanced_strategy(n=3):
    return engine.Strategy(
        opponent_profile="midrange", advanced_opponent_model=True,
        advanced_opponent_seats=[{"strategy": "midrange", "colors": ["G"], "bracket": 3} for _ in range(n)],
    )


class TriggerSpecParsingTests(unittest.TestCase):
    def test_cast_filter_types(self):
        s = parse_trigger("Whenever you cast an enchantment spell, draw a card.")
        self.assertEqual((s.event, s.supported), ("cast", True))
        self.assertTrue(card_matches(s, type_line="Enchantment — Aura"))
        self.assertFalse(card_matches(s, type_line="Instant"))
        s = parse_trigger("Whenever you cast a noncreature spell, create a 1/1 red Elemental creature token.")
        self.assertTrue(card_matches(s, type_line="Sorcery"))
        self.assertFalse(card_matches(s, type_line="Creature — Elf"))
        s = parse_trigger("Magecraft — Whenever you cast or copy an instant or sorcery spell, each opponent loses 1 life.")
        self.assertEqual(s.event, "cast")
        self.assertTrue(card_matches(s, type_line="Instant"))

    def test_ability_word_and_self_or_other(self):
        s = parse_trigger("Constellation — Whenever this creature or another enchantment you control enters, draw a card.")
        self.assertEqual((s.event, s.subject, set(s.types)), ("enters", "self_or_other", {"enchantment"}))

    def test_name_reference_is_self(self):
        self.assertEqual(parse_trigger("When Niko enters, create two Shard tokens.", "Niko Aris").subject, "self")
        self.assertEqual(parse_trigger("When Sin dies, draw a card.", "Sin, Unending Cataclysm").event, "dies")

    def test_conservative_rejections(self):
        self.assertFalse(parse_trigger("At the beginning of your upkeep, if you control a Knight, draw a card.").supported)
        self.assertFalse(parse_trigger("When this creature enters, you may pay {2}. If you do, draw a card.").supported)
        self.assertFalse(parse_trigger("Whenever you attack, target attacking Vampire becomes a Demon. When it dies, create a 4/3 token.").supported)
        self.assertFalse(parse_trigger("At the beginning of each end step, draw a card for each opponent who drew two or more cards this turn.").supported)
        self.assertFalse(parse_trigger("Whenever an opponent casts their first spell each turn, you gain 1 life.").supported)
        self.assertEqual(parse_trigger("Whenever an opponent casts a spell, you gain 1 life.").event, "opponent_cast")  # v4.84.0

    def test_enters_or_attacks_and_opponent_draws(self):
        s = parse_trigger("Whenever this creature enters or attacks, create a Treasure token.")
        self.assertTrue(s.also_attacks)
        self.assertEqual(parse_trigger("Whenever an opponent draws a card, they lose 2 life.").event, "opponent_draws")


class TriggerBusEngineTests(unittest.TestCase):
    def test_cast_trigger_draws(self):
        ench = make_card("Enchantress", power=0, toughness=1, oracle_text="Whenever you cast an enchantment spell, draw a card.")
        spell = noncreature("Some Aura", "Enchantment")
        st = state_with(perm(ench), hand=[spell])
        self.assertTrue(engine.try_cast_card(st, engine.Strategy(), spell))
        self.assertEqual(len(st.hand), 1)

    def test_own_etb_drain_and_other_creature_enters(self):
        watcher = make_card("Watcher", oracle_text="Whenever another creature you control enters, each opponent loses 1 life.")
        elf = make_card("Elf", oracle_text="When this creature enters, each opponent loses 2 life.")
        st = state_with(perm(watcher), hand=[elf])
        engine.try_cast_card(st, engine.Strategy(), elf)
        self.assertEqual(st.opponents, [37.0, 37.0, 37.0])

    def test_legacy_own_etb_draw_is_not_doubled(self):
        elf = make_card("Scholar", oracle_text="When this creature enters, draw a card.")
        st = state_with(hand=[elf])
        engine.try_cast_card(st, engine.Strategy(), elf)
        self.assertEqual(len(st.hand), 1)

    def test_landfall_token_and_end_step_draw(self):
        lf = noncreature("Lf", "Enchantment", "Landfall — Whenever a land you control enters, create a 1/1 green Saproling creature token.")
        es = noncreature("Es", "Enchantment", "At the beginning of your end step, draw a card.")
        st = state_with(perm(lf), perm(es))
        engine.land_enters(st, engine.Strategy(), noncreature("Forest", "Basic Land — Forest", cost="", mv=0))
        self.assertEqual(sum(g.count for g in st.creature_tokens), 1)
        engine.end_step(st, engine.Strategy())
        self.assertEqual(len(st.hand), 1)

    def test_dies_target_player_drain(self):
        artist = make_card("Artist", oracle_text="Whenever this creature or another creature dies, target player loses 1 life and you gain 1 life.")
        bear = make_card("Bear")
        pa, pb = perm(artist), perm(bear)
        st = state_with(pa, pb)
        engine.move_permanent_to_zone(st, engine.Strategy(), pb, "graveyard", reason="test")
        self.assertEqual(sum(st.opponents), 119.0)
        self.assertEqual(st.life, 41.0)

    def test_back_face_trigger_never_fires(self):
        dfc = make_card("Mayor", oracle_text="Other Humans you control get +1/+1.\n//\nAt the beginning of your end step, create a 2/2 green Wolf creature token.")
        st = state_with(perm(dfc))
        engine.end_step(st, engine.Strategy())
        self.assertEqual(sum(g.count for g in st.creature_tokens), 0)

    def test_opponent_draw_is_not_our_draw(self):
        acts = engine._parse_semantic_actions("Whenever you cast a spell, target opponent draws a card. Put a +1/+1 counter on target creature.")
        self.assertFalse(any(a.kind == "draw" for a in acts))
        acts = engine._parse_semantic_actions("Target player draws two cards and loses 2 life.")
        self.assertIsInstance(acts, list)

    def test_devotion_drain(self):
        acts = engine._parse_semantic_actions("When this creature enters, each opponent loses X life, where X is your devotion to black. You gain life equal to the life lost this way.")
        self.assertTrue(any(a.kind == "devotion_drain" and a.keyword == "B" and a.token == "gain" for a in acts))
        gm = make_card("Merchant", mana_cost="{3}{B}{B}", mana_value=5,
                       oracle_text="When this creature enters, each opponent loses X life, where X is your devotion to black. You gain life equal to the life lost this way.")
        shade = make_card("Shade", mana_cost="{B}{B}")
        st = state_with(perm(shade), hand=[gm])
        engine.try_cast_card(st, engine.Strategy(), gm)
        self.assertEqual(st.opponents, [36.0, 36.0, 36.0])   # devotion 4 (BB + BB)
        self.assertEqual(st.life, 52.0)

    def test_opponent_draw_trigger_drains_that_seat(self):
        sheol = make_card("Sheol", oracle_text="Whenever an opponent draws a card, they lose 2 life.")
        st = state_with(perm(sheol))
        engine._tb_emit_opponent_draws(st, engine.Strategy(), 1)
        self.assertEqual(st.opponents, [40.0, 38.0, 40.0])

    def test_trigger_bus_switch_off(self):
        old = dict(engine.TABLE_DYNAMICS["trigger_bus"])
        engine.TABLE_DYNAMICS["trigger_bus"]["enabled"] = False
        try:
            ench = make_card("Enchantress", power=0, toughness=1, oracle_text="Whenever you cast an enchantment spell, draw a card.")
            spell = noncreature("Some Aura", "Enchantment")
            st = state_with(perm(ench), hand=[spell])
            engine.try_cast_card(st, engine.Strategy(), spell)
            self.assertEqual(len(st.hand), 0)
        finally:
            engine.TABLE_DYNAMICS["trigger_bus"].update(old)


class SymmetricTableTests(unittest.TestCase):
    def _table(self, st, strategy):
        return engine._get_advanced_opponent_table(st, strategy)

    def test_seats_synced_and_dead_seat_does_not_act(self):
        strategy = advanced_strategy(3)
        st = make_state(opponents=[40.0], life=10_000.0)
        engine.apply_abstract_opponent_phase(st, strategy, random.Random(1))
        self.assertEqual(len(st.opponents), 3)
        st.opponents[0] = 0.0
        t0 = self._table(st, strategy)[0][1].turn
        engine.apply_abstract_opponent_phase(st, strategy, random.Random(2))
        self.assertEqual(self._table(st, strategy)[0][1].turn, t0)

    def test_seats_attack_each_other(self):
        strategy = advanced_strategy(3)
        st = make_state(life=10_000.0)
        for seed in range(12):
            st.turn += 1
            engine.apply_abstract_opponent_phase(st, strategy, random.Random(seed))
        self.assertLess(min(st.opponents), 40.0)

    def test_interaction_is_consumed(self):
        strategy = advanced_strategy(1)
        st = make_state(opponents=[40.0], life=10_000.0)
        table = self._table(st, strategy)
        table[0][1].interaction_availability = 1.0
        table[0][1].board_presence = 0.0
        st.battlefield = [perm(make_card("Target"))]
        engine.apply_abstract_opponent_phase(st, strategy, random.Random(3))
        self.assertLess(table[0][1].interaction_availability, 0.5)

    def test_wipe_hits_every_seat(self):
        strategy = advanced_strategy(2)
        st = make_state(opponents=[40.0, 40.0], life=10_000.0)
        table = self._table(st, strategy)
        table[0][1].turn = 10
        table[0][1].wipe_readiness = 1.0
        table[0][1].board_presence = 1.0
        table[1][1].board_presence = 8.0
        table[1][1].wipe_readiness = 0.0
        engine.apply_abstract_opponent_phase(st, strategy, random.Random(5))
        self.assertLess(table[1][1].board_presence, 4.0)

    def test_disable_switch_restores_old_phase(self):
        engine.TABLE_DYNAMICS["enabled"] = False
        try:
            strategy = advanced_strategy(1)
            st = make_state(opponents=[40.0, 40.0, 40.0], life=10_000.0)
            engine.apply_abstract_opponent_phase(st, strategy, random.Random(1))
            self.assertEqual(len(st.opponents), 3)   # no seat sync in legacy mode
        finally:
            engine.TABLE_DYNAMICS["enabled"] = True


class TargetingTests(unittest.TestCase):
    def test_focus_targets_lowest_living_opponent(self):
        st = make_state(opponents=[30.0, 0.0, 12.0])
        st._focus_targeting = True
        self.assertEqual(engine._combat_damage_target_index(st), 2)
        st._focus_targeting = False
        self.assertEqual(engine._combat_damage_target_index(st), 0)


class WinConditionExecutionTests(unittest.TestCase):
    def _sc(self, card="Combo Piece"):
        return engine.normalize_scenario({"name": "Test Combo", "kind": "Win Condition", "enabled": True,
                                          "requirements": [{"card": card, "count": 1, "zones": ["battlefield"]}],
                                          "mana": {"total": 0}}, 0)

    def test_reached_win_condition_wins_in_goldfish(self):
        strategy = engine.Strategy(opponent_profile="goldfish")
        strategy.scenarios = [self._sc()]
        st = make_state(battlefield=[perm(make_card("Combo Piece"))])
        engine.maybe_execute_focused_win_condition(st, strategy)
        self.assertEqual(st.win_turn, st.turn)

    def test_disrupted_attempt_costs_a_piece(self):
        strategy = advanced_strategy(3)
        strategy.scenarios = [self._sc()]
        st = make_state(battlefield=[perm(make_card("Combo Piece"))])
        for _p, opp in engine._get_advanced_opponent_table(st, strategy):
            opp.interaction_availability = 1.0
        engine.TABLE_DYNAMICS["win_condition_execution"]["disruption_use_share"] = 1.0
        try:
            engine.maybe_execute_focused_win_condition(st, strategy)
        finally:
            engine.TABLE_DYNAMICS["win_condition_execution"]["disruption_use_share"] = 0.5
        self.assertIsNone(st.win_turn)
        self.assertFalse(any(p.card.name == "Combo Piece" for p in st.battlefield))

    def test_switch_off_keeps_measurement_only(self):
        engine.TABLE_DYNAMICS["win_condition_execution"]["enabled"] = False
        try:
            strategy = engine.Strategy(opponent_profile="goldfish")
            strategy.scenarios = [self._sc()]
            st = make_state(battlefield=[perm(make_card("Combo Piece"))])
            engine.maybe_execute_focused_win_condition(st, strategy)
            self.assertIsNone(st.win_turn)
        finally:
            engine.TABLE_DYNAMICS["win_condition_execution"]["enabled"] = True


class PlayerInteractionTests(unittest.TestCase):
    def test_removal_is_cast_against_the_biggest_board(self):
        strategy = advanced_strategy(3)
        swords = noncreature("Swords", "Instant", "Exile target creature. Its controller gains life equal to its power.")
        st = state_with(hand=[swords])
        table = engine._get_advanced_opponent_table(st, strategy)
        table[1][1].board_presence = 4.0
        engine._use_player_interaction(st, strategy)
        self.assertEqual(table[1][1].board_presence, 3.0)
        self.assertNotIn(swords, st.hand)

    def test_removal_held_when_boards_are_small(self):
        strategy = advanced_strategy(3)
        swords = noncreature("Swords", "Instant", "Exile target creature. Its controller gains life equal to its power.")
        st = state_with(hand=[swords])
        engine._use_player_interaction(st, strategy)
        self.assertIn(swords, st.hand)

    def test_own_wipe_when_far_behind(self):
        strategy = advanced_strategy(3)
        wrath = noncreature("Wrath", "Sorcery", "Destroy all creatures. They can't be regenerated.", cost="{4}", mv=4)
        st = state_with(hand=[wrath])
        table = engine._get_advanced_opponent_table(st, strategy)
        for _p, opp in table:
            opp.board_presence = 4.0
        engine._use_player_interaction(st, strategy)
        self.assertTrue(all(opp.board_presence <= 1.0 for _p, opp in table))

    def test_counterspell_stops_a_wipe(self):
        cs = noncreature("Counter", "Instant", "Counter target spell.", cost="{2}", mv=2)
        st = state_with(perm(make_card("A")), perm(make_card("B")), hand=[cs])
        self.assertTrue(engine._player_counterspell(st, advanced_strategy(), what="wipe", spell_type="sorcery"))
        self.assertIn(cs, st.graveyard)


class OrdinaryKillCreditTests(unittest.TestCase):
    def test_ordinary_credit_and_switch(self):
        from App.combat_model import keyword_effects as kwe
        ctx = kwe.build_context(None)
        self.assertGreater(kwe.attrition_credit(set(), 3.0, ctx), 0.0)
        w = kwe._kw_weights()
        old = w.get("ordinary_kill_credit")
        w["ordinary_kill_credit"] = 0.0
        try:
            self.assertEqual(kwe.attrition_credit(set(), 3.0, ctx), 0.0)
        finally:
            w["ordinary_kill_credit"] = old


if __name__ == "__main__":
    unittest.main()
