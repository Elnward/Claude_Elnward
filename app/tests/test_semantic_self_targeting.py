"""
Unit tests for v4.31.0: self-referential generic-ability text ("this
creature", the card's own name, "itself") must target the SOURCE
permanent, not some other creature on the battlefield.

Found via ChatGPT external review (see Docs/README.md v4.31.0 entry).
Reproduced on the live pre-fix code: `_semantic_target_creature` excluded
`source` from its candidate list unconditionally whenever any other
creature existed, with no regard for what the ability's own text actually
said - so "{T}: Put a +1/+1 counter on this creature." on a permanent
sharing the battlefield with other creatures put the counter on a
DIFFERENT (whichever scored highest via generic_tutor_score) creature
instead of on itself.

Run from the project root:
    python -m unittest tests.test_semantic_self_targeting -v
"""
from __future__ import annotations

import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=2, toughness=2, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class SemanticTargetCreatureSelfReferenceTests(unittest.TestCase):
    def test_this_creature_phrasing_targets_the_source_itself(self):
        source = engine.Permanent(card=make_card("Self Grower"), entered_turn=1)
        # A more "tutor-priority-worthy" creature on the board that the old
        # code would have wrongly picked instead.
        other = engine.Permanent(card=make_card("Bigger Creature", roles={"finisher"}), entered_turn=1)
        state = make_state(battlefield=[source, other])
        target = engine._semantic_target_creature(state, source, "Put a +1/+1 counter on this creature.")
        self.assertIs(target, source)

    def test_the_cards_own_name_also_counts_as_self_reference(self):
        source = engine.Permanent(card=make_card("Grothama, All-Devouring"), entered_turn=1)
        other = engine.Permanent(card=make_card("Bigger Creature", roles={"finisher"}), entered_turn=1)
        state = make_state(battlefield=[source, other])
        target = engine._semantic_target_creature(
            state, source, "Put three +1/+1 counters on Grothama, All-Devouring.",
        )
        self.assertIs(target, source)

    def test_target_creature_phrasing_still_excludes_the_source(self):
        source = engine.Permanent(card=make_card("Support Creature"), entered_turn=1)
        other = engine.Permanent(card=make_card("Beneficiary", roles={"finisher"}), entered_turn=1)
        state = make_state(battlefield=[source, other])
        target = engine._semantic_target_creature(state, source, "Put a +1/+1 counter on target creature.")
        self.assertIs(target, other)

    def test_no_text_at_all_falls_back_to_the_old_exclude_source_behavior(self):
        source = engine.Permanent(card=make_card("Support Creature"), entered_turn=1)
        other = engine.Permanent(card=make_card("Beneficiary", roles={"finisher"}), entered_turn=1)
        state = make_state(battlefield=[source, other])
        target = engine._semantic_target_creature(state, source, "")
        self.assertIs(target, other)

    def test_end_to_end_execute_semantic_action_respects_self_reference(self):
        source = engine.Permanent(card=make_card("Self Grower"), entered_turn=1)
        other = engine.Permanent(card=make_card("Bigger Creature", roles={"finisher"}), entered_turn=1)
        state = make_state(battlefield=[source, other])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        action = engine.SemanticAction(
            kind="plus1_counter", amount=1, target="mentioned_creatures",
            raw="Put a +1/+1 counter on this creature.",
        )
        engine.execute_semantic_action(state, strategy, source, action)
        self.assertEqual(source.counters, 1)
        self.assertEqual(other.counters, 0)


if __name__ == "__main__":
    unittest.main()
