import { describe, expect, it } from "vitest";
import { hardExclusion } from "./hardExclusion";
import { computeDerived } from "./computeDerived";
import { unlockStatus } from "./unlockStatus";
import type { Card, CardHistoryEntry, Currency, Household, MarriottMatrix, Player, Program } from "./types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";
import matrixJson from "../../data/marriott-matrix.json";

const catalog = cardsJson as unknown as Card[];
const currencies = currenciesJson as unknown as Currency[];
const programs = programsJson as unknown as Program[];
const real = new Map(catalog.map((c) => [c.id, c]));

const held = (): CardHistoryEntry => ({ current: 1, approved: { gt48: 1 } });
const person = (cards: Record<string, CardHistoryEntry> = {}, extra: Partial<Player> = {}, name = "P1"): Player => ({
  name, history: { cards }, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false, ...extra,
});
const house = (bonusTypes: string[], excludedPrograms: string[] = []): Household => ({
  maxAnnualFee: 100000, spend3Months: 1e9, spend6Months: 1e9, supplementalSpend3Months: 0, bonusTypes, excludedPrograms,
});

/** Why the card is hidden for this player, given the household's wanted types (others in the household can pool unlockers). */
function why(id: string, types: string[], p: Player = person(), opts: { excluded?: string[]; others?: Player[] } = {}) {
  const players = [p, ...(opts.others ?? [])];
  const ctx = {
    household: house(types, opts.excluded), derived: computeDerived(p, catalog), catalog, currencies, programs,
    unlock: unlockStatus(players, currencies).get(p.name)!,
    marriottMatrix: matrixJson as unknown as MarriottMatrix,
  };
  return hardExclusion(p, real.get(id)!, ctx)?.kind ?? null;
}

describe("unranked cards", () => {
  it("are hidden: the cards with no valuation and the Discover cash back match cards", () => {
    for (const id of ["barclays-breeze", "barclays-carnival", "barclays-emirates-premium", "barclays-emirates-rewards",
                      "boa-allways-rewards", "boa-norwegian-cruise", "discover-it-cash-back", "discover-it-chrome", "discover-it-miles"]) {
      expect(why(id, []), id).toBe("unranked");
    }
  });
});

describe("bonus types wanted", () => {
  it("treats an empty selection as all types", () => {
    for (const id of ["amex-blue-business-cash", "amex-delta-gold", "amex-hilton-surpass", "chase-freedom-flex"]) {
      expect(why(id, []), id).toBeNull();
    }
  });

  it("keeps cash cards for cash back and hides them otherwise", () => {
    expect(why("amex-blue-business-cash", ["cashback"])).toBeNull();
    expect(why("amex-blue-business-cash", ["airline", "hotel"])).toBe("noWantedBonusType");
    expect(why("amex-blue-business-cash", ["airline", "cashback"])).toBeNull();
  });

  it("matches co-branded cards to their program's kind", () => {
    expect(why("amex-delta-gold", ["airline"])).toBeNull();
    expect(why("amex-delta-gold", ["hotel", "cashback"])).toBe("noWantedBonusType");
    expect(why("amex-hilton-surpass", ["hotel"])).toBeNull();
    expect(why("amex-hilton-surpass", ["airline"])).toBe("noWantedBonusType");
  });

  it("matches airline miles that have no program in the data by the card's own type", () => {
    expect(why("barclays-lufthansa", ["airline"])).toBeNull();
    expect(why("barclays-lufthansa", ["hotel"])).toBe("noWantedBonusType");
  });

  it("treats bank points as cash back", () => {
    expect(why("boa-premium-rewards", ["cashback"])).toBeNull();
    expect(why("boa-premium-rewards", ["airline"])).toBe("noWantedBonusType");
  });
});

describe("unlocking transferable currencies", () => {
  it("shows only the unlocker cards to a travel player who has no unlocker", () => {
    for (const id of ["chase-sapphire-preferred", "chase-sapphire-reserve", "chase-sapphire-reserve-business", "chase-ink-preferred"]) {
      expect(why(id, ["airline"]), id).toBeNull();
    }
    for (const id of ["chase-freedom-flex", "chase-freedom-unlimited", "chase-ink-cash", "chase-ink-unlimited"]) {
      expect(why(id, ["airline"]), id).toBe("noUnlocker");
      expect(why(id, ["airline", "hotel"]), id).toBe("noUnlocker");
    }
  });

  it("shows the lesser cards once the player holds an unlocker", () => {
    const p = person({ "chase-sapphire-preferred": held() });
    expect(why("chase-freedom-flex", ["airline"], p)).toBeNull();
    expect(why("chase-ink-cash", ["hotel"], p)).toBeNull();
  });

  it("counts another player's unlocker where points pool (Chase), but not where they do not (Citi)", () => {
    const other = person({ "chase-sapphire-preferred": held(), "citi-strata-premier": held() }, {}, "P2");
    expect(why("chase-freedom-flex", ["airline"], person(), { others: [other] })).toBeNull();
    const citiLesser = catalog.find((c) => c.currency === "citi-thankyou" && !currencies.find((x) => x.id === "citi-thankyou")!.unlockerCards.includes(c.id) && c.recommendable);
    if (citiLesser) expect(why(citiLesser.id, ["airline"], person(), { others: [other] })).toBe("noUnlocker");
  });

  it("lets a cash back player keep the lesser cards, since the points cash out well", () => {
    expect(why("chase-freedom-flex", ["cashback"])).toBeNull();
  });

  it("keeps a lesser card for a player who wants both travel and cash back (cash back is an acceptable redemption)", () => {
    expect(why("chase-freedom-flex", ["airline", "cashback"])).toBeNull();
  });

  it("hides the lesser cards when cash back is excluded and there is no unlocker", () => {
    expect(why("chase-freedom-flex", ["cashback"], person(), { excluded: ["cashback"] })).toBe("noWantedBonusType");
  });

  it("hides a card whose partners of the wanted kind are all excluded, even when unlocked", () => {
    const p = person({ "chase-sapphire-preferred": held() });
    const airlines = programs.filter((x) => x.kind === "airline").map((x) => x.id);
    expect(why("chase-freedom-flex", ["airline"], p, { excluded: airlines })).toBe("noWantedBonusType");
    expect(why("chase-freedom-flex", ["hotel"], p, { excluded: airlines })).toBeNull();
  });

  it("behaves the same way for every currency that has unlocker cards (Chase, Citi, Capital One)", () => {
    for (const cur of currencies.filter((c) => c.unlockerCards.length > 0)) {
      const cards = catalog.filter((c) => c.currency === cur.id && c.recommendable && !c.unrankedReason);
      expect(cards.length, cur.id).toBeGreaterThan(0);
      for (const c of cards) {
        const unlocker = cur.unlockerCards.includes(c.id);
        expect(why(c.id, ["airline"]), c.id).toBe(unlocker ? null : "noUnlocker");
      }
    }
  });
});

describe("Amex points cash-out", () => {
  const schwabHeld = () => person({ "schwab-platinum": held() });

  it("always counts for travel", () => {
    expect(why("amex-gold", ["airline"])).toBeNull();
    expect(why("amex-blue-business-plus", ["hotel"])).toBeNull();
  });

  it("does not count as cash back for a player with no qualifying setup", () => {
    expect(why("amex-gold", ["cashback"])).toBe("noWantedBonusType");
    expect(why("amex-gold", ["cashback"], person({ "amex-business-platinum": held() }))).toBe("noWantedBonusType");
    expect(why("amex-gold", ["cashback"], person({}, { hasAmexBusinessChecking: true }))).toBe("noWantedBonusType");
  });

  it("counts with a Schwab Platinum held now", () => {
    expect(why("amex-gold", ["cashback"], schwabHeld())).toBeNull();
  });

  it("does not count a Schwab Platinum that was closed", () => {
    expect(why("amex-gold", ["cashback"], person({ "schwab-platinum": { current: 0, approved: { gt48: 1 } } }))).toBe("noWantedBonusType");
  });

  it("counts with a Business Platinum held now plus a business checking account", () => {
    const p = person({ "amex-business-platinum": held() }, { hasAmexBusinessChecking: true });
    expect(why("amex-gold", ["cashback"], p)).toBeNull();
  });

  it("does not pool across players", () => {
    const other = schwabHeld();
    other.name = "P2";
    expect(why("amex-gold", ["cashback"], person(), { others: [other] })).toBe("noWantedBonusType");
  });

  it("counts the Schwab Platinum's own bonus as cashable, but the Business Platinum's only with checking", () => {
    expect(why("schwab-platinum", ["cashback"])).toBeNull();
    expect(why("amex-business-platinum", ["cashback"])).toBe("noWantedBonusType");
    expect(why("amex-business-platinum", ["cashback"], person({}, { hasAmexBusinessChecking: true }))).toBeNull();
  });
});
