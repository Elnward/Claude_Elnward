"""
Scenario predicate registry — the "derived" block of Scenario-Schema v4.4.

Mirrors App/keyword_library's pattern: declarative metadata in definitions.json,
implementation in handlers.py, dispatch through a small registry here. Deliberately
engine-agnostic (no `import engine`) to avoid a circular import; the caller passes
an `ops` object (in practice the engine module) exposing whatever primitives a
predicate needs (available_mana_value, best_x_plan, x_effect_metrics, ...).

Evaluation result is a three-way PredicateResult, not a bare bool:
  - satisfied=True/False  -> normal, confident answer
  - computable=False      -> predicate type is declared but not yet implemented
                              (e.g. commander_damage_lethal before WP6/7), OR the
                              named card/target could not be resolved in this state.
A scenario's overall match must NOT silently treat "not computable" as False-forever
without saying so — callers should surface `computable=False` distinctly (e.g. in
Win-Condition reporting as "not modeled yet") rather than reporting a clean miss.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_DEFINITIONS_PATH = Path(__file__).resolve().parent / "definitions.json"

PredicateFunc = Callable[..., "PredicateResult"]


@dataclass
class PredicateResult:
    satisfied: bool
    computable: bool = True
    detail: str = ""
    # v4.15.7 (task #18, "derived-Teilkredit"): optional 0..1 "how close"
    # score, set BY THE HANDLER ITSELF when it can cheaply compute one (e.g.
    # opponent_life_at_or_below already has both the current life and the
    # threshold on hand). None means "no partial-credit signal available" -
    # effective_progress then falls back to the binary satisfied/not
    # reading, so every existing handler stays correct by default without
    # having to opt in. This keeps the "how close" logic living in each
    # handler (the only place that actually knows it), rather than
    # reimplemented in scenario_feasibility - the exact duplication/drift
    # risk the pre-v4.15.7 "deliberately simple, binary-only" note warned
    # about.
    progress: Optional[float] = None

    @staticmethod
    def not_computable(reason: str) -> "PredicateResult":
        return PredicateResult(satisfied=False, computable=False, detail=reason)

    @property
    def effective_progress(self) -> float:
        if self.progress is not None:
            return max(0.0, min(1.0, float(self.progress)))
        return 1.0 if self.satisfied else 0.0


@dataclass
class PredicateDefinition:
    id: str
    model_layer: str
    description_de: str
    params: Dict[str, str] = field(default_factory=dict)
    handler: Optional[str] = None


_HANDLERS: Dict[str, PredicateFunc] = {}


def register_predicate(name: str):
    """Decorator: register a predicate handler under `name` (matches 'handler' in JSON)."""
    def _wrap(fn: PredicateFunc) -> PredicateFunc:
        if name in _HANDLERS and _HANDLERS[name] is not fn:
            raise ValueError(f"scenario_predicates: handler '{name}' already registered")
        _HANDLERS[name] = fn
        return fn
    return _wrap


def _load(path: Path = _DEFINITIONS_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_RAW = _load()

PREDICATES_BY_ID: Dict[str, PredicateDefinition] = {
    d["id"]: PredicateDefinition(
        id=d["id"], model_layer=d.get("model_layer", "review"),
        description_de=d.get("description_de", ""), params=d.get("params", {}),
        handler=d.get("handler"),
    )
    for d in _RAW.get("predicates", [])
}


def get_definition(predicate_id: str) -> Optional[PredicateDefinition]:
    return PREDICATES_BY_ID.get(predicate_id)


def list_predicates() -> List[str]:
    return sorted(PREDICATES_BY_ID)


def list_implemented_predicates() -> List[str]:
    return sorted(pid for pid, d in PREDICATES_BY_ID.items() if d.handler)


def evaluate(ops: Any, predicate_type: str, params: Dict[str, Any], state: Any, strategy: Any = None) -> PredicateResult:
    """Evaluate one 'derived' entry. Never raises for unknown/unimplemented types."""
    definition = PREDICATES_BY_ID.get(predicate_type)
    if definition is None:
        return PredicateResult.not_computable(f"unknown predicate type '{predicate_type}'")
    if not definition.handler:
        return PredicateResult.not_computable(
            f"predicate '{predicate_type}' is declared but not yet implemented "
            f"(model_layer={definition.model_layer})"
        )
    handler = _HANDLERS.get(definition.handler)
    if handler is None:
        return PredicateResult.not_computable(
            f"predicate '{predicate_type}' references unregistered handler '{definition.handler}'"
        )
    try:
        return handler(ops, params or {}, state, strategy)
    except Exception as exc:  # a malformed scenario must not crash a whole run
        return PredicateResult.not_computable(f"error evaluating '{predicate_type}': {exc}")


def evaluate_all(ops: Any, derived: List[Dict[str, Any]], state: Any, strategy: Any = None) -> "DerivedEvaluation":
    """AND-combine every 'derived' entry of a scenario. See DerivedEvaluation for the result shape."""
    results = [
        evaluate(ops, entry.get("type", ""), entry.get("params", {}), state, strategy)
        for entry in (derived or [])
    ]
    all_computable = all(r.computable for r in results)
    all_satisfied = all(r.satisfied for r in results)
    return DerivedEvaluation(
        satisfied=all_satisfied if all_computable else False,
        computable=all_computable,
        results=results,
    )


@dataclass
class DerivedEvaluation:
    satisfied: bool
    computable: bool
    results: List[PredicateResult]


# Import handlers for their registration side-effects.
from . import handlers  # noqa: E402,F401
