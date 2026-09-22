import type { Currency, Player } from "./types";

/**
 * Which points currencies each player can transfer (data/currencies.json, docs/transfer-matrix.md).
 *
 * - A currency with no unlocker cards needs none (Amex, Wells Fargo, Bilt): always unlocked.
 * - Otherwise a player needs an unlocker card currently open. Closed cards do not count.
 * - If the currency pools across the household, any player's unlocker counts for everyone.
 *
 * The catalog is not needed: the currency data names the unlocker card ids directly.
 * Pure: the input is never changed.
 */
export function unlockStatus(players: Player[], currencies: Currency[]): Map<string, Map<string, boolean>> {
  const names = new Set<string>();
  for (const p of players) {
    if (names.has(p.name)) throw new Error(`two players have the same name: ${p.name}`);
    names.add(p.name);
  }

  const holdsAny = (p: Player, cardIds: string[]): boolean =>
    cardIds.some((id) => (p.history.cards?.[id]?.current ?? 0) > 0);

  const result = new Map<string, Map<string, boolean>>();
  for (const p of players) {
    const row = new Map<string, boolean>();
    for (const c of currencies) {
      let unlocked: boolean;
      if (c.unlockerCards.length === 0) unlocked = true;
      else if (c.householdPooling) unlocked = players.some((q) => holdsAny(q, c.unlockerCards));
      else unlocked = holdsAny(p, c.unlockerCards);
      row.set(c.id, unlocked);
    }
    result.set(p.name, row);
  }
  return result;
}
