import { describe, expect, it } from "vitest";
import { formatDate, oldestVerifiedOn } from "./staleness";
import type { Card } from "../engine/types";
import cardsJson from "../../data/cards.json";
import valuationsJson from "../../data/valuations.json";

const card = (id: string, extra: Partial<Card> = {}): Card => ({
  id, name: id, issuer: "citi", kind: "personal", recommendable: true, annualFee: 0, reportsToPersonal: true,
  verifiedOn: "2026-09-20", ...extra,
});

describe("formatDate", () => {
  it("writes an ISO date as a plain-language date", () => {
    expect(formatDate("2026-09-20")).toBe("September 20, 2026");
    expect(formatDate("2026-01-05")).toBe("January 5, 2026");
    expect(formatDate("2026-12-31")).toBe("December 31, 2026");
  });

  it("does not shift across a timezone boundary (parses the date as local components, not through UTC)", () => {
    // A naive `new Date("2026-09-20").toLocaleDateString()` can print September 19th west of UTC; this must not.
    for (const iso of ["2026-01-01", "2026-06-15", "2026-12-31"]) {
      expect(formatDate(iso).endsWith(iso.slice(0, 4))).toBe(true);
      expect(formatDate(iso)).not.toMatch(/undefined|NaN/);
    }
  });
});

describe("oldestVerifiedOn", () => {
  it("is the earliest verifiedOn among ranked cards", () => {
    const catalog = [card("a", { verifiedOn: "2026-09-21" }), card("b", { verifiedOn: "2026-09-18" }), card("c", { verifiedOn: "2026-09-25" })];
    expect(oldestVerifiedOn(catalog)).toBe("2026-09-18");
  });

  it("ignores cards that are not recommendable or have no ranked value", () => {
    const catalog = [
      card("a", { verifiedOn: "2026-09-25" }),
      card("b", { verifiedOn: "2026-01-01", recommendable: false }),
      card("c", { verifiedOn: "2026-01-02", unrankedReason: "no valuation" }),
    ];
    expect(oldestVerifiedOn(catalog)).toBe("2026-09-25");
  });

  it("is null for an empty or all-excluded catalog", () => {
    expect(oldestVerifiedOn([])).toBeNull();
    expect(oldestVerifiedOn([card("a", { recommendable: false })])).toBeNull();
  });

  it("is the oldest date in the real catalog, and it is a plausible recent date", () => {
    const oldest = oldestVerifiedOn(cardsJson as unknown as Card[]);
    expect(oldest).not.toBeNull();
    expect(oldest! >= "2026-01-01").toBe(true);
  });
});

describe("real valuations data has a verifiedOn to show alongside it", () => {
  it("formats cleanly", () => {
    const v = valuationsJson as unknown as { verifiedOn: string };
    expect(formatDate(v.verifiedOn)).not.toMatch(/undefined|NaN/);
  });
});
