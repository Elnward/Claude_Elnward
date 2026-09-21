"""
Handler implementations for the keyword registry.

Each handler has the signature:
    handler(ops, state, strategy, source, action, target) -> bool

`ops` exposes the engine's state-mutating primitives (gain_life, draw_cards, scry, ...).
Logic here is a straight extraction of what used to live inline in
engine.execute_semantic_action's if/elif chain - behavior is unchanged, only the
dispatch mechanism is new.

Adding a new mechanic that behaves like an existing one (e.g. a new set's keyword with
connive-like rules) needs NO new function here - just point a new `definitions.json`
entry's "handler" field at the existing handler name.
"""
from __future__ import annotations

import re

from .registry import register_handler


def _source_name(source) -> str:
    return source.card.name if source else "Semantic ability"


@register_handler("gain_life")
def _h_gain_life(ops, state, strategy, source, action, target) -> bool:
    ops.gain_life(state, action.amount, _source_name(source))
    return True


@register_handler("draw")
def _h_draw(ops, state, strategy, source, action, target) -> bool:
    ops.draw_cards(state, int(action.amount), reason=_source_name(source))
    return True


@register_handler("scry")
def _h_scry(ops, state, strategy, source, action, target) -> bool:
    ops.scry(state, int(action.amount), strategy)
    ops.record_impact(state, _source_name(source), "scry", action.amount)
    return True


@register_handler("surveil")
def _h_surveil(ops, state, strategy, source, action, target) -> bool:
    ops.surveil(state, int(action.amount), strategy)
    ops.record_impact(state, _source_name(source), "surveil", action.amount)
    return True


@register_handler("connive")
def _h_connive(ops, state, strategy, source, action, target) -> bool:
    ops.connive(state, int(action.amount), strategy, source=source)
    ops.record_impact(state, _source_name(source), "connive", action.amount)
    return True


@register_handler("opponent_life_loss")
def _h_opponent_life_loss(ops, state, strategy, source, action, target) -> bool:
    if action.target == "each opponent":
        ops.lose_each_opponent(state, action.amount, _source_name(source))
    else:
        ops.lose_target_opponent(state, action.amount, _source_name(source))
    return True


@register_handler("create_token")
def _h_create_token(ops, state, strategy, source, action, target) -> bool:
    # v4.20.0 fix: ops.create_tokens only actually mutates state for
    # kind in {"food", "treasure", "clue"} OR when called with creature=True
    # - found while testing a Battle's back-face reward ("Create a 3/3 green
    # Bear creature token."), which parses fine (SemanticAction(kind=
    # "create_token", token="3/3 Green Bear Creature")) but was a complete,
    # silent no-op here: this handler never passed creature=True, so a
    # descriptive creature-token string matched none of create_tokens'
    # branches. This affects every card whose generic "create_token" action
    # names a creature token, not just Battles - a pre-existing gap this
    # session's own testing surfaced. Food/Treasure/Clue keep their exact
    # prior behavior unchanged.
    token_desc = (action.token or "Token").strip()
    n = max(1, int(action.amount or 1))
    if token_desc.lower() in ("food", "treasure", "clue"):
        ops.create_tokens(state, strategy, token_desc, n, source=_source_name(source))
        return True

    m = re.match(r"^(\d+)\s*/\s*(\d+)\s+(.*)$", token_desc)
    power, toughness, rest = (float(m.group(1)), float(m.group(2)), m.group(3)) if m else (1.0, 1.0, token_desc)
    if "creature" in token_desc.lower():
        name = re.sub(r"\bcreature\b", "", rest, flags=re.IGNORECASE).strip()
        name = re.sub(r"\s{2,}", " ", name) or "Token"
        ops.create_tokens(
            state, strategy, name, n,
            creature=True, power=power, toughness=toughness,
            source=_source_name(source),
        )
    else:
        # Not a recognized resource token and not described as a creature -
        # e.g. a Clue/Blood/Map-shaped artifact token this parser doesn't
        # special-case. Falls through to create_tokens' own unhandled-kind
        # branch (still a no-op there), same as before this fix - honest
        # rather than guessing at unknown token shapes.
        ops.create_tokens(state, strategy, token_desc, n, source=_source_name(source))
    return True


@register_handler("plus1_counter")
def _h_plus1_counter(ops, state, strategy, source, action, target) -> bool:
    if target is None:
        return False
    n = max(1, int(action.amount or 1))
    # v4.23.0: Doubling Season ("If an effect would put one or more
    # counters on a permanent you control, it puts twice that many of
    # those counters on that permanent instead.") - this is the generic,
    # broadly-reused +1/+1-counter action handler every card's parsed
    # oracle text funnels through, so it's the one root-cause place for
    # the generic case. Other +1/+1-counter call sites (Devour, Persist/
    # Undying's own return-with-a-counter, and the many exact-name
    # dedicated resolvers elsewhere in engine.py) are handled at their own
    # sites, or - for the long tail of exact-name resolvers - deliberately
    # left out of this pass; see engine.py's KNOWN_KEYWORDS "v4.21.0"/
    # "v4.22.0" scope-note comments for the same documented-gap convention.
    if state.has("Doubling Season"):
        n *= 2
    target.counters += n
    ops.record_impact(state, _source_name(source), "counters", n)
    return True


@register_handler("keyword_counter")
def _h_keyword_counter(ops, state, strategy, source, action, target) -> bool:
    if target is None or not action.keyword:
        return False
    target.named_counters[action.keyword] += 1
    return True


@register_handler("grant_keyword_until_eot")
def _h_grant_keyword_until_eot(ops, state, strategy, source, action, target) -> bool:
    if target is None or not action.keyword:
        return False
    target.temporary_keywords.add(action.keyword)
    return True


@register_handler("tap_target")
def _h_tap_target(ops, state, strategy, source, action, target) -> bool:
    if target is None:
        return False
    target.tapped = True
    return True


@register_handler("team_pt_bonus")
def _h_team_pt_bonus(ops, state, strategy, source, action, target) -> bool:
    ops.board_modifiers(state).append(ops.BoardModifier(
        source=_source_name(source),
        expires_turn=state.turn,
        kind="team_pt_bonus",
        amount=float(action.amount or 0),
    ))
    return True


@register_handler("grant_team_keyword")
def _h_grant_team_keyword(ops, state, strategy, source, action, target) -> bool:
    if not action.keyword:
        return False
    ops.board_modifiers(state).append(ops.BoardModifier(
        source=_source_name(source),
        expires_turn=state.turn,
        kind="grant_keyword",
        keyword=action.keyword,
    ))
    return True


@register_handler("set_base_pt")
def _h_set_base_pt(ops, state, strategy, source, action, target) -> bool:
    if target is None:
        return False
    m = ops.re.search(
        r"base power and toughness (?:becomes?|are|is) (\d+)\s*/\s*(\d+)",
        action.raw.lower(),
    )
    if not m:
        return False
    ops.board_modifiers(state).append(ops.BoardModifier(
        source=_source_name(source),
        expires_turn=state.turn,
        kind="set_base_pt",
        target_id=id(target),
        power=float(m.group(1)),
        toughness=float(m.group(2)),
    ))
    return True
