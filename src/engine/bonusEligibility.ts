import type { Card, CardHistoryEntry, Derived, MarriottMatrix, Player } from "./types";

// Issuers whose cards count toward Amex's card limits and follow its lifetime and family rules.
export const AMEX_ISSUED = new Set(["amex", "schwab", "morganstanley"]);
export const isAmexIssued = (card: Card): boolean => AMEX_ISSUED.has(card.issuer);

/**
 * Once in a lifetime, and approval-based: blocked if the player was ever approved for this card, or for a card that
 * blocks it for life (Strata Student blocks Strata, Citi Premier blocks Strata Premier). docs/rule-audit.md A10, K1, K2, K7.
 */
export function lifetimeBlocked(card: Card, derived: Derived): boolean {
  const rules = card.bonusRules;
  if (!rules?.onceInLifetime) return false;
  return derived.everHad.has(card.id) || (rules.lifetimeAlsoBlockedBy ?? []).some((id) => derived.everHad.has(id));
}

/**
 * Family rule: having ever had a card in a higher tier of the same family blocks the bonus on a lower tier. Same-tier
 * cards do not block each other. Amex Section J and the Capital One Venture family (K8).
 */
export function familyBlocked(card: Card, derived: Derived, catalog: Card[]): boolean {
  const family = card.family;
  if (!family) return false;
  return catalog.some((c) => c.family?.id === family.id && c.family.tier > family.tier && derived.everHad.has(c.id));
}

/**
 * Copies approved within the last `months` months, from the count buckets: 12 is the first bucket, 24 the first two,
 * 48 the first three. Coarse by design (a card in the 12 to 24 bucket may be nearly 24 months old). For Southwest
 * and Marriott cards the counts are bonus dates instead of approval dates (the history heading says so).
 */
export function approvedWithin(entry: CardHistoryEntry | undefined, months: 12 | 24 | 48): number {
  const a = entry?.approved ?? {};
  const [b1, b2, b3] = [a.lt12 ?? 0, a.m12to24 ?? 0, a.m24to48 ?? 0];
  return months === 12 ? b1 : months === 24 ? b1 + b2 : b1 + b2 + b3;
}

/**
 * Cooldown rules: no bonus while the card (or any card in its cooldown family) is open, and not within the cooldown
 * after approval or bonus (24 months Chase, Southwest, IHG and BoA; 48 months Citi and Capital One personal).
 * BoA's rule is held-based: an open card, or one approved within the window, blocks. Cards that follow the Marriott
 * matrix are handled there. docs/rule-audit.md G2, K3, K6, A15, G4, G8.
 */
export function cooldownBlocked(player: Player, card: Card, catalog: Card[]): boolean {
  const rules = card.bonusRules;
  if (!rules || rules.marriottMatrixKey) return false;
  const family = rules.cooldownFamily;
  const members = family ? catalog.filter((c) => c.bonusRules?.cooldownFamily === family) : [card];
  const months = rules.cooldownMonths;
  if (months !== undefined && months !== 24 && months !== 48) {
    throw new Error(`unsupported cooldown length for ${card.id}: ${months} months`);
  }
  return members.some((m) => {
    const entry = player.history.cards?.[m.id];
    const isHeld = (entry?.current ?? 0) > 0;
    if (rules.blockedWhileHeld && isHeld) return true;
    if (months === undefined) return false;
    if (rules.cooldownBasis === "held" && isHeld) return true;
    return approvedWithin(entry, months) > 0;
  });
}

/**
 * Marriott eligibility matrix (data/marriott-matrix.json, docs/rule-audit.md Section H): for each prior Marriott card the
 * player has, the rule that applies to the wanted card. A prior card blocks if any part of its rule is met:
 * ever had it; currently holds it; held it within 30 days (open now, or closed within 30 days); approved within 90 days;
 * or received a bonus on it within 24 months (the bucket counts are bonus dates for Marriott cards).
 *
 * skipEver leaves out the "ever had it" cells. Amex's are its lifetime language, which an NLL offer can lift, so they are
 * reported by nllBlock (marriottEverBlocked) and not here; every other part of the matrix stays binding.
 */
export function marriottBlocked(player: Player, derived: Derived, card: Card, matrix: MarriottMatrix, skipEver = false): boolean {
  const key = card.bonusRules?.marriottMatrixKey;
  if (!key) return false;
  for (const [priorId, row] of Object.entries(matrix.matrix)) {
    const code = row[key];
    if (code === undefined) continue;
    const rule = matrix.rules[code];
    if (!rule) throw new Error(`Marriott matrix uses an undefined rule code: ${code}`);
    const entry = player.history.cards?.[priorId];
    const isHeld = (entry?.current ?? 0) > 0;
    if (rule.ever && !skipEver && derived.everHad.has(priorId)) return true;
    if (rule.blockedIfHeld && isHeld) return true;
    if (rule.heldWithinDays && (isHeld || entry?.marriott?.closedWithin30Days)) return true;
    if (rule.approvedWithinDays && entry?.marriott?.approvedWithin90Days) return true;
    if (rule.bonusWithinMonths && approvedWithin(entry, 24) > 0) return true;
  }
  return false;
}

/** True if a matrix "ever had it" cell blocks the wanted card: a prior Marriott card the player was ever approved for. */
export function marriottEverBlocked(card: Card, derived: Derived, matrix: MarriottMatrix): boolean {
  const key = card.bonusRules?.marriottMatrixKey;
  if (!key) return false;
  return Object.entries(matrix.matrix).some(([priorId, row]) => {
    const code = row[key];
    return code !== undefined && matrix.rules[code]?.ever === true && derived.everHad.has(priorId);
  });
}
