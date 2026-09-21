"""archetype_profile -- Analyse-Prototyp fuer Commander Goldfish.

Bildet die Kartenklassifikation + statistischen Referenzprofile aus 1.585 EDHREC-
Average-Decks (32 Farbidentitaeten x Strategie-Tags) ab und stellt darauf aufbauend
eine Funktion bereit, mit der beliebige hochgeladene Decklisten gegen diese Referenz
analysiert werden koennen.

Oeffentliche API (siehe README.md fuer Details/Beispiele):
    - classify.classify_card(name, oracle_text, type_) -> dict
    - mana_utils.parse_pips(mana_cost) -> dict
    - reference_model.AverageDeckModel.load() -> Modell fuer reine Referenz-Abfragen
      (Identitaet x Tag -> geschaetzte Deck-Komposition/Manakurve, ohne eigene Decklist)
    - deck_analyzer.DeckAnalyzer.load() -> Analyse EINER konkreten hochgeladenen Decklist
      gegen die Referenz (das ist der neue Baustein fuer die App-Integration)

Datenbasis liegt unter data/ (aus der EDHREC-Bracket3-Pipeline unter
"Training data/auswertung_v1" exportiert) und wird zur Laufzeit nur gelesen -- kein
Netzwerkzugriff, kein erneuter EDHREC/Scryfall-Abruf.
"""
from .reference_model import AverageDeckModel  # noqa: F401
from .deck_analyzer import DeckAnalyzer, CardLookup, AnalysisResult  # noqa: F401
from .identity_colors import COLORS_TO_SLUG, SLUG_TO_LABEL, normalize_color_identity  # noqa: F401

__all__ = [
    "AverageDeckModel", "DeckAnalyzer", "CardLookup", "AnalysisResult",
    "COLORS_TO_SLUG", "SLUG_TO_LABEL", "normalize_color_identity",
]
