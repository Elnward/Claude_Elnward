"""
Unit tests for v4.27.0: generic direct "each/target opponent loses N life"
sentence on an actually-cast instant/sorcery.

Found via ChatGPT external review (see Docs/README.md v4.27.0 entry).
Reproduced on the live pre-fix code: a plain Sorcery whose only effect was
"Each opponent loses 3 life." parsed as `execution_mode="exact"` via
parse_oracle_semantics (used elsewhere for model-coverage reporting) but did
NOTHING at all when actually cast - resolve_direct_spell_effects had no
branch for this pattern (only draw / scry-surveil-connive / fixed lifegain /
Food-Treasure-Clue creation), and a real Sorcery cast never routes through
the generic execute_semantic_action dispatcher at all.

Run from the project root:
    python -m unittest tests.test_direct_opponent_life_loss -v
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
        name=name, mana_cost="", mana_value=0, type_line="Sorcery", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=None, toughness=None, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0, 40.0], turn=1,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class DirectOpponentLifeLossTests(unittest.TestCase):
    def test_each_opponent_loses_n_life_is_actually_applied_on_cast(self):
        card = make_card("Drain Bolt", oracle_text="Each opponent loses 3 life.")
        state = make_state()
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.resolve_direct_spell_effects(state, strategy, card)
        self.assertEqual(state.opponents, [37.0, 37.0])

    def test_target_opponent_loses_n_life_is_actually_applied_on_cast(self):
        card = make_card("Single Drain", oracle_text="Target opponent loses 5 life.")
        state = make_state(opponents=[40.0, 20.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.resolve_direct_spell_effects(state, strategy, card)
        # lose_target_opponent picks the highest-life opponent (see its own
        # implementation, same heuristic used throughout this engine).
        self.assertEqual(state.opponents, [35.0, 20.0])

    def test_parser_already_classified_this_as_exact_before_the_fix(self):
        # Sanity check: the parser side was never the problem, only the
        # cast-resolution side was - confirms this fix targets the right gap.
        card = make_card("Drain Bolt", oracle_text="Each opponent loses 3 life.")
        abilities = engine.parse_oracle_semantics(card)
        self.assertEqual(len(abilities), 1)
        self.assertEqual(abilities[0].execution_mode, "exact")

    def test_number_word_amount_is_parsed_too(self):
        card = make_card("Word Drain", oracle_text="Each opponent loses two life.")
        state = make_state()
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.resolve_direct_spell_effects(state, strategy, card)
        self.assertEqual(state.opponents, [38.0, 38.0])

    def test_triggered_wording_is_not_misread_as_a_direct_effect(self):
        # "Whenever ... each opponent loses 1 life" is a TRIGGER, not this
        # spell's direct on-cast effect - the existing when/whenever guard
        # (shared with the lifegain/token blocks right above this one) must
        # keep excluding it here too.
        card = make_card(
            "Not Direct", type_line="Enchantment",
            oracle_text="Whenever you draw a card, each opponent loses 1 life.",
        )
        state = make_state()
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        engine.resolve_direct_spell_effects(state, strategy, card)
        self.assertEqual(state.opponents, [40.0, 40.0])


if __name__ == "__main__":
    unittest.main()
