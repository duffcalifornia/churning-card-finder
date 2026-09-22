import type { Card, Derived, OtherPersonalCards, Player } from "./types";

// Issuers whose cards are Amex-issued and so count toward Amex's 5 credit card and 10 charge card limits.
const AMEX_ISSUED = new Set(["amex", "schwab", "morganstanley"]);

const n = (x: number | undefined): number => x ?? 0;
const recentOther = (o: OtherPersonalCards | undefined): number => n(o?.lt12) + n(o?.m12to24);

/**
 * Derived standing for one player, computed from what they entered in the card history.
 * Pure: no I/O, and the input is never changed. See docs/engine-contract.md and docs/rule-audit.md (A1, A2, G6, K7).
 */
export function computeDerived(player: Player, catalog: Card[]): Derived {
  const byId = new Map(catalog.map((c) => [c.id, c]));
  const history = player.history;

  let x24 = 0;
  let x12 = 0;
  const currentByIssuer: Record<string, number> = {};
  const approved12ByIssuer: Record<string, number> = {};
  const bump = (m: Record<string, number>, k: string, by: number) => {
    if (by > 0) m[k] = (m[k] ?? 0) + by;
  };
  let amexCredit = 0;
  let amexCharge = 0;
  let chaseBusinessOpen = 0;
  let inkNoFee = 0;
  let inkAnnualFee = 0;
  const everHad = new Set<string>();
  const unknownCardIds: string[] = [];

  for (const [id, entry] of Object.entries(history.cards ?? {})) {
    const card = byId.get(id);
    if (!card) {
      unknownCardIds.push(id);
      continue;
    }
    const a = entry.approved ?? {};
    const current = n(entry.current);

    if (card.reportsToPersonal) {
      x24 += n(a.lt12) + n(a.m12to24);
      x12 += n(a.lt12);
    }
    bump(currentByIssuer, card.issuer, current);
    bump(approved12ByIssuer, card.issuer, n(a.lt12));

    if (AMEX_ISSUED.has(card.issuer)) {
      if (card.chargeCard) amexCharge += current;
      else amexCredit += current;
    }
    if (card.issuer === "chase" && card.kind === "business") chaseBusinessOpen += current;
    if (id.startsWith("chase-ink-")) {
      if (n(card.annualFee) === 0) inkNoFee += current;
      else inkAnnualFee += current;
    }
    if (current > 0 || n(a.lt12) + n(a.m12to24) + n(a.m24to48) + n(a.gt48) > 0) everHad.add(id);
  }

  for (const [issuer, other] of Object.entries(history.otherPersonalByIssuer ?? {})) {
    x24 += recentOther(other);
    x12 += n(other.lt12);
    bump(approved12ByIssuer, issuer, n(other.lt12));
  }
  x24 += recentOther(history.otherIssuersPersonal);
  x12 += n(history.otherIssuersPersonal?.lt12);

  return {
    x24,
    x12,
    currentByIssuer,
    approved12ByIssuer,
    overFiveTwentyFour: x24 >= 5,
    amexCredit,
    amexCharge,
    chaseBusinessOpen,
    inkNoFee,
    inkAnnualFee,
    everHad,
    unknownCardIds,
  };
}
