"""
Unit tests for v4.15.7 (task #18, "Voltron-GUI-Feld"): exposing the
pre-existing engine field Strategy.voltron_target_index (see
tests/test_wp10_voltron_and_alpha_strike.py for its actual in-combat
behavior) through the GUI and the project (.goldfish.json) file, without
touching that behavior itself.

Covers:
  1. engine.apply_voltron_target_override - the small helper factored out of
     run_pipeline_v440 so the "GUI/pipeline kwarg overrides the strategy" bit
     is testable without driving the full deck-build/simulation pipeline.
  2. engine.project_payload_v43 / load_project_v43 round-trip
     "voltron_target_index" through a real project JSON file on disk,
     including the pre-v4.15.7 backward-compatibility case (key absent
     entirely -> None/"off", not a KeyError or a crash).

Run from the project root:
    python -m unittest tests.test_v4157_voltron_gui_wiring -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402


class ApplyVoltronTargetOverrideTests(unittest.TestCase):
    def test_none_leaves_an_unset_strategy_field_unset(self):
        strategy = engine.ScenarioStrategy()
        self.assertIsNone(strategy.voltron_target_index)
        engine.apply_voltron_target_override(strategy, None)
        self.assertIsNone(strategy.voltron_target_index)

    def test_none_does_not_clear_a_value_already_set_by_the_strategy_file(self):
        # Mirrors run_pipeline_v440's real flow: base_strategy is built first
        # (e.g. from a strategy JSON that already set voltron_target_index),
        # then the pipeline/GUI override is applied on top. A GUI choice of
        # "Aus" must not silently blow away a strategy-file setting.
        strategy = engine.ScenarioStrategy(voltron_target_index=1)
        engine.apply_voltron_target_override(strategy, None)
        self.assertEqual(strategy.voltron_target_index, 1)

    def test_an_explicit_index_overrides_whatever_was_set_before(self):
        strategy = engine.ScenarioStrategy(voltron_target_index=1)
        engine.apply_voltron_target_override(strategy, 0)
        self.assertEqual(strategy.voltron_target_index, 0)

    def test_an_explicit_index_sets_a_previously_unset_field(self):
        strategy = engine.ScenarioStrategy()
        engine.apply_voltron_target_override(strategy, 2)
        self.assertEqual(strategy.voltron_target_index, 2)


class ProjectPayloadVoltronRoundtripTests(unittest.TestCase):
    def _minimal_deck_file(self, tmp_dir: Path) -> Path:
        deck_file = tmp_dir / "deck.txt"
        deck_file.write_text("1 Sol Ring\n", encoding="utf-8")
        return deck_file

    def test_payload_carries_the_chosen_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck_file = self._minimal_deck_file(Path(tmp))
            payload = engine.project_payload_v43(
                deck_file,
                commanders=["Test Commander"],
                runs=200, turns=5, seed=1,
                strategy_tags=[], opponent_profile="goldfish",
                scenarios=[], voltron_target_index=1,
            )
            self.assertEqual(payload["simulation"]["voltron_target_index"], 1)

    def test_payload_defaults_to_none_when_not_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck_file = self._minimal_deck_file(Path(tmp))
            payload = engine.project_payload_v43(
                deck_file,
                commanders=["Test Commander"],
                runs=200, turns=5, seed=1,
                strategy_tags=[], opponent_profile="goldfish",
                scenarios=[],
            )
            self.assertIsNone(payload["simulation"]["voltron_target_index"])

    def test_save_and_load_roundtrips_a_chosen_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck_file = self._minimal_deck_file(tmp_path)
            project_path = tmp_path / "project.goldfish.json"
            engine.save_project_v43(
                project_path,
                deck_file=deck_file,
                commanders=["Test Commander"],
                runs=200, turns=5, seed=1,
                strategy_tags=[], opponent_profile="goldfish",
                scenarios=[], voltron_target_index=0,
            )
            loaded = engine.load_project_v43(project_path)
            self.assertEqual(loaded["voltron_target_index"], 0)

    def test_loading_a_pre_v4157_project_file_without_the_key_defaults_to_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck_file = self._minimal_deck_file(tmp_path)
            project_path = tmp_path / "project.goldfish.json"
            # Save through the real (current) helper, then strip the key to
            # simulate a project file saved by an older engine version -
            # exactly the file shape a real user's saved project would have.
            engine.save_project_v43(
                project_path,
                deck_file=deck_file,
                commanders=["Test Commander"],
                runs=200, turns=5, seed=1,
                strategy_tags=[], opponent_profile="goldfish",
                scenarios=[], voltron_target_index=0,
            )
            import json
            data = json.loads(project_path.read_text(encoding="utf-8"))
            del data["simulation"]["voltron_target_index"]
            project_path.write_text(json.dumps(data), encoding="utf-8")

            loaded = engine.load_project_v43(project_path)
            self.assertIsNone(loaded["voltron_target_index"])


if __name__ == "__main__":
    unittest.main()
