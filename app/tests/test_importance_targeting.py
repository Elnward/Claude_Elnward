"""
Unit tests for App/combat_model/importance.py (WP6, Iteration 2).

Run from the project root:
    python -m unittest tests.test_importance_targeting -v
"""
from __future__ import annotations

import dataclasses
import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App.combat_model import interaction as combat_interaction  # noqa: E402
from App.combat_model import importance as combat_importance  # noqa: E402


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


class LiveImpactScoreTests(unittest.TestCase):
    def test_zero_for_untouched_card(self):
        state = make_state()
        self.assertEqual(combat_importance.live_impact_score(state, "Nobody Cares"), 0.0)

    def test_positive_for_a_card_with_recorded_impact(self):
        state = make_state(turn=4)
        engine.record_impact(state, "Doctor Strange, Surgeon", "combat_damage", 12.0)
        score = combat_importance.live_impact_score(state, "Doctor Strange, Surgeon")
        self.assertGreater(score, 0.0)

    def test_normalized_by_turn(self):
        early = make_state(turn=1)
        late = make_state(turn=10)
        engine.record_impact(early, "X", "combat_damage", 10.0)
        engine.record_impact(late, "X", "combat_damage", 10.0)
        self.assertGreater(
            combat_importance.live_impact_score(early, "X"),
            combat_importance.live_impact_score(late, "X"),
        )


class RemovalTargetScoreTests(unittest.TestCase):
    def test_high_impact_card_scores_above_idle_card_with_same_tutor_priority(self):
        state = make_state(turn=5)
        strategy = engine.ScenarioStrategy(tutor_priority=[])
        important_card = make_card("Doctor Strange, Surgeon")
        idle_card = make_card("Redundant Filler")
        engine.record_impact(state, "Doctor Strange, Surgeon", "combat_damage", 20.0)

        important_score = combat_importance.removal_target_score(engine, state, strategy, important_card)
        idle_score = combat_importance.removal_target_score(engine, state, strategy, idle_card)
        self.assertGreater(important_score, idle_score)


class CombatBlockMultiplierTests(unittest.TestCase):
    def test_most_active_attacker_gets_the_full_bonus(self):
        state = make_state(turn=5)
        engine.record_impact(state, "MVP", "combat_damage", 30.0)
        names = ["MVP", "Sidekick"]
        mvp_mult = combat_importance.combat_block_multiplier(state, "MVP", names)
        sidekick_mult = combat_importance.combat_block_multiplier(state, "Sidekick", names)
        self.assertGreater(mvp_mult, sidekick_mult)
        self.assertGreaterEqual(sidekick_mult, 1.0)

    def test_no_bonus_when_nobody_has_done_anything_yet(self):
        state = make_state(turn=1)
        names = ["A", "B"]
        self.assertEqual(combat_importance.combat_block_multiplier(state, "A", names), 1.0)
        self.assertEqual(combat_importance.combat_block_multiplier(state, "B", names), 1.0)


class ResolveCombatInteractionImportanceIntegrationTests(unittest.TestCase):
    def test_high_impact_attacker_is_blocked_more_often_over_many_trials(self):
        state = make_state(turn=6)
        engine.record_impact(state, "MVP", "combat_damage", 40.0)

        blocked_mvp = 0
        blocked_sidekick = 0
        trials = 2000
        for i in range(trials):
            infos = [
                combat_interaction.AttackerInfo(name="MVP", power=3, lifelink=False, keywords=set()),
                combat_interaction.AttackerInfo(name="Sidekick", power=3, lifelink=False, keywords=set()),
            ]
            outcomes = combat_interaction.resolve_combat_interaction(
                "control", 6, infos, random.Random(i), state=state,
            )
            for o in outcomes:
                if o.blocked and o.name == "MVP":
                    blocked_mvp += 1
                if o.blocked and o.name == "Sidekick":
                    blocked_sidekick += 1

        self.assertGreater(blocked_mvp, blocked_sidekick)


class ChooseRemovalTargetTests(unittest.TestCase):
    """v4.8.3: choose_removal_target replaced a fully deterministic
    max(targets, key=removal_target_score) with a target_focus_chance-gated pick,
    directly in response to the v4.8.2 combat/removal diagnostics showing ~61% of
    all opponent removal in a 200-run Bilbo baseline landing on just two cards."""

    def _targets(self):
        important = engine.Permanent(card=make_card("Doctor Strange, Surgeon"), entered_turn=1, tapped=False)
        idle = engine.Permanent(card=make_card("Redundant Filler"), entered_turn=1, tapped=False)
        return [important, idle]

    def test_focus_chance_1_0_matches_old_fully_deterministic_argmax(self):
        # NOTE: combat_model/importance.py does `from .interaction import _WEIGHTS`,
        # which binds its OWN module-level `_WEIGHTS` name to the same dict object at
        # import time. Patching combat_interaction._WEIGHTS afterwards does not
        # change what combat_importance._weights() sees - the name to patch is
        # combat_importance._WEIGHTS.
        state = make_state(turn=5, battlefield=self._targets())
        strategy = engine.ScenarioStrategy(tutor_priority=[])
        engine.record_impact(state, "Doctor Strange, Surgeon", "combat_damage", 30.0)
        original = combat_importance._WEIGHTS
        try:
            combat_importance._WEIGHTS = {
                **original,
                "importance_targeting": {
                    "removal_weight": 0.8, "combat_block_weight": 0.5,
                    "target_focus_chance": 1.0,
                },
            }
            for seed in range(50):
                target = combat_importance.choose_removal_target(
                    engine, state, strategy, state.battlefield, random.Random(seed),
                )
                self.assertEqual(target.card.name, "Doctor Strange, Surgeon")
        finally:
            combat_importance._WEIGHTS = original

    def test_focus_chance_0_0_is_uniform_over_many_trials(self):
        state = make_state(turn=5, battlefield=self._targets())
        strategy = engine.ScenarioStrategy(tutor_priority=[])
        engine.record_impact(state, "Doctor Strange, Surgeon", "combat_damage", 30.0)
        original = combat_importance._WEIGHTS
        try:
            combat_importance._WEIGHTS = {
                **original,
                "importance_targeting": {
                    "removal_weight": 0.8, "combat_block_weight": 0.5,
                    "target_focus_chance": 0.0,
                },
            }
            picks = Counter()
            trials = 2000
            for seed in range(trials):
                target = combat_importance.choose_removal_target(
                    engine, state, strategy, state.battlefield, random.Random(seed),
                )
                picks[target.card.name] += 1
            important_share = picks["Doctor Strange, Surgeon"] / trials
            # Uniform over 2 targets should land close to 50%; generous bounds to
            # avoid a flaky test while still catching a broken/non-uniform draw.
            self.assertTrue(0.40 < important_share < 0.60, picks)
        finally:
            combat_importance._WEIGHTS = original

    def test_default_project_weights_no_longer_pick_the_top_target_every_time(self):
        """Regression guard for the actual shipped weight, loaded from
        Data/Models/combat_interaction_weights.json (not a mock): the important
        card must still be favored, but must NOT be picked 100% of the time
        anymore - that all-or-nothing determinism was the root cause identified
        in the v4.8.2 diagnostics."""
        state = make_state(turn=5, battlefield=self._targets())
        strategy = engine.ScenarioStrategy(tutor_priority=[])
        engine.record_impact(state, "Doctor Strange, Surgeon", "combat_damage", 30.0)
        picks = Counter()
        trials = 2000
        for seed in range(trials):
            target = combat_importance.choose_removal_target(
                engine, state, strategy, state.battlefield, random.Random(seed),
            )
            picks[target.card.name] += 1
        important_share = picks["Doctor Strange, Surgeon"] / trials
        self.assertGreater(important_share, picks["Redundant Filler"] / trials)
        self.assertLess(important_share, 0.95)


class RemovalPhaseIntegrationTests(unittest.TestCase):
    def test_apply_abstract_opponent_phase_prefers_high_impact_target_over_many_trials(self):
        important = engine.Permanent(card=make_card("Doctor Strange, Surgeon"), entered_turn=1, tapped=False)
        idle = engine.Permanent(card=make_card("Redundant Filler"), entered_turn=1, tapped=False)

        removed_important = 0
        removed_idle = 0
        trials = 300
        for i in range(trials):
            state = make_state(
                battlefield=[
                    engine.Permanent(card=make_card("Doctor Strange, Surgeon"), entered_turn=1, tapped=False),
                    engine.Permanent(card=make_card("Redundant Filler"), entered_turn=1, tapped=False),
                ],
                turn=5, life=40, opponents=[40.0],
            )
            engine.record_impact(state, "Doctor Strange, Surgeon", "combat_damage", 30.0)
            # Force removal to fire deterministically-ish across trials via profile with high removal rate.
            strategy = engine.ScenarioStrategy(opponent_profile="control", tutor_priority=[])
            engine.apply_abstract_opponent_phase(state, strategy, random.Random(i))
            names_on_field = {p.card.name for p in state.battlefield}
            if "Doctor Strange, Surgeon" not in names_on_field and any(
                c.name == "Doctor Strange, Surgeon" for c in state.graveyard
            ):
                removed_important += 1
            if "Redundant Filler" not in names_on_field and any(
                c.name == "Redundant Filler" for c in state.graveyard
            ):
                removed_idle += 1

        # Both may be removed sometimes (removal doesn't fire every trial), but the
        # high-impact card should be removed noticeably more often across many trials.
        self.assertGreater(removed_important, removed_idle)

    def test_end_to_end_removal_is_not_all_concentrated_on_the_top_target_anymore(self):
        """v4.8.3 regression guard, full engine path, real (not mocked) project
        weights: among the games where removal actually resolved and picked ONE
        of these two permanents, Doctor Strange should not be the target in
        essentially every single one - that all-or-nothing pattern is exactly
        what the v4.8.2 diagnostics flagged (~61% deck-wide removal on 2 cards)."""
        removed_important = 0
        removed_idle = 0
        trials = 400
        for i in range(trials):
            state = make_state(
                battlefield=[
                    engine.Permanent(card=make_card("Doctor Strange, Surgeon"), entered_turn=1, tapped=False),
                    engine.Permanent(card=make_card("Redundant Filler"), entered_turn=1, tapped=False),
                ],
                turn=5, life=40, opponents=[40.0],
            )
            engine.record_impact(state, "Doctor Strange, Surgeon", "combat_damage", 30.0)
            strategy = engine.ScenarioStrategy(opponent_profile="control", tutor_priority=[])
            engine.apply_abstract_opponent_phase(state, strategy, random.Random(i))
            names_on_field = {p.card.name for p in state.battlefield}
            if "Doctor Strange, Surgeon" not in names_on_field and any(
                c.name == "Doctor Strange, Surgeon" for c in state.graveyard
            ):
                removed_important += 1
            if "Redundant Filler" not in names_on_field and any(
                c.name == "Redundant Filler" for c in state.graveyard
            ):
                removed_idle += 1

        total_removed = removed_important + removed_idle
        self.assertGreater(total_removed, 0, "expected at least some removal to fire over 400 trials")
        important_share = removed_important / total_removed
        self.assertLess(
            important_share, 0.95,
            f"Doctor Strange still took {important_share:.0%} of resolved removal - "
            "target selection looks deterministic again",
        )


if __name__ == "__main__":
    unittest.main()
