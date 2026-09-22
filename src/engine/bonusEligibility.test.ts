import { describe, expect, it } from "vitest";
import { hardExclusion } from "./hardExclusion";
import { nllBlock } from "./nllBlock";
import { computeDerived } from "./computeDerived";
import type { Card, CardHistoryEntry, Currency, MarriottMatrix, Player, Program } from "./types";
import cardsJson from "../../data/cards.json";
import matrixJson from "../../data/marriott-matrix.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";

const catalog = cardsJson as unknown as Card[];
const real = new Map(catalog.map((c) => [c.id, c]));
const matrix = matrixJson as unknown as MarriottMatrix;

const held = (o: Partial<CardHistoryEntry> = {}): CardHistoryEntry => ({ current: 1, approved: { lt12: 1 }, ...o });
const old = (): CardHistoryEntry => ({ current: 0, approved: { gt48: 1 } });     // held long ago, closed
const recent = (): CardHistoryEntry => ({ current: 0, approved: { lt12: 1 } });  // approved within the last 12 months
const prior = (cards: Record<string, CardHistoryEntry>, extra: Partial<Player> = {}): Player => ({
  name: "P1", history: { cards }, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false, ...extra,
});

function ctxFor(p: Player) {
  return {
    household: { maxAnnualFee: 100000, spend3Months: 1e9, spend6Months: 1e9, supplementalSpend3Months: 0, bonusTypes: [], excludedPrograms: [] },
    derived: computeDerived(p, catalog),
    catalog,
    currencies: currenciesJson as unknown as Currency[],
    programs: programsJson as unknown as Program[],
    unlock: new Map<string, boolean>((currenciesJson as unknown as Currency[]).map((c) => [c.id, true])),
    marriottMatrix: matrix,
  };
}
const why = (p: Player, id: string) => hardExclusion(p, real.get(id)!, ctxFor(p))?.kind ?? null;
const nll = (p: Player, id: string) => nllBlock(p, computeDerived(p, catalog), real.get(id)!, catalog, matrix);

describe("lifetime rules that are hard exclusions (Chase and Citi)", () => {
  it("blocks a Sapphire card the player was ever approved for, even long ago", () => {
    expect(why(prior({ "chase-sapphire-preferred": old() }), "chase-sapphire-preferred")).toBe("lifetime");
    expect(why(prior({}), "chase-sapphire-preferred")).toBeNull();
  });

  it("keeps Sapphire Preferred and Reserve independent of each other", () => {
    expect(why(prior({ "chase-sapphire-preferred": old() }), "chase-sapphire-reserve")).toBeNull();
    expect(why(prior({ "chase-sapphire-reserve": old() }), "chase-sapphire-preferred")).toBeNull();
  });

  it("keeps the business Sapphire Reserve independent of the personal one", () => {
    expect(why(prior({ "chase-sapphire-reserve": old() }), "chase-sapphire-reserve-business")).toBeNull();
    expect(why(prior({ "chase-sapphire-reserve-business": old() }), "chase-sapphire-reserve-business")).toBe("lifetime");
  });

  it("blocks an Ink card the player was ever approved for, but not the other Ink cards", () => {
    expect(why(prior({ "chase-ink-cash": old() }), "chase-ink-cash")).toBe("lifetime");
    expect(why(prior({ "chase-ink-cash": old() }), "chase-ink-unlimited")).toBeNull();
  });

  it("lifts the Ink lifetime block when the player is willing to form a qualifying-state LLC", () => {
    const p = prior({ "chase-ink-cash": old() }, { willingToFormLlcForInk: true });
    expect(why(p, "chase-ink-cash")).toBeNull();
  });

  it("the LLC workaround does not lift the lifetime block for non-Ink Chase cards", () => {
    const p = prior({ "chase-sapphire-preferred": old() }, { willingToFormLlcForInk: true });
    expect(why(p, "chase-sapphire-preferred")).toBe("lifetime");
  });

  it("without opting in, the Ink lifetime block still applies", () => {
    const p = prior({ "chase-ink-cash": old() }, { willingToFormLlcForInk: false });
    expect(why(p, "chase-ink-cash")).toBe("lifetime");
  });

  it("blocks Strata after a Strata Student, Strata Premier after a Citi Premier, and Elite only after an Elite", () => {
    expect(why(prior({ "citi-strata-student": old() }), "citi-strata")).toBe("lifetime");
    expect(why(prior({ "citi-strata": old() }), "citi-strata")).toBe("lifetime");
    expect(why(prior({ "citi-premier": old() }), "citi-strata-premier")).toBe("lifetime");
    expect(why(prior({ "citi-strata-premier": old() }), "citi-strata-premier")).toBe("lifetime");
    expect(why(prior({ "citi-strata-premier": old(), "citi-strata": old(), "citi-premier": old() }), "citi-strata-elite")).toBeNull();
    expect(why(prior({ "citi-strata-elite": old() }), "citi-strata-elite")).toBe("lifetime");
  });

  it("does not block Strata because of a Strata Premier (different families)", () => {
    expect(why(prior({ "citi-strata-premier": old() }), "citi-strata")).toBeNull();
  });
});

describe("family rules that are hard exclusions (Capital One Venture)", () => {
  it("blocks a lower Venture card after a higher one, never the reverse", () => {
    expect(why(prior({ "capone-venture-x": old() }), "capone-venture")).toBe("family");
    expect(why(prior({ "capone-venture-x": old() }), "capone-ventureone")).toBe("family");
    expect(why(prior({ "capone-venture": old() }), "capone-ventureone")).toBe("family");
    expect(why(prior({ "capone-ventureone": old() }), "capone-venture")).toBeNull();
    expect(why(prior({ "capone-venture": old() }), "capone-venture-x")).toBeNull();
  });

  it("leaves the business Venture X and Savor outside the family", () => {
    expect(why(prior({ "capone-venture-x": old() }), "capone-venture-x-business")).toBeNull();
    expect(why(prior({ "capone-venture-x": old() }), "capone-savor")).toBeNull();
  });
});

describe("Amex lifetime and family blocks are NLL blocks, not hard exclusions", () => {
  it("does not hide an Amex card the player has had before, but reports a lifetime NLL block", () => {
    const p = prior({ "amex-platinum": old() });
    expect(why(p, "amex-platinum")).toBeNull();
    expect(nll(p, "amex-platinum")).toBe("lifetime");
  });

  it("reports a family block for a lower card after a higher one", () => {
    const p = prior({ "amex-delta-reserve": old() });
    expect(why(p, "amex-delta-gold")).toBeNull();
    expect(nll(p, "amex-delta-gold")).toBe("family");
    expect(nll(p, "amex-delta-blue")).toBe("family");
    expect(nll(p, "amex-delta-reserve")).toBe("lifetime");
  });

  it("gives lifetime precedence when both apply", () => {
    expect(nll(prior({ "amex-gold": old(), "amex-platinum": old() }), "amex-gold")).toBe("lifetime");
  });

  it("does not block a card from the same tier or a higher one", () => {
    expect(nll(prior({ "amex-platinum": old() }), "schwab-platinum")).toBeNull();
    expect(nll(prior({ "amex-gold": old() }), "amex-platinum")).toBeNull();
  });

  it("covers the Blue Cash, Hilton and Delta business families", () => {
    expect(nll(prior({ "amex-blue-cash-preferred": old() }), "amex-blue-cash-everyday")).toBe("family");
    expect(nll(prior({ "amex-hilton-ascend": old() }), "amex-hilton-surpass")).toBe("family");
    expect(nll(prior({ "amex-hilton-surpass": old() }), "amex-hilton-aspire")).toBeNull();
    expect(nll(prior({ "amex-delta-platinum-business": old() }), "amex-delta-gold-business")).toBe("family");
    expect(nll(prior({ "amex-delta-reserve": old() }), "amex-delta-gold-business")).toBeNull();
  });

  it("applies to Amex-issued partner cards", () => {
    expect(nll(prior({ "schwab-platinum": old() }), "amex-gold")).toBe("family");
    expect(nll(prior({ "morganstanley-platinum": old() }), "morganstanley-platinum")).toBe("lifetime");
  });

  it("never applies to other issuers", () => {
    expect(nll(prior({ "chase-sapphire-preferred": old() }), "chase-sapphire-preferred")).toBeNull();
    expect(nll(prior({}), "chase-freedom-flex")).toBeNull();
  });

  it("treats Amex Marriott cards like every Amex card: lifetime language, lifted only by an NLL offer", () => {
    expect(nll(prior({ "amex-marriott-bevy": old() }), "amex-marriott-bevy")).toBe("lifetime");
    expect(nll(prior({}), "amex-marriott-bevy")).toBeNull();
  });
});

describe("cooldown rules", () => {
  const at = (bucket: "lt12" | "m12to24" | "m24to48" | "gt48", current = 0): CardHistoryEntry => ({ current, approved: { [bucket]: 1 } });

  describe("Chase: 24 months, and never while the card is open", () => {
    it("blocks a card that is currently held", () => {
      expect(why(prior({ "chase-freedom-flex": at("gt48", 1) }), "chase-freedom-flex")).toBe("cooldown");
    });
    it("blocks a card approved in the last 24 months, even if closed", () => {
      expect(why(prior({ "chase-freedom-flex": at("lt12") }), "chase-freedom-flex")).toBe("cooldown");
      expect(why(prior({ "chase-freedom-flex": at("m12to24") }), "chase-freedom-flex")).toBe("cooldown");
    });
    it("allows it again once it is older than 24 months and closed", () => {
      expect(why(prior({ "chase-freedom-flex": at("m24to48") }), "chase-freedom-flex")).toBeNull();
      expect(why(prior({ "chase-freedom-flex": at("gt48") }), "chase-freedom-flex")).toBeNull();
    });
    it("does not let a different Chase card block it", () => {
      expect(why(prior({ "chase-freedom-unlimited": at("lt12", 1) }), "chase-freedom-flex")).toBeNull();
    });
  });

  describe("Southwest personal cards share one clock", () => {
    it("blocks any personal Southwest card while another is held", () => {
      expect(why(prior({ "chase-southwest-priority": at("gt48", 1) }), "chase-southwest-plus")).toBe("cooldown");
    });
    it("blocks them for 24 months after a bonus on any personal Southwest card", () => {
      expect(why(prior({ "chase-southwest-premier": at("m12to24") }), "chase-southwest-plus")).toBe("cooldown");
      expect(why(prior({ "chase-southwest-premier": at("m24to48") }), "chase-southwest-plus")).toBeNull();
    });
    it("keeps personal and business Southwest cards apart", () => {
      expect(why(prior({ "chase-southwest-plus": at("lt12", 1) }), "chase-southwest-premier-business")).toBeNull();
      expect(why(prior({ "chase-southwest-premier-business": at("lt12", 1) }), "chase-southwest-plus")).toBeNull();
    });
  });

  describe("IHG personal cards share one clock", () => {
    it("blocks the other personal IHG card while one is held or was recent", () => {
      expect(why(prior({ "chase-ihg-premier": at("gt48", 1) }), "chase-ihg-traveler")).toBe("cooldown");
      expect(why(prior({ "chase-ihg-traveler": at("m12to24") }), "chase-ihg-premier")).toBe("cooldown");
    });
    it("does not involve the IHG business card", () => {
      expect(why(prior({ "chase-ihg-premier": at("lt12", 1) }), "chase-ihg-premier-business")).toBeNull();
    });
  });

  describe("48 months: Citi, and Capital One personal cards", () => {
    it("blocks the same Citi card for 48 months, counted from approval", () => {
      expect(why(prior({ "citi-double-cash": at("m24to48") }), "citi-double-cash")).toBe("cooldown");
      expect(why(prior({ "citi-double-cash": at("gt48") }), "citi-double-cash")).toBeNull();
    });
    it("does not block a different Citi card", () => {
      expect(why(prior({ "citi-double-cash": at("lt12") }), "citi-aadvantage-platinum-select")).toBeNull();
    });
    it("blocks the same Capital One personal card for 48 months", () => {
      expect(why(prior({ "capone-quicksilver": at("m24to48") }), "capone-quicksilver")).toBe("cooldown");
      expect(why(prior({ "capone-quicksilver": at("gt48") }), "capone-quicksilver")).toBeNull();
    });
    it("has no rule for Capital One business cards", () => {
      expect(why(prior({ "capone-spark-cash": at("lt12", 1) }), "capone-spark-cash")).toBeNull();
    });
  });

  describe("Bank of America: held-based, personal cards only", () => {
    it("blocks a personal card that is held or was held within about 24 months", () => {
      expect(why(prior({ "boa-unlimited-cash": at("gt48", 1) }), "boa-unlimited-cash")).toBe("cooldown");
      expect(why(prior({ "boa-unlimited-cash": at("m12to24") }), "boa-unlimited-cash")).toBe("cooldown");
      expect(why(prior({ "boa-unlimited-cash": at("m24to48") }), "boa-unlimited-cash")).toBeNull();
    });
    it("has no rule for business cards", () => {
      expect(why(prior({ "boa-business-unlimited-cash": at("lt12", 1) }), "boa-business-unlimited-cash")).toBeNull();
    });
  });

  describe("cards that only cannot be held twice, or have no rule", () => {
    it("blocks a Barclays card only while it is held", () => {
      expect(why(prior({ "barclays-jetblue": at("gt48", 1) }), "barclays-jetblue")).toBe("cooldown");
      expect(why(prior({ "barclays-jetblue": at("lt12") }), "barclays-jetblue")).toBeNull();
    });
    it("has no cooldown for US Bank or Amex cards", () => {
      expect(why(prior({ "usbank-triple-cash": at("lt12", 1) }), "usbank-triple-cash")).toBeNull();
      expect(why(prior({ "amex-hilton-aspire": at("lt12", 1) }), "amex-hilton-aspire")).toBeNull();
    });
  });
});

describe("Marriott eligibility matrix", () => {
  const closedLongAgo = (): CardHistoryEntry => ({ current: 0, approved: { gt48: 1 } });
  const bonus = (bucket: "lt12" | "m12to24" | "m24to48"): CardHistoryEntry => ({ current: 0, approved: { [bucket]: 1 } });

  it("lets a card through when the player has none of the Marriott cards", () => {
    for (const id of ["chase-marriott-bold", "chase-marriott-boundless", "chase-marriott-bountiful",
                      "amex-marriott-business", "amex-marriott-brilliant", "amex-marriott-bevy"]) {
      expect(why(prior({}), id), id).toBeNull();
    }
  });

  it("applies the 24 month bonus window (Premier blocks Bold and Boundless)", () => {
    expect(why(prior({ "chase-marriott-premier": bonus("m12to24") }), "chase-marriott-bold")).toBe("marriottMatrix");
    expect(why(prior({ "chase-marriott-premier": bonus("m24to48") }), "chase-marriott-bold")).toBeNull();
    expect(why(prior({ "chase-marriott-premier": bonus("lt12") }), "chase-marriott-bountiful")).toBeNull(); // Premier does not block Bountiful
  });

  it("blocks a card the player currently holds under a 24 month rule", () => {
    expect(why(prior({ "chase-marriott-bountiful": { current: 1, approved: { gt48: 1 } } }), "chase-marriott-bountiful")).toBe("marriottMatrix");
  });

  it("applies the 30 day rule to a held card or one closed within 30 days", () => {
    expect(why(prior({ "amex-marriott-bonvoy": { current: 1, approved: { gt48: 1 } } }), "chase-marriott-bold")).toBe("marriottMatrix");
    expect(why(prior({ "amex-marriott-bonvoy": { ...closedLongAgo(), marriott: { closedWithin30Days: true } } }), "chase-marriott-bold")).toBe("marriottMatrix");
    expect(why(prior({ "amex-marriott-bonvoy": closedLongAgo() }), "chase-marriott-bold")).toBeNull();
  });

  it("applies the 90 day approval rule together with the 24 month bonus rule (Bold before Amex Business)", () => {
    expect(why(prior({ "chase-marriott-bold": { ...closedLongAgo(), marriott: { approvedWithin90Days: true } } }), "amex-marriott-business")).toBe("marriottMatrix");
    expect(why(prior({ "chase-marriott-bold": bonus("m12to24") }), "amex-marriott-business")).toBe("marriottMatrix");
    expect(why(prior({ "chase-marriott-bold": closedLongAgo() }), "amex-marriott-business")).toBeNull();
  });

  it("applies all three windows for a Bevy after Boundless", () => {
    expect(why(prior({ "chase-marriott-boundless": { ...closedLongAgo(), marriott: { closedWithin30Days: true } } }), "amex-marriott-bevy")).toBe("marriottMatrix");
    expect(why(prior({ "chase-marriott-boundless": { ...closedLongAgo(), marriott: { approvedWithin90Days: true } } }), "amex-marriott-bevy")).toBe("marriottMatrix");
    expect(why(prior({ "chase-marriott-boundless": bonus("m12to24") }), "amex-marriott-bevy")).toBe("marriottMatrix");
    expect(why(prior({ "chase-marriott-boundless": closedLongAgo() }), "amex-marriott-bevy")).toBeNull();
  });

  it("treats the matrix's ever-blocks on Amex cards as lifetime language: an NLL block, not a hard one", () => {
    for (const [had, want] of [["amex-marriott-business", "amex-marriott-business"], ["amex-marriott-brilliant", "amex-marriott-brilliant"],
                               ["amex-marriott-bevy", "amex-marriott-bevy"], ["amex-marriott-brilliant", "amex-marriott-bevy"]] as const) {
      const p = prior({ [had]: closedLongAgo() });
      expect(why(p, want), `${had} then ${want}`).toBeNull();
      expect(nll(p, want), `${had} then ${want}`).toBe("lifetime");
    }
  });

  it("keeps the matrix binding even with an NLL offer: the other windows still hide the card", () => {
    // had a Bevy before (NLL-liftable) but also holds a Boundless now, which blocks a Bevy for 30 days under the matrix
    const p = prior({ "amex-marriott-bevy": closedLongAgo(), "chase-marriott-boundless": { current: 1, approved: { gt48: 1 } } });
    expect(why(p, "amex-marriott-bevy")).toBe("marriottMatrix");
  });

  it("does not block in the directions the matrix marks OK (Brilliant after Bevy, Business after Bevy)", () => {
    expect(why(prior({ "amex-marriott-bevy": closedLongAgo() }), "amex-marriott-brilliant")).toBeNull();
    expect(why(prior({ "amex-marriott-bevy": closedLongAgo() }), "amex-marriott-business")).toBeNull();
  });

  it("does not use the matrix for cards without a matrix key", () => {
    expect(why(prior({ "chase-marriott-premier": bonus("lt12") }), "chase-freedom-flex")).toBeNull();
  });
});
