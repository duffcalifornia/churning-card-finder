import { describe, expect, it } from "vitest";
import { hardExclusion } from "./hardExclusion";
import type { Card, Derived, Household, Player } from "./types";
import { computeDerived } from "./computeDerived";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";
import type { Currency, Program } from "./types";

const REAL_CURRENCIES = currenciesJson as unknown as Currency[];
const REAL_PROGRAMS = programsJson as unknown as Program[];
const ALL_UNLOCKED = new Map<string, boolean>(REAL_CURRENCIES.map((c) => [c.id, true]));

const card = (id: string, extra: Partial<Card> = {}): Card => ({
  id, name: id, issuer: "chase", kind: "personal", recommendable: true, annualFee: 95, reportsToPersonal: true, bonusTypes: ["cashback"], verifiedOn: "2026-01-01", ...extra,
});

const player = (extra: Partial<Player> = {}): Player => ({
  name: "P1", history: {}, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false, ...extra,
});

const household = (extra: Partial<Household> = {}): Household => ({
  maxAnnualFee: 500, spend3Months: 10000, spend6Months: 20000, supplementalSpend3Months: 0, bonusTypes: [], excludedPrograms: [],
  ...extra,
});

const derived = (d: Partial<Derived> = {}): Derived => ({
  x24: 0, x12: 0, currentByIssuer: {}, approved12ByIssuer: {}, overFiveTwentyFour: false, amexCredit: 0, amexCharge: 0,
  chaseBusinessOpen: 0, inkNoFee: 0, inkAnnualFee: 0, everHad: new Set(), unknownCardIds: [], ...d,
});
/** Standing at n cards in the last 24 months (n over 5/24 is true from 5). */
const at24 = (n: number): Partial<Derived> => ({ x24: n, overFiveTwentyFour: n >= 5 });

const ctx = (h: Partial<Household> = {}, d: Partial<Derived> = {}) => ({
  household: household(h), derived: derived(d), catalog: [] as Card[], currencies: REAL_CURRENCIES, programs: REAL_PROGRAMS, unlock: ALL_UNLOCKED, marriottMatrix: { rules: {}, matrix: {} },
});

describe("hardExclusion: simple filters", () => {
  it("lets an ordinary card through", () => {
    expect(hardExclusion(player(), card("a"), ctx())).toBeNull();
  });

  it("hides cards that are only in the catalog for the history list", () => {
    expect(hardExclusion(player(), card("a", { recommendable: false }), ctx())?.kind).toBe("notRecommendable");
  });

  describe("shutdown issuers", () => {
    it("hides every card from an issuer that has shut the player down", () => {
      const p = player({ shutdownIssuers: ["chase"] });
      expect(hardExclusion(p, card("a"), ctx())?.kind).toBe("shutdown");
      expect(hardExclusion(p, card("b", { issuer: "citi" }), ctx())).toBeNull();
    });

    it("applies an Amex shutdown to Amex-issued partner cards", () => {
      const p = player({ shutdownIssuers: ["amex"] });
      expect(hardExclusion(p, card("s", { issuer: "schwab" }), ctx())?.kind).toBe("shutdown");
      expect(hardExclusion(p, card("m", { issuer: "morganstanley" }), ctx())?.kind).toBe("shutdown");
    });

    it("does not treat an Amex-issued partner card as shutting down Amex", () => {
      const p = player({ shutdownIssuers: ["chase"] });
      expect(hardExclusion(p, card("s", { issuer: "schwab" }), ctx())).toBeNull();
    });
  });

  describe("AA ban", () => {
    const aa = card("aa", { requiresAAAccess: true });
    it("hides AAdvantage cards from a banned player", () => {
      expect(hardExclusion(player({ bannedFromAA: true }), aa, ctx())?.kind).toBe("aaBan");
    });
    it("leaves them for a player who is not banned", () => {
      expect(hardExclusion(player(), aa, ctx())).toBeNull();
    });
    it("leaves other cards for a banned player", () => {
      expect(hardExclusion(player({ bannedFromAA: true }), card("a"), ctx())).toBeNull();
    });
  });

  describe("business cards", () => {
    const biz = card("biz", { kind: "business", reportsToPersonal: false });
    it("hides business cards from a player who is not open to them", () => {
      expect(hardExclusion(player({ openToBusinessCards: false }), biz, ctx())?.kind).toBe("businessNotWanted");
    });
    it("keeps personal cards for that player", () => {
      expect(hardExclusion(player({ openToBusinessCards: false }), card("a"), ctx())).toBeNull();
    });
    it("keeps business cards for a player who is open to them", () => {
      expect(hardExclusion(player(), biz, ctx())).toBeNull();
    });
  });

  describe("annual fee", () => {
    it("hides a card whose fee is above the household maximum", () => {
      expect(hardExclusion(player(), card("a", { annualFee: 550 }), ctx({ maxAnnualFee: 500 }))?.kind).toBe("annualFee");
    });
    it("allows a fee equal to the maximum", () => {
      expect(hardExclusion(player(), card("a", { annualFee: 500 }), ctx({ maxAnnualFee: 500 }))).toBeNull();
    });
    it("has no limit when the maximum is left blank", () => {
      expect(hardExclusion(player(), card("a", { annualFee: 5000 }), ctx({ maxAnnualFee: null }))).toBeNull();
    });
    it("counts a card whose first-year fee is waived as $0", () => {
      const c = card("a", { annualFee: 150, firstYearFeeWaived: true });
      expect(hardExclusion(player(), c, ctx({ maxAnnualFee: 100 }))).toBeNull();
      expect(hardExclusion(player(), c, ctx({ maxAnnualFee: 0 }))).toBeNull();
    });
    it("counts the full fee when the first year is not waived", () => {
      expect(hardExclusion(player(), card("a", { annualFee: 150 }), ctx({ maxAnnualFee: 100 }))?.kind).toBe("annualFee");
    });
    it("allows any card when the maximum is zero only if the card is free", () => {
      expect(hardExclusion(player(), card("free", { annualFee: 0 }), ctx({ maxAnnualFee: 0 }))).toBeNull();
      expect(hardExclusion(player(), card("paid", { annualFee: 1 }), ctx({ maxAnnualFee: 0 }))?.kind).toBe("annualFee");
    });
  });

  it("reports the first reason when several apply", () => {
    const c = card("a", { annualFee: 900, requiresAAAccess: true });
    const p = player({ shutdownIssuers: ["chase"], bannedFromAA: true });
    expect(hardExclusion(p, c, ctx({ maxAnnualFee: 100 }))?.kind).toBe("shutdown");
    expect(hardExclusion(player({ bannedFromAA: true }), c, ctx({ maxAnnualFee: 100 }))?.kind).toBe("aaBan");
  });

  it("gives a plain-language reason", () => {
    expect(hardExclusion(player(), card("a", { annualFee: 550 }), ctx({ maxAnnualFee: 500 }))?.reason).toMatch(/annual fee/i);
  });

  it("does not change its inputs", () => {
    const p = player({ shutdownIssuers: ["chase"] });
    const c = card("a");
    const before = JSON.stringify([p, c]);
    hardExclusion(p, c, ctx());
    expect(JSON.stringify([p, c])).toBe(before);
  });
});

describe("hardExclusion: velocity rules", () => {
  const chasePersonal = card("chase-freedom", { issuer: "chase" });
  const ink = (id: string, fee: number) => card(id, { issuer: "chase", kind: "business", reportsToPersonal: false, annualFee: fee });

  describe("Chase 5/24", () => {
    it("hides Chase personal cards at 5/24 or over", () => {
      expect(hardExclusion(player(), chasePersonal, ctx({}, at24(5)))?.kind).toBe("chase5_24");
      expect(hardExclusion(player(), chasePersonal, ctx({}, at24(9)))?.kind).toBe("chase5_24");
    });
    it("allows them at 4/24", () => {
      expect(hardExclusion(player(), chasePersonal, ctx({}, at24(4)))).toBeNull();
    });
    it("does not apply to other issuers", () => {
      expect(hardExclusion(player(), card("citi-x", { issuer: "citi" }), ctx({}, at24(8)))).toBeNull();
    });
    it("also applies to Chase business cards other than Ink (owner, 2026-09-21)", () => {
      const united = card("chase-united-business", { issuer: "chase", kind: "business", reportsToPersonal: false });
      expect(hardExclusion(player(), united, ctx({}, at24(5)))?.kind).toBe("chase5_24");
      expect(hardExclusion(player(), united, ctx({}, at24(4)))).toBeNull();
      const reserve = card("chase-sapphire-reserve-business", { issuer: "chase", kind: "business", reportsToPersonal: false });
      expect(hardExclusion(player(), reserve, ctx({}, at24(6)))?.kind).toBe("chase5_24");
    });
    it("reports Ink cards as 3/24 rather than 5/24, since 3/24 is stricter", () => {
      const inkCard = card("chase-ink-cash", { issuer: "chase", kind: "business", reportsToPersonal: false, annualFee: 0 });
      expect(hardExclusion(player(), inkCard, ctx({}, at24(6)))?.kind).toBe("ink3_24");
    });
  });

  describe("Chase Ink 3/24", () => {
    it("hides Ink cards at 3/24 or over", () => {
      expect(hardExclusion(player(), ink("chase-ink-cash", 0), ctx({}, at24(3)))?.kind).toBe("ink3_24");
      expect(hardExclusion(player(), ink("chase-ink-preferred", 95), ctx({}, at24(6)))?.kind).toBe("ink3_24");
    });
    it("allows them at 2/24", () => {
      expect(hardExclusion(player(), ink("chase-ink-cash", 0), ctx({}, at24(2)))).toBeNull();
    });
  });

  describe("Barclays 6/24", () => {
    const barclays = card("barclays-x", { issuer: "barclays" });
    it("hides Barclays cards at 6/24 or over, business too", () => {
      expect(hardExclusion(player(), barclays, ctx({}, at24(6)))?.kind).toBe("barclays6_24");
      const biz = card("barclays-biz", { issuer: "barclays", kind: "business", reportsToPersonal: false });
      expect(hardExclusion(player(), biz, ctx({}, at24(7)))?.kind).toBe("barclays6_24");
    });
    it("allows them at 5/24", () => {
      expect(hardExclusion(player(), barclays, ctx({}, at24(5)))).toBeNull();
    });
  });

  describe("Amex card limits", () => {
    const credit = card("amex-c", { issuer: "amex" });
    const charge = card("amex-g", { issuer: "amex", chargeCard: true });
    it("hides credit cards at the 5 credit card limit", () => {
      expect(hardExclusion(player(), credit, ctx({}, { amexCredit: 5 }))?.kind).toBe("amexCardLimits");
      expect(hardExclusion(player(), credit, ctx({}, { amexCredit: 4 }))).toBeNull();
    });
    it("hides charge cards at the 10 charge card limit", () => {
      expect(hardExclusion(player(), charge, ctx({}, { amexCharge: 10 }))?.kind).toBe("amexCardLimits");
      expect(hardExclusion(player(), charge, ctx({}, { amexCharge: 9 }))).toBeNull();
    });
    it("keeps the two limits separate", () => {
      expect(hardExclusion(player(), charge, ctx({}, { amexCredit: 5 }))).toBeNull();
      expect(hardExclusion(player(), credit, ctx({}, { amexCharge: 10 }))).toBeNull();
    });
    it("applies to Amex-issued partner cards", () => {
      expect(hardExclusion(player(), card("s", { issuer: "schwab", chargeCard: true }), ctx({}, { amexCharge: 10 }))?.kind).toBe("amexCardLimits");
    });
  });

  describe("Bank of America credit-card count", () => {
    const boa = card("boa-x", { issuer: "boa" });
    it("with a deposit account, hides BoA cards after more than 6 cards in 12 months", () => {
      const p = player({ hasBoaDepositAccount: true });
      expect(hardExclusion(p, boa, ctx({}, { x12: 7 }))?.kind).toBe("boaCardCount");
      expect(hardExclusion(p, boa, ctx({}, { x12: 6 }))).toBeNull();
    });
    it("without one, hides them after more than 2 cards in 12 months", () => {
      expect(hardExclusion(player(), boa, ctx({}, { x12: 3 }))?.kind).toBe("boaCardCount");
      expect(hardExclusion(player(), boa, ctx({}, { x12: 2 }))).toBeNull();
    });
    it("applies to BoA business cards as well", () => {
      const biz = card("boa-biz", { issuer: "boa", kind: "business", reportsToPersonal: false });
      expect(hardExclusion(player(), biz, ctx({}, { x12: 3 }))?.kind).toBe("boaCardCount");
    });
    it("does not apply to other issuers", () => {
      expect(hardExclusion(player(), card("c", { issuer: "citi" }), ctx({}, { x12: 9 }))).toBeNull();
    });
  });

  describe("US Bank 5/12", () => {
    const usbank = card("usbank-x", { issuer: "usbank" });
    it("hides US Bank cards after 5 or more cards in 12 months", () => {
      expect(hardExclusion(player(), usbank, ctx({}, { x12: 5 }))?.kind).toBe("usbank5_12");
      expect(hardExclusion(player(), usbank, ctx({}, { x12: 4 }))).toBeNull();
    });
    it("applies to business cards too, and only to US Bank", () => {
      const biz = card("usbank-biz", { issuer: "usbank", kind: "business", reportsToPersonal: false });
      expect(hardExclusion(player(), biz, ctx({}, { x12: 6 }))?.kind).toBe("usbank5_12");
      expect(hardExclusion(player(), card("c", { issuer: "citi" }), ctx({}, { x12: 6 }))).toBeNull();
    });
  });

  describe("Discover", () => {
    const discover = card("discover-it", { issuer: "discover" });
    it("hides Discover cards if one was approved in the last 12 months", () => {
      expect(hardExclusion(player(), discover, ctx({}, { approved12ByIssuer: { discover: 1 } }))?.kind).toBe("discoverLimits");
    });
    it("hides them if the player already holds two", () => {
      expect(hardExclusion(player(), discover, ctx({}, { currentByIssuer: { discover: 2 } }))?.kind).toBe("discoverLimits");
    });
    it("allows a second card once the first is more than a year old", () => {
      expect(hardExclusion(player(), discover, ctx({}, { currentByIssuer: { discover: 1 } }))).toBeNull();
    });
  });

  describe("Chase Ink limit", () => {
    it("allows one no-fee Ink and one annual-fee Ink open", () => {
      expect(hardExclusion(player(), ink("chase-ink-cash", 0), ctx({}, { inkNoFee: 1 }))?.kind).toBe("inkLimit");
      expect(hardExclusion(player(), ink("chase-ink-unlimited", 0), ctx({}, { inkNoFee: 1 }))?.kind).toBe("inkLimit");
      expect(hardExclusion(player(), ink("chase-ink-preferred", 95), ctx({}, { inkAnnualFee: 1 }))?.kind).toBe("inkLimit");
    });
    it("does not let a no-fee Ink block an annual-fee Ink or the other way round", () => {
      expect(hardExclusion(player(), ink("chase-ink-preferred", 95), ctx({}, { inkNoFee: 1 }))).toBeNull();
      expect(hardExclusion(player(), ink("chase-ink-cash", 0), ctx({}, { inkAnnualFee: 1 }))).toBeNull();
    });
  });

  describe("staying under 5/24", () => {
    const reporting = card("capone-x", { issuer: "capone", kind: "business", reportsToPersonal: true });
    const nonReporting = card("amex-business", { issuer: "amex", kind: "business", reportsToPersonal: false });
    it("hides cards that report to personal credit from 4/24 up for a player who wants to stay under", () => {
      const p = player({ wantsUnder524: true });
      expect(hardExclusion(p, card("citi-x", { issuer: "citi" }), ctx({}, at24(4)))?.kind).toBe("stayUnder524");
      expect(hardExclusion(p, reporting, ctx({}, at24(4)))?.kind).toBe("stayUnder524");
    });
    it("keeps business cards that do not report", () => {
      expect(hardExclusion(player({ wantsUnder524: true }), nonReporting, ctx({}, at24(4)))).toBeNull();
    });
    it("does nothing below 4/24 or for a player who does not care", () => {
      expect(hardExclusion(player({ wantsUnder524: true }), card("citi-x", { issuer: "citi" }), ctx({}, at24(3)))).toBeNull();
      expect(hardExclusion(player(), card("citi-x", { issuer: "citi" }), ctx({}, at24(6)))).toBeNull();
    });
  });

  it("checks the simple filters before the velocity rules", () => {
    const c = card("chase-freedom", { issuer: "chase", annualFee: 900 });
    expect(hardExclusion(player(), c, ctx({ maxAnnualFee: 100 }, at24(6)))?.kind).toBe("annualFee");
  });
});

describe("hardExclusion: velocity rules on the real catalog", () => {
  const catalog = cardsJson as unknown as Card[];
  const real = new Map(catalog.map((c) => [c.id, c]));
  const standing = (cards: NonNullable<Player["history"]["cards"]>, extra: Partial<Player> = {}) => {
    const p = player({ history: { cards }, ...extra });
    return { p, c: { household: household(), derived: computeDerived(p, catalog), catalog, currencies: REAL_CURRENCIES, programs: REAL_PROGRAMS, unlock: ALL_UNLOCKED, marriottMatrix: { rules: {}, matrix: {} } } };
  };

  it("hides a Chase Ink card at 3/24 but still allows Sapphire Preferred, using real card data", () => {
    const { p, c } = standing({
      "citi-double-cash": { approved: { lt12: 1 } }, "capone-quicksilver": { approved: { lt12: 1 } }, "discover-it-cash-back": { approved: { m12to24: 1 } },
    });
    expect(hardExclusion(p, real.get("chase-ink-cash")!, c)?.kind).toBe("ink3_24");
    expect(hardExclusion(p, real.get("chase-sapphire-preferred")!, c)).toBeNull();
  });

  it("applies the Amex credit card limit to Delta and Hilton cards", () => {
    const { p, c } = standing({
      "amex-delta-blue": { current: 1, approved: { gt48: 1 } }, "amex-delta-gold": { current: 1, approved: { gt48: 1 } },
      "amex-hilton-honors": { current: 1, approved: { gt48: 1 } }, "amex-hilton-surpass": { current: 1, approved: { gt48: 1 } },
      "amex-blue-cash-everyday": { current: 1, approved: { gt48: 1 } },
    });
    expect(hardExclusion(p, real.get("amex-delta-platinum")!, c)?.kind).toBe("amexCardLimits");
    expect(hardExclusion(p, real.get("amex-platinum")!, { ...c, household: household({ maxAnnualFee: 1000 }) })).toBeNull(); // a charge card: separate limit
  });
});

describe("hardExclusion: real catalog", () => {
  const real = new Map((cardsJson as unknown as Card[]).map((c) => [c.id, c]));
  const get = (id: string) => real.get(id)!;

  it("hides history-only cards", () => {
    expect(hardExclusion(player(), get("chase-ritz-carlton"), ctx())?.kind).toBe("notRecommendable");
    expect(hardExclusion(player(), get("citi-premier"), ctx())?.kind).toBe("notRecommendable");
  });

  it("applies the AA ban to Citi AAdvantage cards", () => {
    expect(hardExclusion(player({ bannedFromAA: true }), get("citi-aadvantage-executive"), ctx())?.kind).toBe("aaBan");
  });

  it("applies the annual fee limit to the Amex Platinum", () => {
    expect(hardExclusion(player(), get("amex-platinum"), ctx({ maxAnnualFee: 500 }))?.kind).toBe("annualFee");
    expect(hardExclusion(player(), get("amex-platinum"), ctx({ maxAnnualFee: 900 }))).toBeNull();
  });
});
