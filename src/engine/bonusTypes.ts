import type { Card, Currency, Household, Player, Program } from "./types";

const ALL_TYPES = ["cashback", "hotel", "airline"];

export interface TypeContext {
  household: Household;
  currencies: Currency[];
  programs: Program[];
  /** This player's unlock status per currency (from unlockStatus). */
  unlock: Map<string, boolean>;
}

const holds = (player: Player, cardId: string): boolean => (player.history.cards?.[cardId]?.current ?? 0) > 0;

/**
 * Whether the currency cashes out well for this player and card: 'good' always, 'none' never, and 'poor' (Amex points)
 * only when a qualifier is met: every listed card held now in the player's own name, plus the named account if any.
 * The card being applied for counts as held, except that an account requirement must already be met.
 */
export function cashOutGood(player: Player, currency: Currency, card: Card): boolean {
  if (currency.cashBackRedemption === "good") return true;
  if (currency.cashBackRedemption === "none") return false;
  return (currency.cashBackQualifiers ?? []).some(
    (q) =>
      q.cards.every((id) => id === card.id || holds(player, id)) &&
      (q.account === undefined || (q.account === "amexBusinessChecking" && player.hasAmexBusinessChecking === true)),
  );
}

/** The bonus types the card offers this player, optionally pretending the currency is unlocked. */
function usableTypes(player: Player, card: Card, ctx: TypeContext, assumeUnlocked: boolean): Set<string> {
  const currency = ctx.currencies.find((c) => c.id === card.currency);
  // Cash cards, bank points and co-branded miles keep the types recorded on the card.
  if (!currency) return new Set(card.bonusTypes ?? []);

  const excluded = new Set(ctx.household.excludedPrograms);
  const programExcluded = (p: Program): boolean => excluded.has(p.id) || (p.group !== undefined && excluded.has(p.group));
  const types = new Set<string>();

  const unlocked = assumeUnlocked || ctx.unlock.get(currency.id) === true || currency.unlockerCards.includes(card.id);
  if (unlocked) {
    for (const p of ctx.programs) {
      if (currency.partners.includes(p.id) && !programExcluded(p)) types.add(p.kind);
    }
  }
  if (cashOutGood(player, currency, card) && !excluded.has("cashback")) types.add("cashback");
  return types;
}

/**
 * Does the card give the player a bonus type the household wants? An empty selection means all types.
 * Transferable points only count as airline or hotel once the currency is unlocked (the unlocker cards themselves are
 * treated as unlocked, since getting one unlocks it) and a partner of that kind is not excluded. They count as cash back
 * when the cash-out is good and cash back is not excluded.
 * 'noUnlocker' means the card would match if the currency were unlocked; 'noWantedBonusType' means it would not.
 */
export function bonusTypeMatch(player: Player, card: Card, ctx: TypeContext): "ok" | "noUnlocker" | "noWantedBonusType" {
  const wanted = new Set(ctx.household.bonusTypes.length ? ctx.household.bonusTypes : ALL_TYPES);
  const matches = (types: Set<string>) => [...types].some((t) => wanted.has(t));
  if (matches(usableTypes(player, card, ctx, false))) return "ok";
  return matches(usableTypes(player, card, ctx, true)) ? "noUnlocker" : "noWantedBonusType";
}
