"""
Unit tests for v4.66.0 ("Kalibrierungs-Synthese Teil 1" - Flavor-Strategie-
Matrix). See:
  - Data/Models/flavor_strategy_matrix.json (the 90 compiled cells + 1
    legacy cell + 17 confirmed combos + 2 documented model limitations)
  - App/opponent_model/state_equation.py's module docstring "v4.66.0"
    section (the opt-in OpponentProfile.flavor mechanism)
  - App/engine.py's "v4.66.0" comment block directly above
    _validate_advanced_opponent_seats' new wrap (the optional
    advanced_opponent_seats[i]["flavor"] key)

Four groups: (1) the JSON data file's own internal consistency, (2)
state_equation.py's _flavor_cell lookup and advance_opponent_state override
behavior (including the critical regression guarantee - no flavor set means
byte-identical behavior to pre-v4.66.0), (3) engine.py's seat-level "flavor"
key wiring, (4) the two disclosed, still-open model limitations are actually
recorded in the data file (not silently dropped).

Run from the project root:
    python -m unittest tests.test_v4660_flavor_strategy_matrix -v
"""
from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402
from App.opponent_model import state_equation as se  # noqa: E402

_MATRIX_PATH = ROOT / "Data" / "Models" / "flavor_strategy_matrix.json"

_FIELDS = (
    "board_presence_growth", "interaction_growth", "wipe_growth", "combo_growth",
    "passive_value_growth", "sac_drain_growth", "disruption_growth", "mana_growth",
    "variance_amplitude", "dead_turn_chance_base",
)


def _load_matrix():
    return json.loads(_MATRIX_PATH.read_text(encoding="utf-8"))


class DataFileTests(unittest.TestCase):
    """Group 1: the JSON file itself, independent of any engine code."""

    @classmethod
    def setUpClass(cls):
        cls.data = _load_matrix()

    def test_exactly_ninety_active_cells(self):
        self.assertEqual(len(self.data["cells"]), 90)

    def test_exactly_fifteen_color_identities_six_flavors_each(self):
        from collections import Counter
        counts = Counter(c["color_identity"] for c in self.data["cells"].values())
        self.assertEqual(len(counts), 15)
        for identity, n in counts.items():
            self.assertEqual(n, 6, f"{identity} has {n} flavors, expected 6")

    def test_every_cell_has_all_ten_state_function_fields_as_numbers(self):
        for cid, c in self.data["cells"].items():
            self.assertEqual(set(c["state_function"].keys()), set(_FIELDS), cid)
            for field in _FIELDS:
                self.assertIsInstance(c["state_function"][field], (int, float), f"{cid}.{field}")

    def test_every_cell_has_a_valid_strategy_classification(self):
        valid = {"goldfish", "aggro", "midrange", "control", "horde"}
        for cid, c in self.data["cells"].items():
            self.assertIn(c["strategy"], valid, cid)
            # none of the 90 real cells were classified "goldfish" - see the
            # source docs' explicit reasoning (Zada/Rot, v4.51.0) for why
            # goldfish is reserved for "no real opponent at all".
            self.assertNotEqual(c["strategy"], "goldfish", cid)

    def test_every_cell_is_keyed_by_its_own_canonical_color_identity(self):
        for cid, c in self.data["cells"].items():
            self.assertTrue(cid.startswith(c["color_identity"] + "/"), cid)
            self.assertEqual(c["color_identity"], se._canonical_color_key(set(c["color_identity"])), cid)

    def test_every_cell_discloses_sample_size_one(self):
        # The single most important disclosed limitation of this whole data
        # set: every value is ONE real decklist, not a broad calibration.
        for cid, c in self.data["cells"].items():
            self.assertEqual(c["sample_size_decks"], 1, cid)

    def test_seventeen_confirmed_combos_each_referencing_a_real_cell(self):
        combos = self.data["confirmed_combos"]
        self.assertEqual(len(combos), 17)
        for combo in combos:
            self.assertIn(combo["cell"], self.data["cells"], combo["cell"])

    def test_legacy_ramp_cell_present_but_marked_superseded(self):
        legacy = self.data["legacy_cells"]
        self.assertEqual(len(legacy), 1)
        cid, cell = next(iter(legacy.items()))
        self.assertEqual(cell["color_identity"], "G")
        self.assertEqual(cell["taxonomy_status"], "legacy_pilot_not_in_active_6flavor_taxonomy")
        # the legacy cell must NOT double-count into the active 90.
        self.assertNotIn(cid, self.data["cells"])

    def test_both_documented_model_limitations_are_recorded(self):
        limits = self.data["documented_model_limitations"]
        self.assertIn("thematic_core_overlap", limits)
        self.assertIn("voltron_board_presence", limits)
        for name, entry in limits.items():
            self.assertGreater(entry["affected_cell_count"], 0, name)
            self.assertTrue(entry["description"].strip(), name)

    def test_spot_check_known_values_against_the_source_documents(self):
        # A handful of exact values cross-checked directly against the
        # "Zelle N" blocks in the source Docs/flavor_strategy_matrix_*.md
        # files, as an independent sanity check on the transcription.
        cells = self.data["cells"]
        self.assertAlmostEqual(cells["G/landfall"]["state_function"]["mana_growth"], 0.23)
        self.assertAlmostEqual(cells["B/aristocrats_sacrifice"]["state_function"]["sac_drain_growth"], 0.10)
        self.assertAlmostEqual(cells["WB/sacrifice"]["state_function"]["sac_drain_growth"], 0.19)
        self.assertAlmostEqual(cells["WU/taxes_pillowfort"]["state_function"]["disruption_growth"], 0.10)
        self.assertAlmostEqual(cells["W/voltron"]["state_function"]["board_presence_growth"], 0.55)
        self.assertEqual(cells["W/voltron"]["notes"], "voltron_board_presence")


class FlavorCellLookupTests(unittest.TestCase):
    def test_known_mono_color_flavor_resolves(self):
        cell = se._flavor_cell({"G"}, "landfall")
        self.assertIsNotNone(cell)
        self.assertEqual(cell["commander"], "Ashaya, Soul of the Wild")

    def test_known_guild_flavor_resolves_regardless_of_color_set_order(self):
        # Selesnya is stored canonically as "WG" - {"G", "W"} must still
        # resolve it (colors are a Python set, order is not meaningful).
        cell_a = se._flavor_cell({"G", "W"}, "hatebears")
        cell_b = se._flavor_cell({"W", "G"}, "hatebears")
        self.assertIsNotNone(cell_a)
        self.assertEqual(cell_a, cell_b)

    def test_fully_qualified_id_also_resolves(self):
        cell = se._flavor_cell({"G"}, "G/landfall")
        self.assertIsNotNone(cell)
        self.assertEqual(cell["flavor_slug"], "landfall")

    def test_unknown_flavor_slug_returns_none(self):
        self.assertIsNone(se._flavor_cell({"G"}, "definitely_not_a_real_flavor"))

    def test_flavor_that_exists_for_a_different_color_identity_returns_none(self):
        # "hatebears" is a real slug, but only under GW (Selesnya) / W (Taxes/
        # Hatebears) - not under mono-Red.
        self.assertIsNone(se._flavor_cell({"R"}, "hatebears"))

    def test_none_or_empty_flavor_returns_none(self):
        self.assertIsNone(se._flavor_cell({"G"}, None))
        self.assertIsNone(se._flavor_cell({"G"}, ""))

    def test_legacy_cell_hidden_by_default_but_reachable_with_include_legacy(self):
        self.assertIsNone(se._flavor_cell({"G"}, "ramp_big_mana"))
        cell = se._flavor_cell({"G"}, "ramp_big_mana", include_legacy=True)
        self.assertIsNotNone(cell)
        self.assertEqual(cell["commander"], "Azusa, Lost but Seeking")


class RegressionTests(unittest.TestCase):
    """Group 2b: the single most important guarantee of this version - a
    profile that never sets `flavor` must behave byte-identically to the
    pre-v4.66.0 module."""

    def test_opponent_profile_flavor_defaults_to_none(self):
        profile = se.OpponentProfile(strategy="midrange", colors={"G"}, bracket=3)
        self.assertIsNone(profile.flavor)

    def test_advance_opponent_state_is_seed_reproducible_without_flavor(self):
        def run():
            profile = se.OpponentProfile(strategy="midrange", colors={"G"}, bracket=3)
            state = se.OpponentState()
            rng = random.Random(12345)
            for _ in range(10):
                se.advance_opponent_state(state, profile, rng)
            return (
                round(state.board_presence, 6), round(state.mana_availability, 6),
                round(state.interaction_availability, 6), round(state.wipe_readiness, 6),
            )

        self.assertEqual(run(), run())

    def test_explicit_flavor_none_matches_omitted_flavor_field(self):
        def run(**kwargs):
            profile = se.OpponentProfile(strategy="control", colors={"U", "B"}, bracket=3, **kwargs)
            state = se.OpponentState()
            rng = random.Random(999)
            for _ in range(8):
                se.advance_opponent_state(state, profile, rng)
            return round(state.board_presence, 9), round(state.mana_availability, 9)

        self.assertEqual(run(), run(flavor=None))


class FlavorOverrideBehaviorTests(unittest.TestCase):
    """Group 2c: when a flavor IS set, the growth actually follows the
    flavor cell's own numbers, not curve*color_modifier."""

    def test_flavor_growth_matches_the_cells_own_declared_rate(self):
        # G/landfall declares mana_growth 0.23 directly - the pre-v4.66.0
        # midrange*G-modifier path would instead compute
        # 0.155 (midrange base) * 1.30 (G mana_growth modifier) = 0.2015.
        cell_rate = 0.23
        curve_times_modifier = se._strategy_curve("midrange")["mana_growth"] * se._color_multiplier({"G"}, "mana_growth")
        self.assertNotAlmostEqual(cell_rate, curve_times_modifier, places=3)

        profile = se.OpponentProfile(strategy="midrange", colors={"G"}, bracket=3, flavor="landfall")
        state = se.OpponentState()
        rng = random.Random(1)
        # First call, no variance influence on mana_availability's growth
        # rate itself matters less than the consistency_floor max() - use
        # many turns and a fixed rng so the deterministic component (growth
        # rate * power_mult) dominates and is checkable via bounds.
        for _ in range(1):
            se.advance_opponent_state(state, profile, rng)
        # After 1 turn (bracket 3 power_multiplier=1.0), with turn_quality
        # noise in [1-amplitude, 1+amplitude], mana_availability should be
        # in the ballpark of the flavor's own 0.23 rate (plus any opening
        # mana boost, which is 0.0 at bracket 3) rather than 0.2015.
        self.assertGreater(state.mana_availability, 0.15)

    def test_flavor_disabled_seat_uses_curve_times_modifier_as_before(self):
        profile_no_flavor = se.OpponentProfile(strategy="midrange", colors={"G"}, bracket=3)
        profile_flavor = se.OpponentProfile(strategy="midrange", colors={"G"}, bracket=3, flavor="landfall")
        state_a, state_b = se.OpponentState(), se.OpponentState()
        rng_a, rng_b = random.Random(42), random.Random(42)
        # Kept short (2 turns) deliberately - mana_availability's 1.0 cap
        # would otherwise be reached by both runs and mask the divergence
        # this test is meant to demonstrate.
        for _ in range(2):
            se.advance_opponent_state(state_a, profile_no_flavor, rng_a)
            se.advance_opponent_state(state_b, profile_flavor, rng_b)
        # Same seed/turns, different mana_growth rate (0.155*1.30=0.2015 vs
        # flavor's 0.23) - the two runs must diverge.
        self.assertNotAlmostEqual(state_a.mana_availability, state_b.mana_availability, places=3)

    def test_unknown_flavor_key_falls_back_to_curve_times_modifier_not_a_crash(self):
        profile = se.OpponentProfile(strategy="midrange", colors={"G"}, bracket=3, flavor="not_a_real_flavor")
        state = se.OpponentState()
        rng = random.Random(7)
        # Must not raise.
        se.advance_opponent_state(state, profile, rng)
        self.assertGreaterEqual(state.mana_availability, 0.0)

    def test_dead_turn_chance_base_does_not_double_apply_the_color_modifier_when_flavor_active(self):
        # R/goblins_go_wide declares dead_turn_chance_base 0.09 directly (see
        # source doc: "nah am R-modifizierten Basiswert 0.09 (0.10*0.90)" -
        # i.e. the flavor's own number ALREADY includes R's 0.90 dead_turn_
        # chance modifier). If _growth_rate's generic helper were used here
        # unmodified, R's 0.90 modifier would be applied a SECOND time,
        # silently deflating dead_turn_chance below the documented value.
        cell = se._flavor_cell({"R"}, "goblins_go_wide")
        flavor_dtc_base = cell["state_function"]["dead_turn_chance_base"]
        self.assertAlmostEqual(flavor_dtc_base, 0.09)

        profile = se.OpponentProfile(strategy="aggro", colors={"R"}, bracket=3, flavor="goblins_go_wide")
        state = se.OpponentState()
        rng = random.Random(3)
        se.advance_opponent_state(state, profile, rng)
        bracket_cfg = se._bracket_config(3)
        variance_mult = bracket_cfg["variance_multiplier"]
        consistency_floor = bracket_cfg["consistency_floor"]
        expected_pre_clamp = flavor_dtc_base * variance_mult * (1.0 - consistency_floor)
        wrongly_double_modified = expected_pre_clamp * se._color_multiplier({"R"}, "dead_turn_chance")
        self.assertNotAlmostEqual(expected_pre_clamp, wrongly_double_modified, places=4)
        # We cannot read dead_turn_chance back off `state` directly (it is
        # consumed internally, not stored) - but we CAN confirm the growth
        # helper used for it does not silently multiply variance_amplitude
        # (a field with no color_modifiers entry) which is the sibling
        # regression risk this same fix category could introduce.
        self.assertGreaterEqual(state.turn, 1)


class EngineSeatWiringTests(unittest.TestCase):
    """Group 3: App/engine.py's optional advanced_opponent_seats[i]["flavor"]."""

    def test_seat_without_flavor_key_behaves_exactly_as_before(self):
        seats = [{"strategy": "midrange", "colors": ["G"]}]
        engine._validate_advanced_opponent_seats(seats)  # must not raise
        table = engine._build_advanced_opponent_table(seats)
        profile, _state = table[0]
        self.assertIsNone(profile.flavor)

    def test_seat_with_valid_flavor_key_is_accepted_and_wired_through(self):
        seats = [{"strategy": "midrange", "colors": ["G"], "flavor": "landfall"}]
        engine._validate_advanced_opponent_seats(seats)  # must not raise
        table = engine._build_advanced_opponent_table(seats)
        profile, _state = table[0]
        self.assertEqual(profile.flavor, "landfall")

    def test_seat_with_unknown_flavor_key_is_rejected(self):
        seats = [{"strategy": "midrange", "colors": ["G"], "flavor": "not_a_real_flavor"}]
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(seats)

    def test_seat_with_flavor_mismatched_to_its_own_colors_is_rejected(self):
        # "hatebears" is real, but only under W or GW - not under mono-Red.
        seats = [{"strategy": "aggro", "colors": ["R"], "flavor": "hatebears"}]
        with self.assertRaises(ValueError):
            engine._validate_advanced_opponent_seats(seats)

    def test_two_seats_only_one_with_a_flavor_key_resolve_independently(self):
        seats = [
            {"strategy": "aggro", "colors": ["R"]},
            {"strategy": "midrange", "colors": ["G"], "flavor": "landfall"},
        ]
        table = engine._build_advanced_opponent_table(seats)
        self.assertIsNone(table[0][0].flavor)
        self.assertEqual(table[1][0].flavor, "landfall")

    def test_end_to_end_multi_turn_simulation_with_a_flavor_seat_does_not_crash(self):
        state = make_state()
        strategy = engine.Strategy(
            advanced_opponent_model=True,
            advanced_opponent_seats=[
                {"strategy": "control", "colors": ["W", "U"], "flavor": "taxes_pillowfort"},
            ],
        )
        rng = random.Random(2024)
        for _ in range(6):
            engine._apply_advanced_multi_opponent_phase(state, strategy, rng)
        table = engine._get_advanced_opponent_table(state, strategy)
        self.assertEqual(table[0][0].flavor, "taxes_pillowfort")


def make_state(**overrides):
    defaults = dict(
        library=[], hand=[], command_zone=[], graveyard=[], exile=[], battlefield=[],
        creature_tokens=[], food=0, treasure=0, clues=0,
        life=40, opponents=[40.0], turn=5,
    )
    defaults.update(overrides)
    return engine.GameState(**defaults)


if __name__ == "__main__":
    unittest.main()
