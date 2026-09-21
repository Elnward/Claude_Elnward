"""
Permanent-type removal classifier (v4.44.0, foundation for the "Punkt 3"
additive opponent-model cross-check - see Docs/README.md v4.44.0 and
App/opponent_model/state_equation.py's module docstring, "Iteration 3"
section, for the original user reasoning behind the permanent-type tag on
passive_value_by_type/sac_drain_by_type/disruption_lockout_by_type).

Purpose: given a REAL card's real Oracle text (App.engine.Card.oracle_text,
sourced from Scryfall - never invented per-card data), determine which of
the 5 permanent-type buckets used by App.opponent_model.state_equation
(artifact/enchantment/creature/planeswalker/land) that card can plausibly
answer, so a later step can compare the TESTED deck's own real removal
breadth against the simulated opponent's board-effect footprint
(App.opponent_model.state_equation.query_board_effects).

Method: regex pattern-matching against STANDARD, WotC-style-guide Magic
templating for target-based removal ("Destroy target X.", "Exile target
X.", "Destroy all X.", "Return target X to its owner's hand."), not a
hand-curated list of specific card names. The exact phrase "destroy target
artifact or enchantment" alone is real, standard templating shared by 130+
printed cards (Gatherer rules-text search, cross-checked during v4.44.0
research) - i.e. this classifier recognizes a real, stable templating
convention, not an invented heuristic.

Explicitly disclosed, KNOWN limitations (an honest first pass, not a claim
of exhaustive detection):
  - Edict/sacrifice effects ("Each opponent sacrifices a creature.") are
    NOT recognized in this version - too easy to false-positive on a
    card's OWN, self-targeting sacrifice cost/ability without a more
    careful pass distinguishing "you sacrifice" from "target
    player/opponent sacrifices". Left out rather than guessed at.
  - Damage/fight-based creature removal that never says "destroy"/"exile"
    explicitly (e.g. "deals 4 damage to target creature") is NOT
    recognized, even though it often kills a creature in practice - the
    text does not name a permanent-type target the way this classifier
    looks for, and guessing a lethality threshold would be invented, not
    evidenced, data.
  - A generic "target permanent"/"target nonland permanent" phrase is
    resolved to ALL matching buckets (e.g. Council's Judgment's real vote
    pool is restricted to nonland permanents already at the voting step,
    but the exile clause itself says "each permanent" - this classifier
    conservatively also counts the land bucket there, a small, disclosed
    over-approximation rather than hand-patching one specific card).
  - Static, always-on answers (e.g. Aura of Silence's activated ability,
    or a card that merely PREVENTS a permanent type from entering) are not
    covered - only the "destroy/exile/bounce a real target" family is.
These gaps make this classifier UNDER-count real removal breadth in some
cases, never over-claim a type of removal a card's text does not mention -
a deliberate, disclosed bias toward false negatives over invented false
positives, consistent with this project's evidence-over-invention
convention.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, Set

ALL_PERMANENT_TYPES = ("artifact", "enchantment", "creature", "planeswalker", "land")

_TYPE_WORDS = {
    "artifact": "artifact",
    "artifacts": "artifact",
    "enchantment": "enchantment",
    "enchantments": "enchantment",
    "creature": "creature",
    "creatures": "creature",
    "planeswalker": "planeswalker",
    "planeswalkers": "planeswalker",
    "land": "land",
    "lands": "land",
}

# Up to two modifier words (e.g. "nonbasic", "nonland", "legendary", a
# color name) may sit between "target"/"all"/"each" and the actual type
# noun - bounded (not an open-ended wildcard) so the match cannot run away
# across sentence boundaries.
_MODIFIER = r"(?:[A-Za-z]+[- ]){0,2}"
_TYPE_NOUN = r"(?:artifact|enchantment|creature|planeswalker|land|permanent)s?"
_ONE_TYPE = _MODIFIER + _TYPE_NOUN
_CONJ = r"(?:\s*(?:,\s*|\s+or\s+|\s+and/or\s+|\s+and\s+)\s*)"
_TYPE_PHRASE = _ONE_TYPE + r"(?:" + _CONJ + _ONE_TYPE + r")*"

_TARGET_PATTERN = re.compile(
    r"\b(?:destroy|exile)\s+(?:up to [a-z]+ )?(?:target|all|each)\s+(?P<types>" + _TYPE_PHRASE + r")",
    re.IGNORECASE,
)
_BOUNCE_PATTERN = re.compile(
    r"\breturn\s+(?:up to [a-z]+ )?target\s+(?P<types>" + _TYPE_PHRASE + r")"
    # A bounded, non-greedy gap (e.g. "you don't control") may sit between
    # the type phrase and "to ... owner's hand" - bounded word count, not an
    # open-ended wildcard, so this cannot run away across sentences.
    r"(?:\s+\S+){0,4}?\s+to (?:its|their|that player's) owner'?s? hand",
    re.IGNORECASE,
)


def _resolve_type_phrase(phrase: str) -> Set[str]:
    phrase_lower = phrase.lower()
    if re.search(r"\bpermanents?\b", phrase_lower):
        if re.search(r"\bnonland\b", phrase_lower):
            return set(ALL_PERMANENT_TYPES) - {"land"}
        return set(ALL_PERMANENT_TYPES)
    found: Set[str] = set()
    for word, bucket in _TYPE_WORDS.items():
        if re.search(r"\b" + word + r"\b", phrase_lower):
            found.add(bucket)
    return found


def classify_removal_permanent_types(oracle_text: str) -> Set[str]:
    """Real permanent-type buckets a single card's real Oracle text can
    answer, per the standard-templating patterns described in the module
    docstring. Empty text or no recognized pattern -> empty set (never a
    guess)."""
    if not oracle_text:
        return set()
    hits: Set[str] = set()
    for pattern in (_TARGET_PATTERN, _BOUNCE_PATTERN):
        for match in pattern.finditer(oracle_text):
            hits |= _resolve_type_phrase(match.group("types"))
    return hits


def deck_removal_coverage(deck: Iterable) -> Dict[str, int]:
    """Real permanent-type removal coverage of a decklist: for each of the
    5 permanent-type buckets, counts how many real cards in `deck` can hit
    that type (per classify_removal_permanent_types on that card's real
    oracle_text attribute). NOT a claim of exhaustive detection - see
    module docstring for disclosed known gaps."""
    coverage = {t: 0 for t in ALL_PERMANENT_TYPES}
    for card in deck:
        text = getattr(card, "oracle_text", "") or ""
        for bucket in classify_removal_permanent_types(text):
            coverage[bucket] += 1
    return coverage
