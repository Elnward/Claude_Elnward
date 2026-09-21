"""Tag-Normalisierung: fasst exotische / sehr kleine EDHREC-Tags (oft Universes-Beyond-
oder reine Kreaturtyp-Tags mit sehr wenigen Decks) unter etablierten Archetyp-Namen
zusammen, damit die gepoolte Strategie-Statistik genug Datenbasis pro Tag hat.

Prinzip:
- Alle reinen Kreaturtyp-("Tribal")-Tags -> "Tribal" (im Datensatz hat KEIN einzelner
  Kreaturtyp-Tag mehr als 6 Decks; als eigene Kategorie waeren sie statistisch nicht
  aussagekraeftig genug, gepoolt aber schon).
- Offensichtliche Synonyme/Naheliegendes zusammenlegen (z.B. "Historic"+"Legends").
- Alles andere bleibt unveraendert (auch kleine, aber inhaltlich eigenstaendige Tags
  wie "Storm" oder "Infect" bleiben eigene Kategorien -- das sind etablierte, nicht
  exotische Archetypen, auch mit wenigen Decks in dieser Stichprobe).
"""
from __future__ import annotations

CANONICAL_TAG_MAP: dict[str, str] = {
    # --- reine Kreaturtyp-/Tribal-Tags -> Tribal ------------------------------------
    "Elves": "Tribal", "Eldrazi": "Tribal", "Angels": "Tribal", "Demons": "Tribal",
    "Humans": "Tribal", "Dinosaurs": "Tribal", "Goblins": "Tribal", "Zombies": "Tribal",
    "Vampires": "Tribal", "Dragons": "Tribal", "Faeries": "Tribal", "Birds": "Tribal",
    "Cats": "Tribal", "Allies": "Tribal", "Elementals": "Tribal", "Phyrexians": "Tribal",
    "Rats": "Tribal", "Saprolings": "Tribal", "Squirrels": "Tribal", "Wizards": "Tribal",
    "Wolves": "Tribal", "Wraiths": "Tribal", "Apes": "Tribal", "Bears": "Tribal",
    "Constructs": "Tribal", "Dogs": "Tribal", "Dwarves": "Tribal", "Gods": "Tribal",
    "Halflings": "Tribal", "Horrors": "Tribal", "Illusions": "Tribal", "Knights": "Tribal",
    "Lhurgoyfs": "Tribal", "Lizards": "Tribal", "Merfolk": "Tribal", "Mice": "Tribal",
    "Otters": "Tribal", "Pirates": "Tribal", "Rabbits": "Tribal", "Rogues": "Tribal",
    "Spiders": "Tribal", "Spirits": "Tribal", "Treefolk": "Tribal", "Werewolves": "Tribal",
    "Ninjas": "Tribal", "Soldiers": "Tribal", "Tyranids": "Tribal",
    "Persistent Petitioners": "Tribal",
    # Universes-Beyond-Themenmechaniken ohne etabliertes MTG-Aequivalent -> naechst-
    # aehnlicher etablierter Archetyp (jeweils n=1-2 Decks in dieser Stichprobe).
    "Time Lords": "Tribal",                 # Doctor Who, kreaturtyp-basiert
    "Spacecraft": "Vehicles",               # Transformers-artige Fahrzeug-Subtypen
    "Earthbending": "Counters Matter",      # Avatar: setzt ueberwiegend +1/+1-Counter
    "Waterbending": "Card Draw",            # Avatar: ueberwiegend Card-Selection-Effekte
    "Firebending": "Burn",                  # Avatar: ueberwiegend Schadenseffekte
    "Airbending": "Tempo",                  # Avatar: ueberwiegend Bounce/Tempo-Effekte
    # --- Synonyme / naheliegende Zusammenlegung -------------------------------------
    "Legends": "Historic",                  # beide = "legendaere Karten sind relevant"
    "Sacrifice": "Aristocrats",             # Sac-Outlets sind Kernbestandteil von Aristocrats
    "Counters Matter": "Counters Matter",   # Sammelbecken fuer generische (nicht +1/+1) Counter
    "Charge Counters": "Counters Matter",
    "Experience Counters": "Counters Matter",
    "Rad Counters": "Counters Matter",
    "-1/-1 Counters": "Counters Matter",
    "Modified Creatures": "Counters Matter",
    "Self-Discard": "Discard",
    "Self-Damage": "Self-Damage",
    "Toolbox": "Toolbox",
    "Curses": "Pillow Fort",                # Curse-Auren sind fast immer Pillow-Fort-artig
    "Shrines": "Enchantress",               # Shrines = Enchantment-Subtyp-Payoff
    "Sagas": "Enchantress",
    "Dungeon": "Toolbox",                   # sehr kleines Sample, naechstliegend: Value-Toolbox
    "The Ring": "Voltron",                  # Ring-tempts = Anthem/Equipment-aehnlicher Solo-Payoff
    "Lessons": "Spellslinger",              # Learn/Lesson-Mechanik = Spells-Matter-Value
}


def normalize_tag(raw_tag: str) -> str:
    if not isinstance(raw_tag, str):
        return "Unbekannt"
    return CANONICAL_TAG_MAP.get(raw_tag.strip(), raw_tag.strip())
