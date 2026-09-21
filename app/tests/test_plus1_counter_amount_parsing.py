"""
Unit tests for v4.30.0: "+1/+1 counter" amount parsing reads the stated
number instead of counting substring occurrences.

Found via ChatGPT external review (see Docs/README.md v4.30.0 entry).
Reproduced on the live pre-fix code: `_parse_semantic_actions` set
`amount=max(1, len(re.findall(r"\+1/\+1 counter", low)))` - i.e. it counted
how many times the literal substring "+1/+1 counter" appeared in the
effect text, which only "worked" by coincidence for "a +1/+1 counter"
(exactly one substring match -> amount=1) and silently undercounted "Put
three +1/+1 counters on target creature." to amount=1 instead of 3, since
the actual stated number word was never read.

Run from the project root:
    python -m unittest tests.test_plus1_counter_amount_parsing -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


class Plus1CounterAmountParsingTests(unittest.TestCase):
    def _amount(self, effect_text: str):
        actions = engine._parse_semantic_actions(effect_text)
        matches = [a for a in actions if a.kind == "plus1_counter"]
        self.assertEqual(len(matches), 1, f"expected exactly one plus1_counter action, got {matches}")
        return matches[0].amount

    def test_a_single_counter_still_parses_as_one(self):
        self.assertEqual(self._amount("Put a +1/+1 counter on target creature."), 1)

    def test_two_counters_parses_as_two_not_one(self):
        self.assertEqual(self._amount("Put two +1/+1 counters on target creature."), 2)

    def test_three_counters_parses_as_three_not_one(self):
        self.assertEqual(self._amount("Put three +1/+1 counters on target creature."), 3)

    def test_digit_form_is_also_recognized(self):
        self.assertEqual(self._amount("Put 4 +1/+1 counters on target creature."), 4)

    def test_two_separate_clauses_are_summed(self):
        self.assertEqual(
            self._amount("Put a +1/+1 counter on this creature and a +1/+1 counter on target creature."),
            2,
        )

    def test_unquantifiable_phrasing_falls_back_to_one_not_a_guess(self):
        # "equal to X" is a real, genuinely dynamic amount this parser does
        # not attempt to compute - falling back to 1 (not inventing a
        # number) is the deliberate, disclosed simplification here.
        self.assertEqual(
            self._amount("Put a number of +1/+1 counters on target creature equal to the number of Elves you control."),
            1,
        )

    def test_end_to_end_battle_back_face_reward_gets_the_full_stated_amount(self):
        # Same shape as a real Battle back-face reward (see
        # App/engine.py::complete_battle) - confirms the fix reaches actual
        # gameplay, not just the parser's own return value.
        card = engine.Card(
            name="Test Battle", type_line="Battle — Siege",
            oracle_text="When Test Battle enters the battlefield, ...\n//\nPut three +1/+1 counters on target creature you control.",
            defense=1,
        )
        battle = engine.Permanent(card=card, entered_turn=1, tapped=False)
        target = engine.Permanent(card=engine.Card(name="Bear", type_line="Creature", power=2, toughness=2), entered_turn=1, tapped=False)
        state = engine.GameState(
            library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[battle, target],
            creature_tokens=[], food=0, treasure=0, clues=0, life=40, opponents=[40.0], turn=5,
        )
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.complete_battle(state, strategy, battle)
        self.assertEqual(target.counters, 3)


if __name__ == "__main__":
    unittest.main()
