"""
v4.76.0 WP1: scaling mana abilities (App/mana_scaling registry).

Diagnosis (Docs/README.md v4.76.0): the generic parser read
"Add {G} for each Elf you control" as a flat 1 mana and
"Add X mana ... where X is the number of Elves" / "equal to its power" as
0 mana. These tests pin the corrected outputs with real Oracle texts, but
built as in-memory Cards so they never depend on the local Scryfall cache.

Run from the project root:
    python -m unittest tests.test_v4760_mana_scaling -v
"""
from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from App import engine as E  # noqa: E402
from App import mana_scaling  # noqa: E402

ELF = "Creature — Elf Druid"


def card(name, text, type_line=ELF, power=1, toughness=1, keywords=None):
    return E.Card(name=name, oracle_text=text, type_line=type_line,
                  power=power, toughness=toughness, keywords=set(keywords or ()))


LLANOWAR = card("Llanowar Elves", "{T}: Add {G}.")
PRIEST = card("Priest of Titania", "{T}: Add {G} for each Elf on the battlefield.")
ARCHDRUID = card("Elvish Archdruid", "Other Elf creatures you control get +1/+1.\n{T}: Add {G} for each Elf you control.", power=2, toughness=2)
CIRCLE = card("Circle of Dreams Druid", "{T}: Add {G} for each creature you control.")
CHANNELER = card("Wirewood Channeler", "{T}: Add X mana of any one color, where X is the number of Elves on the battlefield.", type_line="Creature — Elf Druid")
MARWYN = card("Marwyn, the Nurturer", "Whenever another Elf you control enters, put a +1/+1 counter on Marwyn.\n{T}: Add an amount of {G} equal to Marwyn's power.", type_line="Legendary Creature — Elf Druid")
HERITAGE = card("Heritage Druid", "Tap three untapped Elves you control: Add {G}{G}{G}.")
CRADLE = card("Gaea's Cradle", "{T}: Add {G} for each creature you control.", type_line="Legendary Land", power=None, toughness=None)
BEAR = card("Grizzly Bears", "", type_line="Creature — Bear", power=2, toughness=2)


class _Strategy:
    commander_colors = {"G", "B"}


def state_with(*cards, turn=5, entered=1):
    st = E.GameState(library=[], hand=[], command_zone=[])
    st.turn = turn
    for c in cards:
        st.battlefield.append(E.Permanent(card=c, entered_turn=entered))
    return st


def opts(st, c):
    p = next(p for p in st.battlefield if p.card is c)
    return [dict(o) for o in E.card_mana_options(p, st, _Strategy())]


class ScalingManaTest(unittest.TestCase):
    def test_flat_dork_unchanged(self):
        st = state_with(LLANOWAR, PRIEST)
        self.assertEqual(opts(st, LLANOWAR), [{"G": 1}])

    def test_per_elf_on_battlefield_counts_own_elves(self):
        st = state_with(LLANOWAR, PRIEST, ARCHDRUID, BEAR)
        self.assertEqual(opts(st, PRIEST), [{"G": 3}])  # bear is not an Elf

    def test_per_elf_you_control(self):
        st = state_with(LLANOWAR, PRIEST, ARCHDRUID)
        self.assertEqual(opts(st, ARCHDRUID), [{"G": 3}])

    def test_per_creature_counts_tokens(self):
        st = state_with(CIRCLE, BEAR)
        st.creature_tokens.append(E.TokenGroup(name="Elf Warrior", count=2))
        self.assertEqual(opts(st, CIRCLE), [{"G": 4}])

    def test_elf_tokens_count_as_elves(self):
        st = state_with(PRIEST)
        st.creature_tokens.append(E.TokenGroup(name="Elf Warrior", count=2))
        st.creature_tokens.append(E.TokenGroup(name="Soldier", count=5))
        self.assertEqual(opts(st, PRIEST), [{"G": 3}])

    def test_x_any_one_color_limited_to_commander_colors(self):
        st = state_with(CHANNELER, LLANOWAR)
        self.assertEqual(sorted(opts(st, CHANNELER), key=str), sorted([{"B": 2}, {"G": 2}], key=str))

    def test_equal_to_power_includes_counters_and_team_bonus(self):
        st = state_with(MARWYN, ARCHDRUID)
        p = next(p for p in st.battlefield if p.card is MARWYN)
        p.counters = 2
        # 1 base + 2 counters + 1 from Archdruid's "other Elves get +1/+1"
        self.assertEqual(opts(st, MARWYN), [{"G": 4}])

    def test_tap_three_untapped_requires_enough_elves(self):
        st = state_with(HERITAGE, LLANOWAR)
        self.assertEqual(opts(st, HERITAGE), [])
        st2 = state_with(HERITAGE, LLANOWAR, PRIEST)
        self.assertEqual(opts(st2, HERITAGE), [{"G": 3}])

    def test_land_scaling(self):
        st = state_with(CRADLE, BEAR, LLANOWAR)
        self.assertEqual(opts(st, CRADLE), [{"G": 2}])

    def test_summoning_sick_and_tapped_produce_nothing(self):
        st = state_with(PRIEST, LLANOWAR, turn=5, entered=5)
        self.assertEqual(opts(st, PRIEST), [])
        st2 = state_with(PRIEST, LLANOWAR)
        st2.battlefield[0].tapped = True
        self.assertEqual(opts(st2, PRIEST), [])

    def test_heritage_payment_taps_co_payers(self):
        st = state_with(HERITAGE, BEAR, card("Elf A", ""), card("Elf B", ""))
        plan = E.find_payment(st, _Strategy(), 3, Counter({"G": 3}))
        self.assertIsNotNone(plan)
        E.apply_payment(st, plan, _Strategy())
        tapped = sorted(p.card.name for p in st.battlefield if p.tapped)
        self.assertEqual(tapped, ["Elf A", "Elf B", "Heritage Druid"])

    def test_coverage_report_marks_registry_resolver(self):
        rows = E.card_model_coverage_rows([PRIEST, LLANOWAR])
        by = {r["Name"]: r for r in rows}
        self.assertEqual(by["Priest of Titania"]["Dedicated resolver"], "yes")
        self.assertIn("mana_scaling:", by["Priest of Titania"]["Dedicated resolver note"])
        self.assertEqual(by["Llanowar Elves"]["Dedicated resolver"], "no")

    def test_definitions_are_all_wired_to_handlers(self):
        from App.mana_scaling.registry import _HANDLERS
        for d in mana_scaling.DEFINITIONS:
            self.assertIn(d.handler, _HANDLERS, d.id)


if __name__ == "__main__":
    unittest.main()
