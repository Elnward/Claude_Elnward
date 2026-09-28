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


@register_handler("named_tutor_to_hand")
def _h_named_tutor_to_hand(ops, state, strategy, source, action, target) -> bool:
    # v4.87.3: "Search your library for a card named <X>, put it into your
    # hand[, then shuffle]." action.token carries the exact captured name
    # (any card, not just the source's own - see the action's own parse-site
    # comment in engine.py for the real card, Shadowborn Apostle, that
    # surfaced this gap). tutor_to_hand already no-ops cleanly (records
    # nothing, moves nothing) when no library card matches - same as any
    # other tutor whose target has run out - so this always returns True
    # (the ability itself was recognized and attempted) regardless of
    # whether a copy was actually found.
    name = (action.token or "").strip()
    if not name:
        return False
    ops.tutor_to_hand(state, lambda c: c.name == name, [], _source_name(source))
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


@register_handler("proliferate")
def _h_proliferate(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.proliferate(state, strategy, source=_source_name(source)))


@register_handler("discard_hand")
def _h_discard_hand(ops, state, strategy, source, action, target) -> bool:
    """v4.81.0 "Runde 3": generic bare "discard a card"/"discard N cards"
    EFFECT (never a cost - see App/hand_evaluation and the engine.py
    _parse_semantic_actions wrapper for the self-only scoping)."""
    n = max(1, int(action.amount or 1))
    chosen = ops.choose_worst_hand_cards(state, n)
    for card in chosen:
        state.hand.remove(card)
        state.graveyard.append(card)
    if chosen:
        ops.record_impact(state, _source_name(source), "discard_hand", len(chosen))
        state.log(f"DISCARD ({_source_name(source)}): {', '.join(c.name for c in chosen)}")
    return bool(chosen)


@register_handler("mill")
def _h_mill(ops, state, strategy, source, action, target) -> bool:
    n = ops.mill_library(state, strategy, int(action.amount or 1),
                          target=(action.target or "self"), source=_source_name(source))
    return bool(n)


@register_handler("amass")
def _h_amass(ops, state, strategy, source, action, target) -> bool:
    subtype = (action.token or "Zombie").rstrip("s") or "Zombie"
    return bool(ops.amass(state, strategy, subtype=subtype, n=int(action.amount or 1),
                          source=_source_name(source)))


@register_handler("explore")
def _h_explore(ops, state, strategy, source, action, target) -> bool:
    # Explore always affects the exploring creature itself - use `source`
    # directly rather than the auto-resolved `target` (Explore's own raw
    # text, e.g. bare "Explore.", carries no "this creature" phrasing for
    # _semantic_target_creature's self-check to latch onto).
    return bool(ops.explore(state, strategy, source, source=_source_name(source)))


@register_handler("bolster")
def _h_bolster(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.bolster(state, strategy, int(action.amount or 1), source=_source_name(source)))


@register_handler("fabricate")
def _h_fabricate(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.fabricate(state, strategy, int(action.amount or 1), source, source=_source_name(source)))


@register_handler("monstrosity")
def _h_monstrosity(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.monstrosity(state, strategy, int(action.amount or 1), source, source=_source_name(source)))


@register_handler("populate")
def _h_populate(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.populate(state, strategy, source=_source_name(source)))


@register_handler("support")
def _h_support(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.support(state, strategy, int(action.amount or 1), source=_source_name(source)))


@register_handler("discover")
def _h_discover(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.discover(state, strategy, int(action.amount or 1), source=_source_name(source)))


@register_handler("monarch")
def _h_monarch(ops, state, strategy, source, action, target) -> bool:
    return bool(ops.become_monarch(state, strategy, source=_source_name(source)))


@register_handler("goad")
def _h_goad(ops, state, strategy, source, action, target) -> bool:
    """v4.82.0 "Runde 4": Goad als temporaere Druck-Unterdrueckung fuer genau
    die naechste Gegnerrunde (gegoadete Kreaturen muessen einen ANDEREN
    Spieler angreifen) - siehe engine.suppress_opponent_pressure."""
    kw = ops.combat_keyword_effects._kw_weights()
    amount = float(action.amount or 1)
    if amount == -1.0:
        units = float(kw.get("goad_all_suppression_units", 99))
    elif amount == -2.0:
        units = float(kw.get("goad_one_player_units", 3))
    else:
        units = max(1.0, amount)
    ops.suppress_opponent_pressure(state, units, _source_name(source))
    return True


@register_handler("detain")
def _h_detain(ops, state, strategy, source, action, target) -> bool:
    ops.suppress_opponent_pressure(state, max(1.0, float(action.amount or 1)), _source_name(source))
    return True


@register_handler("fight")
def _h_fight(ops, state, strategy, source, action, target) -> bool:
    fighter = ops._kw_best_fighter(state, source, action.raw)
    return bool(ops.fight_opponent_creature(
        state, strategy, fighter, bite=(action.token == "bite"), source=_source_name(source),
    ))


@register_handler("typed_pt_bonus")
def _h_typed_pt_bonus(ops, state, strategy, source, action, target) -> bool:
    """v4.76.0 WP3: typed team pump until end of turn (Ezuri, Elvish Warmaster,
    Overrun-shaped effects). The engine-side helper owns the BoardModifier
    bookkeeping (App/team_effects/logic.py::apply_team_pump)."""
    kind = (action.target or "creature").strip() or "creature"
    keywords = [k for k in (action.keyword or "").split(",") if k]
    ops.apply_team_pump_v4760(state, _source_name(source), float(action.amount), keywords, kind)
    ops.record_impact(state, _source_name(source), "team_pump", float(action.amount))
    return True



@register_handler("devotion_drain")
def _h_devotion_drain(ops, state, strategy, source, action, target) -> bool:
    """v4.83.0: 'each opponent loses X life, where X is your devotion to C'
    (Gray Merchant of Asphodel). Optional 'you gain life equal to the life
    lost this way' (action.token == 'gain')."""
    x = ops.devotion_to(state, action.keyword or "B")
    if x <= 0:
        return True
    before = sum(max(0.0, v) for v in state.opponents)
    ops.lose_each_opponent(state, float(x), _source_name(source))
    lost = before - sum(max(0.0, v) for v in state.opponents)
    if action.token == "gain" and lost > 0:
        ops.gain_life(state, lost, _source_name(source))
    return True



@register_handler("land_search")
def _h_land_search(ops, state, strategy, source, action, target) -> bool:
    """v4.84.0: 'Search your library for a basic land/Forest card, put it onto
    the battlefield (tapped)' - Nature's Lore, Cultivate, Wood Elves & Co.
    Nicht-Standard-Laender (Duals mit Typen) werden als passendes Standardland
    angenaehert."""
    allowed = {x for x in (action.keyword or "").split(",") if x}
    to_hand = 0
    if (action.target or "").startswith("hand:"):
        to_hand = int(action.target.split(":", 1)[1] or 0)
    ops.land_search(state, strategy, int(action.amount or 1), allowed, action.token == "tapped",
                    to_hand=to_hand, source=_source_name(source) if source is not None else "land search")
    return True
