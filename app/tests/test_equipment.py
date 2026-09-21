"""
Unit tests for App/combat_model/equipment.py (WP7, Iteration 2).

Run from the project root:
    python -m unittest tests.test_equipment -v
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
from App.combat_model import equipment as equipment_model  # noqa: E402
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


def make_equipment_card(name, oracle_text, **overrides):
    return make_card(
        name, type_line="Artifact — Equipment", oracle_text=oracle_text,
        power=None, toughness=None, **overrides,
    )


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


class ParsingTests(unittest.TestCase):
    def test_parse_equip_cost_simple(self):
        card = make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}")
        self.assertEqual(equipment_model.parse_equip_cost(card), 3)

    def test_parse_equip_cost_with_extra_text(self):
        card = make_equipment_card("Bloodforged Battle-Axe", "Whenever equipped creature deals combat damage to a player, create a 1/1. Equip {3}")
        self.assertEqual(equipment_model.parse_equip_cost(card), 3)

    def test_non_equipment_card_has_no_equip_cost(self):
        card = make_card("Just a Bear")
        self.assertIsNone(equipment_model.parse_equip_cost(card))

    def test_parse_bonus_and_keywords(self):
        card = make_equipment_card(
            "Swiftblade Vanguard's Boots",
            "Equipped creature gets +2/+2 and has vigilance and haste.\nEquip {2}",
        )
        power, toughness, kws = equipment_model.parse_equipment_bonus(card)
        self.assertEqual((power, toughness), (2.0, 2.0))
        self.assertEqual(kws, {"vigilance", "haste"})

    def test_bonus_only_no_keywords(self):
        card = make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}")
        power, toughness, kws = equipment_model.parse_equipment_bonus(card)
        self.assertEqual((power, toughness), (10.0, 10.0))
        self.assertEqual(kws, set())


class AttachmentAndBonusIntegrationTests(unittest.TestCase):
    def test_attached_equipment_boosts_creature_power(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Bear", power=2, toughness=2), entered_turn=1)
        state = make_state(battlefield=[hammer, creature])

        self.assertEqual(engine.creature_power(creature, state), 2.0)
        equipment_model.attach_equipment(state, hammer, creature)
        self.assertEqual(engine.creature_power(creature, state), 12.0)

    def test_attached_equipment_grants_keywords(self):
        boots = engine.Permanent(
            card=make_equipment_card("Boots", "Equipped creature gets +1/+1 and has vigilance and trample.\nEquip {1}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Runner"), entered_turn=1)
        state = make_state(battlefield=[boots, creature])
        equipment_model.attach_equipment(state, boots, creature)
        kws = engine.effective_keywords_in_state(creature, state)
        self.assertIn("vigilance", kws)
        self.assertIn("trample", kws)

    def test_unattached_equipment_grants_nothing(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[hammer, creature])
        self.assertEqual(engine.creature_power(creature, state), 2.0)

    def test_detach_when_creature_leaves_battlefield(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[hammer, creature])
        equipment_model.attach_equipment(state, hammer, creature)

        state.battlefield.remove(creature)  # creature dies/leaves, equipment stays
        equipment_model.detach_if_creature_left(state)
        self.assertIsNone(hammer.attached_to)
        self.assertIn(hammer, state.battlefield)


def make_land(name="Wastes"):
    card = engine.Card(name=name, type_line="Land", oracle_text="{T}: Add {C}.", produced_mana={"C"})
    return engine.Permanent(card=card, entered_turn=1, tapped=False)


class AutoEquipStepTests(unittest.TestCase):
    def test_auto_equips_the_commander_when_affordable(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {1}"),
            entered_turn=1,
        )
        commander = engine.Permanent(card=make_card("Mabel", power=3, commander=True), entered_turn=1)
        sidekick = engine.Permanent(card=make_card("Sidekick", power=8, commander=False), entered_turn=1)
        land = make_land()
        state = make_state(battlefield=[hammer, commander, sidekick, land])
        strategy = engine.ScenarioStrategy()

        equipment_model.auto_equip_step(engine, state, strategy)
        self.assertIs(hammer.attached_to, commander)  # commander preferred even though sidekick has more power

    def test_does_not_equip_if_unaffordable(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[hammer, creature])  # no lands at all -> unaffordable
        strategy = engine.ScenarioStrategy()
        equipment_model.auto_equip_step(engine, state, strategy)
        self.assertIsNone(hammer.attached_to)

    def test_v4_29_0_mana_is_actually_spent_not_reusable_for_a_second_equip(self):
        # Found via ChatGPT external review (Docs/README.md v4.29.0 entry):
        # before the fix, auto_equip_step only checked available_mana_value
        # and never called find_payment/apply_payment at all, so the SAME
        # single land could fund an unlimited number of Equip activations.
        # One land (1 mana) can afford exactly ONE of these two Equip {1}
        # hammers, never both.
        hammer_a = engine.Permanent(
            card=make_equipment_card("Colossus Hammer A", "Equipped creature gets +10/+10.\nEquip {1}"),
            entered_turn=1,
        )
        hammer_b = engine.Permanent(
            card=make_equipment_card("Colossus Hammer B", "Equipped creature gets +10/+10.\nEquip {1}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        land = make_land()
        state = make_state(battlefield=[hammer_a, hammer_b, creature, land])
        strategy = engine.ScenarioStrategy()

        equipment_model.auto_equip_step(engine, state, strategy)
        attached = [h for h in (hammer_a, hammer_b) if h.attached_to is not None]
        self.assertEqual(len(attached), 1)  # exactly one, not both
        self.assertTrue(land.tapped)  # the one land actually got spent

    def test_already_attached_equipment_is_left_alone(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {1}"),
            entered_turn=1,
        )
        creature_a = engine.Permanent(card=make_card("A", power=1), entered_turn=1)
        creature_b = engine.Permanent(card=make_card("B", power=99), entered_turn=1)
        state = make_state(battlefield=[hammer, creature_a, creature_b])
        hammer.attached_to = creature_a
        strategy = engine.ScenarioStrategy()
        equipment_model.auto_equip_step(engine, state, strategy)
        self.assertIs(hammer.attached_to, creature_a)  # not re-equipped onto the bigger creature


class DynamicXBonusTests(unittest.TestCase):
    """v4.15.3: 'gets +X/+0, where X is the number of _ counters on this
    Equipment' (real card: Chainsaw) - previously silently mis-parsed as 0/0
    since _EQUIPPED_BONUS_RE only matched literal digits."""

    def _chainsaw_card(self):
        return make_equipment_card(
            "Chainsaw",
            "When this Equipment enters, it deals 3 damage to up to one target creature.\n"
            "Whenever one or more creatures die, put a rev counter on this Equipment.\n"
            "Equipped creature gets +X/+0, where X is the number of rev counters on this Equipment.\n"
            "Equip {3}",
        )

    def test_bare_card_with_no_counters_resolves_x_to_zero(self):
        power, toughness, kws = equipment_model.parse_equipment_bonus(self._chainsaw_card())
        self.assertEqual((power, toughness), (0.0, 0.0))

    def test_permanent_with_rev_counters_resolves_x_to_the_counter_count(self):
        chainsaw = engine.Permanent(card=self._chainsaw_card(), entered_turn=1)
        chainsaw.named_counters["rev"] = 3
        power, toughness, kws = equipment_model.parse_equipment_bonus(chainsaw)
        self.assertEqual((power, toughness), (3.0, 0.0))

    def test_creature_power_reflects_the_dynamic_bonus_end_to_end(self):
        chainsaw = engine.Permanent(card=self._chainsaw_card(), entered_turn=1)
        chainsaw.named_counters["rev"] = 2
        creature = engine.Permanent(card=make_card("Bear", power=2, toughness=2), entered_turn=1)
        state = make_state(battlefield=[chainsaw, creature])
        equipment_model.attach_equipment(state, chainsaw, creature)
        self.assertEqual(engine.creature_power(creature, state), 4.0)  # 2 base + 2 from rev counters

    def test_static_digit_bonus_is_unaffected_by_the_new_x_path(self):
        # Regression guard: an ordinary literal +N/+N equipment must not be
        # accidentally routed through the new X-resolution branch.
        power, toughness, kws = equipment_model.parse_equipment_bonus(
            make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}")
        )
        self.assertEqual((power, toughness), (10.0, 10.0))


class CreatureDeathEquipmentTriggerTests(unittest.TestCase):
    def test_matching_equipment_gains_a_counter(self):
        chainsaw = engine.Permanent(
            card=make_equipment_card(
                "Chainsaw",
                "Whenever one or more creatures die, put a rev counter on this Equipment.\n"
                "Equipped creature gets +X/+0, where X is the number of rev counters on this Equipment.\nEquip {3}",
            ),
            entered_turn=1,
        )
        state = make_state(battlefield=[chainsaw])
        equipment_model.creature_death_equipment_triggers(state)
        self.assertEqual(chainsaw.named_counters["rev"], 1)

    def test_triggers_once_per_call_not_per_creature(self):
        # Real-rules parity: "whenever one or more creatures die" is one
        # trigger for the whole batch, not one per creature - the caller
        # (attack_phase) is responsible for calling this once per combat,
        # not once per death; this test just confirms a single call adds
        # exactly one counter.
        chainsaw = engine.Permanent(
            card=make_equipment_card(
                "Chainsaw",
                "Whenever one or more creatures die, put a rev counter on this Equipment.\nEquip {3}",
            ),
            entered_turn=1,
        )
        state = make_state(battlefield=[chainsaw])
        equipment_model.creature_death_equipment_triggers(state)
        self.assertEqual(chainsaw.named_counters["rev"], 1)

    def test_non_matching_equipment_is_unaffected(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}"),
            entered_turn=1,
        )
        state = make_state(battlefield=[hammer])
        equipment_model.creature_death_equipment_triggers(state)
        self.assertEqual(dict(hammer.named_counters), {})


class AttackTapTriggerTests(unittest.TestCase):
    """v4.15.3: 'Whenever equipped creature attacks, tap target creature
    defending player controls' (real card: Captain America's Shield),
    approximated as a block-rate multiplier for the equipped attacker."""

    def _shield_card(self):
        return make_equipment_card(
            "Captain America's Shield",
            "Indestructible\nEquipped creature gets +0/+8 and has vigilance.\n"
            "Whenever equipped creature attacks, tap target creature defending player controls.\nEquip {2}",
        )

    def test_no_equipment_means_no_effect(self):
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[creature])
        weights = {"equipment": {"attack_tap_trigger_block_rate_multiplier": 0.6}}
        self.assertEqual(equipment_model.equipment_attack_tap_multiplier(weights, state, creature), 1.0)

    def test_equipped_with_tap_trigger_returns_the_configured_multiplier(self):
        shield = engine.Permanent(card=self._shield_card(), entered_turn=1)
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[shield, creature])
        equipment_model.attach_equipment(state, shield, creature)
        weights = {"equipment": {"attack_tap_trigger_block_rate_multiplier": 0.6}}
        self.assertAlmostEqual(equipment_model.equipment_attack_tap_multiplier(weights, state, creature), 0.6)

    def test_unrelated_equipment_does_not_trigger_it(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[hammer, creature])
        equipment_model.attach_equipment(state, hammer, creature)
        weights = {"equipment": {"attack_tap_trigger_block_rate_multiplier": 0.6}}
        self.assertEqual(equipment_model.equipment_attack_tap_multiplier(weights, state, creature), 1.0)

    def test_missing_equipment_section_defaults_to_no_effect(self):
        shield = engine.Permanent(card=self._shield_card(), entered_turn=1)
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[shield, creature])
        equipment_model.attach_equipment(state, shield, creature)
        self.assertEqual(equipment_model.equipment_attack_tap_multiplier({}, state, creature), 1.0)


class CombatDamageCopyTriggerTests(unittest.TestCase):
    """v4.15.3: 'Whenever equipped creature deals combat damage to a player,
    create a token that's a copy of this Equipment' (real card: Bloodforged
    Battle-Axe)."""

    def _axe_card(self):
        return make_equipment_card(
            "Bloodforged Battle-Axe",
            "Equipped creature gets +2/+0.\n"
            "Whenever equipped creature deals combat damage to a player, create a token that's a copy of this Equipment.\n"
            "Equip {2}",
        )

    def test_no_equipment_means_no_triggers(self):
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[creature])
        self.assertEqual(equipment_model.equipment_combat_damage_copy_triggers(state, creature), [])

    def test_equipped_with_copy_trigger_returns_the_card(self):
        axe = engine.Permanent(card=self._axe_card(), entered_turn=1)
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[axe, creature])
        equipment_model.attach_equipment(state, axe, creature)
        result = equipment_model.equipment_combat_damage_copy_triggers(state, creature)
        self.assertEqual([c.name for c in result], ["Bloodforged Battle-Axe"])

    def test_unrelated_equipment_is_not_returned(self):
        hammer = engine.Permanent(
            card=make_equipment_card("Colossus Hammer", "Equipped creature gets +10/+10.\nEquip {3}"),
            entered_turn=1,
        )
        creature = engine.Permanent(card=make_card("Bear"), entered_turn=1)
        state = make_state(battlefield=[hammer, creature])
        equipment_model.attach_equipment(state, hammer, creature)
        self.assertEqual(equipment_model.equipment_combat_damage_copy_triggers(state, creature), [])


class AttackPhaseEquipmentTriggerIntegrationTests(unittest.TestCase):
    """End-to-end through engine.attack_phase itself, not just the combat_model
    unit-level calls above."""

    def test_unblocked_attacker_with_battle_axe_spawns_a_token_copy(self):
        import random
        axe = engine.Permanent(
            card=make_equipment_card(
                "Bloodforged Battle-Axe",
                "Equipped creature gets +2/+0.\n"
                "Whenever equipped creature deals combat damage to a player, create a token that's a copy of this Equipment.\n"
                "Equip {2}",
            ),
            entered_turn=1,
        )
        attacker = engine.Permanent(card=make_card("Attacker", power=3, toughness=3), entered_turn=1, tapped=False)
        state = make_state(battlefield=[axe, attacker], turn=5, opponents=[40.0])
        equipment_model.attach_equipment(state, axe, attacker)
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")  # never blocked -> deterministic damage
        before_axe_count = sum(1 for p in state.battlefield if p.card.name == "Bloodforged Battle-Axe")
        engine.attack_phase(state, strategy, random.Random(1))
        after_axe_count = sum(1 for p in state.battlefield if p.card.name == "Bloodforged Battle-Axe")
        self.assertEqual(after_axe_count, before_axe_count + 1)

    def test_combat_death_increments_a_rev_counter_on_a_present_chainsaw(self):
        import random
        chainsaw = engine.Permanent(
            card=make_equipment_card(
                "Chainsaw",
                "Whenever one or more creatures die, put a rev counter on this Equipment.\n"
                "Equipped creature gets +X/+0, where X is the number of rev counters on this Equipment.\nEquip {3}",
            ),
            entered_turn=1,
        )
        attacker = engine.Permanent(card=make_card("Doomed Attacker"), entered_turn=1, tapped=False)
        state = make_state(battlefield=[chainsaw, attacker], turn=5, opponents=[40.0])
        strategy = engine.ScenarioStrategy(opponent_profile="control")
        original_weights = combat_interaction._WEIGHTS
        try:
            combat_interaction._WEIGHTS = {
                "profiles": {"control": {"block_rate_base": 1.0, "trade_rate_given_blocked": 1.0}},
                "evasion_keyword_multiplier": {"flying": 1.0, "menace": 1.0, "trample": 1.0},
                "wide_board": {"soft_cap_attackers": 999, "decay_per_extra_attacker": 1.0, "min_multiplier": 1.0},
                "turn_ramp": {"start_turn": 0, "max_turn": 1, "start_multiplier": 1.0, "max_multiplier": 1.0},
            }
            engine.attack_phase(state, strategy, random.Random(3))
            self.assertNotIn(attacker, state.battlefield)  # died as intended (forces the death-trigger path)
            self.assertEqual(chainsaw.named_counters["rev"], 1)
        finally:
            combat_interaction._WEIGHTS = original_weights

    def test_no_death_this_combat_does_not_add_a_rev_counter(self):
        import random
        chainsaw = engine.Permanent(
            card=make_equipment_card(
                "Chainsaw",
                "Whenever one or more creatures die, put a rev counter on this Equipment.\nEquip {3}",
            ),
            entered_turn=1,
        )
        attacker = engine.Permanent(card=make_card("Safe Attacker"), entered_turn=1, tapped=False)
        state = make_state(battlefield=[chainsaw, attacker], turn=5, opponents=[40.0])
        strategy = engine.ScenarioStrategy(opponent_profile="goldfish")  # never blocked -> nobody dies
        engine.attack_phase(state, strategy, random.Random(1))
        self.assertEqual(chainsaw.named_counters.get("rev", 0), 0)


if __name__ == "__main__":
    unittest.main()
