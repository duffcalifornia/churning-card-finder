import type { BonusTier, Card, Valuations } from "./types";

function centsPerPoint(currency: string, valuations: Valuations, unlocked: boolean): number {
  const entry = valuations.values[currency];
  if (entry === undefined) throw new Error(`no valuation for currency ${currency}: it is never guessed`);
  return typeof entry === "number" ? entry : unlocked ? entry.withUnlocker : entry.withoutUnlocker;
}

/**
 * Dollar value of a card's welcome bonus: points times cents per point, plus cash back, plus other value (free night
 * certificates), plus any extra tiers (the household already meets the first threshold, or the card would be hidden).
 * `unlocked` picks the rate for currencies with two rates. The TypeScript twin of scripts/cardfinder/value.py.
 */
export function bonusValue(card: Card, valuations: Valuations, unlocked: boolean): number {
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
    (bonus.additionalTiers ?? []).reduce((sum, t) => sum + tierValue(t), 0)
  );
}

/** What the card costs in its first year: the annual fee, or $0 when the first-year fee is waived. */
export function firstYearFee(card: Card): number {
  return card.firstYearFeeWaived ? 0 : card.annualFee ?? 0;
}

/** Bonus value minus the first-year annual fee. */
export function netValue(card: Card, valuations: Valuations, unlocked: boolean): number {
  return bonusValue(card, valuations, unlocked) - firstYearFee(card);
}
