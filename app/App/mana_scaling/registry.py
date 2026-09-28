"""
Scaling-mana registry (v4.76.0, WP1).

Same design as App/keyword_library: mechanics are described declaratively in
`definitions.json` and dispatched to a small set of handlers. The module is
engine-agnostic (no `import engine`); engine.py passes itself as `ops`.

Public entry points:
    resolve_mana_options(ops, permanent, state, strategy) -> Optional[List[Counter]]
        None  = no scaling pattern on this card -> caller keeps its old result
        []    = pattern recognized but currently produces nothing (e.g. 0 Elves)
        [...] = one Counter per alternative output of ONE activation
    match_card(oracle_text) -> List[ScalingManaDefinition]
        which patterns a card carries (for the model-coverage report)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_DEFINITIONS_PATH = Path(__file__).resolve().parent / "definitions.json"

HandlerFunc = Callable[..., Optional[list]]
_HANDLERS: Dict[str, HandlerFunc] = {}


@dataclass
class ScalingManaDefinition:
    id: str
    model_layer: str
    regex: "re.Pattern[str]"
    handler: str
    scope: str
    description_de: str


def register_handler(name: str):
    def _wrap(fn: HandlerFunc) -> HandlerFunc:
        if name in _HANDLERS and _HANDLERS[name] is not fn:
            raise ValueError(f"mana_scaling: handler '{name}' already registered")
        _HANDLERS[name] = fn
        return fn
    return _wrap


def _load(path: Path = _DEFINITIONS_PATH) -> List[ScalingManaDefinition]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        ScalingManaDefinition(
            id=d["id"],
            model_layer=d.get("model_layer", "simplified"),
            regex=re.compile(d["regex"]),
            handler=d["handler"],
            scope=d.get("scope", "you_control"),
            description_de=d.get("description_de", ""),
        )
        for d in raw.get("patterns", [])
    ]


DEFINITIONS: List[ScalingManaDefinition] = _load()


def reload() -> None:
    global DEFINITIONS
    DEFINITIONS = _load()


def _lines(ops: Any, oracle_text: str) -> List[str]:
    return [ops.strip_reminder_text(line).lower().strip() for line in ops.split_oracle_lines(oracle_text or "")]


def match_card(ops: Any, oracle_text: str) -> List[ScalingManaDefinition]:
    found = []
    for line in _lines(ops, oracle_text):
        for d in DEFINITIONS:
            if d.regex.search(line) and d not in found:
                found.append(d)
    return found


def text_without_scaling_lines(ops: Any, oracle_text: str) -> str:
    """The card's Oracle text minus every line a scaling pattern handles --
    so the engine's generic parser can still read the card's OTHER mana
    lines without re-reading a scaling line as a flat 1-mana ability."""
    keep = []
    for raw in ops.split_oracle_lines(oracle_text or ""):
        low = ops.strip_reminder_text(raw).lower().strip()
        if not any(d.regex.search(low) for d in DEFINITIONS):
            keep.append(raw)
    return "\n".join(keep)


def resolve_mana_options(ops: Any, permanent: Any, state: Any, strategy: Any) -> Optional[list]:
    """First matching pattern wins per line; results of several matching
    lines are offered as alternatives (a permanent activates one mana
    ability per tap)."""
    options: Optional[list] = None
    for line in _lines(ops, permanent.card.oracle_text):
        for d in DEFINITIONS:
            m = d.regex.search(line)
            if not m:
                continue
            handler = _HANDLERS.get(d.handler)
            if handler is None:
                continue
            out = handler(ops, permanent, state, strategy, d, m)
            if out is None:
                continue
            options = (options or []) + list(out)
            break
    return options
