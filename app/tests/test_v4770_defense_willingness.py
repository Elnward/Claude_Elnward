"""
v4.77.0 WP-A: block_willingness's effect on App/combat_model/defense.py
(the block-side half of the deck-wide play-style sliders -- see
App/combat_model/playstyle.py for the attack-side half).

Run from the project root:
    python -m unittest tests.test_v4770_defense_willingness -v
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

    def __init__(self, playstyle=None):
        self.playstyle = playstyle


def state(*perms, life=40.0, turn=6):
    st = E.GameState(library=[], hand=[], command_zone=[])
    st.turn = turn
    st.life = life
    for c, tapped in perms:
        st.battlefield.append(E.Permanent(card=c, entered_turn=1, tapped=tapped))
    return st


class DefaultWillingnessMatchesFixedPolicyTest(unittest.TestCase):
    """block_willingness == 50 (the default, incl. no playstyle at all) must
    reproduce the pre-v4.77.0 fixed WP2 policy exactly."""

    def test_no_playstyle_matches_explicit_50(self):
        elf = creature("Elf", 1, 1)
        no_ps = defense.absorb_pressure(E, state((elf, False), life=10), _Strategy(None),
                                        random.Random(1), 6.0, "aggro")
        explicit_50 = defense.absorb_pressure(E, state((creature("Elf", 1, 1), False), life=10),
                                              _Strategy({"block_willingness": 50}),
                                              random.Random(1), 6.0, "aggro")
        self.assertEqual(no_ps, explicit_50)

    def test_chump_threshold_unchanged_at_50(self):
        base_threshold = interaction._WEIGHTS["defense"]["chump_only_below_life"]
        high = state((creature("Elf", 1, 1), False), life=base_threshold + 1)
        self.assertEqual(
            defense.absorb_pressure(E, high, _Strategy({"block_willingness": 50}), random.Random(1), 6.0, "aggro")[0],
            0.0,
        )
        low = state((creature("Elf", 1, 1), False), life=base_threshold - 1)
        self.assertGreater(
            defense.absorb_pressure(E, low, _Strategy({"block_willingness": 50}), random.Random(1), 6.0, "aggro")[0],
            0.0,
        )


class LowWillingnessTest(unittest.TestCase):
    def test_chump_threshold_scales_down(self):
        base_threshold = interaction._WEIGHTS["defense"]["chump_only_below_life"]
        # willingness=0 -> effective threshold 0 -> chump never triggers, even at 1 life.
        st = state((creature("Elf", 1, 1), False), life=1)
        prevented, _, _ = defense.absorb_pressure(E, st, _Strategy({"block_willingness": 0}), random.Random(1), 6.0, "aggro")
        self.assertEqual(prevented, 0.0)

    def test_protected_creature_never_chumps_pre_lethal_even_at_low_willingness(self):
        cmd = creature("Commander", 5, 6, commander=True)
        st = state((cmd, False), life=2)  # below default chump threshold, not lethal
        prevented, _, _ = defense.absorb_pressure(E, st, _Strategy({"block_willingness": 0}), random.Random(1), 6.0, "aggro")
        self.assertEqual(prevented, 0.0)

    def test_available_blockers_are_capped_below_50(self):
        walls = [(creature(f"Wall{i}", 0, 9), False) for i in range(10)]
        st = state(*walls, life=30)
        prevented_full, _, _ = defense.absorb_pressure(E, state(*walls, life=30), _Strategy({"block_willingness": 50}),
                                                        random.Random(1), 10.0, "aggro")
        prevented_low, _, _ = defense.absorb_pressure(E, st, _Strategy({"block_willingness": 10}),
                                                       random.Random(1), 10.0, "aggro")
        self.assertLessEqual(prevented_low, prevented_full)

    def test_zero_willingness_still_blocks_lethal_damage(self):
        wall = creature("Wall", 0, 9)
        st = state((wall, False), life=-2)  # already lethal
        prevented, _, _ = defense.absorb_pressure(E, st, _Strategy({"block_willingness": 0}), random.Random(1), 9.0, "aggro")
        self.assertGreater(prevented, 0.0)


class HighWillingnessTest(unittest.TestCase):
    def test_chump_threshold_scales_up(self):
        base_threshold = interaction._WEIGHTS["defense"]["chump_only_below_life"]
        # willingness=100 -> effective threshold = 2x base; life between base and 2x
        # only chumps at high willingness.
        life = base_threshold * 1.5
        st_low = state((creature("Elf", 1, 1), False), life=life)
        st_high = state((creature("Elf", 1, 1), False), life=life)
        self.assertEqual(
            defense.absorb_pressure(E, st_low, _Strategy({"block_willingness": 50}), random.Random(1), 6.0, "aggro")[0],
            0.0,
        )
        self.assertGreater(
            defense.absorb_pressure(E, st_high, _Strategy({"block_willingness": 100}), random.Random(1), 6.0, "aggro")[0],
            0.0,
        )

    def test_protected_creature_may_chump_pre_lethal_at_80_plus(self):
        eng = creature("Engine", 1, 1, roles=("engine",))
        st = state((eng, False), life=1)  # not lethal, below any reasonable chump threshold
        prevented, _, _ = defense.absorb_pressure(E, st, _Strategy({"block_willingness": 90}), random.Random(1), 6.0, "aggro")
        self.assertGreater(prevented, 0.0)


if __name__ == "__main__":
    unittest.main()
