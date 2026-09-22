import { AMEX_ISSUED, cooldownBlocked, familyBlocked, isAmexIssued, lifetimeBlocked, marriottBlocked } from "./bonusEligibility";
import { bonusTypeMatch } from "./bonusTypes";
import { excludedByProgram, spendCapacity } from "./householdFilters";
import { firstYearFee } from "./netValue";
import type { Card, Currency, Derived, Exclusion, Household, MarriottMatrix, Player, Program } from "./types";

/** Shared inputs for the exclusion rules. More fields are added as later rule groups need them. */
export interface ExclusionContext {
  household: Household;
  derived: Derived;
  catalog: Card[];
  currencies: Currency[];
  programs: Program[];
  /** This player's unlock status per currency (from unlockStatus). */
  unlock: Map<string, boolean>;
  marriottMatrix: MarriottMatrix;
}

// Cards issued by Amex under another name: an Amex shutdown applies to them (Section J lists them with the Amex families).
const n = (x: number | undefined): number => x ?? 0;

const SHUTDOWN_ISSUER: Record<string, string> = { schwab: "amex", morganstanley: "amex" };

/**
 * The reason a card is hidden for a player, or null if nothing hides it.
 *
 * Rules are checked in a fixed order and the first that applies is returned:
 * catalog status, shutdown issuers, AA ban, business cards not wanted, the household's annual fee limit (the first-year
 * fee: a waived first year counts as $0), minimum spend against the household's capacity, excluded programs, the wanted
 * bonus types (with the unlock rules, bonusTypes.ts), then the issuers' velocity rules that the count buckets can decide:
 * Chase Ink 3/24 and 5/24 for every other Chase card (business included), Barclays 6/24, Amex 5 credit and 10 charge cards, US Bank 5/12, BoA's credit-card
 * count (docs/rule-audit.md K5), Discover and the Ink one-of-each limit; then bonus eligibility (lifetime and family
 * rules for non-Amex cards, cooldowns, the Marriott matrix; see bonusEligibility.ts); and finally the player's wish to
 * stay under 5/24.
 * Rules that need windows shorter than the buckets (Amex 2/90, Chase 2/30, Citi 8/65) are banners, not exclusions.
 *
 * Pure: the inputs are never changed.
 */
export function hardExclusion(player: Player, card: Card, ctx: ExclusionContext): Exclusion | null {
  if (!card.recommendable) {
    return { kind: "notRecommendable", reason: "The card is in the catalog only for the history list." };
  }

  if (card.unrankedReason) {
    return { kind: "unranked", reason: `The card has no value to rank it by: ${card.unrankedReason}` };
  }

  const issuer = SHUTDOWN_ISSUER[card.issuer] ?? card.issuer;
  if (player.shutdownIssuers.includes(issuer)) {
    return { kind: "shutdown", reason: `The player has been shut down by ${issuer}.` };
  }

  if (player.bannedFromAA && card.requiresAAAccess) {
    return { kind: "aaBan", reason: "The player is banned from earning AAdvantage miles." };
  }

  if (!player.openToBusinessCards && card.kind === "business") {
    return { kind: "businessNotWanted", reason: "The player does not want business cards." };
  }

  // The limit is on what the player would pay in the card's first year, so a waived first-year fee counts as $0.
  // Ranking uses the same first-year fee (see netValue).
  if (ctx.household.maxAnnualFee !== null && firstYearFee(card) > ctx.household.maxAnnualFee) {
    return {
      kind: "annualFee",
      reason: `The annual fee ($${card.annualFee}) is above the household maximum ($${ctx.household.maxAnnualFee}).`,
    };
  }
  if (card.typicalMinSpend && card.typicalMinSpend.amount > spendCapacity(ctx.household, card.typicalMinSpend.months)) {
    return { kind: "spend", reason: `The minimum spend ($${card.typicalMinSpend.amount}) is more than the household can spend in ${card.typicalMinSpend.months} months.` };
  }
  if (excludedByProgram(card, ctx.household, ctx.currencies, ctx.programs)) {
    return { kind: "excludedProgram", reason: "Every way of using this card's points is on the excluded list." };
  }

  const match = bonusTypeMatch(player, card, ctx);
  if (match === "noUnlocker") {
    return { kind: "noUnlocker", reason: "The card's points only reach the wanted travel programs through an unlocking card the player does not have." };
  }
  if (match === "noWantedBonusType") {
    return { kind: "noWantedBonusType", reason: "The card offers none of the bonus types the household wants." };
  }

  const d = ctx.derived;
  const isInk = card.id.startsWith("chase-ink-");

  // Ink is checked first: its 3/24 limit is stricter than the 5/24 that every other Chase card, business included, has.
  if (isInk && d.x24 >= 3) {
    return { kind: "ink3_24", reason: "Chase Ink cards are usually declined at 3/24 or over." };
  }
  if (card.issuer === "chase" && d.overFiveTwentyFour) {
    return { kind: "chase5_24", reason: "Chase declines its cards, business ones too, at 5/24 or over." };
  }
  if (card.issuer === "barclays" && d.x24 >= 6) {
    return { kind: "barclays6_24", reason: "Barclays generally declines at 6/24 or over." };
  }
  if (card.issuer === "usbank" && d.x12 >= 5) {
    return { kind: "usbank5_12", reason: "US Bank may decline after 5 or more cards opened in 12 months." };
  }
  if (AMEX_ISSUED.has(card.issuer)) {
    if (card.chargeCard && d.amexCharge >= 10) {
      return { kind: "amexCardLimits", reason: "The player already holds 10 Amex charge cards." };
    }
    if (!card.chargeCard && d.amexCredit >= 5) {
      return { kind: "amexCardLimits", reason: "The player already holds 5 Amex credit cards." };
    }
  }
  if (card.issuer === "boa") {
    const limit = player.hasBoaDepositAccount ? 6 : 2;
    if (d.x12 > limit) {
      return { kind: "boaCardCount", reason: `BoA declines after more than ${limit} cards opened in 12 months${player.hasBoaDepositAccount ? "" : " without a BoA deposit account"}.` };
    }
  }
  if (card.issuer === "discover") {
    if ((d.approved12ByIssuer["discover"] ?? 0) >= 1 || (d.currentByIssuer["discover"] ?? 0) >= 2) {
      return { kind: "discoverLimits", reason: "Discover: wait 12 months after a first card, and hold at most 2 cards." };
    }
  }
  if (isInk) {
    const free = n(card.annualFee) === 0;
    if ((free && d.inkNoFee >= 1) || (!free && d.inkAnnualFee >= 1)) {
      return { kind: "inkLimit", reason: `The player already holds an Ink card ${free ? "without" : "with"} an annual fee.` };
    }
  }

  // Bonus eligibility. Amex's lifetime and family blocks are not exclusions: nllBlock reports them so the card can be
  // shown "(via NLL only)". Everyone else's are hard, since Chase and Citi have no NLL offers today.
  // Exception: an Ink card's lifetime block is lifted for a player willing to form a qualifying-state LLC (K7); the
  // engine trusts that answer rather than asking which state, since the two only matter together.
  const inkLlcWorkaround = isInk && player.willingToFormLlcForInk === true;
  if (!isAmexIssued(card)) {
    if (!inkLlcWorkaround && lifetimeBlocked(card, d)) {
      return { kind: "lifetime", reason: "The player was already approved for this card, and its bonus is once per lifetime." };
    }
    if (familyBlocked(card, d, ctx.catalog)) {
      return { kind: "family", reason: "The player has had a higher card in this card's family." };
    }
  }

  if (cooldownBlocked(player, card, ctx.catalog)) {
    return { kind: "cooldown", reason: "The player holds this card (or one in its family), or received its bonus too recently." };
  }

  if (marriottBlocked(player, d, card, ctx.marriottMatrix, isAmexIssued(card))) {
    return { kind: "marriottMatrix", reason: "A Marriott card the player has or had blocks this card's bonus." };
  }

  if (player.wantsUnder524 && d.x24 >= 4 && card.reportsToPersonal) {
    return { kind: "stayUnder524", reason: "The player wants to get or stay under 5/24 and this card would count." };
  }

  return null;
}
