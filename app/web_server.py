#!/usr/bin/env python3
"""Urza's Spearfishing Guide -- local web backend.

Runs the real App/engine.py simulation pipeline behind a small Flask API and
serves the new web interface (webui/index.html) on top of it, so the
interface is genuinely operational instead of only replaying a recorded
batch. Start it with:

    python web_server.py

then open the printed http://127.0.0.1:PORT address (a browser window opens
automatically unless --no-browser is passed). Everything runs locally --
no data leaves this machine except the normal Scryfall image/card lookups
your browser already makes when Scryfall is reachable.

Scope of this first version (documented, not hidden): the deck under test
is fixed to Decks/Bilbo V1.txt with its Bilbo, Birthday Celebrant commander
and the bundled win-condition scenarios -- "Run again" on the Simulation
page, and the combo builder's "Save combo" -> re-run loop, are fully live
against the real engine. Switching to a different bundled deck (Katara,
Aziza, Mice with Swords) from the interface still shows their last
recorded batch; wiring deck-switching to the live engine too is a natural
next step and does not require changes to this file's API shape, only a
`deck_file`/`commander_names` field on the /api/simulate request body,
which the endpoint already accepts.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, request, send_from_directory  # noqa: E402

from App import engine  # noqa: E402
from webui_transform import to_frontend_run  # noqa: E402

WEBUI_DIR = ROOT / "webui"
DECKS_DIR = ROOT / "Decks"
CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"
RESULTS_ROOT = ROOT / "Goldfish_Results"

DEFAULT_DECK_FILE = "Bilbo V1.txt"
DEFAULT_COMMANDERS = ["Bilbo, Birthday Celebrant"]
DEFAULT_SCENARIOS_FILE = DECKS_DIR / "bilbo_win_conditions_40_each_v4_3.json"

app = Flask(__name__, static_folder=None)

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _load_default_scenarios() -> list[dict]:
    if DEFAULT_SCENARIOS_FILE.exists():
        try:
            return engine.load_scenarios(DEFAULT_SCENARIOS_FILE)
        except Exception:
            return []
    return []


def _build_reference(deck_file: Path, commander_names: list[str], tags: list[str]) -> dict | None:
    """Same App/archetype_profile comparison the desktop app's "Vergleich
    (1.585 Decks)" tab uses, computed for whichever deck/tags this run
    just simulated -- see App/engine.py::compare_deck_to_archetype_reference.
    """
    try:
        deck = engine.build_deck_v4(deck_file, commander_names, CACHE_PATH, True, None)
        commanders = set(commander_names)
        deck = [engine.replace(c, commander=(c.name in commanders)) for c in deck]
        cards = {}
        for c in deck:
            cards.setdefault(c.name, c)
        result = engine.compare_deck_to_archetype_reference(deck, commanders, cards, tags=tags)

        def ser(ar):
            if ar is None:
                return None
            return {"basis": ar.basis, "comparison": ar.comparison, "unclassified_cards": ar.unclassified_cards}

        return {
            "identity_slug": result["identity_slug"],
            "identity_label": result["identity_label"],
            "recognized_tags": result["recognized_tags"],
            "requested_tags": result["requested_tags"],
            "identity_only": ser(result["identity_only"]),
            "with_strategy": ser(result["with_strategy"]),
        }
    except Exception as exc:  # noqa: BLE001 - a missing/broken reference must never break the run itself
        return {"error": str(exc)}


def _run_job(job_id: str, body: dict) -> None:
    job = JOBS[job_id]
    try:
        deck_file = DECKS_DIR / body.get("deck_file", DEFAULT_DECK_FILE)
        commander_names = body.get("commander_names") or DEFAULT_COMMANDERS
        runs = max(10, min(5000, int(body.get("runs", 200))))
        turns = max(1, min(20, int(body.get("turns", 10))))
        seed = int(body.get("seed", 1))
        opponent_profile = body.get("opponent_profile", "random")
        strategy_tags = set(body.get("strategy_tags") or [])
        raw_scenarios = body.get("scenarios")
        if raw_scenarios:
            scenarios = [engine.normalize_scenario(s, i) for i, s in enumerate(raw_scenarios)]
        else:
            scenarios = _load_default_scenarios()

        job["total"] = runs

        def progress_cb(done, total):
            job["done"] = done
            job["total"] = total

        result = engine.run_pipeline_v440(
            deck_file=deck_file,
            commander_names=commander_names,
            runs=runs, turns=turns, seed=seed,
            strategy_tags=strategy_tags,
            opponent_profile=opponent_profile,
            scenarios=scenarios,
            cache_path=CACHE_PATH,
            offline=True,
            output_root=RESULTS_ROOT / deck_file.stem,
            progress_callback=progress_cb,
        )
        ref = _build_reference(deck_file, commander_names, sorted(strategy_tags))
        run_label = "Live run, " + time.strftime("%d.%m.%Y, %H:%M")
        summary = to_frontend_run(result["summary"], ref, run_label)
        with JOBS_LOCK:
            job["status"] = "done"
            job["done"] = job["total"]
            job["summary"] = summary
    except Exception as exc:  # noqa: BLE001 - surface the real error to the UI instead of hanging the poll
        with JOBS_LOCK:
            job["status"] = "error"
            job["error"] = f"{type(exc).__name__}: {exc}"


@app.get("/")
def index():
    return send_from_directory(WEBUI_DIR, "index.html")


@app.get("/api/health")
def health():
    return jsonify(ok=True, engine=engine.ENGINE_VERSION)


@app.get("/api/decks")
def list_decks():
    return jsonify([f.stem for f in sorted(DECKS_DIR.glob("*.txt"))])


@app.post("/api/simulate")
def start_simulate():
    body = request.get_json(force=True, silent=True) or {}
    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "running", "done": 0, "total": int(body.get("runs", 200))}
    threading.Thread(target=_run_job, args=(job_id, body), daemon=True).start()
    return jsonify(job_id=job_id)


@app.get("/api/simulate/<job_id>")
def poll_simulate(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify(error="unknown job_id"), 404
    return jsonify(job)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    url = f"http://127.0.0.1:{args.port}/"
    print(f"Urza's Spearfishing Guide -- engine {engine.ENGINE_VERSION}")
    print(f"Serving on {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
