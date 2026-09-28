"""
v4.76.0 WP4: model-gap diagnostic (App/engine.py::compute_model_gaps,
model_gaps.json, summary["model_gaps"], webui_transform pass-through).

Run from the project root:
    python -m unittest tests.test_v4760_model_gaps -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from App import engine as E  # noqa: E402
import webui_transform  # noqa: E402


def card(name, roles=(), commander=False, type_line="Creature — Elf"):
    return E.Card(name=name, type_line=type_line, roles=set(roles), commander=commander)


def imp(name, seen, cast, vpc):
    return {"Name": name, "Seen": seen, "Cast": cast, "Estimated value / cast": vpc}


def cov(name, mix, dedicated="no"):
    return {"Name": name, "Semantic execution mix": mix, "Dedicated resolver": dedicated}


class _S:
    scenarios = [{"name": "Hoof", "enabled": True, "requirements": [{"card": "Plain Elf"}],
                  "packages": [{"members": [{"card": "Finale"}]}]}]


class ModelGapTest(unittest.TestCase):
    def setUp(self):
        self.deck = [
            card("Finale", type_line="Sorcery"),                    # win-condition card
            card("Hoof", roles=("finisher",)),
            card("Removal", roles=("interaction",), type_line="Instant"),
            card("Plain Elf"),                                        # win-condition card
            card("Vanilla", type_line="Creature — Bear"),        # not key
            card("Engine", roles=("engine",)),
            card("Cmdr", commander=True),
        ]
        self.impact = [
            imp("Finale", 44, 0, 0), imp("Hoof", 35, 10, 0.2), imp("Removal", 40, 0, 0),
            imp("Plain Elf", 40, 38, 3.0), imp("Vanilla", 30, 0, 0), imp("Engine", 30, 28, 0.1),
            imp("Cmdr", 200, 150, 0.05),
        ]
        self.cov = [cov("Hoof", "review:1 | simplified:1"), cov("Engine", "review:2", dedicated="yes"),
                    cov("Cmdr", "exact:1 | review:1"), cov("Plain Elf", "review:1")]

    def gaps(self):
        return {g["name"]: g for g in E.compute_model_gaps(self.deck, self.impact, self.cov, 200, _S())}

    def test_never_cast_key_card(self):
        g = self.gaps()
        self.assertEqual(g["Finale"]["reason"], "never_cast")
        self.assertTrue(g["Finale"]["in_win_condition"])

    def test_no_modeled_effect(self):
        self.assertEqual(self.gaps()["Hoof"]["reason"], "no_modeled_effect")

    def test_exclusions(self):
        g = self.gaps()
        self.assertNotIn("Removal", g)      # reactive, held on purpose
        self.assertNotIn("Vanilla", g)      # not a key card
        self.assertNotIn("Engine", g)       # a (registry) resolver executes it
        self.assertNotIn("Plain Elf", g)    # has real modeled value

    def test_commander_listed_first(self):
        out = E.compute_model_gaps(self.deck, self.impact, self.cov, 200, _S())
        self.assertEqual(out[0]["name"], "Cmdr")

    def test_transform_passes_gaps_and_models(self):
        summary = {"simulation": {"runs": 200, "turns": 10, "seed": 1, "opponent_profile": "random",
                                  "advanced_opponent_model": True, "defense_model": "board-aware v1"},
                   "by_turn": {}, "outcomes": {}, "model_gaps": [{"name": "X"}], "model_gaps_total": 3}
        run = webui_transform.to_frontend_run(summary, None, "t")
        self.assertEqual(run["model_gaps"], [{"name": "X"}])
        self.assertEqual(run["model_gaps_total"], 3)
        self.assertTrue(run["simulation"]["advanced_opponent_model"])
        self.assertEqual(run["simulation"]["defense_model"], "board-aware v1")


if __name__ == "__main__":
    unittest.main()
