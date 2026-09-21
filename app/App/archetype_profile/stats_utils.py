"""Gemeinsame Statistik-Hilfsfunktionen: gewichteter Median/Quantile/Histogramm.
Gewicht = `quantity` (wie oft die Karte ueber alle betrachteten Decks gespielt wurde),
NICHT einfacher Kartendurchschnitt -- das ist bewusst so gewaehlt, damit haeufig
gespielte Karten (z.B. Sol Ring in fast jedem Deck) staerker in die Verteilung
einfliessen als eine Karte, die nur in einem einzigen Deck einmal auftaucht.
"""
from __future__ import annotations

import numpy as np


def weighted_quantile(values, weights, q):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    mask = ~np.isnan(values)
    values, weights = values[mask], weights[mask]
    if len(values) == 0:
        return np.nan
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = np.cumsum(w) - 0.5 * w
    cw /= w.sum()
    return float(np.interp(q, cw, v))


def weighted_stats(values, weights) -> dict:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    mask = ~np.isnan(values)
    v, w = values[mask], weights[mask]
    if len(v) == 0 or w.sum() == 0:
        return dict(n=0, min=np.nan, p25=np.nan, median=np.nan, mean=np.nan,
                    p75=np.nan, max=np.nan, std=np.nan)
    mean = float(np.average(v, weights=w))
    var = float(np.average((v - mean) ** 2, weights=w))
    return dict(
        n=int(w.sum()),
        min=float(v.min()),
        p25=weighted_quantile(v, w, 0.25),
        median=weighted_quantile(v, w, 0.5),
        mean=mean,
        p75=weighted_quantile(v, w, 0.75),
        max=float(v.max()),
        std=var ** 0.5,
    )


def weighted_histogram(values, weights, bins) -> dict:
    """Gibt ein einfaches Histogramm (Bin-Kanten -> Anteil) als dict zurueck --
    das ist die tatsaechliche Verteilungsfunktion (keine reine Kurve): jeder Bin
    traegt den gewichteten Anteil der Karten, die in dieses Manavalue-/Statwert-
    Intervall fallen."""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    mask = ~np.isnan(values)
    v, w = values[mask], weights[mask]
    if len(v) == 0:
        return {}
    hist, edges = np.histogram(v, bins=bins, weights=w)
    total = hist.sum()
    if total == 0:
        return {}
    shares = hist / total
    return {f"{edges[i]:g}-{edges[i+1]:g}": float(shares[i]) for i in range(len(shares))}


def weighted_value_counts(labels, weights, top_n=12) -> dict:
    """Gewichtete Haeufigkeitsverteilung fuer kategoriale Felder (z.B. effect_tags)."""
    from collections import defaultdict
    acc = defaultdict(float)
    for lab, w in zip(labels, weights):
        if not isinstance(lab, str) or not lab:
            continue
        for tag in lab.split(";"):
            tag = tag.strip()
            if tag:
                acc[tag] += w
    total = sum(acc.values())
    if total == 0:
        return {}
    ranked = sorted(acc.items(), key=lambda kv: -kv[1])[:top_n]
    return {tag: round(val / total, 4) for tag, val in ranked}
