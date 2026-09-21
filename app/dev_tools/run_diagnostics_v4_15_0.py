#!/usr/bin/env python3
"""WP6 (task #10): frischer 200er-Diagnostic-Run gegen alle 4 echten Decks
auf dem aktuellen Engine-Stand (v4.15.0), als Evidenzbasis fuer eine
moegliche Neukalibrierung der Combat-Gewichte (task #11).

Gleiches Protokoll wie run_bilbo_v482.py/run_bilbo_v483.py (runs=200,
turns=10, seed=1, opponent_profile="random", kein Scenario-File), jetzt
fuer alle vier vom Nutzer bereitgestellten Decks. Fuer Bilbo wird weiterhin
strategy_tags={"lifegain"} verwendet (Kontinuitaet zum v4.8.2/v4.8.3-
Baseline-Vergleich). Fuer Katara/Aziza/Mice with Swords existiert kein
vorheriger Tag-Baseline-Lauf, daher hier bewusst OHNE strategy_tags
(automatische Archetyp-Inferenz aus Deck/Commander), was laut
AI_ANALYSIS_INSTRUCTIONS.md ein reguraer unterstuetzter Modus ist.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402

print("Engine version:", engine.ENGINE_VERSION)

DECKS = [
    {
        "label": "Bilbo V1",
        "deck_file": ROOT / "Decks" / "Bilbo V1.txt",
        "commander_names": ["Bilbo, Birthday Celebrant"],
        "strategy_tags": {"lifegain"},
    },
    {
        "label": "Katara V3",
        "deck_file": ROOT / "Decks" / "Katara V3.txt",
        "commander_names": ["Katara, Water Tribe's Hope"],
        "strategy_tags": None,
    },
    {
        "label": "Aziza V2",
        "deck_file": ROOT / "Decks" / "Aziza V2.txt",
        "commander_names": ["Aziza, Mage Tower Captain"],
        "strategy_tags": None,
    },
    {
        "label": "Mice with Swords",
        "deck_file": ROOT / "Decks" / "Mice with Swords.txt",
        "commander_names": ["Mabel, Heir to Cragflame"],
        "strategy_tags": None,
    },
]

all_results = {}

for d in DECKS:
    print("=" * 80)
    print("Running:", d["label"], "tags=", d["strategy_tags"])
    kwargs = dict(
        deck_file=d["deck_file"],
        commander_names=d["commander_names"],
        runs=200,
        turns=10,
        seed=1,
        opponent_profile="random",
        cache_path=ROOT / "App" / ".scryfall_card_cache_v4.json",
        offline=True,
        output_root=ROOT / "Goldfish_Results" / d["label"],
    )
    if d["strategy_tags"]:
        kwargs["strategy_tags"] = d["strategy_tags"]
    result = engine.run_pipeline_v440(**kwargs)
    print("result_dir:", result["result_dir"])
    summary = result["summary"]
    outcomes = summary.get("outcomes", {})
    diagnostics = summary.get("combat_and_removal_diagnostics", {})
    print(json.dumps(outcomes, indent=2, ensure_ascii=False)[:1500])
    print(json.dumps(diagnostics, indent=2, ensure_ascii=False))
    all_results[d["label"]] = {
        "result_dir": str(result["result_dir"]),
        "outcomes": outcomes,
        "combat_and_removal_diagnostics": diagnostics,
    }

out_path = ROOT / "Goldfish_Results" / "wp6_diagnostic_v4_15_0_summary.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(
    json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("=" * 80)
print("Combined summary written to:", out_path)
