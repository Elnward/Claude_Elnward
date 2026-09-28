"""
Trainingsdeck-Benchmark (v4.83.0) - Konsistenzpruefung Engine <-> Trainingsdaten.

Idee: die abstrakten Gegner-Sitze des Advanced-Modells sind aus den echten
EDHREC-Durchschnittsdecks abgeleitet ("Training data"). Laesst man genau
solche Decks als TESTDECK gegen drei zufaellige Bracket-3-Sitze spielen,
muss bei einem fairen Vierertisch im Mittel ~25 % Siegquote herauskommen
(ueber ausgespielte Partien). Weicht der Wert stark ab, ist die Engine
nicht mit ihren eigenen Lehrdaten im Einklang - genau so wurde der
v4.83.0-Fehler gefunden (vorher 0,6 % Siege).

Nur lokale Dateien (deck_cards_slim.csv, unique_cards_enriched.csv aus dem
manuell gepflegten Training-data-Ordner) - KEIN Zugriff auf EDHREC oder
Scryfall (offline=True).

Aufruf (aus dem app-Ordner):
    python -m App.benchmark.training_deck_benchmark --training-dir "../Training data" --decks 40 --runs 50 --turns 20
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import csv
import io
import json
import random
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TAGMAP = {"Tokens": "tokens", "Aggro": "aggro", "Combo": "combo", "+1/+1 Counters": "counters", "Control": "control",
          "Artifacts": "artifacts", "Aristocrats": "aristocrats", "Lifegain": "lifegain", "Spellslinger": "spellslinger",
          "Voltron": "voltron", "Enchantress": "enchantress", "Graveyard": "graveyard", "Reanimator": "graveyard",
          "Mill": "mill", "Lands Matter": "lands", "Landfall": "lands", "Equipment": "voltron", "Burn": "aggro"}
BASIC = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G", "Wastes": "C"}


def _ci(c: dict) -> list:
    s = set(re.findall(r"\{([WUBRG])(?:/[WUBRGP])?\}", (c.get("mana_cost") or "") + " " + (c.get("oracle_text") or "")))
    s |= {x for x in (c.get("colors") or "") if x in "WUBRG"}
    return sorted(s)


def _produced(c: dict) -> list:
    o, out = c.get("oracle_text") or "", set()
    for m in re.finditer(r"[Aa]dd ([^.]*)", o):
        seg = m.group(1)
        out |= set(re.findall(r"\{([WUBRGC])\}", seg))
        if "any color" in seg or "any one color" in seg or "one mana of any" in seg:
            out |= set("WUBRG")
    for b, col in BASIC.items():
        if b in (c.get("type_line") or ""):
            out.add(col)
    return sorted(out)


def _dfc_oracle(c: dict) -> str:
    """unique_cards_enriched.csv schreibt DFCs als 'Name A: text\n\nName B: text'.
    Scryfall-Format der Engine: 'text A\n//\ntext B' (ohne Namenspraefixe)."""
    o = c.get("oracle_text") or ""
    if " // " not in (c.get("type_line") or "") or "\n\n" not in o:
        return o
    faces = []
    names = [n.strip() for n in (c.get("card_name") or "").split(" // ")]
    for part in o.split("\n\n"):
        for n in names:
            if part.startswith(n + ": "):
                part = part[len(n) + 2:]
                break
        faces.append(part)
    return "\n//\n".join(faces)

def _faces_for(c: dict):
    """Synthetische Scryfall-card_faces/layout fuer doppelseitige Karten aus
    unique_cards_enriched.csv (dort ohne Layout-Angabe): Land-Rueckseite oder
    zwei Manakosten -> modal_dfc, Adventure -> keine Faces, sonst transform."""
    t = c.get("type_line") or ""
    if " // " not in t or "Adventure" in t:
        return None, None
    names = [n.strip() for n in (c.get("card_name") or "").split(" // ")]
    types = [x.strip() for x in t.split(" // ")]
    costs = [x.strip() for x in (c.get("mana_cost") or "").split(" // ")] + ["", ""]
    texts = _dfc_oracle(c).split("\n//\n") + ["", ""]
    if len(names) < 2 or len(types) < 2:
        return None, None
    layout = "modal_dfc" if (("Land" in types[1] and "Land" not in types[0]) or costs[1]) else "transform"
    faces = []
    for i in range(2):
        faces.append({"name": names[i], "mana_cost": costs[i], "type_line": types[i], "oracle_text": texts[i],
                      "power": (c.get("power") or None) if i == 0 else None,
                      "toughness": (c.get("toughness") or None) if i == 0 else None})
    return layout, faces



def build_sample(training_dir: Path, out_dir: Path, n: int, seed: int, base_cache: dict) -> list:
    rows = list(csv.DictReader(open(training_dir / "deck_cards_slim.csv", encoding="utf-8")))
    decks = collections.defaultdict(list)
    for r in rows:
        decks[(r["identity_slug"], r["commander_name"], r["tag"])].append(r)
    cards = {r["card_name"]: r for r in csv.DictReader(open(training_dir / "unique_cards_enriched.csv", encoding="utf-8"))}
    chosen = random.Random(seed).sample(sorted(decks), min(n, len(decks)))
    (out_dir / "decks").mkdir(parents=True, exist_ok=True)
    cache, manifest = {}, []
    for key in chosen:
        _slug, cmd, tag = key
        cmds = [x.strip() for x in cmd.split(" // ")]
        lines = [f'{r["quantity"]} {r["card_name"]}' for r in decks[key] if r["is_commander"] != "1"]
        fname = re.sub(r"[^A-Za-z0-9]+", "_", f"{cmd}_{tag}")[:60]
        (out_dir / "decks" / f"{fname}.txt").write_text("\n".join(lines) + "\n\n" + "\n".join("1 " + c for c in cmds) + "\n", encoding="utf-8")
        manifest.append({"file": fname, "commander": cmds, "tag": tag})
        for name in [r["card_name"] for r in decks[key]] + cmds:
            k = "name:" + name.casefold()
            if k in cache:
                continue
            if k in base_cache:
                cache[k] = base_cache[k]
                continue
            c = cards.get(name)
            if not c:
                continue
            cache[k] = {"object": "card", "name": name, "mana_cost": (c["mana_cost"] or "").split(" // ")[0], "cmc": float(c["cmc"] or 0),
                        "type_line": c["type_line"].split(" // ")[0], "oracle_text": _dfc_oracle(c),
                        "colors": [x for x in (c["colors"] or "") if x in "WUBRG"], "color_identity": _ci(c),
                        "keywords": [x.strip() for x in re.split(r"[|,;]", c["keywords"] or "") if x.strip()],
                        "produced_mana": _produced(c), "power": c["power"] or None, "toughness": c["toughness"] or None,
                        "set": "", "collector_number": ""}
            _lay, _faces = _faces_for(c)
            if _faces:
                cache[k]["layout"] = _lay
                cache[k]["card_faces"] = _faces
    (out_dir / "cache.json").write_text(json.dumps(cache), encoding="utf-8")
    return manifest


def run_benchmark(training_dir: Path, *, decks: int = 40, runs: int = 50, turns: int = 20, seed: int = 20260926,
                  base_cache_path: Path = None) -> dict:
    import App.engine as engine
    base_cache = {}
    if base_cache_path and base_cache_path.exists():
        base_cache = json.loads(base_cache_path.read_text(encoding="utf-8"))
    work = Path(tempfile.mkdtemp(prefix="cg_benchmark_"))
    try:
        manifest = build_sample(training_dir, work, decks, seed, base_cache)
        results = []
        for m in manifest:
            seats = [{"strategy": "?", "colors": "?", "bracket": 3} for _ in range(3)]
            with contextlib.redirect_stdout(io.StringIO()):
                r = engine.run_pipeline_v440(
                    deck_file=work / "decks" / f"{m['file']}.txt", commander_names=m["commander"], runs=runs, turns=turns,
                    seed=1, strategy_tags={TAGMAP[m["tag"]]} if m["tag"] in TAGMAP else set(), opponent_profile="random",
                    scenarios=[], cache_path=work / "cache.json", offline=True, output_root=work / "out" / m["file"],
                    advanced_opponent_model=True, advanced_opponent_seats=seats)
            o = r["summary"]["outcomes"]
            results.append({"deck": m["file"], "tag": m["tag"], "win_pct": o["win_by_turn_limit_pct"],
                            "loss_pct": o["loss_by_turn_limit_pct"]})
            print(f"  {m['file'][:48]:48} win {o['win_by_turn_limit_pct']:5.1f}  loss {o['loss_by_turn_limit_pct']:5.1f}", flush=True)
        n = max(1, len(results))
        win = sum(x["win_pct"] for x in results) / n
        loss = sum(x["loss_pct"] for x in results) / n
        return {"engine_version": engine.ENGINE_VERSION, "decks": len(results), "runs_per_deck": runs, "turns": turns,
                "mean_win_pct": round(win, 2), "mean_loss_pct": round(loss, 2),
                "win_share_of_decided_pct": round(100.0 * win / max(1e-9, win + loss), 2),
                "expected_fair_table_pct": 25.0, "per_deck": results}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Trainingsdeck-Benchmark (Engine <-> Lehrdaten)")
    ap.add_argument("--training-dir", type=Path, required=True)
    ap.add_argument("--decks", type=int, default=40)
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--turns", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260926)
    ap.add_argument("--cache", type=Path, default=ROOT / "App" / ".scryfall_card_cache_v4.json")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    res = run_benchmark(a.training_dir, decks=a.decks, runs=a.runs, turns=a.turns, seed=a.seed, base_cache_path=a.cache)
    print(f"\nMittel: {res['mean_win_pct']:.1f} % Siege, {res['mean_loss_pct']:.1f} % Niederlagen, "
          f"{res['win_share_of_decided_pct']:.1f} % der entschiedenen Partien (fairer Tisch: 25 %)")
    if a.out:
        a.out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
