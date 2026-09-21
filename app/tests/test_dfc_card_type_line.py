"""
Unit tests for v4.34.0: `card_from_scryfall` must give a double-faced/
Adventure/modal card its FRONT face's type_line, not the top-level
"Front // Back" combined string Scryfall returns for any card with
`card_faces`.

Found via ChatGPT external review (see Docs/README.md v4.34.0 entry).
Reproduced on the live pre-fix code: `type_line = obj.get("type_line") or
" // ".join(...)` always found Scryfall's own top-level combined type_line
first (it is populated for every card_faces layout: transform, modal DFC,
and Adventure), so it never even reached its own fallback. Card.is_creature/
is_sorcery/is_planeswalker/etc. (App/engine.py) are plain substring checks
on type_line, so ANY card with card_faces ended up with every one of its
faces' types simultaneously true for the entire game - this engine has no
in-game transform tracking (see index_scryfall_cards' own docstring), so a
permanent must resolve to exactly the front face's type, the same face
power/toughness/loyalty/defense already fall back to.

Uses two real cards actually present in this project's own Scryfall cache
(App/.scryfall_card_cache_v4.json) - "Gloin the Mighty // Easy Pickings" (a
real Adventure card: creature front, sorcery back) demonstrates the bug with
data already in this project, not a hypothetical. A second, synthetic-but-
evidence-based fixture models Nicol Bolas, the Ravager // Nicol Bolas, the
Arisen (confirmed against Scryfall/mtg.wtf: front "Legendary Creature - Elder
Dragon" 4/4, back "Legendary Planeswalker - Bolas" loyalty 7) - not in this
project's cache, but the single clearest real-world case of the two-flags-
at-once bug (is_creature AND is_planeswalker both true), since it swaps
whole card TYPES across faces rather than just adding a spell type.

Run from the project root:
    python -m unittest tests.test_dfc_card_type_line -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import App.engine as engine  # noqa: E402

_SCRYFALL_CACHE_PATH = ROOT / "App" / ".scryfall_card_cache_v4.json"


def _load_real_scryfall_obj(name: str) -> dict:
    with _SCRYFALL_CACHE_PATH.open("r", encoding="utf-8") as f:
        cache = json.load(f)
    for obj in cache.values():
        if isinstance(obj, dict) and obj.get("name") == name:
            return obj
    raise AssertionError(f"{name!r} not found in {_SCRYFALL_CACHE_PATH}")


# Nicol Bolas, the Ravager // Nicol Bolas, the Arisen (M19 #218 / PJ21 #9).
# Front face: "Legendary Creature - Elder Dragon", {1}{U}{B}{R}, 4/4.
# Back face: "Legendary Planeswalker - Bolas", loyalty 7.
# Confirmed against Scryfall/mtg.wtf - shaped to match Scryfall's own real
# /cards/collection response schema (top-level combined type_line + a
# card_faces list with each face's own type_line/power/toughness/loyalty).
NICOL_BOLAS_OBJ = {
    "name": "Nicol Bolas, the Ravager // Nicol Bolas, the Arisen",
    "set": "m19",
    "collector_number": "218",
    "layout": "transform",
    "mana_cost": "{1}{U}{B}{R}",
    "cmc": 4.0,
    "type_line": "Legendary Creature — Elder Dragon // Legendary Planeswalker — Bolas",
    "color_identity": ["U", "B", "R"],
    "card_faces": [
        {
            "name": "Nicol Bolas, the Ravager",
            "mana_cost": "{1}{U}{B}{R}",
            "type_line": "Legendary Creature — Elder Dragon",
            "oracle_text": (
                "Flying\n"
                "When Nicol Bolas, the Ravager enters the battlefield, each opponent discards a card.\n"
                "{4}{U}{B}{R}: Exile Nicol Bolas, then return him to the battlefield transformed "
                "under his owner's control. Activate only as a sorcery."
            ),
            "power": "4",
            "toughness": "4",
        },
        {
            "name": "Nicol Bolas, the Arisen",
            "type_line": "Legendary Planeswalker — Bolas",
            "oracle_text": (
                "+2: Draw two cards.\n"
                "-3: Nicol Bolas, the Arisen deals 10 damage to target creature or planeswalker.\n"
                "-4: Put target creature or planeswalker card from a graveyard onto the battlefield "
                "under your control.\n"
                "-12: Exile all but the bottom card of target player's library."
            ),
            "loyalty": "7",
        },
    ],
}


class DoubleFacedCardResolvesToFrontFaceTypeTests(unittest.TestCase):
    def test_real_project_adventure_card_is_only_a_creature_not_also_a_sorcery(self):
        obj = _load_real_scryfall_obj("Glóin the Mighty // Easy Pickings")
        # Sanity check: confirm the fixture actually has the shape the bug
        # depends on (a top-level combined type_line spanning two types).
        self.assertIn("Sorcery", obj["type_line"])
        entry = engine.DeckEntry(name=obj["name"])
        card = engine.card_from_scryfall(entry, obj, commander_name=None)

        self.assertEqual(card.type_line, "Legendary Creature — Dwarf Warrior")
        self.assertTrue(card.is_creature)
        self.assertFalse(
            card.is_sorcery,
            "Gloin the Mighty is a creature on the battlefield - it must not "
            "also register as a Sorcery just because its Adventure back "
            "face is one",
        )
        # Front-face power/toughness must still resolve correctly (unrelated
        # existing fallback logic - confirms this fix didn't disturb it).
        self.assertEqual(card.power, 4.0)
        self.assertEqual(card.toughness, 3.0)

    def test_nicol_bolas_is_only_a_creature_while_its_back_face_is_ignored(self):
        entry = engine.DeckEntry(name=NICOL_BOLAS_OBJ["name"])
        card = engine.card_from_scryfall(entry, NICOL_BOLAS_OBJ, commander_name=None)

        self.assertEqual(card.type_line, "Legendary Creature — Elder Dragon")
        self.assertTrue(card.is_creature)
        self.assertFalse(
            card.is_planeswalker,
            "a creature-front DFC must not simultaneously be a planeswalker "
            "just because its back face is one - this engine never models "
            "the in-game transform",
        )
        self.assertEqual(card.power, 4.0)
        self.assertEqual(card.toughness, 4.0)
        # Loyalty must NOT leak from the back face onto a card whose (front,
        # in-play) type isn't even a planeswalker.
        self.assertIsNone(card.loyalty)

    def test_oracle_text_still_combines_both_faces_unaffected_by_this_fix(self):
        # Battle back-face rewards and similar text-driven logic rely on
        # oracle_text staying "front\n//\nback" - only type_line changes here.
        entry = engine.DeckEntry(name=NICOL_BOLAS_OBJ["name"])
        card = engine.card_from_scryfall(entry, NICOL_BOLAS_OBJ, commander_name=None)
        self.assertIn("each opponent discards a card", card.oracle_text)
        self.assertIn("Draw two cards", card.oracle_text)

    def test_single_faced_card_is_completely_unaffected(self):
        obj = {
            "name": "Sol Ring", "set": "c21", "collector_number": "263",
            "mana_cost": "{1}", "cmc": 1.0, "type_line": "Artifact",
            "oracle_text": "{T}: Add {C}{C}.", "color_identity": [],
        }
        entry = engine.DeckEntry(name="Sol Ring")
        card = engine.card_from_scryfall(entry, obj, commander_name=None)
        self.assertEqual(card.type_line, "Artifact")
        self.assertTrue(card.is_artifact)


if __name__ == "__main__":
    unittest.main()
