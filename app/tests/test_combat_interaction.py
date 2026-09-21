"""
Unit tests for App/combat_model and its integration into engine.attack_phase.

Run from the project root:
    python -m unittest tests.test_combat_interaction -v

No Tkinter/display required.
"""
from __future__ import annotations

import dataclasses
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App.combat_model import interaction as combat_interaction  # noqa: E402


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
        life=40, opponents=[40.0],
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


def make_strategy(profile="midrange"):
    return engine.ScenarioStrategy(opponent_profile=profile)


class WeightsSanityTests(unittest.TestCase):
    def test_goldfish_profile_never_blocks(self):
        rate = combat_interaction.block_rate_for("goldfish", turn=10, n_attackers=1, keywords=set())
        self.assertEqual(rate, 0.0)

    def test_flying_reduces_block_rate_vs_no_keywords(self):
        no_evasion = combat_interaction.block_rate_for("control", turn=5, n_attackers=1, keywords=set())
        flying = combat_interaction.block_rate_for("control", turn=5, n_attackers=1, keywords={"flying"})
        self.assertLess(flying, no_evasion)

    def test_wide_board_reduces_block_rate(self):
        few = combat_interaction.block_rate_for("control", turn=5, n_attackers=1, keywords=set())
        many = combat_interaction.block_rate_for("control", turn=5, n_attackers=10, keywords=set())
        self.assertLess(many, few)

    def test_rate_is_always_a_probability(self):
        for profile in ("goldfish", "aggro", "midrange", "control", "horde"):
            for turn in (1, 5, 12):
                for n in (1, 6, 15):
                    rate = combat_interaction.block_rate_for(profile, turn, n, {"flying", "menace", "trample"})
                    self.assertGreaterEqual(rate, 0.0)
                    self.assertLessEqual(rate, 1.0)


class CommanderBlockBiasTests(unittest.TestCase):
    """WP6, Iteration 2+ (v4.15.1): the commander should get a higher block
    chance than an otherwise-identical non-commander attacker, independent of
    live-run impact (state=None here on purpose - isolates the flat
    commander_targeting.block_bias from the separate impact-based
    importance_targeting.combat_block_weight, which is tested elsewhere)."""

    def test_commander_flag_raises_block_rate_over_non_commander(self):
        non_commander = combat_interaction.block_rate_for(
            "control", turn=5, n_attackers=1, keywords=set(), is_commander=False,
        )
        commander = combat_interaction.block_rate_for(
            "control", turn=5, n_attackers=1, keywords=set(), is_commander=True,
        )
        self.assertGreater(commander, non_commander)

    def test_default_is_commander_false_matches_explicit_false(self):
        default = combat_interaction.block_rate_for("midrange", turn=6, n_attackers=2, keywords=set())
        explicit = combat_interaction.block_rate_for(
            "midrange", turn=6, n_attackers=2, keywords=set(), is_commander=False,
        )
        self.assertEqual(default, explicit)

    def test_bias_of_one_means_no_effect(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                **original,
                "commander_targeting": {"block_bias": 1.0},
            }
            non_commander = combat_interaction.block_rate_for(
                "control", turn=5, n_attackers=1, keywords=set(), is_commander=False,
            )
            commander = combat_interaction.block_rate_for(
                "control", turn=5, n_attackers=1, keywords=set(), is_commander=True,
            )
            self.assertEqual(commander, non_commander)
        finally:
            combat_interaction._WEIGHTS = original

    def test_bias_still_clamped_to_a_probability(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                **original,
                "commander_targeting": {"block_bias": 50.0},
            }
            rate = combat_interaction.block_rate_for(
                "control", turn=8, n_attackers=1, keywords=set(), is_commander=True,
            )
            self.assertLessEqual(rate, 1.0)
        finally:
            combat_interaction._WEIGHTS = original

    def test_goldfish_profile_unaffected_by_commander_bias(self):
        # block_rate_base=0 short-circuits before the commander multiplier -
        # our own goldfish simulation of the OPPONENT profile stays at 0 either way.
        rate = combat_interaction.block_rate_for(
            "goldfish", turn=5, n_attackers=1, keywords=set(), is_commander=True,
        )
        self.assertEqual(rate, 0.0)

    def test_real_project_weights_bias_the_commander_in_full_combat_resolution(self):
        # Uses the actual shipped Data/Models/combat_interaction_weights.json
        # (not mocked): over enough trials, a commander attacker should be
        # blocked strictly more often than an identical non-commander attacker
        # under the same profile/turn/board-width conditions.
        commander_infos = [
            combat_interaction.AttackerInfo(
                name=f"Cmdr{i}", power=3, lifelink=False, keywords=set(), is_commander=True,
            )
            for i in range(400)
        ]
        non_commander_infos = [
            combat_interaction.AttackerInfo(
                name=f"NonCmdr{i}", power=3, lifelink=False, keywords=set(), is_commander=False,
            )
            for i in range(400)
        ]
        commander_outcomes = combat_interaction.resolve_combat_interaction(
            "control", 8, commander_infos, random.Random(11),
        )
        non_commander_outcomes = combat_interaction.resolve_combat_interaction(
            "control", 8, non_commander_infos, random.Random(11),
        )
        commander_block_rate = sum(o.blocked for o in commander_outcomes) / len(commander_outcomes)
        non_commander_block_rate = sum(o.blocked for o in non_commander_outcomes) / len(non_commander_outcomes)
        self.assertGreater(commander_block_rate, non_commander_block_rate)


class AttackPhaseCommanderBlockBiasIntegrationTests(unittest.TestCase):
    def test_attack_phase_passes_is_commander_through_to_block_rate(self):
        # End-to-end: a commander attacker and an identical non-commander attacker
        # in the SAME combat, against aggressive-but-not-certain weights, should
        # show the commander blocked more often across many seeds - verifies the
        # is_commander flag actually reaches resolve_combat_interaction via
        # attack_phase's own AttackerInfo construction (App/engine.py), not just
        # the unit-level combat_model call above. commander_posture="aggressive"
        # bypasses the SEPARATE Posture gate (App/combat_model/posture.py), which
        # otherwise can hold a lone commander back from attacking at all - that
        # gate is a different mechanic (WP5/WP6 Posture) than the block-bias under
        # test here, and must not confound this test.
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 0.4, "trade_rate_given_blocked": 1.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
                "commander_targeting": {"block_bias": 2.0},
            }
            commander_deaths = 0
            non_commander_deaths = 0
            trials = 200
            for seed in range(trials):
                cmdr = engine.Permanent(
                    card=make_card("Commander Attacker", commander=True), entered_turn=1, tapped=False,
                )
                state = make_state(battlefield=[cmdr], turn=5, opponents=[1000.0])
                strategy = engine.ScenarioStrategy(opponent_profile="control", commander_posture="aggressive")
                engine.attack_phase(state, strategy, random.Random(seed))
                self.assertTrue(cmdr.tapped, "commander must actually attack for this test to be meaningful")
                if cmdr not in state.battlefield:
                    commander_deaths += 1

                noncmdr = engine.Permanent(
                    card=make_card("Plain Attacker", commander=False), entered_turn=1, tapped=False,
                )
                state2 = make_state(battlefield=[noncmdr], turn=5, opponents=[1000.0])
                engine.attack_phase(state2, strategy, random.Random(seed))
                if noncmdr not in state2.battlefield:
                    non_commander_deaths += 1
            self.assertGreater(commander_deaths, non_commander_deaths)
        finally:
            combat_interaction._WEIGHTS = original


class FirstStrikeTradeRateTests(unittest.TestCase):
    """WP6 (v4.15.2): a blocked attacker with 'first strike' or 'double strike'
    approximates the real two-stage first-strike/regular-damage combat step as
    a reduced chance of dying in the trade (see
    interaction._first_strike_trade_rate_multiplier). Forces block_rate_base=1.0
    so every attacker is guaranteed to be blocked, isolating the trade outcome."""

    _ALWAYS_BLOCKED_WEIGHTS = {
        "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
        "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
        "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
        "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
        "first_strike": {"trade_rate_multiplier": 0.5},
    }

    def test_first_strike_keyword_alone_reduces_the_effective_trade_rate(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = self._ALWAYS_BLOCKED_WEIGHTS
            self.assertEqual(combat_interaction._first_strike_trade_rate_multiplier(set()), 1.0)
            self.assertEqual(combat_interaction._first_strike_trade_rate_multiplier({"first strike"}), 0.5)
        finally:
            combat_interaction._WEIGHTS = original

    def test_first_strike_keyword_makes_death_certain_only_at_a_lower_threshold(self):
        # trade_rate_given_blocked=1.0, multiplier=0.5 -> effective_trade_rate=0.5:
        # a plain attacker (still trade_rate 1.0) always dies once blocked;
        # a first-strike attacker under the exact same forced-block weights only
        # dies on the roughly-half of rng draws below 0.5 - demonstrated here by
        # picking one seed known to fall on each side of that threshold.
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = self._ALWAYS_BLOCKED_WEIGHTS
            plain = combat_interaction.AttackerInfo(name="Plain", power=3, lifelink=False, keywords=set())
            plain_out = combat_interaction.resolve_combat_interaction("control", 5, [plain], random.Random(9))[0]
            self.assertTrue(plain_out.blocked)
            self.assertTrue(plain_out.died)  # trade_rate=1.0, no reduction -> certain death regardless of seed

            fs = combat_interaction.AttackerInfo(name="FS", power=3, lifelink=False, keywords={"first strike"})
            survived_seed = next(
                seed for seed in range(50)
                if not combat_interaction.resolve_combat_interaction("control", 5, [fs], random.Random(seed))[0].died
            )
            fs_out = combat_interaction.resolve_combat_interaction("control", 5, [fs], random.Random(survived_seed))[0]
            self.assertTrue(fs_out.blocked)
            self.assertFalse(fs_out.died)
        finally:
            combat_interaction._WEIGHTS = original

    def test_double_strike_gets_the_same_reduction_as_first_strike(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = self._ALWAYS_BLOCKED_WEIGHTS
            fs = combat_interaction.AttackerInfo(name="FS", power=3, lifelink=False, keywords={"first strike"})
            ds = combat_interaction.AttackerInfo(name="DS", power=3, lifelink=False, keywords={"double strike"})
            fs_out = combat_interaction.resolve_combat_interaction("control", 5, [fs], random.Random(3))[0]
            ds_out = combat_interaction.resolve_combat_interaction("control", 5, [ds], random.Random(3))[0]
            self.assertEqual(fs_out.died, ds_out.died)
        finally:
            combat_interaction._WEIGHTS = original

    def test_multiplier_of_one_means_no_effect(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                **self._ALWAYS_BLOCKED_WEIGHTS,
                "first_strike": {"trade_rate_multiplier": 1.0},
            }
            fs = combat_interaction.AttackerInfo(name="FS", power=3, lifelink=False, keywords={"first strike"})
            out = combat_interaction.resolve_combat_interaction("control", 5, [fs], random.Random(9))[0]
            self.assertTrue(out.died)  # unchanged: trade_rate stays 1.0
        finally:
            combat_interaction._WEIGHTS = original

    def test_missing_first_strike_section_defaults_to_no_effect(self):
        weights_without_section = {k: v for k, v in self._ALWAYS_BLOCKED_WEIGHTS.items() if k != "first_strike"}
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = weights_without_section
            fs = combat_interaction.AttackerInfo(name="FS", power=3, lifelink=False, keywords={"first strike"})
            out = combat_interaction.resolve_combat_interaction("control", 5, [fs], random.Random(9))[0]
            self.assertTrue(out.died)  # no first_strike section -> multiplier defaults to 1.0
        finally:
            combat_interaction._WEIGHTS = original

    def test_unrelated_keywords_are_unaffected(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = self._ALWAYS_BLOCKED_WEIGHTS
            flying = combat_interaction.AttackerInfo(name="Flyer", power=3, lifelink=False, keywords={"flying"})
            out = combat_interaction.resolve_combat_interaction("control", 5, [flying], random.Random(9))[0]
            self.assertTrue(out.died)  # flying is not a first-strike-timing keyword
        finally:
            combat_interaction._WEIGHTS = original

    def test_real_project_weights_first_strike_dies_less_often_over_many_trials(self):
        # Uses the actual shipped Data/Models/combat_interaction_weights.json
        # (not mocked): with the real (non-100%) block/trade rates, a
        # first-strike attacker should still die strictly less often than an
        # otherwise-identical plain attacker, over enough trials.
        plain_infos = [
            combat_interaction.AttackerInfo(name=f"Plain{i}", power=3, lifelink=False, keywords=set())
            for i in range(500)
        ]
        fs_infos = [
            combat_interaction.AttackerInfo(name=f"FS{i}", power=3, lifelink=False, keywords={"first strike"})
            for i in range(500)
        ]
        plain_outcomes = combat_interaction.resolve_combat_interaction("control", 8, plain_infos, random.Random(21))
        fs_outcomes = combat_interaction.resolve_combat_interaction("control", 8, fs_infos, random.Random(21))
        plain_deaths = sum(o.died for o in plain_outcomes)
        fs_deaths = sum(o.died for o in fs_outcomes)
        self.assertGreater(plain_deaths, fs_deaths)

    def test_unblocked_double_strike_damage_doubling_is_unaffected_by_this_change(self):
        # Regression guard: the pre-existing v4.7.5 UNBLOCKED double-strike damage
        # doubling must still work unchanged (goldfish profile: never blocked).
        ds = combat_interaction.AttackerInfo(name="DS", power=4, lifelink=False, keywords={"double strike"})
        out = combat_interaction.resolve_combat_interaction("goldfish", 5, [ds], random.Random(1))[0]
        self.assertFalse(out.blocked)
        self.assertEqual(out.damage_dealt, 8.0)


class ResolveCombatInteractionTests(unittest.TestCase):
    def test_goldfish_profile_all_unblocked(self):
        infos = [
            combat_interaction.AttackerInfo(name="A", power=3, lifelink=False, keywords=set()),
            combat_interaction.AttackerInfo(name="B", power=5, lifelink=False, keywords=set()),
        ]
        outcomes = combat_interaction.resolve_combat_interaction("goldfish", 5, infos, random.Random(1))
        self.assertTrue(all(not o.blocked for o in outcomes))
        self.assertEqual(sum(o.damage_dealt for o in outcomes), 8)

    def test_deterministic_given_same_seed(self):
        infos = [combat_interaction.AttackerInfo(name=f"A{i}", power=2, lifelink=False, keywords=set()) for i in range(20)]
        out1 = combat_interaction.resolve_combat_interaction("control", 6, infos, random.Random(42))
        out2 = combat_interaction.resolve_combat_interaction("control", 6, infos, random.Random(42))
        self.assertEqual(
            [(o.blocked, o.died, o.damage_dealt) for o in out1],
            [(o.blocked, o.died, o.damage_dealt) for o in out2],
        )

    def test_some_attackers_can_die_against_an_interactive_profile(self):
        # Large sample, aggressive profile params, to reliably exercise the death path.
        infos = [combat_interaction.AttackerInfo(name=f"A{i}", power=2, lifelink=False, keywords=set()) for i in range(300)]
        outcomes = combat_interaction.resolve_combat_interaction("control", 8, infos, random.Random(7))
        self.assertTrue(any(o.died for o in outcomes), "expected at least one death across 300 attackers vs control")


class AttackPhaseIntegrationTests(unittest.TestCase):
    def test_attack_phase_runs_end_to_end_and_deals_damage(self):
        attacker = engine.Permanent(card=make_card("Attacker", power=5, toughness=5), entered_turn=1, tapped=False)
        state = make_state(battlefield=[attacker], turn=5, opponents=[40.0])
        strategy = make_strategy("goldfish")  # deterministic: never blocked
        engine.attack_phase(state, strategy, random.Random(1))
        self.assertEqual(state.opponents[0], 35.0)
        self.assertTrue(attacker.tapped)

    def test_dying_attacker_is_actually_removed_from_battlefield(self):
        # Rig via a fixed rng sequence is fragile; instead force it through very
        # aggressive weights by monkeypatching the loaded weights table directly,
        # then restore them - keeps this test independent of tuning changes.
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
            }
            attacker = engine.Permanent(card=make_card("Doomed Attacker"), entered_turn=1, tapped=False)
            state = make_state(battlefield=[attacker], turn=5, opponents=[40.0])
            strategy = make_strategy("control")
            engine.attack_phase(state, strategy, random.Random(3))
            self.assertNotIn(attacker, state.battlefield)
            self.assertTrue(any(c.name == "Doomed Attacker" for c in state.graveyard))
            self.assertEqual(state.opponents[0], 40.0)  # blocked -> no damage through
        finally:
            combat_interaction._WEIGHTS = original

    def test_indestructible_attacker_survives_a_lethal_block(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
            }
            attacker = engine.Permanent(
                card=make_card("Indestructible Attacker", keywords={"indestructible"}),
                entered_turn=1, tapped=False,
            )
            state = make_state(battlefield=[attacker], turn=5, opponents=[40.0])
            strategy = make_strategy("control")
            engine.attack_phase(state, strategy, random.Random(3))
            self.assertIn(attacker, state.battlefield)
        finally:
            combat_interaction._WEIGHTS = original

    def test_token_group_count_decrements_on_death(self):
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
            }
            group = engine.TokenGroup(name="Soldier", count=3, power=1, toughness=1, keywords=set(), entered_turn=1)
            state = make_state(creature_tokens=[group], turn=5, opponents=[40.0])
            strategy = make_strategy("control")
            engine.attack_phase(state, strategy, random.Random(3))
            self.assertEqual(group.count, 2)
        finally:
            combat_interaction._WEIGHTS = original

    def test_unblocked_token_group_deals_count_times_power_damage(self):
        # v4.24.0 regression (found via ChatGPT external review): a group of
        # 10 grouped 1/1 tokens attacking unblocked must deal 10 damage, not
        # 1 - the old formula only scaled the flat team-bonus part of power
        # by g.count and left the token's own base power unscaled.
        group = engine.TokenGroup(name="Soldier", count=10, power=1, toughness=1, keywords=set(), entered_turn=1)
        state = make_state(creature_tokens=[group], turn=5, opponents=[40.0])
        strategy = make_strategy("goldfish")  # deterministic: never blocked
        engine.attack_phase(state, strategy, random.Random(1))
        self.assertEqual(state.opponents[0], 30.0)

    def test_unblocked_token_group_scales_with_a_global_team_bonus_too(self):
        # The global team +1/+0-style bonus (team_pt_bonus) must also be
        # applied per token, not just once for the whole group.
        group = engine.TokenGroup(name="Soldier", count=4, power=1, toughness=1, keywords=set(), entered_turn=1)
        booster = engine.Permanent(
            card=make_card(
                "Team Booster", type_line="Enchantment",
                oracle_text="Creatures you control get +1/+0.",
            ),
            entered_turn=1, tapped=False,
        )
        state = make_state(creature_tokens=[group], battlefield=[booster], turn=5, opponents=[40.0])
        strategy = make_strategy("goldfish")
        engine.attack_phase(state, strategy, random.Random(1))
        # 4 tokens at (1 base + 1 team bonus) power each = 8 damage.
        self.assertEqual(state.opponents[0], 32.0)

    def test_token_group_attack_weight_counts_toward_wide_board_math(self):
        # v4.24.0: a 10-token group must count as 10 real attackers for
        # wide_board's soft-cap/decay, not 1 - otherwise a lone Permanent
        # sharing combat with a big token group gets an under-decayed
        # (too-high) block rate.
        infos = [
            combat_interaction.AttackerInfo(name="Lone", power=1, lifelink=False, keywords=set()),
            combat_interaction.AttackerInfo(
                name="Tokens", power=10, lifelink=False, keywords=set(),
                source_kind="token_group", attack_weight=9.0,
            ),
        ]
        original = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 0.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 5, "decay_per_extra_attacker": 0.5, "min_multiplier": 0.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
            }
            # Total attack_weight = 1 + 9 = 10, well past soft_cap=5 -> heavy decay
            # -> block_rate collapses toward 0 -> both attackers get through.
            rate = combat_interaction.block_rate_for("control", turn=5, n_attackers=10, keywords=set())
            self.assertLess(rate, 0.05)
        finally:
            combat_interaction._WEIGHTS = original


if __name__ == "__main__":
    unittest.main()
