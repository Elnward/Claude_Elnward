"""Shared transform: raw engine summary -> the flat JSON shape the
Urza's Spearfishing Guide web frontend (app3/app4/app5.js) consumes as
`DATA.run`. Used both to (re)build the static preview data.js and by the
Flask backend after every live simulation, so static-preview and live
mode render through exactly the same frontend code path."""
import json


def to_frontend_run(summary: dict, archetype_ref: dict | None, run_label: str) -> dict:
    sim = summary["simulation"]
    by_turn = summary["by_turn"]
    byturn = [
        dict(
            t=int(t),
            avg_life=v.get("avg_life"),
            avg_mana_start_main=v.get("avg_mana_start_main"),
            avg_lands=v.get("avg_lands"),
        )
        for t, v in sorted(by_turn.items(), key=lambda kv: int(kv[0]))
    ]
    scen = [
        dict(
            name=s["name"],
            reach=s.get("reach_pct", 0.0),
            cards=s.get("cards_thresholds_reached_pct", 0.0),
            bn=s.get("top_diagnostic_bottlenecks", []),
        )
        for s in summary.get("scenarios", [])
    ]
    deck = summary.get("deck", {})
    return dict(
        run_label=run_label,
        simulation=dict(
            runs=sim["runs"], turns=sim["turns"], seed=sim["seed"],
            opponent_profile=sim["opponent_profile"],
            strategy_tags=sim.get("strategy_tags", []),
            scenario_count=sim.get("scenario_count", 0),
            engine_version=summary.get("version"),
        ),
        outcomes=summary["outcomes"],
        deck=dict(
            curve=deck.get("curve", {}),
            colored_pips=deck.get("colored_pips", {}),
            role_counts=deck.get("role_counts", {}),
        ),
        opening=summary.get("opening", {}),
        byturn=byturn,
        opp=summary.get("opponent_breakdown", {}),
        combat=summary.get("combat_and_removal_diagnostics", {}),
        hl=summary.get("relative_card_highlights", []),
        scen=scen,
        engine_invariants=summary.get("engine_invariants", {}),
        archetype_reference=archetype_ref,
    )


if __name__ == "__main__":
    import sys
    from pathlib import Path
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ref = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")) if len(sys.argv) > 2 else None
    out = to_frontend_run(raw, ref, sys.argv[3] if len(sys.argv) > 3 else "run")
    print(json.dumps(out, ensure_ascii=False))
