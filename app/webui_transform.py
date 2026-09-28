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
            # v4.79.0 (Runde 1): "each" = predicate checked ALL opponents
            # (a real full win per check_win()'s all-opponents rule), "any"/
            # "mixed" = at least one predicate only checked a single (the
            # weakest) opponent, so reaching the setup is not the same as
            # winning the game. See win_condition_reach_and_full_win_pct /
            # win_condition_reach_but_no_full_win_pct in outcomes below.
            target_scope=s.get("target_scope", "n/a"),
            # v4.87.4: fuer die neu gestalteten Win-Condition-Eintraege -
            # typischer Zug und kumulierte Erreichung je Zug (Mini-Verlauf).
            median_turn=s.get("median_reached_turn"),
            cum=[
                [int(t), v]
                for t, v in sorted((s.get("cumulative_reach_by_turn_pct") or {}).items(), key=lambda kv: int(kv[0]))
            ],
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
            advanced_opponent_model=bool(sim.get("advanced_opponent_model", False)),
            defense_model=sim.get("defense_model", ""),
            playstyle=sim.get("playstyle", {}),
            trigger_bus=sim.get("trigger_bus", {}),
            table_model=sim.get("table_model", ""),
            loose_win_condition_policy=sim.get("loose_win_condition_policy", ""),
            simple_profile_mapped_to_table=sim.get("simple_profile_mapped_to_table", ""),
            commander_posture=sim.get("commander_posture", "auto"),
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
        model_gaps=summary.get("model_gaps", []),
        model_gaps_total=summary.get("model_gaps_total", len(summary.get("model_gaps", []) or [])),
        archetype_reference=archetype_ref,
        metrics=summary.get("metrics") or _legacy_metrics(summary, byturn),
    )


def _legacy_metrics(summary: dict, byturn: list) -> dict:
    """v4.87.4: Laeufe, die vor den generischen Fokus-Metriken aufgezeichnet
    wurden, kennen nur Leben (mit festen Schwellen), Mana und Laender pro
    Zug. Daraus dieselbe Form bauen, damit die Oberflaeche nur einen Pfad
    braucht; 'legacy' sagt ihr, dass ein neuer Lauf mehr zeigt."""
    o = summary.get("outcomes", {}) or {}
    raw_bt = summary.get("by_turn", {}) or {}

    def series(field):
        return [dict(t=d["t"], avg=d.get(field)) for d in byturn if d.get(field) is not None]

    out = {}
    life_fixed = [[m, o.get(f"reach_{m}_life_pct")] for m in (50, 60, 80, 100, 111)
                  if o.get(f"reach_{m}_life_pct") is not None]
    if byturn:
        out["life"] = dict(label="Life total", unit="life", dir="up", group="Life",
                           by_turn=series("avg_life"), fixed=life_fixed, legacy=True)
        out["mana"] = dict(label="Mana at start of main phase", unit="mana", dir="up", group="Mana",
                           by_turn=series("avg_mana_start_main"), legacy=True)
        out["lands"] = dict(label="Lands on the battlefield", unit="lands", dir="up", group="Mana",
                            by_turn=series("avg_lands"), legacy=True)
        hand = [dict(t=int(t), avg=v.get("avg_hand_size")) for t, v in sorted(raw_bt.items(), key=lambda kv: int(kv[0]))
                if v.get("avg_hand_size") is not None]
        if hand:
            out["hand"] = dict(label="Cards in hand", unit="cards", dir="up", group="Cards", by_turn=hand, legacy=True)
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ref = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")) if len(sys.argv) > 2 else None
    out = to_frontend_run(raw, ref, sys.argv[3] if len(sys.argv) > 3 else "run")
    print(json.dumps(out, ensure_ascii=False))
