import { describe, expect, it } from "vitest";
import { bonusValue, netValue } from "./netValue";
import type { Card, Valuations } from "./types";
import cardsJson from "../../data/cards.json";
import valuationsJson from "../../data/valuations.json";

const valuations = valuationsJson as unknown as Valuations;
const real = new Map((cardsJson as unknown as Card[]).map((c) => [c.id, c]));
const get = (id: string) => real.get(id)!;
const card = (extra: Partial<Card>): Card => ({
  id: "x", name: "x", issuer: "citi", kind: "personal", recommendable: true, annualFee: 0, reportsToPersonal: true, verifiedOn: "2026-01-01", ...extra,
});
const V: Valuations = {
  values: { flat: 2, twoRate: { withUnlocker: 1.5, withoutUnlocker: 1 } },
  freeNightCertificates: {},
};

describe("bonusValue", () => {
  it("is points times cents per point, over 100", () => {
    expect(bonusValue(card({ currency: "flat", welcomeBonus: { points: 50000 } }), V, false)).toBe(1000);
  });
  it("uses the with-unlocker rate only when unlocked", () => {
    const c = card({ currency: "twoRate", welcomeBonus: { points: 60000 } });
    expect(bonusValue(c, V, true)).toBe(900);
    expect(bonusValue(c, V, false)).toBe(600);
  });
  it("adds cash back and other value at face value", () => {
    expect(bonusValue(card({ currency: "cash", welcomeBonus: { cashBack: 200 } }), V, false)).toBe(200);
    expect(bonusValue(card({ currency: "flat", welcomeBonus: { points: 10000, cashBack: 50, otherValue: 100 } }), V, false)).toBe(350);
  });
  it("adds extra tiers", () => {
    const c = card({ currency: "flat", welcomeBonus: { points: 10000, additionalTiers: [{ points: 5000 }, { cashBack: 25 }] } });
    expect(bonusValue(c, V, false)).toBe(200 + 100 + 25);
  });
  it("refuses to value a card with no bonus or with points and no currency", () => {
    expect(() => bonusValue(card({}), V, false)).toThrow(/welcome bonus/);
    expect(() => bonusValue(card({ welcomeBonus: { points: 1000 } }), V, false)).toThrow(/currency/);
  });
  it("refuses a currency with no valuation instead of guessing", () => {
    expect(() => bonusValue(card({ currency: "mystery", welcomeBonus: { points: 1000 } }), V, false)).toThrow(/valuation/);
  });
});

describe("netValue", () => {
  it("subtracts nothing for a card whose first-year fee is waived", () => {
    expect(netValue(card({ currency: "cash", annualFee: 95, firstYearFeeWaived: true, welcomeBonus: { cashBack: 200 } }), V, false)).toBe(200);
  });
  it("subtracts the full annual fee when the first year is not waived", () => {
    expect(netValue(card({ currency: "cash", annualFee: 95, welcomeBonus: { cashBack: 200 } }), V, false)).toBe(105);
  });
});

describe("value of real cards", () => {
  it("values Ink Business Cash's 75,000 Ultimate Rewards at 1.5 cents unlocked and 1.0 otherwise", () => {
    expect(bonusValue(get("chase-ink-cash"), valuations, true)).toBeCloseTo(1125);
    expect(bonusValue(get("chase-ink-cash"), valuations, false)).toBeCloseTo(750);
  });
  it("values a free night certificate card with the stored certificate value", () => {
    const c = get("amex-hilton-surpass");
    const cpp = valuations.values["hilton-honors"] as number;
    expect(bonusValue(c, valuations, false)).toBeCloseTo((130000 * cpp) / 100 + valuations.freeNightCertificates["hilton"]!);
  });
  it("adds Aeroplan's second tier", () => {
    const c = get("chase-aeroplan");
    const first = c.welcomeBonus!.points!;
    const tier = c.welcomeBonus!.additionalTiers![0]!.points ?? 0;
    const cpp = valuations.values["aeroplan"] as number;
    expect(bonusValue(c, valuations, false)).toBeCloseTo(((first + tier) * cpp) / 100);
  });
  it("can value every ranked card in the catalog", () => {
    let n = 0;
    for (const c of real.values()) {
      if (c.recommendable && !c.unrankedReason) {
        expect(Number.isFinite(netValue(c, valuations, true)), c.id).toBe(true);
        n++;
      }
    }
    expect(n).toBe(121);
  });
});
