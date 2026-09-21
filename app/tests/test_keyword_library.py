"""
Unit tests for App/keyword_library.

Run from the project root:
    python -m unittest tests.test_keyword_library -v

No Tkinter/display required - App/engine.py is GUI-free.
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
        power=1, toughness=1, commander=False,
    )
    defaults.update(overrides)
    return engine.Card(**{k: v for k, v in defaults.items() if k in field_names})


def make_state(**overrides):
    defaults = dict(
        library=[make_card(f"Lib {i}") for i in range(20)],
        hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[{"life": 40, "name": "Opp"}],
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class KeywordRegistryTests(unittest.TestCase):
    def test_all_definitions_have_a_registered_handler(self):
        for kw_id, definition in engine.keyword_registry.KEYWORDS_BY_ID.items():
            with self.subTest(keyword=kw_id):
                self.assertIn(
                    definition.handler, engine.keyword_registry._HANDLERS,
                    f"'{kw_id}' points at unregistered handler '{definition.handler}'",
                )

    def test_unknown_action_kind_is_reported_not_silently_true(self):
        state = make_state()
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(kind="totally_unknown_kind", raw="???")
        handled = engine.execute_semantic_action(state, None, source, action)
        self.assertFalse(handled)

    def test_draw_action_actually_draws(self):
        state = make_state()
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(kind="draw", amount=2, raw="Draw two cards.")
        handled = engine.execute_semantic_action(state, None, source, action)
        self.assertTrue(handled)
        self.assertEqual(len(state.hand), 2)

    def test_gain_life_action_actually_gains_life(self):
        state = make_state()
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(kind="gain_life", amount=3, raw="You gain 3 life.")
        handled = engine.execute_semantic_action(state, None, source, action)
        self.assertTrue(handled)
        self.assertEqual(state.life, 43)

    def test_plus1_counter_action_needs_and_uses_a_target(self):
        state = make_state()
        target = engine.Permanent(card=make_card("Target"), entered_turn=1)
        action = engine.SemanticAction(kind="plus1_counter", amount=2, raw="Put two +1/+1 counters.")
        handled = engine.execute_semantic_action(state, None, target, action, target=target)
        self.assertTrue(handled)
        self.assertEqual(target.counters, 2)

    def test_hobbit_placeholder_shares_the_connive_handler(self):
        connive = engine.keyword_registry.get_definition("connive")
        hobbit = engine.keyword_registry.get_definition("hobbit_second_breakfast")
        self.assertIsNotNone(hobbit)
        self.assertEqual(connive.handler, hobbit.handler)


class KeywordAliasTests(unittest.TestCase):
    """
    v4.36.0: `KeywordDefinition.aliases` was parsed from definitions.json
    into every entry but never consulted anywhere - a "declarative" field
    with zero actual effect (found via ChatGPT external review). No entry in
    the real definitions.json currently declares any aliases, so these tests
    build a small throwaway registry (module-private helpers, restored in
    tearDown) to prove the alias-resolution machinery itself actually works,
    the same way a future definitions.json entry would rely on it.
    """

    def setUp(self):
        reg = engine.keyword_registry
        self._orig_by_id = reg.KEYWORDS_BY_ID
        self._orig_aliases = reg._ALIASES_BY_ID
        gain_life = reg.KEYWORDS_BY_ID["gain_life"]
        aliased = dataclasses.replace(gain_life, id="gain_life", aliases=["lifegain", "gain_life"])
        reg.KEYWORDS_BY_ID = dict(reg.KEYWORDS_BY_ID, gain_life=aliased)
        reg._ALIASES_BY_ID = reg._build_alias_index(reg.KEYWORDS_BY_ID)

    def tearDown(self):
        reg = engine.keyword_registry
        reg.KEYWORDS_BY_ID = self._orig_by_id
        reg._ALIASES_BY_ID = self._orig_aliases

    def test_an_alias_resolves_to_the_same_definition_as_the_canonical_id(self):
        reg = engine.keyword_registry
        canonical = reg.get_definition("gain_life")
        via_alias = reg.get_definition("lifegain")
        self.assertIsNotNone(via_alias)
        self.assertIs(via_alias, canonical)

    def test_is_known_recognizes_aliases_too(self):
        self.assertTrue(engine.keyword_registry.is_known("lifegain"))

    def test_an_alias_that_collides_with_a_real_canonical_id_is_ignored(self):
        # "gain_life" itself was (deliberately, in setUp) also listed as its
        # own "alias" - the real canonical id must always win, never be
        # silently shadowed by an alias entry.
        reg = engine.keyword_registry
        self.assertIs(reg.get_definition("gain_life"), reg.KEYWORDS_BY_ID["gain_life"])

    def test_end_to_end_action_with_an_aliased_kind_actually_executes(self):
        state = make_state()
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(kind="lifegain", amount=5, raw="You gain 5 life.")
        handled = engine.execute_semantic_action(state, None, source, action)
        self.assertTrue(handled)
        self.assertEqual(state.life, 45)


class KeywordExpectsGapDiagnosticTests(unittest.TestCase):
    """
    v4.36.0: `KeywordDefinition.expects` was likewise parsed but never
    consulted - every handler call went ahead regardless of whether the
    action actually carried the fields its own handler needs, so a future
    parsing gap (an action kind that forgets to set `amount`) would
    silently call the handler with an inert default instead of surfacing
    anywhere. This is diagnostic-only (never blocks the handler), so a
    "gap" still executes exactly as before - only a metric is added.
    """

    def test_missing_amount_records_a_diagnostic_but_still_runs_the_handler(self):
        state = make_state()
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        # "draw" expects ["amount"] - leaving it at its 0.0 dataclass
        # default simulates a parser that forgot to set it.
        action = engine.SemanticAction(kind="draw", raw="Draw a card.")
        handled = engine.execute_semantic_action(state, None, source, action)
        self.assertTrue(handled, "the handler must still run even when a diagnostic fires")
        self.assertEqual(len(state.hand), 0, "amount defaulted to 0, so 0 cards were actually drawn")
        self.assertGreater(state.impact["__ENGINE__"]["keyword_expects_gap:draw:amount"], 0)

    def test_a_properly_populated_action_records_no_diagnostic(self):
        state = make_state()
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(kind="draw", amount=2, raw="Draw two cards.")
        engine.execute_semantic_action(state, None, source, action)
        self.assertNotIn("keyword_expects_gap:draw:amount", state.impact["__ENGINE__"])

    def test_target_gap_is_satisfied_by_either_the_string_field_or_the_resolved_permanent(self):
        # plus1_counter expects ["amount", "target"] - satisfied here via
        # the RESOLVED permanent parameter, even though action.target (the
        # string field) is left empty, matching how this handler actually
        # reads its target (see _expects_gaps's own docstring).
        state = make_state()
        target = engine.Permanent(card=make_card("Target"), entered_turn=1)
        action = engine.SemanticAction(kind="plus1_counter", amount=1, raw="Put a +1/+1 counter on this creature.")
        engine.execute_semantic_action(state, None, target, action, target=target)
        self.assertNotIn("keyword_expects_gap:plus1_counter:target", state.impact["__ENGINE__"])

    def test_target_gap_fires_when_neither_form_of_target_is_present(self):
        state = make_state()
        # A non-creature source referencing "target creature" with no
        # creature anywhere on the board - _semantic_target_creature's own
        # "fall back to source" rule only applies when source IS a
        # creature (see its docstring), so this genuinely resolves to no
        # target at all.
        source = engine.Permanent(card=make_card("Source", type_line="Artifact", power=None, toughness=None), entered_turn=1)
        action = engine.SemanticAction(kind="plus1_counter", amount=1, raw="Put a +1/+1 counter on target creature.")
        handled = engine.execute_semantic_action(state, None, source, action, target=None)
        self.assertFalse(handled, "plus1_counter's own handler still refuses a missing target")
        self.assertGreater(state.impact["__ENGINE__"]["keyword_expects_gap:plus1_counter:target"], 0)


class CreateTokenHandlerTests(unittest.TestCase):
    """v4.20.0 fix: a "create_token" action naming a CREATURE token (e.g.
    "3/3 Green Bear Creature", as parsed from "Create a 3/3 green Bear
    creature token.") was a complete, silent no-op - ops.create_tokens only
    mutates state for food/treasure/clue or when called with creature=True,
    and the handler never passed that. Found while testing a Battle's
    back-face reward, but the bug (and the fix) is general-purpose."""

    def test_creature_shaped_token_description_actually_creates_a_token_group(self):
        state = make_state()
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(
            kind="create_token", amount=1, token="3/3 Green Bear Creature",
            raw="Create a 3/3 green Bear creature token.",
        )
        handled = engine.execute_semantic_action(state, strategy, source, action)
        self.assertTrue(handled)
        self.assertEqual(len(state.creature_tokens), 1)
        group = state.creature_tokens[0]
        self.assertEqual(group.power, 3.0)
        self.assertEqual(group.toughness, 3.0)
        self.assertEqual(group.count, 1)
        self.assertNotIn("Creature", group.name)  # the literal word, not the type

    def test_multiple_creature_tokens_set_the_right_count(self):
        state = make_state()
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(
            kind="create_token", amount=2, token="1/1 White Soldier Creature",
            raw="Create two 1/1 white Soldier creature tokens.",
        )
        engine.execute_semantic_action(state, strategy, source, action)
        self.assertEqual(state.creature_tokens[0].count, 2)

    def test_food_token_description_still_uses_the_real_food_resource_track(self):
        # Regression guard: the fix must not touch the pre-existing,
        # already-correct Food/Treasure/Clue path.
        state = make_state()
        source = engine.Permanent(card=make_card("Source"), entered_turn=1)
        action = engine.SemanticAction(
            kind="create_token", amount=1, token="Food", raw="Create a Food token.",
        )
        engine.execute_semantic_action(state, None, source, action)
        self.assertEqual(state.food, 1)
        self.assertEqual(state.creature_tokens, [])


if __name__ == "__main__":
    unittest.main()
