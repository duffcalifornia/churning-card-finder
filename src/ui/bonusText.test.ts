import { describe, expect, it } from "vitest";
import { describeBonus } from "./bonusText";
import type { Card, Currency, Program } from "../engine/types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";

const catalog = cardsJson as unknown as Card[];
const currencies = currenciesJson as unknown as Currency[];
const programs = programsJson as unknown as Program[];
const text = (id: string) => describeBonus(catalog.find((c) => c.id === id)!, currencies, programs);
/** A real card with its offer replaced, for wording tests that should not break when the live offer changes. */
const textWith = (id: string, extra: Partial<Card>) => describeBonus({ ...catalog.find((c) => c.id === id)!, ...extra }, currencies, programs);

describe("describeBonus", () => {
  it("names transferable points by their currency", () => {
    expect(text("chase-sapphire-preferred")).toEqual(["75,000 Chase Ultimate Rewards points"]);
  });
  it("still names the currency plainly when there is no extra tier", () => {
    expect(text("amex-hilton-surpass")[0]).toBe("130,000 Hilton Honors points");
  });
  it("shows the advertised cash figure for points paid as cash back", () => {
    expect(text("chase-ink-cash")).toEqual(["75,000 Chase Ultimate Rewards points (advertised as $750)"]);
  });
  it("adds miles or points to a program name only when it does not already say so", () => {
    expect(text("chase-aeroplan")[0]).toContain("75,000 Air Canada Aeroplan miles");
    expect(text("amex-hilton-surpass")[0]).toBe("130,000 Hilton Honors points");
    expect(text("amex-delta-gold")[0]).toContain("Delta SkyMiles");
    expect(text("amex-delta-gold")[0]).not.toContain("miles miles");
  });
  it("marks an 'as high as' offer with Up to, on the first amount only", () => {
    expect(text("amex-delta-gold")).toEqual(["Up to 80,000 Delta SkyMiles"]); // Amex's page dropped the $250 statement credit, 2026-10-08
    expect(text("amex-gold")[0]).toBe("Up to 100,000 Amex Membership Rewards points");
  });
  it("puts Up to on a cash-only ceiling offer", () => {
    expect(textWith("amex-blue-cash-everyday", { welcomeBonus: { cashBack: 200, ceiling: true } }))
      .toEqual(["Up to $200 statement credit or cash back"]);
  });
  it("shows cash and free nights", () => {
    expect(textWith("amex-blue-business-cash", { welcomeBonus: { cashBack: 250 } })).toEqual(["$250 statement credit or cash back"]);
    expect(textWith("amex-hilton-surpass", { welcomeBonus: { points: 130000, freeNights: 1, otherValue: 521 } }))
      .toEqual(["130,000 Hilton Honors points", "1 free night award"]);
    // Boundless's own offer became 200,000 points on 2026-11-06; the wording is checked on its earlier offer.
    expect(textWith("chase-marriott-boundless", { welcomeBonus: { freeNights: 3, otherValue: 822 } })).toEqual(["3 free night awards"]);
  });
  it("phrases a cumulative second tier as a total, not as spend on top of the first (Aeroplan needs $20,000, not $24,000)", () => {
    expect(text("chase-aeroplan")).toEqual([
      "Get 75,000 Air Canada Aeroplan miles after spending $4,000 in 3 months, then get an additional 40,000 after spending $20,000 in total in 12 months",
    ]);
  });
  it("phrases a second tier that is spend at one merchant as exactly that", () => {
    // The Wyndham Earner's own offer dropped this tier on 2026-11-01; the wording is checked on its earlier offer.
    const earlier: Partial<Card> = {
      welcomeBonus: {
        points: 30000,
        additionalTiers: [{ points: 45000, minSpend: 500, windowMonths: 6, spendBasis: "merchant", merchant: "Hotels by Wyndham" }],
      },
      typicalMinSpend: { amount: 1000, months: 3 },
    };
    expect(textWith("barclays-wyndham-earner", earlier)).toEqual([
      "Get 30,000 Wyndham Rewards points after spending $1,000 in 3 months, then get an additional 45,000 after spending $500 at Hotels by Wyndham in 6 months",
    ]);
  });
  it("keeps 'more' when the issuer's own wording says the second spend is on top of the first", () => {
    expect(text("barclays-hawaiian")).toEqual([
      "Get 60,000 Alaska Atmos Rewards miles after spending $1,000 in 3 months, then get an additional 10,000 after spending $1,000 more in 6 months",
    ]);
  });
  it("gives friendly names to currencies that are not in the currency or program lists", () => {
    expect(text("boa-premium-rewards")).toEqual(["60,000 bank points"]);
    expect(textWith("barclays-lufthansa", { welcomeBonus: { points: 70000 } })).toEqual(["70,000 Miles & More miles"]);
  });
  it("describes every ranked card, and never says undefined or NaN", () => {
    for (const c of catalog.filter((c) => c.recommendable && !c.unrankedReason)) {
      const parts = describeBonus(c, currencies, programs);
      expect(parts.length, c.id).toBeGreaterThan(0);
      for (const p of parts) expect(p, c.id).not.toMatch(/undefined|NaN|null/);
    }
  });
});
