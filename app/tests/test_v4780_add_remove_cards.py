"""
v4.78.0 (UI-Feedback Punkt 7c). App.engine.add_card_to_txt_deck /
remove_card_from_txt_deck: the two primitives behind the Deck tab's
"add"/"remove card" controls. Both operate directly on a TXT decklist file
and are built on the exact same section-tracking scan load_txt_entries uses
(_txt_mainboard_line_indices), so they only ever touch mainboard lines --
never a sideboard duplicate of the same card name.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


def _deck(text: str):
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name) / "deck.txt"
    p.write_text(text, encoding="utf-8")
    return tmp, p


class AddCardTests(unittest.TestCase):
    def test_new_card_is_appended(self):
        tmp, p = _deck("1 Sol Ring\n1 Arcane Signet\n")
        with tmp:
            total = engine.add_card_to_txt_deck(p, "Command Tower", 1)
            self.assertEqual(total, 1)
            entries = engine.load_txt_entries(p)
            names = sorted(e.name for e in entries)
            self.assertEqual(names, ["Arcane Signet", "Command Tower", "Sol Ring"])

    def test_existing_card_count_is_bumped_not_duplicated(self):
        tmp, p = _deck("1 Sol Ring\n1 Arcane Signet\n")
        with tmp:
            total = engine.add_card_to_txt_deck(p, "Sol Ring", 2)
            self.assertEqual(total, 3)
            entries = engine.load_txt_entries(p)
            sol = [e for e in entries if e.name == "Sol Ring"]
            self.assertEqual(len(sol), 1)
            self.assertEqual(sol[0].count, 3)
            self.assertEqual(len(entries), 2)  # still just 2 distinct lines

    def test_match_is_case_and_whitespace_insensitive(self):
        tmp, p = _deck("1 Sol Ring\n")
        with tmp:
            total = engine.add_card_to_txt_deck(p, "sol ring", 1)
            self.assertEqual(total, 2)
            entries = engine.load_txt_entries(p)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].count, 2)

    def test_never_bumps_a_sideboard_duplicate(self):
        tmp, p = _deck("1 Sol Ring\n\nSideboard\n1 Pithing Needle\n")
        with tmp:
            # "Pithing Needle" only exists in the sideboard -> must be a
            # brand new mainboard line, not a bump of the sideboard one.
            total = engine.add_card_to_txt_deck(p, "Pithing Needle", 1)
            self.assertEqual(total, 1)
            entries = engine.load_txt_entries(p)
            pn = [e for e in entries if e.name == "Pithing Needle"]
            self.assertEqual(len(pn), 1)
            self.assertEqual(pn[0].count, 1)
            # the old sideboard line is untouched and still excluded
            raw = p.read_text(encoding="utf-8")
            self.assertIn("Sideboard", raw)

    def test_appending_after_an_empty_trailing_sideboard_header_still_lands_in_mainboard(self):
        # Edge case the blank-line-closes-sideboard heuristic alone can't
        # handle: a "Sideboard" header with nothing under it at all, so
        # sideboard_saw_card never becomes True and a blank line wouldn't
        # close it. add_card_to_txt_deck must still land the new card in
        # the mainboard (it writes an explicit "Mainboard" header instead).
        tmp, p = _deck("1 Sol Ring\n\nSideboard\n")
        with tmp:
            total = engine.add_card_to_txt_deck(p, "Arcane Signet", 1)
            self.assertEqual(total, 1)
            entries = engine.load_txt_entries(p)
            names = sorted(e.name for e in entries)
            self.assertEqual(names, ["Arcane Signet", "Sol Ring"])

    def test_appending_twice_after_sideboard_does_not_reopen_it(self):
        tmp, p = _deck("1 Sol Ring\n\nSideboard\n1 Pithing Needle\n")
        with tmp:
            engine.add_card_to_txt_deck(p, "Arcane Signet", 1)
            engine.add_card_to_txt_deck(p, "Command Tower", 1)
            entries = engine.load_txt_entries(p)
            names = sorted(e.name for e in entries)
            self.assertEqual(names, ["Arcane Signet", "Command Tower", "Sol Ring"])

    def test_rejects_non_positive_count(self):
        tmp, p = _deck("1 Sol Ring\n")
        with tmp:
            with self.assertRaises(ValueError):
                engine.add_card_to_txt_deck(p, "Arcane Signet", 0)


class RemoveCardTests(unittest.TestCase):
    def test_removes_whole_line_by_default(self):
        tmp, p = _deck("1 Sol Ring\n1 Arcane Signet\n")
        with tmp:
            ok = engine.remove_card_from_txt_deck(p, "Sol Ring")
            self.assertTrue(ok)
            entries = engine.load_txt_entries(p)
            self.assertEqual([e.name for e in entries], ["Arcane Signet"])

    def test_partial_count_decrements_instead_of_removing(self):
        tmp, p = _deck("3 Forest\n1 Sol Ring\n")
        with tmp:
            ok = engine.remove_card_from_txt_deck(p, "Forest", 1)
            self.assertTrue(ok)
            entries = engine.load_txt_entries(p)
            forest = [e for e in entries if e.name == "Forest"]
            self.assertEqual(forest[0].count, 2)

    def test_count_exceeding_current_removes_the_line(self):
        tmp, p = _deck("3 Forest\n1 Sol Ring\n")
        with tmp:
            ok = engine.remove_card_from_txt_deck(p, "Forest", 99)
            self.assertTrue(ok)
            entries = engine.load_txt_entries(p)
            self.assertEqual([e.name for e in entries], ["Sol Ring"])

    def test_card_not_in_mainboard_returns_false(self):
        tmp, p = _deck("1 Sol Ring\n\nSideboard\n1 Pithing Needle\n")
        with tmp:
            # sideboard-only card -> not something a simulation run counts,
            # so "remove" correctly reports nothing was found.
            ok = engine.remove_card_from_txt_deck(p, "Pithing Needle")
            self.assertFalse(ok)
            ok2 = engine.remove_card_from_txt_deck(p, "Nonexistent Card")
            self.assertFalse(ok2)


class VersionSyncTests(unittest.TestCase):
    def test_engine_version_is_4_78_0(self):
        self.assertEqual(engine.ENGINE_VERSION, "4.87.0")


if __name__ == "__main__":
    unittest.main()
