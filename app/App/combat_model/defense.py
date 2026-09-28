"""
Board-aware defense against the abstract opponent pressure (v4.76.0, WP2).

Diagnosis (Docs/README.md v4.76.0): the abstract opponent phase dealt a fixed,
purely turn-dependent amount of "combat/pressure" damage (aggro: 1.4 x (turn-1)
+-30 %), completely independent of the tested deck's own board. Every deck
without heavy lifegain therefore died to "aggro" around turn 9 -- 94-100 % of
all aggro games for Lathril, Katara, Mice with Swords and Aziza alike -- which
says nothing about the deck.

This module lets the creatures that are still UNTAPPED when the opponents act
(i.e. did not attack and were not tapped for mana this turn -- the engine's
opponent phase runs at the end of our own turn, before our untap step) block
part of that pressure. It is an expected-value approximation, not a combat
simulator: the pressure number is split into abstract attackers of a
profile-typical power, a profile-typical share of them is blockable (the rest
is evasion, burn, drain), and every block stops one attacker. Blocking has a
real cost: an outclassed blocker (toughness <= attacker power) usually dies.

Policy, deliberately simple and disclosed:
  * blockers that probably survive (toughness > attacker power) always block;
  * chump blocks (blocker probably dies) only once life after the hit would be
    below `chump_only_below_life`;
  * the commander and engine-role creatures (same _ENGINE_ROLES as the
    attack posture) only block to prevent lethal damage.

All numbers live in Data/Models/combat_interaction_weights.json -> "defense"
and are first estimates, labeled as such there.

v4.77.0 (WP-A): the fixed policy above is now the ``block_willingness=50``
midpoint of the deck-wide play-style slider (see combat_model/playstyle.py)
-- ``strategy.playstyle["block_willingness"]`` scales `chump_only_below_life`
around its configured value (0 at willingness 0, 2x at willingness 100),
lets protected (commander/engine-role) creatures chump pre-lethal once
willingness reaches 80, and below willingness 50 caps how many of the
available blockers are even considered (a willingness/50 share, kept from
the toughest/most valuable end of the already-sorted list). At the default
willingness=50 every one of these is a no-op and behavior is byte-identical
to the pre-v4.77.0 fixed policy.

Engine-agnostic (no `import engine`); `ops` is the engine module.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from .interaction import _WEIGHTS
from .posture import _ENGINE_ROLES
from . import playstyle as _playstyle


def _defense_weights() -> dict:
    return _WEIGHTS.get("defense", {"enabled": False})


@dataclass
class _Blocker:
    kind: str            # "permanent" | "token"
    ref: Any             # Permanent or TokenGroup
    name: str
    toughness: float
    protected: bool      # commander / engine role -> only blocks vs lethal
    value: float         # lower = sacrificed first


def _toughness(ops: Any, state: Any, p: Any) -> float:
    base_p = float(p.card.power or 0)
    base_t = float(p.card.toughness or 0)
    try:
        eff_p = float(ops.creature_power(p, state))
    except Exception:
        eff_p = base_p
    # +1/+1 counters and anthems are symmetric +X/+X in practically every
    # case this engine models; reuse the power delta instead of a second
    # parallel toughness pipeline.
    return max(0.0, base_t + (eff_p - base_p))


def _candidate_blockers(ops: Any, state: Any, strategy: Any) -> List[_Blocker]:
    out: List[_Blocker] = []
    prio = getattr(strategy, "tutor_priority", []) or []
    for p in state.battlefield:
        if not p.card.is_creature or p.tapped:
            continue
        roles = getattr(p.card, "roles", set()) or set()
        protected = bool(p.card.commander) or bool(roles & _ENGINE_ROLES)
        try:
            value = float(ops.generic_tutor_score(p.card, prio))
        except Exception:
            value = 0.0
        out.append(_Blocker("permanent", p, p.card.name, _toughness(ops, state, p), protected, value))
    for g in getattr(state, "creature_tokens", []) or []:
        kws = {k.lower() for k in (g.keywords or set())}
        # Non-sick token groups always attack in this engine (attack_phase),
        # so only freshly made or vigilant tokens are still untapped now.
        if g.count <= 0 or not (g.entered_turn == state.turn or "vigilance" in kws):
            continue
        if getattr(g, "_tapped_for_cost_turn", None) == state.turn:
            continue  # tapped to pay a cost (v4.76.0 WP3) -> cannot block
        for _ in range(int(g.count)):
            out.append(_Blocker("token", g, g.name, float(g.toughness or 0), False, -1.0))
    return out


def absorb_pressure(
    ops: Any,
    state: Any,
    strategy: Any,
    rng: Any,
    dealt: float,
    profile: str,
) -> Tuple[float, int, List[str]]:
    """Returns (damage prevented, blockers lost, log lines). Caller applies
    the prevented amount to life; this function only removes dead blockers."""
    w = _defense_weights()
    if not w.get("enabled", False) or dealt <= 0:
        return 0.0, 0, []
    # v4.82.0: farbabhaengiges Keyword-Modell (keyword_effects.py) - vom
    # Aufrufer (engine.apply_abstract_opponent_phase-Wrapper) ueber
    # state._kw_defense_ctx gesetzt; fehlt es, laeuft der alte Pfad unveraendert.
    kw_ctx = getattr(state, "_kw_defense_ctx", None)
    if kw_ctx is not None:
        return _absorb_pressure_keywords(ops, state, strategy, rng, dealt, profile, w, kw_ctx)
    power_by = w.get("avg_attacker_power", {})
    share_by = w.get("blockable_share", {})
    atk_power = float(power_by.get(profile, power_by.get("midrange", 4.0)))
    blockable = float(share_by.get(profile, share_by.get("midrange", 0.75)))
    if atk_power <= 0:
        return 0.0, 0, []

    blockable_attackers = (dealt / atk_power) * blockable
    if blockable_attackers <= 0:
        return 0.0, 0, []

    willingness = _playstyle.get(strategy)["block_willingness"]
    life_after_hit = float(state.life)       # the hit has already been applied
    lethal = life_after_hit <= 0
    chump_only_below_life = float(w.get("chump_only_below_life", 15)) * (willingness / 50.0)
    allow_chump = life_after_hit < chump_only_below_life
    protected_may_block = lethal or willingness >= 80

    cands = _candidate_blockers(ops, state, strategy)
    survivors = [b for b in cands if b.toughness > atk_power and (not b.protected or protected_may_block)]
    chumps = [b for b in cands if b.toughness <= atk_power and (not b.protected or protected_may_block)]
    chumps.sort(key=lambda b: (b.kind != "token", b.value, b.toughness))
    survivors.sort(key=lambda b: -b.toughness)
    chosen = survivors + (chumps if allow_chump else [])
    if willingness < 50 and not lethal:
        # Reluctant to trade creatures away even when a block would survive --
        # only a willingness/50 share of the available blockers is offered,
        # kept from the front of the list (toughest survivors first).
        cap = int(math.ceil(len(chosen) * (willingness / 50.0)))
        chosen = chosen[:cap]

    n_blocks = min(len(chosen), int(math.ceil(blockable_attackers - 1e-9)))
    if n_blocks <= 0:
        return 0.0, 0, []
    # the last block may cover only part of an attacker's worth of pressure
    blocked_units = min(float(n_blocks), blockable_attackers)
    prevented = min(blocked_units * atk_power, dealt * float(w.get("max_prevented_share", 0.8)))

    lost = 0
    logs = [f"DEFENSE ({profile}): {n_blocks} blocker(s) stopped {prevented:.1f} of {dealt:.1f} pressure damage"]
    die_out = float(w.get("death_rate_when_outclassed", 0.8))
    die_ok = float(w.get("death_rate_when_survivable", 0.1))
    for b in chosen[:n_blocks]:
        p_die = die_ok if b.toughness > atk_power else die_out
        if rng.random() >= p_die:
            continue
        if b.kind == "token":
            if b.ref.count > 0:
                b.ref.count -= 1
                lost += 1
        else:
            kws = set()
            try:
                kws = ops.effective_keywords_in_state(b.ref, state)
            except Exception:
                pass
            if "indestructible" in kws:
                continue
            ops.move_permanent_to_zone(state, strategy, b.ref, "graveyard", reason="died blocking abstract attacker")
            ops.record_impact(state, b.name, "died_blocking", 1)
            lost += 1
        logs.append(f"DEFENSE: {b.name} died blocking")
    state.creature_tokens[:] = [g for g in state.creature_tokens if g.count > 0]
    return prevented, lost, logs


# ---------------------------------------------------------------------------
# v4.82.0 "Runde 4": Keyword-Variante von absorb_pressure.
# ---------------------------------------------------------------------------
def _blocker_keywords(ops: Any, state: Any, b: "_Blocker") -> set:
    if b.kind == "token":
        return {str(k).lower() for k in (b.ref.keywords or set())}
    try:
        return {str(k).lower() for k in ops.effective_keywords_in_state(b.ref, state)}
    except Exception:
        return {str(k).lower() for k in (b.ref.card.keywords or set())}


def _blocker_power(ops: Any, state: Any, b: "_Blocker") -> float:
    if b.kind == "token":
        return float(b.ref.power or 0)
    try:
        return float(ops.creature_power(b.ref, state))
    except Exception:
        return float(b.ref.card.power or 0)


def _absorb_pressure_keywords(ops, state, strategy, rng, dealt, profile, w, ctx):
    """Wie absorb_pressure, plus die Keyword-Zusammensetzung des gegnerischen
    Drucks aus den echten Decklisten seiner Farbe(n) (ctx):

      * Der Druck zerfaellt in Boden- und Luftangreifer. blockable_share (alte
        Kalibrierung) gilt weiter als der BODEN-blockbare Anteil gegen den
        gepoolten Durchschnittsgegner; der fliegende Anteil ist nur fuer
        eigene Flying/Reach-Blocker erreichbar. Gegen eine Farbe mit mehr
        Fliegern schrumpft der Bodenanteil entsprechend (am ALL-Wert
        verankert: gegen den Durchschnittsgegner bleibt er exakt gleich).
      * Menace-Angreifer binden im Erwartungswert (1 + Menace-Anteil) Blocker.
      * Gegnerisches Deathtouch/First Strike toetet Blocker haeufiger, Trample
        drueckt Ueberschuss (Angreiferstaerke - Blocker-Toughness) durch.
      * Eigene Blocker: First Strike senkt die eigene Todeschance (gleicher
        Faktor wie beim Angriff), Deathtouch/Wither/Infect toeten den
        Angreifer (Attrition -> ops.record_opponent_attrition), Lifelink
        gewinnt Leben in Hoehe der eigenen Power.
    """
    from . import keyword_effects as _kwe
    from .interaction import _WEIGHTS as _IW

    kw = _kwe._kw_weights()
    power_by = w.get("avg_attacker_power", {})
    share_by = w.get("blockable_share", {})
    atk_power = float(power_by.get(profile, power_by.get("midrange", 4.0)))
    blockable = float(share_by.get(profile, share_by.get("midrange", 0.75)))
    if atk_power <= 0:
        return 0.0, 0, []

    fly_all = float(_kwe.identity_row(None).get("flying", 0.18))
    fly = ctx.mean("flying", fly_all)
    combat_share = min(1.0, blockable / max(0.05, 1.0 - fly_all))
    units = dealt / atk_power
    ground_left = units * combat_share * (1.0 - fly)
    air_left = units * combat_share * fly
    menace = ctx.mean("menace", 0.0)
    dt = ctx.mean("deathtouch", 0.0)
    fs = ctx.mean("first_strike", 0.0)
    tr = ctx.mean("trample", 0.0)
    cost = 1.0 + menace
    if ground_left + air_left <= 0:
        return 0.0, 0, []

    willingness = _playstyle.get(strategy)["block_willingness"]
    life_after_hit = float(state.life)
    lethal = life_after_hit <= 0
    chump_only_below_life = float(w.get("chump_only_below_life", 15)) * (willingness / 50.0)
    allow_chump = life_after_hit < chump_only_below_life
    protected_may_block = lethal or willingness >= 80

    cands = _candidate_blockers(ops, state, strategy)
    survivors = [b for b in cands if b.toughness > atk_power and (not b.protected or protected_may_block)]
    chumps = [b for b in cands if b.toughness <= atk_power and (not b.protected or protected_may_block)]
    chumps.sort(key=lambda b: (b.kind != "token", b.value, b.toughness))
    survivors.sort(key=lambda b: -b.toughness)
    chosen = survivors + (chumps if allow_chump else [])
    if willingness < 50 and not lethal:
        cap = int(math.ceil(len(chosen) * (willingness / 50.0)))
        chosen = chosen[:cap]

    used = []  # (blocker, covered_units, keywords)
    for b in chosen:
        if ground_left <= 1e-9 and air_left <= 1e-9:
            break
        kws = _blocker_keywords(ops, state, b)
        share = 1.0 / cost
        got = 0.0
        if kws & {"flying", "reach"} and air_left > 1e-9:
            # Flying/Reach-Blocker decken zuerst die Luft (nur sie koennen das),
            # Restkapazitaet geht an den Boden.
            got = min(share, air_left)
            air_left -= got
        if ground_left > 1e-9 and share - got > 1e-9:
            g = min(share - got, ground_left)
            ground_left -= g
            got += g
        if got <= 1e-9:
            continue
        used.append((b, got, kws))
    if not used:
        return 0.0, 0, []

    prevented = 0.0
    for b, got, _kws in used:
        pass_through = tr * max(0.0, atk_power - b.toughness)
        prevented += got * max(0.0, atk_power - pass_through)
    prevented = min(prevented, dealt * float(w.get("max_prevented_share", 0.8)))

    logs = [f"DEFENSE+KW ({profile}): {len(used)} blocker(s) stopped {prevented:.1f} of {dealt:.1f} pressure damage "
            f"(opp. fliers {fly:.0%}, menace {menace:.0%}, deathtouch {dt:.0%})"]
    die_out = float(w.get("death_rate_when_outclassed", 0.8))
    die_ok = float(w.get("death_rate_when_survivable", 0.1))
    fs_own = float(_IW.get("first_strike", {}).get("trade_rate_multiplier", 1.0))
    fs_bump = float(kw.get("defense_first_strike_death_bump", 0.5))
    lost = 0
    kills = 0.0
    for b, got, kws in used:
        frac = min(1.0, got * cost)
        p_die = die_ok if b.toughness > atk_power else die_out
        if kws & {"first strike", "double strike"}:
            p_die *= fs_own
        p_die = dt + (1.0 - dt) * p_die
        p_die = p_die + (1.0 - p_die) * fs * fs_bump
        kills += frac * _kwe.attrition_credit(kws, _blocker_power(ops, state, b), ctx)
        if "lifelink" in kws:
            gain = frac * _blocker_power(ops, state, b)
            if gain > 0:
                try:
                    ops.gain_life(state, gain, f"{b.name} lifelink (block)")
                except Exception:
                    pass
        if rng.random() >= p_die:
            continue
        if b.kind == "token":
            if b.ref.count > 0:
                b.ref.count -= 1
                lost += 1
        else:
            if "indestructible" in kws:
                continue
            ops.move_permanent_to_zone(state, strategy, b.ref, "graveyard", reason="died blocking abstract attacker")
            ops.record_impact(state, b.name, "died_blocking", 1)
            lost += 1
        logs.append(f"DEFENSE: {b.name} died blocking")
    state.creature_tokens[:] = [g for g in state.creature_tokens if g.count > 0]
    if kills > 0 and hasattr(ops, "record_opponent_attrition"):
        ops.record_opponent_attrition(state, strategy, rng, kills, "blocking (deathtouch/wither/infect)")
    return prevented, lost, logs
