"""Regelbasierte Klassifikation einer MTG-Karte in Rolle + vereinfachten Effekt-Tags.

Prioritaet fuer die *eine* Haupt-Rolle (wie im Plan festgelegt):
    Interaction > Ramp > CardAdvantage > Strategy

Eine Karte kann trotzdem mehrere `effect_tags` tragen (z.B. Ramp *und* CardAdvantage
gleichzeitig, siehe Wachtwood Elemental o.ae.) -- die `primary_role` entscheidet nur,
in welchem Topf die Karte fuer die Farbidentitaets-/Strategie-Statistik landet.
"""
from __future__ import annotations

import re

ROLE_PRIORITY = ["Interaction", "Ramp", "CardAdvantage", "Strategy"]


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text) for p in patterns)


# ---------------------------------------------------------------------------
# Kuratierte Overrides fuer die haeufigsten / komplexesten Karten (Pareto-Ansatz:
# ~ Top 300-500 nach Gesamt-Stueckzahl ueber alle Decks). Format:
#   name -> dict(role=..., effect_tags=[...], simple_effect="...", halbwertszeit=...)
# `halbwertszeit` ist eine grobe 0-1 Einschaetzung, wie *zuverlaessig/oft* der
# vereinfachte Effekt pro Zug tatsaechlich eintritt (1.0 = fast garantiert,
# 0.3 = eher selten/bedingt). Nur informativ, fliesst nicht in die Kern-Statistik
# ein, dient aber als Metadatum fuer spaetere Simulationszwecke.
CURATED_OVERRIDES: dict[str, dict] = {
    "Rhystic Study": dict(
        role="CardAdvantage",
        effect_tags=["draw_conditional_per_opponent_spell", "tax_effect"],
        simple_effect="every opponent turn: draw 1 card for each opponent spell cast, unless that opponent pays {1}",
        halbwertszeit=0.55,
    ),
    "Smothering Tithe": dict(
        role="Ramp",
        effect_tags=["treasure_conditional_per_opponent_land", "tax_effect"],
        simple_effect="every opponent turn: create 1 Treasure for each opponent land play, unless that opponent pays {2}",
        halbwertszeit=0.6,
    ),
    "Mystic Remora": dict(
        role="CardAdvantage",
        effect_tags=["draw_conditional_per_opponent_spell", "tax_effect"],
        simple_effect="each opponent noncreature spell: draw 1 card unless they pay {4}; fades after your first turn",
        halbwertszeit=0.35,
    ),
    "Esper Sentinel": dict(
        role="CardAdvantage",
        effect_tags=["draw_conditional_per_opponent_spell", "tax_effect"],
        simple_effect="each opponent noncreature spell: draw 1 card unless they pay {X} (X = Sentinel's power)",
        halbwertszeit=0.5,
    ),
    "Cyclonic Rift": dict(
        role="Interaction",
        effect_tags=["bounce_single", "bounce_board_overload"],
        simple_effect="{1}{U}: bounce 1 target nonland permanent; {6}{U} overload: bounce all opponents' nonland permanents",
        halbwertszeit=1.0,
    ),
    "Sol Ring": dict(
        role="Ramp",
        effect_tags=["mana_rock_fixed"],
        simple_effect="{T}: add {C}{C} (net +1 mana per turn from turn 1)",
        halbwertszeit=1.0,
    ),
    "Demonic Tutor": dict(
        role="CardAdvantage",
        effect_tags=["tutor_any_card"],
        simple_effect="search library for any card, put into hand",
        halbwertszeit=1.0,
    ),
    "Swords to Plowshares": dict(
        role="Interaction",
        effect_tags=["removal_single_creature_exile"],
        simple_effect="exile target creature; owner gains life equal to its power",
        halbwertszeit=1.0,
    ),
    "Dockside Extortionist": dict(
        role="Ramp",
        effect_tags=["treasure_burst_scaling"],
        simple_effect="on ETB: create Treasures equal to the number of artifacts/enchantments opponents control (one-time burst)",
        halbwertszeit=1.0,
    ),
    "Skullclamp": dict(
        role="CardAdvantage",
        effect_tags=["draw_on_creature_death", "equipment"],
        simple_effect="equipped creature dies: draw 2 cards (repeatable engine with token generators)",
        halbwertszeit=0.7,
    ),
    "Toxic Deluge": dict(
        role="Interaction",
        effect_tags=["removal_board_scalable"],
        simple_effect="pay X life: all creatures get -X/-X this turn (scalable board wipe)",
        halbwertszeit=1.0,
    ),

    # -------------------------------------------------------------------
    # v4.71.0-Nachtrag: erste systematische Erweiterung nach der vom Nutzer
    # praezisierten Methodik ("von der gesamten moeglichen Datengrundlage
    # abhaengen"). Kandidaten wurden per Skript ermittelt: alle 8.445
    # Karten aus deck_cards_slim.csv nach Gesamt-Stueckzahl ueber alle 1.585
    # Decks sortiert, dann die, bei denen weder CURATED_OVERRIDES noch die
    # Regel-Engine (Stage 1) etwas anderes als den generischen Fallback
    # ("unclassified"/"vanilla_or_unclassified_body") liefern. Vor dem
    # Kuratieren wurden dabei 5 echte, allgemeine Regel-Luecken gefunden und
    # als neue _RAMP_RULES/_STRATEGY_RULES-Muster behoben (siehe dort:
    # land_recursion, trigger_doubler, clone_effect, extra_untap_steps,
    # damage_multiplier, sowie die "with mana value N or less"-Erweiterung
    # von graveyard_recursion) - diese treffen zusammen bereits 102 weitere
    # Karten (u.a. Sun Titan, Seedborn Muse, Panharmonicon, Phyrexian
    # Metamorph), OHNE dass dafuer Einzelkarten-Overrides noetig waren.
    # Erst danach wurden die verbliebenen Top-Kandidaten (>= 30 Kopien
    # gesamt) einzeln hier kuratiert - 74 neue Eintraege, macht 85 von den
    # angepeilten 300-500. Volle Methodik/Statusbericht:
    # Docs/opponent_model_calibration_v4_71_0.md.
    "Deflecting Swat": dict(
        role="Interaction",
        effect_tags=["redirect_free_with_commander"],
        simple_effect="if you control a commander: free spell, choose new targets for a spell or ability (protects your permanents / redirects removal)",
        halbwertszeit=0.4,
    ),
    "Victimize": dict(
        role="Strategy",
        effect_tags=["reanimate_two_for_one_sacrifice"],
        simple_effect="sacrifice 1 creature, return 2 creatures from graveyard to battlefield (net +1 body, one-time)",
        halbwertszeit=1.0,
    ),
    "Rat Colony": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "unlimited_copies"],
        simple_effect="gets +1/+0 per other Rat you control; deck may run unlimited copies (goes wide as a single 'card')",
        halbwertszeit=0.5,
    ),
    "Azusa, Lost but Seeking": dict(
        role="Ramp",
        effect_tags=["extra_land_drop"],
        simple_effect="play up to 2 additional lands each turn (ramp engine while it survives)",
        halbwertszeit=0.7,
    ),
    "The Ozolith": dict(
        role="Strategy",
        effect_tags=["counters_matter", "counter_salvage"],
        simple_effect="saves +1/+1 (or other) counters from your creatures that leave the battlefield, moves them to a new creature at combat",
        halbwertszeit=0.5,
    ),
    "Mystic Forge": dict(
        role="CardAdvantage",
        effect_tags=["play_from_top_of_library"],
        simple_effect="look at the top card any time; cast artifact/colorless spells from the top of your library (extra value if deck is artifact-heavy)",
        halbwertszeit=0.5,
    ),
    "Return of the Wildspeaker": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling_by_power"],
        simple_effect="draw cards equal to your greatest non-Human power, or pump non-Human creatures +3/+3 (modal)",
        halbwertszeit=0.9,
    ),
    "Sylvan Library": dict(
        role="CardAdvantage",
        effect_tags=["draw_selection_paid"],
        simple_effect="each draw step: see 2 extra cards, keep any by paying 4 life each (card selection engine)",
        halbwertszeit=0.9,
    ),
    "Craterhoof Behemoth": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="on ETB: your creatures get +X/+X and trample, X = number of creatures you control (frequent go-wide finisher/wincon)",
        halbwertszeit=1.0,
    ),
    "Viscera Seer": dict(
        role="Strategy",
        effect_tags=["free_sac_outlet"],
        simple_effect="{T}, sacrifice a creature: scry 1 (repeatable free sacrifice outlet)",
        halbwertszeit=0.7,
    ),
    "Dispatch": dict(
        role="Interaction",
        effect_tags=["removal_conditional_metalcraft"],
        simple_effect="tap target creature, or exile it if you control 3+ artifacts (removal_single_exile equivalent, condition-gated)",
        halbwertszeit=0.7,
    ),
    "Rishkar's Expertise": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling_by_power", "free_spell_follow_up"],
        simple_effect="draw cards equal to your greatest creature's power, then cast a spell with mana value 5 or less for free",
        halbwertszeit=0.9,
    ),
    "Chandra's Ignition": dict(
        role="Interaction",
        effect_tags=["removal_board_via_creature_power"],
        simple_effect="one creature you control deals damage equal to its power to every other creature and each opponent (board wipe + burn, needs a big creature)",
        halbwertszeit=0.6,
    ),
    "Wild Growth": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="enchanted land taps for 1 extra {G} (net +1 mana per turn, aura-based ramp)",
        halbwertszeit=0.85,
    ),
    "Etali, Primal Storm": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff", "free_spells_from_exile"],
        simple_effect="whenever it attacks: exile the top card of each player's library, may cast any of them for free (huge value if it connects)",
        halbwertszeit=0.5,
    ),
    "Anger": dict(
        role="Strategy",
        effect_tags=["graveyard_static_ability"],
        simple_effect="grants haste to your creatures from the graveyard as long as you control a Mountain (passive, no need to cast)",
        halbwertszeit=0.75,
    ),
    "Unnatural Growth": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="doubles power and toughness of your creatures at the start of each combat (repeatable combat finisher)",
        halbwertszeit=0.7,
    ),
    "Living Death": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_symmetric"],
        simple_effect="all players exile their graveyard creatures, sacrifice their creatures, then put the exiled ones onto the battlefield (symmetric mass reanimation swing)",
        halbwertszeit=1.0,
    ),
    "Grand Abolisher": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="during your turn, opponents can't cast spells or activate artifact/creature/enchantment abilities (protects your turn's plays)",
        halbwertszeit=0.6,
    ),
    "Terror of the Peaks": dict(
        role="Strategy",
        effect_tags=["etb_ping_payoff"],
        simple_effect="flying; whenever another creature you control enters, deals damage equal to its power to any target (repeatable removal/burn engine)",
        halbwertszeit=0.65,
    ),
    "Mizzix's Mastery": dict(
        role="CardAdvantage",
        effect_tags=["free_spell_from_graveyard"],
        simple_effect="cast a free copy of an instant/sorcery from your graveyard (overload: do it for every eligible card at once)",
        halbwertszeit=0.5,
    ),
    "Reconnaissance": dict(
        role="Interaction",
        effect_tags=["combat_protection_free"],
        simple_effect="{0}: remove and untap one of your attacking creatures from combat (free repeated combat protection)",
        halbwertszeit=0.55,
    ),
    "All Will Be One": dict(
        role="Strategy",
        effect_tags=["counters_matter", "counter_damage_payoff"],
        simple_effect="whenever you add counters to a permanent or player, deals that much damage to an opponent/their creature/planeswalker (counters-matter payoff)",
        halbwertszeit=0.5,
    ),
    "Cyberdrive Awakener": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="flying; other artifact creatures you control have flying; on ETB, turns your noncreature artifacts into 4/4s for the turn (one-time wide swing)",
        halbwertszeit=0.6,
    ),
    "Aetherize": dict(
        role="Interaction",
        effect_tags=["bounce_board_combat_trick"],
        simple_effect="return all attacking creatures to their owners' hands (one-sided combat blowout when you're being attacked)",
        halbwertszeit=0.9,
    ),
    "Second Harvest": dict(
        role="Strategy",
        effect_tags=["token_creation", "token_or_counter_doubler"],
        simple_effect="creates a copy of every token you control (one-time token count doubler)",
        halbwertszeit=0.8,
    ),
    "Finale of Devastation": dict(
        role="CardAdvantage",
        effect_tags=["tutor_conditional", "team_pump_finisher"],
        simple_effect="search library/graveyard for a creature with mana value X or less, put it onto the battlefield; at X>=10 also pumps your team and gives haste (scalable finisher/tutor)",
        halbwertszeit=0.9,
    ),
    "Sigarda's Aid": dict(
        role="Strategy",
        effect_tags=["voltron_aura_equipment"],
        simple_effect="cast Auras/Equipment at instant speed; auto-attaches Equipment on ETB (Voltron support)",
        halbwertszeit=0.5,
    ),
    "Flashback": dict(
        role="CardAdvantage",
        effect_tags=["flashback_grant"],
        simple_effect="target instant/sorcery in your graveyard gains flashback (at its own mana cost) until end of turn (one-time graveyard recast enabler)",
        halbwertszeit=0.6,
    ),
    "Ghalta, Primal Hunger": dict(
        role="Strategy",
        effect_tags=["cost_reduction_by_board_state"],
        simple_effect="costs {X} less where X = total power of your creatures (often cast for very little); trample finisher",
        halbwertszeit=0.75,
    ),
    "Serra Ascendant": dict(
        role="Strategy",
        effect_tags=["lifegain", "threshold_pump"],
        simple_effect="lifelink; gets +5/+5 and flying once you have 30+ life (early game 1-drop that snowballs)",
        halbwertszeit=0.5,
    ),
    "Splendid Reclamation": dict(
        role="Ramp",
        effect_tags=["land_recursion_mass"],
        simple_effect="return all land cards from your graveyard to the battlefield tapped (one-time mass ramp, best after land-sac/fetch effects)",
        halbwertszeit=1.0,
    ),
    "Soul's Attendant": dict(
        role="Strategy",
        effect_tags=["lifegain", "etb_ping_payoff"],
        simple_effect="whenever another creature enters, may gain 1 life (small incremental lifegain engine)",
        halbwertszeit=0.6,
    ),
    "Howling Mine": dict(
        role="CardAdvantage",
        effect_tags=["group_hug_or_symmetric_draw"],
        simple_effect="each player draws an extra card on their draw step (symmetric card advantage, favors decks that use extra cards best)",
        halbwertszeit=0.85,
    ),
    "Accursed Marauder": dict(
        role="Interaction",
        effect_tags=["removal_edict_symmetric"],
        simple_effect="on ETB, each player sacrifices a creature of their choice (one-time symmetric edict)",
        halbwertszeit=1.0,
    ),
    "Utopia Sprawl": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="enchanted Forest taps for 1 extra mana of a chosen color (net +1 mana per turn, aura-based ramp)",
        halbwertszeit=0.85,
    ),
    "Sanctum Weaver": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="taps for X mana of any one color, X = number of enchantments you control (scales with enchantment count)",
        halbwertszeit=0.6,
    ),
    "Mechanized Production": dict(
        role="Strategy",
        effect_tags=["token_creation", "alt_win_condition"],
        simple_effect="each upkeep, creates a copy of the enchanted artifact; alternate win condition at 8 copies of the same name",
        halbwertszeit=0.7,
    ),
    "Peregrine Drake": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork", "etb_ramp_burst"],
        simple_effect="flying; on ETB, untaps up to 5 lands (mana-positive creature, common combo piece with reanimation/blink)",
        halbwertszeit=1.0,
    ),
    "Return the Favor": dict(
        role="Interaction",
        effect_tags=["spell_copy_or_redirect"],
        simple_effect="modal: copy a target spell/ability and/or redirect a single-target spell/ability (flexible counter-magic-adjacent interaction)",
        halbwertszeit=0.5,
    ),
    "Manifold Key": dict(
        role="Strategy",
        effect_tags=["untap_utility"],
        simple_effect="untap another artifact, or make a creature unblockable for the turn (flexible utility, situational)",
        halbwertszeit=0.4,
    ),
    "High Fae Trickster": dict(
        role="Strategy",
        effect_tags=["flash_enabler"],
        simple_effect="flash, flying; lets you cast all your spells at instant speed (flexibility/ambush engine)",
        halbwertszeit=0.5,
    ),
    "Crackle with Power": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="deals 5xX damage split among up to X targets (scalable burn/removal, X = mana invested)",
        halbwertszeit=0.85,
    ),
    "High Tide": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="until end of turn, tapping an Island for mana adds one extra {U} (temporary mono-blue ritual/combo enabler)",
        halbwertszeit=0.3,
    ),
    "Underworld Breach": dict(
        role="CardAdvantage",
        effect_tags=["graveyard_recasting_engine"],
        simple_effect="every nonland card in your graveyard can be cast via escape (its mana cost + exile 3 other graveyard cards); sacrifices itself at end of turn (powerful one-turn graveyard combo enabler)",
        halbwertszeit=0.5,
    ),
    "Grasp of Fate": dict(
        role="Interaction",
        effect_tags=["removal_multi_exile"],
        simple_effect="on ETB, exiles up to one nonland permanent from each opponent until this leaves the battlefield (multi-target O-Ring effect)",
        halbwertszeit=1.0,
    ),
    "Ashaya, Soul of the Wild": dict(
        role="Strategy",
        effect_tags=["lands_matter_synergy"],
        simple_effect="power/toughness equal to your land count; your other creatures are also Forests (huge landfall/ramp synergy enabler)",
        halbwertszeit=0.5,
    ),
    "Training Grounds": dict(
        role="Strategy",
        effect_tags=["cost_reduction"],
        simple_effect="your creatures' activated abilities cost {2} less, down to a minimum of {1} (value engine for ability-heavy decks)",
        halbwertszeit=0.6,
    ),
    "Eerie Ultimatum": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="return any number of differently-named permanent cards from your graveyard to the battlefield (one-time mass reanimation swing)",
        halbwertszeit=1.0,
    ),
    "Exquisite Blood": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="whenever an opponent loses life, you gain that much life (drain/combo piece, especially with Sanguine Bond-type effects)",
        halbwertszeit=0.5,
    ),
    "Kediss, Emberclaw Familiar": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="whenever your commander deals combat damage to an opponent, deals that much damage to each other opponent too (multiplies commander damage)",
        halbwertszeit=0.4,
    ),
    "Ram Through": dict(
        role="Interaction",
        effect_tags=["removal_via_fight"],
        simple_effect="your creature deals damage equal to its power to a creature you don't control (fight-style removal; excess damage tramples over if your creature has trample)",
        halbwertszeit=0.8,
    ),
    "Kodama of the East Tree": dict(
        role="Ramp",
        effect_tags=["free_permanent_cheat"],
        simple_effect="whenever another permanent you control enters, you may put a cheaper-or-equal permanent from hand onto the battlefield free (cascading value/ramp engine)",
        halbwertszeit=0.55,
    ),
    "Improvisation Capstone": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile", "recurring_value"],
        simple_effect="exile cards from your library until total mana value >=4, cast any for free; recasts itself for free at each of your first main phases after the first resolution",
        halbwertszeit=0.6,
    ),
    "Inspiring Statuary": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="your nonartifact spells gain improvise (artifacts help pay for them) - effectively extra mana from your artifact count",
        halbwertszeit=0.6,
    ),
    "Elesh Norn, Grand Cenobite": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher", "removal_board"],
        simple_effect="your other creatures get +2/+2, opponents' creatures get -2/-2 (one-sided anthem + soft board wipe)",
        halbwertszeit=0.9,
    ),
    "Clever Concealment": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="phase out any number of your nonland permanents (temporary protection from removal/combat/wipes, convoke to cast cheaply)",
        halbwertszeit=0.6,
    ),
    "Avatar's Wrath": dict(
        role="Interaction",
        effect_tags=["removal_board_temporary"],
        simple_effect="exile all creatures except one you choose (owners may recast for {2}); opponents restricted to casting only from hand until your next turn (temporary board wipe + tempo lock)",
        halbwertszeit=0.75,
    ),
    "Dauthi Voidwalker": dict(
        role="Interaction",
        effect_tags=["graveyard_hate_exile", "steal_effect"],
        simple_effect="cards that would go to an opponent's graveyard are exiled instead (with a void counter); sacrifice this creature to cast one of those exiled cards for free (graveyard hate + one-time value)",
        halbwertszeit=0.6,
    ),
    "Imp's Mischief": dict(
        role="Interaction",
        effect_tags=["redirect_paid"],
        simple_effect="change the target of a single-target spell; costs life equal to its mana value (protects your permanents / redirects removal)",
        halbwertszeit=0.45,
    ),
    "Peer into the Abyss": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling_by_library", "life_cost_payoff"],
        simple_effect="draw cards equal to half your library, lose half your life (massive one-time card draw at a steep life cost)",
        halbwertszeit=1.0,
    ),
    "Rise of the Dark Realms": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="put every creature card from every graveyard onto the battlefield under your control (extreme one-time mass reanimation swing)",
        halbwertszeit=1.0,
    ),
    "Suture Priest": dict(
        role="Strategy",
        effect_tags=["lifegain", "etb_ping_payoff"],
        simple_effect="gain 1 life when your creatures enter; opponents lose 1 life when their creatures enter (incremental lifegain/drain engine, strong vs token strategies)",
        halbwertszeit=0.6,
    ),
    "Aven Mindcensor": dict(
        role="Interaction",
        effect_tags=["tutor_disruption"],
        simple_effect="flash, flying; opponents searching their library only see the top 4 cards instead (tutor disruption)",
        halbwertszeit=0.4,
    ),
    "Wonder": dict(
        role="Strategy",
        effect_tags=["graveyard_static_ability"],
        simple_effect="grants flying to your creatures from the graveyard as long as you control an Island (passive, no need to cast)",
        halbwertszeit=0.7,
    ),
    "Rising of the Day": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="your creatures have haste; your legendary creatures get +1/+0 (aggressive static anthem)",
        halbwertszeit=0.8,
    ),
    "Redirect Lightning": dict(
        role="Interaction",
        effect_tags=["redirect_paid"],
        simple_effect="change the target of a single-target spell or ability; costs 5 life or {2} (protects your permanents / redirects removal or burn)",
        halbwertszeit=0.45,
    ),
    "Thousand-Year Storm": dict(
        role="Strategy",
        effect_tags=["spell_copy", "spellslinger_payoff"],
        simple_effect="whenever you cast an instant/sorcery, copy it once for each other instant/sorcery you've already cast this turn (exponential spellslinger payoff/combo piece)",
        halbwertszeit=0.5,
    ),
    "Resourceful Defense": dict(
        role="Strategy",
        effect_tags=["counters_matter", "counter_salvage"],
        simple_effect="saves counters from your permanents that leave the battlefield onto another permanent; can also manually move counters between your permanents for {4}{W} (counters-matter protection/synergy engine)",
        halbwertszeit=0.5,
    ),
    "The Ten Rings": dict(
        role="CardAdvantage",
        effect_tags=["draw_to_hand_size"],
        simple_effect="maximum hand size 10; at end step, draws up to 10 cards in hand (steady card advantage engine once it sticks)",
        halbwertszeit=0.75,
    ),
    "Bloodthirsty Conqueror": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="flying, deathtouch; whenever an opponent loses life (including combat damage), you gain that much life (drain/combo piece)",
        halbwertszeit=0.55,
    ),
    "Ghalta, Stampede Tyrant": dict(
        role="Strategy",
        effect_tags=["free_permanent_cheat"],
        simple_effect="on ETB, puts any number of creature cards from your hand onto the battlefield for free (one-time mass creature cheat)",
        halbwertszeit=0.8,
    ),
    "Rhox Faithmender": dict(
        role="Strategy",
        effect_tags=["lifegain", "lifegain_doubler"],
        simple_effect="lifelink; doubles all life you gain (lifegain payoff/combo piece)",
        halbwertszeit=0.75,
    ),
    "Comet Storm": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="deals X damage split among 1+ targets (one target per multikick), X scales with mana invested (flexible scalable burn/removal)",
        halbwertszeit=0.85,
    ),
    # -----------------------------------------------------------------
    # v4.73.0: CURATED_OVERRIDES-Erweiterung Runde 2 (gleiche daten-
    # getriebene Ranking-Methodik wie Runde 1 (v4.72.0), erneut ange-
    # wendet: alle verbleibenden Fallback-Karten mit Gesamt-Quantity
    # >=15 ueber alle 1.585 echten Decks, NACHDEM die 6 neuen
    # generellen Regex-Regeln aus Runde 2 bereits angewendet wurden.
    # Siehe Docs/curated_overrides_expansion_v4_73_0.md fuer Details.
    # -----------------------------------------------------------------
    "Venser, Shaper Savant": dict(
        role="Interaction",
        effect_tags=["bounce_single_flexible"],
        simple_effect="flash; on ETB, return target spell or permanent to its owner's hand (flexible bounce/counter-adjacent tempo play)",
        halbwertszeit=0.85,
    ),
    "Bloodletter of Aclazotz": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="flying; doubles life an opponent loses during your turn (damage/drain payoff, one-sided)",
        halbwertszeit=0.5,
    ),
    "Disrupt Decorum": dict(
        role="Interaction",
        effect_tags=["goad_group"],
        simple_effect="goad all creatures you don't control - they must attack, and not you, until your next turn (group removal-adjacent redirect of opposing threats)",
        halbwertszeit=0.8,
    ),
    "Wilderness Reclamation": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="untap all your lands at the beginning of your end step (effectively doubles your available mana for instant-speed plays)",
        halbwertszeit=0.8,
    ),
    "Winding Constrictor": dict(
        role="Strategy",
        effect_tags=["counters_matter"],
        simple_effect="you get one additional counter of each kind whenever you would put counters on a permanent or player you control (counters-matter payoff)",
        halbwertszeit=0.7,
    ),
    "Muldrotha, the Gravetide": dict(
        role="Strategy",
        effect_tags=["graveyard_recursion"],
        simple_effect="each turn, play a land and cast one permanent spell of each permanent type from your graveyard (repeatable multi-type graveyard value engine)",
        halbwertszeit=0.8,
    ),
    "Crashing Drawbridge": dict(
        role="Strategy",
        effect_tags=["haste_enabler"],
        simple_effect="defender; {T}: your creatures gain haste until end of turn (repeatable haste enabler)",
        halbwertszeit=0.6,
    ),
    "Fleshbag Marauder": dict(
        role="Interaction",
        effect_tags=["removal_edict_symmetric"],
        simple_effect="on ETB, each player sacrifices a creature of their choice (one-time symmetric edict)",
        halbwertszeit=1.0,
    ),
    "Shared Animosity": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="attacking creatures get +1/+0 for each other attacker sharing a creature type (go-wide tribal combat pump)",
        halbwertszeit=0.6,
    ),
    "Overwhelming Stampede": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="your creatures gain trample and get +X/+X until end of turn, X = your greatest power (one-time go-wide finisher)",
        halbwertszeit=0.9,
    ),
    "Burgeoning": dict(
        role="Ramp",
        effect_tags=["extra_land_drop"],
        simple_effect="whenever an opponent plays a land, you may put a land from your hand onto the battlefield free (fast, passive extra land drops early)",
        halbwertszeit=0.6,
    ),
    "Kiora's Follower": dict(
        role="Ramp",
        effect_tags=["untap_utility_repeatable"],
        simple_effect="{T}: untap another target permanent (repeatable ramp/utility - usually used to untap a mana dork or rock for extra mana)",
        halbwertszeit=0.6,
    ),
    "Voltaic Key": dict(
        role="Ramp",
        effect_tags=["untap_utility_repeatable"],
        simple_effect="{1}, {T}: untap target artifact (repeatable ramp when used on mana rocks, also enables tap-ability abuse)",
        halbwertszeit=0.55,
    ),
    "Moonshaker Cavalry": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="flying; on ETB, your creatures gain flying and get +X/+X until end of turn, X = number of creatures you control (one-time go-wide finisher)",
        halbwertszeit=0.85,
    ),
    "Felidar Sovereign": dict(
        role="Strategy",
        effect_tags=["lifegain", "alt_win_condition"],
        simple_effect="vigilance, lifelink; you win the game at your upkeep if you have 40+ life (lifegain payoff/alternate win condition)",
        halbwertszeit=0.5,
    ),
    "Torbran, Thane of Red Fell": dict(
        role="Strategy",
        effect_tags=["damage_boost_flat"],
        simple_effect="your red damage sources deal 2 extra damage to opponents/their permanents (burn/ping payoff amplifier)",
        halbwertszeit=0.6,
    ),
    "Arbor Elf": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="{T}: untap target Forest (mana dork - effectively an extra mana source alongside a Forest, often doubled with mana-doubling lands)",
        halbwertszeit=0.8,
    ),
    "The Skullspore Nexus": dict(
        role="Strategy",
        effect_tags=["cost_reduction", "aristocrats_sac_death_trigger"],
        simple_effect="costs less based on your biggest creature's power; when your nontoken creatures die, creates a token scaled to their combined power; can double a creature's power (value/aristocrats engine)",
        halbwertszeit=0.55,
    ),
    "Assault Formation": dict(
        role="Strategy",
        effect_tags=["stat_swap_combat"],
        simple_effect="your creatures deal combat damage equal to toughness instead of power; lets defenders attack for {G}; team +0/+1 pump (defender/toughness-matters payoff)",
        halbwertszeit=0.55,
    ),
    "Tower Defense": dict(
        role="Interaction",
        effect_tags=["team_toughness_pump_defensive"],
        simple_effect="your creatures get +0/+5 and gain reach until end of turn (one-time team defensive combat trick, blanks most attacks)",
        halbwertszeit=0.75,
    ),
    "Mirror Entity": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher", "tribal_synergy_lord"],
        simple_effect="every creature type; {X}: your creatures become X/X and gain all creature types until end of turn (scalable team pump + tribal enabler)",
        halbwertszeit=0.7,
    ),
    "Manabarbs": dict(
        role="Strategy",
        effect_tags=["symmetric_burn_tax"],
        simple_effect="deals 1 damage to a player whenever they tap a land for mana (symmetric slow burn, punishes heavy mana use)",
        halbwertszeit=0.5,
    ),
    "Electrodominance": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable", "free_spell_follow_up"],
        simple_effect="deals X damage to any target, then cast a spell with mana value X or less for free (flexible burn + value)",
        halbwertszeit=0.85,
    ),
    "Twilight Diviner": dict(
        role="Strategy",
        effect_tags=["graveyard_recursion", "token_creation"],
        simple_effect="on ETB, surveil 2; whenever another of your creatures enters from the graveyard, create a copy of it once per turn (graveyard reanimator value engine)",
        halbwertszeit=0.5,
    ),
    "Tree of Perdition": dict(
        role="Interaction",
        effect_tags=["life_total_manipulation"],
        simple_effect="{T}: swap a target opponent's life total with this creature's toughness (build a huge toughness, then crash their life total down - situational finisher/removal-adjacent)",
        halbwertszeit=0.4,
    ),
    "Selective Obliteration": dict(
        role="Interaction",
        effect_tags=["removal_board_conditional"],
        simple_effect="each player chooses a color; exile every permanent that isn't colorless or that chosen color (multi-color-dependent board wipe)",
        halbwertszeit=0.85,
    ),
    "Brave the Sands": dict(
        role="Strategy",
        effect_tags=["defensive_static_buff"],
        simple_effect="your creatures have vigilance and can each block one additional creature (defensive team buff, enables attack-and-block)",
        halbwertszeit=0.7,
    ),
    "Dark Deal": dict(
        role="Strategy",
        effect_tags=["wheel_effect"],
        simple_effect="each player discards their hand then draws that many cards minus one (symmetric wheel effect, slightly asymmetric in your favor if hand sizes are uneven)",
        halbwertszeit=0.85,
    ),
    "Teferi's Puzzle Box": dict(
        role="Strategy",
        effect_tags=["wheel_effect"],
        simple_effect="each player's draw step: put their hand on the bottom of their library and draw that many cards (symmetric hand refill/wheel each turn)",
        halbwertszeit=0.85,
    ),
    "Temur Battle Rage": dict(
        role="Strategy",
        effect_tags=["combat_trick_finisher"],
        simple_effect="target creature gains double strike (and trample if you control a 4+ power creature) - a common lethal combat finisher/combo enabler",
        halbwertszeit=0.8,
    ),
    "Noxious Revival": dict(
        role="CardAdvantage",
        effect_tags=["graveyard_to_library_recursion"],
        simple_effect="put target card from any graveyard on top of its owner's library (can be cast for 2 life instead of mana; sets up a redraw of any graveyard card)",
        halbwertszeit=0.6,
    ),
    "Ondu Spiritdancer": dict(
        role="Strategy",
        effect_tags=["token_creation", "clone_effect"],
        simple_effect="whenever an enchantment you control enters, once per turn, create a token copy of it (enchantment value engine)",
        halbwertszeit=0.55,
    ),
    "Thalia, Heretic Cathar": dict(
        role="Interaction",
        effect_tags=["tempo_lockdown"],
        simple_effect="first strike; opponents' creatures and nonbasic lands enter tapped (persistent tempo disruption)",
        halbwertszeit=0.7,
    ),
    "Spellskite": dict(
        role="Interaction",
        effect_tags=["redirect_paid"],
        simple_effect="pay {U} or 2 life: redirect a target of a spell/ability to this creature (protects your other permanents by soaking removal/burn)",
        halbwertszeit=0.6,
    ),
    "Mirror Box": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="removes the legend rule for you; your legendary creatures get +1/+1, and creatures get +1/+1 per other same-named creature you control (legend/token-copy payoff)",
        halbwertszeit=0.5,
    ),
    "Blasphemous Edict": dict(
        role="Interaction",
        effect_tags=["removal_edict_mass"],
        simple_effect="each player sacrifices 13 creatures of their choice (usually a full wipe); can be cast for {B} if 13+ creatures are on the battlefield",
        halbwertszeit=0.85,
    ),
    "Phyrexian Obliterator": dict(
        role="Interaction",
        effect_tags=["removal_via_combat_punisher"],
        simple_effect="trample; whenever a source deals damage to this creature, its controller sacrifices that many permanents (brutal combat/removal deterrent)",
        halbwertszeit=0.6,
    ),
    "Valley Rotcaller": dict(
        role="Strategy",
        effect_tags=["life_drain_direct", "tribal_synergy_lord"],
        simple_effect="menace; whenever it attacks, drains life equal to your other Squirrels/Bats/Lizards/Rats (tribal-scaled drain finisher)",
        halbwertszeit=0.5,
    ),
    "Seven Dwarves": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "unlimited_copies"],
        simple_effect="gets +1/+1 per other Seven Dwarves you control; deck may run up to 7 copies (goes wide as a single 'card', similar to Rat Colony but capped)",
        halbwertszeit=0.5,
    ),
    "Balefire Dragon": dict(
        role="Interaction",
        effect_tags=["removal_board_via_combat_damage"],
        simple_effect="flying; whenever it deals combat damage to a player, deals that much damage to each creature that player controls (built-in one-sided board wipe on connect)",
        halbwertszeit=0.65,
    ),
    "Warstorm Surge": dict(
        role="Strategy",
        effect_tags=["etb_ping_payoff"],
        simple_effect="whenever a creature you control enters, it deals damage equal to its power to any target (repeatable removal/burn engine off ETBs)",
        halbwertszeit=0.65,
    ),
    "Leyline of Anticipation": dict(
        role="Strategy",
        effect_tags=["flash_enabler"],
        simple_effect="free if in your opening hand; you may cast spells as though they had flash (flexibility/ambush engine)",
        halbwertszeit=0.6,
    ),
    "Umbral Collar Zealot": dict(
        role="Strategy",
        effect_tags=["free_sac_outlet"],
        simple_effect="sacrifice another creature or artifact: surveil 1 (repeatable sacrifice outlet + light card selection)",
        halbwertszeit=0.6,
    ),
    "Resurgent Belief": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="return all enchantment cards from your graveyard to the battlefield (delayed via suspend 2, or cast normally later) - one-time mass enchantment reanimation",
        halbwertszeit=0.85,
    ),
    "Animist's Awakening": dict(
        role="Ramp",
        effect_tags=["land_ramp_mass_burst"],
        simple_effect="reveal the top X cards, put all lands among them onto the battlefield tapped (or untapped with 2+ instants/sorceries in graveyard) - scalable one-time land ramp burst",
        halbwertszeit=0.85,
    ),
    "Hellkite Tyrant": dict(
        role="Strategy",
        effect_tags=["theft_effect", "alt_win_condition"],
        simple_effect="flying, trample; whenever it deals combat damage to a player, gain control of every artifact they control; win the game at your upkeep with 20+ artifacts (artifact theft engine + alt win con)",
        halbwertszeit=0.55,
    ),
    "Greater Auramancy": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="your other enchantments (and creatures they enchant) have shroud, protecting them from targeted removal",
        halbwertszeit=0.75,
    ),
    "Jetmir, Nexus of Revels": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="your creatures get scaling +1/+0 and keywords (vigilance/trample/double strike) based on how many creatures you control (go-wide payoff anthem)",
        halbwertszeit=0.7,
    ),
    "Slaughter the Strong": dict(
        role="Interaction",
        effect_tags=["removal_board_conditional"],
        simple_effect="each player keeps any creatures with total power 4 or less, sacrifices the rest (board wipe that punishes big-creature decks, spares small-creature ones)",
        halbwertszeit=0.85,
    ),
    "Tree of Redemption": dict(
        role="Strategy",
        effect_tags=["life_total_manipulation"],
        simple_effect="{T}: swap your life total with this creature's toughness (build a huge toughness, then bank it as life - defensive/combo piece)",
        halbwertszeit=0.45,
    ),
    "Felothar the Steadfast": dict(
        role="Strategy",
        effect_tags=["stat_swap_combat", "aristocrats_sac_death_trigger"],
        simple_effect="creatures deal combat damage equal to toughness; your defenders can attack; sac a creature to loot cards equal to its toughness/power (toughness-matters value engine)",
        halbwertszeit=0.5,
    ),
    "Skittering Cicada": dict(
        role="Strategy",
        effect_tags=["spellslinger_payoff"],
        simple_effect="flash; lets you cast colorless spells at instant speed; grows and gains trample when you cast a colorless spell (colorless-spell payoff)",
        halbwertszeit=0.45,
    ),
    "Sakashima of a Thousand Faces": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="enters as a copy of another creature you control (keeping Sakashima's own abilities too); the legend rule doesn't apply to your permanents (flexible clone value)",
        halbwertszeit=0.75,
    ),
    "Flare of Malice": dict(
        role="Interaction",
        effect_tags=["removal_edict_scalable"],
        simple_effect="may be cast free by sacrificing a black creature; each opponent sacrifices their biggest creature/planeswalker (free, scalable edict removal)",
        halbwertszeit=0.8,
    ),
    "Empyrean Eagle": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="flying; your other flying creatures get +1/+1 (evasive tribal anthem)",
        halbwertszeit=0.75,
    ),
    "Ingenious Artillerist": dict(
        role="Strategy",
        effect_tags=["etb_ping_payoff"],
        simple_effect="whenever your artifacts enter, deals that much damage to each opponent (repeatable artifact-triggered burn engine)",
        halbwertszeit=0.55,
    ),
    "Archon of Emeria": dict(
        role="Interaction",
        effect_tags=["spell_lock", "tempo_lockdown"],
        simple_effect="flying; each player can cast at most one spell per turn; opponents' nonbasic lands enter tapped (symmetric spell-count restriction + tempo tax)",
        halbwertszeit=0.75,
    ),
    "Sheoldred's Edict": dict(
        role="Interaction",
        effect_tags=["removal_edict_symmetric"],
        simple_effect="modal: each opponent sacrifices a nontoken creature, a token creature, or a planeswalker of their choice (flexible one-time edict)",
        halbwertszeit=1.0,
    ),
    "Dragon Tempest": dict(
        role="Strategy",
        effect_tags=["haste_enabler", "tribal_synergy_lord"],
        simple_effect="your flying creatures gain haste on ETB; your Dragons deal damage on ETB scaled by Dragon count (tribal Dragons payoff)",
        halbwertszeit=0.5,
    ),
    "Twinflame": dict(
        role="Strategy",
        effect_tags=["token_creation", "clone_effect"],
        simple_effect="copy any number of your creatures (costs more per extra target), tokens have haste but are exiled end of turn (scalable one-time combat burst)",
        halbwertszeit=0.8,
    ),
    "Light Up the Stage": dict(
        role="CardAdvantage",
        effect_tags=["card_selection"],
        simple_effect="exile the top 2 cards, may play them until your next turn (temporary card advantage, cheaper if an opponent lost life this turn)",
        halbwertszeit=0.85,
    ),
    "Passionate Archaeologist": dict(
        role="Strategy",
        effect_tags=["spellslinger_payoff"],
        simple_effect="Background: your commander deals damage equal to mana value whenever you cast a spell from exile (niche cast-from-exile payoff)",
        halbwertszeit=0.3,
    ),
    "Apex Altisaur": dict(
        role="Interaction",
        effect_tags=["removal_via_fight"],
        simple_effect="on ETB and whenever it's dealt damage, fights a target creature you don't control (repeatable fight-based removal)",
        halbwertszeit=0.75,
    ),
    "Riptide Gearhulk": dict(
        role="Interaction",
        effect_tags=["removal_multi_tuck"],
        simple_effect="double strike, prowess; on ETB, puts a nonland permanent from each opponent into their library third from the top (multi-target temporary removal)",
        halbwertszeit=0.85,
    ),
    "Guardian of Faith": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="flash, vigilance; on ETB, phase out any number of your creatures (temporary protection from removal/combat/wipes)",
        halbwertszeit=0.7,
    ),
    "Wake the Past": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="return all artifact cards from your graveyard to the battlefield with haste (one-time mass artifact reanimation)",
        halbwertszeit=1.0,
    ),
    "It That Betrays": dict(
        role="Interaction",
        effect_tags=["theft_effect"],
        simple_effect="annihilator 2 (opponents sacrifice 2 permanents when it attacks); whenever an opponent sacrifices a nontoken permanent, you get it (massive attack-triggered value/theft)",
        halbwertszeit=0.5,
    ),
    "Silent Arbiter": dict(
        role="Interaction",
        effect_tags=["tempo_lockdown"],
        simple_effect="only one creature can attack or block each combat (severe symmetric combat restriction)",
        halbwertszeit=0.85,
    ),
    "Tolarian Winds": dict(
        role="CardAdvantage",
        effect_tags=["wheel_effect"],
        simple_effect="discard your hand, then draw that many cards (one-time personal hand refill/wheel)",
        halbwertszeit=0.85,
    ),
    "Past in Flames": dict(
        role="CardAdvantage",
        effect_tags=["graveyard_recasting_engine"],
        simple_effect="every instant/sorcery in your graveyard gains flashback at its own cost until end of turn; has flashback itself (mass graveyard spell-recast enabler)",
        halbwertszeit=0.6,
    ),
    "Sulfuric Vortex": dict(
        role="Strategy",
        effect_tags=["symmetric_burn_tax"],
        simple_effect="deals 2 damage to each player each upkeep; no one can gain life (symmetric clock, locks out lifegain strategies)",
        halbwertszeit=0.85,
    ),
    "Urabrask the Hidden": dict(
        role="Strategy",
        effect_tags=["haste_enabler", "tempo_lockdown"],
        simple_effect="your creatures have haste; opponents' creatures enter tapped (aggressive tempo asymmetry)",
        halbwertszeit=0.75,
    ),
    "Amulet of Vigor": dict(
        role="Ramp",
        effect_tags=["etb_ramp_burst"],
        simple_effect="whenever your permanents enter tapped, untap them immediately (turns tapped-lands/ramp-pieces into instant value)",
        halbwertszeit=0.6,
    ),
    "Desynchronization": dict(
        role="Interaction",
        effect_tags=["bounce_board_conditional"],
        simple_effect="return every nonland, non-historic (non-artifact/non-legendary/non-Saga) permanent to hand (conditional one-sided-ish board bounce)",
        halbwertszeit=0.7,
    ),
    "Master of Etherium": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="power/toughness equal to your artifact count; other artifact creatures get +1/+1 (artifact tribal payoff/finisher)",
        halbwertszeit=0.6,
    ),
    "Aven Interrupter": dict(
        role="Interaction",
        effect_tags=["removal_single_exile"],
        simple_effect="flash, flying; on ETB, exile target spell (its owner may recast it later as a sorcery); opponents' graveyard/exile spells cost more (tempo-delay removal + tax)",
        halbwertszeit=0.75,
    ),
    "Forced Fruition": dict(
        role="Strategy",
        effect_tags=["group_hug_or_symmetric_draw"],
        simple_effect="whenever an opponent casts a spell, that opponent draws 7 cards (huge one-sided card advantage FOR THEM unless you're punishing a specific strategy - usually a trap/political card)",
        halbwertszeit=0.4,
    ),
    "Fallen Shinobi": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff", "free_spells_from_exile"],
        simple_effect="ninjutsu; whenever it deals combat damage to a player, that player exiles their top 2 cards which you may play for free until end of turn (attack-triggered card theft/value)",
        halbwertszeit=0.5,
    ),
    "Kaervek the Merciless": dict(
        role="Strategy",
        effect_tags=["symmetric_burn_tax"],
        simple_effect="whenever an opponent casts a spell, deals damage equal to its mana value to any target (reactive burn engine, punishes opponents' spellslinging)",
        halbwertszeit=0.55,
    ),
    "Dark Confidant": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling"],
        simple_effect="each upkeep, reveal and draw the top card, lose life equal to its mana value (powerful but risky repeatable card advantage)",
        halbwertszeit=0.85,
    ),
    "Twilight Prophet": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="flying; once you have 10+ permanents (city's blessing), each upkeep reveals your top card into hand and drains life equal to its mana value (delayed but powerful repeatable drain/draw engine)",
        halbwertszeit=0.5,
    ),
    "Doomwake Giant": dict(
        role="Interaction",
        effect_tags=["removal_board_repeatable"],
        simple_effect="whenever this or another of your enchantments enters, all opponents' creatures get -1/-1 until end of turn (repeatable mini board wipe off enchantment ETBs)",
        halbwertszeit=0.5,
    ),
    "Akiri, Line-Slinger": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="first strike, vigilance; gets +1/+0 per artifact you control (artifact-count payoff)",
        halbwertszeit=0.6,
    ),
    "Vial Smasher the Fierce": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="whenever you cast your first spell each turn, deals damage equal to its mana value to a random opponent or their planeswalker (repeatable, semi-random burn)",
        halbwertszeit=0.6,
    ),
    "Gilded Lotus": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="{T}: add 3 mana of one color (large fixed mana rock)",
        halbwertszeit=0.9,
    ),
    "Ardenn, Intrepid Archaeologist": dict(
        role="Strategy",
        effect_tags=["voltron_aura_equipment"],
        simple_effect="each combat, may attach any number of your Auras/Equipment to any permanent/player for free (Voltron enabler)",
        halbwertszeit=0.6,
    ),
    "Meekstone": dict(
        role="Interaction",
        effect_tags=["tempo_lockdown"],
        simple_effect="creatures with power 3+ (yours and opponents') don't untap normally - symmetric but usually built around to only hurt opponents (tempo lockdown on big creatures)",
        halbwertszeit=0.55,
    ),
    "Intruder Alarm": dict(
        role="Strategy",
        effect_tags=["combo_piece_untap_on_etb"],
        simple_effect="creatures don't untap normally, but ALL creatures untap whenever any creature enters (classic combo piece with token generators/blink effects)",
        halbwertszeit=0.3,
    ),
    "Roiling Vortex": dict(
        role="Strategy",
        effect_tags=["symmetric_burn_tax"],
        simple_effect="deals 1 damage to each player each upkeep, plus 5 damage whenever anyone casts a spell for free; {R}: opponents can't gain life this turn (symmetric burn + free-spell punisher)",
        halbwertszeit=0.55,
    ),
    "Eladamri, Korvecdal": dict(
        role="CardAdvantage",
        effect_tags=["play_from_top_of_library"],
        simple_effect="you may play creature spells from the top of your library; tap 2 creatures to dig for a creature and put it onto the battlefield (creature-focused card advantage engine)",
        halbwertszeit=0.55,
    ),
    "Insurrection": dict(
        role="Strategy",
        effect_tags=["theft_effect"],
        simple_effect="untap and gain control of all creatures (yours and opponents') with haste until end of turn (massive one-time alpha strike/combo finisher)",
        halbwertszeit=0.9,
    ),
    "Weaver of Harmony": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "spell_copy"],
        simple_effect="other enchantment creatures get +1/+1; may copy target activated/triggered ability from an enchantment source (enchantment-tribal value engine)",
        halbwertszeit=0.45,
    ),
    "Augur of Autumn": dict(
        role="CardAdvantage",
        effect_tags=["play_from_top_of_library"],
        simple_effect="you may play lands from the top of your library; with 3+ differently-powered creatures, may also cast creature spells from there (top-of-library value engine)",
        halbwertszeit=0.6,
    ),
    "Axebane Guardian": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="defender; {T}: adds X mana of any colors, X = your number of defenders (scaling mana dork for defender-heavy decks)",
        halbwertszeit=0.55,
    ),
    "Wernog, Rider's Chaplain": dict(
        role="CardAdvantage",
        effect_tags=["investigate_value"],
        simple_effect="when it enters or leaves, opponents may investigate (make a Clue) or lose 1 life; you investigate extra times based on how many did (flexible one-time clue/value generation)",
        halbwertszeit=0.55,
    ),
    "Lyra Dawnbringer": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "lifegain"],
        simple_effect="flying, first strike, lifelink; your other Angels get +1/+1 and lifelink (Angel tribal anthem + lifegain)",
        halbwertszeit=0.75,
    ),
    "Deafening Silence": dict(
        role="Interaction",
        effect_tags=["spell_lock"],
        simple_effect="each player can cast at most one noncreature spell per turn (symmetric spell-count restriction, usually built around to favor creature decks)",
        halbwertszeit=0.7,
    ),
    "The Reality Chip": dict(
        role="CardAdvantage",
        effect_tags=["play_from_top_of_library"],
        simple_effect="you may look at your top card any time; while attached to a creature, you may play lands/cast spells from the top of your library (reconfigurable top-of-library value engine)",
        halbwertszeit=0.6,
    ),
    "Genesis Wave": dict(
        role="Strategy",
        effect_tags=["free_permanent_cheat"],
        simple_effect="reveal the top X cards, put any number of permanents with mana value <=X onto the battlefield free (scalable one-time mass permanent cheat)",
        halbwertszeit=0.9,
    ),
    "Ezuri, Renegade Leader": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="regenerate another Elf; pump all your Elves +3/+3 and trample (Elf tribal protection + finisher)",
        halbwertszeit=0.55,
    ),
    "Dance of the Manse": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="return up to X artifact/enchantment cards (mana value <=X) from your graveyard to the battlefield; at X>=6 they also become 4/4 creatures (scalable mass reanimation + finisher)",
        halbwertszeit=0.8,
    ),
    "The Lord of Pain": dict(
        role="Strategy",
        effect_tags=["symmetric_burn_tax"],
        simple_effect="menace; opponents can't gain life; whenever a player casts their first spell each turn, deals damage equal to its mana value to a chosen player (burn engine + anti-lifegain lock)",
        halbwertszeit=0.55,
    ),
    "Duelist's Heritage": dict(
        role="Strategy",
        effect_tags=["combat_trick_finisher"],
        simple_effect="whenever your creatures attack, you may give one of them double strike until end of turn (repeatable combat finisher)",
        halbwertszeit=0.6,
    ),
    "Oblivion Sower": dict(
        role="Strategy",
        effect_tags=["theft_effect"],
        simple_effect="on cast, an opponent exiles their top 4 cards; you may put any land cards among them onto the battlefield under your control (one-time land theft/ramp)",
        halbwertszeit=0.75,
    ),
    "Shimmer Myr": dict(
        role="Strategy",
        effect_tags=["flash_enabler"],
        simple_effect="flash; you may cast artifact spells as though they had flash (flexibility/ambush engine for artifacts)",
        halbwertszeit=0.5,
    ),
    "Ultron, Artificial Malevolence": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="whenever another nontoken artifact you control enters, pay {2} to create a copy of it (repeatable artifact-doubling value engine)",
        halbwertszeit=0.5,
    ),
    "Gisela, the Broken Blade": dict(
        role="Strategy",
        effect_tags=["lifegain"],
        simple_effect="flying, first strike, lifelink; can meld with Bruna into a much bigger creature if you own/control both (situational combo upside on top of solid stats)",
        halbwertszeit=0.6,
    ),
    "Intangible Virtue": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="your creature tokens get +1/+1 and vigilance (token-strategy anthem)",
        halbwertszeit=0.7,
    ),
    "Raise the Past": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="return all creature cards with mana value <=2 from your graveyard to the battlefield (one-time mass small-creature reanimation)",
        halbwertszeit=0.85,
    ),
    "Thrumming Stone": dict(
        role="Strategy",
        effect_tags=["spell_copy"],
        simple_effect="your spells have ripple 4 (may reveal your top 4 cards and cast any with the same name for free) - powerful with 'deck full of one card' builds",
        halbwertszeit=0.4,
    ),
    "Baldin, Century Herdmaster": dict(
        role="Strategy",
        effect_tags=["stat_swap_combat", "team_pump_finisher"],
        simple_effect="your creatures deal combat damage equal to toughness; whenever it attacks, pump your team's toughness by your hand size (toughness-matters finisher)",
        halbwertszeit=0.5,
    ),
    "Valgavoth, Terror Eater": dict(
        role="Interaction",
        effect_tags=["graveyard_hate_exile"],
        simple_effect="flying, lifelink; opponents' cards that would go to their graveyard are exiled instead; you may cast those exiled cards by paying life instead of mana (graveyard hate + big value engine)",
        halbwertszeit=0.55,
    ),
    "Archfiend of Depravity": dict(
        role="Interaction",
        effect_tags=["removal_board_repeatable"],
        simple_effect="flying; each opponent's end step, they keep at most 2 creatures and sacrifice the rest (repeatable symmetric-looking but very one-sided board control)",
        halbwertszeit=0.7,
    ),
    "Disciple of the Vault": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="whenever one of your artifacts dies, may drain an opponent for 1 life (artifact-sacrifice payoff)",
        halbwertszeit=0.55,
    ),
    "Kiki-Jiki, Mirror Breaker": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="haste; {T}: create a hasty copy of target nonlegendary creature you control, sacrificed at end of turn (classic combo piece + repeatable value)",
        halbwertszeit=0.6,
    ),
    "Chandra's Incinerator": dict(
        role="Strategy",
        effect_tags=["cost_reduction", "burn_payoff_engine"],
        simple_effect="trample; costs less based on noncombat damage already dealt this turn; whenever your noncombat damage sources hit an opponent, deals that much damage again to one of their creatures/planeswalkers (burn payoff engine)",
        halbwertszeit=0.5,
    ),
    "Orthion, Hero of Lavabrink": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="{1}{R}, {T}: create a hasty copy of another creature you control (sacrificed end of turn); bigger cost makes 5 at once (scalable repeatable token-copy engine)",
        halbwertszeit=0.5,
    ),
    "Fire Covenant": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="pay X life as an additional cost: deal X damage divided among any number of target creatures (scalable multi-target removal, no mana scaling needed)",
        halbwertszeit=0.85,
    ),
    "The Last Agni Kai": dict(
        role="Interaction",
        effect_tags=["removal_via_fight"],
        simple_effect="your creature fights an opponent's creature; excess damage dealt becomes red mana you can spend this turn (fight removal + potential mana burst)",
        halbwertszeit=0.7,
    ),
    "End-Raze Forerunners": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="vigilance, trample, haste; on ETB, your other creatures get +2/+2 and gain vigilance/trample until end of turn (immediate go-wide finisher)",
        halbwertszeit=0.95,
    ),
    "Fling": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="sacrifice a creature as an additional cost: deal damage equal to its power to any target (turns a doomed/big creature into burn/removal)",
        halbwertszeit=0.7,
    ),
    "Hallowed Haunting": dict(
        role="Strategy",
        effect_tags=["token_creation", "tribal_synergy_lord"],
        simple_effect="with 7+ enchantments, your creatures fly and have vigilance; whenever you cast an enchantment, create a Spirit token scaled to your Spirit count (enchantment payoff engine)",
        halbwertszeit=0.5,
    ),
    "Bruenor Battlehammer": dict(
        role="Strategy",
        effect_tags=["voltron_aura_equipment"],
        simple_effect="your creatures get +2/+0 per Equipment attached to them; your first equip each turn is free (Equipment-matters payoff)",
        halbwertszeit=0.6,
    ),
    "Wrathful Raptors": dict(
        role="Strategy",
        effect_tags=["removal_via_combat_punisher"],
        simple_effect="trample; whenever a Dinosaur you control is dealt damage, it deals that much damage to any non-Dinosaur target (damage-redirect punisher, tribal payoff)",
        halbwertszeit=0.4,
    ),
    "Doran, the Siege Tower": dict(
        role="Strategy",
        effect_tags=["stat_swap_combat"],
        simple_effect="ALL creatures (yours and opponents') deal combat damage equal to toughness instead of power (symmetric but usually built around with high-toughness/low-power creatures)",
        halbwertszeit=0.8,
    ),
    "Clock of Omens": dict(
        role="Ramp",
        effect_tags=["untap_utility_repeatable"],
        simple_effect="tap two untapped artifacts: untap target artifact (repeatable artifact-chaining utility, net-neutral unless combined with cheap artifacts)",
        halbwertszeit=0.45,
    ),
    "Thousand-Year Elixir": dict(
        role="Strategy",
        effect_tags=["haste_enabler"],
        simple_effect="your creatures' activated abilities work as though they had haste; {1},{T}: untap target creature (haste enabler + repeatable creature untap)",
        halbwertszeit=0.55,
    ),
    "Coretapper": dict(
        role="Strategy",
        effect_tags=["counters_matter"],
        simple_effect="{T}: put a charge counter on target artifact; sacrifice: put 2 charge counters (charge-counter support piece for specific artifact payoffs)",
        halbwertszeit=0.35,
    ),
    "Coat of Arms": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="every creature gets +1/+1 for each other creature on the battlefield sharing a creature type with it (symmetric but usually built around with go-wide tribal decks)",
        halbwertszeit=0.75,
    ),
    "Heliod's Intervention": dict(
        role="Interaction",
        effect_tags=["removal_board_scalable"],
        simple_effect="modal: destroy X target artifacts/enchantments, or gain 2X life (flexible scalable removal or lifegain)",
        halbwertszeit=0.85,
    ),
    "Scourge of Fleets": dict(
        role="Interaction",
        effect_tags=["bounce_board_conditional"],
        simple_effect="on ETB, bounce every opponent creature with toughness <= your Island count (scalable one-time mass bounce)",
        halbwertszeit=0.6,
    ),
    "Esior, Wardwing Familiar": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="flying; spells targeting your commanders cost opponents {3} more (commander protection tax)",
        halbwertszeit=0.55,
    ),
    "Favorable Winds": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="your flying creatures get +1/+1 (evasive tribal anthem)",
        halbwertszeit=0.75,
    ),
    "Starwinder": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff"],
        simple_effect="whenever your creatures deal combat damage to a player, may draw that many cards (temporary via warp, strong attack-triggered card draw)",
        halbwertszeit=0.55,
    ),
    "Delina, Wild Mage": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="whenever it attacks, roll a d20 to create a hasty attacking copy of a chosen creature you control, possibly more than one (random but powerful attack-triggered token copy engine)",
        halbwertszeit=0.5,
    ),
    "Doom Whisperer": dict(
        role="CardAdvantage",
        effect_tags=["card_selection"],
        simple_effect="flying, trample; pay 2 life: surveil 2 (repeatable paid card selection)",
        halbwertszeit=0.7,
    ),
    "Worldsoul's Rage": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="deals X damage to any target; also puts up to X lands from hand/graveyard onto the battlefield tapped (scalable burn + land ramp in one spell)",
        halbwertszeit=0.8,
    ),
    "Fertile Ground": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="enchanted land taps for 1 extra mana of any color (net +1 fixed mana per turn, aura-based ramp)",
        halbwertszeit=0.85,
    ),
    "Drana and Linvala": dict(
        role="Strategy",
        effect_tags=["theft_effect"],
        simple_effect="flying, vigilance; opponents' creatures' activated abilities can't be used; you gain access to and can use all of them yourself (locks down and steals opponent activated abilities)",
        halbwertszeit=0.45,
    ),
    "Valley Floodcaller": dict(
        role="Strategy",
        effect_tags=["flash_enabler", "tribal_synergy_lord"],
        simple_effect="flash; your noncreature spells gain flash; casting one pumps and untaps your Birds/Frogs/Otters/Rats (flash-matters tribal payoff)",
        halbwertszeit=0.45,
    ),
    "Deflecting Palm": dict(
        role="Interaction",
        effect_tags=["combat_protection_free"],
        simple_effect="prevent the next damage a chosen source would deal to you this turn, then deal that much damage back to its controller (one-time combat/burn protection + reflect)",
        halbwertszeit=0.6,
    ),
    "Doppelgang": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="create X copies of each of X target permanents (extremely scalable, expensive one-time mass clone effect)",
        halbwertszeit=0.6,
    ),
    "Extravagant Replication": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="each upkeep, create a copy token of another nonland permanent you control (repeatable clone value engine)",
        halbwertszeit=0.75,
    ),
    "Sneak Attack": dict(
        role="Strategy",
        effect_tags=["free_permanent_cheat"],
        simple_effect="{R}: put a creature card from hand onto the battlefield with haste, sacrificed at end of turn (repeatable one-turn creature cheat, classic combo piece)",
        halbwertszeit=0.55,
    ),
    "Riveteers Ascendancy": dict(
        role="Strategy",
        effect_tags=["aristocrats_sac_death_trigger", "graveyard_recursion"],
        simple_effect="whenever you sacrifice a creature, once per turn, return a cheaper creature from your graveyard to the battlefield tapped (aristocrats-fueled reanimation engine)",
        halbwertszeit=0.55,
    ),
    "Villainous Wealth": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="an opponent exiles their top X cards; cast any of them with mana value <=X for free (scalable value/theft from an opponent's deck)",
        halbwertszeit=0.85,
    ),
    "Phyrexian Vindicator": dict(
        role="Interaction",
        effect_tags=["combat_protection_free"],
        simple_effect="flying; damage that would be dealt to this creature is prevented and instead dealt to another target of your choice (built-in damage redirect/removal)",
        halbwertszeit=0.6,
    ),
    "Odric, Master Tactician": dict(
        role="Interaction",
        effect_tags=["combat_control"],
        simple_effect="first strike; when Odric and 3+ other creatures attack, you decide which creatures block and how (total combat control, situational finisher)",
        halbwertszeit=0.35,
    ),
    "Thalia, Guardian of Thraben": dict(
        role="Interaction",
        effect_tags=["cost_tax"],
        simple_effect="first strike; opponents' noncreature spells cost {1} more (persistent tax slowing down removal/interaction/ramp)",
        halbwertszeit=0.75,
    ),
    "Masterwork of Ingenuity": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="enters as a copy of any Equipment on the battlefield (flexible one-time Equipment value)",
        halbwertszeit=0.65,
    ),
    "Silence": dict(
        role="Interaction",
        effect_tags=["spell_lock"],
        simple_effect="opponents can't cast spells this turn (one-time protection window, great before your combo/attack)",
        halbwertszeit=0.7,
    ),
    "Bulk Up": dict(
        role="Strategy",
        effect_tags=["combat_trick_finisher"],
        simple_effect="double target creature's power until end of turn; has flashback (repeatable one-time combat finisher across two casts)",
        halbwertszeit=0.7,
    ),
    "Ilharg, the Raze-Boar": dict(
        role="Strategy",
        effect_tags=["free_permanent_cheat"],
        simple_effect="trample; whenever it attacks, put a creature from hand onto the battlefield tapped and attacking, then return it to hand (repeatable attack-triggered creature cheat)",
        halbwertszeit=0.55,
    ),
    "Beacon of Immortality": dict(
        role="Strategy",
        effect_tags=["life_total_manipulation"],
        simple_effect="double target player's life total (one-time massive life swing, reusable by shuffling itself back into your library)",
        halbwertszeit=0.85,
    ),
    "Scion of Oona": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "protection_grant"],
        simple_effect="flash, flying; your other Faeries get +1/+1 and shroud (Faerie tribal anthem + protection)",
        halbwertszeit=0.6,
    ),
    "Blood Seeker": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="whenever an opponent's creature enters, may drain them for 1 life (incremental drain, strong vs token/go-wide opponents)",
        halbwertszeit=0.55,
    ),
    "Arcane Bombardment": dict(
        role="CardAdvantage",
        effect_tags=["free_spell_from_graveyard"],
        simple_effect="whenever you cast your first instant/sorcery each turn, exile a random one from your graveyard and cast free copies of everything exiled this way (repeatable graveyard spell-copy value)",
        halbwertszeit=0.45,
    ),
    "Hellkite Courser": dict(
        role="Strategy",
        effect_tags=["free_permanent_cheat"],
        simple_effect="flying; on ETB, may put your commander from the command zone onto the battlefield with haste for one turn, avoiding the tax (one-time commander cheat/tempo play)",
        halbwertszeit=0.5,
    ),
    "Clever Impersonator": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="enters as a copy of any nonland permanent on the battlefield (maximally flexible one-time clone value)",
        halbwertszeit=0.8,
    ),
    "Gishath, Sun's Avatar": dict(
        role="Strategy",
        effect_tags=["attack_trigger_payoff", "free_permanent_cheat"],
        simple_effect="vigilance, trample, haste; whenever it deals combat damage, reveal that many cards and put any Dinosaurs among them onto the battlefield free (tribal attack-triggered value engine)",
        halbwertszeit=0.55,
    ),
    "Pantlaza, Sun-Favored": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="whenever it or another Dinosaur enters, once per turn, discover X (X = that creature's toughness) - dig for a free spell or card (tribal value engine)",
        halbwertszeit=0.55,
    ),
    "Vedalken Orrery": dict(
        role="Strategy",
        effect_tags=["flash_enabler"],
        simple_effect="you may cast spells as though they had flash (flexibility/ambush engine for your whole deck)",
        halbwertszeit=0.55,
    ),
    "Atarka, World Render": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "combat_trick_finisher"],
        simple_effect="flying, trample; your attacking Dragons gain double strike (tribal Dragons combat finisher)",
        halbwertszeit=0.6,
    ),
    "Klauth, Unrivaled Ancient": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="flying, haste; whenever it attacks, adds mana equal to total attacking power, usable only for spells this turn (attack-triggered mana burst)",
        halbwertszeit=0.5,
    ),
    "Scourge of Valkas": dict(
        role="Strategy",
        effect_tags=["etb_ping_payoff", "tribal_synergy_lord"],
        simple_effect="flying; whenever it or another Dragon enters, deals damage equal to your Dragon count to any target (tribal Dragons burn engine)",
        halbwertszeit=0.55,
    ),
    "Silas Renn, Seeker Adept": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff", "graveyard_recursion"],
        simple_effect="deathtouch; whenever it deals combat damage to a player, may cast an artifact card from your graveyard this turn (attack-triggered artifact recursion)",
        halbwertszeit=0.5,
    ),
    "Bruse Tarl, Boorish Herder": dict(
        role="Strategy",
        effect_tags=["combat_trick_finisher", "lifegain"],
        simple_effect="whenever it enters or attacks, target creature you control gains double strike and lifelink until end of turn (repeatable combat finisher + lifegain)",
        halbwertszeit=0.65,
    ),
    # -----------------------------------------------------------------
    # v4.74.0: CURATED_OVERRIDES-Erweiterung Runde 3 (gleiche daten-
    # getriebene Ranking-Methodik wie Runde 1/2, erneut angewendet: alle
    # verbleibenden Fallback-Karten mit Gesamt-Quantity >=10 ueber alle
    # 1.585 echten Decks, NACHDEM die 4 neuen generellen Regex-Regeln aus
    # Runde 3 bereits angewendet wurden. Siehe
    # Docs/curated_overrides_expansion_v4_74_0.md fuer Details.
    # -----------------------------------------------------------------
    "Desecrate Reality": dict(
        role="Interaction",
        effect_tags=["removal_single_exile"],
        simple_effect="for each opponent, exile up to one target permanent with even mana value; adamant: also return an odd-mv permanent card from graveyard to battlefield (conditional exile removal + possible bonus recursion)",
        halbwertszeit=0.7,
    ),
    "Cyberman Patrol": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="your artifact creatures have afflict 3 (whenever blocked, defending player loses 3 life) - artifact-creature tribal payoff",
        halbwertszeit=0.5,
    ),
    "Strionic Resonator": dict(
        role="Strategy",
        effect_tags=["trigger_copy_repeatable"],
        simple_effect="{2}, {T}: copy target triggered ability you control, may choose new targets (repeatable trigger-doubling utility)",
        halbwertszeit=0.65,
    ),
    "Angel of Vitality": dict(
        role="Strategy",
        effect_tags=["lifegain"],
        simple_effect="flying; life you gain is increased by 1; gets +2/+2 as long as you have 25+ life (lifegain payoff/threshold body)",
        halbwertszeit=0.6,
    ),
    "Nine-Lives Familiar": dict(
        role="Strategy",
        effect_tags=["self_recursion_repeatable"],
        simple_effect="enters with 8 revival counters if cast; when it dies with a revival counter, returns to the battlefield with one fewer counter (repeatable self-recursion, resilient threat)",
        halbwertszeit=0.45,
    ),
    "Unleash Fury": dict(
        role="Strategy",
        effect_tags=["combat_trick_finisher"],
        simple_effect="double target creature's power until end of turn (one-time combat finisher)",
        halbwertszeit=0.6,
    ),
    "Sunbird's Invocation": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="whenever you cast a spell from hand, reveal the top X cards (X = that spell's mana value) and may cast a spell with mana value X or less from among them for free (repeatable spell-cast-triggered value engine)",
        halbwertszeit=0.6,
    ),
    "Crawlspace": dict(
        role="Interaction",
        effect_tags=["tempo_lockdown"],
        simple_effect="no more than two creatures can attack you each combat (persistent defensive combat restriction)",
        halbwertszeit=0.7,
    ),
    "Chain Reaction": dict(
        role="Interaction",
        effect_tags=["removal_board"],
        simple_effect="deals X damage to each creature, X = total number of creatures on the battlefield (scalable one-time board wipe)",
        halbwertszeit=0.85,
    ),
    "Invigorate": dict(
        role="Strategy",
        effect_tags=["combat_trick_finisher"],
        simple_effect="alternate cost: an opponent gains 3 life instead of paying mana if you control a Forest; target creature gets +4/+4 until end of turn (free/cheap one-time combat trick)",
        halbwertszeit=0.55,
    ),
    "Skyhunter Strike Force": dict(
        role="Strategy",
        effect_tags=["melee_payoff"],
        simple_effect="flying; melee (+1/+1 per opponent attacked this combat); lieutenant grants melee to your other creatures while you control your commander (go-wide combat payoff)",
        halbwertszeit=0.5,
    ),
    "Judge's Familiar": dict(
        role="Interaction",
        effect_tags=["counterspell_conditional"],
        simple_effect="flying; sacrifice: counter target instant or sorcery unless its controller pays {1} (one-time conditional counterspell on a flying body)",
        halbwertszeit=0.55,
    ),
    "Silent-Blade Oni": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff", "free_spells_from_exile"],
        simple_effect="ninjutsu; whenever it deals combat damage to a player, look at their hand and may cast a spell from it for free (attack-triggered hand theft/value)",
        halbwertszeit=0.55,
    ),
    "Sower of Discord": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="flying; on ETB choose two players; whenever damage is dealt to one chosen player, the other chosen player also loses that much life (political damage-redirect engine)",
        halbwertszeit=0.4,
    ),
    "Rionya, Fire Dancer": dict(
        role="Strategy",
        effect_tags=["clone_effect", "spellslinger_payoff"],
        simple_effect="beginning of combat on your turn, create X hasty token copies of another target creature you control (X = 1 + instants/sorceries cast this turn), exiled at end step (scalable spellslinger-fueled token-copy finisher)",
        halbwertszeit=0.55,
    ),
    "Dream Devourer": dict(
        role="Strategy",
        effect_tags=["cost_reduction", "combat_trick_finisher"],
        simple_effect="your nonland hand cards without foretell gain foretell at mana cost minus {2}; whenever you foretell a card, gets +2/+0 until end of turn (foretell cost-reduction + combat payoff)",
        halbwertszeit=0.45,
    ),
    "Puppeteer Clique": dict(
        role="Strategy",
        effect_tags=["theft_effect"],
        simple_effect="flying; on ETB, put target creature card from an opponent's graveyard onto the battlefield under your control with haste, exiled at next end step; persist (temporary graveyard theft, recurs itself once)",
        halbwertszeit=0.6,
    ),
    "Druid of Purification": dict(
        role="Interaction",
        effect_tags=["removal_board_conditional"],
        simple_effect="on ETB, starting with you each player may choose an artifact or enchantment they don't control; destroy each permanent chosen this way (multiplayer edict-style removal on artifacts/enchantments)",
        halbwertszeit=0.6,
    ),
    "Heartbeat of Spring": dict(
        role="Ramp",
        effect_tags=["mana_doubler"],
        simple_effect="whenever a player taps a land for mana, that player adds one extra mana of any type that land produced (symmetric mana doubler, usually built around to favor you more)",
        halbwertszeit=0.85,
    ),
    "Shigeki, Jukai Visionary": dict(
        role="Ramp",
        effect_tags=["land_ramp_tutor", "graveyard_recursion"],
        simple_effect="{1}{G}, T, return to hand: reveal top 4, put a land from among them onto the battlefield tapped; channel: discard to return X nonlegendary cards from graveyard to hand (land ramp/dig plus graveyard recursion)",
        halbwertszeit=0.5,
    ),
    "Blade Historian": dict(
        role="Strategy",
        effect_tags=["team_pump_finisher"],
        simple_effect="your attacking creatures have double strike (persistent go-wide combat anthem)",
        halbwertszeit=0.75,
    ),
    "Inventory Management": dict(
        role="Strategy",
        effect_tags=["voltron_aura_equipment"],
        simple_effect="split second; for each Aura and Equipment you control, you may attach it to a creature you control (mass free re-attachment, protected from responses)",
        halbwertszeit=0.55,
    ),
    "Ancient Brass Dragon": dict(
        role="Strategy",
        effect_tags=["attack_trigger_payoff"],
        simple_effect="flying; whenever it deals combat damage to a player, roll a d20 and put creature cards with total mana value up to the result from graveyards onto the battlefield under your control (attack-triggered mass reanimation, any graveyard)",
        halbwertszeit=0.5,
    ),
    "Walking Bulwark": dict(
        role="Strategy",
        effect_tags=["stat_swap_combat"],
        simple_effect="defender; {2}: until end of turn, target defender you control gains haste, can attack, and deals combat damage equal to toughness instead of power (repeatable defender-to-attacker enabler)",
        halbwertszeit=0.45,
    ),
    "Winged Hive Tyrant": dict(
        role="Strategy",
        effect_tags=["counters_matter"],
        simple_effect="flying, haste; your other creatures with counters on them have flying and haste (counters-matter evasion payoff)",
        halbwertszeit=0.5,
    ),
    "Dracogenesis": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "free_permanent_cheat"],
        simple_effect="you may cast Dragon spells without paying their mana costs (tribal Dragons free-cast enabler)",
        halbwertszeit=0.55,
    ),
    "Calamity of the Titans": dict(
        role="Interaction",
        effect_tags=["removal_board_conditional"],
        simple_effect="additional cost: reveal a colorless creature card from hand; exile each creature and planeswalker with mana value less than the revealed card's (scalable conditional board wipe)",
        halbwertszeit=0.75,
    ),
    "Master Transmuter": dict(
        role="Strategy",
        effect_tags=["free_permanent_cheat"],
        simple_effect="{U}, T, return an artifact you control to hand: you may put an artifact card from hand onto the battlefield (repeatable artifact cheat/rebuy engine)",
        halbwertszeit=0.55,
    ),
    "Soulless Jailer": dict(
        role="Interaction",
        effect_tags=["graveyard_hate_lockdown"],
        simple_effect="permanent cards in graveyards can't enter the battlefield; players can't cast noncreature spells from graveyards or exile (broad graveyard/recursion hate)",
        halbwertszeit=0.6,
    ),
    "Faerie Seer": dict(
        role="CardAdvantage",
        effect_tags=["card_selection"],
        simple_effect="flying; on ETB, scry 2 (light card selection on an evasive body)",
        halbwertszeit=0.6,
    ),
    "Demon's Disciple": dict(
        role="Interaction",
        effect_tags=["removal_edict_symmetric"],
        simple_effect="on ETB, each player sacrifices a creature or planeswalker of their choice (one-time symmetric edict)",
        halbwertszeit=0.9,
    ),
    "Ink-Eyes, Servant of Oni": dict(
        role="Strategy",
        effect_tags=["theft_effect", "attack_trigger_payoff"],
        simple_effect="ninjutsu; whenever it deals combat damage to a player, may put target creature card from that player's graveyard onto the battlefield under your control; regenerate (attack-triggered graveyard theft)",
        halbwertszeit=0.5,
    ),
    "Enduring Courage": dict(
        role="Strategy",
        effect_tags=["haste_enabler"],
        simple_effect="whenever another creature you control enters, it gets +2/+0 and haste until end of turn; when it dies as a creature, returns as a (noncreature) enchantment (haste enabler with built-in self-recursion)",
        halbwertszeit=0.5,
    ),
    "Nashi, Moon Sage's Scion": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff", "free_spells_from_exile"],
        simple_effect="ninjutsu; whenever it deals combat damage to a player, exile the top card of each library, playable until end of turn (pay life instead of mana if cast this way) (attack-triggered multi-player impulse draw)",
        halbwertszeit=0.5,
    ),
    "Ancient Silver Dragon": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff", "draw_scaling"],
        simple_effect="flying; whenever it deals combat damage to a player, roll a d20 and draw that many cards; no maximum hand size for the rest of the game (attack-triggered scalable card draw)",
        halbwertszeit=0.55,
    ),
    "Eidolon of Rhetoric": dict(
        role="Interaction",
        effect_tags=["spell_lock"],
        simple_effect="each player can't cast more than one spell each turn (symmetric spell-count restriction, usually built around to favor low-spell-count decks)",
        halbwertszeit=0.65,
    ),
    "The Jolly Balloon Man": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="haste; {1}, T: create a 1/1 flying/hasty token copy of another target creature you control (with altered color/type), sacrificed at end of turn (repeatable one-turn token-copy engine)",
        halbwertszeit=0.5,
    ),
    "Mind's Dilation": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="whenever an opponent casts their first spell each turn, that opponent exiles the top card of their library; you may cast it for free if nonland (repeatable free-cast value off opponents' turns)",
        halbwertszeit=0.55,
    ),
    "Paradox Haze": dict(
        role="Strategy",
        effect_tags=["extra_upkeep_steps"],
        simple_effect="enchant player; enchanted player gets an additional upkeep step each turn (extra-upkeep-trigger payoff enabler, usually attached to yourself)",
        halbwertszeit=0.5,
    ),
    "Polyraptor": dict(
        role="Strategy",
        effect_tags=["clone_effect", "token_creation"],
        simple_effect="enrage: whenever it's dealt damage, create a token copy of it (damage-triggered self-copying engine, explosive with pinger/fight effects)",
        halbwertszeit=0.5,
    ),
    "Deepglow Skate": dict(
        role="Strategy",
        effect_tags=["counter_doubler_effect"],
        simple_effect="on ETB, double the number of each kind of counter on any number of target permanents (one-time counters-matter doubler)",
        halbwertszeit=0.6,
    ),
    "Welding Jar": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="sacrifice: regenerate target artifact (cheap one-time artifact protection)",
        halbwertszeit=0.4,
    ),
    "Single Combat": dict(
        role="Interaction",
        effect_tags=["removal_board_conditional"],
        simple_effect="each player chooses a creature or planeswalker they control and sacrifices the rest; no one can cast creature/planeswalker spells until the end of your next turn (symmetric-looking but usually one-sided board wipe + lockout)",
        halbwertszeit=0.8,
    ),
    "Rampaging Ferocidon": dict(
        role="Interaction",
        effect_tags=["anti_lifegain_lock"],
        simple_effect="menace; players can't gain life; whenever another creature enters, deals 1 damage to that creature's controller (symmetric anti-lifegain lock + go-wide punisher)",
        halbwertszeit=0.55,
    ),
    "Frontier Warmonger": dict(
        role="Strategy",
        effect_tags=["evasion_grant_group"],
        simple_effect="whenever one or more creatures you control attack an opponent or their planeswalker, those creatures gain menace until end of turn (repeatable go-wide evasion grant)",
        halbwertszeit=0.6,
    ),
    "Hunter's Insight": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff"],
        simple_effect="choose target creature you control; whenever it deals combat damage to a player or planeswalker this turn, draw that many cards (one-turn attack-triggered card draw)",
        halbwertszeit=0.65,
    ),
    "Mistblade Shinobi": dict(
        role="Interaction",
        effect_tags=["bounce_single_flexible"],
        simple_effect="ninjutsu; whenever it deals combat damage to a player, may return target creature that player controls to its owner's hand (attack-triggered bounce)",
        halbwertszeit=0.6,
    ),
    "Scheming Symmetry": dict(
        role="CardAdvantage",
        effect_tags=["tutor_any_card"],
        simple_effect="choose two target players; each searches their library for a card and puts it on top (symmetric tutor, usually used to immediately draw the found card yourself)",
        halbwertszeit=0.7,
    ),
    "Mai, Scornful Striker": dict(
        role="Interaction",
        effect_tags=["symmetric_burn_tax"],
        simple_effect="first strike; whenever a player casts a noncreature spell, they lose 2 life (symmetric tax on noncreature spells)",
        halbwertszeit=0.55,
    ),
    "Hex Magic": dict(
        role="CardAdvantage",
        effect_tags=["wheel_effect"],
        simple_effect="exile all cards from your hand, then draw that many cards; may play the exiled cards until the end of your next turn (one-time hand refill that also banks the old hand as playable)",
        halbwertszeit=0.7,
    ),
    "Keen Duelist": dict(
        role="CardAdvantage",
        effect_tags=["card_selection"],
        simple_effect="upkeep: you and target opponent each reveal your top card, each lose life equal to the mana value of the other's revealed card, then each put your own revealed card into your hand (repeatable symmetric value + life cost)",
        halbwertszeit=0.5,
    ),
    "Sanctum of Stone Fangs": dict(
        role="Strategy",
        effect_tags=["life_drain_direct"],
        simple_effect="at your first main phase, each opponent loses X life and you gain X life, X = number of Shrines you control (repeatable scalable drain)",
        halbwertszeit=0.5,
    ),
    "Nature's Will": dict(
        role="Strategy",
        effect_tags=["attack_trigger_payoff"],
        simple_effect="whenever one or more creatures you control deal combat damage to a player, tap all lands that player controls and untap all your lands (attack-triggered mana denial + ramp)",
        halbwertszeit=0.55,
    ),
    "Monstrous Vortex": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="whenever you cast a creature spell with power 5 or greater, discover X (X = that spell's mana value) (repeatable big-creature-triggered discover engine)",
        halbwertszeit=0.55,
    ),
    "Derevi, Empyrial Tactician": dict(
        role="Strategy",
        effect_tags=["attack_trigger_payoff"],
        simple_effect="flying; on ETB and whenever a creature you control deals combat damage to a player, you may tap or untap target permanent; can be cast from the command zone for {1}{G}{W}{U} (repeatable tap/untap utility engine)",
        halbwertszeit=0.6,
    ),
    "Reunion of the House": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="return any number of target creature cards with total power 10 or less from your graveyard to the battlefield; exile itself (scalable one-time mass reanimation)",
        halbwertszeit=0.75,
    ),
    "Wave of Reckoning": dict(
        role="Interaction",
        effect_tags=["removal_board"],
        simple_effect="each creature deals damage to itself equal to its power (symmetric one-time board wipe, hits high-power creatures hardest)",
        halbwertszeit=0.85,
    ),
    "Isochron Scepter": dict(
        role="Strategy",
        effect_tags=["imprint_spell_engine"],
        simple_effect="imprint an instant with mana value 2 or less from hand on ETB; {2}, T: copy the exiled card, may cast the copy for free (repeatable free-recast engine for one chosen cheap instant)",
        halbwertszeit=0.6,
    ),
    "Mathemagics": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling"],
        simple_effect="target player draws 2^X cards, X chosen at cast (exponentially scalable one-time card draw, usually cast on yourself)",
        halbwertszeit=0.7,
    ),
    "Spectral Deluge": dict(
        role="Interaction",
        effect_tags=["bounce_board_conditional"],
        simple_effect="return each creature an opponent controls with toughness up to your Island count to its owner's hand; has foretell (scalable one-time mass bounce)",
        halbwertszeit=0.75,
    ),
    "Caged Sun": dict(
        role="Strategy",
        effect_tags=["mana_doubler", "tribal_synergy_lord"],
        simple_effect="choose a color on ETB; your creatures of that color get +1/+1; mana abilities that add mana of that color add one extra (color-focused anthem + mana doubler)",
        halbwertszeit=0.75,
    ),
    "Run Away Together": dict(
        role="Interaction",
        effect_tags=["bounce_single_flexible"],
        simple_effect="choose two target creatures controlled by different players; return them to their owners' hands (flexible 2-for-1 bounce, often political)",
        halbwertszeit=0.55,
    ),
    "Innocent Blood": dict(
        role="Interaction",
        effect_tags=["removal_edict_symmetric"],
        simple_effect="each player sacrifices a creature of their choice (one-time symmetric edict, cheap and colorshifted-agnostic in black)",
        halbwertszeit=0.95,
    ),
    "Patriarch's Bidding": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="each player chooses a creature type; each player returns all creature cards of a type chosen this way from graveyard to battlefield (symmetric-looking but usually built around to favor a wide single-type board)",
        halbwertszeit=0.7,
    ),
    "Soul Shatter": dict(
        role="Interaction",
        effect_tags=["removal_edict_symmetric"],
        simple_effect="each opponent sacrifices a creature or planeswalker with the greatest mana value among those they control (scalable one-time symmetric-per-opponent edict)",
        halbwertszeit=0.85,
    ),
    "Grenzo, Havoc Raiser": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff", "free_spells_from_exile"],
        simple_effect="whenever a creature you control deals combat damage to a player, choose to goad a creature they control or exile their top card and let you cast it with any mana this turn (flexible repeatable attack-triggered value/goad)",
        halbwertszeit=0.5,
    ),
    "Liquimetal Coating": dict(
        role="Strategy",
        effect_tags=["type_change_utility"],
        simple_effect="{T}: target permanent becomes an artifact in addition to its other types until end of turn (niche type-change enabler/combo piece)",
        halbwertszeit=0.35,
    ),
    "Harsh Mentor": dict(
        role="Interaction",
        effect_tags=["tempo_lockdown"],
        simple_effect="whenever an opponent activates a nonmana ability of an artifact, creature, or land, deals 2 damage to that player (persistent tax/punisher on activated abilities)",
        halbwertszeit=0.55,
    ),
    "Fated Firepower": dict(
        role="Strategy",
        effect_tags=["damage_boost_flat"],
        simple_effect="flash; enters with X fire counters; your damage sources deal that many extra damage to opponents/their permanents (scalable persistent damage amplifier)",
        halbwertszeit=0.6,
    ),
    "Sylvan Anthem": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="your green creatures get +1/+1; whenever a green creature you control enters, scry 1 (green-color anthem + card selection payoff)",
        halbwertszeit=0.7,
    ),
    "Omnath, Locus of Mana": dict(
        role="Strategy",
        effect_tags=["mana_retention_payoff"],
        simple_effect="doesn't lose unspent green mana as steps/phases end; gets +1/+1 for each unspent green mana you have (mana-sink payoff, rewards holding up green mana)",
        halbwertszeit=0.6,
    ),
    "Wrenn and Seven": dict(
        role="Strategy",
        effect_tags=["land_ramp_mass_burst", "mass_reanimation_own_graveyard"],
        simple_effect="planeswalker: dig for lands into hand, mass land drop from hand, make a land-scaling Treefolk token, or (ultimate) return all permanent cards from graveyard to hand with an emblem for no max hand size (flexible land/graveyard value engine)",
        halbwertszeit=0.65,
    ),
    "Force of Vigor": dict(
        role="Interaction",
        effect_tags=["removal_board_scalable"],
        simple_effect="free alternate cost (exile a green card from hand) if not your turn; destroy up to two target artifacts and/or enchantments (scalable, often free, 2-target removal)",
        halbwertszeit=0.8,
    ),
    "Soulcatchers' Aerie": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="whenever a Bird you control dies, put a feather counter on this; your Birds get +1/+1 per feather counter (tribal Birds scaling anthem)",
        halbwertszeit=0.55,
    ),
    "Lim-D\u00fbl's Vault": dict(
        role="CardAdvantage",
        effect_tags=["card_selection"],
        simple_effect="look at the top 5 cards of your library; repeatedly pay 1 life to shuffle them back and look at the top 5 again; keep the final 5 on top in chosen order (deep, repeatable library-ordering dig)",
        halbwertszeit=0.7,
    ),
    "Scroll Rack": dict(
        role="CardAdvantage",
        effect_tags=["card_selection"],
        simple_effect="{1}, T: exile any number of hand cards face down, draw that many from the top of your library, then put the exiled cards back on top in any order (repeatable hand/library filtering engine)",
        halbwertszeit=0.65,
    ),
    "Thousand-Faced Shadow": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="ninjutsu; flying; when it enters from hand while attacking, create an attacking token copy of another target attacking creature (attack-triggered one-time token copy)",
        halbwertszeit=0.5,
    ),
    "Diregraf Captain": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord", "life_drain_direct"],
        simple_effect="deathtouch; your other Zombies get +1/+1; whenever another Zombie you control dies, target opponent loses 1 life (Zombie tribal anthem + drain payoff)",
        halbwertszeit=0.55,
    ),
    "Brainstealer Dragon": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="flying; end step: exile the top card of each opponent's library, playable by you for as long as it stays exiled, with any-color mana; when a nonland permanent an opponent owns enters under your control, they lose life equal to its mana value (repeatable card theft/value engine)",
        halbwertszeit=0.5,
    ),
    "Enhanced Surveillance": dict(
        role="CardAdvantage",
        effect_tags=["card_selection"],
        simple_effect="look at two additional cards each time you surveil; exile this: shuffle your graveyard into your library (repeatable card-selection amplifier plus one-shot graveyard reset)",
        halbwertszeit=0.55,
    ),
    "Darkstar Augur": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling"],
        simple_effect="offspring {B}; flying; upkeep: reveal and draw the top card, lose life equal to its mana value (Dark-Confidant-style repeatable risky card advantage)",
        halbwertszeit=0.8,
    ),
    "Hunting Velociraptor": dict(
        role="Strategy",
        effect_tags=["cost_reduction"],
        simple_effect="first strike; your Dinosaur spells have prowl (cast for a cheaper alternate cost if you dealt combat damage with a shared creature type this turn) (tribal cost-reduction enabler)",
        halbwertszeit=0.4,
    ),
    "Composer of Spring": dict(
        role="Ramp",
        effect_tags=["extra_land_drop"],
        simple_effect="constellation: whenever an enchantment you control enters, put a land (or, with 6+ enchantments, a creature or land) from hand onto the battlefield tapped (repeatable enchantment-triggered extra land drop)",
        halbwertszeit=0.55,
    ),
    "Lurrus of the Dream-Den": dict(
        role="Strategy",
        effect_tags=["graveyard_recasting_engine"],
        simple_effect="companion (cheap-permanent deck restriction); lifelink; once each turn, cast a permanent spell with mana value 2 or less from your graveyard (repeatable cheap-permanent recursion)",
        halbwertszeit=0.75,
    ),
    "Niv-Mizzet, Visionary": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling"],
        simple_effect="flying; no maximum hand size; whenever a source you control deals noncombat damage to an opponent, draw that many cards (repeatable burn-to-draw conversion)",
        halbwertszeit=0.65,
    ),
    "Prismari, the Inspiration": dict(
        role="Strategy",
        effect_tags=["spell_copy"],
        simple_effect="flying; ward - pay 5 life; your instant and sorcery spells have storm (persistent storm-granting engine)",
        halbwertszeit=0.6,
    ),
    "Hazel of the Rootbloom": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="T, pay 2 life, tap X untapped tokens you control: add X mana of any colors; end step: create a copy of a token you control (two copies if it's a Squirrel) (token-fueled mana ramp + token doubling)",
        halbwertszeit=0.5,
    ),
    "Owlin Spiralmancer": dict(
        role="Strategy",
        effect_tags=["spell_copy"],
        simple_effect="flying, vigilance; whenever you cast your first spell with {X} in its cost each turn, you may copy it with new targets (repeatable X-spell copy engine)",
        halbwertszeit=0.5,
    ),
    "Hostage Taker": dict(
        role="Interaction",
        effect_tags=["removal_single_exile"],
        simple_effect="on ETB, exile target creature or artifact another player controls until this leaves the battlefield; you may cast it with any mana while exiled (flexible temporary removal + theft)",
        halbwertszeit=0.75,
    ),
    "High Alert": dict(
        role="Strategy",
        effect_tags=["stat_swap_combat"],
        simple_effect="your creatures deal combat damage equal to toughness rather than power and can attack despite defender; {2}{W}{U}: untap target creature (defender-matters toughness payoff)",
        halbwertszeit=0.55,
    ),
    "Stalwart Shield-Bearers": dict(
        role="Strategy",
        effect_tags=["defensive_static_buff"],
        simple_effect="defender; your other creatures with defender get +0/+2 (defender-tribal defensive anthem)",
        halbwertszeit=0.45,
    ),
    "Arboreal Grazer": dict(
        role="Ramp",
        effect_tags=["extra_land_drop"],
        simple_effect="reach; on ETB, may put a land card from hand onto the battlefield tapped (one-time land ramp on a defensive body)",
        halbwertszeit=0.8,
    ),
    "Aether Spike": dict(
        role="Interaction",
        effect_tags=["counterspell_conditional"],
        simple_effect="choose target spell; get two energy counters, then may pay any amount of energy; counter that spell unless its controller pays {1} per energy paid (scalable one-time conditional counterspell)",
        halbwertszeit=0.55,
    ),
    "Aetherworks Marvel": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="whenever a permanent you control dies, get an energy counter; T, pay 6 energy: look at the top 6 cards of your library and may cast one for free (repeatable big free-cast engine, fueled by attrition)",
        halbwertszeit=0.55,
    ),
    "Aurora Shifter": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="whenever it deals combat damage to a player, get that many energy; beginning of combat, may pay 2 energy to become a copy of another target creature you control (repeatable shapeshifting combat value)",
        halbwertszeit=0.4,
    ),
    "Decoction Module": dict(
        role="Strategy",
        effect_tags=["bounce_own_creature_value"],
        simple_effect="whenever a creature you control enters, get an energy counter; {4}, T: return target creature you control to its owner's hand (repeatable self-bounce ETB replay engine, energy-gated)",
        halbwertszeit=0.35,
    ),
    "Comeuppance": dict(
        role="Interaction",
        effect_tags=["damage_prevention_redirect"],
        simple_effect="prevent all damage that would be dealt to you and your planeswalkers this turn by sources you don't control, and redirect that damage back to those sources/their controllers (one-time full damage prevention + reflect, not combat-only)",
        halbwertszeit=0.55,
    ),
    "Officious Interrogation": dict(
        role="CardAdvantage",
        effect_tags=["investigate_value"],
        simple_effect="costs {W}{U} more per target beyond the first; investigate X times per chosen player, X = total creatures that player controls (scalable multi-target Clue generation)",
        halbwertszeit=0.6,
    ),
    "Primevals' Glorious Rebirth": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="legendary sorcery (needs a legendary creature/planeswalker to cast); return all legendary permanent cards from your graveyard to the battlefield (one-time mass legendary reanimation)",
        halbwertszeit=0.85,
    ),
    "Hope of Ghirapur": dict(
        role="Interaction",
        effect_tags=["tempo_lockdown"],
        simple_effect="flying; legendary; sacrifice: until your next turn, a player it dealt combat damage to this turn can't cast noncreature spells (one-time attack-triggered spell-lock)",
        halbwertszeit=0.5,
    ),
    "Drannith Magistrate": dict(
        role="Interaction",
        effect_tags=["spell_lock"],
        simple_effect="opponents can't cast spells from anywhere other than their hands (persistent lockdown on flashback/cascade/cast-from-exile strategies)",
        halbwertszeit=0.75,
    ),
    "Clockspinning": dict(
        role="Strategy",
        effect_tags=["counters_matter"],
        simple_effect="buyback {3}; move a counter from one permanent or suspended card to another (or add another of that kind), returns to hand if buyback paid (repeatable counter-manipulation utility)",
        halbwertszeit=0.4,
    ),
    "Chakram Retriever": dict(
        role="Ramp",
        effect_tags=["untap_utility_repeatable"],
        simple_effect="partner with Chakram Slinger; whenever you cast a spell during your turn, untap target creature (repeatable creature-untap utility, often abused for mana dorks)",
        halbwertszeit=0.5,
    ),
    "Mindslicer": dict(
        role="Strategy",
        effect_tags=["discard_disruption"],
        simple_effect="when it dies, each player discards their hand (symmetric one-time hand disruption, usually paired with a sacrifice outlet to time it favorably)",
        halbwertszeit=0.55,
    ),
    "Vona's Hunger": dict(
        role="Interaction",
        effect_tags=["removal_edict_scalable"],
        simple_effect="ascend; each opponent sacrifices a creature of their choice, or (with the city's blessing) half their creatures rounded up (scalable one-time edict removal)",
        halbwertszeit=0.75,
    ),
    "Knollspine Dragon": dict(
        role="CardAdvantage",
        effect_tags=["wheel_effect"],
        simple_effect="flying; on ETB, may discard your hand and draw cards equal to the damage dealt to target opponent this turn (conditional one-time hand refill scaled by damage dealt)",
        halbwertszeit=0.4,
    ),
    "Ruxa, Patient Professor": dict(
        role="Strategy",
        effect_tags=["graveyard_recursion"],
        simple_effect="whenever it enters or attacks, return target creature card with no abilities from your graveyard to hand; your no-ability creatures get +1/+1 and may deal combat damage as though unblocked (vanilla-creatures-matter recursion/payoff engine)",
        halbwertszeit=0.45,
    ),
    "Helix Pinnacle": dict(
        role="Strategy",
        effect_tags=["alt_win_condition"],
        simple_effect="shroud; X: put X tower counters on this; at your upkeep, win the game if it has 100+ tower counters (slow-burn ramp-fueled alternate win condition)",
        halbwertszeit=0.5,
    ),
    "Life's Legacy": dict(
        role="CardAdvantage",
        effect_tags=["draw_scaling"],
        simple_effect="additional cost: sacrifice a creature; draw cards equal to the sacrificed creature's power (sacrifice-fueled scalable card draw)",
        halbwertszeit=0.6,
    ),
    "Endurance": dict(
        role="Interaction",
        effect_tags=["graveyard_hate_exile"],
        simple_effect="flash, reach; on ETB, up to one target player shuffles their graveyard into their library; evoke by exiling a green card from hand (free graveyard hate on a resilient body)",
        halbwertszeit=0.65,
    ),
    "Timberwatch Elf": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="{T}: target creature gets +X/+X until end of turn, X = number of Elves on the battlefield (scalable tribal pump)",
        halbwertszeit=0.5,
    ),
    "Imposter Mech": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="may enter as a copy of a creature an opponent controls, except it's a Vehicle with crew 3 (flexible one-time clone value, dodges some clone hate as a Vehicle)",
        halbwertszeit=0.5,
    ),
    "Solemnity": dict(
        role="Interaction",
        effect_tags=["counters_lockdown"],
        simple_effect="players can't get counters; counters can't be put on artifacts, creatures, enchantments, or lands (broad symmetric anti-counters hate)",
        halbwertszeit=0.55,
    ),
    "The Lord of the Eagles": dict(
        role="Strategy",
        effect_tags=["cost_reduction"],
        simple_effect="flash; costs {X} less, X = total power of your flying creatures; flying (tribal flying cost-reduction enabler)",
        halbwertszeit=0.55,
    ),
    "Storm of Souls": dict(
        role="Strategy",
        effect_tags=["mass_reanimation_own_graveyard"],
        simple_effect="return all creature cards from your graveyard to the battlefield as 1/1 flying Spirits (in addition to other types); exile itself (one-time mass reanimation, normalizes stats)",
        halbwertszeit=0.85,
    ),
    "Silver-Fur Master": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="ninjutsu abilities you activate cost {1} less; your other Ninjas and Rogues get +1/+1 (Ninja/Rogue tribal cost-reduction + anthem)",
        halbwertszeit=0.5,
    ),
    "Cleaver Skaab": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="{3}, T, sacrifice another Zombie: create two token copies of the sacrificed creature (sacrifice-fueled token-doubling engine)",
        halbwertszeit=0.5,
    ),
    "Death Baron": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="Skeletons you control and your other Zombies get +1/+1 and deathtouch (Skeleton/Zombie tribal anthem)",
        halbwertszeit=0.7,
    ),
    "Rooftop Storm": dict(
        role="Ramp",
        effect_tags=["free_permanent_cheat"],
        simple_effect="you may pay {0} rather than the mana cost for Zombie creature spells you cast (tribal free-cast enabler)",
        halbwertszeit=0.55,
    ),
    "Soothing of Sm\u00e9agol": dict(
        role="Interaction",
        effect_tags=["bounce_single_flexible"],
        simple_effect="return target nontoken creature to its owner's hand; the Ring tempts you (one-time bounce with a minor upside)",
        halbwertszeit=0.6,
    ),
    "Lord of the Void": dict(
        role="Strategy",
        effect_tags=["theft_effect"],
        simple_effect="flying; whenever it deals combat damage to a player, exile the top 7 of that player's library, then put a creature card from among them onto the battlefield under your control (attack-triggered creature theft)",
        halbwertszeit=0.55,
    ),
    "No Mercy": dict(
        role="Interaction",
        effect_tags=["removal_board_repeatable"],
        simple_effect="whenever a creature deals damage to you, destroy it (repeatable defensive deterrent/removal)",
        halbwertszeit=0.65,
    ),
    "Persistent Constrictor": dict(
        role="Interaction",
        effect_tags=["removal_via_counters_repeatable"],
        simple_effect="each opponent's upkeep, they lose 1 life and you put a -1/-1 counter on up to one target creature they control; persist (repeatable slow removal, recurs itself once)",
        halbwertszeit=0.55,
    ),
    "Rug of Smothering": dict(
        role="Strategy",
        effect_tags=["symmetric_burn_tax"],
        simple_effect="flying; whenever a player casts a spell, they lose 1 life for each spell they've cast this turn (symmetric spellslinger tax, usually favors slower decks)",
        halbwertszeit=0.5,
    ),
    "Fandaniel, Telophoroi Ascian": dict(
        role="Interaction",
        effect_tags=["removal_edict_scalable"],
        simple_effect="whenever you cast an instant or sorcery, surveil 1; end step: each opponent sacrifices a nontoken creature or loses 2 life per instant/sorcery card in your graveyard (spellslinger-fueled repeatable edict/burn)",
        halbwertszeit=0.5,
    ),
    "Heartless Hidetsugu": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="T: deals damage to each player equal to half their life total, rounded down (repeatable symmetric life-based burn, usually built around to survive it)",
        halbwertszeit=0.6,
    ),
    "Jaya's Immolating Inferno": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="legendary sorcery (needs a legendary creature/planeswalker to cast); deals X damage to each of up to three targets (scalable multi-target burn/removal)",
        halbwertszeit=0.85,
    ),
    "Somberwald Sage": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="T: add 3 mana of one color, spendable only on creature spells (restricted but large mana dork)",
        halbwertszeit=0.6,
    ),
    "Berserk": dict(
        role="Strategy",
        effect_tags=["combat_trick_finisher"],
        simple_effect="cast only before the combat damage step; target creature gains trample and gets +X/+0 (X = its power) until end of turn; destroy it at end step if it attacked (huge one-time combat finisher with a drawback)",
        halbwertszeit=0.75,
    ),
    "Champion of the Path": dict(
        role="Strategy",
        effect_tags=["etb_ping_payoff"],
        simple_effect="additional cost: exile an Elemental you control or from hand; whenever another Elemental you control enters, it deals damage equal to its power to each opponent; when this leaves, return the exiled card (tribal Elemental ETB burn engine)",
        halbwertszeit=0.5,
    ),
    "Kaheera, the Orphanguard": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="companion (creature-type deck restriction); vigilance; your other Cats/Elementals/Nightmares/Dinosaurs/Beasts get +1/+1 and vigilance (multi-tribal anthem)",
        halbwertszeit=0.55,
    ),
    "King of the Pride": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="your other Cats get +2/+1 (Cat tribal anthem)",
        halbwertszeit=0.65,
    ),
    "Descendants' Path": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="upkeep: reveal your top card; if it's a creature card sharing a type with one you control, you may cast it for free, otherwise put it on the bottom (repeatable conditional tribal free-cast engine)",
        halbwertszeit=0.5,
    ),
    "Song of the Worldsoul": dict(
        role="Strategy",
        effect_tags=["token_creation"],
        simple_effect="whenever you cast a spell, populate (create a copy of a creature token you control) (spell-count-fueled token-copy engine)",
        halbwertszeit=0.55,
    ),
    "Valley Questcaller": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="whenever one or more other Rabbits/Bats/Birds/Mice you control enter, scry 1; those creatures get +1/+1 (multi-tribal anthem + card selection)",
        halbwertszeit=0.6,
    ),
    "Collective Voyage": dict(
        role="Ramp",
        effect_tags=["land_ramp_mass_burst"],
        simple_effect="join forces: each player may pay mana; each searches for up to X basic lands (X = total mana paid) and puts them onto the battlefield tapped (group-fueled scalable mass land ramp)",
        halbwertszeit=0.6,
    ),
    "Legion Lieutenant": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="your other Vampires get +1/+1 (Vampire tribal anthem)",
        halbwertszeit=0.65,
    ),
    "Olivia's Wrath": dict(
        role="Interaction",
        effect_tags=["removal_board"],
        simple_effect="each non-Vampire creature gets -X/-X until end of turn, X = number of Vampires you control (tribal-scaled asymmetric board wipe)",
        halbwertszeit=0.7,
    ),
    "Ghost Vacuum": dict(
        role="Interaction",
        effect_tags=["graveyard_hate_exile"],
        simple_effect="T: exile target card from a graveyard; {6}, T, sacrifice: creatures exiled this way become 1/1 flying Spirits on the battlefield under your control (graveyard hate that banks a delayed payoff)",
        halbwertszeit=0.4,
    ),
    "Ol\u00f3rin's Searing Light": dict(
        role="Interaction",
        effect_tags=["removal_board_scalable"],
        simple_effect="each opponent exiles a creature with the greatest power among theirs; spell mastery: also deals damage to each opponent equal to the power of the creature they exiled (scalable multi-opponent removal + optional burn)",
        halbwertszeit=0.75,
    ),
    "Penance": dict(
        role="Interaction",
        effect_tags=["combat_protection_free"],
        simple_effect="put a card from hand on top of your library: prevent the next damage a chosen black or red source would deal this turn (repeatable card-cost-based damage prevention)",
        halbwertszeit=0.45,
    ),
    "Sakura-Tribe Scout": dict(
        role="Ramp",
        effect_tags=["extra_land_drop"],
        simple_effect="T: may put a land card from hand onto the battlefield (one-time land ramp via activated ability, dodges summoning-sickness restrictions on ETB ramp)",
        halbwertszeit=0.7,
    ),
    "Magus of the Candelabra": dict(
        role="Ramp",
        effect_tags=["untap_utility_repeatable"],
        simple_effect="{X}, T: untap X target lands (scalable repeatable mana burst)",
        halbwertszeit=0.55,
    ),
    "Demon of Fate's Design": dict(
        role="Strategy",
        effect_tags=["cost_reduction"],
        simple_effect="flying, trample; once each turn, cast an enchantment spell by paying life equal to its mana value instead of mana; {2}{B}, sacrifice another enchantment: gets +X/+0 (X = sacrificed enchantment's mana value) (enchantment-payoff cost reduction + pump)",
        halbwertszeit=0.5,
    ),
    "Firebending Student": dict(
        role="Ramp",
        effect_tags=["mana_rock_or_dork"],
        simple_effect="prowess; firebending X (X = this creature's power): whenever it attacks, add X red mana usable until end of combat (combat-conditional scalable mana burst)",
        halbwertszeit=0.45,
    ),
    "Snapcaster Mage": dict(
        role="CardAdvantage",
        effect_tags=["graveyard_recasting_engine"],
        simple_effect="flash; on ETB, target instant or sorcery card in your graveyard gains flashback equal to its mana cost until end of turn (classic one-shot graveyard-spell rebuy on a flash body)",
        halbwertszeit=0.85,
    ),
    "Kess, Dissident Mage": dict(
        role="CardAdvantage",
        effect_tags=["graveyard_recasting_engine"],
        simple_effect="flying; once each turn, cast an instant or sorcery spell from your graveyard (exiled instead of going to graveyard again if cast this way) (repeatable graveyard-spell recursion)",
        halbwertszeit=0.75,
    ),
    "Chameleon, Master of Disguise": dict(
        role="Strategy",
        effect_tags=["clone_effect"],
        simple_effect="may enter as a copy of a creature you control (keeping its own name); mayhem lets it be cast from graveyard if discarded this turn (flexible clone value with graveyard recovery)",
        halbwertszeit=0.55,
    ),
    "Leyline Tyrant": dict(
        role="Strategy",
        effect_tags=["mana_retention_payoff"],
        simple_effect="flying; doesn't lose unspent red mana as steps/phases end; when it dies, may pay any amount of red mana to deal that much damage to any target (mana-sink payoff + death-triggered burn)",
        halbwertszeit=0.45,
    ),
    "Regal Behemoth": dict(
        role="Strategy",
        effect_tags=["monarch_engine"],
        simple_effect="trample; on ETB, become the monarch; while you're the monarch, tapping a land for mana adds one extra mana of any color (monarch card-draw engine + conditional mana doubler)",
        halbwertszeit=0.5,
    ),
    "Temple Altisaur": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="if a source would deal damage to another Dinosaur you control, prevent all but 1 of that damage (persistent tribal damage-reduction protection)",
        halbwertszeit=0.55,
    ),
    "Whitemane Lion": dict(
        role="Strategy",
        effect_tags=["blink_flicker"],
        simple_effect="flash; on ETB, return a creature you control to its owner's hand (cheap self-bounce, classic ETB-replay combo piece)",
        halbwertszeit=0.55,
    ),
    "The Pride of Hull Clade": dict(
        role="CardAdvantage",
        effect_tags=["attack_trigger_payoff"],
        simple_effect="costs {X} less, X = total toughness of creatures you control; defender; {2}{U}{U}: target creature you control gets +1/+0, gains combat-damage-triggered draw equal to its toughness, and can attack despite defender (toughness-matters cost reduction + granted attack-trigger draw)",
        halbwertszeit=0.45,
    ),
    "Protection Magic": dict(
        role="Interaction",
        effect_tags=["protection_grant"],
        simple_effect="put a shield counter on each of up to three target creatures (scalable one-time protection from damage/destruction)",
        halbwertszeit=0.7,
    ),
    "Ancient Lumberknot": dict(
        role="Strategy",
        effect_tags=["stat_swap_combat"],
        simple_effect="your creatures with toughness greater than power deal combat damage equal to toughness instead of power (conditional toughness-matters payoff)",
        halbwertszeit=0.5,
    ),
    "Long-Range Sensor": dict(
        role="CardAdvantage",
        effect_tags=["free_spells_from_exile"],
        simple_effect="whenever you attack a player, put a charge counter on this; {1}, remove two charge counters: discover 4 (attack-fueled repeatable discover engine)",
        halbwertszeit=0.55,
    ),
    "Th\u00e9oden, King of Rohan": dict(
        role="Strategy",
        effect_tags=["tribal_synergy_lord"],
        simple_effect="whenever Th\u00e9oden or another Human you control enters, target creature gains double strike until end of turn (Human-tribal combat-trigger payoff)",
        halbwertszeit=0.5,
    ),
    "Aether Revolt": dict(
        role="Strategy",
        effect_tags=["damage_boost_flat"],
        simple_effect="revolt: your noncombat damage sources deal 2 extra damage while a permanent left the battlefield under your control this turn; whenever you get energy, deals that much damage to any target (conditional damage amplifier + energy-fueled burn)",
        halbwertszeit=0.45,
    ),
    "Confiscation Coup": dict(
        role="Strategy",
        effect_tags=["theft_effect"],
        simple_effect="choose target artifact or creature; get four energy, then may pay energy equal to its mana value to gain control of it (energy-gated one-time theft)",
        halbwertszeit=0.55,
    ),
    "Galvanic Discharge": dict(
        role="Interaction",
        effect_tags=["removal_or_burn_scalable"],
        simple_effect="choose target creature or planeswalker; get three energy, then may pay any amount of energy to deal that much damage to it (scalable energy-gated removal/burn)",
        halbwertszeit=0.7,
    ),
    "Thundermane Dragon": dict(
        role="CardAdvantage",
        effect_tags=["play_from_top_of_library"],
        simple_effect="flying; may look at the top card of your library any time; may cast creature spells with power 4+ from the top of your library, gaining haste (top-of-library value engine on a flying body)",
        halbwertszeit=0.55,
    ),
    "Iroh, Grand Lotus": dict(
        role="CardAdvantage",
        effect_tags=["graveyard_recasting_engine"],
        simple_effect="firebending 2; on your turn, non-Lesson instant/sorcery cards in your graveyard have flashback equal to their mana cost, and Lesson cards have flashback {1} (persistent broad graveyard-spell recasting engine)",
        halbwertszeit=0.6,
    ),
    "Erdwal Illuminator": dict(
        role="CardAdvantage",
        effect_tags=["investigate_value"],
        simple_effect="flying; whenever you investigate for the first time each turn, investigate an additional time (repeatable Clue-doubling engine)",
        halbwertszeit=0.5,
    ),
}


# ---------------------------------------------------------------------------
# Regelbasierte Muster (Stage 1). Reihenfolge = Prioritaet innerhalb einer Rolle.
# Alle Muster arbeiten auf dem lowercased oracle_text.

_INTERACTION_RULES = [
    (r"destroy all|exile all (artifacts|creatures|enchantments|permanents|nonland permanents|graveyards)"
     r"|deals? \d+ damage to (each|all)|each creature gets? -\d+/-\d+|-x/-x to (each|all)|all creatures get -"
     r"|each player sacrifices all permanents", "removal_board"),
    (r"counter target (\w+ )?spell", "counterspell"),
    (r"exile target (nonland |non-creature |non-token )?(creature|permanent|artifact|enchantment|planeswalker|player)", "removal_single_exile"),
    (r"destroy target (\w+ )?(creature|permanent|artifact|enchantment|planeswalker)", "removal_single_destroy"),
    (r"deals? \d+ damage to (target (creature|player|opponent)|any target)", "removal_or_burn_single"),
    (r"-\d+/-\d+ to target|target creature gets -\d+/-\d+", "removal_single_debuff"),
    (r"return target (creature|permanent|nonland permanent) to (its|their) owner", "bounce_single"),
    (r"shuffles? (it|that permanent|target permanent) into (their|its owner's) library", "removal_or_tuck_single"),
    (r"can't be countered|hexproof|indestructible|protection from|ward \{", "protection_grant"),
    (r"can't attack|can't block|doesn't untap|skip.*untap step", "tempo_lockdown"),
    # v4.73.0-Nachtrag (CURATED_OVERRIDES-Erweiterung Runde 2): "prevent all
    # combat damage" (Fog-Effekte: Spore Frog, Dolmen Gate, Fog selbst) ist
    # eine eigene, haeufig wiederkehrende Interaction-Vorlage - schuetzt zwar
    # nicht durch Entfernen eines Bedrohers, sondern durch Verhindern von
    # Kampfschaden, gehoert aber klar zur Interaction-Rolle (reaktiver
    # Schutzeffekt), nicht zu Strategy.
    (r"prevent all combat damage", "fog_effect"),
]

_RAMP_RULES = [
    (r"search your library for [^.]*(land|forest|island|swamp|mountain|plains|gate)[^.]*onto the battlefield", "land_ramp_tutor"),
    (r"add (\{|one mana|\d+ mana|mana of any)", "mana_rock_or_dork"),
    (r"create.*treasure token", "treasure_generation"),
    (r"you may play an additional land", "extra_land_drop"),
    (r"lands? you control.*enters? untapped|play.*land.*tapped.*untapped", "land_ramp_misc"),
    # v4.71.0-Nachtrag: "play lands from your graveyard" ist eine eigene,
    # haeufig wiederkehrende Vorlage (Ramunap Excavator, Crucible of Worlds,
    # Conduit of Worlds, Ancient Greenwarden, ...), die von keiner der obigen
    # Regeln erfasst wird (kein "search library", keine "add mana"-Formulierung).
    (r"play lands from your graveyard", "land_recursion"),
    # v4.73.0-Nachtrag: "produces twice/three times as much [mana]" (Mana
    # Reflection, Nyxbloom Ancient) ist eine eigene Mana-Verdoppler-Vorlage,
    # von "add (...)" nicht erfasst (kein "add"-Verb im Satz selbst).
    (r"produces? (twice|three times) as much", "mana_doubler"),
    # v4.74.0-Nachtrag (Runde 3, dieselbe Ranking-Methodik erneut angewendet):
    # "each land is a [Basic Land Type] in addition to its other land types"
    # (Yavimaya Cradle of Growth, Urborg Tomb of Yawgmoth) ist eine eigene,
    # sehr hochfrequente Mana-Fixing-Vorlage (macht jedes Land jeder Farbe
    # zugaenglich), von keiner obigen Regel erfasst.
    (r"each land is a \w+ in addition to its other land types", "land_type_fixing"),
]

_CARD_ADVANTAGE_RULES = [
    (r"search your library for a card", "tutor_any_card"),
    (r"search your library for.*card", "tutor_conditional"),
    (r"draws? (a|an|two|three|four|five|x) (additional )?cards?", "draw_cards"),
    (r"draws? a card for each|draw a card for each", "draw_scaling"),
    (r"look at the top .* cards? of your library.*put.*(hand|battlefield)", "card_selection"),
    (r"reveal cards from the top of your library", "card_selection_reveal"),
    # v4.73.0-Nachtrag: "(look at|reveal) the top card ... if it's a land
    # card ... battlefield ... hand" (Coiling Oracle, Risen Reef, Fecund
    # Greenshell) ist eine eigene, sehr haeufige Landfall-Value-Vorlage, von
    # der obigen "look at the top .* cards? .* put .* hand/battlefield"-Regel
    # NICHT erfasst (die verlangt "put" direkt nach dem "look at"-Satzteil,
    # hier steht dazwischen ein "if it's a land card"-Bedingungssatz).
    (r"(look at|reveal) the top card of your library\.? if it'?s a land card", "card_selection"),
    # v4.74.0-Nachtrag (Runde 3): "exile the top [N/X] card(s) of your
    # library ... you may play that card/those cards/it" (Wrenn's Resolve,
    # Commune with Lava, Charred Foyer) ist die klassische "Impulse Draw"-
    # Vorlage, extrem haeufig ueber viele Sets/Farben hinweg - eigenstaendig,
    # da "put ... into hand/battlefield" (die obigen card_selection-Regeln)
    # hier nicht zutrifft (Karten bleiben exiliert statt in die Hand/aufs
    # Battlefield zu wandern).
    (r"exile the top .{0,25}cards? of your library\.? .{0,60}?you may play (that card|those cards|it|them)", "impulse_draw"),
]

_STRATEGY_RULES = [
    (r"\+1/\+1 counters?|proliferate", "counters_matter"),
    (r"twice that many (of )?(those )?tokens|twice that many.*counters|copies of that token", "token_or_counter_doubler"),
    (r"create.*(\d+/\d+|x/x).*creature token", "token_creation"),
    (r"sacrifice a creature.*(draw|damage|counter|life)|whenever.*creature.*dies", "aristocrats_sac_death_trigger"),
    (r"equipped creature|enchant creature|aura.*attached", "voltron_aura_equipment"),
    (r"you gain \d+ life|whenever you gain life|gain life equal to", "lifegain"),
    (r"each opponent loses \d+ life|loses life equal to|life total to \d+", "life_drain_direct"),
    (r"(return|put) .*card (with (mana value|cmc) \d+ or (less|greater)[^.]*?)?from (a |your |their )?graveyard (to|onto) (your hand|the battlefield)|reanimate", "graveyard_recursion"),
    (r"mill|put the top .* cards? of .* library into.*graveyard", "mill"),
    (r"discards? (their|your) hand,? then draws?", "wheel_effect"),
    (r"discards? a card|each opponent discards", "discard_disruption"),
    (r"takes? an extra turn", "extra_turn"),
    (r"additional combat phase|extra combat", "extra_combat"),
    (r"destroy target land|sacrifice a land", "land_destruction"),
    (r"each player draws?|each opponent draws", "group_hug_or_symmetric_draw"),
    (r"gain control of target|steal", "theft_effect"),
    (r"copy target (spell|instant or sorcery)|copy that spell", "spell_copy"),
    (r"landfall", "landfall"),
    (r"blink|exile.*return.*battlefield|flicker", "blink_flicker"),
    (r"whenever .* attacks?, .*(damage|counter|token|draw)", "attack_trigger_payoff"),
    (r"infect|poison counter", "infect_poison"),
    (r"storm \(", "storm"),
    (r"spells? (you cast )?(of the chosen (type|color)|cost \{\d+\} less to cast)|costs? \{\d+\} less to cast", "cost_reduction"),
    (r"choose a creature type", "tribal_synergy_lord"),
    # v4.71.0-Nachtrag: vier weitere, in der Stichprobe haeufig wiederkehrende
    # Vorlagen, beim CURATED_OVERRIDES-Erweiterungs-Audit (Ranking nach
    # Gesamt-Stueckzahl ueber alle 1.585 Decks) gefunden - allgemeine
    # Regel-Fixes statt Einzelkarten-Overrides, da sie jeweils viele Karten
    # gleichzeitig treffen (siehe Docs/opponent_model_calibration_v4_71_0.md,
    # Nachtrag-Abschnitt):
    (r"triggers? an additional time", "trigger_doubler"),
    (r"copy of (any|target) (artifact|creature|permanent|land)", "clone_effect"),
    (r"untap all .*during each (other player|opponent)", "extra_untap_steps"),
    (r"deals? (double|triple|twice|three times) (that|the) (damage|much damage)", "damage_multiplier"),
    # v4.73.0-Nachtrag (Runde 2, dieselbe Ranking-Methodik erneut angewendet):
    # zwei weitere haeufige Vorlagen.
    (r"\bcascade\b", "cascade_value"),
    (r"can't be blocked\b", "evasion_unblockable"),
    # v4.74.0-Nachtrag (Runde 3, dieselbe Ranking-Methodik erneut angewendet):
    # zwei weitere haeufige Vorlagen.
    (r"untap all nonland permanents you control", "untap_all_nonland_combo"),
    # Breitere Fassung der bestehenden wheel_effect-Regel oben (die nur
    # "discards ... then draws" abdeckt): "shuffles the cards from
    # hand/graveyard into library, then draws that many/seven cards"
    # (Winds of Change, Echo of Eons, Molten Psyche) ist dieselbe Grund-
    # Vorlage (Handnachfuellung), nur mit "shuffle" statt "discard"
    # formuliert.
    (r"shuffles? (the cards from )?(their|your) hand( and graveyard)? into (their|your) library,? then draws? (that many|seven) cards", "wheel_effect"),
]


def _match_any(text: str, rules) -> list[str]:
    tags = []
    for pattern, tag in rules:
        if re.search(pattern, text):
            tags.append(tag)
    return tags


# ---------------------------------------------------------------------------
# v4.70.0 ("Halbwertszeiten-Recherche"): welchen der 5 permanent_type_half_
# life_turns-Buckets (creature/artifact/enchantment/planeswalker/land) kann
# eine Karte durch destroy/exile/bounce/-X/-X/Schaden tatsaechlich vom Brett
# entfernen? `classify_card`s bestehende `_INTERACTION_RULES` klassifizieren
# NUR die grobe Rolle/den Effekt-Tag (z.B. "removal_single_exile") und werfen
# dabei die vom Regex eigentlich schon gefangene Zielangabe ("target
# CREATURE" vs. "target ARTIFACT") wieder weg. `removal_target_types` ist ein
# bewusst SEPARATER, additiver Zusatz (aendert `classify_card`s bestehende
# Rueckgabe-Keys nicht, ergaenzt nur einen neuen) - siehe Docs/README.md fuer
# den Auftrag ("stichprobenartig herausfinden, zu wie viel Prozent eine Hand
# [...] ein Removal Spell hat, der auf diese Permanente [...] passt").
_PERMANENT_TYPE_WORD_MAP = {
    "creature": "creature",
    "artifact": "artifact",
    "enchantment": "enchantment",
    "planeswalker": "planeswalker",
    # "permanent"/"nonland permanent" hat kein festes Ziel -> alle 4 (Land
    # bewusst ausgenommen: "target nonland permanent" schliesst Land explizit
    # aus, und ein reines "target permanent" trifft in der Praxis so gut wie
    # nie tatsaechlich ein Land, weil dafuer eigene "target land"-Karten
    # existieren - siehe land_destruction unten, separat behandelt).
    "permanent": "ALL",
    "nonland permanent": "ALL",
}
ALL_PERMANENT_TYPES = frozenset({"creature", "artifact", "enchantment", "planeswalker"})
_TARGET_WORD_RE = re.compile(r"(nonland permanent|permanent|creature|artifact|enchantment|planeswalker)s?")


def _expand_target_words(span: str) -> frozenset[str]:
    out: set[str] = set()
    for word in _TARGET_WORD_RE.findall(span):
        mapped = _PERMANENT_TYPE_WORD_MAP.get(word)
        if mapped == "ALL":
            out |= ALL_PERMANENT_TYPES
        elif mapped:
            out.add(mapped)
    return frozenset(out)


def removal_target_types(oracle_text: str) -> frozenset[str]:
    """Welche Permanenttypen kann diese Karte per destroy/exile/Board-Wipe/
    Bounce/-X/-X/Schaden vom Brett entfernen? Liefert eine Teilmenge von
    {"creature","artifact","enchantment","planeswalker","land"}, oder ein
    leeres frozenset, wenn nichts erkannt wurde (inkl. Counterspells - die
    verhindern, dass ein Permanent je aufs Brett kommt, entfernen aber kein
    BEREITS liegendes Permanent, was fuer die Halbwertszeiten-Frage "wie
    lange ueberlebt ein Permanent, das schon auf dem Brett liegt" der
    relevante Massstab ist - bewusst ausgeschlossen).

    Heuristisch (Regex auf lowercased oracle_text): deckt Standard-
    Formulierungen (inkl. "destroy target creature, artifact, or enchantment"
    -Mehrfachaufzaehlungen ueber `_expand_target_words`) ab, nicht jede
    denkbare Karten-Sondertextvariante (z.B. Council's Judgment/"choose a
    permanent" ueber Abstimmung wird NICHT erkannt) - eine bewusst
    dokumentierte Naeherung, kein Anspruch auf Vollstaendigkeit.
    """
    text = oracle_text.lower() if isinstance(oracle_text, str) else ""
    targets: set[str] = set()

    # Board-Wipes: "destroy/exile all <typ(en)>".
    for m in re.finditer(r"(?:destroy|exile) all ((?:nonland )?(?:artifacts?|creatures?|enchantments?|permanents?)(?:,? (?:and |or )?(?:artifacts?|creatures?|enchantments?|permanents?))*)", text):
        targets |= _expand_target_words(m.group(1))
    if re.search(r"(?:each|all) creatures? gets? -(?:\d+|x)/-(?:\d+|x)"
                 r"|-(?:\d+|x)/-(?:\d+|x) to (?:each|all) creatures?", text):
        targets.add("creature")
    if re.search(r"each player sacrifices all permanents", text):
        targets |= ALL_PERMANENT_TYPES

    # Einzelziel destroy/exile/tuck, inkl. Mehrfachaufzaehlungen ("target
    # creature, artifact, or enchantment") und beliebig vieler "non-X"-
    # Einschraenkungen ("nonblack creature", "nonland permanent", ...) vor
    # dem eigentlichen Zielwort - alles bis zum naechsten Punkt/Komma-
    # Nebensatz wird nach Zielwoertern durchsucht.
    for m in re.finditer(
        r"(?:destroy|exile|shuffles? .*? into (?:its owner's|their) library) target "
        r"(?:non-?\w+\s+)*((?:creature|artifact|enchantment|planeswalker|permanent)s?"
        r"(?:,? (?:and |or )?(?:another )?(?:creature|artifact|enchantment|planeswalker|permanent)s?)*)",
        text,
    ):
        targets |= _expand_target_words(m.group(1))

    # "Owner of target X shuffles it into their library" (z.B. Chaos Warp) -
    # hier steht "target X" VOR dem eigentlichen Verb, nicht danach.
    for m in re.finditer(
        r"of target (?:non-?\w+\s+)*((?:creature|artifact|enchantment|planeswalker|permanent)s?)"
        r"[^.]*?shuffles it into (?:its owner's|their) library",
        text,
    ):
        targets |= _expand_target_words(m.group(1))

    # Einzelziel-Entwertung (-X/-X) - trifft in dieser Formulierung immer nur Kreaturen.
    if re.search(r"-\d+/-\d+ to target creature|target creature gets -\d+/-\d+"
                 r"|-x/-x to target creature|target creature gets -x/-x", text):
        targets.add("creature")

    # Schaden - "target creature" trifft nur Kreaturen, "any target" potentiell
    # auch Planeswalker (aber praktisch nie Artefakte/Verzauberungen/Land -
    # die sind normalerweise keine legalen Schadensziele).
    if re.search(r"deals? \d+ damage to target creature", text):
        targets.add("creature")
    if re.search(r"deals? \d+ damage to any target", text):
        targets.update({"creature", "planeswalker"})

    # Bounce - befoerdert ein Permanent von Brett -> Hand; zaehlt hier als
    # "entfernt", auch wenn nicht dauerhaft (die Halbwertszeiten-Frage ist
    # "wie lange bleibt es LIEGEN", nicht "wie lange ist es fuer immer weg").
    # Beliebiger Zwischentext vor "to its/their owner" erlaubt (z.B. "you
    # don't control", "an opponent controls"), daher [^.]*? statt direktem
    # Anschluss.
    for m in re.finditer(
        r"return target (?:non-?\w+\s+)*((?:creature|artifact|enchantment|planeswalker|permanent)s?"
        r"(?:,? (?:and |or )?(?:creature|artifact|enchantment|planeswalker|permanent)s?)*)"
        r"[^.]*? to (?:its|their) owner",
        text,
    ):
        targets |= _expand_target_words(m.group(1))

    # Landzerstoerung - eigener Bucket, separat von den 4 oben. "sacrifices?"
    # deckt sowohl "Sacrifice a land" (Imperativ) als auch "Target player
    # sacrifices a land"/"Each player sacrifices a land" (3. Person) ab.
    if re.search(r"destroy target land|sacrifices? a land", text):
        targets.add("land")

    return frozenset(targets)


def classify_card(name: str, oracle_text: str, type_: str) -> dict:
    """Liefert dict(primary_role, effect_tags:list[str], simple_effect:str,
    curated:bool, removal_targets:list[str]).

    `removal_targets` (v4.70.0) ist additiv - siehe `removal_target_types`s
    Docstring - und wird fuer JEDE Karte berechnet, unabhaengig davon, ob sie
    ueber `CURATED_OVERRIDES` oder die Regel-Engine klassifiziert wird (ein
    kuratierter Override ersetzt nur primary_role/effect_tags/simple_effect,
    nicht die separate Zieltyp-Erkennung)."""
    removal_targets = sorted(removal_target_types(oracle_text))
    if name in CURATED_OVERRIDES:
        ov = CURATED_OVERRIDES[name]
        return dict(
            primary_role=ov["role"],
            effect_tags=ov["effect_tags"],
            simple_effect=ov["simple_effect"],
            curated=True,
            halbwertszeit=ov.get("halbwertszeit"),
            removal_targets=removal_targets,
        )

    text = oracle_text.lower() if isinstance(oracle_text, str) else ""

    if type_ == "Land":
        # Laender sind strukturell eine eigene Kategorie (kein Spell-Effekt-Slot).
        # Fetch-/Ramp-Laender trotzdem als Ramp markieren (fixing/zusaetzliche Karte
        # auf dem Feld); reine Utility-Laender (Bojuka Bog etc.) bleiben "Land".
        if _has(text, r"search your library for a.*card, put (it|that card) onto the battlefield",
                      r"add \{.\}\{.\}"):
            return dict(primary_role="Ramp", effect_tags=["land_fixing_or_ramp"],
                        simple_effect="mana fixing / ramp land (fetch or dual-mana land)",
                        curated=False, halbwertszeit=None, removal_targets=removal_targets)
        return dict(primary_role="Land", effect_tags=["land_base"],
                    simple_effect="produces mana (base land function)", curated=False, halbwertszeit=None,
                    removal_targets=removal_targets)

    interaction_tags = _match_any(text, _INTERACTION_RULES)
    if interaction_tags:
        return dict(primary_role="Interaction", effect_tags=interaction_tags,
                    simple_effect=interaction_tags[0].replace("_", " "), curated=False, halbwertszeit=None,
                    removal_targets=removal_targets)

    ramp_tags = _match_any(text, _RAMP_RULES)
    if ramp_tags:
        return dict(primary_role="Ramp", effect_tags=ramp_tags,
                    simple_effect=ramp_tags[0].replace("_", " "), curated=False, halbwertszeit=None,
                    removal_targets=removal_targets)

    ca_tags = _match_any(text, _CARD_ADVANTAGE_RULES)
    if ca_tags:
        return dict(primary_role="CardAdvantage", effect_tags=ca_tags,
                    simple_effect=ca_tags[0].replace("_", " "), curated=False, halbwertszeit=None,
                    removal_targets=removal_targets)

    strat_tags = _match_any(text, _STRATEGY_RULES)
    if strat_tags:
        return dict(primary_role="Strategy", effect_tags=strat_tags,
                    simple_effect=strat_tags[0].replace("_", " "), curated=False, halbwertszeit=None,
                    removal_targets=removal_targets)

    # Kein Muster gegriffen -> generischer Fallback nach Kartentyp.
    if type_ == "Creature":
        return dict(primary_role="Strategy", effect_tags=["vanilla_or_unclassified_body"],
                    simple_effect="body/stats only (kein textbasierter Zusatzeffekt erkannt)",
                    curated=False, halbwertszeit=None, removal_targets=removal_targets)
    return dict(primary_role="Strategy", effect_tags=["unclassified"],
                simple_effect="kein Regel-Muster gegriffen", curated=False, halbwertszeit=None,
                removal_targets=removal_targets)
