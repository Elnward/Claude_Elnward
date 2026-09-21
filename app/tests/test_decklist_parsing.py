"""
Regression tests for App.engine's TXT deck-list line parser.

Covers a real bug found via the GUI: Moxfield/Archidekt-style exports append a
trailing foil/finish marker like " *F*" after "(SET) collector_number", which the
original TXT_LINE_RE did not expect - it silently swallowed the whole set/collector
suffix into the card NAME instead, so Scryfall lookups failed with garbled names.

v4.15.9 (Fremd-Deck-Import) adds: "4x Card" quantity notation, a foil marker
surviving even with no set/collector present, and tolerance for bare (non-"//")
header/comment lines - Commander/Deck/Sideboard/Companion section keywords
(matching the header families the cross-site decklist.gg importer documents)
plus arbitrary unrecognized header/prose lines (a bare category header, a
Moxfield "About" metadata block) that must not crash the import. See
tests.test_decklist_parsing.BareHeaderToleranceTests and
FlexibleQuantityAndFoilTests below.

v4.16.0 (Fremd-Deck-Import cont'd) adds two more real-world bugs found by
running actual EDHREC-sourced and official Wizards precon decklists through
the tool: (1) a trailing "(Commander)" annotation on a card's own line, with
no section header at all - the real format several official Commander
precon text exports (Secrets of Strixhaven, Tarkir: Dragonstorm, Lorwyn
Eclipsed) use - was previously swallowed into the parsed card NAME. See
InlineCommanderAnnotationTests below. (2) ScryfallProvider.get_many() only
indexed Scryfall's returned cards by their combined "Front // Back" name for
double-faced/transform cards, so a decklist line naming just the front face
(e.g. "Duskwatch Recruiter") silently failed with "No metadata for X" even
though Scryfall found and returned the card. See
ScryfallCardIndexingTests below (exercises the extracted, network-free
index_scryfall_cards() helper directly).

v4.17.0 fixes a much bigger finding from a real local run against all 12
Fremd-Decks: App/engine.py monkey-patches ScryfallProvider.get_many at
MODULE LOAD TIME, twice (_scryfall_get_many_requests, then
_scryfall_get_many_urllib overrides it again a couple thousand lines
later) - so the v4.16.0 DFC-indexing fix, applied only to the class body's
own get_many(), was DEAD CODE the whole time; the urllib version actually
live at runtime never had it, which is exactly why Duskwatch Recruiter kept
failing for the user even after that "fix". All three get_many() bodies
now delegate to one shared, tested method, ScryfallProvider._resolve_missing(),
which also (a) collects unresolved cards across EVERY batch instead of
raising on the first bad one (so a ~99-card deck's second batch was
previously never even checked once the first batch had a problem), and (b)
falls back to Scryfall's own fuzzy /cards/named endpoint for any name-only
entry the exact lookup still can't match. See
ScryfallGetManyLiveBehaviorTests below - it exercises the ACTUAL bound
ScryfallProvider.get_many (via a fake urllib.request.urlopen), not just the
extracted helper, specifically so this class of bug (fixing a shadowed,
non-live copy) cannot silently recur.

Run from the project root:
    python -m unittest tests.test_decklist_parsing -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def _load_txt(text: str):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "deck.txt"
        p.write_text(text, encoding="utf-8")
        return engine.load_txt_entries(p)


class TxtLineRegexTests(unittest.TestCase):
    def test_plain_line_without_set_info(self):
        m = engine.TXT_LINE_RE.match("1 Sol Ring")
        self.assertEqual(m.group("name"), "Sol Ring")
        self.assertIsNone(m.group("set"))
        self.assertIsNone(m.group("collector"))

    def test_line_with_set_and_collector_number(self):
        m = engine.TXT_LINE_RE.match("1 Sol Ring (C21) 263")
        self.assertEqual(m.group("name"), "Sol Ring")
        self.assertEqual(m.group("set"), "C21")
        self.assertEqual(m.group("collector"), "263")

    def test_line_with_foil_marker_is_not_swallowed_into_the_name(self):
        m = engine.TXT_LINE_RE.match("1 Wyleth, Soul of Steel (CMR) 362 *F*")
        self.assertEqual(m.group("name"), "Wyleth, Soul of Steel")
        self.assertEqual(m.group("set"), "CMR")
        self.assertEqual(m.group("collector"), "362")

    def test_line_with_set_code_containing_digits(self):
        m = engine.TXT_LINE_RE.match("1 Hordeling Outburst (F15) 3 *F*")
        self.assertEqual(m.group("name"), "Hordeling Outburst")
        self.assertEqual(m.group("set"), "F15")
        self.assertEqual(m.group("collector"), "3")

    def test_name_with_internal_parentheses_like_text_is_still_fine(self):
        m = engine.TXT_LINE_RE.match("1 The Scarlet Witch (MSH) 431 *F*")
        self.assertEqual(m.group("name"), "The Scarlet Witch")
        self.assertEqual(m.group("set"), "MSH")
        self.assertEqual(m.group("collector"), "431")

    def test_etched_marker_also_supported(self):
        m = engine.TXT_LINE_RE.match("1 Some Card (NEO) 123 *E*")
        self.assertEqual(m.group("name"), "Some Card")
        self.assertEqual(m.group("set"), "NEO")
        self.assertEqual(m.group("collector"), "123")

    def test_multi_digit_count(self):
        m = engine.TXT_LINE_RE.match("12 Forest (MH3) 401")
        self.assertEqual(m.group("count"), "12")
        self.assertEqual(m.group("name"), "Forest")


class RealDeckFilesParseCleanlyTests(unittest.TestCase):
    """Every shipped deck should parse with set_code/collector_number on every line
    that has one in the source file - this is what feeds the Scryfall lookup."""

    def _check_deck(self, filename: str):
        path = ROOT / "Decks" / filename
        if not path.exists():
            self.skipTest(f"{filename} not present in this checkout")
        entries = engine.load_txt_entries(path)
        self.assertGreater(len(entries), 0)
        garbled = [
            e for e in entries
            if "(" in e.name and ")" in e.name and not e.set_code
        ]
        self.assertEqual(
            garbled, [],
            f"entries whose name still contains an unparsed '(...)' suffix: {garbled}",
        )
        # v4.17.0: every shipped deck happens to be a legal 100-card
        # Commander deck (99 + commander, or the commander folded into a
        # header-less card list) - a cheap, meaningful sanity check that a
        # future edit hasn't dropped or duplicated a line.
        total = sum(e.count for e in entries)
        self.assertEqual(total, 100, f"{filename}: expected 100 total cards, got {total}")

    def test_bilbo_deck_parses_cleanly(self):
        self._check_deck("Bilbo V1.txt")

    def test_mice_with_swords_deck_parses_cleanly(self):
        self._check_deck("Mice with Swords.txt")

    def test_aziza_deck_parses_cleanly(self):
        self._check_deck("Aziza V2.txt")

    def test_katara_deck_parses_cleanly(self):
        self._check_deck("Katara V3.txt")


class FremdDeckFilesParseCleanlyTests(unittest.TestCase):
    """v4.17.0 (task #25): the 12 Fremd-Decks (5 hand-assembled from real
    EDHREC data in v4.15.9/v4.16.0, plus 7 real official Wizards precon
    exports) now build successfully end-to-end - user-confirmed via a real
    local run: engine_invariants PASS, 0 resource-invariant violations, 0
    payment-resource conflicts, across all 12 (see the v4.17.0 README
    entry). That confirmation needed live Scryfall access this project
    can't reach from here, so it can't be re-verified as an automated test;
    what CAN be locked in permanently, offline, the same way
    RealDeckFilesParseCleanlyTests does for the 4 original decks above, is
    the parsing half of that guarantee: every file parses without a
    garbled name, is a legal 100-card Commander deck, and its detected
    commander hints match what a real run actually used.

    Two files legitimately have NO detectable commander hint by design
    (The Ur-Dragon: EDHREC-clipboard-style, no header, no annotation at
    all; Quandrix Unlimited, Prismari Artistry: real official precon
    exports with no header and no inline "(Commander)" annotation on any
    line) - confirmed with the user that this is expected, not a defect;
    the GUI needs a manual commander pick for those three.
    """

    FREMD = ROOT / "Decks" / "Fremd"

    def _check_deck(self, relative_path: str, expected_commander_hints):
        path = self.FREMD / relative_path
        if not path.exists():
            self.skipTest(f"{relative_path} not present in this checkout")
        entries = engine.load_txt_entries(path)
        self.assertGreater(len(entries), 0)
        garbled = [
            e for e in entries
            if "(" in e.name and ")" in e.name and not e.set_code
        ]
        self.assertEqual(
            garbled, [],
            f"entries whose name still contains an unparsed '(...)' suffix: {garbled}",
        )
        total = sum(e.count for e in entries)
        self.assertEqual(total, 100, f"{relative_path}: expected 100 total cards, got {total}")
        hints = engine.detect_commander_hints(path)
        self.assertEqual(sorted(hints), sorted(expected_commander_hints))

    def test_krenko_mob_boss(self):
        self._check_deck("Krenko Mob Boss.txt", ["Krenko, Mob Boss"])

    def test_the_scarab_god(self):
        self._check_deck("The Scarab God.txt", ["The Scarab God"])

    def test_korvold_fae_cursed_king(self):
        self._check_deck("Korvold Fae-Cursed King.txt", ["Korvold, Fae-Cursed King"])

    def test_old_gnawbone(self):
        self._check_deck("Old Gnawbone.txt", ["Old Gnawbone"])

    def test_the_ur_dragon(self):
        self._check_deck("The Ur-Dragon.txt", [])

    def test_precon_witherbloom_pestilence(self):
        self._check_deck("Precons/Witherbloom Pestilence.txt", ["Dina, Essence Brewer"])

    def test_precon_silverquill_influence(self):
        self._check_deck("Precons/Silverquill Influence.txt", ["Killian, Decisive Mentor"])

    def test_precon_quandrix_unlimited(self):
        self._check_deck("Precons/Quandrix Unlimited.txt", [])

    def test_precon_lorehold_spirit(self):
        self._check_deck("Precons/Lorehold Spirit.txt", ["Quintorius, History Chaser"])

    def test_precon_prismari_artistry(self):
        self._check_deck("Precons/Prismari Artistry.txt", [])

    def test_precon_blight_curse(self):
        self._check_deck("Precons/Blight Curse.txt", ["Auntie Ool, Cursewretch"])

    def test_precon_sultai_arisen(self):
        self._check_deck("Precons/Sultai Arisen.txt", ["Teval, the Balanced Scale"])


class FlexibleQuantityAndFoilTests(unittest.TestCase):
    """v4.15.9: '4x Card' alongside '4 Card' (decklist.gg documents both as
    the two real quantity notations used across sites), and a foil marker
    that survives even with no set/collector on the line."""

    def test_x_suffixed_count_is_accepted(self):
        m = engine.TXT_LINE_RE.match("4x Lightning Bolt")
        self.assertEqual(m.group("count"), "4")
        self.assertEqual(m.group("name"), "Lightning Bolt")

    def test_x_suffixed_count_case_insensitive(self):
        m = engine.TXT_LINE_RE.match("2X Forest")
        self.assertEqual(m.group("count"), "2")
        self.assertEqual(m.group("name"), "Forest")

    def test_plain_count_still_works_unchanged(self):
        m = engine.TXT_LINE_RE.match("1 Sol Ring")
        self.assertEqual(m.group("count"), "1")
        self.assertEqual(m.group("name"), "Sol Ring")

    def test_foil_marker_survives_with_no_set_or_collector(self):
        m = engine.TXT_LINE_RE.match("1 Sol Ring *F*")
        self.assertEqual(m.group("name"), "Sol Ring")
        self.assertIsNone(m.group("set"))
        self.assertEqual(m.group("foil"), "F")

    def test_foil_marker_still_works_after_set_and_collector(self):
        m = engine.TXT_LINE_RE.match("1 Wyleth, Soul of Steel (CMR) 362 *F*")
        self.assertEqual(m.group("name"), "Wyleth, Soul of Steel")
        self.assertEqual(m.group("set"), "CMR")
        self.assertEqual(m.group("foil"), "F")

    def test_end_to_end_load_txt_entries_with_x_count_and_bare_foil(self):
        entries = _load_txt("4x Lightning Bolt\n1 Sol Ring *F*\n")
        self.assertEqual(len(entries), 2)
        by_name = {e.name: e for e in entries}
        self.assertEqual(by_name["Lightning Bolt"].count, 4)
        self.assertEqual(by_name["Sol Ring"].name, "Sol Ring")


class BareHeaderToleranceTests(unittest.TestCase):
    """v4.15.9 (Fremd-Deck-Import): a decklist that uses bare section headers
    (no '//' prefix) - as EDHREC/Moxfield-style exports may - must import
    cleanly instead of raising on the first header line."""

    def test_bare_commander_header_is_recognized_and_skipped(self):
        entries = _load_txt("Commander\n1 Bilbo, Birthday Celebrant\n\nDeck\n1 Sol Ring\n")
        names = [e.name for e in entries]
        self.assertIn("Bilbo, Birthday Celebrant", names)
        self.assertIn("Sol Ring", names)

    def test_bare_category_header_with_count_does_not_crash_import(self):
        entries = _load_txt(
            "Creatures (2)\n1 Birds of Paradise\n1 Llanowar Elves\n\n"
            "Lands (1)\n1 Forest\n"
        )
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Birds of Paradise", "Forest", "Llanowar Elves"])

    def test_moxfield_style_about_metadata_block_is_ignored(self):
        text = (
            "About\n"
            "This is my pet deck, built around go-wide tokens and a sac outlet.\n"
            "It leans aggressive but can grind if needed.\n\n"
            "Commander\n1 Mabel, Heir to Cragflame\n\n"
            "Deck\n1 Sol Ring\n1 Arcane Signet\n"
        )
        entries = _load_txt(text)
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Arcane Signet", "Mabel, Heir to Cragflame", "Sol Ring"])

    def test_bare_sideboard_header_excludes_its_cards(self):
        entries = _load_txt("Deck\n1 Sol Ring\n\nSideboard\n1 Pithing Needle\n")
        names = [e.name for e in entries]
        self.assertEqual(names, ["Sol Ring"])

    def test_bare_maybeboard_header_excludes_its_cards(self):
        entries = _load_txt("Deck\n1 Sol Ring\n\nMaybeboard\n1 Chaos Warp\n")
        names = [e.name for e in entries]
        self.assertEqual(names, ["Sol Ring"])

    def test_a_digit_leading_line_that_still_fails_to_parse_still_raises(self):
        # Safety net preserved: a genuinely corrupted card-shaped line must
        # not be silently swallowed the way a bare header line now is.
        with self.assertRaises(ValueError):
            _load_txt("Deck\n1 Sol Ring\n2)()(garbled\n")

    def test_slash_prefixed_headers_are_unchanged_from_before_v4159(self):
        # Original convention (our own shipped decks use this) must keep
        # working byte-for-byte the same.
        entries = _load_txt("// COMMANDER\n1 Bilbo, Birthday Celebrant\n\n1 Sol Ring\n")
        names = [e.name for e in entries]
        self.assertEqual(names, ["Bilbo, Birthday Celebrant", "Sol Ring"])

    def test_slash_prefixed_sideboard_still_excludes_its_cards(self):
        entries = _load_txt("1 Sol Ring\n\n// Sideboard\n1 Pithing Needle\n")
        names = [e.name for e in entries]
        self.assertEqual(names, ["Sol Ring"])


class DetectCommanderHintsBareHeaderTests(unittest.TestCase):
    """v4.15.9: detect_commander_hints (used by the GUI to pre-select a
    commander before the deck is fully built) recognizes a bare 'Commander'
    header the same way load_txt_entries does."""

    def _hints(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "deck.txt"
            p.write_text(text, encoding="utf-8")
            return engine.detect_commander_hints(p)

    def test_bare_commander_header(self):
        hints = self._hints("Commander\n1 Bilbo, Birthday Celebrant\n\nDeck\n1 Sol Ring\n")
        self.assertEqual(hints, ["Bilbo, Birthday Celebrant"])

    def test_bare_commanders_plural_header(self):
        hints = self._hints("Commanders\n1 Akiri, Fearless Voyager\n1 Bruse Tarl, Boorish Herder\n\nDeck\n1 Sol Ring\n")
        self.assertEqual(sorted(hints), ["Akiri, Fearless Voyager", "Bruse Tarl, Boorish Herder"])

    def test_slash_prefixed_commander_header_unchanged(self):
        hints = self._hints("// COMMANDER\n1 Mabel, Heir to Cragflame\n\n1 Sol Ring\n")
        self.assertEqual(hints, ["Mabel, Heir to Cragflame"])

    def test_no_commander_header_returns_empty(self):
        hints = self._hints("1 Sol Ring\n1 Arcane Signet\n")
        self.assertEqual(hints, [])


class InlineCommanderAnnotationTests(unittest.TestCase):
    """v4.16.0: real official Commander precon text exports (Secrets of
    Strixhaven, Tarkir: Dragonstorm, Lorwyn Eclipsed) use NO section header
    at all - a single flat card list - and mark the commander inline on its
    own line instead, e.g. "1 Dina, Essence Brewer (Commander)"."""

    def _hints(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "deck.txt"
            p.write_text(text, encoding="utf-8")
            return engine.detect_commander_hints(p)

    def test_annotation_is_stripped_from_the_parsed_card_name(self):
        entries = _load_txt("1 Dina, Essence Brewer (Commander)\n1 Sol Ring\n")
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Dina, Essence Brewer", "Sol Ring"])

    def test_annotation_is_case_insensitive(self):
        entries = _load_txt("1 Dina, Essence Brewer (commander)\n")
        self.assertEqual(entries[0].name, "Dina, Essence Brewer")

    def test_detect_commander_hints_finds_it_with_no_header_at_all(self):
        hints = self._hints(
            "1 Killian, Decisive Mentor (Commander)\n1 Command Tower\n1 Anguished Unmaking\n"
        )
        self.assertEqual(hints, ["Killian, Decisive Mentor"])

    def test_annotation_and_header_based_hints_are_deduplicated(self):
        hints = self._hints("Commander\n1 Bilbo, Birthday Celebrant (Commander)\n\nDeck\n1 Sol Ring\n")
        self.assertEqual(hints, ["Bilbo, Birthday Celebrant"])

    def test_flat_precon_list_with_no_header_and_no_annotation_still_parses(self):
        # Not every real precon paste has the annotation on every commander
        # line either - the file must still import cleanly even then (the
        # GUI simply falls back to manual commander selection).
        entries = _load_txt("1 Zimone, Infinite Analyst\n1 Command Tower\n1 Sol Ring\n")
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Command Tower", "Sol Ring", "Zimone, Infinite Analyst"])

    def test_real_witherbloom_precon_excerpt_end_to_end(self):
        # A trimmed, verbatim excerpt of the real "Witherbloom Pestilence"
        # Secrets of Strixhaven Commander precon text export.
        text = (
            "1 Dina, Essence Brewer (Commander)\n"
            "1 Bojuka Bog\n"
            "1 Command Tower\n"
            "8 Forest\n"
            "8 Swamp\n"
            "1 Beledros Witherbloom\n"
            "1 Blood Artist\n"
            "1 Arcane Signet\n"
            "1 Sol Ring\n"
        )
        entries = _load_txt(text)
        self.assertEqual(sum(e.count for e in entries), 23)
        names = {e.name for e in entries}
        self.assertIn("Dina, Essence Brewer", names)
        self.assertNotIn("Dina, Essence Brewer (Commander)", names)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "deck.txt"
            p.write_text(text, encoding="utf-8")
            self.assertEqual(engine.detect_commander_hints(p), ["Dina, Essence Brewer"])


class ScryfallCardIndexingTests(unittest.TestCase):
    """v4.16.0: index_scryfall_cards() (extracted from ScryfallProvider.get_many
    so it's testable without network) must index a double-faced/transform
    card by BOTH its combined "Front // Back" name and each individual face
    name, since a decklist normally names only the front face. Shapes below
    mirror Scryfall's real /cards/collection response schema for a transform
    card (top-level 'name' is the combined name; 'card_faces' holds each
    face's own name) - modeled on the real card Duskwatch Recruiter, whose
    front face is what any real decklist actually writes down.
    """

    DUSKWATCH_RECRUITER = {
        "name": "Duskwatch Recruiter // Krallenhorde Howler",
        "set": "soi",
        "collector_number": "187",
        "layout": "transform",
        "card_faces": [
            {"name": "Duskwatch Recruiter", "type_line": "Creature — Human Warrior"},
            {"name": "Krallenhorde Howler", "type_line": "Creature — Werewolf"},
        ],
    }
    SOL_RING = {
        "name": "Sol Ring",
        "set": "c21",
        "collector_number": "263",
    }

    def test_dfc_is_reachable_by_its_front_face_name(self):
        by_print, by_name = engine.index_scryfall_cards([self.DUSKWATCH_RECRUITER])
        self.assertIn("duskwatch recruiter", by_name)
        self.assertEqual(by_name["duskwatch recruiter"]["name"], "Duskwatch Recruiter // Krallenhorde Howler")

    def test_dfc_is_also_reachable_by_its_back_face_name(self):
        _, by_name = engine.index_scryfall_cards([self.DUSKWATCH_RECRUITER])
        self.assertIn("krallenhorde howler", by_name)

    def test_dfc_is_still_reachable_by_its_full_combined_name(self):
        _, by_name = engine.index_scryfall_cards([self.DUSKWATCH_RECRUITER])
        self.assertIn("duskwatch recruiter // krallenhorde howler", by_name)

    def test_dfc_is_reachable_by_set_and_collector_number(self):
        by_print, _ = engine.index_scryfall_cards([self.DUSKWATCH_RECRUITER])
        self.assertIn("set:soi#187", by_print)

    def test_single_faced_card_is_unaffected(self):
        by_print, by_name = engine.index_scryfall_cards([self.SOL_RING])
        self.assertEqual(by_name["sol ring"]["name"], "Sol Ring")
        self.assertEqual(by_print["set:c21#263"]["name"], "Sol Ring")

    def test_get_many_resolves_a_name_only_lookup_for_a_dfc_from_the_cache(self):
        # End-to-end through the real cache path (no network): pre-seed the
        # cache exactly the way get_many() would have stored it after a
        # successful online fetch, and confirm a name-only DeckEntry for the
        # front face resolves from the offline cache.
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            provider = engine.ScryfallProvider(cache_path, offline=True)
            provider.cache["name:duskwatch recruiter"] = self.DUSKWATCH_RECRUITER
            entry = engine.DeckEntry(name="Duskwatch Recruiter")
            result = provider.get_many([entry])
            self.assertIn(engine.ScryfallProvider.key(entry), result)


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._data = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _make_fake_urlopen(collection_payloads, fuzzy_results):
    """collection_payloads: one dict per expected POST (collection) call, in
    order. fuzzy_results: casefolded name -> card dict for GET (fuzzy
    /cards/named) calls; a missing key simulates Scryfall's 404 (no match).
    """
    calls = {"post": 0}

    def fake_urlopen(req, timeout=30):
        if req.get_method() == "POST":
            idx = calls["post"]
            calls["post"] += 1
            return _FakeHTTPResponse(collection_payloads[idx])
        import urllib.parse as up
        qs = up.parse_qs(up.urlparse(req.full_url).query)
        name = qs.get("fuzzy", [""])[0]
        result = fuzzy_results.get(name.casefold())
        if result is None:
            raise Exception("404 Not Found (simulated)")
        return _FakeHTTPResponse(result)

    return fake_urlopen


class ScryfallGetManyLiveBehaviorTests(unittest.TestCase):
    """v4.17.0. Exercises the ACTUAL bound ScryfallProvider.get_many (the
    live urllib-backed implementation, reached the same way build_deck()
    reaches it) via a fake urllib.request.urlopen - not just the extracted
    _resolve_missing() helper - so a future fix applied to the wrong one of
    several near-duplicate get_many() bodies fails a test immediately
    instead of silently doing nothing at runtime, the way v4.16.0's DFC fix
    did.
    """

    def setUp(self):
        self._original_urlopen = engine.urllib.request.urlopen

    def tearDown(self):
        engine.urllib.request.urlopen = self._original_urlopen

    def _provider(self, tmp):
        return engine.ScryfallProvider(Path(tmp) / "cache.json", offline=False)

    def test_get_many_is_bound_to_the_live_urllib_implementation(self):
        # Regression guard for the exact bug this version fixes: two
        # module-level monkey-patches of ScryfallProvider.get_many exist
        # (one requests-backed, one stdlib-urllib-backed); only the LAST
        # one assigned is ever live. If a third patch is ever added after
        # _scryfall_get_many_urllib without updating this test, this fails
        # immediately instead of silently shadowing a future fix again.
        self.assertIs(engine.ScryfallProvider.get_many, engine._scryfall_get_many_urllib)

    def test_dfc_resolves_by_front_face_name_through_the_live_bound_method(self):
        entries = [engine.DeckEntry(name="Duskwatch Recruiter")]
        payload = {"data": [ScryfallCardIndexingTests.DUSKWATCH_RECRUITER]}
        engine.urllib.request.urlopen = _make_fake_urlopen([payload], fuzzy_results={})
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            result = provider.get_many(entries)
        self.assertIn(engine.ScryfallProvider.key(entries[0]), result)

    def test_unresolved_cards_across_multiple_batches_are_all_reported_together(self):
        # 75 entries -> two batches (70 + 5). Batch 1 is missing its last
        # card, batch 2 is missing its last card too. Before v4.17.0 the
        # exception raised on batch 1 would abort before batch 2 was even
        # requested, so "Batch2 Card 4" would never be reported at all.
        entries = [engine.DeckEntry(name=f"Batch1 Card {i}") for i in range(70)]
        entries += [engine.DeckEntry(name=f"Batch2 Card {i}") for i in range(5)]
        payload1 = {"data": [{"name": f"Batch1 Card {i}"} for i in range(69)]}
        payload2 = {"data": [{"name": f"Batch2 Card {i}"} for i in range(4)]}
        engine.urllib.request.urlopen = _make_fake_urlopen([payload1, payload2], fuzzy_results={})
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            with self.assertRaises(RuntimeError) as ctx:
                provider.get_many(entries)
        message = str(ctx.exception)
        self.assertIn("Batch1 Card 69", message)
        self.assertIn("Batch2 Card 4", message)

    def test_fuzzy_fallback_resolves_a_name_the_exact_lookup_missed(self):
        # Mirrors the real "Sarkhan the Dragonspeaker" (missing comma) case:
        # the exact collection lookup finds nothing, but Scryfall's own
        # fuzzy /cards/named matcher - the authoritative arbiter, not a
        # guess made here - resolves it.
        entries = [engine.DeckEntry(name="Sarkhan the Dragonspeaker")]
        payload = {"data": []}
        fuzzy_card = {"name": "Sarkhan, the Dragonspeaker", "set": "dtk", "collector_number": "155"}
        engine.urllib.request.urlopen = _make_fake_urlopen(
            [payload], fuzzy_results={"sarkhan the dragonspeaker": fuzzy_card}
        )
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            result = provider.get_many(entries)
        key = engine.ScryfallProvider.key(entries[0])
        self.assertIn(key, result)
        self.assertEqual(result[key]["name"], "Sarkhan, the Dragonspeaker")

    def test_fuzzy_fallback_failure_still_raises_with_the_original_name(self):
        entries = [engine.DeckEntry(name="Totally Made Up Card")]
        payload = {"data": []}
        engine.urllib.request.urlopen = _make_fake_urlopen([payload], fuzzy_results={})
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            with self.assertRaises(RuntimeError) as ctx:
                provider.get_many(entries)
        self.assertIn("Totally Made Up Card", str(ctx.exception))

    def test_fuzzy_fallback_is_not_attempted_for_set_and_collector_entries(self):
        # A set+collector identifier is exact by construction; a fuzzy
        # name-based retry would make no sense and must not be attempted.
        entries = [engine.DeckEntry(name="Some Card", set_code="ABC", collector_number="1")]
        payload = {"data": []}
        engine.urllib.request.urlopen = _make_fake_urlopen([payload], fuzzy_results={"some card": {"name": "Some Card"}})
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            with self.assertRaises(RuntimeError):
                provider.get_many(entries)


if __name__ == "__main__":
    unittest.main()
