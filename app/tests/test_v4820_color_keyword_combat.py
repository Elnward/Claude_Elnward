"""
v4.82.0 "Runde 4": farbabhaengiges Keyword-Kampfmodell
(App/combat_model/keyword_effects.py, Data/Models/color_keyword_profile.json).

Kampf-/Blocker-Keywords wirken jetzt als Wahrscheinlichkeits-Verschiebungen
bzw. (abklingende) Buffs/Debuffs auf die abstrakte Kampf- und Gegnerfunktion,
gespeist aus den echten Decklisten jeder Farbidentitaet (1.585 EDHREC-Decks).

Run from the project root:
    python -m unittest tests.test_v4820_color_keyword_combat -v
"""
from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App.combat_model import keyword_effects as kwe  # noqa: E402
from App.combat_model import interaction  # noqa: E402
from App.combat_model import defense  # noqa: E402
from App.opponent_model import state_equation as se  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="{2}", mana_value=2, type_line="Creature — Bear", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0, 40.0, 40.0], turn=6,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def perm(card, **kw):
    kw.setdefault("entered_turn", 0)
    return engine.Permanent(card=card, **kw)


class StubRng:
    """Deterministic rng: random() cycles through `vals`."""
    def __init__(self, *vals):
        self.vals = list(vals) or [0.5]
        self.i = 0

    def random(self):
        v = self.vals[self.i % len(self.vals)]
        self.i += 1
        return v

    def uniform(self, a, b):
        return (a + b) / 2.0


def ctx_for(*color_sets):
    return kwe.build_context([set(c) for c in color_sets] if color_sets else None)


class ProfileDataTests(unittest.TestCase):
    def test_profile_covers_all_identities_and_pooled_row(self):
        data = json.loads((ROOT / "Data" / "Models" / "color_keyword_profile.json").read_text(encoding="utf-8"))
        ids = data["identities"]
        self.assertIn("ALL", ids)
        self.assertEqual(ids["ALL"]["decks"], 1585)
        for key in ("W", "U", "B", "R", "G", "WU", "UB", "BR", "RG", "WG", "WB", "UR", "BG", "WR", "UG"):
            self.assertIn(key, ids)
            self.assertGreater(ids[key]["creature_copies"], 500)

    def test_real_color_signal_is_present(self):
        wu, rg, g = kwe.identity_row({"W", "U"}), kwe.identity_row({"R", "G"}), kwe.identity_row({"G"})
        self.assertGreater(wu["air_blocker"], 0.35)
        self.assertLess(rg["air_blocker"], 0.15)
        self.assertGreater(g["reach"], g["flying"])      # green blocks fliers mostly via reach
        self.assertGreater(g["deathtouch"], kwe.identity_row({"U"})["deathtouch"])


class AttackBlockMultiplierTests(unittest.TestCase):
    def test_flying_anchor_reproduces_old_flat_value_against_pooled_opponent(self):
        m = kwe.attack_block_multiplier({"flying"}, {}, set(), ctx_for())
        self.assertAlmostEqual(m, interaction._WEIGHTS["evasion_keyword_multiplier"]["flying"], places=6)

    def test_flying_depends_on_opponent_colors(self):
        wu = kwe.attack_block_multiplier({"flying"}, {}, set(), ctx_for({"W", "U"}))
        rg = kwe.attack_block_multiplier({"flying"}, {}, set(), ctx_for({"R", "G"}))
        self.assertGreater(wu, 0.5)
        self.assertLess(rg, 0.3)

    def test_mixed_table_is_equal_blend_of_seats(self):
        blend = kwe.attack_block_multiplier({"flying"}, {}, set(), ctx_for({"W", "U"}, {"R", "G"}))
        wu = kwe.attack_block_multiplier({"flying"}, {}, set(), ctx_for({"W", "U"}))
        rg = kwe.attack_block_multiplier({"flying"}, {}, set(), ctx_for({"R", "G"}))
        self.assertAlmostEqual(blend, (wu + rg) / 2, places=9)

    def test_menace_anchor_and_density(self):
        self.assertAlmostEqual(kwe.attack_block_multiplier({"menace"}, {}, set(), ctx_for()), 0.55, places=6)
        dense = kwe.attack_block_multiplier({"menace"}, {}, set(), ctx_for({"B", "G"}))
        thin = kwe.attack_block_multiplier({"menace"}, {}, set(), ctx_for({"U", "R"}))
        self.assertGreater(dense, thin)

    def test_landwalk_unblockable_only_against_that_color(self):
        extras = {"landwalk": {"U"}}
        self.assertEqual(kwe.attack_block_multiplier(set(), extras, set(), ctx_for({"U"})), 0.0)
        self.assertEqual(kwe.attack_block_multiplier(set(), extras, set(), ctx_for({"R"})), 1.0)
        pooled = kwe.attack_block_multiplier(set(), extras, set(), ctx_for())
        self.assertTrue(0.3 < pooled < 0.7)

    def test_protection_from_color_and_shadow(self):
        prot_b = {"protection_from": {"B"}}
        self.assertLess(kwe.attack_block_multiplier(set(), prot_b, set(), ctx_for({"B"})), 0.2)
        self.assertAlmostEqual(kwe.attack_block_multiplier(set(), prot_b, set(), ctx_for({"W"})), 1.0, places=6)
        self.assertEqual(kwe.attack_block_multiplier(set(), {"shadow": 1}, set(), ctx_for()), 0.0)

    def test_fear_is_weak_against_black(self):
        vs_black = kwe.attack_block_multiplier(set(), {"fear": 1}, set(), ctx_for({"B"}))
        vs_white = kwe.attack_block_multiplier(set(), {"fear": 1}, set(), ctx_for({"W"}))
        self.assertGreater(vs_black, 0.9)
        self.assertLess(vs_white, 0.3)

    def test_trample_excess_and_deathtouch_shortcut(self):
        ctx = ctx_for()
        t = ctx.mean("mean_toughness")
        self.assertAlmostEqual(kwe.trample_excess(6, {"trample"}, ctx), 6 - t, places=6)
        self.assertEqual(kwe.trample_excess(6, {"trample", "deathtouch"}, ctx), 5.0)
        self.assertEqual(kwe.trample_excess(6, {"flying"}, ctx), 0.0)


class ParserTests(unittest.TestCase):
    def test_static_lines_only(self):
        p = kwe.parse_combat_keywords("Flying, protection from black and from red\nExalted\nAfflict 2\nIslandwalk")
        self.assertEqual(p["protection_from"], {"B", "R"})
        self.assertEqual(p["exalted"], 1)
        self.assertEqual(p["afflict"], 2)
        self.assertEqual(p["landwalk"], {"U"})

    def test_granting_lines_are_ignored(self):
        p = kwe.parse_combat_keywords("Other creatures you control have exalted.\nEquipped creature gets +1/+1 and has fear.")
        self.assertEqual(p, {})


class AttackResolutionTests(unittest.TestCase):
    def _attacker(self, **kw):
        base = dict(name="A", power=6.0, lifelink=False, keywords=set())
        base.update(kw)
        return interaction.AttackerInfo(**base)

    def test_blocked_trampler_deals_excess_only_with_context(self):
        state = make_state()
        rng = StubRng(0.0, 0.99)          # blocked, survives
        a = self._attacker(keywords={"trample"})
        state._kw_combat_ctx = ctx_for()
        out = interaction.resolve_combat_interaction("control", 8, [a], rng, state=state)[0]
        self.assertTrue(out.blocked)
        self.assertAlmostEqual(out.damage_dealt, 6 - ctx_for().mean("mean_toughness"), places=6)
        state._kw_combat_ctx = None
        out_old = interaction.resolve_combat_interaction("control", 8, [a], StubRng(0.0, 0.99), state=state)[0]
        self.assertEqual(out_old.damage_dealt, 0.0)

    def test_engine_wrapper_deathtouch_block_records_attrition_and_lifelink(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="control")
        state._kw_strategy = strategy
        card = make_card("Deathtouch Lifelinker", power=3, toughness=3)
        p = perm(card)
        state.battlefield = [p]
        a = self._attacker(name=card.name, power=3.0, lifelink=True, keywords={"deathtouch", "lifelink"},
                           source_kind="permanent", source_ref=p)
        life_before = state.life
        outs = engine._v4820_resolve_combat_interaction("control", 8, [a], StubRng(0.0, 0.99), state=state)
        self.assertTrue(outs[0].blocked)
        self.assertAlmostEqual(state.kw_kill_units, 1.0)
        self.assertGreater(state.life, life_before)   # lifelink damage to the blocker counts

    def test_afflict_and_frenzy(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="control")
        state._kw_strategy = strategy
        c1 = make_card("Afflicter", oracle_text="Afflict 3", power=2, toughness=2)
        c2 = make_card("Frenzied", oracle_text="Frenzy 2", power=2, toughness=2)
        p1, p2 = perm(c1), perm(c2)
        state.battlefield = [p1, p2]
        a1 = self._attacker(name=c1.name, power=2.0, source_kind="permanent", source_ref=p1)
        a2 = self._attacker(name=c2.name, power=2.0, source_kind="permanent", source_ref=p2)
        outs = engine._v4820_resolve_combat_interaction("control", 8, [a1, a2], StubRng(0.0, 0.99, 0.99), state=state)
        self.assertTrue(outs[0].blocked)
        self.assertEqual(sorted(state.opponents)[0], 37.0)     # afflict 3 on one opponent
        self.assertFalse(outs[1].blocked)
        self.assertEqual(outs[1].damage_dealt, 4.0)             # 2 power + frenzy 2


class AttritionLedgerTests(unittest.TestCase):
    def test_simple_mode_refund_and_decay(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="midrange")
        state.kw_kill_units = 1.0
        old = engine._V4820_apply_opponent_old

        def fake(st, strat, rng):
            st.life -= 10.0
            st.damage_taken += 10.0
            engine.record_opponent_attrition(st, strat, None, 1.0, "blocker")   # new kill during this phase
        engine._V4820_apply_opponent_old = fake
        try:
            engine.apply_abstract_opponent_phase(state, strategy, StubRng(0.5))
        finally:
            engine._V4820_apply_opponent_old = old
        unit = defense._defense_weights()["avg_attacker_power"]["midrange"]
        self.assertAlmostEqual(state.life, 40 - 10 + unit)       # only the PRE-EXISTING kill refunds now
        self.assertAlmostEqual(state.kw_kill_units, 0.5 + 1.0)   # old decays by half, new carried in full

    def test_suppression_lasts_exactly_one_round(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="aggro")
        engine.suppress_opponent_pressure(state, 1.0, "Goad test")
        old = engine._V4820_apply_opponent_old

        def fake(st, strat, rng):
            st.life -= 6.0
            st.damage_taken += 6.0
        engine._V4820_apply_opponent_old = fake
        try:
            engine.apply_abstract_opponent_phase(state, strategy, StubRng(0.5))
            first = state.life
            engine.apply_abstract_opponent_phase(state, strategy, StubRng(0.5))
        finally:
            engine._V4820_apply_opponent_old = old
        unit = defense._defense_weights()["avg_attacker_power"]["aggro"]
        self.assertAlmostEqual(first, 40 - 6 + unit)
        self.assertAlmostEqual(state.life, first - 6)

    def test_advanced_mode_attrition_lowers_board_presence(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="random")
        strategy.advanced_opponent_model = True
        strategy.advanced_opponent_seats = [{"strategy": "midrange", "colors": ["G"], "bracket": 3}]
        opp = se.OpponentState(board_presence=4.0)
        state._advanced_opponent_table = [(se.OpponentProfile(strategy="midrange", colors={"G"}), opp)]
        engine.record_opponent_attrition(state, strategy, None, 1.0, "Deathtouch test")
        self.assertAlmostEqual(opp.board_presence, 3.0)
        self.assertFalse(getattr(state, "kw_kill_units", 0.0))


class DefenseKeywordTests(unittest.TestCase):
    def _run(self, blocker_card, colors, dealt=16.0):
        state = make_state(life=40)
        strategy = engine.Strategy(opponent_profile="midrange")
        state.battlefield = [perm(blocker_card)]
        state._kw_defense_ctx = ctx_for(colors) if colors else ctx_for()
        prevented, lost, logs = defense.absorb_pressure(engine, state, strategy, StubRng(0.99), dealt, "midrange")
        return prevented, state

    def test_ground_blocker_stops_less_against_flying_heavy_colors(self):
        wall = make_card("Wall", power=0, toughness=6)
        vs_wu, _ = self._run(wall, {"W", "U"}, dealt=4.0)
        vs_rg, _ = self._run(wall, {"R", "G"}, dealt=4.0)
        self.assertLess(vs_wu, vs_rg)

    def test_reach_blocker_covers_fliers(self):
        wall = make_card("Wall", power=0, toughness=6)
        spider = make_card("Spider", power=0, toughness=6, keywords={"reach"}, oracle_text="Reach")
        ground, _ = self._run(wall, {"W", "U"}, dealt=4.0)
        reach, _ = self._run(spider, {"W", "U"}, dealt=4.0)
        self.assertGreater(reach, ground)

    def test_deathtouch_blocker_kills_and_lifelink_blocker_gains(self):
        dt = make_card("DT", power=1, toughness=5, keywords={"deathtouch"}, oracle_text="Deathtouch")
        _p, st = self._run(dt, {"G"})
        self.assertGreater(getattr(st, "kw_kill_units", 0.0), 0.0)
        ll = make_card("LL", power=3, toughness=5, keywords={"lifelink"}, oracle_text="Lifelink")
        _p, st2 = self._run(ll, {"G"})
        self.assertGreater(st2.life, 40)


class RemovalAndFlashTests(unittest.TestCase):
    def test_shroud_counts_as_hexproof_against_opponent_removal(self):
        state = make_state()
        p = perm(make_card("Shrouded", keywords={"shroud"}, oracle_text="Shroud"))
        self.assertIn("hexproof", engine.effective_keywords_in_state(p, state))

    def test_protection_from_seat_color_blocks_removal_only_during_that_seat(self):
        state = make_state()
        p = perm(make_card("Pro Black", keywords={"protection"}, oracle_text="Protection from black"))
        self.assertNotIn("hexproof", engine.effective_keywords_in_state(p, state))
        engine._KW_ACTIVE_SEAT_COLORS = {"B"}
        try:
            self.assertIn("hexproof", engine.effective_keywords_in_state(p, state))
            engine._KW_ACTIVE_SEAT_COLORS = {"W"}
            self.assertNotIn("hexproof", engine.effective_keywords_in_state(p, state))
        finally:
            engine._KW_ACTIVE_SEAT_COLORS = None

    def test_flash_creature_dodges_wipe_on_its_own_turn(self):
        state = make_state(turn=5)
        strategy = engine.Strategy()
        fresh = perm(make_card("Flash Bear", keywords={"flash"}), entered_turn=5)
        old = perm(make_card("Old Flash Bear", keywords={"flash"}), entered_turn=3)
        state.battlefield = [fresh, old]
        engine.move_permanent_to_zone(state, strategy, fresh, "graveyard", reason="destroy boardwipe")
        engine.move_permanent_to_zone(state, strategy, old, "graveyard", reason="destroy boardwipe")
        self.assertIn(fresh, state.battlefield)
        self.assertNotIn(old, state.battlefield)


class ActionTests(unittest.TestCase):
    def test_goad_and_detain_queue_suppression(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="midrange")
        engine.execute_semantic_action(state, strategy, None, engine.SemanticAction(kind="goad", amount=1.0))
        engine.execute_semantic_action(state, strategy, None, engine.SemanticAction(kind="detain", amount=2.0))
        self.assertAlmostEqual(state.kw_suppression_units, 3.0)
        engine.execute_semantic_action(state, strategy, None, engine.SemanticAction(kind="goad", amount=-1.0))
        self.assertGreaterEqual(state.kw_suppression_units, 99.0)

    def test_fight_kills_by_power_and_small_fighter_dies(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="midrange")
        small = perm(make_card("Small", power=2, toughness=2))
        state.battlefield = [small]
        ok = engine.fight_opponent_creature(state, strategy, small, source="Fight test")
        self.assertTrue(ok)
        self.assertGreater(state.kw_kill_units, 0.5)
        self.assertNotIn(small, state.battlefield)

    def test_bite_never_kills_own_creature(self):
        state = make_state()
        strategy = engine.Strategy(opponent_profile="midrange")
        small = perm(make_card("Small", power=2, toughness=1))
        state.battlefield = [small]
        engine.fight_opponent_creature(state, strategy, small, bite=True, source="Bite test")
        self.assertIn(small, state.battlefield)


class DisableSwitchTests(unittest.TestCase):
    def test_enabled_false_restores_old_path(self):
        cfg = interaction._WEIGHTS["keyword_effects"]
        cfg["enabled"] = False
        try:
            self.assertIsNone(kwe.build_context(None))
            state = make_state()
            self.assertIsNone(engine._kw_context_for(state, engine.Strategy(opponent_profile="midrange")))
            p = perm(make_card("Shrouded", keywords={"shroud"}))
            self.assertNotIn("hexproof", engine.effective_keywords_in_state(p, state))
        finally:
            cfg["enabled"] = True

    def test_goldfish_has_no_context(self):
        self.assertIsNone(engine._kw_context_for(make_state(), engine.Strategy(opponent_profile="goldfish")))


if __name__ == "__main__":
    unittest.main()
