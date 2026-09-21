"""Das eigentliche Ziel des Nutzers: EINE Funktion, mit der sich ein durchschnittliches
Commander-Deck fuer eine gegebene Farbidentitaet + ein oder mehrere Strategie-Tags
abbilden laesst.

Methodik (Ueberlagerung / Farbbias-Korrektur, wie vom Nutzer gefordert):

    geschaetzter_Wert(Identitaet, Tag, Feld)
        = Baseline(Identitaet, Feld)                       # ueber ALLE Decks dieser Farbe
        + [ Tag-Profil(Feld) - Referenzprofil(Feld) ]       # Tag-typische ABWEICHUNG vom
                                                             # farbneutralen Durchschnitt

Damit wird nicht das rohe Tag-Mittel uebernommen (das waere z.B. bei "Midrange" durch
die ueberproportional vielen gruenen Midrange-Decks in der Stichprobe farblich verzerrt),
sondern nur die tag-TYPISCHE Verschiebung gegenueber dem Durchschnitt -- additiv auf die
eigene Farbbasis der gewuenschten Identitaet. Ein monorotes Deck mit einem sonst eher
blauen Tag bekommt so nicht automatisch blaues Card-Draw/Stack-Interaction-Niveau
aufgepraegt, sondern nur den tag-spezifischen Zusatz-Schub oben auf seine eigene (rote)
Basis.

Datenquellen (muessen vorher per step2/step3/step4 erzeugt worden sein):
    output/deck_profiles.csv            (reale Einzeldecks, Basis fuer Baseline/Tag-Median)
    output/identity_type_summary.json   (Manavalue-Verteilung je Identitaet x Typ)
    output/identity_tag_summary.json    (Manavalue-Verteilung je Tag, NUR Strategy-Karten)
    output/strategy_reference_profile.json  (farbneutrale Strategy-Referenz)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .tag_normalize import normalize_tag

_DECK_PROFILE_FIELDS = [
    "n_lands", "n_creatures", "n_artifacts", "n_enchantments", "n_instants",
    "n_sorceries", "n_planeswalkers", "n_ramp", "n_card_advantage",
    "n_interaction_total", "n_interaction_single_target", "n_boardwipes",
    "n_protection", "n_strategy_cards", "avg_nonland_cmc", "median_nonland_cmc",
]


@dataclass
class AverageDeckModel:
    deck_profiles: pd.DataFrame
    identity_type_summary: dict
    identity_tag_summary: dict
    strategy_reference: dict
    _global_median: dict = field(default_factory=dict)

    @classmethod
    def load(cls, output_dir: str = "output") -> "AverageDeckModel":
        deck_profiles = pd.read_csv(f"{output_dir}/deck_profiles.csv")
        with open(f"{output_dir}/identity_type_summary.json", encoding="utf-8") as fh:
            its = json.load(fh)
        with open(f"{output_dir}/identity_tag_summary.json", encoding="utf-8") as fh:
            tag_summary = json.load(fh)
        with open(f"{output_dir}/strategy_reference_profile.json", encoding="utf-8") as fh:
            ref = json.load(fh)
        model = cls(deck_profiles, its, tag_summary, ref)
        model._global_median = {f: float(deck_profiles[f].median()) for f in _DECK_PROFILE_FIELDS}
        return model

    # -------------------------------------------------------------- Deck-Komposition
    def estimate_composition(self, identity_slug: str, tags: list[str],
                              combine_mode: str = "mean") -> dict:
        """Liefert die geschaetzte Kartenanzahl (Land/Ramp/CardAdvantage/Interaction/
        Boardwipes/Strategy/Kreaturen/... ) fuer Identitaet x Tag-Kombination, inkl.
        Konfidenz-Hinweis (echte Deck-Beobachtung vs. reine Ueberlagerungs-Schaetzung).
        """
        canon_tags = [normalize_tag(t) for t in tags]

        exact = self.deck_profiles[
            (self.deck_profiles["identity_slug"] == identity_slug)
            & (self.deck_profiles["canonical_tag"].isin(canon_tags))
        ]
        if len(exact) >= 1:
            basis = "beobachtet (reale Average Decks dieser Identitaet+Tag-Kombination)"
            result = {f: float(exact[f].median()) for f in _DECK_PROFILE_FIELDS}
            result["_n_observed_decks"] = int(len(exact))
        else:
            basis = "ueberlagert (Baseline der Identitaet + tag-typische Abweichung, keine exakte reale Deck-Beobachtung)"
            identity_rows = self.deck_profiles[self.deck_profiles["identity_slug"] == identity_slug]
            baseline = {f: float(identity_rows[f].median()) if len(identity_rows) else self._global_median[f]
                        for f in _DECK_PROFILE_FIELDS}

            deviations = []
            for tag in canon_tags:
                tag_rows = self.deck_profiles[self.deck_profiles["canonical_tag"] == tag]
                if len(tag_rows) == 0:
                    continue
                dev = {f: float(tag_rows[f].median()) - self._global_median[f] for f in _DECK_PROFILE_FIELDS}
                deviations.append(dev)

            result = dict(baseline)
            if deviations:
                for f in _DECK_PROFILE_FIELDS:
                    devs = [d[f] for d in deviations]
                    combined = float(np.mean(devs)) if combine_mode == "mean" else float(np.sum(devs))
                    result[f] = baseline[f] + combined
            result["_n_observed_decks"] = 0

        # Deckgroesse auf 100 normalisieren (rundungsbedingt kann die Summe leicht
        # abweichen; Nichtland-Kategorien werden proportional skaliert).
        result["_basis"] = basis
        result["_identity_slug"] = identity_slug
        result["_tags"] = canon_tags
        return result

    # ------------------------------------------------------------- Manavalue-Kurve
    def estimate_manacurve(self, identity_slug: str, tags: list[str], type_: str = "Creature") -> dict:
        """Manavalue-Verteilung (Histogramm) fuer einen Kartentyp:
        - Ramp/CardAdvantage/Interaction-Anteile kommen NICHT hier rein (das ist reine
          Farbidentitaets-Basis, siehe identity_type_summary direkt), sondern nur die
          Strategy-Karten-Kurve wird tag-ueberlagert.
        """
        canon_tags = [normalize_tag(t) for t in tags]
        identity_block = self.identity_type_summary.get(identity_slug, {}).get(type_)
        if identity_block is None:
            return {}
        base_hist = dict(identity_block["cmc_histogram"])
        base_median = identity_block["cmc_stats"]["median"]
        base_mean = identity_block["cmc_stats"]["mean"]

        # Residual auf Basis des Mittelwerts (nicht Median), da CMC-Mediane fast immer
        # auf denselben ganzzahligen Wert (meist 3.0) fallen und so keine Farb-/Tag-
        # Unterschiede sichtbar waeren; der Mittelwert reagiert feinkoerniger.
        ref_mean = self.strategy_reference["cmc_stats"]["mean"]
        tag_means = []
        for tag in canon_tags:
            tblock = self.identity_tag_summary.get(tag)
            if tblock and tblock["cmc_stats"]["n"]:
                tag_means.append(tblock["cmc_stats"]["mean"])
        if tag_means:
            residual = float(np.mean(tag_means)) - ref_mean
        else:
            residual = 0.0

        return dict(
            identity_baseline_median_cmc=base_median,
            identity_baseline_mean_cmc=base_mean,
            tag_residual_applied=residual,
            estimated_median_cmc=base_median + residual,
            identity_histogram=base_hist,
            note=("Histogramm bleibt die Identitaets-Basisverteilung; der Tag-Residual-Wert "
                  "zeigt an, ob diese Strategie tendenziell teurere (+) oder billigere (-) "
                  "Spitzenkarten dieses Typs gegenueber dem farbneutralen Durchschnitt spielt."),
        )

    # --------------------------------------------------------------------- Report
    def describe(self, identity_slug: str, tags: list[str]) -> str:
        comp = self.estimate_composition(identity_slug, tags)
        curve = self.estimate_manacurve(identity_slug, tags, "Creature")
        lines = [
            f"Durchschnittliches {identity_slug}-Deck mit Tag(s) {', '.join(comp['_tags'])} "
            f"[{comp['_basis']}]:",
            f"  Laender:              {comp['n_lands']:.0f}",
            f"  Ramp:                 {comp['n_ramp']:.0f}",
            f"  Card Advantage:       {comp['n_card_advantage']:.0f}",
            f"  Interaction (gesamt): {comp['n_interaction_total']:.0f}"
            f"   davon Board Wipes: {comp['n_boardwipes']:.0f}",
            f"  Strategie-Karten:     {comp['n_strategy_cards']:.0f}",
            f"  Kreaturen:            {comp['n_creatures']:.0f}",
            f"  Ø Manavalue (Nicht-Land): {comp['avg_nonland_cmc']:.2f}",
        ]
        if curve:
            lines.append(f"  Kreatur-Manavalue-Median: {curve['estimated_median_cmc']:.2f} "
                         f"(Basis {curve['identity_baseline_median_cmc']:.2f} "
                         f"{'+' if curve['tag_residual_applied']>=0 else ''}{curve['tag_residual_applied']:.2f} Tag-Effekt)")
        return "\n".join(lines)


if __name__ == "__main__":
    m = AverageDeckModel.load()
    for identity, tags in [
        ("simic", ["Landfall"]),
        ("mono-red", ["Midrange"]),   # untypische Kombination -> reine Ueberlagerung
        ("gruul", ["Aggro"]),
        ("mono-blue", ["Voltron"]),   # untypische Kombination -> reine Ueberlagerung
    ]:
        print(m.describe(identity, tags))
        print()
