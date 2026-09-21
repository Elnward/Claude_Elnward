"""
Unit/integration tests for v4.15.0 (WP10): targeted attack-priority logic
for commander damage (Mabel's "21 commander damage on one fixed target"
Voltron plan) and steering-aware 'derived' predicates for Win Conditions
built primarily around dynamic/computed conditions (the real Aziza
Alpha-Strike scenario: tap 3 creatures + an X-spell reaches lethal).

Covers:
  1. attack_phase respects Strategy.voltron_target_index for COMMANDER
     damage specifically - directing it at a fixed opponent instead of the
     pre-existing "whoever currently has the most life" heuristic - while
     leaving non-commander damage and the unset-default case unchanged
     (regression guard against the pre-v4.15.0 behavior).
  2. Falls back to the old highest-life heuristic when the fixed target is
     already eliminated (0 life), so a stale/invalid Voltron target can
     never waste damage or crash.
  3. scenario_feasibility now credits a scenario's 'derived' block (until
     this version, evaluated only for "reached" status, never for
     STEERING) - a scenario built with no plain requirements/thresholds/
     mana beyond a single card gets real, non-trivial feasibility once its
     derived predicates start becoming true.
  4. The actual Aziza Alpha-Strike and Mabel Voltron scenario definitions
     (Data/Scenarios/aziza_alpha_strike_v1.json,
     Data/Scenarios/mabel_voltron_v1.json) load, normalize, and round-trip
     correctly, and behave sensibly (higher feasibility when set up, lower
     when not) against real constructed game states using real cards from
     the project's own Aziza V2 / Mice with Swords decks.

Run from the project root:
    python -m unittest tests.test_wp10_voltron_and_alpha_strike -v
"""
from __future__ import annotations

import dataclasses
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App.combat_model import interaction as combat_interaction  # noqa: E402

_SCRYFALL_CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"

ALWAYS_UNBLOCKED_WEIGHTS = {
    "profiles": {"goldfish": {"block_rate_base": 0.0, "trade_rate_given_blocked": 0.0}},
    "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
    "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
    "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
    "importance_targeting": {"removal_weight": 0.0, "combat_block_weight": 0.0},
}


def _with_deterministic_weights(fn):
    original = combat_interaction._WEIGHTS
    try:
        combat_interaction._WEIGHTS = ALWAYS_UNBLOCKED_WEIGHTS
        fn()
    finally:
        combat_interaction._WEIGHTS = original


def _load_real_card(name: str, *, commander: bool = False) -> engine.Card:
    with _SCRYFALL_CACHE_PATH.open("r", encoding="utf-8") as f:
        cache = json.load(f)
    for obj in cache.values():
        if isinstance(obj, dict) and obj.get("name") == name:
            entry = engine.DeckEntry(name=name)
            card = engine.card_from_scryfall(entry, obj, commander_name=name if commander else None)
            return dataclasses.replace(card, commander=commander)
    raise AssertionError(f"{name!r} not found in {_SCRYFALL_CACHE_PATH}")


def make_card(name="Test Card", **overrides):
    field_names = {f.name for f in dataclasses.fields(engine.Card)}
    defaults = dict(
        name=name, mana_cost="", mana_value=0, type_line="Creature", oracle_text="",
        color_identity=set(), produced_mana=set(), keywords=set(), roles=set(),
        power=5, toughness=5, commander=False,
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


class VoltronFixedTargetCommanderDamageTests(unittest.TestCase):
    def test_default_unset_target_keeps_the_original_highest_life_heuristic(self):
        def run():
            commander = engine.Permanent(card=make_card("Voltron Commander", power=6, commander=True), entered_turn=1, tapped=False)
            state = make_state(battlefield=[commander], opponents=[10.0, 40.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive")
            self.assertIsNone(strategy.voltron_target_index)
            engine.attack_phase(state, strategy, random.Random(1))
            # Unset target: old behavior - damage goes to whoever has the most life (opponent 1).
            self.assertEqual(state.commander_damage_dealt.get(("Voltron Commander", 1), 0.0), 6.0)
            self.assertEqual(state.commander_damage_dealt.get(("Voltron Commander", 0), 0.0), 0.0)
        _with_deterministic_weights(run)

    def test_fixed_target_overrides_the_highest_life_heuristic_for_commander_damage(self):
        def run():
            commander = engine.Permanent(card=make_card("Voltron Commander", power=6, commander=True), entered_turn=1, tapped=False)
            # Opponent 1 has much higher life than opponent 0 - the old
            # heuristic would target opponent 1. voltron_target_index=0
            # must redirect commander damage to opponent 0 instead.
            state = make_state(battlefield=[commander], opponents=[10.0, 40.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive", voltron_target_index=0)
            engine.attack_phase(state, strategy, random.Random(1))
            self.assertEqual(state.commander_damage_dealt.get(("Voltron Commander", 0), 0.0), 6.0)
            self.assertEqual(state.commander_damage_dealt.get(("Voltron Commander", 1), 0.0), 0.0)
            self.assertEqual(state.opponents[0], 4.0)
        _with_deterministic_weights(run)

    def test_fixed_target_falls_back_to_highest_life_once_that_opponent_is_eliminated(self):
        def run():
            commander = engine.Permanent(card=make_card("Voltron Commander", power=6, commander=True), entered_turn=1, tapped=False)
            # Target opponent 0 is already at 0 life (eliminated) - must not
            # waste damage there; falls back to opponent 1 (highest life).
            state = make_state(battlefield=[commander], opponents=[0.0, 40.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive", voltron_target_index=0)
            engine.attack_phase(state, strategy, random.Random(1))
            self.assertEqual(state.commander_damage_dealt.get(("Voltron Commander", 1), 0.0), 6.0)
            self.assertEqual(state.commander_damage_dealt.get(("Voltron Commander", 0), 0.0), 0.0)
        _with_deterministic_weights(run)

    def test_fixed_target_does_not_affect_noncommander_damage(self):
        def run():
            commander = engine.Permanent(card=make_card("Voltron Commander", power=6, commander=True), entered_turn=1, tapped=False)
            sidekick = engine.Permanent(card=make_card("Sidekick", power=4, commander=False), entered_turn=1, tapped=False)
            state = make_state(battlefield=[commander, sidekick], opponents=[10.0, 40.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive", voltron_target_index=0)
            engine.attack_phase(state, strategy, random.Random(1))
            # Commander damage goes to the fixed target (opponent 0).
            self.assertEqual(state.commander_damage_dealt.get(("Voltron Commander", 0), 0.0), 6.0)
            # Sidekick's non-commander damage is untouched by the fixed
            # target - it still chases the highest-life opponent. After the
            # commander's 6 damage, opponent 0 is at 4 and opponent 1 at 40,
            # so the sidekick's damage should land on opponent 1.
            self.assertEqual(state.opponents[1], 36.0)
        _with_deterministic_weights(run)

    def test_repeatedly_hitting_the_fixed_target_can_reach_21_and_eliminate_it(self):
        def run():
            # entered_turn=0 so the creature is never summoning-sick against
            # make_state()'s default turn=5, across every repeated attack.
            # Both opponents start with plenty of life so normal combat-damage
            # subtraction alone never zeroes out the fixed target before the
            # commander-damage LEDGER itself crosses 21 - isolating the
            # >=21-forces-to-0 elimination rule from ordinary life loss.
            commander = engine.Permanent(card=make_card("Voltron Commander", power=7, commander=True), entered_turn=0, tapped=False)
            state = make_state(battlefield=[commander], opponents=[100.0, 100.0])
            strategy = engine.ScenarioStrategy(opponent_profile="goldfish", commander_posture="aggressive", voltron_target_index=0)
            # Three attacks of 7 = 21 exactly, all directed at opponent 0
            # despite opponent 1 always having far more life.
            for _ in range(3):
                for p in state.battlefield:
                    p.tapped = False
                engine.attack_phase(state, strategy, random.Random(1))
            self.assertGreaterEqual(state.commander_damage_dealt.get(("Voltron Commander", 0), 0.0), 21.0)
            self.assertEqual(state.opponents[0], 0.0)
        _with_deterministic_weights(run)


class ScenarioFeasibilityCreditsDerivedPredicatesTests(unittest.TestCase):
    """Before v4.15.0, scenario_feasibility (the steering heuristic) never
    looked at the 'derived' block at all - only requirements/packages/
    thresholds/mana. A Win Condition built primarily around derived
    predicates (like the real Aziza Alpha-Strike scenario below) would get
    feasibility ONLY from its plain requirements, so the engine would never
    deliberately steer toward assembling it."""

    def setUp(self):
        self.strategy = engine.ScenarioStrategy(opponent_profile="goldfish")

    def test_scenario_with_no_derived_block_is_unaffected(self):
        # Backward compatibility: a scenario without 'derived' behaves
        # exactly as before (feasibility comes only from other parts).
        scenario = engine.normalize_scenario({
            "name": "Plain", "kind": "Setup",
            "requirements": [{"card": "Sol Ring", "zones": ["battlefield"]}],
        })
        sol_ring = engine.Permanent(card=make_card("Sol Ring"), entered_turn=1, tapped=False)
        state = make_state(battlefield=[sol_ring])
        self.assertEqual(engine.scenario_feasibility(state, self.strategy, scenario), 1.0)

    def test_satisfied_derived_predicate_raises_feasibility(self):
        scenario = engine.normalize_scenario({
            "name": "Derived only", "kind": "Win Condition",
            "derived": [{"type": "resource_available", "params": {"resource": "untapped_creatures", "min_count": 3}}],
        })
        creatures = [engine.Permanent(card=make_card(f"C{i}"), entered_turn=1, tapped=False) for i in range(3)]
        satisfied_state = make_state(battlefield=creatures)
        unsatisfied_state = make_state(battlefield=creatures[:1])
        satisfied_score = engine.scenario_feasibility(satisfied_state, self.strategy, scenario)
        unsatisfied_score = engine.scenario_feasibility(unsatisfied_state, self.strategy, scenario)
        self.assertGreater(satisfied_score, unsatisfied_score)
        self.assertEqual(satisfied_score, 1.0)

    def test_not_computable_derived_predicate_counts_as_not_yet_satisfied(self):
        # commander_damage_lethal is not-computable with no commander on the
        # battlefield - must count as 0.0 credit, not crash and not silently
        # count as satisfied.
        scenario = engine.normalize_scenario({
            "name": "Commander damage WC", "kind": "Win Condition",
            "derived": [{"type": "commander_damage_lethal", "params": {"target": "any"}}],
        })
        state = make_state(battlefield=[])
        self.assertEqual(engine.scenario_feasibility(state, self.strategy, scenario), 0.0)


class AzizaAlphaStrikeScenarioTests(unittest.TestCase):
    """The real, shipped Aziza Alpha-Strike scenario definition
    (Data/Scenarios/aziza_alpha_strike_v1.json), built from Aziza, Mage
    Tower Captain's real "tap three creatures to copy" cost and Banefire,
    both real cards from the project's own Aziza V2 deck."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "Data" / "Scenarios" / "aziza_alpha_strike_v1.json"
        cls.raw_scenarios = json.loads(path.read_text(encoding="utf-8"))

    def _find(self, name_fragment):
        for raw in self.raw_scenarios:
            if name_fragment.lower() in raw.get("name", "").lower():
                return engine.normalize_scenario(raw)
        raise AssertionError(f"no scenario matching {name_fragment!r} in the shipped file")

    def test_banefire_scenario_normalizes_as_a_win_condition_with_real_requirements(self):
        sc = self._find("Banefire")
        self.assertEqual(sc["kind"], "Win Condition")
        req_cards = {r["card"] for r in sc["requirements"]}
        self.assertIn(engine.AZIZA_NAME, req_cards)
        derived_types = {d["type"] for d in sc["derived"]}
        self.assertIn("resource_available", derived_types)
        self.assertIn("x_spell_lethal", derived_types)

    def test_scenario_round_trips_through_save_and_load(self):
        import tempfile
        sc = self._find("Banefire")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "roundtrip.json"
            engine.save_scenarios(path, [sc])
            loaded = engine.load_scenarios(path)
        self.assertEqual(loaded[0]["derived"], sc["derived"])
        self.assertEqual(loaded[0]["requirements"], sc["requirements"])

    def test_fully_set_up_board_scores_high_feasibility(self):
        sc = self._find("Banefire")
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        aziza = engine.Permanent(card=_load_real_card(engine.AZIZA_NAME, commander=True), entered_turn=1, tapped=False)
        helpers = [engine.Permanent(card=make_card(f"Helper {i}"), entered_turn=1, tapped=False) for i in range(3)]
        banefire = _load_real_card("Banefire")

        orig_mana = engine.available_mana_value
        try:
            engine.available_mana_value = lambda state, strategy: 20
            state = make_state(battlefield=[aziza] + helpers, hand=[banefire], opponents=[10.0])
            score = engine.scenario_feasibility(state, strategy, sc)
        finally:
            engine.available_mana_value = orig_mana

        self.assertGreater(score, 0.8, "Aziza in play, 3 untapped creatures, Banefire in hand and enough mana should score near-maximal feasibility")

    def test_missing_pieces_score_lower_feasibility(self):
        sc = self._find("Banefire")
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        state = make_state(battlefield=[], hand=[], opponents=[10.0])
        score = engine.scenario_feasibility(state, strategy, sc)
        self.assertLess(score, 0.3)


class MabelVoltronScenarioTests(unittest.TestCase):
    """The real, shipped Mabel Voltron scenario definition
    (Data/Scenarios/mabel_voltron_v1.json), built around
    commander_damage_lethal against Mabel, Heir to Cragflame - a real card
    from the project's own Mice with Swords deck."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "Data" / "Scenarios" / "mabel_voltron_v1.json"
        cls.raw_scenarios = json.loads(path.read_text(encoding="utf-8"))
        cls.sc = engine.normalize_scenario(cls.raw_scenarios[0])

    def test_scenario_is_a_win_condition_requiring_mabel(self):
        self.assertEqual(self.sc["kind"], "Win Condition")
        req_cards = {r["card"] for r in self.sc["requirements"]}
        self.assertIn("Mabel, Heir to Cragflame", req_cards)
        derived_types = {d["type"] for d in self.sc["derived"]}
        self.assertIn("commander_damage_lethal", derived_types)

    def test_lethal_commander_power_scores_full_derived_credit(self):
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        mabel = engine.Permanent(card=_load_real_card("Mabel, Heir to Cragflame", commander=True), entered_turn=1, tapped=False)
        # Give Mabel enough power via a board modifier to be lethal for the
        # remaining 21 against a target with no prior commander damage.
        big_mabel = engine.Permanent(card=dataclasses.replace(mabel.card, power=21.0), entered_turn=1, tapped=False)
        state = make_state(battlefield=[big_mabel], opponents=[40.0])
        score = engine.scenario_feasibility(state, strategy, self.sc)
        self.assertGreater(score, 0.5)

    def test_end_to_end_attack_with_fixed_target_moves_toward_the_scenarios_own_win_condition(self):
        def run():
            mabel = engine.Permanent(card=dataclasses.replace(_load_real_card("Mabel, Heir to Cragflame", commander=True), power=21.0), entered_turn=0, tapped=False)
            state = make_state(battlefield=[mabel], opponents=[10.0, 40.0])
            strategy = engine.ScenarioStrategy(
                opponent_profile="goldfish", commander_posture="aggressive", voltron_target_index=0,
            )
            engine.attack_phase(state, strategy, random.Random(1))
            self.assertEqual(state.opponents[0], 0.0)
            self.assertGreaterEqual(state.commander_damage_dealt.get(("Mabel, Heir to Cragflame", 0), 0.0), 21.0)
        _with_deterministic_weights(run)


if __name__ == "__main__":
    unittest.main()
