"""
Unit/integration tests for v4.13.0 (Route D): "Engine Value" - blending a
card's predefined, card-shape-only value with a value LEARNED from real,
persisted simulation history across multiple runs.

Covers:
  1. ValueModel.engine_value - the Bayesian-shrinkage blend. Cold start
     (no learned history) must return the predefined value UNCHANGED
     (byte-identical), the same safety pattern as v4.11.0's
     color_identity=None fallback. Blend weight grows toward
     engine_value_max_learned_weight as learned_seen grows, never past it.
  2. predefined_static_value - a pure card-shape estimate with no
     GameState, reusing the same tested building blocks cast_score_v4
     uses (metric_value/keyword_value/creature_body_value/instant premium/
     flat tutor-recursion-protection rates). Real Katara card confirms it
     actually runs end-to-end on a real Scryfall-cache card.
  3. update_engine_value_store - the cross-run seen-weighted merge
     arithmetic (pure function, no disk I/O), including that a Seen==0 row
     contributes nothing and does not dilute the running average.
  4. load_engine_value_store/save_engine_value_store - round-trips via a
     temp path; a missing file returns a valid, empty store rather than
     raising (the normal "no run has completed yet" state).
  5. End-to-end: a store built from synthetic impact_rows blended against
     a predefined value, confirming the blend actually moves toward the
     learned number as sample size grows, while never overshooting it.

Run from the project root:
    python -m unittest tests.test_engine_value -v
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

_SCRYFALL_CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"


def _load_real_card(name: str, enrich: bool = False) -> engine.Card:
    with _SCRYFALL_CACHE_PATH.open("r", encoding="utf-8") as f:
        cache = json.load(f)
    for obj in cache.values():
        if isinstance(obj, dict) and obj.get("name") == name:
            entry = engine.DeckEntry(name=name)
            card = engine.card_from_scryfall(entry, obj, commander_name=None)
            return engine.enrich_semantics(card) if enrich else card
    raise AssertionError(f"{name!r} not found in {_SCRYFALL_CACHE_PATH}")


class EngineValueBlendTests(unittest.TestCase):
    def setUp(self):
        self.vm = engine.ValueModel.load()

    def test_no_learned_history_returns_predefined_value_unchanged(self):
        # learned_seen == 0: the store simply has no entry for this card
        # yet (fresh checkout / never-before-seen card). Must be
        # byte-identical to predefined_value, not just "close".
        self.assertEqual(self.vm.engine_value(4.2, None, 0.0), 4.2)
        self.assertEqual(self.vm.engine_value(4.2, 0.9, 0.0), 4.2)

    def test_learned_value_none_with_positive_seen_still_falls_back(self):
        # Defensive: a malformed/partial store entry (seen > 0 but no
        # recorded average) must not crash or produce a nonsense blend.
        self.assertEqual(self.vm.engine_value(4.2, None, 500.0), 4.2)

    def test_blend_weight_grows_toward_learned_value_with_more_samples(self):
        predefined = 2.0
        learned = 8.0
        small_sample = self.vm.engine_value(predefined, learned, 5.0)
        large_sample = self.vm.engine_value(predefined, learned, 5000.0)
        self.assertGreater(small_sample, predefined)
        self.assertLess(small_sample, large_sample)
        self.assertGreater(large_sample, small_sample)
        # Even at a huge sample size, the result never reaches the raw
        # learned value - engine_value_max_learned_weight caps it below 1.0.
        self.assertLess(large_sample, learned)

    def test_blend_never_exceeds_the_max_learned_weight_cap(self):
        predefined = 0.0
        learned = 10.0
        cap = float(self.vm.values["engine_value_max_learned_weight"])
        result = self.vm.engine_value(predefined, learned, 10_000_000.0)
        self.assertAlmostEqual(result, cap * learned, places=3)

    def test_exact_cold_start_pseudo_seen_formula(self):
        # At learned_seen == engine_value_cold_start_pseudo_seen, the
        # formula's blend_weight is exactly 0.5 (by construction:
        # seen / (seen + pseudo) with seen == pseudo).
        pseudo = float(self.vm.values["engine_value_cold_start_pseudo_seen"])
        predefined, learned = 2.0, 6.0
        result = self.vm.engine_value(predefined, learned, pseudo)
        self.assertAlmostEqual(result, (predefined + learned) / 2.0, places=6)


class PredefinedStaticValueTests(unittest.TestCase):
    def setUp(self):
        self.vm = engine.ValueModel.load()
        self.strategy = engine.ScenarioStrategy(opponent_profile="goldfish", value_model=self.vm)

    def test_blank_card_with_no_roles_keywords_or_body_is_zero(self):
        blank = engine.Card(name="Blank", mana_cost="{3}", mana_value=3, type_line="Sorcery")
        self.assertEqual(engine.predefined_static_value(blank, self.strategy), 0.0)

    def test_draw_role_contributes_the_calibrated_draw_metric_value(self):
        drawer = engine.Card(
            name="Test Draw Spell", mana_cost="{2}{U}", mana_value=3, type_line="Sorcery",
            oracle_text="Draw two cards.", color_identity={"U"}, roles={"draw"},
        )
        expected = self.vm.metric_value("draw", 2, self.strategy.archetypes, {"U"})
        self.assertAlmostEqual(engine.predefined_static_value(drawer, self.strategy), expected, places=6)

    def test_creature_with_keywords_and_body_sums_both_factors(self):
        creature = engine.Card(
            name="Test Flyer", mana_cost="{2}{W}", mana_value=3, type_line="Creature",
            power=2.0, toughness=2.0, keywords={"flying"},
        )
        expected = self.vm.keyword_value({"flying"}) + self.vm.creature_body_value(2.0, 2.0)
        self.assertAlmostEqual(engine.predefined_static_value(creature, self.strategy), expected, places=6)

    def test_instant_gets_the_instant_speed_premium_added(self):
        sorcery_shape = engine.Card(name="Test Sorcery", mana_cost="{1}{B}", mana_value=2, type_line="Sorcery", roles={"tutor"})
        instant_shape = engine.Card(name="Test Instant", mana_cost="{1}{B}", mana_value=2, type_line="Instant", roles={"tutor"})
        diff = engine.predefined_static_value(instant_shape, self.strategy) - engine.predefined_static_value(sorcery_shape, self.strategy)
        self.assertAlmostEqual(diff, float(self.vm.values["instant_speed_premium"]), places=6)

    def test_real_katara_scores_the_same_as_manually_summing_her_components(self):
        katara = _load_real_card("Katara, Water Tribe's Hope", enrich=True)
        expected = self.vm.keyword_value(katara.keywords) + self.vm.creature_body_value(katara.power, katara.toughness)
        self.assertAlmostEqual(engine.predefined_static_value(katara, self.strategy), expected, places=6)
        self.assertGreater(engine.predefined_static_value(katara, self.strategy), 0.0)


class UpdateEngineValueStoreTests(unittest.TestCase):
    def test_first_merge_into_an_empty_store_just_records_the_run(self):
        store = {"cards": {}}
        rows = [{"Name": "Sol Ring", "Seen": 100.0, "Estimated value / seen": 0.6}]
        updated = engine.update_engine_value_store(store, rows)
        entry = updated["cards"]["Sol Ring"]
        self.assertEqual(entry["seen"], 100.0)
        self.assertAlmostEqual(entry["learned_value_per_seen"], 0.6, places=6)
        self.assertEqual(entry["runs_merged"], 1)
        self.assertIn("last_updated", entry)

    def test_second_merge_is_a_seen_weighted_running_average(self):
        store = {"cards": {"Sol Ring": {"seen": 100.0, "learned_value_per_seen": 0.6, "runs_merged": 1}}}
        rows = [{"Name": "Sol Ring", "Seen": 300.0, "Estimated value / seen": 1.0}]
        updated = engine.update_engine_value_store(store, rows)
        entry = updated["cards"]["Sol Ring"]
        expected_avg = (0.6 * 100.0 + 1.0 * 300.0) / 400.0
        self.assertAlmostEqual(entry["seen"], 400.0, places=6)
        self.assertAlmostEqual(entry["learned_value_per_seen"], expected_avg, places=6)
        self.assertEqual(entry["runs_merged"], 2)

    def test_row_with_zero_seen_is_skipped_not_averaged_in(self):
        store = {"cards": {"Sol Ring": {"seen": 100.0, "learned_value_per_seen": 0.6, "runs_merged": 1}}}
        rows = [{"Name": "Sol Ring", "Seen": 0.0, "Estimated value / seen": 0.0}]
        updated = engine.update_engine_value_store(store, rows)
        entry = updated["cards"]["Sol Ring"]
        self.assertEqual(entry["seen"], 100.0)
        self.assertAlmostEqual(entry["learned_value_per_seen"], 0.6, places=6)
        self.assertEqual(entry["runs_merged"], 1)

    def test_original_store_dict_is_not_mutated(self):
        store = {"cards": {"Sol Ring": {"seen": 100.0, "learned_value_per_seen": 0.6, "runs_merged": 1}}}
        rows = [{"Name": "Sol Ring", "Seen": 50.0, "Estimated value / seen": 2.0}]
        engine.update_engine_value_store(store, rows)
        self.assertEqual(store["cards"]["Sol Ring"]["seen"], 100.0)


class LoadSaveEngineValueStoreTests(unittest.TestCase):
    def test_missing_file_returns_a_valid_empty_store(self):
        with tempfile.TemporaryDirectory() as d:
            missing = Path(d) / "does_not_exist.json"
            store = engine.load_engine_value_store(missing)
            self.assertEqual(store, {"cards": {}})

    def test_save_then_load_roundtrips_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "engine_value_store.json"
            store = {"cards": {"Sol Ring": {"seen": 42.0, "learned_value_per_seen": 0.75, "runs_merged": 1, "last_updated": "2026-01-01T00:00:00"}}}
            engine.save_engine_value_store(store, path)
            self.assertTrue(path.exists())
            loaded = engine.load_engine_value_store(path)
            self.assertEqual(loaded, store)

    def test_corrupted_file_falls_back_to_empty_store_rather_than_raising(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "engine_value_store.json"
            path.write_text("{not valid json", encoding="utf-8")
            store = engine.load_engine_value_store(path)
            self.assertEqual(store, {"cards": {}})


class EndToEndBlendAcrossSimulatedRunsTests(unittest.TestCase):
    """Builds a store the way real runs would (via update_engine_value_store
    across several synthetic 'runs'), then blends it against a predefined
    value the way the run_pipeline_v440 hook does, confirming the whole
    chain behaves sensibly end to end."""

    def test_engine_value_converges_toward_real_observed_performance(self):
        vm = engine.ValueModel.load()
        predefined = engine.predefined_static_value(
            engine.Card(name="Test Card", mana_cost="{2}", mana_value=2, type_line="Sorcery", roles={"tutor"}),
            engine.ScenarioStrategy(opponent_profile="goldfish", value_model=vm),
        )
        # This card under-performs its predefined estimate in every real run
        # (e.g. it frequently has no legal target and rots in hand).
        store = {"cards": {}}
        for _ in range(5):
            store = engine.update_engine_value_store(store, [{"Name": "Test Card", "Seen": 200.0, "Estimated value / seen": 0.1}])

        entry = store["cards"]["Test Card"]
        blended = vm.engine_value(predefined, entry["learned_value_per_seen"], entry["seen"])

        self.assertLess(blended, predefined, "1000 real games of underperformance should pull the blended value down")
        self.assertGreater(blended, entry["learned_value_per_seen"], "the cap keeps a residual anchor to the predefined estimate")


if __name__ == "__main__":
    unittest.main()
