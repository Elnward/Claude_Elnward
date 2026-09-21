"""
Rudimentary opponent state equation (v4.38.0 "Iteration 1", calibrated and
extended in v4.39.0 "Iteration 2" against real decklists).

Background / design mandate (see Docs/README.md v4.38.0 entry for the full
German writeup): the existing opponent abstraction (App/engine.py's
OPPONENT_PROFILES + apply_abstract_opponent_phase) is a flat, per-profile
constant table driving simple turn-thresholded probabilistic damage/removal/
wipe rolls. It has no notion of an opponent BOARD, HAND, or MANA STATE at
all - just a life total and a single "damage_scale" pressure constant. There
is also no "Bracket" (Commander power-level, 1-5, see
https://mtg.wiki/page/Commander_Brackets) concept anywhere in the codebase.

This module is a deliberately RUDIMENTARY first pass at something richer,
per the user's explicit request: model the opponent as an abstract, evolving
STATE (life, board presence, available interaction, mana development, hand
quality, ...) rather than any specific card. The explicit design mandate
(user's own words, translated): "the equation must look the SAME for every
opponent type - only the WEIGHTING differs, depending on strategy [color,
and bracket]." Concretely:

  - ONE function, `advance_opponent_state`, is the entire state-transition
    equation. Every strategy/color/bracket combination runs through the
    exact same code path - there is no per-type branching in the equation
    itself, only weight lookups (Data/Models/opponent_state_weights.json).
  - Genuine variance is modeled, not just an expected-value curve: a shared
    per-turn "turn quality" roll (mana screw / a clunky draw / a great
    curve-out) plus a separate discrete "dead turn" Bernoulli event (an
    unplayable hand), both weighted by strategy and smoothed by Bracket
    (a higher Bracket deck is more consistent - see `consistency_floor`).
  - An explicit guardrail the user called out by name is hard-enforced,
    not just defaulted: a board wipe is never "available" before turn 4,
    regardless of how the weights are tuned (`GUARDRAIL_WIPE_MIN_TURN`).
  - The STATE, not individual cards, is what the rest of the engine is
    meant to query: `query_combat_state` (for the combat-phase decision
    point the user named) and `query_castable_state` (for "what could the
    opponent/player currently do" checks, on either player's turn) are pure,
    read-only functions over the current OpponentState - they never mutate
    it. Only `advance_opponent_state` mutates state, and per the user's own
    turn-structure ("state gets QUERIED during the simulated player's own
    turn; the state equation gets UPDATED during the opponent's own turn")
    it is meant to be called exactly once per opponent turn.

v4.39.0 ("Iteration 2" - calibration pass): per the user's own explicitly-
stated next step, 10 real Commander decklists were gathered from EDHREC's
"average deck" aggregates - one lower-power ("budget") and one higher-power
("expensive") build for a canonical commander/strategy in each of the 5
mono-colors (mono-R Krenko Mob Boss/aggro, mono-W Giada Font of Hope/aggro,
mono-U Lier Disciple of the Drowned/control, mono-B Endrek Sahr Master
Breeder/aristocrats-as-midrange, mono-G Azusa Lost but Seeking/ramp). Each
list was Bracket-classified against the REAL, verified 53-card Game
Changers list (magic.wizards.com, cross-checked against two independent
mirrors) plus the mass-land-destruction/extra-turn criteria - not trusted
by a source label - and every card was checked against the 5 existing
readiness dimensions. Findings (full writeup: Docs/README.md v4.39.0 entry
and the project doc this version also writes):

  - color_modifiers for U (interaction_availability) and G (mana_growth)
    were revised upward - the real decklists showed blue's counterspell/
    bounce/protection density (17-25% of nonland slots) and green's ramp
    density (15-20%) meaningfully higher than the v4.38.0 first-guess
    multipliers implied relative to the other three colors.
  - A genuine, evidenced gap: EVERY "expensive"/high-Bracket decklist in
    the sample (all 5 colors) added a cluster of explosive, near-0-mana
    accelerants (Ancient Tomb/Mana Vault/Chrome Mox/Jeweled Lotus/Lotus
    Petal/Ashnod's Altar/Phyrexian Altar) that was COMPLETELY ABSENT from
    every "budget" list - a one-time early spike, not steady growth. Added
    `bracket_scaling.*.opening_mana_boost`, applied once on turn 1.
  - A second genuine, evidenced gap: Game-Changer-list density jumped
    sharply by Bracket (0-2 cards in every Bracket-2/3 list vs. 4-5+ in
    every Bracket-4/5 list) - i.e. the Bracket system's real-world meaning
    is largely ABOUT alternate win conditions/combo pieces clustering at
    the top end, which the v4.38.0 model had no dimension for at all.
    Added `combo_finish_readiness` (OpponentState) / `combo_growth`
    (per-strategy curve) - hard-gated to Bracket >= COMBO_MIN_BRACKET and
    turn >= the combo-min-turn guardrail (same double-floor pattern as the
    wipe guardrail), since 0-2 Game Changers is nowhere near a real combo
    assembled.
  - Two further gaps were identified but explicitly DEFERRED (small
    sample, and each would need real new mechanics, not just weight
    tuning, to model honestly): (a) passive, no-action value/tax engines
    (Rhystic Study, Smothering Tithe, Sylvan Library, Necropotence) that
    boost hand quality without a discrete "draw" event; (b) black's
    sacrifice/aristocrats free-damage loops (Ashnod's Altar + Phyrexian
    Altar + death-trigger drain) as a life-total pressure vector distinct
    from combat and from spot removal. Neither is silently ignored - both
    are named here and in Docs/README.md as known, deferred gaps.
  - The calibration itself is explicitly a SMALL, DIRECTED sample (2 real
    decklists per color = 10 total, not the "many decks per Bracket per
    color" full matrix) - the numbers below are real density ratios from
    real decklists, which is a genuine improvement over v4.38.0's pure
    first guesses, but this is still NOT the statistically broad
    calibration the user named as their own further future step.

v4.40.0 ("Iteration 3" - closing the two v4.39.0-deferred gaps): the user
proposed generalizing "complex, individually-simulated card effects" into
typed, DURATION-BOUND board effects instead - the same "state, not cards"
philosophy applied to persistent permanents. Two new stocks, using the same
growth mechanism as every other dimension plus a decay term:

  - `OpponentState.passive_value_by_type` (closes the "passive value/tax
    engine" gap: Rhystic Study, Smothering Tithe, Sylvan Library,
    Necropotence, ...) and `sac_drain_by_type` (closes the "sacrifice/
    aristocrats free-damage loop" gap: Ashnod's Altar + Phyrexian Altar +
    death-trigger drain) are each a small dict keyed by the PERMANENT TYPE
    the effect would realistically live on ("artifact"/"enchantment"/
    "creature") rather than a growing list of named cards.
  - Per the user's own reasoning: the permanent-type tag is not there to
    simulate the permanent itself, but so a LATER integration step (running
    the actual tested deck against this simulated opponent) can check
    whether the tested deck's own removal suite can actually interact with
    that permanent type at all - a mono-red deck with only creature/
    artifact removal has no real answer to an enchantment-based Rhystic
    Study, and that mismatch is exactly what the permanent-type breakdown
    is for. This module still does not perform that cross-check itself
    (App/engine.py already tracks the tested deck's real removal breadth
    elsewhere) - `query_board_effects` merely exposes the breakdown so a
    later wiring step can compare it.
  - DECAY instead of a fixed duration: since this module does not simulate
    opponents interacting with EACH OTHER (only the tested player's deck is
    real), a live effect's realistic lifespan is modeled as a per-turn
    half-life (`permanent_type_half_life_turns`) standing in for "some
    other player at the table eventually answers it" - applied every turn
    to whatever is currently in each bucket, before that turn's own growth
    is added. Enchantment-based engines get the longest half-life (fewest
    real decks run enchantment removal), creatures the shortest (the most
    commonly/easily removed permanent type in practice) - first-guess
    values, disclosed as such (no real "how long does a Rhystic Study
    survive at a table" statistic exists to calibrate against).
  - `passive_value_by_type` growth is additionally scaled by a new
    `table_size` parameter (default 4, a typical Commander pod) - unlike
    every other dimension, real tax/value engines like Rhystic Study or
    Smothering Tithe scale with the NUMBER OF OTHER PLAYERS at the table,
    not just interaction against the one player being tested. This was a
    genuinely missing input the v4.39.0 model had no place for at all.
    `sac_drain_by_type` is NOT scaled by table_size (a real Blood Artist-
    style drain trigger typically hits one chosen target, not every
    player), which is why the two stocks take separate growth paths
    despite sharing the same growth+decay mechanism.
  - The user explicitly asked for BOTH new stocks AND a mapping of the 53
    Game Changers into a handful of effect archetypes, to be done without
    further manual lookups on their part. That mapping lives in
    `Data/Models/game_changer_archetypes.json` - purely a CALIBRATION/
    tagging aid (which of the existing dimensions each real Game Changer
    card is evidence for), never a runtime per-card lookup inside the
    simulation itself. `permanent_type_distribution` (which bucket a newly
    -grown passive_value/sac_drain point lands in) and the relative
    strategy_curves/color_modifiers weights for the two new growth rates
    were informed by that mapping plus the already-gathered v4.39.0
    decklist sample - see Docs/README.md v4.40.0 for the full reasoning.

Explicitly OUT OF SCOPE for this pass (disclosed, not silent):
  - Wiring these functions into App/engine.py's actual turn loop
    (attack_phase / apply_abstract_opponent_phase / castability checks),
    INCLUDING the permanent-type-vs-tested-deck-removal cross-check just
    described, is a separate, later integration step - this module stands
    alone and is fully unit-tested on its own, following this project's
    established "engine-agnostic, ops-passed-in" module convention (see
    App/combat_model/interaction.py, App/resource_planner/planner.py).
  - A full Bracket x color x strategy matrix trained on many decks per
    cell remains the user's own explicitly-stated further future step.

v4.41.0 ("Iteration 3b" - LSV-inspired half-life refinement, plus the start
of "Iteration 4" - the color-identity expansion): two separate follow-ups.

  (1) The user asked to ground the half-life concept in the official LSV
      (Luis Scott-Vargas / ChannelFireball) card-quality scale, specifically
      to derive board-tenure from card quality. Researched via WebSearch/
      WebFetch (see Docs/README.md v4.41.0 for sources): the LSV scale is a
      per-SET LIMITED DRAFT review scale (commonly S/A/B/C/D/F or an
      equivalent 0-5 band, e.g. "S: ridiculous bomb" down to "F: mostly
      unplayable") written fresh by reviewers for each new set's limited
      environment. There is NO single universal LSV rating covering every
      Magic card ever printed - in particular, old/reprint Commander staples
      such as Mana Vault, Necropotence, or Rhystic Study were never
      themselves the subject of a limited set review and simply have no LSV
      number to look up. Treating "the LSV rating of Rhystic Study" as a
      citable fact would have violated this project's evidence-over-
      invention convention, so no per-card LSV numbers are used anywhere in
      this codebase.
      What IS genuinely usable is the underlying mechanism the user's own
      research surfaced independent of LSV specifically: a "threat
      relevance" / "dies to removal" paradox, where a higher-impact
      ("bomb-tier") permanent draws answers fast and a filler permanent gets
      ignored and survives many turns. This project already has exactly one
      real, rule-verified, evidence-based "this is bomb-tier" signal: Game-
      Changer membership (the official 53-card list). And Game-Changer
      density already correlates strongly with Bracket (established in
      v4.39.0 and reconfirmed with the two-color sample below). So the
      paradox is applied at the Bracket level, not the individual-card
      level: `bracket_scaling.<bracket>.impact_half_life_multiplier`
      shortens the effective half-life of both new v4.40.0 stocks at higher
      Brackets (more bomb-tier permanents on average -> answered faster),
      applied via `_impact_half_life_multiplier()` on top of the existing
      per-permanent-type half-life. The magnitude is a disclosed REASONED
      estimate (there is no play-by-play game log to count real "answered on
      turn X" statistics from a decklist), exactly like the v4.40.0
      permanent-type half-life values already were - not a new category of
      invention, the same honestly-labeled kind of estimate this module
      already contained.

  (2) The user separately asked to extend calibration beyond monocolor to
      "all color combinations, 50 decks per Bracket x color-identity x
      strategy". Disclosed honestly rather than silently under-delivered:
      a full matrix at that density is 32 color identities (5 mono + 10 two-
      color + 10 three-color + 5 four-color + 1 five-color + colorless) times
      5 Brackets times several strategies times 50 decks - many thousands of
      individually-sourced, verified real decklists. That is not achievable
      as real, evidence-based data within a single pass (it would require
      either inventing numbers, which this project's own conventions
      explicitly forbid, or a genuinely multi-session research effort). This
      version instead takes the next honest, proportionate step, matching
      the project's own established increment size (the v4.39.0 monocolor
      pass used 10 real decks): all 10 two-color guilds, ONE real EDHREC
      average-deck each (a well-known commander with a conventional strategy
      per guild), Game-Changer-verified into real Brackets exactly like the
      monocolor pass. Findings (full detail in Docs/opponent_model_
      calibration_v4_41_0.md):
        - Bracket coverage across the 10 guild decks: Bracket 2 (Golgari/
          Meren, 0 Game Changers), Bracket 3 (5 guilds), Bracket 4 (4
          guilds) - confirms the Game-Changer-count Bracket classification
          generalizes beyond monocolor without changes.
        - The existing multiplicative color-modifier model (two colors'
          per-letter modifiers multiplied together) broadly holds up:
          Azorius (WU, high W and U passive_value_growth) showed the
          heaviest passive-value-engine density of the sample, as predicted.
        - A genuine NEW limitation was found and is explicitly NOT patched
          this version: some guilds show real, decklist-evidenced synergy
          that a simple per-LETTER-per-DIMENSION multiplication cannot
          express, because the synergy crosses dimensions. Orzhov (WB/Teysa
          Karlov) had the densest sacrifice/aristocrats-drain package of any
          deck sampled so far (denser than the mono-Black Endrek-Expensive
          list) - white itself has no sac_drain_growth modifier, so the
          model currently attributes this entirely to Black, missing that
          White's TOKEN GENERATION is what is actually feeding Black's
          drain triggers here. Izzet (UR/Niv-Mizzet Parun) showed unusually
          dense passive-value/card-draw effects for a guild where Red
          contributes no passive_value_growth modifier at all - again a
          real cross-dimension synergy (spellslinger tempo feeding card
          advantage) the current single-dimension-per-letter model cannot
          see. Both are disclosed as a genuine future-iteration candidate
          (guild-specific synergy bonuses, NOT the same as the user's own
          "Iteration 5" naming below, which is about color-identity
          coverage rather than synergy modeling) rather than silently
          patched from a single data point per guild, which would not be a
          responsibly evidenced change.

v4.42.0 ("Iteration 5", part 1 - the user's own naming, for extending
color-identity coverage beyond mono/two-color): the user confirmed the
existing sample sizes (2 decks/mono-color, 1 deck/two-color guild) as
sufficient for now, with deeper recalibration explicitly deferred to "once
the whole tool mechanic is 100% familiar and everything works and the
design fits" (i.e. after this module is actually wired into App/engine.py's
turn loop - still not done, see the "explicitly out of scope" note above).
This version applies the same 1-deck-per-identity cadence to all 10
three-color wedges/shards. It is a pure VALIDATION pass - every finding
confirmed the existing multiplicative color model rather than contradicting
it (Esper/WUB predicted the single highest passive_value_growth multiplier
combination found so far, and real Zur the Enchanter data matched; Jund/BRG
reconfirmed Black's sac-drain dominance for a third color pairing) - so
NEITHER `state_equation.py` NOR `opponent_state_weights.json`'s numeric
values changed. The one real, evidence-based refinement is to the (offline,
human) Bracket-classification heuristic used to label real decks before
deriving weights, not to any runtime code: a clean 10-Game-Changer deck with
no ritual/altar cluster (Zur) shows that >= ~7 Game Changers alone, without
the extra cluster signal v4.39.0 required, is enough for Bracket 5. See
Docs/opponent_model_calibration_v4_42_0.md for the full decklist table and
reasoning, and Docs/README.md v4.42.0 for a compiled review of every
currently open/disclosed gap in this module (none of which block this
color-identity expansion - they are independent, already-disclosed,
deliberately deferred items).

v4.66.0 ("Kalibrierungs-Synthese Teil 1" - Flavor-Strategie-Matrix): between
v4.47.0 and v4.62.0 (16 project versions, entirely separate from this
module's own history above), the user had 90 additional real-decklist
"flavor" cells researched (5 mono-colors x 6 flavors + 10 two-color guilds x
6 flavors, one real EDHREC Bracket-3 decklist per cell, e.g. "White ->
Voltron/Auras&Equipment -> Light-Paws, Emperor's Voice") on top of the
color/strategy grid already calibrated above - see Docs/flavor_strategy_
matrix_*.md and Docs/README.md v4.47.0-v4.62.0. Every one of those 16
documents explicitly and repeatedly labels its own numbers "Kandidaten,
keine Gewichtsaenderung" (candidates, not a weight change) precisely because
each cell is ONE real decklist, not the "many decks per cell" breadth this
module's own OWN color/strategy grid above was calibrated against (10, then
+10, then +10 decks). Silently promoting N=1-per-cell numbers into this
module's actual DEFAULT weights (color_modifiers/strategy_curves in
opponent_state_weights.json) would therefore be exactly the kind of
speculative, insufficiently-evidenced change this project's own principles
reject - so this version does NOT do that. `opponent_state_weights.json`'s
color_modifiers/strategy_curves are numerically UNCHANGED by this version.

Instead: the 90 cells are compiled, losslessly and without any new
research, into Data/Models/flavor_strategy_matrix.json (see
Docs/README.md v4.66.0 and that file's own "note" field for the full
transcription methodology), and this module gains a strictly OPT-IN way to
actually use one: `OpponentProfile.flavor` (new field, default None - every
existing caller that never sets it sees byte-identical behavior, verified by
regression tests). When a caller deliberately sets `profile.flavor` to a
known "<color_identity>/<flavor_slug>" cell matching `profile.colors`,
`advance_opponent_state` uses that cell's own 10-field state function
DIRECTLY in place of `curve[dimension] * _color_multiplier(colors,
dimension)` for that one simulated opponent - the flavor cell's values are
already the proposed FINAL per-turn growth rate (see every "Zelle N" block
in the source documents: they are candidate REPLACEMENTS for the combined
curve*modifier value, not an additional multiplier layered on top of it).
Unknown/unset flavor keys, or a flavor whose stored color_identity does not
match `profile.colors`, fall back to the pre-existing curve*modifier
behavior unchanged (see `_flavor_cell`/`_growth_rate` below) - a caller
typo never silently breaks the simulation, and this module continues to
prefer a disclosed fallback over an invented one. `bracket_scaling` (power_
multiplier/variance_multiplier/consistency_floor/opening_mana_boost) and the
hard wipe/combo turn-and-Bracket guardrails are UNCHANGED and continue to
apply exactly as before even when a flavor is active - those are a
completely separate, already-broadly-calibrated axis this 90-cell research
pass did not touch. Two model limitations that recurred across the flavor
research (a "thematic core density has no dedicated dimension" pattern in
>10 cells, and a "Voltron/concentration decks understate board_presence"
pattern in 6 of 10 guilds - see flavor_strategy_matrix.json's own
`documented_model_limitations`) are disclosed, NOT fixed, in this version -
each would need a genuinely new state dimension, not just a data-plumbing
step, and remain an explicit future-version candidate.

v4.67.0 ("Kalibrierungs-Synthese Teil 2" - statistisch breite Neukalibrierung):
unlike v4.66.0's flavor matrix (90 cells, N=1 decklist each, deliberately
NOT promoted into default weights), this version DOES update
`opponent_state_weights.json`'s actual `color_modifiers`/`strategy_curves`
defaults - because the new evidence base (App/archetype_profile/data/
deck_profiles.csv, 1,585 real EDHREC "average deck" composition profiles
across all 32 color identities and 115 canonical strategy tags, see project
note edhrec-bracket3-database.md) is exactly the "statistically broad
calibration" the user named as a deferred future step as far back as the
v4.39.0 docstring section above (n=50 decks/mono-color, n=41-131 decks/
strategy-tag, vs. the original n=2/color). Same density-ratio methodology as
v4.39.0 (share of non-land deck slots), just at 20-50x the sample size:
color_modifiers.{board_presence,wipe_readiness,mana_growth} recalibrated per
color as (color's median density ratio) / (five-color mean of that ratio);
strategy_curves.{board_presence_growth,mana_growth} recalibrated for aggro/
midrange/control the same way, anchored to the OLD cross-strategy average so
absolute pacing does not swing wildly on a single recalibration pass, only
the relative shape between strategies. Full derivation, raw numbers, and
every value actually changed: Docs/opponent_model_calibration_v4_67_0.md and
Data/Models/opponent_state_weights.json's own "note" field.

Two deliberately-NOT-applied findings, both left as disclosed gaps rather
than silently "improved" (the same discipline as every prior calibration
round in this module's history):
  - interaction_availability/interaction_growth, and strategy_curves'
    wipe_growth: the 1,585-deck sample shows Aggro/Midrange/Control decks do
    NOT meaningfully differ in raw removal/counterspell/wipe card density
    (~0.22 of non-land slots for all three; even after narrowing the signal
    to single-target-answer+protection cards and excluding board wipes to
    avoid double-counting against the separate wipe dimension, the
    flattening persisted) - and Blue's own density (0.21) came out BELOW
    White's (0.29) and Red's (0.26), contradicting Blue's well-evidenced
    v4.39.0 role as the highest-interaction color. Likely explanation: a
    Commander pod's multiplayer reality demands a broadly similar baseline
    of "some answers" from every archetype, and White's abundant
    single-target exile removal simply outnumbers Blue's rarer-but-stronger
    counterspells in raw count - real data, but not what these dimensions
    are meant to represent (see OpponentState.interaction_availability's own
    docstring: "chance of live removal/counterspell/protection in hand").
    Adopting the raw ratios would have flattened the deliberately staggered
    Aggro<Midrange<Control differentiation and inverted Blue's documented
    role, so both dimensions stay on the smaller but more targeted v4.39.0/
    v4.43.0 calibration instead.
  - strategy_curves.horde.board_presence_growth: EDHREC has no native
    "Horde"/go-wide tag, so the "Tokens" tag (n=131, the closest available
    proxy) was used for horde's mana_growth/wipe_growth - but NOT for
    board_presence_growth, because real Tokens-tagged decklists show no
    elevated Creature-TYPE card count (0.45 of non-land slots, barely above
    the four-strategy average) - a token strategy's actual board presence
    comes overwhelmingly from non-Creature cards (anthems, sacrifice
    enablers, token-generating enchantments/sorceries) that make tokens
    DURING PLAY, which a static decklist's card-type census structurally
    cannot capture. The old, design-reasoned first-guess value (1.30) was
    kept rather than replaced with a misleadingly low, evidence-labeled
    number.

v4.69.0 ("Kalibrierungs-Synthese Teil 3" - deconfounding color x strategy):
the user directly challenged v4.67.0's methodology above. Marginal pooling
(averaging a strategy's card density across ALL colors, and a color's
density across ALL strategies) can hide a genuine per-axis effect through
confounding: if a strategy tag's color mix isn't representative of the
five-color average - or a color's strategy mix isn't representative of the
four-tag average - the two axes contaminate each other, and a real effect on
one axis can cancel out through the other before it's ever measured. The
user asked for exactly this to be checked against the data, not assumed
either way, and was explicit that the answer must not turn out to be "just
the mean of all decks" by construction.

To check this, a real two-way OLS regression (numpy.linalg.lstsq, no
intercept; statsmodels is not installed in this environment) was run on
n=337 decks (all 4 focal EDHREC tags - Aggro/104, Midrange/41, Control/61,
Tokens/131 - drawn from ALL 32 color identities, not just the 5 mono-colors
v4.67.0 used for the color axis) with 5 color-presence dummy columns
(multi-hot - a multicolor deck sets more than one) PLUS 4 mutually-exclusive
strategy-tag dummy columns as simultaneous regressors. This isolates each
color's coefficient while HOLDING the strategy-tag mix fixed, and vice
versa - unlike marginal pooling, which averages one axis away entirely
before ever looking at the other. Significance: |coefficient| > 2 * standard
error (homoskedastic OLS: sigma^2 = residual_sum_of_squares / (n-k), SE from
the diagonal of sigma^2 * pinv(X'X)). Full coefficient/SE table for every
color x dimension and every strategy x dimension: Docs/opponent_model_
calibration_v4_69_0.md.

The answer to the user's question is a genuine mix, not a flat collapse:

  - Some effects ARE real, robust color effects that survive deconfounding:
    board_presence (W/B/G significantly above neutral), interaction_
    availability (W significantly above, G significantly below - see the
    Black finding just below for the third), wipe_readiness (R significantly
    above, U/G significantly below), mana_growth (B/R/G significantly
    above). Several of these were NOT visible, or were miscalibrated, under
    v4.67.0's marginal method precisely because the color axis was
    contaminated by strategy mix: board_presence_growth's whole strategy
    axis, for instance, was UNDERSTATED by marginal pooling (aggro/midrange/
    control all move up substantially once color mix is held fixed - see
    Docs/opponent_model_calibration_v4_69_0.md's before/after table).
  - The HEADLINE correction: color_modifiers.B.interaction_availability
    (unchanged since v4.39.0's real Endrek Sahr decklist, at 1.20) turns out
    to be a SIGNIFICANT overestimate once strategy mix is held fixed
    (coefficient -0.031, SE 0.0068) - dropped to 0.85. This is not a
    v4.67.0-style "inconclusive, so leave it" gap; it is a positive,
    statistically confirmed CONTRADICTION of the prior value, and is treated
    accordingly (applied, not merely disclosed).
  - By contrast, color_modifiers.U.interaction_availability's new result is
    merely NOT significant (coefficient +0.012, SE 0.0073) - not
    contradictory. Per the decision rule this version applies uniformly (see
    Docs/opponent_model_calibration_v4_69_0.md's "Entscheidungsschema"): a
    significant contradiction of an existing real-decklist-evidenced value
    is applied; a merely-inconclusive new result does NOT override an
    existing real-decklist-evidenced value (Blue's 1.45 stays, from the real
    Lier decklist); and a non-significant result with no independent prior
    evidence is reverted to neutral (several v4.67.0-introduced
    color_modifiers keys - W/U.mana_growth, U/R.board_presence - are removed
    entirely on this basis).
  - Some effects that v4.67.0 suspected might be confound artifacts are
    CONFIRMED as genuinely flat even after deconfounding, not methodological
    flaws: strategy_curves' interaction_growth, wipe_growth, and mana_growth
    all remain statistically indistinguishable between Aggro/Midrange/
    Control after controlling for color mix. These were moved off the old,
    2-decks-per-tag staggered v4.39.0 values onto new, closely-clustered
    (but not manually flattened - each tag's own point estimate is kept)
    deconfounded values, since the old staggering is no longer defensible
    against a 337-deck deconfounded null result.
  - color_modifiers.G.wipe_readiness's v4.67.0 policy floor (0.15, a
    modeling decision forced by a raw mono-green median of exactly 0.0) is
    replaced by a real, significant, data-derived value (0.40) - the
    two-way regression draws on every green-inclusive deck across all 32
    identities, not just the 50 purely-mono-green decks that had the
    zero-median problem.
  - strategy_curves.horde.board_presence_growth stays UNCHANGED (1.30)
    independent of this deconfounding pass, for the same reason as in
    v4.67.0: the limitation is a missing DATA DIMENSION (token generation
    via non-Creature cards during play), not a color/strategy confound - a
    two-way regression cannot recover a signal the decklist census never
    captured in the first place.

Full coefficient tables, every individual apply/keep/revert decision with
its rationale, and the anchoring formula used for strategy_curves: Docs/
opponent_model_calibration_v4_69_0.md and Data/Models/
opponent_state_weights.json's own "note" field.

v4.70.0 ("Halbwertszeiten-Recherche" - empirically deriving
permanent_type_half_life_turns): the user asked whether the opponent state
equation could now be derived from the deconfounded color/deck understanding
above, or whether more questions were needed first. Answer given: this
equation already exists (since v4.38.0) and has been repeatedly recalibrated
(most recently v4.69.0) - this was not a from-scratch build. The user's
concrete ask instead targeted `permanent_type_half_life_turns`
(creature/artifact/enchantment/planeswalker/land), documented since v4.40.0
as "first-guess estimates, no real statistics behind them" - and proposed a
concrete two-part method: (1) sample what fraction of a possible opponent's
hand contains a removal spell matching a given permanent type, using the
1,585 real EDHREC-average decks as the population, and (2) use card price
(available "in the databases", i.e. Scryfall) as a rough quality/value proxy
to weight that frequency signal.

Implementation:
  - App/archetype_profile/classify.py gained a new, additive
    `removal_target_types(oracle_text)` function returning the subset of
    {creature, artifact, enchantment, planeswalker, land} a card's
    destroy/exile/wipe/bounce/-X/-X/damage effects can remove from an
    opponent's board. Counterspells are deliberately excluded (they prevent
    something from ever entering play, not remove an existing permanent -
    the relevant question here is "how long does an already-resolved
    permanent survive"). Four regex bugs were found and fixed against 18
    real test cards, including Chaos Warp's reversed word order ("owner of
    target permanent shuffles it into their library") and Toxic Deluge's
    literal "-X/-X" text; Council's Judgment-style vote effects (no "target"
    keyword) remain a disclosed, known miss.
  - The user's local `export_card_training_data.py` script was extended to
    also capture Scryfall's `prices` object (usd/usd_foil/eur/tix) - no new
    API cost, since the Collection/Named endpoints already return this
    object on every request, it just wasn't read before. The user re-ran it
    locally: 8,422/8,445 cards enriched, 92.9% with a resolved USD price.
  - Hand-sampling simulation: for each of the 1,585 decks, the full card
    pool is expanded by `quantity` (critical for correct land dilution -
    a quantity=20 basic land line must count as 20 individual cards in the
    pool, not 1), and 40 random 7-card hands are drawn without replacement
    per deck (63,400 hands total, seed 20260919). Per hand and per permanent
    type, both are recorded: whether >=1 card in the hand has a matching
    `removal_target_types` hit, and (if so) the highest resolved price among
    the matching cards (fallback chain price_usd -> price_usd_foil ->
    price_eur*1.08 -> price_tix, median-of-known-prices for the 4.7% of
    cards with no price data at all), log1p-transformed before averaging so
    a single very expensive outlier card does not dominate the mean.
  - Raw hit frequency (fraction of hands with >=1 matching removal, after
    two small regex gaps found while writing this version's tests were
    fixed - see below): creature 34.81%, artifact 19.52%, enchantment
    18.10%, planeswalker 16.93%, land 2.18%. Already on its own this
    overturns the old ordering: artifact (half-life 7) was longer than
    planeswalker (half-life 6), even though artifacts are answered MORE
    often in real decklists than planeswalkers - backwards.
  - While writing this version's tests, two small, genuine gaps surfaced in
    `removal_target_types` itself and were fixed: the -X/-X detection only
    matched the digit form ("-5/-5"), missing Toxic Deluge's own actual
    wording ("each creature gets -X/-X"); and the land-destruction detection
    only matched the imperative "Sacrifice a land", missing the third-person
    form ("Target player sacrifices a land"). Both regexes were broadened
    accordingly (see App/archetype_profile/classify.py) before the frequency
    numbers above were finalized.
  - Price weighting turned out to be a WEAK differentiator between the 4
    non-land types (log1p-mean best-answer price: creature ~$2.08, artifact
    ~$2.10, enchantment ~$2.14, planeswalker ~$2.21 - relative weights only
    0.986-1.021): frequency remains the dominant signal, price nudges the
    ranking only slightly rather than reshaping it. Combined into a
    frequency*price "removal pressure" score per type, anchored to the old
    4-type average (6.5) and redistributed by relative pressure - the same
    "anchor to old average, redistribute by new evidence" pattern used for
    strategy_curves in v4.67.0/v4.69.0. Result: creature 4->4.2 (stays
    shortest, now evidenced instead of assumed), artifact 7->7.5, enchantment
    9->8.0 (no longer the longest by convention), planeswalker 6->8.4 (now
    correctly the longest of the four, matching its lowest hit frequency).
  - Land is a deliberate, disclosed POLICY exception, not a plain data
    adoption: the raw inverse-frequency extrapolation comes out to ~63.8
    turns, which exceeds this tool's own maximum simulatable game length
    (App/gui.py's turns_var Spinbox tops out at 30) - applying it as-is would
    silently make Land's decay unobservable in any game this tool can ever
    run, equivalent to "never decays" without saying so. Rather than adopt
    the raw value, a new general guardrail
    (`guardrails.half_life_ceiling_turns = 30`, enforced in
    `_permanent_type_half_life` below on ALL five types, not just Land) caps
    it - Land sits at that ceiling (12->30), a disclosed modeling decision
    in the same spirit as v4.67.0's green wipe-readiness policy floor, not a
    value read off the data like the other four.

Known, disclosed limitations of this whole approach (not silently glossed
over): the hand-sampling simulation is a static "opening hand" snapshot, not
a turn-by-turn game simulation across a full game; card price is a rough,
correlational quality proxy, not a causal measure of removal efficiency; and
`removal_target_types` itself is a documented regex approximation (misses
vote-based effects). Full raw-value tables and the price-weighting formula:
Docs/opponent_model_calibration_v4_70_0.md.

v4.71.0 ("Wertigkeits-Funktion" + Engine-Integration audit): the user asked
three things. (1) Whether the "Engine-Integration (App/engine.py-
Zugschleife)" item, carried since v4.43.0 in opponent_state_weights.json's
"note" field as "Verbleibend offen", was actually still open. It was not:
the real turn-loop integration (`advanced_opponent_model`/
`advanced_opponent_seats`, `_apply_advanced_opponent_phase` and friends
below) has existed since v4.63.0, is wired into the GUI (an "Erweitert"
seat-configuration dialog and a results tab), and is covered by
tests/test_advanced_opponent_model.py including a real end-to-end
simulate_game run. The stale sentence was simply never removed from the
JSON's historical note trail - corrected in place there (see that field's
own text) rather than treated as a real code gap.

(2) A non-linear, logarithmic, floor-bounded "Wertigkeit" (value) function
for card price, replacing linear price-weighting, per the user's explicit
spec: "kleine Aenderungen im Preis machen schon einiges aus, aber der
Unterschied zwischen einer 30-Euro-Karte und einer 500-Euro-Karte sollte
kaum merkbar sein. Keine Karte soll jemals nie interagierend sein - ein Wert
von 0 sollte eine Karte nicht [...] immun machen." Implemented as three new
functions below: `_card_value_weight` (the saturating log1p curve itself,
with an explicit floor so a $0 price never produces a 0 weight),
`_bucket_value_multiplier` (maps a bucket's real, play-frequency-weighted
average price - `permanent_type_value_usd`, newly derived from all 1,585
decks, THE PERMANENT'S OWN PRICE this time, not the answering removal
spell's price like v4.70.0's signal - onto a bounded half-life multiplier),
and `_effective_half_life` (the single place that now combines the
frequency-derived base, the existing bracket-level
`impact_half_life_multiplier`, and this new bucket-value multiplier, then
re-applies `guardrails.half_life_ceiling_turns` to the FINAL combined
result - not just the raw table value as in v4.70.0 - as a structural,
belt-and-suspenders guarantee against the user's named immunity risk,
independent of how carefully the curve itself is calibrated). The two call
sites in `advance_opponent_state` (passive_value/sac_drain decay,
disruption_lockout decay) were updated to go through `_effective_half_life`
instead of the old flat `_permanent_type_half_life(bucket) * impact_mult`.
`bracket_scaling.*.impact_half_life_multiplier` itself is left unchanged -
it still cannot be grounded in real per-deck Bracket labels (those exist
only for the small, targeted ~30-deck calibration sample, not the full
1,585), so it remains a disclosed, reasoned estimate representing a
different, complementary dimension ("how powerful is this whole deck")
from the new bucket-value factor ("how valuable is a typical permanent of
this type").

(3) A full audit of every prior version's disclosed gaps, to check what is
now actually closed versus still genuinely open. Full results: Docs/
opponent_model_calibration_v4_71_0.md - the short version is that the
Engine-Integration item above was the only one that was actually wrong;
every other disclosed gap (4-/5-color and colorless identities, the guild-
synergy gap, real turn-by-turn half-life validation without logged game
data) remains genuinely open and is listed there with its current status.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set

_WEIGHTS_PATH = Path(__file__).resolve().parent.parent.parent / "Data" / "Models" / "opponent_state_weights.json"

_KNOWN_COLORS = ("W", "U", "B", "R", "G")

# Hard-enforced regardless of Data/Models/opponent_state_weights.json tuning
# (belt-and-suspenders on top of guardrails.wipe_min_turn_hard_floor in the
# JSON itself) - the user's explicit example rule: a board wipe effect is
# realistically never cheaper than ~4-5 mana, so it cannot be "available" any
# earlier than this, no matter how a future weight edit tunes wipe_min_turn.
GUARDRAIL_WIPE_MIN_TURN = 4

# v4.39.0: same belt-and-suspenders pattern as GUARDRAIL_WIPE_MIN_TURN, for
# combo_finish_readiness (see module docstring, "Iteration 2" section). Even
# a cEDH-level deck realistically cannot have assembled and resolved a real
# alternate-win-condition/combo line before turn 3.
GUARDRAIL_COMBO_MIN_TURN = 3
# Evidenced by the Game-Changer-density jump found in the real decklist
# sample (0-2 cards at Bracket <=3 vs. 4-5+ at Bracket >=4 in every single
# sampled deck) - combo_finish_readiness is hard-gated to Bracket 4+
# regardless of weight tuning.
GUARDRAIL_COMBO_MIN_BRACKET = 4

# v4.40.0: the permanent-type buckets used by passive_value_by_type and
# sac_drain_by_type. A fixed, small set (not an open-ended card list) - see
# module docstring "Iteration 3". Deliberately NOT extended with planeswalker/
# land (see DISRUPTION_PERMANENT_TYPE_BUCKETS below) - every real Game
# Changer feeding these two stocks is an artifact, enchantment, or creature
# (see Data/Models/game_changer_archetypes.json), and changing this tuple
# would break every existing test/state that constructs a 3-key
# passive_value_by_type/sac_drain_by_type dict by hand.
PERMANENT_TYPE_BUCKETS = ("artifact", "enchantment", "creature")

# v4.43.0 (closes the "unmapped_persistent_disruption" gap from v4.40.0/
# v4.41.0's Docs/README.md open-points review): the 9 real, verified Game
# Changers that are persistent, STATIC stax/denial permanents (Braids Cabal
# Minion, Drannith Magistrate, Grand Arbiter Augustin IV, Humility, Narset
# Parter of Veils, Notion Thief, Opposition Agent, Tergrid God of Fright, The
# Tabernacle at Pendrell Vale) include two permanent types PERMANENT_TYPE_
# BUCKETS does not cover: Narset is a PLANESWALKER and the Tabernacle is a
# LAND - both real, not invented (verified via scrollvault.net's game-
# changers guide). A separate, wider bucket set for JUST this new dimension
# avoids the PERMANENT_TYPE_BUCKETS backward-compatibility problem above.
DISRUPTION_PERMANENT_TYPE_BUCKETS = ("artifact", "enchantment", "creature", "planeswalker", "land")

_GAME_CHANGER_ARCHETYPES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "Data" / "Models" / "game_changer_archetypes.json"
)


def _load_game_changer_archetypes(path: Path = _GAME_CHANGER_ARCHETYPES_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_GAME_CHANGER_ARCHETYPES = _load_game_changer_archetypes()


def reload_game_changer_archetypes() -> None:
    global _GAME_CHANGER_ARCHETYPES
    _GAME_CHANGER_ARCHETYPES = _load_game_changer_archetypes()


def _load_weights(path: Path = _WEIGHTS_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_WEIGHTS = _load_weights()


def reload_weights() -> None:
    global _WEIGHTS
    _WEIGHTS = _load_weights()


# v4.66.0 ("Kalibrierungs-Synthese Teil 1", see module docstring): the 90
# real-decklist flavor cells, compiled losslessly into a separate data file
# rather than folded into _WEIGHTS/opponent_state_weights.json above - see
# the module docstring for why these stay a distinct, strictly OPT-IN
# lookup instead of changing this module's actual default weights.
_FLAVOR_MATRIX_PATH = (
    Path(__file__).resolve().parent.parent.parent / "Data" / "Models" / "flavor_strategy_matrix.json"
)

# The 10 growth-rate/curve dimensions a flavor cell's "state_function" can
# override - deliberately the exact same key set opponent_state_weights.
# json's strategy_curves entries use, so a flavor cell is a drop-in
# replacement for "curve[dimension] * _color_multiplier(colors, dimension)"
# rather than a parallel, differently-shaped concept.
FLAVOR_STATE_FUNCTION_FIELDS = (
    "board_presence_growth", "interaction_growth", "wipe_growth", "combo_growth",
    "passive_value_growth", "sac_drain_growth", "disruption_growth", "mana_growth",
    "variance_amplitude", "dead_turn_chance_base",
)


def _load_flavor_matrix(path: Path = _FLAVOR_MATRIX_PATH) -> Dict[str, Any]:
    if not path.exists():
        # Disclosed, not silent: an opt-in feature whose data file is
        # missing behaves exactly as if no flavor were ever configured
        # (see _flavor_cell), it never crashes module import - the same
        # "fail safe toward the pre-existing behavior" preference as the
        # rest of this module's fallback handling.
        return {"cells": {}, "legacy_cells": {}}
    return json.loads(path.read_text(encoding="utf-8"))


_FLAVOR_MATRIX = _load_flavor_matrix()


def reload_flavor_matrix() -> None:
    global _FLAVOR_MATRIX
    _FLAVOR_MATRIX = _load_flavor_matrix()


def _canonical_color_key(colors: Set[str]) -> str:
    """WUBRG-ordered color-identity string used as the flavor matrix's
    lookup key (e.g. {"G", "W"} -> "WG", matching how Selesnya/GW cells are
    stored) - independent of what order/spelling a caller passes colors in."""
    order = "WUBRG"
    upper = {c.upper() for c in colors}
    return "".join(c for c in order if c in upper)


def _flavor_cell(colors: Set[str], flavor: Optional[str], *, include_legacy: bool = False) -> Optional[Dict[str, Any]]:
    """Looks up one flavor-strategy-matrix cell by (color identity, flavor
    slug). Returns None (never raises) if `flavor` is falsy, unknown, or its
    stored color_identity does not match `colors` - every caller of this
    function is expected to fall back to the pre-existing curve*color-
    modifier behavior in that case, per the module docstring's disclosed-
    fallback-over-invented-precision preference. `include_legacy=True` also
    searches superseded-taxonomy cells (currently just G/ramp_big_mana, see
    flavor_strategy_matrix.json) - off by default since those are explicitly
    not part of the active 6-flavor-per-identity taxonomy."""
    if not flavor:
        return None
    key = _canonical_color_key(colors)
    cell_id = flavor if "/" in flavor else f"{key}/{flavor}"
    cell = _FLAVOR_MATRIX.get("cells", {}).get(cell_id)
    if cell is None and include_legacy:
        cell = _FLAVOR_MATRIX.get("legacy_cells", {}).get(cell_id)
    if cell is None:
        return None
    if cell.get("color_identity") != key:
        return None
    return cell


@dataclass
class OpponentProfile:
    """
    The "voreingestellte Stellparameter" (preset tunable parameters) the
    user named explicitly: strategy, color(s), and Bracket. Turn is NOT part
    of the profile - it lives on OpponentState, since it changes every turn
    while the profile itself is fixed for the whole game.
    """
    strategy: str = "midrange"
    colors: Set[str] = field(default_factory=set)
    bracket: int = 3
    # v4.66.0 ("Kalibrierungs-Synthese Teil 1", see module docstring): opt-in
    # flavor-strategy-matrix override, e.g. "G/landfall" or just "landfall"
    # (color identity then inferred from `colors`). None (default) means
    # "no override" - every pre-v4.66.0 caller that never sets this field
    # sees byte-identical behavior, see test_v4660_flavor_strategy_matrix.py.
    flavor: Optional[str] = None

    def __post_init__(self):
        self.colors = {c.upper() for c in self.colors if c.upper() in _KNOWN_COLORS}
        self.bracket = max(1, min(5, int(self.bracket)))


@dataclass
class OpponentState:
    """
    Abstract, card-agnostic per-opponent state. Every "readiness" dimension
    is a 0..1 probability-flavoured proxy for "is this currently available
    to the opponent RIGHT NOW", not a count of specific cards - per the
    user's explicit instruction that the model should ask "what STATES can
    individual cards invoke/create/influence", not track the cards
    themselves.

    life and cards_remaining are the two concrete, literal values the user
    named explicitly ("Leben, Anzahl an Karten im Deck"); the rest
    (board_presence, interaction_availability, wipe_readiness,
    mana_availability, hand_quality) are the abstract proxies the user asked
    to be derived rather than card-tracked.
    """
    life: float = 40.0
    turn: int = 0
    cards_remaining: int = 92  # ~99-card Commander deck minus a 7-card opening hand
    board_presence: float = 0.0        # 0..10ish "effective blocker/pressure body count"
    interaction_availability: float = 0.0  # 0..1 - chance of live removal/counterspell/protection in hand right now
    wipe_readiness: float = 0.0        # 0..1 - chance of a castable board wipe in hand right now
    mana_availability: float = 0.0     # 0..1 - how "online" the mana base currently is
    hand_quality: float = 0.5          # 0..1 - fraction of hand that is currently live/castable
    dead_turn: bool = False            # True if the last advance_opponent_state() call rolled a "did essentially nothing" turn
    # v4.39.0 ("Iteration 2", see module docstring): 0..1 - chance the
    # opponent currently has an alternate win condition / combo finish
    # assembled and live. Hard-gated to Bracket >= GUARDRAIL_COMBO_MIN_BRACKET
    # and turn >= GUARDRAIL_COMBO_MIN_TURN - see advance_opponent_state.
    combo_finish_readiness: float = 0.0
    # v4.40.0 ("Iteration 3", see module docstring): persistent, DECAYING
    # stocks for passive value/tax engines (Rhystic Study-style) and
    # sacrifice/aristocrats drain loops (Ashnod's Altar + death-trigger
    # drain-style), each broken down by PERMANENT_TYPE_BUCKETS - not to
    # simulate the permanent itself, but so a later integration step can
    # check whether the tested deck's own removal suite can interact with
    # that permanent type at all (the user's own reasoning for why the
    # permanent-type tag matters). See query_board_effects.
    passive_value_by_type: Dict[str, float] = field(
        default_factory=lambda: {k: 0.0 for k in PERMANENT_TYPE_BUCKETS}
    )
    sac_drain_by_type: Dict[str, float] = field(
        default_factory=lambda: {k: 0.0 for k in PERMANENT_TYPE_BUCKETS}
    )
    # v4.43.0: a THIRD decaying stock, for persistent, STATIC stax/denial
    # permanents (Drannith Magistrate/Grand Arbiter/Humility/Opposition
    # Agent-style effects) that neither generate card advantage
    # (passive_value_by_type) nor drain life (sac_drain_by_type), but instead
    # persistently DENY the tested player some option. Broken down by
    # DISRUPTION_PERMANENT_TYPE_BUCKETS (wider than the other two stocks -
    # see that constant's docstring for why). Same growth+decay mechanism as
    # the other two stocks - see advance_opponent_state.
    disruption_lockout_by_type: Dict[str, float] = field(
        default_factory=lambda: {k: 0.0 for k in DISRUPTION_PERMANENT_TYPE_BUCKETS}
    )

    # life is intentionally NOT touched by advance_opponent_state - combat
    # damage and other life-total changes remain the caller's/engine's
    # responsibility (see module docstring, "out of scope"). It stays on
    # this dataclass because the user explicitly named life as one of the
    # values that must be tracked as part of the opponent's state.


def _strategy_curve(strategy: str) -> Dict[str, float]:
    curves = _WEIGHTS["strategy_curves"]
    return curves.get(strategy, curves["midrange"])


def _bracket_config(bracket: int) -> Dict[str, float]:
    table = _WEIGHTS["bracket_scaling"]
    return table.get(str(max(1, min(5, int(bracket)))), table["3"])


def _color_multiplier(colors: Set[str], dimension: str) -> float:
    mods = _WEIGHTS["color_modifiers"]
    mult = 1.0
    for c in colors:
        mult *= mods.get(c, {}).get(dimension, 1.0)
    return mult


def _wipe_min_turn(curve: Dict[str, float]) -> int:
    """The effective minimum turn for wipe_readiness to leave 0, after
    applying BOTH the JSON-level guardrail and the hard-coded
    GUARDRAIL_WIPE_MIN_TURN floor - see module docstring."""
    json_floor = int(_WEIGHTS.get("guardrails", {}).get("wipe_min_turn_hard_floor", GUARDRAIL_WIPE_MIN_TURN))
    return max(int(curve.get("wipe_min_turn", 999)), json_floor, GUARDRAIL_WIPE_MIN_TURN)


def _combo_min_turn(curve: Dict[str, float]) -> int:
    """Same double-floor pattern as _wipe_min_turn, for combo_finish_readiness
    (v4.39.0) - see module docstring. Unlike wipe_min_turn, no strategy_curve
    currently declares an explicit "combo_min_turn" (no evidence yet
    justifying a per-strategy override beyond the shared guardrail floor) -
    so a MISSING key defaults to 0 here (not 999, which would mean "never"
    and would silently disable combo_finish_readiness for every strategy,
    since none of them currently sets this key at all)."""
    json_floor = int(_WEIGHTS.get("guardrails", {}).get("combo_min_turn_hard_floor", GUARDRAIL_COMBO_MIN_TURN))
    return max(int(curve.get("combo_min_turn", 0)), json_floor, GUARDRAIL_COMBO_MIN_TURN)


def _combo_min_bracket() -> int:
    json_floor = int(_WEIGHTS.get("guardrails", {}).get("combo_min_bracket_hard_floor", GUARDRAIL_COMBO_MIN_BRACKET))
    return max(json_floor, GUARDRAIL_COMBO_MIN_BRACKET)


def _half_life_decay_multiplier(half_life_turns: float) -> float:
    """Fraction remaining after one turn, given a half-life of
    `half_life_turns` turns (0.5 ** (1/half_life)). A half_life <= 0 means
    "never decays" (multiplier 1.0) - not currently used by any real bucket,
    but kept safe rather than dividing by zero."""
    if half_life_turns <= 0:
        return 1.0
    return 0.5 ** (1.0 / half_life_turns)


def _half_life_ceiling() -> float:
    """v4.70.0 ('Halbwertszeiten-Recherche' - see module docstring):
    permanent_type_half_life_turns.land's raw hand-sampling extrapolation
    (~63.8 turns) exceeds this tool's own maximum simulatable game length
    (App/gui.py's turns_var Spinbox goes up to 30), which would make Land's
    half-life decay practically unobservable in any game this tool can ever
    simulate - silently equivalent to "never decays" without disclosing it
    as such. This ceiling is a disclosed, guardrail-level policy cap on
    EVERY permanent_type_half_life_turns entry (not just Land), following
    the same pattern as the existing wipe_min_turn/combo_min_turn hard
    floors, sourced from guardrails.half_life_ceiling_turns."""
    return float(_WEIGHTS.get("guardrails", {}).get("half_life_ceiling_turns", 30.0))


def _permanent_type_half_life(bucket: str) -> float:
    table = _WEIGHTS.get("permanent_type_half_life_turns", {})
    raw = float(table.get(bucket, 6.0))
    return min(raw, _half_life_ceiling())


def _impact_half_life_multiplier(bracket_cfg: Dict[str, float]) -> float:
    """v4.41.0 ('Iteration 3b', LSV/'threat relevance' refinement - see module
    docstring): multiplies the base, permanent-type half-life from
    `_permanent_type_half_life`. <1.0 SHORTENS the half-life (answered
    faster), 1.0 leaves it unchanged, missing/absent means unchanged.

    This is NOT a per-card LSV number (no such universal rating exists for
    old Commander staples - see the v4.41.0 README/calibration-doc research
    note) but a bracket-level stand-in for the same real phenomenon LSV's
    scale describes for Limited: a higher-impact ('bomb-tier') permanent
    draws removal priority and survives fewer turns than an unremarkable
    filler permanent, which often gets ignored and sits for a long time.
    Since Game-Changer density (the one real, rule-verified 'this pod
    contains bomb-tier permanents' signal available to this model) rises
    sharply with Bracket (see the v4.39.0 and v4.41.0 calibration docs),
    Bracket stands in for average board-impact here. The magnitude is a
    disclosed, REASONED estimate, not measured from decklists - no game logs
    exist to count real removed-on-turn-X data - see the module docstring
    for the honest limitation.

    v4.71.0: this bracket-level factor is kept as-is (still disclosed as
    reasoned, not measured - no per-deck Bracket label exists for the full
    1,585-deck dataset, so it still cannot itself be grounded in real data)
    but is now COMBINED with a new, genuinely data-grounded per-bucket
    factor - see `_bucket_value_multiplier` and `_effective_half_life`
    below - rather than replaced. Bracket captures "how powerful is this
    whole deck" (a per-game dimension); the new factor captures "how
    valuable is a typical permanent of this specific type" (a per-bucket
    dimension) - genuinely different, complementary signals."""
    return float(bracket_cfg.get("impact_half_life_multiplier", 1.0))


def _card_value_weight(price_usd: float) -> float:
    """v4.71.0 ("Wertigkeits-Funktion" - see module docstring): a bounded,
    LOGARITHMIC-saturation proxy for "how worth answering is a permanent
    priced around `price_usd`", per the user's explicit spec:

      - "nicht linear [...] sondern logarithmisch" - uses log1p(price), not
        price itself, so the curve is concave (diminishing returns).
      - "kleine Aenderungen im Preis machen schon einiges aus" at the low
        end - a $0 vs $5 card differs a lot (raw jumps from 0.0 to ~0.88 at
        the calibrated saturation constant below).
      - "der Unterschied [...] bei einer 30-Euro-Karte und einer
        500-Euro-Karte sollte kaum merkbar sein" - the same curve, evaluated
        at $30 vs $500, differs by only ~0.03 in raw terms (~0.02 after the
        floor below) - both already deep in the saturated regime.
      - "keine Karte soll [...] durch ihre Wertigkeit immun [werden]" - a
        literal price of $0 must NOT collapse this to 0 and, downstream,
        to an unboundedly long (effectively infinite/"immune") half-life.
        Enforced TWICE here: once by the `floor` below (this function never
        returns exactly 0), and again, belt-and-suspenders, by
        `_effective_half_life` re-applying `half_life_ceiling_turns` to the
        FINAL combined half-life regardless of what this function returns.

    Formula: `floor + (1-floor) * log1p(price) / (log1p(price) + k)`, `k`
    and `floor` read from `card_value_weighting` in opponent_state_weights.
    json (k=0.25, floor=0.3 as shipped - see that key's own `_comment` for
    the calibration against the user's $30-vs-$500 example). Returns a
    value in [floor, 1.0) - never 0, never exactly 1."""
    cfg = _WEIGHTS.get("card_value_weighting", {})
    k = float(cfg.get("log_saturation_k", 0.25))
    floor = float(cfg.get("floor", 0.3))
    price = max(0.0, float(price_usd))
    log_price = math.log1p(price)
    raw = log_price / (log_price + k) if (log_price + k) > 0 else 0.0
    return floor + (1.0 - floor) * raw


def _bucket_value_multiplier(bucket: str) -> float:
    """v4.71.0: maps `bucket`'s real, play-quantity-weighted average card
    price (`permanent_type_value_usd` in opponent_state_weights.json - see
    Docs/opponent_model_calibration_v4_71_0.md for the derivation from all
    1,585 real decks) through `_card_value_weight`, then onto a bounded
    half-life MULTIPLIER range (`card_value_weighting.min_multiplier` /
    `.max_multiplier`, 0.65/1.25 as shipped): a bucket whose typical
    permanent is pricier gets a multiplier BELOW 1.0 (shortens its
    half-life - worth answering sooner), a bucket whose typical permanent
    is cheap gets a multiplier ABOVE 1.0 but explicitly BOUNDED (never
    unboundedly long, never "immune" - see `_card_value_weight` and
    `_effective_half_life`)."""
    prices = _WEIGHTS.get("permanent_type_value_usd", {})
    price = float(prices.get(bucket, 2.0))
    weight = _card_value_weight(price)
    cfg = _WEIGHTS.get("card_value_weighting", {})
    min_mult = float(cfg.get("min_multiplier", 0.65))
    max_mult = float(cfg.get("max_multiplier", 1.25))
    return max_mult - weight * (max_mult - min_mult)


def _effective_half_life(bucket: str, bracket_cfg: Dict[str, float]) -> float:
    """v4.71.0: the single place that combines every half-life factor for
    `bucket` - the frequency-derived base (`_permanent_type_half_life`,
    already itself ceiling-capped once), the bracket-level impact factor
    (`_impact_half_life_multiplier`), and the new price-grounded bucket
    value factor (`_bucket_value_multiplier`) - and re-applies
    `half_life_ceiling_turns` to the FINAL combined result, not just the
    raw table lookup. This is a deliberate belt-and-suspenders guarantee:
    no future combination of multipliers (a cheap-bucket multiplier above
    1.0 stacked with a lenient bracket multiplier, say) can silently push
    an effective half-life past the tool's own maximum simulatable game
    length again - the exact failure mode `half_life_ceiling_turns` was
    introduced in v4.70.0 to prevent for the raw table alone, now closed
    for the fully-combined value too, per the user's explicit "no card
    should ever become immune through its value" requirement."""
    base = _permanent_type_half_life(bucket)
    combined = base * _impact_half_life_multiplier(bracket_cfg) * _bucket_value_multiplier(bucket)
    return min(combined, _half_life_ceiling())


def _pick_permanent_type(rng: random.Random, distribution: Dict[str, float]) -> str:
    """Weighted random pick of one of PERMANENT_TYPE_BUCKETS, given a
    {bucket: weight} distribution (need not sum to 1 - normalized here)."""
    items = [(k, v) for k, v in distribution.items() if v > 0]
    if not items:
        return PERMANENT_TYPE_BUCKETS[0]
    total = sum(w for _k, w in items)
    roll = rng.random() * total
    upto = 0.0
    for bucket, weight in items:
        upto += weight
        if roll <= upto:
            return bucket
    return items[-1][0]


def _permanent_type_distribution(dimension: str) -> Dict[str, float]:
    table = _WEIGHTS.get("permanent_type_distribution", {})
    return table.get(dimension, {"artifact": 1.0})


def _growth_rate(
    profile: "OpponentProfile", curve_field: str, modifier_dimension: str, curve: Dict[str, float]
) -> float:
    """v4.66.0 (see module docstring): the single place `advance_opponent_
    state` looks up a per-turn growth rate. `curve_field` is the strategy-
    curve/flavor-state-function key (e.g. "board_presence_growth");
    `modifier_dimension` is the SEPARATE color_modifiers key the pre-v4.66.0
    formula multiplies by (e.g. "board_presence" - several dimensions use a
    shorter/differently-worded color_modifiers key than their curve field
    name, see opponent_state_weights.json, so the two are intentionally not
    assumed to be the same string).

    If `profile.flavor` resolves to a real flavor-strategy-matrix cell
    matching `profile.colors` AND `curve_field` is one of the 10 FLAVOR_
    STATE_FUNCTION_FIELDS, that cell's own value is used DIRECTLY (it is
    already the proposed final replacement for curve*modifier, not an extra
    multiplier - see the module docstring). Otherwise falls back to the
    exact pre-v4.66.0 formula (`curve[curve_field] *
    _color_multiplier(profile.colors, modifier_dimension)`) - identical for
    every profile that never sets `flavor`."""
    if curve_field in FLAVOR_STATE_FUNCTION_FIELDS:
        cell = _flavor_cell(profile.colors, profile.flavor)
        if cell is not None:
            return float(cell["state_function"][curve_field])
    return curve.get(curve_field, 0.0) * _color_multiplier(profile.colors, modifier_dimension)


def advance_opponent_state(
    state: OpponentState,
    profile: OpponentProfile,
    rng: random.Random,
    *,
    table_size: int = 4,
) -> OpponentState:
    """
    THE state equation. Called once per simulated OPPONENT turn (the "update"
    half of the user's query/update split). Mutates and returns `state`.

    Identical formula for every profile - see module docstring. Only the
    looked-up weights (strategy curve, color multipliers, bracket scaling)
    differ between an aggro-mono-red-Bracket-2 opponent and a
    control-Esper-Bracket-5 opponent; the code path is the same call.

    `table_size` (v4.40.0, default 4 - a typical Commander pod) is the ONLY
    parameter here that is not per-opponent: it is a property of the whole
    game, needed because passive_value_by_type's growth (Rhystic Study/
    Smothering Tithe-style effects) realistically scales with how many
    OTHER players are at the table, not just interaction against the one
    tested player. See module docstring "Iteration 3".
    """
    curve = _strategy_curve(profile.strategy)
    bracket_cfg = _bracket_config(profile.bracket)
    power_mult = bracket_cfg["power_multiplier"]
    variance_mult = bracket_cfg["variance_multiplier"]
    consistency_floor = bracket_cfg["consistency_floor"]

    state.turn += 1

    # v4.39.0 ("Iteration 2"): a one-time turn-1 mana spike, evidenced by
    # every "expensive"/high-Bracket real decklist in the calibration sample
    # adding a cluster of explosive fast-mana artifacts (Ancient Tomb, Mana
    # Vault, Chrome Mox, Jeweled Lotus, Lotus Petal, Ashnod's/Phyrexian
    # Altar) that was completely absent from every lower-Bracket list - a
    # front-loaded jump, not steady per-turn growth, so it is applied once
    # rather than folded into mana_growth.
    if state.turn == 1:
        opening_boost = bracket_cfg.get("opening_mana_boost", 0.0)
        state.mana_availability = max(0.0, min(1.0, state.mana_availability + opening_boost))

    # --- Genuine variance: one shared "how did this turn go" roll ---------
    # A single continuous roll stands in for everything from a clunky draw
    # to a perfect curve-out; a SEPARATE discrete roll below models the more
    # extreme "essentially unplayable hand" case explicitly, per the user's
    # own examples ("unplayable cards in hand", "possibly empty hands",
    # "un-drawn alternatives", "suboptimal turns" are explicitly called out
    # as distinct from a merely-average turn).
    # v4.66.0: variance_amplitude has no color_modifiers entry at all in
    # opponent_state_weights.json - _color_multiplier(colors, "variance_
    # amplitude") is therefore always exactly 1.0 regardless of colors, so
    # routing this through _growth_rate is a byte-identical no-op for every
    # profile without a flavor, while still picking up a flavor cell's own
    # variance_amplitude value when one is active.
    amplitude = max(0.0, _growth_rate(profile, "variance_amplitude", "variance_amplitude", curve) * variance_mult)
    turn_quality = 1.0 + rng.uniform(-amplitude, amplitude)
    turn_quality = max(0.05, turn_quality)

    # v4.66.0: dead_turn_chance_base is one of the 10 flavor-overridable
    # fields, but (unlike every other field) the pre-v4.66.0 formula's
    # color-modifier dimension key ("dead_turn_chance") does not match the
    # curve-field name ("dead_turn_chance_base") - _growth_rate's generic
    # curve_field/modifier_dimension split does not apply directly here
    # because a flavor cell's dead_turn_chance_base is already the proposed
    # FINAL value (see module docstring), so it must NOT additionally be
    # multiplied by _color_multiplier(colors, "dead_turn_chance") once a
    # flavor is active - doing so would double-apply the color influence the
    # flavor research already baked in. Handled explicitly instead of via
    # _growth_rate to keep that helper's contract simple and correct for
    # its other 9 call sites below.
    _flavor_cell_for_turn = _flavor_cell(profile.colors, profile.flavor)
    if _flavor_cell_for_turn is not None:
        dead_turn_base = float(_flavor_cell_for_turn["state_function"]["dead_turn_chance_base"])
        dead_turn_chance = dead_turn_base * variance_mult * (1.0 - consistency_floor)
    else:
        dead_turn_chance = (
            curve["dead_turn_chance_base"]
            * variance_mult
            * (1.0 - consistency_floor)
            * _color_multiplier(profile.colors, "dead_turn_chance")
        )
    dead_turn_chance = max(0.0, min(0.9, dead_turn_chance))
    dead_turn = rng.random() < dead_turn_chance
    state.dead_turn = dead_turn
    # A dead turn still happens (the clock keeps running) but contributes
    # almost nothing to board/interaction/mana development this turn.
    effective_quality = 0.1 if dead_turn else turn_quality

    def _grow(current: float, growth_rate: float, cap: float) -> float:
        gained = growth_rate * power_mult * effective_quality
        return max(0.0, min(cap, current + gained))

    state.board_presence = _grow(
        state.board_presence,
        _growth_rate(profile, "board_presence_growth", "board_presence", curve),
        cap=10.0,
    )
    state.interaction_availability = _grow(
        state.interaction_availability,
        _growth_rate(profile, "interaction_growth", "interaction_availability", curve),
        cap=1.0,
    )
    state.mana_availability = max(
        consistency_floor,
        _grow(
            state.mana_availability,
            _growth_rate(profile, "mana_growth", "mana_growth", curve),
            cap=1.0,
        ),
    )
    # hand_quality tracks the current turn's quality directly (bounded
    # 0..1), rather than accumulating - a bad turn now means a currently
    # weaker hand NOW, it does not permanently damage future turns (those
    # get their own fresh turn_quality roll).
    state.hand_quality = max(consistency_floor, min(1.0, 0.5 * effective_quality))

    min_wipe_turn = _wipe_min_turn(curve)
    if state.turn >= min_wipe_turn:
        state.wipe_readiness = _grow(
            state.wipe_readiness,
            _growth_rate(profile, "wipe_growth", "wipe_readiness", curve),
            cap=1.0,
        )
    else:
        state.wipe_readiness = 0.0

    # v4.39.0 ("Iteration 2"): combo_finish_readiness, hard-gated to
    # Bracket >= GUARDRAIL_COMBO_MIN_BRACKET (regardless of curve tuning) AND
    # turn >= the combo-min-turn guardrail - see module docstring for the
    # real-decklist evidence behind both the dimension and the gate.
    if profile.bracket >= _combo_min_bracket() and state.turn >= _combo_min_turn(curve):
        state.combo_finish_readiness = _grow(
            state.combo_finish_readiness,
            _growth_rate(profile, "combo_growth", "combo_finish_readiness", curve),
            cap=1.0,
        )
    else:
        state.combo_finish_readiness = 0.0

    # v4.40.0 ("Iteration 3"): passive value/tax engines and sacrifice-drain
    # loops - decay (half-life) is applied FIRST to whatever already sits in
    # each bucket (representing time passing since last turn, e.g. someone
    # else at the table dealing with it), THEN this turn's own growth is
    # added fresh - see module docstring for the full reasoning.
    for bucket in PERMANENT_TYPE_BUCKETS:
        decay = _half_life_decay_multiplier(_effective_half_life(bucket, bracket_cfg))
        state.passive_value_by_type[bucket] *= decay
        state.sac_drain_by_type[bucket] *= decay

    table_multiplier = max(0.0, (table_size - 1) / 3.0)
    passive_growth_rate = (
        _growth_rate(profile, "passive_value_growth", "passive_value_growth", curve) * table_multiplier
    )
    passive_gain = passive_growth_rate * power_mult * effective_quality
    if passive_gain > 0:
        bucket = _pick_permanent_type(rng, _permanent_type_distribution("passive_value"))
        state.passive_value_by_type[bucket] = min(1.0, state.passive_value_by_type[bucket] + passive_gain)

    sac_growth_rate = _growth_rate(profile, "sac_drain_growth", "sac_drain_growth", curve)
    sac_gain = sac_growth_rate * power_mult * effective_quality
    if sac_gain > 0:
        bucket = _pick_permanent_type(rng, _permanent_type_distribution("sac_drain"))
        state.sac_drain_by_type[bucket] = min(1.0, state.sac_drain_by_type[bucket] + sac_gain)

    # v4.43.0: persistent static stax/denial permanents - same growth+decay
    # mechanism as passive_value/sac_drain above, but its own (wider) bucket
    # set. Scaled by table_size like passive_value_by_type: the majority of
    # the 9 real Game Changers behind this dimension (Grand Arbiter,
    # Opposition Agent, Narset, Notion Thief) explicitly say "each opponent"/
    # "another player" in their own card text, i.e. their real value is
    # table-wide, not just pressure on the one tested player - see module
    # docstring for the full card-by-card evidence.
    for bucket in DISRUPTION_PERMANENT_TYPE_BUCKETS:
        decay = _half_life_decay_multiplier(_effective_half_life(bucket, bracket_cfg))
        state.disruption_lockout_by_type[bucket] *= decay

    disruption_growth_rate = (
        _growth_rate(profile, "disruption_growth", "disruption_growth", curve) * table_multiplier
    )
    disruption_gain = disruption_growth_rate * power_mult * effective_quality
    if disruption_gain > 0:
        bucket = _pick_permanent_type(rng, _permanent_type_distribution("disruption_lockout"))
        state.disruption_lockout_by_type[bucket] = min(1.0, state.disruption_lockout_by_type[bucket] + disruption_gain)

    # Deck depletion proxy: draw for turn, unless the turn was so dead the
    # opponent is assumed to be near/at an empty library already.
    if state.cards_remaining > 0:
        state.cards_remaining -= 1

    return state


@dataclass
class CombatQuery:
    """Result of query_combat_state - read-only, no card specifics."""
    effective_blockers: float
    block_chance_multiplier: float


@dataclass
class CastabilityQuery:
    """Result of query_castable_state - read-only, no card specifics."""
    has_interaction: bool
    has_wipe: bool
    has_big_play: bool
    has_combo_finish: bool = False


def query_combat_state(state: OpponentState) -> CombatQuery:
    """
    Queried DURING THE SIMULATED PLAYER'S OWN TURN, at the combat-phase
    decision point the user named explicitly. Pure read - never mutates
    `state`. A `dead_turn` (rolled by the most recent advance_opponent_state
    call, i.e. the opponent's own last turn) halves the EFFECTIVE blockers
    available right now (a clunky turn means fewer creatures untapped/held
    back to block), but does not erase board_presence itself - creatures
    already on the battlefield from earlier turns do not vanish just
    because this last turn was bad.
    """
    effective = state.board_presence * (0.5 if state.dead_turn else 1.0)
    return CombatQuery(
        effective_blockers=effective,
        block_chance_multiplier=1.0 + min(1.0, effective / 5.0),
    )


@dataclass
class BoardEffectsQuery:
    """
    Result of query_board_effects - read-only. Exposes the PERMANENT_TYPE
    breakdown (not just a single aggregate number) precisely so a later
    integration step can compare it against the tested deck's own real
    removal suite (does it have enchantment removal? artifact removal?) -
    see module docstring "Iteration 3" for why the user asked for this
    breakdown rather than one lump value.
    """
    passive_value_total: float
    passive_value_by_type: Dict[str, float]
    sac_drain_total: float
    sac_drain_by_type: Dict[str, float]
    # v4.43.0: third stock, see OpponentState.disruption_lockout_by_type.
    disruption_lockout_total: float = 0.0
    disruption_lockout_by_type: Dict[str, float] = field(default_factory=dict)


def query_board_effects(state: OpponentState) -> BoardEffectsQuery:
    """
    Queried the same way as query_combat_state/query_castable_state - pure
    read, never mutates `state`. Returns the current passive-value,
    sacrifice-drain, and disruption-lockout stocks, each as a total and
    broken down by the permanent type they are modeled as living on.
    """
    return BoardEffectsQuery(
        passive_value_total=sum(state.passive_value_by_type.values()),
        passive_value_by_type=dict(state.passive_value_by_type),
        sac_drain_total=sum(state.sac_drain_by_type.values()),
        sac_drain_by_type=dict(state.sac_drain_by_type),
        disruption_lockout_total=sum(state.disruption_lockout_by_type.values()),
        disruption_lockout_by_type=dict(state.disruption_lockout_by_type),
    )


def query_castable_state(state: OpponentState, rng: random.Random) -> CastabilityQuery:
    """
    Queried at "what can currently be played" decision points - either
    during the simulated player's own turn (e.g. "would this resolve into
    live interaction?") or as the READ half of the opponent's own turn,
    before that turn's advance_opponent_state WRITE half runs - per the
    user's explicit turn-structure requirement.

    Each dimension is an INDEPENDENT probability roll against the current
    readiness value, not a deterministic threshold check - the same state
    can answer "no" on one query and "yes" on the next, because a nonzero
    interaction_availability means "the opponent COULD have this", not
    "the opponent DOES have this in hand this instant".
    """
    return CastabilityQuery(
        has_interaction=rng.random() < state.interaction_availability,
        has_wipe=rng.random() < state.wipe_readiness,
        has_big_play=rng.random() < (state.mana_availability * state.hand_quality),
        has_combo_finish=rng.random() < state.combo_finish_readiness,
    )
