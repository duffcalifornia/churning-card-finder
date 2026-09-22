# Engine contract (draft)

Signatures only. No logic yet. Types come from data/schema/*.json (profile, card, currency, program, results). Pure functions, no I/O, no dates read from the clock except where noted.

```ts
// 1. Derived standing for one player.
computeDerived(player: Player, catalog: Card[]): Derived
// Derived = { x24, overFiveTwentyFour, amexCredit, amexCharge, chaseBusinessOpen,
//             inkNoFee, inkAnnualFee (open Ink cards by fee, per player), everHad: Set<cardId>, unknownCardIds }
// Implemented in src/engine/computeDerived.ts. The Ink SSN/EIN split was dropped (K7): sole proprietors are caught either way.

// 2. Which currencies can this player use for transfers (hard filter on unlockers).
unlockStatus(players: Player[], currencies: Currency[]): Map<playerName, Map<currencyId, boolean>>
// Implemented in src/engine/unlockStatus.ts. No catalog needed (the currency data names the unlocker card ids). A currency with no
// unlocker cards is always unlocked; an unlocker counts only while currently open; player names must be unique.
// Uses currency.householdPooling: pooled currencies count another player's unlocker.

// 3. Rules that hide a card for a player outright.
hardExclusion(player: Player, card: Card, ctx: ExclusionContext): Exclusion | null
// ctx = { household, derived, ...more as later rule groups need them (unlock, programs, catalog, Marriott matrix) }.
// Implemented in src/engine/hardExclusion.ts. Rules run in a fixed order; the first that applies is returned.
// Group 1 (done): notRecommendable, shutdown (Schwab and Morgan Stanley follow Amex), aaBan, businessNotWanted, annualFee (first-year fee: waived counts as $0).
// Group 2 (done): chase5_24 (all Chase cards, business included; Ink is checked first at 3/24), ink3_24, barclays6_24, amexCardLimits (5 credit, 10 charge), boaCardCount (K5,
//   authorized-user accounts are ignored entirely), usbank5_12, discoverLimits, inkLimit (one no-fee and one annual-fee Ink open), stayUnder524.
// Group 3 (done, src/engine/bonusEligibility.ts): lifetime (Chase Sapphire and Ink, Citi Strata; approval-based; an Ink card's lifetime
//   block is lifted in hardExclusion.ts when player.willingToFormLlcForInk is true, K7), family (Capital One Venture
//   tiers), cooldown (24 months Chase, Southwest and IHG family clocks, BoA held-based; 48 months Citi and Capital One personal;
//   Barclays no second copy), marriottMatrix. Amex lifetime and family are NOT exclusions: see nllBlock below.
// Group 4 (done): spend (householdFilters.ts, capacity for 3 to 6 month windows), excludedProgram, unranked (hidden: the six cards with no
//   valuation and the Discover match cards), then noWantedBonusType / noUnlocker (bonusTypes.ts). ctx also carries currencies, programs
//   and this player's unlock row.
// Banners, not exclusions: rules that need windows shorter than the buckets (Amex 2/90 and 1/5, Chase 2/30, Citi 8/65).

// 4. Blocks that an NLL offer would remove. Only Amex family and lifetime rules. Implemented in src/engine/nllBlock.ts (lifetime
//    reported first if both apply). Every Amex card carries lifetime language, Marriott ones too: the matrix's EVER cells on Amex
//    cards count as lifetime (NLL-liftable) and all other matrix cells stay hard. nllBlock(player, derived, card, catalog, marriottMatrix).
nllBlock(player, derived, card, catalog): 'family' | 'lifetime' | null

// 5. Ranking (decided 2026-09-21): value ranking alone for the first version. No rankFor; recommend sorts each player's eligible
//    cards by netValue. The flowchart-list ranking (Section C) is deferred and the card `rank` fields are empty.
netValue(card: Card, valuations: Valuations, unlocked: boolean): number   // src/engine/netValue.ts
// bonusValue = points x cpp(currency, unlocked) / 100 + cashBack + otherValue + extra tiers; netValue = bonusValue - first-year annual fee (waived = $0).
// unlocked = the player's currency is unlocked, or the card is itself an unlocker for its currency (assumption: getting it unlocks).
// Ties break on card id. "As high as" offers are valued at their ceiling.
// recommend: each player's top N by netValue (+ ceiling backups), combined into one list ranked by value (a shared card at the
// highest value any player gets from it).

// 6. Spend capacity for a card's window.
spendCapacity(household, months: number): number
// 3 months: spend3 + supp3. 6 months: spend6 + 2*supp3. Between: linear interpolation.

// 7. The whole thing (implemented in src/engine/recommend.ts).
recommend(profile, catalog, currencies, programs, opts?: { perPlayer?: number /* default 5 */ }): Results
// Steps per player: drop hard exclusions, mark NLL blocks, sort by rankFor, take top N.
// Merge players' lists in rank order; label each card with players (and viaNllOnly per player).
// Ceiling backups: for each card in a player's top N with welcomeBonus.ceiling, add one more card for that player:
// the best-ranked eligible card below the cutoff that is not a ceiling offer and not already listed. Flag it backup: true for that player.
// bestPersonal: for players with wantsUnder524 and x24 >= 4, their top 3 eligible personal cards.
```

## Testing plan
- One test per hardExclusion kind and per nllBlock kind, using small fixture catalogs.
- Persona tests through recommend() (see the plan's persona list).
- Property tests: never list a card for a player who has a hard exclusion; NLL cards appear at the rank they would have without the block.

## Open items
- Data model for rank: currently five lists in card.schema.json (chasePersonal, chaseBusiness, nonChaseBusiness, travel, cashback). With "list in order of rank" and the under-5/24 and over-5/24 branches, a simpler model may be: `rank.under524`, `rank.over524Travel`, `rank.over524Cashback`. Needs the user's decision because they will supply this data.
- Bilt: resolved. Generic page-level blurb for all users; Bilt cards are never in any list. `showBiltBlurb` in results.schema.json should become a page-level flag (to change when the schemas are next revised).
- Proposed by the user (2026-09-20, not yet confirmed): rank by welcome bonus value = points x a per-currency cents-per-point value the user supplies, compared directly against cash back bonuses. This would replace the flowchart priority lists as the ranking basis. See the discussion in the conversation; schemas are unchanged until confirmed.
- Tie-break when merged travel and cashback ranks are equal (working assumption: travel first).
