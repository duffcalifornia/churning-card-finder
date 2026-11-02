import { spendCapacity } from "./householdFilters";
import type { BonusTier, Card, Household, Valuations } from "./types";

function centsPerPoint(currency: string, valuations: Valuations, unlocked: boolean): number {
  const entry = valuations.values[currency];
  if (entry === undefined) throw new Error(`no valuation for currency ${currency}: it is never guessed`);
  return typeof entry === "number" ? entry : unlocked ? entry.withUnlocker : entry.withoutUnlocker;
}

/**
 * True if the household's spending reaches an extra tier. "total" tiers count spend since opening; "more" tiers come on
 * top of the first tier's minimum spend. Merchant tiers (spend at Wyndham) and tiers with no stated spend are always
 * counted, since the household's spending answers say nothing about them.
 */
function tierReachable(card: Card, tier: BonusTier, household: Household): boolean {
  if (!tier.minSpend || !tier.windowMonths || tier.spendBasis === "merchant") return true;
  const needed = tier.spendBasis === "total" ? tier.minSpend : tier.minSpend + (card.typicalMinSpend?.amount ?? 0);
  return needed <= spendCapacity(household, tier.windowMonths);
}

/**
 * Dollar value of a card's welcome bonus: points times cents per point, plus cash back, plus other value (free night
 * certificates), plus the extra tiers. Given a household, only the extra tiers its spending reaches count (the first
 * tier is always reached, or the card would be hidden); without one, every tier counts.
 * `unlocked` picks the rate for currencies with two rates. The TypeScript twin of scripts/cardfinder/value.py.
 */
export function bonusValue(card: Card, valuations: Valuations, unlocked: boolean, household?: Household): number {
  const bonus = card.welcomeBonus;
  if (!bonus) throw new Error(`${card.id} has no welcome bonus to value`);
  const pointsValue = (points: number | undefined): number => {
    if (!points) return 0;
    if (!card.currency) throw new Error(`${card.id} has points but no currency`);
    return (points * centsPerPoint(card.currency, valuations, unlocked)) / 100;
  };
  const tierValue = (t: BonusTier): number => pointsValue(t.points) + (t.cashBack ?? 0);
  return (
    pointsValue(bonus.points) + (bonus.cashBack ?? 0) + (bonus.otherValue ?? 0) +
    (bonus.additionalTiers ?? [])
      .filter((t) => !household || tierReachable(card, t, household))
      .reduce((sum, t) => sum + tierValue(t), 0)
  );
}

/** What the card costs in its first year: the annual fee, or $0 when the first-year fee is waived. */
export function firstYearFee(card: Card): number {
  return card.firstYearFeeWaived ? 0 : card.annualFee ?? 0;
}

/** Bonus value minus the first-year annual fee. */
export function netValue(card: Card, valuations: Valuations, unlocked: boolean, household?: Household): number {
  return bonusValue(card, valuations, unlocked, household) - firstYearFee(card);
}
