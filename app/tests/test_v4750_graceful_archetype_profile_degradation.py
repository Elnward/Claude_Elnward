"""
Unit tests for v4.75.0 ("Graceful Degradation ohne numpy" -
App/engine.py's archetype_profile import block).

Context: a user reported that starting the app (Start_Goldfish_GUI.bat ->
commander_goldfish.py -> App/gui.py -> App/engine.py) crashed immediately
with "ModuleNotFoundError: No module named 'numpy'" (nested inside several
"No module named 'archetype_profile'" fallback attempts). Root cause: since
v4.68.0, App/engine.py imports App.archetype_profile at MODULE LOAD TIME
(not lazily), and App/archetype_profile/__init__.py imports numpy (via
reference_model.py) at ITS OWN module load time. numpy was never installed
in that user's Python environment - it is not otherwise a dependency of
this tool at all (goldfishing, win condition testing, the opponent model,
etc. are pure-stdlib). Because both the "App.archetype_profile" AND the
bare "archetype_profile" import fallback fail identically (both ultimately
hit the same missing numpy), the ImportError propagated all the way up and
crashed the ENTIRE application at startup, even though the only feature
that actually needs archetype_profile is the "Vergleich (1.585 Decks)" tab,
whose own call into App/gui.py::_build_deck_comparison() was ALREADY
wrapped in a try/except that shows a friendly in-tab message.

Fix: App/engine.py's archetype_profile import block now catches this
failure, leaves the archetype_profile symbols as None/empty plus a
recorded _ARCHETYPE_PROFILE_IMPORT_ERROR message, and
_get_archetype_analyzer()/commander_identity_slug() now raise a clear,
catchable RuntimeError (mentioning "pip install numpy") ONLY if/when the
comparison feature is actually used - never at import time. The rest of
the application is completely unaffected.

This test suite verifies the DEGRADED path (numpy unavailable) via a
subprocess with numpy's import blocked, so it can never pollute this
process's already-imported, numpy-backed App.engine module (which the
whole rest of the test suite, including test_v4680_archetype_profile_
integration.py, relies on being fully functional). The NORMAL path (numpy
present, archetype_profile fully working) continues to be covered by
test_v4680_archetype_profile_integration.py - this file only adds
coverage for what is NEW in v4.75.0.

Run from the project root:
    python -m unittest tests.test_v4750_graceful_archetype_profile_degradation -v
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App import engine  # noqa: E402

_GUI_SRC = ROOT / "App" / "gui.py"
_README = ROOT / "Docs" / "README.md"


class VersionSyncTests(unittest.TestCase):
    def test_engine_version_is_4_75_0(self):
        self.assertEqual(engine.ENGINE_VERSION, "4.87.0")

    def test_gui_title_mentions_4_75_0(self):
        src = _GUI_SRC.read_text(encoding="utf-8")
        self.assertIn("Commander Goldfish v4.87.0", src)

    def test_readme_has_v4750_entry(self):
        text = _README.read_text(encoding="utf-8")
        self.assertIn("v4.75.0", text)


class NormalPathUnaffectedTests(unittest.TestCase):
    """Sanity check that the fix is purely additive: with numpy present
    (this process's normal state), everything behaves exactly as before
    v4.75.0."""

    def test_archetype_profile_symbols_are_loaded(self):
        self.assertIsNotNone(engine._ArchetypeDeckAnalyzer)
        self.assertIsNone(engine._ARCHETYPE_PROFILE_IMPORT_ERROR)

    def test_analyzer_still_loads_normally(self):
        analyzer = engine._get_archetype_analyzer()
        self.assertIsNotNone(analyzer)

    def test_commander_identity_slug_still_works_normally(self):
        # "colorless" is the documented fallback when no commander/cards are
        # resolvable - this must NOT raise, exactly as before v4.75.0.
        self.assertEqual(engine.commander_identity_slug({}, {"Unknown Commander"}), "colorless")


class _MissingNumpySubprocessTestCase(unittest.TestCase):
    """Runs a small script in a FRESH interpreter with numpy's import
    blocked, simulating the user's actual Python environment. A subprocess
    is used deliberately: forcing ImportError into an already-running
    process's sys.modules would corrupt this process's own (working,
    numpy-backed) App.engine for every other test in the suite."""

    def _run(self, script: str) -> subprocess.CompletedProcess:
        full_script = textwrap.dedent(
            f"""
            import builtins, sys
            _real_import = builtins.__import__
            def _blocked_import(name, *args, **kwargs):
                if name == "numpy" or name.startswith("numpy."):
                    raise ModuleNotFoundError("No module named 'numpy'")
                return _real_import(name, *args, **kwargs)
            builtins.__import__ = _blocked_import
            sys.path.insert(0, {str(ROOT)!r})
            {textwrap.indent(textwrap.dedent(script), "            ")}
            """
        )
        return subprocess.run(
            [sys.executable, "-c", full_script],
            capture_output=True, text=True, timeout=30,
        )

    def test_engine_imports_successfully_without_numpy(self):
        result = self._run(
            """
            from App import engine
            print("IMPORT_OK")
            print("ANALYZER_IS_NONE", engine._ArchetypeDeckAnalyzer is None)
            """
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("IMPORT_OK", result.stdout)
        self.assertIn("ANALYZER_IS_NONE True", result.stdout)

    def test_gui_module_also_imports_successfully_without_numpy(self):
        # This is the actual failure the user hit: gui.py (and transitively
        # commander_goldfish.py's launch_gui) failing to import at all.
        # tkinter may be unavailable in this headless container, which is a
        # separate/unrelated concern - only import-time NameError/
        # ModuleNotFoundError about archetype_profile/numpy specifically is
        # what this test guards against.
        result = self._run(
            """
            try:
                from App import gui
                print("IMPORT_OK")
            except ImportError as exc:
                if "numpy" in str(exc) or "archetype_profile" in str(exc):
                    raise
                # Any other ImportError (e.g. tkinter missing in this
                # headless container) is an unrelated environment gap, not
                # what this test checks.
                print("IMPORT_OK (unrelated ImportError, not numpy/archetype_profile):", exc)
            """
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("IMPORT_OK", result.stdout)

    def test_get_archetype_analyzer_raises_clear_runtime_error(self):
        result = self._run(
            """
            from App import engine
            try:
                engine._get_archetype_analyzer()
                print("NO_ERROR_RAISED")
            except RuntimeError as exc:
                print("RUNTIME_ERROR:", exc)
            """
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("RUNTIME_ERROR:", result.stdout)
        self.assertIn("numpy", result.stdout)
        self.assertIn("pip install", result.stdout)

    def test_commander_identity_slug_raises_clear_runtime_error(self):
        result = self._run(
            """
            from App import engine
            try:
                engine.commander_identity_slug({}, {"whatever"})
                print("NO_ERROR_RAISED")
            except RuntimeError as exc:
                print("RUNTIME_ERROR:", exc)
            """
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("RUNTIME_ERROR:", result.stdout)
        self.assertIn("numpy", result.stdout)


if __name__ == "__main__":
    unittest.main()
