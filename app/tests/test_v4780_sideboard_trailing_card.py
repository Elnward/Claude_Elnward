"""
v4.78.0 (UI-Feedback Paket D). Real bug reported by the user: a decklist
export (a "Ms. Bumbleflower" deck) puts a "SIDEBOARD:" marker followed by two
real sideboard cards, then a blank line, then ONE MORE card line with no
header of its own before EOF. In this particular export that trailing card
happened to be the deck's own commander.

Before this fix, App.engine.load_txt_entries's `in_sideboard` flag was
sticky-to-EOF: once a "sideboard"/"companion" header was seen, every
subsequent line was dropped, including that trailing card - the user's
100-card deck silently imported as 99 cards.

The fix mirrors a heuristic detect_commander_hints already used for its own
"Commander" section: a blank line closes an active sideboard/companion
section, but only once at least one card line was actually consumed inside
it (so an incidental blank line right after "SIDEBOARD:" itself, before any
sideboard card, doesn't immediately re-open mainboard parsing).
"""
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


class TrailingCardAfterSideboardTests(unittest.TestCase):
    def test_card_after_blank_line_following_sideboard_is_parsed(self):
        # The user's reported shape, trimmed to the essentials.
        text = (
            "1 Sol Ring\n1 Witch Enchanter\n1 Yavimaya Coast\n\n"
            "SIDEBOARD:\n1 Bumbleflower's Sharepot\n1 Ethereal Armor\n\n"
            "1 Ms. Bumbleflower\n"
        )
        entries = _load_txt(text)
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Ms. Bumbleflower", "Sol Ring", "Witch Enchanter", "Yavimaya Coast"])
        self.assertNotIn("Bumbleflower's Sharepot", names)
        self.assertNotIn("Ethereal Armor", names)

    def test_real_sideboard_cards_with_no_trailing_blank_still_excluded(self):
        # Unchanged pre-existing behavior: no blank line after the last
        # sideboard card (file just ends) -> still correctly excluded.
        entries = _load_txt("1 Sol Ring\n\nSideboard\n1 Pithing Needle\n1 Chaos Warp\n")
        names = [e.name for e in entries]
        self.assertEqual(names, ["Sol Ring"])

    def test_blank_line_immediately_after_sideboard_header_does_not_reopen(self):
        # A blank line right after "Sideboard" itself, before any sideboard
        # card has been consumed, must not immediately flip back to
        # mainboard parsing (sideboard_saw_card is still False at that point).
        entries = _load_txt("1 Sol Ring\n\nSideboard\n\n1 Pithing Needle\n")
        names = [e.name for e in entries]
        self.assertEqual(names, ["Sol Ring"])

    def test_slash_prefixed_sideboard_same_trailing_behavior(self):
        text = "1 Sol Ring\n\n// Sideboard\n1 Pithing Needle\n\n1 Arcane Signet\n"
        entries = _load_txt(text)
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Arcane Signet", "Sol Ring"])
        self.assertNotIn("Pithing Needle", names)

    def test_multiple_blank_separated_blocks_after_sideboard(self):
        # Two trailing blocks after the sideboard closes - both parsed as
        # ordinary mainboard cards once the section has closed once.
        text = "1 Sol Ring\n\nSideboard\n1 Pithing Needle\n\n1 Arcane Signet\n\n1 Command Tower\n"
        entries = _load_txt(text)
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Arcane Signet", "Command Tower", "Sol Ring"])
        self.assertNotIn("Pithing Needle", names)

    def test_companion_header_same_trailing_behavior(self):
        text = "1 Sol Ring\n\nCompanion\n1 Lurrus of the Dream-Den\n\n1 Arcane Signet\n"
        entries = _load_txt(text)
        names = sorted(e.name for e in entries)
        self.assertEqual(names, ["Arcane Signet", "Sol Ring"])
        self.assertNotIn("Lurrus of the Dream-Den", names)


class VersionSyncTests(unittest.TestCase):
    def test_engine_version_is_4_78_0(self):
        self.assertEqual(engine.ENGINE_VERSION, "4.87.0")


if __name__ == "__main__":
    unittest.main()
