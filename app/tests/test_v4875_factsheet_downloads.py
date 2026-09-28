"""
Unit tests for v4.87.5: Analysis downloads.

- App/factsheet_pdf.py: a dependency-free PDF writer that lays out the run the
  Analysis page shows (setup, results, charts, deck list) as an A4 fact sheet
  with an embedded DejaVu Sans Mono font.
- web_server.py: POST /api/factsheet streams that PDF; GET
  /api/deck/<deck>/runs/<run_dir>/zip hands out a run's result folder as a ZIP
  (only for real folders under Goldfish_Results - no path tricks).

Run from the project root:
    python -m unittest tests.test_v4875_factsheet_downloads -v
"""
from __future__ import annotations

import io
import re
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import factsheet_pdf as fs  # noqa: E402


def sample_payload(**over):
    run = {
        "run_label": "Live run, 27.09.2026, 15:27",
        "simulation": {"runs": 60, "turns": 10, "seed": 1, "opponent_profile": "random",
                       "engine_version": "4.87.0", "advanced_opponent_model": True, "commander_posture": "aggressive"},
        "outcomes": {"win_by_turn_limit_pct": 6.7, "loss_by_turn_limit_pct": 13.3, "win_condition_reach_pct": 1.7,
                     "median_win_turn_when_winning": 10, "avg_cards_drawn": 11, "avg_opponents_eliminated": 1.1},
        "opening": {"avg_mulligans": 0.33},
        "byturn": [{"t": t, "avg_life": 40 - t, "avg_mana_start_main": t * .9, "avg_lands": t} for t in range(1, 11)],
        "opp": {"aggro": {"win_pct": 6.7, "loss_pct": 0, "active_at_limit_pct": 93.3}},
        "scen": [{"name": "Sanguine Bond (online)", "reach": 12.5, "cards": 30, "median_turn": 8, "target_scope": "each",
                  "bn": [["Sanguine Bond in battlefield", 40]], "cum": [[0, 0], [10, 12.5]]}],
        "metrics": {"life": {"label": "Life total", "unit": "life", "dir": "up",
                             "by_turn": [{"t": t, "avg": 40 - t, "p25": 38 - t, "p75": 41 - t, "n": 60} for t in range(1, 11)],
                             "peak": {"games": 60, "hist": [[40.0, 50], [55.0, 10]], "median": 40}}},
        "hl": [{"name": "Sol Ring", "tier": "S", "value_per_seen": 7.2}],
        "model_gaps": [{"name": "Shadowborn Apostle", "reason": "no_modeled_effect", "detail": "review only"}],
        "archetype_reference": {"identity_label": "Abzan", "identity_only": {"comparison": [
            {"field": "n_lands", "observed": 36, "expected": 36, "diff": 0, "diff_pct": 0}]}},
    }
    payload = {
        "run": run,
        "deck": {"name": "Bilbo (V1)", "commanders": ["Bilbo, Birthday Celebrant"], "tags": ["lifegain"],
                 "playstyle": {"aggression": 80},
                 "cards": [{"q": 1, "n": "Bilbo, Birthday Celebrant", "c": "{W}{B}{G}", "t": "Legendary Creature", "mv": 3, "cmd": True},
                           {"q": 1, "n": "Sol Ring", "c": "{1}", "t": "Artifact", "mv": 1},
                           {"q": 8, "n": "Forest", "c": "", "t": "Basic Land — Forest", "mv": 0}]},
        "table": {"enabled": True, "target_mode": "threat", "kingmaking_life_threshold": 15, "kingmaking_revenge_weight": 2},
        "view": {"opponents": "random mix, 15 each", "focus": {"key": "life", "benchmarks": [{"label": "55+ life", "p": 16.7}],
                                                               "summary": "Typical best point per game: 40 life (median)."},
                 "tips": [{"kind": "con", "title": "Light on interaction", "body": "Removal sits 44.8 % below average — opposing threats (e.g. ≥3) may go unanswered."}]},
    }
    payload.update(over)
    return payload


def page_count(pdf: bytes) -> int:
    m = re.search(rb"/Type /Pages /Kids \[[^\]]*\] /Count (\d+)", pdf)
    return int(m.group(1)) if m else 0


def all_text(pdf: bytes) -> str:
    """Decompress every content stream and collect the (...) Tj strings."""
    out = []
    for m in re.finditer(rb"<< /Length (\d+) /Filter /FlateDecode >>\nstream\n", pdf):
        start = m.end()
        data = pdf[start:start + int(m.group(1))]
        try:
            txt = zlib.decompress(data)
        except zlib.error:
            continue
        if b" Tj ET" in txt:
            out.extend(s.decode("cp1252").replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
                       for s in re.findall(rb"\(((?:\\.|[^\\)])*)\) Tj", txt))
    return "\n".join(out)


class TestPdfPrimitives(unittest.TestCase):
    def test_text_is_escaped_and_mapped_to_winansi(self):
        self.assertEqual(fs.pdf_text("a(b)c\\"), b"a\\(b\\)c\\\\")
        self.assertEqual(fs.pdf_text("life ≥ 40 — ok"), "life >= 40 — ok".encode("cp1252"))

    def test_wrap_respects_width(self):
        lines = fs.wrap("one two three four five six seven eight nine ten", 60, 8)
        per = int(60 // (fs.CHAR_W * 8))
        self.assertTrue(all(len(l) <= per for l in lines))
        self.assertEqual(" ".join(lines), "one two three four five six seven eight nine ten")

    def test_fonts_ship_with_the_app(self):
        for f in fs.FONT_FILES.values():
            self.assertTrue((fs.FONT_DIR / f).is_file(), f)


class TestFactsheet(unittest.TestCase):
    def test_builds_a_valid_multi_page_pdf(self):
        pdf = fs.build_factsheet_pdf(sample_payload())
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertGreaterEqual(page_count(pdf), 2)  # results + deck list page
        self.assertIn(b"/FontFile2", pdf)
        # xref offsets point at the objects they claim to
        xref = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
        self.assertTrue(pdf[xref:].startswith(b"xref"))
        first = re.search(rb"0000000000 65535 f \n(\d{10}) 00000 n", pdf[xref:])
        self.assertTrue(pdf[int(first.group(1)):].startswith(b"1 0 obj"))

    def test_content_covers_setup_results_and_deck(self):
        text = all_text(fs.build_factsheet_pdf(sample_payload()))
        for needle in ("Bilbo (V1)", "SETUP", "aggressive", "threat (attack the leader)", "WIN CONDITIONS",
                       "Sanguine Bond (online)", "FOCUS: LIFE TOTAL", "55+ life", "Light on interaction", ">=3",
                       "Shadowborn Apostle", "DECK LIST", "COMMANDER (1)", "Forest"):
            self.assertIn(needle, text)

    def test_minimal_run_without_optional_sections(self):
        p = sample_payload()
        for k in ("scen", "metrics", "hl", "model_gaps", "archetype_reference", "opp", "byturn"):
            p["run"].pop(k)
        p["deck"]["cards"] = []
        p["view"] = {}
        pdf = fs.build_factsheet_pdf(p)
        self.assertEqual(page_count(pdf), 1)
        self.assertIn("No win-condition setups", all_text(pdf))


class TestServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import web_server
        cls.ws = web_server
        cls.client = web_server.app.test_client()

    def test_factsheet_endpoint_returns_pdf(self):
        r = self.client.post("/api/factsheet", json=sample_payload())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "application/pdf")
        self.assertIn('filename="Bilbo V1 fact sheet.pdf"', r.headers["Content-Disposition"])
        self.assertTrue(r.data.startswith(b"%PDF"))

    def test_factsheet_endpoint_needs_a_run(self):
        r = self.client.post("/api/factsheet", json={"deck": {"name": "x"}})
        self.assertEqual(r.status_code, 400)

    def test_zip_endpoint_serves_a_run_folder_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = self.ws.RESULTS_ROOT
            self.ws.RESULTS_ROOT = Path(tmp)
            try:
                run = Path(tmp) / "Deck A" / "Deck A_v4_7_0_20260101-000000"
                run.mkdir(parents=True)
                (run / "summary.json").write_text("{}", encoding="utf-8")
                r = self.client.get("/api/deck/Deck%20A/runs/Deck%20A_v4_7_0_20260101-000000/zip")
                self.assertEqual(r.status_code, 200)
                names = zipfile.ZipFile(io.BytesIO(r.data)).namelist()
                self.assertIn("Deck A_v4_7_0_20260101-000000/summary.json", names)
                self.assertEqual(self.client.get("/api/deck/Deck%20A/runs/..%2F..%2Fsecret/zip").status_code, 404)
                self.assertEqual(self.client.get("/api/deck/Deck%20A/runs/.hidden/zip").status_code, 404)
                self.assertEqual(self.client.get("/api/deck/Deck%20A/runs/missing/zip").status_code, 404)
            finally:
                self.ws.RESULTS_ROOT = old


if __name__ == "__main__":
    unittest.main()
