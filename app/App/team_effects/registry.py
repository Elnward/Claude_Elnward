"""
Team-effect registry (v4.76.0, WP3): tribal/team pumps, Craterhoof-style ETB
finishers, X creature tutors and "Tap N untapped <Type> you control" costs.

Same design as App/keyword_library and App/mana_scaling: patterns live in
`definitions.json`; this module only matches Oracle lines and returns plain
parse results. It is engine-agnostic (no `import engine`); every state
change happens in engine.py's additive v4.76.0 block or in the keyword
library's `typed_pt_bonus` handler.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from ..mana_scaling.handlers import singular
except (ImportError, ValueError):  # engine.py run standalone from inside App/
    from mana_scaling.handlers import singular

_DEFINITIONS_PATH = Path(__file__).resolve().parent / "definitions.json"
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10}


@dataclass
class TeamEffectDefinition:
    id: str
    kind: str
    model_layer: str
    regex: "re.Pattern[str]"
    description_de: str
    extra: Dict[str, Any]


def _load(path: Path = _DEFINITIONS_PATH) -> Dict[str, TeamEffectDefinition]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for d in raw.get("patterns", []):
        extra = {k: v for k, v in d.items() if k not in {"id", "kind", "model_layer", "regex", "description_de"}}
        if "pump_regex" in extra:
            extra["pump_regex"] = re.compile(extra["pump_regex"])
        out[d["id"]] = TeamEffectDefinition(d["id"], d["kind"], d.get("model_layer", "simplified"),
                                            re.compile(d["regex"]), d.get("description_de", ""), extra)
    return out


DEFINITIONS: Dict[str, TeamEffectDefinition] = _load()


def reload() -> None:
    global DEFINITIONS
    DEFINITIONS = _load()


def _type_of(group: str) -> str:
    g = group.strip()
    if g == "creatures":
        return "creature"
    if g.endswith(" creatures"):
        return singular(g[: -len(" creatures")])
    return singular(g)


def _norm(ops: Any, line: str) -> str:
    return ops.strip_reminder_text(line).lower().strip()


def parse_pump(text: str) -> Optional[Tuple[str, float, List[str], bool]]:
    """Effect text (the part after the activation colon, or a whole spell /
    trigger line). -> (type, +N, keywords, other) or None."""
    low = text.lower().strip()
    if "for each" in low:
        return None
    m = DEFINITIONS["typed_pump_until_eot"].regex.search(low)
    if not m:
        return None
    kws = [k.strip() for k in (m.group(5) or "").split(" and ") if k.strip()]
    return _type_of(m.group(2)), float(m.group(3)), kws, bool(m.group(1))


def parse_anthem(line: str) -> Optional[Tuple[str, float, List[str], bool]]:
    low = line.lower().strip()
    if "for each" in low or "until end of turn" in low:
        return None
    m = DEFINITIONS["typed_anthem_static"].regex.search(low)
    if not m:
        return None
    kws = [m.group(5)] if m.group(5) else []
    return _type_of(m.group(2)), float(m.group(3)), kws, bool(m.group(1))


def spell_pump(ops: Any, oracle_text: str) -> Optional[Tuple[str, float, List[str], bool]]:
    """Whole-line pump without an activation cost (Overrun-shaped spell text)."""
    for line in ops.split_oracle_lines(oracle_text or ""):
        low = _norm(ops, line)
        if ":" in low or low.startswith(("when", "whenever", "at the beginning")):
            continue
        hit = parse_pump(low)
        if hit:
            return hit
    return None


def etb_team_pump(ops: Any, oracle_text: str) -> bool:
    d = DEFINITIONS["etb_team_pump_x_creatures"]
    return any(d.regex.search(_norm(ops, l)) for l in ops.split_oracle_lines(oracle_text or ""))


def x_creature_tutor(ops: Any, oracle_text: str) -> Optional[Dict[str, Any]]:
    d = DEFINITIONS["x_creature_tutor_to_battlefield"]
    low = _norm(ops, oracle_text or "").replace("\n", " ")
    m = d.regex.search(low)
    if not m:
        return None
    out: Dict[str, Any] = {"graveyard": bool(m.group(1)), "color": m.group(2) or ""}
    pm = d.extra["pump_regex"].search(low)
    if pm:
        out["pump_at"] = int(pm.group(1))
        out["pump_keyword"] = pm.group(2)
    return out


def tap_n_cost(ability_raw: str) -> Optional[Tuple[int, str]]:
    cost = ability_raw.split(":", 1)[0].lower() if ":" in ability_raw else ""
    m = DEFINITIONS["tap_n_untapped_cost"].regex.search(cost)
    if not m:
        return None
    word = m.group(1)
    n = NUMBER_WORDS.get(word) or (int(word) if word.isdigit() else 0)
    return (n, singular(m.group(2))) if n > 0 else None


def notes(ops: Any, oracle_text: str) -> List[str]:
    found = []
    for line in ops.split_oracle_lines(oracle_text or ""):
        low = _norm(ops, line)
        if ":" in low and parse_pump(low.split(":", 1)[1]):
            found.append("typed_pump_until_eot")          # activated pump
        if parse_anthem(low):
            found.append("typed_anthem_static")
        if DEFINITIONS["etb_team_pump_x_creatures"].regex.search(low):
            found.append("etb_team_pump_x_creatures")
        if tap_n_cost(low):
            found.append("tap_n_untapped_cost")
    if spell_pump(ops, oracle_text):
        found.append("typed_pump_until_eot")              # pump spell (Overrun)
    if x_creature_tutor(ops, oracle_text):
        found.append("x_creature_tutor_to_battlefield")
    return [f"team_effects:{i} ({DEFINITIONS[i].model_layer})" for i in dict.fromkeys(found)]
