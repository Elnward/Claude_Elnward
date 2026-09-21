"""
Keyword / mechanic registry.

Purpose (see project handoff, "Keyword-Bibliothek"):
Instead of a growing if/elif chain in the engine for every recognized Oracle-text
action, each mechanic is described declaratively in `definitions.json` and resolved
at runtime through a small handler registry. Adding a new, mechanically-identical
mechanic (e.g. a new set's keyword that behaves like `connive`) therefore requires
ONLY a new JSON entry pointing at the existing handler - no engine.py changes.

Design note on "ops":
This module is deliberately engine-agnostic (no `import engine`), to avoid a circular
import (engine.py is the one that imports this package) and to keep the library
reusable/unit-testable on its own. The caller (engine.py) passes an `ops` object
that exposes the actual state-mutating primitives (gain_life, draw_cards, scry, ...).
In practice `ops` is simply the engine module itself.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_DEFINITIONS_PATH = Path(__file__).resolve().parent / "definitions.json"

HandlerFunc = Callable[..., bool]


@dataclass
class KeywordDefinition:
    id: str
    category: str                 # "action" (from `keywords`) 
    model_layer: str              # exact / simplified / probabilistic / review
    description_de: str
    handler: str
    expects: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)


@dataclass
class StaticKeywordDefinition:
    id: str
    model_layer: str
    description_de: str


_HANDLERS: Dict[str, HandlerFunc] = {}


def register_handler(name: str):
    """Decorator: register a handler function under `name` (matches 'handler' in JSON)."""
    def _wrap(fn: HandlerFunc) -> HandlerFunc:
        if name in _HANDLERS and _HANDLERS[name] is not fn:
            raise ValueError(f"keyword_library: handler '{name}' already registered")
        _HANDLERS[name] = fn
        return fn
    return _wrap


def _load_definitions(path: Path = _DEFINITIONS_PATH) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw


_RAW = _load_definitions()


def _build_keywords_by_id(raw: Dict[str, Any]) -> Dict[str, KeywordDefinition]:
    return {
        d["id"]: KeywordDefinition(
            id=d["id"],
            category=d.get("category", "action"),
            model_layer=d.get("model_layer", "review"),
            description_de=d.get("description_de", ""),
            handler=d["handler"],
            expects=d.get("expects", []),
            aliases=d.get("aliases", []),
        )
        for d in raw.get("keywords", [])
    }


def _build_static_keywords_by_id(raw: Dict[str, Any]) -> Dict[str, StaticKeywordDefinition]:
    return {
        d["id"]: StaticKeywordDefinition(
            id=d["id"],
            model_layer=d.get("model_layer", "exact"),
            description_de=d.get("description_de", ""),
        )
        for d in raw.get("static_keywords", [])
    }


def _build_alias_index(by_id: Dict[str, KeywordDefinition]) -> Dict[str, KeywordDefinition]:
    """
    v4.36.0: `aliases` was parsed from definitions.json into every
    KeywordDefinition but never consulted anywhere - a "declarative" field
    with zero actual effect (found via ChatGPT external review). This maps
    each declared alias to its canonical KeywordDefinition so a
    SemanticAction.kind spelled as an alias resolves exactly like the
    canonical id - e.g. a new set's alternate name for an existing
    mechanically-identical keyword needs only a `definitions.json` entry
    ("aliases": ["new_name"]), no engine.py or handlers.py change, matching
    this module's own stated design goal for the `handler` field.

    An alias that collides with an existing canonical id, or with another
    keyword's alias, is ignored (first-registered wins) rather than
    silently letting one definitions.json entry shadow another's real id -
    same caution as register_handler's own "already registered" guard.
    """
    aliases: Dict[str, KeywordDefinition] = {}
    for definition in by_id.values():
        for alias in definition.aliases:
            if alias in by_id or alias in aliases:
                continue
            aliases[alias] = definition
    return aliases


KEYWORDS_BY_ID: Dict[str, KeywordDefinition] = _build_keywords_by_id(_RAW)
STATIC_KEYWORDS_BY_ID: Dict[str, StaticKeywordDefinition] = _build_static_keywords_by_id(_RAW)
_ALIASES_BY_ID: Dict[str, KeywordDefinition] = _build_alias_index(KEYWORDS_BY_ID)

# v4.36.0: the SemanticAction-dataclass default value for each `expects`
# field name that has an unambiguous, checkable "still at its default"
# sentinel (see _expects_gaps below). "target" is deliberately NOT listed
# here - it needs its own dual check (see _expects_gaps's docstring).
_EXPECTS_DEFAULT_SENTINELS: Dict[str, Any] = {
    "amount": 0.0,
    "keyword": "",
    "token": "",
}


def _expects_gaps(definition: KeywordDefinition, action: Any, target: Any) -> List[str]:
    """
    v4.36.0: `expects` was parsed from definitions.json into every
    KeywordDefinition but never consulted anywhere either - every handler
    call went ahead regardless of whether the action actually carried the
    fields its own handler needs, so a future parsing gap (an action kind
    that forgets to set `amount`) would silently call the handler with an
    inert default instead of surfacing anywhere (this is the same shape of
    bug already found and fixed directly at the parser for specific fields
    in v4.26.0/v4.30.0 - this closes the general case).

    Returns the `expects` field names that still sit at their SemanticAction
    dataclass default, i.e. probably unset rather than genuinely zero/empty
    - a non-fatal signal, not a hard requirement (some real card text could
    in principle produce a genuinely-zero amount), so callers should record
    a diagnostic and still run the handler, never block execution on this.

    "target" is checked against BOTH the action's own `target` string field
    (some handlers, e.g. opponent_life_loss, read that name directly to
    choose between "each opponent" and a single opponent) AND the resolved
    target Permanent parameter (most handlers, e.g. plus1_counter, actually
    need this instead) - satisfied if either is present, since which one a
    given handler cares about isn't recorded separately in definitions.json.
    """
    gaps: List[str] = []
    for field_name in definition.expects:
        if field_name == "target":
            if not getattr(action, "target", "") and target is None:
                gaps.append(field_name)
            continue
        sentinel = _EXPECTS_DEFAULT_SENTINELS.get(field_name)
        if sentinel is None:
            continue  # not a field this check knows how to evaluate - skip, don't guess
        if getattr(action, field_name, sentinel) == sentinel:
            gaps.append(field_name)
    return gaps


def get_definition(kind: str) -> Optional[KeywordDefinition]:
    return KEYWORDS_BY_ID.get(kind) or _ALIASES_BY_ID.get(kind)


def is_known(kind: str) -> bool:
    return kind in KEYWORDS_BY_ID or kind in _ALIASES_BY_ID


def list_keywords() -> List[str]:
    return sorted(KEYWORDS_BY_ID)


def list_static_keywords() -> List[str]:
    return sorted(STATIC_KEYWORDS_BY_ID)


def reload() -> None:
    """Re-read definitions.json at runtime (useful for editing definitions without restart)."""
    global _RAW, KEYWORDS_BY_ID, STATIC_KEYWORDS_BY_ID, _ALIASES_BY_ID
    _RAW = _load_definitions()
    KEYWORDS_BY_ID = _build_keywords_by_id(_RAW)
    STATIC_KEYWORDS_BY_ID = _build_static_keywords_by_id(_RAW)
    _ALIASES_BY_ID = _build_alias_index(KEYWORDS_BY_ID)


def resolve_action(ops: Any, state: Any, strategy: Any, source: Any, action: Any, *, target: Any = None) -> bool:
    """
    Generic dispatcher, replaces the old engine.py if/elif chain in execute_semantic_action.

    Returns False (not True with no effect) whenever the action's kind is unknown or its
    handler is not registered, so callers can log/count unhandled mechanics instead of
    silently doing nothing.

    v4.36.0: also records a non-fatal `keyword_expects_gap:<id>:<fields>`
    engine metric (via `ops.record_engine_metric`, when available) whenever
    the action is missing a field its own handler `expects` - purely a
    diagnostic, never blocks the handler call, so this cannot change any
    currently-working card's behavior.
    """
    definition = get_definition(getattr(action, "kind", None))
    if definition is None:
        return False
    handler = _HANDLERS.get(definition.handler)
    if handler is None:
        return False
    gaps = _expects_gaps(definition, action, target)
    if gaps and hasattr(ops, "record_engine_metric"):
        ops.record_engine_metric(
            state, f"keyword_expects_gap:{definition.id}:{','.join(gaps)}",
        )
    return bool(handler(ops, state, strategy, source, action, target))


# Import handlers for their registration side-effects.
from . import handlers  # noqa: E402,F401
