import type { Card, Currency, Program } from "../engine/types";

// Currencies that are not in the currency or program lists, with how to say them.
const OTHER_CURRENCIES: Record<string, string> = {
  "default-bank-points": "bank points",
  "frontier-bonus-miles": "Frontier miles",
  "miles-and-more": "Miles & More miles",
};

const n = (x: number): string => x.toLocaleString("en-US");

/** "Delta SkyMiles" already says miles, "Chase Ultimate Rewards" does not: add the unit only where it is missing. */
function withUnit(name: string, unit: string): string {
  return /miles|points/i.test(name) ? name : `${name} ${unit}`;
}

function currencyName(card: Card, currencies: Currency[], programs: Program[]): string {
  const id = card.currency ?? "";
  const program = programs.find((p) => p.id === id);
  if (program) return withUnit(program.name, program.kind === "airline" ? "miles" : "points");
  const currency = currencies.find((c) => c.id === id);
  if (currency?.name) return withUnit(currency.name, "points");
  return OTHER_CURRENCIES[id] ?? "points";
}

/**
 * The welcome bonus in words, one part per component (points or miles, cash, free nights, extra tiers). An "as high as"
 * offer says "Up to" on its first amount. The parts are meant to be joined with " + ".
 */
/**
 * The first tier plus any extra tiers phrased the way the offer itself reads: "Get A after spending B in C months,
 * then get an additional X after spending Y more in Z months". Falls back to the plain description when the card has
 * no spend requirement to hang that phrasing on (a gift-card style bonus).
 */
function tieredAmount(bonus: NonNullable<Card["welcomeBonus"]>, unit: string): string {
  const advertised = bonus.displayedAsCash ? ` (advertised as $${n(bonus.displayedAsCash)})` : "";
  return bonus.points ? `${n(bonus.points)} ${unit}` : bonus.cashBack ? `$${n(bonus.cashBack)} statement credit or cash back` : "";
}

export function describeBonus(card: Card, currencies: Currency[], programs: Program[]): string[] {
  const bonus = card.welcomeBonus;
  if (!bonus) return [];
  const spend = card.typicalMinSpend;
  const tier = bonus.additionalTiers?.[0];

  if (spend && tier && !bonus.ceiling) {
    const unit = currencyName(card, currencies, programs);
    const first = tieredAmount(bonus, unit);
    const extra = tier.points ? n(tier.points) : tier.cashBack ? `$${n(tier.cashBack)}` : "";
    const extraSpend = tier.minSpend !== undefined && tier.minSpend !== null ? `$${n(tier.minSpend)}` : "more";
    const extraWindow = tier.windowMonths ? ` in ${tier.windowMonths} months` : "";
    const parts = [`Get ${first} after spending $${n(spend.amount)} in ${spend.months} months, then get an additional ${extra} after spending ${extraSpend} more${extraWindow}`];
    if (bonus.freeNights) parts.push(`${bonus.freeNights} free night award${bonus.freeNights === 1 ? "" : "s"}`);
    return parts;
  }

  const parts: string[] = [];
  const upTo = (text: string): string => (bonus.ceiling && parts.length === 0 ? `Up to ${text}` : text);

  if (bonus.points) {
    const unit = currencyName(card, currencies, programs);
    const advertised = bonus.displayedAsCash ? ` (advertised as $${n(bonus.displayedAsCash)})` : "";
    parts.push(upTo(`${n(bonus.points)} ${unit}`) + advertised);
  }
  if (bonus.cashBack) parts.push(upTo(`$${n(bonus.cashBack)} statement credit or cash back`));
  if (bonus.freeNights) parts.push(`${bonus.freeNights} free night award${bonus.freeNights === 1 ? "" : "s"}`);
  for (const t of bonus.additionalTiers ?? []) {
    const extra = t.points ? n(t.points) : t.cashBack ? `$${n(t.cashBack)}` : "";
    if (extra) parts.push(`plus ${extra} more with additional spending`);
  }
  return parts;
}
