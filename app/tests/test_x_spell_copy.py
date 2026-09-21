"""
Unit/integration tests for WP9: X-spell/Copy refinement (Aziza, Mage Tower
Captain / Mica, Reader of Ruins).

Covers:
  1. best_x_plan no longer defaults to the maximal affordable X:
     - smallest X that reaches lethal (same template as
       scenario_predicates' x_spell_lethal), including the copy_multiplier
       effect when Aziza/Mica could double the spell;
     - once no X is lethal, "value mode" also takes the smallest X that
       already clears x_min_roi/x_min_net_value (v4.9.2: replaced an
       earlier post-hoc overkill discount, ValueModel.diminish_x_value,
       that could crush a spell's value before it ever reached its own
       viable X - see BestXPlanOverkillAvoidanceTests below).
  2 + 3 + 4. Copy != Cast: casting an instant/sorcery with Aziza or Mica on
     the battlefield only copies it if their real cost (tap three untapped
     creatures / sacrifice an artifact) can actually be paid, and the copy
     does NOT re-trigger "whenever you cast" (recorded via the `cast` impact
     metric, which must stay at 1 even though the effect happens twice).

Run from the project root:
    python -m unittest tests.test_x_spell_copy -v
"""
from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402

_SCRYFALL_CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"


def _load_real_card(name: str, *, commander: bool = False) -> engine.Card:
    """Same approach as tests/test_waterbend.py::_load_real_card - builds a
    real Card from the project's own offline Scryfall cache via the actual
    card_from_scryfall import path, rather than hand-authoring one."""
    with _SCRYFALL_CACHE_PATH.open("r", encoding="utf-8") as f:
        cache = json.load(f)
    for obj in cache.values():
        if isinstance(obj, dict) and obj.get("name") == name:
            entry = engine.DeckEntry(name=name)
            return engine.card_from_scryfall(entry, obj, commander_name=name if commander else None)
    raise AssertionError(f"{name!r} not found in {_SCRYFALL_CACHE_PATH}")


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


def _fake_payment(state, strategy, total_cost, req, *args, **kwargs):
    # Bypasses the colored-mana DP solver entirely (no lands on these tiny
    # test boards) - matches the monkeypatch pattern already used in
    # tests/test_equipment.py for available_mana_value. apply_payment() is a
    # safe no-op for an empty `used` list.
    return engine.PaymentPlan(used=[], total=Counter(), penalty=0.0)


class _WithFakeManaMixin:
    """Patches engine.available_mana_value/find_payment for the duration of
    each test, so best_x_plan/cast_option can be exercised without needing a
    real board of lands."""

    MANA = 25

    def setUp(self):
        self._orig_mana = engine.available_mana_value
        self._orig_find = engine.find_payment
        engine.available_mana_value = lambda state, strategy: self.MANA
        engine.find_payment = _fake_payment

    def tearDown(self):
        engine.available_mana_value = self._orig_mana
        engine.find_payment = self._orig_find


class BestXPlanSmallestLethalTests(_WithFakeManaMixin, unittest.TestCase):
    """WP9 goal 1, first half: smallest X for lethal, same template as
    scenario_predicates.handlers._p_x_spell_lethal."""

    def test_picks_the_smallest_lethal_x_not_the_biggest_affordable(self):
        card = make_card("Test Bolt", type_line="Sorcery", mana_cost="{X}", oracle_text="Test Bolt deals X damage to any target.")
        state = make_state(opponents=[10.0])  # max_x would be 20 (self.MANA), lethal at X=10
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")

        plan = engine.best_x_plan(card, state, strategy)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.x, 10, "should stop at the first X that kills, not keep going to X=20")

    def test_aziza_potential_copy_halves_the_lethal_x(self):
        # Aziza on board with >=3 untapped creatures could double the spell's
        # damage (see _potential_cast_copy_multiplier) - the smallest LETHAL X
        # should account for that, same as x_spell_lethal's copy_multiplier.
        card = make_card("Test Bolt", type_line="Sorcery", mana_cost="{X}", oracle_text="Test Bolt deals X damage to any target.")
        aziza = engine.Permanent(card=make_card(engine.AZIZA_NAME, power=2, toughness=2), entered_turn=1, tapped=False)
        helpers = [engine.Permanent(card=make_card(f"Helper {i}"), entered_turn=1, tapped=False) for i in range(3)]
        state = make_state(opponents=[10.0], battlefield=[aziza] + helpers)
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")

        plan = engine.best_x_plan(card, state, strategy)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.x, 5, "with a potential copy, X=5 * 2 copies = 10 damage is already lethal")


class BestXPlanOverkillAvoidanceTests(_WithFakeManaMixin, unittest.TestCase):
    """WP9 goal 1, second half: value-mode X should not default to maximal
    once no X is lethal.

    v4.9.2: this used to be "avoid overkill" via ValueModel.diminish_x_value,
    a soft-cap decay applied to gross_value beyond a fixed X. That could
    permanently zero out a spell only profitable at high X, because the
    decay started well before the spell's own break-even point (real-run
    evidence: White Sun's Zenith, Seen=49/Cast=0 across 200 games under
    DEFAULT_VALUE_MODEL - see the second test below, which reproduces that
    exact shape). The fix generalizes the lethal branch's own "smallest X
    that already works" search to value mode too, so there is no discount
    curve left to regress: "avoiding overkill" now just falls out of always
    preferring the smallest X that clears the ROI/net-value gates."""

    MANA = 25

    def _token_spell(self):
        return make_card(
            "Test Token Spell", type_line="Sorcery", mana_cost="{X}",
            oracle_text="Create X 2/2 white Cat creature tokens.",
        )

    def _generous_value_model(self):
        # Deliberately high per-token value (well above mana_unit=1.0) so the
        # spell clears the ROI/net-value gates already at X=1 - isolates
        # "does best_x_plan stop at the smallest viable X" from "does this
        # spell clear the gate at all".
        return engine.ValueModel(values=dict(
            engine.DEFAULT_VALUE_MODEL,
            creature_token_body_base=3.0, creature_token_power=0.0, creature_token_toughness=0.0,
        ))

    def test_picks_the_smallest_viable_x_not_the_affordable_max(self):
        state = make_state(opponents=[1000.0])  # unreachable - value mode only
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=self._generous_value_model())

        plan = engine.best_x_plan(self._token_spell(), state, strategy)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.x, 1, "already clears the gates at X=1 - should not keep climbing to the 25-mana affordable max")

    def test_a_spell_only_viable_at_high_x_is_no_longer_crushed_before_it_gets_there(self):
        # Reproduces the real White Sun's Zenith-shaped regression under the
        # project's own DEFAULT_VALUE_MODEL: a 2/2-token X-spell's per-X body
        # value (0.35 + 2*0.25 + 2*0.12 = 1.09) barely exceeds mana_unit
        # (1.0). The old soft-cap decay (starting at X=6) discounted
        # gross_value well before this spell's break-even, so it was never
        # castable in value mode at all - fixed in v4.9.2 (smallest-viable-X
        # search, no more soft cap) and reinforced in v4.10.0 (see
        # ValueModel.curved_count: creature_tokens now has a mildly
        # INCREASING exponent, since a wide board of tokens is worth
        # disproportionately more than the same tokens counted one at a
        # time) - together they bring the break-even down from X=12
        # (v4.9.2, flat-linear token value) to X=4 here.
        vm = engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL))
        state = make_state(opponents=[1000.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=vm)

        plan = engine.best_x_plan(self._token_spell(), state, strategy)

        self.assertIsNotNone(plan, "should still find a viable X once it exists, instead of being crushed by a soft cap")
        self.assertEqual(plan.x, 4, "X=4 is the smallest X where the curved net_value first clears x_min_net_value")

    def test_real_white_suns_zenith_becomes_castable_within_a_realistic_mana_range(self):
        # v4.10.0: the real card (not the synthetic {X} test fixture above)
        # costs {X}{W}{W}{W} - a 3-mana base the earlier fixture didn't
        # model. Under the OLD flat-linear token value, that base cost alone
        # pushed the true break-even to X=45 (need 48 total mana) - hard
        # confirmation, from the second real GUI run, that this card was
        # mathematically unreachable within any 10-turn game (observed real
        # mana ceiling across 200 runs: 17, at turn 10). The v4.10.0
        # increasing-returns curve brings that down to X=8 (11 total mana) -
        # comfortably inside the ~9-13 mana most real games reach by turn
        # 9-10, without touching the base cost or the token's own P/T.
        card = _load_real_card("White Sun's Zenith")
        vm = engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL))
        state = make_state(opponents=[1000.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=vm)

        plan = engine.best_x_plan(card, state, strategy)

        self.assertIsNotNone(plan, "should now be reachable well within the mana available by turn 10 in a real game")
        self.assertEqual(plan.x, 8, "X=8 (11 total mana with the WWW base cost) is the new break-even")

    def test_creature_token_curve_rewards_going_wide_more_than_proportionally(self):
        # Direct, mechanism-level demonstration of the "3 tokens are worse
        # than proportionally scaled-up 5 tokens" argument: the value of N
        # tokens should grow FASTER than N itself once the increasing-
        # returns curve is applied - i.e. value(5)/value(3) > 5/3.
        vm = engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL))
        body_per_token = 1.09  # default creature_token_body_base/power/toughness at 2/2

        value_3 = vm.metric_value("creature_tokens", body_per_token * 3, set())
        value_5 = vm.metric_value("creature_tokens", body_per_token * 5, set())

        self.assertGreater(
            value_5 / value_3, 5 / 3,
            "5 tokens should be worth more than 5/3 times 3 tokens - going wide is disproportionately good",
        )

    def test_burn_damage_curve_makes_a_cheap_efficient_bolt_better_per_mana_than_a_huge_x_spell(self):
        # Mirrors the user's own Lightning Bolt vs. Banefire argument: per
        # point of damage, a cheap efficient burn spell should be worth MORE
        # than the same per-point rate applied to a huge X spell's total -
        # i.e. value(1)/1 > value(40)/40 once the diminishing exponent is
        # applied (opponent_life_loss now curves down, not just flat).
        vm = engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL))

        value_per_point_at_1 = vm.metric_value("opponent_life_loss", 1, set()) / 1
        value_per_point_at_40 = vm.metric_value("opponent_life_loss", 40, set()) / 40

        self.assertGreater(
            value_per_point_at_1, value_per_point_at_40,
            "a single point of damage (Bolt-shaped) should be worth more per point than the same rate stretched over X=40 (Banefire-shaped)",
        )


class BestXPlanProximityToLethalTests(_WithFakeManaMixin, unittest.TestCase):
    """v4.9.3: face-damage X-spells (Banefire, Crater's Claws in the real
    Aziza V2 deck) were found, via a real GUI run, to be mathematically
    uncastable in value mode under DEFAULT_VALUE_MODEL at ANY X - ROI(x) =
    opponent_life_loss_per_point * x / (x + x_card_opportunity_cost)
    approaches only opponent_life_loss_per_point=0.42 as x grows, always
    under x_min_roi=0.88. That is intentional for genuine chip damage (see
    _x_spell_proximity_bonus's docstring), but was missing a way for burn
    that actually closes in on a kill to be worth more than the same damage
    spread thin over a full life total. x_spell_proximity_bonus_max fixes
    that without touching the chip-damage case.

    v4.10.0 additionally applies a mildly DIMINISHING curve to the base
    opponent_life_loss contribution itself (ValueModel.curved_count) - a
    cheap, efficient burn spell is real-Magic more mana-efficient per point
    than a huge X spell, which the old flat per-point rate couldn't
    express. That curve only touches the base per-point contribution to
    gross_value; the proximity bonus below is still computed from the RAW,
    uncurved damage amount, so it isn't affected - closer to lethal is
    closer to lethal regardless of how the base rate curves. The expected
    smallest-viable-X values below moved from v4.9.3 (X=19) to v4.10.0
    (X=24) purely because the base contribution now grows a bit more
    slowly, requiring a bit more X before the (unchanged) proximity bonus
    can carry it over the gate."""

    MANA = 25

    def _burn_spell(self):
        # v4.11.0: color_identity is explicit here (red - the natural color
        # for a "deals X damage to any target" burn spell, and the WotC-
        # primary color for opponent_life_loss, multiplier 1.0) so this
        # helper keeps reproducing the exact pre-v4.11.0 calibrated numbers
        # (X=24 etc. below) rather than silently picking up the colorless
        # fallback discount that an unset color_identity now carries.
        return make_card(
            "Test Burn Spell", type_line="Sorcery", mana_cost="{X}",
            oracle_text="Test Burn Spell deals X damage to any target.",
            color_identity={"R"},
        )

    def test_far_from_lethal_stays_uncastable_in_value_mode(self):
        # Regression guard: the proximity bonus must not change the
        # pre-existing (and, per the flagged calibration gap, likely
        # intentional) result for genuine chip damage - opponent nowhere
        # near dying, bonus should be negligible, spell stays uncastable.
        state = make_state(opponents=[1000.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL)))

        plan = engine.best_x_plan(self._burn_spell(), state, strategy)

        self.assertIsNone(plan, "far from lethal, this should stay just as uncastable as before v4.9.3")

    def test_getting_close_to_lethal_makes_it_castable(self):
        # Opponent at 30, max affordable X capped at 25 by available mana -
        # not lethal (25 < 30), but the best affordable X gets close enough
        # (25/30 proximity) that the bonus should now clear the gates.
        state = make_state(opponents=[30.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL)))

        plan = engine.best_x_plan(self._burn_spell(), state, strategy)

        self.assertIsNotNone(plan, "close to lethal (25 affordable vs. 30 remaining) should now be worth casting")
        self.assertEqual(plan.x, 24, "X=24 is the smallest X where the proximity-boosted net_value first clears the gate")

    def test_a_potential_aziza_copy_brings_a_spell_within_proximity_range_that_would_otherwise_stay_uncastable(self):
        # Same 25-mana cap, opponent at 60 - out of reach even including a
        # potential copy for the lethal check (25*2=50 < 60), but a potential
        # copy still counts double for the PROXIMITY bonus, same as it
        # already counts double for the lethal check above. Without Aziza,
        # this stays uncastable (mirrors the previous test's shape at a
        # farther remove); with Aziza on board, the doubled potential
        # damage (50 out of 60) is close enough to flip it castable.
        vm = engine.ValueModel(values=dict(engine.DEFAULT_VALUE_MODEL))

        state_no_aziza = make_state(opponents=[60.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=vm)
        self.assertIsNone(
            engine.best_x_plan(self._burn_spell(), state_no_aziza, strategy),
            "without a potential copy, 25 affordable vs. 60 remaining is still too far from lethal",
        )

        aziza = engine.Permanent(card=make_card(engine.AZIZA_NAME, power=2, toughness=2), entered_turn=1, tapped=False)
        helpers = [engine.Permanent(card=make_card(f"Helper {i}"), entered_turn=1, tapped=False) for i in range(3)]
        state_with_aziza = make_state(opponents=[60.0], battlefield=[aziza] + helpers)

        plan = engine.best_x_plan(self._burn_spell(), state_with_aziza, strategy)

        self.assertIsNotNone(plan, "a potential Aziza copy should count toward proximity, same as it does for the lethal check")
        self.assertEqual(plan.x, 24)


class AzizaMicaCopyCostTests(_WithFakeManaMixin, unittest.TestCase):
    """WP9 goals 2-4: Copy != Cast, and each card's real cost actually gates
    the copy (not an unconditional free copy)."""

    MANA = 25

    def _token_spell(self, name="Test Token Spell"):
        return make_card(
            name, type_line="Sorcery", mana_cost="{X}",
            oracle_text="Create X 2/2 white Cat creature tokens.",
        )

    def _strategy(self):
        vm = engine.ValueModel(values=dict(
            engine.DEFAULT_VALUE_MODEL,
            creature_token_body_base=3.0, creature_token_power=0.0, creature_token_toughness=0.0,
        ))
        return engine.ScenarioStrategy(opponent_profile="goldfish", value_model=vm)

    def _cast(self, card, state, strategy):
        opt = engine.cast_option(card, state, strategy)
        self.assertIsNotNone(opt, "expected a castable X plan for this synthetic spell")
        ok = engine.try_cast_option(state, strategy, opt)
        self.assertTrue(ok)
        return opt

    def test_aziza_copies_when_she_can_pay_and_the_cast_trigger_does_not_recur(self):
        aziza = engine.Permanent(card=make_card(engine.AZIZA_NAME, power=2, toughness=2), entered_turn=1, tapped=False)
        helpers = [engine.Permanent(card=make_card(f"Helper {i}"), entered_turn=1, tapped=False) for i in range(3)]
        state = make_state(opponents=[1000.0], battlefield=[aziza] + helpers)
        strategy = self._strategy()
        card = self._token_spell()
        state.hand.append(card)

        opt = self._cast(card, state, strategy)

        self.assertEqual(state.total_tokens_created, 2 * opt.x_plan.x, "original + exactly one copy, not more")
        self.assertEqual(state.impact[card.name]["cast"], 1, "the copy must not re-trigger a second 'cast' event")
        self.assertEqual(sum(1 for line in state.event_log if "copied" in line), 1, "exactly one copy, no infinite/duplicate copying")
        self.assertEqual(sum(1 for h in helpers if h.tapped) + int(aziza.tapped), 3, "exactly 3 creatures tapped for the cost, not 6")

    def test_aziza_does_not_copy_when_she_cannot_pay_the_cost(self):
        # Only 2 untapped creatures total (Aziza + 1 helper) - her cost needs 3.
        aziza = engine.Permanent(card=make_card(engine.AZIZA_NAME, power=2, toughness=2), entered_turn=1, tapped=False)
        helper = engine.Permanent(card=make_card("Helper"), entered_turn=1, tapped=False)
        state = make_state(opponents=[1000.0], battlefield=[aziza, helper])
        strategy = self._strategy()
        card = self._token_spell()
        state.hand.append(card)

        opt = self._cast(card, state, strategy)

        self.assertEqual(state.total_tokens_created, opt.x_plan.x, "no copy - the cost could not be paid")
        self.assertFalse(aziza.tapped)
        self.assertFalse(helper.tapped)
        self.assertNotIn(engine.AZIZA_NAME, state.impact)

    def test_mica_copies_by_sacrificing_an_artifact_regardless_of_its_tapped_state(self):
        mica = engine.Permanent(card=make_card(engine.MICA_NAME, power=4, toughness=4), entered_turn=1, tapped=False)
        # Tapped artifact - a real sacrifice cost doesn't care about tap state,
        # unlike Aziza's tap cost. If Mica's check wrongly reused
        # "untapped_artifacts" semantics, this would fail to copy.
        artifact = engine.Permanent(card=make_card("Some Artifact", type_line="Artifact"), entered_turn=1, tapped=True)
        state = make_state(opponents=[1000.0], battlefield=[mica, artifact])
        strategy = self._strategy()
        card = self._token_spell()
        state.hand.append(card)

        opt = self._cast(card, state, strategy)

        self.assertEqual(state.total_tokens_created, 2 * opt.x_plan.x)
        self.assertNotIn(artifact, state.battlefield, "the artifact should have been sacrificed")
        self.assertIn(artifact.card, state.graveyard)
        self.assertEqual(state.impact[card.name]["cast"], 1)

    def test_mica_does_not_copy_with_no_artifact_to_sacrifice(self):
        mica = engine.Permanent(card=make_card(engine.MICA_NAME, power=4, toughness=4), entered_turn=1, tapped=False)
        state = make_state(opponents=[1000.0], battlefield=[mica])
        strategy = self._strategy()
        card = self._token_spell()
        state.hand.append(card)

        opt = self._cast(card, state, strategy)

        self.assertEqual(state.total_tokens_created, opt.x_plan.x)
        self.assertNotIn(engine.MICA_NAME, state.impact)

    def test_x_spell_copy_reuses_the_same_x_not_a_freshly_chosen_one(self):
        # A copy of an X spell copies the value of X already chosen for the
        # original - it does not get to pick its own X. With both create-token
        # log lines showing the same X, this is implicitly covered by the
        # total_tokens_created == 2*x assertions above, but this test pins it
        # explicitly against the log.
        aziza = engine.Permanent(card=make_card(engine.AZIZA_NAME, power=2, toughness=2), entered_turn=1, tapped=False)
        helpers = [engine.Permanent(card=make_card(f"Helper {i}"), entered_turn=1, tapped=False) for i in range(3)]
        state = make_state(opponents=[1000.0], battlefield=[aziza] + helpers)
        strategy = self._strategy()
        card = self._token_spell()
        state.hand.append(card)

        opt = self._cast(card, state, strategy)

        x_lines = [line for line in state.event_log if line.startswith("X-VALUE")]
        self.assertEqual(len(x_lines), 2, "one X-VALUE resolution for the original, one for the copy")
        self.assertTrue(all(f"X={opt.x_plan.x}" in line for line in x_lines))


class RealAzizaDeckCardsTests(_WithFakeManaMixin, unittest.TestCase):
    """At least one test against real Aziza V2 cards, loaded from the
    project's own offline Scryfall cache - not hand-authored - per the WP9
    brief. Both Aziza and Banefire are real cards from that deck."""

    def test_real_banefire_smallest_lethal_x_copied_by_real_aziza(self):
        aziza = engine.Permanent(card=_load_real_card(engine.AZIZA_NAME, commander=True), entered_turn=1, tapped=False)
        helpers = [engine.Permanent(card=make_card(f"Helper {i}"), entered_turn=1, tapped=False) for i in range(3)]
        state = make_state(opponents=[10.0], battlefield=[aziza] + helpers)
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")
        banefire = _load_real_card("Banefire")
        state.hand.append(banefire)

        plan = engine.best_x_plan(banefire, state, strategy)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.x, 5, "X=5 * 2 (real Aziza could copy it) = 10 damage, already lethal")

        opt = engine.cast_option(banefire, state, strategy)
        ok = engine.try_cast_option(state, strategy, opt)
        self.assertTrue(ok)
        self.assertLessEqual(state.opponents[0], 0.0, "original (X=5) + copy (X=5) should have been lethal")
        self.assertEqual(state.impact[banefire.name]["cast"], 1)


if __name__ == "__main__":
    unittest.main()
