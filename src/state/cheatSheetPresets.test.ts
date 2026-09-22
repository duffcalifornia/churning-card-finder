import { describe, expect, it } from "vitest";
import { CHEAT_SHEET_PRESETS, presetProfile, rankForPreset } from "./cheatSheetPresets";
import { computeDerived } from "../engine/computeDerived";
import type { Card, Currency, EngineData, Program } from "../engine/types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";
import valuationsJson from "../../data/valuations.json";
import matrixJson from "../../data/marriott-matrix.json";

const data: EngineData = {
  catalog: cardsJson as unknown as Card[],
  currencies: currenciesJson as unknown as Currency[],
  programs: programsJson as unknown as Program[],
  valuations: valuationsJson as unknown as EngineData["valuations"],
  marriottMatrix: matrixJson as unknown as EngineData["marriottMatrix"],
};
const byId = (id: string) => data.catalog.find((c) => c.id === id)!;
const ids = (preset: (typeof CHEAT_SHEET_PRESETS)[number]) => rankForPreset(preset, data, "net").map((e) => e.cardId);
const preset = (fiveTwentyFour: "under" | "over", focus: "cashback" | "travel") =>
  CHEAT_SHEET_PRESETS.find((p) => p.fiveTwentyFour === fiveTwentyFour && p.focus === focus)!;

describe("CHEAT_SHEET_PRESETS", () => {
  it("has exactly the four combinations", () => {
    expect(CHEAT_SHEET_PRESETS).toHaveLength(4);
    for (const f of ["under", "over"] as const) {
      for (const b of ["cashback", "travel"] as const) {
        expect(CHEAT_SHEET_PRESETS.filter((p) => p.fiveTwentyFour === f && p.focus === b)).toHaveLength(1);
      }
    }
  });
});

describe("rankForPreset: shows everything, not a top 5", () => {
  it("returns far more than 5 cards for a permissive preset", () => {
    expect(ids(preset("under", "travel")).length).toBeGreaterThan(20);
  });

  it("never adds a 'backup' label: there is no cutoff for a ceiling offer to fall outside of", () => {
    const r = rankForPreset(preset("under", "travel"), data, "net");
    expect(r.every((e) => e.players.every((p) => !p.backup))).toBe(true);
  });
});

describe("rankForPreset: assumes no history at all", () => {
  it("never triggers a lifetime, family, or cooldown block (nothing was ever held)", () => {
    // Chase Sapphire Reserve is once-per-lifetime; with no history it must be eligible under "under 5/24".
    expect(ids(preset("under", "travel"))).toContain("chase-sapphire-reserve");
    // An Amex family: Platinum (higher tier) must still show since nothing was ever held (no NLL-only mark needed).
    const platinum = rankForPreset(preset("under", "travel"), data, "net").find((e) => e.cardId === "amex-platinum");
    expect(platinum?.players[0]?.viaNllOnly).toBeUndefined();
  });

  it("never hides a card for minimum spend: spend is effectively unlimited", () => {
    // Business Platinum needs $20,000 in 3 months, the highest in the catalog.
    expect(ids(preset("under", "travel"))).toContain("amex-business-platinum");
  });
});

describe("rankForPreset: 5/24 status", () => {
  it("shows Chase personal and business cards when under 5/24", () => {
    const list = ids(preset("under", "cashback"));
    expect(list).toContain("chase-freedom-unlimited");
    expect(list).toContain("chase-ink-cash");
  });

  it("hides every Chase card, personal and business, at 5/24 or over", () => {
    const list = ids(preset("over", "cashback"));
    for (const id of list) expect(byId(id).issuer, id).not.toBe("chase");
  });

  it("does not trip Bank of America's or US Bank's separate 12-month velocity rules just from simulating 5/24", () => {
    // The synthetic history must land in the 12-24 month bucket, not under-12, or these issuers would be
    // wrongly excluded as a side effect of faking Chase's unrelated 24-month count.
    const list = ids(preset("over", "cashback"));
    expect(list.some((id) => byId(id).issuer === "boa")).toBe(true);
    expect(list.some((id) => byId(id).issuer === "usbank")).toBe(true);
  });

  it("puts the synthetic 5/24 history in the 12-24 month bucket, not under-12", () => {
    // Asserted directly against the built profile (not just its effects above) so a future refactor that moves the
    // count into the wrong bucket fails here first, with a clear reason, rather than as an obscure BoA/US Bank leak.
    const p = presetProfile(preset("over", "cashback"));
    const other = p.players[0]!.history.otherIssuersPersonal;
    expect(other?.m12to24).toBe(5);
    expect(other?.lt12 ?? 0).toBe(0);
  });

  it("puts no synthetic history at all in the under-5/24 preset", () => {
    const p = presetProfile(preset("under", "cashback"));
    expect(p.players[0]!.history.otherIssuersPersonal ?? {}).toEqual({});
    expect(computeDerived(p.players[0]!, data.catalog).x24).toBe(0);
  });
});

describe("rankForPreset: bonus focus", () => {
  it("cashback preset shows cash cards and not pure travel co-branded cards", () => {
    const list = ids(preset("under", "cashback"));
    expect(list).toContain("chase-freedom-unlimited");
    expect(list).not.toContain("amex-delta-gold");
  });

  it("travel preset shows co-branded travel cards and the currency-unlocking cards, not their lesser siblings", () => {
    const list = ids(preset("under", "travel"));
    expect(list).toContain("amex-delta-gold");
    expect(list).toContain("chase-sapphire-preferred"); // an Ultimate Rewards unlocker: always shown
    expect(list).not.toContain("chase-freedom-flex"); // UR but not an unlocker, and none is held: hidden for travel
  });
});

describe("rankForPreset: raw vs net still works", () => {
  it("produces the same set of ids regardless of rankBy, only reordered", () => {
    const net = new Set(ids(preset("under", "travel")));
    const raw = new Set(rankForPreset(preset("under", "travel"), data, "raw").map((e) => e.cardId));
    expect(raw).toEqual(net);
  });
});
