import { familyBlocked, isAmexIssued, lifetimeBlocked, marriottEverBlocked } from "./bonusEligibility";
import type { Card, Derived, MarriottMatrix, Player } from "./types";

/**
 * Blocks that an NLL ("no lifetime language") offer would remove: Amex's lifetime and family rules. Every Amex card
 * carries lifetime language by default. For Amex Marriott cards the matrix's "ever had it" cells are that lifetime
 * language; the rest of the matrix still applies with an NLL offer (see marriottBlocked).
 * The card is not hidden; the results show it as "(via NLL only)". If both apply, lifetime is reported.
 * docs/rule-audit.md A10, H, J.
 */
export function nllBlock(
  _player: Player, derived: Derived, card: Card, catalog: Card[], matrix: MarriottMatrix,
): "lifetime" | "family" | null {
  if (!isAmexIssued(card)) return null;
  if (lifetimeBlocked(card, derived) || marriottEverBlocked(card, derived, matrix)) return "lifetime";
  if (familyBlocked(card, derived, catalog)) return "family";
  return null;
}
