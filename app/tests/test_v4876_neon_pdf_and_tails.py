"""
Unit tests for v4.87.6.

- The fact sheet carries the neon sign in the top right of page 1. The two
  PNGs in App/factsheet_assets are embedded without decoding (their IDAT
  data goes into the PDF with the PNG predictor), colour plus soft mask.
- Focus metrics now also carry p10/p90 per turn, so the chart can show the
  strongest games of a turn next to the middle-half band.

Run from the project root:
    python -m unittest tests.test_v4876_neon_pdf_and_tails -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402
from App import factsheet_pdf as fs  # noqa: E402


def minimal_payload():
    return {
        "run": {"run_label": "run", "simulation": {"runs": 10, "turns": 3},
                "outcomes": {"win_by_turn_limit_pct": 10, "loss_by_turn_limit_pct": 0}},
        "deck": {"name": "Test deck", "commanders": ["Someone"]},
        "view": {},
    }


class TestNeonInFactsheet(unittest.TestCase):
    def test_assets_are_simple_pngs_of_equal_size(self):
        w, h, ct, data = fs.read_png(fs.ASSET_DIR / fs.NEON_RGB)
        aw, ah, act, adata = fs.read_png(fs.ASSET_DIR / fs.NEON_ALPHA)
        self.assertEqual((w, h), (aw, ah))
        self.assertEqual((ct, act), (2, 0))
        self.assertTrue(data and adata)

    def test_sign_is_embedded_with_soft_mask(self):
        pdf = fs.build_factsheet_pdf(minimal_payload())
        self.assertIn(b"/Subtype /Image", pdf)
        self.assertIn(b"/SMask", pdf)
        self.assertIn(b"/XObject << /Neon", pdf)

    def test_sheet_still_builds_without_the_assets(self):
        old = fs.ASSET_DIR
        fs.ASSET_DIR = Path(old) / "does-not-exist"
        try:
            pdf = fs.build_factsheet_pdf(minimal_payload())
        finally:
            fs.ASSET_DIR = old
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertNotIn(b"/Neon", pdf)

    def test_long_deck_names_shrink_instead_of_running_into_the_sign(self):
        p = minimal_payload()
        p["deck"]["name"] = "A really quite long deck name that goes on and on"
        pdf = fs.build_factsheet_pdf(p)
        self.assertTrue(pdf.startswith(b"%PDF"))


class TestFocusMetricTails(unittest.TestCase):
    def test_by_turn_has_p10_and_p90(self):
        stats = engine.StreamingStatsV440(runs=10, turns=1)
        saved = engine._V4874_stats_add_old
        engine._V4874_stats_add_old = lambda self, rr, tr, sr: None
        try:
            for life in range(30, 50, 2):  # 10 games, one turn each
                row = {"turn": 1}
                for k in engine._FOCUS_KEYS:
                    row["fm_" + k] = 0.0
                row["fm_life"] = float(life)
                engine._streaming_stats_add_v4874(stats, {}, [row], [])
        finally:
            engine._V4874_stats_add_old = saved
        bt = engine.build_focus_metrics(stats)["life"]["by_turn"][0]
        self.assertLessEqual(bt["p10"], bt["p25"])
        self.assertLessEqual(bt["p75"], bt["p90"])
        self.assertEqual(bt["p90"], 46.0)
        self.assertEqual(bt["p10"], 30.0)


if __name__ == "__main__":
    unittest.main()
