"""
Structural guard for v4.37.0: App/engine.py must never accumulate dead
top-level function definitions again.

Background (see Docs/README.md v4.37.0 entry): the project's own
established convention is "last-definition-wins" - engine.py has been
edited over many versions by simply adding a NEW `def some_name(...):` at
the bottom rather than editing the existing one in place, so only the LAST
top-level definition of a given name is ever actually reachable (Python
keeps exactly one module-level binding per name). Found via ChatGPT
external review: two different things had been happening under this same
umbrella pattern, conflated together -

  1. A genuine, INTENTIONAL "wrapper chain": an older version is captured
     under a new alias name (e.g. `_V460_apply_payment_old = apply_payment`)
     immediately before being shadowed, and the new definition explicitly
     calls that alias - so the old code IS still reachable, on purpose, as
     part of the new version's own logic. This is fine and must stay.
  2. Plain, unreferenced DEAD CODE: an earlier definition simply gets
     shadowed by a later one with no capture at all - genuinely unreachable
     from the moment the later `def` executes, forever. v4.37.0 removed 42
     such definitions (1123 lines) after verifying, line by line, that
     nothing (no top-level assignment, no default-argument evaluation, no
     class-body attribute, no decorator) ever captured the shadowed value -
     see the removal script's analysis this changelog entry documents.

This test re-runs that same "is it captured before being shadowed" analysis
as a permanent guard, so an editor who adds a new `def some_name(...):`
lower in the file - shadowing an existing one without capturing it first -
gets a clear, named failure here instead of silently growing this file with
more unreachable code.

Run from the project root:
    python -m unittest tests.test_no_dead_top_level_definitions -v
"""
from __future__ import annotations

import ast
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENGINE_PATH = ROOT / "App" / "engine.py"


def _find_dead_definitions(source: str):
    """
    Returns a list of (name, lineno, end_lineno) for every top-level
    FunctionDef in `source` that is shadowed by a LATER top-level def of the
    same name WITHOUT ever being captured by a simple top-level
    `alias = name` assignment in between. The final (last) definition of
    each name is never "dead" - it's the live, reachable one.
    """
    tree = ast.parse(source)

    stmts = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            stmts.append((node.lineno, node.end_lineno, "def", node.name, None))
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            rhs_name = node.value.id if isinstance(node.value, ast.Name) else None
            stmts.append((node.lineno, node.end_lineno, "assign", node.targets[0].id, rhs_name))

    def_indices_by_name = defaultdict(list)
    for i, (lineno, end, kind, name, _rhs) in enumerate(stmts):
        if kind == "def":
            def_indices_by_name[name].append(i)

    captured_def_indices = set()
    last_def_index_for_name = {}
    for i, (lineno, end, kind, name, rhs) in enumerate(stmts):
        if kind == "def":
            last_def_index_for_name[name] = i
        elif kind == "assign" and rhs is not None and rhs in last_def_index_for_name:
            captured_def_indices.add(last_def_index_for_name[rhs])

    dead = []
    for name, indices in def_indices_by_name.items():
        for idx in indices[:-1]:  # every def except the last (live) one
            if idx not in captured_def_indices:
                lineno, end, _kind, _name, _rhs = stmts[idx]
                dead.append((name, lineno, end))
    return dead


class NoDeadTopLevelDefinitionsTests(unittest.TestCase):
    def test_engine_py_has_no_uncaptured_shadowed_definitions(self):
        source = ENGINE_PATH.read_text(encoding="utf-8")
        dead = _find_dead_definitions(source)
        if dead:
            details = "\n".join(f"  - {name} at line {lineno}-{end}" for name, lineno, end in sorted(dead, key=lambda x: x[1]))
            self.fail(
                f"Found {len(dead)} dead (shadowed-but-never-captured) top-level "
                f"function definition(s) in App/engine.py:\n{details}\n"
                "Either remove the dead code, or - if the old version is meant "
                "to still be reachable - capture it first with a plain top-level "
                "`_vX_name_old = name` assignment (the established wrapper-chain "
                "convention) before redefining it."
            )

    def test_the_detector_itself_flags_a_synthetic_dead_definition(self):
        # Sanity check on the detector: a plain shadow with no capture at
        # all must be flagged as dead.
        source = (
            "def foo():\n"
            "    return 1\n"
            "\n"
            "def foo():\n"
            "    return 2\n"
        )
        dead = _find_dead_definitions(source)
        self.assertEqual(len(dead), 1)
        self.assertEqual(dead[0][0], "foo")
        self.assertEqual(dead[0][1], 1)

    def test_the_detector_does_not_flag_a_captured_wrapper_chain(self):
        # The established, intentional convention: capture the old value
        # under an alias, then call it from the new definition. Must NOT be
        # flagged as dead.
        source = (
            "def foo():\n"
            "    return 1\n"
            "\n"
            "_old_foo = foo\n"
            "\n"
            "def foo():\n"
            "    return _old_foo() + 1\n"
        )
        dead = _find_dead_definitions(source)
        self.assertEqual(dead, [])

    def test_the_detector_never_flags_the_final_live_definition(self):
        source = (
            "def foo():\n"
            "    return 1\n"
            "\n"
            "def foo():\n"
            "    return 2\n"
            "\n"
            "def foo():\n"
            "    return 3\n"
        )
        dead = _find_dead_definitions(source)
        # Both earlier ones (uncaptured) are dead; the last is never listed.
        self.assertEqual(len(dead), 2)
        self.assertNotIn(3, [lineno for _n, lineno, _e in dead])


if __name__ == "__main__":
    unittest.main()
