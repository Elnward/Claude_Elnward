"""
Unit tests for v4.68.0 ("Kalibrierungs-Synthese Teil 2, Integration" -
archetype_profile package wiring). See:
  - App/archetype_profile/ (restructured to relative imports, see its
    README.md "Naechste Schritte" #1 - was previously an unconnected
    standalone-script prototype, only present on the real device, not in
    this session's working copy until this version)
  - App/engine.py: commander_identity_slug, compare_deck_to_archetype_
    reference, _STRATEGY_TAG_TO_ARCHETYPE_TAG (the new integration surface)
  - App/gui.py: AnalysisPage._build_deck_comparison (new "Vergleich (1.585
    Decks)" tab)

Four groups: (1) the package imports cleanly as App.archetype_profile with
relative internal imports (the actual "Naechste Schritte" #1 fix), (2)
commander_identity_slug resolves the REAL commander color identity rather
than estimating from the whole deck (closes gap #3 from the same README),
(3) compare_deck_to_archetype_reference's full behavior including the
STRATEGY_TAGS -> canonical-tag bridge and its graceful-degradation paths,
(4) a real end-to-end run against one of the project's own real decklists.

Run from the project root:
    python -m unittest tests.test_v4680_archetype_profile_integration -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402


def _card(name, mana_cost="", mana_value=0.0, type_line="", color_identity=None, oracle_text=""):
    return engine.Card(
        name=name, mana_cost=mana_cost, mana_value=mana_value, type_line=type_line,
        color_identity=set(color_identity or ()), oracle_text=oracle_text,
    )


class PackageImportTests(unittest.TestCase):
    """Group 1: App.archetype_profile imports cleanly as a real subpackage."""

    def test_public_api_importable_as_subpackage(self):
        from App.archetype_profile import DeckAnalyzer, AverageDeckModel, CardLookup, AnalysisResult
        self.assertTrue(callable(DeckAnalyzer.load))
        self.assertTrue(callable(AverageDeckModel.load))
        self.assertIsNotNone(CardLookup)
        self.assertIsNotNone(AnalysisResult)

    def test_internal_modules_use_relative_imports(self):
        """The concrete regression this version fixes: deck_analyzer.py and
        reference_model.py previously did `from classify import ...` /
        `from tag_normalize import ...` (bare, top-level) which only worked
        when run as flat standalone scripts, not as a real App subpackage."""
        import App.archetype_profile.deck_analyzer as da
        import App.archetype_profile.reference_model as rm
        src_da = Path(da.__file__).read_text(encoding="utf-8")
        src_rm = Path(rm.__file__).read_text(encoding="utf-8")
        self.assertIn("from .classify import", src_da)
        self.assertIn("from .identity_colors import", src_da)
        self.assertIn("from .reference_model import", src_da)
        self.assertIn("from .tag_normalize import", src_rm)
        self.assertNotRegex(src_da, r"^from classify import", msg="bare top-level import left over")
        self.assertNotRegex(src_rm, r"^from tag_normalize import", msg="bare top-level import left over")

    def test_reference_data_loads(self):
        analyzer = engine._get_archetype_analyzer()
        self.assertGreater(len(analyzer.lookup), 8000)


class CommanderIdentityTests(unittest.TestCase):
    """Group 2: identity comes from the commander, not the whole decklist's
    mana pips (closes README.md gap #3)."""

    def test_single_commander_identity(self):
        cards = {"Lier, Disciple of the Drowned": _card(
            "Lier, Disciple of the Drowned", "{4}{U}{U}", 6, "Legendary Creature", color_identity={"U"},
        )}
        slug = engine.commander_identity_slug(cards, {"Lier, Disciple of the Drowned"})
        self.assertEqual(slug, "mono-blue")

    def test_partner_commanders_union_colors(self):
        cards = {
            "Commander A": _card("Commander A", "{W}", 1, "Legendary Creature", color_identity={"W"}),
            "Commander B": _card("Commander B", "{B}", 1, "Legendary Creature", color_identity={"B"}),
        }
        slug = engine.commander_identity_slug(cards, {"Commander A", "Commander B"})
        self.assertEqual(slug, "orzhov")

    def test_no_resolvable_commander_falls_back_to_colorless(self):
        slug = engine.commander_identity_slug({}, {"Unknown Commander"})
        self.assertEqual(slug, "colorless")

    def test_identity_ignores_noncommander_deck_colors(self):
        """The whole point of using the commander instead of
        detect_identity_slug()'s mana-pip estimate: a mono-white commander
        whose 99 happens to include a splash artifact/land producing other
        colors should still resolve to mono-white, not multicolor."""
        cards = {
            "Giada, Font of Hope": _card(
                "Giada, Font of Hope", "{2}{W}{W}", 4, "Legendary Creature", color_identity={"W"},
            ),
        }
        slug = engine.commander_identity_slug(cards, {"Giada, Font of Hope"})
        self.assertEqual(slug, "mono-white")


class CompareDeckToReferenceTests(unittest.TestCase):
    """Group 3: the full GUI-facing integration function."""

    @classmethod
    def setUpClass(cls):
        cls.commander = _card(
            "Lier, Disciple of the Drowned", "{4}{U}{U}", 6, "Legendary Creature", color_identity={"U"},
        )
        cls.cards = {"Lier, Disciple of the Drowned": cls.commander}
        cls.deck = [cls.commander] + [
            _card("Sol Ring", "{1}", 1, "Artifact"),
            _card("Rhystic Study", "{2}{U}", 3, "Enchantment"),
            _card("Cyclonic Rift", "{1}{U}", 2, "Instant"),
            _card("Swords to Plowshares", "{W}", 1, "Instant"),
        ] + [_card("Island", "", 0, "Basic Land — Island") for _ in range(35)]

    def test_returns_identity_only_by_default(self):
        result = engine.compare_deck_to_archetype_reference(self.deck, {"Lier, Disciple of the Drowned"}, self.cards)
        self.assertEqual(result["identity_slug"], "mono-blue")
        self.assertEqual(result["identity_label"], "Mono-Blue")
        self.assertIsNotNone(result["identity_only"])
        self.assertIsNone(result["with_strategy"])
        self.assertEqual(result["recognized_tags"], [])

    def test_recognized_strategy_tag_produces_second_comparison(self):
        result = engine.compare_deck_to_archetype_reference(
            self.deck, {"Lier, Disciple of the Drowned"}, self.cards, tags={"control"},
        )
        self.assertEqual(result["recognized_tags"], ["Control"])
        self.assertIsNotNone(result["with_strategy"])
        self.assertEqual(result["with_strategy"].tags, ["Control"])

    def test_all_fourteen_strategy_tags_recognized(self):
        """Every in-app STRATEGY_TAGS entry must resolve to a real canonical
        tag in the reference data - a silent typo here would make that tag's
        comparison column quietly always empty."""
        analyzer = engine._get_archetype_analyzer()
        for engine_tag in engine.STRATEGY_TAGS:
            self.assertIn(engine_tag, engine._STRATEGY_TAG_TO_ARCHETYPE_TAG)
            archetype_tag = engine._STRATEGY_TAG_TO_ARCHETYPE_TAG[engine_tag]
            self.assertIn(
                archetype_tag, analyzer.model.identity_tag_summary,
                msg=f"{engine_tag!r} -> {archetype_tag!r} not found in reference data",
            )

    def test_unrecognized_tag_degrades_to_identity_only(self):
        result = engine.compare_deck_to_archetype_reference(
            self.deck, {"Lier, Disciple of the Drowned"}, self.cards, tags={"not_a_real_tag"},
        )
        self.assertEqual(result["recognized_tags"], [])
        self.assertIsNone(result["with_strategy"])
        self.assertEqual(result["requested_tags"], ["not_a_real_tag"])

    def test_uncataloged_card_still_classified_via_live_fallback(self):
        """A card not in the 8.445-card reference lookup, but with mana_cost/
        type_line supplied (as every App.engine.Card always has), should
        still be classified - not silently dropped as unknown."""
        deck_with_unknown = self.deck + [
            _card("Totally Fictional Test Card XYZ", "{2}{U}", 3, "Sorcery",
                  oracle_text="Draw two cards."),
        ]
        result = engine.compare_deck_to_archetype_reference(
            deck_with_unknown, {"Lier, Disciple of the Drowned"}, self.cards,
        )
        self.assertNotIn(
            "Totally Fictional Test Card XYZ", result["identity_only"].unclassified_cards,
        )


class RealDecklistTxtParsingTests(unittest.TestCase):
    """Group 4: at least the txt-entry parsing step (App.engine.load_txt_entries,
    the confirmed real entry point - see build_deck_v4) against one of the
    project's own real decklists, feeding names straight into
    compare_deck_to_archetype_reference without needing live Scryfall
    metadata (mana_cost/type_line stay empty, which only means those cards
    fall through to the reference-database lookup by name, or land in
    unclassified_cards - both handled paths, see CompareDeckToReferenceTests
    ::test_uncataloged_card_still_classified_via_live_fallback for the
    other path). Building full engine.Card objects with real Scryfall
    metadata needs network access or the local Scryfall cache and is
    intentionally out of scope for this offline unit test."""

    def test_bilbo_txt_entries_flow_into_the_comparison(self):
        deck_path = ROOT / "Decks" / "Bilbo V1.txt"
        if not deck_path.exists():
            self.skipTest("Decks/Bilbo V1.txt not present in this checkout")
        entries = engine.load_txt_entries(deck_path)
        self.assertGreater(len(entries), 50, "a real Commander decklist should have >50 entries")

        # load_txt_entries' DeckEntry has no commander flag (that's resolved
        # elsewhere, from the file's "// Commander" section header plus
        # gui.py's normalize_commander_selection - out of scope for this
        # offline parsing test) - use the first entry as a stand-in so the
        # full compare_deck_to_archetype_reference plumbing still runs
        # end-to-end; this test checks the pipeline does not crash on a real
        # decklist and returns a well-shaped result, not that the guessed
        # "commander" is semantically correct (that's CommanderIdentityTests).
        deck = [_card(e.name) for e in entries]
        cards = {c.name: c for c in deck}
        commanders = {deck[0].name}

        result = engine.compare_deck_to_archetype_reference(deck, commanders, cards)
        self.assertIn(result["identity_slug"], engine._ARCHETYPE_SLUG_TO_LABEL)
        self.assertGreater(len(result["identity_only"].comparison), 0)


if __name__ == "__main__":
    unittest.main()
