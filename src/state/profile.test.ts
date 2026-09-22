import { describe, expect, it } from "vitest";
import Ajv2020 from "ajv/dist/2020";
import {
  ISSUER_SECTIONS, clearHistory, defaultProfile, historyCardsByIssuer, issuerLabel, parseStoredProfile, setCardCount,
  setMarriottFlag, setOtherCount, setPlayerCount, setProgramChoice,
} from "./profile";
import type { Card, MarriottMatrix } from "../engine/types";
import cardsJson from "../../data/cards.json";
import matrixJson from "../../data/marriott-matrix.json";
import profileSchema from "../../data/schema/profile.schema.json";

const catalog = cardsJson as unknown as Card[];
const matrix = matrixJson as unknown as MarriottMatrix;
const validate = new Ajv2020({ strict: false }).compile(profileSchema);
const cards = (p: ReturnType<typeof defaultProfile>, i = 0) => p.players[i]!.history.cards ?? {};

describe("issuerLabel", () => {
  it("maps every real issuer id in the catalog to a real display name", () => {
    for (const c of catalog) {
      expect(issuerLabel(c.issuer)).not.toBe("");
      // schwab/morganstanley (Amex-issued brokerage cards) fold into the Amex badge, matching the history step
      if (c.issuer === "schwab" || c.issuer === "morganstanley") expect(issuerLabel(c.issuer)).toBe("American Express");
    }
  });
  it("falls back to the raw id for something not in ISSUER_SECTIONS", () => {
    expect(issuerLabel("made-up-issuer")).toBe("made-up-issuer");
  });
});

describe("defaultProfile", () => {
  it("has the requested number of players, named Player 1, Player 2, ...", () => {
    expect(defaultProfile(2).players.map((p) => p.name)).toEqual(["Player 1", "Player 2"]);
  });
  it("validates against the profile schema", () => {
    expect(validate(defaultProfile(3)), JSON.stringify(validate.errors)).toBe(true);
  });
});

describe("household defaults and program choices", () => {
  it("starts with no annual fee limit and no targeted programs", () => {
    const h = defaultProfile(1).household;
    expect(h.maxAnnualFee).toBeNull();
    expect(h.targetPrograms).toEqual([]);
  });
  it("adds and removes a targeted program", () => {
    let p = setProgramChoice(defaultProfile(1), "targeted", "world-of-hyatt", true);
    expect(p.household.targetPrograms).toEqual(["world-of-hyatt"]);
    p = setProgramChoice(p, "targeted", "world-of-hyatt", false);
    expect(p.household.targetPrograms).toEqual([]);
  });
  it("does not add a program twice", () => {
    let p = setProgramChoice(defaultProfile(1), "excluded", "cashback", true);
    p = setProgramChoice(p, "excluded", "cashback", true);
    expect(p.household.excludedPrograms).toEqual(["cashback"]);
  });
  it("a program cannot be both excluded and targeted: choosing one clears the other", () => {
    let p = setProgramChoice(defaultProfile(1), "targeted", "aeroplan", true);
    p = setProgramChoice(p, "excluded", "aeroplan", true);
    expect(p.household.excludedPrograms).toEqual(["aeroplan"]);
    expect(p.household.targetPrograms).toEqual([]);
    p = setProgramChoice(p, "targeted", "aeroplan", true);
    expect(p.household.targetPrograms).toEqual(["aeroplan"]);
    expect(p.household.excludedPrograms).toEqual([]);
  });
  it("validates against the profile schema with a blank limit and targets", () => {
    const p = setProgramChoice(defaultProfile(1), "targeted", "aeroplan", true);
    expect(validate(p), JSON.stringify(validate.errors)).toBe(true);
    const limited = { ...p, household: { ...p.household, maxAnnualFee: 250 } };
    expect(validate(limited), JSON.stringify(validate.errors)).toBe(true);
  });
});

describe("setPlayerCount", () => {
  it("adds players without touching the existing ones", () => {
    const p = setCardCount(defaultProfile(1), 0, "chase-freedom-flex", "lt12", 2);
    const q = setPlayerCount(p, 3);
    expect(q.players).toHaveLength(3);
    expect(cards(q, 0)["chase-freedom-flex"]!.approved!.lt12).toBe(2);
    expect(q.players[2]!.name).toBe("Player 3");
  });
  it("drops players from the end", () => {
    expect(setPlayerCount(defaultProfile(3), 1).players.map((p) => p.name)).toEqual(["Player 1"]);
  });
  it("keeps between 1 and 6 players", () => {
    expect(setPlayerCount(defaultProfile(2), 0).players).toHaveLength(1);
    expect(setPlayerCount(defaultProfile(2), 9).players).toHaveLength(6);
  });
  it("does not change its input", () => {
    const p = defaultProfile(1);
    const before = JSON.stringify(p);
    setPlayerCount(p, 3);
    expect(JSON.stringify(p)).toBe(before);
  });
});

describe("setCardCount", () => {
  it("records approvals in a window", () => {
    const p = setCardCount(defaultProfile(1), 0, "amex-gold", "m12to24", 1);
    expect(cards(p)["amex-gold"]).toEqual({ current: 0, approved: { m12to24: 1 } });
  });
  it("raising the current count never touches any approval window (owner, 2026-09-22)", () => {
    let p = setCardCount(defaultProfile(1), 0, "amex-gold", "gt48", 1);
    p = setCardCount(p, 0, "amex-gold", "current", 3);
    expect(cards(p)["amex-gold"]!.current).toBe(3);
    expect(cards(p)["amex-gold"]!.approved).toEqual({ gt48: 1 }); // no auto-filled lt12
  });
  it("lowering an approval window never touches current or any other window (owner, 2026-09-22)", () => {
    let p = setCardCount(defaultProfile(1), 0, "amex-gold", "lt12", 2);
    p = setCardCount(p, 0, "amex-gold", "current", 2);
    p = setCardCount(p, 0, "amex-gold", "lt12", 1);
    expect(cards(p)["amex-gold"]!.current).toBe(2); // unchanged, even though it now exceeds total approved
    expect(cards(p)["amex-gold"]!.approved).toEqual({ lt12: 1 });
  });
  it("setting one approval window never touches a different one", () => {
    let p = setCardCount(defaultProfile(1), 0, "amex-gold", "current", 1);
    p = setCardCount(p, 0, "amex-gold", "gt48", 1);
    expect(cards(p)["amex-gold"]).toEqual({ current: 1, approved: { gt48: 1 } }); // no phantom lt12
  });
  it("never lets a count go negative or fractional", () => {
    const p = setCardCount(setCardCount(defaultProfile(1), 0, "amex-gold", "lt12", -3), 0, "amex-gold", "m12to24", 1.9);
    expect(cards(p)["amex-gold"]).toEqual({ current: 0, approved: { m12to24: 1 } });
  });
  it("removes an entry whose counts are all zero", () => {
    let p = setCardCount(defaultProfile(1), 0, "amex-gold", "lt12", 1);
    p = setCardCount(p, 0, "amex-gold", "lt12", 0);
    expect(cards(p)).toEqual({});
  });
  it("affects only the chosen player", () => {
    const p = setCardCount(defaultProfile(2), 1, "amex-gold", "lt12", 1);
    expect(cards(p, 0)).toEqual({});
    expect(cards(p, 1)["amex-gold"]).toBeDefined();
  });
  it("produces a profile that validates against the schema", () => {
    const p = setCardCount(setCardCount(defaultProfile(1), 0, "amex-gold", "lt12", 1), 0, "amex-gold", "current", 1);
    expect(validate(p), JSON.stringify(validate.errors)).toBe(true);
  });
});

describe("setMarriottFlag", () => {
  it("records the 30 and 90 day answers and keeps the entry", () => {
    const p = setMarriottFlag(defaultProfile(1), 0, "chase-marriott-boundless", "approvedWithin90Days", true);
    expect(cards(p)["chase-marriott-boundless"]!.marriott).toEqual({ approvedWithin90Days: true });
    expect(validate(p), JSON.stringify(validate.errors)).toBe(true);
  });
  it("removes the flag again when unchecked and the entry is otherwise empty", () => {
    let p = setMarriottFlag(defaultProfile(1), 0, "chase-marriott-boundless", "approvedWithin90Days", true);
    p = setMarriottFlag(p, 0, "chase-marriott-boundless", "approvedWithin90Days", false);
    expect(cards(p)).toEqual({});
  });
});

describe("other personal cards", () => {
  it("records counts per issuer and for unlisted issuers", () => {
    let p = setOtherCount(defaultProfile(1), 0, "citi", "lt12", 2);
    p = setOtherCount(p, 0, "other", "m12to24", 1);
    expect(p.players[0]!.history.otherPersonalByIssuer).toEqual({ citi: { lt12: 2 } });
    expect(p.players[0]!.history.otherIssuersPersonal).toEqual({ m12to24: 1 });
    expect(validate(p), JSON.stringify(validate.errors)).toBe(true);
  });
  it("drops an issuer whose counts return to zero", () => {
    const p = setOtherCount(setOtherCount(defaultProfile(1), 0, "citi", "lt12", 2), 0, "citi", "lt12", 0);
    expect(p.players[0]!.history.otherPersonalByIssuer).toEqual({});
  });
});

describe("clearHistory", () => {
  it("empties one player's history, for the 'no cards' shortcut", () => {
    let p = setCardCount(defaultProfile(2), 0, "amex-gold", "lt12", 1);
    p = setCardCount(p, 1, "amex-gold", "lt12", 1);
    p = clearHistory(p, 0);
    expect(cards(p, 0)).toEqual({});
    expect(cards(p, 1)["amex-gold"]).toBeDefined();
  });
});

describe("parseStoredProfile", () => {
  it("returns a saved profile", () => {
    const p = defaultProfile(2);
    expect(parseStoredProfile(JSON.stringify(p))).toEqual(p);
  });
  it("accepts a blank annual fee limit, and a profile saved before targeted programs existed", () => {
    const p = defaultProfile(1);
    expect(parseStoredProfile(JSON.stringify(p))).not.toBeNull();
    const old = { ...p, household: { ...p.household, maxAnnualFee: 300 } } as unknown as Record<string, Record<string, unknown>>;
    delete old.household!.targetPrograms;
    expect(parseStoredProfile(JSON.stringify(old))).not.toBeNull();
  });
  it("returns null for damaged or unknown-version data instead of crashing", () => {
    expect(parseStoredProfile("not json")).toBeNull();
    expect(parseStoredProfile("{}")).toBeNull();
    expect(parseStoredProfile(JSON.stringify({ ...defaultProfile(1), version: 2 }))).toBeNull();
    expect(parseStoredProfile(JSON.stringify({ version: 1, players: [], household: {} }))).toBeNull();
    expect(parseStoredProfile(null)).toBeNull();
  });
});

describe("historyCardsByIssuer", () => {
  const sections = historyCardsByIssuer(catalog, matrix);
  const idsIn = (section: string) => (sections.get(section) ?? []).map((c) => c.id);

  it("has a section for each issuer the design lists", () => {
    expect(ISSUER_SECTIONS.map((s) => s.id)).toEqual([
      "chase", "amex", "boa", "citi", "usbank", "wellsfargo", "bilt", "barclays", "capone", "discover", "fnbo",
    ]);
  });
  it("lists cards that can be recommended", () => {
    expect(idsIn("chase")).toContain("chase-sapphire-preferred");
    expect(idsIn("capone")).toContain("capone-venture-x");
  });
  it("includes history-only cards that a rule names", () => {
    expect(idsIn("citi")).toContain("citi-premier");
    expect(idsIn("citi")).toContain("citi-strata-student");
    expect(idsIn("chase")).toContain("chase-ritz-carlton");
    expect(idsIn("amex")).toContain("amex-marriott-bonvoy");
    expect(idsIn("amex")).toContain("amex-delta-options");
  });
  it("puts Schwab and Morgan Stanley cards under Amex", () => {
    expect(idsIn("amex")).toContain("schwab-platinum");
    expect(idsIn("amex")).toContain("morganstanley-platinum");
  });
  it("lists every card the Marriott matrix or a lifetime rule names", () => {
    const all = new Set([...sections.values()].flat().map((c) => c.id));
    for (const c of matrix.cards ?? []) expect(all.has(c.id), c.id).toBe(true);
    for (const c of catalog) for (const other of c.bonusRules?.lifetimeAlsoBlockedBy ?? []) expect(all.has(other), other).toBe(true);
  });
  it("lists every card that has a family or an Amex charge card flag, and reporting business cards", () => {
    const all = new Set([...sections.values()].flat().map((c) => c.id));
    for (const c of catalog.filter((c) => c.family || c.chargeCard || (c.kind === "business" && c.reportsToPersonal))) {
      expect(all.has(c.id), c.id).toBe(true);
    }
  });
  it("lists no card twice", () => {
    const all = [...sections.values()].flat().map((c) => c.id);
    expect(new Set(all).size).toBe(all.length);
  });
});
