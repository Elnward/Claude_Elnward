"""
Hand-Qualitaets-Score (v4.81.0 "Runde 3" WP-B): reusable heuristic for
deciding WHICH card(s) in a player's hand are the best candidates to give
up when an effect asks for a hand-based choice (a generic "discard a
card"/"discard N cards" EFFECT is the first consumer - see engine.py's
"discard_hand" keyword action - future consumers such as a generic
Cycling-choice-among-many or a Learn-style "discard to draw" effect can
reuse this module without re-deriving the same heuristic).

Design (per user request, Docs/README.md v4.81.0 entry): analogous to the
existing mulligan-quality check (engine.hand_quality / engine.keep_hand),
but evaluated mid-game against the CURRENT board state rather than only the
opening hand, and per-card rather than only whole-hand. Builds directly on
engine.discard_score's existing, already-shipped philosophy (protect lands
while land-light, protect tutors/draw-engines/finishers, treat well-over-
curve cards as increasingly disposable) and adds two pieces of board-state
context discard_score does not have:
  * whether the player has probably already missed/skipped recent land
    drops (lands in play compared to turns played is the only proxy
    available here - this engine does not track a per-turn "land already
    played this turn" flag anywhere), and
  * whether a nonland card is realistically castable soon (its mana cost
    against the player's CURRENT land count) - a card well above the
    current mana base is safer to give up than one about to come online.

A fully probabilistic ("gewichtete Zufallsauswahl") selection was
considered - it was the user's own suggestion - but deliberately NOT
implemented: this project's existing precedent for the identical problem
(discard_score + strict min(), used by connive() and the generic
Discard-N-as-activation-cost path) is already deterministic, and a random
pick would make every test built on top of this module non-reproducible
without seeding through several unrelated call sites. The deterministic
worst-first ranking below reaches the same practical goal - low-value
cards are preferred first - while staying fully testable; this is a
disclosed, considered simplification, not a silent gap.
"""
from __future__ import annotations

from typing import Iterable, List, Optional


def hand_card_score(card, state) -> float:
    """Lower = more disposable. Same shape/scale as engine.discard_score
    (a card scored identically by both stays identically ranked), plus the
    board-state add-ons described in the module docstring."""
    score = 0.0
    lands_in_play = len(state.lands())
    if card.is_land:
        if lands_in_play < 5:
            score += 3.0
            # Once the player already has at least as many lands in play
            # as turns taken, a spare land in hand is progressively less
            # useful to keep holding onto - land drops taken roughly on
            # curve mean the NEXT land is what actually matters, not a
            # second one sitting in hand.
            if lands_in_play >= max(1, int(getattr(state, "turn", 0)) - 1):
                score -= 1.0
        else:
            score -= 1.0
    else:
        if card.roles & {"tutor", "draw", "draw_engine", "engine", "finisher"}:
            score += 3.0
        if card.roles & {"interaction", "protection", "boardwipe", "counterspell"}:
            score += 0.5
        score -= max(0, card.min_cost - 5) * 0.4
        if lands_in_play and card.min_cost > lands_in_play + 2:
            score -= 0.75
    return score


def choose_worst_hand_cards(state, count: int, *, exclude: Optional[Iterable] = None) -> List:
    """Deterministic worst-first pick of up to `count` distinct cards from
    state.hand (lowest hand_card_score first), skipping anything present in
    `exclude`. Returns a (possibly shorter, if the eligible hand has fewer
    cards) list of the actual Card objects from state.hand - callers remove
    them from state.hand themselves (mirrors connive()'s own convention)."""
    if count <= 0:
        return []
    exclude = list(exclude) if exclude else []
    pool = [c for c in state.hand if c not in exclude]
    pool.sort(key=lambda c: hand_card_score(c, state))
    return pool[:int(count)]
