#!/usr/bin/env python3
"""Same protocol as run_bilbo_v482.py (runs=200, turns=10, seed=1,
strategy_tags={"lifegain"}, opponent_profile="random"), now against v4.8.3
(target_focus_chance=0.35 spot-removal targeting) to compare against the
v4.8.2 baseline."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402

print("Engine version:", engine.ENGINE_VERSION)

result = engine.run_pipeline_v440(
    deck_file=ROOT / "Decks" / "Bilbo V1.txt",
    commander_names=["Bilbo, Birthday Celebrant"],
    runs=200,
    turns=10,
    seed=1,
    strategy_tags={"lifegain"},
    opponent_profile="random",
    cache_path=ROOT / "App" / ".scryfall_card_cache_v4.json",
    offline=True,
    output_root=ROOT / "Goldfish_Results" / "Bilbo V1",
)

print("result_dir:", result["result_dir"])
print("zip_path:", result["zip_path"])
summary = result["summary"]
print(json.dumps(summary.get("outcomes", {}), indent=2, ensure_ascii=False)[:2000])
print(json.dumps(summary.get("combat_and_removal_diagnostics", {}), indent=2, ensure_ascii=False))
