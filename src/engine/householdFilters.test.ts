import { describe, expect, it } from "vitest";
import { excludedByProgram, spendCapacity } from "./householdFilters";
import { hardExclusion } from "./hardExclusion";
import { computeDerived } from "./computeDerived";
import type { Card, Currency, Household, MarriottMatrix, Player, Program } from "./types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";
import matrixJson from "../../data/marriott-matrix.json";

const catalog = cardsJson as unknown as Card[];
const currencies = currenciesJson as unknown as Currency[];
const programs = programsJson as unknown as Program[];
const real = new Map(catalog.map((c) => [c.id, c]));

const household = (h: Partial<Household> = {}): Household => ({
  maxAnnualFee: 100000, spend3Months: 10000, spend6Months: 20000, supplementalSpend3Months: 2000, bonusTypes: [], excludedPrograms: [], ...h,
});
const player: Player = { name: "P1", history: {}, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false };
const why = (id: string, h: Partial<Household> = {}, card?: Card) => {
  const ctx = {
    household: household(h), derived: computeDerived(player, catalog), catalog, currencies, programs, unlock: new Map<string, boolean>(currencies.map((c) => [c.id, true])),
    marriottMatrix: matrixJson as unknown as MarriottMatrix,
  };
  return hardExclusion(player, card ?? real.get(id)!, ctx)?.kind ?? null;
};
const fake = (extra: Partial<Card>): Card => ({
  id: "fake", name: "fake", issuer: "citi", kind: "personal", recommendable: true, annualFee: 0, reportsToPersonal: true, bonusTypes: ["cashback"], verifiedOn: "2026-01-01", ...extra,
});

describe("spendCapacity", () => {
  const h = household(); // 3 months: 10000 + 2000; 6 months: 20000 + 2 x 2000
  it("is spend plus supplemental spend at 3 months", () => expect(spendCapacity(h, 3)).toBe(12000));
  it("is spend plus twice the supplemental spend at 6 months", () => expect(spendCapacity(h, 6)).toBe(24000));
  it("interpolates linearly in between", () => {
    expect(spendCapacity(h, 4)).toBeCloseTo(16000);
    expect(spendCapacity(h, 5)).toBeCloseTo(20000);
  });
  it("refuses windows outside 3 to 6 months rather than guess", () => {
    expect(() => spendCapacity(h, 2)).toThrow(/window/);
    expect(() => spendCapacity(h, 12)).toThrow(/window/);
  });
  it("assumes double the 3-month spend at 6 months when spend6Months was left blank (owner, 2026-09-22)", () => {
    const blank6 = household({ spend3Months: 3000, spend6Months: 0, supplementalSpend3Months: 0 });
    expect(spendCapacity(blank6, 6)).toBe(6000); // 2 x 3000, not the literal 0 stored
    expect(spendCapacity(blank6, 3)).toBe(3000); // 3-month figure itself is untouched
  });
  it("an explicit, real spend6Months of 0 is never actually meaningful (spend only ever grows), so it is always treated as blank", () => {
    // Deliberately not distinguished from "not entered": a lower real 6-month total than the 3-month total would
    // be a nonsensical answer (spend does not shrink), so there is no legitimate case this reinterprets wrongly.
    const h0 = household({ spend3Months: 5000, spend6Months: 0, supplementalSpend3Months: 0 });
    expect(spendCapacity(h0, 6)).toBe(10000);
  });
  it("treats a genuinely blank (null) spend3Months or supplementalSpend3Months as 0 (owner, 2026-09-22)", () => {
    const blank = household({ spend3Months: null, spend6Months: null, supplementalSpend3Months: null });
    expect(spendCapacity(blank, 3)).toBe(0);
    expect(spendCapacity(blank, 6)).toBe(0);
  });
  it("a null spend6Months falls back to double spend3Months, same as a stored 0", () => {
    const h = household({ spend3Months: 4000, spend6Months: null, supplementalSpend3Months: 0 });
    expect(spendCapacity(h, 6)).toBe(8000);
  });
});

describe("hardExclusion: minimum spend", () => {
  it("hides a card whose spend is above the household capacity for its window", () => {
    expect(why("", {}, fake({ typicalMinSpend: { amount: 12001, months: 3 } }))).toBe("spend");
  });
  it("keeps a card whose spend equals the capacity", () => {
    expect(why("", {}, fake({ typicalMinSpend: { amount: 12000, months: 3 } }))).toBeNull();
  });
  it("uses the capacity for the card's own window", () => {
    expect(why("", {}, fake({ typicalMinSpend: { amount: 22000, months: 6 } }))).toBeNull();
    expect(why("", {}, fake({ typicalMinSpend: { amount: 22000, months: 3 } }))).toBe("spend");
    expect(why("", {}, fake({ typicalMinSpend: { amount: 17000, months: 4 } }))).toBe("spend");
  });
  it("always keeps a card with no spend requirement", () => {
    expect(why("chase-amazon-prime", { spend3Months: 0, spend6Months: 0, supplementalSpend3Months: 0 })).toBeNull();
  });
  it("applies to real cards", () => {
    expect(why("amex-business-platinum", { spend3Months: 5000, supplementalSpend3Months: 0 })).toBe("spend"); // $20,000 in 3 months
    expect(why("chase-sapphire-preferred", { spend3Months: 5000, supplementalSpend3Months: 0 })).toBeNull();
  });
});

describe("hardExclusion: excluded programs", () => {
  const partnersOf = (id: string) => currencies.find((c) => c.id === id)!.partners;

  it("hides a co-branded card whose program is excluded", () => {
    expect(why("amex-delta-gold", { excludedPrograms: ["delta-skymiles"] })).toBe("excludedProgram");
    expect(why("amex-delta-gold", { excludedPrograms: ["united-mileageplus"] })).toBeNull();
  });

  it("excludes the Avios airlines together, by group or by id", () => {
    expect(why("chase-british-airways", { excludedPrograms: ["Avios"] })).toBe("excludedProgram");
    expect(why("chase-british-airways", { excludedPrograms: ["avios"] })).toBe("excludedProgram");
  });

  it("hides a cash card when cash back is excluded", () => {
    expect(why("amex-blue-business-cash", { excludedPrograms: ["cashback"] })).toBe("excludedProgram");
    expect(why("amex-blue-business-cash", { excludedPrograms: ["delta-skymiles"] })).toBeNull();
  });

  describe("transferable-points cards", () => {
    it("stay while any redemption is left", () => {
      const allPartners = partnersOf("ultimate-rewards");
      expect(why("chase-sapphire-preferred", { excludedPrograms: allPartners })).toBeNull(); // cash back is left
      expect(why("chase-sapphire-preferred", { excludedPrograms: [...allPartners.slice(1), "cashback"] })).toBeNull(); // one partner is left
    });
    it("are hidden only when every partner and cash back are excluded", () => {
      expect(why("chase-sapphire-preferred", { excludedPrograms: [...partnersOf("ultimate-rewards"), "cashback"] })).toBe("excludedProgram");
    });
    it("count an excluded Avios group as excluding the Avios partner", () => {
      const rest = partnersOf("ultimate-rewards").filter((p) => p !== "avios");
      expect(why("chase-sapphire-preferred", { excludedPrograms: [...rest, "Avios", "cashback"] })).toBe("excludedProgram");
    });
    it("treat cash back as a redemption for Amex points too", () => {
      const mr = partnersOf("amex-membership-rewards");
      const gold = real.get("amex-gold")!;
      const isExcluded = (excluded: string[]) => excludedByProgram(gold, household({ excludedPrograms: excluded }), currencies, programs);
      expect(isExcluded(mr)).toBe(false); // cash back is left, even though it is a poor redemption for Amex points
      expect(isExcluded([...mr, "cashback"])).toBe(true);
      expect(why("amex-gold", { excludedPrograms: [...mr, "cashback"] })).toBe("excludedProgram");
    });
  });

  it("never hides a card whose miles have no program in the data", () => {
    expect(why("barclays-lufthansa", { excludedPrograms: programs.map((p) => p.id).concat(["cashback"]) })).toBeNull();
  });
});
