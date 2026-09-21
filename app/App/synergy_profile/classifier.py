"""
Lifegain-payoff cross-color synergy classifier (v4.46.0).

Background (see Docs/opponent_model_orzhov_deep_dive_v4_45_0.md and
Docs/opponent_model_moxfield_methodology_v4_46_0.md for the full research
trail): the v4.41.0 hypothesis was that Orzhov (WB) has a guild-wide
cross-color synergy gap - White "feeds" token/lifegain triggers that Black
"converts" into drain/damage. A 5-deck pilot (v4.45.0) found this too
coarse: whether a REAL deck shows a clean, unidirectional White-source ->
Black-payoff dependency, or is instead self-sufficient in a single color,
depends on the SPECIFIC commander/build, not on the guild as a whole. A
follow-up round (v4.46.0, Moxfield + EDHREC evidence, see the methodology
doc) deepened this: 5/5 independently-sourced real Aristokraten decks
(Teysa Karlov) showed Black already self-sufficient (its own sac outlets
AND its own drain payoffs), while of 3 independent real "lifegain-drain"
commanders, 2/3 (Karlov of the Ghost Council, Kambal Consul of Allocation)
showed a genuine White-source/Black-payoff split, but the 3rd (Vito, Thorn
of the Dusk Rose) achieved the identical Sanguine-Bond/Exquisite-Blood
payoff shell using ONLY mono-Black lifelink-vampire sources - no White
contribution at all.

Conclusion drawn from this: a single static per-guild (or even
per-sub-strategy) cross-color weight would misrepresent roughly as many
real decks as it would correctly describe. What IS reliably real and
detectable is the PATTERN ITSELF, per deck: does this specific decklist's
"whenever you gain life" payoff shell depend on a different color than its
own lifegain sources, or is it self-sufficient? This module answers that
question from a deck's real card data (App.engine.Card.oracle_text /
color_identity - never invented per-card data), the same
evidence-from-real-oracle-text approach already used by
App.removal_profile.classifier (v4.44.0).

Method:
  - "payoff" cards: real, stable Magic templating "Whenever you gain
    life,"/"Whenever a player gains life," (Sanguine Bond, Vito Thorn of
    the Dusk Rose, Cliffhaven Vampire, Bloodchief Ascension - all
    verified via WebSearch/WebFetch during v4.46.0 research) - these
    CONVERT a life-gain event into something else (damage, counters,
    life loss for an opponent).
  - "source" cards: real templating "whenever <other event>, you gain N
    life" (Soul Warden - "Whenever another creature enters the
    battlefield under your control, you gain 1 life.", and the same
    family of card) - these PRODUCE life gain as a side effect of some
    other trigger, WITHOUT themselves being a payoff.
  - A card matching the payoff pattern is never also counted as a source,
    even if it incidentally contains "you gain ... life" wording, to avoid
    double-counting a single payoff card as its own source.

Explicitly disclosed, KNOWN limitations (an honest first pass, consistent
with App.removal_profile.classifier's own disclosed-gaps convention):
  - Life gain that is not phrased as a "whenever" triggered ability (e.g.
    a one-shot spell like "You gain 4 life", or devotion-scaling effects
    like Gray Merchant of Asphodel's "you lose life equal to...you gain
    life equal to the damage dealt") is NOT recognized as a "source" -
    these are real lifegain but not a repeatable trigger the way Soul
    Warden or a payoff engine expects to chain off of.
  - Lifelink (a keyword, not oracle-text prose) is NOT recognized as a
    "source" either, even though it reliably produces repeated life gain
    in practice (this is exactly how Vito's real average deck achieves
    self-sufficiency - see the module docstring above) - detecting it
    would require creature/combat-damage simulation this classifier does
    not have access to, so it is left as a disclosed gap rather than
    guessed at.
  - Only `color_identity` (the printed color identity, not mana cost) is
    used to attribute a card to a color; colorless payoff/source cards
    (there are none known among the real cards checked so far) would be
    classified as their own "colorless" bucket rather than silently
    dropped.
These gaps mean this classifier can UNDER-count real self-sufficiency
(e.g. it would flag a lifelink-only deck like Vito's real average build as
"no source found" rather than correctly detecting the lifelink route) -
again a deliberate, disclosed bias toward false negatives (missing a
self-sufficient path) over invented false positives (claiming a
cross-color dependency exists where the real deck avoids it), matching
this project's evidence-over-invention convention.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set

_PAYOFF_PATTERN = re.compile(
    r"whenever (?:you|a player) gains? life",
    re.IGNORECASE,
)
_SOURCE_PATTERN = re.compile(
    r"whenever [^.]*,\s*you gain \d+ life",
    re.IGNORECASE,
)


def classify_lifegain_role(oracle_text: str) -> str:
    """Real lifegain role of a single card's real Oracle text: "payoff"
    (converts a life-gain event into something else), "source" (produces
    life gain as a side effect of some other trigger), or "" (neither, per
    the disclosed known limitations in the module docstring - never a
    guess)."""
    if not oracle_text:
        return ""
    if _PAYOFF_PATTERN.search(oracle_text):
        return "payoff"
    if _SOURCE_PATTERN.search(oracle_text):
        return "source"
    return ""


def _card_colors(card) -> Set[str]:
    colors = getattr(card, "color_identity", None) or set()
    return set(colors) if colors else {"colorless"}


def deck_lifegain_synergy_profile(deck: Iterable) -> Dict[str, object]:
    """Real per-deck lifegain-payoff synergy profile: which real cards are
    "source"/"payoff" (see classify_lifegain_role), which colors those
    cards belong to, and whether the payoff side's colors overlap with the
    source side's colors (self-sufficient) or not (cross-color
    dependency) - see module docstring for the v4.45.0/v4.46.0 research
    that motivated a PER-DECK check instead of a static per-guild weight.

    Returns a dict with:
      source_cards / payoff_cards: real card names found (never invented).
      source_colors / payoff_colors: color_identity union of each side.
      cross_color_dependency: True only if BOTH sides are non-empty AND
        share no color (self-sufficient overlap, including a shared
        "colorless" card on both sides, counts as NOT a dependency).
    """
    source_cards: List[str] = []
    payoff_cards: List[str] = []
    source_colors: Set[str] = set()
    payoff_colors: Set[str] = set()

    for card in deck:
        text = getattr(card, "oracle_text", "") or ""
        role = classify_lifegain_role(text)
        if role == "payoff":
            payoff_cards.append(getattr(card, "name", ""))
            payoff_colors |= _card_colors(card)
        elif role == "source":
            source_cards.append(getattr(card, "name", ""))
            source_colors |= _card_colors(card)

    cross_color_dependency = bool(
        source_cards and payoff_cards and not (source_colors & payoff_colors)
    )

    return {
        "source_cards": source_cards,
        "payoff_cards": payoff_cards,
        "source_colors": sorted(source_colors),
        "payoff_colors": sorted(payoff_colors),
        "cross_color_dependency": cross_color_dependency,
    }
