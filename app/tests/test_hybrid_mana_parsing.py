"""
Unit tests for v4.35.0: hybrid-mana cost parsing (`parse_mana_cost`) and
multi-option mana-ability parsing (`parse_add_mana_options`).

Found via ChatGPT external review (see Docs/README.md v4.35.0 entry).

Two confirmed bugs in `parse_mana_cost`, reproduced against real cards
already in this project's own Scryfall cache (App/.scryfall_card_cache_v4.json):
Sokka, Lateral Strategist {1}{W/U}{W/U}; Kirol, Attentive First-Year
{1}{R/W}{R/W}; Practiced Scrollsmith {R}{R/W}{W}; Raph & Leo, Sibling
Rivals {1}{R/W}{R/W}.

  1. A two-real-color hybrid like {W/U} recorded NO colored requirement at
     all (only a mono-colored hybrid with exactly one recognized color got
     one) - so find_payment's real payment path (payment_meets is a hard
     AND-check on `req`) would accept paying {W/U} with, say, pure green
     mana, which is illegal.
  2. A mono-colored hybrid with a generic fallback like {2/W} recorded a
     MANDATORY color requirement (req["W"] += 1) despite {2/W} always being
     legally payable with 2 generic mana of ANY kind - so the real payment
     path would refuse a perfectly legal cast whenever the caster had
     enough generic mana but no white.

One confirmed bug in `parse_add_mana_options`: a 3+-option comma/"or" choice
list ("Add {W}, {U}, or {B}." - the classic Triome land pattern) only ever
produced the FIRST option; the other two were silently dropped. No card in
this project's current cache has this exact shape, but it is a common,
real Commander land pattern (e.g. Savai Triome), so this closes the same
documented gap proactively.

Run from the project root:
    python -m unittest tests.test_hybrid_mana_parsing -v
"""
from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


class TwoColorHybridRequiresOneOfItsPrintedColorsTests(unittest.TestCase):
    def test_w_slash_u_requires_white_not_nothing(self):
        # Sokka, Lateral Strategist: {1}{W/U}{W/U} - real project card.
        total, req = engine.parse_mana_cost("{1}{W/U}{W/U}")
        self.assertEqual(total, 3)
        self.assertGreater(sum(req.values()), 0, "a two-color hybrid must require SOME printed color, not none")
        # The first-listed color is the deterministic convention this fix uses.
        self.assertEqual(req, Counter({"W": 2}))

    def test_r_slash_w_requires_red_not_nothing(self):
        # Kirol, Attentive First-Year / Raph & Leo, Sibling Rivals: {1}{R/W}{R/W}.
        total, req = engine.parse_mana_cost("{1}{R/W}{R/W}")
        self.assertEqual(total, 3)
        self.assertEqual(req, Counter({"R": 2}))

    def test_end_to_end_payment_rejects_an_off_color_pool(self):
        # Real regression: before the fix, {W/U}'s req was empty, so
        # find_payment's payment_meets would accept ANY color for it,
        # including green - illegal under real MTG rules.
        total, req = engine.parse_mana_cost("{W/U}")
        pool_all_green = Counter({"G": 1})
        self.assertFalse(engine.payment_meets(pool_all_green, total, req))
        pool_with_white = Counter({"W": 1})
        self.assertTrue(engine.payment_meets(pool_with_white, total, req))


class MonoColorHybridWithGenericFallbackNeverBlocksTheGenericPathTests(unittest.TestCase):
    def test_2_slash_w_has_no_mandatory_color_requirement(self):
        total, req = engine.parse_mana_cost("{2/W}")
        self.assertEqual(
            sum(req.values()), 0,
            "{2/W} can always be paid with 2 generic mana - it must never "
            "impose a mandatory color requirement",
        )
        self.assertEqual(total, 2)

    def test_end_to_end_payment_accepts_pure_generic_mana(self):
        # Real regression: before the fix, {2/W} required a literal W pip,
        # so a caster with 2 non-white mana (a perfectly legal payment in
        # real MTG) would be illegally refused.
        total, req = engine.parse_mana_cost("{2/W}")
        pool_two_generic = Counter({"C": 2})
        self.assertTrue(engine.payment_meets(pool_two_generic, total, req))

    def test_practiced_scrollsmith_full_cost_has_no_mandatory_pip_from_the_hybrid_symbol(self):
        # Practiced Scrollsmith: {R}{R/W}{W} - real project card. Note this
        # specific real card is a two-COLOR hybrid ({R/W}), not a numeral
        # hybrid, so it DOES get a mandatory requirement via the other
        # branch (see TwoColorHybridRequiresOneOfItsPrintedColorsTests) -
        # this test just pins its overall total/req shape for completeness.
        total, req = engine.parse_mana_cost("{R}{R/W}{W}")
        self.assertEqual(total, 3)
        self.assertEqual(req, Counter({"R": 2, "W": 1}))


class PhyrexianManaIsUnaffectedByThisFixTests(unittest.TestCase):
    def test_phyrexian_mana_still_requires_its_color_same_as_before(self):
        # {W/P}: not a numeral hybrid (no digit), still one real color -
        # falls into the same branch as before, unchanged behavior (this
        # engine's real payment path doesn't model paying life for
        # Phyrexian mana - a separately documented, pre-existing gap).
        total, req = engine.parse_mana_cost("{W/P}")
        self.assertEqual(total, 1)
        self.assertEqual(req, Counter({"W": 1}))


class AddManaChoiceListParsingTests(unittest.TestCase):
    def test_three_option_oxford_comma_list_produces_all_three_options(self):
        options = engine.parse_add_mana_options("{T}: Add {W}, {U}, or {B}.")
        got = {tuple(sorted(o.items())) for o in options}
        expected = {(("W", 1),), (("U", 1),), (("B", 1),)}
        self.assertEqual(got, expected)

    def test_four_option_list_produces_all_four_options(self):
        options = engine.parse_add_mana_options("{T}: Add {W}, {U}, {B}, or {R}.")
        got = {tuple(sorted(o.items())) for o in options}
        expected = {(("W", 1),), (("U", 1),), (("B", 1),), (("R", 1),)}
        self.assertEqual(got, expected)

    def test_two_option_list_still_works_as_before(self):
        options = engine.parse_add_mana_options("{T}: Add {G} or {W}.")
        got = {tuple(sorted(o.items())) for o in options}
        self.assertEqual(got, {(("G", 1),), (("W", 1),)})

    def test_contiguous_simultaneous_symbols_are_unaffected(self):
        options = engine.parse_add_mana_options("Add {C}{C}.")
        self.assertEqual(options, [Counter({"C": 2})])

    def test_add_gw_simultaneous_two_colors_is_unaffected(self):
        options = engine.parse_add_mana_options("Add {G}{W}.")
        self.assertEqual(options, [Counter({"G": 1, "W": 1})])


if __name__ == "__main__":
    unittest.main()
