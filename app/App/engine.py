#!/usr/bin/env python3
"""
Commander Goldfish Simulator v3
===============================

A reusable, heuristic Commander goldfish simulator for MTG decklists.

Major v3 changes
----------------
* TXT deck exports are first-class input.
* Scryfall metadata is cached locally (or an enriched CSV can be used offline).
* Reactive cards are held instead of being blindly cast into an empty goldfish board.
* Better mana model:
  - Sol Ring produces 2
  - bounce lands can produce 2
  - Treasure is one-shot mana, not permanent ramp
  - mana dorks respect summoning sickness
  - colored mana requirements are paid by an actual small DP solver
* Better land handling:
  - Brokers Hideout / Riveteers Overlook / Obscura Storefront fetch basics
  - Selesnya Sanctuary bounces a land
  - Gingerbread Cabin checks the "three other Forests" condition
  - gainlands and Temples resolve ETB life/scry
* Better semantic parsing:
  - direct draw is separated from "whenever/if you would draw"
  - activated draw abilities are not treated as ETB draw
  - lifegain payoffs such as Sanguine Bond are not falsely counted as lifegain sources
  - Scry, Surveil, Connive, Draw, Ward, Hexproof, Indestructible, Lifelink,
    Vigilance, Flying, Trample, Deathtouch, Menace, Haste, Reach, First strike,
    Double strike, Flash and Defender are recognized
* Token/resource model:
  - Food, Treasure, Clue and creature tokens
  - Peregrin Took / Tippy-Toe token replacement effects
  - Mirkwood Bats / Kambal / Baron Bertram interactions
* Bilbo-aware life engine:
  - Bilbo / Honor Troll +1 replacement effects
  - Doctor Strange / Alhammarret's Archive doubling
  - amount-based and per-event drain payoffs
  - 111-life milestone and optional Bilbo activation
* Basic combat goldfish:
  - creatures attack after summoning sickness
  - haste and lifelink are meaningful
  - Doctor Strange combat buff is approximated
  - no blockers are assumed
* Richer logs:
  - color access by turn
  - life milestones
  - Bilbo activation / win turn
  - scry / surveil / connive / draw counts
  - Food / Treasure / Clue
  - reactive cards held

This is still NOT a complete Magic rules engine. It is intended for deck-development
statistics and goldfishing, not judge-level game reconstruction.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    from App.keyword_library import registry as keyword_registry
except ImportError:
    from keyword_library import registry as keyword_registry  # engine.py run standalone from inside App/

try:
    from App.scenario_predicates import registry as scenario_predicates_registry
except ImportError:
    from scenario_predicates import registry as scenario_predicates_registry

try:
    from App.combat_model import interaction as combat_interaction
except ImportError:
    from combat_model import interaction as combat_interaction

try:
    from App.combat_model import importance as combat_importance
except ImportError:
    from combat_model import importance as combat_importance

try:
    from App.combat_model import equipment as equipment_model
except ImportError:
    from combat_model import equipment as equipment_model

try:
    from App.combat_model import posture as commander_posture
except ImportError:
    from combat_model import posture as commander_posture

try:
    from App.resource_planner import planner as resource_planner
except ImportError:
    from resource_planner import planner as resource_planner

# v4.68.0 ("Kalibrierungs-Synthese Teil 2, Integration"): the archetype_profile
# package (1.585-real-EDHREC-deck reference model, see
# App/archetype_profile/README.md) was previously an unconnected prototype -
# "Prototyp, noch nicht an engine.py/gui.py angeschlossen" per its own README.
# This wires it in, same try/except-standalone-fallback pattern as every other
# App/<package> import above.
#
# v4.75.0-Nachtrag: archetype_profile/reference_model.py (and deck_analyzer.py,
# stats_utils.py) import numpy at module load time. Until now, a Python
# environment without numpy installed made BOTH the "App.archetype_profile"
# and the bare "archetype_profile" fallback above fail identically (the
# ImportError is really numpy's, not a module-path issue), which propagated
# all the way up through gui.py's own import fallbacks and crashed the
# ENTIRE application at startup - even for users who never open the
# "Vergleich (1.585 Decks)" tab that is the only feature actually using this
# package. numpy is not otherwise a dependency of this tool (goldfishing, win
# condition testing, the opponent model etc. are pure-stdlib). Degrade
# gracefully instead: catch the failure, leave the archetype_profile symbols
# as None/empty, and let _get_archetype_analyzer()/commander_identity_slug()
# raise a clear, catchable RuntimeError only if/when that one comparison
# feature is actually used - App/gui.py::_build_deck_comparison() already
# wraps that call in a try/except and shows a friendly in-tab message, so
# this alone is enough to keep the rest of the app fully usable.
_ARCHETYPE_PROFILE_IMPORT_ERROR: Optional[str] = None
try:
    from App.archetype_profile import DeckAnalyzer as _ArchetypeDeckAnalyzer
    from App.archetype_profile import (
        COLORS_TO_SLUG as _ARCHETYPE_COLORS_TO_SLUG,
        SLUG_TO_LABEL as _ARCHETYPE_SLUG_TO_LABEL,
        normalize_color_identity as _archetype_normalize_color_identity,
    )
except ImportError as _archetype_import_error:
    try:
        from archetype_profile import DeckAnalyzer as _ArchetypeDeckAnalyzer
        from archetype_profile import (
            COLORS_TO_SLUG as _ARCHETYPE_COLORS_TO_SLUG,
            SLUG_TO_LABEL as _ARCHETYPE_SLUG_TO_LABEL,
            normalize_color_identity as _archetype_normalize_color_identity,
        )
    except ImportError as _archetype_import_error2:
        _ArchetypeDeckAnalyzer = None
        _ARCHETYPE_COLORS_TO_SLUG = {}
        _ARCHETYPE_SLUG_TO_LABEL = {}
        _archetype_normalize_color_identity = None
        # Prefer the FIRST attempt's error (from "App.archetype_profile",
        # the normal/expected import path): it is almost always the real
        # root cause (e.g. "No module named 'numpy'", raised while
        # App/archetype_profile/__init__.py loads its own numpy-dependent
        # submodules). The second attempt's "No module named
        # 'archetype_profile'" is close to always just a path artifact of
        # that bare-module fallback never being importable on a normal
        # install, and would otherwise mask the actually useful message.
        _ARCHETYPE_PROFILE_IMPORT_ERROR = str(_archetype_import_error) or str(_archetype_import_error2)


COLORS = ("W", "U", "B", "R", "G")

# Single source of truth for the version string written into summary.json /
# simulation_config.json. Bump this on every shipped iteration - it was previously
# a hardcoded "4.7.0" literal deep in the report builder, which meant every run's
# output claimed to be v4.7.0 regardless of how many work packages had actually
# landed. That made it impossible to tell, from a result ZIP alone, which build
# produced it.
ENGINE_VERSION = "4.75.0"
COLORLESS = "C"

BASIC_COLOR = {
    "Plains": "W",
    "Island": "U",
    "Swamp": "B",
    "Mountain": "R",
    "Forest": "G",
}

BASIC_SUBTYPES = {
    "Plains": "Plains",
    "Island": "Island",
    "Swamp": "Swamp",
    "Mountain": "Mountain",
    "Forest": "Forest",
}

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

TXT_LINE_RE = re.compile(
    r"""^\s*
        (?P<count>\d+)\s*[xX]?
        \s+
        (?P<name>.*?)
        (?:\s+\((?P<set>[A-Za-z0-9]+)\)\s+(?P<collector>[^\s]+))?
        (?:\s+\*(?P<foil>[A-Za-z]+)\*)?
        \s*$
    """,
    re.VERBOSE,
)
# v4.15.9 (Fremd-Deck-Import): "4x Lightning Bolt" (count immediately followed
# by a bare x/X, no space - the decklist.gg cross-site parser explicitly
# validates both "4 Card" and "4x Card" as the two real-world quantity
# notations) is now accepted alongside the original "4 Card". The foil marker
# ("*F*"/"*Foil*"/...) is now its own independent trailing group rather than
# nested inside the set/collector group, so it is recognized (and stripped
# out of the card name) even on a line with no set/collector at all - e.g.
# "1 Sol Ring *F*" previously left "*F*" glued onto the parsed name.

_TXT_HEADER_KEYWORDS = {
    "commander": {"commander", "commanders", "edh"},
    "mainboard": {"deck", "main deck", "maindeck", "mainboard"},
    "sideboard": {"sideboard", "side board", "sb", "maybeboard"},
    "companion": {"companion"},
}

# v4.16.0 (Fremd-Deck-Import cont'd): real precon text exports (seen in
# Wizards' own "Secrets of Strixhaven"/"Tarkir: Dragonstorm"/"Lorwyn
# Eclipsed" Commander precon decklists) use no section header at all - a
# single flat card list - and instead mark the commander inline on its own
# line, e.g. "1 Dina, Essence Brewer (Commander)". Left unhandled, that
# annotation would be swallowed into the parsed card NAME (breaking the
# Scryfall lookup) exactly the way a stray foil marker used to. Stripped out
# in load_txt_entries before the name is used for anything, and used by
# detect_commander_hints as an additional (header-independent) way to spot
# the commander.
_TRAILING_COMMANDER_ANNOTATION_RE = re.compile(r"\s*\(Commander\)\s*$", re.IGNORECASE)


def _classify_txt_header(text: str) -> Optional[str]:
    """v4.15.9 (Fremd-Deck-Import). Classifies a decklist header/comment line
    (with or without a leading '//') into 'commander' / 'mainboard' /
    'sideboard' / 'companion', or None if it's some other header text (a
    category header like 'Creatures (24)', a plain description line, an
    'About' metadata block Moxfield exports sometimes include, ...) that
    should just be skipped without changing section state. Keyword list
    matches the header text real cross-site decklist importers (e.g.
    decklist.gg, which documents exactly these header families) recognize
    for Commander/Deck/Sideboard/Companion sections - not invented.
    A trailing parenthetical (a card count, "(24)", or free text, "(cards)")
    is stripped before matching, so "Sideboard (5)" still classifies.
    """
    normalized = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip().rstrip(":").strip().lower()
    for kind, keywords in _TXT_HEADER_KEYWORDS.items():
        if normalized in keywords:
            return kind
    return None

KNOWN_KEYWORDS = {
    "flying", "first strike", "double strike", "deathtouch", "haste", "hexproof",
    "indestructible", "lifelink", "menace", "reach", "trample", "vigilance",
    "ward", "flash", "defender", "protection", "shroud",
    # v4.21.0: infect / wither / persist / undying - real static keyword
    # lines, same "bare word or comma-separated list" templating as the
    # existing simple entries above (deathtouch, haste, ...), no "Nx" suffix
    # like ward's needs. Devour is deliberately NOT added here (it always
    # has a number suffix, "Devour N", and is parsed directly from oracle
    # text where it's used - see own_etb_effects's "v4.21.0: Devour" block).
    "infect", "wither", "persist", "undying",
    # v4.22.0: prowess / delve - same bare-keyword-line templating. Cycling,
    # Flashback and Kicker are NOT added here, same reason as Devour above
    # (all three always carry a "{cost}" suffix and are parsed directly
    # from oracle text where they're used - maybe_cycle_cards /
    # maybe_flashback_cards / cast_option's Kicker scope note).
    "prowess", "delve",
}

ROLE_REACTIVE = {"interaction", "protection", "boardwipe", "counterspell"}

# Useful exact-name behavior for cards whose templating is intentionally unusual.
BILBO_NAME = "Bilbo, Birthday Celebrant"
ARCHIVE_NAME = "Alhammarret's Archive"
DOCTOR_STRANGE_NAME = "Doctor Strange, Surgeon"
HONOR_TROLL_NAME = "Honor Troll"
KATARA_HOPE_NAME = "Katara, Water Tribe's Hope"
AZIZA_NAME = "Aziza, Mage Tower Captain"
MICA_NAME = "Mica, Reader of Ruins"

DEFAULT_BILBO_PILE = [
    "Doctor Strange, Surgeon",
    "Bogwater Lumaret",
    "Daxos, Blessed by the Sun",
    "Elas il-Kor, Sadistic Pilgrim",
    "Prosperous Innkeeper",
    "Dina, Soul Steeper",
    "Marauding Blight-Priest",
    "Corpse Knight",
    "Vito, Thorn of the Dusk Rose",
    "Defiant Bloodlord",
    "Kambal, Profiteering Mayor",
]

DEFAULT_TUTOR_PRIORITY = [
    "Doctor Strange, Surgeon",
    "Vito, Thorn of the Dusk Rose",
    "Dina, Soul Steeper",
    "Marauding Blight-Priest",
    "Bogwater Lumaret",
    "Elas il-Kor, Sadistic Pilgrim",
    "Daxos, Blessed by the Sun",
    "Prosperous Innkeeper",
    "Mirkwood Bats",
    "Gyome, Master Chef",
    "Blossoming Bogbeast",
]

DEFAULT_ENCHANTMENT_TUTOR_PRIORITY = [
    "Sanguine Bond",
    "Moldervine Reclamation",
    "Heroic Feast",
    "Trudge Garden",
    "Bastion of Remembrance",
]

DEFAULT_LEGENDARY_TUTOR_PRIORITY = [
    "Doctor Strange, Surgeon",
    "Vito, Thorn of the Dusk Rose",
    "Dina, Soul Steeper",
    "Arwen, Mortal Queen",
    "Gyome, Master Chef",
    "Elas il-Kor, Sadistic Pilgrim",
    "Kambal, Profiteering Mayor",
]


# ---------------------------------------------------------------------------
# Helpers / input
# ---------------------------------------------------------------------------

def norm_col(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower().replace("_", " "))


def normalize_name(name: str) -> str:
    return (name or "").strip()


def parse_number_token(token: str, default: int = 1) -> int:
    token = (token or "").strip().lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token, default)


def split_oracle_lines(text: str) -> List[str]:
    text = (text or "").replace(" / // / ", "\n//\n").replace(" / ", "\n")
    return [x.strip() for x in text.splitlines() if x.strip() and x.strip() != "//"]


def strip_reminder_text(text: str) -> str:
    # Good enough for semantic classification. Oracle reminder text is usually parenthetical.
    return re.sub(r"\([^()]*\)", "", text or "")


def first_mana_face(mana_cost: str) -> str:
    return (mana_cost or "").split(" // ")[0].strip()


def parse_mana_cost(mana_cost: str) -> Tuple[int, Counter]:
    """
    Returns minimum total mana and colored-pip requirements for the first/default face.
    X contributes zero to minimum total. Hybrid is approximated conservatively.
    """
    cost = first_mana_face(mana_cost)
    tokens = re.findall(r"\{([^}]+)\}", cost.upper())
    total = 0
    req = Counter()
    for tok in tokens:
        if tok.isdigit():
            total += int(tok)
        elif tok == "X":
            continue
        elif tok in COLORS:
            total += 1
            req[tok] += 1
        elif tok == COLORLESS:
            total += 1
            req[COLORLESS] += 1
        elif "/" in tok:
            parts = tok.split("/")
            numeric_parts = [p for p in parts if p.isdigit()]
            colored = [p for p in parts if p in COLORS]
            if numeric_parts and colored:
                # v4.35.0: a mono-colored hybrid with a generic fallback
                # (e.g. {2/W}) can ALWAYS be legally paid with the printed
                # generic amount in any mana at all - that fallback is
                # unconditional, so this must never impose a mandatory
                # color requirement the way the plain-color branch above
                # does. This engine's (total, req) pair can't express "1
                # colored OR N generic" as a true either/or (find_payment's
                # payment_meets treats req as a hard AND-requirement), so -
                # per this function's own "approximated conservatively"
                # docstring - the safe choice is the worse-case generic
                # amount with NO color requirement: this can never produce
                # an illegal payment (paying required generic mana of any
                # color is always legal) and never blocks a legal cast for
                # lack of one specific color, at the cost of sometimes
                # overstating the true minimum cost when that color happens
                # to be available. The previous code did the opposite
                # (total=1 AND a mandatory color requirement) - the least
                # safe combination possible for this shape.
                total += int(numeric_parts[0])
            elif colored:
                # A hybrid of two (or more) real colors with NO generic
                # fallback at all (e.g. {W/U}) - confirmed real, in-project
                # cards: Sokka, Lateral Strategist {1}{W/U}{W/U}; Kirol,
                # Attentive First-Year {1}{R/W}{R/W}; Practiced Scrollsmith
                # {R}{R/W}{W}; Raph & Leo, Sibling Rivals {1}{R/W}{R/W} (see
                # App/.scryfall_card_cache_v4.json). Recording NO requirement
                # here (the old behavior) let this be paid with literally
                # any color, including ones not even printed on the symbol -
                # strictly worse than requiring the FIRST listed color: an
                # imperfect approximation (a deck with only the second color
                # available is wrongly blocked), but this function's own
                # comment already established "mark the first colored
                # option" as the intended convention for the single-color
                # case; this just stops silently exempting the multi-color
                # case from that same rule instead of granting it a free
                # pass on requirements entirely.
                total += 1
                req[colored[0]] += 1
            else:
                total += 1
        elif tok.endswith("P") and tok[0] in COLORS:
            total += 1
            req[tok[0]] += 1
        else:
            total += 1
    return total, req


def parse_add_mana_options(text: str) -> List[Counter]:
    """
    Parse simple printed mana abilities into possible outputs.
    Examples:
      Add {C}{C} -> [{C:2}]
      Add {G}{W} -> [{G:1,W:1}]
      Add {G} or {W} -> [{G:1},{W:1}]
      Add {W}, {U}, or {B} -> [{W:1},{U:1},{B:1}]
    """
    out: List[Counter] = []
    for line in split_oracle_lines(text):
        if "Add " not in line:
            continue
        # Skip reminder text after the primary sentence where possible.
        s = strip_reminder_text(line)
        if "Add one mana of any color" in s:
            out.extend(Counter({c: 1}) for c in COLORS)
            continue

        # v4.35.0: a comma/"or"-separated CHOICE list ("Add {W}, {U}, or
        # {B}." - the classic Triome pattern) of any length, each option a
        # single mana symbol. Matched BEFORE the plain-contiguous pattern
        # below so a 3+-option list's own first symbol is never ALSO
        # mistaken for a fixed simultaneous-production output - the old
        # code only had a 2-option "X or Y" pattern, so a 3+-option list
        # fell through to the contiguous-symbols regex instead, which
        # greedily matches one bare {SYMBOL} right after "Add " and
        # silently discarded every other option (there is no comma-
        # separated real card of this exact shape in this project's own
        # Scryfall cache today, but the underlying mechanic - real Triome
        # lands like Savai Triome's "Add {R}, {W}, or {B}." - is real and
        # common in Commander, so this closes the same documented gap
        # proactively rather than only once a specific deck needs it).
        choice = re.search(
            r"Add (\{[WUBRGC]\}(?:,? \{[WUBRGC]\})*,? or \{[WUBRGC]\})", s,
        )
        if choice:
            symbols = re.findall(r"\{([WUBRGC])\}", choice.group(1))
            out.extend(Counter({c: 1}) for c in symbols)
            continue

        m = re.search(r"Add ((?:\{[WUBRGC]\})+)", s)
        if m:
            symbols = re.findall(r"\{([WUBRGC])\}", m.group(1))
            out.append(Counter(symbols))
    # dedupe
    seen, deduped = set(), []
    for opt in out:
        key = tuple(sorted(opt.items()))
        if key not in seen:
            seen.add(key)
            deduped.append(opt)
    return deduped


@dataclass
class DeckEntry:
    name: str
    count: int = 1
    set_code: str = ""
    collector_number: str = ""
    row_data: dict = field(default_factory=dict)


def detect_input_format(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".dek", ".list"}:
        return "txt"
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    lines = [x for x in sample.splitlines() if x.strip()]
    if lines and TXT_LINE_RE.match(lines[0]) and not any(d in lines[0] for d in ",;\t"):
        return "txt"
    return "csv"


def load_txt_entries(path: Path) -> List[DeckEntry]:
    entries = []
    in_sideboard = False
    for lineno, raw in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("//"):
            heading = line[2:].strip()
            kind = _classify_txt_header(heading)
            if kind:
                in_sideboard = kind in ("sideboard", "companion")
            else:
                # Unrecognized "//" header text - fall back to the original
                # substring check so no pre-existing "// ..." file (ours or a
                # user's) can silently change behavior on this rewrite.
                low = heading.lower()
                in_sideboard = "sideboard" in low or "maybeboard" in low
            continue
        if line.startswith("#"):
            continue
        if not line[:1].isdigit():
            # v4.15.9 (Fremd-Deck-Import): a bare (non-"//") header/comment
            # line - e.g. Moxfield's "About" metadata block, or a category
            # header like "Creatures (24)"/"Commander" some export styles use
            # without a "//" prefix. Every real card line in every format
            # checked (Moxfield, EDHREC clipboard export, decklist.gg's
            # documented cross-site parser) starts with a digit count, so a
            # non-digit-leading line is safely treated as a comment/header,
            # never a card. _classify_txt_header updates section state for
            # known keywords (Commander/Deck/Sideboard/Companion, matching
            # decklist.gg's documented header families); anything else (a
            # category header, free-form description text) is just skipped.
            kind = _classify_txt_header(line)
            if kind:
                in_sideboard = kind in ("sideboard", "companion")
            continue
        if in_sideboard:
            continue
        line = _TRAILING_COMMANDER_ANNOTATION_RE.sub("", line).strip()
        m = TXT_LINE_RE.match(line)
        if not m:
            raise ValueError(f"Could not parse TXT line {lineno}: {raw!r}")
        entries.append(DeckEntry(
            name=normalize_name(m.group("name")),
            count=int(m.group("count")),
            set_code=(m.group("set") or "").upper(),
            collector_number=(m.group("collector") or ""),
        ))
    return entries


def sniff_dialect(path: Path) -> csv.Dialect:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:65536]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def pick_column(fieldnames: Sequence[str], aliases: Set[str]) -> Optional[str]:
    normalized = {norm_col(f): f for f in fieldnames}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def load_csv_entries(path: Path) -> Tuple[List[DeckEntry], dict]:
    aliases = {
        "name": {"card name", "name", "card", "product name", "english name"},
        "count": {"count", "quantity", "qty", "amount", "copies", "number"},
        "type": {"type", "type line", "typeline", "card type"},
        "cost": {"mana cost", "manacost", "cost", "mana_cost"},
        "mv": {"mana value", "manavalue", "cmc", "converted mana cost", "mana_value"},
        "text": {"oracle text", "oracle", "text", "rules text", "card text", "oracle_text"},
        "commander": {"commander", "is commander", "is_commander"},
        "ci": {"color identity", "color_identity"},
        "produced": {"produced mana", "produced_mana"},
        "keywords": {"keywords", "keyword"},
        "power": {"power"},
        "toughness": {"toughness"},
        "loyalty": {"loyalty"},
        "defense": {"defense"},
        "set": {"set", "set code", "set_code"},
        "collector": {"collector number", "collector_number", "number"},
    }
    dialect = sniff_dialect(path)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("CSV contains no header row.")
        cols = {k: pick_column(reader.fieldnames, v) for k, v in aliases.items()}
        if not cols["name"]:
            raise ValueError(f"Could not find card-name column. Columns: {reader.fieldnames}")

        entries = []
        for row in reader:
            name = normalize_name(row.get(cols["name"], ""))
            if not name:
                continue
            count = 1
            if cols["count"]:
                try:
                    count = max(1, int(float(str(row.get(cols["count"]) or "1").replace(",", "."))))
                except ValueError:
                    pass
            entries.append(DeckEntry(
                name=name,
                count=count,
                set_code=(row.get(cols["set"]) or "").upper() if cols["set"] else "",
                collector_number=str(row.get(cols["collector"]) or "") if cols["collector"] else "",
                row_data=row,
            ))
    return entries, cols


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

@dataclass
class Card:
    name: str
    mana_cost: str = ""
    mana_value: float = 0.0
    type_line: str = ""
    oracle_text: str = ""
    color_identity: Set[str] = field(default_factory=set)
    produced_mana: Set[str] = field(default_factory=set)
    keywords: Set[str] = field(default_factory=set)
    roles: Set[str] = field(default_factory=set)
    power: Optional[float] = None
    toughness: Optional[float] = None
    commander: bool = False
    set_code: str = ""
    collector_number: str = ""
    metadata_source: str = ""
    # v4.19.0: planeswalker starting loyalty / battle starting defense, from
    # Scryfall's own "loyalty" / "defense" fields (top-level for a single-
    # faced planeswalker/battle, front-face for a DFC one such as Nicol
    # Bolas, the Ravager - see card_from_scryfall).
    loyalty: Optional[float] = None
    defense: Optional[float] = None

    @property
    def is_land(self) -> bool:
        return "land" in self.type_line.lower()

    @property
    def is_creature(self) -> bool:
        return "creature" in self.type_line.lower()

    @property
    def is_artifact(self) -> bool:
        return "artifact" in self.type_line.lower()

    @property
    def is_equipment(self) -> bool:
        return "equipment" in self.type_line.lower()

    @property
    def is_enchantment(self) -> bool:
        return "enchantment" in self.type_line.lower()

    @property
    def is_instant(self) -> bool:
        return "instant" in self.type_line.lower()

    @property
    def is_sorcery(self) -> bool:
        return "sorcery" in self.type_line.lower()

    @property
    def is_planeswalker(self) -> bool:
        return "planeswalker" in self.type_line.lower()

    @property
    def is_battle(self) -> bool:
        return "battle" in self.type_line.lower()

    @property
    def is_permanent(self) -> bool:
        return (
            self.is_land or self.is_creature or self.is_artifact
            or self.is_enchantment or self.is_planeswalker or self.is_battle
        )

    @property
    def min_cost(self) -> int:
        return parse_mana_cost(self.mana_cost)[0]

    @property
    def color_requirements(self) -> Counter:
        return parse_mana_cost(self.mana_cost)[1]


def index_scryfall_cards(cards: List[dict]) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Builds the two lookup indexes ScryfallProvider.get_many() matches a
    batch's requested identifiers against: by_print (keyed "set:<set>#<num>")
    and by_name (keyed by casefolded card name).

    v4.16.0: double-faced/transform/modal cards come back from Scryfall's
    collection endpoint with a combined "Front // Back" top-level name, but a
    decklist that names only the front face (the normal way to write e.g.
    "Duskwatch Recruiter") is looked up by that face name alone. Without
    also indexing each face's own name, get_many() silently "loses" every
    DFC looked up by name only: Scryfall finds and returns the card (so it
    never lands in payload["not_found"]), yet it was unreachable under the
    front-face key, so build_deck() later raised a misleading "No metadata
    for <front face name>". Pulled out into its own pure function (no
    network) so this indexing logic is directly unit-testable.
    """
    by_print: Dict[str, dict] = {}
    by_name: Dict[str, dict] = {}
    for obj in cards:
        s = (obj.get("set") or "").lower()
        cn = str(obj.get("collector_number") or "")
        if s and cn:
            by_print[f"set:{s}#{cn}"] = obj
        by_name[(obj.get("name") or "").casefold()] = obj
        # Index each face's own name too (first match wins, so a
        # combined-name exact hit already stored is never clobbered).
        for face in (obj.get("card_faces") or []):
            face_name = (face.get("name") or "").casefold()
            if face_name and face_name not in by_name:
                by_name[face_name] = obj
    return by_print, by_name


class ScryfallProvider:
    COLLECTION_URL = "https://api.scryfall.com/cards/collection"

    def __init__(self, cache_path: Path, offline: bool = False):
        self.cache_path = cache_path
        self.offline = offline
        self.cache = {}
        if cache_path.exists():
            try:
                self.cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                self.cache = {}

    @staticmethod
    def key(entry: DeckEntry) -> str:
        if entry.set_code and entry.collector_number:
            return f"set:{entry.set_code.lower()}#{entry.collector_number}"
        return f"name:{entry.name.casefold()}"

    def save(self):
        self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _split_cache(self, entries: List[DeckEntry]) -> Tuple[Dict[str, dict], List[DeckEntry]]:
        unique = {self.key(e): e for e in entries}
        result, missing = {}, []
        for key, entry in unique.items():
            if key in self.cache:
                result[key] = self.cache[key]
            else:
                missing.append(entry)
        return result, missing

    def _resolve_missing(self, missing: List[DeckEntry], post_json, fuzzy_named) -> Dict[str, dict]:
        """Shared batch-fetch + fuzzy-fallback logic behind every get_many()
        this provider has ever been monkey-patched with (see the v4.17.0
        README entry: three near-duplicate get_many() bodies used to exist,
        one per HTTP backend, each unconditionally overriding
        ScryfallProvider.get_many at import time - only the LAST one
        assigned is ever actually live, so a fix applied to an earlier one
        silently did nothing at runtime. This is now the one place the
        logic lives; every get_many() variant is a thin wrapper around it).

        v4.17.0 also fixes two real bugs found from a real local run against
        the Fremd-Decks: (1) a batch that came back with any not_found
        identifiers used to abort the WHOLE deck immediately, so only the
        first bad batch's cards were ever reported, and any remaining
        batches (a ~99-card deck needs 2, since a batch caps at 70) were
        never even checked - fixed by collecting every unresolved card
        across ALL batches and raising exactly one combined error at the
        end. (2) a name-only entry Scryfall's EXACT collection lookup
        couldn't match (a missing comma, a curly vs. straight apostrophe, an
        en dash vs. hyphen, a brand-new card not yet reachable by its exact
        printed name in some export) now gets one fallback lookup through
        Scryfall's own fuzzy `/cards/named` endpoint before being given up
        on - Scryfall's fuzzy matcher is the authoritative arbiter for "did
        you mean X", not a name correction guessed here.

        post_json(url, body_bytes) -> parsed JSON dict; must raise
            RuntimeError with a clear, user-facing message on any HTTP or
            network failure.
        fuzzy_named(name) -> a Scryfall card dict, or None if unresolved.
        """
        result: Dict[str, dict] = {}
        unresolved: List[DeckEntry] = []

        for start in range(0, len(missing), 70):
            batch = missing[start:start + 70]
            identifiers = []
            for e in batch:
                if e.set_code and e.collector_number:
                    identifiers.append({"set": e.set_code.lower(), "collector_number": e.collector_number})
                else:
                    identifiers.append({"name": e.name})

            print(f"Scryfall metadata: {start+1}-{start+len(batch)} / {len(missing)}")
            payload = post_json(
                self.COLLECTION_URL,
                json.dumps({"identifiers": identifiers}).encode("utf-8"),
            )

            cards = payload.get("data", [])
            by_print, by_name = index_scryfall_cards(cards)

            for e in batch:
                key = self.key(e)
                obj = by_print.get(key) or by_name.get(e.name.casefold())
                if obj:
                    self.cache[key] = obj
                    result[key] = obj
                else:
                    unresolved.append(e)

            self.save()
            time.sleep(0.15)

        still_unresolved: List[DeckEntry] = []
        for e in unresolved:
            obj = None
            if not (e.set_code and e.collector_number):
                obj = fuzzy_named(e.name)
            if obj:
                key = self.key(e)
                self.cache[key] = obj
                result[key] = obj
                print(f"Scryfall Fuzzy-Treffer: {e.name!r} -> {obj.get('name')!r}")
            else:
                still_unresolved.append(e)

        if unresolved:
            self.save()

        if still_unresolved:
            names = sorted({e.name for e in still_unresolved})
            raise RuntimeError(
                f"Scryfall konnte {len(names)} Karte(n) nicht identifizieren: "
                + ", ".join(names)
            )

        return result

    def _fuzzy_lookup_urllib(self, name: str) -> Optional[dict]:
        import urllib.parse
        url = "https://api.scryfall.com/cards/named?" + urllib.parse.urlencode({"fuzzy": name})
        req = urllib.request.Request(url, headers={
            "User-Agent": "CommanderGoldfishSimulator/3.0 (personal deck analysis)",
            "Accept": "application/json;q=0.9,*/*;q=0.8",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
        except Exception:
            obj = None
        time.sleep(0.1)
        return obj

    def get_many(self, entries: List[DeckEntry]) -> Dict[str, dict]:
        result, missing = self._split_cache(entries)

        if missing and self.offline:
            raise RuntimeError(
                f"{len(missing)} cards are not in the local Scryfall cache. "
                f"Run once without --offline or pass --metadata-csv."
            )

        def post_json(url, body):
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "User-Agent": "CommanderGoldfishSimulator/3.0 (personal deck analysis)",
                    "Accept": "application/json;q=0.9,*/*;q=0.8",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Scryfall HTTP {exc.code}: {detail[:700]}") from exc
            except Exception as exc:
                raise RuntimeError(f"Could not reach Scryfall: {exc}") from exc

        result.update(self._resolve_missing(missing, post_json, self._fuzzy_lookup_urllib))
        return result


def num_or_none(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def card_from_scryfall(entry: DeckEntry, obj: dict, commander_name: Optional[str]) -> Card:
    faces = obj.get("card_faces") or []
    f0 = faces[0] if faces else {}
    mana_cost = obj.get("mana_cost") or f0.get("mana_cost") or ""
    # v4.34.0: a transform/modal-DFC's TOP-LEVEL type_line from Scryfall is
    # already the combined "Front // Back" string (e.g. "Legendary Creature
    # - Elder Dragon // Legendary Planeswalker - Bolas" for Nicol Bolas, the
    # Ravager // Nicol Bolas, the Arisen - confirmed against Scryfall/
    # mtg.wtf), so the old `obj.get("type_line") or " // ".join(...)` never
    # even reached its own fallback: it always found the top-level combined
    # line and used it directly. Card.is_creature/is_planeswalker/etc. are
    # plain substring checks on type_line (see the Card dataclass above), so
    # a card like Nicol Bolas ended up simultaneously is_creature=True AND
    # is_planeswalker=True for the entire game - this engine has no in-game
    # transform tracking (see index_scryfall_cards' own docstring: "scoped to
    # Scryfall NAME lookup only, never in-game flipping"), so a permanent
    # must resolve to exactly the ONE type it actually has while sitting on
    # the battlefield/in hand: its FRONT face's type_line, the same face
    # power/toughness/loyalty/defense already fall back to below. Only fall
    # back to the combined line if the front face is somehow missing its own
    # type_line (defensive - not expected from real Scryfall data).
    if faces:
        type_line = f0.get("type_line") or obj.get("type_line") or " // ".join(f.get("type_line", "") for f in faces)
    else:
        type_line = obj.get("type_line") or ""
    oracle_text = obj.get("oracle_text") or "\n//\n".join(f.get("oracle_text", "") for f in faces)

    produced = set(obj.get("produced_mana") or [])
    for f in faces:
        produced.update(f.get("produced_mana") or [])

    keywords = {str(k).lower() for k in (obj.get("keywords") or [])}
    return Card(
        name=entry.name,
        mana_cost=mana_cost,
        mana_value=float(obj.get("cmc") or 0),
        type_line=type_line,
        oracle_text=oracle_text,
        color_identity=set(obj.get("color_identity") or []),
        produced_mana=produced,
        keywords=keywords,
        power=num_or_none(obj.get("power") or f0.get("power")),
        toughness=num_or_none(obj.get("toughness") or f0.get("toughness")),
        commander=(entry.name == commander_name),
        set_code=entry.set_code or str(obj.get("set") or "").upper(),
        collector_number=entry.collector_number or str(obj.get("collector_number") or ""),
        metadata_source="scryfall",
        loyalty=num_or_none(obj.get("loyalty") or f0.get("loyalty")),
        defense=num_or_none(obj.get("defense") or f0.get("defense")),
    )


def load_metadata_csv(path: Path) -> Dict[str, Card]:
    """
    Reads v2/v3 enriched CSVs as an offline metadata source.
    """
    out = {}
    dialect = sniff_dialect(path)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, dialect=dialect)
        for row in reader:
            name = normalize_name(row.get("Name", ""))
            if not name:
                continue
            keywords = set(filter(None, re.split(r"[|,;]", (row.get("Keywords") or "").lower())))
            produced = set(c for c in COLORS + (COLORLESS,) if c in (row.get("Produced Mana") or ""))
            ci = set(c for c in COLORS if c in (row.get("Color Identity") or ""))
            out[name.casefold()] = Card(
                name=name,
                mana_cost=row.get("Mana Cost", "") or "",
                mana_value=float(row.get("Mana Value") or 0),
                type_line=row.get("Type Line", "") or "",
                oracle_text=(row.get("Oracle Text", "") or "").replace(" / ", "\n"),
                color_identity=ci,
                produced_mana=produced,
                keywords=keywords,
                power=num_or_none(row.get("Power")),
                toughness=num_or_none(row.get("Toughness")),
                set_code=row.get("Set", "") or "",
                collector_number=str(row.get("Collector Number", "") or ""),
                metadata_source="metadata_csv",
                loyalty=num_or_none(row.get("Loyalty")),
                defense=num_or_none(row.get("Defense")),
            )
    return out


def card_from_local_csv(entry: DeckEntry, cols: dict, commander_name: Optional[str]) -> Card:
    r = entry.row_data
    cost = (r.get(cols.get("cost")) or "").strip() if cols.get("cost") else ""
    mv = 0.0
    if cols.get("mv"):
        try:
            mv = float(str(r.get(cols["mv"]) or 0).replace(",", "."))
        except ValueError:
            pass
    ci = set(c for c in COLORS if c in str(r.get(cols.get("ci")) or "").upper()) if cols.get("ci") else set()
    produced = set(c for c in COLORS + (COLORLESS,) if c in str(r.get(cols.get("produced")) or "").upper()) if cols.get("produced") else set()
    keywords = set(filter(None, re.split(r"[|,;]", str(r.get(cols.get("keywords")) or "").lower()))) if cols.get("keywords") else set()

    commander = entry.name == commander_name
    if cols.get("commander"):
        commander = commander or str(r.get(cols["commander"]) or "").strip().lower() in {"1", "true", "yes", "commander"}

    return Card(
        name=entry.name,
        mana_cost=cost,
        mana_value=mv,
        type_line=(r.get(cols.get("type")) or "") if cols.get("type") else "",
        oracle_text=(r.get(cols.get("text")) or "") if cols.get("text") else "",
        color_identity=ci,
        produced_mana=produced,
        keywords=keywords,
        power=num_or_none(r.get(cols.get("power"))) if cols.get("power") else None,
        toughness=num_or_none(r.get(cols.get("toughness"))) if cols.get("toughness") else None,
        commander=commander,
        set_code=entry.set_code,
        collector_number=entry.collector_number,
        metadata_source="input_csv",
        loyalty=num_or_none(r.get(cols.get("loyalty"))) if cols.get("loyalty") else None,
        defense=num_or_none(r.get(cols.get("defense"))) if cols.get("defense") else None,
    )


# ---------------------------------------------------------------------------
# Semantic parser
# ---------------------------------------------------------------------------


def has_direct_draw(card: Card) -> bool:
    """
    Direct spell/ability-on-resolution draw only.
    Excludes triggered, activated and replacement lines.
    """
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).strip()
        low = s.lower()
        if not re.search(r"\bdraw\b", low):
            continue
        if low.startswith(("whenever ", "when ", "at the beginning ", "if ", "as ", "each time ")):
            continue
        if ":" in s.split("Draw")[0]:
            continue
        if "if you would draw" in low:
            continue
        if re.match(r"^draw (?:a|one|two|three|four|five|six|seven|\d+) cards?", low):
            return True
        if re.match(r"^draw (?:a|one|\d+) card", low):
            return True
    return False


def direct_draw_count(card: Card) -> int:
    total = 0
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).strip()
        low = s.lower()
        if low.startswith(("whenever ", "when ", "at the beginning ", "if ", "as ")):
            continue
        if "if you would draw" in low:
            continue
        m = re.match(r"^draw (a|one|two|three|four|five|six|seven|\d+) cards?", low)
        if m:
            total += parse_number_token(m.group(1))
    return total


def direct_action_count(card: Card, action: str) -> int:
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).strip().lower()
        if s.startswith(("whenever ", "when ", "at the beginning ", "if ", "as ")):
            continue
        if action not in s:
            continue
        if ":" in s.split(action)[0]:
            continue
        m = re.search(rf"\b{action}\s+(a|one|two|three|four|five|six|seven|\d+)\b", s)
        if m:
            return parse_number_token(m.group(1))
        if action == "connive" and re.search(r"\bconnive\b", s):
            return 1
    return 0


def role_set(card: Card) -> Set[str]:
    text = strip_reminder_text(card.oracle_text)
    low = text.lower()
    roles: Set[str] = set()

    if card.is_land:
        roles.add("land")

    # Ramp: actual reusable mana source or land-to-battlefield effect.
    if card.is_permanent and not card.is_land and "{t}: add " in low:
        roles.add("ramp")
    if "search your library for a basic land" in low and "onto the battlefield" in low:
        roles.add("ramp")
    if "search your library for a land card" in low and "onto the battlefield" in low:
        roles.add("ramp")
    if card.name in {"Arcane Signet", "Sol Ring", "Talisman of Unity", "Talisman of Hierarchy", "Talisman of Resilience", "Pristine Talisman", "Great Divide Guide", "Gilded Goose"}:
        roles.add("ramp")

    # Treasure creation is acceleration, but explicitly one-shot rather than persistent ramp.
    if "create a treasure token" in low or "create treasure tokens" in low:
        roles.add("burst_mana")

    # Draw/card advantage.
    if has_direct_draw(card):
        roles.add("draw")
    if re.search(r"(whenever|at the beginning).*draw (?:a|one|\d+) card", low, re.S):
        roles.add("draw_engine")
    if re.search(r":\s*draw (?:a|one|two|\d+) cards?", low):
        roles.add("draw_engine")
    if "if you would draw a card" in low:
        roles.add("draw_replacement")
    if "connive" in low:
        roles.add("filtering")
    if "scry" in low or "surveil" in low:
        roles.add("selection")

    # Lifegain SOURCE: require text that actually instructs the controller to gain life.
    # "Whenever you gain life, ..." is a payoff and should NOT be classified as a source.
    source_lines = []
    for line in split_oracle_lines(card.oracle_text):
        clean = strip_reminder_text(line).lower()
        if re.search(r"\byou gain\b", clean) and "life" in clean:
            if clean.startswith("if you would gain life"):
                continue
            if clean.startswith("whenever you gain life"):
                continue
            source_lines.append(clean)
    if source_lines:
        roles.add("lifegain")
    if "lifelink" in keyword_set(card):
        roles.add("lifegain")

    # Lifegain replacement/payoff.
    if "if you would gain life" in low:
        roles.add("lifegain_replacement")
    if "whenever you gain life" in low:
        roles.add("lifegain_payoff")

    # Interaction / wipes.
    if any(x in low for x in (
        "destroy target ", "exile target ", "counter target spell",
        "target creature gets -", "target opponent sacrifices",
    )):
        roles.add("interaction")
    if any(x in low for x in (
        "destroy all creatures", "destroy all artifacts", "destroy all enchantments",
        "all creatures get -", "each player sacrifices three creatures",
    )):
        roles.add("boardwipe")

    # Protection.
    if any(x in low for x in (
        "gains hexproof until end of turn", "gain hexproof until end of turn",
        "gains indestructible until end of turn", "gain indestructible until end of turn",
        "exile any number of target creatures you control",
        "phase out",
    )):
        roles.add("protection")
    if "ward" in keyword_set(card):
        roles.add("resilient")

    # Tutors.
    if "search your library for" in low and any(x in low for x in ("put it into your hand", "put them into your hand", "put it on top of your library", "put them onto the battlefield", "put it onto the battlefield")):
        if "basic land" not in low and "land card" not in low:
            roles.add("tutor")

    # Recursion.
    if "from your graveyard" in low and any(x in low for x in ("return", "put")):
        roles.add("recursion")

    # Token engines.
    if "create " in low and " token" in low:
        roles.add("token")
    if "food token" in low or "food tokens" in low:
        roles.add("food")
    if "treasure token" in low or "treasure tokens" in low:
        roles.add("treasure")
    if "clue token" in low or "clue tokens" in low or "investigate" in low:
        roles.add("clue")

    # Finishers.
    if "each opponent loses" in low or "target opponent loses" in low:
        roles.add("finisher")
    if card.name in {"Storm Herd", "Blossoming Bogbeast"}:
        roles.add("finisher")

    # Generic proactive engine.
    if roles & {"draw_engine", "lifegain_payoff", "lifegain_replacement", "token", "tutor"} and card.is_permanent:
        roles.add("engine")

    return roles




# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

@dataclass
class Strategy:
    commander_colors: Set[str] = field(default_factory=set)
    tutor_priority: List[str] = field(default_factory=lambda: list(DEFAULT_TUTOR_PRIORITY))
    enchantment_tutor_priority: List[str] = field(default_factory=lambda: list(DEFAULT_ENCHANTMENT_TUTOR_PRIORITY))
    legendary_tutor_priority: List[str] = field(default_factory=lambda: list(DEFAULT_LEGENDARY_TUTOR_PRIORITY))
    bilbo_pile: List[str] = field(default_factory=lambda: list(DEFAULT_BILBO_PILE))
    hold_cards: Set[str] = field(default_factory=set)
    never_cast_goldfish: Set[str] = field(default_factory=set)
    prefer_food_for_life_until: int = 111
    max_food_activations_per_turn: int = 3




# ---------------------------------------------------------------------------
# Game objects / mana
# ---------------------------------------------------------------------------

@dataclass
class Permanent:
    card: Card
    entered_turn: int
    tapped: bool = False
    counters: int = 0
    chosen_color: Optional[str] = None
    # Generic named counters let Oracle text such as "indestructible counter",
    # "lifelink counter", etc. affect the simplified rules model without
    # hard-coding a card name.
    named_counters: Counter = field(default_factory=Counter)
    # Short-lived keyword grants used by simplified protection / board effects.
    temporary_keywords: Set[str] = field(default_factory=set)
    # Equipment model (WP7, Iteration 2): if this Permanent IS an Equipment, which
    # creature Permanent it is currently attached to (None = unattached).
    attached_to: Optional["Permanent"] = None
    # v4.19.0: current planeswalker loyalty / battle defense counters. Seeded
    # from the card's printed starting value in __post_init__ so every one of
    # the half-dozen "Permanent(card=...)" call sites (real casts, token
    # copies, etc.) gets this for free instead of needing its own separate
    # edit - the same "fix at the root, not per call site" reasoning as the
    # v4.15.6 Baron Bertram sacrifice-cost fix. Pass loyalty/defense
    # explicitly only to override the printed starting value (e.g. a test).
    loyalty: Optional[float] = None
    defense: Optional[float] = None
    # v4.19.0: which turn this planeswalker last activated a loyalty
    # ability (once per planeswalker per turn, real rule) / -1 = never yet.
    loyalty_activated_turn: int = -1
    # v4.21.0: -1/-1 counters, parallel to `counters` (+1/+1) above. The
    # only source that puts these on a Permanent right now is Persist's own
    # "return with a -1/-1 counter on it" (see move_permanent_to_zone's
    # "v4.21.0: Persist / Undying" block) - no removal effect that deals
    # -1/-1 counters directly (wither/infect creature damage) is modeled,
    # since this engine has no opposing creatures for that to ever matter
    # against. Kept as a real counter type rather than folding into
    # `counters` so Undying's own "no +1/+1 counters" check stays correct
    # for a creature that persisted earlier.
    minus1_counters: int = 0

    def __post_init__(self):
        if self.loyalty is None and self.card.is_planeswalker and self.card.loyalty is not None:
            self.loyalty = float(self.card.loyalty)
        if self.defense is None and self.card.is_battle and self.card.defense is not None:
            self.defense = float(self.card.defense)

    @property
    def summoning_sick(self) -> bool:
        return self.card.is_creature and "haste" not in self.card.keywords


@dataclass
class TokenGroup:
    name: str
    count: int
    power: float = 1.0
    toughness: float = 1.0
    keywords: Set[str] = field(default_factory=set)
    entered_turn: int = 0


@dataclass
class ManaSource:
    label: str
    kind: str                 # permanent / treasure / goose
    permanent_index: Optional[int]
    options: List[Counter]    # output if source is used once
    penalty: float = 0.0
    life_delta_on_use: float = 0.0


@dataclass
class PaymentPlan:
    used: List[Tuple[ManaSource, Counter]]
    total: Counter
    penalty: float


@dataclass
class GameState:
    library: List[Card]
    hand: List[Card]
    command_zone: List[Card]
    graveyard: List[Card] = field(default_factory=list)
    exile: List[Card] = field(default_factory=list)
    battlefield: List[Permanent] = field(default_factory=list)
    creature_tokens: List[TokenGroup] = field(default_factory=list)
    food: int = 0
    treasure: int = 0
    clues: int = 0
    life: float = 40.0
    opponents: List[float] = field(default_factory=lambda: [40.0, 40.0, 40.0])
    turn: int = 0
    commander_casts: int = 0
    nontoken_creatures_entered_this_turn: int = 0
    gained_life_this_turn: bool = False
    baron_triggered_this_turn: bool = False
    life_events_this_turn: int = 0
    well_caps_this_turn: List[float] = field(default_factory=list)
    trudge_garden_triggers_this_turn: int = 0
    frying_pan_bonus_this_turn: float = 0.0
    scry_count: int = 0
    surveil_count: int = 0
    connive_count: int = 0
    cards_drawn_total: int = 0
    reactive_held_total: int = 0
    bilbo_activation_turn: Optional[int] = None
    win_turn: Optional[int] = None
    milestones: Dict[int, Optional[int]] = field(default_factory=lambda: {50: None, 60: None, 80: None, 100: None, 111: None})
    event_log: List[str] = field(default_factory=list)

    def log(self, msg: str):
        self.event_log.append(msg)

    def cards_in_play(self, name: str) -> List[Permanent]:
        return [p for p in self.battlefield if p.card.name == name]

    def has(self, name: str) -> bool:
        return any(p.card.name == name for p in self.battlefield)

    def lands(self) -> List[Permanent]:
        return [p for p in self.battlefield if p.card.is_land]

    def creatures(self) -> List[Permanent]:
        return [p for p in self.battlefield if p.card.is_creature]

    def forest_count(self) -> int:
        return sum("forest" in p.card.type_line.lower() for p in self.lands())

    def swamp_count(self) -> int:
        return sum("swamp" in p.card.type_line.lower() for p in self.lands())


def card_mana_options(p: Permanent, state: GameState, strategy: Strategy) -> List[Counter]:
    c = p.card
    if p.tapped:
        return []

    # Summoning sickness prevents creatures from using tap abilities.
    if c.is_creature and p.entered_turn == state.turn and "haste" not in c.keywords:
        # Static Great Divide Guide still changes lands, but the Guide itself can't tap.
        return []

    if c.name == "Sol Ring":
        return [Counter({COLORLESS: 2})]

    if c.name == "Arcane Signet":
        return [Counter({x: 1}) for x in (strategy.commander_colors or set(COLORS))]

    if c.name.startswith("Talisman of "):
        opts = [Counter({COLORLESS: 1})]
        cols = c.produced_mana & set(COLORS)
        opts.extend(Counter({x: 1}) for x in cols)
        return opts

    if c.name == "Pristine Talisman":
        return [Counter({COLORLESS: 1})]

    if c.name == "Great Divide Guide":
        return [Counter({x: 1}) for x in (strategy.commander_colors or set(COLORS))]

    if c.name == "Gilded Goose":
        # Food is consumed separately when payment is applied.
        if state.food > 0:
            return [Counter({x: 1}) for x in (strategy.commander_colors or set(COLORS))]
        return []

    if c.is_land:
        # Great Divide Guide gives every land an alternate rainbow tap ability.
        opts = []
        if state.has("Great Divide Guide"):
            opts.extend(Counter({x: 1}) for x in (strategy.commander_colors or set(COLORS)))

        # Thriving lands: primary + chosen color.
        if c.name.startswith("Thriving "):
            primary = {
                "Thriving Heath": "W", "Thriving Moor": "B", "Thriving Grove": "G",
                "Thriving Isle": "U", "Thriving Bluff": "R",
            }.get(c.name)
            if primary:
                opts.append(Counter({primary: 1}))
            if p.chosen_color:
                opts.append(Counter({p.chosen_color: 1}))
            return dedupe_options(opts)

        # Tainted Wood condition.
        if c.name == "Tainted Wood":
            opts.append(Counter({COLORLESS: 1}))
            if state.swamp_count() > 0:
                opts.extend([Counter({"B": 1}), Counter({"G": 1})])
            return dedupe_options(opts)

        parsed = parse_add_mana_options(c.oracle_text)
        if parsed:
            opts.extend(parsed)
        elif c.produced_mana:
            opts.extend(Counter({x: 1}) for x in c.produced_mana)
        else:
            for basic, color in BASIC_COLOR.items():
                if basic.lower() in c.type_line.lower():
                    opts.append(Counter({color: 1}))
        return dedupe_options(opts)

    # Other printed tap-for-mana permanents.
    parsed = parse_add_mana_options(c.oracle_text)
    return parsed


def dedupe_options(options: List[Counter]) -> List[Counter]:
    out, seen = [], set()
    for o in options:
        k = tuple(sorted(o.items()))
        if k not in seen:
            seen.add(k)
            out.append(o)
    return out


def build_mana_sources(state: GameState, strategy: Strategy) -> List[ManaSource]:
    sources = []
    for i, p in enumerate(state.battlefield):
        opts = card_mana_options(p, state, strategy)
        if not opts:
            continue
        penalty = 0.0
        life_delta = 0.0
        kind = "permanent"
        if p.card.name == "Pristine Talisman":
            life_delta = +1.0
        if p.card.name.startswith("Talisman of "):
            penalty = 0.05  # prefer colorless/other sources if equally good
        if p.card.name == "Gilded Goose":
            kind = "goose"
            penalty = 0.35  # food is a real resource
        sources.append(ManaSource(
            label=p.card.name,
            kind=kind,
            permanent_index=i,
            options=opts,
            penalty=penalty,
            life_delta_on_use=life_delta,
        ))

    # Each Treasure is a separate one-shot source.
    for j in range(state.treasure):
        sources.append(ManaSource(
            label=f"Treasure#{j+1}",
            kind="treasure",
            permanent_index=None,
            options=[Counter({x: 1}) for x in (strategy.commander_colors or set(COLORS))],
            penalty=0.25,
        ))
    return sources


def output_total(counter: Counter) -> int:
    return sum(counter.values())


def payment_meets(pool: Counter, total_cost: int, req: Counter) -> bool:
    for c, n in req.items():
        if pool[c] < n:
            return False
    return output_total(pool) >= total_cost




def on_permanent_tapped(state: GameState, strategy: Optional[Strategy], p: Permanent, reason: str = "tap"):
    if strategy is None:
        return
    for line in split_oracle_lines(p.card.oracle_text):
        low = strip_reminder_text(line).lower()
        if not ("whenever this creature becomes tapped" in low or "whenever this permanent becomes tapped" in low):
            continue
        m = re.search(r"you gain (\d+) life", low)
        if m:
            gain_life(state, int(m.group(1)), f"{p.card.name} tapped")
        m = re.search(r"scry (\d+)", low)
        if m:
            scry(state, int(m.group(1)), strategy)
        m = re.search(r"draw (a|one|two|three|\d+) cards?", low)
        if m:
            draw_cards(state, parse_number_token(m.group(1)), reason=f"{p.card.name} tapped")


def tap_permanent(state: GameState, strategy: Optional[Strategy], index: int, reason: str = "tap"):
    if index < 0 or index >= len(state.battlefield):
        return
    p = state.battlefield[index]
    if p.tapped:
        return
    p.tapped = True
    on_permanent_tapped(state, strategy, p, reason)


def apply_payment(state: GameState, plan: PaymentPlan, strategy: Optional[Strategy] = None):
    treasure_used = 0
    goose_used = 0
    for src, opt in plan.used:
        if src.kind == "treasure":
            treasure_used += 1
        elif src.kind == "goose":
            goose_used += 1
            if src.permanent_index is not None:
                tap_permanent(state, strategy, src.permanent_index, reason="mana")
        elif src.permanent_index is not None:
            tap_permanent(state, strategy, src.permanent_index, reason="mana")

        if src.life_delta_on_use > 0:
            gain_life(state, src.life_delta_on_use, source=src.label)
        elif src.life_delta_on_use < 0:
            state.life += src.life_delta_on_use

        # Talisman colored mode costs 1 life. Only apply when output was colored.
        if src.label.startswith("Talisman of ") and any(k in COLORS for k in opt):
            state.life -= 1

    if treasure_used:
        state.treasure -= treasure_used
        token_sacrificed(state, "Treasure", treasure_used, strategy)
    if goose_used:
        state.food -= goose_used
        token_sacrificed(state, "Food", goose_used, strategy)


def available_mana_value(state: GameState, strategy: Strategy) -> int:
    # Upper bound used for logging, not payment.
    total = 0
    for src in build_mana_sources(state, strategy):
        total += max((output_total(o) for o in src.options), default=0)
    return total


# ---------------------------------------------------------------------------
# Library manipulation / draw / keywords
# ---------------------------------------------------------------------------

def card_keep_score(card: Card, state: GameState, strategy: Strategy) -> float:
    score = 0.0
    land_count = len(state.lands())
    if card.is_land:
        if land_count < min(state.turn + 1, 5):
            score += 6
        elif land_count >= 7:
            score -= 3
        else:
            score += 1
    else:
        if card.min_cost <= max(2, available_mana_value(state, strategy) + 1):
            score += 2
        if card.roles & {"ramp", "draw", "draw_engine", "tutor", "engine"}:
            score += 2
        if card.roles & ROLE_REACTIVE:
            score -= 0.5
        if card.min_cost >= 7 and state.turn <= 4:
            score -= 2
    return score


def draw_cards(state: GameState, n: int, *, draw_step: bool = False, reason: str = "draw"):
    if n <= 0:
        return
    actual = n
    # Archive replaces each non-draw-step draw with two draws.
    if state.has(ARCHIVE_NAME) and not draw_step:
        actual *= 2
    drawn = []
    for _ in range(min(actual, len(state.library))):
        c = state.library.pop()
        state.hand.append(c)
        drawn.append(c.name)
        state.cards_drawn_total += 1
    if drawn:
        state.log(f"{reason}: drew {', '.join(drawn)}")


def scry(state: GameState, n: int, strategy: Strategy):
    n = min(n, len(state.library))
    if n <= 0:
        return
    state.scry_count += n
    top = [state.library.pop() for _ in range(n)]
    # Cards with negative keep score go to bottom. Keep best cards on top.
    keep = [c for c in top if card_keep_score(c, state, strategy) >= 0]
    bottom = [c for c in top if c not in keep]
    # bottom of library is index 0
    state.library = bottom + state.library
    # best card should be drawn first => append it last
    keep.sort(key=lambda c: card_keep_score(c, state, strategy))
    state.library.extend(keep)
    state.log(f"scry {n}: kept {[c.name for c in keep]}, bottom {[c.name for c in bottom]}")


def surveil(state: GameState, n: int, strategy: Strategy):
    n = min(n, len(state.library))
    if n <= 0:
        return
    state.surveil_count += n
    top = [state.library.pop() for _ in range(n)]
    keep, grave = [], []
    for c in top:
        if card_keep_score(c, state, strategy) >= 0:
            keep.append(c)
        else:
            grave.append(c)
    state.graveyard.extend(grave)
    keep.sort(key=lambda c: card_keep_score(c, state, strategy))
    state.library.extend(keep)
    state.log(f"surveil {n}: kept {[c.name for c in keep]}, grave {[c.name for c in grave]}")


def discard_score(card: Card, state: GameState) -> float:
    # Lower = more disposable.
    score = 0.0
    if card.is_land:
        score += 3 if len(state.lands()) < 5 else -1
    if card.roles & {"tutor", "draw", "draw_engine", "engine", "finisher"}:
        score += 3
    if card.roles & ROLE_REACTIVE:
        score += 0.5
    score -= max(0, card.min_cost - 5) * 0.4
    return score


def connive(state: GameState, n: int, strategy: Strategy, source: Optional[Permanent] = None):
    if n <= 0:
        return
    state.connive_count += n
    # Archive can replace the draws; connive still discards only n.
    draw_cards(state, n, draw_step=False, reason=f"connive {n}")
    for _ in range(min(n, len(state.hand))):
        card = min(state.hand, key=lambda c: discard_score(c, state))
        state.hand.remove(card)
        state.graveyard.append(card)
        if source is not None and not card.is_land:
            source.counters += 1
        state.log(f"connive discard: {card.name}")


# ---------------------------------------------------------------------------
# Life / drains / tokens / ETB
# ---------------------------------------------------------------------------

def check_life_milestones(state: GameState):
    for m in sorted(state.milestones):
        if state.life >= m and state.milestones[m] is None:
            state.milestones[m] = state.turn


def lose_each_opponent(state: GameState, amount: float, source: str = ""):
    if amount <= 0:
        return
    state.opponents = [max(0.0, x - amount) for x in state.opponents]
    if source:
        state.log(f"{source}: each opponent -{amount:g}")
    check_win(state)


def lose_target_opponent(state: GameState, amount: float, source: str = ""):
    if amount <= 0 or not state.opponents:
        return
    # Spread target-drain efficiently: hit the highest-life opponent.
    i = max(range(len(state.opponents)), key=lambda j: state.opponents[j])
    state.opponents[i] = max(0.0, state.opponents[i] - amount)
    if source:
        state.log(f"{source}: target opponent -{amount:g}")
    check_win(state)




def life_replacement_amount(state: GameState, base: float) -> float:
    amount = base
    additions = 0
    multipliers = 1
    # Generic parse of battlefield replacement effects.
    for p in state.battlefield:
        low = strip_reminder_text(p.card.oracle_text).lower()
        if "if you would gain life" not in low:
            continue
        if "that much life plus 1" in low:
            additions += 1
        if "twice that much life" in low:
            multipliers *= 2
    # Affected player chooses order; additions before doublers maximizes life.
    return (amount + additions) * multipliers




def token_sacrificed(state: GameState, token_type: str, n: int = 1, strategy: Optional[Strategy] = None):
    if n <= 0:
        return
    if state.has("Mirkwood Bats"):
        lose_each_opponent(state, n, "Mirkwood Bats")

    # Unlucky Cabbage Merchant triggers once for EACH Food sacrificed.
    if token_type.lower() == "food" and strategy is not None:
        merchants = state.cards_in_play("Unlucky Cabbage Merchant")
        if merchants:
            for _ in range(n):
                put_basic_from_library(state, strategy, set(), tapped=True, source="Unlucky Cabbage Merchant")
            p = merchants[0]
            if p in state.battlefield:
                state.battlefield.remove(p)
                state.library.insert(0, p.card)
                state.log("Unlucky Cabbage Merchant -> bottom of library")


def creature_entry_lifegain_events(state: GameState, count: int, batch_cards: Optional[List[Card]] = None):
    """
    Resolve the generic "another creature enters" / Lumaret triggers for a creature batch.
    batch_cards are already on the battlefield before this function is called.
    """
    batch_cards = batch_cards or []
    batch_names = {c.name for c in batch_cards}

    for p in list(state.battlefield):
        name = p.card.name
        if name == "Bogwater Lumaret":
            # Lumaret sees itself if it was part of the batch.
            events = count
            for _ in range(events):
                gain_life(state, 1, "Bogwater Lumaret")
        elif name in {"Daxos, Blessed by the Sun", "Elas il-Kor, Sadistic Pilgrim", "Prosperous Innkeeper"}:
            events = count - (1 if name in batch_names else 0)
            for _ in range(max(0, events)):
                gain_life(state, 1, name)

    # Corpse Knight sees every "other" creature.
    if state.has("Corpse Knight"):
        events = count - (1 if "Corpse Knight" in batch_names else 0)
        if events > 0:
            lose_each_opponent(state, events, "Corpse Knight")


def choose_thriving_color(card: Card, state: GameState, strategy: Strategy) -> Optional[str]:
    primary = {
        "Thriving Heath": "W", "Thriving Moor": "B", "Thriving Grove": "G",
        "Thriving Isle": "U", "Thriving Bluff": "R",
    }.get(card.name)
    candidates = list((strategy.commander_colors or set(COLORS)) - ({primary} if primary else set()))
    if not candidates:
        return None

    # Prefer colors least represented among current lands.
    counts = Counter()
    for p in state.lands():
        for opt in card_mana_options(p, state, strategy):
            for c in opt:
                if c in COLORS:
                    counts[c] += 1
    return min(candidates, key=lambda c: counts[c])


def create_tokens(
    state: GameState,
    strategy: Strategy,
    token_type: str,
    n: int,
    *,
    creature: bool = False,
    power: float = 1.0,
    toughness: float = 1.0,
    keywords: Optional[Set[str]] = None,
    allow_replacements: bool = True,
):
    if n <= 0:
        return

    foods_extra = 0
    if allow_replacements:
        if state.has("Peregrin Took"):
            foods_extra += 1
        if state.has("Tippy-Toe, Terrific Partner"):
            foods_extra += 1

    total_created = n + foods_extra
    if token_type.lower() == "food":
        state.food += n
    elif token_type.lower() == "treasure":
        state.treasure += n
    elif token_type.lower() == "clue":
        state.clues += n
    elif creature:
        state.creature_tokens.append(TokenGroup(
            name=token_type,
            count=n,
            power=power,
            toughness=toughness,
            keywords=set(keywords or set()),
            entered_turn=state.turn,
        ))

    # Replacement effects add Food to the SAME token-creation event.
    if foods_extra:
        state.food += foods_extra

    state.log(f"create tokens: {n} {token_type}" + (f" + {foods_extra} Food replacement" if foods_extra else ""))

    # Mirkwood Bats triggers once for each token created.
    if state.has("Mirkwood Bats"):
        lose_each_opponent(state, total_created, "Mirkwood Bats")

    # Kambal triggers once per token-enter event.
    if state.has("Kambal, Profiteering Mayor"):
        lose_each_opponent(state, 1, "Kambal, Profiteering Mayor")
        gain_life(state, 1, "Kambal, Profiteering Mayor")

    # Baron triggers only once each turn and creates a separate token event.
    if state.has("Baron Bertram Graywater") and not state.baron_triggered_this_turn:
        state.baron_triggered_this_turn = True
        create_tokens(
            state, strategy, "Vampire Rogue", 1,
            creature=True, power=1, toughness=1, keywords={"lifelink"},
            allow_replacements=True,
        )

    if creature:
        creature_entry_lifegain_events(state, n, batch_cards=[])


def find_basic_for_fetch(state: GameState, allowed: Set[str], strategy: Strategy) -> Optional[Card]:
    candidates = []
    for c in state.library:
        if not c.is_land or "basic land" not in c.type_line.lower():
            continue
        subtypes = {b for b in BASIC_SUBTYPES if b.lower() in c.type_line.lower()}
        if allowed and not (subtypes & allowed):
            continue
        candidates.append(c)

    if not candidates:
        return None

    # Prefer missing/needed commander colors.
    land_color_counts = Counter()
    for p in state.lands():
        for opt in card_mana_options(p, state, strategy):
            for col in opt:
                if col in COLORS:
                    land_color_counts[col] += 1

    def score(c: Card):
        cols = {BASIC_COLOR[b] for b in BASIC_COLOR if b.lower() in c.type_line.lower()}
        missing_bonus = sum(3 for x in cols if land_color_counts[x] == 0)
        green_early = 1 if "G" in cols and state.turn <= 3 else 0
        return missing_bonus + green_early - sum(land_color_counts[x] for x in cols) * 0.1

    return max(candidates, key=score)




def land_enters(state: GameState, strategy: Strategy, card: Card):
    low = strip_reminder_text(card.oracle_text).lower()
    tapped = "this land enters tapped" in low or "enters the battlefield tapped" in low

    # Conditional Gingerbread Cabin.
    if card.name == "Gingerbread Cabin":
        tapped = state.forest_count() < 3

    chosen = choose_thriving_color(card, state, strategy) if card.name.startswith("Thriving ") else None
    perm = Permanent(card=card, entered_turn=state.turn, tapped=tapped, chosen_color=chosen)
    state.battlefield.append(perm)

    # Fetch lands sacrifice themselves and replace the land with a basic.
    fetch_map = {
        "Brokers Hideout": {"Forest", "Plains", "Island"},
        "Riveteers Overlook": {"Swamp", "Mountain", "Forest"},
        "Obscura Storefront": {"Plains", "Island", "Swamp"},
    }
    if card.name in fetch_map:
        state.battlefield.remove(perm)
        state.graveyard.append(card)
        put_basic_from_library(state, strategy, fetch_map[card.name], tapped=True, source=card.name)
        gain_life(state, 1, card.name)
        return

    # Bounce lands.
    if card.name in {"Selesnya Sanctuary", "Golgari Rot Farm", "Orzhov Basilica", "Simic Growth Chamber", "Azorius Chancery", "Rakdos Carnarium", "Gruul Turf", "Boros Garrison", "Dimir Aqueduct", "Izzet Boilerworks"}:
        others = [p for p in state.lands() if p is not perm]
        if others:
            # Prefer a tapped land, then an ETB-value land.
            def bounce_score(p: Permanent):
                etb_value = any(x in p.card.oracle_text.lower() for x in ("when this land enters", "scry"))
                return (1 if p.tapped else 0) + (1 if etb_value else 0)
            target = max(others, key=bounce_score)
        else:
            target = perm
        state.battlefield.remove(target)
        state.hand.append(target.card)
        state.log(f"{card.name}: bounced {target.card.name}")

    # Generic ETB gain.
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).lower()
        m = re.search(r"when this land enters(?: the battlefield)?, you gain (\d+) life", s)
        if m:
            gain_life(state, int(m.group(1)), card.name)

    # Scry on Temple-style lands.
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).lower()
        m = re.search(r"when this land enters(?: the battlefield)?, scry (\d+)", s)
        if m:
            scry(state, int(m.group(1)), strategy)

    # Gingerbread Cabin creates Food only if it entered untapped.
    if card.name == "Gingerbread Cabin" and not tapped:
        create_tokens(state, strategy, "Food", 1)


def own_etb_effects(state: GameState, strategy: Strategy, p: Permanent):
    c = p.card
    low = strip_reminder_text(c.oracle_text).lower()

    # v4.23.0: Doubling Season's "twice that many counters" clause also
    # covers a planeswalker's starting loyalty and a Battle's starting
    # defense (both are "counters put on a permanent" as it enters, and
    # doubling a planeswalker's loyalty this way is Doubling Season's
    # single most famous real-world use case) - Permanent.__post_init__
    # already seeded p.loyalty/p.defense from the printed value with no
    # access to `state`, so the doubling has to happen here instead, the
    # first point in the ETB pipeline that has both.
    if state.has("Doubling Season"):
        if p.loyalty is not None:
            p.loyalty *= 2
        if p.defense is not None:
            p.defense *= 2

    # Exact resource/ramp cards in the current Bilbo deck.
    if c.name == "Prosperous Innkeeper":
        create_tokens(state, strategy, "Treasure", 1)
    elif c.name == "Gilded Goose":
        create_tokens(state, strategy, "Food", 1)
    elif c.name == "Unlucky Cabbage Merchant":
        create_tokens(state, strategy, "Food", 1)
    elif c.name == "Heroic Feast":
        create_tokens(state, strategy, "Food", 1)
    elif c.name == "Field-Tested Frying Pan":
        create_tokens(state, strategy, "Food", 1)
        create_tokens(state, strategy, "Halfling", 1, creature=True, power=1, toughness=1)
    elif c.name == "Heaped Harvest":
        put_basic_from_library(state, strategy, set(), tapped=True, source="Heaped Harvest ETB")

    # Moon-Blessed Cleric: enchantment to top.
    if c.name == "Moon-Blessed Cleric":
        tutor_to_top(state, lambda x: x.is_enchantment, strategy.enchantment_tutor_priority, "Moon-Blessed Cleric")

    # Generic ETB scry/surveil/connive/draw/create token.
    for line in split_oracle_lines(c.oracle_text):
        s = strip_reminder_text(line).strip()
        lowline = s.lower()
        if not (lowline.startswith("when ") and (" enters" in lowline or "enters the battlefield" in lowline)):
            continue
        m = re.search(r"\bscry (\d+)", lowline)
        if m:
            scry(state, int(m.group(1)), strategy)
        m = re.search(r"\bsurveil (\d+)", lowline)
        if m:
            surveil(state, int(m.group(1)), strategy)
        m = re.search(r"\bconnives? ?(\d+)?", lowline)
        if m:
            connive(state, int(m.group(1) or 1), strategy, source=p)
        m = re.search(r"\bdraw (a|one|two|three|\d+) cards?", lowline)
        if m:
            draw_cards(state, parse_number_token(m.group(1)), reason=f"{c.name} ETB")

        # Avoid double-counting the exact cards handled above.
        if c.name not in {"Prosperous Innkeeper", "Gilded Goose", "Unlucky Cabbage Merchant", "Heroic Feast", "Field-Tested Frying Pan"}:
            m = re.search(r"create (a|one|two|three|\d+) (food|treasure|clue) tokens?", lowline)
            if m:
                create_tokens(state, strategy, m.group(2).title(), parse_number_token(m.group(1)))

    # v4.21.0: Devour N ("As this creature enters the battlefield, you may
    # sacrifice any number of creatures. This creature enters the
    # battlefield with N +1/+1 counters on it for each creature devoured
    # this way.") No real Devour card appeared in any of the 14 audited
    # decks, so this is uncalibrated territory - the conservative, honest
    # default: only ever devour creature TOKENS we control (never a real,
    # named creature on the battlefield, which would need a genuine value
    # judgment this engine has no calibration data to make), smallest-power
    # group first so the least combat value is given up. A deck with no
    # spare token creatures out simply devours nothing, same as a player
    # who correctly declines a bad trade.
    m = re.search(r"\bdevour (\d+)\b", low)
    if m and state.creature_tokens:
        multiplier = int(m.group(1))
        devoured = 0
        for g in sorted(state.creature_tokens, key=lambda g: token_group_power(g, state)):
            if g.count <= 0:
                continue
            devoured += g.count
            record_impact(state, c.name, "devoured_tokens", g.count)
            g.count = 0
        if devoured > 0:
            gained = devoured * multiplier
            if state.has("Doubling Season"):
                gained *= 2
            p.counters += gained
            record_impact(state, c.name, "devour_counters", gained)
            state.log(
                f"DEVOUR: {c.name} devoured {devoured} token creature(s) "
                f"-> +{gained}/+{gained}"
            )


def permanent_enters(state: GameState, strategy: Strategy, card: Card):
    p = Permanent(card=card, entered_turn=state.turn, tapped=False)
    state.battlefield.append(p)
    if card.is_creature:
        state.nontoken_creatures_entered_this_turn += 1
        creature_entry_lifegain_events(state, 1, batch_cards=[card])
    own_etb_effects(state, strategy, p)


def batch_creatures_enter(state: GameState, strategy: Strategy, cards: List[Card]):
    if not cards:
        return
    perms = [Permanent(card=c, entered_turn=state.turn, tapped=False) for c in cards]
    state.battlefield.extend(perms)
    state.nontoken_creatures_entered_this_turn += len(cards)
    creature_entry_lifegain_events(state, len(cards), batch_cards=cards)
    for p in perms:
        own_etb_effects(state, strategy, p)


# ---------------------------------------------------------------------------
# Tutors / recursion / spell effects
# ---------------------------------------------------------------------------

def priority_rank(name: str, priority: List[str]) -> int:
    try:
        return len(priority) - priority.index(name)
    except ValueError:
        return 0


def generic_tutor_score(card: Card, priority: List[str]) -> float:
    score = priority_rank(card.name, priority) * 10
    if card.roles & {"finisher", "engine", "draw_engine", "lifegain_replacement"}:
        score += 4
    if card.roles & {"draw", "tutor"}:
        score += 2
    score -= card.min_cost * 0.1
    return score


def tutor_to_hand(state: GameState, predicate, priority: List[str], source: str, count: int = 1):
    candidates = [c for c in state.library if predicate(c)]
    chosen = []
    for _ in range(count):
        if not candidates:
            break
        c = max(candidates, key=lambda x: generic_tutor_score(x, priority))
        candidates.remove(c)
        state.library.remove(c)
        state.hand.append(c)
        chosen.append(c.name)
    if chosen:
        state.log(f"{source} tutor -> hand: {', '.join(chosen)}")


def tutor_to_top(state: GameState, predicate, priority: List[str], source: str):
    candidates = [c for c in state.library if predicate(c)]
    if not candidates:
        return
    c = max(candidates, key=lambda x: generic_tutor_score(x, priority))
    state.library.remove(c)
    state.library.append(c)
    state.log(f"{source} tutor -> top: {c.name}")


def return_from_graveyard_to_hand(state: GameState, predicate, source: str, count: int = 1):
    candidates = [c for c in state.graveyard if predicate(c)]
    for _ in range(min(count, len(candidates))):
        c = max(candidates, key=lambda x: generic_tutor_score(x, DEFAULT_TUTOR_PRIORITY))
        state.graveyard.remove(c)
        state.hand.append(c)
        candidates.remove(c)
        state.log(f"{source}: returned {c.name} to hand")


def resolve_direct_spell_effects(state: GameState, strategy: Strategy, card: Card):
    low = strip_reminder_text(card.oracle_text).lower()

    # Exact current-deck cards first.
    if card.name == "Deadly Dispute":
        # Additional cost should have been paid before casting.
        draw_cards(state, 2, reason="Deadly Dispute")
        create_tokens(state, strategy, "Treasure", 1)
        return

    if card.name == "Farseek":
        put_basic_from_library(state, strategy, {"Plains", "Island", "Swamp", "Mountain"}, tapped=True, source="Farseek")
        return

    if card.name == "Rampant Growth":
        put_basic_from_library(state, strategy, set(), tapped=True, source="Rampant Growth")
        return

    if card.name == "Shared Summons":
        tutor_to_hand(state, lambda x: x.is_creature, strategy.tutor_priority, "Shared Summons", count=2)
        return

    if card.name == "Pulse of Murasa":
        return_from_graveyard_to_hand(state, lambda x: x.is_creature or x.is_land, "Pulse of Murasa", count=1)
        gain_life(state, 6, "Pulse of Murasa")
        return

    if card.name == "Heroes' Reunion":
        gain_life(state, 7, "Heroes' Reunion")
        return

    if card.name == "Elixir of Immortality":
        # Activated ability is handled separately, not on cast.
        return

    if card.name == "Storm Herd":
        n = max(0, int(math.floor(state.life)))
        create_tokens(state, strategy, "Pegasus", n, creature=True, power=1, toughness=1, keywords={"flying"})
        return

    # Generic direct draw.
    n = direct_draw_count(card)
    if n:
        draw_cards(state, n, reason=card.name)

    # Direct scry/surveil/connive.
    n = direct_action_count(card, "scry")
    if n:
        scry(state, n, strategy)
    n = direct_action_count(card, "surveil")
    if n:
        surveil(state, n, strategy)
    n = direct_action_count(card, "connive")
    if n:
        connive(state, n, strategy)

    # Generic direct fixed lifegain sentence.
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).strip().lower()
        if s.startswith(("when ", "whenever ", "at the beginning ", "if ", "as ")):
            continue
        m = re.search(r"\byou gain (\d+) life\b", s)
        if m:
            gain_life(state, int(m.group(1)), card.name)

    # Generic fixed Food/Treasure/Clue creation.
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).strip().lower()
        if s.startswith(("when ", "whenever ", "at the beginning ", "if ", "as ")):
            continue
        m = re.search(r"create (a|one|two|three|four|\d+) (food|treasure|clue) tokens?", s)
        if m:
            create_tokens(state, strategy, m.group(2).title(), parse_number_token(m.group(1)))

    # v4.27.0: generic direct "each/target opponent loses N life" sentence
    # (e.g. a plain Sorcery whose only effect is "Each opponent loses 3
    # life."). Found via ChatGPT external review (Docs/README.md v4.27.0
    # entry): _parse_semantic_actions already recognizes this shape fine
    # (kind="opponent_life_loss", used elsewhere for coverage reporting,
    # which is why such a card was misleadingly marked "exact" model
    # coverage) and a handler for it already exists in
    # App/keyword_library/handlers.py - but nothing on the actual CAST path
    # ever called it: this function only ever hooks up draw / scry-surveil-
    # connive / fixed lifegain / Food-Treasure-Clue creation via its own
    # hardcoded patterns above, so a card whose whole effect was "each
    # opponent loses N life" silently did nothing at all when cast. Not
    # routed through the generic execute_semantic_action/keyword_registry
    # dispatcher here (that dispatcher expects a Permanent `source` and a
    # `target`, neither of which a resolving instant/sorcery has) - same
    # narrow, mirrored-pattern fix as the two generic blocks immediately
    # above it, not a broader unification of this function with the
    # semantic-action dispatcher (a materially bigger change, out of scope
    # for a single evidence-based bug fix).
    for line in split_oracle_lines(card.oracle_text):
        s = strip_reminder_text(line).strip().lower()
        if s.startswith(("when ", "whenever ", "at the beginning ", "if ", "as ")):
            continue
        m = re.search(
            r"\b(each opponent|target opponent) loses (a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+) life\b",
            s,
        )
        if m:
            amount = parse_number_token(m.group(2))
            if m.group(1) == "each opponent":
                lose_each_opponent(state, amount, card.name)
            else:
                lose_target_opponent(state, amount, card.name)


# ---------------------------------------------------------------------------
# Casting decisions
# ---------------------------------------------------------------------------

def is_reactive_only(card: Card, strategy: Strategy) -> bool:
    if card.name in strategy.hold_cards or card.name in strategy.never_cast_goldfish:
        return True
    if card.roles & ROLE_REACTIVE:
        # A creature with an ETB removal ability can still be a proactive body.
        proactive = card.roles & {"ramp", "draw", "draw_engine", "engine", "tutor", "lifegain", "finisher", "token"}
        if not proactive and not card.is_creature:
            return True
        if "boardwipe" in card.roles:
            return True
    return False


def can_pay_additional_cost(card: Card, state: GameState) -> bool:
    low = strip_reminder_text(card.oracle_text).lower()
    if "as an additional cost to cast this spell, sacrifice an artifact or creature" in low:
        return state.food > 0 or state.treasure > 0 or state.clues > 0 or len(state.creatures()) > 0 or any(p.card.is_artifact for p in state.battlefield)
    return True




def cast_score(card: Card, state: GameState, strategy: Strategy) -> float:
    score = 0.0
    if "ramp" in card.roles:
        score += 9 if state.turn <= 4 else 2
    if "burst_mana" in card.roles:
        score += 3 if state.turn <= 4 else 1
    if "draw" in card.roles:
        score += 6
    if "draw_engine" in card.roles:
        score += 5
    if "tutor" in card.roles:
        score += 5
    if "engine" in card.roles:
        score += 4
    if "lifegain" in card.roles:
        score += 2
    if "finisher" in card.roles:
        score += 1 if state.turn <= 4 else 5
    if card.is_creature:
        score += 1.0
    score -= max(0, card.min_cost - 5) * (0.5 if state.turn <= 5 else 0.1)

    # Specific timing.
    if card.name == "Storm Herd":
        score = 12 if state.life >= 30 and available_mana_value(state, strategy) >= 10 else -20
    if card.name == "Deadly Dispute" and len(state.hand) <= 4:
        score += 4
    return score




def try_cast_arkenstone_adventure(state: GameState, strategy: Strategy, card: Card) -> bool:
    if card.name != "The Arkenstone":
        return False
    # Seek the Heart costs 2W. Prefer it if Doctor/Vito/other high-priority legend isn't already accessible.
    if any(c.name in strategy.legendary_tutor_priority[:2] for c in state.hand):
        return False
    req = Counter({"W": 1})
    plan = find_payment(state, strategy, 3, req)
    if not plan:
        return False
    apply_payment(state, plan, strategy)
    state.hand.remove(card)
    tutor_to_hand(
        state,
        lambda x: x.is_creature and "legendary" in x.type_line.lower(),
        strategy.legendary_tutor_priority,
        "Seek the Heart",
        count=1,
    )
    # Adventure: card moves to exile and may later be cast as artifact.
    state.exile.append(card)
    state.log("The Arkenstone -> Adventure exile")
    return True


def try_cast_adventure_permanent_from_exile(state: GameState, strategy: Strategy) -> bool:
    card = next((c for c in state.exile if c.name == "The Arkenstone"), None)
    if not card:
        return False
    plan = find_payment(state, strategy, 5, Counter())
    if not plan:
        return False
    apply_payment(state, plan, strategy)
    state.exile.remove(card)
    permanent_enters(state, strategy, card)
    state.log("CAST The Arkenstone from Adventure exile")
    return True


def cast_commander_if_good(state: GameState, strategy: Strategy) -> bool:
    if not state.command_zone:
        return False
    commander = state.command_zone[0]
    cost = commander.min_cost + 2 * state.commander_casts
    plan = find_payment(state, strategy, cost, commander.color_requirements)
    if not plan:
        return False

    # Prioritize early ramp over commander if mana cannot do both.
    cheap_ramp = [
        c for c in state.hand
        if "ramp" in c.roles and c.min_cost <= 2 and not is_reactive_only(c, strategy)
    ]
    if state.turn <= 2 and cheap_ramp:
        return False

    apply_payment(state, plan, strategy)
    state.command_zone.pop(0)
    state.commander_casts += 1
    permanent_enters(state, strategy, commander)
    state.log(f"CAST COMMANDER {commander.name}")
    return True


# ---------------------------------------------------------------------------
# Activated resources / end step / combat
# ---------------------------------------------------------------------------

def sacrifice_food_for_life(state: GameState, strategy: Strategy) -> bool:
    if state.food <= 0:
        return False
    plan = find_payment(state, strategy, 2, Counter())
    if not plan:
        return False
    apply_payment(state, plan, strategy)
    state.food -= 1
    token_sacrificed(state, "Food", 1, strategy)
    gain_life(state, 3, "Food")
    state.log("Food sacrificed for life")
    return True


def use_lobelia(state: GameState, strategy: Strategy) -> bool:
    lobelias = [p for p in state.cards_in_play("Lobelia, Defender of Bag End") if not p.tapped and not (p.entered_turn == state.turn and "haste" not in p.card.keywords)]
    if not lobelias:
        return False
    if state.food + state.treasure + state.clues <= 0:
        return False
    p = lobelias[0]
    p.tapped = True
    if state.food > 0:
        state.food -= 1
        token_sacrificed(state, "Food", 1, strategy)
    elif state.clues > 0:
        state.clues -= 1
        token_sacrificed(state, "Clue", 1, strategy)
    else:
        state.treasure -= 1
        token_sacrificed(state, "Treasure", 1, strategy)
    lose_each_opponent(state, 2, "Lobelia")
    gain_life(state, 2, "Lobelia")
    return True


def use_peregrin_draw(state: GameState, strategy: Strategy) -> bool:
    if not state.has("Peregrin Took") or state.food < 3:
        return False
    state.food -= 3
    token_sacrificed(state, "Food", 3, strategy)
    draw_cards(state, 1, reason="Peregrin Took")
    return True




def use_elixir(state: GameState, strategy: Strategy) -> bool:
    ps = [p for p in state.cards_in_play("Elixir of Immortality") if not p.tapped]
    if not ps or len(state.graveyard) < 5:
        return False
    plan = find_payment(state, strategy, 2, Counter())
    if not plan:
        return False
    apply_payment(state, plan, strategy)
    p = ps[0]
    p.tapped = True
    gain_life(state, 5, "Elixir of Immortality")
    # Shuffle graveyard + Elixir into library.
    state.battlefield.remove(p)
    cards = state.graveyard + [p.card]
    state.graveyard.clear()
    state.library.extend(cards)
    random.shuffle(state.library)
    state.log("Elixir shuffled graveyard into library")
    return True


def use_heaped_harvest(state: GameState, strategy: Strategy) -> bool:
    ps = [p for p in state.cards_in_play("Heaped Harvest") if not p.tapped]
    if not ps:
        return False
    plan = find_payment(state, strategy, 2, Counter())
    if not plan:
        return False
    apply_payment(state, plan, strategy)
    p = ps[0]
    if p not in state.battlefield:
        return False
    state.battlefield.remove(p)
    state.graveyard.append(p.card)
    # Heaped Harvest is a Food artifact but NOT a token, so Mirkwood Bats does not trigger.
    gain_life(state, 3, "Heaped Harvest")
    put_basic_from_library(state, strategy, set(), tapped=True, source="Heaped Harvest sacrifice")
    state.log("Heaped Harvest sacrificed")
    return True

def use_well_of_lost_dreams(state: GameState, strategy: Strategy):
    # Each lifegain event creates its own trigger with X <= amount gained.
    # With all other proactive actions already finished, total spare mana can be allocated
    # across those triggers. Paying a combined X is equivalent for goldfish draw totals.
    if not state.has("Well of Lost Dreams") or not state.well_caps_this_turn:
        return
    max_x = int(sum(state.well_caps_this_turn))
    # Safety cap keeps pathological replacement chains from making logs enormous.
    max_x = min(max_x, 12)
    for x in range(max_x, 0, -1):
        plan = find_payment(state, strategy, x, Counter())
        if plan:
            apply_payment(state, plan, strategy)
            draw_cards(state, x, reason="Well of Lost Dreams")
            break


def use_trudge_garden(state: GameState, strategy: Strategy):
    """v4.15.6. Trudge Garden ("Whenever you gain life, you may pay {2}. If
    you do, create a 4/4 green Fungus Beast creature token with trample.") -
    one independent optional payment per lifegain event this turn
    (state.trudge_garden_triggers_this_turn, incremented in gain_life),
    each resolved against actual spare mana via find_payment - same
    end-of-step "spend what's left" pattern as use_well_of_lost_dreams
    above, not a single assumed-affordable flat cost. Closes the "repeated
    {2}->4/4 lifegain-trigger decisions are not yet fully modeled" gap
    (KNOWN_COVERAGE_NOTES)."""
    if not state.has("Trudge Garden"):
        return
    # Safety cap: a pathological number of lifegain events in one turn
    # shouldn't spawn dozens of tokens or dominate the log.
    triggers = min(int(state.trudge_garden_triggers_this_turn), 8)
    for _ in range(triggers):
        plan = find_payment(state, strategy, 2, Counter())
        if not plan:
            break
        apply_payment(state, plan, strategy)
        create_tokens(
            state, strategy, "Fungus Beast", 1,
            creature=True, power=4, toughness=4,
            keywords={"trample"}, source="Trudge Garden",
        )
        record_impact(state, "Trudge Garden", "token_multiplier", 1)


def use_baron_bertram_sac_draw(state: GameState, strategy: Strategy):
    """v4.15.6. Baron Bertram Graywater's second ability ("{1}{B}, Sacrifice
    another creature or artifact: Draw a card.") - his token-enter Vampire
    generation (first ability) was already modeled; this closes the
    "activated sacrifice-to-draw line is not fully optimized" gap
    (KNOWN_COVERAGE_NOTES), narrowly: converts a genuinely leftover, unspent
    Treasure token (an artifact, valid sacrifice fodder) into a card when
    {1}{B} can still be paid from remaining mana. Deliberately does NOT
    sacrifice creatures or Food for this - Food already has its own
    life-gain economy (sacrifice_food_for_life/_use_food_to_life_target) and
    creatures are board presence/attackers, both real strategic trade-offs a
    bare end-of-turn heuristic shouldn't make casually; an unused Treasure
    still sitting in play at end of turn is unambiguous excess."""
    if not state.has("Baron Bertram Graywater") or state.treasure <= 0:
        return
    plan = find_payment(state, strategy, 2, Counter({"B": 1}))
    if not plan:
        return
    apply_payment(state, plan, strategy)
    state.treasure -= 1
    token_sacrificed(state, "Treasure", 1, strategy)
    draw_cards(state, 1, reason="Baron Bertram Graywater sacrifice")
    record_impact(state, "Baron Bertram Graywater", "card_advantage", 1)


def end_step(state: GameState, strategy: Strategy):
    # Gyome.
    if state.has("Gyome, Master Chef") and state.nontoken_creatures_entered_this_turn > 0:
        create_tokens(state, strategy, "Food", state.nontoken_creatures_entered_this_turn)

    # Tippy-Toe.
    if state.has("Tippy-Toe, Terrific Partner") and state.gained_life_this_turn:
        draw_cards(state, 1, reason="Tippy-Toe end step")

    # The Arkenstone artifact side.
    if state.has("The Arkenstone"):
        draw_cards(state, 1, reason="The Arkenstone end step")

    # Use resource engines with leftover mana.
    use_well_of_lost_dreams(state, strategy)

    # Lobelia is free and usually better than normal Food activation in goldfish.
    use_lobelia(state, strategy)

    # Heaped Harvest converts spare mana into both life and a real land.
    use_heaped_harvest(state, strategy)

    # If the hand is nearly empty, Peregrin may be worth using even before 111.
    if len(state.hand) <= 2:
        use_peregrin_draw(state, strategy)

    # If life is below the configured threshold, spend spare mana on a few Foods.
    food_uses = 0
    while state.life < strategy.prefer_food_for_life_until and food_uses < strategy.max_food_activations_per_turn:
        if not sacrifice_food_for_life(state, strategy):
            break
        food_uses += 1

    # Above 111, prefer converting excess Food to cards.
    if state.life >= strategy.prefer_food_for_life_until:
        use_peregrin_draw(state, strategy)
        use_clue(state, strategy)


def creature_power(p: Permanent, state: GameState) -> float:
    power = p.card.power or 0.0
    power += p.counters
    if state.has("The Arkenstone"):
        power += 1
    # Doctor Strange buff.
    if state.has(DOCTOR_STRANGE_NAME) and state.life >= 50:
        power += 2
    return max(0.0, power)


def token_group_power(g: TokenGroup, state: GameState) -> float:
    p = g.power
    if state.has("The Arkenstone"):
        p += 1
    if state.has(DOCTOR_STRANGE_NAME) and state.life >= 50:
        p += 2
    # v4.15.6: Field-Tested Frying Pan's equipped-creature lifegain pump
    # (see gain_life) - applies only to the specific Halfling token it
    # created and attached to, until end of turn.
    if g.name == "Halfling" and state.has("Field-Tested Frying Pan"):
        p += getattr(state, "frying_pan_bonus_this_turn", 0.0)
    return max(0.0, p)


def attack_phase(state: GameState, strategy: Strategy):
    if state.win_turn is not None:
        return

    attackers: List[Tuple[str, float, bool]] = []

    for p in state.creatures():
        if p.tapped:
            continue
        if "defender" in p.card.keywords:
            continue
        if p.entered_turn == state.turn and "haste" not in p.card.keywords:
            continue
        power = creature_power(p, state)
        if power <= 0:
            continue
        lifelink = "lifelink" in p.card.keywords
        attackers.append((p.card.name, power, lifelink))
        if "vigilance" not in p.card.keywords:
            idx = state.battlefield.index(p)
            tap_permanent(state, strategy, idx, reason="attack")

    for g in state.creature_tokens:
        if g.count <= 0 or (g.entered_turn == state.turn and "haste" not in g.keywords):
            continue
        power = token_group_power(g, state)
        if power <= 0:
            continue
        # Aggregate the group.
        attackers.append((g.name, power * g.count, "lifelink" in g.keywords))

    if not attackers:
        return

    # Generic attack-trigger keyword actions: connive/scry/surveil/draw.
    for p in list(state.creatures()):
        if p.entered_turn == state.turn and "haste" not in p.card.keywords:
            continue
        if p.card.name not in {name for name, _, _ in attackers}:
            continue
        for line in split_oracle_lines(p.card.oracle_text):
            low = strip_reminder_text(line).lower()
            if "attacks" not in low or not low.startswith("whenever"):
                continue
            m = re.search(r"connives? ?(\d+)?", low)
            if m:
                connive(state, int(m.group(1) or 1), strategy, source=p)
            m = re.search(r"scry (\d+)", low)
            if m:
                scry(state, int(m.group(1)), strategy)
            m = re.search(r"surveil (\d+)", low)
            if m:
                surveil(state, int(m.group(1)), strategy)
            m = re.search(r"draw (a|one|two|three|\d+) cards?", low)
            if m:
                draw_cards(state, parse_number_token(m.group(1)), reason=f"{p.card.name} attack")

    # Blossoming Bogbeast attack trigger.
    bog_attackers = sum(1 for name, _, _ in attackers if name == "Blossoming Bogbeast")
    if bog_attackers:
        for _ in range(bog_attackers):
            gained = gain_life(state, 2, "Blossoming Bogbeast attack")
            # Approximate +X/+X to all attackers for this combat.
            attackers = [(n, pwr + gained, ll) for n, pwr, ll in attackers]

    # Spread combat damage among highest-life opponents.
    for name, damage, lifelink in attackers:
        if not state.opponents:
            break
        i = max(range(len(state.opponents)), key=lambda j: state.opponents[j])
        state.opponents[i] = max(0.0, state.opponents[i] - damage)
        if lifelink:
            gain_life(state, damage, f"{name} lifelink")
    check_win(state)


# ---------------------------------------------------------------------------
# Bilbo activation
# ---------------------------------------------------------------------------

def try_activate_bilbo(state: GameState, strategy: Strategy) -> bool:
    if state.bilbo_activation_turn is not None or state.life < 111:
        return False
    bilbos = [p for p in state.cards_in_play(BILBO_NAME) if not p.tapped and not (p.entered_turn == state.turn and "haste" not in p.card.keywords)]
    if not bilbos:
        return False

    # Ability costs 2WBG and tap/exile Bilbo.
    plan = find_payment(state, strategy, 5, Counter({"W": 1, "B": 1, "G": 1}))
    if not plan:
        return False

    apply_payment(state, plan, strategy)
    bilbo = bilbos[0]
    state.battlefield.remove(bilbo)
    state.exile.append(bilbo.card)

    available_by_name = {c.name: c for c in state.library if c.is_creature}
    chosen = []
    for name in strategy.bilbo_pile:
        c = available_by_name.get(name)
        if c and c not in chosen:
            chosen.append(c)

    # If the configured pile is sparse, add strong creature payoffs.
    if len(chosen) < 5:
        remaining = [c for c in state.library if c.is_creature and c not in chosen]
        remaining.sort(key=lambda c: generic_tutor_score(c, strategy.tutor_priority), reverse=True)
        chosen.extend(remaining[:max(0, 8-len(chosen))])

    for c in chosen:
        state.library.remove(c)

    state.bilbo_activation_turn = state.turn
    state.log(f"BILBO ACTIVATE: {len(chosen)} creatures -> battlefield")
    batch_creatures_enter(state, strategy, chosen)
    check_win(state)
    return True


# ---------------------------------------------------------------------------
# Mulligan / land choice / simulation
# ---------------------------------------------------------------------------

@dataclass
class MulliganPolicy:
    min_lands: int = 2
    max_lands: int = 5
    max_avg_nonland_mv: float = 4.25


@dataclass
class SimConfig:
    runs: int = 5000
    turns: int = 10
    seed: int = 1
    starting_life: int = 40
    free_mulligan: bool = True
    max_mulligans: int = 4


def opening_metrics(hand: Sequence[Card]) -> dict:
    lands = [c for c in hand if c.is_land]
    spells = [c for c in hand if not c.is_land]
    cheap = [c for c in spells if c.min_cost <= 3]
    early_ramp = [c for c in spells if "ramp" in c.roles and c.min_cost <= 3]
    avg_mv = statistics.mean([c.min_cost for c in spells]) if spells else 0.0
    return {
        "lands": len(lands),
        "cheap": len(cheap),
        "ramp": len(early_ramp),
        "avg_mv": avg_mv,
    }


def keep_hand(hand: Sequence[Card], policy: MulliganPolicy) -> Tuple[bool, List[str]]:
    m = opening_metrics(hand)
    reasons = []
    if m["lands"] < policy.min_lands:
        reasons.append("too_few_lands")
    if m["lands"] > policy.max_lands:
        reasons.append("too_many_lands")
    if m["lands"] <= 3 and m["cheap"] == 0:
        reasons.append("no_early_play")
    if m["avg_mv"] > policy.max_avg_nonland_mv and m["ramp"] == 0:
        reasons.append("too_expensive")
    if m["lands"] == 2 and m["cheap"] + m["ramp"] < 2:
        reasons.append("fragile_two_land_hand")
    return len(reasons) == 0, reasons


def hand_quality(hand: Sequence[Card]) -> float:
    m = opening_metrics(hand)
    score = 0.0
    score += 5 if 2 <= m["lands"] <= 4 else -5
    score += min(m["cheap"], 3)
    score += min(m["ramp"], 2) * 1.5
    score -= max(0, m["avg_mv"] - 4) * 0.5
    return score


def london_mulligan(library: List[Card], policy: MulliganPolicy, cfg: SimConfig, rng: random.Random):
    history = []
    mulligans = 0
    while True:
        deck = library[:]
        rng.shuffle(deck)
        hand, rest = deck[:7], deck[7:]
        keep, reasons = keep_hand(hand, policy)
        history.append(f"M{mulligans}: {' | '.join(c.name for c in hand)} -> {'KEEP' if keep else 'MULL ' + ','.join(reasons)}")
        if keep or mulligans >= cfg.max_mulligans:
            bottoms = max(0, mulligans - (1 if cfg.free_mulligan and mulligans > 0 else 0))
            for _ in range(min(bottoms, len(hand))):
                best_i = 0
                best_score = -10**9
                for i in range(len(hand)):
                    trial = hand[:i] + hand[i+1:]
                    sc = hand_quality(trial)
                    if sc > best_score:
                        best_score = sc
                        best_i = i
                rest.insert(0, hand.pop(best_i))
            return hand, rest, mulligans, history
        mulligans += 1


def land_score(card: Card, state: GameState, strategy: Strategy) -> float:
    score = 0.0
    if card.name == "Selesnya Sanctuary" and len(state.lands()) == 0:
        return -100
    if "this land enters tapped" not in card.oracle_text.lower():
        score += 2
    # Missing color value.
    represented = set()
    for p in state.lands():
        for opt in card_mana_options(p, state, strategy):
            represented.update(k for k in opt if k in COLORS)
    possible = set(card.produced_mana) | {k for o in parse_add_mana_options(card.oracle_text) for k in o if k in COLORS}
    score += sum(3 for c in possible if c in strategy.commander_colors and c not in represented)
    # Early green is valuable for many Commander decks with green ramp.
    if state.turn <= 2 and "G" in possible:
        score += 1
    # ETB value.
    if "you gain 1 life" in card.oracle_text.lower() or "scry 1" in card.oracle_text.lower():
        score += 0.5
    return score


def choose_land(state: GameState, strategy: Strategy) -> Optional[Card]:
    lands = [c for c in state.hand if c.is_land]
    if not lands:
        return None
    return max(lands, key=lambda c: land_score(c, state, strategy))


def color_access(state: GameState, strategy: Strategy) -> Set[str]:
    out = set()
    for src in build_mana_sources(state, strategy):
        for opt in src.options:
            out.update(c for c in opt if c in COLORS)
    return out


def hold_reactive_count(state: GameState, strategy: Strategy) -> int:
    return sum(is_reactive_only(c, strategy) for c in state.hand)


def untap_step(state: GameState):
    for p in state.battlefield:
        p.tapped = False


def simulate_game(
    deck: List[Card],
    strategy_template: Strategy,
    cfg: SimConfig,
    policy: MulliganPolicy,
    rng: random.Random,
    run_id: int,
):
    commanders = [c for c in deck if c.commander]
    commander = commanders[0] if commanders else None
    library = deck[:]
    if commander:
        library.remove(commander)

    hand, rest, mulligans, mull_history = london_mulligan(library, policy, cfg, rng)
    rng.shuffle(rest)

    strategy = replace(strategy_template)
    if commander and not strategy.commander_colors:
        strategy.commander_colors = set(commander.color_identity)

    state = GameState(
        library=rest,
        hand=hand[:],
        command_zone=[commander] if commander else [],
        life=cfg.starting_life,
    )
    opening_hand = [c.name for c in hand]
    turn_rows = []

    for turn in range(1, cfg.turns + 1):
        state.turn = turn
        state.nontoken_creatures_entered_this_turn = 0
        state.gained_life_this_turn = False
        state.baron_triggered_this_turn = False
        state.life_events_this_turn = 0
        state.well_caps_this_turn = []
        state.trudge_garden_triggers_this_turn = 0
        state.frying_pan_bonus_this_turn = 0.0
        state.event_log = []
        untap_step(state)

        # Normal draw step is never doubled by Archive's "except first draw in draw step" clause.
        draw_cards(state, 1, draw_step=True, reason="draw step")

        start_hand = [c.name for c in state.hand]

        # Land drop.
        land = choose_land(state, strategy)
        land_name = ""
        if land:
            state.hand.remove(land)
            land_name = land.name
            land_enters(state, strategy, land)

        # Main phase: early ramp first, then commander/engines.
        cast_this_turn = []

        # Arkenstone Adventure can be the intended early half.
        arken = next((c for c in state.hand if c.name == "The Arkenstone"), None)
        if arken and try_cast_arkenstone_adventure(state, strategy, arken):
            cast_this_turn.append("Seek the Heart")

        # Greedy proactive casts.
        safety = 0
        while safety < 20:
            safety += 1
            candidates = [
                c for c in state.hand
                if not c.is_land
                and not is_reactive_only(c, strategy)
                and can_pay_additional_cost(c, state)
                and find_payment(state, strategy, c.min_cost, c.color_requirements) is not None
            ]
            if not candidates:
                break

            # Avoid casting The Arkenstone artifact if it is still better as Adventure and Adventure was impossible only due mana.
            candidates.sort(key=lambda c: cast_score(c, state, strategy), reverse=True)
            c = candidates[0]
            if cast_score(c, state, strategy) < 0:
                break
            if try_cast_card(state, strategy, c):
                cast_this_turn.append(c.name)
            else:
                break

        # Adventure cards may now be cast from exile on their permanent half.
        if try_cast_adventure_permanent_from_exile(state, strategy):
            cast_this_turn.append("The Arkenstone(from exile)")

        # Cast commander after efficient development if still possible.
        if cast_commander_if_good(state, strategy):
            cast_this_turn.append(f"Commander:{commander.name if commander else ''}")

        # Bilbo activation before combat if possible. Bilbo must not be summoning sick because activation has {T}.
        try_activate_bilbo(state, strategy)

        # Combat.
        attack_phase(state, strategy)

        # Second main: one more pass for cheap proactive cards.
        safety = 0
        while safety < 10:
            safety += 1
            candidates = [
                c for c in state.hand
                if not c.is_land
                and not is_reactive_only(c, strategy)
                and can_pay_additional_cost(c, state)
                and find_payment(state, strategy, c.min_cost, c.color_requirements) is not None
            ]
            if not candidates:
                break
            candidates.sort(key=lambda c: cast_score(c, state, strategy), reverse=True)
            c = candidates[0]
            if cast_score(c, state, strategy) < 1:
                break
            if try_cast_card(state, strategy, c):
                cast_this_turn.append(c.name)
            else:
                break

        # Bilbo can also activate in second main if we crossed 111 during combat.
        try_activate_bilbo(state, strategy)

        end_step(state, strategy)
        try_activate_bilbo(state, strategy)

        reactive_held = hold_reactive_count(state, strategy)
        state.reactive_held_total += reactive_held
        access = color_access(state, strategy)

        turn_rows.append({
            "run": run_id,
            "turn": turn,
            "start_hand": " | ".join(start_hand),
            "land_played": land_name,
            "casts": " | ".join(cast_this_turn),
            "events": " || ".join(state.event_log),
            "end_hand": " | ".join(c.name for c in state.hand),
            "hand_size": len(state.hand),
            "lands_in_play": len(state.lands()),
            "available_mana_after_actions": available_mana_value(state, strategy),
            "color_access": "".join(c for c in COLORS if c in access),
            "has_all_commander_colors": int(bool(strategy.commander_colors) and strategy.commander_colors <= access),
            "life": round(state.life, 2),
            "opponent_life": " | ".join(str(round(x, 2)) for x in state.opponents),
            "food": state.food,
            "treasure": state.treasure,
            "clues": state.clues,
            "reactive_cards_held": reactive_held,
            "life_events_this_turn": state.life_events_this_turn,
            "bilbo_activated": int(state.bilbo_activation_turn == turn),
            "win": int(state.win_turn == turn),
        })

    run_row = {
        "run": run_id,
        "mulligans": mulligans,
        "opening_hand": " | ".join(opening_hand),
        "opening_land_count": sum(c.is_land for c in hand),
        "opening_cheap_spells": sum((not c.is_land) and c.min_cost <= 3 for c in hand),
        "opening_early_ramp": sum("ramp" in c.roles and c.min_cost <= 3 for c in hand),
        "lands_end": len(state.lands()),
        "hand_size_end": len(state.hand),
        "life_end": round(state.life, 2),
        "food_end": state.food,
        "treasure_end": state.treasure,
        "cards_drawn_total": state.cards_drawn_total,
        "scry_count": state.scry_count,
        "surveil_count": state.surveil_count,
        "connive_count": state.connive_count,
        "bilbo_activation_turn": state.bilbo_activation_turn or "",
        "win_turn": state.win_turn or "",
        "opponents_remaining": sum(x > 0 for x in state.opponents),
        "life_50_turn": state.milestones[50] or "",
        "life_60_turn": state.milestones[60] or "",
        "life_80_turn": state.milestones[80] or "",
        "life_100_turn": state.milestones[100] or "",
        "life_111_turn": state.milestones[111] or "",
        "reactive_held_total_turn_snapshots": state.reactive_held_total,
    }
    opening_row = {
        "run": run_id,
        "mulligans": mulligans,
        "opening_hand": " | ".join(opening_hand),
        "mulligan_history": " || ".join(mull_history),
    }
    return run_row, turn_rows, opening_row


# ---------------------------------------------------------------------------
# Build deck / outputs / summary
# ---------------------------------------------------------------------------

def build_deck(
    input_path: Path,
    commander_name: Optional[str],
    cache_path: Path,
    offline: bool,
    metadata_csv: Optional[Path],
) -> List[Card]:
    fmt = detect_input_format(input_path)
    cols = {}
    if fmt == "txt":
        entries = load_txt_entries(input_path)
    else:
        entries, cols = load_csv_entries(input_path)

    offline_meta = load_metadata_csv(metadata_csv) if metadata_csv else {}

    need_online = []
    base_cards: Dict[str, Card] = {}
    for e in entries:
        m = offline_meta.get(e.name.casefold())
        if m:
            c = replace(
                m,
                name=e.name,
                commander=(e.name == commander_name),
                set_code=e.set_code or m.set_code,
                collector_number=e.collector_number or m.collector_number,
            )
            base_cards[ScryfallProvider.key(e)] = c
        elif fmt == "csv" and e.row_data and cols.get("type") and cols.get("text"):
            base_cards[ScryfallProvider.key(e)] = card_from_local_csv(e, cols, commander_name)
        else:
            need_online.append(e)

    if need_online:
        provider = ScryfallProvider(cache_path, offline=offline)
        objs = provider.get_many(need_online)
        for e in need_online:
            obj = objs.get(ScryfallProvider.key(e))
            if not obj:
                raise RuntimeError(f"No metadata for {e.name}")
            base_cards[ScryfallProvider.key(e)] = card_from_scryfall(e, obj, commander_name)

    deck = []
    for e in entries:
        c = base_cards[ScryfallProvider.key(e)]
        c = enrich_semantics(c)
        for _ in range(e.count):
            deck.append(c)
    return deck


def write_csv(path: Path, rows: List[dict]):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_enriched(path: Path, deck: List[Card]):
    counts = Counter(c.name for c in deck)
    first = {}
    for c in deck:
        first.setdefault(c.name, c)
    rows = []
    for name in sorted(first):
        c = first[name]
        rows.append({
            "Quantity": counts[name],
            "Name": c.name,
            "Set": c.set_code,
            "Collector Number": c.collector_number,
            "Commander": c.commander,
            "Mana Cost": c.mana_cost,
            "Mana Value": c.mana_value,
            "Type Line": c.type_line,
            "Power": "" if c.power is None else c.power,
            "Toughness": "" if c.toughness is None else c.toughness,
            "Color Identity": "".join(sorted(c.color_identity)),
            "Produced Mana": "".join(sorted(c.produced_mana)),
            "Keywords": "|".join(sorted(c.keywords)),
            "Roles": "|".join(sorted(c.roles)),
            "Direct Draw": direct_draw_count(c),
            "Direct Scry": direct_action_count(c, "scry"),
            "Direct Surveil": direct_action_count(c, "surveil"),
            "Direct Connive": direct_action_count(c, "connive"),
            "Oracle Text": c.oracle_text.replace("\n", " / "),
            "Metadata Source": c.metadata_source,
        })
    write_csv(path, rows)


def pct_with_value(rows: List[dict], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if str(r.get(key, "")).strip() not in {"", "0", "0.0"}) / len(rows) * 100


def mean_numeric(rows: List[dict], key: str) -> float:
    vals = []
    for r in rows:
        try:
            vals.append(float(r[key]))
        except (ValueError, TypeError, KeyError):
            pass
    return statistics.mean(vals) if vals else 0.0


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    pos = (len(xs)-1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi]-xs[lo]) * (pos-lo)


def summarize(deck: List[Card], run_rows: List[dict], turn_rows: List[dict], cfg: SimConfig) -> dict:
    commander = next((c for c in deck if c.commander), None)
    lands = sum(c.is_land for c in deck)
    roles = Counter(role for c in deck for role in c.roles)
    keywords = Counter(kw for c in deck for kw in c.keywords)
    pips = Counter()
    curve = Counter()
    for c in deck:
        if not c.is_land:
            curve[int(math.ceil(c.mana_value))] += 1
            pips.update(c.color_requirements)

    by_turn = {}
    for t in range(1, cfg.turns+1):
        rows = [r for r in turn_rows if int(r["turn"]) == t]
        by_turn[str(t)] = {
            "avg_hand_size": mean_numeric(rows, "hand_size"),
            "avg_life": mean_numeric(rows, "life"),
            "avg_lands": mean_numeric(rows, "lands_in_play"),
            "all_commander_colors_pct": mean_numeric(rows, "has_all_commander_colors") * 100,
            "avg_food": mean_numeric(rows, "food"),
            "win_pct_this_turn": mean_numeric(rows, "win") * 100,
            "bilbo_activation_pct_this_turn": mean_numeric(rows, "bilbo_activated") * 100,
        }

    win_turns = [float(r["win_turn"]) for r in run_rows if str(r["win_turn"]).strip()]
    bilbo_turns = [float(r["bilbo_activation_turn"]) for r in run_rows if str(r["bilbo_activation_turn"]).strip()]

    return {
        "version": 3,
        "simulation": {"runs": cfg.runs, "turns": cfg.turns, "seed": cfg.seed},
        "deck": {
            "cards": len(deck),
            "commander": commander.name if commander else None,
            "lands": lands,
            "curve": dict(sorted(curve.items())),
            "colored_pips": dict(pips),
            "role_counts": dict(roles),
            "keyword_counts": dict(keywords),
        },
        "opening": {
            "avg_mulligans": mean_numeric(run_rows, "mulligans"),
            "avg_opening_lands": mean_numeric(run_rows, "opening_land_count"),
            "avg_opening_early_ramp": mean_numeric(run_rows, "opening_early_ramp"),
        },
        "outcomes": {
            "win_by_turn_limit_pct": pct_with_value(run_rows, "win_turn"),
            "median_win_turn_when_winning": percentile(win_turns, .5) if win_turns else None,
            "bilbo_activation_pct": pct_with_value(run_rows, "bilbo_activation_turn"),
            "median_bilbo_activation_turn": percentile(bilbo_turns, .5) if bilbo_turns else None,
            "reach_50_life_pct": pct_with_value(run_rows, "life_50_turn"),
            "reach_60_life_pct": pct_with_value(run_rows, "life_60_turn"),
            "reach_80_life_pct": pct_with_value(run_rows, "life_80_turn"),
            "reach_100_life_pct": pct_with_value(run_rows, "life_100_turn"),
            "reach_111_life_pct": pct_with_value(run_rows, "life_111_turn"),
            "avg_end_hand": mean_numeric(run_rows, "hand_size_end"),
            "avg_end_life": mean_numeric(run_rows, "life_end"),
            "avg_cards_drawn": mean_numeric(run_rows, "cards_drawn_total"),
            "avg_scry": mean_numeric(run_rows, "scry_count"),
            "avg_surveil": mean_numeric(run_rows, "surveil_count"),
            "avg_connive": mean_numeric(run_rows, "connive_count"),
        },
        "by_turn": by_turn,
        "limitations": [
            "No opponent interaction, blockers, removal, graveyard hate or counterspells are simulated.",
            "Ward/hexproof/indestructible are recognized and reported but have little effect in pure goldfish mode.",
            "The combat model assumes no blockers and uses simplified power for characteristic-defining abilities.",
            "Generic tutor and resource choices are heuristic; use --strategy for deck-specific priorities.",
            "This is not a comprehensive Magic rules engine."
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v3")
    ap.add_argument("deck_file", type=Path)
    ap.add_argument("--commander", default=None)
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None,
                    help="Use an existing enriched CSV as an offline metadata source.")
    ap.add_argument("--strategy", type=Path, default=None,
                    help="Optional deck-specific strategy JSON.")
    ap.add_argument("--output-prefix", type=Path, default=None)
    args = ap.parse_args()

    cache = args.cache or (Path(__file__).resolve().parent / ".scryfall_card_cache_v3.json")
    deck = build_deck(
        args.deck_file,
        commander_name=args.commander,
        cache_path=cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
    )

    if len(deck) != 100:
        print(f"NOTE: loaded {len(deck)} cards; Commander decks normally contain 100 total.")

    commander = next((c for c in deck if c.commander), None)
    strategy = load_strategy(args.strategy, commander)
    cfg = SimConfig(runs=args.runs, turns=args.turns, seed=args.seed)
    policy = MulliganPolicy()
    rng = random.Random(args.seed)

    run_rows, turn_rows, opening_rows = [], [], []
    for run_id in range(1, args.runs+1):
        rr, tr, oh = simulate_game(deck, strategy, cfg, policy, rng, run_id)
        run_rows.append(rr)
        turn_rows.extend(tr)
        opening_rows.append(oh)

    prefix = Path(args.output_prefix or args.deck_file.with_suffix(""))
    enriched = prefix.parent / f"{prefix.name}_v3_enriched.csv"
    summary = prefix.parent / f"{prefix.name}_v3_goldfish_summary.json"
    runs = prefix.parent / f"{prefix.name}_v3_goldfish_runs.csv"
    turns = prefix.parent / f"{prefix.name}_v3_goldfish_turns.csv"
    openings = prefix.parent / f"{prefix.name}_v3_goldfish_opening_hands.csv"

    write_enriched(enriched, deck)
    write_csv(runs, run_rows)
    write_csv(turns, turn_rows)
    write_csv(openings, opening_rows)
    data = summarize(deck, run_rows, turn_rows, cfg)
    summary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nGoldfish v3 complete")
    print("Enriched:", enriched)
    print("Summary: ", summary)
    print("Runs:    ", runs)
    print("Turns:   ", turns)
    print("Openings:", openings)
    print("\nHeadline")
    print(f"  cards:                 {len(deck)}")
    print(f"  lands:                 {data['deck']['lands']}")
    print(f"  avg mulligans:         {data['opening']['avg_mulligans']:.3f}")
    print(f"  all-colors T3:         {data['by_turn'].get('3',{}).get('all_commander_colors_pct',0):.1f}%")
    print(f"  reach 111 life:        {data['outcomes']['reach_111_life_pct']:.1f}%")
    print(f"  Bilbo activation:      {data['outcomes']['bilbo_activation_pct']:.1f}%")
    print(f"  win by turn {cfg.turns}:       {data['outcomes']['win_by_turn_limit_pct']:.1f}%")
    print(f"  avg end hand:          {data['outcomes']['avg_end_hand']:.2f}")




# ===========================================================================
# v4 EXTENSION LAYER
# ===========================================================================
#
# v4 deliberately builds on the tested v3 rules/metadata layer, then replaces
# the parts that benefit from a more general utility/value model:
#   * strategy/archetype tags
#   * generic X-spell valuation
#   * card impact ledger / "high value" highlighting
#   * commander-first sequencing
#   * structural vs remaining color access
#   * abstract opponent profiles (experimental)
#   * result folder + ZIP + AI analysis instructions
#
# The original v3 functions remain in this file as fallbacks for card-specific
# effects that v4 does not need to redefine.
# ===========================================================================

import shutil as _shutil
import zipfile as _zipfile
from datetime import datetime as _datetime
from collections import defaultdict as _defaultdict

V4_VERSION = "4.0"

# Save selected v3 implementations before overriding names below.
_V3_Strategy = Strategy
_V3_GameState = GameState
_V3_draw_cards = draw_cards
_V3_lose_each_opponent = lose_each_opponent
_V3_lose_target_opponent = lose_target_opponent
_V3_create_tokens = create_tokens
_V3_apply_payment = apply_payment
_V3_resolve_direct_spell_effects = resolve_direct_spell_effects
_V3_attack_phase = attack_phase
_V3_tutor_to_hand = tutor_to_hand
_V3_tutor_to_top = tutor_to_top
_V3_return_from_graveyard_to_hand = return_from_graveyard_to_hand
_V3_permanent_enters = permanent_enters
_V3_batch_creatures_enter = batch_creatures_enter
_V3_end_step = end_step
_V3_scry = scry
_V3_surveil = surveil
_V3_connive = connive


# ---------------------------------------------------------------------------
# General value model
# ---------------------------------------------------------------------------

DEFAULT_VALUE_MODEL = {
    "mana_unit": 1.0,
    "card_spent": 0.75,
    "draw_curve": {
        "1": 2.0,
        "2": 3.0,
        "3": 4.0,
        "4": 5.2,
        "5": 6.4,
        "6": 7.5,
        "7": 8.6
    },
    "draw_extra_each": 1.05,
    "discard_self": -1.20,
    "discard_opponent": 1.50,
    "life_gain_per_point": 0.667,
    "opponent_life_loss_per_point": 0.42,
    "combat_damage_per_point": 0.28,
    "scry_per_card": 0.45,
    "surveil_per_card": 0.60,
    "connive_per_card": 0.85,
    "mill_per_card": 0.16,
    "grave_hate_per_card": 0.18,
    "counter_1_1": 0.50,
    "food_token": 0.55,
    "treasure_token": 1.00,
    "clue_token": 1.20,
    "creature_token_body_base": 0.35,
    "creature_token_power": 0.25,
    "creature_token_toughness": 0.12,
    "mana_generated": 0.48,
    "mana_discount": 0.95,
    "tutor_card": 2.40,
    "recursion_card": 2.10,
    "spell_copy": 2.50,
    "token_multiplier": 0.70,
    "protection_event": 2.20,
    "removal_event": 2.50,
    "boardwipe_event": 4.00,
    "selection_event": 0.45,
    "x_min_roi": 0.88,
    "x_min_net_value": 0.25,
    "x_card_opportunity_cost": 0.75,
    "x_spell_proximity_bonus_max": 1.0,
    "value_curve_exponents": {
        "creature_tokens": 1.15,
        "opponent_life_loss": 0.85,
    },
    "color_category_multipliers": {
        "draw": {"W": 0.30, "U": 1.00, "B": 0.60, "R": 0.25, "G": 0.50},
        "opponent_life_loss": {"W": 0.15, "U": 0.10, "B": 0.35, "R": 1.00, "G": 0.15},
        "removal": {"W": 0.80, "U": 0.35, "B": 1.00, "R": 0.70, "G": 0.60},
        "boardwipe": {"W": 1.00, "U": 0.35, "B": 0.70, "R": 0.65, "G": 0.30},
        "mana_generated": {"W": 0.20, "U": 0.45, "B": 0.40, "R": 0.55, "G": 1.00},
    },
    "color_category_multipliers_colorless_fallback": 0.5,
    "keyword_weights": {
        "flying": 0.50, "menace": 0.35, "trample": 0.35, "unblockable": 0.55,
        "deathtouch": 0.40, "first strike": 0.35, "double strike": 0.70,
        "vigilance": 0.30, "reach": 0.15, "lifelink": 0.40,
        "hexproof": 0.60, "indestructible": 0.70, "ward": 0.50, "haste": 0.30,
        "protection": 0.55, "flash": 0.30,
    },
    "keyword_weight_default": 0.25,
    "creature_pt_sum_rate": 0.50,
    "instant_speed_premium": 0.50,
    "boardwipe_scaling_discount_per_creature": 1.0,
    "boardwipe_scaling_cost_floor": 1.0,
    "engine_value_cold_start_pseudo_seen": 30.0,
    "engine_value_max_learned_weight": 0.85,
    "wc_preservation_bias_strength": 0.15,
    "wc_preservation_floor_multiplier": 0.5,
    "context_empty_hand_threshold": 2,
    "context_empty_hand_draw_boost": 1.3,
    "context_large_board_threshold": 6,
    "context_large_board_passive_boost": 1.2,
    "resource_to_mana_conversion": {
        "life_as_cost_rate": 0.5,
        "delve_rate": 1.0,
        "convoke_improvise_rate": 1.0,
        "stun_counter_mana_equivalent_rate": 1.0,
        "stun_counter_value_discount_per_counter": 0.15,
    },
}

STRATEGY_MULTIPLIERS = {
    "lifegain": {
        "life_gain": 1.65,
        "life_amplified": 1.85,
        "food_created": 1.15,
        "opponent_life_loss": 1.10,
    },
    "mill": {
        "mill": 2.30,
        "surveil": 1.10,
        "grave_hate": 0.80,
    },
    "counters": {
        "counters": 1.70,
        "creature_tokens": 1.10,
    },
    "voltron": {
        "counters": 1.40,
        "combat_damage": 1.45,
        "protection": 1.35,
    },
    "tokens": {
        "creature_tokens": 1.50,
        "food_created": 1.20,
        "treasure_created": 1.15,
        "token_multiplier": 1.65,
    },
    "aristocrats": {
        "token_sacrificed": 1.55,
        "opponent_life_loss": 1.35,
        "creature_tokens": 1.20,
        "recursion": 1.20,
    },
    "spellslinger": {
        "draw": 1.20,
        "spell_copy": 1.70,
        "mana_discount": 1.35,
        "scry": 1.10,
    },
    "artifacts": {
        "treasure_created": 1.20,
        "food_created": 1.15,
        "clue_created": 1.20,
    },
    "enchantress": {
        "draw": 1.20,
        "tutor": 1.20,
    },
    "graveyard": {
        "surveil": 1.35,
        "recursion": 1.55,
        "discard_self": 0.55,
    },
    "lands": {
        "mana_generated": 1.15,
        "mana_discount": 1.10,
    },
    "control": {
        "draw": 1.20,
        "scry": 1.20,
        "surveil": 1.15,
        "protection": 1.30,
        "removal": 1.35,
    },
    "aggro": {
        "combat_damage": 1.35,
        "creature_tokens": 1.15,
        "counters": 1.10,
    },
    "combo": {
        "tutor": 1.60,
        "draw": 1.20,
        "mana_generated": 1.15,
        "mana_discount": 1.25,
        "spell_copy": 1.25,
    },
}

STRATEGY_TAGS = [
    "lifegain", "mill", "counters", "voltron", "tokens", "aristocrats",
    "spellslinger", "artifacts", "enchantress", "graveyard", "lands",
    "control", "aggro", "combo",
]

# v4.68.0: STRATEGY_TAGS -> archetype_profile's 115 canonical EDHREC tags
# (App/archetype_profile/tag_normalize.py). A straightforward 1:1 vocabulary
# bridge, not a research finding - every one of the 14 in-app tags already
# has a directly matching EDHREC canonical tag (same concept, different
# casing/wording), verified against the full canonical tag list.
_STRATEGY_TAG_TO_ARCHETYPE_TAG = {
    "lifegain": "Lifegain", "mill": "Mill", "counters": "Counters Matter",
    "voltron": "Voltron", "tokens": "Tokens", "aristocrats": "Aristocrats",
    "spellslinger": "Spellslinger", "artifacts": "Artifacts",
    "enchantress": "Enchantress", "graveyard": "Graveyard",
    "lands": "Lands Matter", "control": "Control", "aggro": "Aggro",
    "combo": "Combo",
}

_ARCHETYPE_ANALYZER = None  # lazy singleton - App/archetype_profile/data/ takes ~1-2s to load


def _get_archetype_analyzer():
    """v4.68.0. Loaded once, reused across calls (GUI may re-request the
    comparison tab repeatedly within one session).

    v4.75.0-Nachtrag: raises a clear RuntimeError (instead of an
    AttributeError on None) if archetype_profile could not be imported -
    see the import block near the top of this module. Callers (currently
    only compare_deck_to_archetype_reference, which App/gui.py::
    _build_deck_comparison already wraps in a try/except) surface this as a
    friendly in-tab message rather than crashing."""
    global _ARCHETYPE_ANALYZER
    if _ArchetypeDeckAnalyzer is None:
        raise RuntimeError(
            "1.585-Deck-Vergleich nicht verfügbar: archetype_profile konnte nicht "
            f"geladen werden ({_ARCHETYPE_PROFILE_IMPORT_ERROR}). Meist fehlt "
            "'numpy' in dieser Python-Umgebung - 'pip install numpy' beheben "
            "und die App neu starten. Der Rest des Tools funktioniert davon "
            "unabhängig."
        )
    if _ARCHETYPE_ANALYZER is None:
        _ARCHETYPE_ANALYZER = _ArchetypeDeckAnalyzer.load()
    return _ARCHETYPE_ANALYZER


def commander_identity_slug(cards: Dict[str, "Card"], commanders) -> Optional[str]:
    """v4.68.0: the tested deck's real color identity, taken from the
    commander(s) actually chosen in the app (union, for partner commanders) -
    NOT estimated from the whole decklist's mana pips. Closes
    App/archetype_profile/README.md's own documented gap #3 ("Farbidentitaet
    aus dem Commander uebernehmen... statt detect_identity_slug() zu
    nutzen"). Falls back to "colorless" only if no commander is resolvable
    (should not normally happen once a deck is loaded).

    v4.75.0-Nachtrag: raises the same clear RuntimeError as
    _get_archetype_analyzer() if archetype_profile is unavailable, rather
    than failing with an opaque "NoneType is not callable" further down."""
    if _archetype_normalize_color_identity is None:
        raise RuntimeError(
            "1.585-Deck-Vergleich nicht verfügbar: archetype_profile konnte nicht "
            f"geladen werden ({_ARCHETYPE_PROFILE_IMPORT_ERROR}). Meist fehlt "
            "'numpy' in dieser Python-Umgebung - 'pip install numpy' beheben "
            "und die App neu starten. Der Rest des Tools funktioniert davon "
            "unabhängig."
        )
    colors: set = set()
    for name in commanders or ():
        c = cards.get(name)
        if c is not None:
            colors |= set(c.color_identity)
    if not colors:
        return "colorless"
    return _ARCHETYPE_COLORS_TO_SLUG.get(_archetype_normalize_color_identity("".join(colors)))


def compare_deck_to_archetype_reference(
    deck: List["Card"], commanders, cards: Dict[str, "Card"], tags=None
) -> dict:
    """v4.68.0. GUI-facing entry point for the Auswertungsmaske's "Vergleich"-
    Tab: compares the currently tested deck against the 1.585-real-EDHREC-deck
    reference (App/archetype_profile), by color identity alone AND (if any
    in-app strategy tags are selected and recognized) by identity+strategy.

    Returns dict(
        identity_slug, identity_label,
        identity_only: AnalysisResult,            # color-identity baseline only
        with_strategy: AnalysisResult | None,      # identity + recognized tag(s), if any
        recognized_tags: list[str],                # archetype_profile tag names actually used
        requested_tags: list[str],                 # the raw in-app tags passed in
    )
    Every card in `deck` is passed through with its own mana_cost/type_line/
    oracle_text/power/toughness as live-classification fallback data (see
    App/archetype_profile/deck_analyzer.py::classify_uploaded_card) - a card
    not in the 8.445-card reference lookup still gets classified the same
    way the reference data itself was built, instead of silently dropping
    out as "unknown"."""
    analyzer = _get_archetype_analyzer()
    decklist = [
        dict(
            name=c.name, quantity=1, mana_cost=c.mana_cost, type=c.type_line,
            oracle_text=c.oracle_text, power=c.power, toughness=c.toughness,
        )
        for c in deck
    ]
    identity_slug = commander_identity_slug(cards, commanders)
    identity_only = analyzer.analyze(decklist, identity_slug=identity_slug, tags=[])

    recognized_tags = [
        _STRATEGY_TAG_TO_ARCHETYPE_TAG[t] for t in (tags or [])
        if t in _STRATEGY_TAG_TO_ARCHETYPE_TAG
    ]
    with_strategy = (
        analyzer.analyze(decklist, identity_slug=identity_slug, tags=recognized_tags)
        if recognized_tags else None
    )

    return dict(
        identity_slug=identity_slug,
        identity_label=_ARCHETYPE_SLUG_TO_LABEL.get(identity_slug, identity_slug),
        identity_only=identity_only,
        with_strategy=with_strategy,
        recognized_tags=recognized_tags,
        requested_tags=list(tags or []),
    )


@dataclass
class ValueModel:
    values: dict = field(default_factory=lambda: json.loads(json.dumps(DEFAULT_VALUE_MODEL)))

    @classmethod
    def load(cls, path: Optional[Path] = None):
        data = json.loads(json.dumps(DEFAULT_VALUE_MODEL))
        if path:
            user = json.loads(Path(path).read_text(encoding="utf-8"))
            # shallow + one-level dict merge is enough for this config
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(data.get(k), dict):
                    data[k].update(v)
                else:
                    data[k] = v
        return cls(data)

    def draw_value(self, n: float) -> float:
        n = max(0, int(round(n)))
        if n <= 0:
            return 0.0
        curve = self.values["draw_curve"]
        if str(n) in curve:
            return float(curve[str(n)])
        highest = max(int(k) for k in curve)
        return float(curve[str(highest)]) + (n - highest) * float(self.values["draw_extra_each"])

    def curved_count(self, category: str, amount: float) -> float:
        """
        v4.10.0. Generalizes the diminishing-returns idea draw_curve already
        proves out for "draw" to other metrics that were still flat/linear -
        via a single tunable power-law exponent per metric
        (value_curve_exponents in DEFAULT_VALUE_MODEL):
        effective = amount ** exponent.

        exponent == 1.0 (the default for any metric not listed) reproduces
        today's flat-linear behavior exactly - this is additive, not a
        silent recalibration of every existing metric. Two directions are
        used here, deliberately opposite:
          - opponent_life_loss: exponent < 1 (diminishing). A cheap,
            efficient burn spell (Lightning Bolt: 3 damage for 1 mana) is
            real-Magic more mana-efficient per point than a huge X spell
            (Banefire at X=14 for 15 mana) - the flat per-point rate from
            v4.9.1-v4.9.3 couldn't express that, only "damage is damage".
            (This is separate from, and additive with, the v4.9.3
            proximity-to-lethal bonus in best_x_plan, which answers a
            different question - "does this closes out a kill" - and is
            deliberately computed from the RAW, uncurved damage amount so
            the lethal check itself is never distorted by a value curve.)
          - creature_tokens: exponent > 1 (increasing). A wide board of
            tokens is worth disproportionately more than the same tokens
            counted one at a time - board-wipe resistance, evasion/chump-
            blocking math, and go-wide synergies all compound with count,
            the opposite shape from draw's per-card diminishing returns.

        Approximation, documented rather than hidden: this curves the
        metric's already-computed amount, which for creature_tokens already
        folds in per-token power/toughness (creature_token_power/
        toughness), not a bare token count. For a single spell creating N
        identical tokens (the common case, and the one the real-run
        evidence - White Sun's Zenith - is about) this is equivalent to
        curving N itself, since the per-token body is constant across the
        cast; it is not exact for comparing two DIFFERENTLY-sized tokens
        against each other. A strict count-only curve would need
        x_effect_metrics to track token count and per-token body as two
        separate Counter keys instead of one pre-multiplied figure - left
        for a future WP if real evidence calls for that distinction.
        """
        if amount <= 0:
            return amount
        exponent = float(self.values.get("value_curve_exponents", {}).get(category, 1.0))
        if exponent == 1.0:
            return amount
        return amount ** exponent

    def multiplier(self, metric: str, tags: Set[str]) -> float:
        mult = 1.0
        for tag in tags:
            mult *= float(STRATEGY_MULTIPLIERS.get(tag, {}).get(metric, 1.0))
        # Avoid runaway stacking when several broad archetype labels are selected.
        return min(mult, 3.0)

    def color_category_multiplier(self, category: str, color_identity: Optional[Set[str]]) -> float:
        """
        v4.11.0. Scales a category's existing flat per-point/per-event rate
        by how good the casting color is at that category, per the official
        WotC "Mechanical Color Pie" primary/secondary/tertiary classification
        (see Docs/DEFAULT_VALUES_AND_COLOR_PIE_v1.md for sources and the
        red-pilot EDHREC cross-check). 1.0 is the ceiling everywhere - it
        means "as good as today's flat rate", not "boosted" - so this change
        can only ever hold a color/category combo at today's value or pull
        it down for colors that aren't primary there; nothing gets more
        valuable than it was pre-v4.11.0. That also makes it fully backward
        compatible: any call site that doesn't pass color_identity (None)
        gets 1.0, i.e. exactly today's behavior.

        Multicolor cards use the BEST applicable color for the category
        (max across color_identity), not an average - a Rakdos card doing
        red-style burn should be judged as red, not held back by black's
        weaker burn multiplier. Colorless cards (empty/no color identity)
        are floored at the WORST color already in that category's own
        table (min across the table's values), not a single flat guessed
        constant - v4.15.7 research finding (task #18, "Farblos-Fallback-
        Recherche"): Mark Rosewater's official design article on artifacts
        ("Just the Artifacts, Ma'am", magic.wizards.com/en/news/making-
        magic/just-artifacts-maam-2005-02-28) states the design rule
        directly - "any ability you give to artifacts you are giving to the
        weakest color in that ability." That is a floor-at-the-worst-color
        rule, not an average/middle-of-the-pack one, and the flat 0.5 this
        replaces was in fact ABOVE several colors' own worst rating in
        every category (e.g. removal's U=0.35 < the old 0.5 fallback) -
        i.e. colorless was, incorrectly, being modeled as better than a
        color already is at that color's own weakest categories.
        color_category_multipliers_colorless_fallback is kept as an
        emergency fallback only, for a category with no table at all.
        """
        table = self.values.get("color_category_multipliers", {}).get(category)
        if table is None:
            return 1.0
        if color_identity is None:
            # Caller doesn't know/pass color info (e.g. an as-yet-unupdated
            # call site) - stay a no-op, not the colorless fallback. Only an
            # explicitly empty set (a card confirmed to have no color
            # identity) should trigger the colorless fallback below.
            return 1.0
        if not color_identity:
            if table:
                return min(float(v) for v in table.values())
            # Category listed but with no per-color values at all - the
            # min-of-worst-color rule above has nothing to floor against,
            # so fall back to the flat constant (should not normally be
            # reached with the shipped Data/Models/*.json tables).
            return float(self.values.get("color_category_multipliers_colorless_fallback", 0.5))
        if not table:
            return 1.0
        return max(float(table.get(c, 1.0)) for c in color_identity)

    def metric_value(self, metric: str, amount: float, tags: Set[str], color_identity: Optional[Set[str]] = None) -> float:
        if not amount:
            return 0.0
        if metric == "draw":
            base = self.draw_value(amount) * self.color_category_multiplier("draw", color_identity)
        elif metric == "discard_self":
            base = abs(float(self.values["discard_self"])) * amount
            return -base * self.multiplier(metric, tags)
        elif metric == "discard_opponent":
            base = float(self.values["discard_opponent"]) * amount
        elif metric in {"life_gain", "life_amplified"}:
            base = float(self.values["life_gain_per_point"]) * amount
        elif metric == "opponent_life_loss":
            base = float(self.values["opponent_life_loss_per_point"]) * self.curved_count("opponent_life_loss", amount)
            base *= self.color_category_multiplier("opponent_life_loss", color_identity)
        elif metric == "combat_damage":
            base = float(self.values["combat_damage_per_point"]) * amount
        elif metric == "scry":
            base = float(self.values["scry_per_card"]) * amount
        elif metric == "surveil":
            base = float(self.values["surveil_per_card"]) * amount
        elif metric == "connive":
            base = float(self.values["connive_per_card"]) * amount
        elif metric == "mill":
            base = float(self.values["mill_per_card"]) * amount
        elif metric == "grave_hate":
            base = float(self.values["grave_hate_per_card"]) * amount
        elif metric == "counters":
            base = float(self.values["counter_1_1"]) * amount
        elif metric == "food_created":
            base = float(self.values["food_token"]) * amount
        elif metric == "treasure_created":
            base = float(self.values["treasure_token"]) * amount
        elif metric == "clue_created":
            base = float(self.values["clue_token"]) * amount
        elif metric == "creature_tokens":
            # amount here is already "body-equivalent units" (see
            # curved_count's docstring for the approximation this implies)
            base = self.curved_count("creature_tokens", amount)
        elif metric == "mana_generated":
            base = float(self.values["mana_generated"]) * amount * self.color_category_multiplier("mana_generated", color_identity)
        elif metric == "mana_discount":
            base = float(self.values["mana_discount"]) * amount
        elif metric == "tutor":
            base = float(self.values["tutor_card"]) * amount
        elif metric == "recursion":
            base = float(self.values["recursion_card"]) * amount
        elif metric == "spell_copy":
            base = float(self.values["spell_copy"]) * amount
        elif metric == "token_multiplier":
            base = float(self.values["token_multiplier"]) * amount
        elif metric == "protection":
            base = float(self.values["protection_event"]) * amount
        elif metric == "removal":
            base = float(self.values["removal_event"]) * amount * self.color_category_multiplier("removal", color_identity)
        elif metric == "boardwipe":
            base = float(self.values["boardwipe_event"]) * amount * self.color_category_multiplier("boardwipe", color_identity)
        else:
            base = amount * 0.25
        return base * self.multiplier(metric, tags)

    def aggregate_value(self, metrics: Counter, tags: Set[str], color_identity: Optional[Set[str]] = None) -> float:
        return sum(self.metric_value(k, float(v), tags, color_identity) for k, v in metrics.items()
                   if k not in {"seen", "cast", "mana_spent", "entered", "board_turns"})

    def keyword_value(self, keywords: Optional[Set[str]]) -> float:
        """
        v4.12.0 (Route C). A single bundled "Keywords" value, per the user's
        own request to lump combat/ability keywords (Lifelink, Flying,
        Deathtouch, etc.) into one category rather than modeling each
        separately. This evaluates a card's STATIC keyword set for card-
        priority/sequencing purposes (see its use in cast_score_v4) - it is
        NOT wired into aggregate_value/metric_value, because keywords are a
        fixed property of the card, not a per-turn simulated event the way
        draw/opponent_life_loss/etc. are.

        Deliberately lower-confidence than the color-category work: unlike
        Draw/Interaction/Board-Wipe/Ramp, there is no EDHREC-style inclusion
        data or official WotC per-keyword price list to calibrate against,
        so keyword_weights below are a first, reasoned estimate (roughly
        ordered by real competitive impact - evasion and protection keywords
        weighted above pure combat-math ones), not cross-validated the way
        the color multipliers are. Any keyword not in the table falls back
        to keyword_weight_default rather than being silently worth 0.
        """
        if not keywords:
            return 0.0
        table = self.values.get("keyword_weights", {})
        default = float(self.values.get("keyword_weight_default", 0.25))
        return sum(float(table.get(k.lower(), default)) for k in keywords)

    def creature_body_value(self, power: Optional[float], toughness: Optional[float]) -> float:
        """
        v4.12.0 (Route C). General creature power+toughness evaluation for
        card-priority scoring, using the SUM of power and toughness rather
        than weighting them separately - per the user's own suggestion that
        this may be more meaningful than tracking them apart for general
        creature comparison. Deliberately separate from
        creature_token_power/creature_token_toughness (which stay per-point-
        weighted and untouched here) - those are already calibrated/tested
        specifically for TOKEN generation (see ValueModel.metric_value's
        "creature_tokens" branch and its v4.10.0 curve), and this function
        does not touch that path at all.

        Calibration: creature_pt_sum_rate defaults to 0.5, chosen from
        Magic's own well-known informal design heuristic (the "vanilla
        test" - see Mark Rosewater's design articles): a fairly-costed
        vanilla creature has power+toughness roughly equal to twice its
        mana value (e.g. a 3-mana 3/3, a 4-mana 4/4). At rate=0.5, a vanilla
        creature's body value exactly matches its mana cost
        (0.5 * 2*mana_value == mana_value), i.e. net_value ~= 0 for a bare
        vanilla creature - neither a great nor a bad play by itself, which
        is the right default for "just stats, no text".
        """
        if power is None and toughness is None:
            return 0.0
        total = float(power or 0.0) + float(toughness or 0.0)
        return total * float(self.values.get("creature_pt_sum_rate", 0.5))

    def boardwipe_effective_cost_estimate(self, base_cost: float, scaling_count: int) -> float:
        """
        v4.12.0 (Route C). Board wipes with a self-scaling cost reduction
        (Blasphemous Act: "costs {1} less to cast for each creature on the
        battlefield", floor {R}) don't fit a single flat boardwipe_event
        rate - flagged as an open gap in the red pilot
        (Docs/COLOR_VALUE_PILOT_v1_red.md Sec. 4: "needs a two-parameter
        model (base cost + scaling discount condition), a plain per-mana
        damage number misrepresents cards like Blasphemous Act"). This is
        that two-parameter estimate: base_cost (the printed/ceiling cost)
        minus boardwipe_scaling_discount_per_creature for each relevant
        permanent/card the scaling condition counts (creatures controlled,
        cards in graveyard, etc. - whatever the specific card's own text
        scales on), floored at boardwipe_scaling_cost_floor.

        IMPORTANT SCOPE NOTE, UPDATED v4.15.5: this remains a VALUE-estimation
        utility for ranking/reporting purposes only, callable with just a
        caller-supplied (base_cost, scaling_count) pair without any oracle-
        text parsing. The REAL cast/payment path gap this docstring used to
        describe is now closed separately: `boardwipe_self_scaling_discount`
        (module-level function, just above `_potential_cast_copy_multiplier`)
        parses a card's own self-referential "costs {N} less ... for each
        <condition>" text directly and is called from `cast_option` alongside
        `effective_cost_discount`, so a card like Furygale Flocking is now
        actually cheaper to cast in the real payment path too, not only
        ranked as if it were. That function deliberately does NOT cover
        additional-cost-CHOICE scaling (March of Wretched Sorrow's "exile
        cards from hand, cost less per card exiled this way") - see its own
        docstring for why. This estimate-only method is kept as-is (still
        useful when a caller wants a rough ranking number without doing real
        text parsing), not superseded.
        """
        per_unit = float(self.values.get("boardwipe_scaling_discount_per_creature", 1.0))
        floor = float(self.values.get("boardwipe_scaling_cost_floor", 1.0))
        return max(floor, float(base_cost) - per_unit * max(0, int(scaling_count)))

    # -----------------------------------------------------------------
    # Resource-to-mana conversion (v4.15.4; design: Docs/
    # DEFAULT_VALUES_AND_COLOR_PIE_v1.md Sec. 5.1/5.1.1, mirrored in
    # Data/Models/default_value_table_and_color_pie.json::
    # resource_to_mana_conversion). Bucket A (life/delve/convoke/improvise/
    # sacrifice): a real resource is actually spent to replace mana, so it
    # converts into mana_unit-equivalents at the rates below - life/delve/
    # convoke all have an OFFICIAL WotC conversion rate (Phyrexian mana
    # templating, Delve/Convoke/Improvise keyword templating); sacrifice does
    # not (Emerge's own reminder text confirms "value of the specific card",
    # not a flat constant). Bucket B (stun counters/suspend/decayed/
    # conditional restrictions): no resource changes hands, only usability is
    # restricted, so these use a value multiplier instead of a mana
    # conversion (folding them into mana-equivalents would be a category
    # error - see uptime_value_discount).
    #
    # VALUE-ESTIMATION UTILITIES ONLY, same scope note as
    # boardwipe_effective_cost_estimate above: these do not change what a
    # spell can actually be paid for in the real cast/payment path
    # (available_mana_value) - they exist for ranking/reporting a card's
    # effective cost, not for computing what the engine can legally cast.
    # Wiring an alternative-cost-aware real payment path is a separate,
    # larger, not-yet-built feature (same class of gap as
    # boardwipe_effective_cost_estimate's own real-payment-path note).
    # -----------------------------------------------------------------

    def _resource_conversion(self) -> dict:
        return self.values.get("resource_to_mana_conversion", {}) or {}

    def life_as_mana_equivalent(self, life_paid: float) -> float:
        """Bucket A: official WotC design rate from Phyrexian mana templating
        (New Phyrexia {C/P}: pay 1 colored mana OR 2 life) - 2 life = 1 mana."""
        rate = float(self._resource_conversion().get("life_as_cost_rate", 0.5))
        return max(0.0, float(life_paid)) * rate

    def delve_mana_equivalent(self, graveyard_cards_exiled: int) -> float:
        """Bucket A: official WotC keyword templating - exiling a card from
        the graveyard pays for exactly {1} generic mana (Treasure Cruise,
        Dig Through Time, Tasigur, the Golden Fang)."""
        rate = float(self._resource_conversion().get("delve_rate", 1.0))
        return max(0, int(graveyard_cards_exiled)) * rate

    def convoke_improvise_mana_equivalent(self, tapped_permanents: int) -> float:
        """Bucket A: official WotC keyword templating - tapping an untapped
        creature (Convoke) or artifact (Improvise) pays for {1} generic mana
        (real project example: Hour of Reckoning, Decks/Aziza V2.txt)."""
        rate = float(self._resource_conversion().get("convoke_improvise_rate", 1.0))
        return max(0, int(tapped_permanents)) * rate

    def sacrifice_cost_equivalent(
        self, sacrificed_card: Optional["Card"], strategy: Optional["Strategy"] = None,
    ) -> float:
        """Bucket A, dynamic lookup - confirmed by Emerge's own official
        reminder text ("the mana value of the exiled creature"), not a flat
        constant: a 1-mana token and a fully-built bomb are not equivalent
        sacrifices. Reuses predefined_static_value (same card-shape-only
        estimate Engine Value's predefined half already uses)."""
        if sacrificed_card is None:
            return 0.0
        strategy = strategy or Strategy(value_model=self)
        return max(0.0, predefined_static_value(sacrificed_card, strategy))

    def stun_counter_value_multiplier(self, counters: int) -> float:
        """Bucket B, PREFERRED method: a percentage discount on the affected
        permanent's OWN value (delaying a bomb is worse than delaying a mana
        dork), rather than a flat mana amount. LOW-CONFIDENCE first-guess
        constant (Data/Models/goldfish_value_model.json::
        resource_to_mana_conversion.stun_counter_value_discount_per_counter,
        default 0.15) - unlike life/delve/convoke, no official WotC
        conversion rate exists for stun counters."""
        discount = float(self._resource_conversion().get("stun_counter_value_discount_per_counter", 0.15))
        return max(0.0, 1.0 - discount * max(0, int(counters)))

    def stun_counter_mana_equivalent_fallback(self, counters: int) -> float:
        """Bucket B fallback method: only use this flat mana-equivalent when
        the affected permanent's own value is not yet known at evaluation
        time - stun_counter_value_multiplier (the percentage-of-value
        discount) is the preferred method otherwise."""
        rate = float(self._resource_conversion().get("stun_counter_mana_equivalent_rate", 1.0))
        return max(0, int(counters)) * rate

    def uptime_value_discount(self, base_value: float, uptime_fraction: float) -> float:
        """Bucket B, general form: no resource changes hands here (folding
        this into a mana-equivalent would be a category error - see Docs/
        DEFAULT_VALUES_AND_COLOR_PIE_v1.md Sec. 5.1d), only usability is
        restricted. One shared implementation for conditional attack/block
        restrictions ('can attack only if...'), Suspend (uptime ~= the
        fraction of the game after the delay has resolved), and Decayed
        (value as a single attack's worth of impact instead of ongoing board
        presence) - per the design doc's explicit 'same bucket-B logic, no
        new formula needed' for all three, deliberately not three near-
        identical methods."""
        return max(0.0, float(base_value)) * max(0.0, min(1.0, float(uptime_fraction)))

    def engine_value(
        self,
        predefined_value: float,
        learned_value_per_seen: Optional[float],
        learned_seen: float,
    ) -> float:
        """
        v4.13.0 (Route D, "Engine Value"). Blends a card's predefined,
        card-shape-only value (predefined_static_value, or any other Route
        A-C-shaped estimate) with a value LEARNED from real, persisted
        simulation history (learned_value_per_seen/learned_seen, from
        Data/Learned/engine_value_store.json via update_engine_value_store).

        Bayesian-shrinkage blend, same family as e.g. IMDB's old weighted-
        rating formula: engine_value_cold_start_pseudo_seen (default 30)
        represents how many games' worth of trust the predefined estimate
        starts with. blend_weight -> 0 as learned_seen -> 0, so a fresh
        checkout with an empty store returns predefined_value UNCHANGED,
        byte-for-byte - no special-casing needed, same safety pattern as
        color_category_multiplier's color_identity=None fallback (v4.11.0).
        engine_value_max_learned_weight (default 0.85) caps how far the
        learned side can ever dominate, even at huge sample size - recorded
        metric events are themselves an incomplete picture (e.g. a vanilla
        creature's combat contribution is only partially captured via
        combat_damage_per_point), so a residual anchor to the card-shape
        estimate is kept deliberately, not just as a cold-start crutch.

        See Docs/ENGINE_VALUE_v1.md for the full design writeup and its
        explicitly stated v1 scope boundaries (not wired into cast_score_v4
        yet, no decay, no per-deck namespace, no win-correlation/causal
        inference).
        """
        if learned_value_per_seen is None or learned_seen <= 0:
            return predefined_value
        pseudo = float(self.values.get("engine_value_cold_start_pseudo_seen", 30.0))
        max_blend = float(self.values.get("engine_value_max_learned_weight", 0.85))
        blend_weight = min(max_blend, learned_seen / (learned_seen + pseudo))
        return (1.0 - blend_weight) * predefined_value + blend_weight * float(learned_value_per_seen)

    def win_condition_preservation_multiplier(self, card_name: str, scenarios: Sequence[dict]) -> float:
        """
        v4.14.0 (Route E, Sec. 2 of Docs/WINCON_AND_CONTEXT_VALUE_v1.md).
        A SOFT downward bias on how attractive it is to cast/spend a card
        right now, applied when that card is a piece of one or more defined
        Win Conditions - the idea being that spending a WC piece purely for
        its immediate value can throw away a game plan the deck was built
        around.

        Structural design (matches the concept doc's Sec. 2.1/2.3):
          - scales INVERSELY with how many Win-Condition-kind scenarios are
            currently enabled/defined (wc_count) - preserving one piece
            matters much less when 5 alternative WCs exist than when it's
            the only one.
          - is discounted by a crude REDUNDANCY proxy: the number of
            distinct cards this scenario's requirements ask for in total.
            This is NOT the "interchangeable alternative cards" redundancy
            the concept doc describes (Sec. 2.2) - that needs a real
            requirements-schema extension (e.g. a `redundant_with` list)
            that does not exist yet, deliberately deferred rather than
            rushed ahead of WP10's upcoming scenario-system work. Treat
            this as a v1 approximation: "a WC needing many pieces is less
            fragile per-piece than a single-card WC", which is directionally
            related but not equivalent to true interchangeability.
          - is FLOORED at wc_preservation_floor_multiplier (default 0.5) -
            per the concept doc's explicit "kein Hard-Lock" requirement
            (Sec. 2.3), this can make a WC piece less attractive to cast
            NOW, but must never come close to zeroing it out or removing it
            from consideration.

        HONESTY NOTE: unlike the color-pie (EDHREC/WotC-sourced) or
        creature-body (Rosewater "vanilla test") calibrations, there is no
        external reference for wc_preservation_bias_strength - the concept
        doc says so explicitly (Sec. 5: "keine belastbare externe Referenz
        ... jede konkrete Formel wäre freihändig erfunden"). This is a
        first, clearly-flagged STARTING estimate (same honest pattern as
        v4.9.3's x_spell_proximity_bonus_max or v4.10.0's
        value_curve_exponents), meant to be revisited once real
        Data/Learned/engine_value_store.json history exists to check
        whether WC pieces are actually getting spent too early. NOT wired
        into cast_score_v4/live sequencing by default in this version -
        same reporting-first caution as Route D.
        """
        active_wc_scenarios = [
            sc for sc in scenarios
            if sc.get("enabled", True) and sc.get("kind") == "Win Condition"
        ]
        wc_count = len(active_wc_scenarios)
        if wc_count == 0:
            return 1.0

        involved = [
            sc for sc in active_wc_scenarios
            if any(normalize_name(str(r.get("card") or "")) == normalize_name(card_name) for r in sc.get("requirements", []))
        ]
        if not involved:
            return 1.0

        # Redundancy proxy: use the LEAST redundant (most fragile) scenario
        # this card participates in - a card that's a lone linchpin in even
        # one WC deserves the stronger bias, not the average.
        redundancy = min(max(1, len({normalize_name(str(r.get("card") or "")) for r in sc.get("requirements", [])})) for sc in involved)

        strength = float(self.values.get("wc_preservation_bias_strength", 0.15))
        floor = float(self.values.get("wc_preservation_floor_multiplier", 0.5))
        bias = strength / (wc_count * redundancy)
        return max(floor, 1.0 - bias)

    def hand_board_context_multiplier(self, role: str, hand_size: int, board_size: int) -> float:
        """
        v4.14.0 (Route E, Sec. 3 of Docs/WINCON_AND_CONTEXT_VALUE_v1.md). A
        contextual modulation layer on top of a card's value, based on the
        CURRENT hand/board state rather than the card's own shape or an
        archetype tag - conceptually a sibling to ValueModel.multiplier
        (which already does archetype-based modulation), just situational
        instead of strategy-based.

        Two directions, per the concept doc's own examples:
          - a near-empty hand raises the relative priority of draw/card-
            advantage roles (resource-scarcity situation);
          - a large existing board raises the relative priority of passive/
            board-scaling roles (they synergize with width/presence that's
            already there).

        Bounded on both sides (never below 1.0 / max_blend... - here,
        never below 1.0 itself, since this is a BOOST not a discount; the
        boost constants are individually capped) so a single context signal
        can meaningfully nudge sequencing without ever dominating the
        card's own predefined/learned value.

        Same HONESTY NOTE as win_condition_preservation_multiplier: these
        are first, uncalibrated starting estimates (no external reference
        exists for "how much should an empty hand boost draw priority") -
        not wired into cast_score_v4/live sequencing by default in this
        version.
        """
        multiplier = 1.0
        empty_hand_threshold = float(self.values.get("context_empty_hand_threshold", 2))
        large_board_threshold = float(self.values.get("context_large_board_threshold", 6))
        if role in {"draw", "draw_engine"} and hand_size <= empty_hand_threshold:
            multiplier *= float(self.values.get("context_empty_hand_draw_boost", 1.3))
        if role in {"engine", "boardwipe_protection", "anthem", "token"} and board_size >= large_board_threshold:
            multiplier *= float(self.values.get("context_large_board_passive_boost", 1.2))
        return multiplier


def predefined_static_value(card: "Card", strategy: "Strategy") -> float:
    """
    v4.13.0 (Route D). A pure card-shape value estimate - no GameState, no
    simulated events - answering "what should this card be worth, roughly,
    if it does exactly what its text says once?" This is the "predefined"
    half of Engine Value's blend (see ValueModel.engine_value and
    Docs/ENGINE_VALUE_v1.md); the "learned" half comes from real, persisted
    simulation history instead.

    Deliberately reuses the same already-calibrated, already-tested
    building blocks cast_score_v4 uses for its role/keyword/body bonuses
    (ValueModel.metric_value with color awareness, keyword_value,
    creature_body_value, the instant-speed premium, plus the same flat
    tutor/recursion/protection rates used elsewhere in DEFAULT_VALUE_MODEL)
    rather than inventing a second, parallel scoring formula - so a change
    to those calibrated rates automatically flows through here too.
    """
    vm = strategy.value_model or ValueModel.load()
    total = 0.0
    roles = card.roles or set()
    if "draw" in roles:
        total += vm.metric_value("draw", max(1, direct_draw_count(card)), strategy.archetypes, card.color_identity)
    if "tutor" in roles:
        total += float(vm.values.get("tutor_card", 2.4))
    if "recursion" in roles:
        total += float(vm.values.get("recursion_card", 2.1))
    if "interaction" in roles:
        total += vm.metric_value("removal", 1, strategy.archetypes, card.color_identity)
    if "boardwipe" in roles:
        total += vm.metric_value("boardwipe", 1, strategy.archetypes, card.color_identity)
    if "ramp" in roles or "burst_mana" in roles:
        total += vm.metric_value("mana_generated", 1, strategy.archetypes, card.color_identity)
    if "protection" in roles:
        total += float(vm.values.get("protection_event", 2.2))
    if card.keywords:
        total += vm.keyword_value(card.keywords)
    if card.is_creature:
        total += vm.creature_body_value(card.power, card.toughness)
    if card.is_instant:
        total += float(vm.values.get("instant_speed_premium", 0.5))
    return total


_ENGINE_VALUE_STORE_PATH = Path(__file__).resolve().parent.parent / "Data" / "Learned" / "engine_value_store.json"


def load_engine_value_store(path: Optional[Path] = None) -> dict:
    """
    v4.13.0 (Route D). Loads the cross-run learned-value store (see
    Docs/ENGINE_VALUE_v1.md Sec. 3). Missing file (fresh checkout, or no
    real run has completed yet) returns an empty-but-valid store rather
    than raising - the whole point of the cold-start blend_weight=0
    behavior in ValueModel.engine_value is that "no history yet" is a
    normal, safe state, not an error.
    """
    p = Path(path) if path else _ENGINE_VALUE_STORE_PATH
    if not p.exists():
        return {"cards": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"cards": {}}
    if not isinstance(data.get("cards"), dict):
        data["cards"] = {}
    return data


def save_engine_value_store(store: dict, path: Optional[Path] = None) -> None:
    p = Path(path) if path else _ENGINE_VALUE_STORE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def update_engine_value_store(store: dict, impact_rows: List[dict]) -> dict:
    """
    v4.13.0 (Route D). Merges one run's impact_rows (from
    impact_rows_from_aggregate - each row already has "Name", "Seen" and
    "Estimated value / seen") into the persisted cross-run store via a
    seen-weighted running average:

        new_seen = old_seen + row_seen
        new_avg  = (old_avg * old_seen + row_avg * row_seen) / new_seen

    Rows with Seen == 0 (never drawn in this run) contribute nothing and
    are skipped, rather than diluting the average toward 0. Pure function -
    takes a store dict, returns an updated one - so tests can exercise the
    merge arithmetic directly without touching disk (see
    tests/test_engine_value.py).
    """
    cards = dict(store.get("cards", {}))
    now = _datetime.now().isoformat(timespec="seconds")
    for row in impact_rows:
        row_seen = float(row.get("Seen", 0) or 0)
        if row_seen <= 0:
            continue
        row_avg = float(row.get("Estimated value / seen", 0) or 0)
        name = row.get("Name")
        if not name:
            continue
        prior = cards.get(name, {"seen": 0.0, "learned_value_per_seen": 0.0, "runs_merged": 0})
        old_seen = float(prior.get("seen", 0.0))
        old_avg = float(prior.get("learned_value_per_seen", 0.0))
        new_seen = old_seen + row_seen
        new_avg = (old_avg * old_seen + row_avg * row_seen) / new_seen if new_seen > 0 else 0.0
        cards[name] = {
            "seen": new_seen,
            "learned_value_per_seen": new_avg,
            "runs_merged": int(prior.get("runs_merged", 0)) + 1,
            "last_updated": now,
        }
    return {"cards": cards}


# ---------------------------------------------------------------------------
# Strategy / state extensions
# ---------------------------------------------------------------------------

@dataclass
class Strategy(_V3_Strategy):
    archetypes: Set[str] = field(default_factory=set)
    opponent_profile: str = "goldfish"
    commander_priority: str = "high"
    # auto = default Commander behavior:
    #   graveyard/exile -> command zone unless the engine supports a useful
    #   self-cast-from-that-zone ability;
    #   hand -> normally stay in hand;
    #   library -> normally command zone.
    commander_zone_policy: str = "auto"
    commander_zone_overrides: Dict[str, str] = field(default_factory=dict)
    x_min_roi: float = DEFAULT_VALUE_MODEL["x_min_roi"]
    x_min_net_value: float = DEFAULT_VALUE_MODEL["x_min_net_value"]
    x_spell_minimums: Dict[str, int] = field(default_factory=dict)
    x_spell_maximums: Dict[str, int] = field(default_factory=dict)
    value_model: Optional[ValueModel] = None
    # v4.15.0 (WP10): a fixed opponent index for COMMANDER damage specifically
    # (a Voltron/"21 to one target" plan - see Mabel, Heir to Cragflame). None
    # (default) preserves the pre-v4.15.0 behavior exactly: every damage
    # instance, commander or not, targets whichever opponent currently has
    # the highest life. When set, attack_phase directs commander-damage
    # outcomes at this fixed index instead - falling back to the old
    # highest-life heuristic if that opponent is already eliminated (0 life),
    # so a stale/invalid target can never waste damage or crash. Regular,
    # non-commander combat damage is deliberately left on the old heuristic
    # unchanged - this is scoped to the specific "accumulate 21 on ONE
    # target" plan, not a general targeting overhaul.
    voltron_target_index: Optional[int] = None
    # v4.63.0: erste echte Turnschleifen-Integration von
    # App/opponent_model/state_equation.py (bislang seit v4.44.0 nur additiver,
    # rein synthetischer Seiten-Cross-Check - siehe
    # _opponent_model_cross_check weiter unten). Default False: am Verhalten
    # von apply_abstract_opponent_phase aendert sich fuer JEDEN bestehenden
    # Aufrufer nichts, solange dieses Feld nicht explizit gesetzt wird - siehe
    # den neuen Wrapper direkt unter _apply_advanced_multi_opponent_phase.
    advanced_opponent_model: bool = False
    # Ein Eintrag JE Gegner-Sitzplatz: {"strategy": "aggro"/"midrange"/
    # "control"/"horde", "colors": ["U", "B"]}. opponent_profile (oben) wird
    # in diesem Modus NICHT mehr verwendet - jeder Sitzplatz traegt seine
    # EIGENE Strategie/Farbe. Diese erste Integrationsstufe unterstuetzt
    # ausdruecklich nur 1-2 Farben je Sitzplatz und Bracket 3 (kein
    # Bracket-Feld je Sitzplatz - siehe _validate_advanced_opponent_seats
    # fuer die harte Durchsetzung und Docs/README.md v4.63.0 fuer die
    # Begruendung: dies ist der einzige Bracket mit ausreichend breiten,
    # echten EDHREC-Kalibrierungsdaten fuer ein- und zweifarbige
    # Identitaeten). Drei-/vier-/fuenffarbige Identitaeten und weitere
    # Brackets sind nach eigener Nutzer-Vorgabe spaeteren Schritten
    # vorbehalten.
    advanced_opponent_seats: List[Dict[str, Any]] = field(default_factory=list)


def load_strategy(path: Optional[Path], commander: Optional[Card], *,
                  archetypes: Optional[Set[str]] = None,
                  opponent_profile: Optional[str] = None,
                  value_model: Optional[ValueModel] = None) -> Strategy:
    s = Strategy()
    if commander:
        s.commander_colors = set(commander.color_identity)
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for k in ("tutor_priority", "enchantment_tutor_priority", "legendary_tutor_priority", "bilbo_pile"):
            if k in data:
                setattr(s, k, list(data[k]))
        for k in ("hold_cards", "never_cast_goldfish"):
            if k in data:
                setattr(s, k, set(data[k]))
        if "commander_colors" in data:
            s.commander_colors = set(data["commander_colors"])
        if "prefer_food_for_life_until" in data:
            s.prefer_food_for_life_until = int(data["prefer_food_for_life_until"])
        if "max_food_activations_per_turn" in data:
            s.max_food_activations_per_turn = int(data["max_food_activations_per_turn"])
        if "archetypes" in data:
            s.archetypes = set(data["archetypes"])
        if "opponent_profile" in data:
            s.opponent_profile = str(data["opponent_profile"]).lower()
        if "commander_priority" in data:
            s.commander_priority = str(data["commander_priority"]).lower()
        if "commander_zone_policy" in data:
            s.commander_zone_policy = str(data["commander_zone_policy"]).lower()
        if "commander_zone_overrides" in data:
            s.commander_zone_overrides = {
                str(k): str(v).lower()
                for k, v in dict(data["commander_zone_overrides"]).items()
            }
        if "x_min_roi" in data:
            s.x_min_roi = float(data["x_min_roi"])
        if "x_min_net_value" in data:
            s.x_min_net_value = float(data["x_min_net_value"])
        if "x_spell_minimums" in data:
            s.x_spell_minimums = {str(k): int(v) for k, v in data["x_spell_minimums"].items()}
        if "x_spell_maximums" in data:
            s.x_spell_maximums = {str(k): int(v) for k, v in data["x_spell_maximums"].items()}
        if "voltron_target_index" in data and data["voltron_target_index"] is not None:
            s.voltron_target_index = int(data["voltron_target_index"])
        if "advanced_opponent_model" in data:
            s.advanced_opponent_model = bool(data["advanced_opponent_model"])
        if "advanced_opponent_seats" in data:
            s.advanced_opponent_seats = [dict(seat) for seat in data["advanced_opponent_seats"]]

    if archetypes:
        s.archetypes = set(archetypes)
    if opponent_profile:
        s.opponent_profile = opponent_profile.lower()
    s.value_model = value_model or ValueModel.load()
    return s


@dataclass
class GameState(_V3_GameState):
    life_gained_this_turn_amount: float = 0.0
    impact: Dict[str, Counter] = field(default_factory=lambda: _defaultdict(Counter))
    virtual_opponent_graveyard: int = 0
    damage_taken: float = 0.0
    lost_turn: Optional[int] = None
    commander_cast_counts: Counter = field(default_factory=Counter)
    # Commander Damage Ledger (WP7, per-commander since v4.28.0): cumulative
    # combat damage dealt BY a specific commander TO a specific opponent,
    # keyed by (commander_card_name, opponent_index) - opponent_index is the
    # same index as state.opponents. A player is dealt with lethally by a
    # SINGLE commander reaching 21 damage from that one commander (real
    # rule: 903.10a, tracked separately per commander). v4.28.0 fix (found
    # via ChatGPT external review, Docs/README.md v4.28.0 entry): this used
    # to be keyed by opponent_index alone, on the stated assumption "this
    # engine only ever has one commander" - which build_deck_v4/
    # build_deck_v3 already contradict (both collect ALL cards with
    # card.commander=True into command_zone, i.e. Partner/background
    # co-commanders are a real, already-supported case). Two different
    # commanders each dealing 11 combat damage to the same opponent used to
    # pool into a single 22, wrongly triggering the 21-damage loss even
    # though neither commander individually reached 21.
    commander_damage_dealt: Dict[Tuple[str, int], float] = field(default_factory=lambda: _defaultdict(float))
    # v4.21.0: Infect. Poison counters per opponent, keyed the same way as
    # commander_damage_dealt (a Dict, not a fixed-length list, since
    # state.opponents itself can be any length across call sites/tests) - an
    # infect creature's combat damage to a player becomes poison counters
    # instead of life loss (see attack_phase's "v4.21.0: Infect" block); a
    # player with 10+ poison counters loses, modeled the same way the
    # existing 21-commander-damage rule already does (directly zeroing that
    # opponent's tracked life instead of a separate loss-condition list).
    poison_counters: Dict[int, int] = field(default_factory=lambda: _defaultdict(int))


def _canonical_source(state: GameState, source: str) -> Optional[str]:
    if not source or source in {"draw", "draw step", "combat"}:
        return None
    all_cards = (
        [p.card for p in state.battlefield] +
        state.hand + state.graveyard + state.exile + state.command_zone
    )
    names = sorted({c.name for c in all_cards}, key=len, reverse=True)
    for name in names:
        if source == name or source.startswith(name):
            return name
    return source


def record_impact(state: GameState, source: Optional[str], metric: str, amount: float = 1.0):
    if not source or not amount:
        return
    source = _canonical_source(state, source)
    if source:
        state.impact[source][metric] += float(amount)


def mark_seen(state: GameState, card: Card, amount: float = 1.0):
    state.impact[card.name]["seen"] += amount


# ---------------------------------------------------------------------------
# Better impact attribution
# ---------------------------------------------------------------------------

def draw_cards(state: GameState, n: int, *, draw_step: bool = False, reason: str = "draw"):
    if n <= 0:
        return
    actual = n
    if state.has(ARCHIVE_NAME) and not draw_step:
        # Attribute the extra cards to Archive, while the base draw remains attributed
        # to the original source.
        extra = n
        record_impact(state, ARCHIVE_NAME, "draw", extra)
        actual *= 2

    drawn = []
    for _ in range(min(actual, len(state.library))):
        c = state.library.pop()
        state.hand.append(c)
        mark_seen(state, c)
        drawn.append(c.name)
        state.cards_drawn_total += 1

    if not draw_step:
        record_impact(state, reason, "draw", n)
    if drawn:
        state.log(f"{reason}: drew {', '.join(drawn)}")


def lose_each_opponent(state: GameState, amount: float, source: str = ""):
    if amount <= 0:
        return
    alive_before = sum(x > 0 for x in state.opponents)
    actual_total = 0.0
    new = []
    for x in state.opponents:
        dealt = min(max(0.0, x), amount)
        actual_total += dealt
        new.append(max(0.0, x - amount))
    state.opponents = new
    record_impact(state, source, "opponent_life_loss", actual_total)
    if source:
        state.log(f"{source}: each opponent -{amount:g}")
    check_win(state)


def lose_target_opponent(state: GameState, amount: float, source: str = ""):
    if amount <= 0 or not state.opponents:
        return
    i = max(range(len(state.opponents)), key=lambda j: state.opponents[j])
    actual = min(state.opponents[i], amount)
    state.opponents[i] = max(0.0, state.opponents[i] - amount)
    record_impact(state, source, "opponent_life_loss", actual)
    if source:
        state.log(f"{source}: target opponent -{amount:g}")
    check_win(state)




def create_tokens(
    state: GameState,
    strategy: Strategy,
    token_type: str,
    n: int,
    *,
    creature: bool = False,
    power: float = 1.0,
    toughness: float = 1.0,
    keywords: Optional[Set[str]] = None,
    allow_replacements: bool = True,
    source: str = "",
):
    if n <= 0:
        return

    foods_extra = 0
    if allow_replacements:
        if state.has("Peregrin Took"):
            foods_extra += 1
            record_impact(state, "Peregrin Took", "token_multiplier", 1)
            record_impact(state, "Peregrin Took", "food_created", 1)
        if state.has("Tippy-Toe, Terrific Partner"):
            foods_extra += 1
            record_impact(state, "Tippy-Toe, Terrific Partner", "token_multiplier", 1)
            record_impact(state, "Tippy-Toe, Terrific Partner", "food_created", 1)

    total_created = n + foods_extra
    kind = token_type.lower()

    if kind == "food":
        state.food += n
        record_impact(state, source, "food_created", n)
    elif kind == "treasure":
        state.treasure += n
        record_impact(state, source, "treasure_created", n)
    elif kind == "clue":
        state.clues += n
        record_impact(state, source, "clue_created", n)
    elif creature:
        state.creature_tokens.append(TokenGroup(
            name=token_type, count=n, power=power, toughness=toughness,
            keywords=set(keywords or set()), entered_turn=state.turn,
        ))
        vm = strategy.value_model or ValueModel.load()
        body_unit = (
            float(vm.values["creature_token_body_base"]) +
            power * float(vm.values["creature_token_power"]) +
            toughness * float(vm.values["creature_token_toughness"])
        )
        record_impact(state, source, "creature_tokens", body_unit * n)

    if foods_extra:
        state.food += foods_extra

    state.log(f"create tokens: {n} {token_type}" + (f" + {foods_extra} Food replacement" if foods_extra else ""))

    if state.has("Mirkwood Bats"):
        lose_each_opponent(state, total_created, "Mirkwood Bats")

    if state.has("Kambal, Profiteering Mayor"):
        lose_each_opponent(state, 1, "Kambal, Profiteering Mayor")
        gain_life(state, 1, "Kambal, Profiteering Mayor")

    if state.has("Baron Bertram Graywater") and not state.baron_triggered_this_turn:
        state.baron_triggered_this_turn = True
        create_tokens(
            state, strategy, "Vampire Rogue", 1,
            creature=True, power=1, toughness=1, keywords={"lifelink"},
            allow_replacements=True, source="Baron Bertram Graywater",
        )

    if creature:
        creature_entry_lifegain_events(state, n, batch_cards=[])


def apply_payment(state: GameState, plan: PaymentPlan, strategy: Optional[Strategy] = None):
    treasure_used = 0
    goose_used = 0
    for src, opt in plan.used:
        amount = output_total(opt)
        if src.kind == "treasure":
            treasure_used += 1
        elif src.kind == "goose":
            goose_used += 1
            if src.permanent_index is not None:
                tap_permanent(state, strategy, src.permanent_index, reason="mana")
        elif src.permanent_index is not None:
            tap_permanent(state, strategy, src.permanent_index, reason="mana")

        # Highlight nonland sources that actually generated mana.
        if src.label not in {"Plains", "Island", "Swamp", "Mountain", "Forest"}:
            perm = None
            if src.permanent_index is not None and 0 <= src.permanent_index < len(state.battlefield):
                perm = state.battlefield[src.permanent_index]
            if perm is None or not perm.card.is_land:
                record_impact(state, src.label, "mana_generated", amount)

        if src.life_delta_on_use > 0:
            gain_life(state, src.life_delta_on_use, source=src.label)
        elif src.life_delta_on_use < 0:
            state.life += src.life_delta_on_use

        if src.label.startswith("Talisman of ") and any(k in COLORS for k in opt):
            state.life -= 1

    if treasure_used:
        state.treasure -= treasure_used
        token_sacrificed(state, "Treasure", treasure_used, strategy)
    if goose_used:
        state.food -= goose_used
        token_sacrificed(state, "Food", goose_used, strategy)


def tutor_to_hand(state: GameState, predicate, priority: List[str], source: str, count: int = 1):
    candidates = [c for c in state.library if predicate(c)]
    chosen = []
    for _ in range(count):
        if not candidates:
            break
        c = max(candidates, key=lambda x: generic_tutor_score(x, priority))
        candidates.remove(c)
        state.library.remove(c)
        state.hand.append(c)
        mark_seen(state, c)
        chosen.append(c.name)
    if chosen:
        record_impact(state, source, "tutor", len(chosen))
        state.log(f"{source} tutor -> hand: {', '.join(chosen)}")


def tutor_to_top(state: GameState, predicate, priority: List[str], source: str):
    candidates = [c for c in state.library if predicate(c)]
    if not candidates:
        return
    c = max(candidates, key=lambda x: generic_tutor_score(x, priority))
    state.library.remove(c)
    state.library.append(c)
    record_impact(state, source, "tutor", 1)
    state.log(f"{source} tutor -> top: {c.name}")


def return_from_graveyard_to_hand(state: GameState, predicate, source: str, count: int = 1):
    candidates = [c for c in state.graveyard if predicate(c)]
    returned = 0
    for _ in range(min(count, len(candidates))):
        c = max(candidates, key=lambda x: generic_tutor_score(x, DEFAULT_TUTOR_PRIORITY))
        state.graveyard.remove(c)
        state.hand.append(c)
        mark_seen(state, c)
        candidates.remove(c)
        returned += 1
        state.log(f"{source}: returned {c.name} to hand")
    if returned:
        record_impact(state, source, "recursion", returned)


# ---------------------------------------------------------------------------
# X-spell value engine
# ---------------------------------------------------------------------------

@dataclass
class XPlan:
    x: int
    total_cost: int
    gross_value: float
    net_value: float
    roi: float
    metrics: Counter
    payment: PaymentPlan


def x_symbol_count(card: Card) -> int:
    return len(re.findall(r"\{X\}", first_mana_face(card.mana_cost).upper()))


def has_x_cost(card: Card) -> bool:
    return x_symbol_count(card) > 0


def x_base_cost_and_req(card: Card) -> Tuple[int, Counter]:
    # parse_mana_cost already treats X as zero.
    return parse_mana_cost(card.mana_cost)


def _virtual_target_cap(card: Card, state: GameState) -> Optional[int]:
    low = strip_reminder_text(card.oracle_text).lower()
    if "target cards from target player's graveyard" in low or "target cards from a graveyard" in low:
        return max(0, int(state.virtual_opponent_graveyard))
    return None


def x_effect_metrics(card: Card, x: int, state: GameState, strategy: Strategy) -> Counter:
    low = strip_reminder_text(card.oracle_text).lower()
    m = Counter()

    # Draw X.
    if re.search(r"\bdraw x cards?\b", low):
        m["draw"] += x

    # Gain X life.
    if re.search(r"\byou gain x life\b", low):
        m["life_gain"] += x

    # Drain/damage.
    if re.search(r"\beach opponent loses x life\b", low):
        m["opponent_life_loss"] += x * max(1, len(state.opponents))
    elif re.search(r"\btarget opponent loses x life\b", low):
        m["opponent_life_loss"] += x
    elif re.search(r"\bdeals x damage to (?:any target|target player|each opponent)\b", low):
        mult = len(state.opponents) if "each opponent" in low else 1
        m["opponent_life_loss"] += x * mult

    # Graveyard hate.
    if re.search(r"\bexile x target cards? from", low):
        m["grave_hate"] += x

    # Mill.
    if re.search(r"\bmill x\b", low) or re.search(r"\bputs? the top x cards", low):
        m["mill"] += x

    # +1/+1 counters.
    if re.search(r"\bput x \+1/\+1 counters?\b", low):
        m["counters"] += x

    # X token creation, including twice X.
    token_match = re.search(
        r"create (twice x|x) (?:(\d+)/(\d+) [^.,;]+ )?(food|treasure|clue|[^.,;]+?) tokens?",
        low
    )
    if token_match:
        mult = 2 if token_match.group(1) == "twice x" else 1
        n = x * mult
        token_name = token_match.group(4).strip()
        if "food" in token_name:
            m["food_created"] += n
        elif "treasure" in token_name:
            m["treasure_created"] += n
        elif "clue" in token_name:
            m["clue_created"] += n
        else:
            pwr = float(token_match.group(2) or 1)
            tou = float(token_match.group(3) or 1)
            vm = strategy.value_model or ValueModel.load()
            body = (
                float(vm.values["creature_token_body_base"]) +
                pwr * float(vm.values["creature_token_power"]) +
                tou * float(vm.values["creature_token_toughness"])
            )
            m["creature_tokens"] += body * n

    # Scalable creature removal is only valuable in opponent modes. In pure goldfish
    # it remains held by is_reactive_only().
    if re.search(r"(gets -x/-x|deals x damage to target creature|destroy up to x target)", low):
        if strategy.opponent_profile != "goldfish":
            # Diminishing estimate: X=3 is typically enough for a meaningful target.
            m["removal"] += min(1.5, x / 3.0)

    return m


def effective_cost_discount(card: Card, state: GameState) -> Tuple[int, Dict[str, int]]:
    raw = card.min_cost
    discount = 0
    attribution: Dict[str, int] = {}

    for p in state.battlefield:
        low = strip_reminder_text(p.card.oracle_text).lower()

        # Ezzaroot-style dynamic reduction.
        if card.is_creature and "creature spells you cast cost {x} less" in low and "amount of life you gained this turn" in low:
            d = max(0, int(math.floor(state.life_gained_this_turn_amount)))
            discount += d
            attribution[p.card.name] = attribution.get(p.card.name, 0) + d
            continue

        # Generic fixed cost reduction.
        fixed = re.findall(r"(?:spells|creature spells|artifact spells|enchantment spells) you cast cost \{(\d+)\} less", low)
        if fixed:
            applies = True
            if "creature spells" in low and not card.is_creature:
                applies = False
            if "artifact spells" in low and not card.is_artifact:
                applies = False
            if "enchantment spells" in low and not card.is_enchantment:
                applies = False
            if applies:
                d = max(int(x) for x in fixed)
                discount += d
                attribution[p.card.name] = attribution.get(p.card.name, 0) + d

    # Generic reductions cannot remove colored requirements. The payment solver will
    # still enforce colored pips.
    return discount, attribution


_SELF_SCALING_DISCOUNT_RE = re.compile(
    r"this spell costs \{(\d+)\} less to cast for each ([^.\n]+)\.", re.IGNORECASE,
)
# Additional-cost-CHOICE scaling ("as an additional cost..., exile/discard/
# sacrifice ... this spell costs {N} less ... this way") is a DIFFERENT
# mechanic from passive board-state scaling - the discount there depends on a
# choice the player makes while paying, not on something already countable on
# the board. Real project example: March of Wretched Sorrow (Decks/Bilbo
# V1.txt) - "As an additional cost to cast this spell, you may exile any
# number of black cards from your hand. This spell costs {2} less to cast for
# each card exiled this way." Deliberately NOT handled by
# boardwipe_self_scaling_discount below (see its docstring) - and moot for
# March of Wretched Sorrow specifically anyway, since it is an X-spell and
# cast_option's X-cost branch never reaches effective_cost_discount at all.
_ADDITIONAL_COST_CHOICE_MARKERS = ("as an additional cost", "this way")


def _count_self_scaling_condition(condition: str, state: GameState) -> int:
    """Board-state count for a 'for each <condition>' clause already matched
    by _SELF_SCALING_DISCOUNT_RE. Only a few known, real condition shapes are
    recognized (see boardwipe_self_scaling_discount's docstring for the real
    cards behind each) - an unrecognized condition returns 0 (no discount)
    rather than guessing, same caution as effective_cost_discount's own
    generic-reduction parsing above."""
    condition = condition.strip().lower()
    # NOTE: no "other" special-casing here, deliberately. "This spell costs
    # {N} less to cast for each other creature you control" is evaluated
    # WHILE PAYING - the spell is still on the stack/in hand, not yet a
    # permanent on the battlefield, so "other" only ever excludes itself
    # (which isn't there to begin with). Every matching permanent already on
    # the battlefield counts; unlike a static battlefield ability (where the
    # source itself IS one of the permanents and "other" genuinely excludes
    # it), there is nothing to subtract here.
    #
    # v4.33.0 fix: the REAL Blasphemous Act text is "...for each creature on
    # the battlefield" (confirmed against Scryfall), not "...you control" -
    # this engine has no separate opponent-battlefield model to distinguish
    # the two anyway (state.battlefield only ever holds the player's own
    # permanents in this goldfish simulation), so "on the battlefield" counts
    # the same way "you control" already did. Before this fix, the real card
    # text fell through every branch below to the final `return 0` - the
    # classic self-scaling discount case this function exists for was silent
    # for the actual real-world card, only "working" for the test fixture's
    # own (non-real) "...you control" wording. See ChatGPT external review
    # (Docs/README.md v4.33.0 entry).
    if "creature" in condition and (
        "you control" in condition or "on the battlefield" in condition
    ):
        return sum(1 for p in state.battlefield if p.card.is_creature)
    if "artifact" in condition and (
        "you control" in condition or "on the battlefield" in condition
    ):
        return sum(1 for p in state.battlefield if p.card.is_artifact)
    if "graveyard" in condition:
        gy = state.graveyard
        if "instant" in condition and "sorcery" in condition:
            return sum(1 for c in gy if c.is_instant or c.is_sorcery)
        if "creature" in condition:
            return sum(1 for c in gy if c.is_creature)
        return len(gy)
    if "opponent" in condition:
        return len(state.opponents)
    return 0


def boardwipe_self_scaling_discount(card: Card, state: GameState) -> Tuple[int, Dict[str, int]]:
    """
    v4.15.5. Real (not estimate-only) discount for a card's OWN self-
    referential "This spell costs {N} less to cast for each <board-state
    condition>" text - the Blasphemous-Act-shaped gap flagged since v4.11.0
    and explicitly named as unimplemented in ValueModel.
    boardwipe_effective_cost_estimate's own docstring ("wiring the actual
    payment/casting path ... is a separate, not-yet-built feature"). This IS
    that wiring: called from cast_option (App/engine.py) alongside
    effective_cost_discount, so a card like this is actually cheaper to cast
    in the real payment path, not just ranked as if it were.

    Real project examples confirming the shape (both grounded in the
    project's own decks, not hypothetical): Furygale Flocking (Decks/Aziza
    V2.txt, "{1} less ... for each instant and sorcery card in your
    graveyard") and the classic Blasphemous Act pattern ("{1} less ... for
    each creature ON THE BATTLEFIELD" - note: NOT "you control", confirmed
    against Scryfall; see _count_self_scaling_condition's v4.33.0 fix) this
    was originally flagged for.

    Deliberately narrower than effective_cost_discount's generic reduction
    parsing: only recognizes a handful of known, real condition shapes
    (creatures/artifacts you control, graveyard cards optionally filtered by
    type, opponents) via _count_self_scaling_condition - an unrecognized
    condition text yields NO discount rather than a guessed one.

    Deliberately does NOT handle additional-cost-CHOICE scaling (e.g. March
    of Wretched Sorrow's "exile cards from hand, costs less per card exiled
    this way") - see _ADDITIONAL_COST_CHOICE_MARKERS - that is a materially
    different mechanic (a choice made while paying, not a passive board-state
    count) and is moot for X-spells specifically anyway, since cast_option's
    X-cost branch never reaches this function.
    """
    text = strip_reminder_text(card.oracle_text or "")
    low = text.lower()
    if any(marker in low for marker in _ADDITIONAL_COST_CHOICE_MARKERS):
        return 0, {}
    m = _SELF_SCALING_DISCOUNT_RE.search(low)
    if not m:
        return 0, {}
    per_unit = int(m.group(1))
    count = _count_self_scaling_condition(m.group(2), state)
    if count <= 0 or per_unit <= 0:
        return 0, {}
    discount = per_unit * count
    return discount, {card.name: discount}


def delve_discount(card: Card, state: GameState) -> Tuple[int, Dict[str, int]]:
    """
    v4.22.0: Delve ("Each card you exile from your graveyard while casting
    this spell pays for {1}."). Wired the same way as
    boardwipe_self_scaling_discount right above - called from cast_option
    alongside it, and the actual exile happens in try_cast_option (keyed off
    this function's "Delve" attribution entry) so the discount is a REAL
    paid cost, not a free stat-line reduction.

    No real Delve card appeared in any of the 14 audited decks, so the
    "how much to delve" policy below is a reasonable default rather than a
    calibrated one: always delve the maximum useful amount (the whole
    generic portion of the cost, capped by graveyard size) - Delve can't
    reduce colored pips, and this engine has no other card that cares about
    graveyard SIZE (only Moldervine Reclamation, which triggers on a
    creature dying, not on graveyard occupancy) to weigh against emptying it.
    """
    if "delve" not in card.keywords:
        return 0, {}
    generic_portion = card.min_cost - sum(card.color_requirements.values())
    amount = max(0, min(generic_portion, len(state.graveyard)))
    if amount <= 0:
        return 0, {}
    return amount, {"Delve": amount}


# v4.22.0 scope note: Kicker ("You may pay an additional {cost} as you cast
# this spell. If this spell was kicked, ...") is deliberately NOT
# implemented, unlike Delve/Cycling/Prowess/Devour/Persist/Undying/Infect
# above. Those all hook a single well-defined, low-risk seam (a cost
# function feeding cast_option's existing discount pipeline, a shared
# death-event hook, a shared successful-cast funnel, a self-contained
# hand/mana side-activity). Kicker instead needs cast_option's own
# total-cost decision to conditionally go UP (not down) before find_payment
# runs, AND the resolution path (permanent_enters / resolve_direct_spell_
# effects / resolve_x_spell) to know after the fact whether the extra was
# paid, to apply a second, materially different effect. Wiring that
# correctly - without breaking the existing, working affordability/X-cost
# logic those functions already carry - is real surgery on the core casting
# path, not an additive hook, and no real Kicker card exists in any audited
# deck to calibrate a "when is it worth kicking" heuristic against. Left
# honestly unmodeled rather than wired in shallow/wrong; see also Wither's
# scope note in KNOWN_KEYWORDS's neighborhood (App/engine.py, "v4.21.0:
# infect / wither / persist / undying") for the same "documented gap, not a
# silent one" convention.


def _potential_cast_copy_multiplier(state: GameState) -> int:
    """
    WP9. Non-mutating estimate, for VALUATION only, of how many extra copies
    an instant/sorcery cast right now could get from Aziza/Mica - does not tap
    or sacrifice anything itself (that only happens for real, once the spell
    is actually cast, in _maybe_copy_cast_instant_or_sorcery). Mirrors the
    same copy_multiplier concept scenario_predicates' x_spell_lethal already
    uses (there it's an author-supplied scenario param; here best_x_plan has
    no scenario params to read, so it derives the same fact from the actual
    board state instead).
    """
    extra = 0
    if state.has(AZIZA_NAME) and sum(1 for p in state.creatures() if not p.tapped) >= 3:
        extra += 1
    if state.has(MICA_NAME) and any(p.card.is_artifact for p in state.battlefield):
        extra += 1
    return 1 + extra


def _x_spell_proximity_bonus(metrics: Counter, state: GameState, copy_multiplier: int, vm: "ValueModel") -> float:
    """
    v4.9.3. Face-damage X-spells are deliberately undervalued per-point
    (opponent_life_loss_per_point=0.42 in DEFAULT_VALUE_MODEL, well under
    mana_unit=1.0) because chip damage that doesn't threaten to close out
    the game is genuinely weak Commander value - that part of the model is
    not a bug. What it was missing: burn that gets CLOSE to a kill (even if
    not quite lethal this turn, see the lethal branch above for the exact-
    lethal case) should be worth much more per point than the same damage
    spread thin over a 40-life game, because it converts into real pressure
    (a follow-up kill next turn, forcing the opponent to react). Modeled the
    same way as _potential_cast_copy_multiplier feeds the lethal search:
    non-mutating, valuation-only, and it folds in a potential Aziza/Mica
    copy the same way "how close to lethal" already does there.

    proximity = how much of the opponent's remaining life this cast (times
    any potential copy) would take off, capped at 1.0 - always < 1 here in
    practice, since a cast that reaches exactly 1.0 would already have been
    caught by the lethal branch and never reach this value-mode search.
    The bonus itself is a single, JSON-tunable per-point add-on
    (x_spell_proximity_bonus_max, same "one named knob" convention as
    draw_curve/x_min_roi), scaled linearly by proximity - 0 far from a kill
    (unchanged, still-conservative chip-damage treatment), largest right at
    the edge of lethal range.
    """
    amount = float(metrics.get("opponent_life_loss", 0.0))
    if amount <= 0 or not state.opponents:
        return 0.0
    remaining = min(state.opponents)
    if remaining <= 0:
        return 0.0
    bonus_max = float(vm.values.get("x_spell_proximity_bonus_max", 0.0))
    if bonus_max <= 0:
        return 0.0
    proximity = min(1.0, (amount * copy_multiplier) / remaining)
    return amount * bonus_max * proximity


def best_x_plan(card: Card, state: GameState, strategy: Strategy) -> Optional[XPlan]:
    if not has_x_cost(card):
        return None

    vm = strategy.value_model or ValueModel.load()
    base, req = x_base_cost_and_req(card)
    x_count = x_symbol_count(card)
    target_cap = _virtual_target_cap(card, state)

    min_x = max(0, int(strategy.x_spell_minimums.get(card.name, 0)))
    explicit_max = strategy.x_spell_maximums.get(card.name)

    # Practical upper bound from current available mana.
    max_mana = available_mana_value(state, strategy)
    max_x = max(0, (max_mana - base) // max(1, x_count))
    if explicit_max is not None:
        max_x = min(max_x, int(explicit_max))
    if target_cap is not None:
        max_x = min(max_x, target_cap)

    # WP9: don't default to maximal X. First check for a LETHAL X, using the
    # same smallest-X-for-lethal search as scenario_predicates' x_spell_lethal
    # (App/scenario_predicates/handlers.py::_p_x_spell_lethal is the template
    # this generalizes into the actual casting decision) - if one exists,
    # cast exactly that, not the biggest affordable X. Only falls through to
    # the value-mode net-value search below when no X is lethal.
    if state.opponents:
        remaining = min(state.opponents)
        copy_multiplier = _potential_cast_copy_multiplier(state)
        if remaining > 0:
            for x in range(max(min_x, 1), max_x + 1):
                gross_cost = base + x_count * x
                discount, _attrib = effective_cost_discount(card, state)
                total_cost = max(sum(req.values()), gross_cost - discount)
                payment = find_payment(state, strategy, total_cost, req)
                if not payment:
                    continue
                metrics = x_effect_metrics(card, x, state, strategy)
                if not metrics:
                    continue
                damage = float(metrics.get("opponent_life_loss", 0.0)) * copy_multiplier
                if damage < remaining:
                    continue
                gross_value = vm.aggregate_value(metrics, strategy.archetypes, card.color_identity)
                cost_value = total_cost * float(vm.values["mana_unit"]) + float(vm.values["x_card_opportunity_cost"])
                net = gross_value - cost_value
                roi = gross_value / max(0.01, cost_value)
                return XPlan(x, total_cost, gross_value, net, roi, metrics, payment)

    # WP9 (v4.9.2 fix): no X was lethal (checked above). Avoid overkill in
    # this value mode the same way the lethal branch above avoids it -
    # search X from smallest to largest and take the FIRST one whose own
    # (undiscounted) net_value/ROI already clears the thresholds, rather
    # than collecting every affordable X, discounting each by a soft-cap
    # curve, and picking whichever discounted candidate scores highest.
    #
    # An earlier version of this branch (ValueModel.diminish_x_value, a
    # decay applied to gross_value for X beyond a fixed "soft cap") could
    # permanently zero out spells that are only profitable at high X: a
    # linear per-point effect whose thresholds aren't cleared until, say,
    # X=12 would already be decayed past viability by the time X reaches
    # the soft cap at X=6, so the search never got to see it un-crushed.
    # Real-run evidence (White Sun's Zenith: Seen=49, Cast=0 across 200
    # games, despite not being a reactive/held-back card) confirmed this
    # was happening. Smallest-viable-X has no such cliff: it simply keeps
    # walking X upward, on the real numbers, until something clears the
    # bar or the affordable range runs out.
    # v4.9.3: a potential Aziza/Mica copy also feeds the proximity bonus below
    # (closing distance to lethal, not just clearing the lethal bar outright).
    copy_multiplier = _potential_cast_copy_multiplier(state)
    min_roi = max(float(vm.values["x_min_roi"]), float(strategy.x_min_roi))
    min_net = max(float(vm.values["x_min_net_value"]), float(strategy.x_min_net_value))
    for x in range(min_x, max_x + 1):
        gross_cost = base + x_count * x
        discount, _attrib = effective_cost_discount(card, state)
        total_cost = max(sum(req.values()), gross_cost - discount)
        payment = find_payment(state, strategy, total_cost, req)
        if not payment:
            continue

        metrics = x_effect_metrics(card, x, state, strategy)
        if not metrics:
            continue

        gross_value = vm.aggregate_value(metrics, strategy.archetypes, card.color_identity)
        gross_value += _x_spell_proximity_bonus(metrics, state, copy_multiplier, vm)
        cost_value = total_cost * float(vm.values["mana_unit"]) + float(vm.values["x_card_opportunity_cost"])
        net = gross_value - cost_value
        roi = gross_value / max(0.01, cost_value)
        if roi < min_roi or net < min_net:
            continue
        return XPlan(x, total_cost, gross_value, net, roi, metrics, payment)

    return None


def resolve_x_spell(state: GameState, strategy: Strategy, card: Card, plan: XPlan):
    x = plan.x
    low = strip_reminder_text(card.oracle_text).lower()

    # Apply the same concrete effects used by the value engine.
    if re.search(r"\bdraw x cards?\b", low):
        draw_cards(state, x, reason=card.name)
    if re.search(r"\byou gain x life\b", low):
        gain_life(state, x, card.name)
    if re.search(r"\beach opponent loses x life\b", low):
        lose_each_opponent(state, x, card.name)
    elif re.search(r"\btarget opponent loses x life\b", low):
        lose_target_opponent(state, x, card.name)
    elif re.search(r"\bdeals x damage to (?:any target|target player|each opponent)\b", low):
        # WP9 bug fix: x_effect_metrics already valued this pattern (real
        # cards like Banefire/Crater's Claws use it) but no branch here ever
        # actually applied the damage - a burn-style X spell was scored for
        # AI decisions yet did nothing when actually cast. Surfaced by the
        # real-card test in tests/test_x_spell_copy.py.
        if "each opponent" in low:
            lose_each_opponent(state, x, card.name)
        else:
            lose_target_opponent(state, x, card.name)

    if re.search(r"\bexile x target cards? from", low):
        state.virtual_opponent_graveyard = max(0, state.virtual_opponent_graveyard - x)
        record_impact(state, card.name, "grave_hate", x)

    if re.search(r"\bmill x\b", low):
        record_impact(state, card.name, "mill", x)

    if re.search(r"\bput x \+1/\+1 counters?\b", low):
        record_impact(state, card.name, "counters", x)

    token_match = re.search(
        r"create (twice x|x) (?:(\d+)/(\d+) [^.,;]+ )?(food|treasure|clue|[^.,;]+?) tokens?",
        low
    )
    if token_match:
        mult = 2 if token_match.group(1) == "twice x" else 1
        n = x * mult
        token_name = token_match.group(4).strip()
        if "food" in token_name:
            create_tokens(state, strategy, "Food", n, source=card.name)
        elif "treasure" in token_name:
            create_tokens(state, strategy, "Treasure", n, source=card.name)
        elif "clue" in token_name:
            create_tokens(state, strategy, "Clue", n, source=card.name)
        else:
            create_tokens(
                state, strategy, token_name.title(), n, creature=True,
                power=float(token_match.group(2) or 1),
                toughness=float(token_match.group(3) or 1),
                source=card.name,
            )

    state.log(
        f"X-VALUE {card.name}: X={x}, gross={plan.gross_value:.2f}, "
        f"net={plan.net_value:.2f}, ROI={plan.roi:.2f}"
    )


@dataclass
class CastOption:
    card: Card
    total_cost: int
    payment: PaymentPlan
    x_plan: Optional[XPlan] = None
    discount_attribution: Dict[str, int] = field(default_factory=dict)






def cast_score_v4(opt: CastOption, state: GameState, strategy: Strategy) -> float:
    card = opt.card
    if opt.x_plan:
        # Let the value model drive scalable spells.
        return 3.0 + opt.x_plan.net_value + min(4.0, opt.x_plan.roi)

    score = cast_score(card, state, strategy)
    vm = strategy.value_model or ValueModel.load()

    # Add a light semantic estimate, without replacing the sequencing heuristics.
    if "draw" in card.roles:
        score += 0.5 * vm.metric_value("draw", max(1, direct_draw_count(card)), strategy.archetypes, card.color_identity)
    if "tutor" in card.roles:
        score += vm.metric_value("tutor", 1, strategy.archetypes) * 0.5
    if "lifegain_replacement" in card.roles:
        score += 3.0 if "lifegain" in strategy.archetypes else 1.5

    # v4.12.0 (Route C, "Baukastensystem"): card-shape factors that apply
    # regardless of category - each one independently JSON-tunable, added
    # rather than folded into one monolithic formula, per the user's own
    # request for a modular building-block system.
    if card.is_instant:
        # The user's own White-Sun's-Zenith-era observation: being an
        # instant (holding up mana, responding to the opponent) is worth
        # something on its own, separate from the effect itself.
        score += float(vm.values.get("instant_speed_premium", 0.5))
    if card.keywords:
        score += vm.keyword_value(card.keywords)
    if card.is_creature:
        score += vm.creature_body_value(card.power, card.toughness)
    return score


# ---------------------------------------------------------------------------
# Structural color access and commander sequencing
# ---------------------------------------------------------------------------

def structural_color_access(state: GameState, strategy: Strategy) -> Set[str]:
    """
    Colors the current battlefield can produce when untapped.
    This is intentionally different from remaining mana after actions.
    """
    out: Set[str] = set()
    for p in state.battlefield:
        q = Permanent(
            card=p.card,
            entered_turn=max(0, state.turn - 1),
            tapped=False,
            counters=p.counters,
            chosen_color=p.chosen_color,
        )
        for opt in card_mana_options(q, state, strategy):
            out.update(c for c in opt if c in COLORS)

    if state.treasure > 0:
        out.update(strategy.commander_colors or set(COLORS))
    return out


def cast_one_commander(state: GameState, strategy: Strategy) -> Optional[str]:
    if not state.command_zone:
        return None

    options = []
    for commander in list(state.command_zone):
        tax_count = int(state.commander_cast_counts[commander.name])
        base = commander.min_cost + 2 * tax_count
        discount, attribution = effective_cost_discount(commander, state)
        total = max(sum(commander.color_requirements.values()), base - discount)
        payment = find_payment(state, strategy, total, commander.color_requirements)
        if payment:
            # Cheap commander / engine commanders are preferred.
            score = 5.0 - total * 0.1
            if "lifegain_replacement" in commander.roles and "lifegain" in strategy.archetypes:
                score += 5
            options.append((score, commander, total, payment, attribution))

    if not options:
        return None

    _score, commander, total, payment, attribution = max(options, key=lambda x: x[0])
    apply_payment(state, payment, strategy)
    state.command_zone.remove(commander)
    state.commander_cast_counts[commander.name] += 1
    state.commander_casts += 1
    record_impact(state, commander.name, "cast", 1)
    record_impact(state, commander.name, "mana_spent", total)
    for source, amount in attribution.items():
        record_impact(state, source, "mana_discount", amount)
    permanent_enters(state, strategy, commander)
    record_impact(state, commander.name, "entered", 1)
    state.log(f"CAST COMMANDER {commander.name}")
    return commander.name


def _cast_early_ramp_before_commander(state: GameState, strategy: Strategy) -> List[str]:
    """
    Turns 1-2: develop cheap ramp. From turn 3 onward the commander gets priority
    when strategy.commander_priority == 'high'.
    """
    casts = []
    if state.turn > 2:
        return casts
    for _ in range(4):
        opts = []
        for c in state.hand:
            if c.is_land or "ramp" not in c.roles or c.min_cost > 2:
                continue
            o = cast_option(c, state, strategy)
            if o:
                opts.append(o)
        if not opts:
            break
        o = max(opts, key=lambda x: cast_score_v4(x, state, strategy))
        if try_cast_option(state, strategy, o):
            casts.append(o.card.name)
        else:
            break
    return casts


# ---------------------------------------------------------------------------
# Abstract opponent profiles (experimental)
# ---------------------------------------------------------------------------

OPPONENT_PROFILES = {
    "goldfish": {
        "damage_scale": 0.0, "removal": 0.0, "wipe": 0.0, "block_factor": 1.00,
    },
    "aggro": {
        "damage_scale": 1.40, "removal": 0.07, "wipe": 0.01, "block_factor": 0.78,
    },
    "midrange": {
        "damage_scale": 0.90, "removal": 0.14, "wipe": 0.035, "block_factor": 0.68,
    },
    "control": {
        "damage_scale": 0.45, "removal": 0.24, "wipe": 0.075, "block_factor": 0.58,
    },
    "horde": {
        "damage_scale": 2.20, "removal": 0.0, "wipe": 0.0, "block_factor": 0.72,
    },
}


def _consume_protection(state: GameState, wide: bool = False) -> Optional[str]:
    preferred = (
        ["Heroic Intervention", "Eerie Interlude", "Cosmic Intervention"]
        if wide else
        ["Royal Treatment", "Heroic Intervention", "Eerie Interlude", "Armor of Shadows"]
    )
    for name in preferred:
        card = next((c for c in state.hand if c.name == name), None)
        if card:
            state.hand.remove(card)
            state.graveyard.append(card)
            record_impact(state, name, "protection", 1)
            state.log(f"{name}: used against abstract opponent interaction")
            return name
    return None




def attack_phase(state: GameState, strategy: Strategy):
    """
    Use v3 combat, but apply an abstract-blocker damage correction in opponent modes.
    The correction is done by temporarily padding opponent life and then applying
    only the expected unblocked fraction of the damage delta.
    """
    if strategy.opponent_profile == "goldfish":
        before = list(state.opponents)
        _V3_attack_phase(state, strategy)
        # Attribute total combat life lost back to attackers only at aggregate level.
        delta = sum(max(0, a-b) for a, b in zip(before, state.opponents))
        if delta:
            record_impact(state, "Combat", "combat_damage", delta)
        return

    profile = OPPONENT_PROFILES.get(strategy.opponent_profile, OPPONENT_PROFILES["midrange"])
    before = list(state.opponents)
    _V3_attack_phase(state, strategy)
    raw_loss = [max(0.0, a-b) for a, b in zip(before, state.opponents)]
    factor = float(profile["block_factor"])
    # Restore the blocked share.
    state.opponents = [
        max(0.0, before_i - raw * factor)
        for before_i, raw in zip(before, raw_loss)
    ]
    record_impact(state, "Combat", "combat_damage", sum(raw_loss) * factor)
    check_win(state)


# ---------------------------------------------------------------------------
# Card interpretation / impact report
# ---------------------------------------------------------------------------

def card_value_primitives(card: Card) -> List[str]:
    low = strip_reminder_text(card.oracle_text).lower()
    items = []
    if has_x_cost(card):
        items.append("X spell: dynamic value/ROI evaluation")
    if "draw" in card.roles or "draw_engine" in card.roles:
        items.append("card draw / card advantage")
    if "lifegain" in card.roles:
        items.append("lifegain source")
    if "lifegain_replacement" in card.roles:
        items.append("lifegain amplifier / replacement effect")
    if "lifegain_payoff" in card.roles:
        items.append("lifegain payoff")
    if "ramp" in card.roles:
        items.append("mana acceleration")
    if "tutor" in card.roles:
        items.append("tutor")
    if "recursion" in card.roles:
        items.append("recursion")
    if "token" in card.roles:
        items.append("token production")
    if "interaction" in card.roles:
        items.append("interaction (held in pure goldfish)")
    if "protection" in card.roles:
        items.append("protection (held unless opponent mode needs it)")
    if "copy" in low:
        items.append("copy effect (simple cast-copy patterns supported)")
    if "cost" in low and "less" in low:
        items.append("cost reduction (fixed + life-gained creature reduction supported)")
    if card.keywords:
        items.append("keywords: " + ", ".join(sorted(card.keywords)))
    return items


def interpretation_text(card: Card, strategy: Strategy) -> str:
    vm = strategy.value_model or ValueModel.load()
    lines = [
        f"Roles: {', '.join(sorted(card.roles)) or 'none detected'}",
        f"Keywords/actions: {', '.join(sorted(card.keywords)) or 'none detected'}",
        "",
        "Goldfish interpretation:",
    ]
    primitives = card_value_primitives(card)
    lines.extend(f"- {x}" for x in primitives or ["no special heuristic beyond mana/curve/permanent combat"])

    if has_x_cost(card):
        lines += [
            "",
            "X evaluation:",
            "- X is not fixed.",
            "- v4 tests every currently payable X.",
            "- It estimates mana-equivalent benefit, subtracts mana + card opportunity cost,",
            "  then requires minimum ROI/net value before casting.",
            f"- Current default minimum ROI: {strategy.x_min_roi:.2f}",
            f"- Current default minimum net value: {strategy.x_min_net_value:.2f}",
        ]
    return "\n".join(lines)


def impact_rows_from_aggregate(
    deck: List[Card],
    aggregate: Dict[str, Counter],
    runs: int,
    strategy: Strategy,
) -> List[dict]:
    vm = strategy.value_model or ValueModel.load()
    card_names = sorted({c.name for c in deck})
    by_name = {c.name: c for c in deck}
    rows = []
    for name in card_names:
        m = aggregate.get(name, Counter())
        c = by_name.get(name)
        value = vm.aggregate_value(m, strategy.archetypes, c.color_identity if c else None)
        seen = float(m.get("seen", 0))
        cast_n = float(m.get("cast", 0))
        mana_spent = float(m.get("mana_spent", 0))
        synergy = (
            vm.metric_value("life_amplified", m.get("life_amplified", 0), strategy.archetypes)
            + vm.metric_value("token_multiplier", m.get("token_multiplier", 0), strategy.archetypes)
            + vm.metric_value("mana_discount", m.get("mana_discount", 0), strategy.archetypes)
            + vm.metric_value("spell_copy", m.get("spell_copy", 0), strategy.archetypes)
        )
        rows.append({
            "Name": name,
            "Seen": round(seen, 2),
            "Cast": round(cast_n, 2),
            "Cast rate when seen %": round(100 * cast_n / seen, 2) if seen else 0,
            "Mana spent": round(mana_spent, 2),
            "Life gained base": round(m.get("life_gain", 0), 2),
            "Life amplified": round(m.get("life_amplified", 0), 2),
            "Cards drawn": round(m.get("draw", 0), 2),
            "Opponent life lost": round(m.get("opponent_life_loss", 0), 2),
            "Mana generated": round(m.get("mana_generated", 0), 2),
            "Mana discounted": round(m.get("mana_discount", 0), 2),
            "Food created": round(m.get("food_created", 0), 2),
            "Treasure created": round(m.get("treasure_created", 0), 2),
            "Creature token value units": round(m.get("creature_tokens", 0), 2),
            "Counters": round(m.get("counters", 0), 2),
            "Tutor cards": round(m.get("tutor", 0), 2),
            "Recursion cards": round(m.get("recursion", 0), 2),
            "Copies": round(m.get("spell_copy", 0), 2),
            "Protection uses": round(m.get("protection", 0), 2),
            "Estimated total value": round(value, 3),
            "Estimated value / seen": round(value / seen, 3) if seen else 0,
            "Estimated value / cast": round(value / cast_n, 3) if cast_n else 0,
            "Estimated value / mana spent": round(value / mana_spent, 3) if mana_spent else 0,
            "Synergy value": round(synergy, 3),
            "Synergy value / seen": round(synergy / seen, 3) if seen else 0,
        })

    # Highlight tiers are relative to the deck, not universal card grades.
    eligible = sorted(
        [r["Estimated value / seen"] for r in rows if r["Seen"] >= max(5, runs * 0.01)]
    )
    if eligible:
        q75 = percentile(eligible, .75)
        q90 = percentile(eligible, .90)
        q97 = percentile(eligible, .97)
    else:
        q75 = q90 = q97 = 999999

    for r in rows:
        v = r["Estimated value / seen"]
        if r["Seen"] < max(5, runs * 0.01):
            tier = "insufficient sample"
        elif v >= q97:
            tier = "S"
        elif v >= q90:
            tier = "A"
        elif v >= q75:
            tier = "B"
        else:
            tier = "C"
        r["Relative highlight tier"] = tier

    return sorted(rows, key=lambda r: r["Estimated value / seen"], reverse=True)


# ---------------------------------------------------------------------------
# v4 simulation
# ---------------------------------------------------------------------------

def _available_options(state: GameState, strategy: Strategy) -> List[CastOption]:
    opts = []
    for c in state.hand:
        if c.is_land:
            continue
        o = cast_option(c, state, strategy)
        if o:
            opts.append(o)
    return opts


def _play_proactive_cards(state: GameState, strategy: Strategy, min_score: float, limit: int = 20) -> List[str]:
    casts = []
    for _ in range(limit):
        opts = _available_options(state, strategy)
        if not opts:
            break
        opts.sort(key=lambda o: cast_score_v4(o, state, strategy), reverse=True)
        o = opts[0]
        if cast_score_v4(o, state, strategy) < min_score:
            break
        if try_cast_option(state, strategy, o):
            casts.append(o.card.name + (f"(X={o.x_plan.x})" if o.x_plan else ""))
        else:
            break
    return casts


def simulate_game_v4(
    deck: List[Card],
    strategy_template: Strategy,
    cfg: SimConfig,
    policy: MulliganPolicy,
    rng: random.Random,
    run_id: int,
):
    commanders = [c for c in deck if c.commander]
    library = deck[:]
    for commander in commanders:
        if commander in library:
            library.remove(commander)

    hand, rest, mulligans, mull_history = london_mulligan(library, policy, cfg, rng)
    rng.shuffle(rest)

    strategy = replace(strategy_template)
    if commanders and not strategy.commander_colors:
        strategy.commander_colors = set().union(*(c.color_identity for c in commanders))

    state = GameState(
        library=rest,
        hand=hand[:],
        command_zone=commanders[:],
        life=cfg.starting_life,
    )

    for c in hand:
        mark_seen(state, c)
    for c in commanders:
        mark_seen(state, c)

    opening_hand = [c.name for c in hand]
    turn_rows = []

    for turn in range(1, cfg.turns + 1):
        if state.win_turn is not None or state.lost_turn is not None:
            # Keep rows rectangular while not continuing game actions.
            pass

        state.turn = turn
        state.nontoken_creatures_entered_this_turn = 0
        state.gained_life_this_turn = False
        state.life_gained_this_turn_amount = 0.0
        state.baron_triggered_this_turn = False
        state.life_events_this_turn = 0
        state.well_caps_this_turn = []
        state.trudge_garden_triggers_this_turn = 0
        state.frying_pan_bonus_this_turn = 0.0
        state.event_log = []
        untap_step(state)

        # Keep virtual graveyard plausible even in pure goldfish.
        state.virtual_opponent_graveyard = max(
            state.virtual_opponent_graveyard,
            max(0, int(turn * 1.25 - 1)),
        )

        draw_cards(state, 1, draw_step=True, reason="draw step")
        start_hand = [c.name for c in state.hand]

        # Land drop.
        land = choose_land(state, strategy)
        land_name = ""
        if land:
            state.hand.remove(land)
            land_name = land.name
            land_enters(state, strategy, land)

        structural_access_before = structural_color_access(state, strategy)
        mana_before = available_mana_value(state, strategy)
        casts = []

        # Turns 1-2: cheap ramp first.
        casts.extend(_cast_early_ramp_before_commander(state, strategy))

        # From turn 3, high-priority commanders are deployed BEFORE generic value plays.
        if strategy.commander_priority == "high" and turn >= 3:
            commander_name = cast_one_commander(state, strategy)
            if commander_name:
                casts.append(f"Commander:{commander_name}")

        # Arkenstone Adventure remains an explicit special case.
        arken = next((c for c in state.hand if c.name == "The Arkenstone"), None)
        if arken and try_cast_arkenstone_adventure(state, strategy, arken):
            record_impact(state, "The Arkenstone", "cast", 1)
            record_impact(state, "The Arkenstone", "mana_spent", 3)
            casts.append("Seek the Heart")

        casts.extend(_play_proactive_cards(state, strategy, min_score=0.0, limit=20))

        if try_cast_adventure_permanent_from_exile(state, strategy):
            record_impact(state, "The Arkenstone", "cast", 1)
            record_impact(state, "The Arkenstone", "mana_spent", 5)
            casts.append("The Arkenstone(from exile)")

        # Normal/low commander priority gets a chance after development.
        if strategy.commander_priority != "high":
            commander_name = cast_one_commander(state, strategy)
            if commander_name:
                casts.append(f"Commander:{commander_name}")

        try_activate_bilbo(state, strategy)
        attack_phase(state, strategy)

        # Second main.
        casts.extend(_play_proactive_cards(state, strategy, min_score=1.0, limit=10))
        try_activate_bilbo(state, strategy)

        end_step(state, strategy)
        try_activate_bilbo(state, strategy)

        # Board-turn attribution for persistent engines.
        for p in state.battlefield:
            if not p.card.is_land:
                record_impact(state, p.card.name, "board_turns", 1)

        apply_abstract_opponent_phase(state, strategy, rng)

        reactive_held = hold_reactive_count(state, strategy)
        state.reactive_held_total += reactive_held
        remaining_access = color_access(state, strategy)
        structural_access_after = structural_color_access(state, strategy)

        turn_rows.append({
            "run": run_id,
            "turn": turn,
            "start_hand": " | ".join(start_hand),
            "land_played": land_name,
            "casts": " | ".join(casts),
            "events": " || ".join(state.event_log),
            "end_hand": " | ".join(c.name for c in state.hand),
            "hand_size": len(state.hand),
            "lands_in_play": len(state.lands()),
            "mana_available_start_main": mana_before,
            "available_mana_after_actions": available_mana_value(state, strategy),
            "structural_color_access_before_actions": "".join(c for c in COLORS if c in structural_access_before),
            "structural_color_access_after_actions": "".join(c for c in COLORS if c in structural_access_after),
            "remaining_untapped_color_access": "".join(c for c in COLORS if c in remaining_access),
            "has_all_commander_colors_structural": int(
                bool(strategy.commander_colors) and strategy.commander_colors <= structural_access_after
            ),
            "life": round(state.life, 2),
            "damage_taken": round(state.damage_taken, 2),
            "opponent_life": " | ".join(str(round(x, 2)) for x in state.opponents),
            "virtual_opponent_graveyard": state.virtual_opponent_graveyard,
            "food": state.food,
            "treasure": state.treasure,
            "clues": state.clues,
            "reactive_cards_held": reactive_held,
            "life_events_this_turn": state.life_events_this_turn,
            "life_gained_this_turn": round(state.life_gained_this_turn_amount, 2),
            "bilbo_activated": int(state.bilbo_activation_turn == turn),
            "win": int(state.win_turn == turn),
            "loss": int(state.lost_turn == turn),
        })

        if state.win_turn is not None or state.lost_turn is not None:
            # Stop playing after a resolved outcome; future-turn distributions should
            # not count fake game actions.
            break

    run_row = {
        "run": run_id,
        "mulligans": mulligans,
        "opening_hand": " | ".join(opening_hand),
        "opening_land_count": sum(c.is_land for c in hand),
        "opening_cheap_spells": sum((not c.is_land) and c.min_cost <= 3 for c in hand),
        "opening_early_ramp": sum("ramp" in c.roles and c.min_cost <= 3 for c in hand),
        "lands_end": len(state.lands()),
        "hand_size_end": len(state.hand),
        "life_end": round(state.life, 2),
        "damage_taken": round(state.damage_taken, 2),
        "food_end": state.food,
        "treasure_end": state.treasure,
        "cards_drawn_total": state.cards_drawn_total,
        "scry_count": state.scry_count,
        "surveil_count": state.surveil_count,
        "connive_count": state.connive_count,
        "bilbo_activation_turn": state.bilbo_activation_turn or "",
        "win_turn": state.win_turn or "",
        "loss_turn": state.lost_turn or "",
        "opponents_remaining": sum(x > 0 for x in state.opponents),
        "life_50_turn": state.milestones[50] or "",
        "life_60_turn": state.milestones[60] or "",
        "life_80_turn": state.milestones[80] or "",
        "life_100_turn": state.milestones[100] or "",
        "life_111_turn": state.milestones[111] or "",
        "reactive_held_total_turn_snapshots": state.reactive_held_total,
    }
    opening_row = {
        "run": run_id,
        "mulligans": mulligans,
        "opening_hand": " | ".join(opening_hand),
        "mulligan_history": " || ".join(mull_history),
    }
    return run_row, turn_rows, opening_row, state.impact


# ---------------------------------------------------------------------------
# Output / AI handoff
# ---------------------------------------------------------------------------

def commander_eligible_card(card: Card) -> bool:
    """Conservative Commander eligibility used to prevent accidental lands/spells."""
    low_type = (card.type_line or "").lower()
    low_text = strip_reminder_text(card.oracle_text).lower()
    return (
        ("legendary" in low_type and "creature" in low_type)
        or "can be your commander" in low_text
    )


def build_deck_v4(
    input_path: Path,
    commander_names: Sequence[str],
    cache_path: Path,
    offline: bool,
    metadata_csv: Optional[Path],
) -> List[Card]:
    # Load metadata once without relying on v3's single-commander marker.
    deck = build_deck(
        input_path,
        commander_name=None,
        cache_path=cache_path,
        offline=offline,
        metadata_csv=metadata_csv,
    )
    requested = set(commander_names)
    eligible_names = {c.name for c in deck if commander_eligible_card(c)}
    # Silently discard impossible accidental selections such as Command Tower.
    names = requested & eligible_names
    return [replace(c, commander=(c.name in names)) for c in deck]


def detect_commander_hints(path: Path) -> List[str]:
    """Scans a TXT-family decklist for its Commander section header and
    collects the card name(s) listed under it, WITHOUT requiring the full
    Scryfall-backed build_deck_v4 (used to pre-select commanders before a
    deck is fully loaded).

    v4.15.9 (Fremd-Deck-Import): recognizes a bare "Commander"/"Commanders"/
    "EDH" header line, not just "// Commander" - Moxfield/EDHREC-style
    exports don't always use the "//" comment convention. Behavior for
    "//"-prefixed headers is unchanged from before this version.

    v4.16.0 (Fremd-Deck-Import cont'd): also recognizes a real precon-export
    quirk with NO section header at all - a flat card list where only the
    commander's own line carries a trailing "(Commander)" annotation, e.g.
    "1 Dina, Essence Brewer (Commander)". This check runs independently of
    the header-based scan below (so it works even with zero headers in the
    file) and de-duplicates against header-based hints.
    """
    if path.suffix.lower() not in {".txt", ".dek", ".list"}:
        return []
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    hints = []

    def _add_hint(name: str) -> None:
        if name and name not in hints:
            hints.append(name)

    active = False
    for raw in lines:
        s = raw.strip()
        if not s:
            if active and hints:
                break
            continue
        is_card_line = s[:1].isdigit()
        # Strip a trailing "(Commander)" annotation once, up front, so both
        # the inline check below and the header-active match at the bottom
        # of the loop see the same clean card name (matching what
        # load_txt_entries actually parses) instead of each computing it
        # independently and risking two different hint strings for one line.
        card_line = _TRAILING_COMMANDER_ANNOTATION_RE.sub("", s).strip() if is_card_line else s
        has_inline_annotation = is_card_line and card_line != s
        if has_inline_annotation:
            m_inline = TXT_LINE_RE.match(card_line)
            if m_inline:
                _add_hint(normalize_name(m_inline.group("name")))
        if s.startswith("//"):
            kind = _classify_txt_header(s[2:].strip())
            if kind == "commander":
                active = True
            elif active:
                break
            continue
        if not is_card_line:
            kind = _classify_txt_header(s)
            if kind == "commander":
                active = True
            elif kind is not None and active:
                break
            # An unrecognized bare header (category header, prose) doesn't
            # end an active commander section by itself - mirrors the
            # pre-v4.15.9 "// Commander"-only behavior, where only another
            # recognized/"//" header (or a blank line once hints exist)
            # closes the section.
            continue
        if active:
            m = TXT_LINE_RE.match(card_line)
            if m:
                _add_hint(normalize_name(m.group("name")))
    return hints


def summarize_v4(
    deck: List[Card],
    run_rows: List[dict],
    turn_rows: List[dict],
    cfg: SimConfig,
    strategy: Strategy,
    impact_rows: List[dict],
) -> dict:
    commanders = [c.name for c in deck if c.commander]
    lands = sum(c.is_land for c in deck)
    roles = Counter(role for c in deck for role in c.roles)
    keywords = Counter(kw for c in deck for kw in c.keywords)
    pips = Counter()
    curve = Counter()
    for c in deck:
        if not c.is_land:
            curve[int(math.ceil(c.mana_value))] += 1
            pips.update(c.color_requirements)

    by_turn = {}
    for t in range(1, cfg.turns + 1):
        rows = [r for r in turn_rows if int(r["turn"]) == t]
        if not rows:
            continue
        by_turn[str(t)] = {
            "games_still_active_or_finishing_this_turn": len(rows),
            "avg_hand_size": mean_numeric(rows, "hand_size"),
            "avg_life": mean_numeric(rows, "life"),
            "avg_lands": mean_numeric(rows, "lands_in_play"),
            "all_commander_colors_structural_pct": mean_numeric(rows, "has_all_commander_colors_structural") * 100,
            "avg_food": mean_numeric(rows, "food"),
            "avg_mana_start_main": mean_numeric(rows, "mana_available_start_main"),
            "win_pct_this_turn_of_rows": mean_numeric(rows, "win") * 100,
            "loss_pct_this_turn_of_rows": mean_numeric(rows, "loss") * 100,
            "bilbo_activation_pct_this_turn_of_rows": mean_numeric(rows, "bilbo_activated") * 100,
        }

    win_turns = [float(r["win_turn"]) for r in run_rows if str(r["win_turn"]).strip()]
    bilbo_turns = [float(r["bilbo_activation_turn"]) for r in run_rows if str(r["bilbo_activation_turn"]).strip()]
    loss_turns = [float(r["loss_turn"]) for r in run_rows if str(r["loss_turn"]).strip()]

    highlights = [
        {
            "name": r["Name"],
            "tier": r["Relative highlight tier"],
            "value_per_seen": r["Estimated value / seen"],
            "synergy_value_per_seen": r["Synergy value / seen"],
        }
        for r in impact_rows
        if r["Relative highlight tier"] in {"S", "A"}
    ][:15]

    return {
        "version": V4_VERSION,
        "simulation": {
            "runs": cfg.runs,
            "turns": cfg.turns,
            "seed": cfg.seed,
            "opponent_profile": strategy.opponent_profile,
            "strategy_tags": sorted(strategy.archetypes),
        },
        "deck": {
            "cards": len(deck),
            "commanders": commanders,
            "lands": lands,
            "curve": dict(sorted(curve.items())),
            "colored_pips": dict(pips),
            "role_counts": dict(roles),
            "keyword_counts": dict(keywords),
        },
        "opening": {
            "avg_mulligans": mean_numeric(run_rows, "mulligans"),
            "avg_opening_lands": mean_numeric(run_rows, "opening_land_count"),
            "avg_opening_early_ramp": mean_numeric(run_rows, "opening_early_ramp"),
        },
        "outcomes": {
            "win_by_turn_limit_pct": pct_with_value(run_rows, "win_turn"),
            "loss_by_turn_limit_pct": pct_with_value(run_rows, "loss_turn"),
            "median_win_turn_when_winning": percentile(win_turns, .5) if win_turns else None,
            "median_loss_turn_when_losing": percentile(loss_turns, .5) if loss_turns else None,
            "bilbo_activation_pct": pct_with_value(run_rows, "bilbo_activation_turn"),
            "median_bilbo_activation_turn": percentile(bilbo_turns, .5) if bilbo_turns else None,
            "reach_50_life_pct": pct_with_value(run_rows, "life_50_turn"),
            "reach_60_life_pct": pct_with_value(run_rows, "life_60_turn"),
            "reach_80_life_pct": pct_with_value(run_rows, "life_80_turn"),
            "reach_100_life_pct": pct_with_value(run_rows, "life_100_turn"),
            "reach_111_life_pct": pct_with_value(run_rows, "life_111_turn"),
            "avg_end_hand": mean_numeric(run_rows, "hand_size_end"),
            "avg_end_life": mean_numeric(run_rows, "life_end"),
            "avg_cards_drawn": mean_numeric(run_rows, "cards_drawn_total"),
            "avg_scry": mean_numeric(run_rows, "scry_count"),
            "avg_surveil": mean_numeric(run_rows, "surveil_count"),
            "avg_connive": mean_numeric(run_rows, "connive_count"),
        },
        "relative_card_highlights": highlights,
        "by_turn": by_turn,
        "value_model_note": (
            "Card value is a heuristic mana-equivalent model, adjusted by selected strategy tags. "
            "Highlight tiers are relative within this simulated deck, not universal card grades."
        ),
        "limitations": [
            "This is a heuristic deck-development simulator, not a complete Magic rules engine.",
            "Pure goldfish has no real blockers/removal/counterspells. Abstract opponent profiles are deliberately coarse and are NOT matchup win-rate models.",
            "Ward/hexproof/indestructible matter only in abstract opponent modes and still use simplified interaction.",
            "X-spell valuation only understands effect patterns represented by the parser; unrecognized X effects are held rather than guessed.",
            "Card-impact attribution captures modeled effects. An unimplemented ability can make a strong real card look weak.",
            "Copy/cost-reduction/token-multiplier support is partial and pattern-based.",
            "Full precon-vs-precon simulation would require a substantially more complete rules/priority/targeting engine."
        ],
    }


def write_ai_analysis_instructions(
    path: Path,
    deck_file: Path,
    summary_file: str,
    strategy: Strategy,
):
    known_tags = ", ".join(sorted(strategy.archetypes)) if strategy.archetypes else "UNKNOWN / not supplied"
    text = f"""# AI ANALYSIS INSTRUCTIONS — Commander Goldfish v4

This folder/ZIP was produced by Commander Goldfish Simulator v4.

## First action
The selected strategy/archetype tags are: **{known_tags}**.

If these tags are empty, obviously wrong, or insufficient to explain the deck, ASK THE USER
for the deck's intended strategy before making card-cut/add recommendations. Examples:
lifegain, mill, counters, Voltron, tokens, aristocrats, spellslinger, artifacts,
enchantress, graveyard, lands, control, aggro, combo.

## Files
- `{deck_file.name}`: original deck export.
- `deck_enriched.csv`: card metadata, roles, keywords/actions and Oracle text.
- `{summary_file}`: headline simulation metrics and limitations.
- `runs.csv`: one row per simulated game.
- `turns.csv`: turn-by-turn state/action log.
- `opening_hands.csv`: kept hands and mulligan histories.
- `card_impact.csv`: modeled per-card contribution/value/highlight data.
- `simulation_config.json`: exact run configuration and selected strategy.
- `value_model.json`: mana-equivalent heuristic used for X spells and card highlighting.

## Required interpretation discipline
1. Distinguish **measured simulator output** from **real-game inference**.
2. Do NOT treat simulated win percentage as a real pod win rate.
3. Check `limitations` in the summary before recommending changes.
4. A low card-impact score may mean the ability is not modeled; inspect Oracle text and
   the enriched interpretation before calling a card weak.
5. High value is strategy-relative. A lifegain amplifier in a lifegain deck is intentionally
   weighted more heavily than in an unrelated deck.
6. For X spells, inspect logged `X-VALUE` events. v4 chooses X dynamically from current
   mana and a mana-equivalent benefit/ROI model; X is not hardcoded.
7. Color access has two meanings:
   - structural color access = colors the battlefield can produce when untapped;
   - remaining untapped color access = mana still available after actions.
   Use structural access for manabase conclusions.
8. Abstract opponent profiles (Aggro/Midrange/Control/Horde) are stress tests only.
   They are not actual decks and do not reproduce full Magic rules.

## Suggested analysis order
- Validate deck size, commander(s), land count, curve and colored pips.
- Opening hand / mulligan quality.
- Structural color access by turns 2–5.
- Mana development and missed/late development.
- Hand size / card-advantage trajectory.
- Strategy-specific milestones (e.g. life totals, mill, counters, token volume).
- Commander timing and main win-condition timing.
- Alternative win conditions.
- `card_impact.csv`: identify high-value engines and underperformers, then cross-check
  each against whether its important abilities are actually modeled.
- Only then propose swaps.

## Important
If the user asks whether the deck is "good", explain both:
(A) what the goldfish data supports, and
(B) what remains uncertain because opponents, hidden information, politics and full
Magic rules are not simulated.
"""
    path.write_text(text, encoding="utf-8")


def write_value_model(path: Path, vm: ValueModel):
    path.write_text(json.dumps(vm.values, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline_v4(
    deck_file: Path,
    commander_names: Sequence[str],
    *,
    runs: int = 5000,
    turns: int = 10,
    seed: int = 1,
    strategy_file: Optional[Path] = None,
    strategy_tags: Optional[Set[str]] = None,
    opponent_profile: str = "goldfish",
    value_model_file: Optional[Path] = None,
    cache_path: Optional[Path] = None,
    offline: bool = False,
    metadata_csv: Optional[Path] = None,
    output_root: Optional[Path] = None,
    progress_callback=None,
):
    deck_file = Path(deck_file)
    vm = ValueModel.load(value_model_file)
    cache_path = cache_path or (Path(__file__).resolve().parent / ".scryfall_card_cache_v4.json")

    deck = build_deck_v4(
        deck_file,
        commander_names,
        cache_path,
        offline,
        metadata_csv,
    )
    commander = next((c for c in deck if c.commander), None)
    strategy = load_strategy(
        strategy_file,
        commander,
        archetypes=strategy_tags,
        opponent_profile=opponent_profile,
        value_model=vm,
    )
    if commander_names:
        strategy.commander_colors = set().union(
            *(c.color_identity for c in deck if c.commander)
        )

    cfg = SimConfig(runs=runs, turns=turns, seed=seed)
    policy = MulliganPolicy()
    rng = random.Random(seed)

    timestamp = _datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(output_root or (deck_file.parent / "Goldfish_Results"))
    result_dir = root / f"{deck_file.stem}_v4_{timestamp}"
    result_dir.mkdir(parents=True, exist_ok=True)

    run_rows, turn_rows, opening_rows = [], [], []
    aggregate: Dict[str, Counter] = _defaultdict(Counter)

    for run_id in range(1, runs + 1):
        rr, tr, oh, impact = simulate_game_v4(deck, strategy, cfg, policy, rng, run_id)
        run_rows.append(rr)
        turn_rows.extend(tr)
        opening_rows.append(oh)
        for name, metrics in impact.items():
            aggregate[name].update(metrics)

        if progress_callback and (run_id == 1 or run_id % max(1, runs // 100) == 0 or run_id == runs):
            progress_callback(run_id, runs)

    impact_rows = impact_rows_from_aggregate(deck, aggregate, runs, strategy)
    summary_data = summarize_v4(deck, run_rows, turn_rows, cfg, strategy, impact_rows)

    # Stable, simple names inside the result package.
    enriched_path = result_dir / "deck_enriched.csv"
    summary_path = result_dir / "summary.json"
    runs_path = result_dir / "runs.csv"
    turns_path = result_dir / "turns.csv"
    openings_path = result_dir / "opening_hands.csv"
    impact_path = result_dir / "card_impact.csv"
    config_path = result_dir / "simulation_config.json"
    value_path = result_dir / "value_model.json"
    ai_path = result_dir / "AI_ANALYSIS_INSTRUCTIONS.md"
    original_path = result_dir / deck_file.name

    write_enriched(enriched_path, deck)
    write_csv(runs_path, run_rows)
    write_csv(turns_path, turn_rows)
    write_csv(openings_path, opening_rows)
    write_csv(impact_path, impact_rows)
    summary_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_value_model(value_path, vm)
    _shutil.copy2(deck_file, original_path)

    config = {
        "version": V4_VERSION,
        "deck_file": deck_file.name,
        "commanders": list(commander_names),
        "runs": runs,
        "turns": turns,
        "seed": seed,
        "strategy_tags": sorted(strategy.archetypes),
        "opponent_profile": strategy.opponent_profile,
        "commander_priority": strategy.commander_priority,
        "x_min_roi": strategy.x_min_roi,
        "x_min_net_value": strategy.x_min_net_value,
        "strategy_file": str(strategy_file) if strategy_file else None,
        "metadata_csv": str(metadata_csv) if metadata_csv else None,
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    write_ai_analysis_instructions(ai_path, deck_file, summary_path.name, strategy)

    if strategy_file and Path(strategy_file).exists():
        _shutil.copy2(strategy_file, result_dir / Path(strategy_file).name)

    zip_path = result_dir.with_suffix(".zip")
    with _zipfile.ZipFile(zip_path, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
        for f in result_dir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(result_dir))

    return {
        "result_dir": result_dir,
        "zip_path": zip_path,
        "summary": summary_data,
        "deck": deck,
        "strategy": strategy,
        "impact_rows": impact_rows,
    }


def main_v4():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[],
                    help="Commander name. Repeat for Partner/background co-commanders.")
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="",
                    help="Comma-separated strategy tags, e.g. lifegain,tokens,aristocrats")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        try:
            from commander_goldfish_v4_gui import launch_gui
        except Exception as exc:
            print("Could not start GUI:", exc)
            print("Place commander_goldfish_v4_gui.py in the same folder as this file.")
            raise
        launch_gui()
        return

    commander_names = list(args.commander)
    if not commander_names:
        commander_names = detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit(
            "No commander detected. Use --commander \"Name\" or open the GUI with --gui."
        )

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v4(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )

    s = result["summary"]
    print("\nGoldfish v4 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])
    print("\nHeadline")
    print(f"  cards:             {s['deck']['cards']}")
    print(f"  lands:             {s['deck']['lands']}")
    print(f"  avg mulligans:     {s['opening']['avg_mulligans']:.3f}")
    print(f"  reach 111 life:    {s['outcomes']['reach_111_life_pct']:.1f}%")
    print(f"  Bilbo activation:  {s['outcomes']['bilbo_activation_pct']:.1f}%")
    print(f"  win by turn {args.turns}:   {s['outcomes']['win_by_turn_limit_pct']:.1f}%")
    if args.opponent != "goldfish":
        print(f"  abstract losses:   {s['outcomes']['loss_by_turn_limit_pct']:.1f}%")
    print("\nTop relative card highlights:")
    for h in s["relative_card_highlights"][:8]:
        print(f"  {h['tier']:>2}  {h['name']}: value/seen {h['value_per_seen']:.2f}")



# ---------------------------------------------------------------------------
# v4.0.1 extra X-patterns: "for each card exiled this way" and death-value tokens
# ---------------------------------------------------------------------------

_X_V4_ORIGINAL_EFFECT_METRICS = x_effect_metrics
_X_V4_ORIGINAL_RESOLVE = resolve_x_spell

def x_effect_metrics(card: Card, x: int, state: GameState, strategy: Strategy) -> Counter:
    m = _X_V4_ORIGINAL_EFFECT_METRICS(card, x, state, strategy)
    low = strip_reminder_text(card.oracle_text).lower()

    # Suffer-the-Past style templating: the result is proportional to the X cards
    # exiled even though Oracle text does not literally say "gain X life".
    if (
        "exile x target cards" in low
        and "for each card exiled this way" in low
        and "you gain 1 life" in low
    ):
        m["life_gain"] += x
        if "that player loses 1 life" in low:
            m["opponent_life_loss"] += x

    # Tokens carrying a death-trigger have future value. Do not count it at 100%:
    # in a goldfish there is no guarantee they die before the horizon.
    if "create twice x" in low and 'when this token dies, you gain 1 life' in low:
        m["life_gain"] += (2 * x) * 0.45

    return m


def resolve_x_spell(state: GameState, strategy: Strategy, card: Card, plan: XPlan):
    x = plan.x
    low = strip_reminder_text(card.oracle_text).lower()

    # Use the original concrete resolver first.
    _X_V4_ORIGINAL_RESOLVE(state, strategy, card, plan)

    # Concrete Suffer-the-Past style proportional result.
    if (
        "exile x target cards" in low
        and "for each card exiled this way" in low
        and "you gain 1 life" in low
    ):
        # The original resolver already reduced virtual graveyard / logged grave_hate,
        # but did not perform the proportional gain/loss because Oracle lacks literal X.
        gain_life(state, x, card.name)
        if "that player loses 1 life" in low:
            lose_target_opponent(state, x, card.name)



# ===========================================================================
# v4.1 SCENARIO / COMBO-SETUP EXTENSION
# ===========================================================================
#
# A scenario is a user-defined target STATE, not an attempt to infer a combo.
# Requirements are ANDed across cards/resources. For a single card, multiple
# allowed zones are ORed. This lets users define, for example:
#   - Bilbo must be on battlefield, untapped and ready;
#   - Doctor Strange may be in library OR already on battlefield;
#   - life >= 111;
#   - 5 mana available with W/B/G represented.
#
# Alternate preparations are modeled as separate scenarios rather than a hidden
# rule language. Example: scenario 2 may allow a combo piece in library OR
# graveyard and separately require Elixir of Immortality in hand/battlefield.
# ===========================================================================

V41_VERSION = "4.1"
SCENARIO_ZONES = ("library", "hand", "battlefield", "graveyard", "exile", "command_zone")
SCENARIO_KINDS = ("Setup", "Combo", "Win Condition")
SCENARIO_READY_MODES = ("ignore", "ready", "sick")

_V4_Strategy = Strategy
_V4_load_strategy = load_strategy
_V4_cast_score_v4 = cast_score_v4
_V4_available_options = _available_options
_V4_play_proactive_cards = _play_proactive_cards
_V4_write_ai_analysis_instructions = write_ai_analysis_instructions


def new_scenario(name: str = "New Scenario") -> dict:
    return {
        "id": (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "scenario") + f"-{time.time_ns() % 1000000000:09d}",
        "name": name,
        "kind": "Setup",
        "enabled": True,
        "steer": True,
        "description": "",
        "requirements": [],
        "mana": {"total": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0},
        "thresholds": {"life": 0, "lands": 0, "food": 0, "treasure": 0, "clues": 0},
        "derived": [],
    }


def normalize_scenario(raw: dict, index: int = 0) -> dict:
    s = new_scenario(str(raw.get("name") or f"Scenario {index+1}"))
    s.update({k: raw[k] for k in ("id", "name", "kind", "enabled", "steer", "description") if k in raw})
    if s["kind"] not in SCENARIO_KINDS:
        s["kind"] = "Setup"
    s["enabled"] = bool(s.get("enabled", True))
    s["steer"] = bool(s.get("steer", True))

    mana = dict(s["mana"])
    mana.update(raw.get("mana") or {})
    s["mana"] = {k: max(0, int(mana.get(k, 0) or 0)) for k in ("total", "W", "U", "B", "R", "G", "C")}

    thresholds = dict(s["thresholds"])
    thresholds.update(raw.get("thresholds") or {})
    s["thresholds"] = {k: max(0, int(thresholds.get(k, 0) or 0)) for k in ("life", "lands", "food", "treasure", "clues")}

    reqs = []
    for r in raw.get("requirements") or []:
        name = normalize_name(str(r.get("card") or r.get("name") or ""))
        if not name:
            continue
        zones = [z for z in (r.get("zones") or ["library"]) if z in SCENARIO_ZONES]
        if not zones:
            zones = ["library"]
        ready = str(r.get("ready") or "ignore").lower()
        if ready not in SCENARIO_READY_MODES:
            ready = "ignore"
        untapped = bool(r.get("untapped", False))
        # Readiness/untapped are battlefield-only concepts. Make this explicit
        # rather than silently accepting a library card as "ready".
        if ready != "ignore" or untapped:
            zones = ["battlefield"]
        reqs.append({
            "card": name,
            "count": max(1, int(r.get("count", 1) or 1)),
            "zones": zones,
            "ready": ready,
            "untapped": untapped,
        })
    s["requirements"] = reqs

    derived = []
    for d in raw.get("derived") or []:
        if not isinstance(d, dict) or not d.get("type"):
            continue
        derived.append({
            "type": str(d["type"]),
            "params": dict(d.get("params") or {}),
        })
    s["derived"] = derived
    return s






@dataclass
class ScenarioStrategy(_V4_Strategy):
    scenarios: List[dict] = field(default_factory=list)
    # Commander Posture (WP5): "auto" | "passive" | "balanced" | "aggressive".
    # See App/combat_model/posture.py for what each mode actually does.
    commander_posture: str = "auto"


def load_strategy_v41(path: Optional[Path], commander: Optional[Card], *,
                      archetypes: Optional[Set[str]] = None,
                      opponent_profile: Optional[str] = None,
                      value_model: Optional[ValueModel] = None,
                      scenarios: Optional[Sequence[dict]] = None) -> ScenarioStrategy:
    base = _V4_load_strategy(
        path, commander, archetypes=archetypes,
        opponent_profile=opponent_profile, value_model=value_model,
    )
    s = ScenarioStrategy(**base.__dict__, scenarios=[normalize_scenario(x, i) for i, x in enumerate(scenarios or [])])

    # User-defined scenario pieces that need to move to hand/battlefield become
    # high-priority tutor candidates. Library-only requirements are intentionally
    # NOT pulled out of the library.
    priority = []
    for sc in s.scenarios:
        if not sc.get("enabled", True) or not sc.get("steer", True):
            continue
        for req in sc.get("requirements", []):
            zones = set(req.get("zones", []))
            if zones & {"hand", "battlefield"}:
                priority.append(req["card"])
    if priority:
        seen = set()
        front = [x for x in priority if not (x in seen or seen.add(x))]
        s.tutor_priority = front + [x for x in s.tutor_priority if x not in seen]
        s.legendary_tutor_priority = front + [x for x in s.legendary_tutor_priority if x not in seen]
        s.enchantment_tutor_priority = front + [x for x in s.enchantment_tutor_priority if x not in seen]
    return s




def _zone_instances(state: GameState, card_name: str, zone: str, req: dict) -> int:
    if zone == "library":
        return sum(c.name == card_name for c in state.library)
    if zone == "hand":
        return sum(c.name == card_name for c in state.hand)
    if zone == "graveyard":
        return sum(c.name == card_name for c in state.graveyard)
    if zone == "exile":
        return sum(c.name == card_name for c in state.exile)
    if zone == "command_zone":
        return sum(c.name == card_name for c in state.command_zone)
    if zone == "battlefield":
        n = 0
        for p in state.battlefield:
            if p.card.name != card_name:
                continue
            ready_mode = req.get("ready", "ignore")
            if ready_mode == "ready" and not _perm_ready(p, state):
                continue
            if ready_mode == "sick" and _perm_ready(p, state):
                continue
            if req.get("untapped") and p.tapped:
                continue
            n += 1
        return n
    return 0


def scenario_card_requirement_met(state: GameState, req: dict) -> Tuple[bool, str]:
    needed = int(req.get("count", 1))
    found = 0
    details = []
    for zone in req.get("zones", []):
        n = _zone_instances(state, req["card"], zone, req)
        if n:
            details.append(f"{zone}:{n}")
        found += n
    ok = found >= needed
    if ok:
        return True, f"{req['card']} ({', '.join(details)})"
    ztxt = "/".join(req.get("zones", []))
    extra = ""
    if req.get("ready") == "ready":
        extra += ", ready"
    elif req.get("ready") == "sick":
        extra += ", summoning sick"
    if req.get("untapped"):
        extra += ", untapped"
    return False, f"{req['card']} x{needed} in {ztxt}{extra}"


def scenario_nonmana_status(state: GameState, scenario: dict) -> Tuple[bool, List[str]]:
    missing = []
    for req in scenario.get("requirements", []):
        ok, detail = scenario_card_requirement_met(state, req)
        if not ok:
            missing.append(detail)
    th = scenario.get("thresholds", {})
    if state.life < th.get("life", 0):
        missing.append(f"life {state.life:.0f}/{th.get('life', 0)}")
    if len(state.lands()) < th.get("lands", 0):
        missing.append(f"lands {len(state.lands())}/{th.get('lands', 0)}")
    if state.food < th.get("food", 0):
        missing.append(f"food {state.food}/{th.get('food', 0)}")
    if state.treasure < th.get("treasure", 0):
        missing.append(f"treasure {state.treasure}/{th.get('treasure', 0)}")
    if state.clues < th.get("clues", 0):
        missing.append(f"clues {state.clues}/{th.get('clues', 0)}")
    return not missing, missing


def scenario_mana_status(state: GameState, strategy: Strategy, scenario: dict) -> Tuple[bool, str]:
    m = scenario.get("mana", {})
    req = Counter({c: int(m.get(c, 0) or 0) for c in COLORS + (COLORLESS,) if int(m.get(c, 0) or 0) > 0})
    total = max(int(m.get("total", 0) or 0), sum(req.values()))
    if total <= 0:
        return True, ""
    plan = find_payment(state, strategy, total, req)
    if plan:
        return True, ""
    colored = " ".join(f"{c}:{req[c]}" for c in COLORS + (COLORLESS,) if req[c])
    return False, f"mana total {total}" + (f" ({colored})" if colored else "")


def scenario_derived_status(state: GameState, strategy: Strategy, scenario: dict) -> Tuple[bool, bool, List[str]]:
    """
    Evaluate the v4.4 'derived' block (dynamic/computed conditions), if present.
    Returns (satisfied, computable, missing_details). Absent/empty 'derived' is
    vacuously satisfied+computable so v4.3 scenario files behave identically.
    """
    derived = scenario.get("derived") or []
    if not derived:
        return True, True, []
    evaluation = scenario_predicates_registry.evaluate_all(
        sys.modules[__name__], derived, state, strategy,
    )
    missing = []
    for entry, result in zip(derived, evaluation.results):
        if result.satisfied:
            continue
        label = entry.get("type", "?")
        if not result.computable:
            missing.append(f"[nicht berechenbar] {label}: {result.detail}")
        else:
            missing.append(f"{label}: {result.detail}")
    return evaluation.satisfied, evaluation.computable, missing


def scenario_status(state: GameState, strategy: Strategy, scenario: dict) -> dict:
    nonmana_ok, missing = scenario_nonmana_status(state, scenario)
    mana_ok, mana_missing = scenario_mana_status(state, strategy, scenario)
    derived_ok, derived_computable, derived_missing = scenario_derived_status(state, strategy, scenario)
    all_missing = list(missing)
    if not mana_ok:
        all_missing.append(mana_missing)
    all_missing.extend(derived_missing)
    return {
        "cards_and_thresholds_met": nonmana_ok,
        "mana_met": mana_ok,
        "derived_met": derived_ok,
        "derived_computable": derived_computable,
        "reached": nonmana_ok and mana_ok and derived_ok,
        "missing": all_missing,
    }






def scenario_requires_board_card(state: GameState, strategy: ScenarioStrategy, card_name: str) -> bool:
    reached = getattr(state, "scenario_reached_names", set())
    for sc in strategy.scenarios:
        if not sc.get("enabled", True) or not sc.get("steer", True) or sc["id"] in reached:
            continue
        for req in sc.get("requirements", []):
            if req["card"] != card_name or "battlefield" not in req.get("zones", []):
                continue
            ok, _ = scenario_card_requirement_met(state, req)
            if not ok:
                return True
    return False






def scenario_cast_adjustment(opt: CastOption, state: GameState, strategy: ScenarioStrategy) -> float:
    card = opt.card
    if scenario_requires_hand_only(strategy, card.name):
        return -100.0
    bonus = 0.0
    if scenario_requires_board_card(state, strategy, card.name):
        bonus += 14.0
    if scenario_requires_graveyard_spell(strategy, card):
        bonus += 8.0

    # If a scenario has all non-mana conditions already satisfied, protect mana
    # instead of spending it on unrelated filler. Ramp/draw/tutors may still be
    # worth developing when mana is not yet reachable.
    reached = getattr(state, "scenario_reached_names", set())
    for sc in strategy.scenarios:
        if not sc.get("enabled", True) or not sc.get("steer", True) or sc["id"] in reached:
            continue
        nonmana_ok, _ = scenario_nonmana_status(state, sc)
        mana_ok, _ = scenario_mana_status(state, strategy, sc)
        if nonmana_ok and not mana_ok and not scenario_requires_board_card(state, strategy, card.name):
            if not (card.roles & {"ramp", "draw", "draw_engine", "tutor"}):
                bonus -= 6.0
    return bonus


def cast_score_v41(opt: CastOption, state: GameState, strategy: ScenarioStrategy) -> float:
    return _V4_cast_score_v4(opt, state, strategy) + scenario_cast_adjustment(opt, state, strategy)


def _available_options_v41(state: GameState, strategy: ScenarioStrategy) -> List[CastOption]:
    opts = []
    for c in state.hand:
        if c.is_land:
            continue
        if scenario_requires_hand_only(strategy, c.name):
            continue
        o = cast_option(c, state, strategy)
        if o:
            opts.append(o)
    return opts


def _play_proactive_cards_v41(state: GameState, strategy: ScenarioStrategy, min_score: float, limit: int = 20) -> List[str]:
    casts = []
    for _ in range(limit):
        opts = _available_options_v41(state, strategy)
        if not opts:
            break
        opts.sort(key=lambda o: cast_score_v41(o, state, strategy), reverse=True)
        o = opts[0]
        if cast_score_v41(o, state, strategy) < min_score:
            break
        if try_cast_option(state, strategy, o):
            casts.append(o.card.name + (f"(X={o.x_plan.x})" if o.x_plan else ""))
        else:
            break
    return casts


def _scenario_commander_bonus(state: GameState, strategy: ScenarioStrategy, commander_name: str) -> float:
    return 12.0 if scenario_requires_board_card(state, strategy, commander_name) else 0.0


def cast_one_commander_v41(state: GameState, strategy: ScenarioStrategy) -> Optional[str]:
    if not state.command_zone:
        return None
    options = []
    for commander in list(state.command_zone):
        tax_count = int(state.commander_cast_counts[commander.name])
        base = commander.min_cost + 2 * tax_count
        discount, attribution = effective_cost_discount(commander, state)
        total = max(sum(commander.color_requirements.values()), base - discount)
        payment = find_payment(state, strategy, total, commander.color_requirements)
        if payment:
            score = 5.0 - total * 0.1 + _scenario_commander_bonus(state, strategy, commander.name)
            if "lifegain_replacement" in commander.roles and "lifegain" in strategy.archetypes:
                score += 5
            options.append((score, commander, total, payment, attribution))
    if not options:
        return None
    _score, commander, total, payment, attribution = max(options, key=lambda x: x[0])
    apply_payment(state, payment, strategy)
    state.command_zone.remove(commander)
    state.commander_cast_counts[commander.name] += 1
    state.commander_casts += 1
    record_impact(state, commander.name, "cast", 1)
    record_impact(state, commander.name, "mana_spent", total)
    for source, amount in attribution.items():
        record_impact(state, source, "mana_discount", amount)
    permanent_enters(state, strategy, commander)
    record_impact(state, commander.name, "entered", 1)
    state.log(f"CAST COMMANDER {commander.name}")
    return commander.name




def simulate_game_v41(
    deck: List[Card],
    strategy_template: ScenarioStrategy,
    cfg: SimConfig,
    policy: MulliganPolicy,
    rng: random.Random,
    run_id: int,
):
    commanders = [c for c in deck if c.commander]
    library = deck[:]
    for commander in commanders:
        if commander in library:
            library.remove(commander)

    hand, rest, mulligans, mull_history = london_mulligan(library, policy, cfg, rng)
    rng.shuffle(rest)
    strategy = replace(strategy_template, scenarios=[normalize_scenario(x, i) for i, x in enumerate(strategy_template.scenarios)])
    if commanders and not strategy.commander_colors:
        strategy.commander_colors = set().union(*(c.color_identity for c in commanders))

    state = GameState(library=rest, hand=hand[:], command_zone=commanders[:], life=cfg.starting_life)
    state.scenario_reached_names = set()
    for c in hand:
        mark_seen(state, c)
    for c in commanders:
        mark_seen(state, c)

    opening_hand = [c.name for c in hand]
    turn_rows = []
    sc_progress = init_scenario_progress(strategy)
    state.turn = 0
    update_scenario_progress(state, strategy, sc_progress, "opening")

    for turn in range(1, cfg.turns + 1):
        state.turn = turn
        state.nontoken_creatures_entered_this_turn = 0
        state.gained_life_this_turn = False
        state.life_gained_this_turn_amount = 0.0
        state.baron_triggered_this_turn = False
        state.life_events_this_turn = 0
        state.well_caps_this_turn = []
        state.trudge_garden_triggers_this_turn = 0
        state.frying_pan_bonus_this_turn = 0.0
        state.event_log = []
        untap_step(state)
        update_scenario_progress(state, strategy, sc_progress, "untap")

        state.virtual_opponent_graveyard = max(state.virtual_opponent_graveyard, max(0, int(turn * 1.25 - 1)))
        draw_cards(state, 1, draw_step=True, reason="draw step")
        update_scenario_progress(state, strategy, sc_progress, "draw")
        start_hand = [c.name for c in state.hand]

        land = choose_land(state, strategy)
        land_name = ""
        if land:
            state.hand.remove(land)
            land_name = land.name
            land_enters(state, strategy, land)
        update_scenario_progress(state, strategy, sc_progress, "after land")

        structural_access_before = structural_color_access(state, strategy)
        mana_before = available_mana_value(state, strategy)
        casts = []

        casts.extend(_cast_early_ramp_before_commander(state, strategy))
        update_scenario_progress(state, strategy, sc_progress, "after early ramp")

        if strategy.commander_priority == "high" and turn >= 3:
            commander_name = cast_one_commander_v41(state, strategy)
            if commander_name:
                casts.append(f"Commander:{commander_name}")
            update_scenario_progress(state, strategy, sc_progress, "after commander")

        arken = next((c for c in state.hand if c.name == "The Arkenstone"), None)
        if arken and not scenario_requires_hand_only(strategy, arken.name) and try_cast_arkenstone_adventure(state, strategy, arken):
            record_impact(state, "The Arkenstone", "cast", 1)
            record_impact(state, "The Arkenstone", "mana_spent", 3)
            casts.append("Seek the Heart")

        casts.extend(_play_proactive_cards_v41(state, strategy, min_score=0.0, limit=20))
        if try_cast_adventure_permanent_from_exile(state, strategy):
            record_impact(state, "The Arkenstone", "cast", 1)
            record_impact(state, "The Arkenstone", "mana_spent", 5)
            casts.append("The Arkenstone(from exile)")

        if strategy.commander_priority != "high":
            commander_name = cast_one_commander_v41(state, strategy)
            if commander_name:
                casts.append(f"Commander:{commander_name}")
        update_scenario_progress(state, strategy, sc_progress, "end main 1")

        try_activate_bilbo(state, strategy)
        update_scenario_progress(state, strategy, sc_progress, "after special activation")
        attack_phase(state, strategy)
        update_scenario_progress(state, strategy, sc_progress, "after combat")

        casts.extend(_play_proactive_cards_v41(state, strategy, min_score=1.0, limit=10))
        try_activate_bilbo(state, strategy)
        update_scenario_progress(state, strategy, sc_progress, "end main 2")

        end_step(state, strategy)
        try_activate_bilbo(state, strategy)
        update_scenario_progress(state, strategy, sc_progress, "end step")

        for p in state.battlefield:
            if not p.card.is_land:
                record_impact(state, p.card.name, "board_turns", 1)

        apply_abstract_opponent_phase(state, strategy, rng)
        update_scenario_progress(state, strategy, sc_progress, "after opponent stress")

        reactive_held = hold_reactive_count(state, strategy)
        state.reactive_held_total += reactive_held
        remaining_access = color_access(state, strategy)
        structural_access_after = structural_color_access(state, strategy)
        reached_names = [p["scenario"]["name"] for p in sc_progress.values() if p["first_reached_turn"] is not None]

        turn_rows.append({
            "run": run_id,
            "turn": turn,
            "start_hand": " | ".join(start_hand),
            "land_played": land_name,
            "casts": " | ".join(casts),
            "events": " || ".join(state.event_log),
            "end_hand": " | ".join(c.name for c in state.hand),
            "hand_size": len(state.hand),
            "lands_in_play": len(state.lands()),
            "mana_available_start_main": mana_before,
            "available_mana_after_actions": available_mana_value(state, strategy),
            "structural_color_access_before_actions": "".join(c for c in COLORS if c in structural_access_before),
            "structural_color_access_after_actions": "".join(c for c in COLORS if c in structural_access_after),
            "remaining_untapped_color_access": "".join(c for c in COLORS if c in remaining_access),
            "has_all_commander_colors_structural": int(bool(strategy.commander_colors) and strategy.commander_colors <= structural_access_after),
            "life": round(state.life, 2),
            "damage_taken": round(state.damage_taken, 2),
            "opponent_life": " | ".join(str(round(x, 2)) for x in state.opponents),
            "virtual_opponent_graveyard": state.virtual_opponent_graveyard,
            "food": state.food,
            "treasure": state.treasure,
            "clues": state.clues,
            "reactive_cards_held": reactive_held,
            "life_events_this_turn": state.life_events_this_turn,
            "life_gained_this_turn": round(state.life_gained_this_turn_amount, 2),
            "scenarios_reached_so_far": " | ".join(reached_names),
            "bilbo_activated": int(state.bilbo_activation_turn == turn),
            "win": int(state.win_turn == turn),
            "loss": int(state.lost_turn == turn),
        })
        if state.win_turn is not None or state.lost_turn is not None:
            break

    run_row = {
        "run": run_id,
        "mulligans": mulligans,
        "opening_hand": " | ".join(opening_hand),
        "opening_land_count": sum(c.is_land for c in hand),
        "opening_cheap_spells": sum((not c.is_land) and c.min_cost <= 3 for c in hand),
        "opening_early_ramp": sum("ramp" in c.roles and c.min_cost <= 3 for c in hand),
        "lands_end": len(state.lands()),
        "hand_size_end": len(state.hand),
        "life_end": round(state.life, 2),
        "damage_taken": round(state.damage_taken, 2),
        "food_end": state.food,
        "treasure_end": state.treasure,
        "cards_drawn_total": state.cards_drawn_total,
        "scry_count": state.scry_count,
        "surveil_count": state.surveil_count,
        "connive_count": state.connive_count,
        "bilbo_activation_turn": state.bilbo_activation_turn or "",
        "win_turn": state.win_turn or "",
        "loss_turn": state.lost_turn or "",
        "opponents_remaining": sum(x > 0 for x in state.opponents),
        "life_50_turn": state.milestones[50] or "",
        "life_60_turn": state.milestones[60] or "",
        "life_80_turn": state.milestones[80] or "",
        "life_100_turn": state.milestones[100] or "",
        "life_111_turn": state.milestones[111] or "",
        "reactive_held_total_turn_snapshots": state.reactive_held_total,
    }
    opening_row = {"run": run_id, "mulligans": mulligans, "opening_hand": " | ".join(opening_hand), "mulligan_history": " || ".join(mull_history)}
    return run_row, turn_rows, opening_row, state.impact, scenario_run_rows(run_id, sc_progress, state)


def summarize_scenarios(scenario_rows: List[dict], scenarios: Sequence[dict], runs: int, turns: int) -> List[dict]:
    out = []
    for sc in scenarios:
        if not sc.get("enabled", True):
            continue
        rows = [r for r in scenario_rows if r["scenario_id"] == sc["id"]]
        reached_turns = [int(r["first_reached_turn"]) for r in rows if str(r["first_reached_turn"]).strip()]
        nonmana_turns = [int(r["first_cards_thresholds_turn"]) for r in rows if str(r["first_cards_thresholds_turn"]).strip()]
        fail_reasons = Counter()
        for r in rows:
            if r["reached"]:
                continue
            for reason in str(r["final_missing"]).split(" | "):
                if reason:
                    # Normalize changing numeric progress such as "life 82/111".
                    key = re.sub(r"\d+(?:\.\d+)?/\d+", "current/target", reason)
                    fail_reasons[key] += 1
        cumulative = {}
        for t in range(0, turns + 1):
            cumulative[str(t)] = round(100 * sum(x <= t for x in reached_turns) / max(1, runs), 3)
        out.append({
            "id": sc["id"],
            "name": sc["name"],
            "kind": sc["kind"],
            "steer": bool(sc.get("steer", True)),
            "reach_pct": round(100 * len(reached_turns) / max(1, runs), 3),
            "median_reached_turn": percentile([float(x) for x in reached_turns], .5) if reached_turns else None,
            "p25_reached_turn": percentile([float(x) for x in reached_turns], .25) if reached_turns else None,
            "p75_reached_turn": percentile([float(x) for x in reached_turns], .75) if reached_turns else None,
            "cards_thresholds_reached_pct": round(100 * len(nonmana_turns) / max(1, runs), 3),
            "cumulative_reach_by_turn_pct": cumulative,
            "top_final_bottlenecks": fail_reasons.most_common(8),
        })
    return out


def summarize_v41(deck: List[Card], run_rows: List[dict], turn_rows: List[dict], cfg: SimConfig,
                   strategy: ScenarioStrategy, impact_rows: List[dict], scenario_rows: List[dict]) -> dict:
    base = summarize_v4(deck, run_rows, turn_rows, cfg, strategy, impact_rows)
    base["version"] = V41_VERSION
    base["simulation"]["scenario_count"] = len([s for s in strategy.scenarios if s.get("enabled", True)])
    base["scenarios"] = summarize_scenarios(scenario_rows, strategy.scenarios, cfg.runs, cfg.turns)
    base["limitations"].insert(0,
        "Scenario reach means the user-defined state was observed. It does NOT prove the combo actually resolves, is deterministic, or wins through interaction."
    )
    base["limitations"].insert(1,
        "Scenario steering only prioritizes explicit setup pieces and preserves obvious resources; it is not a general combo planner."
    )
    return base


def write_ai_analysis_instructions_v41(path: Path, deck_file: Path, summary_file: str, strategy: ScenarioStrategy):
    _V4_write_ai_analysis_instructions(path, deck_file, summary_file, strategy)
    extra = """

## User-defined Combo / Win-Condition Scenarios (v4.1)
The package may contain `combo_scenarios.json` and `scenario_runs.csv`.

A scenario is an explicitly user-authored TARGET STATE. Requirements across cards/resources
are AND conditions; multiple allowed zones on one card are OR conditions. Examples include:
"Bilbo is on battlefield, untapped and no longer summoning sick; Doctor Strange is in
library or battlefield; life >= 111; 5 mana including W/B/G is available."

Interpret scenario data as **setup accessibility**, not as proof that a combo resolves.
The simulator does not infer missing combo steps, priority, opposing responses, hidden
replacement interactions or deterministic lethality unless separately modeled.

For each scenario analyze:
1. reach percentage within the simulated horizon;
2. median / quartile first-reach turn;
3. cumulative reach by turn;
4. whether cards/thresholds or mana are the main bottleneck;
5. common final missing requirements;
6. whether the scenario definition itself is too strict or too permissive.

If the user has not supplied scenarios but asks about combo consistency, ask them to define
the desired setup state (required cards, allowed zones, readiness/untapped state, mana and
resource thresholds) rather than inventing a combo line.
"""
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(extra)


def run_pipeline_v41(
    deck_file: Path,
    commander_names: Sequence[str],
    *,
    runs: int = 5000,
    turns: int = 10,
    seed: int = 1,
    strategy_file: Optional[Path] = None,
    strategy_tags: Optional[Set[str]] = None,
    opponent_profile: str = "goldfish",
    value_model_file: Optional[Path] = None,
    scenarios: Optional[Sequence[dict]] = None,
    scenarios_file: Optional[Path] = None,
    cache_path: Optional[Path] = None,
    offline: bool = False,
    metadata_csv: Optional[Path] = None,
    output_root: Optional[Path] = None,
    progress_callback=None,
):
    deck_file = Path(deck_file)
    vm = ValueModel.load(value_model_file)
    cache_path = cache_path or (Path(__file__).resolve().parent / ".scryfall_card_cache_v4.json")
    deck = build_deck_v4(deck_file, commander_names, cache_path, offline, metadata_csv)
    commander = next((c for c in deck if c.commander), None)

    scenario_list = []
    if scenarios_file:
        scenario_list.extend(load_scenarios(scenarios_file))
    if scenarios:
        scenario_list.extend(normalize_scenario(x, i + len(scenario_list)) for i, x in enumerate(scenarios))
    # Dedupe by id, last definition wins.
    scenario_list = list({s["id"]: s for s in scenario_list}.values())

    strategy = load_strategy_v41(
        strategy_file, commander, archetypes=strategy_tags,
        opponent_profile=opponent_profile, value_model=vm,
        scenarios=scenario_list,
    )
    if commander_names:
        strategy.commander_colors = set().union(*(c.color_identity for c in deck if c.commander))

    cfg = SimConfig(runs=runs, turns=turns, seed=seed)
    policy = MulliganPolicy()
    rng = random.Random(seed)

    timestamp = _datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(output_root or (deck_file.parent / "Goldfish_Results"))
    result_dir = root / f"{deck_file.stem}_v4_1_{timestamp}"
    result_dir.mkdir(parents=True, exist_ok=True)

    run_rows, turn_rows, opening_rows, scenario_rows = [], [], [], []
    aggregate: Dict[str, Counter] = _defaultdict(Counter)
    for run_id in range(1, runs + 1):
        rr, tr, oh, impact, sr = simulate_game_v41(deck, strategy, cfg, policy, rng, run_id)
        run_rows.append(rr); turn_rows.extend(tr); opening_rows.append(oh); scenario_rows.extend(sr)
        for name, metrics in impact.items():
            aggregate[name].update(metrics)
        if progress_callback and (run_id == 1 or run_id % max(1, runs // 100) == 0 or run_id == runs):
            progress_callback(run_id, runs)

    impact_rows = impact_rows_from_aggregate(deck, aggregate, runs, strategy)
    summary_data = summarize_v41(deck, run_rows, turn_rows, cfg, strategy, impact_rows, scenario_rows)

    enriched_path = result_dir / "deck_enriched.csv"
    summary_path = result_dir / "summary.json"
    runs_path = result_dir / "runs.csv"
    turns_path = result_dir / "turns.csv"
    openings_path = result_dir / "opening_hands.csv"
    impact_path = result_dir / "card_impact.csv"
    scenario_path = result_dir / "scenario_runs.csv"
    scenario_json = result_dir / "combo_scenarios.json"
    config_path = result_dir / "simulation_config.json"
    value_path = result_dir / "value_model.json"
    ai_path = result_dir / "AI_ANALYSIS_INSTRUCTIONS.md"
    original_path = result_dir / deck_file.name

    write_enriched(enriched_path, deck)
    write_csv(runs_path, run_rows); write_csv(turns_path, turn_rows); write_csv(openings_path, opening_rows)
    write_csv(impact_path, impact_rows); write_csv(scenario_path, scenario_rows)
    summary_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_value_model(value_path, vm)
    save_scenarios(scenario_json, strategy.scenarios)
    _shutil.copy2(deck_file, original_path)

    config = {
        "version": V41_VERSION,
        "deck_file": deck_file.name,
        "commanders": list(commander_names),
        "runs": runs, "turns": turns, "seed": seed,
        "strategy_tags": sorted(strategy.archetypes),
        "opponent_profile": strategy.opponent_profile,
        "commander_priority": strategy.commander_priority,
        "scenario_count": len(strategy.scenarios),
        "scenario_names": [s["name"] for s in strategy.scenarios if s.get("enabled", True)],
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    write_ai_analysis_instructions_v41(ai_path, deck_file, summary_path.name, strategy)
    if strategy_file and Path(strategy_file).exists():
        _shutil.copy2(strategy_file, result_dir / Path(strategy_file).name)

    zip_path = result_dir.with_suffix(".zip")
    with _zipfile.ZipFile(zip_path, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
        for f in result_dir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(result_dir))

    return {"result_dir": result_dir, "zip_path": zip_path, "summary": summary_data,
            "deck": deck, "strategy": strategy, "impact_rows": impact_rows,
            "scenario_rows": scenario_rows}


def main_v41():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.1 — user-defined combo/setup scenarios")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None,
                    help="Scenario JSON created by the GUI or manually.")
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_1_gui import launch_gui
        launch_gui(); return

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")
    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v41(
        args.deck_file, commander_names,
        runs=args.runs, turns=args.turns, seed=args.seed,
        strategy_file=args.strategy, strategy_tags=tags or None,
        opponent_profile=args.opponent, value_model_file=args.value_model,
        scenarios_file=args.scenarios, cache_path=args.cache, offline=args.offline,
        metadata_csv=args.metadata_csv, output_root=args.output_root,
    )
    s = result["summary"]
    print("\nGoldfish v4.1 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])
    if s.get("scenarios"):
        print("\nScenario reach:")
        for sc in s["scenarios"]:
            print(f"  {sc['name']}: {sc['reach_pct']:.1f}% | median turn {sc['median_reached_turn']}")




# ===========================================================================
# v4.2 CARD PACKAGE / N-OF-M SCENARIO EXTENSION
# ===========================================================================
#
# Scenario logic:
#   * single requirements are ANDed;
#   * allowed zones inside one requirement are ORed;
#   * every card package is another ANDed requirement;
#   * inside a package, at least N of M distinct member cards must satisfy the
#     package condition.
#
# Example:
#   Bilbo on battlefield AND
#   at least 3 of 8 "ETB/drain pile" cards in Library OR Battlefield AND
#   life >= 111 AND
#   5 mana including W/B/G.
#
# Packages are deliberately state definitions, not a hidden combo scripting
# language. Alternative preparation lines remain separate scenarios.
# ===========================================================================

V42_VERSION = "4.2"

_V41_new_scenario = new_scenario
_V41_normalize_scenario = normalize_scenario
_V41_load_strategy_v41 = load_strategy_v41
_V41_scenario_nonmana_status = scenario_nonmana_status
_V41_scenario_requires_board_card = scenario_requires_board_card
_V41_scenario_cast_adjustment = scenario_cast_adjustment
_V41_write_ai_analysis_instructions_v41 = write_ai_analysis_instructions_v41


def new_card_package(name: str = "Card Package") -> dict:
    return {
        "id": (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "package")
              + f"-{time.time_ns() % 1000000000:09d}",
        "name": name,
        "enabled": True,
        "min_required": 1,
        "zones": ["library"],
        "ready": "ignore",
        "untapped": False,
        "count_per_card": 1,
        "members": [],
        "description": "",
    }


def normalize_card_package(raw: dict, index: int = 0) -> dict:
    p = new_card_package(str(raw.get("name") or f"Package {index+1}"))
    for key in ("id", "name", "enabled", "description"):
        if key in raw:
            p[key] = raw[key]
    p["enabled"] = bool(p.get("enabled", True))

    zones = [z for z in (raw.get("zones") or ["library"]) if z in SCENARIO_ZONES]
    if not zones:
        zones = ["library"]

    ready = str(raw.get("ready") or "ignore").lower()
    if ready not in SCENARIO_READY_MODES:
        ready = "ignore"
    untapped = bool(raw.get("untapped", False))
    if ready != "ignore" or untapped:
        zones = ["battlefield"]

    p["zones"] = zones
    p["ready"] = ready
    p["untapped"] = untapped
    p["count_per_card"] = max(1, int(raw.get("count_per_card", 1) or 1))

    members = []
    seen = set()
    for item in raw.get("members") or raw.get("cards") or []:
        if isinstance(item, str):
            member = {"card": normalize_name(item)}
        elif isinstance(item, dict):
            member = dict(item)
            member["card"] = normalize_name(str(member.get("card") or member.get("name") or ""))
        else:
            continue
        name = member.get("card", "")
        if not name or name in seen:
            continue
        seen.add(name)

        # Optional per-member overrides make the JSON expressive enough for AI-
        # authored scenarios while the GUI can stay simple with package defaults.
        mzones = member.get("zones")
        if mzones is not None:
            mzones = [z for z in mzones if z in SCENARIO_ZONES] or list(p["zones"])
        mready = str(member.get("ready", p["ready"])).lower()
        if mready not in SCENARIO_READY_MODES:
            mready = p["ready"]
        muntapped = bool(member.get("untapped", p["untapped"]))
        if mready != "ignore" or muntapped:
            mzones = ["battlefield"]

        clean = {"card": name}
        if mzones is not None:
            clean["zones"] = mzones
        if "ready" in member:
            clean["ready"] = mready
        if "untapped" in member:
            clean["untapped"] = muntapped
        if "count" in member:
            clean["count"] = max(1, int(member.get("count", p["count_per_card"]) or 1))
        members.append(clean)

    p["members"] = members
    max_members = max(1, len(members))
    p["min_required"] = min(
        max_members,
        max(1, int(raw.get("min_required", 1) or 1))
    )
    return p


def new_scenario(name: str = "New Scenario") -> dict:
    s = _V41_new_scenario(name)
    s["packages"] = []
    return s


def normalize_scenario(raw: dict, index: int = 0) -> dict:
    s = _V41_normalize_scenario(raw, index)
    packages = []
    for i, p in enumerate(raw.get("packages") or raw.get("card_packages") or []):
        packages.append(normalize_card_package(p, i))
    s["packages"] = packages
    return s


def load_scenarios(path: Optional[Path]) -> List[dict]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("scenarios", [])
    if not isinstance(data, list):
        raise ValueError("Scenario JSON must be a list or an object containing a 'scenarios' list.")
    return [normalize_scenario(x, i) for i, x in enumerate(data)]


def save_scenarios(path: Path, scenarios: Sequence[dict]):
    payload = {
        "version": V42_VERSION,
        "semantics": {
            "scenario": "AND across single requirements, packages, thresholds and mana",
            "single_requirement_zones": "OR",
            "package": "N-of-M distinct member cards",
            "package_member_default_condition": "package zones/readiness/untapped/count_per_card",
        },
        "scenarios": [normalize_scenario(x, i) for i, x in enumerate(scenarios)],
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def package_member_requirement(package: dict, member: dict) -> dict:
    ready = str(member.get("ready", package.get("ready", "ignore"))).lower()
    untapped = bool(member.get("untapped", package.get("untapped", False)))
    zones = member.get("zones", package.get("zones", ["library"]))
    zones = [z for z in zones if z in SCENARIO_ZONES] or ["library"]
    if ready != "ignore" or untapped:
        zones = ["battlefield"]
    return {
        "card": member["card"],
        "count": max(1, int(member.get("count", package.get("count_per_card", 1)) or 1)),
        "zones": zones,
        "ready": ready if ready in SCENARIO_READY_MODES else "ignore",
        "untapped": untapped,
    }


def scenario_package_status(state: GameState, package: dict) -> dict:
    package = normalize_card_package(package)
    if not package.get("enabled", True):
        return {
            "met": True, "matched": 0, "needed": 0, "total": len(package.get("members", [])),
            "matched_cards": [], "missing_cards": [], "detail": "disabled"
        }

    matched_cards = []
    missing_cards = []
    member_details = []
    for member in package.get("members", []):
        req = package_member_requirement(package, member)
        ok, detail = scenario_card_requirement_met(state, req)
        member_details.append({"card": member["card"], "met": ok, "detail": detail})
        if ok:
            matched_cards.append(member["card"])
        else:
            missing_cards.append(member["card"])

    needed = min(max(1, int(package.get("min_required", 1))), max(1, len(package.get("members", []))))
    matched = len(matched_cards)
    met = matched >= needed
    detail = (
        f'package "{package["name"]}" {matched}/{needed} matched '
        f'(pool {len(package.get("members", []))})'
    )
    return {
        "met": met,
        "matched": matched,
        "needed": needed,
        "total": len(package.get("members", [])),
        "matched_cards": matched_cards,
        "missing_cards": missing_cards,
        "member_details": member_details,
        "detail": detail,
    }


def scenario_nonmana_status(state: GameState, scenario: dict) -> Tuple[bool, List[str]]:
    missing = []

    # Required single cards: AND.
    for req in scenario.get("requirements", []):
        ok, detail = scenario_card_requirement_met(state, req)
        if not ok:
            missing.append(detail)

    # Packages: AND across packages, N-of-M within each package.
    for package in scenario.get("packages", []):
        ps = scenario_package_status(state, package)
        if not ps["met"]:
            examples = ", ".join(ps["missing_cards"][:4])
            more = max(0, len(ps["missing_cards"]) - 4)
            missing.append(
                f'{ps["detail"]}'
                + (f"; candidates not matching: {examples}" if examples else "")
                + (f" (+{more} more)" if more else "")
            )

    th = scenario.get("thresholds", {})
    if state.life < th.get("life", 0):
        missing.append(f"life {state.life:.0f}/{th.get('life', 0)}")
    if len(state.lands()) < th.get("lands", 0):
        missing.append(f"lands {len(state.lands())}/{th.get('lands', 0)}")
    if state.food < th.get("food", 0):
        missing.append(f"food {state.food}/{th.get('food', 0)}")
    if state.treasure < th.get("treasure", 0):
        missing.append(f"treasure {state.treasure}/{th.get('treasure', 0)}")
    if state.clues < th.get("clues", 0):
        missing.append(f"clues {state.clues}/{th.get('clues', 0)}")
    return not missing, missing


def _package_unmet_for_card(state: GameState, scenario: dict, card_name: str,
                            destination: str) -> bool:
    for package in scenario.get("packages", []):
        if not package.get("enabled", True):
            continue
        members = {m["card"] for m in package.get("members", [])}
        if card_name not in members:
            continue
        ps = scenario_package_status(state, package)
        if ps["met"]:
            continue
        member = next(m for m in package["members"] if m["card"] == card_name)
        req = package_member_requirement(package, member)
        if destination not in set(req.get("zones", [])):
            continue
        ok, _ = scenario_card_requirement_met(state, req)
        if not ok:
            return True
    return False








def load_strategy_v41(path: Optional[Path], commander: Optional[Card], *,
                      archetypes: Optional[Set[str]] = None,
                      opponent_profile: Optional[str] = None,
                      value_model: Optional[ValueModel] = None,
                      scenarios: Optional[Sequence[dict]] = None) -> ScenarioStrategy:
    # Start with v4.1 behavior for mandatory single-card requirements.
    s = _V41_load_strategy_v41(
        path, commander, archetypes=archetypes,
        opponent_profile=opponent_profile, value_model=value_model,
        scenarios=scenarios,
    )
    s.scenarios = [normalize_scenario(x, i) for i, x in enumerate(s.scenarios)]

    # Add redundant package members to tutor priority only when the package allows
    # the target to end in hand or battlefield. They are deliberately below
    # mandatory single-card requirements.
    package_priority = []
    for sc in s.scenarios:
        if not sc.get("enabled", True) or not sc.get("steer", True):
            continue
        for package in sc.get("packages", []):
            if not package.get("enabled", True):
                continue
            for member in package.get("members", []):
                req = package_member_requirement(package, member)
                if set(req.get("zones", [])) & {"hand", "battlefield"}:
                    package_priority.append(member["card"])

    if package_priority:
        seen = set()
        pp = [x for x in package_priority if not (x in seen or seen.add(x))]
        # Keep current mandatory priorities in front; insert package members before
        # the untouched generic tail where possible.
        for attr in ("tutor_priority", "legendary_tutor_priority", "enchantment_tutor_priority"):
            current = list(getattr(s, attr))
            current_set = set(current)
            merged = current[:]
            for name in pp:
                if name not in current_set:
                    merged.insert(min(len(merged), 6), name)
                    current_set.add(name)
            setattr(s, attr, merged)
    return s


def scenario_json_schema_markdown() -> str:
    return r"""# Combo / Win Condition Scenario Schema — v4.4

A scenario describes a **target game state**. It does not describe how a combo resolves.

## Boolean semantics

- Scenario = **AND** of:
  - every `requirements[]` single-card condition,
  - every enabled `packages[]` condition,
  - resource `thresholds`,
  - `mana`,
  - every `derived[]` predicate (v4.4+, see below).
- A single card's `zones` are **OR**.
- A package is **N-of-M**: at least `min_required` distinct member cards must satisfy
  the package condition.
- Different packages are ANDed.
- The same physical card may satisfy conditions in more than one package. Packages
  are logical observations, not resource reservations.

## Minimal example

```json
{
  "version": "4.4",
  "scenarios": [
    {
      "name": "Example setup",
      "kind": "Win Condition",
      "enabled": true,
      "steer": true,
      "requirements": [
        {
          "card": "Commander Name",
          "count": 1,
          "zones": ["battlefield"],
          "ready": "ready",
          "untapped": true
        }
      ],
      "packages": [
        {
          "name": "Redundant ETB enablers",
          "min_required": 1,
          "zones": ["hand", "battlefield"],
          "ready": "ignore",
          "untapped": false,
          "count_per_card": 1,
          "members": [
            {"card": "Card A"},
            {"card": "Card B"},
            {"card": "Card C"}
          ]
        }
      ],
      "mana": {"total": 5, "W": 1, "U": 0, "B": 1, "R": 0, "G": 1, "C": 0},
      "thresholds": {"life": 111, "lands": 0, "food": 0, "treasure": 0, "clues": 0},
      "derived": [
        {"type": "opponent_life_at_or_below", "params": {"threshold": 5, "target": "any"}}
      ]
    }
  ]
}
```

## Zones

`library`, `hand`, `battlefield`, `graveyard`, `exile`, `command_zone`

## Readiness

`ignore`, `ready`, `sick`

Readiness and `untapped` are battlefield-only. If either is requested, the engine
normalizes the condition to `battlefield`.

## Package member overrides

The GUI uses one shared condition for the whole package. JSON authored by a human or
AI may optionally override a member:

```json
{
  "card": "Card B",
  "zones": ["graveyard", "battlefield"],
  "ready": "ignore",
  "untapped": false,
  "count": 1
}
```

If omitted, package defaults apply.

## Derived conditions (`derived[]`, v4.4+)

`requirements`/`packages`/`thresholds`/`mana` all describe STATIC facts about cards
and resources. `derived[]` is for conditions that need actual game-state COMPUTATION
to answer — "is this X spell lethal right now", "would 21 commander damage connect" —
rather than "is this card on the battlefield". Each entry is
`{"type": "<predicate id>", "params": {...}}`; all entries in the list are ANDed with
each other and with everything else in the scenario. Implemented predicate types
(`App/scenario_predicates/definitions.json` is the authoritative, versioned list):

- `resource_available` — `{"resource": "mana|untapped_creatures|untapped_artifacts|food|treasure|clues", "min_count": int}`.
- `opponent_life_at_or_below` — `{"threshold": float, "target": "any|each|<int index>"}`.
- `x_spell_lethal` — `{"card": "<name in hand>", "copy_multiplier": int (default 1), "target": "any|each|<int index>"}`:
  smallest affordable X of a named X-spell such that its damage output reaches the
  target's remaining life. Simplification: total available mana as the X budget, not
  a full colored-mana payment solve.
- `commander_damage_lethal` — `{"commander": "<name>", "target": "any|each|<int index>"}`:
  an OPPORTUNITY check ("would be lethal if unblocked"), not a guarantee — whether it
  actually connects is decided by the probabilistic combat-interaction step at
  simulation time, not by this predicate.

Every predicate returns a three-way result, never a bare bool: `satisfied` (the
normal answer), `computable` (False for a declared-but-not-yet-implemented predicate
type, or one whose named card/target can't be resolved in this state — surfaced
distinctly, never silently scored as "not satisfied"), and an optional `progress`
(v4.15.6+): a 0..1 "how close" score the handler computes when it can do so cheaply
from data it already has (e.g. current life vs. threshold). `scenario_feasibility`
averages this across a scenario's derived predicates to steer play toward a CLOSER
unsatisfied state, not just reward the binary flip to `satisfied=True` — a predicate
with no `progress` signal falls back to the old binary 1.0/0.0 reading, so this is
purely additive. This progress score is for search/AI STEERING only; whether a
scenario counts as "reached" is still the plain boolean `satisfied`.

## Guidance for an AI authoring scenarios

1. Ask what state represents "ready to execute", not how to play every priority step.
2. Use mandatory `requirements` for irreplaceable pieces.
3. Use `packages` for redundancy: "any 1 of these tutors", "at least 2 of these engines",
   "3 of these creatures still in library/battlefield".
4. Use multiple scenarios for alternative preparation routes rather than inventing a
   procedural mini-language.
5. Use `derived[]` for conditions that depend on computing something at simulation
   time (an X-spell's lethality, whether commander damage would close a game) rather
   than trying to hand-encode them as static card/zone facts.
6. Do not claim scenario reach proves a deterministic win through interaction.
"""


def write_ai_analysis_instructions_v41(
    path: Path,
    deck_file: Path,
    summary_file: str,
    strategy: ScenarioStrategy,
):
    _V41_write_ai_analysis_instructions_v41(path, deck_file, summary_file, strategy)
    extra = r"""

## v4.2 — Card Packages / redundancy groups

`combo_scenarios.json` may contain `packages`.

Boolean semantics:
- mandatory single cards are AND requirements;
- zones within one card are OR;
- packages are AND requirements at scenario level;
- a package itself is N-of-M: at least `min_required` distinct package members must
  satisfy that package's zone/readiness condition.

Example: "1 of 5 ETB enablers in hand/battlefield" is one package, not five mandatory
cards.

When analyzing `scenario_runs.csv`, treat an unmet package as a redundancy bottleneck:
ask whether the deck has enough interchangeable cards, enough tutors/draw, or an
overly strict package definition.

A package is an observation, not a resource reservation. If the same card appears in
two packages it may logically satisfy both. If exclusivity matters, define separate
scenarios or explain that limitation.
"""
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(extra)


def run_pipeline_v42(
    deck_file: Path,
    commander_names: Sequence[str],
    *,
    runs: int = 5000,
    turns: int = 10,
    seed: int = 1,
    strategy_file: Optional[Path] = None,
    strategy_tags: Optional[Set[str]] = None,
    opponent_profile: str = "goldfish",
    value_model_file: Optional[Path] = None,
    scenarios: Optional[Sequence[dict]] = None,
    scenarios_file: Optional[Path] = None,
    cache_path: Optional[Path] = None,
    offline: bool = False,
    metadata_csv: Optional[Path] = None,
    output_root: Optional[Path] = None,
    progress_callback=None,
):
    deck_file = Path(deck_file)
    vm = ValueModel.load(value_model_file)
    cache_path = cache_path or (Path(__file__).resolve().parent / ".scryfall_card_cache_v4.json")
    deck = build_deck_v4(deck_file, commander_names, cache_path, offline, metadata_csv)
    commander = next((c for c in deck if c.commander), None)

    scenario_list = []
    if scenarios_file:
        scenario_list.extend(load_scenarios(scenarios_file))
    if scenarios:
        scenario_list.extend(normalize_scenario(x, i + len(scenario_list)) for i, x in enumerate(scenarios))
    scenario_list = list({s["id"]: s for s in scenario_list}.values())

    strategy = load_strategy_v41(
        strategy_file, commander, archetypes=strategy_tags,
        opponent_profile=opponent_profile, value_model=vm,
        scenarios=scenario_list,
    )
    if commander_names:
        strategy.commander_colors = set().union(*(c.color_identity for c in deck if c.commander))

    cfg = SimConfig(runs=runs, turns=turns, seed=seed)
    policy = MulliganPolicy()
    rng = random.Random(seed)

    timestamp = _datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(output_root or (deck_file.parent / "Goldfish_Results"))
    result_dir = root / f"{deck_file.stem}_v4_3_2_{timestamp}"
    result_dir.mkdir(parents=True, exist_ok=True)

    run_rows, turn_rows, opening_rows, scenario_rows = [], [], [], []
    aggregate: Dict[str, Counter] = _defaultdict(Counter)
    for run_id in range(1, runs + 1):
        rr, tr, oh, impact, sr = simulate_game_v41(deck, strategy, cfg, policy, rng, run_id)
        run_rows.append(rr)
        turn_rows.extend(tr)
        opening_rows.append(oh)
        scenario_rows.extend(sr)
        for name, metrics in impact.items():
            aggregate[name].update(metrics)
        if progress_callback and (run_id == 1 or run_id % max(1, runs // 100) == 0 or run_id == runs):
            progress_callback(run_id, runs)

    impact_rows = impact_rows_from_aggregate(deck, aggregate, runs, strategy)
    summary_data = summarize_v41(deck, run_rows, turn_rows, cfg, strategy, impact_rows, scenario_rows)
    summary_data["version"] = V43_VERSION
    summary_data["simulation"]["package_count"] = sum(
        len([p for p in s.get("packages", []) if p.get("enabled", True)])
        for s in strategy.scenarios if s.get("enabled", True)
    )

    enriched_path = result_dir / "deck_enriched.csv"
    summary_path = result_dir / "summary.json"
    runs_path = result_dir / "runs.csv"
    turns_path = result_dir / "turns.csv"
    openings_path = result_dir / "opening_hands.csv"
    impact_path = result_dir / "card_impact.csv"
    scenario_path = result_dir / "scenario_runs.csv"
    scenario_json = result_dir / "combo_scenarios.json"
    schema_path = result_dir / "SCENARIO_SCHEMA_v4_2.md"
    config_path = result_dir / "simulation_config.json"
    value_path = result_dir / "value_model.json"
    ai_path = result_dir / "AI_ANALYSIS_INSTRUCTIONS.md"
    original_path = result_dir / deck_file.name

    write_enriched(enriched_path, deck)
    write_csv(runs_path, run_rows)
    write_csv(turns_path, turn_rows)
    write_csv(openings_path, opening_rows)
    write_csv(impact_path, impact_rows)
    write_csv(scenario_path, scenario_rows)
    summary_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_value_model(value_path, vm)
    save_scenarios(scenario_json, strategy.scenarios)
    schema_path.write_text(scenario_json_schema_markdown(), encoding="utf-8")
    _shutil.copy2(deck_file, original_path)

    config = {
        "version": V43_VERSION,
        "deck_file": deck_file.name,
        "commanders": list(commander_names),
        "runs": runs,
        "turns": turns,
        "seed": seed,
        "strategy_tags": sorted(strategy.archetypes),
        "opponent_profile": strategy.opponent_profile,
        "commander_priority": strategy.commander_priority,
        "scenario_count": len(strategy.scenarios),
        "package_count": summary_data["simulation"]["package_count"],
        "scenario_names": [s["name"] for s in strategy.scenarios if s.get("enabled", True)],
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    write_ai_analysis_instructions_v41(ai_path, deck_file, summary_path.name, strategy)
    if strategy_file and Path(strategy_file).exists():
        _shutil.copy2(strategy_file, result_dir / Path(strategy_file).name)

    zip_path = result_dir.with_suffix(".zip")
    with _zipfile.ZipFile(zip_path, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
        for f in result_dir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(result_dir))

    return {
        "result_dir": result_dir,
        "zip_path": zip_path,
        "summary": summary_data,
        "deck": deck,
        "strategy": strategy,
        "impact_rows": impact_rows,
        "scenario_rows": scenario_rows,
    }


def main_v42():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.2 — N-of-M card packages")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None,
                    help="v4.2 Scenario JSON; supports N-of-M card packages.")
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_2_gui import launch_gui
        launch_gui()
        return

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v42(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    s = result["summary"]
    print("\nGoldfish v4.2 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])
    if s.get("scenarios"):
        print("\nScenario reach:")
        for sc in s["scenarios"]:
            print(f"  {sc['name']}: {sc['reach_pct']:.1f}% | median turn {sc['median_reached_turn']}")




# ===========================================================================
# v4.3 SINGLE-WINDOW GUI / PORTABLE PROJECT SUPPORT
# ===========================================================================

V43_VERSION = "4.3.2"
PROJECT_KIND_V43 = "commander_goldfish_project"


def project_payload_v43(
    deck_file: Path,
    *,
    commanders: Sequence[str],
    runs: int,
    turns: int,
    seed: int,
    strategy_tags: Sequence[str],
    opponent_profile: str,
    scenarios: Sequence[dict],
    strategy_file: Optional[Path] = None,
    value_model_file: Optional[Path] = None,
    voltron_target_index: Optional[int] = None,
) -> dict:
    deck_file = Path(deck_file)
    payload = {
        "kind": PROJECT_KIND_V43,
        "version": V43_VERSION,
        "deck": {
            "file_name": deck_file.name,
            "source_path": str(deck_file),
            "embedded_text": deck_file.read_text(encoding="utf-8-sig", errors="replace"),
        },
        "commanders": list(commanders),
        "simulation": {
            "runs": int(runs),
            "turns": int(turns),
            "seed": int(seed),
            "strategy_tags": sorted(set(strategy_tags)),
            "opponent_profile": opponent_profile,
            # v4.15.7 (task #18, "Voltron-GUI-Feld"): None if the field
            # loads/saves fine either way; missing entirely in project files
            # saved before v4.15.7 (load_project_v43/gui.load_project both
            # default that case to "off").
            "voltron_target_index": voltron_target_index,
        },
        "scenarios": [normalize_scenario(x, i) for i, x in enumerate(scenarios)],
        "strategy": None,
        "value_model": None,
    }
    if strategy_file and Path(strategy_file).exists():
        payload["strategy"] = {
            "file_name": Path(strategy_file).name,
            "source_path": str(strategy_file),
            "embedded_json": json.loads(Path(strategy_file).read_text(encoding="utf-8")),
        }
    if value_model_file and Path(value_model_file).exists():
        payload["value_model"] = {
            "file_name": Path(value_model_file).name,
            "source_path": str(value_model_file),
            "embedded_json": json.loads(Path(value_model_file).read_text(encoding="utf-8")),
        }
    return payload


def save_project_v43(path: Path, **kwargs):
    path = Path(path)
    payload = project_payload_v43(**kwargs)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project_v43(path: Path) -> dict:
    """
    Load a portable v4.3 project. If the original deck/strategy/value-model paths
    no longer exist, embedded copies are materialized next to the project file.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("kind") != PROJECT_KIND_V43:
        raise ValueError("This JSON is not a Commander Goldfish v4.3 project.")

    materialized_dir = path.parent / ".goldfish_project_files"
    materialized_dir.mkdir(parents=True, exist_ok=True)

    deck_info = data.get("deck") or {}
    source = Path(deck_info.get("source_path") or "")
    if source.exists():
        deck_path = source
    else:
        name = deck_info.get("file_name") or "project_deck.txt"
        deck_path = materialized_dir / name
        deck_path.write_text(deck_info.get("embedded_text") or "", encoding="utf-8")

    def resolve_embedded_json(section: str) -> Optional[Path]:
        info = data.get(section)
        if not info:
            return None
        p = Path(info.get("source_path") or "")
        if p.exists():
            return p
        embedded = info.get("embedded_json")
        if embedded is None:
            return None
        name = info.get("file_name") or f"{section}.json"
        p = materialized_dir / name
        p.write_text(json.dumps(embedded, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    sim = data.get("simulation") or {}
    return {
        "project_path": path,
        "deck_path": deck_path,
        "commanders": list(data.get("commanders") or []),
        "runs": int(sim.get("runs", 5000)),
        "turns": int(sim.get("turns", 10)),
        "seed": int(sim.get("seed", 1)),
        "strategy_tags": set(sim.get("strategy_tags") or []),
        "opponent_profile": sim.get("opponent_profile", "goldfish"),
        # v4.15.7 (task #18, "Voltron-GUI-Feld"): absent in project files
        # saved before v4.15.7 -> None ("Aus"), same as a fresh strategy.
        "voltron_target_index": sim.get("voltron_target_index"),
        "scenarios": [normalize_scenario(x, i) for i, x in enumerate(data.get("scenarios") or [])],
        "strategy_file": resolve_embedded_json("strategy"),
        "value_model_file": resolve_embedded_json("value_model"),
    }




def main_v43():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.3")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_3_gui import launch_gui
        launch_gui()
        return

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v43(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.3 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




# ===========================================================================
# v4.3.1 — automatic dependency bootstrap
# ===========================================================================

V431_VERSION = "4.3.1"


def _dependency_importable(import_name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(import_name) is not None


def _run_pip_install(pip_name: str, status_callback=None):
    import subprocess
    import sys

    def status(msg):
        if status_callback:
            status_callback(msg)

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        status("pip fehlt – Python ensurepip wird ausgeführt …")
        subprocess.run(
            [sys.executable, "-m", "ensurepip", "--upgrade"],
            check=True,
        )

    cmd = [
        sys.executable, "-m", "pip", "install",
        "--disable-pip-version-check",
        pip_name,
    ]
    status(f"Installiere fehlendes Python-Paket: {pip_name} …")

    try:
        subprocess.run(cmd, check=True)
        return
    except subprocess.CalledProcessError:
        in_venv = getattr(sys, "base_prefix", sys.prefix) != sys.prefix
        if in_venv:
            raise

    status(f"Normale Installation nicht möglich – versuche Benutzerinstallation für {pip_name} …")
    subprocess.run(cmd + ["--user"], check=True)


def ensure_pip_dependency(import_name: str, pip_name: str, status_callback=None) -> bool:
    import importlib
    import sys

    if _dependency_importable(import_name):
        return False

    try:
        _run_pip_install(pip_name, status_callback=status_callback)
    except Exception as exc:
        raise RuntimeError(
            f"Das benötigte Python-Paket '{pip_name}' fehlt und konnte nicht automatisch "
            f"installiert werden. Starte notfalls manuell:\n"
            f'  "{sys.executable}" -m pip install {pip_name}\n\n'
            f"Ursprünglicher Fehler: {exc}"
        ) from exc

    importlib.invalidate_caches()
    if not _dependency_importable(import_name):
        raise RuntimeError(
            f"'{pip_name}' wurde installiert, ist aber in diesem Python-Prozess noch "
            f"nicht importierbar. Bitte das Programm einmal neu starten."
        )
    return True




def _scryfall_fuzzy_lookup_requests(session, name: str) -> Optional[dict]:
    import requests
    try:
        response = session.get(
            "https://api.scryfall.com/cards/named",
            params={"fuzzy": name},
            timeout=30,
        )
        if response.status_code == 200:
            obj = response.json()
        else:
            obj = None
    except requests.RequestException:
        obj = None
    time.sleep(0.1)
    return obj


def _scryfall_get_many_requests(self, entries: List[DeckEntry]) -> Dict[str, dict]:
    """
    Requests-backed Scryfall lookup while keeping the existing local cache.

    v4.17.0: delegates the actual batch-fetch + fuzzy-fallback logic to
    ScryfallProvider._resolve_missing() (see its docstring for why - this
    function used to have its own full copy of that logic, duplicated
    across three call sites, which is exactly how a real bug fix (the
    v4.16.0 double-faced-card indexing fix) silently failed to reach the
    actually-live get_many() implementation last time).
    """
    import requests

    result, missing = self._split_cache(entries)

    if missing and self.offline:
        raise RuntimeError(
            f"{len(missing)} Karten fehlen im lokalen Scryfall-Cache. "
            f"Einmal ohne --offline starten."
        )

    session = requests.Session()
    session.headers.update({
        "User-Agent": "CommanderGoldfishSimulator/4.3.2 (personal deck analysis)",
        "Accept": "application/json;q=0.9,*/*;q=0.8",
        "Content-Type": "application/json",
    })

    def post_json(url, body):
        try:
            response = session.post(url, data=body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise RuntimeError(
                "Scryfall ist nicht erreichbar. Prüfe Internetzugang, Firewall oder VPN. "
                f"Technischer Fehler: {exc}"
            ) from exc

    def fuzzy_named(name):
        return _scryfall_fuzzy_lookup_requests(session, name)

    result.update(self._resolve_missing(missing, post_json, fuzzy_named))
    return result


# Use the bootstrapped HTTP layer for Scryfall metadata.
ScryfallProvider.get_many = _scryfall_get_many_requests


def main_v431():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.3.1")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_3_1_gui import launch_gui
        launch_gui()
        return

    ensure_runtime_dependencies(include_images=False, status_callback=print)

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v43(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.3.1 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




# ===========================================================================
# v4.3.2 — strategy visibility + setup steering fixes
# ===========================================================================

V432_VERSION = "4.3.4"
MANA_FONT_URL = "https://mana.andrewgioia.com/icons.html"

# Preserve the prior implementations before overriding them.
_V431_role_set = role_set
_V431_is_reactive_only = is_reactive_only
_V431_cast_score_v4 = cast_score_v4
_V431_attack_phase = attack_phase
_V431_resolve_x_spell = resolve_x_spell

STRATEGY_CAST_ROLE_BONUSES = {
    "lifegain": {
        "lifegain": 1.2,
        "lifegain_replacement": 2.2,
        "lifegain_payoff": 1.7,
    },
    "mill": {"selection": 0.8, "draw": 0.5, "draw_engine": 0.5},
    "counters": {"token": 0.4, "engine": 0.5},
    "voltron": {"engine": 0.4, "finisher": 0.7},
    "tokens": {"token": 1.6, "food": 0.6, "treasure": 0.5},
    "aristocrats": {"token": 0.8, "finisher": 0.8, "recursion": 0.7},
    "spellslinger": {"draw": 0.8, "draw_engine": 0.7, "selection": 0.5},
    "artifacts": {"food": 0.8, "treasure": 0.8, "ramp": 0.4},
    "enchantress": {"draw_engine": 0.8, "tutor": 0.6},
    "graveyard": {"recursion": 1.4, "selection": 0.7},
    "lands": {"ramp": 1.5},
    "control": {"draw": 0.8, "draw_engine": 0.8, "selection": 0.5},
    "aggro": {"finisher": 0.8, "token": 0.5},
    "combo": {"tutor": 1.7, "draw": 0.7, "ramp": 0.6, "engine": 0.5},
}

STRATEGY_EXPLANATIONS = {
    "lifegain": "Gewichtet Lifegain-Quellen, Lifegain-Verstärker und Lifegain-Payoffs höher.",
    "mill": "Gewichtet Selection/Filtering und Mill-nahe Value-Effekte höher.",
    "counters": "Bevorzugt Engine-/Token-Entwicklung, die Counter-Pläne unterstützt.",
    "voltron": "Bevorzugt Commander-/Finisher-Entwicklung; Schutz bleibt im reinen Goldfish auf der Hand.",
    "tokens": "Gewichtet Token-, Food- und Treasure-Produktion höher.",
    "aristocrats": "Gewichtet Token, Recursion und Drain-/Finisher-Payoffs höher.",
    "spellslinger": "Gewichtet Draw, Selection und spell-basierte Engines höher.",
    "artifacts": "Gewichtet Food/Treasure und artefaktnahe Ressourcen höher.",
    "enchantress": "Gewichtet Draw-Engines und Tutor-Value höher.",
    "graveyard": "Gewichtet Recursion und graveyard-nahe Selection höher.",
    "lands": "Gewichtet Ramp und Manaentwicklung höher.",
    "control": "Gewichtet Kartenfluss und Selection höher; Interaktion wird im Goldfish nicht blind verbraucht.",
    "aggro": "Gewichtet frühe Boardpräsenz, Token und Finisher etwas höher.",
    "combo": "Gewichtet Tutor, Draw, Ramp und Engine-Pieces höher.",
}


def strategy_explanation(tags: Set[str]) -> str:
    tags = set(tags or set())
    if not tags:
        return (
            "Keine Strategie-Tags aktiv: neutrale Value-Heuristik. "
            "Tags ändern Value-Gewichte, X-Spell-ROI, Card-Highlights und moderat die Cast-Priorität; "
            "sie ersetzen keine vollständige Pilot-KI."
        )
    lines = [STRATEGY_EXPLANATIONS.get(t, t) for t in sorted(tags)]
    return " ".join(lines) + (
        " Die Tags beeinflussen Value/X-Spell-Bewertung, Card-Highlights und moderat die Cast-Priorität; "
        "Regeltexte und Win-Condition-Szenarien werden dadurch nicht umgeschrieben."
    )


def role_set(card: Card) -> Set[str]:
    """v4.3.2 semantic fixes, especially pure protection instants."""
    roles = set(_V431_role_set(card))
    low = strip_reminder_text(card.oracle_text).lower()

    # Heroic Intervention style plural wording was missed by the older parser.
    if card.is_instant and any(x in low for x in (
        "gain hexproof",
        "gains hexproof",
        "gain indestructible",
        "gains indestructible",
        "phase out",
        "return those cards to the battlefield",
    )):
        roles.add("protection")

    return roles


def is_reactive_only(card: Card, strategy: Strategy) -> bool:
    # Explicit user/deck strategy still wins.
    if card.name in strategy.hold_cards or card.name in strategy.never_cast_goldfish:
        return True

    # Protection instants are reactive even when they create a Role/token as a side
    # effect (Royal Treatment was previously cast just because it had the `token` role).
    if card.is_instant and "protection" in card.roles:
        return True

    return _V431_is_reactive_only(card, strategy)


def _strategy_semantic_bonus(card: Card, strategy: Strategy) -> float:
    bonus = 0.0
    tags = set(getattr(strategy, "archetypes", set()) or set())
    for tag in tags:
        for role, amount in STRATEGY_CAST_ROLE_BONUSES.get(tag, {}).items():
            if role in card.roles:
                bonus += amount

    low = strip_reminder_text(card.oracle_text).lower()
    if "mill" in tags and "mill" in low:
        bonus += 1.5
    if "counters" in tags and "+1/+1 counter" in low:
        bonus += 1.4
    if "voltron" in tags and ("equipped creature" in low or "equip" in card.keywords):
        bonus += 1.3
    if "aristocrats" in tags and "sacrifice" in low:
        bonus += 0.8
    if "spellslinger" in tags and (card.is_instant or card.is_sorcery):
        bonus += 0.45
    if "artifacts" in tags and card.is_artifact:
        bonus += 0.65
    if "enchantress" in tags and card.is_enchantment:
        bonus += 0.65
    if "graveyard" in tags and "graveyard" in low:
        bonus += 0.75
    if "aggro" in tags and card.is_creature and card.min_cost <= 3:
        bonus += 0.55
    return min(4.0, bonus)


def cast_score_v4(opt_or_card, state: GameState, strategy: Strategy) -> float:
    """
    Keep the prior value model, then let selected strategy tags make a modest,
    transparent sequencing difference.
    """
    score = _V431_cast_score_v4(opt_or_card, state, strategy)
    card = opt_or_card.card if hasattr(opt_or_card, "card") else opt_or_card
    return score + _strategy_semantic_bonus(card, strategy)






def resolve_x_spell(state: GameState, strategy: Strategy, card: Card, plan: XPlan):
    # Pest Infestation was previously logged as creating "This" tokens due a
    # generic regex swallowing the death-trigger text. Model its actual Pests.
    if card.name == "Pest Infestation":
        x = plan.x
        create_tokens(
            state, strategy, "Pest", 2 * x,
            creature=True, power=1, toughness=1,
            source=card.name,
        )
        state.log(
            f"X-VALUE {card.name}: X={x}, gross={plan.gross_value:.2f}, "
            f"net={plan.net_value:.2f}, ROI={plan.roi:.2f}"
        )
        return
    return _V431_resolve_x_spell(state, strategy, card, plan)


def main_v432():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.3.4")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_3_4_gui import launch_gui
        launch_gui()
        return

    ensure_runtime_dependencies(include_images=False, status_callback=print)
    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")
    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v43(
        args.deck_file, commander_names,
        runs=args.runs, turns=args.turns, seed=args.seed,
        strategy_file=args.strategy, strategy_tags=tags or None,
        opponent_profile=args.opponent, value_model_file=args.value_model,
        scenarios_file=args.scenarios, cache_path=args.cache,
        offline=args.offline, metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.3.4 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




# ===========================================================================
# v4.4.0 — PERFORMANCE / ADAPTIVE SCENARIO / MODEL-COVERAGE PASS
# ===========================================================================

V440_VERSION = ENGINE_VERSION


# ---------------------------------------------------------------------------
# 1) Stop resolving the goldfish immediately after a deterministic win.
# ---------------------------------------------------------------------------

class GoldfishWinReached(Exception):
    """Internal control-flow exception used only to stop deterministic post-win work."""


def check_win(state: GameState):
    if state.win_turn is None and state.opponents and all(x <= 0 for x in state.opponents):
        state.win_turn = state.turn
        state.log("ALL OPPONENTS AT 0: WIN")
        if getattr(state, "abort_on_win", False):
            raise GoldfishWinReached()


# ---------------------------------------------------------------------------
# 2) Strict intrinsic keyword parsing.
# ---------------------------------------------------------------------------

def keyword_set(card: Card) -> Set[str]:
    """
    Intrinsic keyword abilities + strategic keyword actions.

    Scryfall's `keywords` array means "keywords used by this card", not necessarily
    "keywords this permanent intrinsically has". Therefore a card that merely grants
    deathtouch/lifelink/ward to another object must NOT inherit that keyword here.
    """
    kws: Set[str] = set()

    for line in split_oracle_lines(card.oracle_text):
        clean = strip_reminder_text(line).strip().lower()
        if not clean:
            continue

        # A static keyword line is typically "Flying", "Deathtouch, lifelink",
        # "Ward {2}", etc. Sentences that grant keywords are excluded.
        grants_other = any(
            phrase in clean
            for phrase in (
                " gains ", " gain ", " have ", " gets ",
                " creatures you control have ", " creature has ",
                " tokens have ", " equipped creature has ",
            )
        )
        static_candidate = "" if grants_other else clean

        if static_candidate:
            for kw in KNOWN_KEYWORDS:
                if kw == "ward":
                    pattern = r"(?:^|,\s*)ward(?:\s*[—-]\s*[^,.]+|\s+\{[^}]+\}|\s+\d+)?(?:,|$)"
                elif kw == "protection":
                    pattern = r"(?:^|,\s*)protection from [^,.]+(?:,|$)"
                else:
                    pattern = rf"(?:^|,\s*){re.escape(kw)}(?:,|$)"
                if re.search(pattern, static_candidate):
                    kws.add(kw)

        # Keyword actions are mechanics even when used inside triggered/activated text.
        for action in ("scry", "surveil", "connive", "investigate", "proliferate"):
            if re.search(rf"\b{action}(?:s|d|ed)?\b", clean):
                kws.add(action)

    return kws


# Re-run semantic enrichment with the strict keyword model.
def enrich_semantics(card: Card) -> Card:
    clean_keywords = keyword_set(card)
    tmp = replace(card, keywords=clean_keywords)
    return replace(tmp, roles=role_set(tmp))


# ---------------------------------------------------------------------------
# 3) Adaptive scenario focus: observe all, steer only one probabilistically.
# ---------------------------------------------------------------------------

def _active_scenario_by_id(strategy: ScenarioStrategy, sid: Optional[str]) -> Optional[dict]:
    if not sid:
        return None
    return next(
        (s for s in strategy.scenarios if s.get("id") == sid and s.get("enabled", True)),
        None,
    )


def _focused_scenario(state: GameState, strategy: ScenarioStrategy) -> Optional[dict]:
    return _active_scenario_by_id(strategy, getattr(state, "scenario_focus_id", None))


def _card_anywhere(state: GameState, name: str) -> Set[str]:
    zones = set()
    if any(c.name == name for c in state.library):
        zones.add("library")
    if any(c.name == name for c in state.hand):
        zones.add("hand")
    if any(p.card.name == name for p in state.battlefield):
        zones.add("battlefield")
    if any(c.name == name for c in state.graveyard):
        zones.add("graveyard")
    if any(c.name == name for c in state.exile):
        zones.add("exile")
    if any(c.name == name for c in state.command_zone):
        zones.add("command_zone")
    return zones


def _requirement_feasibility(state: GameState, req: dict) -> float:
    ok, _ = scenario_card_requirement_met(state, req)
    if ok:
        return 1.0

    actual = _card_anywhere(state, req["card"])
    desired = set(req.get("zones", []))
    if not actual:
        return 0.0

    # Approximate accessibility, not a rules claim.
    best = 0.08
    if "battlefield" in desired:
        if "hand" in actual:
            best = max(best, 0.72)
        if "command_zone" in actual:
            best = max(best, 0.68)
        if "library" in actual:
            best = max(best, 0.38)
        if "graveyard" in actual:
            best = max(best, 0.22)
    if "hand" in desired:
        if "library" in actual:
            best = max(best, 0.48)
        if "graveyard" in actual:
            best = max(best, 0.28)
    if "library" in desired:
        if "library" in actual:
            best = max(best, 0.95)
        else:
            # Getting a specific card back into the library is usually not trivial.
            best = max(best, 0.12)
    if "graveyard" in desired:
        if "hand" in actual:
            best = max(best, 0.45)
        if "battlefield" in actual:
            best = max(best, 0.32)
        if "library" in actual:
            best = max(best, 0.18)
    if "exile" in desired and "exile" in actual:
        best = 1.0
    if "command_zone" in desired and "command_zone" in actual:
        best = 1.0
    return best


def scenario_feasibility(state: GameState, strategy: ScenarioStrategy, scenario: dict) -> float:
    """
    0..1 heuristic for how close the current game is to the user-defined target state.
    It is used only to bias pilot choices, never to declare a scenario reached.
    """
    parts = []

    reqs = scenario.get("requirements", [])
    if reqs:
        parts.append((0.48, sum(_requirement_feasibility(state, r) for r in reqs) / len(reqs)))

    packages = [p for p in scenario.get("packages", []) if p.get("enabled", True)]
    if packages:
        pkg_scores = []
        for pkg in packages:
            ps = scenario_package_status(state, pkg)
            needed = max(1, ps.get("needed", 1))
            matched = ps.get("matched", 0)
            exact = min(1.0, matched / needed)
            if exact < 1.0:
                # Give some credit when missing members still exist in plausible zones.
                member_scores = []
                for member in pkg.get("members", []):
                    req = package_member_requirement(pkg, member)
                    member_scores.append(_requirement_feasibility(state, req))
                potential = (sum(sorted(member_scores, reverse=True)[:needed]) / needed) if member_scores else 0.0
                exact = max(exact, 0.65 * potential)
            pkg_scores.append(exact)
        parts.append((0.17, sum(pkg_scores) / len(pkg_scores)))

    th = scenario.get("thresholds", {})
    threshold_ratios = []
    mapping = {
        "life": float(state.life),
        "lands": float(len(state.lands())),
        "food": float(state.food),
        "treasure": float(state.treasure),
        "clues": float(state.clues),
    }
    for key, current in mapping.items():
        target = float(th.get(key, 0) or 0)
        if target > 0:
            threshold_ratios.append(min(1.0, current / target))
    if threshold_ratios:
        parts.append((0.20, sum(threshold_ratios) / len(threshold_ratios)))

    # v4.15.0 (WP10): the 'derived' block (v4.4, dynamic/computed predicates -
    # resource_available/opponent_life_at_or_below/x_spell_lethal/
    # commander_damage_lethal) was, until v4.15.0, evaluated ONLY for
    # "reached" status (scenario_derived_status/scenario_status), never for
    # STEERING - a scenario built primarily around derived predicates (e.g.
    # a Win Condition that's really "tap 3 creatures + an X-spell reaches
    # lethal", with no plain card/threshold/mana requirements of its own,
    # like the real Aziza Alpha-Strike scenario) would get feasibility ONLY
    # from whatever plain requirements/thresholds/mana it also happens to
    # declare - the actual win-condition-defining logic was invisible to
    # select_adaptive_scenario_focus, so the engine would never deliberately
    # steer toward assembling it. v4.15.0 fixed that with a simple 1.0/0.0
    # credit per predicate (satisfied/not, "not computable" counted as
    # not-yet-satisfied), deliberately without per-predicate partial credit
    # like packages/thresholds get - reimplementing each handler's own "how
    # close" logic here would have risked drifting out of sync with
    # scenario_predicates/handlers.py over time.
    #
    # v4.15.7 (task #18, "derived-Teilkredit"): closes that gap WITHOUT the
    # duplication risk above - PredicateResult now carries an optional
    # `progress` field (App/scenario_predicates/registry.py) that each
    # handler sets itself, from data it already has on hand (e.g.
    # opponent_life_at_or_below already computed both the current life and
    # the threshold; it just exposes their ratio too). effective_progress
    # falls back to the old binary satisfied/not reading whenever a handler
    # doesn't set one, so this is purely additive.
    derived = scenario.get("derived") or []
    if derived:
        evaluation = scenario_predicates_registry.evaluate_all(
            sys.modules[__name__], derived, state, strategy,
        )
        if evaluation.results:
            derived_score = sum(r.effective_progress for r in evaluation.results) / len(evaluation.results)
            parts.append((0.25, derived_score))

    mana = scenario.get("mana", {})
    mana_target = max(
        int(mana.get("total", 0) or 0),
        sum(int(mana.get(c, 0) or 0) for c in COLORS + (COLORLESS,))
    )
    if mana_target > 0:
        mana_now = float(available_mana_value(state, strategy))
        mana_score = min(1.0, mana_now / mana_target)
        mana_ok, _ = scenario_mana_status(state, strategy, scenario)
        if mana_ok:
            mana_score = 1.0
        parts.append((0.15, mana_score))

    if not parts:
        return 0.0
    total_w = sum(w for w, _ in parts)
    return max(0.0, min(1.0, sum(w * v for w, v in parts) / total_w))


def _weighted_choice(rng: random.Random, items: List[Tuple[object, float]]):
    total = sum(max(0.0, w) for _, w in items)
    if total <= 0:
        return items[0][0] if items else None
    roll = rng.random() * total
    acc = 0.0
    for item, weight in items:
        acc += max(0.0, weight)
        if roll <= acc:
            return item
    return items[-1][0]


def select_adaptive_scenario_focus(
    state: GameState,
    strategy: ScenarioStrategy,
    rng: random.Random,
) -> Optional[dict]:
    candidates = [
        s for s in strategy.scenarios
        if s.get("enabled", True)
        and s.get("steer", True)
        and s.get("id") not in getattr(state, "scenario_reached_names", set())
    ]
    if not candidates:
        state.scenario_focus_id = None
        state.scenario_focus_feasibility = 0.0
        state.scenario_focus_strength = 0.0
        strategy._active_focus_id = None
        return None

    scored = [(s, scenario_feasibility(state, strategy, s)) for s in candidates]
    best = max(v for _, v in scored)

    # Deliberately non-deterministic commitment: even a promising line is not followed
    # 100% of the time. This lets the goldfish still discover alternative value lines.
    commitment_probability = min(0.90, 0.18 + 0.72 * best)
    if rng.random() > commitment_probability:
        state.scenario_focus_id = None
        state.scenario_focus_feasibility = best
        state.scenario_focus_strength = 0.0
        strategy._active_focus_id = None
        return None

    choice = _weighted_choice(
        rng,
        [(s, 0.08 + (score ** 2.6) * 3.0) for s, score in scored],
    )
    chosen_score = dict((s["id"], score) for s, score in scored)[choice["id"]]
    state.scenario_focus_id = choice["id"]
    state.scenario_focus_feasibility = chosen_score
    state.scenario_focus_strength = 0.35 + 0.65 * chosen_score
    strategy._active_focus_id = choice["id"]

    # Dynamic tutor preferences: only the current focus gets steering priority.
    if not hasattr(strategy, "_neutral_tutor_priority"):
        strategy._neutral_tutor_priority = list(strategy.tutor_priority)
        strategy._neutral_legendary_priority = list(strategy.legendary_tutor_priority)
        strategy._neutral_enchantment_priority = list(strategy.enchantment_tutor_priority)

    focus_names = []
    for req in choice.get("requirements", []):
        if set(req.get("zones", [])) & {"hand", "battlefield"}:
            focus_names.append(req["card"])
    for pkg in choice.get("packages", []):
        ps = scenario_package_status(state, pkg)
        if ps.get("met"):
            continue
        for member in pkg.get("members", []):
            req = package_member_requirement(pkg, member)
            if set(req.get("zones", [])) & {"hand", "battlefield"}:
                focus_names.append(member["card"])

    def front(base):
        seen = set()
        ordered = [x for x in focus_names if not (x in seen or seen.add(x))]
        return ordered + [x for x in base if x not in seen]

    strategy.tutor_priority = front(strategy._neutral_tutor_priority)
    strategy.legendary_tutor_priority = front(strategy._neutral_legendary_priority)
    strategy.enchantment_tutor_priority = front(strategy._neutral_enchantment_priority)

    state.log(
        f"SCENARIO FOCUS: {choice['name']} "
        f"(feasibility {chosen_score:.2f}, commitment {commitment_probability:.2f})"
    )
    return choice


def _steering_scenarios(state: GameState, strategy: ScenarioStrategy) -> List[dict]:
    sc = _focused_scenario(state, strategy)
    return [sc] if sc else []


def scenario_requires_board_card(state: GameState, strategy: ScenarioStrategy, card_name: str) -> bool:
    for sc in _steering_scenarios(state, strategy):
        if sc["id"] in getattr(state, "scenario_reached_names", set()):
            continue
        for req in sc.get("requirements", []):
            if req["card"] == card_name and "battlefield" in req.get("zones", []):
                ok, _ = scenario_card_requirement_met(state, req)
                if not ok:
                    return True
        for pkg in sc.get("packages", []):
            ps = scenario_package_status(state, pkg)
            if ps.get("met"):
                continue
            for member in pkg.get("members", []):
                if member["card"] != card_name:
                    continue
                req = package_member_requirement(pkg, member)
                if "battlefield" in req.get("zones", []):
                    ok, _ = scenario_card_requirement_met(state, req)
                    if not ok:
                        return True
    return False


def scenario_requires_hand_only(strategy: ScenarioStrategy, card_name: str) -> bool:
    sid = getattr(strategy, "_active_focus_id", None)
    sc = _active_scenario_by_id(strategy, sid)
    if not sc:
        return False
    for req in sc.get("requirements", []):
        if req["card"] == card_name:
            zones = set(req.get("zones", []))
            if "hand" in zones and not (zones & {"battlefield", "graveyard", "exile"}):
                return True
    return False


def scenario_requires_graveyard_spell(strategy: ScenarioStrategy, card: Card) -> bool:
    if not (card.is_instant or card.is_sorcery):
        return False
    sid = getattr(strategy, "_active_focus_id", None)
    sc = _active_scenario_by_id(strategy, sid)
    if not sc:
        return False
    return any(
        req["card"] == card.name and set(req.get("zones", [])) == {"graveyard"}
        for req in sc.get("requirements", [])
    )


def scenario_package_cast_bonus(state: GameState, strategy: ScenarioStrategy, card_name: str) -> float:
    sc = _focused_scenario(state, strategy)
    if not sc:
        return 0.0
    strength = float(getattr(state, "scenario_focus_strength", 0.0))
    bonus = 0.0
    for pkg in sc.get("packages", []):
        if not pkg.get("enabled", True):
            continue
        ps = scenario_package_status(state, pkg)
        if ps.get("met"):
            continue
        member = next((m for m in pkg.get("members", []) if m["card"] == card_name), None)
        if not member:
            continue
        req = package_member_requirement(pkg, member)
        if "battlefield" in req.get("zones", []):
            bonus += (4.0 + 1.2 * max(0, ps["needed"] - ps["matched"])) * strength
    return bonus


def scenario_cast_adjustment(opt: CastOption, state: GameState, strategy: ScenarioStrategy) -> float:
    card = opt.card
    sc = _focused_scenario(state, strategy)
    if not sc:
        return 0.0

    strength = float(getattr(state, "scenario_focus_strength", 0.0))
    if scenario_requires_hand_only(strategy, card.name):
        return -100.0

    bonus = scenario_package_cast_bonus(state, strategy, card.name)
    if scenario_requires_board_card(state, strategy, card.name):
        bonus += 13.0 * strength
    if scenario_requires_graveyard_spell(strategy, card):
        bonus += 7.0 * strength

    status = scenario_status(state, strategy, sc)
    if status["reached"]:
        # The target state already exists: do not burn the exact resources that made
        # it possible while a modeled executor gets its chance.
        if not scenario_requires_board_card(state, strategy, card.name):
            bonus -= 25.0 * max(0.5, strength)
    elif status["cards_and_thresholds_met"] and not status["mana_met"]:
        if not (card.roles & {"ramp", "draw", "draw_engine", "tutor"}):
            bonus -= 5.0 * strength

    return bonus


def scenario_preserve_untapped(state: GameState, strategy: Strategy, card_name: str) -> bool:
    sc = _focused_scenario(state, strategy) if isinstance(strategy, ScenarioStrategy) else None
    if not sc:
        return False
    for req in sc.get("requirements", []):
        if (
            req.get("card") == card_name
            and req.get("untapped", False)
            and "battlefield" in req.get("zones", [])
        ):
            return True
    for pkg in sc.get("packages", []):
        if not pkg.get("enabled", True) or not pkg.get("untapped", False):
            continue
        if any(m.get("card") == card_name for m in pkg.get("members", [])):
            return True
    return False


# ---------------------------------------------------------------------------
# 4) Better scenario diagnostics: "ever had mana" vs "mana left at final checkpoint".
# ---------------------------------------------------------------------------

def init_scenario_progress(strategy: ScenarioStrategy) -> Dict[str, dict]:
    out = {}
    for sc in strategy.scenarios:
        if not sc.get("enabled", True):
            continue
        out[sc["id"]] = {
            "scenario": sc,
            "first_nonmana_turn": None,
            "first_nonmana_checkpoint": "",
            "first_mana_turn": None,
            "first_mana_checkpoint": "",
            "first_reached_turn": None,
            "first_reached_checkpoint": "",
            "final_missing": [],
            "best_nonmana_missing": [],
            "best_nonmana_missing_count": 10**9,
            "best_all_missing": [],
            "best_all_missing_count": 10**9,
        }
    return out


def update_scenario_progress(
    state: GameState,
    strategy: ScenarioStrategy,
    progress: Dict[str, dict],
    checkpoint: str,
):
    reached_names = getattr(state, "scenario_reached_names", set())

    # Several Win Conditions often ask for the same mana package (e.g. 2WBG).
    # v4.3.x solved that identical payment problem once PER SCENARIO PER CHECKPOINT.
    # Cache equal mana requirements inside this checkpoint so one payment search can
    # serve every scenario with the same requirement.
    mana_cache: Dict[Tuple[int, int, int, int, int, int, int], Tuple[bool, str]] = {}

    def cached_mana_status(sc: dict) -> Tuple[bool, str]:
        m = sc.get("mana", {})
        key = (
            int(m.get("total", 0) or 0),
            int(m.get("W", 0) or 0),
            int(m.get("U", 0) or 0),
            int(m.get("B", 0) or 0),
            int(m.get("R", 0) or 0),
            int(m.get("G", 0) or 0),
            int(m.get("C", 0) or 0),
        )
        if key not in mana_cache:
            mana_cache[key] = scenario_mana_status(state, strategy, sc)
        return mana_cache[key]

    for sid, p in progress.items():
        sc = p["scenario"]
        nonmana_ok, nonmana_missing = scenario_nonmana_status(state, sc)
        mana_ok, mana_missing = cached_mana_status(sc)
        all_missing = list(nonmana_missing) + ([] if mana_ok else [mana_missing])

        if len(nonmana_missing) < p["best_nonmana_missing_count"]:
            p["best_nonmana_missing_count"] = len(nonmana_missing)
            p["best_nonmana_missing"] = list(nonmana_missing)
        if len(all_missing) < p["best_all_missing_count"]:
            p["best_all_missing_count"] = len(all_missing)
            p["best_all_missing"] = list(all_missing)

        if nonmana_ok and p["first_nonmana_turn"] is None:
            p["first_nonmana_turn"] = state.turn
            p["first_nonmana_checkpoint"] = checkpoint
        if mana_ok and p["first_mana_turn"] is None:
            p["first_mana_turn"] = state.turn
            p["first_mana_checkpoint"] = checkpoint
        if nonmana_ok and mana_ok and p["first_reached_turn"] is None:
            p["first_reached_turn"] = state.turn
            p["first_reached_checkpoint"] = checkpoint
            reached_names.add(sid)
            state.log(f"SCENARIO REACHED: {sc['name']} @ {checkpoint}")
            if sid == getattr(state, "scenario_focus_id", None):
                state.scenario_lock_id = sid

        p["final_missing"] = all_missing
    state.scenario_reached_names = reached_names


def _scenario_diagnostic_bottlenecks(p: dict) -> List[str]:
    if p["first_reached_turn"] is not None:
        return []
    out = []
    if p["first_nonmana_turn"] is None:
        if p["best_nonmana_missing"]:
            out.extend(p["best_nonmana_missing"])
        else:
            out.append("cards/thresholds never ready")
    if p["first_mana_turn"] is None:
        out.append("mana never ready")
    if p["first_nonmana_turn"] is not None and p["first_mana_turn"] is not None:
        out.append("setup/mana timing mismatch (not simultaneous)")
    return out or list(p.get("best_all_missing") or p.get("final_missing") or ["target state not reached"])


def scenario_run_rows(run_id: int, progress: Dict[str, dict], state: GameState) -> List[dict]:
    rows = []
    focus_counts = getattr(state, "scenario_focus_counts", Counter())
    played_turns = max(1, int(getattr(state, "played_turns", state.turn or 1)))
    for sid, p in progress.items():
        sc = p["scenario"]
        bottlenecks = _scenario_diagnostic_bottlenecks(p)
        rows.append({
            "run": run_id,
            "scenario_id": sid,
            "scenario_name": sc["name"],
            "kind": sc["kind"],
            "steer_candidate": int(bool(sc.get("steer", True))),
            "focused_turns": int(focus_counts.get(sid, 0)),
            "focused_pct_of_played_turns": round(100 * focus_counts.get(sid, 0) / played_turns, 2),
            "reached": int(p["first_reached_turn"] is not None),
            "first_reached_turn": "" if p["first_reached_turn"] is None else p["first_reached_turn"],
            "first_reached_checkpoint": p["first_reached_checkpoint"],
            "first_cards_thresholds_turn": "" if p["first_nonmana_turn"] is None else p["first_nonmana_turn"],
            "first_cards_thresholds_checkpoint": p["first_nonmana_checkpoint"],
            "first_mana_ready_turn": "" if p["first_mana_turn"] is None else p["first_mana_turn"],
            "first_mana_ready_checkpoint": p["first_mana_checkpoint"],
            "diagnostic_bottlenecks": " | ".join(bottlenecks),
            "final_missing_debug": " | ".join(p["final_missing"]),
            "life_end": round(state.life, 2),
            "lands_end": len(state.lands()),
            "food_end": state.food,
            "treasure_end": state.treasure,
        })
    return rows


# ---------------------------------------------------------------------------
# 5) Strategy-aware Food use and resource preservation.
# ---------------------------------------------------------------------------

def focused_life_target(state: GameState, strategy: Strategy) -> int:
    if isinstance(strategy, ScenarioStrategy):
        sc = _focused_scenario(state, strategy)
        if sc:
            target = int(sc.get("thresholds", {}).get("life", 0) or 0)
            if target > 0:
                return target
    if "lifegain" in getattr(strategy, "archetypes", set()):
        return int(getattr(strategy, "prefer_food_for_life_until", 111) or 111)
    return 0


_ORIGINAL_build_mana_sources_v440 = build_mana_sources
def build_mana_sources(state: GameState, strategy: Strategy) -> List[ManaSource]:
    sources = _ORIGINAL_build_mana_sources_v440(state, strategy)
    target = focused_life_target(state, strategy)
    preserve_food = target > state.life
    if preserve_food:
        for src in sources:
            if src.kind == "goose":
                src.penalty += 2.0
    return sources


def pay_additional_cost(card: Card, state: GameState, strategy: Optional[Strategy] = None):
    low = strip_reminder_text(card.oracle_text).lower()
    if "as an additional cost to cast this spell, sacrifice an artifact or creature" not in low:
        return

    target = focused_life_target(state, strategy) if strategy is not None else 0
    preserve_food = target > state.life

    def sac_clue():
        if state.clues > 0:
            state.clues -= 1
            token_sacrificed(state, "Clue", 1, strategy)
            state.log(f"{card.name}: sacrificed Clue as additional cost")
            return True
        return False

    def sac_treasure():
        if state.treasure > 0:
            state.treasure -= 1
            token_sacrificed(state, "Treasure", 1, strategy)
            state.log(f"{card.name}: sacrificed Treasure as additional cost")
            return True
        return False

    def sac_low_permanent():
        candidates = [
            p for p in state.battlefield
            if (p.card.is_creature or p.card.is_artifact)
            and not scenario_preserve_untapped(state, strategy, p.card.name)
        ]
        if not candidates:
            return False
        p = min(candidates, key=lambda x: generic_tutor_score(x.card, DEFAULT_TUTOR_PRIORITY))
        state.battlefield.remove(p)
        state.graveyard.append(p.card)
        state.log(f"{card.name}: sacrificed {p.card.name} as additional cost")
        return True

    def sac_food():
        if state.food > 0:
            state.food -= 1
            token_sacrificed(state, "Food", 1, strategy)
            state.log(f"{card.name}: sacrificed Food as additional cost")
            return True
        return False

    # Lifegain plans preserve Food when plausible; neutral decks keep the older cheap-token preference.
    order = (sac_clue, sac_treasure, sac_low_permanent, sac_food) if preserve_food else (sac_food, sac_clue, sac_treasure, sac_low_permanent)
    for action in order:
        if action():
            return


def _use_food_to_life_target(state: GameState, strategy: Strategy, target: int, hard_cap: Optional[int] = None) -> int:
    uses = 0
    while state.food > 0 and (target <= 0 or state.life < target):
        if hard_cap is not None and uses >= hard_cap:
            break
        if not sacrifice_food_for_life(state, strategy):
            break
        uses += 1
    return uses


_ORIGINAL_end_step_v440 = end_step
def end_step(state: GameState, strategy: Strategy):
    if state.win_turn is not None:
        return

    # Deterministic end-step triggers.
    if state.has("Gyome, Master Chef") and state.nontoken_creatures_entered_this_turn > 0:
        create_tokens(
            state, strategy, "Food",
            state.nontoken_creatures_entered_this_turn,
            source="Gyome, Master Chef",
        )
    if state.has("Tippy-Toe, Terrific Partner") and state.gained_life_this_turn:
        draw_cards(state, 1, reason="Tippy-Toe end step")
    if state.has("The Arkenstone"):
        draw_cards(state, 1, reason="The Arkenstone end step")

    use_well_of_lost_dreams(state, strategy)
    use_trudge_garden(state, strategy)

    target = focused_life_target(state, strategy)
    life_plan_active = target > state.life

    # Heaped Harvest is excellent for the lifegain plan: base 3 life + real land.
    if life_plan_active:
        use_heaped_harvest(state, strategy)

        # Use payable Foods for the actual life objective before cashing three of them
        # into Peregrin draw. A focused target is allowed to use every affordable Food;
        # neutral lifegain play remains bounded to avoid pathological resource dumping.
        cap = None if _focused_scenario(state, strategy) else 5
        _use_food_to_life_target(state, strategy, target, hard_cap=cap)

        # If mana is exhausted but a Food remains, Lobelia converts one artifact into
        # base 2 life + table drain without paying {2}. This is less raw life than Food,
        # so it comes after normal Food activations.
        if state.life < target:
            use_lobelia(state, strategy)
    else:
        # Outside an active life target, preserve the old utility-first behavior.
        use_lobelia(state, strategy)
        use_heaped_harvest(state, strategy)

    if state.win_turn is not None:
        return

    # Draw conversion is secondary while a defined life threshold is still missing.
    if not life_plan_active or state.life >= target:
        if len(state.hand) <= 2:
            use_peregrin_draw(state, strategy)
        use_peregrin_draw(state, strategy)
        use_clue(state, strategy)

    # v4.15.6: whatever Treasure is still unspent after every other end-step
    # decision above is genuine excess - last in line, not competing with
    # the lifegain/ramp/draw plans above for the same mana.
    use_baron_bertram_sac_draw(state, strategy)


# ---------------------------------------------------------------------------
# v4.19.0: Planeswalker loyalty abilities.
# ---------------------------------------------------------------------------
#
# Found during the v4.18.0 model-coverage audit: "planeswalker" appeared
# exactly once in the whole engine (Card.is_permanent) - no loyalty
# tracking, no ability activation, ever. This is a real, goldfish-shaped
# model of the mechanic, not a full rules engine for it:
#   - This is a one-sided goldfish simulator (see the module docstring's
#     "no blockers are assumed" and grep -n "opponent.*attack" turning up
#     nothing anywhere in engine.py) - opponents never attack anything of
#     ours, so a planeswalker we control can only ever lose loyalty by
#     paying for its own "-N" ability, never to incoming damage. That
#     removes the single hardest part of modeling planeswalkers for free.
#   - Once per planeswalker per turn (real rule), at sorcery speed, this
#     picks the single affordable ability whose parsed effect scores
#     highest via the existing ValueModel - the same generic scoring
#     already used to sequence normal spells. A "-N" ultimate naturally
#     gets picked once loyalty covers its cost, since its effect (usually
#     several stacked actions) scores far above a repeated "+" ability -
#     no separate "bank loyalty for the ultimate" rule needed.
#   - Effect execution reuses the SAME generic action parser/executor as
#     everything else (_parse_semantic_actions / keyword_registry), so
#     only effects already in that generic vocabulary (damage-to-a-player-
#     shaped target, draw, gain life, create tokens) actually happen.
#     Bespoke effects with no parseable action - Ugin's "-X: Exile each
#     permanent with mana value X or less" (board wipes require targets
#     this engine doesn't track), Nicol Bolas's "-4: put target creature
#     or planeswalker on top of its owner's library" (needs an opposing
#     permanent to target), Sarkhan's "+1: becomes a 4/4 Dragon creature"
#     (a temporary type change this engine doesn't model), any emblem -
#     are intentionally left unexecuted rather than guessed at. A
#     planeswalker whose abilities are ALL of that shape (e.g. Sarkhan)
#     will simply never activate anything, same as it measured 0 in the
#     real Ur-Dragon audit run - honest, not silently inflated.
_LOYALTY_ABILITY_RE = re.compile(r"^([+−-])\s*(\d+|X)\s*:\s*(.+)$")


@dataclass
class LoyaltyAbility:
    sign: str          # "+", "-", or "0"
    cost_text: str      # numeric string, "X", or "0"
    text: str
    actions: List[SemanticAction] = field(default_factory=list)

    @property
    def is_x(self) -> bool:
        return self.cost_text.upper() == "X"

    @property
    def cost(self) -> float:
        return 0.0 if self.is_x else float(self.cost_text)


def parse_loyalty_abilities(card: Card) -> List[LoyaltyAbility]:
    if not card.is_planeswalker:
        return []
    abilities: List[LoyaltyAbility] = []
    for raw_line in split_oracle_lines(card.oracle_text):
        line = strip_reminder_text(raw_line).strip()
        if not line:
            continue
        m = _LOYALTY_ABILITY_RE.match(line)
        if m:
            sign_raw, cost_text, text = m.groups()
            sign = "-" if sign_raw in ("−", "-") else "+"
        elif line.startswith("0:"):
            sign, cost_text, text = "0", "0", line.split(":", 1)[1]
        else:
            continue
        text = text.strip()
        abilities.append(LoyaltyAbility(
            sign=sign, cost_text=cost_text, text=text,
            actions=_parse_semantic_actions(text),
        ))
    return abilities


_LOYALTY_ACTION_METRIC = {
    "draw": "draw",
    "gain_life": "life_gain",
    "opponent_life_loss": "opponent_life_loss",
    "create_token": "creature_tokens",
}


def _loyalty_ability_value(ability: LoyaltyAbility, strategy: Strategy, color_identity: Optional[Set[str]]) -> float:
    if not ability.actions:
        return float("-inf")  # nothing this engine can actually execute
    vm = strategy.value_model or ValueModel.load()
    total = 0.0
    for action in ability.actions:
        metric = _LOYALTY_ACTION_METRIC.get(action.kind)
        if not metric or not action.amount:
            continue
        total += vm.metric_value(metric, float(action.amount), strategy.archetypes, color_identity)
    return total


def activate_planeswalker_loyalty_abilities(state: GameState, strategy: Strategy):
    """Once per planeswalker per turn, at sorcery speed: activate whichever
    affordable, actually-executable loyalty ability scores highest. See the
    module comment above for what "actually-executable" excludes."""
    if state.win_turn is not None:
        return
    for p in [p for p in state.battlefield if p.card.is_planeswalker]:
        if p.loyalty is None or p.loyalty_activated_turn == state.turn:
            continue
        abilities = parse_loyalty_abilities(p.card)
        affordable = [
            a for a in abilities
            if not a.is_x and (a.sign != "-" or p.loyalty >= a.cost)
        ]
        scored = [(a, _loyalty_ability_value(a, strategy, p.card.color_identity)) for a in affordable]
        scored = [(a, v) for a, v in scored if v > float("-inf")]
        if not scored:
            continue
        best, _ = max(scored, key=lambda pair: pair[1])

        p.loyalty_activated_turn = state.turn
        if best.sign == "+":
            p.loyalty += best.cost
        elif best.sign == "-":
            p.loyalty -= best.cost

        did = False
        for action in best.actions:
            did = execute_semantic_action(state, strategy, p, action) or did
        if did:
            record_impact(state, p.card.name, "semantic_ability_uses", 1)
            state.log(
                f"LOYALTY [{best.sign}{best.cost_text}]: {p.card.name}: {best.text} "
                f"(loyalty now {p.loyalty:g})"
            )

        if p.loyalty <= 0:
            record_impact(state, p.card.name, "planeswalker_loyalty_zero", 1)
            move_permanent_to_zone(state, strategy, p, "graveyard", reason="loyalty reached 0")


def use_speaker_of_the_heavens(state: GameState, strategy: Strategy) -> bool:
    """Model the simple sorcery-speed Speaker activation when the life condition is met."""
    if state.life < 47:
        return False
    speakers = [
        p for p in state.cards_in_play("Speaker of the Heavens")
        if not p.tapped
        and _perm_ready(p, state)
        and not scenario_preserve_untapped(state, strategy, p.card.name)
    ]
    if not speakers:
        return False
    p = speakers[0]
    p.tapped = True
    create_tokens(
        state, strategy, "Angel", 1,
        creature=True, power=4, toughness=4,
        keywords={"flying", "vigilance"},
        source="Speaker of the Heavens",
    )
    record_impact(state, "Speaker of the Heavens", "token_multiplier", 1)
    state.log("Speaker of the Heavens: created 4/4 flying vigilance Angel")
    return True


def mycoloth_upkeep_trigger(state: GameState, strategy: Strategy):
    """
    v4.23.0: Mycoloth (real card, confirmed via card_impact.csv in the
    audited Witherbloom Pestilence deck) - "Devour 2 ... At the beginning
    of your upkeep, create a 1/1 green Saproling creature token for each
    +1/+1 counter on this creature." The Devour half is already handled
    generically (own_etb_effects' "v4.21.0: Devour" block seeds
    p.counters when Mycoloth enters); this is the recurring half, and it's
    a DYNAMIC count (however many counters Devour actually put on, which
    changes creature to creature and game to game) that the fully generic
    "create N tokens" parser (fixed number/number-word only) can't express
    - genuinely needs this card's own hook, not a guessed generic rule.
    """
    for p in state.cards_in_play("Mycoloth"):
        n = int(p.counters)
        if n > 0:
            create_tokens(
                state, strategy, "Saproling", n,
                creature=True, power=1, toughness=1, source="Mycoloth",
            )


def ribtruss_roaster_end_step_trigger(state: GameState, strategy: Strategy):
    """
    v4.23.0: Ribtruss Roaster (real card, confirmed via card_impact.csv in
    the same audited Witherbloom Pestilence deck as Mycoloth) - "Devour 1
    ... At the beginning of your end step, create a number of 1/1 black and
    green Pest creature tokens equal to the number of +1/+1 counters on
    this creature." Same shape and same reasoning as Mycoloth above (a
    dynamic per-game count, not a fixed generic-parser number) - just an
    end-step trigger instead of upkeep. The tokens' own "when this token
    dies, you gain 1 life" ability is not separately modeled (this engine
    has no per-token-instance death tracking within a TokenGroup, only a
    group-level count), a minor, disclosed simplification.
    """
    for p in state.cards_in_play("Ribtruss Roaster"):
        n = int(p.counters)
        if n > 0:
            create_tokens(
                state, strategy, "Pest", n,
                creature=True, power=1, toughness=1, source="Ribtruss Roaster",
            )


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def zimone_all_questioning_end_step_trigger(state: GameState, strategy: Strategy):
    """
    v4.23.0: Zimone, All-Questioning (real card, confirmed via
    card_model_coverage.csv in the audited Quandrix Unlimited deck) - "At
    the beginning of your end step, if a land entered the battlefield under
    your control this turn and you control a prime number of lands, create
    Primo, the Indivisible, a legendary 0/0 green and blue Fractal creature
    token, then put that many +1/+1 counters on it." "That many" = the
    (prime) number of lands controlled. The legend rule isn't separately
    enforced anywhere in this engine (no permanent is ever sacrificed for
    it - see e.g. Chatterfang/Augusta above, also legendary and also
    uncapped), so a later trigger just creates another same-named
    TokenGroup rather than growing one existing Primo - consistent with
    how every other repeated same-name creature-token creation already
    behaves here (create_tokens never merges into an existing group), not
    a special case invented for this card.
    """
    if not state.has("Zimone, All-Questioning"):
        return
    lands = [p for p in state.battlefield if p.card.is_land]
    if not any(p.entered_turn == state.turn for p in lands):
        return
    n = len(lands)
    if not _is_prime(n):
        return
    create_tokens(
        state, strategy, "Primo, the Indivisible", 1,
        creature=True, power=n, toughness=n, source="Zimone, All-Questioning",
    )
    record_impact(state, "Zimone, All-Questioning", "primo_counters", n)
    state.log(f"ZIMONE: created Primo, the Indivisible with {n} +1/+1 counter(s)")


def maybe_use_food_before_combat(state: GameState, strategy: Strategy):
    """
    A narrow precombat optimization, not a full pilot:
    use spare Food only when it can cross a known combat-relevant lifegain threshold.
    """
    if state.food <= 0:
        return
    # Doctor Strange's team buff turns on at 50.
    if state.has(DOCTOR_STRANGE_NAME) and state.life < 50:
        projected = life_replacement_amount(state, 3)
        if state.life + projected >= 50:
            sacrifice_food_for_life(state, strategy)
            return
    # Blossoming Bogbeast scales from total life gained this turn.
    if state.has("Blossoming Bogbeast") and "lifegain" in getattr(strategy, "archetypes", set()):
        # Spend at most one spare Food precombat; the rest remains for post-main planning.
        sacrifice_food_for_life(state, strategy)


# ---------------------------------------------------------------------------
# 6) High-impact Bilbo card fixes that remain useful without a full rules engine.
# ---------------------------------------------------------------------------

def gain_life(state: GameState, base: float, source: str = "") -> float:
    if base <= 0 or state.win_turn is not None:
        return 0.0

    amount = float(base)
    additions, doublers = [], []
    for p in state.battlefield:
        low = strip_reminder_text(p.card.oracle_text).lower()
        if "if you would gain life" not in low:
            continue
        if "that much life plus 1" in low:
            additions.append(p.card.name)
        if "twice that much life" in low:
            doublers.append(p.card.name)

    for name in additions:
        amount += 1
        record_impact(state, name, "life_amplified", 1)
    for name in doublers:
        extra = amount
        amount *= 2
        record_impact(state, name, "life_amplified", extra)

    state.life += amount
    state.life_gained_this_turn_amount += amount
    state.gained_life_this_turn = True
    state.life_events_this_turn += 1
    record_impact(state, source, "life_gain", base)
    check_life_milestones(state)

    if source:
        state.log(f"{source}: gain {amount:g} life (base {base:g})")
    if state.has("Well of Lost Dreams"):
        state.well_caps_this_turn.append(amount)
    # v4.15.6: Trudge Garden ("Whenever you gain life, you may pay {2}. If you
    # do, create a 4/4 green Fungus Beast creature token with trample.") -
    # one trigger per lifegain EVENT (matching the real rule), deferred and
    # resolved with spare mana at end of step - same pattern as Well of Lost
    # Dreams's well_caps_this_turn above, not an assumed-affordable flat cost.
    if state.has("Trudge Garden"):
        state.trudge_garden_triggers_this_turn += 1
    # v4.15.6: Field-Tested Frying Pan ("Equipped creature has 'Whenever you
    # gain life, this creature gets +X/+X until end of turn, where X is the
    # amount of life you gained.'") - the Pan's own ETB creates and attaches
    # to a 1/1 Halfling token (own_etb_effects), and goldfish has no reason
    # to move it elsewhere afterward, so the pump is modeled as applying to
    # that Halfling token group specifically (token_group_power below) for
    # as long as both the Pan and a Halfling token are in play.
    if state.has("Field-Tested Frying Pan") and any(
        g.name == "Halfling" and g.count > 0 for g in state.creature_tokens
    ):
        state.frying_pan_bonus_this_turn += amount
        record_impact(state, "Field-Tested Frying Pan", "combat_pump", amount)

    # Heroic Feast: one +1/+1 counter on up to 'amount gained' target creatures.
    # Choose the highest-current-power creatures for goldfish combat value.
    feast_count = len(state.cards_in_play("Heroic Feast"))
    for _ in range(feast_count):
        creatures = list(state.creatures())
        if creatures:
            chosen = sorted(creatures, key=lambda p: creature_power(p, state), reverse=True)[:int(amount)]
            for target in chosen:
                target.counters += 1
                record_impact(state, "Heroic Feast", "counters", 1)

    for p in list(state.battlefield):
        low = strip_reminder_text(p.card.oracle_text).lower()
        if "whenever you gain life" not in low:
            continue
        if "each opponent loses 1 life" in low:
            lose_each_opponent(state, 1, p.card.name)
        if "target opponent loses that much life" in low:
            lose_target_opponent(state, amount, p.card.name)
        if "put a +1/+1 counter on this creature" in low:
            p.counters += 1
            record_impact(state, p.card.name, "counters", 1)
    return amount




# ---------------------------------------------------------------------------
# 7) Fairer ramp impact: fetched lands remember which card enabled them.
# ---------------------------------------------------------------------------

def put_basic_from_library(
    state: GameState,
    strategy: Strategy,
    allowed: Set[str],
    tapped: bool = True,
    source: str = "ramp",
) -> bool:
    card = find_basic_for_fetch(state, allowed, strategy)
    if not card:
        return False
    state.library.remove(card)
    perm = Permanent(card=card, entered_turn=state.turn, tapped=tapped)
    setattr(perm, "origin_source", source)
    state.battlefield.append(perm)
    state.log(f"{source}: fetched {card.name} {'tapped' if tapped else 'untapped'}")
    return True


_ORIGINAL_apply_payment_v440 = apply_payment
def apply_payment(state: GameState, plan: PaymentPlan, strategy: Optional[Strategy] = None):
    # Snapshot provenance before tapping mutates state.
    enabled_credit = []
    for src, opt in plan.used:
        if src.permanent_index is None:
            continue
        if 0 <= src.permanent_index < len(state.battlefield):
            p = state.battlefield[src.permanent_index]
            origin = getattr(p, "origin_source", None)
            if origin:
                enabled_credit.append((origin, output_total(opt)))

    _ORIGINAL_apply_payment_v440(state, plan, strategy)

    for origin, amount in enabled_credit:
        record_impact(state, origin, "mana_generated", amount)


# ---------------------------------------------------------------------------
# 8) Focus-aware Bilbo pile / execute opportunity.
# ---------------------------------------------------------------------------

def _focus_bilbo_pile(state: GameState, strategy: ScenarioStrategy, scenario: dict) -> List[str]:
    names = []
    for req in scenario.get("requirements", []):
        if "library" in req.get("zones", []):
            c = next((c for c in state.library if c.name == req["card"] and c.is_creature), None)
            if c:
                names.append(c.name)

    for pkg in scenario.get("packages", []):
        if "library" not in pkg.get("zones", []):
            continue
        ps = scenario_package_status(state, pkg)
        need = max(0, ps.get("needed", 1) - ps.get("matched", 0))
        candidates = [
            m["card"] for m in pkg.get("members", [])
            if any(c.name == m["card"] and c.is_creature for c in state.library)
        ]
        candidates.sort(key=lambda n: (
            strategy.tutor_priority.index(n) if n in strategy.tutor_priority else 999,
            n,
        ))
        names.extend(candidates[:need])

    seen = set()
    focus = [n for n in names if not (n in seen or seen.add(n))]
    return focus + [n for n in strategy.bilbo_pile if n not in seen]


def maybe_execute_focused_win_condition(state: GameState, strategy: ScenarioStrategy) -> bool:
    sc = _focused_scenario(state, strategy)
    if not sc or sc.get("kind") != "Win Condition":
        return False
    st = scenario_status(state, strategy, sc)
    if not st["reached"]:
        return False

    # Generic scenarios remain status measurements. Bilbo has one explicitly modeled
    # executor, so use it before spending the state away.
    bilbo_req = any(
        r.get("card") == BILBO_NAME and "battlefield" in r.get("zones", [])
        for r in sc.get("requirements", [])
    )
    if bilbo_req and state.life >= 111:
        old = list(strategy.bilbo_pile)
        strategy.bilbo_pile = _focus_bilbo_pile(state, strategy, sc)
        try:
            return try_activate_bilbo(state, strategy)
        finally:
            strategy.bilbo_pile = old
    return False


# ---------------------------------------------------------------------------
# v4.4 game simulation
# ---------------------------------------------------------------------------

def _turn_row_v440(
    run_id: int,
    turn: int,
    state: GameState,
    strategy: ScenarioStrategy,
    start_hand: List[str],
    land_name: str,
    casts: List[str],
    mana_before: float,
    structural_access_before: Set[str],
    sc_progress: Dict[str, dict],
) -> dict:
    reactive_held = hold_reactive_count(state, strategy)
    remaining_access = color_access(state, strategy)
    structural_access_after = structural_color_access(state, strategy)
    reached_names = [p["scenario"]["name"] for p in sc_progress.values() if p["first_reached_turn"] is not None]
    focus = _focused_scenario(state, strategy)
    return {
        "run": run_id,
        "turn": turn,
        "start_hand": " | ".join(start_hand),
        "land_played": land_name,
        "casts": " | ".join(casts),
        "events": " || ".join(state.event_log),
        "end_hand": " | ".join(c.name for c in state.hand),
        "hand_size": len(state.hand),
        "lands_in_play": len(state.lands()),
        "mana_available_start_main": mana_before,
        "available_mana_after_actions": available_mana_value(state, strategy),
        "structural_color_access_before_actions": "".join(c for c in COLORS if c in structural_access_before),
        "structural_color_access_after_actions": "".join(c for c in COLORS if c in structural_access_after),
        "remaining_untapped_color_access": "".join(c for c in COLORS if c in remaining_access),
        "has_all_commander_colors_structural": int(bool(strategy.commander_colors) and strategy.commander_colors <= structural_access_after),
        "life": round(state.life, 2),
        "damage_taken": round(state.damage_taken, 2),
        "opponent_life": " | ".join(str(round(x, 2)) for x in state.opponents),
        "virtual_opponent_graveyard": state.virtual_opponent_graveyard,
        "food": state.food,
        "treasure": state.treasure,
        "clues": state.clues,
        "reactive_cards_held": reactive_held,
        "life_events_this_turn": state.life_events_this_turn,
        "life_gained_this_turn": round(state.life_gained_this_turn_amount, 2),
        "scenario_focus": focus["name"] if focus else "",
        "scenario_focus_feasibility": round(float(getattr(state, "scenario_focus_feasibility", 0.0)), 3),
        "scenario_focus_strength": round(float(getattr(state, "scenario_focus_strength", 0.0)), 3),
        "scenarios_reached_so_far": " | ".join(reached_names),
        "bilbo_activated": int(state.bilbo_activation_turn == turn),
        "win": int(state.win_turn == turn),
        "loss": int(state.lost_turn == turn),
    }


def simulate_game_v440(
    deck: List[Card],
    strategy_template: ScenarioStrategy,
    cfg: SimConfig,
    policy: MulliganPolicy,
    rng: random.Random,
    run_id: int,
):
    commanders = [c for c in deck if c.commander]
    library = deck[:]
    for commander in commanders:
        if commander in library:
            library.remove(commander)

    hand, rest, mulligans, mull_history = london_mulligan(library, policy, cfg, rng)
    rng.shuffle(rest)

    strategy = replace(
        strategy_template,
        scenarios=[normalize_scenario(x, i) for i, x in enumerate(strategy_template.scenarios)],
    )
    if commanders and not strategy.commander_colors:
        strategy.commander_colors = set().union(*(c.color_identity for c in commanders))

    state = GameState(library=rest, hand=hand[:], command_zone=commanders[:], life=cfg.starting_life)
    state.abort_on_win = True
    state.scenario_reached_names = set()
    state.scenario_focus_id = None
    state.scenario_focus_counts = Counter()
    state.played_turns = 0

    for c in hand:
        mark_seen(state, c)
    for c in commanders:
        mark_seen(state, c)

    opening_hand = [c.name for c in hand]
    turn_rows = []
    sc_progress = init_scenario_progress(strategy)
    state.turn = 0
    update_scenario_progress(state, strategy, sc_progress, "opening")

    for turn in range(1, cfg.turns + 1):
        state.turn = turn
        state.played_turns += 1
        state.nontoken_creatures_entered_this_turn = 0
        state.gained_life_this_turn = False
        state.life_gained_this_turn_amount = 0.0
        state.baron_triggered_this_turn = False
        state.life_events_this_turn = 0
        state.well_caps_this_turn = []
        state.trudge_garden_triggers_this_turn = 0
        state.frying_pan_bonus_this_turn = 0.0
        state.event_log = []

        start_hand, land_name, casts = [], "", []
        mana_before = 0.0
        structural_access_before: Set[str] = set()

        try:
            untap_step(state)
            update_scenario_progress(state, strategy, sc_progress, "untap")

            # v4.23.0: Mycoloth's "at the beginning of your upkeep" trigger -
            # between untap and draw, matching real turn structure.
            mycoloth_upkeep_trigger(state, strategy)

            state.virtual_opponent_graveyard = max(
                state.virtual_opponent_graveyard,
                max(0, int(turn * 1.25 - 1)),
            )
            draw_cards(state, 1, draw_step=True, reason="draw step")
            update_scenario_progress(state, strategy, sc_progress, "draw")
            start_hand = [c.name for c in state.hand]

            land = choose_land(state, strategy)
            if land:
                state.hand.remove(land)
                land_name = land.name
                land_enters(state, strategy, land)
            update_scenario_progress(state, strategy, sc_progress, "after land")

            focus = select_adaptive_scenario_focus(state, strategy, rng)
            if focus:
                state.scenario_focus_counts[focus["id"]] += 1

            structural_access_before = structural_color_access(state, strategy)
            mana_before = available_mana_value(state, strategy)

            # A setup may already be executable at untap/draw/land. Give it first chance.
            update_scenario_progress(state, strategy, sc_progress, "focus selected")
            maybe_execute_focused_win_condition(state, strategy)

            casts.extend(_cast_early_ramp_before_commander(state, strategy))
            update_scenario_progress(state, strategy, sc_progress, "after early ramp")
            maybe_execute_focused_win_condition(state, strategy)

            if strategy.commander_priority == "high" and turn >= 3:
                commander_name = cast_one_commander_v41(state, strategy)
                if commander_name:
                    casts.append(f"Commander:{commander_name}")
                update_scenario_progress(state, strategy, sc_progress, "after commander")
                maybe_execute_focused_win_condition(state, strategy)

            arken = next((c for c in state.hand if c.name == "The Arkenstone"), None)
            if arken and not scenario_requires_hand_only(strategy, arken.name) and try_cast_arkenstone_adventure(state, strategy, arken):
                record_impact(state, "The Arkenstone", "cast", 1)
                record_impact(state, "The Arkenstone", "mana_spent", 3)
                casts.append("Seek the Heart")

            casts.extend(_play_proactive_cards_v41(state, strategy, min_score=0.0, limit=20))
            if try_cast_adventure_permanent_from_exile(state, strategy):
                record_impact(state, "The Arkenstone", "cast", 1)
                record_impact(state, "The Arkenstone", "mana_spent", 5)
                casts.append("The Arkenstone(from exile)")

            if strategy.commander_priority != "high":
                commander_name = cast_one_commander_v41(state, strategy)
                if commander_name:
                    casts.append(f"Commander:{commander_name}")

            update_scenario_progress(state, strategy, sc_progress, "end main 1")
            maybe_execute_focused_win_condition(state, strategy)

            # Simple sorcery-speed engine activations that materially affect the board.
            use_speaker_of_the_heavens(state, strategy)
            activate_planeswalker_loyalty_abilities(state, strategy)

            # Resource use can matter for combat thresholds (Doctor/Bogbeast), but is narrow.
            maybe_use_food_before_combat(state, strategy)
            equipment_model.auto_equip_step(sys.modules[__name__], state, strategy)
            update_scenario_progress(state, strategy, sc_progress, "precombat resources")
            maybe_execute_focused_win_condition(state, strategy)

            # Bilbo remains allowed as a general deck plan when no focused state is ready.
            try_activate_bilbo(state, strategy)
            update_scenario_progress(state, strategy, sc_progress, "after special activation")

            attack_phase(state, strategy, rng)

            update_scenario_progress(state, strategy, sc_progress, "after combat")

            casts.extend(_play_proactive_cards_v41(state, strategy, min_score=1.0, limit=10))
            try_activate_bilbo(state, strategy)
            update_scenario_progress(state, strategy, sc_progress, "end main 2")

            # v4.22.0: Flashback, then Cycling - spend whatever mana the two
            # casting passes above left untapped, after everything else
            # this turn was already decided. Flashback first: a real spell
            # recast is preferred over cycling when both draw from the same
            # leftover mana.
            maybe_flashback_cards(state, strategy)
            maybe_cycle_cards(state, strategy)

            # v4.23.0: Ribtruss Roaster's and Zimone, All-Questioning's own
            # "at the beginning of your end step" triggers.
            ribtruss_roaster_end_step_trigger(state, strategy)
            zimone_all_questioning_end_step_trigger(state, strategy)

            end_step(state, strategy)
            update_scenario_progress(state, strategy, sc_progress, "end step")
            maybe_execute_focused_win_condition(state, strategy)
            try_activate_bilbo(state, strategy)

            for p in state.battlefield:
                if not p.card.is_land:
                    record_impact(state, p.card.name, "board_turns", 1)

            apply_abstract_opponent_phase(state, strategy, rng)
            update_scenario_progress(state, strategy, sc_progress, "after opponent stress")

        except GoldfishWinReached:
            # Intentional fast exit: preserve the exact state at lethal and do no more work.
            try:
                update_scenario_progress(state, strategy, sc_progress, "win")
            except Exception:
                pass

        # Snapshot exactly once for this played turn.
        state.reactive_held_total += hold_reactive_count(state, strategy)
        turn_rows.append(
            _turn_row_v440(
                run_id, turn, state, strategy, start_hand, land_name, casts,
                mana_before, structural_access_before, sc_progress,
            )
        )

        if state.win_turn is not None or state.lost_turn is not None:
            break

    run_row = {
        "run": run_id,
        "mulligans": mulligans,
        "opening_hand": " | ".join(opening_hand),
        "opening_land_count": sum(c.is_land for c in hand),
        "opening_cheap_spells": sum((not c.is_land) and c.min_cost <= 3 for c in hand),
        "opening_early_ramp": sum("ramp" in c.roles and c.min_cost <= 3 for c in hand),
        "lands_end": len(state.lands()),
        "hand_size_end": len(state.hand),
        "life_end": round(state.life, 2),
        "damage_taken": round(state.damage_taken, 2),
        "food_end": state.food,
        "treasure_end": state.treasure,
        "cards_drawn_total": state.cards_drawn_total,
        "scry_count": state.scry_count,
        "surveil_count": state.surveil_count,
        "connive_count": state.connive_count,
        "bilbo_activation_turn": state.bilbo_activation_turn or "",
        "win_turn": state.win_turn or "",
        "loss_turn": state.lost_turn or "",
        "opponents_remaining": sum(x > 0 for x in state.opponents),
        "life_50_turn": state.milestones[50] or "",
        "life_60_turn": state.milestones[60] or "",
        "life_80_turn": state.milestones[80] or "",
        "life_100_turn": state.milestones[100] or "",
        "life_111_turn": state.milestones[111] or "",
        "reactive_held_total_turn_snapshots": state.reactive_held_total,
    }
    opening_row = {
        "run": run_id,
        "mulligans": mulligans,
        "opening_hand": " | ".join(opening_hand),
        "mulligan_history": " || ".join(mull_history),
    }
    return run_row, turn_rows, opening_row, state.impact, scenario_run_rows(run_id, sc_progress, state)


# ---------------------------------------------------------------------------
# 9) Streaming aggregation + sampled detailed turn logs.
# ---------------------------------------------------------------------------

class LazyCSVWriter:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.fh = None
        self.writer = None

    def write(self, row: dict):
        if self.writer is None:
            self.fh = self.path.open("w", newline="", encoding="utf-8")
            self.writer = csv.DictWriter(self.fh, fieldnames=list(row.keys()))
            self.writer.writeheader()
        self.writer.writerow(row)

    def close(self):
        if self.fh:
            self.fh.close()
            self.fh = None


@dataclass
class StreamingStatsV440:
    runs: int
    turns: int
    run_count: int = 0
    sums: Counter = field(default_factory=Counter)
    milestone_counts: Counter = field(default_factory=Counter)
    win_turns: List[float] = field(default_factory=list)
    loss_turns: List[float] = field(default_factory=list)
    bilbo_turns: List[float] = field(default_factory=list)
    turn_stats: Dict[int, Counter] = field(default_factory=lambda: _defaultdict(Counter))
    scenario_stats: Dict[str, dict] = field(default_factory=dict)

    def add(self, rr: dict, tr: List[dict], sr: List[dict]):
        self.run_count += 1
        for key in (
            "mulligans", "opening_land_count", "opening_early_ramp",
            "hand_size_end", "life_end", "cards_drawn_total",
            "scry_count", "surveil_count", "connive_count",
        ):
            self.sums[key] += float(rr.get(key, 0) or 0)

        for field_name, bucket in (
            ("win_turn", self.win_turns),
            ("loss_turn", self.loss_turns),
            ("bilbo_activation_turn", self.bilbo_turns),
        ):
            val = rr.get(field_name)
            if str(val).strip():
                bucket.append(float(val))

        for m in (50, 60, 80, 100, 111):
            if str(rr.get(f"life_{m}_turn", "")).strip():
                self.milestone_counts[m] += 1

        for row in tr:
            t = int(row["turn"])
            a = self.turn_stats[t]
            a["count"] += 1
            for k in ("hand_size", "life", "lands_in_play", "food", "mana_available_start_main",
                      "has_all_commander_colors_structural", "win", "loss", "bilbo_activated"):
                a[k] += float(row.get(k, 0) or 0)

        for row in sr:
            sid = row["scenario_id"]
            a = self.scenario_stats.setdefault(sid, {
                "name": row["scenario_name"],
                "kind": row["kind"],
                "steer_candidate": bool(row.get("steer_candidate", 0)),
                "reached_turns": [],
                "nonmana_turns": [],
                "focus_turns": 0,
                "bottlenecks": Counter(),
            })
            a["focus_turns"] += int(row.get("focused_turns", 0) or 0)
            if str(row.get("first_reached_turn", "")).strip():
                a["reached_turns"].append(int(row["first_reached_turn"]))
            if str(row.get("first_cards_thresholds_turn", "")).strip():
                a["nonmana_turns"].append(int(row["first_cards_thresholds_turn"]))
            if not int(row.get("reached", 0) or 0):
                for reason in str(row.get("diagnostic_bottlenecks", "")).split(" | "):
                    if reason:
                        key = re.sub(r"\d+(?:\.\d+)?/\d+", "current/target", reason)
                        a["bottlenecks"][key] += 1


def _streaming_scenario_summary(stats: StreamingStatsV440, scenarios: Sequence[dict]) -> List[dict]:
    out = []
    by_id = {s["id"]: s for s in scenarios if s.get("enabled", True)}
    for sid, sc in by_id.items():
        a = stats.scenario_stats.get(sid, {
            "reached_turns": [], "nonmana_turns": [], "focus_turns": 0, "bottlenecks": Counter()
        })
        reached = a["reached_turns"]
        nonmana = a["nonmana_turns"]
        cumulative = {
            str(t): round(100 * sum(x <= t for x in reached) / max(1, stats.runs), 3)
            for t in range(0, stats.turns + 1)
        }
        out.append({
            "id": sid,
            "name": sc["name"],
            "kind": sc["kind"],
            "steer_candidate": bool(sc.get("steer", True)),
            "focused_turns_total": int(a.get("focus_turns", 0)),
            "reach_pct": round(100 * len(reached) / max(1, stats.runs), 3),
            "median_reached_turn": percentile([float(x) for x in reached], .5) if reached else None,
            "p25_reached_turn": percentile([float(x) for x in reached], .25) if reached else None,
            "p75_reached_turn": percentile([float(x) for x in reached], .75) if reached else None,
            "cards_thresholds_reached_pct": round(100 * len(nonmana) / max(1, stats.runs), 3),
            "cumulative_reach_by_turn_pct": cumulative,
            "top_diagnostic_bottlenecks": a.get("bottlenecks", Counter()).most_common(8),
        })
    return out


def streaming_summary_v440(
    deck: List[Card],
    stats: StreamingStatsV440,
    cfg: SimConfig,
    strategy: ScenarioStrategy,
    impact_rows: List[dict],
    detailed_runs_logged: int,
    log_policy: str,
) -> dict:
    commanders = [c.name for c in deck if c.commander]
    lands = sum(c.is_land for c in deck)
    roles = Counter(role for c in deck for role in c.roles)
    keywords = Counter(kw for c in deck for kw in c.keywords)
    pips, curve = Counter(), Counter()
    for c in deck:
        if not c.is_land:
            curve[int(math.ceil(c.mana_value))] += 1
            pips.update(c.color_requirements)

    by_turn = {}
    for t in range(1, cfg.turns + 1):
        a = stats.turn_stats.get(t)
        if not a or not a["count"]:
            continue
        n = a["count"]
        by_turn[str(t)] = {
            "games_still_active_or_finishing_this_turn": int(n),
            "avg_hand_size": a["hand_size"] / n,
            "avg_life": a["life"] / n,
            "avg_lands": a["lands_in_play"] / n,
            "all_commander_colors_structural_pct": 100 * a["has_all_commander_colors_structural"] / n,
            "avg_food": a["food"] / n,
            "avg_mana_start_main": a["mana_available_start_main"] / n,
            "win_pct_this_turn_of_rows": 100 * a["win"] / n,
            "loss_pct_this_turn_of_rows": 100 * a["loss"] / n,
            "bilbo_activation_pct_this_turn_of_rows": 100 * a["bilbo_activated"] / n,
        }

    highlights = [
        {
            "name": r["Name"],
            "tier": r["Relative highlight tier"],
            "value_per_seen": r["Estimated value / seen"],
            "synergy_value_per_seen": r["Synergy value / seen"],
        }
        for r in impact_rows if r["Relative highlight tier"] in {"S", "A"}
    ][:15]

    n = max(1, stats.run_count)
    return {
        "version": V440_VERSION,
        "simulation": {
            "runs": cfg.runs,
            "turns": cfg.turns,
            "seed": cfg.seed,
            "opponent_profile": strategy.opponent_profile,
            "strategy_tags": sorted(strategy.archetypes),
            "scenario_count": len([s for s in strategy.scenarios if s.get("enabled", True)]),
            "scenario_steering": "adaptive single-focus probabilistic steering; all scenarios still observed",
            "detailed_turn_log_policy": log_policy,
            "detailed_runs_logged": detailed_runs_logged,
        },
        "deck": {
            "cards": len(deck),
            "commanders": commanders,
            "lands": lands,
            "curve": dict(sorted(curve.items())),
            "colored_pips": dict(pips),
            "role_counts": dict(roles),
            "keyword_counts": dict(keywords),
        },
        "opening": {
            "avg_mulligans": stats.sums["mulligans"] / n,
            "avg_opening_lands": stats.sums["opening_land_count"] / n,
            "avg_opening_early_ramp": stats.sums["opening_early_ramp"] / n,
        },
        "outcomes": {
            "win_by_turn_limit_pct": 100 * len(stats.win_turns) / n,
            "loss_by_turn_limit_pct": 100 * len(stats.loss_turns) / n,
            "median_win_turn_when_winning": percentile(stats.win_turns, .5) if stats.win_turns else None,
            "median_loss_turn_when_losing": percentile(stats.loss_turns, .5) if stats.loss_turns else None,
            "bilbo_activation_pct": 100 * len(stats.bilbo_turns) / n,
            "median_bilbo_activation_turn": percentile(stats.bilbo_turns, .5) if stats.bilbo_turns else None,
            "reach_50_life_pct": 100 * stats.milestone_counts[50] / n,
            "reach_60_life_pct": 100 * stats.milestone_counts[60] / n,
            "reach_80_life_pct": 100 * stats.milestone_counts[80] / n,
            "reach_100_life_pct": 100 * stats.milestone_counts[100] / n,
            "reach_111_life_pct": 100 * stats.milestone_counts[111] / n,
            "avg_end_hand": stats.sums["hand_size_end"] / n,
            "avg_end_life": stats.sums["life_end"] / n,
            "avg_cards_drawn": stats.sums["cards_drawn_total"] / n,
            "avg_scry": stats.sums["scry_count"] / n,
            "avg_surveil": stats.sums["surveil_count"] / n,
            "avg_connive": stats.sums["connive_count"] / n,
        },
        "relative_card_highlights": highlights,
        "scenarios": _streaming_scenario_summary(stats, strategy.scenarios),
        "by_turn": by_turn,
        "value_model_note": (
            "Card value is a heuristic mana-equivalent model. Ramp fetched-land mana is now "
            "credited back to the card that enabled the land, but impact attribution remains partial."
        ),
        "limitations": [
            "This is a deck-building heuristic simulator, not a complete Magic rules engine.",
            "Mechanics are NOT guaranteed to be interpreted completely or played optimally. An AI reviewing the output must compare Oracle text with card_model_coverage.csv and actively look for unmodeled lines that could accelerate or strengthen the deck's real game plan.",
            "Food is modeled as a real {2}, tap, sacrifice resource for 3 life and is used more aggressively for an active lifegain target; nevertheless Food opportunity costs, politics, timing and every card-specific Food conversion are not exhaustively optimized.",
            "Scenario reach means the user-defined state was observed. It does not prove a combo resolves through interaction.",
            "Scenario steering chooses at most one focus per turn probabilistically based on estimated feasibility; other scenarios remain observations.",
            "Pure goldfish has no real blockers/removal/counterspells. Abstract opponent profiles remain coarse stress tests, not matchup win rates.",
            "Card-impact attribution is incomplete for delayed/indirect value even though fetched-land ramp attribution is improved.",
            "X-spell valuation understands supported text patterns only.",
        ],
    }


# ---------------------------------------------------------------------------
# 10) Model-coverage report for AI/human review.
# ---------------------------------------------------------------------------

KNOWN_COVERAGE_NOTES = {
    "Bilbo, Birthday Celebrant": ("partial+", "111 threshold, tap/exile activation and creature batch are modeled; selected pile remains heuristic/scenario-guided."),
    "Doctor Strange, Surgeon": ("strong", "lifegain doubling and 50-life combat buff are modeled."),
    "Honor Troll": ("strong", "lifegain +1 replacement is modeled; other combat text relies on generic keyword parsing."),
    "Peregrin Took": ("strong", "token->extra Food replacement and 3-Food draw are modeled."),
    "Tippy-Toe, Terrific Partner": ("strong", "extra Food replacement and end-step draw after lifegain are modeled."),
    "Mirkwood Bats": ("strong", "token creation/sacrifice drain is modeled."),
    "Kambal, Profiteering Mayor": ("partial", "your-token enter drain/lifegain is modeled; copying opponent tokens is not represented in pure goldfish."),
    "Gyome, Master Chef": ("partial", "end-step Food creation is modeled; the generic semantic-protection engine (Food, Sacrifice a Food: indestructible + tap) exists but is deliberately kept reactive-only, triggered from removal/board-wipe handling - deferred until opponent-turn removal threats are in scope (see try_semantic_board_protection)."),
    "Heroic Feast": ("strong", "ETB Food and lifegain-trigger +1/+1 counter distribution are modeled heuristically."),
    "Field-Tested Frying Pan": ("partial+", "ETB Food/Halfling are modeled; the equipped-creature lifegain pump (+X/+X where X = life gained, until end of turn) is now applied to that Halfling token for as long as both the Pan and the Halfling are in play (v4.15.6). Re-equipping to a different creature is not modeled - goldfish has no reason to move it off its own ETB target."),
    "Trudge Garden": ("partial+", "the card's own repeated per-lifegain-event 'you may pay {2}, create a 4/4 trample Fungus Beast' decision is now resolved once per real lifegain event against actual spare mana at end of step (v4.15.6, use_trudge_garden), not left unmodeled."),
    "Speaker of the Heavens": ("strong", "47-life condition and tap-to-create 4/4 flying vigilance Angel activation are modeled at sorcery-speed main phase."),
    "Baron Bertram Graywater": ("partial+", "token-enter Vampire generation is modeled; the sacrifice-to-draw activated ability now converts a genuinely leftover, unspent Treasure token into a card at end of step (v4.15.6, use_baron_bertram_sac_draw). Sacrificing creatures or Food for it is a real strategic trade-off deliberately left unautomated."),
    "Moldervine Reclamation": ("partial+", "the death trigger (gain 1 life, draw a card) now fires on every creature death this simulator actually tracks - both real Permanent deaths (hooked into the shared move_permanent_to_zone graveyard path) and token-group combat deaths (hooked directly in attack_phase) (v4.15.6). Non-combat removal deaths remain out of scope until opponent-turn interaction is modeled."),
    "Blossoming Bogbeast": ("strong", "attack lifegain and +X/+X using total life gained this turn are modeled heuristically."),
    "Lobelia, Defender of Bag End": ("partial", "artifact-sacrifice drain/lifegain mode is modeled; stolen-card mode is not."),
    "Gilded Goose": ("partial+", "Food ETB and Food-to-mana are modeled; lifegain plans now assign Food-mana a higher opportunity cost."),
    "Unlucky Cabbage Merchant": ("partial+", "Food ETB and Food-sacrifice basic-ramp trigger are modeled approximately."),
    "Well of Lost Dreams": ("partial+", "lifegain-event caps and spare-mana draw are modeled; trigger-by-trigger tactical allocation is simplified."),
    "Old Gnawbone": ("strong", "the Treasure-per-combat-damage trigger now fires for every unblocked attacker (including Old Gnawbone itself), sized by the real per-attacker damage amount already computed for commander-damage/lifelink tracking (v4.18.0)."),
    # v4.65.3: Nutzerauftrag "Bilbo-Drain-Payoff-Coverage ranmachen" - Folgeauftrag
    # zum in v4.65.1 offengelegten Kontextpunkt ("Bilbo's drain-payoff cards sind
    # nur 'generic'-abgedeckt"). Recherche ergab: die Kernmechanik ALLER fuenf
    # Karten ist bereits im gain_life()-Text-Match (App/engine.py, Abschnitt "High-
    # impact Bilbo card fixes") real implementiert - "generic" bedeutete hier NICHT
    # "unsimuliert", sondern nur "keine dieser Eintraege existierte bisher", und der
    # generische Semantik-Parser (_parse_semantic_actions) unterschaetzte Sanguine
    # Bond/Vito zusaetzlich, weil seine "opponent loses N life"-Regex nur feste
    # Zahlen erkennt, nicht "loses THAT MUCH life" (dynamische Menge = gerade
    # gewonnenes Leben) - separat als generischer Parser-Fix behoben (siehe
    # _parse_semantic_actions-Wrapper direkt vor main_v470).
    "Sanguine Bond": ("strong", "der Leben-Verlust-spiegelt-Gewinn-Trigger ('target opponent loses that much life') ist ueber gain_life()s dynamischen Text-Match exakt modelliert (lose_target_opponent mit dem tatsaechlich gewonnenen Betrag) - einzige Faehigkeit der Karte, vollstaendig abgedeckt."),
    "Vito, Thorn of the Dusk Rose": ("strong", "beide Zeilen sind modelliert: derselbe Leben-Verlust-spiegelt-Gewinn-Trigger wie Sanguine Bond (inkl. Lebensgewinn aus der eigenen Lifelink-Aktivierung, da Kampf-Lifelink ebenfalls ueber gain_life() laeuft), sowie die {3}{B}{B}-Team-Lifelink-Aktivierung ueber den generischen Keyword-Grant-Parser."),
    "Corpse Knight": ("strong", "der 'weitere eigene Kreatur betritt -> Gegner verliert 1 Leben'-Trigger ist ueber den generischen Semantik-Parser exakt modelliert (fester Betrag) - einzige Faehigkeit der Karte, vollstaendig abgedeckt."),
    "Marauding Blight-Priest": ("strong", "der 'du gewinnst Leben -> jeder Gegner verliert 1 Leben'-Trigger ist ueber den generischen Semantik-Parser exakt modelliert (fester Betrag, derselbe Mechanismus wie Dina, Soul Steeper) - einzige Faehigkeit der Karte, vollstaendig abgedeckt."),
    "Dina, Soul Steeper": ("partial+", "der 'du gewinnst Leben -> jeder Gegner verliert 1 Leben'-Trigger ist exakt modelliert (derselbe Mechanismus wie Marauding Blight-Priest); die zweite Faehigkeit ('{1}, Opfere eine weitere Kreatur: Dina erhaelt +X/+0', X = Staerke der geopferten Kreatur) bleibt eine echte, offengelegte Luecke - eine bedingte Opfer-Kampftrick-Entscheidung, die die generische Aktivierungs-Heuristik dieser Engine nicht bewertet/ausfuehrt."),
}


def card_model_coverage_rows(deck: List[Card]) -> List[dict]:
    rows = []
    seen = set()
    for c in deck:
        if c.name in seen:
            continue
        seen.add(c.name)
        low = strip_reminder_text(c.oracle_text).lower()

        level, note = KNOWN_COVERAGE_NOTES.get(c.name, ("generic", "Uses generic mana/role/keyword/text-pattern heuristics."))

        review = []
        if ":" in c.oracle_text and not c.is_land:
            review.append("activated ability")
        if "whenever" in low or "at the beginning" in low:
            review.append("triggered ability")
        if "may pay" in low:
            review.append("conditional payment")
        if "copy" in low:
            review.append("copy effect")
        if "equip" in low or "equipped" in low:
            review.append("equipment/attachment")
        if "dies" in low:
            review.append("death trigger")
        if "for each" in low:
            review.append("scaling/for-each")
        if "choose" in low:
            review.append("choice/target selection")
        if "sacrifice" in low:
            review.append("sacrifice/resource conversion")
        if "graveyard" in low:
            review.append("graveyard dependency")

        rows.append({
            "Name": c.name,
            "Coverage": level,
            "Modeled / review note": note,
            "Mechanics requiring AI cross-check": " | ".join(sorted(set(review))),
            "Oracle Text": c.oracle_text,
        })
    return rows


def write_model_review_instructions(path: Path):
    text = """# MODEL COVERAGE / AI REVIEW REQUIREMENT

The goldfish engine is deliberately a deck-building heuristic, not a full Magic rules simulator.

## Mandatory review step
Before recommending cuts/additions or claiming that a deck is slow, an analyzing AI MUST:

1. Read `card_model_coverage.csv`.
2. Compare important cards' Oracle text with what the simulator says it models.
3. Identify abilities/mechanics that are absent, simplified, conditional, or strategically underused.
4. Ask: "Could this omitted potential make the deck reach its game plan earlier, create more cards/mana/life/tokens, or protect the setup better?"
5. Separate:
   - measured simulation result;
   - likely direction of model bias;
   - real-game inference.
6. Do NOT treat a low Card Impact score as evidence that a card is weak when its primary ability is partial/unmodeled.

Examples of commonly underrepresented value:
activated abilities, repeated optional payments, Food conversion choices, Equipment attachment/pump,
death triggers, recursion, opponent-dependent removal/lifegain, copy effects, token multiplication,
cost reductions, combat/block decisions and political multiplayer effects.

For lifegain/Food decks specifically, verify whether Food was spent for life, mana, draw or another
card-specific outlet in a way consistent with the intended plan. The simulator now prioritizes Food
for an active lifegain threshold more intelligently, but it still does not prove optimal resource use.
"""
    Path(path).write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# 11) v4.4 pipeline.
# ---------------------------------------------------------------------------

def apply_voltron_target_override(strategy: "Strategy", voltron_target_index: Optional[int]) -> None:
    """v4.15.7 (task #18, "Voltron-GUI-Feld"): an explicit pipeline/GUI value
    overrides whatever the strategy file set (or leaves the field unset if
    neither the GUI nor the strategy file specifies one). This is additive
    to the pre-existing strategy-file loading path (load_strategy already
    reads "voltron_target_index" out of a strategy JSON) - it just gives
    the GUI a way to set it without hand-authoring a strategy file. Factored
    out of run_pipeline_v440 so it is directly unit-testable without driving
    the full deck-build/simulation pipeline.
    """
    if voltron_target_index is not None:
        strategy.voltron_target_index = voltron_target_index


def apply_advanced_opponent_model_override(
    strategy: "Strategy",
    advanced_opponent_model: Optional[bool],
    advanced_opponent_seats: Optional[Sequence[Dict[str, Any]]],
) -> None:
    """v4.64.0 (GUI-'Gegnerprofil'-Dialog, siehe App/gui.py): dieselbe
    additive Override-Logik wie apply_voltron_target_override direkt
    oberhalb - ein expliziter GUI-/Pipeline-Wert ueberschreibt, was eine
    Strategie-Datei gesetzt hat (oder laesst das Feld unveraendert, wenn
    weder GUI noch Datei etwas vorgeben). Gibt der GUI einen Weg, das
    v4.63.0-Mehrgegner-Zustandsmodell (siehe _apply_advanced_multi_opponent_
    phase weiter unten) zu setzen, ohne eine Strategie-JSON von Hand zu
    schreiben. Factored out fuer direkte Testbarkeit, exakt wie das
    Voltron-Vorbild."""
    if advanced_opponent_model is not None:
        strategy.advanced_opponent_model = bool(advanced_opponent_model)
    if advanced_opponent_seats is not None:
        strategy.advanced_opponent_seats = [dict(seat) for seat in advanced_opponent_seats]


def _detail_log_policy(runs: int) -> Tuple[int, str]:
    if runs <= 500:
        return runs, "full diagnostic logs for every run"
    if runs <= 5000:
        return 250, "first 250 runs + every win/Bilbo activation/scenario reach"
    return 500, "first 500 runs + every win/Bilbo activation/scenario reach"


def run_pipeline_v440(
    deck_file: Path,
    commander_names: Sequence[str],
    *,
    runs: int = 5000,
    turns: int = 10,
    seed: int = 1,
    strategy_file: Optional[Path] = None,
    strategy_tags: Optional[Set[str]] = None,
    opponent_profile: str = "goldfish",
    value_model_file: Optional[Path] = None,
    scenarios: Optional[Sequence[dict]] = None,
    scenarios_file: Optional[Path] = None,
    cache_path: Optional[Path] = None,
    offline: bool = False,
    metadata_csv: Optional[Path] = None,
    output_root: Optional[Path] = None,
    progress_callback=None,
    voltron_target_index: Optional[int] = None,
    advanced_opponent_model: Optional[bool] = None,
    advanced_opponent_seats: Optional[Sequence[Dict[str, Any]]] = None,
):
    deck_file = Path(deck_file)
    vm = ValueModel.load(value_model_file)
    cache_path = cache_path or (Path(__file__).resolve().parent / ".scryfall_card_cache_v4.json")
    deck = build_deck_v4(deck_file, commander_names, cache_path, offline, metadata_csv)
    commander = next((c for c in deck if c.commander), None)

    scenario_list = []
    if scenarios_file:
        scenario_list.extend(load_scenarios(scenarios_file))
    if scenarios:
        scenario_list.extend(normalize_scenario(x, i + len(scenario_list)) for i, x in enumerate(scenarios))
    scenario_list = list({s["id"]: s for s in scenario_list}.values())

    # Build scenario strategy without pre-biasing tutors toward every scenario simultaneously.
    base_strategy = _V4_load_strategy(
        strategy_file,
        commander,
        archetypes=strategy_tags,
        opponent_profile=opponent_profile,
        value_model=vm,
    )
    strategy = ScenarioStrategy(
        **base_strategy.__dict__,
        scenarios=[normalize_scenario(x, i) for i, x in enumerate(scenario_list)],
    )
    if commander_names:
        strategy.commander_colors = set().union(*(c.color_identity for c in deck if c.commander))
    apply_voltron_target_override(strategy, voltron_target_index)
    apply_advanced_opponent_model_override(strategy, advanced_opponent_model, advanced_opponent_seats)

    cfg = SimConfig(runs=runs, turns=turns, seed=seed)
    policy = MulliganPolicy()
    rng = random.Random(seed)

    timestamp = _datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(output_root or (deck_file.parent / "Goldfish_Results"))
    result_dir = root / f"{deck_file.stem}_v4_7_0_{timestamp}"
    result_dir.mkdir(parents=True, exist_ok=True)

    runs_path = result_dir / "runs.csv"
    turns_path = result_dir / "turns.csv"
    openings_path = result_dir / "opening_hands.csv"
    scenario_path = result_dir / "scenario_runs.csv"

    run_writer = LazyCSVWriter(runs_path)
    turn_writer = LazyCSVWriter(turns_path)
    opening_writer = LazyCSVWriter(openings_path)
    scenario_writer = LazyCSVWriter(scenario_path)

    aggregate: Dict[str, Counter] = _defaultdict(Counter)
    stats = StreamingStatsV440(runs=runs, turns=turns)
    base_log_runs, log_policy = _detail_log_policy(runs)
    logged_run_ids = set()

    try:
        for run_id in range(1, runs + 1):
            rr, tr, oh, impact, sr = simulate_game_v440(deck, strategy, cfg, policy, rng, run_id)

            run_writer.write(rr)
            opening_writer.write(oh)
            for row in sr:
                scenario_writer.write(row)

            exceptional = (
                bool(str(rr.get("win_turn", "")).strip())
                or bool(str(rr.get("bilbo_activation_turn", "")).strip())
                or any(int(x.get("reached", 0) or 0) for x in sr)
            )
            if run_id <= base_log_runs or exceptional:
                logged_run_ids.add(run_id)
                for row in tr:
                    turn_writer.write(row)

            stats.add(rr, tr, sr)
            for name, metrics in impact.items():
                aggregate[name].update(metrics)

            if progress_callback and (
                run_id == 1
                or run_id % max(1, runs // 100) == 0
                or run_id == runs
            ):
                progress_callback(run_id, runs)
    finally:
        for writer in (run_writer, turn_writer, opening_writer, scenario_writer):
            writer.close()

    impact_rows = impact_rows_from_aggregate(deck, aggregate, runs, strategy)
    summary_data = streaming_summary_v440(
        deck, stats, cfg, strategy, impact_rows,
        detailed_runs_logged=len(logged_run_ids),
        log_policy=log_policy,
    )
    summary_data["simulation"]["package_count"] = sum(
        len([p for p in s.get("packages", []) if p.get("enabled", True)])
        for s in strategy.scenarios if s.get("enabled", True)
    )

    # Aggregate turn stats are compact and complete even when detailed turns.csv is sampled.
    turn_aggregate_rows = []
    for t in range(1, turns + 1):
        row = summary_data.get("by_turn", {}).get(str(t))
        if row:
            turn_aggregate_rows.append({"turn": t, **row})
    write_csv(result_dir / "turn_aggregates.csv", turn_aggregate_rows)

    write_enriched(result_dir / "deck_enriched.csv", deck)
    write_csv(result_dir / "card_impact.csv", impact_rows)
    write_csv(result_dir / "card_model_coverage.csv", card_model_coverage_rows(deck))
    (result_dir / "summary.json").write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_value_model(result_dir / "value_model.json", vm)
    save_scenarios(result_dir / "combo_scenarios.json", strategy.scenarios)
    (result_dir / "SCENARIO_SCHEMA.md").write_text(scenario_json_schema_markdown(), encoding="utf-8")
    write_model_review_instructions(result_dir / "MODEL_COVERAGE_AND_AI_REVIEW.md")
    _shutil.copy2(deck_file, result_dir / deck_file.name)

    # Existing AI handoff + stronger explicit model-coverage requirement.
    ai_path = result_dir / "AI_ANALYSIS_INSTRUCTIONS.md"
    write_ai_analysis_instructions_v41(ai_path, deck_file, "summary.json", strategy)
    with ai_path.open("a", encoding="utf-8") as fh:
        fh.write("""

## v4.4 mandatory model-bias review
Mechanics are NOT assumed to be optimally or completely interpreted.
Before any deck recommendation, inspect `card_model_coverage.csv` and
`MODEL_COVERAGE_AND_AI_REVIEW.md`. Explicitly report important unmodeled/partial abilities
that could make the real game plan faster or stronger than the simulation shows.

In particular, do not infer "card is weak" from low modeled impact when its real value
comes from an activated ability, optional payment, Food conversion, death trigger,
equipment attachment, recursion, copy effect, cost reduction, opponent-dependent trigger,
or another mechanic marked partial/generic.

`turns.csv` may intentionally contain only sampled/exceptional detailed runs.
Use `turn_aggregates.csv` and `summary.json` for population-wide turn statistics.
""")

    config = {
        "version": V440_VERSION,
        "deck_file": deck_file.name,
        "commanders": list(commander_names),
        "runs": runs,
        "turns": turns,
        "seed": seed,
        "strategy_tags": sorted(strategy.archetypes),
        "opponent_profile": strategy.opponent_profile,
        "scenario_count": len(strategy.scenarios),
        "scenario_steering": "adaptive probabilistic single focus",
        "turn_log_policy": log_policy,
        "detailed_runs_logged": len(logged_run_ids),
        "parallel_execution": False,
    }
    # v4.65.1: opponent_profile oben bleibt bewusst die simple Dropdown-
    # Auswahl (Abwaertskompatibilitaet) - ist aber bei aktivem "Gegnerprofil"-
    # Dialog (advanced_opponent_model) irrefuehrend, da dann tatsaechlich
    # eigene, echten Schaden austeilende Sitzplaetze simuliert werden statt
    # dieses einen Profils. Siehe Docs/README.md v4.65.1 fuer die volle
    # Herleitung (gefunden durch kritische Durchsicht zweier echter Nutzer-
    # Runs). summary_data["simulation"] traegt diese Felder bereits aus dem
    # additiven streaming_summary_v440-Wrapper weiter unten im Modul.
    sim_meta = summary_data.get("simulation", {})
    if sim_meta.get("advanced_opponent_model"):
        config["advanced_opponent_model"] = True
        config["advanced_opponent_seat_specs"] = sim_meta.get("advanced_opponent_seat_specs", [])
        config["advanced_opponent_actual_seat_summary"] = sim_meta.get(
            "advanced_opponent_actual_seat_summary", []
        )
        config["advanced_opponent_label"] = sim_meta.get("advanced_opponent_label", "")
    (result_dir / "simulation_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if strategy_file and Path(strategy_file).exists():
        _shutil.copy2(strategy_file, result_dir / Path(strategy_file).name)

    zip_path = result_dir.with_suffix(".zip")
    with _zipfile.ZipFile(zip_path, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
        for f in result_dir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(result_dir))

    return {
        "result_dir": result_dir,
        "zip_path": zip_path,
        "summary": summary_data,
        "deck": deck,
        "strategy": strategy,
        "impact_rows": impact_rows,
    }


# Keep portable project behavior, but route simulations to v4.4.
def run_pipeline_v43(*args, **kwargs):
    return run_pipeline_v440(*args, **kwargs)


def main_v440():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.4.0")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_4_0_gui import launch_gui
        launch_gui()
        return

    ensure_runtime_dependencies(include_images=False, status_callback=print)

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v440(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.4.0 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




# ===========================================================================
# v4.4.1 — NO REQUIRED PIP DEPENDENCIES FOR SCRYFALL
# ===========================================================================
#
# The v4.3.1-v4.4.0 bootstrap made Scryfall depend on `requests`. That created a
# real Windows problem when `pip` on PATH belonged to a different Python
# installation than `sys.executable`.
#
# v4.4.1 removes that architectural dependency:
#   * Scryfall metadata uses Python's standard-library urllib.
#   * No `requests` installation is required.
#   * Pillow is optional only; core simulation and Scryfall metadata do not
#     depend on it.
# ===========================================================================


def ensure_runtime_dependencies(include_images: bool = True, status_callback=None) -> dict:
    """
    v4.4.1 has NO required third-party dependency for Scryfall/core simulation.

    Pillow remains optional. The GUI can use Tk's native PNG support for card
    images and falls back to text for table mana-cost rendering when Pillow is
    unavailable.
    """
    report = {
        "required": [],
        "already_present": [],
        "optional_unavailable": [],
    }

    if status_callback:
        status_callback("Scryfall: Standardbibliothek aktiv – keine pip-Installation nötig.")

    if include_images:
        if _dependency_importable("PIL"):
            report["already_present"].append("Pillow")
            if status_callback:
                status_callback("Pillow: vorhanden; erweitertes Bild-/Mana-Rendering aktiv.")
        else:
            report["optional_unavailable"].append("Pillow")
            if status_callback:
                status_callback(
                    "Pillow nicht vorhanden – kein Problem: Kartenbilder nutzen Tk-PNG-Fallback; "
                    "Mana-Tabelle nutzt Text-Fallback."
                )
    return report


def _scryfall_fuzzy_lookup_stdlib_urllib(name: str) -> Optional[dict]:
    import urllib.parse
    import urllib.request as _ur
    url = "https://api.scryfall.com/cards/named?" + urllib.parse.urlencode({"fuzzy": name})
    req = _ur.Request(url, headers={
        "User-Agent": "CommanderGoldfishSimulator/4.4.1 (personal deck analysis)",
        "Accept": "application/json",
    })
    try:
        with _ur.urlopen(req, timeout=30) as response:
            obj = json.loads(response.read().decode("utf-8"))
    except Exception:
        obj = None
    time.sleep(0.1)
    return obj


def _scryfall_get_many_urllib(self, entries: List[DeckEntry]) -> Dict[str, dict]:
    """
    Scryfall collection lookup using only Python stdlib urllib.

    This deliberately avoids `requests`, `pip`, and interpreter-environment
    mismatches on Windows. THIS is the get_many() implementation that is
    actually live at runtime (see the module-level assignment right below
    this function, and ScryfallProvider._resolve_missing()'s docstring for
    why that matters): it is the last of two competing monkey-patches of
    ScryfallProvider.get_many, so whichever one is assigned last always
    wins, unconditionally, regardless of which HTTP backend is installed.

    v4.17.0: delegates to ScryfallProvider._resolve_missing() instead of
    carrying its own full copy of the batch-fetch/error logic - that
    duplication is exactly how the v4.16.0 double-faced-card indexing fix
    (applied only to the OTHER, non-live get_many() body at the time) never
    actually took effect for a real user run.
    """
    import urllib.error
    import urllib.request

    result, missing = self._split_cache(entries)

    if missing and self.offline:
        raise RuntimeError(
            f"{len(missing)} Karten fehlen im lokalen Scryfall-Cache. "
            f"Einmal mit Internetzugang starten."
        )

    def post_json(url, body):
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "User-Agent": "CommanderGoldfishSimulator/4.4.1 (personal deck analysis)",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise RuntimeError(
                f"Scryfall HTTP {exc.code}. "
                f"Antwort: {detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Scryfall ist nicht erreichbar. Prüfe Internetzugang, Firewall, Proxy oder VPN. "
                f"Technischer Fehler: {exc.reason}"
            ) from exc

    result.update(self._resolve_missing(missing, post_json, _scryfall_fuzzy_lookup_stdlib_urllib))
    return result


# Override the requests-backed method from older embedded versions. This is
# the LAST assignment to ScryfallProvider.get_many at module load time, so
# _scryfall_get_many_urllib above is the one actually live at runtime -
# see its docstring and the v4.17.0 README entry.
ScryfallProvider.get_many = _scryfall_get_many_urllib


def main_v441():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.4.1")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_4_1_gui import launch_gui
        launch_gui()
        return

    ensure_runtime_dependencies(include_images=False, status_callback=print)

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v440(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.4.1 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




def main_v442():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.4.2")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()
    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_4_2_gui import launch_gui
        launch_gui(); return
    ensure_runtime_dependencies(include_images=False, status_callback=print)
    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")
    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v440(args.deck_file, commander_names, runs=args.runs, turns=args.turns, seed=args.seed,
        strategy_file=args.strategy, strategy_tags=tags or None, opponent_profile=args.opponent,
        value_model_file=args.value_model, scenarios_file=args.scenarios, cache_path=args.cache,
        offline=args.offline, metadata_csv=args.metadata_csv, output_root=args.output_root)
    print("\\nGoldfish v4.4.2 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])



def main_v443():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.4.3")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_4_3_gui import launch_gui
        launch_gui()
        return

    ensure_runtime_dependencies(include_images=False, status_callback=print)

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v440(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\\nGoldfish v4.4.3 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




def main_v444():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.4.4")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_4_4_gui import launch_gui
        launch_gui()
        return

    ensure_runtime_dependencies(include_images=False, status_callback=print)

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v440(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.4.4 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




# ===========================================================================
# v4.5.0 — COMMANDER ZONES + GENERIC ORACLE SEMANTICS
# ===========================================================================

SEMANTIC_RUNTIME_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Oracle -> simplified ability model
# ---------------------------------------------------------------------------

@dataclass
class SemanticAction:
    kind: str
    amount: float = 0.0
    keyword: str = ""
    token: str = ""
    target: str = ""
    raw: str = ""


@dataclass
class SemanticAbility:
    source: str
    raw: str
    ability_kind: str                 # activated / triggered / static / replacement
    trigger: str = ""
    mana_total: int = 0
    mana_requirements: Counter = field(default_factory=Counter)
    tap_source: bool = False
    sacrifice_resource: str = ""
    remove_source_counter: str = ""
    another_target_only: bool = False
    actions: List[SemanticAction] = field(default_factory=list)
    execution_mode: str = "review"    # exact / simplified / probabilistic / review
    confidence: float = 0.0
    unrecognized_sacrifice_cost: bool = False
    discard_count: int = 0             # v4.26.0: "Discard a/N card(s)" as part of an activation cost


def _split_activation_cost_effect(line: str) -> Tuple[str, str]:
    if ":" not in line:
        return "", line
    left, right = line.split(":", 1)
    return left.strip(), right.strip()


def _activation_mana(cost_text: str) -> Tuple[int, Counter]:
    symbols = re.findall(r"\{([^}]+)\}", cost_text or "")
    keep = []
    for sym in symbols:
        up = sym.upper()
        if up in {"T", "Q"}:
            continue
        # parse_mana_cost already understands digits/colors/hybrid conservatively.
        keep.append("{" + sym + "}")
    return parse_mana_cost("".join(keep))


def _semantic_trigger(low: str) -> str:
    if low.startswith(("when ", "whenever ")):
        if "you gain life" in low:
            return "life_gain"
        if "enters" in low:
            if "another creature" in low:
                return "another_creature_enters"
            if "creature" in low:
                return "creature_enters"
            if "token" in low:
                return "token_enters"
            return "enters"
        if "dies" in low:
            return "dies"
        if "attacks" in low:
            return "attacks"
        if "becomes tapped" in low:
            return "becomes_tapped"
        if "sacrifice" in low or "sacrificed" in low:
            return "sacrifice"
        return "triggered_other"
    if low.startswith("at the beginning"):
        if "end step" in low:
            return "end_step"
        if "combat" in low:
            return "begin_combat"
        if "upkeep" in low:
            return "upkeep"
        return "begin_step"
    return ""


def _parse_semantic_actions(effect: str) -> List[SemanticAction]:
    low = strip_reminder_text(effect).lower()
    actions: List[SemanticAction] = []

    # v4.19.0: extended "five" -> "ten" (NUMBER_WORDS already goes to ten -
    # parse_number_token could always handle "seven", these regexes just
    # never matched far enough to hand it one). Found via Ugin's real "-10:
    # You gain 7 life, draw seven cards, ..." during the planeswalker work:
    # the life half parsed, "draw seven cards" silently didn't. Strictly
    # more permissive than before - nothing that matched here previously
    # stops matching - so this is a pure coverage improvement, not scoped to
    # planeswalkers.
    _NUM_WORDS_RE = "a|one|two|three|four|five|six|seven|eight|nine|ten"

    for action_name in ("scry", "surveil", "connive"):
        m = re.search(rf"\b{action_name}\s+({_NUM_WORDS_RE}|\d+)", low)
        if m:
            actions.append(SemanticAction(
                kind=action_name,
                amount=parse_number_token(m.group(1)),
                raw=effect,
            ))

    m = re.search(rf"\bdraw ({_NUM_WORDS_RE}|\d+) cards?", low)
    if m:
        actions.append(SemanticAction(
            kind="draw",
            amount=parse_number_token(m.group(1)),
            raw=effect,
        ))

    m = re.search(rf"\byou gain ({_NUM_WORDS_RE}|\d+) life", low)
    if m:
        actions.append(SemanticAction(
            kind="gain_life",
            amount=parse_number_token(m.group(1)),
            raw=effect,
        ))

    m = re.search(rf"\b(each opponent|target opponent) loses ({_NUM_WORDS_RE}|\d+) life", low)
    if m:
        actions.append(SemanticAction(
            kind="opponent_life_loss",
            amount=parse_number_token(m.group(2)),
            target=m.group(1),
            raw=effect,
        ))

    m = re.search(rf"create ({_NUM_WORDS_RE}|\d+) ([a-z0-9 +'/\-]+?) tokens?\b", low)
    if m:
        token_name = m.group(2).strip().title()
        actions.append(SemanticAction(
            kind="create_token",
            amount=parse_number_token(m.group(1)),
            token=token_name,
            raw=effect,
        ))

    # Keyword grants / counters.
    for kw in KNOWN_KEYWORDS | {"lifelink", "indestructible"}:
        if re.search(rf"\b(?:target|that|another target) creature gains {re.escape(kw)} until end of turn\b", low):
            actions.append(SemanticAction(
                kind="grant_keyword_until_eot",
                keyword=kw,
                target="target_creature",
                raw=effect,
            ))
        if re.search(rf"\ba {re.escape(kw)} counter\b", low):
            actions.append(SemanticAction(
                kind="keyword_counter",
                keyword=kw,
                target="mentioned_creatures",
                raw=effect,
            ))

    # +1/+1 counters. v4.30.0 fix (found via ChatGPT external review,
    # Docs/README.md v4.30.0 entry): the old code counted how many times the
    # literal substring "+1/+1 counter" appeared in the text as a proxy for
    # the total amount - that only "worked" by coincidence for "a +1/+1
    # counter" (exactly one substring match) and silently undercounted
    # "Put three +1/+1 counters on target creature." to 1 instead of 3,
    # since it never actually read the stated number word/digit. Sum every
    # "<N> +1/+1 counter(s)" clause found (a card can have more than one,
    # e.g. two separate targets each getting their own).
    counter_matches = re.findall(
        rf"\b({_NUM_WORDS_RE}|\d+)\s+\+1/\+1 counters?\b", low,
    )
    if counter_matches:
        actions.append(SemanticAction(
            kind="plus1_counter",
            amount=sum(parse_number_token(x) for x in counter_matches),
            target="mentioned_creatures",
            raw=effect,
        ))
    elif "+1/+1 counter" in low:
        # Doesn't match "<number> +1/+1 counter(s)" (e.g. "counters equal to
        # ..." or other unusual phrasing this parser doesn't attempt to
        # quantify) - fall back to the historical "assume 1" default rather
        # than guessing at a number that isn't actually stated.
        actions.append(SemanticAction(
            kind="plus1_counter",
            amount=1,
            target="mentioned_creatures",
            raw=effect,
        ))

    if re.search(r"\btap it\b", low):
        actions.append(SemanticAction(kind="tap_target", target="target_creature", raw=effect))

    # Common base P/T setters (useful foundation for Waterbend-like board effects).
    m = re.search(
        r"base power and toughness (?:becomes?|are|is) (\d+)\s*/\s*(\d+)",
        low,
    )
    if m:
        actions.append(SemanticAction(
            kind="set_base_pt",
            amount=float(m.group(1)),
            target=f"{m.group(1)}/{m.group(2)}",
            raw=effect,
        ))

    return actions


def parse_oracle_semantics(card: Card) -> List[SemanticAbility]:
    abilities: List[SemanticAbility] = []

    for raw_line in split_oracle_lines(card.oracle_text):
        line = strip_reminder_text(raw_line).strip()
        low = line.lower()
        if not low:
            continue

        # v4.25.0: a planeswalker's loyalty-ability lines ("+1: ...",
        # "-3: ...", "0: ...") must NEVER become a generic "activated"
        # SemanticAbility here. They contain a colon, so without this guard
        # the block below classifies them as an ordinary activated ability
        # with cost_text="+1"/"-3" - _activation_mana() finds no {mana}
        # symbols in that, so mana_total/mana_req/tap_source/sacrifice_resource
        # all come back empty/False, and the ability was STILL treated as
        # having a "recognized" (i.e. free) cost. try_generic_semantic_activations
        # (called from end_step) does not check execution_mode and has no
        # per-card loyalty exclusion (only DEDICATED_RESOLVERS, a small
        # hardcoded name list), so it happily executed these for free -
        # completely bypassing the real, correct, once-per-turn loyalty
        # resolver (activate_planeswalker_loyalty_abilities /
        # parse_loyalty_abilities, which uses this exact same
        # _LOYALTY_ABILITY_RE) and never touching p.loyalty at all. Found via
        # ChatGPT external review (Docs/README.md v4.25.0 entry) - reproduced
        # on the live code before this fix: an ordinary "+1: Draw a card."
        # planeswalker got a second, completely free draw every end step, on
        # top of its correct once-per-turn loyalty activation.
        if card.is_planeswalker and (
            _LOYALTY_ABILITY_RE.match(line) or low.startswith("0:")
        ):
            continue

        ability_kind = "static"
        trigger = _semantic_trigger(low)
        cost_text = ""
        effect_text = line

        if ":" in line:
            ability_kind = "activated"
            cost_text, effect_text = _split_activation_cost_effect(line)
        elif trigger:
            ability_kind = "triggered"
        elif low.startswith("if you would"):
            ability_kind = "replacement"

        mana_total, mana_req = _activation_mana(cost_text)
        tap_source = "{t}" in cost_text.lower()
        sacrifice_resource = ""
        remove_counter = ""

        m = re.search(r"sacrifice (?:a|an) (food|treasure|clue)", cost_text.lower())
        if m:
            sacrifice_resource = m.group(1).title()

        # v4.15.6: a cost that says "sacrifice ..." something OTHER than a
        # recognized Food/Treasure/Clue token (e.g. "sacrifice another
        # creature or artifact", Baron Bertram Graywater) must NOT be
        # silently treated as free. Without this flag, mana_total alone
        # already satisfied recognized_cost below, and execute_semantic_ability
        # (App/engine.py) has no other way to know a sacrifice was required -
        # it would pay only the mana and skip the sacrifice entirely, handing
        # out the effect for less than its real cost. Caught during the
        # v4.15.6 KNOWN_COVERAGE_NOTES review of Baron Bertram Graywater's
        # own sacrifice-to-draw line, which was hitting exactly this gap.
        unrecognized_sacrifice_cost = (
            ability_kind == "activated"
            and "sacrifice" in cost_text.lower()
            and not sacrifice_resource
        )

        m = re.search(r"remove (?:an?|one) ([a-z +/\-]+?) counter from", cost_text.lower())
        if m:
            remove_counter = m.group(1).strip()

        # v4.26.0: "Discard a card:"/"Discard two cards:"-shaped activation
        # costs (real, common looting-style pattern - e.g. "{T}, Discard a
        # card: Draw a card.") were not recognized as a cost component AT
        # ALL before this. Unlike an unrecognized "sacrifice ..." cost (see
        # unrecognized_sacrifice_cost above), an unrecognized "discard ..."
        # cost was silently invisible to recognized_cost below - with no
        # mana, no {T}, and no sacrifice, cost_text.strip() != "" so it
        # still fell through to "activated with nothing recognized" =
        # NOT recognized_cost... except real cards combining a tap symbol
        # with the discard ({T}, Discard a card: ...) DID get
        # tap_source=True, which alone made recognized_cost true - so the
        # ability was auto-executed as "exact", paying the tap but never
        # discarding a card, net hand size going UP for a "loot" effect
        # that should have been unchanged. Found via ChatGPT external
        # review (Docs/README.md v4.26.0 entry).
        m = re.search(
            r"\bdiscard (a|an|one|two|three|four|five|\d+) cards?\b",
            cost_text.lower(),
        )
        discard_count = parse_number_token(m.group(1)) if m else 0

        another_target_only = "another target creature" in effect_text.lower()
        actions = _parse_semantic_actions(effect_text)

        # Classify how faithfully this line can currently be represented.
        recognized_cost = (
            not unrecognized_sacrifice_cost
            and (
                ability_kind != "activated"
                or bool(mana_total or mana_req or tap_source or sacrifice_resource or remove_counter or discard_count)
                or cost_text.strip() == ""
            )
        )
        complex_markers = any(x in low for x in (
            "choose one", "choose two", "for each opponent", "for each card",
            "you may cast", "copy target", "random", "unless", "up to",
            "where x is", "equal to",
        ))

        if actions and recognized_cost and not complex_markers:
            mode, conf = "exact", 0.92
        elif actions and recognized_cost:
            mode, conf = "simplified", 0.72
        elif any(x in low for x in ("target", "whenever", "at the beginning", "sacrifice", "counter")):
            mode, conf = "probabilistic", 0.45
        else:
            mode, conf = "review", 0.20

        abilities.append(SemanticAbility(
            source=card.name,
            raw=line,
            ability_kind=ability_kind,
            trigger=trigger,
            mana_total=mana_total,
            mana_requirements=mana_req,
            tap_source=tap_source,
            sacrifice_resource=sacrifice_resource,
            remove_source_counter=remove_counter,
            another_target_only=another_target_only,
            actions=actions,
            execution_mode=mode,
            confidence=conf,
            unrecognized_sacrifice_cost=unrecognized_sacrifice_cost,
            discard_count=discard_count,
        ))

    return abilities


def semantic_card_summary(card: Card) -> str:
    abilities = parse_oracle_semantics(card)
    if not abilities:
        return "Semantic model: no Oracle abilities parsed."
    lines = ["Semantic model:"]
    for a in abilities:
        actions = ", ".join(
            f"{x.kind}{'('+x.keyword+')' if x.keyword else ''}"
            for x in a.actions
        ) or "review"
        lines.append(
            f"- {a.ability_kind}/{a.execution_mode} "
            f"[{a.trigger or 'no trigger'}]: {actions}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Effective permanent state / board modifiers
# ---------------------------------------------------------------------------

def effective_keywords(p: Permanent) -> Set[str]:
    out = set(p.card.keywords)
    out.update(k for k, n in p.named_counters.items() if n > 0 and k in KNOWN_KEYWORDS | {"lifelink", "indestructible"})
    out.update(p.temporary_keywords)
    return out


def _initialize_semantic_permanent(p: Permanent):
    """Apply generic 'enters with a NAME counter' text to a Permanent."""
    for line in split_oracle_lines(p.card.oracle_text):
        low = strip_reminder_text(line).lower()
        m = re.search(r"enters with (?:an?|one) ([a-z +/\-]+?) counter on", low)
        if m:
            counter_name = m.group(1).strip()
            if counter_name == "+1/+1":
                p.counters += 1
            else:
                p.named_counters[counter_name] += 1


_V450_permanent_enters_old = permanent_enters
def permanent_enters(state: GameState, strategy: Strategy, card: Card):
    before = len(state.battlefield)
    _V450_permanent_enters_old(state, strategy, card)
    if len(state.battlefield) > before:
        _initialize_semantic_permanent(state.battlefield[-1])


_V450_batch_creatures_enter_old = batch_creatures_enter
def batch_creatures_enter(state: GameState, strategy: Strategy, cards: List[Card]):
    before = len(state.battlefield)
    _V450_batch_creatures_enter_old(state, strategy, cards)
    for p in state.battlefield[before:]:
        _initialize_semantic_permanent(p)


_V450_untap_step_old = untap_step
def untap_step(state: GameState):
    # "until end of turn" semantic grants from the prior abstract opponent turn
    # are gone before the next turn begins.
    for p in state.battlefield:
        p.temporary_keywords.clear()
    _V450_untap_step_old(state)


def _perm_ready(p: Permanent, state: GameState) -> bool:
    if not p.card.is_creature:
        return True
    return p.entered_turn < state.turn or "haste" in effective_keywords(p)


# ---------------------------------------------------------------------------
# Commander zone state-based action / replacement-choice model
# ---------------------------------------------------------------------------

def commander_self_cast_zones(card: Card) -> Set[str]:
    low = strip_reminder_text(card.oracle_text).lower()
    name = re.escape(card.name.lower())
    zones = set()

    grave_patterns = (
        rf"cast {name} from your graveyard",
        r"cast this card from your graveyard",
        r"you may cast .* from your graveyard",
    )
    exile_patterns = (
        rf"cast {name} from exile",
        r"cast this card from exile",
        r"you may cast .* from exile",
    )
    if any(re.search(pat, low) for pat in grave_patterns):
        zones.add("graveyard")
    if any(re.search(pat, low) for pat in exile_patterns):
        zones.add("exile")
    return zones


def commander_zone_choice(card: Card, zone: str, state: GameState, strategy: Strategy) -> str:
    override = getattr(strategy, "commander_zone_overrides", {}).get(card.name)
    if override in {"command_zone", "graveyard", "exile", "hand", "library"}:
        return override

    policy = getattr(strategy, "commander_zone_policy", "auto")
    if policy == "command_zone":
        return "command_zone"

    if policy == "stay":
        return zone

    # AUTO:
    # Graveyard/exile normally return to command zone. The main supported
    # exception is a commander whose own Oracle text explicitly allows it to
    # be cast from that zone; in that case the simulator can actually use it.
    if zone in {"graveyard", "exile"}:
        if zone in commander_self_cast_zones(card):
            return zone
        return "command_zone"

    # A commander in hand can usually be recast without commander tax, so the
    # simplified pilot keeps it unless explicitly overridden.
    if zone == "hand":
        return "hand"

    # Library is hidden/random and poorly represented by the goldfish pilot:
    # default to command zone.
    if zone == "library":
        return "command_zone"

    return "command_zone"


def apply_commander_zone_state_based_actions(state: GameState, strategy: Strategy):
    """
    Simplified Commander SBA:
    commanders really enter graveyard/exile first, then the owner may move them.
    This preserves dies/exile-event semantics for future trigger handling.
    """
    for zone_name, zone in (("graveyard", state.graveyard), ("exile", state.exile)):
        for card in list(zone):
            if not getattr(card, "commander", False):
                continue
            choice = commander_zone_choice(card, zone_name, state, strategy)
            if choice == "command_zone":
                zone.remove(card)
                if not any(c is card or c.name == card.name for c in state.command_zone):
                    state.command_zone.append(card)
                record_impact(state, card.name, "commander_zone_return", 1)
                state.log(f"COMMANDER SBA: {card.name} -> command zone from {zone_name}")
            else:
                state.log(f"COMMANDER SBA: {card.name} stays in {zone_name} ({choice})")


def commander_replacement_for_hidden_zone(
    state: GameState,
    strategy: Strategy,
    card: Card,
    destination: str,
) -> str:
    if not card.commander:
        return destination
    return commander_zone_choice(card, destination, state, strategy)


# Apply Commander SBAs at every scenario/checkpoint boundary. This is late
# enough that a graveyard/exile event has happened, but early enough that the
# next game action does not incorrectly treat the commander as permanently gone.
_V450_update_scenario_progress_old = update_scenario_progress
def update_scenario_progress(
    state: GameState,
    strategy: ScenarioStrategy,
    progress: Dict[str, dict],
    checkpoint: str,
):
    apply_commander_zone_state_based_actions(state, strategy)
    return _V450_update_scenario_progress_old(state, strategy, progress, checkpoint)


# ---------------------------------------------------------------------------
# Cast supported self-recurring commanders from graveyard/exile
# ---------------------------------------------------------------------------

_V450_cast_one_commander_v41_old = cast_one_commander_v41


# ---------------------------------------------------------------------------
# Generic resource outlets (Arwen/Gyome are parsed, not named)
# ---------------------------------------------------------------------------

def semantic_protection_abilities(p: Permanent) -> List[SemanticAbility]:
    out = []
    for a in parse_oracle_semantics(p.card):
        if a.ability_kind != "activated":
            continue
        if any(x.kind == "grant_keyword_until_eot" and x.keyword == "indestructible" for x in a.actions):
            out.append(a)
    return out


def _resource_available_for_ability(
    state: GameState,
    source: Permanent,
    ability: SemanticAbility,
) -> bool:
    if ability.tap_source and source.tapped:
        return False
    if ability.sacrifice_resource == "Food" and state.food <= 0:
        return False
    if ability.sacrifice_resource == "Treasure" and state.treasure <= 0:
        return False
    if ability.sacrifice_resource == "Clue" and state.clues <= 0:
        return False
    if ability.remove_source_counter:
        if source.named_counters.get(ability.remove_source_counter, 0) <= 0:
            return False
    plan = find_payment(state, Strategy(
        commander_colors=set(),
        value_model=getattr(getattr(state, "_semantic_strategy", None), "value_model", None),
    ), ability.mana_total, ability.mana_requirements) if False else None
    return True







def _find_semantic_payment(
    state: GameState,
    strategy: Strategy,
    ability: SemanticAbility,
) -> Optional[PaymentPlan]:
    reservation = reservation_for_resource(
        ability.sacrifice_resource, 1
    )
    return find_payment(
        state,
        strategy,
        ability.mana_total,
        ability.mana_requirements,
        reservation=reservation,
    )


def _pay_semantic_cost(
    state: GameState,
    strategy: Strategy,
    source: Permanent,
    ability: SemanticAbility,
    payment: PaymentPlan,
):
    apply_payment(state, payment, strategy)

    if ability.tap_source:
        try:
            idx = state.battlefield.index(source)
            tap_permanent(
                state, strategy, idx,
                reason=f"{source.card.name} semantic activation",
            )
        except ValueError:
            source.tapped = True

    if ability.sacrifice_resource == "Food":
        if state.food <= 0:
            record_engine_metric(
                state, "semantic_resource_conflict", 1
            )
            return False
        state.food -= 1
        token_sacrificed(
            state, "Food", 1, strategy
        )
    elif ability.sacrifice_resource == "Treasure":
        if state.treasure <= 0:
            record_engine_metric(
                state, "semantic_resource_conflict", 1
            )
            return False
        state.treasure -= 1
        token_sacrificed(
            state, "Treasure", 1, strategy
        )
    elif ability.sacrifice_resource == "Clue":
        if state.clues <= 0:
            record_engine_metric(
                state, "semantic_resource_conflict", 1
            )
            return False
        state.clues -= 1
        token_sacrificed(
            state, "Clue", 1, strategy
        )

    if ability.remove_source_counter:
        if (
            source.named_counters.get(
                ability.remove_source_counter, 0
            ) <= 0
        ):
            record_engine_metric(
                state, "semantic_counter_conflict", 1
            )
            return False
        source.named_counters[
            ability.remove_source_counter
        ] -= 1
        if (
            source.named_counters[
                ability.remove_source_counter
            ] <= 0
        ):
            del source.named_counters[
                ability.remove_source_counter
            ]

    guard_resource_invariants(
        state,
        f"semantic cost {source.card.name}",
    )
    return True





def try_semantic_board_protection(
    state: GameState,
    strategy: Strategy,
    target: Permanent,
) -> Optional[str]:
    """
    Use parsed on-board activated abilities that grant indestructible.
    This generalizes Gyome/Arwen-style resource outlets.
    """
    sources = sorted(
        list(state.battlefield),
        key=lambda p: generic_tutor_score(p.card, strategy.tutor_priority),
        reverse=True,
    )
    for source in sources:
        for ability in semantic_protection_abilities(source):
            if ability.another_target_only and source is target:
                continue
            # v4.15.6: same guard as execute_semantic_ability - never pay
            # only the mana portion of a cost this parser can't actually
            # collect (e.g. an unrecognized "sacrifice a <thing>" clause).
            if ability.unrecognized_sacrifice_cost:
                continue

            if ability.tap_source and source.tapped:
                continue
            if ability.sacrifice_resource == "Food" and state.food <= 0:
                continue
            if ability.sacrifice_resource == "Treasure" and state.treasure <= 0:
                continue
            if ability.sacrifice_resource == "Clue" and state.clues <= 0:
                continue
            if ability.remove_source_counter and source.named_counters.get(ability.remove_source_counter, 0) <= 0:
                continue

            payment = _find_semantic_payment(state, strategy, ability)
            if not payment:
                continue

            if not _pay_semantic_cost(state, strategy, source, ability, payment):
                continue
            _apply_semantic_protection_effect(state, strategy, source, target, ability)
            return source.card.name
    return None


# ---------------------------------------------------------------------------
# Abstract opponent interaction using effective keywords + parsed board outlets
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Combat with semantic keyword counters
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Coverage / AI handoff now exposes semantic execution mode
# ---------------------------------------------------------------------------

_V450_card_model_coverage_rows_old = card_model_coverage_rows
def card_model_coverage_rows(deck: List[Card]) -> List[dict]:
    base = _V450_card_model_coverage_rows_old(deck)
    by_name = {c.name: c for c in deck}

    for row in base:
        c = by_name.get(row["Name"])
        if not c:
            continue
        abilities = parse_oracle_semantics(c)
        modes = Counter(a.execution_mode for a in abilities)
        parsed = []
        for a in abilities:
            action_names = [x.kind + (f":{x.keyword}" if x.keyword else "") for x in a.actions]
            parsed.append(
                f"{a.ability_kind}:{a.trigger or '-'}:"
                f"{a.execution_mode}:" + ",".join(action_names or ["review"])
            )
        row["Semantic runtime version"] = SEMANTIC_RUNTIME_VERSION
        row["Parsed semantic abilities"] = " || ".join(parsed)
        row["Semantic execution mix"] = " | ".join(
            f"{k}:{v}" for k, v in sorted(modes.items())
        )
        row["Commander self-cast zones"] = " | ".join(sorted(commander_self_cast_zones(c)))
    return base


_V450_write_model_review_old = write_model_review_instructions
def write_model_review_instructions(path: Path):
    _V450_write_model_review_old(path)
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write("""

## v4.5 semantic execution tiers

Oracle abilities are now additionally parsed into four execution modes:

- exact: the simplified engine understands the trigger/cost/action shape directly;
- simplified: the game-state effect is represented, but targeting/timing/choice is compressed;
- probabilistic: the ability is recognized but depends strongly on unknown opponents/choices;
- review: text is recognized as relevant but not safely executed.

An AI MUST treat these as model-confidence labels, not card-quality labels.

v4.5 also models parsed on-board indestructible outlets such as:
- mana + sacrifice Food -> target creature indestructible / tap it;
- mana + remove a named source counter -> another creature indestructible, with
  recognized +1/+1 / lifelink counter side effects.

Commander movement is modeled as a separate zone rule. Graveyard/exile happens first,
then the command-zone decision, so future dies/exile trigger modeling is not erased.
""")


_V450_streaming_summary_old = streaming_summary_v440
def streaming_summary_v440(
    deck: List[Card],
    stats: StreamingStatsV440,
    cfg: SimConfig,
    strategy: ScenarioStrategy,
    impact_rows: List[dict],
    detailed_runs_logged: int,
    log_policy: str,
) -> dict:
    data = _V450_streaming_summary_old(
        deck, stats, cfg, strategy, impact_rows,
        detailed_runs_logged, log_policy,
    )
    data["version"] = "4.5.0"
    data["simulation"]["commander_zone_policy"] = getattr(strategy, "commander_zone_policy", "auto")
    data["simulation"]["semantic_runtime_version"] = SEMANTIC_RUNTIME_VERSION
    data.setdefault("limitations", []).extend([
        "Commander graveyard/exile decisions are now modeled; auto mode normally returns to the command zone unless a supported self-cast-from-that-zone ability makes staying useful.",
        "Oracle semantics use exact/simplified/probabilistic/review tiers. Complex target selection, multiplayer politics and unknown opposing permanents remain abstractions.",
        "Parsed board protection outlets are real resource-based simplifications; they do not constitute a full priority/stack simulator.",
    ])
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main_v450():
    ap = argparse.ArgumentParser(description="Commander Goldfish Simulator v4.5.0")
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument("--opponent", choices=sorted(OPPONENT_PROFILES), default="goldfish")
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        from commander_goldfish_v4_5_0_gui import launch_gui
        launch_gui()
        return

    ensure_runtime_dependencies(include_images=False, status_callback=print)

    commander_names = list(args.commander) or detect_commander_hints(args.deck_file)
    if not commander_names:
        raise SystemExit("No commander detected. Use --commander or the GUI.")

    tags = {x.strip().lower() for x in args.tags.split(",") if x.strip()}
    result = run_pipeline_v440(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.5.0 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




# ===========================================================================
# v4.6.0 — RESOURCE / INTERACTION / SEMANTIC RUNTIME HARDENING
# ===========================================================================

SEMANTIC_RUNTIME_VERSION = "2.0"


# ---------------------------------------------------------------------------
# Shared engine diagnostics
# ---------------------------------------------------------------------------

def record_engine_metric(state: GameState, metric: str, amount: float = 1.0):
    state.impact["__ENGINE__"][metric] += amount


def resource_snapshot(state: GameState) -> dict:
    return {
        "food": int(state.food),
        "treasure": int(state.treasure),
        "clues": int(state.clues),
    }


def resource_invariant_ok(state: GameState) -> bool:
    return state.food >= 0 and state.treasure >= 0 and state.clues >= 0


def guard_resource_invariants(state: GameState, context: str = ""):
    if state.food < 0:
        record_engine_metric(state, "negative_food", 1)
        state.log(f"ENGINE INVARIANT: Food below zero at {context}; clamped.")
        state.food = 0
    if state.treasure < 0:
        record_engine_metric(state, "negative_treasure", 1)
        state.log(f"ENGINE INVARIANT: Treasure below zero at {context}; clamped.")
        state.treasure = 0
    if state.clues < 0:
        record_engine_metric(state, "negative_clues", 1)
        state.log(f"ENGINE INVARIANT: Clues below zero at {context}; clamped.")
        state.clues = 0


# ---------------------------------------------------------------------------
# 1) Resource reservation / payment
# ---------------------------------------------------------------------------

@dataclass
class ResourceReservation:
    food: int = 0
    treasure: int = 0
    clues: int = 0
    permanent_ids: Set[int] = field(default_factory=set)


def reservation_for_resource(resource: str, count: int = 1) -> ResourceReservation:
    r = ResourceReservation()
    if resource == "Food":
        r.food = count
    elif resource == "Treasure":
        r.treasure = count
    elif resource == "Clue":
        r.clues = count
    return r


_V460_build_mana_sources_old = build_mana_sources
def build_mana_sources(
    state: GameState,
    strategy: Strategy,
    reservation: Optional[ResourceReservation] = None,
) -> List[ManaSource]:
    sources = _V460_build_mana_sources_old(state, strategy)
    reservation = reservation or ResourceReservation()

    out = []
    treasure_slots_to_hide = max(0, reservation.treasure)
    available_food_for_goose = max(0, state.food - reservation.food)

    for src in sources:
        if src.permanent_index is not None:
            if 0 <= src.permanent_index < len(state.battlefield):
                if id(state.battlefield[src.permanent_index]) in reservation.permanent_ids:
                    continue

        if src.kind == "treasure":
            if treasure_slots_to_hide > 0:
                treasure_slots_to_hide -= 1
                continue

        if src.kind == "goose" and available_food_for_goose <= 0:
            continue

        out.append(src)

    return out


def find_payment(
    state: GameState,
    strategy: Strategy,
    total_cost: int,
    req: Counter,
    reservation: Optional[ResourceReservation] = None,
) -> Optional[PaymentPlan]:
    """DP mana solver with token/permanent resource reservation."""
    sources = build_mana_sources(state, strategy, reservation=reservation)
    dp = {(0, 0, 0, 0, 0, 0, 0): (0.0, [], Counter())}

    need = {c: req.get(c, 0) for c in COLORS + (COLORLESS,)}
    total_cap = max(total_cost, sum(need.values()))

    def key_for(pool: Counter):
        return (
            min(pool["W"], need["W"]),
            min(pool["U"], need["U"]),
            min(pool["B"], need["B"]),
            min(pool["R"], need["R"]),
            min(pool["G"], need["G"]),
            min(pool["C"], need["C"]),
            min(output_total(pool), total_cap),
        )

    for source in sources:
        newdp = dict(dp)
        for _key, (penalty, used, pool) in list(dp.items()):
            for option in source.options:
                newpool = pool + option
                key = key_for(newpool)
                newpenalty = penalty + source.penalty
                old = newdp.get(key)
                if old is None or newpenalty < old[0]:
                    newdp[key] = (
                        newpenalty,
                        used + [(source, option)],
                        newpool,
                    )
        dp = newdp

    candidates = []
    for _key, (penalty, used, pool) in dp.items():
        if payment_meets(pool, total_cost, req):
            candidates.append((penalty, len(used), used, pool))

    if not candidates:
        return None

    penalty, _n, used, pool = min(candidates, key=lambda x: (x[0], x[1]))
    return PaymentPlan(used=used, total=pool, penalty=penalty)


_V460_apply_payment_old = apply_payment
def apply_payment(state: GameState, plan: PaymentPlan, strategy: Optional[Strategy] = None):
    goose_need = sum(1 for src, _ in plan.used if src.kind == "goose")
    treasure_need = sum(1 for src, _ in plan.used if src.kind == "treasure")

    if goose_need > state.food:
        record_engine_metric(state, "payment_resource_conflict", 1)
        state.log(
            f"ENGINE PAYMENT WARNING: plan wanted {goose_need} Food for mana, "
            f"only {state.food} available."
        )
    if treasure_need > state.treasure:
        record_engine_metric(state, "payment_resource_conflict", 1)
        state.log(
            f"ENGINE PAYMENT WARNING: plan wanted {treasure_need} Treasure, "
            f"only {state.treasure} available."
        )

    _V460_apply_payment_old(state, plan, strategy)
    guard_resource_invariants(state, "apply_payment")


@dataclass
class AdditionalCostChoice:
    resource: str = ""
    permanent_id: Optional[int] = None
    permanent_name: str = ""


def choose_additional_cost(
    card: Card,
    state: GameState,
    strategy: Optional[Strategy],
) -> Optional[AdditionalCostChoice]:
    low = strip_reminder_text(card.oracle_text).lower()
    if "as an additional cost to cast this spell, sacrifice an artifact or creature" not in low:
        return AdditionalCostChoice()

    target = focused_life_target(state, strategy) if strategy is not None else 0
    preserve_food = target > state.life

    resources = (
        [("Clue", state.clues), ("Treasure", state.treasure), ("Food", state.food)]
        if preserve_food else
        [("Food", state.food), ("Clue", state.clues), ("Treasure", state.treasure)]
    )
    for resource, count in resources:
        if count > 0:
            return AdditionalCostChoice(resource=resource)

    candidates = [
        p for p in state.battlefield
        if (p.card.is_creature or p.card.is_artifact)
        and not p.card.commander
    ]
    if candidates:
        p = min(
            candidates,
            key=lambda x: generic_tutor_score(x.card, DEFAULT_TUTOR_PRIORITY),
        )
        return AdditionalCostChoice(
            permanent_id=id(p),
            permanent_name=p.card.name,
        )
    return None


def reservation_for_additional_choice(choice: Optional[AdditionalCostChoice]) -> ResourceReservation:
    r = ResourceReservation()
    if not choice:
        return r
    if choice.resource == "Food":
        r.food = 1
    elif choice.resource == "Treasure":
        r.treasure = 1
    elif choice.resource == "Clue":
        r.clues = 1
    if choice.permanent_id is not None:
        r.permanent_ids.add(choice.permanent_id)
    return r


def consume_additional_choice(
    card: Card,
    state: GameState,
    strategy: Optional[Strategy],
    choice: Optional[AdditionalCostChoice],
) -> bool:
    if choice is None:
        return False
    if not choice.resource and choice.permanent_id is None:
        return True

    if choice.resource:
        attr = choice.resource.lower() if choice.resource != "Clue" else "clues"
        if choice.resource == "Food":
            if state.food <= 0:
                record_engine_metric(state, "additional_cost_conflict", 1)
                return False
            state.food -= 1
        elif choice.resource == "Treasure":
            if state.treasure <= 0:
                record_engine_metric(state, "additional_cost_conflict", 1)
                return False
            state.treasure -= 1
        elif choice.resource == "Clue":
            if state.clues <= 0:
                record_engine_metric(state, "additional_cost_conflict", 1)
                return False
            state.clues -= 1
        token_sacrificed(state, choice.resource, 1, strategy)
        state.log(f"{card.name}: sacrificed {choice.resource} as additional cost")
        guard_resource_invariants(state, f"{card.name} additional cost")
        return True

    p = next((x for x in state.battlefield if id(x) == choice.permanent_id), None)
    if p is None:
        record_engine_metric(state, "additional_cost_conflict", 1)
        return False
    state.battlefield.remove(p)
    state.graveyard.append(p.card)
    state.log(f"{card.name}: sacrificed {p.card.name} as additional cost")
    if strategy is not None:
        apply_commander_zone_state_based_actions(state, strategy)
    return True


def cast_option(card: Card, state: GameState, strategy: Strategy) -> Optional[CastOption]:
    if is_reactive_only(card, strategy):
        return None

    choice = choose_additional_cost(card, state, strategy)
    if choice is None:
        return None
    reservation = reservation_for_additional_choice(choice)

    if has_x_cost(card):
        # No current deck card combines the supported X model with an additional
        # token/permanent sacrifice. Keep the safe behavior rather than silently
        # double-spending resources.
        if choice.resource or choice.permanent_id is not None:
            return None
        xp = best_x_plan(card, state, strategy)
        if not xp:
            return None
        opt = CastOption(card, xp.total_cost, xp.payment, x_plan=xp)
        setattr(opt, "additional_choice", choice)
        return opt

    discount, attribution = effective_cost_discount(card, state)
    # v4.15.5: a card's OWN self-referential "costs {N} less ... for each
    # <board-state condition>" text (Blasphemous-Act-shaped; real project
    # example: Furygale Flocking) - additive with the external-reduction
    # discount above, same attribution dict so both show up in the same
    # mana_discount impact rows.
    scaling_discount, scaling_attribution = boardwipe_self_scaling_discount(card, state)
    if scaling_discount:
        discount += scaling_discount
        for source, amount in scaling_attribution.items():
            attribution[source] = attribution.get(source, 0) + amount
    # v4.22.0: Delve - see delve_discount's own docstring; the matching
    # exile-from-graveyard happens in try_cast_option once this cast
    # actually goes through, keyed off the "Delve" attribution entry.
    delve_amount, delve_attribution = delve_discount(card, state)
    if delve_amount:
        discount += delve_amount
        for source, amount in delve_attribution.items():
            attribution[source] = attribution.get(source, 0) + amount
    raw = card.min_cost
    total = max(sum(card.color_requirements.values()), raw - discount)
    payment = find_payment(
        state,
        strategy,
        total,
        card.color_requirements,
        reservation=reservation,
    )
    if not payment:
        return None

    opt = CastOption(card, total, payment, discount_attribution=attribution)
    setattr(opt, "additional_choice", choice)
    return opt


def _pay_cast_copy_trigger_cost(state: GameState, strategy: Strategy, p: Permanent) -> bool:
    """
    WP9. "Whenever you cast an instant or sorcery spell, copy it" with a real
    optional cost gating it (Aziza: tap three untapped creatures; Mica:
    sacrifice an artifact) - scoped to exactly these two real cards rather
    than a generic oracle-text pattern match, since each has its own real
    cost that must actually be paid, not assumed free. Returns whether the
    cost was paid (i.e. whether the copy happens) - an unaffordable "you may"
    cost just means the trigger does nothing, same as declining it.
    """
    if p.card.name == AZIZA_NAME:
        # Reuses the existing resource_available scenario predicate (see
        # App/scenario_predicates/handlers.py) rather than re-deriving "are
        # there >=3 untapped creatures" from scratch.
        result = scenario_predicates_registry.evaluate(
            sys.modules[__name__], "resource_available",
            {"resource": "untapped_creatures", "min_count": 3}, state, strategy,
        )
        if not result.satisfied:
            return False
        paid = 0
        for creature in state.creatures():
            if paid >= 3:
                break
            if creature.tapped:
                continue
            idx = state.battlefield.index(creature)
            tap_permanent(state, strategy, idx, reason="aziza_copy_cost")
            paid += 1
        return True

    if p.card.name == MICA_NAME:
        # Sacrifice cost, not a tap cost - unlike Aziza's, tapped state is
        # irrelevant here, so this is a plain "is there >=1 artifact to
        # sacrifice" existence check, not resource_available's
        # "untapped_artifacts" (the wrong check for a sacrifice). A single
        # yes/no lookup with no X to choose and no competing candidates to
        # rank doesn't need the WP8 Resource Planner's allocation search -
        # using it here would be over-engineering a 3-line check, which the
        # WP9 brief explicitly allows substituting with a simpler, justified
        # solution. Picks the first artifact found (no attempt to identify
        # the "worst" one to lose) - a disclosed simplification, consistent
        # with this project's existing level of abstraction elsewhere.
        artifacts = [a for a in state.battlefield if a.card.is_artifact]
        if not artifacts:
            return False
        sac = artifacts[0]
        state.battlefield.remove(sac)
        state.graveyard.append(sac.card)
        record_impact(state, MICA_NAME, "sacrifice", 1)
        return True

    return False  # no other card is modeled with a paid cast-copy trigger


def _maybe_copy_cast_instant_or_sorcery(state: GameState, strategy: Strategy, card: Card, opt: "CastOption"):
    """
    WP9 bug fix, not a new feature: an earlier version of this "whenever you
    cast an instant or sorcery spell, copy it" check existed in an older,
    superseded definition of try_cast_option earlier in this file - but this
    module's last-definition-wins layering (see COWORK_HANDOFF.md section 3)
    means that older code was never actually reachable, so the feature was
    silently dead in every real run. Reinstated here, in the function that is
    actually active, scoped to Aziza/Mica with their real costs (see
    _pay_cast_copy_trigger_cost) rather than reviving the old unconditional
    free-copy version of the check.
    """
    if not (card.is_instant or card.is_sorcery):
        return
    for p in list(state.battlefield):
        if p.card.name not in (AZIZA_NAME, MICA_NAME):
            continue
        if not _pay_cast_copy_trigger_cost(state, strategy, p):
            continue
        record_impact(state, p.card.name, "spell_copy", 1)
        # Copying is not casting: this deliberately does NOT route back
        # through try_cast_option/this function - a copy does not itself
        # trigger "whenever you cast" abilities (this permanent's own trigger
        # included, so no double- or infinite-copying), and it reuses the
        # SAME X (opt.x_plan) rather than choosing a new one, matching how a
        # copy of an X spell actually works in real Magic.
        if opt.x_plan:
            resolve_x_spell(state, strategy, card, opt.x_plan)
        else:
            resolve_direct_spell_effects(state, strategy, card)
        state.log(f"{p.card.name}: copied {card.name}")


def _record_commander_hand_cast(state: GameState, card: Card):
    if not card.commander:
        return
    state.commander_casts += 1
    record_impact(state, card.name, "commander_hand_cast", 1)
    casted = getattr(state, "_commander_games_cast", set())
    if card.name not in casted:
        record_impact(state, card.name, "commander_games_cast", 1)
        casted.add(card.name)
        state._commander_games_cast = casted


def try_cast_option(state: GameState, strategy: Strategy, opt: CastOption) -> bool:
    card = opt.card
    choice = getattr(opt, "additional_choice", AdditionalCostChoice())

    apply_payment(state, opt.payment, strategy)
    if not consume_additional_choice(card, state, strategy, choice):
        return False

    if card in state.hand:
        state.hand.remove(card)

    _record_commander_hand_cast(state, card)
    record_impact(state, card.name, "cast", 1)
    record_impact(state, card.name, "mana_spent", opt.total_cost)
    for source, amount in opt.discount_attribution.items():
        record_impact(state, source, "mana_discount", amount)
        # v4.22.0: Delve is a real paid cost (exile that many graveyard
        # cards), not a free discount - see delve_discount's docstring.
        # min() guards against the graveyard having shrunk between
        # cast_option computing the discount and this actually running
        # (nothing currently does that mid-cast in this engine, but cheap
        # to be safe rather than risk a negative-length slice).
        if source == "Delve" and amount > 0:
            n = min(int(amount), len(state.graveyard))
            exiled, state.graveyard[:] = state.graveyard[:n], state.graveyard[n:]
            state.exile.extend(exiled)
            record_impact(state, card.name, "delved", n)
            state.log(f"DELVE: {card.name} exiled {n} card(s) from the graveyard")

    state.log(f"CAST {card.name}" + (f" X={opt.x_plan.x}" if opt.x_plan else ""))

    # v4.22.0: Prowess ("Whenever you cast a noncreature spell, this
    # creature gets +1/+1 until end of turn."). try_cast_option is the
    # single funnel every successful spell cast goes through (creature and
    # noncreature alike; lands are played, not cast, and never reach this
    # function), so this is the one place that needs the check regardless
    # of what kind of noncreature spell was just cast. Only power matters -
    # this engine has no toughness-based combat math anywhere (see
    # creature_power's own callers; combat is resolved from power plus the
    # abstract block/trade roll, never lethal-damage-vs-toughness).
    if not card.is_creature and not card.is_land:
        for p in state.battlefield:
            if "prowess" in effective_keywords_in_state(p, state):
                board_modifiers(state).append(BoardModifier(
                    source=f"{p.card.name} (prowess)", expires_turn=state.turn,
                    kind="team_pt_bonus", amount=1.0, target_id=id(p),
                ))
                record_impact(state, p.card.name, "prowess_triggers", 1)

    if card.is_permanent and not card.is_land:
        permanent_enters(state, strategy, card)
        record_impact(state, card.name, "entered", 1)
    else:
        if opt.x_plan:
            resolve_x_spell(state, strategy, card, opt.x_plan)
        else:
            resolve_direct_spell_effects(state, strategy, card)
        if card not in state.exile and card not in state.graveyard:
            state.graveyard.append(card)
        _maybe_copy_cast_instant_or_sorcery(state, strategy, card, opt)

    guard_resource_invariants(state, f"cast {card.name}")
    return True


def try_cast_card(
    state: GameState,
    strategy: Strategy,
    card: Card,
    total_cost: Optional[int] = None,
) -> bool:
    if is_reactive_only(card, strategy):
        return False
    opt = cast_option(card, state, strategy)
    if opt is None:
        return False
    if total_cost is not None and opt.total_cost != total_cost:
        # Legacy callers very rarely use this path; preserve their requested cost.
        choice = getattr(opt, "additional_choice", AdditionalCostChoice())
        reservation = reservation_for_additional_choice(choice)
        payment = find_payment(
            state, strategy, total_cost, card.color_requirements,
            reservation=reservation,
        )
        if not payment:
            return False
        opt.total_cost = total_cost
        opt.payment = payment
    return try_cast_option(state, strategy, opt)


# ---------------------------------------------------------------------------
# 2) Reactive protection pays real mana; Eerie actually blinks creatures
# ---------------------------------------------------------------------------

def _protection_card_answers(card: Card, *, wide: bool, removal_type: str) -> bool:
    low = strip_reminder_text(card.oracle_text).lower()
    blink = "exile any number of target creatures you control" in low and "return those cards" in low
    phases = "phases out" in low
    indestructible = "indestructible until end of turn" in low
    hexproof = "hexproof until end of turn" in low or "gain hexproof" in low

    if blink or phases:
        return True
    if wide:
        return removal_type == "destroy" and indestructible
    # Targeted interaction can be blanked by hexproof before resolution.
    if hexproof:
        return True
    return removal_type == "destroy" and indestructible




def try_reactive_protection(
    state: GameState,
    strategy: Strategy,
    *,
    wide: bool,
    removal_type: str,
    target: Optional[Permanent] = None,
) -> Optional[str]:
    preferred = (
        ["Heroic Intervention", "Eerie Interlude", "Cosmic Intervention"]
        if wide else
        ["Royal Treatment", "Heroic Intervention", "Eerie Interlude", "Armor of Shadows"]
    )

    for name in preferred:
        card = next((c for c in state.hand if c.name == name), None)
        if card is None or not _protection_card_answers(
            card, wide=wide, removal_type=removal_type
        ):
            continue

        payment = find_payment(
            state,
            strategy,
            card.min_cost,
            card.color_requirements,
        )
        if payment is None:
            continue

        apply_payment(state, payment, strategy)
        state.hand.remove(card)
        state.graveyard.append(card)
        record_impact(state, name, "cast", 1)
        record_impact(state, name, "mana_spent", card.min_cost)
        record_impact(state, name, "protection", 1)

        low = strip_reminder_text(card.oracle_text).lower()
        if "exile any number of target creatures you control" in low and "return those cards" in low:
            blink_targets = (
                list(state.creatures())
                if wide else
                ([target] if target is not None and target.card.is_creature else [])
            )
            _blink_creatures(state, strategy, blink_targets, name)
        else:
            if wide:
                for p in state.battlefield:
                    if "hexproof" in low:
                        p.temporary_keywords.add("hexproof")
                    if "indestructible" in low:
                        p.temporary_keywords.add("indestructible")
            elif target is not None:
                if "hexproof" in low:
                    target.temporary_keywords.add("hexproof")
                if "indestructible" in low:
                    target.temporary_keywords.add("indestructible")

        state.log(
            f"{name}: paid {card.mana_cost or card.min_cost} and used against "
            f"abstract {removal_type} {'wipe' if wide else 'removal'}"
        )
        return name

    return None


# ---------------------------------------------------------------------------
# 3) Self-reference: "Arwen" means "Arwen, Mortal Queen"
# ---------------------------------------------------------------------------

def card_reference_names(card: Card) -> Set[str]:
    names = {card.name.lower()}
    first = card.name.split(",", 1)[0].strip().lower()
    if first:
        names.add(first)
    # DFC / subtitle-ish names often use the first segment in Oracle self-reference.
    if " // " in card.name:
        names.add(card.name.split(" // ", 1)[0].strip().lower())
    return names


def text_references_source(card: Card, text: str) -> bool:
    low = (text or "").lower()
    if any(ref and re.search(rf"\b{re.escape(ref)}\b", low) for ref in card_reference_names(card)):
        return True
    return any(
        phrase in low
        for phrase in ("this creature", "this permanent", "this card", "itself")
    )


def _apply_semantic_protection_effect(
    state: GameState,
    strategy: Strategy,
    source: Permanent,
    target: Permanent,
    ability: SemanticAbility,
):
    target.temporary_keywords.add("indestructible")
    low = ability.raw.lower()
    source_referenced = text_references_source(source.card, ability.raw)

    if "+1/+1 counter" in low:
        if "that creature" in low or "target creature" in low:
            target.counters += 1
            record_impact(state, source.card.name, "counters", 1)
        if source_referenced:
            source.counters += 1
            record_impact(state, source.card.name, "counters", 1)

    if "lifelink counter" in low:
        if "that creature" in low or "target creature" in low:
            target.named_counters["lifelink"] += 1
        if source_referenced:
            source.named_counters["lifelink"] += 1

    if re.search(r"\btap it\b", low):
        target.tapped = True

    record_impact(state, source.card.name, "protection", 1)
    state.log(
        f"SEMANTIC protection: {source.card.name} protects {target.card.name} "
        f"via parsed activated ability"
    )


# ---------------------------------------------------------------------------
# 4 + 5) Typed abstract removal + complete commander zone movement helper
# ---------------------------------------------------------------------------

SPOT_REMOVAL_MIX = {
    "aggro":     {"destroy": .70, "exile": .10, "bounce": .10, "shrink": .08, "tuck": .02},
    "midrange":  {"destroy": .55, "exile": .20, "bounce": .10, "shrink": .10, "tuck": .05},
    "control":   {"destroy": .30, "exile": .28, "bounce": .20, "shrink": .12, "tuck": .10},
    "horde":     {"destroy": 1.0},
    "goldfish":  {"destroy": 1.0},
}
WIPE_REMOVAL_MIX = {
    "aggro":     {"destroy": .75, "exile": .08, "bounce": .07, "shrink": .10},
    "midrange":  {"destroy": .60, "exile": .15, "bounce": .10, "shrink": .15},
    "control":   {"destroy": .42, "exile": .25, "bounce": .18, "shrink": .15},
    "horde":     {"destroy": 1.0},
    "goldfish":  {"destroy": 1.0},
}


def weighted_key(rng: random.Random, weights: Dict[str, float]) -> str:
    total = sum(max(0.0, v) for v in weights.values())
    roll = rng.random() * total
    acc = 0.0
    for key, weight in weights.items():
        acc += max(0.0, weight)
        if roll <= acc:
            return key
    return next(iter(weights))


def choose_removal_type(profile: str, rng: random.Random, *, wide: bool) -> str:
    table = WIPE_REMOVAL_MIX if wide else SPOT_REMOVAL_MIX
    return weighted_key(rng, table.get(profile, table["midrange"]))






def _wipe_destination(removal_type: str) -> str:
    return {
        "destroy": "graveyard",
        "shrink": "graveyard",
        "exile": "exile",
        "bounce": "hand",
        "tuck": "library",
    }.get(removal_type, "graveyard")


# ---------------------------------------------------------------------------
# 6 + 7 + 8 + 9) Cached semantic executor, board modifiers, probabilities
# ---------------------------------------------------------------------------


_V460_parse_semantic_actions_old = _parse_semantic_actions
def _parse_semantic_actions(effect: str) -> List[SemanticAction]:
    actions = _V460_parse_semantic_actions_old(effect)
    low = strip_reminder_text(effect).lower()

    m = re.search(
        r"creatures you control get \+(\d+)/\+(\d+)(?: until end of turn)?",
        low,
    )
    if m and not any(a.kind == "team_pt_bonus" for a in actions):
        actions.append(SemanticAction(
            kind="team_pt_bonus",
            amount=float(m.group(1)),
            target=f"{m.group(1)}/{m.group(2)}",
            raw=effect,
        ))

    for kw in KNOWN_KEYWORDS | {"lifelink", "indestructible"}:
        if re.search(
            rf"creatures you control (?:gain|have) {re.escape(kw)}(?: until end of turn)?",
            low,
        ):
            if not any(
                a.kind == "grant_team_keyword"
                and a.keyword == kw
                for a in actions
            ):
                actions.append(SemanticAction(
                    kind="grant_team_keyword",
                    keyword=kw,
                    target="creatures_you_control",
                    raw=effect,
                ))

    # v4.19.0: fixed-number "deals N damage to <a player-shaped target>" -
    # added for planeswalker loyalty abilities (e.g. Ugin's "+2: Ugin deals 3
    # damage to any target."), but general-purpose for any card. This engine
    # has no opposing creatures/permanents to damage, so - same simplification
    # already used for "each/target opponent loses N life" above - a target
    # phrase that CAN mean a player ("any target", "target player", "target
    # opponent", "each opponent") is redirected at opponent life loss via the
    # existing opponent_life_loss handler. A target phrase that can ONLY mean
    # a permanent ("target creature", "target creature or planeswalker", ...)
    # is deliberately NOT matched here - this engine has nothing on an
    # opponent's side of the board for that to remove, and guessing it means
    # "hit their face" would silently inflate a removal spell's value. X-cost
    # damage ("deals X damage") is excluded too - that already goes through
    # the dedicated best_x_plan machinery, not this generic parser.
    m = re.search(
        r"deals? (a|one|two|three|four|five|six|seven|eight|nine|ten|\d+) damage to "
        r"(any target|target player|target opponent|each opponent)\b",
        low,
    )
    if m and not any(a.kind == "opponent_life_loss" for a in actions):
        actions.append(SemanticAction(
            kind="opponent_life_loss",
            amount=parse_number_token(m.group(1)),
            target=("each opponent" if m.group(2) == "each opponent" else "target opponent"),
            raw=effect,
        ))

    return actions


_V460_parse_oracle_semantics_raw = parse_oracle_semantics
_SEMANTIC_CACHE: Dict[Tuple[str, str, str], Tuple[SemanticAbility, ...]] = {}
_SEMANTIC_CACHE_HITS = 0
_SEMANTIC_CACHE_MISSES = 0


def parse_oracle_semantics(card: Card) -> List[SemanticAbility]:
    global _SEMANTIC_CACHE_HITS, _SEMANTIC_CACHE_MISSES
    key = (card.name, card.oracle_text, card.type_line)
    if key in _SEMANTIC_CACHE:
        _SEMANTIC_CACHE_HITS += 1
        return list(_SEMANTIC_CACHE[key])

    _SEMANTIC_CACHE_MISSES += 1
    abilities = _V460_parse_oracle_semantics_raw(card)

    # Opponent-dependent trigger shapes are the principal probabilistic tier.
    for ability in abilities:
        low = ability.raw.lower()
        opponent_trigger = (
            low.startswith("whenever an opponent")
            or low.startswith("whenever one or more opponents")
            or low.startswith("whenever a creature an opponent")
            or low.startswith("whenever a permanent an opponent")
        )
        if opponent_trigger and ability.actions:
            ability.execution_mode = "probabilistic"
            ability.confidence = min(ability.confidence, 0.55)

    _SEMANTIC_CACHE[key] = tuple(abilities)
    return list(abilities)


@dataclass
class BoardModifier:
    source: str
    expires_turn: int
    kind: str
    scope: str = "creatures_you_control"
    target_id: Optional[int] = None
    power: Optional[float] = None
    toughness: Optional[float] = None
    amount: float = 0.0
    keyword: str = ""


def board_modifiers(state: GameState) -> List[BoardModifier]:
    if not hasattr(state, "_board_modifiers"):
        state._board_modifiers = []
    return state._board_modifiers


def expire_board_modifiers(state: GameState):
    state._board_modifiers = [
        m for m in board_modifiers(state)
        if m.expires_turn >= state.turn
    ]


_V460_untap_step_old = untap_step
def untap_step(state: GameState):
    expire_board_modifiers(state)
    state._semantic_activated_this_turn = set()
    state._semantic_probabilistic_this_turn = set()
    _V460_untap_step_old(state)


_V460_creature_power_old = creature_power
def creature_power(p: Permanent, state: GameState) -> float:
    base_override = None
    bonus = 0.0

    # Static generic team bonuses from non-dedicated cards are derived live from
    # the battlefield, so they disappear automatically when the source leaves.
    for source in state.battlefield:
        if source is p and False:
            pass
        if source.card.name in DEDICATED_RESOLVERS:
            continue
        for ability in parse_oracle_semantics(source.card):
            if ability.ability_kind != "static":
                continue
            for action in ability.actions:
                if action.kind == "team_pt_bonus":
                    bonus += float(action.amount or 0)

    for modifier in board_modifiers(state):
        if modifier.target_id is not None and modifier.target_id != id(p):
            continue
        if modifier.kind == "set_base_pt" and modifier.power is not None:
            base_override = modifier.power
        elif modifier.kind == "team_pt_bonus":
            bonus += modifier.amount

    if base_override is None:
        power = p.card.power or 0.0
    else:
        power = base_override
    power += p.counters + bonus
    power += equipment_model.equipment_power_bonus(state, p)

    if state.has("The Arkenstone"):
        power += 1
    if state.has(DOCTOR_STRANGE_NAME) and state.life >= 50:
        power += 2
    return max(0.0, power)


def _modifier_keywords_for(p: Permanent, state: GameState) -> Set[str]:
    out = set()
    for modifier in board_modifiers(state):
        if modifier.target_id is not None and modifier.target_id != id(p):
            continue
        if modifier.kind == "grant_keyword" and modifier.keyword:
            out.add(modifier.keyword)
    return out


_V460_effective_keywords_old = effective_keywords
def effective_keywords(p: Permanent) -> Set[str]:
    # Backwards-compatible helper when no state is available.
    return _V460_effective_keywords_old(p)


def effective_keywords_in_state(p: Permanent, state: GameState) -> Set[str]:
    out = _V460_effective_keywords_old(p)
    out.update(_modifier_keywords_for(p, state))
    out.update(equipment_model.equipment_granted_keywords(state, p))

    for source in state.battlefield:
        if source.card.name in DEDICATED_RESOLVERS:
            continue
        for ability in parse_oracle_semantics(source.card):
            if ability.ability_kind != "static":
                continue
            for action in ability.actions:
                if action.kind == "grant_team_keyword" and action.keyword:
                    out.add(action.keyword)
    return out


def _semantic_target_creature(
    state: GameState,
    source: Optional[Permanent],
    text: str = "",
) -> Optional[Permanent]:
    # v4.31.0 fix (found via ChatGPT external review, Docs/README.md
    # v4.31.0 entry): this used to exclude `source` unconditionally
    # whenever any other creature existed, regardless of what the ability's
    # own text actually says - so "{T}: Put a +1/+1 counter on this
    # creature." on a permanent sharing the battlefield with other
    # creatures put the counter on a DIFFERENT creature instead of itself.
    # `text_references_source` (already used the same way by
    # _apply_semantic_protection_effect below) tells self-referential
    # phrasing ("this creature"/"this permanent"/"itself"/the card's own
    # name) apart from genuine other-creature targeting ("target
    # creature"/"another target creature") - only the latter should ever
    # exclude `source`.
    if source is not None and source.card.is_creature and text_references_source(source.card, text):
        return source
    candidates = [
        p for p in state.creatures()
        if source is None or p is not source
    ]
    if not candidates:
        return source if source and source.card.is_creature else None
    return max(
        candidates,
        key=lambda p: generic_tutor_score(p.card, DEFAULT_TUTOR_PRIORITY),
    )


def execute_semantic_action(
    state: GameState,
    strategy: Strategy,
    source: Optional[Permanent],
    action: SemanticAction,
    *,
    target: Optional[Permanent] = None,
) -> bool:
    """
    Dispatches to App/keyword_library. The registry looks up `action.kind` in
    definitions.json and calls the matching handler in keyword_library/handlers.py;
    `ops=sys.modules[__name__]` (this module) supplies the actual primitives
    (gain_life, draw_cards, scry, ...) the handlers call.

    New mechanically-equivalent keywords (see Docs for the Hobbit-mechanic example)
    are added by editing definitions.json only - no change needed here.
    """
    target = target or _semantic_target_creature(state, source, action.raw)
    handled = keyword_registry.resolve_action(
        sys.modules[__name__], state, strategy, source, action, target=target,
    )
    if not handled:
        record_engine_metric(state, f"unhandled_semantic_action:{action.kind}")
    return handled


def execute_semantic_ability(
    state: GameState,
    strategy: Strategy,
    source: Permanent,
    ability: SemanticAbility,
    *,
    target: Optional[Permanent] = None,
    already_paid: bool = False,
) -> bool:
    # v4.15.6: never auto-execute a cost this parser cannot actually collect.
    # "Sacrifice another creature or artifact"-shaped costs (Baron Bertram
    # Graywater) don't match the Food/Treasure/Clue sacrifice_resource
    # patterns, so without this guard the mana portion alone would already
    # satisfy the caller and the effect would fire for free - see the
    # unrecognized_sacrifice_cost docstring at its parse site.
    if ability.unrecognized_sacrifice_cost:
        return False
    reservation = reservation_for_resource(ability.sacrifice_resource, 1)
    if ability.remove_source_counter:
        if source.named_counters.get(ability.remove_source_counter, 0) <= 0:
            return False
    if ability.sacrifice_resource == "Food" and state.food <= 0:
        return False
    if ability.sacrifice_resource == "Treasure" and state.treasure <= 0:
        return False
    if ability.sacrifice_resource == "Clue" and state.clues <= 0:
        return False
    if ability.tap_source and (source.tapped or not _perm_ready(source, state)):
        return False
    # v4.26.0: a "Discard N cards" activation cost must actually be payable
    # (enough cards in hand) before this ability is allowed to auto-execute -
    # same "fail closed, don't hand out the effect for less than its real
    # cost" precedent as the Food/Treasure/Clue checks above.
    if ability.discard_count and len(state.hand) < ability.discard_count:
        return False

    if not already_paid:
        payment = find_payment(
            state,
            strategy,
            ability.mana_total,
            ability.mana_requirements,
            reservation=reservation,
        )
        if payment is None:
            return False
        apply_payment(state, payment, strategy)

        if ability.tap_source:
            idx = state.battlefield.index(source)
            tap_permanent(state, strategy, idx, reason="semantic ability")

        if ability.sacrifice_resource == "Food":
            state.food -= 1
            token_sacrificed(state, "Food", 1, strategy)
        elif ability.sacrifice_resource == "Treasure":
            state.treasure -= 1
            token_sacrificed(state, "Treasure", 1, strategy)
        elif ability.sacrifice_resource == "Clue":
            state.clues -= 1
            token_sacrificed(state, "Clue", 1, strategy)

        if ability.remove_source_counter:
            source.named_counters[ability.remove_source_counter] -= 1
            if source.named_counters[ability.remove_source_counter] <= 0:
                del source.named_counters[ability.remove_source_counter]

        # v4.26.0: actually pay a "Discard N cards" cost, same
        # most-disposable-first heuristic already used for Connive.
        for _ in range(min(ability.discard_count, len(state.hand))):
            discarded = min(state.hand, key=lambda c: discard_score(c, state))
            state.hand.remove(discarded)
            state.graveyard.append(discarded)
            state.log(f"{source.card.name}: discarded {discarded.name} (activation cost)")

    did = False
    for action in ability.actions:
        did = execute_semantic_action(
            state, strategy, source, action, target=target
        ) or did

    if did:
        record_impact(state, source.card.name, "semantic_ability_uses", 1)
        state.log(
            f"SEMANTIC EXECUTE [{ability.execution_mode}]: "
            f"{source.card.name}: {ability.raw}"
        )
    guard_resource_invariants(state, f"semantic {source.card.name}")
    return did


DEDICATED_RESOLVERS = {
    BILBO_NAME: "111-life command-zone activation and creature pile resolver",
    DOCTOR_STRANGE_NAME: "lifegain replacement and combat buff",
    HONOR_TROLL_NAME: "lifegain +1 replacement",
    ARCHIVE_NAME: "lifegain/draw replacement support",
    "Peregrin Took": "token replacement and 3-Food draw",
    "Tippy-Toe, Terrific Partner": "token replacement and lifegain end-step draw",
    "Mirkwood Bats": "token create/sacrifice drain",
    "Kambal, Profiteering Mayor": "your-token batch drain/lifegain",
    "Gyome, Master Chef": "end-step Food plus generic semantic protection outlet",
    "Heroic Feast": "ETB Food and lifegain counter distribution",
    "Baron Bertram Graywater": "token-enter Vampire generation plus real Treasure-sacrifice-to-draw (v4.15.6, use_baron_bertram_sac_draw) - MUST stay excluded from try_generic_semantic_activations: its 'Sacrifice another creature or artifact' cost text isn't recognized by the generic sacrifice-cost parser (only Food/Treasure/Clue are), so the generic path would otherwise auto-fire 'Draw a card' for {1}{B} alone with no sacrifice paid at all.",
    "Trudge Garden": "per-lifegain-event {2}->4/4 trample token (v4.15.6, use_trudge_garden)",
    "Field-Tested Frying Pan": "ETB Food/Halfling plus equipped-creature lifegain pump (v4.15.6)",
    "Moldervine Reclamation": "creature-death gain-life/draw, both Permanent and token-group deaths (v4.15.6)",
    "Blossoming Bogbeast": "attack lifegain and life-gained-this-turn pump",
    "Speaker of the Heavens": "47-life Angel activation",
    "Well of Lost Dreams": "lifegain-trigger mana-to-draw allocation",
    "Lobelia, Defender of Bag End": "artifact-sacrifice drain/lifegain mode",
    "Gilded Goose": "Food ETB and Food-to-mana source",
    "Unlucky Cabbage Merchant": "Food ETB and Food-sacrifice ramp approximation",
    "Suffer the Past": "dynamic X-spell graveyard/lifegain/drain resolver",
    "The Arkenstone": "Adventure tutor and delayed permanent cast",
    KATARA_HOPE_NAME: "post-attack Waterbend X activation via the resource planner",
    AZIZA_NAME: "cast-triggered instant/sorcery copy, gated on a real tap-3-creatures cost",
    MICA_NAME: "cast-triggered instant/sorcery copy, gated on a real artifact-sacrifice cost",
    "Old Gnawbone": "combat-damage-to-player -> that-many-Treasure trigger (v4.18.0)",
}


def has_dedicated_resolver(card: Card) -> bool:
    return card.name in DEDICATED_RESOLVERS






def probabilistic_semantic_probability(
    ability: SemanticAbility,
    strategy: Strategy,
    state: GameState,
) -> float:
    low = ability.raw.lower()
    base = {
        "goldfish": .12,
        "aggro": .55,
        "midrange": .48,
        "control": .50,
        "horde": .65,
    }.get(strategy.opponent_profile, .40)

    if "casts" in low or "cast a spell" in low:
        base += .08
    if "creates" in low or "token" in low:
        base += .05
    return max(.05, min(.85, base))


def try_probabilistic_semantics(
    state: GameState,
    strategy: Strategy,
    rng: random.Random,
) -> int:
    used = getattr(state, "_semantic_probabilistic_this_turn", set())
    fired = 0

    for source in list(state.battlefield):
        if has_dedicated_resolver(source.card):
            continue
        for ability in parse_oracle_semantics(source.card):
            if ability.execution_mode != "probabilistic" or not ability.actions:
                continue
            key = (id(source), ability.raw)
            if key in used:
                continue
            probability = probabilistic_semantic_probability(
                ability, strategy, state
            )
            used.add(key)
            if rng.random() <= probability:
                for action in ability.actions:
                    execute_semantic_action(
                        state, strategy, source, action
                    )
                record_impact(
                    state, source.card.name,
                    "semantic_probabilistic_events", 1,
                )
                state.log(
                    f"SEMANTIC PROBABILISTIC ({probability:.2f}): "
                    f"{source.card.name}: {ability.raw}"
                )
                fired += 1

    state._semantic_probabilistic_this_turn = used
    return fired


_V460_on_permanent_tapped_old = on_permanent_tapped
def on_permanent_tapped(
    state: GameState,
    strategy: Optional[Strategy],
    p: Permanent,
    reason: str = "tap",
):
    if strategy is None:
        return
    matched = False
    for ability in parse_oracle_semantics(p.card):
        if ability.trigger != "becomes_tapped" or not ability.actions:
            continue
        matched = True
        # Trigger has no activation cost; execute the actions directly.
        for action in ability.actions:
            execute_semantic_action(
                state, strategy, p, action, target=p
            )
        record_impact(state, p.card.name, "semantic_ability_uses", 1)
    if not matched:
        _V460_on_permanent_tapped_old(state, strategy, p, reason)


_V460_end_step_old = end_step


# ---------------------------------------------------------------------------
# Typed interaction phase
# ---------------------------------------------------------------------------

def apply_abstract_opponent_phase(
    state: GameState,
    strategy: Strategy,
    rng: random.Random,
):
    profile = OPPONENT_PROFILES.get(
        strategy.opponent_profile,
        OPPONENT_PROFILES["goldfish"],
    )
    if strategy.opponent_profile == "goldfish":
        state.virtual_opponent_graveyard = max(
            state.virtual_opponent_graveyard,
            max(0, int(state.turn * 1.25 - 1)),
        )
        try_probabilistic_semantics(state, strategy, rng)
        apply_commander_zone_state_based_actions(state, strategy)
        guard_resource_invariants(state, "goldfish opponent phase")
        return

    state.virtual_opponent_graveyard += max(
        1, int(0.8 + state.turn * 0.25)
    )
    try_probabilistic_semantics(state, strategy, rng)

    if strategy.opponent_profile == "horde":
        damage = max(0.0, (state.turn - 4) * profile["damage_scale"])
    elif strategy.opponent_profile == "aggro":
        damage = max(0.0, (state.turn - 1) * profile["damage_scale"])
    elif strategy.opponent_profile == "midrange":
        damage = max(0.0, (state.turn - 2) * profile["damage_scale"])
    else:
        damage = max(0.0, (state.turn - 4) * profile["damage_scale"])

    if damage > 0:
        damage *= rng.uniform(0.70, 1.30)
        state.life -= damage
        state.damage_taken += damage
        state.log(
            f"ABSTRACT {strategy.opponent_profile}: "
            f"took {damage:.1f} combat/pressure damage"
        )
        if state.life <= 0 and state.lost_turn is None:
            state.lost_turn = state.turn

    # Spot removal with explicit removal type.
    if state.turn >= 3 and rng.random() < profile["removal"]:
        targets = [
            p for p in state.battlefield
            if not p.card.is_land and p.card.is_permanent
        ]
        if targets:
            target = combat_importance.choose_removal_target(
                sys.modules[__name__], state, strategy, targets, rng
            )
            removal_type = choose_removal_type(
                strategy.opponent_profile, rng, wide=False
            )
            kws = effective_keywords_in_state(target, state)

            if "hexproof" in kws:
                state.log(
                    f"ABSTRACT {removal_type} failed: "
                    f"{target.card.name} has hexproof"
                )
            elif "ward" in kws and rng.random() < 0.35:
                state.log(
                    f"ABSTRACT {removal_type} declined/failed into ward "
                    f"on {target.card.name}"
                )
            elif try_reactive_protection(
                state, strategy,
                wide=False,
                removal_type=removal_type,
                target=target,
            ):
                pass
            elif removal_type == "destroy" and "indestructible" in kws:
                state.log(
                    f"ABSTRACT destroy failed: "
                    f"{target.card.name} is indestructible"
                )
            elif removal_type == "destroy" and try_semantic_board_protection(
                state, strategy, target
            ):
                pass
            else:
                _spot_remove_target(
                    state, strategy, target, removal_type
                )
                record_impact(state, target.card.name, "removed_by_opponent", 1)
                state.log(
                    f"ABSTRACT {removal_type}: {target.card.name}"
                )

    # Board wipe with explicit effect type.
    if state.turn >= 5 and rng.random() < profile["wipe"]:
        removal_type = choose_removal_type(
            strategy.opponent_profile, rng, wide=True
        )

        if try_reactive_protection(
            state, strategy,
            wide=True,
            removal_type=removal_type,
        ):
            # For destroy + Heroic, the spell has only granted indestructible;
            # the wipe still resolves, so remove unprotected creatures below.
            if removal_type != "destroy" or any(
                "exile any number of target creatures you control"
                in strip_reminder_text(c.oracle_text).lower()
                for c in state.graveyard[-1:]
            ):
                guard_resource_invariants(state, "protected wipe")
                return

        survivors = set()
        if removal_type == "destroy":
            candidates = sorted(
                list(state.creatures()),
                key=lambda p: generic_tutor_score(
                    p.card, strategy.tutor_priority
                ),
                reverse=True,
            )
            for p in candidates:
                if "indestructible" in effective_keywords_in_state(p, state):
                    survivors.add(id(p))
                    continue
                if try_semantic_board_protection(state, strategy, p):
                    survivors.add(id(p))

        affected = []
        destination = _wipe_destination(removal_type)
        for p in list(state.battlefield):
            if not p.card.is_creature:
                continue
            if removal_type == "destroy":
                if id(p) in survivors or "indestructible" in effective_keywords_in_state(p, state):
                    continue
            affected.append(p.card.name)
            record_impact(state, p.card.name, "wiped_by_opponent", 1)
            move_permanent_to_zone(
                state, strategy, p, destination,
                reason=f"{removal_type} boardwipe",
            )

        if affected:
            state.log(
                f"ABSTRACT {removal_type} boardwipe: "
                + ", ".join(affected)
            )

    apply_commander_zone_state_based_actions(state, strategy)
    guard_resource_invariants(state, "abstract opponent phase")


# ---------------------------------------------------------------------------
# Commander casting/reporting
# ---------------------------------------------------------------------------

def _record_commander_game_cast(state: GameState, commander: Card):
    casted = getattr(state, "_commander_games_cast", set())
    if commander.name not in casted:
        record_impact(
            state, commander.name,
            "commander_games_cast", 1,
        )
        casted.add(commander.name)
        state._commander_games_cast = casted


def cast_one_commander_v41(
    state: GameState,
    strategy: ScenarioStrategy,
) -> Optional[str]:
    # Supported self-recurring commanders intentionally left in graveyard/exile.
    special = []
    for zone_name, zone in (
        ("graveyard", state.graveyard),
        ("exile", state.exile),
    ):
        for commander in list(zone):
            if (
                not commander.commander
                or zone_name not in commander_self_cast_zones(commander)
            ):
                continue
            discount, attribution = effective_cost_discount(
                commander, state
            )
            total = max(
                sum(commander.color_requirements.values()),
                commander.min_cost - discount,
            )
            payment = find_payment(
                state, strategy, total,
                commander.color_requirements,
            )
            if payment:
                score = 5.2 - total * 0.1
                if (
                    "lifegain_replacement" in commander.roles
                    and "lifegain" in strategy.archetypes
                ):
                    score += 4
                special.append((
                    score, zone_name, commander,
                    total, payment, attribution,
                ))

    if special:
        (
            _score, zone_name, commander,
            total, payment, attribution,
        ) = max(special, key=lambda x: x[0])
        apply_payment(state, payment, strategy)
        for source, amount in attribution.items():
            record_impact(
                state, source, "mana_discount", amount
            )
        zone = (
            state.graveyard
            if zone_name == "graveyard"
            else state.exile
        )
        zone.remove(commander)
        state.commander_casts += 1
        _record_commander_game_cast(state, commander)
        record_impact(state, commander.name, "cast", 1)
        record_impact(state, commander.name, "mana_spent", total)
        record_impact(
            state, commander.name,
            "commander_special_zone_cast", 1,
        )
        permanent_enters(state, strategy, commander)
        record_impact(state, commander.name, "entered", 1)
        state.log(
            f"CAST COMMANDER {commander.name} "
            f"FROM {zone_name.upper()}"
        )
        return commander.name

    if not state.command_zone:
        return None

    options = []
    for commander in list(state.command_zone):
        tax_count = int(
            state.commander_cast_counts[commander.name]
        )
        tax = 2 * tax_count
        base = commander.min_cost + tax
        discount, attribution = effective_cost_discount(
            commander, state
        )
        total = max(
            sum(commander.color_requirements.values()),
            base - discount,
        )
        payment = find_payment(
            state, strategy, total,
            commander.color_requirements,
        )
        if payment:
            score = (
                5.0 - total * 0.1
                + _scenario_commander_bonus(
                    state, strategy, commander.name
                )
            )
            if (
                "lifegain_replacement" in commander.roles
                and "lifegain" in strategy.archetypes
            ):
                score += 5
            options.append((
                score, commander, total, payment,
                attribution, tax,
            ))

    if not options:
        return None

    (
        _score, commander, total, payment,
        attribution, tax,
    ) = max(options, key=lambda x: x[0])

    apply_payment(state, payment, strategy)
    state.command_zone.remove(commander)
    state.commander_cast_counts[commander.name] += 1
    state.commander_casts += 1
    _record_commander_game_cast(state, commander)
    record_impact(state, commander.name, "cast", 1)
    record_impact(state, commander.name, "mana_spent", total)
    record_impact(
        state, commander.name,
        "commander_command_zone_cast", 1,
    )
    record_impact(
        state, commander.name,
        "commander_tax_paid", tax,
    )
    permanent_enters(state, strategy, commander)
    record_impact(state, commander.name, "entered", 1)

    state.log(
        f"CAST COMMANDER {commander.name} "
        f"(tax {tax}, total {total})"
    )
    return commander.name


# ---------------------------------------------------------------------------
# 10) Output/reporting: commander stats, semantic vs dedicated, invariants
# ---------------------------------------------------------------------------

_V460_impact_rows_old = impact_rows_from_aggregate
def impact_rows_from_aggregate(
    deck: List[Card],
    aggregate: Dict[str, Counter],
    runs: int,
    strategy: Strategy,
) -> List[dict]:
    rows = _V460_impact_rows_old(
        deck, aggregate, runs, strategy
    )
    by_name = {c.name: c for c in deck}

    for row in rows:
        c = by_name.get(row["Name"])
        metrics = aggregate.get(row["Name"], Counter())
        if c and c.commander:
            games_cast = float(
                metrics.get("commander_games_cast", 0)
            )
            total_casts = float(metrics.get("cast", 0))
            row["Cast rate when seen %"] = (
                round(
                    100 * games_cast / row["Seen"], 2
                )
                if row["Seen"] else 0
            )
            row["Commander games cast"] = round(
                games_cast, 2
            )
            row["Commander games cast %"] = round(
                100 * games_cast / max(1, runs), 2
            )
            row["Avg commander casts / run"] = round(
                total_casts / max(1, runs), 3
            )
            row["Avg casts when commander appeared"] = (
                round(total_casts / games_cast, 3)
                if games_cast else 0
            )
            row["Command-zone casts"] = round(
                metrics.get(
                    "commander_command_zone_cast", 0
                ), 2
            )
            row["Hand casts"] = round(
                metrics.get("commander_hand_cast", 0), 2
            )
            row["Special-zone casts"] = round(
                metrics.get(
                    "commander_special_zone_cast", 0
                ), 2
            )
            row["Commander zone returns"] = round(
                metrics.get(
                    "commander_zone_return", 0
                ), 2
            )
            row["Commander tax paid"] = round(
                metrics.get(
                    "commander_tax_paid", 0
                ), 2
            )
        else:
            row["Commander games cast"] = ""
            row["Commander games cast %"] = ""
            row["Avg commander casts / run"] = ""
            row["Avg casts when commander appeared"] = ""
            row["Command-zone casts"] = ""
            row["Hand casts"] = ""
            row["Special-zone casts"] = ""
            row["Commander zone returns"] = ""
            row["Commander tax paid"] = ""

    return rows


_V460_coverage_old = card_model_coverage_rows
def card_model_coverage_rows(
    deck: List[Card],
) -> List[dict]:
    rows = _V460_coverage_old(deck)
    by_name = {c.name: c for c in deck}

    for row in rows:
        card = by_name.get(row["Name"])
        if not card:
            continue

        # v4.19.0: planeswalkers are diverse enough (10 different cards
        # already across the audited real decks) that hand-writing a
        # KNOWN_COVERAGE_NOTES entry per card doesn't scale the way it does
        # for a handful of hardcoded engine-role cards - so this is a type-
        # level note, generated from what actually determines a specific
        # planeswalker's coverage: whether ANY of its loyalty abilities
        # parsed at least one executable action (see
        # activate_planeswalker_loyalty_abilities's module comment for
        # exactly what that vocabulary covers and excludes).
        if card.is_planeswalker and card.name not in KNOWN_COVERAGE_NOTES:
            loyalty_abilities = parse_loyalty_abilities(card)
            executable_abilities = [a for a in loyalty_abilities if a.actions]
            if executable_abilities:
                row["Coverage"] = "partial"
                row["Modeled / review note"] = (
                    f"loyalty tracked from {card.loyalty!r} starting counters; "
                    f"once per turn the engine auto-activates whichever affordable "
                    f"ability scores highest, but only "
                    f"{len(executable_abilities)}/{len(loyalty_abilities)} of its "
                    f"printed loyalty abilities have an effect this engine can "
                    f"actually execute (damage-to-a-player-shaped target / draw / "
                    f"gain life / create tokens) - the rest (board-affecting exile, "
                    f"targeting an opponent's permanent, temporary type changes, "
                    f"emblems, ...) are recognized as loyalty abilities but not "
                    f"executed."
                )
            else:
                row["Coverage"] = "generic"
                row["Modeled / review note"] = (
                    f"loyalty tracked from {card.loyalty!r} starting counters, but "
                    f"none of its {len(loyalty_abilities)} printed loyalty "
                    f"abilities have an effect in this engine's generic action "
                    f"vocabulary (damage-to-a-player-shaped target / draw / gain "
                    f"life / create tokens) - it is cast and sits on the "
                    f"battlefield but never activates anything."
                )

        # v4.20.0: Battles, same reasoning as the planeswalker block above -
        # a type-level note rather than a per-card KNOWN_COVERAGE_NOTES
        # entry, generated from what actually determines a specific
        # Battle's coverage: whether its back face (if any) parses to at
        # least one executable action (see complete_battle's module
        # comment for the exact vocabulary and scope boundaries).
        if card.is_battle and card.name not in KNOWN_COVERAGE_NOTES:
            back_face_text = (
                card.oracle_text.split("\n//\n", 1)[1]
                if "\n//\n" in card.oracle_text else ""
            )
            reward_actions = (
                [a for a in _parse_semantic_actions(back_face_text) if a.kind]
                if back_face_text else []
            )
            row["Coverage"] = "partial" if reward_actions else "generic"
            row["Modeled / review note"] = (
                f"defense tracked from {card.defense!r} starting counters; "
                f"our own creatures (never opponent's, since this engine "
                f"models no opposing board) are diverted to attack it down "
                f"before the normal player-facing combat step, smallest-"
                f"power-first, unconditionally connecting (no blockers "
                f"modeled anywhere in this engine). On defeat it moves to "
                f"the graveyard"
                + (
                    f"; its back face's reward ({len(reward_actions)} "
                    f"executable action(s)) fires once as an approximation "
                    f"of the flip, but is NOT modeled as an ongoing "
                    f"permanent (no general transform/DFC support exists "
                    f"anywhere in this engine)."
                    if reward_actions else
                    "; its back face (if any) has no effect in this "
                    "engine's generic action vocabulary, so completion "
                    "carries no reward."
                )
            )

        abilities = parse_oracle_semantics(card)
        executable = sum(
            1 for ability in abilities
            if ability.actions
            and ability.execution_mode
            in {"exact", "simplified", "probabilistic"}
        )
        row["Generic semantic runtime coverage"] = (
            f"{executable}/{len(abilities)} parsed "
            f"ability lines executable/approximable"
            if abilities else "0/0"
        )
        row["Dedicated resolver"] = (
            "yes" if has_dedicated_resolver(card)
            else "no"
        )
        row["Dedicated resolver note"] = (
            DEDICATED_RESOLVERS.get(card.name, "")
        )
        row["Semantic parser cached"] = "yes"

    return rows


_V460_stats_add_old = StreamingStatsV440.add
def _streaming_stats_add_v460(
    self, rr: dict, tr: List[dict], sr: List[dict]
):
    _V460_stats_add_old(self, rr, tr, sr)
    self.sums["resource_invariant_violations"] += float(
        rr.get("resource_invariant_violations", 0) or 0
    )
    self.sums["payment_resource_conflicts"] += float(
        rr.get("payment_resource_conflicts", 0) or 0
    )
StreamingStatsV440.add = _streaming_stats_add_v460


_V460_simulate_game_old = simulate_game_v440
def simulate_game_v440(*args, **kwargs):
    rr, tr, oh, impact, sr = _V460_simulate_game_old(
        *args, **kwargs
    )
    engine_metrics = impact.get("__ENGINE__", Counter())
    endpoint_violations = 0
    for key in ("food_end", "treasure_end"):
        if float(rr.get(key, 0) or 0) < 0:
            endpoint_violations += 1
    for row in tr:
        if (
            float(row.get("food", 0) or 0) < 0
            or float(row.get("treasure", 0) or 0) < 0
            or float(row.get("clues", 0) or 0) < 0
        ):
            endpoint_violations += 1

    rr["resource_invariant_violations"] = int(
        endpoint_violations
        + engine_metrics.get("negative_food", 0)
        + engine_metrics.get("negative_treasure", 0)
        + engine_metrics.get("negative_clues", 0)
    )
    rr["payment_resource_conflicts"] = int(
        engine_metrics.get(
            "payment_resource_conflict", 0
        )
        + engine_metrics.get(
            "additional_cost_conflict", 0
        )
        + engine_metrics.get(
            "semantic_resource_conflict", 0
        )
        + engine_metrics.get(
            "semantic_counter_conflict", 0
        )
    )
    return rr, tr, oh, impact, sr


_V460_summary_old = streaming_summary_v440
def streaming_summary_v440(
    deck: List[Card],
    stats: StreamingStatsV440,
    cfg: SimConfig,
    strategy: ScenarioStrategy,
    impact_rows: List[dict],
    detailed_runs_logged: int,
    log_policy: str,
) -> dict:
    data = _V460_summary_old(
        deck, stats, cfg, strategy,
        impact_rows, detailed_runs_logged,
        log_policy,
    )
    data["version"] = "4.6.0"
    data["simulation"]["semantic_runtime_version"] = (
        SEMANTIC_RUNTIME_VERSION
    )
    data["simulation"]["semantic_parse_cache"] = {
        "entries": len(_SEMANTIC_CACHE),
        "hits": _SEMANTIC_CACHE_HITS,
        "misses": _SEMANTIC_CACHE_MISSES,
    }
    data["engine_invariants"] = {
        "resource_invariant_violations": int(
            stats.sums["resource_invariant_violations"]
        ),
        "payment_resource_conflicts": int(
            stats.sums["payment_resource_conflicts"]
        ),
        "status": (
            "PASS"
            if (
                stats.sums["resource_invariant_violations"] == 0
                and stats.sums["payment_resource_conflicts"] == 0
            )
            else "REVIEW"
        ),
    }
    data.setdefault("limitations", []).extend([
        "Reactive protection now pays real mana; Eerie Interlude is represented as a blink/return with ETB re-entry, but priority and stack interactions remain simplified.",
        "Abstract interaction distinguishes destroy/exile/bounce/shrink/tuck; this is a stress-test distribution, not a prediction of a specific metagame.",
        "The generic semantic executor currently executes supported actions for simple activated/tapped/opponent-dependent abilities; a complete Magic event bus is still outside scope.",
        "Probabilistic semantic effects use explicit conservative opponent-profile probabilities and are labeled as approximations in logs/output.",
        "Board modifiers support temporary base-P/T and keyword-style state, providing a foundation for Waterbend-like mechanics; not every global Oracle template is parsed yet.",
    ])
    return data


def write_semantic_runtime_report(
    path: Path,
    deck: List[Card],
):
    rows = []
    seen = set()
    for card in deck:
        if card.name in seen:
            continue
        seen.add(card.name)
        abilities = parse_oracle_semantics(card)
        for i, ability in enumerate(abilities, 1):
            rows.append({
                "Name": card.name,
                "Ability #": i,
                "Ability type": ability.ability_kind,
                "Trigger": ability.trigger,
                "Execution mode": ability.execution_mode,
                "Confidence": ability.confidence,
                "Actions": " | ".join(
                    a.kind + (
                        f":{a.keyword}"
                        if a.keyword else ""
                    )
                    for a in ability.actions
                ),
                "Dedicated resolver": (
                    "yes"
                    if has_dedicated_resolver(card)
                    else "no"
                ),
                "Dedicated resolver note": (
                    DEDICATED_RESOLVERS.get(
                        card.name, ""
                    )
                ),
                "Oracle line": ability.raw,
            })
    write_csv(path, rows)


# Wrap pipeline only to add runtime report and stronger AI note to the ZIP folder.
_V460_run_pipeline_old = run_pipeline_v440
def run_pipeline_v440(*args, **kwargs):
    result = _V460_run_pipeline_old(
        *args, **kwargs
    )
    result_dir = Path(result["result_dir"])
    deck = result["deck"]

    write_semantic_runtime_report(
        result_dir / "semantic_runtime_report.csv",
        deck,
    )

    ai_path = result_dir / "AI_ANALYSIS_INSTRUCTIONS.md"
    with ai_path.open("a", encoding="utf-8") as fh:
        fh.write("""

## v4.6 engine-integrity checks
Read `summary.json -> engine_invariants` before interpreting deck results.
If status is not PASS, resource-related conclusions require review.

Use both:
- `card_model_coverage.csv` for generic semantic coverage vs dedicated resolvers;
- `semantic_runtime_report.csv` for per-Oracle-line execution mode.

Commander rows in `card_impact.csv` use game-level commander cast rate rather than
total recasts / seen, and separately report Command Zone casts, hand/special-zone casts,
returns, and Commander tax.
""")

    # The old pipeline zipped before this wrapper added the new report/note.
    # Rebuild the ZIP so the user handoff contains the final v4.6 files.
    zip_path = Path(result["zip_path"])
    with _zipfile.ZipFile(
        zip_path, "w",
        compression=_zipfile.ZIP_DEFLATED,
    ) as zf:
        for f in result_dir.rglob("*"):
            if f.is_file():
                zf.write(
                    f, arcname=f.relative_to(result_dir)
                )

    return result



_V460_sacrifice_food_for_life_old = sacrifice_food_for_life
def sacrifice_food_for_life(
    state: GameState,
    strategy: Strategy,
) -> bool:
    if state.food <= 0:
        return False
    plan = find_payment(
        state, strategy, 2, Counter(),
        reservation=ResourceReservation(food=1),
    )
    if not plan:
        return False
    apply_payment(state, plan, strategy)
    if state.food <= 0:
        record_engine_metric(
            state, "semantic_resource_conflict", 1
        )
        return False
    state.food -= 1
    token_sacrificed(state, "Food", 1, strategy)
    gain_life(state, 3, "Food")
    state.log("Food sacrificed for life")
    guard_resource_invariants(
        state, "Food life activation"
    )
    return True


def use_clue(
    state: GameState,
    strategy: Strategy,
) -> bool:
    if state.clues <= 0:
        return False
    plan = find_payment(
        state, strategy, 2, Counter(),
        reservation=ResourceReservation(clues=1),
    )
    if not plan:
        return False
    apply_payment(state, plan, strategy)
    if state.clues <= 0:
        record_engine_metric(
            state, "semantic_resource_conflict", 1
        )
        return False
    state.clues -= 1
    token_sacrificed(state, "Clue", 1, strategy)
    draw_cards(state, 1, reason="Clue")
    guard_resource_invariants(
        state, "Clue draw activation"
    )
    return True



def main_v460():
    ap = argparse.ArgumentParser(
        description="Commander Goldfish Simulator v4.6.0"
    )
    ap.add_argument("deck_file", nargs="?", type=Path)
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--metadata-csv", type=Path, default=None)
    ap.add_argument("--strategy", type=Path, default=None)
    ap.add_argument("--tags", default="")
    ap.add_argument(
        "--opponent",
        choices=sorted(OPPONENT_PROFILES),
        default="goldfish",
    )
    ap.add_argument("--value-model", type=Path, default=None)
    ap.add_argument("--scenarios", type=Path, default=None)
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        try:
            from App.gui import launch_gui
        except ImportError:
            from gui import launch_gui  # engine.py run standalone, gui.py alongside it
        launch_gui()
        return

    ensure_runtime_dependencies(
        include_images=False,
        status_callback=print,
    )
    commanders = (
        list(args.commander)
        or detect_commander_hints(args.deck_file)
    )
    if not commanders:
        raise SystemExit(
            "No commander detected. Use --commander or the GUI."
        )

    tags = {
        x.strip().lower()
        for x in args.tags.split(",")
        if x.strip()
    }
    result = run_pipeline_v440(
        args.deck_file,
        commanders,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.6.0 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])




# ===========================================================================
# v4.7.0 — DASHBOARD / RANDOM OPPONENT / SEMANTIC TIMING HARDENING
# ===========================================================================

RANDOM_OPPONENT_CHOICES = ("aggro", "midrange", "control", "horde")
# Pseudo-profile so CLI/GUI can expose "random". Individual games replace it
# with one of RANDOM_OPPONENT_CHOICES before game logic starts.
OPPONENT_PROFILES.setdefault(
    "random",
    {
        "damage_scale": 0.0,
        "removal": 0.0,
        "wipe": 0.0,
        "block_factor": 1.0,
    },
)


# ---------------------------------------------------------------------------
# Reproducible zone movement
# ---------------------------------------------------------------------------

def move_permanent_to_zone(
    state: GameState,
    strategy: Strategy,
    permanent: Permanent,
    destination: str,
    *,
    reason: str = "",
    rng: Optional[random.Random] = None,
):
    if permanent not in state.battlefield:
        return

    card = permanent.card
    state.battlefield.remove(permanent)

    if destination in {"hand", "library"} and card.commander:
        chosen = commander_replacement_for_hidden_zone(
            state, strategy, card, destination
        )
        if chosen == "command_zone":
            state.command_zone.append(card)
            record_impact(state, card.name, "commander_zone_return", 1)
            state.log(
                f"COMMANDER replacement: {card.name} -> command zone "
                f"instead of {destination}"
            )
            return
        destination = chosen

    if destination == "graveyard":
        state.graveyard.append(card)
        apply_commander_zone_state_based_actions(state, strategy)
        # v4.15.6: Moldervine Reclamation ("Whenever a creature you control
        # dies, you gain 1 life and draw a card.") - "dies" = battlefield ->
        # graveyard, exactly this branch. Covers combat deaths and any other
        # real Permanent-creature death that routes through this shared
        # zone-move function, closing the "creature-death events are only
        # partially represented" gap (KNOWN_COVERAGE_NOTES) for the
        # Permanent case. Token-creature deaths (TokenGroup.count
        # decremented, never a Permanent, never routed through here) are
        # handled by a separate hook in attack_phase.
        if card.is_creature and state.has("Moldervine Reclamation"):
            gain_life(state, 1, "Moldervine Reclamation")
            draw_cards(state, 1, reason="Moldervine Reclamation")

        # v4.21.0: Persist / Undying. Same shared root as the Moldervine
        # hook above - this branch is every real nontoken-creature death,
        # regardless of cause (combat, sacrifice, Battle interactions, a
        # future Devour sac, ...), which is exactly what these two "when
        # this creature dies" abilities need. A creature with BOTH (rare)
        # only gets one return in real rules (both trigger, but whichever
        # resolves first returns the creature, and the other ability's
        # source object is gone by the time it tries to resolve) - Undying
        # is checked first as an arbitrary-but-consistent tiebreak, no real
        # card in any audited deck has both to calibrate against. Only
        # fires if the card is still actually IN the graveyard after the
        # commander-SBA call above (a commander that died is likely to have
        # already been redirected to the command zone instead).
        if card.is_creature and card in state.graveyard:
            has_undying = "undying" in card.keywords or "undying" in permanent.temporary_keywords
            has_persist = "persist" in card.keywords or "persist" in permanent.temporary_keywords
            returned_as = None
            if has_undying and permanent.counters <= 0:
                returned_as = "undying"
            elif has_persist and permanent.minus1_counters <= 0:
                returned_as = "persist"
            if returned_as:
                state.graveyard.remove(card)
                new_p = Permanent(card=card, entered_turn=state.turn, tapped=False)
                if returned_as == "undying":
                    new_p.counters = 1
                else:
                    new_p.minus1_counters = 1
                state.battlefield.append(new_p)
                record_impact(state, card.name, returned_as, 1)
                state.log(
                    f"{returned_as.upper()}: {card.name} returns to the "
                    f"battlefield with a {'+1/+1' if returned_as == 'undying' else '-1/-1'} counter"
                )
    elif destination == "exile":
        state.exile.append(card)
        apply_commander_zone_state_based_actions(state, strategy)
    elif destination == "hand":
        state.hand.append(card)
        mark_seen(state, card)
    elif destination == "library":
        state.library.append(card)
        # Never use the module-global RNG: a fixed simulator seed must fully
        # reproduce the run. Abstract opponent calls pass their seeded rng.
        if rng is not None:
            rng.shuffle(state.library)
        else:
            # Deterministic fallback for non-simulation helper calls.
            card = state.library.pop()
            state.library.insert(0, card)
    else:
        raise ValueError(f"Unsupported destination: {destination}")

    state.log(
        f"ZONE MOVE: {card.name} -> {destination}"
        + (f" ({reason})" if reason else "")
    )


def _spot_remove_target(
    state: GameState,
    strategy: Strategy,
    target: Permanent,
    removal_type: str,
    rng: Optional[random.Random] = None,
):
    if removal_type in {"destroy", "shrink"}:
        move_permanent_to_zone(
            state, strategy, target, "graveyard",
            reason=removal_type, rng=rng,
        )
    elif removal_type == "exile":
        move_permanent_to_zone(
            state, strategy, target, "exile",
            reason=removal_type, rng=rng,
        )
    elif removal_type == "bounce":
        move_permanent_to_zone(
            state, strategy, target, "hand",
            reason=removal_type, rng=rng,
        )
    elif removal_type == "tuck":
        move_permanent_to_zone(
            state, strategy, target, "library",
            reason=removal_type, rng=rng,
        )


# ---------------------------------------------------------------------------
# Delayed blink: Eerie-style protection returns after opponent interaction.
# ---------------------------------------------------------------------------

def _blink_creatures(
    state: GameState,
    strategy: Strategy,
    targets: List[Permanent],
    source: str,
):
    cards = []
    for p in list(targets):
        if p not in state.battlefield:
            continue
        state.battlefield.remove(p)
        cards.append(p.card)

    if not cards:
        return

    queue = getattr(state, "_delayed_blink_queue", [])
    queue.append((source, cards))
    state._delayed_blink_queue = queue
    record_impact(state, source, "blinked_creatures", len(cards))
    state.log(
        f"{source}: exiled {len(cards)} creature(s); "
        "return queued after abstract interaction"
    )


def resolve_delayed_blinks(
    state: GameState,
    strategy: Strategy,
):
    queue = list(getattr(state, "_delayed_blink_queue", []))
    state._delayed_blink_queue = []
    for source, cards in queue:
        batch_creatures_enter(state, strategy, cards)
        state.log(
            f"{source}: returned {len(cards)} blinked creature(s)"
        )


# ---------------------------------------------------------------------------
# Semantic runtime timing
# ---------------------------------------------------------------------------

def semantic_action_timing(action: SemanticAction) -> str:
    """Coarse strategic timing category, not a Magic timing rule."""
    if action.kind in {
        "team_pt_bonus", "grant_team_keyword", "set_base_pt"
    }:
        return "precombat"
    if (
        action.kind == "grant_keyword_until_eot"
        and action.keyword in {
            "lifelink", "vigilance", "trample",
            "flying", "menace", "haste",
        }
    ):
        return "precombat"
    return "value"


def semantic_ability_score(
    ability: SemanticAbility,
    state: GameState,
    phase: str = "value",
) -> float:
    score = 0.0
    relevant_actions = []
    for action in ability.actions:
        timing = semantic_action_timing(action)
        if phase == "precombat" and timing != "precombat":
            continue
        if phase == "value" and timing == "precombat":
            continue
        relevant_actions.append(action)
        score += {
            "draw": 4.0,
            "scry": 1.0,
            "surveil": 1.2,
            "connive": 1.5,
            "gain_life": 1.2,
            "create_token": 1.5,
            "plus1_counter": 1.0,
            "keyword_counter": 1.2,
            "team_pt_bonus": 2.0,
            "grant_team_keyword": 1.7,
            "grant_keyword_until_eot": 1.3,
            "set_base_pt": -10.0,
        }.get(action.kind, 0.2)

    if not relevant_actions:
        return -999.0
    score -= ability.mana_total * 0.35
    # v4.26.0: a "Discard N cards" activation cost (now actually paid, see
    # execute_semantic_ability) has a real opportunity cost this scoring
    # function must weigh in, same direction/magnitude as the existing
    # discard_self=-1.20 constant in DEFAULT_VALUE_MODEL (App/engine.py) -
    # otherwise "Discard a card: Draw a card" scored as a flat +4.0 (pure
    # draw value), i.e. this engine would loot away real cards from hand
    # every single turn for no modeled downside at all.
    score -= ability.discard_count * 1.2
    return score


def try_generic_semantic_activations(
    state: GameState,
    strategy: Strategy,
    *,
    limit: int = 3,
    phase: str = "value",
) -> int:
    used = getattr(state, "_semantic_activated_this_turn", set())
    count = 0
    candidates = []

    for source in state.battlefield:
        if has_dedicated_resolver(source.card):
            continue
        for ability in parse_oracle_semantics(source.card):
            if ability.ability_kind != "activated":
                continue
            if not ability.actions:
                continue
            if any(
                a.kind == "grant_keyword_until_eot"
                and a.keyword == "indestructible"
                for a in ability.actions
            ):
                continue  # keep protection resource reactive
            key = (id(source), ability.raw)
            if key in used:
                continue
            candidates.append(
                (
                    semantic_ability_score(
                        ability, state, phase=phase
                    ),
                    source, ability, key,
                )
            )

    for score, source, ability, key in sorted(
        candidates, key=lambda x: x[0], reverse=True
    ):
        if count >= limit or score <= 0:
            break
        if execute_semantic_ability(
            state, strategy, source, ability
        ):
            used.add(key)
            count += 1

    state._semantic_activated_this_turn = used
    return count


_V470_maybe_food_precombat_old = maybe_use_food_before_combat
def maybe_use_food_before_combat(
    state: GameState,
    strategy: Strategy,
):
    # Combat-relevant generic Oracle activations happen before attacks, not
    # wastefully in the end step.
    try_generic_semantic_activations(
        state, strategy, limit=3, phase="precombat"
    )
    return _V470_maybe_food_precombat_old(state, strategy)


_FLASHBACK_RE = re.compile(r"\bflashback\s*((?:\{[^}]+\})+)")


def _flashback_cost(card: Card) -> Optional[Tuple[int, Counter]]:
    if card.is_permanent:
        return None  # scope: instants/sorceries, the overwhelming real-card case
    m = _FLASHBACK_RE.search(strip_reminder_text(card.oracle_text).lower())
    return parse_mana_cost(m.group(1)) if m else None


def maybe_flashback_cards(state: GameState, strategy: Strategy, limit: int = 5):
    """
    v4.22.0: Flashback ("You may cast this card from your graveyard for its
    flashback cost. Then exile it."). Reuses resolve_direct_spell_effects
    directly - the same effect-resolution function every instant/sorcery
    already resolves through on a normal cast, and it is zone-agnostic
    (purely name/oracle-text driven, never checks hand membership - see its
    own docstring-free top for confirmation), so this is a real second
    resolution of the spell's effect, paid for with real mana via
    find_payment/apply_payment, not a guessed value bonus. X-cost flashback
    spells are out of scope (ignored here, same as any other X-cost
    interaction this pass doesn't special-case) - no real card in any
    audited deck combines the two to calibrate against.

    Same leftover-mana-only, cheapest-first, capped-loop shape as
    maybe_cycle_cards below (see its docstring) - called before it in the
    main turn loop so a real spell recast is preferred over cycling when
    both draw from the same pool of leftover mana.
    """
    for _ in range(limit):
        options = []
        for card in state.graveyard:
            parsed = _flashback_cost(card)
            if parsed is not None:
                options.append((parsed[0], card, parsed[1]))
        if not options:
            return
        options.sort(key=lambda t: t[0])
        for total_cost, card, req in options:
            plan = find_payment(state, strategy, total_cost, req)
            if plan is None:
                continue
            apply_payment(state, plan, strategy)
            state.graveyard.remove(card)
            resolve_direct_spell_effects(state, strategy, card)
            state.exile.append(card)
            record_impact(state, card.name, "flashback_cast", 1)
            state.log(f"FLASHBACK: {card.name} cast from graveyard, then exiled")
            break
        else:
            return


_CYCLING_RE = re.compile(r"\bcycling\s*((?:\{[^}]+\})+)")


def _cycling_cost(card: Card) -> Optional[Tuple[int, Counter]]:
    if not card.is_land:  # a land can't be cycled from hand for mana it doesn't have yet
        m = _CYCLING_RE.search(strip_reminder_text(card.oracle_text).lower())
        if m:
            return parse_mana_cost(m.group(1))
    return None


def maybe_cycle_cards(state: GameState, strategy: Strategy, limit: int = 10):
    """
    v4.22.0: Cycling ("{cost}, Discard this card: Draw a card."). Runs at
    the end of the turn's normal proactive-casting passes, spending only
    whatever mana those passes left untapped - reuses find_payment/
    apply_payment (the same primitives every normal spell pays with)
    directly, rather than going through the spell-casting pipeline, since
    cycling is a hand-only activated ability, not casting a spell.

    Cheapest-to-cycle affordable card first, so leftover mana chains into
    as many draws as it can afford. `limit` bounds the loop (a newly drawn
    card can itself have Cycling and keep the chain going, which is
    correct real-game behavior, not a bug - the cap exists only so a
    degenerate all-cycling hand can't loop unboundedly in one simulated
    turn) rather than reflecting any real per-turn restriction.
    """
    for _ in range(limit):
        options = []
        for card in state.hand:
            parsed = _cycling_cost(card)
            if parsed is not None:
                options.append((parsed[0], card, parsed[1]))
        if not options:
            return
        options.sort(key=lambda t: t[0])
        for total_cost, card, req in options:
            plan = find_payment(state, strategy, total_cost, req)
            if plan is None:
                continue
            apply_payment(state, plan, strategy)
            state.hand.remove(card)
            state.graveyard.append(card)
            draw_cards(state, 1, reason=f"{card.name} cycling")
            record_impact(state, card.name, "cycled", 1)
            state.log(f"CYCLING: {card.name} discarded, drew a card")
            break
        else:
            return  # nothing on the board could actually afford any of them


def end_step(state: GameState, strategy: Strategy):
    # Only value/resource activations belong in this window.
    try_generic_semantic_activations(
        state, strategy, limit=3, phase="value"
    )
    _V460_end_step_old(state, strategy)
    guard_resource_invariants(state, "end step")


# ---------------------------------------------------------------------------
# Board modifiers must affect real combat, including creature tokens.
# ---------------------------------------------------------------------------

def team_modifier_bonus(state: GameState) -> float:
    bonus = 0.0
    for modifier in board_modifiers(state):
        if (
            modifier.target_id is None
            and modifier.kind == "team_pt_bonus"
        ):
            bonus += modifier.amount
    for source in state.battlefield:
        if source.card.name in DEDICATED_RESOLVERS:
            continue
        for ability in parse_oracle_semantics(source.card):
            if ability.ability_kind != "static":
                continue
            for action in ability.actions:
                if action.kind == "team_pt_bonus":
                    bonus += float(action.amount or 0)
    return bonus


def team_modifier_keywords(state: GameState) -> Set[str]:
    kws = set()
    for modifier in board_modifiers(state):
        if (
            modifier.target_id is None
            and modifier.kind == "grant_keyword"
            and modifier.keyword
        ):
            kws.add(modifier.keyword)
    for source in state.battlefield:
        if source.card.name in DEDICATED_RESOLVERS:
            continue
        for ability in parse_oracle_semantics(source.card):
            if ability.ability_kind != "static":
                continue
            for action in ability.actions:
                if (
                    action.kind == "grant_team_keyword"
                    and action.keyword
                ):
                    kws.add(action.keyword)
    return kws


def _untapped_noncreature_artifacts(state: GameState) -> List[Permanent]:
    return [
        p for p in state.battlefield
        if p.card.is_artifact and not p.card.is_creature and not p.tapped
    ]


def maybe_use_waterbend(
    state: GameState,
    strategy: Strategy,
    attacker_infos: List["combat_interaction.AttackerInfo"],
) -> Optional[int]:
    """
    Dedicated resolver (WP8) for Katara, Water Tribe's Hope:
    "Waterbend {X}: Creatures you control have base power and toughness X/X
    until end of turn. X can't be 0. Activate only during your turn. (While
    paying a waterbend cost, you can tap your artifacts and creatures to help.
    Each one pays for {1}.)"

    Called from attack_phase AFTER attackers are already committed - this
    ordering is the whole point (see COWORK_HANDOFF.md section 3 / v4.9.0
    changelog). A Vigilance attacker is still untapped once it has been
    declared, so tapping it here to help pay the waterbend cost does not
    remove it from combat - tap_permanent() never touches attacker_infos, and
    only still-untapped permanents are ever legal payment sources in the first
    place. So every creature this function can possibly tap is "free" from
    this decision's point of view: either it is a Vigilance attacker that
    stays in combat, or it never attacked this turn at all. That is why every
    creature candidate below is costs_attacker=False; the abstract case where
    costs_attacker=True actually changes the answer is covered by
    tests/test_resource_planner.py, not by this integration.

    Deliberately NOT funded by floating generic mana (see
    Data/Models/resource_planner_weights.json -> waterbend.include_generic_mana)
    - only untapped non-creature artifacts and untapped creatures. Katara
    herself has no tap symbol in her cost and is not required to be untapped
    to activate; she IS an eligible creature-tap candidate like any other.
    """
    if not state.has(KATARA_HOPE_NAME):
        return None

    creature_candidates = [
        resource_planner.Resource(
            key=f"creature:{id(p)}", type="creature", amount=1.0,
            costs_attacker=False, ref=p,
        )
        for p in state.creatures()
        if not p.tapped
    ]
    artifact_candidates = [
        resource_planner.Resource(
            key=f"artifact:{id(p)}", type="artifact", amount=1.0,
            costs_attacker=False, ref=p,
        )
        for p in _untapped_noncreature_artifacts(state)
    ]
    resources = artifact_candidates + creature_candidates
    if not resources:
        return None

    n_attackers = len(attacker_infos)
    action = resource_planner.Action(key="waterbend", min_units=1, max_units=None)

    def goal(units: int, attackers_lost: int) -> float:
        # Damage = (n_attackers - attackers_lost) * X, the same formula as the
        # WP8 brief's worked examples (see tests/test_resource_planner.py).
        # Nothing offered here ever costs an attacker (see docstring), so
        # attackers_lost is always 0 in this real integration and this
        # reduces to plain n_attackers * X - but writing it the general way
        # keeps this goal function correct (not just "happens to work today")
        # if a future change ever offers a costs_attacker=True candidate here.
        # Routed through plan_allocation rather than a hand-rolled max() so
        # this stays on the same tested code path as the abstract planner.
        return (n_attackers - attackers_lost) * units

    plan = resource_planner.plan_allocation(resources, action, goal)
    if plan is None or plan.units <= 0:
        return None

    # Waterbend SETS base power/toughness for everyone to X/X - it does not add
    # to it. So this is only worth activating if the resulting total attacker
    # damage (n_attackers * X) actually beats what these attackers already hit
    # for at their current (possibly much higher) power - e.g. a single
    # power-3 Katara funding only X=1 by tapping herself would cut her own
    # damage from 3 to 1. Compare against the concrete pre-Waterbend total
    # rather than skip this check, so a small/lone board does not talk itself
    # into a strictly worse attack.
    current_total_power = sum(a.power for a in attacker_infos)
    if plan.value <= current_total_power:
        return None

    tapped_creatures = 0
    for r in plan.used_resources:
        idx = state.battlefield.index(r.ref)
        tap_permanent(state, strategy, idx, reason="waterbend")
        if r.type == "creature":
            tapped_creatures += 1

    board_modifiers(state).append(BoardModifier(
        source=KATARA_HOPE_NAME, expires_turn=state.turn, kind="set_base_pt",
        power=float(plan.units), toughness=float(plan.units),
    ))
    record_impact(state, KATARA_HOPE_NAME, "semantic_ability_uses", 1)
    state.log(
        f"WATERBEND {KATARA_HOPE_NAME}: X={plan.units} "
        f"(tapped {tapped_creatures} creature(s) + "
        f"{len(plan.used_resources) - tapped_creatures} artifact(s)), "
        f"creatures you control -> base {plan.units}/{plan.units} until end of turn"
    )
    return plan.units


# ---------------------------------------------------------------------------
# v4.20.0: Battles.
# ---------------------------------------------------------------------------
#
# Found during the v4.18.0 model-coverage audit: no Battle card appeared in
# any of the 14 audited real decks, and the engine had zero Battle support
# at all (no is_battle, no defense counters, no "battle" text anywhere).
# Genuinely uncalibrated territory - unlike the planeswalker work above,
# there is no real card_impact.csv data to check this against yet. Scope,
# stated plainly (same honesty pattern as the planeswalker section):
#   - Defense counters are tracked (Card.defense / Permanent.defense) and
#     reduced by our own creatures attacking the battle instead of an
#     opponent (see the "v4.20.0: Battles" block inside attack_phase) -
#     real rule (the caster is never the "protector", so the caster's own
#     creatures CAN attack their own Battle), simplified to "always
#     connects" the same way this whole engine already assumes no
#     blockers exist for player-facing attacks either.
#   - When defense reaches 0, complete_battle() below fires. A transforming
#     Battle's back face becoming an ongoing permanent (a land, a
#     creature, ...) is NOT modeled - that would need general DFC
#     transform support this engine doesn't have anywhere else either (its
#     existing double-faced-card handling is scoped to Scryfall NAME
#     lookup only, see index_scryfall_cards, never in-game flipping). What
#     IS modeled: if the back face's own text parses to at least one
#     executable action via the same generic action vocabulary as
#     everything else (create tokens / draw / gain life / damage-to-a-
#     player-shaped target), that one-shot reward fires once, as an
#     approximation of "you get what the flip was for" without the
#     ongoing permanent. Otherwise the completion is still tracked and
#     logged, just without a one-shot reward.
def complete_battle(state: GameState, strategy: Strategy, battle: Permanent):
    card = battle.card
    record_impact(state, card.name, "battle_completed", 1)

    # A transforming Battle's two faces are joined by the same "\n//\n"
    # separator card_from_scryfall already uses for any double-faced card's
    # combined oracle text (see index_scryfall_cards' docstring) - the back
    # face, if present, is everything after it.
    parts = card.oracle_text.split("\n//\n", 1)
    back_face_text = parts[1] if len(parts) > 1 else ""
    did = False
    if back_face_text:
        for action in _parse_semantic_actions(back_face_text):
            did = execute_semantic_action(state, strategy, battle, action) or did

    move_permanent_to_zone(state, strategy, battle, "graveyard", reason="battle defense reached 0")
    state.log(
        f"BATTLE COMPLETED: {card.name}"
        + (" (back-face reward applied)" if did else " (no executable back-face reward)")
    )


def attack_phase(state: GameState, strategy: Strategy, rng: Optional[random.Random] = None):
    if state.win_turn is not None:
        return
    if rng is None:
        # Only reached from superseded/dead call sites that predate seeded combat
        # interaction; kept functional (non-reproducible) rather than crashing.
        rng = random.Random()

    preserved = []
    for p in state.battlefield:
        if (
            p.card.is_creature
            and not p.tapped
            and scenario_preserve_untapped(
                state, strategy, p.card.name
            )
        ):
            p.tapped = True
            preserved.append(p)

    try:
        attackers: List[Tuple[str, float, bool]] = []
        attacker_infos: List[combat_interaction.AttackerInfo] = []
        candidate_creatures: List[Tuple[Permanent, Set[str], float]] = []
        global_kws = team_modifier_keywords(state)
        global_bonus = team_modifier_bonus(state)

        for p in state.creatures():
            if p.tapped:
                continue
            kws = effective_keywords_in_state(p, state)
            if "defender" in kws:
                continue
            if (
                p.entered_turn == state.turn
                and "haste" not in kws
            ):
                continue
            power = creature_power(p, state)
            if power <= 0:
                continue
            candidate_creatures.append((p, kws, power))

        def _is_gated(p) -> bool:
            roles = getattr(p.card, "roles", set()) or set()
            return bool(p.card.commander) or bool(roles & commander_posture._ENGINE_ROLES)

        always_attack = [c for c in candidate_creatures if not _is_gated(c[0])]
        gated = [c for c in candidate_creatures if _is_gated(c[0])]

        # v4.20.0: Battles. Real rule: the caster picks an opponent as
        # "protector"; everyone else (including the caster) can attack the
        # battle to remove defense counters. This engine has no opposing
        # creatures at all (goldfish - see attack_phase's own "no blockers
        # are assumed" precedent for combat damage to a player), so an
        # attack on our own Battle is modeled as unconditionally connecting,
        # same simplifying assumption. Pulled only from `always_attack`
        # (ordinary creatures), never from `gated` (commander/engine-role
        # creatures) - a Battle's reward isn't worth derailing the deck's
        # actual plan for, and this keeps existing commander-damage/engine-
        # role tests unaffected. Smallest-power-first so the least possible
        # attacking power is diverted from opponents.
        for battle in [p for p in state.battlefield if p.card.is_battle and (p.defense or 0) > 0]:
            always_attack.sort(key=lambda c: c[2])
            remaining = float(battle.defense or 0)
            consumed = []
            for c in always_attack:
                if remaining <= 0:
                    break
                p, kws, power = c
                consumed.append(c)
                remaining -= power
                if "vigilance" not in kws:
                    idx = state.battlefield.index(p)
                    tap_permanent(state, strategy, idx, reason="attack battle")
            if not consumed:
                continue
            for c in consumed:
                always_attack.remove(c)
            dealt = float(battle.defense or 0) - max(0.0, remaining)
            battle.defense = max(0.0, remaining)
            record_impact(state, battle.card.name, "battle_defense_damage", dealt)
            state.log(f"BATTLE: {battle.card.name} takes {dealt:g} (defense now {battle.defense:g})")
            if battle.defense <= 0:
                complete_battle(state, strategy, battle)

        def _commit_creature_attacker(p, kws, power):
            attackers.append(
                (p.card.name, power, "lifelink" in kws)
            )
            # v4.15.3: equipment "Whenever equipped creature attacks, tap
            # target creature ..." trigger, approximated as a per-attacker
            # block-rate multiplier (see equipment.py module docstring).
            equip_mult = equipment_model.equipment_attack_tap_multiplier(
                combat_interaction._WEIGHTS, state, p,
            )
            attacker_infos.append(combat_interaction.AttackerInfo(
                name=p.card.name, power=power, lifelink="lifelink" in kws,
                keywords=set(kws), is_commander=bool(p.card.commander),
                source_kind="permanent", source_ref=p,
                equipment_evasion_multiplier=equip_mult,
            ))
            if "vigilance" not in kws:
                idx = state.battlefield.index(p)
                tap_permanent(
                    state, strategy, idx,
                    reason="attack",
                )

        for p, kws, power in always_attack:
            _commit_creature_attacker(p, kws, power)

        # Gated creatures (commander + engine-role pieces) are resolved in board
        # order, each seeing how many attackers are already committed so far
        # (always-attackers plus any gated creature already decided this combat) -
        # an evolving-count approximation rather than a full fixed-point search,
        # which is more than this decision needs.
        committed_gated = 0
        for p, kws, power in gated:
            if commander_posture.creature_should_attack(
                sys.modules[__name__], state, strategy, p,
                other_attacker_count=len(always_attack) + committed_gated,
            ):
                _commit_creature_attacker(p, kws, power)
                committed_gated += 1

        # v4.24.0: token groups. Real bug found via ChatGPT external review
        # (see Docs/README.md v4.24.0 entry): `power` here is the TOTAL
        # combat damage this group's attack deals to a player - it must be
        # per-token power times how many tokens are actually attacking.
        # The previous formula, `token_group_power(g, state) + global_bonus
        # * g.count`, only scaled the flat team-bonus part by count and left
        # the token's own base power (and per-token bonuses from
        # token_group_power, e.g. The Arkenstone/Doctor Strange) completely
        # unscaled - 10 grouped 1/1 tokens dealt 1 damage unblocked instead
        # of 10. Group resolution stays a single block/no-block roll per
        # group (unchanged - no real per-token blocker simulation exists in
        # this goldfish engine, same disclosed simplification as ordinary
        # creature combat), so a block still only kills one token
        # (g.count -= 1 below) while an unblocked hit now correctly deals
        # the WHOLE group's total power.
        for g in state.creature_tokens:
            token_kws = set(g.keywords) | global_kws
            if (
                g.count <= 0
                or (
                    g.entered_turn == state.turn
                    and "haste" not in token_kws
                )
            ):
                continue
            power = (
                token_group_power(g, state) + global_bonus
            ) * g.count
            if power > 0:
                attackers.append(
                    (
                        g.name,
                        power,
                        "lifelink" in token_kws,
                    )
                )
                attacker_infos.append(combat_interaction.AttackerInfo(
                    name=g.name, power=power, lifelink="lifelink" in token_kws,
                    keywords=set(token_kws), is_commander=False,
                    source_kind="token_group", source_ref=g,
                    attack_weight=float(g.count),
                ))

        if not attackers:
            return

        attacking_names = {
            name for name, _, _ in attackers
        }
        for p in list(state.creatures()):
            if p.card.name not in attacking_names:
                continue
            for line in split_oracle_lines(
                p.card.oracle_text
            ):
                low = strip_reminder_text(line).lower()
                if (
                    "attacks" not in low
                    or not low.startswith("whenever")
                ):
                    continue
                m = re.search(
                    r"connives? ?(\d+)?", low
                )
                if m:
                    connive(
                        state,
                        int(m.group(1) or 1),
                        strategy,
                        source=p,
                    )
                m = re.search(r"scry (\d+)", low)
                if m:
                    scry(
                        state, int(m.group(1)), strategy
                    )
                m = re.search(r"surveil (\d+)", low)
                if m:
                    surveil(
                        state, int(m.group(1)), strategy
                    )
                m = re.search(
                    r"draw (a|one|two|three|\d+) cards?",
                    low,
                )
                if m:
                    draw_cards(
                        state,
                        parse_number_token(m.group(1)),
                        reason=f"{p.card.name} attack",
                    )

        bog_attackers = sum(
            1 for name, _, _ in attackers
            if name == "Blossoming Bogbeast"
        )
        for _ in range(bog_attackers):
            gain_life(
                state, 2,
                "Blossoming Bogbeast attack",
            )
            x = float(
                state.life_gained_this_turn_amount
            )
            attackers = [
                (n, pwr + x, ll)
                for n, pwr, ll in attackers
            ]
            record_impact(
                state,
                "Blossoming Bogbeast",
                "combat_damage",
                x * len(attackers),
            )

        # Keep attacker_infos power in sync with any pre-damage mutations above
        # (e.g. Blossoming Bogbeast's per-attack lifegain-power bump). The Bogbeast
        # loop rebuilds `attackers` via a list comprehension, so order/length stay
        # aligned with attacker_infos - zip by index, not by name (names can repeat).
        for (name, power, lifelink), meta in zip(attackers, attacker_infos):
            meta.power = power
            meta.lifelink = lifelink

        # WP8: Katara's Waterbend, activated AFTER attackers are committed (see
        # maybe_use_waterbend's docstring for why that ordering is the point).
        # It can rewrite every creature's base P/T via a set_base_pt
        # BoardModifier, so re-sync attacker_infos power the same way the
        # Bogbeast loop above does, for every attacker backed by a real
        # Permanent (token-group attackers have no board modifier target and
        # are unaffected - Katara's ability says "creatures you control",
        # which this engine does not model token groups as being included in).
        waterbend_x = maybe_use_waterbend(state, strategy, attacker_infos)
        if waterbend_x is not None:
            for meta in attacker_infos:
                if meta.source_kind == "permanent":
                    meta.power = creature_power(meta.source_ref, state)

        # v4.23.0: Augusta, Order Returned (real card, confirmed via
        # card_impact.csv in the audited Lorehold Spirit deck) - "Whenever
        # Augusta attacks, each player exiles a card from their graveyard.
        # When one or more nonland cards are exiled this way, put that many
        # +1/+1 counters on target attacking creature." This engine tracks
        # only our OWN graveyard (no opposing graveyards are modeled
        # anywhere - pure one-sided goldfish simulator), so "each player
        # exiles a card" degrades to "we exile one card from our own
        # graveyard", a disclosed simplification rather than a guess at
        # unmodeled opponent state. The counters always land on Augusta
        # herself - the real "target attacking creature" choice is a player
        # decision, and Augusta is the overwhelmingly natural target (she
        # grows herself turn over turn) rather than a full attacker-
        # selection heuristic for one specific card.
        if "Augusta, Order Returned" in {name for name, _, _ in attackers} and state.graveyard:
            exiled_card = state.graveyard.pop(0)
            state.exile.append(exiled_card)
            if not exiled_card.is_land:
                augusta = next(
                    (p for p in state.battlefield if p.card.name == "Augusta, Order Returned"),
                    None,
                )
                if augusta is not None:
                    n = 2 if state.has("Doubling Season") else 1
                    augusta.counters += n
                    record_impact(state, "Augusta, Order Returned", "counters", n)
                    state.log(
                        f"AUGUSTA: exiled {exiled_card.name} (nonland) -> "
                        f"+{n} +1/+1 counter(s)"
                    )
                    # Same re-sync reasoning as the Bogbeast/Waterbend blocks
                    # above - the bonus lands mid-combat but only actually
                    # matters for THIS combat's damage if Augusta is still an
                    # attacker in attacker_infos.
                    for i2, (name2, _power2, _ll2) in enumerate(attackers):
                        if name2 == "Augusta, Order Returned":
                            new_power = creature_power(augusta, state)
                            attackers[i2] = (name2, new_power, attackers[i2][2])
                            attacker_infos[i2].power = new_power

        profile_name = getattr(strategy, "opponent_profile", "goldfish")
        outcomes = combat_interaction.resolve_combat_interaction(
            profile_name, state.turn, attacker_infos, rng, state=state,
        )

        any_combat_death = False
        for outcome in outcomes:
            if state.win_turn is not None:
                return
            if not state.opponents:
                break

            if outcome.damage_dealt > 0:
                # v4.15.0 (WP10): commander damage respects a fixed Voltron
                # target (strategy.voltron_target_index) when one is set and
                # that opponent is still alive - otherwise (unset, invalid,
                # or the target has already been eliminated) fall back to the
                # original highest-life heuristic unchanged. Non-commander
                # damage always uses the original heuristic - deliberately
                # scoped to the "21 commander damage on one target" plan.
                fixed_target = getattr(strategy, "voltron_target_index", None)
                if (
                    outcome.is_commander
                    and fixed_target is not None
                    and 0 <= fixed_target < len(state.opponents)
                    and state.opponents[fixed_target] > 0
                ):
                    i = fixed_target
                else:
                    i = max(
                        range(len(state.opponents)),
                        key=lambda j: state.opponents[j],
                    )
                # v4.21.0: Infect. "Damage dealt to a player by a source
                # with infect isn't dealt as normal - it causes that many
                # poison counters instead" (real rule 702.90c), with 10+
                # poison counters a separate loss condition. Everything else
                # about this outcome (commander-damage ledger, lifelink,
                # equipment/Old Gnawbone combat-damage triggers, check_win)
                # is unaffected - the damage was still dealt, only which
                # meter it reduces changes.
                is_infect = (
                    "infect" in effective_keywords_in_state(outcome.source_ref, state)
                    if outcome.source_kind == "permanent" and outcome.source_ref is not None
                    else "infect" in getattr(outcome.source_ref, "keywords", set())
                )
                if is_infect:
                    state.poison_counters[i] += int(round(outcome.damage_dealt))
                    record_impact(state, outcome.name, "poison_counters", outcome.damage_dealt)
                    state.log(
                        f"INFECT: {outcome.name} dealt {outcome.damage_dealt:g} poison "
                        f"to opponent {i} (total {state.poison_counters[i]})"
                    )
                    if state.poison_counters[i] >= 10:
                        state.opponents[i] = 0.0
                        record_impact(state, outcome.name, "poison_lethal", 1)
                        state.log(
                            f"POISON: opponent {i} reached {state.poison_counters[i]} "
                            f"poison counters (>=10, eliminated)"
                        )
                else:
                    state.opponents[i] = max(
                        0.0, state.opponents[i] - outcome.damage_dealt
                    )
                    record_impact(
                        state, "Combat",
                        "combat_damage", outcome.damage_dealt,
                    )
                if outcome.is_commander:
                    # v4.28.0: keyed per-commander (outcome.name is the
                    # attacking commander's own card name), not pooled
                    # across every commander a Partner/background deck may
                    # have - see the GameState.commander_damage_dealt
                    # docstring for why.
                    ledger_key = (outcome.name, i)
                    state.commander_damage_dealt[ledger_key] += outcome.damage_dealt
                    if state.commander_damage_dealt[ledger_key] >= 21:
                        state.opponents[i] = 0.0
                        record_impact(state, outcome.name, "commander_damage_lethal", 1)
                        state.log(
                            f"COMMANDER DAMAGE: {outcome.name} dealt "
                            f"{state.commander_damage_dealt[ledger_key]:.1f} to opponent {i} (>=21, eliminated)"
                        )
                if outcome.lifelink_gain:
                    gain_life(
                        state, outcome.lifelink_gain, f"{outcome.name} lifelink"
                    )
                check_win(state)

                # v4.15.3: equipment "Whenever equipped creature deals combat
                # damage to a player, create a token that's a copy of this
                # Equipment" (e.g. Bloodforged Battle-Axe). damage_dealt > 0
                # only ever happens on an UNBLOCKED outcome (see
                # resolve_combat_interaction), so this is exactly "dealt
                # combat damage to a player" - no separate blocked-check needed.
                if outcome.source_kind == "permanent" and outcome.source_ref is not None:
                    for copy_card in equipment_model.equipment_combat_damage_copy_triggers(
                        state, outcome.source_ref,
                    ):
                        state.battlefield.append(
                            Permanent(card=copy_card, entered_turn=state.turn, tapped=False)
                        )
                        record_impact(state, copy_card.name, "equipment_token_copy_created", 1)

                # v4.18.0: Old Gnawbone ("Whenever a creature you control
                # deals combat damage to a player, create that many Treasure
                # tokens.") - found unmodeled during the v4.18.0 model-coverage
                # audit: card_model_coverage.csv tagged this trigger
                # "review"/probabilistic and card_impact.csv showed 0
                # Treasure ever created for it across 173 real casts, even
                # though it was the deck's commander and its entire game
                # plan. This is the same "dealt combat damage to a player"
                # event already isolated above for the equipment copy-token
                # trigger (damage_dealt > 0 only ever happens on an unblocked
                # outcome - see that comment), so no separate blocked-check
                # is needed here either. The trigger includes Old Gnawbone's
                # own combat damage, not just other creatures'.
                if state.has("Old Gnawbone"):
                    treasure_n = int(round(outcome.damage_dealt))
                    if treasure_n > 0:
                        create_tokens(
                            state, strategy, "Treasure", treasure_n,
                            source="Old Gnawbone",
                        )

            if not outcome.blocked:
                continue

            record_impact(state, outcome.name, "combat_blocked", 1)
            if not outcome.died:
                continue

            # Indestructible survives lethal combat interaction (real-rules parity);
            # treat it like a chump block instead of a death.
            if outcome.source_kind == "permanent" and outcome.source_ref is not None:
                p = outcome.source_ref
                if "indestructible" in effective_keywords_in_state(p, state):
                    continue
                record_impact(state, outcome.name, "died_in_combat", 1)
                move_permanent_to_zone(
                    state, strategy, p, "graveyard",
                    reason="died in combat (abstract interaction)", rng=rng,
                )
                any_combat_death = True
            elif outcome.source_kind == "token_group" and outcome.source_ref is not None:
                g = outcome.source_ref
                if "indestructible" in g.keywords:
                    continue
                g.count = max(0, g.count - 1)
                record_impact(state, outcome.name, "died_in_combat", 1)
                any_combat_death = True
                # v4.15.6: Moldervine Reclamation - a token creature dying
                # never routes through move_permanent_to_zone (a TokenGroup
                # is not a Permanent), so it needs this separate hook to
                # trigger the same "creature you control dies" event.
                if state.has("Moldervine Reclamation"):
                    gain_life(state, 1, "Moldervine Reclamation")
                    draw_cards(state, 1, reason="Moldervine Reclamation")

        # v4.15.3: "Whenever one or more creatures die, put a _ counter on this
        # Equipment" (e.g. Chainsaw) - batched once per combat, matching the
        # real rule (one trigger for the whole event, not once per creature).
        # Combat-deaths-only boundary: see equipment.py module docstring.
        if any_combat_death:
            equipment_model.creature_death_equipment_triggers(state)
    finally:
        for p in preserved:
            if p in state.battlefield:
                p.tapped = False


# ---------------------------------------------------------------------------
# Current/cumulative dashboard metrics
# ---------------------------------------------------------------------------

_V470_gain_life_old = gain_life
def gain_life(
    state: GameState,
    base: float,
    source: str = "",
) -> float:
    amount = _V470_gain_life_old(
        state, base, source
    )
    state.total_life_gained = (
        float(
            getattr(state, "total_life_gained", 0.0)
        )
        + float(amount or 0)
    )
    return amount


_V470_create_tokens_old = create_tokens
def create_tokens(
    state: GameState,
    strategy: Strategy,
    token_type: str,
    n: int,
    **kwargs,
):
    # v4.23.0: Doubling Season ("If an effect would create one or more
    # tokens under your control, it creates twice that many of those
    # tokens instead.") - this wrapper is the single shared function every
    # token creation in this engine already routes through (real cards,
    # the generic semantic "create_token" handler, Devour's fodder, the
    # Chatterfang bonus below, ...), so it's the one correct root-cause
    # place to double token COUNT. Doubling Season's separate "twice that
    # many counters" clause is handled at its own call sites (the generic
    # plus1_counter handler in App/keyword_library/handlers.py, and
    # planeswalker starting loyalty / Battle starting defense in
    # own_etb_effects) - a different event, not this one.
    if state.has("Doubling Season") and n > 0:
        n = n * 2

    before = (
        state.food
        + state.treasure
        + state.clues
        + sum(g.count for g in state.creature_tokens)
    )
    result = _V470_create_tokens_old(
        state, strategy, token_type, n, **kwargs
    )
    after = (
        state.food
        + state.treasure
        + state.clues
        + sum(g.count for g in state.creature_tokens)
    )
    created = max(0, int(after - before))
    state.total_tokens_created = (
        int(
            getattr(state, "total_tokens_created", 0)
        )
        + created
    )

    # v4.23.0: Chatterfang, Squirrel General (real card, confirmed via
    # card_impact.csv in the audited Korvold deck) - "If one or more tokens
    # would be created under your control, those tokens plus that many 1/1
    # green Squirrel creature tokens are created instead." Applies to ANY
    # token type (Food/Treasure/Clue included, not just creatures) and adds
    # ONCE per create_tokens call - the Squirrels it makes do NOT
    # themselves re-trigger this block (token_type != "Squirrel" guard, and
    # a direct call to the un-doubled base function below), matching the
    # real replacement-effect rule that a single event is replaced only
    # once. `created` already reflects Doubling Season's doubling above, so
    # "that many" here is the actual (possibly doubled) amount created,
    # same real-game order most players choose when running both cards.
    if created > 0 and token_type != "Squirrel" and state.has("Chatterfang, Squirrel General"):
        _V470_create_tokens_old(
            state, strategy, "Squirrel", created,
            creature=True, power=1.0, toughness=1.0,
            source="Chatterfang, Squirrel General",
        )
        state.total_tokens_created += created
        record_impact(state, "Chatterfang, Squirrel General", "bonus_squirrels", created)

    return result


_V470_token_sacrificed_old = token_sacrificed
def token_sacrificed(
    state: GameState,
    token_type: str,
    n: int = 1,
    strategy: Optional[Strategy] = None,
):
    result = _V470_token_sacrificed_old(
        state, token_type, n, strategy
    )
    state.total_tokens_sacrificed = (
        int(
            getattr(
                state,
                "total_tokens_sacrificed",
                0,
            )
        )
        + max(0, int(n))
    )
    return result


_V470_turn_row_old = _turn_row_v440
def _turn_row_v440(
    run_id: int,
    turn: int,
    state: GameState,
    strategy: ScenarioStrategy,
    start_hand: List[str],
    land_name: str,
    casts: List[str],
    mana_before: float,
    structural_access_before: Set[str],
    sc_progress: Dict[str, dict],
) -> dict:
    row = _V470_turn_row_old(
        run_id, turn, state, strategy,
        start_hand, land_name, casts,
        mana_before, structural_access_before,
        sc_progress,
    )
    creature_tokens = sum(
        max(0, int(g.count))
        for g in state.creature_tokens
    )
    plus1 = sum(
        max(0, int(p.counters))
        for p in state.battlefield
    )
    named = sum(
        sum(max(0, int(v)) for v in p.named_counters.values())
        for p in state.battlefield
    )
    row.update({
        "opponent_profile": strategy.opponent_profile,
        "creature_tokens": creature_tokens,
        "tokens_total_current": (
            creature_tokens
            + state.food
            + state.treasure
            + state.clues
        ),
        "tokens_created_total": int(
            getattr(state, "total_tokens_created", 0)
        ),
        "tokens_sacrificed_total": int(
            getattr(
                state,
                "total_tokens_sacrificed",
                0,
            )
        ),
        "life_gained_total": round(
            float(
                getattr(
                    state, "total_life_gained", 0.0
                )
            ),
            2,
        ),
        "creatures_in_play": len(
            state.creatures()
        ),
        "permanents_in_play": len(
            state.battlefield
        ),
        "plus1_counters_on_board": plus1,
        "named_counters_on_board": named,
    })
    return row


# ---------------------------------------------------------------------------
# Random opponent per run.
# ---------------------------------------------------------------------------

_V470_simulate_game_old = simulate_game_v440
def simulate_game_v440(
    deck: List[Card],
    strategy_template: ScenarioStrategy,
    cfg: SimConfig,
    policy: MulliganPolicy,
    rng: random.Random,
    run_id: int,
):
    requested_profile = strategy_template.opponent_profile
    if requested_profile == "random":
        # Balanced randomized cycles: every complete block of four runs contains
        # Aggro, Midrange, Control and Horde exactly once, but in a seeded
        # shuffled order. This is better for direct dashboard comparisons than
        # independent random draws, especially in 200-run diagnostics.
        block = (run_id - 1) // len(RANDOM_OPPONENT_CHOICES)
        position = (run_id - 1) % len(RANDOM_OPPONENT_CHOICES)
        chooser = random.Random(
            (int(cfg.seed) + 1) * 1000003 + block
        )
        profiles = list(RANDOM_OPPONENT_CHOICES)
        chooser.shuffle(profiles)
        actual_profile = profiles[position]
        run_strategy = replace(
            strategy_template,
            opponent_profile=actual_profile,
        )
    else:
        actual_profile = requested_profile
        run_strategy = strategy_template

    rr, tr, oh, impact, sr = _V470_simulate_game_old(
        deck, run_strategy, cfg, policy, rng, run_id
    )
    rr["opponent_profile"] = actual_profile
    oh["opponent_profile"] = actual_profile
    for row in tr:
        row["opponent_profile"] = actual_profile
    for row in sr:
        row["opponent_profile"] = actual_profile
    return rr, tr, oh, impact, sr


# ---------------------------------------------------------------------------
# Complete aggregate dashboard stats, including Random profile breakdown.
# ---------------------------------------------------------------------------

_V470_stats_add_old = StreamingStatsV440.add
def _streaming_stats_add_v470(
    self,
    rr: dict,
    tr: List[dict],
    sr: List[dict],
):
    _V470_stats_add_old(self, rr, tr, sr)

    if not hasattr(self, "_dashboard_turn_stats"):
        self._dashboard_turn_stats = _defaultdict(Counter)
    if not hasattr(self, "_opponent_dashboard"):
        self._opponent_dashboard = {}

    dashboard_fields = (
        "life", "hand_size", "lands_in_play",
        "mana_available_start_main",
        "food", "treasure", "clues",
        "creature_tokens", "tokens_total_current",
        "tokens_created_total",
        "tokens_sacrificed_total",
        "life_gained_total",
        "life_gained_this_turn",
        "life_events_this_turn",
        "creatures_in_play",
        "permanents_in_play",
        "plus1_counters_on_board",
        "named_counters_on_board",
        "damage_taken",
    )

    for row in tr:
        t = int(row["turn"])
        a = self._dashboard_turn_stats[t]
        a["count"] += 1
        for field_name in dashboard_fields:
            a[field_name] += float(
                row.get(field_name, 0) or 0
            )

    profile = str(
        rr.get("opponent_profile", "unknown")
    )
    group = self._opponent_dashboard.setdefault(
        profile,
        {
            "runs": 0,
            "wins": 0,
            "losses": 0,
            "life_end_sum": 0.0,
            "hand_end_sum": 0.0,
            "damage_sum": 0.0,
            "reach111": 0,
            "bilbo": 0,
            "win_turns": [],
            "loss_turns": [],
            "turns": _defaultdict(Counter),
        },
    )
    group["runs"] += 1
    group["wins"] += int(
        bool(str(rr.get("win_turn", "")).strip())
    )
    group["losses"] += int(
        bool(str(rr.get("loss_turn", "")).strip())
    )
    group["life_end_sum"] += float(
        rr.get("life_end", 0) or 0
    )
    group["hand_end_sum"] += float(
        rr.get("hand_size_end", 0) or 0
    )
    group["damage_sum"] += float(
        rr.get("damage_taken", 0) or 0
    )
    group["reach111"] += int(
        bool(
            str(
                rr.get("life_111_turn", "")
            ).strip()
        )
    )
    group["bilbo"] += int(
        bool(
            str(
                rr.get(
                    "bilbo_activation_turn", ""
                )
            ).strip()
        )
    )
    if str(rr.get("win_turn", "")).strip():
        group["win_turns"].append(
            int(float(rr["win_turn"]))
        )
    if str(rr.get("loss_turn", "")).strip():
        group["loss_turns"].append(
            int(float(rr["loss_turn"]))
        )

    for row in tr:
        t = int(row["turn"])
        a = group["turns"][t]
        a["count"] += 1
        for field_name in dashboard_fields:
            a[field_name] += float(
                row.get(field_name, 0) or 0
            )

StreamingStatsV440.add = _streaming_stats_add_v470


def _average_dashboard_turns(
    raw: Dict[int, Counter],
    turns: int,
) -> List[dict]:
    fields = (
        "life", "hand_size", "lands_in_play",
        "mana_available_start_main",
        "food", "treasure", "clues",
        "creature_tokens", "tokens_total_current",
        "tokens_created_total",
        "tokens_sacrificed_total",
        "life_gained_total",
        "life_gained_this_turn",
        "life_events_this_turn",
        "creatures_in_play",
        "permanents_in_play",
        "plus1_counters_on_board",
        "named_counters_on_board",
        "damage_taken",
    )
    out = []
    for t in range(1, turns + 1):
        a = raw.get(t)
        if not a or not a["count"]:
            continue
        n = float(a["count"])
        row = {
            "turn": t,
            "active_games": int(n),
        }
        for field_name in fields:
            row[f"avg_{field_name}"] = (
                float(a[field_name]) / n
            )
        out.append(row)
    return out


_V470_summary_old = streaming_summary_v440
def streaming_summary_v440(
    deck: List[Card],
    stats: StreamingStatsV440,
    cfg: SimConfig,
    strategy: ScenarioStrategy,
    impact_rows: List[dict],
    detailed_runs_logged: int,
    log_policy: str,
) -> dict:
    data = _V470_summary_old(
        deck, stats, cfg, strategy,
        impact_rows, detailed_runs_logged,
        log_policy,
    )
    data["version"] = ENGINE_VERSION
    data["simulation"]["requested_opponent_profile"] = (
        strategy.opponent_profile
    )
    data["simulation"]["random_opponent_choices"] = (
        list(RANDOM_OPPONENT_CHOICES)
        if strategy.opponent_profile == "random"
        else []
    )

    runs_n = max(1, cfg.runs)

    def _top(field_name: str, n: int = 5):
        ranked = sorted(
            (r for r in impact_rows if r.get(field_name)),
            key=lambda r: r[field_name], reverse=True,
        )[:n]
        return [{"name": r["Name"], field_name: r[field_name]} for r in ranked]

    data["combat_and_removal_diagnostics"] = {
        "note": (
            "Introduced alongside WP6/WP7 to make combat-death and removal-"
            "targeting mechanics visible in results, instead of only inferable "
            "indirectly from outcome shifts. All totals are summed across the "
            "whole batch; divide by runs for a per-game average."
        ),
        "total_died_in_combat": sum(r.get("Died in combat", 0) for r in impact_rows),
        "avg_died_in_combat_per_run": sum(r.get("Died in combat", 0) for r in impact_rows) / runs_n,
        "total_removed_by_opponent": sum(r.get("Removed by opponent", 0) for r in impact_rows),
        "avg_removed_by_opponent_per_run": sum(r.get("Removed by opponent", 0) for r in impact_rows) / runs_n,
        "total_wiped_by_opponent": sum(r.get("Wiped by opponent", 0) for r in impact_rows),
        "top_died_in_combat": _top("Died in combat"),
        "top_removed_by_opponent": _top("Removed by opponent"),
    }

    dashboard_turns = _average_dashboard_turns(
        getattr(
            stats, "_dashboard_turn_stats", {}
        ),
        cfg.turns,
    )
    data["dashboard_by_turn"] = dashboard_turns

    # Population-cumulative outcome curves do not suffer from the survivor
    # bias present in average active-game life on later turns.
    data["cumulative_outcomes_by_turn"] = [
        {
            "turn": t,
            "win_pct": 100.0
            * sum(x <= t for x in stats.win_turns)
            / max(1, stats.run_count),
            "loss_pct": 100.0
            * sum(x <= t for x in stats.loss_turns)
            / max(1, stats.run_count),
            "active_pct": 100.0
            * (
                stats.run_count
                - sum(x <= t for x in stats.win_turns)
                - sum(x <= t for x in stats.loss_turns)
            )
            / max(1, stats.run_count),
        }
        for t in range(1, cfg.turns + 1)
    ]

    breakdown = {}
    for profile, group in sorted(
        getattr(
            stats, "_opponent_dashboard", {}
        ).items()
    ):
        n = max(1, group["runs"])
        breakdown[profile] = {
            "runs": group["runs"],
            "run_share_pct": (
                100.0
                * group["runs"]
                / max(1, stats.run_count)
            ),
            "win_pct": 100.0 * group["wins"] / n,
            "loss_pct": 100.0 * group["losses"] / n,
            "active_at_limit_pct": (
                100.0
                * (
                    group["runs"]
                    - group["wins"]
                    - group["losses"]
                )
                / n
            ),
            "avg_end_life": group["life_end_sum"] / n,
            "avg_end_hand": group["hand_end_sum"] / n,
            "avg_damage_taken": group["damage_sum"] / n,
            "reach_111_pct": 100.0 * group["reach111"] / n,
            "bilbo_activation_pct": 100.0 * group["bilbo"] / n,
            "median_win_turn": (
                percentile(
                    [float(x) for x in group["win_turns"]],
                    .5,
                )
                if group["win_turns"] else None
            ),
            "median_loss_turn": (
                percentile(
                    [float(x) for x in group["loss_turns"]],
                    .5,
                )
                if group["loss_turns"] else None
            ),
            "by_turn": _average_dashboard_turns(
                group["turns"], cfg.turns
            ),
        }
    data["opponent_breakdown"] = breakdown

    role_counts = Counter(
        role for card in deck for role in card.roles
    )
    selected = sorted(strategy.archetypes)
    inferred = []
    if role_counts.get("lifegain", 0) >= 8:
        inferred.append("lifegain")
    if role_counts.get("token", 0) >= 6:
        inferred.append("tokens")
    if (
        role_counts.get("lifegain_payoff", 0) >= 5
        or sum(
            1 for c in deck
            if "+1/+1 counter" in c.oracle_text.lower()
        ) >= 5
    ):
        inferred.append("counters")
    if role_counts.get("recursion", 0) >= 4:
        inferred.append("graveyard")
    data["dashboard_strategy"] = {
        "selected": selected,
        "inferred_for_display_only": [
            x for x in inferred if x not in selected
        ],
        "simulation_used_selected_tags": bool(selected),
    }
    return data


# ---------------------------------------------------------------------------
# Actual opponent phase wrapper: seeded tuck + delayed blink resolution.
# ---------------------------------------------------------------------------

_V470_apply_opponent_old = apply_abstract_opponent_phase
def apply_abstract_opponent_phase(
    state: GameState,
    strategy: Strategy,
    rng: random.Random,
):
    # v4.6's typed interaction uses _spot_remove_target and
    # move_permanent_to_zone by global lookup, so the v4.7 seeded versions
    # above are used automatically. Preserve rng for helpers that need it.
    state._current_opponent_rng = rng
    try:
        return _V470_apply_opponent_old(
            state, strategy, rng
        )
    finally:
        resolve_delayed_blinks(state, strategy)
        state._current_opponent_rng = None


# The v4.6 opponent implementation invokes _spot_remove_target without rng.
# Read the current seeded opponent rng from state in that path.
_V470_spot_remove_seeded = _spot_remove_target
def _spot_remove_target(
    state: GameState,
    strategy: Strategy,
    target: Permanent,
    removal_type: str,
    rng: Optional[random.Random] = None,
):
    return _V470_spot_remove_seeded(
        state, strategy, target, removal_type,
        rng=(
            rng
            or getattr(
                state, "_current_opponent_rng", None
            )
        ),
    )


# ---------------------------------------------------------------------------
# Dashboard handoff file + semantic execution metrics in card impact.
# ---------------------------------------------------------------------------

_V470_impact_rows_old = impact_rows_from_aggregate
def impact_rows_from_aggregate(
    deck: List[Card],
    aggregate: Dict[str, Counter],
    runs: int,
    strategy: Strategy,
) -> List[dict]:
    rows = _V470_impact_rows_old(
        deck, aggregate, runs, strategy
    )
    for row in rows:
        metrics = aggregate.get(
            row["Name"], Counter()
        )
        row["Semantic ability uses"] = round(
            metrics.get(
                "semantic_ability_uses", 0
            ), 2
        )
        row["Probabilistic semantic events"] = round(
            metrics.get(
                "semantic_probabilistic_events", 0
            ), 2
        )
        row["Blinked creatures"] = round(
            metrics.get("blinked_creatures", 0),
            2,
        )
        # WP6/WP7 attrition diagnostics - previously tracked internally via
        # record_impact() but never surfaced in any exported file, which made it
        # impossible to tell from a result ZIP whether the new combat-death/
        # removal-targeting mechanics were actually responsible for an outcome
        # shift. Now exported so future runs give evidence instead of guesses.
        row["Died in combat"] = round(metrics.get("died_in_combat", 0), 2)
        row["Blocked in combat"] = round(metrics.get("combat_blocked", 0), 2)
        row["Removed by opponent"] = round(metrics.get("removed_by_opponent", 0), 2)
        row["Wiped by opponent"] = round(metrics.get("wiped_by_opponent", 0), 2)
        row["Commander damage lethal hits"] = round(metrics.get("commander_damage_lethal", 0), 2)
    return rows


def build_analysis_overview(
    summary: dict,
    impact_rows: List[dict],
) -> dict:
    outcomes = summary.get("outcomes", {})
    sim = summary.get("simulation", {})
    engine_info = summary.get(
        "engine_invariants", {}
    )
    runs = int(sim.get("runs", 0) or 0)

    win_pct = float(
        outcomes.get(
            "win_by_turn_limit_pct", 0
        ) or 0
    )
    loss_pct = float(
        outcomes.get(
            "loss_by_turn_limit_pct", 0
        ) or 0
    )
    unresolved = max(
        0.0, 100.0 - win_pct - loss_pct
    )

    observations = []
    if engine_info.get("status") == "PASS":
        observations.append(
            "Engine-Integrität: PASS — keine erkannten "
            "Ressourcen-/Payment-Verletzungen."
        )
    else:
        observations.append(
            "Engine-Integrität: REVIEW — Ressourcen-/"
            "Payment-Warnungen vor Deckschlussfolgerungen prüfen."
        )

    strategy_info = summary.get(
        "dashboard_strategy", {}
    )
    selected = strategy_info.get(
        "selected", []
    )
    inferred = strategy_info.get(
        "inferred_for_display_only", []
    )
    if not selected:
        if inferred:
            observations.append(
                "Keine Strategy-Tags für die Pilotlogik ausgewählt. "
                "Dashboard erkennt nur zur Anzeige: "
                + ", ".join(inferred)
                + "."
            )
        else:
            observations.append(
                "Keine Strategy-Tags ausgewählt; Pilotlogik läuft neutral."
            )

    if loss_pct >= 35:
        observations.append(
            f"Hoher Gegnerdruck: {loss_pct:.1f}% verlieren "
            "bis zum Turn-Limit."
        )
    if float(
        outcomes.get("reach_111_life_pct", 0) or 0
    ) > 0:
        observations.append(
            "111-Life-Schwelle: "
            f"{float(outcomes.get('reach_111_life_pct', 0)):.2f}%."
        )
    if float(
        outcomes.get("avg_end_hand", 0) or 0
    ) < 2.5:
        observations.append(
            "Card-Flow auffällig knapp: durchschnittliche "
            "Endhand unter 2,5 Karten."
        )

    highlights = []
    for row in impact_rows:
        if row.get(
            "Relative highlight tier"
        ) in {"S", "A"}:
            highlights.append({
                "name": row["Name"],
                "tier": row[
                    "Relative highlight tier"
                ],
                "value_per_seen": row.get(
                    "Estimated value / seen", 0
                ),
            })
        if len(highlights) >= 10:
            break

    return {
        "version": ENGINE_VERSION,
        "runs": runs,
        "opponent": sim.get(
            "requested_opponent_profile",
            sim.get("opponent_profile", ""),
        ),
        "strategy": strategy_info,
        "engine_invariants": engine_info,
        "outcomes": {
            **outcomes,
            "active_at_turn_limit_pct": unresolved,
        },
        "opening": summary.get("opening", {}),
        "turns": summary.get(
            "dashboard_by_turn", []
        ),
        "cumulative_outcomes": summary.get(
            "cumulative_outcomes_by_turn", []
        ),
        "scenarios": summary.get("scenarios", []),
        "opponent_breakdown": summary.get(
            "opponent_breakdown", {}
        ),
        "observations": observations,
        "card_highlights": highlights,
        "note": (
            "Turn-average board/life values use games that are still active "
            "or finish on that turn. Cumulative win/loss percentages use the "
            "full starting population and avoid survivor-bias confusion."
        ),
    }


_V470_pipeline_old = run_pipeline_v440
def run_pipeline_v440(*args, **kwargs):
    result = _V470_pipeline_old(
        *args, **kwargs
    )
    result_dir = Path(result["result_dir"])
    summary = result["summary"]
    impact_rows = result["impact_rows"]

    overview = build_analysis_overview(
        summary, impact_rows
    )
    (result_dir / "analysis_overview.json").write_text(
        json.dumps(
            overview,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Save a compact CSV useful outside the GUI.
    turn_rows = []
    cumulative = {
        int(r["turn"]): r
        for r in overview.get(
            "cumulative_outcomes", []
        )
    }
    for row in overview.get("turns", []):
        t = int(row["turn"])
        turn_rows.append({
            **row,
            "cumulative_win_pct": cumulative.get(
                t, {}
            ).get("win_pct", 0),
            "cumulative_loss_pct": cumulative.get(
                t, {}
            ).get("loss_pct", 0),
            "cumulative_active_pct": cumulative.get(
                t, {}
            ).get("active_pct", 0),
        })
    write_csv(
        result_dir / "analysis_turns.csv",
        turn_rows,
    )

    with (
        result_dir / "AI_ANALYSIS_INSTRUCTIONS.md"
    ).open("a", encoding="utf-8") as fh:
        fh.write("""

## v4.7 direct analysis dashboard
`analysis_overview.json` and `analysis_turns.csv` contain the same compact, non-AI
statistics used by the desktop Analysis window. For a Random opponent run, read
`opponent_breakdown` to compare the actual per-run opponent profiles.

If no Strategy tags were selected, do not assume the simulation used an inferred
archetype. `dashboard_strategy.inferred_for_display_only` is visualization guidance only.

## v4.13.0 Engine Value (Route D)
`engine_value.csv` blends each card's predefined, card-shape-only value with a
value learned from real, persisted simulation history across ALL past runs
(`Data/Learned/engine_value_store.json`, updated by this run). See
`Docs/ENGINE_VALUE_v1.md` for the design and its stated v1 scope boundaries -
this is a reporting-only signal in v1, not yet wired into in-game card
sequencing.
""")

    # v4.13.0 (Route D): blend predefined card-shape value with the
    # cross-run learned value and persist the update. Deck comes from the
    # deck the run was actually simulated with, threaded through result
    # like everything else this wrapper chain already reads from `result`.
    try:
        vm = result.get("value_model") or ValueModel.load()
        deck_for_run = result.get("deck") or []
        strategy_for_run = result.get("strategy")
        by_name_for_run = {c.name: c for c in deck_for_run}
        store = load_engine_value_store()
        store = update_engine_value_store(store, impact_rows)
        save_engine_value_store(store)
        engine_value_rows = []
        for row in impact_rows:
            name = row.get("Name")
            c = by_name_for_run.get(name)
            predefined = (
                predefined_static_value(c, strategy_for_run)
                if c is not None and strategy_for_run is not None
                else 0.0
            )
            learned = store["cards"].get(name, {})
            learned_seen = float(learned.get("seen", 0.0))
            learned_avg = learned.get("learned_value_per_seen")
            blended = vm.engine_value(predefined, learned_avg, learned_seen)
            engine_value_rows.append({
                "Name": name,
                "Predefined value (card shape)": round(predefined, 3),
                "Learned value / seen (all-time)": round(float(learned_avg or 0.0), 3),
                "Learned sample size (all-time seen)": round(learned_seen, 2),
                "Engine value (blended)": round(blended, 3),
            })
        write_csv(result_dir / "engine_value.csv", engine_value_rows)
    except Exception:
        # Route D is additive reporting only (see Docs/ENGINE_VALUE_v1.md) -
        # a failure here must never break the primary run/result delivery
        # that the rest of this wrapper (and the base pipeline before it)
        # already produced.
        pass

    # Base wrapper zipped before these new files were created.
    zip_path = Path(result["zip_path"])
    with _zipfile.ZipFile(
        zip_path, "w",
        compression=_zipfile.ZIP_DEFLATED,
    ) as zf:
        for f in result_dir.rglob("*"):
            if f.is_file():
                zf.write(
                    f,
                    arcname=f.relative_to(result_dir),
                )
    return result


# ---------------------------------------------------------------------------
# v4.44.0 (Punkt 3, additiver Opponent-Model-Cross-Check - siehe Docs/
# README.md v4.44.0 fuer den vollen Auftrag und die Nutzer-Antwort "additiver
# Cross-Check, kleinster Schritt"): App.opponent_model.state_equation lief
# seit v4.38.0 komplett eigenstaendig und wurde nirgends in echte Runs
# eingebunden. Dieser Wrapper aendert das bestehende Simulationsergebnis an
# KEINER Stelle - state_equation.py haengt naemlich NICHT vom echten
# Spielzustand ab (nur von Strategie/Farbe/Bracket/Zugzahl, siehe dessen
# Moduldoc), daher laeuft der Cross-Check als eigener, rein synthetischer
# Seiten-Durchlauf MIT EINER EIGENEN, vom echten Spiel-rng KOMPLETT
# UNABHAENGIGEN random.Random-Instanz - kein einziger zusaetzlicher
# rng.random()-Aufruf im echten Simulationspfad, die bestehenden Ergebnisse/
# Statistiken aendern sich dadurch nicht um ein Bit.
# ---------------------------------------------------------------------------
from App.opponent_model.state_equation import (
    OpponentProfile as _OppModelProfile,
    OpponentState as _OppModelState,
    advance_opponent_state as _opp_model_advance,
    query_board_effects as _opp_model_query_board_effects,
    query_castable_state as _opp_model_query_castable,
    _flavor_cell as _opp_model_flavor_cell,
)
from App.removal_profile.classifier import deck_removal_coverage as _deck_removal_coverage
from App.synergy_profile.classifier import (
    deck_lifegain_synergy_profile as _deck_lifegain_synergy_profile,
)

_OPP_MODEL_STRATEGY_KEYS = ("goldfish", "aggro", "midrange", "control", "horde")
_OPP_MODEL_CROSS_CHECK_SAMPLES = 30
# Bracket fest auf 3 (Referenzniveau) und Farben leer gelassen, da
# App/engine.py aktuell kein Bracket-/Gegnerfarb-Konzept kennt - ein
# disclosed vereinfachender Default, kein gemessener Wert (siehe
# Docs/README.md v4.44.0). Ein "random"-Gegnerprofil (kein echter
# state_equation-Strategieschluessel) faellt ebenfalls auf "midrange"
# zurueck - ebenfalls disclosed, nicht gemessen.
_OPP_MODEL_CROSS_CHECK_BRACKET = 3
# Ab diesem gemittelten Bestandswert (reasoniert, nicht gemessen - siehe
# Docs/README.md v4.44.0) gilt ein Permanenttyp-Bestand als "spuerbar genug",
# um eine fehlende echte Entfernung dafuer als Luecke zu melden.
_OPP_MODEL_GAP_THRESHOLD = 0.15


def _opponent_model_cross_check(
    deck: List["Card"],
    strategy: "Strategy",
    turns: int,
    seed: int,
) -> dict:
    """Baut `_OPP_MODEL_CROSS_CHECK_SAMPLES` unabhaengige, rein synthetische
    App.opponent_model.OpponentState-Verlaeufe auf (je `turns` Zuege, mit
    einer eigenen, vom echten Spiel-rng unabhaengigen random.Random-Instanz),
    mittelt query_board_effects() ueber alle Samples und vergleicht das
    Ergebnis mit der ECHTEN Permanenttyp-Entfernungs-Breite des getesteten
    Decks (App.removal_profile.classifier.deck_removal_coverage). Rein
    additive Diagnose, beeinflusst kein bestehendes Simulationsergebnis -
    siehe Docs/README.md v4.44.0.

    v4.46.0: ergaenzt zusaetzlich das getestete Deck's echtes Lifegain-
    Payoff-Synergieprofil (App.synergy_profile.classifier.
    deck_lifegain_synergy_profile) - siehe jenes Modul und
    Docs/opponent_model_moxfield_methodology_v4_46_0.md fuer die Herleitung:
    statt eines statischen Gilden-weiten Kreuzterms (verworfen, siehe
    Docs/opponent_model_orzhov_deep_dive_v4_45_0.md) wird PRO GETESTETEM
    DECK erkannt, ob sein "whenever you gain life"-Payoff auf einer anderen
    Farbe basiert als seine eigenen Lifegain-Quellen (echte Cross-Color-
    Abhaengigkeit) oder ob es farblich selbstgenuegsam ist. Ebenfalls rein
    additiv - aendert kein bestehendes Simulationsergebnis."""
    strategy_key = (
        strategy.opponent_profile
        if strategy.opponent_profile in _OPP_MODEL_STRATEGY_KEYS
        else "midrange"
    )
    profile = _OppModelProfile(
        strategy=strategy_key, colors=set(), bracket=_OPP_MODEL_CROSS_CHECK_BRACKET
    )

    totals = {
        "passive_value_by_type": Counter(),
        "sac_drain_by_type": Counter(),
        "disruption_lockout_by_type": Counter(),
    }
    n = _OPP_MODEL_CROSS_CHECK_SAMPLES
    for sample in range(n):
        state = _OppModelState()
        sample_rng = random.Random((int(seed) + 1) * 7919 + sample)
        for _ in range(max(1, int(turns))):
            _opp_model_advance(state, profile, sample_rng)
        effects = _opp_model_query_board_effects(state)
        for bucket, value in effects.passive_value_by_type.items():
            totals["passive_value_by_type"][bucket] += value
        for bucket, value in effects.sac_drain_by_type.items():
            totals["sac_drain_by_type"][bucket] += value
        for bucket, value in effects.disruption_lockout_by_type.items():
            totals["disruption_lockout_by_type"][bucket] += value

    averaged = {
        dimension: {bucket: round(value / n, 4) for bucket, value in buckets.items()}
        for dimension, buckets in totals.items()
    }
    coverage = _deck_removal_coverage(deck)
    lifegain_synergy = _deck_lifegain_synergy_profile(deck)

    gaps = []
    for dimension, buckets in averaged.items():
        for bucket, value in buckets.items():
            if value >= _OPP_MODEL_GAP_THRESHOLD and coverage.get(bucket, 0) == 0:
                gaps.append({
                    "dimension": dimension,
                    "permanent_type": bucket,
                    "avg_value": value,
                })

    return {
        "opponent_strategy_used": strategy_key,
        "bracket_assumed": _OPP_MODEL_CROSS_CHECK_BRACKET,
        "samples": n,
        "averaged_board_effects": averaged,
        "deck_removal_coverage": coverage,
        "coverage_gaps": gaps,
        "lifegain_synergy_profile": lifegain_synergy,
    }


# ---------------------------------------------------------------------------
# v4.63.0: ECHTE Turnschleifen-Integration von App/opponent_model/
# state_equation.py - "Punkt 3", jetzt ueber den additiven Cross-Check oben
# (v4.44.0, rein synthetisch, aendert kein Simulationsergebnis) hinaus.
#
# Nutzerauftrag (siehe Docs/README.md v4.63.0 fuer die volle Herleitung):
# statt EINES flachen, den ganzen Tisch reprAesentierenden Aggregat-Profils
# (OPPONENT_PROFILES, unveraendert weiter aktiv als Default) bekommt in
# diesem neuen, ausdruecklich OPT-IN-Modus JEDER Gegner am Tisch sein
# EIGENES OpponentProfile/OpponentState-Paar mit eigener Farbe und
# Strategie. Erste Integrationsstufe, bewusst eng begrenzt:
#   - NUR ein- und zweifarbige Gegner-Identitaeten (siehe
#     _validate_advanced_opponent_seats) - die einzigen mit ausreichend
#     breiten, echten EDHREC-verifizierten Kalibrierungsdaten in
#     opponent_state_weights.json.
#   - NUR Bracket 3 (_ADVANCED_OPPONENT_BRACKET) - kein per-Sitzplatz-
#     Bracket-Feld in dieser Stufe.
#   - Drei-/vier-/fuenffarbige Identitaeten, weitere Brackets und eine
#     breitere Trainingsdeck-Vielfalt sind nach eigener Nutzer-Vorgabe
#     ausdruecklich SPAETEREN Schritten vorbehalten, nicht Teil dieser
#     Version.
#
# NEU, auf ausdruecklichen Nutzerwunsch: Mehrspieler-Zielverteilung. Siehe
# _advanced_opponent_targeting_dilution und den Docstring von
# _apply_advanced_multi_opponent_phase fuer die volle Herleitung.
# ---------------------------------------------------------------------------

_ADVANCED_OPPONENT_KNOWN_COLORS = set("WUBRG")
# Der einzige Bracket, fuer den opponent_state_weights.json auf echten,
# EDHREC-verifizierten Decklisten in ausreichender Breite (mono- UND
# zweifarbig) kalibriert wurde - siehe Docs/opponent_model_calibration_
# v4_39_0.md ff. Andere Brackets bleiben in dieser ersten Integrationsstufe
# ausdruecklich gesperrt statt stillschweigend mit ungeeigneten Gewichten zu
# laufen.
_ADVANCED_OPPONENT_BRACKET = 3
# Reasoniert, nicht gemessen (derselbe offengelegte Stil wie z.B.
# bracket_scaling.opening_mana_boost in opponent_state_weights.json): so
# gewaehlt, dass ein Bracket-3-Midrange-Gegner mit vollem Board (board_
# presence-Cap 10.0) bei genau EINEM Gegner am Tisch (Verduennung=1.0, siehe
# unten) groessenordnungsmaessig im Bereich des alten
# OPPONENT_PROFILES["midrange"]["damage_scale"]-Modells liegt - keine exakte
# Aequivalenz beansprucht, siehe Docs/README.md v4.63.0.
_ADVANCED_OPPONENT_COMBAT_DAMAGE_PER_BOARD_UNIT = 1.0


def _validate_advanced_opponent_seats(seats: List[Dict[str, Any]]) -> None:
    """Harte, disclosed Durchsetzung des Umfangs dieser ersten
    Integrationsstufe - ein falsch konfigurierter Sitzplatz soll laut
    fehlschlagen statt still auf einen ungeeigneten Default zurueckzufallen
    (dieses Projekt bevorzugt durchgaengig ein echtes Unterzaehlen/einen
    Fehler gegenueber erfundener/stiller Praezision)."""
    if not seats:
        raise ValueError(
            "advanced_opponent_model=True erfordert mindestens einen Eintrag "
            "in advanced_opponent_seats (je ein Gegner-Sitzplatz)."
        )
    for i, seat in enumerate(seats):
        strat = str(seat.get("strategy", "")).lower()
        if strat not in _OPP_MODEL_STRATEGY_KEYS or strat == "goldfish":
            raise ValueError(
                f"advanced_opponent_seats[{i}]: strategy={seat.get('strategy')!r} "
                "ist kein unterstuetzter echter Gegnertyp "
                "(aggro/midrange/control/horde)."
            )
        colors = {str(c).upper() for c in seat.get("colors", [])}
        if not colors.issubset(_ADVANCED_OPPONENT_KNOWN_COLORS):
            raise ValueError(
                f"advanced_opponent_seats[{i}]: unbekannte Farbe(n) in "
                f"{sorted(colors)} (erlaubt: W/U/B/R/G)."
            )
        if not (1 <= len(colors) <= 2):
            raise ValueError(
                f"advanced_opponent_seats[{i}]: {len(colors)} Farben - diese "
                "erste Integrationsstufe unterstuetzt ausdruecklich nur ein- "
                "oder zweifarbige Gegner-Identitaeten. Drei-/vier-/"
                "fuenffarbige Identitaeten sind ein spaeterer Schritt (siehe "
                "Docs/README.md v4.63.0)."
            )
        if "bracket" in seat and int(seat["bracket"]) != _ADVANCED_OPPONENT_BRACKET:
            raise ValueError(
                f"advanced_opponent_seats[{i}]: bracket={seat['bracket']!r} "
                f"angefordert, aber diese erste Integrationsstufe "
                f"unterstuetzt ausschliesslich Bracket "
                f"{_ADVANCED_OPPONENT_BRACKET} (siehe Docs/README.md v4.63.0)."
            )


def _build_advanced_opponent_table(seats: List[Dict[str, Any]]):
    """Baut EIN (OpponentProfile, OpponentState)-Paar je Sitzplatz -
    unabhaengige, individuelle Gegner statt eines Gesamt-Aggregats. Reine
    Konstruktion, keine Zufallszahlen - der eigentliche Zustandsfortschritt
    passiert ausschliesslich in advance_opponent_state()."""
    _validate_advanced_opponent_seats(seats)
    table = []
    for seat in seats:
        strat = str(seat["strategy"]).lower()
        colors = {str(c).upper() for c in seat.get("colors", [])}
        profile = _OppModelProfile(strategy=strat, colors=colors, bracket=_ADVANCED_OPPONENT_BRACKET)
        table.append((profile, _OppModelState()))
    return table


# ---------------------------------------------------------------------------
# v4.66.0 ("Kalibrierungs-Synthese Teil 1" - siehe Docs/README.md v4.66.0 und
# App/opponent_model/state_equation.py's Moduldoc "v4.66.0" fuer die volle
# Herleitung): rein additiver, opt-in Sitzplatz-Schluessel "flavor" fuer
# advanced_opponent_seats. Ein Sitzplatz OHNE diesen Schluessel (der weit
# haeufigere, bisherige Fall) verhaelt sich an BEIDEN Stellen unten exakt wie
# vor dieser Version - siehe test_v4660_flavor_strategy_matrix.py fuer die
# Regressionsabsicherung.
# ---------------------------------------------------------------------------
_V466_validate_advanced_opponent_seats_old = _validate_advanced_opponent_seats
def _validate_advanced_opponent_seats(seats: List[Dict[str, Any]]) -> None:
    """Fuehrt zuerst alle bisherigen Pruefungen unveraendert aus, prueft dann
    zusaetzlich einen optionalen "flavor"-Schluessel je Sitzplatz, WENN
    vorhanden: er muss auf eine echte Zelle in Data/Models/flavor_strategy_
    matrix.json passen, deren color_identity exakt zu den Farben DIESES
    Sitzplatzes passt - sonst wird laut (ValueError) statt still auf die
    Basis-Kurve/den Farbmodifikator zurueckgefallen, konsistent mit der
    bestehenden "harter Fehler statt stiller Fallback"-Praxis dieser
    Funktion (siehe deren urspruengliches Docstring oben)."""
    _V466_validate_advanced_opponent_seats_old(seats)
    for i, seat in enumerate(seats):
        flavor = seat.get("flavor")
        if not flavor:
            continue
        colors = {str(c).upper() for c in seat.get("colors", [])}
        if _opp_model_flavor_cell(colors, str(flavor)) is None:
            raise ValueError(
                f"advanced_opponent_seats[{i}]: flavor={flavor!r} ist keine "
                f"bekannte Flavor-Strategie-Matrix-Zelle fuer die Farbe(n) "
                f"{sorted(colors)} (siehe Data/Models/flavor_strategy_"
                f"matrix.json - Schluessel-Format \"<Farbidentitaet>/<Flavor-"
                f"Slug>\" oder nur \"<Flavor-Slug>\", wenn er fuer genau eine "
                f"Farbidentitaet eindeutig ist)."
            )


_V466_build_advanced_opponent_table_old = _build_advanced_opponent_table
def _build_advanced_opponent_table(seats: List[Dict[str, Any]]):
    """Baut den Tisch unveraendert ueber die alte Version, setzt danach
    zusaetzlich OpponentProfile.flavor auf jedem Sitzplatz, der einen
    (bereits durch _validate_advanced_opponent_seats geprueften) "flavor"-
    Schluessel traegt - siehe App/opponent_model/state_equation.py's
    Moduldoc "v4.66.0" fuer die eigentliche Wirkung dieses Felds. Sitzplaetze
    ohne "flavor"-Schluessel bleiben unangetastet (profile.flavor bleibt bei
    seinem Dataclass-Default None)."""
    table = _V466_build_advanced_opponent_table_old(seats)
    for (profile, _opp_state), seat in zip(table, seats):
        flavor = seat.get("flavor")
        if flavor:
            profile.flavor = str(flavor)
    return table


def _get_advanced_opponent_table(state: GameState, strategy: Strategy):
    """Baut den Sitzplatz-Tisch EINMALIG pro Partie auf und haengt ihn lose
    an `state` (dynamisches Attribut _advanced_opponent_table, kein
    deklariertes GameState-Feld - derselbe Stil wie state.
    _current_opponent_rng weiter oben), damit jeder Sitzplatz ueber mehrere
    Aufrufe dieser Funktion (= mehrere Runden) hinweg weiterwaechst statt bei
    jedem Aufruf bei 0 neu zu starten."""
    table = getattr(state, "_advanced_opponent_table", None)
    if table is None:
        table = _build_advanced_opponent_table(strategy.advanced_opponent_seats)
        state._advanced_opponent_table = table
    return table


def _advanced_opponent_targeting_dilution(num_players: int) -> float:
    """Nutzer-Vorgabe (siehe Docs/README.md v4.63.0): bei n Spielern am
    Tisch insgesamt (der getestete Spieler + alle Gegner-Sitzplaetze)
    entscheidet sich ein EINZELNER Gegner bei jeder EINZELZIEL-Aktion
    (gezielte Entfernung; Kampf-/Praesenzdruck) fuer GENAU EIN Ziel unter
    den uebrigen (n-1) Spielern - das getestete Deck ist nur EINES dieser
    (n-1) moeglichen Ziele. Unter der Annahme einer Gleichverteilung ueber
    alle moeglichen Ziele (kein Modell dafuer, dass ein Gegner gezielt das
    staerkste/schwaechste Ziel bevorzugt - eine bewusste, offengelegte
    Vereinfachung dieser ersten Integrationsstufe) trifft eine solche Aktion
    das getestete Deck also im Mittel mit Wahrscheinlichkeit 1/(n-1).

    Board-Wipes sind bewusst NICHT hierueber verduennt (ein echter Wipe
    trifft symmetrisch alle Boards am Tisch gleichzeitig, unabhaengig von
    der Tischgroesse) - ebenso combo_finish_readiness (typischerweise eine
    "du gewinnst das Spiel"-Bedingung ohne Einzelziel) und die drei
    zerfallenden Bestaende passive_value_by_type/sac_drain_by_type/
    disruption_lockout_by_type (wachsen pro Sitzplatz unveraendert weiter,
    werden aber - wie schon im additiven Cross-Check seit v4.44.0 - in
    dieser Version noch in KEINEN echten Spieleffekt umgesetzt, siehe
    _apply_advanced_multi_opponent_phase)."""
    return 1.0 / max(1, num_players - 1)


# ---------------------------------------------------------------------------
# v4.64.0: "?" (zufaellig) je Sitzplatz, fuer Farbe UND Strategie getrennt -
# siehe App/gui.py's neuer "Gegnerprofil"-Dialog. Aufgeloest EINMAL PRO RUN
# (nicht einmal pro GUI-Klick, nicht einmal pro Zug) - derselbe Zeitpunkt und
# derselbe reproduzierbare Stil wie das bereits bestehende "random"-
# opponent_profile (siehe RANDOM_OPPONENT_CHOICES/simulate_game_v440 weiter
# unten), nur mit einer eigenen, unabhaengigen random.Random-Instanz (eigene
# Multiplikator-Konstante), damit die beiden Zufallsentscheidungen einander
# nicht korrelieren.
# ---------------------------------------------------------------------------

_ADVANCED_OPPONENT_RANDOM_MARKERS = ("random", "?", "zufällig", "zufaellig", "zufallig")

# Alle 5 mono- und 10 zweifarbigen Identitaeten - exakt der Umfang, den
# _validate_advanced_opponent_seats fuer diese erste Integrationsstufe
# ohnehin zulaesst (siehe dort). Von Hand aufgezaehlt statt per itertools,
# da die Liste klein und statisch ist und dieses Modul bislang kein
# itertools importiert.
RANDOM_ADVANCED_OPPONENT_COLOR_CHOICES = (
    ("W",), ("U",), ("B",), ("R",), ("G",),
    ("W", "U"), ("W", "B"), ("W", "R"), ("W", "G"),
    ("U", "B"), ("U", "R"), ("U", "G"),
    ("B", "R"), ("B", "G"),
    ("R", "G"),
)


def _seat_wants_random_strategy(seat: Dict[str, Any]) -> bool:
    return str(seat.get("strategy", "")).strip().lower() in _ADVANCED_OPPONENT_RANDOM_MARKERS


def _seat_wants_random_colors(seat: Dict[str, Any]) -> bool:
    colors = seat.get("colors")
    if colors is None:
        return False
    if isinstance(colors, str):
        return colors.strip().lower() in _ADVANCED_OPPONENT_RANDOM_MARKERS
    colors = list(colors)
    return len(colors) == 1 and str(colors[0]).strip().lower() in _ADVANCED_OPPONENT_RANDOM_MARKERS


def _resolve_advanced_opponent_seats_for_run(
    seats: Sequence[Dict[str, Any]], seed: int, run_id: int
) -> List[Dict[str, Any]]:
    """Ersetzt jeden "?"-Marker (Farbe und/oder Strategie, je Sitzplatz
    unabhaengig) durch einen konkreten, reproduzierbaren Wert - eine eigene
    random.Random-Instanz, ausschliesslich aus (seed, run_id) gebildet, nie
    aus dem geteilten Spiel-rng. Sitzplaetze ohne "?"-Marker bleiben
    unveraendert. Gibt bei keinem einzigen Marker dieselbe Liste zurueck
    (billiger No-op-Pfad fuer den weit haeufigeren Fall fest konfigurierter
    Sitzplaetze)."""
    if not any(_seat_wants_random_strategy(s) or _seat_wants_random_colors(s) for s in seats):
        return list(seats)
    chooser = random.Random((int(seed) + 1) * 4001141 + int(run_id))
    resolved = []
    for seat in seats:
        seat = dict(seat)
        if _seat_wants_random_strategy(seat):
            seat["strategy"] = chooser.choice(RANDOM_OPPONENT_CHOICES)
        if _seat_wants_random_colors(seat):
            seat["colors"] = list(chooser.choice(RANDOM_ADVANCED_OPPONENT_COLOR_CHOICES))
        resolved.append(seat)
    return resolved


_V464_simulate_game_old = simulate_game_v440
def simulate_game_v440(
    deck: List[Card],
    strategy_template: ScenarioStrategy,
    cfg: SimConfig,
    policy: MulliganPolicy,
    rng: random.Random,
    run_id: int,
):
    """v4.64.0: loest "?"-Marker in strategy_template.advanced_opponent_seats
    auf, BEVOR das eigentliche Spiel beginnt (derselbe Zeitpunkt wie das
    bestehende "random"-opponent_profile in der inneren, hier umwickelten
    Version dieser Funktion) - siehe _resolve_advanced_opponent_seats_for_run
    fuer die Reproduzierbarkeits-Herleitung. Ohne einen einzigen "?"-Marker
    (der weit haeufigere Fall) ist dies ein reiner Durchreich-Wrapper ohne
    jede Verhaltensaenderung."""
    if getattr(strategy_template, "advanced_opponent_model", False) and strategy_template.advanced_opponent_seats:
        resolved = _resolve_advanced_opponent_seats_for_run(
            strategy_template.advanced_opponent_seats, cfg.seed, run_id
        )
        if resolved != list(strategy_template.advanced_opponent_seats):
            strategy_template = replace(strategy_template, advanced_opponent_seats=resolved)
    return _V464_simulate_game_old(
        deck, strategy_template, cfg, policy, rng, run_id
    )


def _apply_advanced_multi_opponent_phase(
    state: GameState,
    strategy: Strategy,
    rng: random.Random,
) -> None:
    """Der eigentliche neue Mehrgegner-Zug-Effekt - nur aktiv, wenn
    strategy.advanced_opponent_model=True gesetzt ist (siehe der Wrapper von
    apply_abstract_opponent_phase direkt unterhalb dieser Funktion). Fuer
    das volle Design (Umfang, Verduennung, was noch nicht umgesetzt ist)
    siehe den Modulkommentar oben und Docs/README.md v4.63.0.

    Ablauf je Aufruf (= eine Runde, in der jeder Sitzplatz einmal am Zug
    ist, analog zur alten Semantik von apply_abstract_opponent_phase):
    jeder Sitzplatz rueckt seinen eigenen OpponentState per
    advance_opponent_state() genau einmal vor (table_size = Sitzplaetze +
    getesteter Spieler, dieselbe Zahl wie fuer die Zielverduennung), dann
    wird ueber query_castable_state() abgefragt, ob dieser Sitzplatz gerade
    Interaktion/einen Wipe zur Verfuegung hat. Kampf-/Praesenzdruck und
    gezielte Entfernung werden mit der Zielverduennung gewuerfelt (siehe
    _advanced_opponent_targeting_dilution); ein Wipe wird IMMER angewendet,
    wenn er verfuegbar ist."""
    seats = _get_advanced_opponent_table(state, strategy)
    num_players = len(seats) + 1
    dilution = _advanced_opponent_targeting_dilution(num_players)

    state.virtual_opponent_graveyard += max(1, int(0.8 + state.turn * 0.25))
    try_probabilistic_semantics(state, strategy, rng)

    for profile, opp_state in seats:
        _opp_model_advance(opp_state, profile, rng, table_size=num_players)
        cq = _opp_model_query_castable(opp_state, rng)
        seat_label = f"{profile.strategy}/{''.join(sorted(profile.colors)) or 'C'}"

        # --- Kampf-/Praesenzdruck: Einzelziel, daher verduennt -------------
        if opp_state.board_presence > 0 and rng.random() < dilution:
            damage = opp_state.board_presence * _ADVANCED_OPPONENT_COMBAT_DAMAGE_PER_BOARD_UNIT
            damage *= rng.uniform(0.70, 1.30)
            if damage > 0:
                state.life -= damage
                state.damage_taken += damage
                state.log(
                    f"ADVANCED {seat_label}: took {damage:.1f} combat/pressure "
                    f"damage (targeted, avg 1/{num_players - 1} chance)"
                )
                if state.life <= 0 and state.lost_turn is None:
                    state.lost_turn = state.turn

        # --- Gezielte Entfernung: Einzelziel, daher verduennt --------------
        if cq.has_interaction and rng.random() < dilution:
            targets = [
                p for p in state.battlefield
                if not p.card.is_land and p.card.is_permanent
            ]
            if targets:
                target = combat_importance.choose_removal_target(
                    sys.modules[__name__], state, strategy, targets, rng
                )
                removal_type = choose_removal_type(profile.strategy, rng, wide=False)
                kws = effective_keywords_in_state(target, state)

                if "hexproof" in kws:
                    state.log(f"ADVANCED {removal_type} failed: {target.card.name} has hexproof")
                elif "ward" in kws and rng.random() < 0.35:
                    state.log(
                        f"ADVANCED {removal_type} declined/failed into ward "
                        f"on {target.card.name}"
                    )
                elif try_reactive_protection(
                    state, strategy, wide=False, removal_type=removal_type, target=target,
                ):
                    pass
                elif removal_type == "destroy" and "indestructible" in kws:
                    state.log(f"ADVANCED destroy failed: {target.card.name} is indestructible")
                elif removal_type == "destroy" and try_semantic_board_protection(state, strategy, target):
                    pass
                else:
                    _spot_remove_target(state, strategy, target, removal_type)
                    record_impact(state, target.card.name, "removed_by_opponent", 1)
                    state.log(f"ADVANCED {removal_type} ({seat_label}): {target.card.name}")

        # --- Board-Wipe: NICHT verduennt, trifft den ganzen Tisch ----------
        if cq.has_wipe:
            removal_type = choose_removal_type(profile.strategy, rng, wide=True)

            if try_reactive_protection(state, strategy, wide=True, removal_type=removal_type):
                if removal_type != "destroy" or any(
                    "exile any number of target creatures you control"
                    in strip_reminder_text(c.oracle_text).lower()
                    for c in state.graveyard[-1:]
                ):
                    guard_resource_invariants(state, "advanced protected wipe")
                    continue

            survivors = set()
            if removal_type == "destroy":
                candidates = sorted(
                    list(state.creatures()),
                    key=lambda p: generic_tutor_score(p.card, strategy.tutor_priority),
                    reverse=True,
                )
                for p in candidates:
                    if "indestructible" in effective_keywords_in_state(p, state):
                        survivors.add(id(p))
                        continue
                    if try_semantic_board_protection(state, strategy, p):
                        survivors.add(id(p))

            affected = []
            destination = _wipe_destination(removal_type)
            for p in list(state.battlefield):
                if not p.card.is_creature:
                    continue
                if removal_type == "destroy":
                    if id(p) in survivors or "indestructible" in effective_keywords_in_state(p, state):
                        continue
                affected.append(p.card.name)
                record_impact(state, p.card.name, "wiped_by_opponent", 1)
                move_permanent_to_zone(
                    state, strategy, p, destination,
                    reason=f"{removal_type} boardwipe (advanced/{seat_label})",
                )

            if affected:
                state.log(f"ADVANCED {removal_type} boardwipe ({seat_label}): " + ", ".join(affected))

    apply_commander_zone_state_based_actions(state, strategy)
    guard_resource_invariants(state, "advanced multi-opponent phase")


_V463_apply_opponent_old = apply_abstract_opponent_phase
def apply_abstract_opponent_phase(
    state: GameState,
    strategy: Strategy,
    rng: random.Random,
):
    """v4.63.0: additiver Einstiegspunkt fuer das neue Mehrgegner-
    Zustandsmodell. Ausschliesslich aktiv, wenn
    strategy.advanced_opponent_model=True gesetzt ist - Default bleibt
    unveraendert False, sodass JEDER bestehende Aufrufer (alle frueheren
    Pipeline-Versionen, alle bestehenden Tests) weiterhin exakt denselben
    Code wie vor dieser Version durchlaeuft, kein Bit anders."""
    if getattr(strategy, "advanced_opponent_model", False):
        return _apply_advanced_multi_opponent_phase(state, strategy, rng)
    return _V463_apply_opponent_old(state, strategy, rng)


_V4440_pipeline_old = run_pipeline_v440
def run_pipeline_v440(*args, **kwargs):
    result = _V4440_pipeline_old(*args, **kwargs)
    try:
        deck = result.get("deck") or []
        strategy = result.get("strategy")
        sim_cfg = (result.get("summary") or {}).get("simulation", {})
        turns = int(sim_cfg.get("turns", 10) or 10)
        seed = int(sim_cfg.get("seed", 1) or 1)
        if strategy is not None:
            cross_check = _opponent_model_cross_check(deck, strategy, turns, seed)
            if isinstance(result.get("summary"), dict):
                result["summary"]["opponent_model_cross_check"] = cross_check
            result_dir = Path(result["result_dir"])
            (result_dir / "opponent_model_cross_check.json").write_text(
                json.dumps(cross_check, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            ai_path = result_dir / "AI_ANALYSIS_INSTRUCTIONS.md"
            if ai_path.exists():
                with ai_path.open("a", encoding="utf-8") as fh:
                    fh.write("""

## v4.44.0 Opponent-Model-Cross-Check (additive Diagnose)
`opponent_model_cross_check.json` vergleicht den simulierten, ABSTRAKTEN
Gegner-Board-Fussabdruck (App/opponent_model/state_equation.py, bislang
eigenstaendig und nicht Teil der eigentlichen Zugschleife) mit der ECHTEN
Permanenttyp-Entfernungs-Breite dieses Decks. `coverage_gaps` listet jeden
Permanenttyp, fuer den der simulierte Gegner spuerbaren Bestand aufbaut
(Bracket 3 als fester Referenzwert angenommen - siehe Docs/README.md
v4.44.0), das Deck aber laut `App/removal_profile/classifier.py` KEINE
verifizierte Entfernung besitzt. Diese Diagnose beeinflusst keine der
uebrigen Dateien in diesem Ergebnisordner in irgendeiner Weise.

### v4.46.0 Lifegain-Synergieprofil (additive Diagnose, Teil derselben Datei)
`lifegain_synergy_profile` innerhalb derselben Datei zeigt, ob dieses Decks
echter "whenever you gain life"-Payoff (z. B. Sanguine Bond) auf einer
ANDEREN Farbe basiert als seine eigenen erkannten Lifegain-Quellen (z. B.
Soul Warden) - `cross_color_dependency: true` - oder ob es farblich
selbstgenuegsam ist. Siehe App/synergy_profile/classifier.py und
Docs/opponent_model_moxfield_methodology_v4_46_0.md: ein Gilden- oder
Sub-Strategie-weiter Kreuzterm wurde bewusst NICHT eingefuehrt, weil echte
Decks (Moxfield/EDHREC, v4.45.0+v4.46.0) hier je nach Commander/Build
unterschiedlich ausfallen - diese Pro-Deck-Erkennung ersetzt einen
statischen Gewichts-Fix.
""")
    except Exception:
        # Rein additive Diagnose (siehe Docs/README.md v4.44.0) - ein Fehler
        # hier darf die eigentliche Ergebnisauslieferung nie gefaehrden.
        pass
    return result


# ---------------------------------------------------------------------------
# v4.65.0: Konfigurierbare Win-Condition-Anzeige (statt hartcodierter
# "111 Leben"-Schwelle) + Handzusammensetzung im Zeitverlauf.
#
# Nutzerauftrag (siehe Docs/README.md v4.65.0 fuer die volle Herleitung): die
# Auswertung zeigte bislang eine fest einprogrammierte "111 Leben"-Kennzahl
# (GameState.milestones{50,60,80,100,111}/check_life_milestones oben),
# UNABHAENGIG davon, welche Win Condition/welches Setup auf der Scenario-
# Oberflaeche (ScenarioPage in App/gui.py) tatsaechlich konfiguriert wurde.
# Das Scenario-System selbst (new_scenario/normalize_scenario/
# scenario_status weiter oben) kennt bereits beliebige Schwellen (Leben,
# Laender, Food, Treasure, Clues) UND beliebige Kartenanforderungen/derived-
# Praedikate fuer Szenarien vom Kind "Win Condition" - diese Flexibilitaet
# wurde bislang nur in der "Win Conditions"-Tabelle (Match %/Median Turn,
# siehe AnalysisPage._build_scenarios in App/gui.py) sichtbar gemacht, nicht
# aber in der Uebersicht/Opponent-Breakdown, wo weiterhin die feste 111-
# Schwelle auftauchte.
#
# Diese Version macht die Uebersicht/Opponent-Breakdown-Anzeige GENERISCH:
# sie aggregiert reach %/median turn ueber ALLE aktiven Szenarien vom Kind
# "Win Condition" (sc.get("kind") == "Win Condition" - exakt dasselbe
# Filterkriterium, das an anderer Stelle im Code bereits verwendet wird,
# z.B. fuer wc_preservation_bias weiter oben). Ist keine Win-Condition
# konfiguriert, wird das EHRLICH so angezeigt ("keine Win Condition
# konfiguriert") statt stillschweigend auf 111 zurueckzufallen - passend
# zum Projektgrundsatz, keine Zahlen zu erfinden/zu verschleiern.
#
# Das alte milestones-System (life_50_turn...life_111_turn,
# reach_111_life_pct, reach_111_pct) bleibt UNVERAENDERT im Hintergrund
# bestehen (rueckwaertskompatibel fuer evtl. externe Auswertungen/Tests) -
# es wird nur nicht mehr als GUI-Hauptkennzahl angezeigt. Bilbo, Birthday
# Celebrant's eigene echte Karten-Faehigkeit (state.life >= 111 fuer die
# Command-Zone-Aktivierung, siehe try_activate_bilbo/maybe_execute_
# focused_win_condition oben) ist davon KOMPLETT unberuehrt - das ist eine
# andere, kartenspezifische Spielmechanik, keine Analyse-Anzeige.
#
# Zusaetzlich (eigenstaendige Auswertungs-Durchsicht, ebenfalls Nutzerauftrag
# - siehe Docs/README.md v4.65.0): Handzusammensetzung ueber die Zeit
# (Laender/Ramp/Interaction/Card Advantage/Kreaturen/sonstige Spells/
# Sonstiges), je Turn gemittelt ueber alle noch aktiven Runs - macht
# sichtbar, ob die Hand im Schnitt zu landlastig wird oder Interaction/Ramp
# im spaeten Spiel ausgeht. Kategorien nutzen die bereits bestehende,
# deckweit kalibrierte role_set()-Klassifikation (siehe ROLE_REACTIVE weiter
# oben) statt einer neu erfundenen Heuristik.
# ---------------------------------------------------------------------------

_HAND_COMPOSITION_BUCKETS = (
    "lands", "ramp", "interaction", "card_advantage", "creatures", "spells", "other",
)
_HAND_COMPOSITION_FIELDS = tuple(f"hand_{b}" for b in _HAND_COMPOSITION_BUCKETS)


def _hand_composition_category(card: Card) -> str:
    """Ordnet eine Handkarte GENAU EINEM der _HAND_COMPOSITION_BUCKETS zu.

    Reihenfolge ist Absicht: Land vor Rolle vor Type-Line-Fallback, damit
    z.B. eine Kreatur mit Ramp-Rolle ("Mana-Dork") als 'ramp' und nicht als
    'creatures' gezaehlt wird - deckungsgleich mit der uebrigen role_set()-
    Verwendung im restlichen Engine-Code (z.B. cast_score_v4 weiter oben).
    Jede Handkarte faellt in GENAU einen Bucket (kein Doppelzaehlen, keine
    Luecke) - "other" faengt alles ohne erkannte Rolle/Type-Line-Match auf
    (Artefakte, Verzauberungen, Planeswalker, Battles, ...).
    """
    if card.is_land:
        return "lands"
    roles = card.roles
    if roles & ROLE_REACTIVE:
        return "interaction"
    if roles & {"ramp", "burst_mana"}:
        return "ramp"
    if roles & {"draw", "draw_engine", "tutor", "engine"}:
        return "card_advantage"
    type_line = card.type_line or ""
    if "Creature" in type_line:
        return "creatures"
    if "Instant" in type_line or "Sorcery" in type_line:
        return "spells"
    return "other"


def _hand_composition_counts(hand) -> Dict[str, int]:
    counts = {b: 0 for b in _HAND_COMPOSITION_BUCKETS}
    for card in hand:
        counts[_hand_composition_category(card)] += 1
    return {f"hand_{b}": counts[b] for b in _HAND_COMPOSITION_BUCKETS}


_V465_turn_row_old = _turn_row_v440
def _turn_row_v440(
    run_id: int,
    turn: int,
    state: GameState,
    strategy: ScenarioStrategy,
    start_hand: List[str],
    land_name: str,
    casts: List[str],
    mana_before: float,
    structural_access_before: Set[str],
    sc_progress: Dict[str, dict],
) -> dict:
    row = _V465_turn_row_old(
        run_id, turn, state, strategy,
        start_hand, land_name, casts,
        mana_before, structural_access_before,
        sc_progress,
    )
    row.update(_hand_composition_counts(state.hand))
    return row


def _wc_kind_scenarios(scenarios) -> List[dict]:
    """Alle aktivierten Szenarien vom Kind 'Win Condition' - dasselbe Filter-
    kriterium wie an anderer Stelle im Code (z.B. wc_preservation_bias)."""
    return [
        sc for sc in (scenarios or [])
        if sc.get("enabled", True) and sc.get("kind") == "Win Condition"
    ]


_V465_stats_add_old = StreamingStatsV440.add
def _streaming_stats_add_v465(self, rr: dict, tr: List[dict], sr: List[dict]):
    _V465_stats_add_old(self, rr, tr, sr)

    if not hasattr(self, "_wc_reached_count"):
        self._wc_reached_count = 0
        self._wc_reached_turns = []
        self._wc_configured = False
    wc_rows = [row for row in sr if row.get("kind") == "Win Condition"]
    if wc_rows:
        self._wc_configured = True
        reached_turns = [
            int(row["first_reached_turn"])
            for row in wc_rows
            if row.get("first_reached_turn") not in (None, "")
        ]
        if reached_turns:
            self._wc_reached_count += 1
            self._wc_reached_turns.append(min(reached_turns))

    for row in tr:
        t = int(row["turn"])
        a = self._dashboard_turn_stats[t]
        for field_name in _HAND_COMPOSITION_FIELDS:
            a[field_name] += float(row.get(field_name, 0) or 0)

    profile = str(rr.get("opponent_profile", "unknown"))
    group = self._opponent_dashboard.get(profile)
    if group is not None:
        if "wc_reached" not in group:
            group["wc_reached"] = 0
        if wc_rows and any(row.get("reached") for row in wc_rows):
            group["wc_reached"] += 1
        for row in tr:
            t = int(row["turn"])
            a = group["turns"][t]
            for field_name in _HAND_COMPOSITION_FIELDS:
                a[field_name] += float(row.get(field_name, 0) or 0)

StreamingStatsV440.add = _streaming_stats_add_v465


_V465_average_dashboard_turns_old = _average_dashboard_turns
def _average_dashboard_turns(raw: Dict[int, Counter], turns: int) -> List[dict]:
    out = _V465_average_dashboard_turns_old(raw, turns)
    for row in out:
        a = raw.get(row["turn"])
        if not a or not a["count"]:
            continue
        n = float(a["count"])
        for field_name in _HAND_COMPOSITION_FIELDS:
            row[f"avg_{field_name}"] = float(a.get(field_name, 0)) / n
    return out


_V465_summary_old = streaming_summary_v440
def streaming_summary_v440(
    deck: List[Card],
    stats: StreamingStatsV440,
    cfg: SimConfig,
    strategy: ScenarioStrategy,
    impact_rows: List[dict],
    detailed_runs_logged: int,
    log_policy: str,
) -> dict:
    data = _V465_summary_old(
        deck, stats, cfg, strategy,
        impact_rows, detailed_runs_logged,
        log_policy,
    )
    n = max(1, stats.run_count)
    wc_scenarios = _wc_kind_scenarios(strategy.scenarios)
    wc_configured = bool(wc_scenarios) or bool(getattr(stats, "_wc_configured", False))
    reached_turns = getattr(stats, "_wc_reached_turns", [])
    data["outcomes"]["win_condition_configured"] = wc_configured
    data["outcomes"]["win_condition_names"] = [sc["name"] for sc in wc_scenarios]
    data["outcomes"]["win_condition_reach_pct"] = (
        100.0 * getattr(stats, "_wc_reached_count", 0) / n if wc_configured else 0.0
    )
    data["outcomes"]["win_condition_median_turn"] = (
        percentile([float(x) for x in reached_turns], .5) if reached_turns else None
    )

    opponent_dashboard = getattr(stats, "_opponent_dashboard", {})
    for profile, row in data.get("opponent_breakdown", {}).items():
        group = opponent_dashboard.get(profile, {})
        gr = max(1, int(group.get("runs", 0) or 0))
        row["win_condition_reach_pct"] = (
            100.0 * int(group.get("wc_reached", 0) or 0) / gr if wc_configured else 0.0
        )
    return data


_V465_build_overview_old = build_analysis_overview
def build_analysis_overview(summary: dict, impact_rows: List[dict]) -> dict:
    overview = _V465_build_overview_old(summary, impact_rows)
    outcomes = overview.get("outcomes", {})
    obs = list(overview.get("observations", []))

    # Ersetzt die alte fest verdrahtete "111-Life-Schwelle"-Beobachtung (aus
    # der Originalfassung von build_analysis_overview weiter oben) durch
    # eine Beobachtung, die die tatsaechlich konfigurierte(n) Win
    # Condition(s) widerspiegelt.
    obs = [line for line in obs if not line.startswith("111-Life-Schwelle:")]
    if outcomes.get("win_condition_configured"):
        names = ", ".join(outcomes.get("win_condition_names") or []) or "Win Condition"
        pct = float(outcomes.get("win_condition_reach_pct", 0) or 0)
        if pct > 0:
            median = outcomes.get("win_condition_median_turn")
            median_txt = f", Median Turn {median:g}" if median is not None else ""
            obs.append(f"Win Condition erreicht ({names}): {pct:.2f}%{median_txt}.")
    else:
        obs.append(
            "Keine Win Condition (Scenario-Kind \"Win Condition\") konfiguriert - "
            "auf der Setup/Win-Condition-Oberflaeche ein Szenario mit diesem Kind "
            "anlegen, um hier eine flexible Zielkennzahl statt eines festen "
            "Leben-Schwellenwerts zu sehen."
        )
    overview["observations"] = obs

    # Bislang berechnet, aber nie in analysis_overview.json weitergereicht
    # (siehe combat_and_removal_diagnostics in streaming_summary_v440 weiter
    # oben) - eigenstaendige Durchsicht der Auswertung (Docs/README.md
    # v4.65.0) ergab, dass diese Daten fuer die Deck-Abstimmung nuetzlich
    # sind (welche Karten sterben/werden entfernt), aber in der GUI bislang
    # gar nicht sichtbar waren.
    overview["combat_and_removal_diagnostics"] = summary.get(
        "combat_and_removal_diagnostics", {}
    )
    return overview


# ---------------------------------------------------------------------------
# v4.65.1: zwei Bugfixes, gefunden durch kritische Durchsicht zweier echter
# GUI-Runs (Bilbo V1 + Aziza V2, vom Nutzer am 2026-09-14 hochgeladen, mit
# aktivem "Gegnerprofil"-Dialog aus v4.64.0). Beide Befunde unten mit
# konkreter Beweisführung aus diesen zwei Runs; siehe Docs/README.md
# v4.65.1 für die volle Herleitung.
# ---------------------------------------------------------------------------

# --- Fix 1: "goldfish" war irreführend, wenn advanced_opponent_model aktiv ist ---
#
# Befund: strategy.opponent_profile bleibt bei aktivem Gegnerprofil-Dialog
# (advanced_opponent_model=True) unverändert auf dem simplen Dropdown-Wert
# stehen (meist "goldfish", da der Dialog diesen bewusst NICHT überschreibt -
# siehe v4.63.0/v4.64.0). simulation_config.json, die GUI-Anzeige "Gewählter
# Modus" und die Overview-Box "Opponent: X" zeigten deshalb "goldfish" -
# obwohl tatsächlich bis zu vier unabhängige, ECHTEN Schaden austeilende
# Sitzplätze (_apply_advanced_multi_opponent_phase) liefen. In den beiden
# hochgeladenen Runs: state.life sank durch "ADVANCED aggro/BW"-,
# "ADVANCED midrange/RU"- usw. Ereignisse (siehe turns.csv "events"), obwohl
# OPPONENT_PROFILES["goldfish"]["damage_scale"] == 0.0 ist - "goldfish"
# selbst kann und darf keinen Schaden austeilen. Das ist keine kosmetische
# Kleinigkeit: es hat die Interpretation beider Runs verfälscht (0%
# Bilbo-Aktivierung, 0% aller 3 Bilbo-Win-Conditions, 12%/29% Loss-Rate -
# alles plausible Folgen von drei echten Gegnern statt eines passiven
# Goldfish-Tests, aber nur nachvollziehbar, wenn man weiß, dass sie liefen).
#
# Fix: additive Felder statt eine bestehende Semantik zu überschreiben -
# strategy.opponent_profile/config["opponent_profile"] bleiben unverändert
# (weiterhin die simple Dropdown-Auswahl, für Abwärtskompatibilität). Neu
# hinzu kommt "advanced_opponent_model"/"advanced_opponent_seat_specs"
# (die konfigurierten, ggf. "?"-haltigen Sitzplätze) sowie
# "advanced_opponent_actual_seat_summary" - eine REIN DETERMINISTISCHE
# Rekonstruktion (kein neuer Simulationslauf, keine neue Zufallsquelle),
# welche Farb-/Strategie-Ausprägung "?"-Marker über den ganzen Batch
# tatsächlich aufgelöst haben, per exakt denselben (seed, run_id)-Regeln wie
# _resolve_advanced_opponent_seats_for_run (v4.64.0) sie zur Laufzeit auch
# verwendet - hier nur im Nachhinein für alle run_id in [1, runs]
# durchgerechnet statt live mitgeschrieben, weil das ohne jede neue
# Zustands-Durchreichung durch die Simulationsschleife auskommt.

def _advanced_opponent_actual_seat_summary(
    seats: Sequence[Dict[str, Any]], seed: int, runs: int,
) -> List[Dict[str, Any]]:
    """Deterministische Rekonstruktion (ruft _resolve_advanced_opponent_seats_
    for_run für jede run_id 1..runs auf - reiner Funktionsaufruf, keine
    Seiteneffekte, exakt dieselbe Formel wie zur Laufzeit) dessen, was ein
    "?"-Marker je Sitzplatz über den ganzen Batch tatsächlich wurde. Leere
    Liste bei keinen konfigurierten Sitzplätzen."""
    if not seats:
        return []
    per_seat_counts: List[Counter] = [Counter() for _ in seats]
    for run_id in range(1, max(1, int(runs)) + 1):
        resolved = _resolve_advanced_opponent_seats_for_run(seats, seed, run_id)
        for i, seat in enumerate(resolved):
            colors = "".join(sorted(seat.get("colors", []))) or "C"
            label = f"{seat.get('strategy', '?')}/{colors}"
            per_seat_counts[i][label] += 1
    return [
        {
            "seat_index": i,
            "configured": dict(seats[i]),
            "actual_counts": dict(counts.most_common()),
        }
        for i, counts in enumerate(per_seat_counts)
    ]


_V4651_summary_old = streaming_summary_v440
def streaming_summary_v440(
    deck: List[Card],
    stats: StreamingStatsV440,
    cfg: SimConfig,
    strategy: ScenarioStrategy,
    impact_rows: List[dict],
    detailed_runs_logged: int,
    log_policy: str,
) -> dict:
    data = _V4651_summary_old(
        deck, stats, cfg, strategy,
        impact_rows, detailed_runs_logged,
        log_policy,
    )
    active = bool(getattr(strategy, "advanced_opponent_model", False))
    data["simulation"]["advanced_opponent_model"] = active
    if active:
        seat_specs = list(getattr(strategy, "advanced_opponent_seats", []) or [])
        actual = _advanced_opponent_actual_seat_summary(seat_specs, cfg.seed, cfg.runs)
        data["simulation"]["advanced_opponent_seat_specs"] = seat_specs
        data["simulation"]["advanced_opponent_actual_seat_summary"] = actual
        data["simulation"]["advanced_opponent_label"] = (
            f"Gegnerprofil aktiv ({len(seat_specs)} Sitzplätze) statt nur "
            f"'{strategy.opponent_profile}'"
        )
    return data


_V4651_build_overview_old = build_analysis_overview
def build_analysis_overview(summary: dict, impact_rows: List[dict]) -> dict:
    overview = _V4651_build_overview_old(summary, impact_rows)
    sim = summary.get("simulation", {})
    active = bool(sim.get("advanced_opponent_model"))
    overview["advanced_opponent_summary"] = {
        "active": active,
        "label": sim.get("advanced_opponent_label", ""),
        "seat_specs": sim.get("advanced_opponent_seat_specs", []),
        "actual_seat_summary": sim.get("advanced_opponent_actual_seat_summary", []),
    }
    if active:
        label = sim.get("advanced_opponent_label", "Gegnerprofil aktiv")
        overview["observations"] = [
            f"{label} - die Ergebnisse dieses Laufs spiegeln NICHT einen "
            f"passiven '{overview.get('opponent', '?')}'-Test wider, siehe "
            "advanced_opponent_summary/'Opponent'-Tab für die tatsächlich "
            "simulierten Sitzplätze.",
            *overview.get("observations", []),
        ]
    return overview


# --- Fix 2: opponent_model_cross_check.json fehlte in JEDEM ausgelieferten ZIP ---
#
# Befund: der v4.44.0-Wrapper von run_pipeline_v440 (weiter oben, direkt vor
# diesem Block) schreibt opponent_model_cross_check.json und haengt einen
# Abschnitt an AI_ANALYSIS_INSTRUCTIONS.md an - NACHDEM der v4.7-Wrapper
# (siehe dessen eigener Kommentar "Base wrapper zipped before these new
# files were created. Rebuild the ZIP...") das ZIP bereits fertig gebaut
# hat. Niemand zippt seither nochmal neu. Konkret nachgewiesen an den zwei
# am 2026-09-14 hochgeladenen echten Runs: AI_ANALYSIS_INSTRUCTIONS.md im
# ausgelieferten ZIP endete nachweislich VOR dem "## v4.44.0 Opponent-Model-
# Cross-Check"-Abschnitt, und opponent_model_cross_check.json fehlte
# komplett im ZIP - obwohl beides nachweislich im echten result_dir auf
# Platte erzeugt wird (derselbe Code schreibt es dorthin). Betrifft jeden
# Lauf seit Einfuehrung dieses Wrappers, nicht erst seit dieser Version.
#
# Fix: exakt dieselbe Strategie wie die beiden fruehreren Praezedenzfaelle
# (v4.6- und v4.7-Wrapper) - am Ende der GESAMTEN Wrapper-Kette einmal
# abschliessend neu zippen, statt den bestehenden v4.44.0-Wrapper selbst zu
# veraendern.

_V4651_pipeline_old = run_pipeline_v440
def run_pipeline_v440(*args, **kwargs):
    result = _V4651_pipeline_old(*args, **kwargs)
    try:
        result_dir = Path(result["result_dir"])
        zip_path = Path(result["zip_path"])
        with _zipfile.ZipFile(zip_path, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
            for f in result_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=f.relative_to(result_dir))
    except Exception:
        # Wie die fruehreren Re-Zip-Stellen: darf die eigentliche
        # Ergebnisauslieferung nie gefaehrden, falls hier doch einmal etwas
        # schiefgeht (z.B. Datei kurzzeitig durch einen Virenscanner
        # gesperrt).
        pass
    return result


# ---------------------------------------------------------------------------
# v4.65.2: Aziza-Match-vs-Sieg-Luecke (Nutzerauftrag, woertlich: "Ja, an die
# Aziza-Siegdefinitionslücke auch ranmachen" - Folgeauftrag zum v4.65.1-
# Kritikbericht). Befund aus dem Aziza-V2-Run: Azizas beide Win-Condition-
# Szenarien (Data/Scenarios/aziza_alpha_strike_v1.json) nutzen
# x_spell_lethal mit target="any" - App/scenario_predicates/handlers.py
# prueft dabei nur, ob EIN Gegner (der mit dem geringsten Leben,
# min(lives)) lethal getroffen werden koennte. check_win() (oben in dieser
# Datei) verlangt dagegen, dass ALLE Eintraege von state.opponents <= 0
# sind, bevor die Partie als gewonnen gilt - der reale Mehrspieler-Sieg
# (alle Gegner eliminiert), nicht "ein Gegner erledigt". Ein Szenario-Match
# von 99% bei 0% tatsaechlichem Sieg ist deshalb KEIN Bug in der
# Engine-Logik, sondern eine reale Luecke zwischen "Combo geht auf" und
# "Partie beendet" - und zwar generisch fuer JEDES Deck, nicht Aziza-
# spezifisch: alle drei target-bewussten Praedikat-Typen
# (opponent_life_at_or_below, x_spell_lethal, commander_damage_lethal)
# defaulten laut scenario_predicates/definitions.json ohnehin auf
# target="any", wenn "target" im Szenario gar nicht gesetzt ist.
#
# Fix (additiv, generisch): fuer jedes Win-Condition-Szenario wird aus
# seinen 'derived'-Praedikaten automatisch der Ziel-Scope abgeleitet
# (_wc_scenario_target_scope) und in scenarios[].target_scope exportiert;
# zusaetzlich wird pro Run erfasst, ob ein WC-Match (irgendein aktiviertes
# WC-Szenario in diesem Run erreicht) mit einem ECHTEN vollstaendigen Sieg
# (rr["win_turn"] gesetzt, d.h. check_win hat ALLE Gegner auf 0 gesehen)
# zusammenfaellt. Neue Kennzahlen: outcomes["win_condition_reach_and_full_
# win_pct"] / ["win_condition_reach_but_no_full_win_pct"] /
# ["win_condition_single_target_names"], plus eine Beobachtung in
# build_analysis_overview, wenn eine konfigurierte WC nur Einzelziel-Scope
# hat. Das alte "win_condition_reach_pct" (Match, egal ob Einzelziel oder
# alle Gegner) bleibt unveraendert bestehen - rueckwaertskompatibel fuer
# evtl. externe Auswertungen.
# ---------------------------------------------------------------------------

_WC_TARGET_AWARE_PREDICATE_TYPES = {
    "opponent_life_at_or_below", "x_spell_lethal", "commander_damage_lethal",
}


def _wc_scenario_target_scope(sc: dict) -> str:
    """Leitet aus den 'derived'-Praedikaten eines Win-Condition-Szenarios ab,
    ob ein Match nur EIN Ziel betrifft oder ALLE Gegner - generisch fuer
    jedes Deck, nicht hartcodiert auf bestimmte Kartennamen/Szenarien.

    "each"  - alle target-bewussten Praedikate im Szenario nutzen
              target="each" (echte Alle-Gegner-Pruefung).
    "any"   - mindestens eines nutzt target="any" oder einen festen Index
              (Einzelziel) und keines "each".
    "mixed" - beides gemischt in einem Szenario.
    "n/a"   - keiner der drei target-bewussten Praedikat-Typen kommt im
              Szenario vor (z.B. reine Leben-/Ressourcen-Schwelle ohne
              Gegnerbezug) - hier ist die Match-vs-Sieg-Frage nicht
              anwendbar.
    """
    targets = []
    for pred in sc.get("derived", []) or []:
        if pred.get("type") in _WC_TARGET_AWARE_PREDICATE_TYPES:
            targets.append(str((pred.get("params") or {}).get("target", "any")))
    if not targets:
        return "n/a"
    if all(t == "each" for t in targets):
        return "each"
    if any(t == "each" for t in targets):
        return "mixed"
    return "any"


_V4652_stats_add_old = StreamingStatsV440.add
def _streaming_stats_add_v4652(self, rr: dict, tr: List[dict], sr: List[dict]):
    _V4652_stats_add_old(self, rr, tr, sr)
    if not hasattr(self, "_wc_reached_and_full_win_count"):
        self._wc_reached_and_full_win_count = 0
    wc_rows = [row for row in sr if row.get("kind") == "Win Condition"]
    reached_turns = [
        row["first_reached_turn"] for row in wc_rows
        if row.get("first_reached_turn") not in (None, "")
    ]
    if reached_turns and bool(str(rr.get("win_turn", "")).strip()):
        self._wc_reached_and_full_win_count += 1

StreamingStatsV440.add = _streaming_stats_add_v4652


_V4652_summary_old = streaming_summary_v440
def streaming_summary_v440(
    deck: List[Card],
    stats: StreamingStatsV440,
    cfg: SimConfig,
    strategy: ScenarioStrategy,
    impact_rows: List[dict],
    detailed_runs_logged: int,
    log_policy: str,
) -> dict:
    data = _V4652_summary_old(
        deck, stats, cfg, strategy,
        impact_rows, detailed_runs_logged,
        log_policy,
    )
    n = max(1, stats.run_count)
    wc_configured = bool(data["outcomes"].get("win_condition_configured"))
    reached_and_won = getattr(stats, "_wc_reached_and_full_win_count", 0)
    reached_count = getattr(stats, "_wc_reached_count", 0)
    data["outcomes"]["win_condition_reach_and_full_win_pct"] = (
        100.0 * reached_and_won / n if wc_configured else 0.0
    )
    data["outcomes"]["win_condition_reach_but_no_full_win_pct"] = (
        100.0 * max(0, reached_count - reached_and_won) / n if wc_configured else 0.0
    )

    wc_scenarios = _wc_kind_scenarios(strategy.scenarios)
    scope_by_name = {sc["name"]: _wc_scenario_target_scope(sc) for sc in wc_scenarios}
    data["outcomes"]["win_condition_single_target_names"] = [
        name for name, scope in scope_by_name.items() if scope in ("any", "mixed")
    ]
    for row in data.get("scenarios", []):
        if row.get("kind") == "Win Condition":
            row["target_scope"] = scope_by_name.get(row.get("name"), "n/a")
    return data


_V4652_build_overview_old = build_analysis_overview
def build_analysis_overview(summary: dict, impact_rows: List[dict]) -> dict:
    overview = _V4652_build_overview_old(summary, impact_rows)
    outcomes = overview.get("outcomes", {})
    obs = list(overview.get("observations", []))

    single_target_names = outcomes.get("win_condition_single_target_names") or []
    reach_pct = float(outcomes.get("win_condition_reach_pct", 0) or 0)
    if outcomes.get("win_condition_configured") and single_target_names and reach_pct > 0:
        full_win_pct = float(outcomes.get("win_condition_reach_and_full_win_pct", 0) or 0)
        obs.append(
            f"Ziel-Scope-Hinweis: {', '.join(single_target_names)} prüft laut "
            "Konfiguration nur EIN Ziel (target=any oder ein fester Index), "
            "nicht alle Gegner - check_win() verlangt aber ALLE Gegner auf 0 "
            "Leben für einen vollständigen Sieg. Ein Match bedeutet daher "
            "'die Combo geht gegen (mindestens) einen Gegner auf', nicht "
            f"automatisch 'die Partie ist gewonnen'. Match: {reach_pct:.2f}% "
            f"· davon mit tatsächlichem Sieg (alle Gegner eliminiert): "
            f"{full_win_pct:.2f}%."
        )
    overview["observations"] = obs
    return overview


# ---------------------------------------------------------------------------
# v4.65.3: Bilbo-Drain-Payoff-Coverage (Nutzerauftrag, woertlich: "Ja, an die
# Bilbo-Drain-Payoff-Coverage auch ranmachen" - Folgeauftrag zum in v4.65.1
# offengelegten, zunaechst nicht angefassten Kontextpunkt "Bilbos Drain-
# Payoff-Karten sind nur 'generic'-abgedeckt").
#
# Befund nach genauer Pruefung von card_model_coverage.csv UND der
# tatsaechlichen Engine-Logik (App/engine.py:gain_life, Abschnitt "High-
# impact Bilbo card fixes"): die fruehere Einschaetzung war zu pessimistisch.
# "generic" bedeutet in diesem Tool NICHT "unsimuliert" - es heisst nur
# "kein KNOWN_COVERAGE_NOTES-Eintrag, nutzt den generischen Parser". Konkret:
#   - Corpse Knight, Marauding Blight-Priest, Dinas Kern-Trigger: bereits
#     korrekt als "1/1"/"1/2 exact" ausgewiesen - real vollstaendig simuliert,
#     keine Luecke.
#   - Sanguine Bond UND Vitos Drain-Zeile ("target opponent loses that much
#     life"): WERDEN in gain_life() bereits real und exakt ausgefuehrt
#     (lose_target_opponent mit dem tatsaechlich gewonnenen Betrag,
#     inklusive Lifelink-Lebensgewinn, da Kampf-Lifelink ebenfalls ueber
#     gain_life() laeuft) - der COVERAGE-SELBSTBERICHT zeigte hier aber
#     faelschlich 0/1 bzw. 1/2 "executable", weil die generische
#     "opponent loses N life"-Regex (_parse_semantic_actions) nur feste
#     Zahlen/Zahlwoerter erkennt, nicht die dynamische Formulierung "loses
#     THAT MUCH life" (Betrag = gerade gewonnenes Leben). Das ist ein
#     Selbstbericht-Genauigkeitsfehler ("syntax-korrekt, aber inhaltlich
#     falsch" im Sinne des urspruenglichen Nutzerauftrags), keine fehlende
#     Spielmechanik.
#   - Dinas zweite Faehigkeit ({1}, Opfere eine weitere Kreatur: +X/+0) ist
#     die einzige ECHTE, verbleibende Luecke - eine bedingte Kampftrick-
#     Opfer-Entscheidung ausserhalb des Drain-Payoff-Kerns dieser Karte.
#
# Fix (additiv, zweigleisig):
#   1) _parse_semantic_actions erkennt jetzt zusaetzlich "each opponent
#      loses that much life"/"target opponent loses that much life" als
#      exakte opponent_life_loss-Aktion (amount=0.0 als bewusst inerter
#      Platzhalter fuer "dynamisch, keine feste Zahl") - macht den
#      Coverage-Selbstbericht fuer JEDE Karte mit dieser generischen,
#      haeufigen Formulierung korrekt, nicht nur fuer die beiden hier
#      untersuchten. amount=0.0 ist sicher: die einzige Stelle, die
#      opponent_life_loss-Aktionen numerisch aufsummiert
#      (_loyalty_ability_value, NUR fuer Planeswalker-Loyalitaetsfaehig-
#      keiten) ueberspringt bereits explizit falsy/0-Betraege
#      ("if not metric or not action.amount: continue") - keine verzerrte
#      Bewertung moeglich. Nichts in dieser Engine fuehrt generisch eine
#      GETRIGGERTE Faehigkeit aus dieser Aktionsliste aus
#      (try_generic_semantic_activations behandelt ausschliesslich
#      "activated"-Faehigkeiten) - die tatsaechliche Ausfuehrung bleibt
#      unveraendert exakt so, wie sie schon vorher in gain_life() lief;
#      diese Ergaenzung macht nur den Selbstbericht ehrlich.
#   2) KNOWN_COVERAGE_NOTES-Eintraege fuer alle fuenf Karten (oben, direkt
#      im bestehenden Dict ergaenzt - Praezedenzfall: die config={...}-
#      Dict-Bearbeitung in run_pipeline_v440, v4.64.0) korrigieren die
#      Coverage-Stufe/Notiz von "generic" auf "strong" (Sanguine Bond, Vito,
#      Corpse Knight, Marauding Blight-Priest) bzw. "partial+" (Dina, mit
#      der echten Sac-Pump-Luecke weiterhin ehrlich benannt).
# ---------------------------------------------------------------------------

_V4653_parse_semantic_actions_old = _parse_semantic_actions
def _parse_semantic_actions(effect: str) -> List[SemanticAction]:
    actions = _V4653_parse_semantic_actions_old(effect)
    low = strip_reminder_text(effect).lower()

    if not any(a.kind == "opponent_life_loss" for a in actions):
        m = re.search(r"\b(each opponent|target opponent) loses that much life", low)
        if m:
            actions.append(SemanticAction(
                kind="opponent_life_loss",
                amount=0.0,
                target=m.group(1),
                raw=effect,
            ))

    return actions


def main_v470():
    ap = argparse.ArgumentParser(
        description="Commander Goldfish Simulator v4.7.0"
    )
    ap.add_argument(
        "deck_file", nargs="?", type=Path
    )
    ap.add_argument(
        "--commander", action="append", default=[]
    )
    ap.add_argument(
        "--runs", type=int, default=5000
    )
    ap.add_argument(
        "--turns", type=int, default=10
    )
    ap.add_argument(
        "--seed", type=int, default=1
    )
    ap.add_argument(
        "--cache", type=Path, default=None
    )
    ap.add_argument(
        "--offline", action="store_true"
    )
    ap.add_argument(
        "--metadata-csv", type=Path, default=None
    )
    ap.add_argument(
        "--strategy", type=Path, default=None
    )
    ap.add_argument("--tags", default="")
    ap.add_argument(
        "--opponent",
        choices=sorted(OPPONENT_PROFILES),
        default="goldfish",
    )
    ap.add_argument(
        "--value-model", type=Path, default=None
    )
    ap.add_argument(
        "--scenarios", type=Path, default=None
    )
    ap.add_argument(
        "--output-root", type=Path, default=None
    )
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    if args.gui or args.deck_file is None:
        try:
            from App.gui import launch_gui
        except ImportError:
            from gui import launch_gui  # engine.py run standalone, gui.py alongside it
        launch_gui()
        return

    ensure_runtime_dependencies(
        include_images=False,
        status_callback=print,
    )
    commander_names = (
        list(args.commander)
        or detect_commander_hints(args.deck_file)
    )
    if not commander_names:
        raise SystemExit(
            "No commander detected. "
            "Use --commander or the GUI."
        )

    tags = {
        x.strip().lower()
        for x in args.tags.split(",")
        if x.strip()
    }
    result = run_pipeline_v440(
        args.deck_file,
        commander_names,
        runs=args.runs,
        turns=args.turns,
        seed=args.seed,
        strategy_file=args.strategy,
        strategy_tags=tags or None,
        opponent_profile=args.opponent,
        value_model_file=args.value_model,
        scenarios_file=args.scenarios,
        cache_path=args.cache,
        offline=args.offline,
        metadata_csv=args.metadata_csv,
        output_root=args.output_root,
    )
    print("\nGoldfish v4.7.0 complete")
    print("Result folder:", result["result_dir"])
    print("Upload ZIP:   ", result["zip_path"])


if __name__ == "__main__":
    main_v470()
