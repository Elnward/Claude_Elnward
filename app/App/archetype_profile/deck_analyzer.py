"""Analyse-Prototyp: bewertet eine BELIEBIGE hochgeladene Decklist gegen die aus 1.585
EDHREC-Average-Decks gelernten Referenzverteilungen (siehe reference_model.py und
commander_report.md fuer die volle Methodik). Das ist der naechste Schritt auf der in
`auswertung_v1` gelegten Know-how-Basis: "auf dieser Basis hochgeladene Decks
analysieren".

Kurz gesagt:
  1. Jede Karte der hochgeladenen Liste wird klassifiziert -- bevorzugt per Nachschlagen
     in der Referenz-Kartendatenbank (`data/unique_cards_classified.csv`, 8.445 Karten,
     bereits nach denselben Regeln wie die EDHREC-Trainingsdaten eingeordnet). Fuer
     Karten, die dort nicht vorkommen (neue Sets, sehr seltene Karten), kann optional
     Manakosten/Oracle-Text mitgegeben werden -- dann greift dieselbe Live-Klassifikation
     (`classify.py`), die auch beim Aufbau der Trainingsdaten verwendet wurde.
  2. Aus den klassifizierten Karten wird ein Deck-Profil im selben Format wie
     `deck_profiles.csv` gebaut (Laender/Ramp/CardAdvantage/Interaction/... -Zaehlwerte,
     Manakurve, Kreatur-P/T-Verteilung).
  3. Dieses Profil wird der passenden Identitaet x Strategie-Tag-Referenz aus
     `reference_model.AverageDeckModel` gegenuebergestellt (Differenz + Prozent je Feld).

Nutzung (Beispiel):

    from deck_analyzer import DeckAnalyzer

    analyzer = DeckAnalyzer.load()  # laedt data/ + reference_model einmalig
    result = analyzer.analyze(
        decklist=[{"name": "Sol Ring", "quantity": 1}, ...],
        identity_slug="simic",       # optional; sonst Auto-Erkennung aus Manapips
        tags=["Landfall"],           # optional; leer = nur Farbidentitaets-Baseline
    )
    print(result.report_text)

Dieses Modul haengt NICHT von EDHREC/Scryfall zur Laufzeit ab -- es rechnet ausschliesslich
mit den mitgelieferten, bereits exportierten Referenzdateien unter data/.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .classify import classify_card
from .identity_colors import detect_identity_slug
from .mana_utils import parse_pips
from .reference_model import AverageDeckModel, _DECK_PROFILE_FIELDS
from .stats_utils import weighted_quantile

DATA_DIR = Path(__file__).parent / "data"

CMC_EDGES = [0, 1, 2, 3, 4, 5, 6, 7, 99]
CMC_LABELS = ["0", "1", "2", "3", "4", "5", "6", "7+"]

# identisch zu step2_deck_profiles.py, damit die Zaehlweise exakt zu deck_profiles.csv passt
INTERACTION_SINGLE_TAGS = {
    "removal_single_exile", "removal_single_destroy", "removal_or_burn_single",
    "removal_single_debuff", "removal_or_tuck_single", "bounce_single",
    "removal_single_creature_exile", "counterspell",
}
INTERACTION_BOARD_TAGS = {"removal_board", "removal_board_scalable", "bounce_board_overload"}
INTERACTION_PROTECTION_TAGS = {"protection_grant"}


def _to_float(value: Any) -> float | None:
    if value in (None, "", "nan"):
        return None
    try:
        f = float(value)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _norm_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


@dataclass
class CardRecord:
    name: str
    quantity: int
    type: str | None
    cmc: float | None
    power_num: float | None
    toughness_num: float | None
    primary_role: str | None
    effect_tags: list[str]
    simple_effect: str | None
    pips: dict
    source: str  # "reference_db" | "live_classified" | "unknown"


class CardLookup:
    """Nachschlagetabelle name(normalisiert) -> Klassifikations-Zeile aus
    data/unique_cards_classified.csv (8.445 bereits klassifizierte EDHREC-Karten)."""

    def __init__(self, csv_path: Path | str = DATA_DIR / "unique_cards_classified.csv"):
        self._by_name: dict[str, dict] = {}
        with open(csv_path, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                self._by_name.setdefault(_norm_name(row["card_name"]), row)

    def __len__(self) -> int:
        return len(self._by_name)

    def lookup(self, name: str) -> dict | None:
        return self._by_name.get(_norm_name(name))


def classify_uploaded_card(
    name: str,
    quantity: int,
    lookup: CardLookup,
    *,
    mana_cost: str | None = None,
    type_: str | None = None,
    oracle_text: str | None = None,
    power: str | None = None,
    toughness: str | None = None,
) -> CardRecord:
    """Klassifiziert eine hochgeladene Karte. Reihenfolge: (1) Referenz-Datenbank,
    (2) Live-Klassifikation falls genug Rohdaten mitgegeben wurden, (3) 'unknown'."""
    row = lookup.lookup(name)
    if row is not None:
        pips = parse_pips(row.get("mana_cost") or "")
        raw_tags = row.get("effect_tags") or ""
        return CardRecord(
            name=row["card_name"], quantity=quantity, type=row.get("type") or None,
            cmc=_to_float(row.get("cmc")),
            power_num=_to_float(row.get("power_num")), toughness_num=_to_float(row.get("toughness_num")),
            primary_role=row.get("primary_role") or None,
            effect_tags=raw_tags.split(";") if raw_tags else [],
            simple_effect=row.get("simple_effect") or None, pips=pips, source="reference_db",
        )

    if mana_cost is not None or oracle_text is not None:
        cls = classify_card(name, oracle_text or "", type_ or "")
        pips = parse_pips(mana_cost or "")
        cmc = sum(v for k, v in pips.items() if k != "has_x") if mana_cost is not None else None
        return CardRecord(
            name=name, quantity=quantity, type=type_, cmc=cmc,
            power_num=_to_float(power), toughness_num=_to_float(toughness),
            primary_role=cls["primary_role"], effect_tags=cls["effect_tags"],
            simple_effect=cls["simple_effect"], pips=pips, source="live_classified",
        )

    return CardRecord(
        name=name, quantity=quantity, type=type_, cmc=None, power_num=None, toughness_num=None,
        primary_role=None, effect_tags=[], simple_effect=None, pips={}, source="unknown",
    )


def _has_any_tag(effect_tags: list[str], tagset: set[str]) -> bool:
    return bool(set(effect_tags) & tagset)


def build_deck_profile(records: list[CardRecord]) -> dict:
    """Baut aus klassifizierten Karten ein Profil im selben Feld-Schema wie
    deck_profiles.csv (_DECK_PROFILE_FIELDS), plus Manakurven-Histogramme und
    Kreatur-P/T-Statistiken (wie dashboard_data.json)."""

    def qty_where(pred) -> float:
        return float(sum(r.quantity for r in records if pred(r)))

    deck_size = int(sum(r.quantity for r in records))

    nonland = [r for r in records if r.type != "Land"]
    cmc_pairs = [(r.cmc, r.quantity) for r in nonland if r.cmc is not None]
    cmc_vals = np.array([v for v, _ in cmc_pairs], dtype=float)
    cmc_w = np.array([w for _, w in cmc_pairs], dtype=float)

    profile = dict(
        deck_size=deck_size,
        n_lands=qty_where(lambda r: r.type == "Land"),
        n_creatures=qty_where(lambda r: r.type == "Creature"),
        n_artifacts=qty_where(lambda r: r.type == "Artifact"),
        n_enchantments=qty_where(lambda r: r.type == "Enchantment"),
        n_instants=qty_where(lambda r: r.type == "Instant"),
        n_sorceries=qty_where(lambda r: r.type == "Sorcery"),
        n_planeswalkers=qty_where(lambda r: r.type == "Planeswalker"),
        n_ramp=qty_where(lambda r: r.primary_role == "Ramp"),
        n_card_advantage=qty_where(lambda r: r.primary_role == "CardAdvantage"),
        n_interaction_total=qty_where(lambda r: r.primary_role == "Interaction"),
        n_interaction_single_target=qty_where(lambda r: _has_any_tag(r.effect_tags, INTERACTION_SINGLE_TAGS)),
        n_boardwipes=qty_where(lambda r: _has_any_tag(r.effect_tags, INTERACTION_BOARD_TAGS)),
        n_protection=qty_where(lambda r: _has_any_tag(r.effect_tags, INTERACTION_PROTECTION_TAGS)),
        n_strategy_cards=qty_where(lambda r: r.primary_role == "Strategy"),
        avg_nonland_cmc=(float(np.average(cmc_vals, weights=cmc_w)) if len(cmc_vals) else None),
        median_nonland_cmc=(weighted_quantile(cmc_vals, cmc_w, 0.5) if len(cmc_vals) else None),
    )

    creature = [r for r in records if r.type == "Creature"]
    profile["cmc_hist_nonland"] = _hist(cmc_vals, cmc_w)
    creature_cmc_pairs = [(r.cmc, r.quantity) for r in creature if r.cmc is not None]
    profile["cmc_hist_creature"] = _hist(
        np.array([v for v, _ in creature_cmc_pairs], dtype=float),
        np.array([w for _, w in creature_cmc_pairs], dtype=float),
    )
    profile["power_stats"] = _pt_stats([(r.power_num, r.quantity) for r in creature if r.power_num is not None])
    profile["toughness_stats"] = _pt_stats(
        [(r.toughness_num, r.quantity) for r in creature if r.toughness_num is not None]
    )

    pip_totals = {c: 0.0 for c in "WUBRG"}
    for r in records:
        for c in "WUBRG":
            pip_totals[c] += r.pips.get(c, 0.0) * r.quantity
    profile["pip_totals"] = pip_totals

    unknown = [r.name for r in records if r.source == "unknown"]
    profile["_unclassified_cards"] = unknown
    profile["_n_card_copies"] = deck_size
    return profile


def _hist(values: np.ndarray, weights: np.ndarray) -> list[float]:
    if len(values) == 0 or weights.sum() == 0:
        return [0.0] * (len(CMC_EDGES) - 1)
    hist, _ = np.histogram(values, bins=CMC_EDGES, weights=weights)
    return [round(float(x), 2) for x in hist]


def _pt_stats(pairs: list[tuple[float, int]]) -> dict | None:
    if not pairs:
        return None
    v = np.array([p for p, _ in pairs], dtype=float)
    w = np.array([q for _, q in pairs], dtype=float)
    return dict(
        min=float(v.min()), p25=weighted_quantile(v, w, 0.25), median=weighted_quantile(v, w, 0.5),
        p75=weighted_quantile(v, w, 0.75), max=float(v.max()),
    )


_COMPARE_FIELDS = [
    # v4.79.0: was a mix of German and English labels leaking into the Web
    # UI's Analysis tab (deck-vs-reference comparison table) -- all-English
    # now, per UI-Feedback ("everything English, no mixed language").
    ("n_lands", "Lands"), ("n_ramp", "Ramp"), ("n_card_advantage", "Card Advantage"),
    ("n_interaction_total", "Interaction (total)"), ("n_boardwipes", "Board Wipes"),
    ("n_protection", "Protection"), ("n_strategy_cards", "Strategy Cards"),
    ("n_creatures", "Creatures"), ("avg_nonland_cmc", "Avg. Mana Value (Nonland)"),
]


@dataclass
class AnalysisResult:
    identity_slug: str | None
    tags: list[str]
    basis: str
    deck_profile: dict
    reference_composition: dict
    comparison: list[dict] = field(default_factory=list)
    unclassified_cards: list[str] = field(default_factory=list)
    report_text: str = ""


class DeckAnalyzer:
    def __init__(self, model: AverageDeckModel, lookup: CardLookup):
        self.model = model
        self.lookup = lookup

    @classmethod
    def load(cls, data_dir: Path | str = DATA_DIR) -> "DeckAnalyzer":
        data_dir = Path(data_dir)
        model = AverageDeckModel.load(output_dir=str(data_dir))
        lookup = CardLookup(data_dir / "unique_cards_classified.csv")
        return cls(model, lookup)

    def classify_decklist(self, decklist: list[dict]) -> list[CardRecord]:
        return [
            classify_uploaded_card(
                name=entry["name"], quantity=int(entry.get("quantity", 1)), lookup=self.lookup,
                mana_cost=entry.get("mana_cost"), type_=entry.get("type"),
                oracle_text=entry.get("oracle_text"), power=entry.get("power"), toughness=entry.get("toughness"),
            )
            for entry in decklist
        ]

    def analyze(
        self,
        decklist: list[dict],
        identity_slug: str | None = None,
        tags: list[str] | None = None,
        combine_mode: str = "mean",
    ) -> AnalysisResult:
        tags = tags or []
        records = self.classify_decklist(decklist)
        profile = build_deck_profile(records)

        resolved_identity = identity_slug or detect_identity_slug(profile["pip_totals"]) or "colorless"
        ref = self.model.estimate_composition(resolved_identity, tags, combine_mode=combine_mode)

        comparison = []
        for field_key, label in _COMPARE_FIELDS:
            observed = profile.get(field_key)
            expected = ref.get(field_key)
            if observed is None or expected is None:
                continue
            diff = observed - expected
            pct = (diff / expected * 100.0) if expected else None
            comparison.append(dict(
                field=field_key, label=label, observed=round(observed, 2), expected=round(expected, 2),
                diff=round(diff, 2), diff_pct=(round(pct, 1) if pct is not None else None),
            ))

        result = AnalysisResult(
            identity_slug=resolved_identity, tags=[t for t in tags], basis=ref.get("_basis", ""),
            deck_profile=profile, reference_composition=ref, comparison=comparison,
            unclassified_cards=profile.get("_unclassified_cards", []),
        )
        result.report_text = self._render_report(result, decklist)
        return result

    @staticmethod
    def _render_report(result: AnalysisResult, decklist: list[dict]) -> str:
        n_cards = len(decklist)
        lines = [
            f"Deck-Analyse ({result.deck_profile['deck_size']} Karten, {n_cards} Zeilen) "
            f"gegen Referenz {result.identity_slug}"
            + (f" + Tag(s) {', '.join(result.tags)}" if result.tags else " (nur Farbbasis)")
            + f" [{result.basis}]:",
        ]
        for row in result.comparison:
            sign = "+" if row["diff"] >= 0 else ""
            pct = f" ({sign}{row['diff_pct']:.0f} %)" if row["diff_pct"] is not None else ""
            lines.append(
                f"  {row['label']:<26} eigenes Deck: {row['observed']:>6.1f}   "
                f"Referenz: {row['expected']:>6.1f}   Diff: {sign}{row['diff']:.1f}{pct}"
            )
        if result.unclassified_cards:
            preview = ", ".join(result.unclassified_cards[:10])
            more = f" (+{len(result.unclassified_cards) - 10} weitere)" if len(result.unclassified_cards) > 10 else ""
            lines.append(
                f"  Hinweis: {len(result.unclassified_cards)} Karte(n) nicht in der Referenzdatenbank "
                f"und ohne Rohdaten (Manakosten/Oracle-Text) uebergeben, daher nicht klassifiziert: "
                f"{preview}{more}"
            )
        return "\n".join(lines)


if __name__ == "__main__":
    # Kleiner Selbsttest mit einer Handvoll bekannten Karten (kein echtes Deck).
    analyzer = DeckAnalyzer.load()
    demo_decklist = [
        {"name": "Sol Ring", "quantity": 1},
        {"name": "Rhystic Study", "quantity": 1},
        {"name": "Cyclonic Rift", "quantity": 1},
        {"name": "Swords to Plowshares", "quantity": 1},
        {"name": "Forest", "quantity": 30},
        {"name": "Island", "quantity": 10},
    ] + [{"name": "Llanowar Elves", "quantity": 1}] * 1
    res = analyzer.analyze(demo_decklist, tags=["Ramp"])
    print(f"Kartendatenbank geladen: {len(analyzer.lookup)} Referenzkarten")
    print(res.report_text)
