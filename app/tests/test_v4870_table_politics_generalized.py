"""
v4.87.0: Tischpolitik, Bausteine 2-4 - Groll-Gedaechtnis (immer aktiv, klein),
Gruppenhug-Malus, Umschalter Tischfuehrung (Docs/README.md v4.87.0).
Im Spielpfad getestet (echter GameState, echte Sitz-Tabelle).

Run from the project root:
    python -m unittest tests.test_v4870_table_politics_generalized -v
"""
from __future__ import annotations

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import App.engine as engine  # noqa: E402
from test_v4830_winrate_debug import make_card, noncreature, make_state, perm, state_with, advanced_strategy  # noqa: E402


class GroupHugValueTests(unittest.TestCase):
    def test_detects_known_group_hug_shapes(self):
        mine = noncreature("Howling Mine", "Artifact", "Each player draws an additional card during their draw step.")
        st = make_state(battlefield=[perm(mine)])
        self.assertEqual(engine._group_hug_value(st), 1.0)

        rites = noncreature("Rites of Flourishing", "Enchantment",
                             "At the beginning of your draw step, draw an additional card.\n"
                             "Each player may play an additional land on each of their turns.")
        st2 = make_state(battlefield=[perm(rites)])
        self.assertEqual(engine._group_hug_value(st2), 1.0)

    def test_plain_creature_scores_zero(self):
        st = make_state(battlefield=[perm(make_card("Bear"))])
        self.assertEqual(engine._group_hug_value(st), 0.0)

    def test_stacks_but_is_capped(self):
        mines = [perm(noncreature(f"HM{i}", "Artifact", "Each player draws an additional card during their draw step."))
                 for i in range(10)]
        st = make_state(battlefield=mines)
        self.assertEqual(engine._group_hug_value(st), float(engine._td("group_hug_value_cap", 5.0, "table_politics")))


class BaselineGrudgeTests(unittest.TestCase):
    def test_healthy_seat_now_leans_mildly_towards_its_recent_attacker(self):
        strategy = advanced_strategy(3)
        st = make_state(opponents=[40.0, 40.0, 40.0], life=40.0)
        seats = engine._get_advanced_opponent_table(st, strategy)
        st._v4860_dmg_ledger = {0: Counter({1: 20.0})}  # a modest, realistic grudge
        st._v4860_ledger_turn = st.turn
        rng = random.Random(9)
        counts = Counter(engine._kingmaking_target(st, strategy, seats, 0, ["player", 1, 2], rng)
                          for _ in range(600))
        # biased towards seat 1, but nowhere near the kingmaking dominance
        self.assertGreater(counts[1], counts["player"])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(counts["player"], 60)  # still gets picked plenty of times
        self.assertGreater(counts[2], 60)

    def test_no_grudge_and_uniform_target_mode_stays_uniform(self):
        strategy = advanced_strategy(3)
        st = make_state(opponents=[40.0, 40.0, 40.0], life=40.0)
        seats = engine._get_advanced_opponent_table(st, strategy)
        rng = random.Random(3)
        counts = Counter(engine._kingmaking_target(st, strategy, seats, 0, ["player", 1, 2], rng)
                          for _ in range(300))
        for k in ("player", 1, 2):
            self.assertGreater(counts[k], 60)


class ThreatModeTests(unittest.TestCase):
    def test_uniform_mode_ignores_an_unequal_board_outside_kingmaking(self):
        strategy = advanced_strategy(3)
        st = make_state(opponents=[40.0, 40.0, 40.0], life=40.0)
        seats = engine._get_advanced_opponent_table(st, strategy)
        seats[2][1].board_presence = 8.0  # seat 3 has a much bigger board
        rng = random.Random(5)
        counts = Counter(engine._kingmaking_target(st, strategy, seats, 0, ["player", 1, 2], rng)
                          for _ in range(300))
        for k in ("player", 1, 2):
            self.assertGreater(counts[k], 60)  # still roughly uniform

    def test_threat_mode_biases_every_seat_toward_the_leader(self):
        engine.TABLE_DYNAMICS["table_politics"]["target_mode"] = "threat"
        try:
            strategy = advanced_strategy(3)
            st = make_state(opponents=[40.0, 40.0, 40.0], life=40.0)
            seats = engine._get_advanced_opponent_table(st, strategy)
            seats[2][1].board_presence = 8.0
            rng = random.Random(5)
            counts = Counter(engine._kingmaking_target(st, strategy, seats, 0, ["player", 1, 2], rng)
                              for _ in range(600))
            self.assertGreater(counts[2], counts["player"])
            self.assertGreater(counts[2], counts[1])
        finally:
            engine.TABLE_DYNAMICS["table_politics"]["target_mode"] = "uniform"


class GroupHugPlayedOutTests(unittest.TestCase):
    def _run(self, hug_permanent=None):
        strategy = advanced_strategy(3)
        hits = Counter()
        rng = random.Random(13)
        perms = [hug_permanent] if hug_permanent else []
        for _ in range(300):
            st = make_state(opponents=[40.0, 40.0, 40.0], life=40.0, battlefield=list(perms))
            seats = engine._get_advanced_opponent_table(st, strategy)
            seats[0][1].board_presence = 3.0
            seats[1][1].board_presence = 0.0
            seats[2][1].board_presence = 0.0
            engine._apply_advanced_multi_opponent_phase(st, strategy, rng)
            if any("combat/pressure damage" in ev for ev in st.event_log):
                hits["player"] += 1
            elif any("attacks opponent " in ev for ev in st.event_log):
                hits["seat"] += 1
        return hits

    def test_group_hug_card_reduces_how_often_the_player_is_attacked(self):
        without = self._run(None)
        mine = perm(noncreature("Howling Mine", "Artifact", "Each player draws an additional card during their draw step."))
        withhug = self._run(mine)
        self.assertLess(withhug["player"], without["player"])


if __name__ == "__main__":
    unittest.main()
