"""
v4.86.0: Tischpolitik, Baustein 1 - Rache-/Kingmaking-Ziel (Docs/README.md v4.86.0).
Im Spielpfad getestet (echter GameState, echte Sitz-Tabelle, echter attack_phase/
_apply_advanced_multi_opponent_phase-Durchlauf - keine isolierten Mocks).

Run from the project root:
    python -m unittest tests.test_v4860_table_politics -v
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
from test_v4830_winrate_debug import make_card, make_state, perm, state_with, advanced_strategy  # noqa: E402


class KingmakingActiveTests(unittest.TestCase):
    def test_active_only_below_threshold_and_while_alive(self):
        st = make_state(opponents=[10.0, 40.0, 40.0])
        self.assertTrue(engine._kingmaking_active(st, 0))
        self.assertFalse(engine._kingmaking_active(st, 1))
        st.opponents[0] = 0.0
        self.assertFalse(engine._kingmaking_active(st, 0))  # already dead - takes no more actions

    def test_switch_off_disables_it(self):
        engine.TABLE_DYNAMICS.setdefault("table_politics", {})["enabled"] = False
        try:
            st = make_state(opponents=[5.0, 40.0, 40.0])
            self.assertFalse(engine._kingmaking_active(st, 0))
        finally:
            engine.TABLE_DYNAMICS["table_politics"]["enabled"] = True


class LedgerTests(unittest.TestCase):
    def test_records_and_decays_across_turns(self):
        st = make_state(opponents=[5.0, 40.0, 40.0], turn=3)
        engine._record_seat_damage(st, 0, 1, 10.0)
        self.assertAlmostEqual(engine._v4860_ledger(st)[0][1], 10.0)
        st.turn = 4
        row = engine._v4860_ledger(st)  # reading the ledger on a new turn triggers decay
        self.assertAlmostEqual(row[0][1], 6.0)  # default kingmaking_grudge_decay 0.6

    def test_player_is_not_filed_as_a_victim(self):
        st = make_state(opponents=[5.0, 40.0, 40.0])
        engine._record_seat_damage(st, "player", 0, 10.0)
        self.assertEqual(engine._v4860_ledger(st), {})


class KingmakingWeightingTests(unittest.TestCase):
    def test_revenge_and_leader_bias_the_choice(self):
        strategy = advanced_strategy(3)
        st = make_state(opponents=[5.0, 40.0, 40.0], life=40.0)
        seats = engine._get_advanced_opponent_table(st, strategy)
        seats[2][1].board_presence = 8.0  # seat 3 is the table leader (biggest board)
        st._v4860_dmg_ledger = {0: Counter({1: 50.0})}  # seat 2 hurt seat 1 badly before
        st._v4860_ledger_turn = st.turn
        rng = random.Random(7)
        counts = Counter(engine._kingmaking_target(st, strategy, seats, 0, ["player", 1, 2], rng)
                          for _ in range(400))
        self.assertGreater(counts[1], counts["player"])
        self.assertGreater(counts[2], counts["player"])

    def test_without_grudge_or_leader_it_stays_close_to_uniform(self):
        strategy = advanced_strategy(3)
        st = make_state(opponents=[5.0, 40.0, 40.0], life=40.0)
        seats = engine._get_advanced_opponent_table(st, strategy)
        rng = random.Random(3)
        counts = Counter(engine._kingmaking_target(st, strategy, seats, 0, ["player", 1, 2], rng)
                          for _ in range(300))
        for k in ("player", 1, 2):
            self.assertGreater(counts[k], 60)  # roughly 1/3 each, no target starved out


class PlayedOutTests(unittest.TestCase):
    def test_players_own_attack_is_filed_against_the_attacked_seat(self):
        strategy = advanced_strategy(3)
        bear = perm(make_card("Bear", power=6, toughness=6))
        st = state_with(bear, opponents=[10.0, 40.0, 40.0])
        engine.attack_phase(st, strategy, random.Random(1))
        ledger = engine._v4860_ledger(st)
        self.assertIn(0, ledger)  # the lowest-life seat is the focus target
        self.assertGreater(ledger[0].get("player", 0.0), 0.0)

    def test_critically_low_seat_retaliates_against_its_recent_attacker(self):
        strategy = advanced_strategy(3)
        # Seats 1 and 2 also act in the same phase call and can log their own
        # combat lines - classify by the FIRST combat-pressure line only,
        # which is seat 0's (it is processed first, i == 0).
        def first_target(ev_log):
            for ev in ev_log:
                if "attacks opponent 2 for" in ev:
                    return "seat1"
                if "attacks opponent 3 for" in ev:
                    return "seat2"
                if "combat/pressure damage" in ev:
                    return "player"
            return None

        hits = Counter()
        rng = random.Random(11)
        for _ in range(200):
            st = make_state(opponents=[6.0, 40.0, 40.0], life=40.0)
            seats = engine._get_advanced_opponent_table(st, strategy)
            seats[0][1].board_presence = 3.0
            seats[1][1].board_presence = 0.0
            seats[2][1].board_presence = 0.0
            st._v4860_dmg_ledger = {0: Counter({1: 200.0})}
            st._v4860_ledger_turn = st.turn
            engine._apply_advanced_multi_opponent_phase(st, strategy, rng)
            hits[first_target(st.event_log)] += 1
        self.assertGreater(hits["seat1"], hits["seat2"] + hits["player"])

    def test_healthy_seat_without_a_grudge_stays_uniform(self):
        # Regression: a seat above the threshold, with no grudge and the
        # default target_mode "uniform" (v4.87.0), is unaffected.
        strategy = advanced_strategy(3)

        def first_target(ev_log):
            for ev in ev_log:
                if "attacks opponent 2 for" in ev:
                    return "seat1"
                if "attacks opponent 3 for" in ev:
                    return "seat2"
                if "combat/pressure damage" in ev:
                    return "player"
            return None

        hits = Counter()
        rng = random.Random(22)
        for _ in range(200):
            st = make_state(opponents=[40.0, 40.0, 40.0], life=40.0)
            seats = engine._get_advanced_opponent_table(st, strategy)
            seats[0][1].board_presence = 3.0
            seats[1][1].board_presence = 0.0
            seats[2][1].board_presence = 0.0
            engine._apply_advanced_multi_opponent_phase(st, strategy, rng)
            hits[first_target(st.event_log)] += 1
        self.assertGreater(hits["player"], 40)
        self.assertGreater(hits["seat2"], 40)
        self.assertGreater(hits["seat1"], 40)


if __name__ == "__main__":
    unittest.main()
