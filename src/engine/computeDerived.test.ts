import { describe, expect, it } from "vitest";
import { computeDerived } from "./computeDerived";
import type { Card, Player, PlayerHistory } from "./types";
import catalogJson from "../../data/cards.json";

const card = (id: string, issuer: string, kind: "personal" | "business", extra: Partial<Card> = {}): Card => ({
  id, name: id, issuer, kind, recommendable: true, reportsToPersonal: kind === "personal", verifiedOn: "2026-01-01", ...extra,
});

const CATALOG: Card[] = [
  card("chase-freedom", "chase", "personal"),
  card("chase-sapphire", "chase", "personal", { annualFee: 95 }),
  card("chase-ink-cash", "chase", "business", { annualFee: 0 }),
  card("chase-ink-unlimited", "chase", "business", { annualFee: 0 }),
  card("chase-ink-preferred", "chase", "business", { annualFee: 95 }),
  card("chase-united-business", "chase", "business", { annualFee: 99 }),
  card("amex-gold", "amex", "personal", { chargeCard: true }),
  card("amex-hilton", "amex", "personal"),
  card("amex-business-gold", "amex", "business", { chargeCard: true }),
  card("amex-blue-business-plus", "amex", "business"),
  card("schwab-platinum", "schwab", "personal", { chargeCard: true }),
  card("capone-spark-cash", "capone", "business", { reportsToPersonal: true }),
  card("capone-spark-cash-plus", "capone", "business", { reportsToPersonal: false }),
  card("citi-double-cash", "citi", "personal"),
];

const player = (history: PlayerHistory): Player => ({
  name: "Player 1", history, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false,
});

describe("computeDerived: X/24", () => {
  it("is zero for an empty history", () => {
    const d = computeDerived(player({}), CATALOG);
    expect(d).toMatchObject({ x24: 0, overFiveTwentyFour: false, amexCredit: 0, amexCharge: 0, chaseBusinessOpen: 0 });
    expect(d.everHad.size).toBe(0);
  });

  it("counts approvals in the first two buckets only", () => {
    const d = computeDerived(player({ cards: {
      "chase-freedom": { approved: { lt12: 1, m12to24: 1, m24to48: 3, gt48: 4 } },
    } }), CATALOG);
    expect(d.x24).toBe(2);
  });

  it("counts every copy of a card", () => {
    const d = computeDerived(player({ cards: { "citi-double-cash": { approved: { lt12: 2 } } } }), CATALOG);
    expect(d.x24).toBe(2);
  });

  it("counts a business card only if it reports to personal credit", () => {
    const d = computeDerived(player({ cards: {
      "capone-spark-cash": { approved: { lt12: 1 } },
      "capone-spark-cash-plus": { approved: { lt12: 1 } },
      "chase-ink-cash": { approved: { lt12: 1 } },
      "amex-business-gold": { approved: { lt12: 1 } },
    } }), CATALOG);
    expect(d.x24).toBe(1);
  });

  it("adds other personal cards per issuer and for other issuers", () => {
    const d = computeDerived(player({
      cards: { "chase-freedom": { approved: { lt12: 1 } } },
      otherPersonalByIssuer: { chase: { lt12: 1, m12to24: 1 }, citi: { lt12: 0, m12to24: 2 } },
      otherIssuersPersonal: { lt12: 1, m12to24: 0 },
    }), CATALOG);
    expect(d.x24).toBe(1 + 2 + 2 + 1);
  });

  it("ignores authorized-user accounts, even in an older saved profile that still has the field", () => {
    const history = { cards: { "chase-freedom": { approved: { lt12: 1 } } }, authorizedUserAccounts24Months: 4 } as unknown as PlayerHistory;
    const d = computeDerived(player(history), CATALOG);
    expect(d.x24).toBe(1);
    expect(d.x12).toBe(1);
  });

  it("is over 5/24 at five, not at four", () => {
    const at = (n: number) => computeDerived(player({ cards: { "chase-freedom": { approved: { lt12: n } } } }), CATALOG);
    expect(at(4)).toMatchObject({ x24: 4, overFiveTwentyFour: false });
    expect(at(5)).toMatchObject({ x24: 5, overFiveTwentyFour: true });
  });

  it("treats missing counts as zero", () => {
    const d = computeDerived(player({ cards: { "chase-freedom": {}, "chase-sapphire": { approved: { lt12: 1 } } } }), CATALOG);
    expect(d.x24).toBe(1);
  });
});

describe("computeDerived: Amex limits", () => {
  it("splits open Amex cards into credit and charge, personal and business together", () => {
    const d = computeDerived(player({ cards: {
      "amex-gold": { current: 1, approved: { gt48: 1 } },
      "amex-hilton": { current: 2, approved: { lt12: 2 } },
      "amex-business-gold": { current: 1, approved: { lt12: 1 } },
      "amex-blue-business-plus": { current: 1, approved: { m12to24: 1 } },
    } }), CATALOG);
    expect(d.amexCredit).toBe(3);
    expect(d.amexCharge).toBe(2);
  });

  it("counts Amex-issued partner cards (Schwab Platinum)", () => {
    const d = computeDerived(player({ cards: { "schwab-platinum": { current: 1, approved: { lt12: 1 } } } }), CATALOG);
    expect(d.amexCharge).toBe(1);
  });

  it("counts only cards currently open, not closed ones", () => {
    const d = computeDerived(player({ cards: { "amex-hilton": { current: 0, approved: { lt12: 1 } } } }), CATALOG);
    expect(d.amexCredit).toBe(0);
  });
});

describe("computeDerived: Chase business and Ink", () => {
  it("counts open Chase business cards", () => {
    const d = computeDerived(player({ cards: {
      "chase-ink-cash": { current: 1, approved: { lt12: 1 } },
      "chase-united-business": { current: 1, approved: { m12to24: 1 } },
      "chase-freedom": { current: 1, approved: { lt12: 1 } },
      "amex-business-gold": { current: 1, approved: { lt12: 1 } },
    } }), CATALOG);
    expect(d.chaseBusinessOpen).toBe(2);
  });

  it("splits open Ink cards by annual fee", () => {
    const d = computeDerived(player({ cards: {
      "chase-ink-cash": { current: 1, approved: { lt12: 1 } },
      "chase-ink-unlimited": { current: 1, approved: { lt12: 1 } },
      "chase-ink-preferred": { current: 1, approved: { lt12: 1 } },
      "chase-united-business": { current: 1, approved: { lt12: 1 } },
    } }), CATALOG);
    expect(d.inkNoFee).toBe(2);
    expect(d.inkAnnualFee).toBe(1);
  });
});

describe("computeDerived: ever had", () => {
  it("includes cards held now or approved in any window, however old", () => {
    const d = computeDerived(player({ cards: {
      "chase-sapphire": { approved: { gt48: 1 } },
      "amex-gold": { current: 1, approved: { lt12: 1 } },
      "citi-double-cash": { approved: { m24to48: 1 } },
      "amex-hilton": { current: 0, approved: { lt12: 0, m12to24: 0, m24to48: 0, gt48: 0 } },
      "chase-freedom": {},
    } }), CATALOG);
    expect([...d.everHad].sort()).toEqual(["amex-gold", "chase-sapphire", "citi-double-cash"]);
  });
});

describe("computeDerived: robustness", () => {
  it("ignores and reports history for cards no longer in the catalog", () => {
    const d = computeDerived(player({ cards: {
      "gone-card": { current: 1, approved: { lt12: 3 } },
      "chase-freedom": { approved: { lt12: 1 } },
    } }), CATALOG);
    expect(d.x24).toBe(1);
    expect(d.unknownCardIds).toEqual(["gone-card"]);
    expect(d.everHad.has("gone-card")).toBe(false);
  });

  it("does not change its input", () => {
    const p = player({ cards: { "chase-freedom": { current: 1, approved: { lt12: 1 } } } });
    const before = JSON.stringify(p);
    computeDerived(p, CATALOG);
    expect(JSON.stringify(p)).toBe(before);
  });
});

describe("computeDerived: last 12 months and per issuer", () => {
  it("counts cards opened in the last 12 months that report to personal credit", () => {
    const d = computeDerived(player({
      cards: {
        "chase-freedom": { approved: { lt12: 2, m12to24: 3 } },
        "capone-spark-cash": { approved: { lt12: 1 } },
        "capone-spark-cash-plus": { approved: { lt12: 1 } },
        "chase-ink-cash": { approved: { lt12: 1 } },
      },
      otherPersonalByIssuer: { citi: { lt12: 1, m12to24: 4 } },
      otherIssuersPersonal: { lt12: 2, m12to24: 1 },
    }), CATALOG);
    expect(d.x12).toBe(2 + 1 + 1 + 2);
  });

  it("counts current cards per issuer, business included", () => {
    const d = computeDerived(player({ cards: {
      "chase-freedom": { current: 2, approved: { lt12: 2 } },
      "chase-ink-cash": { current: 1, approved: { lt12: 1 } },
      "citi-double-cash": { current: 1, approved: { gt48: 1 } },
    } }), CATALOG);
    expect(d.currentByIssuer).toEqual({ chase: 3, citi: 1 });
  });

  it("counts cards approved in the last 12 months per issuer, including other personal cards", () => {
    const d = computeDerived(player({
      cards: { "chase-freedom": { approved: { lt12: 1, m12to24: 5 } }, "chase-ink-cash": { approved: { lt12: 1 } } },
      otherPersonalByIssuer: { chase: { lt12: 2 }, citi: { m12to24: 1 } },
    }), CATALOG);
    expect(d.approved12ByIssuer).toEqual({ chase: 4 });
  });
});

describe("computeDerived: real catalog", () => {
  const real = catalogJson as unknown as Card[];

  it("agrees with the rules on real card ids", () => {
    const d = computeDerived(player({ cards: {
      "chase-freedom-unlimited": { approved: { lt12: 1 } },
      "capone-spark-cash": { approved: { lt12: 1 } },
      "capone-venture-x-business": { approved: { lt12: 1 } },
      "chase-ink-cash": { current: 1, approved: { lt12: 1 } },
      "amex-platinum": { current: 1, approved: { m12to24: 1 } },
      "amex-delta-gold": { current: 1, approved: { m12to24: 1 } },
    } }), real);
    expect(d.x24).toBe(4); // Freedom Unlimited, Spark Cash, Amex Platinum and Delta Gold; not Venture X Business or Ink
    expect(d.amexCharge).toBe(1);
    expect(d.amexCredit).toBe(1);
    expect(d.chaseBusinessOpen).toBe(1);
    expect(d.inkNoFee).toBe(1);
    expect(d.unknownCardIds).toEqual([]);
  });

  it("every Ink card in the catalog has a fee, so the Ink split is decidable", () => {
    for (const c of real.filter((c) => c.id.startsWith("chase-ink-"))) {
      expect(c.annualFee, c.id).toBeTypeOf("number");
    }
  });
});
