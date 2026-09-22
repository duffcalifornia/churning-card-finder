import type { Card, Currency, Household, Program } from "./types";

interface TargetContext {
  household: Household;
  currencies: Currency[];
  programs: Program[];
  /** This player's unlock status per currency (from unlockStatus). */
  unlock: Map<string, boolean>;
}

/**
 * Does the card lead to a program the household wants to target?
 * - A co-branded card does if its program (or the program's group, such as Avios) is targeted.
 * - A transferable-points card does if its currency transfers to a targeted program and the currency is unlocked for the
 *   player (an unlocker card itself counts, since getting it unlocks the currency).
 * A program that is both targeted and excluded is not targeted.
 */
export function targetsProgram(_player: unknown, card: Card, ctx: TargetContext): boolean {
  const targets = new Set(ctx.household.targetPrograms ?? []);
  if (targets.size === 0) return false;
  const excluded = new Set(ctx.household.excludedPrograms);
  const named = (set: Set<string>, p: Program) => set.has(p.id) || (p.group !== undefined && set.has(p.group));
  const wanted = (id: string): boolean => {
    const p = ctx.programs.find((x) => x.id === id);
    return p !== undefined && named(targets, p) && !named(excluded, p);
  };

  if (card.coBrandedProgram) return wanted(card.coBrandedProgram);
  const currency = ctx.currencies.find((c) => c.id === card.currency);
  if (!currency) return false;
  const unlocked = ctx.unlock.get(currency.id) === true || currency.unlockerCards.includes(card.id);
  return unlocked && currency.partners.some(wanted);
}
