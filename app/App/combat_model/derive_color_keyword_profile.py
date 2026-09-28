#!/usr/bin/env python3
"""
v4.82.0 "Runde 4": leitet Data/Models/color_keyword_profile.json aus den
1.585 echten EDHREC-Bracket-3-Average-Decks ab (Training data/
deck_cards_slim.csv + unique_cards_enriched.csv).

Pro Farbidentitaet (alle 32 plus "ALL" = gepoolt ueber alle Decks) werden
MENGENGEWICHTET (jede Kartenkopie in jedem Deck zaehlt einmal, also genau so,
wie ein Gegner dieser Farbe die Karten tatsaechlich auf dem Tisch hat)
folgende Kreatur-Eigenschaften gemessen:

  * Keyword-Anteile unter Kreaturen: flying, reach, air_blocker (flying ODER
    reach - kann eine fliegende Kreatur blocken), deathtouch, menace,
    first_strike (first strike ODER double strike), double_strike, trample,
    lifelink, vigilance, indestructible, hexproof (hexproof ODER shroud)
  * artifact: Anteil Artefakt-Kreaturen (Fear/Intimidate-Blocker)
  * color_X: Anteil Kreaturen, deren Farben X enthalten (Protection/
    Intimidate/Fear)
  * spell_color_X: Anteil ALLER Nicht-Land-Karten mit Farbe X (Proxy fuer
    "welcher Anteil des gegnerischen Removals ist X-farbig" - Protection
    gegen gegnerisches Removal)
  * mean_power / mean_toughness (nur numerische Werte, "*" ausgelassen)
  * creatures_per_deck: mittlere Kreaturanzahl je Deck (Menace-Doppelblock-
    Faehigkeit)

Aufruf (vom App-Ordner aus):
    python App/combat_model/derive_color_keyword_profile.py \
        "<pfad>/deck_cards_slim.csv" "<pfad>/unique_cards_enriched.csv" \
        Data/Models/color_keyword_profile.json
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

KW_FIELDS = {
    "flying": {"flying"},
    "reach": {"reach"},
    "air_blocker": {"flying", "reach"},
    "deathtouch": {"deathtouch"},
    "menace": {"menace"},
    "first_strike": {"first strike", "double strike"},
    "double_strike": {"double strike"},
    "trample": {"trample"},
    "lifelink": {"lifelink"},
    "vigilance": {"vigilance"},
    "indestructible": {"indestructible"},
    "hexproof": {"hexproof", "shroud"},
}
COLORS = "WUBRG"


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _key(color_identity: str) -> str:
    c = "".join(ch for ch in COLORS if ch in (color_identity or "").upper())
    return c or "C"


def derive(deck_cards_path: Path, cards_path: Path) -> dict:
    cards = {}
    with open(cards_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            kws = {k.strip().lower() for k in (r.get("keywords") or "").split(";") if k.strip()}
            cards[r["card_name"]] = {
                "type": r.get("type_line") or "",
                "colors": set((r.get("colors") or "").upper()),
                "kws": kws,
                "power": _num(r.get("power")),
                "toughness": _num(r.get("toughness")),
            }

    acc = defaultdict(lambda: defaultdict(float))
    decks = defaultdict(set)
    deck_creatures = defaultdict(lambda: defaultdict(float))
    missing = 0
    with open(deck_cards_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            c = cards.get(r["card_name"])
            if c is None:
                missing += 1
                continue
            q = float(r.get("quantity") or 1)
            deck_id = (r["identity_slug"], r["commander_name"], r["tag"])
            for key in (_key(r["color_identity"]), "ALL"):
                a = acc[key]
                decks[key].add(deck_id)
                if "Land" not in c["type"]:
                    a["nonland"] += q
                    for x in COLORS:
                        if x in c["colors"]:
                            a[f"spell_color_{x}"] += q
                if "Creature" not in c["type"]:
                    continue
                deck_creatures[key][deck_id] += q
                a["creatures"] += q
                for name, members in KW_FIELDS.items():
                    if c["kws"] & members:
                        a[name] += q
                if "Artifact" in c["type"]:
                    a["artifact"] += q
                for x in COLORS:
                    if x in c["colors"]:
                        a[f"color_{x}"] += q
                if c["power"] is not None:
                    a["power_sum"] += q * c["power"]
                    a["power_n"] += q
                if c["toughness"] is not None:
                    a["toughness_sum"] += q * c["toughness"]
                    a["toughness_n"] += q

    out = {}
    for key, a in sorted(acc.items()):
        n = max(1.0, a["creatures"])
        row = {"decks": len(decks[key]), "creature_copies": int(a["creatures"])}
        for name in list(KW_FIELDS) + ["artifact"] + [f"color_{x}" for x in COLORS]:
            row[name] = round(a[name] / n, 4)
        nl = max(1.0, a["nonland"])
        for x in COLORS:
            row[f"spell_color_{x}"] = round(a[f"spell_color_{x}"] / nl, 4)
        row["mean_power"] = round(a["power_sum"] / max(1.0, a["power_n"]), 3)
        row["mean_toughness"] = round(a["toughness_sum"] / max(1.0, a["toughness_n"]), 3)
        per_deck = list(deck_creatures[key].values())
        row["creatures_per_deck"] = round(sum(per_deck) / max(1, len(decks[key])), 2)
        out[key] = row
    return {"identities": out, "unmatched_card_rows": missing}


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    data = derive(Path(argv[1]), Path(argv[2]))
    payload = {
        "version": "1.0",
        "source": "1.585 EDHREC Bracket-3 Average Decks (deck_cards_slim.csv, mengengewichtet)",
        "derived_by": "App/combat_model/derive_color_keyword_profile.py",
        **data,
    }
    Path(argv[3]).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {argv[3]}: {len(data['identities'])} identities, unmatched rows {data['unmatched_card_rows']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
