import type { Card, Currency, Household, Program } from "./types";

/**
 * Spend the household can put on one card within a window of 3 to 6 months (the windows in the catalog):
 * 3 months is spend3Months plus the supplemental spend; 6 months is spend6Months plus twice the supplemental spend;
 * windows between are interpolated linearly. Anything else is refused rather than guessed.
 *
 * spend6Months left blank (stored as 0, the field's default) is treated as "double the 3-month answer" (owner,
 * 2026-09-22), since a real 6-month total lower than the 3-month total is never a sensible answer (spend only
 * grows over time) — there is no legitimate case where a household's real answer is genuinely 0 here.
 */
export function spendCapacity(household: Household, months: number): number {
  if (!(months >= 3 && months <= 6)) throw new Error(`unsupported spend window: ${months} months (expected 3 to 6)`);
  const spend6Months = household.spend6Months || household.spend3Months * 2;
  const at3 = household.spend3Months + household.supplementalSpend3Months;
  const at6 = spend6Months + 2 * household.supplementalSpend3Months;
  return at3 + ((at6 - at3) * (months - 3)) / 3;
}

/**
 * True if the household's excluded programs rule the card out.
 * - A co-branded card is out if its program (or the program's group, such as Avios) is excluded.
 * - A cash card, or bank points cashed out, is out if cash back is excluded.
 * - A transferable-points card is out only if every redemption is excluded: all its partners and cash back.
 *   Cash back counts as a redemption unless the currency has none.
 * - Miles with no program in the data (Frontier, Lufthansa) are never excluded.
 * docs/questionnaire-design.md, "Exclusion logic".
 */
export function excludedByProgram(card: Card, household: Household, currencies: Currency[], programs: Program[]): boolean {
  const excluded = new Set(household.excludedPrograms);
  const groupOf = new Map(programs.map((p) => [p.id, p.group]));
  const programExcluded = (id: string): boolean => {
    const group = groupOf.get(id);
    return excluded.has(id) || (group !== undefined && excluded.has(group));
  };
  const cashBackExcluded = excluded.has("cashback");

  if (card.coBrandedProgram) return programExcluded(card.coBrandedProgram);
  if (card.currency === "cash" || card.currency === "default-bank-points") return cashBackExcluded;
  const currency = currencies.find((c) => c.id === card.currency);
  if (currency) {
    const partnerLeft = currency.partners.some((p) => !programExcluded(p));
    const cashLeft = currency.cashBackRedemption !== "none" && !cashBackExcluded;
    return !partnerLeft && !cashLeft;
  }
  return false;
}
