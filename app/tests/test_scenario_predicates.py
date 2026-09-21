"""
Unit tests for App/scenario_predicates and the Scenario-Schema v4.4 'derived' block.

Run from the project root:
    python -m unittest tests.test_scenario_predicates -v

No Tkinter/display required.
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
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0],
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class ScenarioPredicateRegistryTests(unittest.TestCase):
    def test_resource_available_untapped_creatures(self):
        untapped = engine.Permanent(card=make_card("Attacker"), entered_turn=1, tapped=False)
        tapped = engine.Permanent(card=make_card("Tapped One"), entered_turn=1, tapped=True)
        state = make_state(battlefield=[untapped, tapped])
        result = engine.scenario_predicates_registry.evaluate(
            engine, "resource_available",
            {"resource": "untapped_creatures", "min_count": 1},
            state, engine.ScenarioStrategy(),
        )
        self.assertTrue(result.satisfied)
        self.assertTrue(result.computable)

        result2 = engine.scenario_predicates_registry.evaluate(
            engine, "resource_available",
            {"resource": "untapped_creatures", "min_count": 2},
            state, engine.ScenarioStrategy(),
        )
        self.assertFalse(result2.satisfied)

    def test_opponent_life_at_or_below(self):
        state = make_state(opponents=[15.0, 40.0])
        any_low = engine.scenario_predicates_registry.evaluate(
            engine, "opponent_life_at_or_below", {"threshold": 20, "target": "any"}, state, None,
        )
        self.assertTrue(any_low.satisfied)

        each_low = engine.scenario_predicates_registry.evaluate(
            engine, "opponent_life_at_or_below", {"threshold": 20, "target": "each"}, state, None,
        )
        self.assertFalse(each_low.satisfied)

    def test_commander_damage_lethal_is_declared_but_not_computable_yet(self):
        state = make_state()
        result = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"commander": "Mabel, Heir to Cragflame"}, state, None,
        )
        self.assertFalse(result.computable)
        self.assertFalse(result.satisfied)

    def test_unknown_predicate_type_is_not_computable(self):
        state = make_state()
        result = engine.scenario_predicates_registry.evaluate(
            engine, "totally_made_up_predicate", {}, state, None,
        )
        self.assertFalse(result.computable)


class DerivedPredicatePartialCreditTests(unittest.TestCase):
    """v4.15.7 (task #18, 'derived-Teilkredit'): each handler now exposes an
    optional 0..1 `progress` (PredicateResult.effective_progress), so an
    unsatisfied-but-close derived predicate steers scenario_feasibility
    higher than an unsatisfied-and-far one - previously both scored the
    same flat 0.0."""

    def test_resource_available_progress_scales_toward_the_threshold(self):
        far = engine.scenario_predicates_registry.evaluate(
            engine, "resource_available", {"resource": "food", "min_count": 4}, make_state(food=0), None,
        )
        close = engine.scenario_predicates_registry.evaluate(
            engine, "resource_available", {"resource": "food", "min_count": 4}, make_state(food=3), None,
        )
        met = engine.scenario_predicates_registry.evaluate(
            engine, "resource_available", {"resource": "food", "min_count": 4}, make_state(food=4), None,
        )
        self.assertFalse(far.satisfied)
        self.assertFalse(close.satisfied)
        self.assertEqual(far.effective_progress, 0.0)
        self.assertAlmostEqual(close.effective_progress, 0.75)
        self.assertLess(far.effective_progress, close.effective_progress)
        self.assertEqual(met.effective_progress, 1.0)

    def test_opponent_life_at_or_below_progress_scales_as_life_drops(self):
        far = engine.scenario_predicates_registry.evaluate(
            engine, "opponent_life_at_or_below", {"threshold": 10, "target": "any"}, make_state(opponents=[40.0]), None,
        )
        close = engine.scenario_predicates_registry.evaluate(
            engine, "opponent_life_at_or_below", {"threshold": 10, "target": "any"}, make_state(opponents=[12.0]), None,
        )
        self.assertFalse(far.satisfied)
        self.assertFalse(close.satisfied)
        self.assertLess(far.effective_progress, close.effective_progress)
        self.assertGreater(close.effective_progress, 0.8)

    def test_commander_damage_lethal_progress_scales_with_accumulated_damage(self):
        commander = engine.Permanent(
            card=make_card("Mabel, Heir to Cragflame", power=5, toughness=5, commander=True),
            entered_turn=1,
        )
        state_fresh = make_state(battlefield=[commander], opponents=[40.0])
        state_fresh.commander_damage_dealt = {("Mabel, Heir to Cragflame", 0): 0.0}
        fresh = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"commander": "Mabel, Heir to Cragflame", "target": "any"}, state_fresh, None,
        )

        state_close = make_state(battlefield=[commander], opponents=[40.0])
        state_close.commander_damage_dealt = {("Mabel, Heir to Cragflame", 0): 18.0}  # only 3 more needed, power 5 already clears it
        close = engine.scenario_predicates_registry.evaluate(
            engine, "commander_damage_lethal", {"commander": "Mabel, Heir to Cragflame", "target": "any"}, state_close, None,
        )
        self.assertTrue(close.satisfied)
        self.assertEqual(close.effective_progress, 1.0)
        self.assertLess(fresh.effective_progress, close.effective_progress)

    def test_scenario_feasibility_prefers_a_closer_unsatisfied_derived_state(self):
        raw = {
            "name": "Grind opponent low",
            "kind": "Win Condition",
            "derived": [
                {"type": "opponent_life_at_or_below", "params": {"threshold": 5, "target": "any"}},
            ],
        }
        scenario = engine.normalize_scenario(raw)
        strategy = engine.ScenarioStrategy()

        far_state = make_state(opponents=[40.0])
        close_state = make_state(opponents=[7.0])
        far_score = engine.scenario_feasibility(far_state, strategy, scenario)
        close_score = engine.scenario_feasibility(close_state, strategy, scenario)
        self.assertLess(far_score, close_score)


class ScenarioDerivedBlockTests(unittest.TestCase):
    def test_v43_scenario_without_derived_is_unaffected(self):
        """Backward compatibility: a plain v4.3 scenario (no 'derived') behaves identically."""
        raw = {
            "name": "Plain v4.3 scenario",
            "kind": "Setup",
            "thresholds": {"life": 10},
        }
        scenario = engine.normalize_scenario(raw)
        self.assertEqual(scenario.get("derived"), [])

        state = make_state(life=5)
        status = engine.scenario_status(state, engine.ScenarioStrategy(), scenario)
        self.assertFalse(status["reached"])  # life 5 < 10
        self.assertTrue(status["derived_met"])
        self.assertTrue(status["derived_computable"])

        state2 = make_state(life=15)
        status2 = engine.scenario_status(state2, engine.ScenarioStrategy(), scenario)
        self.assertTrue(status2["reached"])

    def test_derived_block_gates_reached(self):
        raw = {
            "name": "Needs 2 untapped creatures",
            "kind": "Win Condition",
            "derived": [
                {"type": "resource_available", "params": {"resource": "untapped_creatures", "min_count": 2}},
            ],
        }
        scenario = engine.normalize_scenario(raw)

        state_short = make_state(battlefield=[
            engine.Permanent(card=make_card("A"), entered_turn=1, tapped=False),
        ])
        status_short = engine.scenario_status(state_short, engine.ScenarioStrategy(), scenario)
        self.assertFalse(status_short["reached"])
        self.assertFalse(status_short["derived_met"])

        state_enough = make_state(battlefield=[
            engine.Permanent(card=make_card("A"), entered_turn=1, tapped=False),
            engine.Permanent(card=make_card("B"), entered_turn=1, tapped=False),
        ])
        status_enough = engine.scenario_status(state_enough, engine.ScenarioStrategy(), scenario)
        self.assertTrue(status_enough["reached"])
        self.assertTrue(status_enough["derived_met"])

    def test_derived_block_survives_save_and_load_roundtrip(self, tmp_path=None):
        import json
        raw = {
            "name": "Roundtrip check",
            "kind": "Win Condition",
            "derived": [
                {"type": "opponent_life_at_or_below", "params": {"threshold": 5, "target": "any"}},
            ],
        }
        scenario = engine.normalize_scenario(raw)
        tmp_file = ROOT / "tests" / "_tmp_scenario_roundtrip.json"
        try:
            engine.save_scenarios(tmp_file, [scenario])
            loaded = engine.load_scenarios(tmp_file)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["derived"], scenario["derived"])
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_not_computable_predicate_does_not_falsely_satisfy_or_silently_pass(self):
        raw = {
            "name": "Mabel placeholder",
            "kind": "Win Condition",
            "derived": [
                {"type": "commander_damage_lethal", "params": {"commander": "Mabel, Heir to Cragflame"}},
            ],
        }
        scenario = engine.normalize_scenario(raw)
        state = make_state()
        status = engine.scenario_status(state, engine.ScenarioStrategy(), scenario)
        self.assertFalse(status["reached"])
        self.assertFalse(status["derived_computable"])
        self.assertTrue(any("nicht berechenbar" in m for m in status["missing"]))


class ScenarioSchemaDocStaysInSyncTests(unittest.TestCase):
    """v4.15.8 (task #19, internal verification pass): the human/AI-facing
    SCENARIO_SCHEMA.md (engine.scenario_json_schema_markdown, written into
    every result dir) was found to still describe the pre-'derived'-block
    v4.2 schema, with no mention of the v4.4 predicate system at all - a
    real doc/code drift, not just a missing feature. Fixed in the same
    version as this test. This guard is deliberately shallow (it does not
    re-derive full English prose from definitions.json) but catches the
    concrete failure mode that actually happened: a new predicate type
    landing in definitions.json/handlers.py without a matching mention in
    the markdown doc a human or an AI scenario author actually reads."""

    def test_doc_mentions_the_derived_block(self):
        doc = engine.scenario_json_schema_markdown()
        self.assertIn("derived", doc)

    def test_doc_lists_every_implemented_predicate_type(self):
        doc = engine.scenario_json_schema_markdown()
        implemented = engine.scenario_predicates_registry.list_implemented_predicates()
        self.assertGreater(len(implemented), 0)
        for predicate_id in implemented:
            self.assertIn(
                f"`{predicate_id}`", doc,
                f"SCENARIO_SCHEMA.md doesn't mention implemented predicate '{predicate_id}'",
            )


class ExistingBilboFileStillLoadsTests(unittest.TestCase):
    def test_bilbo_win_conditions_json_still_loads_and_normalizes(self):
        path = ROOT / "Data" / "Scenarios" / "bilbo_win_conditions.json"
        if not path.exists():
            self.skipTest("bilbo_win_conditions.json not present in this checkout")
        scenarios = engine.load_scenarios(path)
        self.assertGreater(len(scenarios), 0)
        for sc in scenarios:
            self.assertIn("derived", sc)
            self.assertEqual(sc["derived"], [])  # legacy file has no derived conditions


if __name__ == "__main__":
    unittest.main()
