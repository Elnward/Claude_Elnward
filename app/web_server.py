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

Deck handling: the /api/decks and /api/deck/<name> endpoints build any
.txt/.csv decklist in Decks/ live through App/engine.py's own parser
(the same one the desktop app uses -- Moxfield/Archidekt/EDHREC-style
exports, MTGGoldfish CSV, a bare "N Cardname" list, all already supported
there), so a deck someone else built and exported elsewhere works the same
way the bundled decks do. Commander selection persists per deck in
Decks/.deck_meta.json (created on first use).
"""
from __future__ import annotations

import json
import math
import re
import sys
import threading
import time
import uuid
import webbrowser
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from flask import Flask, Response, jsonify, request, send_file, send_from_directory  # noqa: E402

from App import engine  # noqa: E402
from webui_transform import to_frontend_run  # noqa: E402
from App.factsheet_pdf import build_factsheet_pdf  # noqa: E402

WEBUI_DIR = ROOT / "webui"
DECKS_DIR = ROOT / "Decks"
CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"
RESULTS_ROOT = ROOT / "Goldfish_Results"
DECK_META_PATH = DECKS_DIR / ".deck_meta.json"

DECK_EXTENSIONS = (".txt", ".csv", ".dek", ".list")

DEFAULT_DECK_FILE = "Bilbo V1.txt"
DEFAULT_COMMANDERS = ["Bilbo, Birthday Celebrant"]
DEFAULT_SCENARIOS_FILE = DECKS_DIR / "bilbo_win_conditions_40_each_v4_3.json"

CURVE_KEYS = ["0", "1", "2", "3", "4", "5", "6", "7+"]

# Nonland card types that go into the mana curve, and the archetype_profile
# deck-composition field each corresponds to (used to weight each type's own
# reference mana-value histogram into one combined nonland curve -- see
# _reference_nonland_curve below).
_CURVE_TYPES_TO_COMPOSITION_FIELD = {
    "Creature": "n_creatures",
    "Artifact": "n_artifacts",
    "Enchantment": "n_enchantments",
    "Instant": "n_instants",
    "Sorcery": "n_sorceries",
    "Planeswalker": "n_planeswalkers",
}

_UNSAFE_NAME_RE = re.compile(r'[\\/:*?"<>|]')

app = Flask(__name__, static_folder=None)

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


# --------------------------------------------------------------- deck files

def _safe_deck_stem(raw: str) -> str:
    """Turns a user-supplied deck name into a safe filename stem: strips
    path separators and other filesystem-unsafe characters, collapses
    whitespace, caps the length. Never raises -- worst case returns ''."""
    cleaned = _UNSAFE_NAME_RE.sub("", raw or "").strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:80]


def _find_deck_file(stem: str) -> Path | None:
    for ext in DECK_EXTENSIONS:
        p = DECKS_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def _list_deck_files() -> list[Path]:
    seen = set()
    out = []
    for ext in DECK_EXTENSIONS:
        for p in sorted(DECKS_DIR.glob(f"*{ext}")):
            if p.stem not in seen:
                seen.add(p.stem)
                out.append(p)
    return out


def _load_deck_meta() -> dict:
    if DECK_META_PATH.exists():
        try:
            return json.loads(DECK_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_deck_meta(meta: dict) -> None:
    DECK_META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_commanders(deck_stem: str, deck_file: Path) -> list[str]:
    """Commander(s) to use when a request doesn't specify one explicitly:
    whatever was last chosen and saved for this deck (Decks/.deck_meta.json),
    falling back to what App/engine.py can detect straight from the decklist
    file itself (a "// Commander" section, a bare "Commander" header, or a
    "(Commander)" inline annotation -- see engine.detect_commander_hints)."""
    meta = _load_deck_meta()
    stored = (meta.get(deck_stem) or {}).get("commanders")
    if stored:
        return stored
    try:
        return engine.detect_commander_hints(deck_file)
    except Exception:
        return []


def _resolve_tags(deck_stem: str) -> list[str]:
    """Strategy tags saved for this deck (Decks/.deck_meta.json, set together
    with the commander in the "Change commander" dialog) -- deck-scoped, so
    running a different deck's simulation never picks up another deck's
    strategy tags (they feed both the EDHREC archetype-reference comparison
    and the goldfish value model's per-strategy weighting)."""
    meta = _load_deck_meta()
    return list((meta.get(deck_stem) or {}).get("tags") or [])


_PLAYSTYLE_KEYS = ("aggression", "attacker_selection", "block_willingness")

# v4.87.0: the "Table" tab -- global (not per-deck) table-politics knobs from
# Data/Models/table_dynamics.json::table_politics, mirrored here only for
# request validation (kept in sync by hand, same as _PLAYSTYLE_KEYS above).
# "enabled" (bool) and "target_mode" (enum) are validated separately below.
_TABLE_POLITICS_DEFAULTS = {
    "enabled": True,
    "kingmaking_life_threshold": 15.0,
    "kingmaking_revenge_weight": 2.0,
    "kingmaking_leader_weight": 0.08,
    "kingmaking_grudge_decay": 0.6,
    "grudge_weight": 0.1,
    "target_mode": "uniform",
    "threat_leader_weight": 0.08,
    "group_hug_malus_per_point": 0.15,
    "group_hug_value_cap": 5.0,
}
_TABLE_POLITICS_RANGES = {
    "kingmaking_life_threshold": (0.0, 40.0),
    "kingmaking_revenge_weight": (0.0, 10.0),
    "kingmaking_leader_weight": (0.0, 1.0),
    "kingmaking_grudge_decay": (0.0, 1.0),
    "grudge_weight": (0.0, 2.0),
    "threat_leader_weight": (0.0, 1.0),
    "group_hug_malus_per_point": (0.0, 1.0),
    "group_hug_value_cap": (0.0, 20.0),
}
_TABLE_POLITICS_TARGET_MODES = ("uniform", "threat")


def _resolve_playstyle(deck_stem: str) -> dict:
    """Deck-wide play-style sliders saved for this deck (Decks/.deck_meta.json,
    set alongside commander/tags in "Change commander") -- same deck-scoping
    as _resolve_tags. Missing/partial entries are left out here; App/
    combat_model/playstyle.py::get() is what actually defaults them at
    simulation time, so an empty dict correctly means "today's behavior"."""
    meta = _load_deck_meta()
    raw = (meta.get(deck_stem) or {}).get("playstyle") or {}
    out = {}
    for k in _PLAYSTYLE_KEYS:
        if k in raw:
            try:
                out[k] = max(0.0, min(100.0, float(raw[k])))
            except (TypeError, ValueError):
                pass
    return out


def _read_last_run(deck_stem: str) -> dict | None:
    """Light-weight summary of the most recent recorded run for a deck, read
    straight from Goldfish_Results/<deck>/*/summary.json -- no engine call,
    just a filesystem + JSON read, so the deck board can show real numbers
    without rebuilding every deck on every page load."""
    folder = RESULTS_ROOT / deck_stem
    if not folder.is_dir():
        return None
    run_dirs = sorted((p for p in folder.iterdir() if p.is_dir()), reverse=True)
    for run_dir in run_dirs:
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        outcomes = data.get("outcomes", {})
        deck_info = data.get("deck", {})
        return {
            "date": datetime.fromtimestamp(summary_path.stat().st_mtime).strftime("%d.%m.%Y"),
            "engine_version": data.get("version"),
            "win_pct": outcomes.get("win_by_turn_limit_pct"),
            "loss_pct": outcomes.get("loss_by_turn_limit_pct"),
            "cards": deck_info.get("cards"),
            "lands": deck_info.get("lands"),
            "commanders": deck_info.get("commanders"),
        }
    return None


# ----------------------------------------------------------- deck contents

def _curve_dict(deck: list) -> dict:
    buckets: Counter = Counter()
    for c in deck:
        if c.is_land:
            continue
        mv = int(math.ceil(c.mana_value))
        buckets[str(mv) if mv < 7 else "7+"] += 1
    return {k: buckets.get(k, 0) for k in CURVE_KEYS}


def _pips_dict(deck: list) -> dict:
    pips: Counter = Counter()
    for c in deck:
        if not c.is_land:
            pips.update(c.color_requirements)
    return dict(pips)


def _card_rows(deck: list) -> list[dict]:
    order: list[str] = []
    rows: dict[str, dict] = {}
    for c in deck:
        if c.name not in rows:
            rows[c.name] = {
                "n": c.name, "q": 0, "c": c.mana_cost, "t": c.type_line,
                "mv": c.mana_value, "ro": "|".join(sorted(c.roles)),
                "cmd": bool(c.commander),
            }
            order.append(c.name)
        rows[c.name]["q"] += 1
    return [rows[n] for n in order]


def _load_deck_for_commanders(deck_file: Path, commander_names: list[str]) -> list:
    # offline=False: use the local Scryfall cache first (so every already-
    # known card, i.e. every bundled deck, never touches the network at
    # all) and only reach out to Scryfall for names the cache doesn't have
    # yet -- the case that actually matters for a freshly uploaded deck.
    return engine.build_deck_v4(deck_file, commander_names, CACHE_PATH, False, None)


def _bucket_key_for_reference_range(label: str) -> str:
    """archetype_profile's cmc_histogram buckets ("0-1","1-2",...,"8-10",
    "10-25") by their lower edge, which lines up with an integer mana value
    for every bucket except the two tail ones -- both fold into the same
    '7+' bucket the frontend's own curve chart already uses."""
    lo = label.split("-")[0]
    try:
        lo_i = int(float(lo))
    except ValueError:
        return "7+"
    return str(lo_i) if lo_i < 7 else "7+"


def _reference_nonland_curve(model, identity_slug: str, tags: list[str], total_nonland: int) -> dict:
    """The 1,585-deck reference's average nonland mana curve for this color
    identity (+ recognized strategy tags, if any), combined across every
    nonland card type and rescaled to the same total-nonland-card unit as
    the tested deck's own curve, so the two can be drawn as one histogram.
    Uses exactly the same App/archetype_profile methodology (and the same
    cached AverageDeckModel) as the "Reference: 1,585 EDHREC decks" panel."""
    weighted: Counter = Counter()
    total_weight = 0.0
    comp = model.estimate_composition(identity_slug, tags)
    for type_, field in _CURVE_TYPES_TO_COMPOSITION_FIELD.items():
        weight = max(0.0, float(comp.get(field, 0.0) or 0.0))
        if weight <= 0:
            continue
        curve = model.estimate_manacurve(identity_slug, tags, type_)
        hist = curve.get("identity_histogram") or {}
        if not hist:
            continue
        total_weight += weight
        for bucket_label, frac in hist.items():
            weighted[_bucket_key_for_reference_range(bucket_label)] += weight * frac
    raw_sum = sum(weighted.values())
    if total_weight <= 0 or raw_sum <= 0:
        return {}
    scale = total_nonland / raw_sum
    return {k: round(weighted.get(k, 0.0) * scale, 2) for k in CURVE_KEYS}


# --------------------------------------------------------- archetype refs

def _build_reference(deck_file: Path, commander_names: list[str], tags: list[str]) -> dict | None:
    """Same App/archetype_profile comparison the desktop app's "Vergleich
    (1.585 Decks)" tab uses, computed for whichever deck/tags this run
    just simulated -- see App/engine.py::compare_deck_to_archetype_reference.
    """
    try:
        deck = engine.build_deck_v4(deck_file, commander_names, CACHE_PATH, False, None)
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


def _load_default_scenarios() -> list[dict]:
    if DEFAULT_SCENARIOS_FILE.exists():
        try:
            return engine.load_scenarios(DEFAULT_SCENARIOS_FILE)
        except Exception:
            return []
    return []


def _run_job(job_id: str, body: dict) -> None:
    job = JOBS[job_id]
    try:
        if body.get("deck_name"):
            deck_file = _find_deck_file(body["deck_name"])
            if deck_file is None:
                raise RuntimeError(f"deck {body['deck_name']!r} not found")
        else:
            deck_file = DECKS_DIR / body.get("deck_file", DEFAULT_DECK_FILE)
        commander_names = body.get("commander_names") or _resolve_commanders(deck_file.stem, deck_file)
        if not commander_names:
            raise RuntimeError(
                f"No commander selected for {deck_file.stem!r}. Pick one on the Deck tab first."
            )
        runs = max(10, min(5000, int(body.get("runs", 200))))
        turns = max(1, min(20, int(body.get("turns", 20))))  # v4.83.0: 20 statt 10 - am Vierertisch ist nach 10 Zuegen erst ~die Haelfte der Partien entschieden
        seed = int(body.get("seed", 1))
        opponent_profile = body.get("opponent_profile", "random")
        if opponent_profile in ("none", "", None):
            opponent_profile = "goldfish"
        # v4.76.0: the Simulation page's "Advanced opponent model" checkbox
        # (previously not wired to anything). Three Bracket-3 seats from the
        # calibrated App/opponent_model state equation; each seat's strategy
        # follows the chosen opponent type ("?" = re-rolled per run for
        # "random"), colors are re-rolled per run. Meaningless for pure
        # goldfish, so it is ignored there.
        # v4.77.0 WP-C: default True when the caller omits the field
        # entirely (the web UI's own checkbox now also defaults to checked;
        # this covers a direct /api/simulate call, e.g. from a script). An
        # explicit `false` still turns it off.
        advanced = bool(body.get("advanced_opponent_model", True)) and opponent_profile != "goldfish"
        advanced_seats = None
        if advanced:
            seat_strategy = "?" if opponent_profile == "random" else opponent_profile
            advanced_seats = [{"strategy": seat_strategy, "colors": "?", "bracket": 3} for _ in range(3)]
        # Falls back to whatever strategy tags are saved for this deck
        # (Decks/.deck_meta.json, set in "Change commander") if the caller
        # didn't pass any explicitly -- keeps this deck-scoped end to end.
        strategy_tags = set(body.get("strategy_tags") or _resolve_tags(deck_file.stem))
        # v4.77.0: same deck-scoped fallback as strategy_tags -- an explicit
        # per-request override (e.g. a future "try this playstyle without
        # saving it" control) wins, otherwise whatever is saved for this deck.
        playstyle = body.get("playstyle") if isinstance(body.get("playstyle"), dict) else _resolve_playstyle(deck_file.stem)
        raw_scenarios = body.get("scenarios")
        if raw_scenarios:
            scenarios = [engine.normalize_scenario(s, i) for i, s in enumerate(raw_scenarios)]
        elif deck_file.stem == Path(DEFAULT_DECK_FILE).stem:
            # The bundled win-condition scenarios are Bilbo V1-specific (they
            # reference its own cards) -- only fall back to them for that
            # exact deck. Any other deck with nothing saved in the combo
            # builder simply runs without win-condition scenarios.
            scenarios = _load_default_scenarios()
        else:
            scenarios = []

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
            offline=False,
            output_root=RESULTS_ROOT / deck_file.stem,
            progress_callback=progress_cb,
            advanced_opponent_model=advanced or None,
            advanced_opponent_seats=advanced_seats,
            playstyle=playstyle or None,
            # v4.87.4: the Simulation page's "Commander posture" choice
            # (previously collected but never sent anywhere).
            commander_posture=str(body.get("commander_posture") or "auto"),
        )
        ref = _build_reference(deck_file, commander_names, sorted(strategy_tags))
        run_label = "Live run, " + time.strftime("%d.%m.%Y, %H:%M")
        summary = to_frontend_run(result["summary"], ref, run_label)
        # v4.87.5: lets the Analysis page offer this run's folder as a ZIP.
        summary["run_dir"] = Path(result["result_dir"]).name
        summary["deck_name"] = deck_file.stem
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


@app.get("/favicon.ico")
def favicon_ico():
    return send_from_directory(WEBUI_DIR, "favicon.ico")


@app.get("/favicon-32.png")
def favicon_32():
    return send_from_directory(WEBUI_DIR, "favicon-32.png")


@app.get("/apple-touch-icon.png")
def apple_touch_icon():
    return send_from_directory(WEBUI_DIR, "apple-touch-icon.png")


@app.get("/icon-192.png")
def icon_192():
    return send_from_directory(WEBUI_DIR, "icon-192.png")


@app.get("/api/health")
def health():
    return jsonify(ok=True, engine=engine.ENGINE_VERSION)


@app.get("/api/decks")
def list_decks():
    out = []
    for f in _list_deck_files():
        stem = f.stem
        last_run = _read_last_run(stem)
        commanders = (last_run or {}).get("commanders") or _resolve_commanders(stem, f)
        out.append({
            "name": stem,
            "commanders": commanders,
            "cards": (last_run or {}).get("cards"),
            "lands": (last_run or {}).get("lands"),
            "last_run": last_run,
        })
    return jsonify(out)


@app.get("/api/deck/<name>")
def get_deck(name):
    deck_file = _find_deck_file(name)
    if deck_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    commanders = _resolve_commanders(name, deck_file)
    try:
        deck = _load_deck_for_commanders(deck_file, commanders)
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"could not load deck: {exc}"), 500

    cards_map: dict = {}
    for c in deck:
        cards_map.setdefault(c.name, c)
    identity_slug = identity_label = None
    try:
        identity_slug = engine.commander_identity_slug(cards_map, commanders)
        identity_label = engine._ARCHETYPE_SLUG_TO_LABEL.get(identity_slug, identity_slug)
    except Exception:
        pass

    return jsonify({
        "name": name,
        "commanders": commanders,
        "commander_candidates": sorted({c.name for c in deck if engine.commander_eligible_card(c)}),
        "tags": _resolve_tags(name),
        "playstyle": _resolve_playstyle(name),
        "identity_slug": identity_slug,
        "identity_label": identity_label,
        "counts": {
            "total": len(deck),
            "lands": sum(c.is_land for c in deck),
            "nonland": sum(not c.is_land for c in deck),
        },
        "curve": _curve_dict(deck),
        "colored_pips": _pips_dict(deck),
        "role_counts": dict(Counter(role for c in deck for role in c.roles)),
        "cards": _card_rows(deck),
    })


@app.get("/api/deck/<name>/last-run")
def deck_last_run(name):
    """The most recent recorded run for this deck, run through the same
    to_frontend_run() shape the live /api/simulate result uses, so the UI
    can show real numbers for whichever deck is selected as soon as it's
    opened -- not just after a fresh run in this session."""
    deck_file = _find_deck_file(name)
    if deck_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    folder = RESULTS_ROOT / name
    if not folder.is_dir():
        return jsonify(run=None)
    for run_dir in sorted((p for p in folder.iterdir() if p.is_dir()), reverse=True):
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue
        try:
            raw = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        commanders = raw.get("deck", {}).get("commanders") or _resolve_commanders(name, deck_file)
        tags = raw.get("simulation", {}).get("strategy_tags", [])
        ref = _build_reference(deck_file, commanders, tags)
        date_str = datetime.fromtimestamp(summary_path.stat().st_mtime).strftime("%d.%m.%Y, %H:%M")
        frontend_run = to_frontend_run(raw, ref, "Recorded run, " + date_str)
        frontend_run["run_dir"] = run_dir.name
        frontend_run["deck_name"] = name
        return jsonify(run=frontend_run)
    return jsonify(run=None)


# ----------------------------------------------------- v4.87.5: downloads

def _run_folder(name: str, run_dir: str) -> Path | None:
    """Goldfish_Results/<deck>/<run_dir>, only if both are plain folder names
    that really exist there (no path tricks through the URL)."""
    if not name or not run_dir or Path(name).name != name or Path(run_dir).name != run_dir or run_dir.startswith("."):
        return None
    folder = (RESULTS_ROOT / name / run_dir).resolve()
    try:
        folder.relative_to(RESULTS_ROOT.resolve())
    except ValueError:
        return None
    return folder if folder.is_dir() else None


@app.get("/api/deck/<name>/runs/<run_dir>/zip")
def download_run_zip(name, run_dir):
    """The whole result folder of one run (summary, per-game logs, card
    coverage, analysis overview) as a ZIP - the engine already writes one next
    to each run folder; older folders without it are zipped on the fly."""
    folder = _run_folder(name, run_dir)
    if folder is None:
        return jsonify(error="run not found"), 404
    ready = folder.with_suffix(".zip")
    if ready.is_file():
        return send_file(ready, mimetype="application/zip", as_attachment=True, download_name=ready.name)
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(folder.parent))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=folder.name + ".zip")


@app.post("/api/factsheet")
def factsheet_pdf():
    """Fact sheet PDF of the run the Analysis page is showing. The page posts
    what it displays (run, deck, focus metric, notes); the table-politics
    settings are filled in here when the page has not loaded them."""
    body = request.get_json(force=True, silent=True) or {}
    if not isinstance(body.get("run"), dict) or not body["run"].get("outcomes"):
        return jsonify(error="no simulation run to describe"), 400
    if not body.get("table"):
        section = engine.TABLE_DYNAMICS.get("table_politics", {}) or {}
        body["table"] = {k: section.get(k, d) for k, d in _TABLE_POLITICS_DEFAULTS.items()}
    try:
        pdf = build_factsheet_pdf(body)
    except Exception as exc:  # noqa: BLE001 - show the real reason in the UI
        return jsonify(error=f"{type(exc).__name__}: {exc}"), 500
    deck = str((body.get("deck") or {}).get("name") or "deck")
    safe = re.sub(r"[^A-Za-z0-9 ._-]+", "", deck).strip() or "deck"
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{safe} fact sheet.pdf"'})


@app.get("/api/deck/<name>/curve-reference")
def deck_curve_reference(name):
    """The average nonland mana curve of comparable EDHREC decks (same
    color identity, optionally + recognized strategy tags), for the "Show
    average" overlay on the Deck tab's mana curve chart."""
    deck_file = _find_deck_file(name)
    if deck_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    tags = [t for t in request.args.get("tags", "").split(",") if t]
    try:
        commanders = _resolve_commanders(name, deck_file)
        deck = _load_deck_for_commanders(deck_file, commanders)
        cards_map: dict = {}
        for c in deck:
            cards_map.setdefault(c.name, c)
        identity_slug = engine.commander_identity_slug(cards_map, commanders)
        recognized_tags = [
            engine._STRATEGY_TAG_TO_ARCHETYPE_TAG[t]
            for t in tags if t in engine._STRATEGY_TAG_TO_ARCHETYPE_TAG
        ]
        model = engine._get_archetype_analyzer().model
        nonland = sum(not c.is_land for c in deck)
        histogram = _reference_nonland_curve(model, identity_slug, recognized_tags, nonland)
        return jsonify(identity_slug=identity_slug, tags=recognized_tags, histogram=histogram)
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=str(exc)), 500


@app.post("/api/decks/upload")
def upload_deck():
    if "file" not in request.files:
        return jsonify(error="no file uploaded (form field 'file' missing)"), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify(error="empty filename"), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in DECK_EXTENSIONS:
        return jsonify(error=f"unsupported file type {ext or '(none)'!r} -- expected .txt or .csv"), 400

    requested = (request.form.get("name") or Path(f.filename).stem).strip()
    stem = _safe_deck_stem(requested) or "Uploaded Deck"
    overwrite = request.form.get("overwrite") == "true"
    target = DECKS_DIR / f"{stem}{ext}"
    if target.exists() and not overwrite:
        i = 2
        while (DECKS_DIR / f"{stem} ({i}){ext}").exists():
            i += 1
        stem = f"{stem} ({i})"
        target = DECKS_DIR / f"{stem}{ext}"

    try:
        text = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return jsonify(error="could not read this file as text (expected a plain-text decklist export)"), 400

    target.write_text(text, encoding="utf-8")
    try:
        if ext == ".csv":
            entries, _cols = engine.load_csv_entries(target)
        else:
            entries = engine.load_txt_entries(target)
    except Exception as exc:
        target.unlink(missing_ok=True)
        return jsonify(error=f"could not parse this decklist: {exc}"), 400

    if not entries:
        target.unlink(missing_ok=True)
        return jsonify(error="no card lines recognized in this file"), 400

    try:
        hints = engine.detect_commander_hints(target)
    except Exception:
        hints = []
    if hints:
        meta = _load_deck_meta()
        meta[stem] = {"commanders": hints}
        _save_deck_meta(meta)

    return jsonify(
        name=stem,
        card_count=sum(e.count for e in entries),
        unique_cards=len(entries),
        commander_guess=hints,
    )


@app.post("/api/decks/<name>/rename")
def rename_deck(name):
    body = request.get_json(force=True, silent=True) or {}
    new_stem = _safe_deck_stem(body.get("new_name") or "")
    if not new_stem:
        return jsonify(error="new_name required"), 400
    old_file = _find_deck_file(name)
    if old_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    if new_stem == old_file.stem:
        return jsonify(name=new_stem)
    new_file = old_file.with_name(new_stem + old_file.suffix)
    if new_file.exists():
        return jsonify(error=f"a deck named {new_stem!r} already exists"), 409

    old_file.rename(new_file)
    meta = _load_deck_meta()
    if old_file.stem in meta:
        meta[new_stem] = meta.pop(old_file.stem)
        _save_deck_meta(meta)
    old_results = RESULTS_ROOT / old_file.stem
    new_results = RESULTS_ROOT / new_stem
    if old_results.is_dir() and not new_results.exists():
        old_results.rename(new_results)

    return jsonify(name=new_stem)


@app.delete("/api/decks/<name>")
def delete_deck(name):
    """Delete a deck's source file and its saved commander/tags/playstyle
    entry. Recorded Goldfish_Results runs for this deck are left in place
    (they're just historical output, not part of the deck itself) so an
    accidental delete doesn't also wipe past results."""
    deck_file = _find_deck_file(name)
    if deck_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    if len(_list_deck_files()) <= 1:
        return jsonify(error="cannot delete the last remaining deck"), 400
    deck_file.unlink(missing_ok=True)
    meta = _load_deck_meta()
    if meta.pop(name, None) is not None:
        _save_deck_meta(meta)
    return jsonify(ok=True, name=name)


@app.post("/api/decks/<name>/cards")
def add_card(name):
    """Add a card to this deck's mainboard (or increase its count if it's
    already there). Body: {"name": "<card name>", "count": <int, default
    1>}. .txt decklists only -- the deck-editing UI only ever uploads/keeps
    .txt files, so a CSV import here would be scope creep for now."""
    body = request.get_json(force=True, silent=True) or {}
    card_name = (body.get("name") or "").strip()
    if not card_name:
        return jsonify(error="name required"), 400
    try:
        count = int(body.get("count", 1))
    except (TypeError, ValueError):
        return jsonify(error="count must be a whole number"), 400
    deck_file = _find_deck_file(name)
    if deck_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    if deck_file.suffix.lower() != ".txt":
        return jsonify(error="adding cards is only supported for .txt decklists"), 400
    try:
        new_total = engine.add_card_to_txt_deck(deck_file, card_name, count)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(ok=True, name=card_name, count=new_total)


@app.delete("/api/decks/<name>/cards/<card_name>")
def remove_card(name, card_name):
    """Remove a card from this deck's mainboard. Optional query param
    ?count=N removes only N copies of that line (default: the whole line,
    all copies)."""
    deck_file = _find_deck_file(name)
    if deck_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    if deck_file.suffix.lower() != ".txt":
        return jsonify(error="removing cards is only supported for .txt decklists"), 400
    count = request.args.get("count", type=int)
    removed = engine.remove_card_from_txt_deck(deck_file, card_name, count)
    if not removed:
        return jsonify(error=f"{card_name!r} is not in this deck's mainboard"), 404
    return jsonify(ok=True, name=card_name)


@app.post("/api/decks/<name>/commander")
def set_commander(name):
    body = request.get_json(force=True, silent=True) or {}
    commanders = body.get("commanders")
    if not commanders or not isinstance(commanders, list):
        return jsonify(error="commanders (non-empty list) required"), 400
    deck_file = _find_deck_file(name)
    if deck_file is None:
        return jsonify(error=f"deck {name!r} not found"), 404
    try:
        deck = _load_deck_for_commanders(deck_file, commanders)
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"could not load deck: {exc}"), 500

    eligible = {c.name for c in deck if engine.commander_eligible_card(c)}
    invalid = [n for n in commanders if n not in eligible]
    if invalid:
        return jsonify(error=f"not a legal commander in this deck: {', '.join(invalid)}"), 400

    tags = body.get("tags")
    playstyle = body.get("playstyle")

    meta = _load_deck_meta()
    entry = meta.setdefault(name, {})
    entry["commanders"] = commanders
    if isinstance(tags, list):
        # Same request the "Change commander" dialog sends the strategy
        # checkboxes in with -- saved per deck, right alongside the
        # commander, so it's never left pointing at another deck's tags.
        entry["tags"] = [str(t) for t in tags if isinstance(t, str) and t.strip()][:16]
    if isinstance(playstyle, dict):
        # Same per-deck scoping as tags (v4.77.0 "Play style" sliders / an
        # AI-authored scenario-file import -- see importJSON in index.html).
        # Unknown keys and out-of-range/non-numeric values are dropped
        # rather than rejecting the whole request; a partial dict (only one
        # slider) is intentional -- App/combat_model/playstyle.py::get()
        # defaults whatever is missing at simulation time.
        clean = {}
        for k in _PLAYSTYLE_KEYS:
            if k in playstyle:
                try:
                    clean[k] = max(0.0, min(100.0, float(playstyle[k])))
                except (TypeError, ValueError):
                    pass
        entry["playstyle"] = clean
    _save_deck_meta(meta)
    return jsonify(name=name, commanders=commanders, tags=entry.get("tags", []), playstyle=entry.get("playstyle", {}))


@app.get("/api/table-politics")
def get_table_politics():
    """v4.87.0 "Table" tab: current global table-politics settings (not
    per-deck -- these apply to the whole opponent table, every deck)."""
    section = engine.TABLE_DYNAMICS.get("table_politics", {}) or {}
    return jsonify({k: section.get(k, default) for k, default in _TABLE_POLITICS_DEFAULTS.items()})


@app.post("/api/table-politics")
def set_table_politics():
    """Persists straight into Data/Models/table_dynamics.json (only the
    table_politics block is touched; other calibration sections and the
    _comment/_comment_v487 rationale strings are carried over unchanged),
    and updates the live engine.TABLE_DYNAMICS immediately -- a running
    simulation started afterwards picks the new values up without a
    restart."""
    body = request.get_json(force=True, silent=True) or {}
    section = engine.TABLE_DYNAMICS.setdefault("table_politics", {})
    if "enabled" in body:
        section["enabled"] = bool(body["enabled"])
    if "target_mode" in body:
        mode = body["target_mode"]
        if mode not in _TABLE_POLITICS_TARGET_MODES:
            return jsonify(error=f"target_mode must be one of {_TABLE_POLITICS_TARGET_MODES}"), 400
        section["target_mode"] = mode
    for key, (lo, hi) in _TABLE_POLITICS_RANGES.items():
        if key not in body:
            continue
        try:
            section[key] = max(lo, min(hi, float(body[key])))
        except (TypeError, ValueError):
            return jsonify(error=f"{key} must be a number"), 400
    try:
        engine._TD_PATH.write_text(json.dumps(engine.TABLE_DYNAMICS, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"could not persist table_dynamics.json: {exc}"), 500
    return jsonify({k: section.get(k, d) for k, d in _TABLE_POLITICS_DEFAULTS.items()})


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
    import os
    if os.environ.get("PYTHONHASHSEED") != "0":
        print("Hinweis: PYTHONHASHSEED ist nicht 0 - derselbe Seed liefert zwischen zwei Programmstarts "
              "nicht exakt dieselben Zahlen. Start ueber Start_Urzas_Spearfishing_Guide.py setzt das automatisch.")
    print(f"Urza's Spearfishing Guide -- engine {engine.ENGINE_VERSION}")
    print(f"Serving on {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
