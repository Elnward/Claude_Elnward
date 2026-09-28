"""
v4.84.0: offene Punkte A-F aus v4.83.0 (Docs/README.md v4.84.0).
End-to-end im Spielpfad (Lehre aus Runde 3: Funktion getestet, Spielpfad nicht).

Run from the project root:
    python -m unittest tests.test_v4840_open_items -v
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

import App.engine as engine  # noqa: E402
from test_v4830_winrate_debug import (  # noqa: E402
    make_card, noncreature, make_state, perm, state_with, advanced_strategy,
)


def basics_library(n=6):
    return [noncreature(f"Forest{i}", "Basic Land — Forest", cost="", mv=0) for i in range(n)] + \
           [noncreature(f"Plains{i}", "Basic Land — Plains", cost="", mv=0) for i in range(n)]


class AnimationTests(unittest.TestCase):
    BELLO = ("During your turn, each non-Equipment artifact and non-Aura enchantment you control with mana value 4 or "
             "greater is a 4/4 Elemental creature in addition to its other types and has indestructible, haste, and "
             "\"Whenever this creature deals combat damage to a player, draw a card.\"")

    def test_animated_permanents_attack_and_are_restored(self):
        bello = make_card("Bello", power=3, toughness=5, oracle_text=self.BELLO)
        ench = noncreature("Big Enchantment", "Enchantment", cost="{4}", mv=4)
        small = noncreature("Small Enchantment", "Enchantment", cost="{1}", mv=1)
        pe, ps = perm(ench), perm(small)
        st = state_with(perm(bello, entered_turn=5), pe, ps)
        st.turn = 5
        engine.attack_phase(st, engine.Strategy(), random.Random(1))
        self.assertLess(sum(st.opponents), 120.0 - 3.9)      # the 4/4 hit
        self.assertIs(pe.card, ench)                          # restored after combat
        self.assertFalse(pe.card.is_creature)
        self.assertGreaterEqual(len(st.hand), 1)              # granted combat-damage draw

    def test_parser_reads_march_of_the_machines_shape(self):
        specs = engine._anim_specs_for_text("Each noncreature artifact is an artifact creature with power and toughness each equal to its mana value.")
        self.assertTrue(specs and specs[0]["pt_mv"])


class TriggerBusGapTests(unittest.TestCase):
    def test_for_each_opponent_scales(self):
        src = noncreature("Src", "Enchantment", "At the beginning of your end step, create a 1/1 white Spirit creature token for each opponent.")
        st = state_with(perm(src))
        engine.end_step(st, engine.Strategy())
        self.assertEqual(sum(g.count for g in st.creature_tokens), 3)

    def test_for_each_opponent_who_stays_unsupported(self):
        src = noncreature("Share", "Enchantment", "At the beginning of each end step, draw a card for each opponent who drew two or more cards this turn.")
        st = state_with(perm(src))
        engine.end_step(st, engine.Strategy())
        self.assertEqual(len(st.hand), 0)

    def test_second_resolution_bonus(self):
        bb = make_card("Bumble", oracle_text="Whenever you cast a spell, target opponent draws a card. Put a +1/+1 counter on target creature. "
                                             "If this is the second time this ability has resolved this turn, you draw two cards.")
        s1, s2 = noncreature("S1", "Sorcery"), noncreature("S2", "Sorcery")
        st = state_with(perm(bb), hand=[s1, s2])
        engine.try_cast_card(st, engine.Strategy(), s1)
        self.assertEqual(len(st.hand), 1)
        engine.try_cast_card(st, engine.Strategy(), s2)
        self.assertEqual(len(st.hand), 2)

    def test_sacrifice_and_life_gain_triggers(self):
        a = noncreature("SacPayoff", "Enchantment", "Whenever you sacrifice a Treasure, each opponent loses 1 life.")
        b = noncreature("LifePayoff", "Enchantment", "Whenever you gain life, draw a card.")
        st = state_with(perm(a), perm(b))
        engine.token_sacrificed(st, "Treasure", 1, engine.Strategy())
        self.assertEqual(sum(st.opponents), 117.0)
        engine.gain_life(st, 2, "x")
        self.assertEqual(len(st.hand), 1)

    def test_opponent_cast_triggers(self):
        ruric = make_card("Ruric", oracle_text="Whenever an opponent casts a noncreature spell, this creature deals 6 damage to that player.")
        st = state_with(perm(ruric))
        for k in range(6):
            engine._tb_emit_opponent_cast(st, engine.Strategy(), 0, random.Random(k))
        self.assertLess(st.opponents[0], 40.0)
        self.assertEqual(st.opponents[1], 40.0)

    def test_token_death_emits_dies(self):
        artist = make_card("Artist", oracle_text="Whenever another creature you control dies, each opponent loses 1 life.")
        st = state_with(perm(artist))
        engine.create_tokens(st, engine.Strategy(), "Soldier", 2, creature=True, power=1, toughness=1)
        snap = engine._token_snapshot(st)
        st.creature_tokens[0].count -= 1
        engine._emit_token_deaths(st, engine.Strategy(), snap)
        self.assertEqual(sum(st.opponents), 117.0)

    def test_back_face_semantics_ignored(self):
        dfc = make_card("Wolfish", oracle_text="Vigilance\n//\nWhenever this creature attacks, draw a card.")
        self.assertFalse(any("draw" in a.raw.lower() for a in engine.parse_oracle_semantics(dfc)))


class SpellAndRampTests(unittest.TestCase):
    def test_sorcery_creature_tokens_and_storm(self):
        warrens = noncreature("Warrens", "Sorcery", "Create two 1/1 red Goblin creature tokens.\nStorm")
        warrens.keywords = {"storm"}
        opener = noncreature("Opener", "Instant")
        st = state_with(hand=[opener, warrens])
        engine.try_cast_card(st, engine.Strategy(), opener)
        engine.try_cast_card(st, engine.Strategy(), warrens)
        self.assertEqual(sum(g.count for g in st.creature_tokens), 4)   # original + 1 storm copy

    def test_land_search_spell_and_etb(self):
        lore = noncreature("Lore", "Sorcery", "Search your library for a Forest card, put that card onto the battlefield, then shuffle.")
        elves = make_card("Wood Elves", oracle_text="When this creature enters, search your library for a Forest card, put that card onto the battlefield, then shuffle.")
        st = state_with(hand=[lore, elves])
        st.library = basics_library()
        lands_before = len(st.lands())
        engine.try_cast_card(st, engine.Strategy(), lore)
        engine.try_cast_card(st, engine.Strategy(), elves)
        self.assertEqual(len(st.lands()), lands_before + 2)
        self.assertIn("ramp", engine.role_set(lore))

    def test_cultivate_shape(self):
        acts = engine._parse_semantic_actions("Search your library for up to two basic land cards, reveal those cards, put one onto the battlefield tapped and the other into your hand, then shuffle.")
        ls = [a for a in acts if a.kind == "land_search"]
        self.assertEqual((ls[0].amount, ls[0].token, ls[0].target), (1.0, "tapped", "hand:1"))


class TableTests(unittest.TestCase):
    def test_simple_profile_maps_to_table(self):
        seen = {}

        def fake(*a, **k):
            seen.update(k)
            return {"summary": {}}
        old = engine._V4840_pipeline_old
        engine._V4840_pipeline_old = fake
        try:
            engine.run_pipeline_v440(deck_file=None, commander_names=[], opponent_profile="control")
        finally:
            engine._V4840_pipeline_old = old
        self.assertTrue(seen.get("advanced_opponent_model"))
        self.assertEqual(seen["advanced_opponent_seats"][0]["strategy"], "control")

    def test_sac_drain_stock_hits_other_players(self):
        strategy = advanced_strategy(3)
        st = make_state(life=100.0)
        table = engine._get_advanced_opponent_table(st, strategy)
        opp = table[0][1]
        opp.sac_drain_by_type = {k: 0.0 for k in opp.sac_drain_by_type}
        first = next(iter(opp.sac_drain_by_type))
        opp.sac_drain_by_type[first] = 0.5
        engine._apply_seat_stocks(st, strategy, 0, opp, random.Random(1), "x")
        self.assertLess(st.life, 100.0)
        self.assertLess(st.opponents[1], 40.0)
        self.assertEqual(st.opponents[0], 40.0)

    def test_removal_share_zero_means_no_removal(self):
        engine.TABLE_DYNAMICS["interaction_removal_share"] = 0.0
        try:
            st = state_with(perm(make_card("Target")))
            prof = engine._get_advanced_opponent_table(st, advanced_strategy(1))[0][0]
            engine._advanced_removal_on_player(st, advanced_strategy(1), random.Random(1), prof, "x")
            self.assertTrue(any(p.card.name == "Target" for p in st.battlefield))
        finally:
            engine.TABLE_DYNAMICS["interaction_removal_share"] = 0.83


class WinConditionQualityTests(unittest.TestCase):
    def _sc(self, derived=None):
        return engine.normalize_scenario({"name": "Alpha", "kind": "Win Condition", "enabled": True,
                                          "requirements": [{"card": "Piece", "count": 1, "zones": ["battlefield"]}],
                                          "mana": {"total": 0}, "derived": derived or []}, 0)

    def test_quality_classification(self):
        self.assertEqual(engine.win_condition_quality(self._sc())["quality"], "loose")
        d = [{"type": "board_damage_lethal", "params": {"target": "each"}}]
        self.assertEqual(engine.win_condition_quality(self._sc(d))["quality"], "checked")

    def test_measure_only_policy_blocks_loose(self):
        engine.TABLE_DYNAMICS["win_condition_execution"]["loose_policy"] = "measure_only"
        try:
            strategy = engine.Strategy(opponent_profile="goldfish")
            strategy.scenarios = [self._sc()]
            st = make_state(battlefield=[perm(make_card("Piece"))])
            engine.maybe_execute_focused_win_condition(st, strategy)
            self.assertIsNone(st.win_turn)
            self.assertTrue(strategy.scenarios[0]["enabled"])   # restored
        finally:
            engine.TABLE_DYNAMICS["win_condition_execution"]["loose_policy"] = "execute"


class CoverageTests(unittest.TestCase):
    def test_trigger_line_status_counts_resolved_variable_lines(self):
        c = noncreature("Src", "Enchantment", "At the beginning of your end step, create a 1/1 white Spirit creature token for each opponent.\n"
                                              "At the beginning of your upkeep, if you control a Knight, draw a card.")
        lines, ok, reasons = engine.trigger_line_status(c)
        self.assertEqual((lines, ok), (2, 1))
        self.assertEqual(reasons.get("intervening_if"), 1)


if __name__ == "__main__":
    unittest.main()
