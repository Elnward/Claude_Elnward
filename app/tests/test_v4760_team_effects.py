"""
v4.76.0 WP3: team effects (App/team_effects registry + keyword_library
"typed_pt_bonus"): Craterhoof ETB, typed activated pumps (Ezuri, Elvish
Warmaster), tribal anthems, Overrun spells, X creature tutors (Finale of
Devastation) and "Tap N untapped <Type> you control" costs (Lathril).

All cards are in-memory copies of real Oracle texts (no cache dependency).

Run from the project root:
    python -m unittest tests.test_v4760_team_effects -v
"""
from __future__ import annotations

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from App import engine as E  # noqa: E402

ELF = "Creature — Elf Warrior"


def card(name, text="", type_line=ELF, power=1, toughness=1, cost="", mv=0.0, commander=False, ci=("G",)):
    return E.Card(name=name, oracle_text=text, type_line=type_line, power=power, toughness=toughness,
                  mana_cost=cost, mana_value=mv, commander=commander, color_identity=set(ci))


HOOF = card("Craterhoof Behemoth", "Haste\nWhen this creature enters, creatures you control gain trample and get +X/+X until end of turn, where X is the number of creatures you control.",
            type_line="Creature — Beast", power=5, toughness=5, cost="{5}{G}{G}{G}", mv=8)
EZURI = card("Ezuri, Renegade Leader", "{G}: Regenerate another target Elf.\n{2}{G}{G}{G}: Elf creatures you control get +3/+3 and gain trample until end of turn.",
             type_line="Legendary Creature — Elf Warrior", power=2, toughness=2)
WARMASTER = card("Elvish Warmaster", "Whenever one or more other Elves you control enter, create a 1/1 green Elf Warrior creature token. This ability triggers only once each turn.\n{5}{G}{G}: Elves you control get +2/+2 and gain deathtouch until end of turn.", power=2, toughness=2)
PERFECT = card("Imperious Perfect", "Other Elves you control get +1/+1.\n{G}, {T}: Create a 1/1 green Elf Warrior creature token.", power=2, toughness=2)
ARCHDRUID = card("Elvish Archdruid", "Other Elf creatures you control get +1/+1.\n{T}: Add {G} for each Elf you control.", power=2, toughness=2)
BEAR = card("Grizzly Bears", type_line="Creature — Bear", power=2, toughness=2)
LLANOWAR = card("Llanowar Elves", "{T}: Add {G}.")
FINALE = card("Finale of Devastation", "Search your library and/or graveyard for a creature card with mana value X or less and put it onto the battlefield. If you search your library this way, shuffle. If X is 10 or more, creatures you control get +X/+X and gain haste until end of turn.",
              type_line="Sorcery", power=None, toughness=None, cost="{X}{G}{G}", mv=2)
LATHRIL = card("Lathril, Blade of the Elves", "Menace\nWhenever Lathril deals combat damage to a player, create that many 1/1 green Elf Warrior creature tokens.\n{T}, Tap ten untapped Elves you control: Each opponent loses 10 life and you gain 10 life.",
               type_line="Legendary Creature — Elf Noble", power=2, toughness=3, commander=True, ci=("B", "G"))


class _S:
    commander_colors = {"G", "B"}
    tutor_priority = []
    archetypes = set()
    value_model = None
    x_spell_minimums = {}
    x_spell_maximums = {}
    x_min_roi = 0.0
    x_min_net_value = -999.0
    opponent_profile = "goldfish"


def st_with(*cards, turn=6, entered=1):
    st = E.GameState(library=[], hand=[], command_zone=[])
    st.turn = turn
    for c in cards:
        st.battlefield.append(E.Permanent(card=c, entered_turn=entered))
    return st


def power_of(st, c):
    return E.creature_power(next(p for p in st.battlefield if p.card is c), st)


class TeamEffectsTest(unittest.TestCase):
    def test_craterhoof_etb_pumps_team(self):
        st = st_with(LLANOWAR, BEAR)
        st.creature_tokens.append(E.TokenGroup(name="Elf Warrior", count=2, power=1, toughness=1))
        E.permanent_enters(st, _S(), HOOF)
        # X = 2 permanents + 2 tokens + Craterhoof itself = 5
        self.assertEqual(power_of(st, BEAR), 2 + 5)
        self.assertEqual(power_of(st, HOOF), 5 + 5)
        self.assertIn("trample", E.effective_keywords_in_state(st.battlefield[0], st))
        # tokens get generic team bonuses in combat via team_modifier_bonus (existing engine design)
        self.assertEqual(E.token_group_power(st.creature_tokens[0], st) + E.team_modifier_bonus(st), 1 + 5)
        # expires with the turn
        st.turn += 1
        E.expire_board_modifiers(st)
        self.assertEqual(power_of(st, BEAR), 2)

    def test_ezuri_pumps_only_elves(self):
        a = next(x for x in E.parse_oracle_semantics(EZURI) if x.ability_kind == "activated" and x.mana_total == 5)
        self.assertEqual([(y.kind, y.amount, y.target, y.keyword) for y in a.actions],
                         [("typed_pt_bonus", 3.0, "elf", "trample")])
        st = st_with(EZURI, LLANOWAR, BEAR)
        E.execute_semantic_action(st, _S(), st.battlefield[0], a.actions[0])
        self.assertEqual(power_of(st, LLANOWAR), 1 + 3)
        self.assertEqual(power_of(st, BEAR), 2)          # not an Elf
        self.assertIn("trample", E.effective_keywords_in_state(st.battlefield[1], st))

    def test_warmaster_pump_is_now_executable(self):
        a = [x for x in E.parse_oracle_semantics(WARMASTER) if x.ability_kind == "activated"][0]
        self.assertEqual(a.execution_mode, "exact")
        self.assertEqual(a.mana_total, 7)
        self.assertEqual(a.actions[0].kind, "typed_pt_bonus")

    def test_tribal_anthems_typed_and_not_double_counted(self):
        st = st_with(PERFECT, ARCHDRUID, LLANOWAR, BEAR)
        self.assertEqual(power_of(st, LLANOWAR), 1 + 1 + 1)    # both lords
        self.assertEqual(power_of(st, PERFECT), 2 + 1)         # not its own "other"
        self.assertEqual(power_of(st, ARCHDRUID), 2 + 1)
        self.assertEqual(power_of(st, BEAR), 2)                 # previously +1 from Archdruid
        st.creature_tokens.append(E.TokenGroup(name="Elf Warrior", count=1, power=1, toughness=1))
        self.assertEqual(E.token_group_power(st.creature_tokens[0], st), 1 + 2)

    def test_overrun_spell_resolves(self):
        over = card("Overrun", "Creatures you control get +3/+3 and gain trample until end of turn.",
                    type_line="Sorcery", power=None, toughness=None)
        st = st_with(BEAR)
        E.resolve_direct_spell_effects(st, _S(), over)
        self.assertEqual(power_of(st, BEAR), 5)

    def test_finale_tutors_craterhoof_when_board_is_wide(self):
        st = st_with(*[card(f"Elf{i}") for i in range(4)])
        st.library = [HOOF, card("Small Elf", mv=1)]
        for _ in range(12):
            st.battlefield.append(E.Permanent(card=card("Forest", "{T}: Add {G}.", type_line="Basic Land — Forest", power=None, toughness=None), entered_turn=1))
        plan = E.best_x_plan(FINALE, st, _S())
        self.assertIsNotNone(plan)
        self.assertGreaterEqual(plan.x, 8)
        E.resolve_x_spell(st, _S(), FINALE, plan)
        self.assertTrue(st.has("Craterhoof Behemoth"))
        self.assertNotIn(HOOF, st.library)
        if plan.x >= 10:
            self.assertIn("haste", E.effective_keywords_in_state(st.battlefield[0], st))

    def test_lathril_needs_ten_other_untapped_elves(self):
        ab = [x for x in E.parse_oracle_semantics(LATHRIL) if x.ability_kind == "activated"][0]
        few = st_with(LATHRIL, *[card(f"E{i}") for i in range(9)])
        few.opponents = [40.0, 40.0, 40.0]
        self.assertFalse(E.execute_semantic_ability(few, _S(), few.battlefield[0], ab))
        self.assertEqual(few.opponents, [40.0, 40.0, 40.0])
        many = st_with(LATHRIL, *[card(f"E{i}") for i in range(7)])
        many.creature_tokens.append(E.TokenGroup(name="Elf Warrior", count=3, power=1, toughness=1))
        many.opponents = [40.0, 40.0, 40.0]
        self.assertTrue(E.execute_semantic_ability(many, _S(), many.battlefield[0], ab))
        self.assertEqual(many.opponents, [30.0, 30.0, 30.0])
        self.assertEqual(sum(1 for p in many.battlefield if p.tapped), 8)   # Lathril + 7 elves
        spent = [g for g in many.creature_tokens if getattr(g, "_tapped_for_cost_turn", None) == many.turn]
        self.assertEqual(sum(g.count for g in spent), 3)

    def test_tokens_that_attacked_cannot_pay_tap_costs(self):
        ab = [x for x in E.parse_oracle_semantics(LATHRIL) if x.ability_kind == "activated"][0]
        st = st_with(LATHRIL, *[card(f"E{i}") for i in range(7)])
        st.creature_tokens.append(E.TokenGroup(name="Elf Warrior", count=3, power=1, toughness=1, entered_turn=2))
        st._v4760_attack_done_turn = st.turn
        self.assertFalse(E.execute_semantic_ability(st, _S(), st.battlefield[0], ab))

    def test_coverage_notes(self):
        self.assertIn("etb_team_pump_x_creatures", E.team_effects_note(HOOF))
        self.assertIn("x_creature_tutor_to_battlefield", E.team_effects_note(FINALE))
        self.assertIn("tap_n_untapped_cost", E.team_effects_note(LATHRIL))
        self.assertEqual(E.team_effects_note(BEAR), "")


if __name__ == "__main__":
    unittest.main()
