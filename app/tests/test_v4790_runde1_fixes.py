"""
v4.79.0 "Runde 1": generic multi-keyword static-grant fix, model_gaps
false-alarm filter (mana abilities / bare keyword lines), and the new
board_damage_lethal derived predicate (original "Punkt 6": alpha-strike /
token-swarm win conditions against the opponent's CURRENT life, not a
fixed assumed-40).

Run from the project root:
    python -m unittest tests.test_v4790_runde1_fixes -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def make_card(name="Test Card", **overrides):
    import dataclasses
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
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class MultiKeywordGrantTests(unittest.TestCase):
    """Before this fix, 'creatures you control (?:gain|have) {kw}' was
    matched once per keyword against the FULL effect text, so only the
    keyword immediately adjacent to 'have'/'gain' ever matched - a
    comma-separated grant list (the normal templating for this effect,
    not a one-card quirk: 22 cards in this project's own reference set
    use it) silently lost every keyword after the first."""

    def test_akromas_memorial_grants_every_listed_keyword(self):
        actions = engine._parse_semantic_actions(
            "Creatures you control have flying, first strike, vigilance, "
            "trample, haste, and protection from black and from red."
        )
        granted = {a.keyword for a in actions if a.kind == "grant_team_keyword"}
        self.assertEqual(
            granted,
            {"flying", "first strike", "vigilance", "trample", "haste", "protection"},
        )

    def test_single_keyword_grant_still_works(self):
        actions = engine._parse_semantic_actions("Creatures you control have flying.")
        granted = {a.keyword for a in actions if a.kind == "grant_team_keyword"}
        self.assertEqual(granted, {"flying"})

    def test_unrelated_later_keyword_is_not_pulled_in(self):
        # The keyword-list clause is captured only up to the next '.'/';',
        # so a keyword mentioned in a LATER, unrelated sentence must not
        # be swept in.
        actions = engine._parse_semantic_actions(
            "Creatures you control have trample. Whenever a creature you "
            "control with trample deals combat damage, you gain 1 life."
        )
        granted = [a.keyword for a in actions if a.kind == "grant_team_keyword"]
        self.assertEqual(granted, ["trample"])

    def test_no_false_positive_without_the_grant_phrase(self):
        actions = engine._parse_semantic_actions("Target creature gets +1/+1.")
        granted = [a for a in actions if a.kind == "grant_team_keyword"]
        self.assertEqual(granted, [])


class FalseAlarmReviewLineTests(unittest.TestCase):
    """A 'review' execution-tier line that is actually fully handled
    elsewhere (a mana ability via parse_add_mana_options, or a card's own
    bare static-keyword line via its Card.keywords/effective_keywords_in_
    state) must not count as 'not simulated' - it was a labeling
    artifact of the line-by-line SemanticAbility tier system, which has
    no action kind for either shape."""

    def test_plain_mana_ability_is_a_false_alarm(self):
        self.assertTrue(engine._is_false_alarm_review_line("{T}: Add {G}."))
        self.assertTrue(engine._is_false_alarm_review_line("{T}: Add one mana of any color."))

    def test_bare_keyword_lines_are_false_alarms(self):
        self.assertTrue(engine._is_false_alarm_review_line("Flying"))
        self.assertTrue(engine._is_false_alarm_review_line("Trample, haste"))
        self.assertTrue(engine._is_false_alarm_review_line("Ward 2"))
        self.assertTrue(engine._is_false_alarm_review_line(
            "Flying, first strike, vigilance, trample, haste, and protection from black and from red"
        ))

    def test_a_real_unmodeled_line_is_not_a_false_alarm(self):
        self.assertFalse(engine._is_false_alarm_review_line(
            "Whenever this creature attacks, draw a card."
        ))
        self.assertFalse(engine._is_false_alarm_review_line("Target creature gets +1/+1."))

    def test_coverage_rows_do_not_flag_a_mana_dork_as_review(self):
        deck = [make_card("Llanowar Elves", oracle_text="{T}: Add {G}.")]
        rows = engine.card_model_coverage_rows(deck)
        row = next(r for r in rows if r["Name"] == "Llanowar Elves")
        self.assertNotIn("review", row["Semantic execution mix"])

    def test_coverage_rows_still_flag_a_real_unmodeled_ability(self):
        deck = [make_card(
            "Mystery Card",
            oracle_text="You may play an additional land this turn.",
        )]
        rows = engine.card_model_coverage_rows(deck)
        row = next(r for r in rows if r["Name"] == "Mystery Card")
        self.assertIn("review", row["Semantic execution mix"])


class BoardDamageLethalTests(unittest.TestCase):
    """The new board_damage_lethal derived predicate (Runde 1, original
    Punkt 6): alpha-strike/token-swarm win conditions checked against the
    opponent's CURRENT life, not a fixed assumed-40 starting life."""

    def _no_block_weights(self):
        return {
            "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
            "evasion_keyword_multiplier": {},
            "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
            "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
            "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
        }

    def test_lethal_against_an_already_damaged_opponent_not_just_fresh_40(self):
        from App.combat_model import interaction as combat_interaction
        original = combat_interaction._WEIGHTS
        combat_interaction._WEIGHTS = self._no_block_weights()
        try:
            attacker = engine.Permanent(card=make_card("Big Guy", power=12, toughness=12), entered_turn=1, tapped=False)
            # Against a fresh opponent (40 life) 12 power is NOT lethal ...
            fresh = make_state(battlefield=[attacker], opponents=[40.0])
            result_fresh = engine.scenario_predicates_registry.evaluate(
                engine, "board_damage_lethal", {"target": "any"}, fresh, engine.ScenarioStrategy(),
            )
            self.assertFalse(result_fresh.satisfied)

            # ... but against the SAME board, an opponent already chipped down
            # to 10 life IS lethal. This is exactly the case that a fixed
            # "total power >= 40" requirement would have missed entirely.
            damaged = make_state(battlefield=[attacker], opponents=[10.0])
            result_damaged = engine.scenario_predicates_registry.evaluate(
                engine, "board_damage_lethal", {"target": "any"}, damaged, engine.ScenarioStrategy(),
            )
            self.assertTrue(result_damaged.satisfied)
        finally:
            combat_interaction._WEIGHTS = original

    def test_each_target_requires_every_opponent_down(self):
        from App.combat_model import interaction as combat_interaction
        original = combat_interaction._WEIGHTS
        combat_interaction._WEIGHTS = self._no_block_weights()
        try:
            attacker = engine.Permanent(card=make_card("Big Guy", power=12, toughness=12), entered_turn=1, tapped=False)
            state = make_state(battlefield=[attacker], opponents=[10.0, 40.0])
            any_result = engine.scenario_predicates_registry.evaluate(
                engine, "board_damage_lethal", {"target": "any"}, state, engine.ScenarioStrategy(),
            )
            each_result = engine.scenario_predicates_registry.evaluate(
                engine, "board_damage_lethal", {"target": "each"}, state, engine.ScenarioStrategy(),
            )
            self.assertTrue(any_result.satisfied)
            self.assertFalse(each_result.satisfied)
        finally:
            combat_interaction._WEIGHTS = original

    def test_no_attacker_is_not_satisfied_and_not_computable_error(self):
        state = make_state(battlefield=[], opponents=[20.0])
        result = engine.scenario_predicates_registry.evaluate(
            engine, "board_damage_lethal", {"target": "any"}, state, engine.ScenarioStrategy(),
        )
        self.assertFalse(result.satisfied)
        self.assertTrue(result.computable)  # a real "no" answer, not "can't tell"

    def test_target_already_at_zero_is_trivially_satisfied(self):
        state = make_state(battlefield=[], opponents=[0.0])
        result = engine.scenario_predicates_registry.evaluate(
            engine, "board_damage_lethal", {"target": "any"}, state, engine.ScenarioStrategy(),
        )
        self.assertTrue(result.satisfied)

    def test_is_registered_as_target_aware_for_win_condition_scope_reporting(self):
        # v4.65.2's target-scope machinery (surfaced in the UI as the
        # "single target" pill / scope note) must know about this new
        # predicate too, or a board_damage_lethal win condition would be
        # silently left out of that reporting.
        self.assertIn("board_damage_lethal", engine._WC_TARGET_AWARE_PREDICATE_TYPES)


if __name__ == "__main__":
    unittest.main()
