"""
Trigger-Bus, Teil 1: reines Parsen von Ausloese-Bedingungen (v4.83.0).

Hintergrund (Debug-Befund v4.83.0, siehe Docs/README.md): Die Engine parst
seit v4.5 jede Oracle-Zeile in SemanticAbility-Objekte und klassifiziert
ausgeloeste Faehigkeiten ("Whenever you cast an enchantment spell, draw a
card.") als "exact" - es gab aber KEINEN generischen Dispatcher, der solche
Faehigkeiten beim passenden Spielereignis tatsaechlich ausfuehrt. Ausgefuehrt
wurden nur handverdrahtete Einzelfaelle (eigenes ETB mit draw/scry/Food,
Angriffs-Draw/Scry, namensbasierte Sonderfaelle). In 40 echten EDHREC-
Trainingsdecks standen ~1.300 ausgeloeste Zeilen, der Grossteil davon lief
nie. Dieses Modul uebersetzt die AUSLOESE-BEDINGUNG einer Zeile in eine
TriggerSpec; engine.py ruft beim jeweiligen Ereignis `matches()` auf und
fuehrt dann die schon vorhandenen, geparsten Aktionen aus.

Bewusst konservativ: Zeilen mit Zwischen-"if" (intervening if), optionalen
Kosten ("you may pay/sacrifice/discard", "unless") oder Bedingungen, die
dieses Modul nicht sicher lesen kann, bekommen `supported=False` und werden
NICHT ausgefuehrt (lieber ehrlich ausgelassen als falsch ausgefuehrt) -
sie tauchen in der Abdeckungs-Statistik als offen auf.

Keine Engine-Abhaengigkeit: nur Text rein, TriggerSpec raus.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import FrozenSet, Optional, Tuple

# Kartentypen / Supertypen, die in Filtern vorkommen. Alles andere, was vor
# "spell"/"creature" steht, wird als Untertyp (Elf, Dragon, ...) behandelt.
_CARD_TYPES = {
    "creature", "enchantment", "artifact", "land", "instant", "sorcery",
    "planeswalker", "battle", "legendary", "historic", "kindred", "tribal",
    "noncreature", "nonland", "nonartifact", "nontoken", "token", "aura",
    "equipment", "vehicle", "multicolored", "colorless", "permanent",
}
_ABILITY_WORD_RE = re.compile(r"^(?:[a-z0-9'’ ,.!-]+?)\s+[—–]\s+")
_ARTICLE_RE = re.compile(r"^(?:a|an|one|another|each|the)\s+")


@dataclass(frozen=True)
class TriggerSpec:
    event: str                      # cast|enters|land_enters|dies|attacks|you_attack|combat_damage|
                                    # combat_damage_batch|upkeep|end_step|begin_combat|draw|draw_nth|
                                    # opponent_draws|other
    subject: str = "any"            # self|other|any|self_or_other
    types: FrozenSet[str] = frozenset()
    subtypes: FrozenSet[str] = frozenset()
    min_mv: Optional[int] = None
    each_player: bool = False       # "each upkeep"/"each end step" (nicht nur deine)
    once_per_turn: bool = False     # "for the first time each turn"/"your first spell each turn"
    nth: int = 0                    # "your second card each turn" -> 2
    batch: bool = False             # "one or more ... enter/attack/deal"
    also_attacks: bool = False      # "whenever this creature enters or attacks"
    any_player: bool = False        # "whenever a player casts ..." (eigene UND gegnerische Zauber)
    tax: bool = False               # "... unless that player pays {N}" (Rhystic-Study-artig)
    supported: bool = True
    reason: str = ""
    condition: str = ""
    effect: str = ""


def strip_ability_word(low: str) -> str:
    """'constellation — whenever ...' -> 'whenever ...'. Nur wenn danach
    wirklich ein Ausloeser folgt (sonst waere z.B. ein Kapitel-/Modus-Strich
    betroffen)."""
    m = _ABILITY_WORD_RE.match(low)
    if m:
        rest = low[m.end():]
        if rest.startswith(("when ", "whenever ", "at the beginning")):
            return rest
    return low


def split_condition(low: str) -> Tuple[str, str]:
    """Trennt 'whenever X, Y' in (X-Teil, Y-Teil). Nimmt das erste Komma
    nach dem Ausloeser, das nicht innerhalb eines Zahlwort-Konstrukts steht."""
    idx = low.find(", ")
    if idx < 0:
        return low, ""
    return low[:idx].strip(), low[idx + 2:].strip()


def _parse_filter(noun: str) -> Tuple[FrozenSet[str], FrozenSet[str], Optional[int], bool]:
    """'an enchantment spell' / 'a noncreature spell' / 'an instant or
    sorcery spell' / 'a creature spell with mana value 4 or greater' /
    'an elf spell'. Rueckgabe: (types, subtypes, min_mv, ok)."""
    noun = noun.strip()
    min_mv = None
    m = re.search(r"with (?:mana value|converted mana cost) (\d+) or greater", noun)
    if m:
        min_mv = int(m.group(1))
        noun = noun[:m.start()].strip()
    if re.search(r"\bwith\b|\bthat\b|\bwhose\b|\bfrom\b|\bthis turn\b|\bduring\b|\bfirst\b|\bsecond\b", noun):
        return frozenset(), frozenset(), min_mv, False
    noun = re.sub(r"\b(spells?|cards?)\b", "", noun).strip()
    noun = _ARTICLE_RE.sub("", noun).strip()
    if not noun:
        return frozenset(), frozenset(), min_mv, True
    words = [w for w in re.split(r"[\s,]+", noun) if w and w not in ("or", "and", "a", "an")]
    types, subtypes = set(), set()
    for w in words:
        if w in _CARD_TYPES:
            types.add(w)
        elif re.fullmatch(r"[a-z'-]+", w):
            subtypes.add(w.rstrip("s") if w.endswith("s") and len(w) > 3 else w)
        else:
            return frozenset(), frozenset(), min_mv, False
    return frozenset(types), frozenset(subtypes), min_mv, True


_OPTIONAL_COST_RE = re.compile(
    r"may (?:pay|sacrifice|discard|exile|tap|remove|return)|\bunless\b|if you do\b|when you do\b|if (?:the|that) player doesn't"
)


@lru_cache(maxsize=8192)
def parse_trigger(line: str, card_name: str = "") -> Optional[TriggerSpec]:
    """Parst EINE Oracle-Zeile (bereits ohne Reminder-Text, beliebige
    Gross-/Kleinschreibung). None, wenn die Zeile gar keine ausgeloeste
    Faehigkeit ist."""
    low = strip_ability_word(line.strip().lower())
    if not low.startswith(("when ", "whenever ", "at the beginning")):
        return None
    name = card_name.lower().strip()
    short = name.split(",")[0].strip() if name else ""
    selfref = r"(?:this [a-z]+|~" + (f"|{re.escape(name)}" if name else "") + (f"|{re.escape(short)}" if short else "") + ")"
    cond, effect = split_condition(low)

    def spec(event, **kw):
        s = TriggerSpec(event=event, condition=cond, effect=effect, **kw)
        # Zwischen-"if" oder optionale Kosten -> ehrlich ausgelassen.
        if effect.startswith("if ") or re.search(r"\bif\b", cond):
            return TriggerSpec(event=event, condition=cond, effect=effect, supported=False,
                               reason="intervening_if", **{k: v for k, v in kw.items() if k not in ("supported", "reason")})
        eff_for_cost = effect
        if event == "opponent_cast":
            eff_for_cost = re.sub(r"unless that player pays \{[^}]+\}(?:\{[^}]+\})*", "", effect)
        if _OPTIONAL_COST_RE.search(eff_for_cost):
            return TriggerSpec(event=event, condition=cond, effect=effect, supported=False,
                               reason="optional_cost", **{k: v for k, v in kw.items() if k not in ("supported", "reason")})
        if re.search(r"\bfor each\b", effect) or \
                (re.search(r"where x is|equal to (?:the number|its|that|their|your)", effect) and "devotion" not in effect):
            return TriggerSpec(event=event, condition=cond, effect=effect, supported=False,
                               reason="variable_amount", **{k: v for k, v in kw.items() if k not in ("supported", "reason")})
        if re.search(r"\bwhen (?:it|that creature|that token|this creature|they) (?:dies|die|leaves)\b|at the beginning of the next|\buntil your next turn\b.*\bwhenever\b", effect):
            return TriggerSpec(event=event, condition=cond, effect=effect, supported=False,
                               reason="delayed_trigger", **{k: v for k, v in kw.items() if k not in ("supported", "reason")})
        if re.search(r"\bchoose (?:one|two)\b", effect):
            return TriggerSpec(event=event, condition=cond, effect=effect, supported=False,
                               reason="modal", **{k: v for k, v in kw.items() if k not in ("supported", "reason")})
        return s

    once = "for the first time each turn" in cond or "first spell each turn" in cond

    # --- Schritt-Ausloeser ------------------------------------------------
    if cond.startswith("at the beginning"):
        each = bool(re.search(r"\beach (?:player's )?(?:upkeep|end step)|\beach combat\b", cond))
        if "opponent's" in cond or "each opponent" in cond:
            return spec("other", supported=False, reason="opponent_step")
        if "upkeep" in cond or "precombat main" in cond or "first main phase" in cond or "draw step" in cond:
            return spec("upkeep", each_player=each)
        if "end step" in cond:
            return spec("end_step", each_player=each)
        if "combat" in cond:
            if "your turn" not in cond and not each and "each combat" not in cond:
                return spec("begin_combat")
            return spec("begin_combat", each_player=False)
        return spec("other", supported=False, reason="unknown_step")

    # --- Zauber wirken ----------------------------------------------------
    m = re.match(r"whenever (you|a player|an opponent) casts? (?:or copies |or copy )?(.+?)(?: spell)?(?:s)?(?:,|$)", cond + ",")
    if m and " cast" in cond:
        who = m.group(1)
        noun = re.sub(r"^(?:or copy |or copies )", "", m.group(2))
        if who == "an opponent":
            if "first spell" in noun or "second spell" in noun:
                return spec("other", supported=False, reason="nth_spell")
            types, subtypes, min_mv, ok = _parse_filter(noun + " spell")
            if not ok:
                return spec("other", supported=False, reason="cast_filter")
            return spec("opponent_cast", types=types, subtypes=subtypes, min_mv=min_mv,
                        tax="unless that player pays" in effect)
        if "first spell" in noun or "second spell" in noun:
            if re.search(r"your first spell each turn|your first spell during each of your turns", cond):
                return spec("cast", once_per_turn=True)
            return spec("other", supported=False, reason="nth_spell")
        types, subtypes, min_mv, ok = _parse_filter(noun + " spell")
        if not ok:
            return spec("other", supported=False, reason="cast_filter")
        return spec("cast", types=types, subtypes=subtypes, min_mv=min_mv, once_per_turn=once,
                    any_player=(who == "a player"))
    if re.match(r"when(?:ever)? you cast (?:this|~)", cond):
        return spec("other", supported=False, reason="self_cast")

    # --- +1/+1-Marken (v4.85.0) ----------------------------------------------
    if "+1/+1 counter" in cond and re.search(r"\bput\b|\bare put\b|\bis put\b", cond):
        if "opponent" in cond:
            return spec("other", supported=False, reason="opponent_counters")
        if re.search(rf"(?:counters? (?:is|are) put on|counters? on) {selfref}$", cond):
            return spec("counter_placed", subject="self", batch="one or more" in cond, once_per_turn=once)
        m2 = re.search(r"(?:counters? (?:is|are) put on|counters? on) (a|an|another) (.+?)(?: you control)?$", cond)
        if m2:
            types, subtypes, _mv, ok = _parse_filter(m2.group(2))
            if not ok:
                return spec("other", supported=False, reason="counter_filter")
            return spec("counter_placed", subject="other" if m2.group(1) == "another" else "any",
                        types=types, subtypes=subtypes, batch="one or more" in cond, once_per_turn=once)
        return spec("other", supported=False, reason="counter_other")

    # --- Leben gewinnen -----------------------------------------------------
    if re.match(r"whenever you gain life", cond):
        if re.search(r"each opponent loses 1 life|target opponent loses that much life|put a \+1/\+1 counter on this creature", effect):
            return spec("other", supported=False, reason="legacy_lifegain")
        return spec("life_gain", once_per_turn=once)

    # --- Opfern -------------------------------------------------------------
    m = re.match(r"whenever you sacrifice (?:a|an|another|one or more) (.+?)$", cond)
    if m:
        types, subtypes, _mv, ok = _parse_filter(m.group(1))
        if not ok:
            return spec("other", supported=False, reason="sacrifice_filter")
        return spec("sacrifice", types=types, subtypes=subtypes, once_per_turn=once, batch="one or more" in cond)

    # --- Karten ziehen -----------------------------------------------------
    if re.match(r"whenever an opponent draws (?:a|their first) card", cond):
        if "first" in cond:
            return spec("other", supported=False, reason="nth_draw")
        return spec("opponent_draws")
    if re.match(r"whenever you draw a card", cond):
        return spec("draw", once_per_turn=once)
    m = re.match(r"whenever you draw your (second|third) card each turn", cond)
    if m:
        return spec("draw_nth", nth=2 if m.group(1) == "second" else 3)

    # --- "enters or attacks" (sehr haeufige Doppel-Ausloesung) -------------
    if re.match(rf"when(?:ever)? {selfref} enters(?: the battlefield)? or attacks$", cond):
        return spec("enters", subject="self", also_attacks=True)

    # --- Angriff ------------------------------------------------------------
    if re.match(r"whenever you attack", cond):
        return spec("you_attack", once_per_turn=once)
    if re.search(r"deals? combat damage to (?:a player|an opponent|one or more players)(?: or (?:a )?(?:planeswalker|battle))?$", cond):
        if re.match(rf"whenever {selfref} deals", cond) or re.match(r"whenever equipped creature deals", cond) or re.match(r"whenever enchanted creature deals", cond):
            if "equipped" in cond or "enchanted" in cond:
                return spec("combat_damage", subject="attached")
            return spec("combat_damage", subject="self", once_per_turn=once)
        if re.match(r"whenever one or more (.+?) you control deal", cond):
            types, subtypes, _mv, ok = _parse_filter(re.match(r"whenever one or more (.+?) you control deal", cond).group(1))
            if not ok:
                return spec("other", supported=False, reason="combat_filter")
            return spec("combat_damage_batch", types=types, subtypes=subtypes, batch=True, once_per_turn=once)
        m = re.match(r"whenever (?:a|another) (.+?) you control deals", cond)
        if m:
            types, subtypes, _mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="combat_filter")
            return spec("combat_damage", subject="any" if cond.startswith("whenever a ") else "other",
                        types=types, subtypes=subtypes, once_per_turn=once)
        return spec("other", supported=False, reason="combat_damage_other")
    if re.search(r"\battacks?\b", cond) and "attacks you" not in cond and "opponent" not in cond:
        if re.match(rf"whenever {selfref}(?: and at least .*)? attacks$", cond) or re.match(rf"whenever {selfref} attacks", cond):
            if "blocks" in cond or "becomes blocked" in cond:
                return spec("other", supported=False, reason="blocks")
            return spec("attacks", subject="self", once_per_turn=once)
        m = re.match(r"whenever one or more (.+?) you control attack", cond)
        if m:
            types, subtypes, _mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="attack_filter")
            return spec("attacks", subject="any", types=types, subtypes=subtypes, batch=True, once_per_turn=once)
        m = re.match(r"whenever (?:a|another) (.+?) you control attacks", cond)
        if m:
            types, subtypes, _mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="attack_filter")
            return spec("attacks", subject="any" if cond.startswith("whenever a ") else "other",
                        types=types, subtypes=subtypes, once_per_turn=once)
        return spec("other", supported=False, reason="attack_other")

    # --- Sterben ------------------------------------------------------------
    if re.search(r"\bdies\b|\bdie\b|is put into a graveyard from the battlefield", cond):
        if "opponent" in cond or "you don't control" in cond:
            return spec("other", supported=False, reason="opponent_dies")
        if re.match(rf"when(?:ever)? {selfref} dies$", cond) or (
                re.match(r"^when [a-z0-9'’ .-]+ dies$", cond) and not re.search(r"\banother\b|\byou control\b|^when (?:a|an|one) ", cond)):
            return spec("dies", subject="self", types=frozenset({"creature"}))
        m = re.match(rf"whenever {selfref} or another (.+?)(?: you control)? dies$", cond)
        if m:
            types, subtypes, _mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="dies_filter")
            return spec("dies", subject="self_or_other", types=types, subtypes=subtypes, once_per_turn=once)
        m = re.match(r"whenever (?:a|another) (.+?)(?: you control)? dies$", cond)
        if m:
            types, subtypes, _mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="dies_filter")
            return spec("dies", subject="other" if "another" in cond else "any", types=types, subtypes=subtypes,
                        once_per_turn=once)
        m = re.match(r"whenever one or more (.+?)(?: you control)? die$", cond)
        if m:
            types, subtypes, _mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="dies_filter")
            return spec("dies", subject="any", types=types, subtypes=subtypes, batch=True, once_per_turn=once)
        return spec("other", supported=False, reason="dies_other")

    # --- Ins Spiel kommen ---------------------------------------------------
    if re.search(r"\benters?\b(?: the battlefield)?", cond):
        if "opponent" in cond or "you don't control" in cond:
            return spec("other", supported=False, reason="opponent_enters")
        c2 = re.sub(r" the battlefield", "", cond)
        c2 = re.sub(r" under your control", " you control", c2)
        if re.match(r"whenever (?:a|another) land you control enters$", c2) or re.match(r"whenever a land enters", c2) \
                or re.match(r"whenever one or more lands you control enter$", c2):
            return spec("land_enters", once_per_turn=once, batch="one or more" in c2)
        m = re.match(rf"when(?:ever)? {selfref} or another (.+?) you control enters$", c2) or \
            re.match(rf"when(?:ever)? {selfref} or another (.+?) enters$", c2)
        if m:
            types, subtypes, mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="enters_filter")
            return spec("enters", subject="self_or_other", types=types, subtypes=subtypes, min_mv=mv, once_per_turn=once)
        if re.match(rf"when(?:ever)? {selfref}(?: is turned face up)? enters$", c2) or \
                re.match(r"when(?:ever)? this (?:(?!\bor\b)[a-z ])+? enters$", c2):
            return spec("enters", subject="self")
        if re.match(r"^when [a-z0-9'’ .-]+ enters$", c2) and not re.search(r"\banother\b|\byou control\b|^when (?:a|an|one) ", c2):
            return spec("enters", subject="self")
        m = re.match(r"whenever one or more (.+?)(?: you control)? enter$", c2)
        if m:
            types, subtypes, mv, ok = _parse_filter(m.group(1))
            if not ok:
                return spec("other", supported=False, reason="enters_filter")
            return spec("enters", subject="any", types=types, subtypes=subtypes, min_mv=mv, batch=True, once_per_turn=once)
        m = re.match(r"when(?:ever)? (a|an|another) (.+?)(?: you control)? enters$", c2)
        if m:
            types, subtypes, mv, ok = _parse_filter(m.group(2))
            if not ok:
                return spec("other", supported=False, reason="enters_filter")
            if "land" in types:
                return spec("land_enters", once_per_turn=once)
            return spec("enters", subject="other" if m.group(1) == "another" else "any",
                        types=types, subtypes=subtypes, min_mv=mv, once_per_turn=once)
        return spec("other", supported=False, reason="enters_other")

    return spec("other", supported=False, reason="unrecognized")


def card_matches(spec: TriggerSpec, *, type_line: str, mana_value: float = 0.0,
                 is_token: bool = False, colors: int = 1) -> bool:
    """Prueft den Typ-/Untertyp-/MV-Filter einer TriggerSpec gegen die
    Eigenschaften eines Objekts (Zauber, Permanent oder Token)."""
    tl = (type_line or "").lower()
    if spec.min_mv is not None and mana_value < spec.min_mv:
        return False
    types = set(spec.types)
    if "nontoken" in types:
        if is_token:
            return False
        types.discard("nontoken")
    if "token" in types:
        if not is_token:
            return False
        types.discard("token")
    if "noncreature" in types:
        if "creature" in tl:
            return False
        types.discard("noncreature")
    if "nonland" in types:
        if "land" in tl:
            return False
        types.discard("nonland")
    if "nonartifact" in types:
        if "artifact" in tl:
            return False
        types.discard("nonartifact")
    if "multicolored" in types:
        if colors < 2:
            return False
        types.discard("multicolored")
    if "colorless" in types:
        if colors != 0:
            return False
        types.discard("colorless")
    if "historic" in types:
        if not ("legendary" in tl or "artifact" in tl or "saga" in tl):
            return False
        types.discard("historic")
    types.discard("permanent")
    types.discard("kindred")
    types.discard("tribal")
    # verbleibende Kartentypen: "instant or sorcery" ist ODER, alles andere UND
    # waere zu streng - Oracle-Filter mit mehreren Typen sind praktisch immer ODER.
    if types and not any(t in tl for t in types):
        return False
    if spec.subtypes and not any(re.search(rf"\b{re.escape(s)}s?\b", tl) for s in spec.subtypes):
        return False
    return True
