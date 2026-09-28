"""
v4.76.0 WP2: board-aware defense against the abstract opponent pressure
(App/combat_model/defense.py, weights -> Data/Models/combat_interaction_weights.json "defense").

Run from the project root:
    python -m unittest tests.test_v4760_defense -v
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from App import engine as E  # noqa: E402
from App.combat_model import defense, interaction  # noqa: E402


def creature(name, p, t, roles=(), commander=False):
    return E.Card(name=name, type_line="Creature — Test", power=p, toughness=t,
                  roles=set(roles), commander=commander)


class _Strategy:
    opponent_profile = "aggro"
    tutor_priority = []
    commander_colors = {"G"}
    advanced_opponent_model = False


def state(*perms, life=40.0, turn=6):
    st = E.GameState(library=[], hand=[], command_zone=[])
    st.turn = turn
    st.life = life
    for c, tapped in perms:
        st.battlefield.append(E.Permanent(card=c, entered_turn=1, tapped=tapped))
    return st


class DefenseTest(unittest.TestCase):
    def test_surviving_blocker_prevents_damage(self):
        wall = creature("Wall", 0, 5)                   # toughness 5 > aggro attacker power 3
        st = state((wall, False), life=30)
        prevented, lost, _ = defense.absorb_pressure(E, st, _Strategy(), random.Random(1), 9.0, "aggro")
        self.assertAlmostEqual(prevented, 3.0)          # one block = one 3-power attacker
        self.assertEqual(lost, 0)  # survivable block, rng(1) first roll 0.134 >= 0.1

    def test_tapped_creatures_do_not_block(self):
        st = state((creature("Wall", 0, 5), True), life=30)
        prevented, _, _ = defense.absorb_pressure(E, st, _Strategy(), random.Random(1), 9.0, "aggro")
        self.assertEqual(prevented, 0.0)

    def test_chump_blocks_only_below_threshold(self):
        elf = creature("Elf", 1, 1)
        high = state((elf, False), life=30)              # 30 after hit >= 15 -> no chump
        self.assertEqual(defense.absorb_pressure(E, high, _Strategy(), random.Random(1), 6.0, "aggro")[0], 0.0)
        low = state((creature("Elf", 1, 1), False), life=10)
        self.assertGreater(defense.absorb_pressure(E, low, _Strategy(), random.Random(1), 6.0, "aggro")[0], 0.0)

    def test_commander_and_engines_only_block_lethal(self):
        cmd = creature("Commander", 5, 6, commander=True)
        eng = creature("Engine", 1, 6, roles=("engine",))
        safe = state((cmd, False), (eng, False), life=12)
        self.assertEqual(defense.absorb_pressure(E, safe, _Strategy(), random.Random(1), 6.0, "aggro")[0], 0.0)
        lethal = state((creature("Commander", 5, 6, commander=True), False), life=-2)
        self.assertGreater(defense.absorb_pressure(E, lethal, _Strategy(), random.Random(1), 6.0, "aggro")[0], 0.0)

    def test_prevention_is_capped(self):
        walls = [(creature(f"Wall{i}", 0, 9), False) for i in range(10)]
        st = state(*walls, life=30)
        prevented, _, _ = defense.absorb_pressure(E, st, _Strategy(), random.Random(1), 10.0, "aggro")
        cap = interaction._WEIGHTS["defense"]["max_prevented_share"]
        self.assertLessEqual(prevented, 10.0 * cap + 1e-9)

    def test_only_fresh_or_vigilant_tokens_block(self):
        st = state(life=10)
        st.creature_tokens.append(E.TokenGroup(name="Soldier", count=3, power=1, toughness=1, entered_turn=2))
        self.assertEqual(defense.absorb_pressure(E, st, _Strategy(), random.Random(1), 6.0, "aggro")[0], 0.0)
        st.creature_tokens.append(E.TokenGroup(name="Soldier", count=2, power=1, toughness=1, entered_turn=st.turn))
        self.assertGreater(defense.absorb_pressure(E, st, _Strategy(), random.Random(1), 6.0, "aggro")[0], 0.0)

    def test_disabled_restores_old_behavior(self):
        saved = dict(interaction._WEIGHTS["defense"])
        try:
            interaction._WEIGHTS["defense"]["enabled"] = False
            st = state((creature("Wall", 0, 5), False), life=30)
            self.assertEqual(defense.absorb_pressure(E, st, _Strategy(), random.Random(1), 9.0, "aggro"), (0.0, 0, []))
        finally:
            interaction._WEIGHTS["defense"] = saved

    def test_engine_wrapper_undoes_prevented_loss(self):
        def fake_old(st, strategy, rng):
            st.life -= 8; st.damage_taken += 8
            if st.life <= 0:
                st.lost_turn = st.turn
        saved = E._V4760_apply_opponent_old
        try:
            E._V4760_apply_opponent_old = fake_old
            st = state((creature("Wall", 0, 5), False), (creature("Wall2", 0, 5), False), life=5)
            st.damage_taken = 0.0
            st.lost_turn = None
            E.apply_abstract_opponent_phase(st, _Strategy(), random.Random(3))
            self.assertIsNone(st.lost_turn)
            self.assertGreater(st.life, 0)
            self.assertGreater(st.damage_prevented_by_blockers, 0)
        finally:
            E._V4760_apply_opponent_old = saved

    def test_goldfish_untouched(self):
        class G(_Strategy):
            opponent_profile = "goldfish"
        calls = []
        saved = E._V4760_apply_opponent_old
        try:
            E._V4760_apply_opponent_old = lambda st, s, r: calls.append(1)
            E.apply_abstract_opponent_phase(state(), G(), random.Random(0))
            self.assertEqual(calls, [1])
        finally:
            E._V4760_apply_opponent_old = saved


if __name__ == "__main__":
    unittest.main()
